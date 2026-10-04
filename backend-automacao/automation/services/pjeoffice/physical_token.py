"""Verificação de disponibilidade do certificado digital (A1 em memória ou A3 físico)."""

import os
import subprocess
from pathlib import Path


TOKEN_AUSENTE_MENSAGEM = (
    "Token físico não detectado. Conecte o token ao computador e tente novamente."
)
TOKEN_INDISPONIVEL_MENSAGEM = (
    "Não foi possível verificar o token físico. Confirme se o PJeOffice e o "
    "serviço PC/SC estão em execução e tente novamente."
)


class TokenFisicoError(RuntimeError):
    """Erro conhecido durante a pré-verificação do certificado digital."""


def is_a1_configured() -> bool:
    """Verifica se há configuração ativa para certificado A1."""
    return bool(
        os.environ.get("PJE_CERT_A1_BASE64")
        or os.environ.get("PJE_CERT_A1_PATH")
        or os.environ.get("PJE_AUTH_MODE", "").lower() == "a1"
    )


def validar_token_fisico():
    """Garante que há um certificado digital válido e disponível antes da coleta.

    - Modo A1: Valida o carregamento do par de chaves e a expiração do certificado X.509.
    - Modo A3 (Legado): Consulta o leitor PC/SC local sem abrir a janela de autenticação.
    """
    if is_a1_configured():
        from .crypto import A1CryptoEngine, A1CryptoError
        try:
            engine = A1CryptoEngine.from_env()
            if engine.cert_info.is_expired:
                raise TokenFisicoError(
                    f"Certificado digital A1 expirado em {engine.cert_info.not_valid_after.strftime('%d/%m/%Y')}."
                )
            return
        except A1CryptoError as error:
            raise TokenFisicoError(f"Falha na validação do certificado A1: {error}") from error

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
