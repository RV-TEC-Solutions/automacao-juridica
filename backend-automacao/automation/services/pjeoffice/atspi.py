import os
import shutil
import subprocess
import sys
import time

try:
    import pyatspi
except ImportError:
    pyatspi = None

NOMES_APLICACAO = (
    "pjeoffice pro - 2.5.16u",
    "pjeoffice",
    "pjeoffice pro",
    "pjeoffice-pro",
)
NOME_JANELA_PIN = ("informe a senha")
NOMES_BOTAO_CONFIRMAR = ("ok", "confirmar", "prosseguir", "entrar")
KEYSYM_RETURN = 0xFF0D


def percorrer(no):
    yield no

    for filho in no:
        yield from percorrer(filho)


def esta_visivel_e_editavel(no):
    if not pyatspi:
        return False
    estado = no.getState()

    return (
        estado.contains(pyatspi.STATE_SHOWING)
        and estado.contains(pyatspi.STATE_VISIBLE)
        and estado.contains(pyatspi.STATE_EDITABLE)
        and estado.contains(pyatspi.STATE_SENSITIVE)
    )


def localizar_aplicacao():
    if not pyatspi:
        raise RuntimeError("pyatspi não está instalado neste ambiente Python.")

    desktop = pyatspi.Registry.getDesktop(0)

    for aplicacao in desktop:
        nome = (aplicacao.name or "").lower()

        if any(alvo in nome for alvo in NOMES_APLICACAO):
            return aplicacao

    nomes = [
        aplicacao.name
        for aplicacao in desktop
        if aplicacao.name
    ]

    raise RuntimeError(
        "PJEOffice não foi encontrado no AT-SPI. "
        f"Aplicações visíveis: {nomes}"
    )


def localizar_janela(aplicacao):
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    janelas = [
        no
        for no in percorrer(aplicacao)
        if no.getRole() == pyatspi.ROLE_DIALOG
        and (no.name or "").strip().lower() == NOME_JANELA_PIN
        and no.getState().contains(pyatspi.STATE_SHOWING)
        and no.getState().contains(pyatspi.STATE_VISIBLE)
    ]

    if len(janelas) != 1:
        detalhes = [
            f"{janela.getRoleName()}: {janela.name!r}"
            for janela in janelas
        ]

        raise RuntimeError(
            f"Janela do PIN ausente: {detalhes}"
        )

    return janelas[0]


def localizar_campo_pin(janela):
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    campos = [
        no
        for no in percorrer(janela)
        if no.getRole() == pyatspi.ROLE_PASSWORD_TEXT
        and esta_visivel_e_editavel(no)
    ]

    if len(campos) != 1:
        detalhes = [
            f"{campo.getRoleName()}: {campo.name!r}"
            for campo in campos
        ]

        raise RuntimeError(
            f"Campo PIN ambíguo ou ausente: {detalhes}"
        )

    return campos[0]


def localizar_botao_confirmar(janela):
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    botoes = [
        no
        for no in percorrer(janela)
        if no.getRole() == pyatspi.ROLE_PUSH_BUTTON
        and (no.name or "").strip().lower() in NOMES_BOTAO_CONFIRMAR
        and no.getState().contains(pyatspi.STATE_SHOWING)
        and no.getState().contains(pyatspi.STATE_SENSITIVE)
    ]

    if len(botoes) != 1:
        detalhes = [
            f"{botao.getRoleName()}: {botao.name!r}"
            for botao in botoes
        ]

        raise RuntimeError(
            f"Botão OK ambíguo ou ausente: {detalhes}"
        )

    return botoes[0]


def acionar(botao):
    acoes = botao.queryAction()

    if acoes.nActions == 0:
        raise RuntimeError(
            "O botão OK não expõe nenhuma ação AT-SPI."
        )

    if not acoes.doAction(0):
        raise RuntimeError(
            "O AT-SPI recusou a ação do botão OK."
        )


def confirmar_com_enter(campo_pin):
    """Confirma o PIN sem depender do rótulo do botão do PJeOffice."""
    if not pyatspi:
        raise RuntimeError("pyatspi não está disponível.")

    componente = campo_pin.queryComponent()

    if not componente.grabFocus():
        raise RuntimeError(
            "Não foi possível focar o campo do PIN para confirmá-lo com Enter."
        )

    pyatspi.Registry.generateKeyboardEvent(
        KEYSYM_RETURN,
        None,
        pyatspi.KEY_SYM,
    )


