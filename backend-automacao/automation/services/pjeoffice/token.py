"""Módulo de compatibilidade retroativa para token físico."""
from .physical_token import (
    TOKEN_AUSENTE_MENSAGEM,
    TOKEN_INDISPONIVEL_MENSAGEM,
    TokenFisicoError,
    require_hardware_token,
    validar_token_fisico,
)

__all__ = [
    "TOKEN_AUSENTE_MENSAGEM",
    "TOKEN_INDISPONIVEL_MENSAGEM",
    "TokenFisicoError",
    "require_hardware_token",
    "validar_token_fisico",
]
