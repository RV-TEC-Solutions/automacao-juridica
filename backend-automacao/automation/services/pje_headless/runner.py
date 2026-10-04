"""Runner de Coleta Headless para PJe (Rota B).

Executa o fluxo de coleta diretamente por chamadas de rede sem abrir
Chromium ou Playwright, autenticando via A1 e gravando os expedientes
coletados no banco de dados através da persistência existente.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from automation.services.pje.persistence import salvar_expediente
from .api import PJeApiClient
from .auth import PJeAuthClient
from .crypto import A1CryptoEngine
from .session import PJeHttpSession

logger = logging.getLogger("pje.headless.runner")


@dataclass(frozen=True)
class PJeHeadlessEndpointConfig:
    """Configuração dos endpoints de API por tribunal."""
    base_url: str
    endpoint_desafio: str
    endpoint_valida: str
    endpoint_totp: str | None
    endpoint_expedientes: str
    endpoint_avisos: str


# Mapeamento declarativo de endpoints para a Rota B
TRIBUNAL_HEADLESS_CONFIGS: dict[str, PJeHeadlessEndpointConfig] = {
    "pje-tjrn": PJeHeadlessEndpointConfig(
        base_url="https://pje1g.tjrn.jus.br",
        endpoint_desafio="/pje/login/cert",
        endpoint_valida="/pje/login/cert/valida",
        endpoint_totp="/pje/login/totp/valida",
        endpoint_expedientes="/pje/api/v1/painel-advogado/expedientes",
        endpoint_avisos="/pje/api/v1/quadro-avisos",
    ),
    "pje2g-tjrn": PJeHeadlessEndpointConfig(
        base_url="https://pje2g.tjrn.jus.br",
        endpoint_desafio="/pje/login/cert",
        endpoint_valida="/pje/login/cert/valida",
        endpoint_totp="/pje/login/totp/valida",
        endpoint_expedientes="/pje/api/v1/painel-advogado/expedientes",
        endpoint_avisos="/pje/api/v1/quadro-avisos",
    ),
    "trt21": PJeHeadlessEndpointConfig(
        base_url="https://pje.trt21.jus.br",
        endpoint_desafio="/primeirograu/login/cert",
        endpoint_valida="/primeirograu/login/cert/valida",
        endpoint_totp="/primeirograu/login/totp/valida",
        endpoint_expedientes="/primeirograu/api/v1/painel-advogado/expedientes",
        endpoint_avisos="/primeirograu/api/v1/quadro-avisos",
    ),
    "trt21-2g": PJeHeadlessEndpointConfig(
        base_url="https://pje.trt21.jus.br",
        endpoint_desafio="/segundograu/login/cert",
        endpoint_valida="/segundograu/login/cert/valida",
        endpoint_totp="/segundograu/login/totp/valida",
        endpoint_expedientes="/segundograu/api/v1/painel-advogado/expedientes",
        endpoint_avisos="/segundograu/api/v1/quadro-avisos",
    ),
}


class PJeHeadlessRunner:
    """Executor de coletas PJe 100% sem navegador."""

    def __init__(self, source_code: str, crypto_engine: A1CryptoEngine | None = None):
        self.source_code = source_code
        self.config = TRIBUNAL_HEADLESS_CONFIGS.get(source_code)
        if not self.config:
            # Fallback com configuração padrão derivada
            self.config = PJeHeadlessEndpointConfig(
                base_url="https://pje1g.tjrn.jus.br",
                endpoint_desafio="/pje/login/cert",
                endpoint_valida="/pje/login/cert/valida",
                endpoint_totp="/pje/login/totp/valida",
                endpoint_expedientes="/pje/api/v1/painel-advogado/expedientes",
                endpoint_avisos="/pje/api/v1/quadro-avisos",
            )
        self.engine = crypto_engine or A1CryptoEngine.from_env()

    def executar_coleta(self, source, run=None) -> list[Any]:
        """Executa a coleta headless para a fonte informada."""
        logger.info("Iniciando coleta headless PJe (Rota B) para %s", self.source_code)
        now = timezone.now()

        with PJeHttpSession(base_url=self.config.base_url) as session:
            auth_client = PJeAuthClient(session=session, crypto_engine=self.engine)
            auth_client.autenticar_fluxo_completo(
                endpoint_desafio=self.config.endpoint_desafio,
                endpoint_valida=self.config.endpoint_valida,
                endpoint_totp=self.config.endpoint_totp,
            )

            api_client = PJeApiClient(session=session)
            expedientes_dto = api_client.obter_expedientes_painel(
                endpoint_expedientes=self.config.endpoint_expedientes
            )

            expedientes_salvos = []
            for dto in expedientes_dto:
                dados_dict = {
                    "identificador_pje": dto.id_expediente,
                    "numero_processo": dto.numero_processo,
                    "tribunal": source.tribunal,
                    "classe": "",
                    "assunto": "",
                    "partes_texto": "",
                    "unidade_judiciaria": dto.orgao_julgador,
                    "tipo_pendencia": "Ciência",
                    "acao_pje": "Tomar Ciência",
                    "caixa": "Pendentes de ciência ou de resposta",
                    "destinatario": dto.destinatario,
                    "tipo_documento": dto.tipo_comunicacao,
                    "meio_comunicacao": "Eletrônico",
                    "data_expedicao": dto.data_disponibilizacao or now,
                    "prazo_texto": f"{dto.prazo_dias} dias" if dto.prazo_dias else "",
                    "status_prazo_fatal": "Aberto",
                    "prazo_fatal": dto.data_limite or None,
                    "ciencia_texto": dto.teor,
                }
                exp_salvo = salvar_expediente(dados_dict, source=source, run=run, seen_at=now)
                expedientes_salvos.append(exp_salvo)

            logger.info("Coleta headless concluída. %d expedientes salvos.", len(expedientes_salvos))
            return expedientes_salvos