def preencher_pin_x11(pin: str) -> bool:
    """Preenche a senha no diálogo do PJeOffice diretamente via eventos de janela X11 (wmctrl/xdotool)."""
    if not (shutil.which("xdotool") or shutil.which("wmctrl")) or not os.environ.get("DISPLAY"):
        return False

    termos_busca = [
        "informe a senha",
        "informe a sua senha",
        "informe o pin",
        "pjeoffice",
        "senha",
        "pin",
    ]

    candidatos = []

    # 1. Busca via wmctrl se disponível
    if shutil.which("wmctrl"):
        res = subprocess.run(["wmctrl", "-l"], capture_output=True, text=True, check=False)
        for linha in res.stdout.strip().splitlines():
            partes = linha.split(None, 3)
            if len(partes) >= 4:
                hex_id, _, _, titulo = partes
                titulo_lower = titulo.lower()
                if any(ign in titulo_lower for ign in ("chromium", "chrome", "firefox", "bash", "terminal")):
                    continue
                if any(termo in titulo_lower for termo in termos_busca):
                    try:
                        int_wid = str(int(hex_id, 16))
                        candidatos.append((int_wid, titulo))
                    except ValueError:
                        pass

    # 2. Busca complementar via xdotool search
    if shutil.which("xdotool"):
        for termo in ["Informe a senha", "senha", "pjeoffice", "PIN"]:
            res = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", termo],
                capture_output=True,
                text=True,
                check=False,
            )
            for wid in res.stdout.strip().splitlines():
                wid = wid.strip()
                if wid and not any(c[0] == wid for c in candidatos):
                    name_res = subprocess.run(
                        ["xdotool", "getwindowname", wid],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    win_name = name_res.stdout.strip().lower()
                    if any(ign in win_name for ign in ("chromium", "chrome", "firefox", "bash", "terminal")):
                        continue
                    candidatos.append((wid, win_name))

    for wid, win_title in candidatos:
        # Ativa e foca a janela
        subprocess.run(["xdotool", "windowactivate", "--sync", wid], capture_output=True, check=False)
        subprocess.run(["xdotool", "windowfocus", "--sync", wid], capture_output=True, check=False)
        time.sleep(0.3)

        # Digita o PIN no campo em foco
        subprocess.run(
            ["xdotool", "type", "--window", wid, "--delay", "50", "--", pin],
            capture_output=True,
            check=False,
        )
        subprocess.run(
            ["xdotool", "type", "--delay", "50", "--", pin],
            capture_output=True,
            check=False,
        )
        time.sleep(0.1)

        # Envia Return para submeter o diálogo modal
        subprocess.run(["xdotool", "key", "--window", wid, "Return"], capture_output=True, check=False)
        subprocess.run(["xdotool", "key", "Return"], capture_output=True, check=False)

        # Aguarda estabilização da submissão
        time.sleep(0.5)
        return True

    return False


def preencher_pin_atspi(pin: str) -> bool:
    """Preenche a senha utilizando a camada de acessibilidade AT-SPI."""
    if not pyatspi:
        return False

    aplicacao = localizar_aplicacao()
    janela = localizar_janela(aplicacao)
    campo_pin = localizar_campo_pin(janela)
    editor = campo_pin.queryEditableText()

    if not editor.setTextContents(pin):
        raise RuntimeError("AT-SPI recusou o preenchimento do PIN.")

    try:
        botao = localizar_botao_confirmar(janela)
    except RuntimeError:
        confirmar_com_enter(campo_pin)
    else:
        acionar(botao)

    return True


def preencher_pin():
    pin = os.environ.get("PJE_CERT_PIN")

    if not pin:
        raise RuntimeError("PJE_CERT_PIN não foi configurado.")

    limite = time.monotonic() + 30
    ultimo_erro = None

    while time.monotonic() < limite:
        # 1. Tenta método nativo X11 (rápido e determinístico no Xvfb do container)
        try:
            if preencher_pin_x11(pin):
                return
        except Exception as erro:
            ultimo_erro = f"X11: {erro}"

        # 2. Tenta método AT-SPI (acessibilidade GNOME / Java ATK)
        try:
            if preencher_pin_atspi(pin):
                return
        except Exception as erro:
            ultimo_erro = f"AT-SPI: {erro}"

        time.sleep(0.5)

    raise RuntimeError(
        "Não foi possível concluir o PIN em 30 segundos. "
        f"Último diagnóstico: {ultimo_erro}"
    )


if __name__ == "__main__":
    try:
        preencher_pin()
    except Exception as erro:
        print(f"erro: {erro}", file=sys.stderr)
        raise SystemExit(2)
