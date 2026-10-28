"""Identidades das coletas; nunca reutiliza credenciais entre titulares."""

import os
from contextlib import contextmanager
from dataclasses import dataclass

from django.conf import settings
from dotenv import dotenv_values


class CredentialError(RuntimeError):
    """Suspende a identidade no ciclo, antes de outra tentativa de autenticação."""


def credential_values():
    """Única origem dos segredos; nunca mistura arquivo e ambiente herdado."""
    return dotenv_values(settings.PJE_CREDENTIALS_FILE, interpolate=False)


@dataclass(frozen=True)
class Collector:
    code: str
    label: str
    serial: str
    module: str


COLLECTORS = {
    "murilo": Collector("murilo", "MURILO", "2108950019F94896", "/usr/lib/libaetpkss.so.3"),
    "cristiano": Collector("cristiano", "CRISTIANO", "027ef6e7", "/usr/lib/libeToken.so"),
}


def get_collector(code):
    try:
        return COLLECTORS[code]
    except KeyError:
        raise ValueError(f"Titular de coleta desconhecido: {code}.") from None


def collector_order():
    codes = tuple(settings.PJE_COLLECTORS)
    if not codes or len(codes) != len(set(codes)):
        raise ValueError("PJE_COLLECTORS deve conter titulares distintos, em ordem.")
    for code in codes:
        get_collector(code)
    return codes


def credentials_for(code):
    get_collector(code)
    configured = credential_values()
    values = {}
    for key in ("PJE_CERT_PIN", "PJE_TOTP_SECRET"):
        prefixed = f"PJE_{code.upper()}_{key.removeprefix('PJE_')}"
        value = configured.get(prefixed)
        if not value and code == "murilo":
            value = configured.get(key)
        if not value:
            raise CredentialError(f"Configure {prefixed} no .env da raiz do projeto para a coleta de {get_collector(code).label}.")
        values[key] = value
    return values


@contextmanager
def collector_credentials(code):
    """O worker é sequencial; restaura o ambiente mesmo se a coleta falhar."""
    values = credentials_for(code)
    values["PJE_CURRENT_COLLECTOR"] = code
    previous = {key: os.environ.get(key) for key in values}
    try:
        os.environ.update(values)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def collector_status_payload():
    """Somente presença de credenciais e evidências das execuções, sem segredos."""
    from .models import AutomationRun

    configured = credential_values()
    enabled = collector_order()
    result = []
    for code, collector in COLLECTORS.items():
        prefix = f"PJE_{code.upper()}_"
        pin = bool(configured.get(prefix + "CERT_PIN") or (code == "murilo" and configured.get("PJE_CERT_PIN")))
        totp = bool(configured.get(prefix + "TOTP_SECRET") or (code == "murilo" and configured.get("PJE_TOTP_SECRET")))
        runs = AutomationRun.objects.filter(collector=code, descartada_em__isnull=True).exclude(source__code="djen")
        latest = runs.first()
        success = runs.filter(status="success").order_by("-finalizada_em").first()
        state = "disabled" if code not in enabled else "unconfigured" if not (pin and totp) else "idle"
        if state == "idle" and latest:
            state = "blocked" if latest.credential_failure else latest.status
        result.append({
            "code": code, "label": f"Dr. {collector.label.title()}",
            "enabled": code in enabled, "pin_configured": pin, "totp_configured": totp,
            "state": state, "last_success_at": success.finalizada_em if success else None,
            "error": latest.mensagem_erro if latest and latest.status == "failed" else "",
        })
    return result
