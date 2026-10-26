"""Um único assinador do worker, com configuração isolada por titular.

Somente processos iniciados pelo worker são gerenciados aqui. O PJeOffice do
desktop e suas preferências nunca são alterados pela coleta automática.
"""

import os
import re
import signal
import socket
import subprocess
import time
from pathlib import Path

from automation.collectors import get_collector


PID_FILE = Path("/tmp/pjeoffice-managed.pid")
_current_identity = None


def _alive(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split(") ", 1)[1][0] != "Z"
    except FileNotFoundError:
        return False


def verify_token(collector):
    module = Path(os.environ.get(f"PJE_{collector.code.upper()}_PKCS11_MODULE", collector.module))
    if not module.is_file():
        raise RuntimeError(f"Driver PKCS#11 de {collector.label} não instalado no worker: {module}.")
    result = subprocess.run(
        ["pkcs11-tool", "--module", str(module), "--list-slots"],
        capture_output=True, text=True, timeout=20,
    )
    serials = re.findall(r"^\s*serial num\s*:\s*(\S+)", result.stdout, re.MULTILINE)
    if result.returncode or [value.lower() for value in serials] != [collector.serial.lower()]:
        raise RuntimeError(
            f"O módulo de {collector.label} deve reconhecer somente o token esperado "
            f"({collector.serial}). Confira os tokens conectados antes de tentar o PIN."
        )
    if "PIN locked" in result.stdout or "pin locked" in result.stdout:
        raise RuntimeError(f"O PIN do token de {collector.label} está bloqueado.")
    return module.resolve()


def _stop_managed_office():
    if not PID_FILE.exists():
        return
    pid = int(PID_FILE.read_text().strip())
    if not _alive(pid):
        return
    command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    if not any(arg.endswith(b"pjeoffice-pro.jar") for arg in command):
        raise RuntimeError("PID do assinador não corresponde ao PJeOffice gerenciado; reinicie o worker.")
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(.1)
    if _alive(pid):
        raise RuntimeError("PJeOffice anterior não encerrou; nenhuma autenticação foi iniciada.")


def prepare_identity(code):
    global _current_identity
    collector = get_collector(code)
    if os.environ.get("PJE_OFFICE_MANAGED") != "true":
        raise RuntimeError("A coleta com dois titulares exige o PJeOffice gerenciado no worker Docker.")
    module = verify_token(collector)
    if _current_identity == code and PID_FILE.exists() and _alive(int(PID_FILE.read_text().strip())):
        return

    base = Path.home() / ".pjeoffice-pro"
    home = base / "identities" / code
    config_dir = home / ".pjeoffice-pro"
    config_dir.mkdir(parents=True, exist_ok=True)
    config = config_dir / "pjeoffice-pro.config"
    previous = config if config.exists() else base / "pjeoffice-pro.config"
    # Reaproveita somente as autorizações existentes. Seleção memorizada,
    # certificados A1 e bibliotecas de outro titular não entram neste perfil.
    trusted = [line for line in previous.read_text().splitlines() if line.startswith("list.server=")] if previous.exists() else []

    _stop_managed_office()
    _current_identity = None
    config.write_text("\n".join([f"list.a3={module}", "list.a1=", *trusted]) + "\n")
    env = {**os.environ, "PJE_OFFICE_USER_HOME": str(home)}
    with (base / f"startup-{code}.log").open("ab") as log:
        process = subprocess.Popen(
            ["/usr/local/bin/pjeoffice-pro"], env=env,
            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        )
    PID_FILE.write_text(str(process.pid))
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"PJeOffice de {collector.label} não iniciou; confira startup-{code}.log.")
        try:
            with socket.create_connection(("127.0.0.1", 8800), timeout=.5):
                _current_identity = code
                return
        except OSError:
            time.sleep(.2)
    process.terminate()
    raise RuntimeError(f"PJeOffice de {collector.label} não ficou pronto em 20 segundos.")
