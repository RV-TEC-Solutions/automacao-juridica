"""Identidades das coletas; nunca reutiliza credenciais entre titulares."""

import os
from contextlib import contextmanager
from dataclasses import dataclass

from django.conf import settings


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
    values = {}
    for key in ("PJE_CERT_PIN", "PJE_TOTP_SECRET"):
        prefixed = f"PJE_{code.upper()}_{key.removeprefix('PJE_')}"
        value = os.environ.get(prefixed)
        if not value and code == "murilo":
            value = os.environ.get(key)
        if not value:
            raise RuntimeError(f"Configure {prefixed} para a coleta de {get_collector(code).label}.")
        values[key] = value
    return values


@contextmanager
def collector_credentials(code):
    """O worker é sequencial; restaura o ambiente mesmo se a coleta falhar."""
    values = credentials_for(code)
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
