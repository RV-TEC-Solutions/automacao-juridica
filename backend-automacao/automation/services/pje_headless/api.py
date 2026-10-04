"""Consumo das APIs REST Internas do PJe (Rota B).

Permite consultar dados estruturados diretamente em JSON:
- Expedientes (Painel do Advogado: pendentes de ciência e de resposta);
- Quadro de Avisos e Comunicados;
- Consulta a autos com Segredo de Justiça (RBAC autenticado do advogado);
- Download de documentos e peças processuais em PDF.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .session import PJeHttpSession

logger = logging.getLogger("pje.headless.api")


@dataclass(frozen=True)
class ExpedienteDTO:
    """Objeto de transferência de dados representando um expediente extraído via API."""
    id_expediente: str
    numero_processo: str
    tipo_comunicacao: str
    destinatario: str
    data_disponibilizacao: str
    prazo_dias: int | None
    data_limite: str | None
    orgao_julgador: str
    teor: str
    documento_id: str | None = None
    segredo_justica: bool = False


class PJeApiClient:
    """Cliente para as rotas REST internas dos tribunais PJe."""

    def __init__(self, session: PJeHttpSession):
        self.session = session

    def obter_expedientes_painel(
        self,
        endpoint_expedientes: str = "/pje/api/v1/painel-advogado/expedientes",
        pagina: int = 0,
        tamanho_pagina: int = 100,
    ) -> list[ExpedienteDTO]:
        """Consulta intimações e expedientes pendentes diretamente em JSON."""
        logger.info("Consultando expedientes via API REST: %s", endpoint_expedientes)

        params = {
            "pagina": pagina,
            "tamanho": tamanho_pagina,
            "tipo": "pendentes",
        }

        resp = self.session.get(endpoint_expedientes, params=params)
        if resp.status_code >= 400:
            logger.error("Erro ao consultar expedientes via API (%d): %s", resp.status_code, resp.text[:200])
            return []

        try:
            dados = resp.json()
        except Exception:
            logger.error("Resposta de expedientes não retornou JSON válido.")
            return []

        # PJe pode devolver uma lista pura ou um wrapper paginado {'content': [...]}
        itens = dados.get("content", dados) if isinstance(dados, dict) else dados
        if not isinstance(itens, list):
            itens = []

        resultado: list[ExpedienteDTO] = []
        for item in itens:
            dto = ExpedienteDTO(
                id_expediente=str(item.get("id") or item.get("idAviso") or ""),
                numero_processo=item.get("numeroProcesso") or item.get("processo", {}).get("numero", ""),
                tipo_comunicacao=item.get("tipoComunicacao") or item.get("tipo", "Intimação"),
                destinatario=item.get("destinatario") or item.get("nomeParte", ""),
                data_disponibilizacao=item.get("dataDisponibilizacao") or item.get("dataCriacao", ""),
                prazo_dias=item.get("prazoDias"),
                data_limite=item.get("dataLimite") or item.get("dataFinal", ""),
                orgao_julgador=item.get("orgaoJulgador") or item.get("orgao", ""),
                teor=item.get("teor") or item.get("textoCertidao", ""),
                documento_id=str(item.get("idDocumento") or "") or None,
                segredo_justica=bool(item.get("segredoJustica", False)),
            )
            resultado.append(dto)

        logger.info("Coletados %d expedientes via API REST.", len(resultado))
        return resultado

    def obter_avisos(
        self,
        endpoint_avisos: str = "/pje/api/v1/quadro-avisos",
    ) -> list[dict[str, Any]]:
        """Consulta avisos institucionais do tribunal."""
        logger.info("Consultando avisos do tribunal via API: %s", endpoint_avisos)
        resp = self.session.get(endpoint_avisos)
        if resp.status_code >= 400:
            return []
        try:
            dados = resp.json()
            return dados if isinstance(dados, list) else dados.get("content", [])
        except Exception:
            return []

    def obter_detalhes_processo(
        self,
        id_processo: str | int,
        endpoint_template: str = "/pje/api/v1/processos/{id}",
    ) -> dict[str, Any] | None:
        """Acessa o espelho e documentos de autos (incluindo Segredo de Justiça para o patrono)."""
        url = endpoint_template.format(id=id_processo)
        resp = self.session.get(url)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Falha ao obter detalhes do processo %s: status %d", id_processo, resp.status_code)
        return None

    def baixar_documento_pdf(
        self,
        id_documento: str | int,
        endpoint_template: str = "/pje/api/v1/documentos/{id}/conteudo",
    ) -> bytes | None:
        """Faz o download do binário de qualquer documento ou anexo processual."""
        url = endpoint_template.format(id=id_documento)
        resp = self.session.get(url)
        if resp.status_code == 200:
            return resp.content
        logger.warning("Falha ao baixar documento %s: status %d", id_documento, resp.status_code)
        return None
