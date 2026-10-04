"""Módulo de automação PJe Headless Criptográfica (Rota B).

Elimina o uso de navegadores para autenticação, extração de dados e
peticionamento através da emulação nativa do protocolo do tribunal.
"""

from .api import ExpedienteDTO, PJeApiClient
from .auth import PJeAuthClient, PJeAuthError
from .crypto import A1CryptoEngine, A1CryptoError, CertificateInfo
from .peticionamento import DocumentoPeticionamento, ManifestacaoProcessual, PJePeticionamentoClient
from .runner import PJeHeadlessRunner
from .session import PJeHttpSession

__all__ = [
    "A1CryptoEngine",
    "A1CryptoError",
    "CertificateInfo",
    "PJeHttpSession",
    "PJeAuthClient",
    "PJeAuthError",
    "PJeApiClient",
    "ExpedienteDTO",
    "PJePeticionamentoClient",
    "DocumentoPeticionamento",
    "ManifestacaoProcessual",
    "PJeHeadlessRunner",
]
