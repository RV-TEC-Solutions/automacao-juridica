"""Verificação local da presença de token A3 via PC/SC."""

import os
import subprocess


TOKEN_AUSENTE_MENSAGEM = (
    "Token físico não detectado. Conecte o token ao computador e tente novamente."
)
TOKEN_INDISPONIVEL_MENSAGEM = (
    "Não foi possível verificar o token físico. Confirme se o PJeOffice e o "
    "serviço PC/SC estão em execução e tente novamente."
)


class TokenFisicoError(RuntimeError):
    """Erro conhecido durante a pré-verificação do certificado A3."""


def require_hardware_token() -> bool:
    """Indica se a presença física do smartcard A3 é exigida para operar.
    
    Por padrão, se não configurado ou definido como false, permite execução
    em ambientes containerizados/nuvem usando certificados em arquivo ou PJeOffice.
    """
    val = os.environ.get("PJE_REQUIRE_HARDWARE_TOKEN", "").strip().lower()
    return val in ("1", "true", "yes", "sim", "s")


def validar_token_fisico():
    """Garante que o PC/SC enxerga um cartão inserido antes da coleta.

    ``pcsc_scan`` é fornecido pelo pacote usado pelo PJeOffice e consulta o
    leitor sem abrir a janela de autenticação nem enviar o PIN.
    """
    if not require_hardware_token():
        return

    try:
        resultado = subprocess.run(
            ["pcsc_scan", "-c", "-t", "1"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise TokenFisicoError(TOKEN_INDISPONIVEL_MENSAGEM) from error

    diagnostico = f"{resultado.stdout}\n{resultado.stderr}".lower()
    if "card state: card inserted" in diagnostico:
        return
    if "no reader found" in diagnostico or "card state: card removed" in diagnostico:
        raise TokenFisicoError(TOKEN_AUSENTE_MENSAGEM)
    raise TokenFisicoError(TOKEN_INDISPONIVEL_MENSAGEM)
