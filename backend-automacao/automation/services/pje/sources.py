"""Perfis declarativos das fontes PJe suportadas."""

from dataclasses import dataclass


TRF5_PORTAL_URL = "https://www.trf5.jus.br/index.php/pje#container"


@dataclass(frozen=True)
class PJeSourceProfile:
    code: str
    url: str
    tribunal: str
    system: str
    collector: str
    reconcile_missing: bool
    portal_button_name: str | None = None
    portal_destination_host: str | None = None


PJE_SOURCE_ORDER = (
    "pje-tjrn", "pje2g-tjrn", "trt21", "trt21-2g",
    "trf5-2g-tru", "varas-justica-comum", "jef-5-regiao",
    "trs-5-regiao", "tru-5-regiao",
)

SOURCE_PROFILES = {
    "pje-tjrn": PJeSourceProfile(
        code="pje-tjrn",
        url="https://pje1g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam",
        tribunal="TJRN", system="PJe 1º Grau", collector="tjrn", reconcile_missing=True,
    ),
    "pje2g-tjrn": PJeSourceProfile(
        code="pje2g-tjrn",
        url="https://pje2g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam",
        tribunal="TJRN", system="PJe 2º Grau", collector="tjrn", reconcile_missing=True,
    ),
    "trt21": PJeSourceProfile(
        code="trt21",
        url="https://pje.trt21.jus.br/primeirograu/login.seam",
        tribunal="TRT21", system="PJe 1º Grau", collector="trt21", reconcile_missing=False,
    ),
    "trt21-2g": PJeSourceProfile(
        code="trt21-2g",
        url="https://pje.trt21.jus.br/segundograu/login.seam",
        tribunal="TRT21", system="PJe 2º Grau", collector="trt21", reconcile_missing=False,
    ),
    "trf5-2g-tru": PJeSourceProfile(
        code="trf5-2g-tru",
        url=TRF5_PORTAL_URL,
        tribunal="TRF5", system="PJe 2º Grau / TRU", collector="tjrn", reconcile_missing=True,
        portal_button_name="TRF 5ª Região", portal_destination_host="pjett.trf5.jus.br",
    ),
    "varas-justica-comum": PJeSourceProfile(
        code="varas-justica-comum",
        url=TRF5_PORTAL_URL,
        tribunal="TRF5", system="PJe 1º Grau — Varas Federais", collector="tjrn", reconcile_missing=True,
        portal_button_name="Varas da Justiça Comum", portal_destination_host="pje1g.trf5.jus.br",
    ),
    "jef-5-regiao": PJeSourceProfile(
        code="jef-5-regiao",
        url=TRF5_PORTAL_URL,
        tribunal="TRF5", system="PJe 1º Grau — JEF", collector="tjrn", reconcile_missing=True,
        portal_button_name="JEF 5ª Região", portal_destination_host="pje1g.trf5.jus.br",
    ),
    "trs-5-regiao": PJeSourceProfile(
        code="trs-5-regiao",
        url=TRF5_PORTAL_URL,
        tribunal="TRF5", system="PJe — Turmas Recursais", collector="tjrn", reconcile_missing=True,
        portal_button_name="TR's 5ª Região", portal_destination_host="pje2g.trf5.jus.br",
    ),
    "tru-5-regiao": PJeSourceProfile(
        code="tru-5-regiao",
        url=TRF5_PORTAL_URL,
        tribunal="TRF5", system="PJe 2º Grau / TRU — perfil alternativo", collector="tjrn", reconcile_missing=True,
        portal_button_name="TRU 5ª Região", portal_destination_host="pjett.trf5.jus.br",
    ),
}


def get_source_profile(code):
    try:
        return SOURCE_PROFILES[code]
    except KeyError:
        raise RuntimeError(f"Fonte PJe não suportada: {code}") from None
