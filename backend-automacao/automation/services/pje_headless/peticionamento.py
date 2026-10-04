"""Motor de Peticionamento Automático Headless para PJe (Rota B).

Executa o fluxo de juntada de petições e documentos sem navegador:
1. Assinatura digital CAdES-BES de cada arquivo PDF com o certificado A1;
2. Upload multipart/form-data para o repositório temporário do PJe;
3. Protocolo eletrônico da manifestação via POST JSON direto no endpoint de juntada.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .crypto import A1CryptoEngine
from .session import PJeHttpSession

logger = logging.getLogger("pje.headless.peticionamento")


@dataclass
class DocumentoPeticionamento:
    """Representação de um documento a ser juntado aos autos."""
    titulo: str
    tipo_documento_id: int
    conteudo_pdf: bytes
    id_upload: str | None = None
    assinatura_cades: bytes | None = None


@dataclass
class ManifestacaoProcessual:
    """Payload estruturado para protocolo de peticionamento no PJe."""
    id_processo: int | str
    tipo_manifestacao: str
    documento_principal: DocumentoPeticionamento
    anexos: list[DocumentoPeticionamento] = field(default_factory=list)
    segredo_justica: bool = False


class PJePeticionamentoClient:
    """Orquestrador do peticionamento eletrônico headless."""

    def __init__(self, session: PJeHttpSession, crypto_engine: A1CryptoEngine | None = None):
        self.session = session
        self.engine = crypto_engine or A1CryptoEngine.from_env()

    def assinar_e_enviar_documento(
        self,
        documento: DocumentoPeticionamento,
        endpoint_upload: str = "/pje/api/v1/documentos/upload",
    ) -> str:
        """Assina o PDF em CAdES-BES e faz o upload multipart/form-data."""
        logger.info("Assinando documento '%s' em CAdES-BES...", documento.titulo)
        documento.assinatura_cades = self.engine.sign_document_cades(documento.conteudo_pdf)

        logger.info("Enviando binário do documento via multipart para: %s", endpoint_upload)
        files = {
            "arquivo": (f"{documento.titulo}.pdf", documento.conteudo_pdf, "application/pdf"),
            "assinatura": (f"{documento.titulo}.p7s", documento.assinatura_cades, "application/pkcs7-signature"),
        }
        data = {
            "descricao": documento.titulo,
            "tipoDocumento": str(documento.tipo_documento_id),
        }

        resp = self.session.post(endpoint_upload, data=data, files=files)
        if resp.status_code >= 400:
            raise RuntimeError(f"Falha ao enviar documento '{documento.titulo}' ({resp.status_code}): {resp.text[:200]}")

        dados_resp = resp.json()
        id_upload = dados_resp.get("idUpload") or dados_resp.get("id") or dados_resp.get("hash")
        if not id_upload:
            raise RuntimeError(f"Endpoint de upload não retornou o identificador do arquivo: {dados_resp}")

        documento.id_upload = str(id_upload)
        logger.info("Upload de '%s' concluído com idUpload=%s", documento.titulo, documento.id_upload)
        return documento.id_upload

    def protocolar_manifestacao(
        self,
        manifestacao: ManifestacaoProcessual,
        endpoint_protocolo: str = "/pje/api/v1/processos/{id}/manifestacoes",
    ) -> dict[str, Any]:
        """Executa o upload dos documentos e protocola a petição nos autos."""
        # 1. Upload do documento principal
        if not manifestacao.documento_principal.id_upload:
            self.assinar_e_enviar_documento(manifestacao.documento_principal)

        # 2. Upload dos anexos
        for anexo in manifestacao.anexos:
            if not anexo.id_upload:
                self.assinar_e_enviar_documento(anexo)

        # 3. Montagem do payload de protocolo
        payload = {
            "idProcesso": manifestacao.id_processo,
            "tipoManifestacao": manifestacao.tipo_manifestacao,
            "documentoPrincipal": {
                "idUpload": manifestacao.documento_principal.id_upload,
                "descricao": manifestacao.documento_principal.titulo,
                "tipoDocumento": manifestacao.documento_principal.tipo_documento_id,
            },
            "anexos": [
                {
                    "idUpload": anexo.id_upload,
                    "descricao": anexo.titulo,
                    "tipoDocumento": anexo.tipo_documento_id,
                }
                for anexo in manifestacao.anexos
            ],
            "segredoJustica": manifestacao.segredo_justica,
        }

        url = endpoint_protocolo.format(id=manifestacao.id_processo)
        logger.info("Enviando protocolo de petição para: %s", url)
        resp = self.session.post(url, json=payload)

        if resp.status_code >= 400:
            raise RuntimeError(f"Erro ao protocolar manifestação ({resp.status_code}): {resp.text[:300]}")

        dados_retorno = resp.json()
        logger.info("Petição protocolada com sucesso nos autos %s!", manifestacao.id_processo)
        return dados_retorno
