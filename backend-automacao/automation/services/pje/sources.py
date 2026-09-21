"""Perfis declarativos das fontes PJe suportadas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PJeSourceProfile:
    code: str
    url: str
    tribunal: str
    system: str
    collector: str
    reconcile_missing: bool


PJE_SOURCE_ORDER = ("pje-tjrn", "pje2g-tjrn", "trt21", "trt21-2g")

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
        url="https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?response_type=code&client_id=pje-trf5-3g&redirect_uri=https%3A%2F%2Fpjett.trf5.jus.br%2Fpje%2Flogin.seam&state=f8733710-07ae-4ffd-9880-3f69a0a66435&login=true&scope=openid",
        tribunal="TRF5", system="PJe 2º Grau", collector="TRF21", reconcile_missing=False,
    ),
    "varas-justica-comum": PJeSourceProfile(
        code="varas-justica-comum",
        url="https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?response_type=code&client_id=pje-trf5-1g&redirect_uri=https%3A%2F%2Fpje1g.trf5.jus.br%2Fpje%2Flogin.seam&state=4f4df14a-0c9a-491d-ae07-91c615e7a217&login=true&scope=openid",
        tribunal="varas-justica-comum", system="PJe 1º Grau", collector="varas-justica-comum", reconcile_missing=False,
    ),
    "jef-5-regiao": PJeSourceProfile(
        code="jef-5-regiao",
        url="https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?response_type=code&client_id=pje-trf5-1g&redirect_uri=https%3A%2F%2Fpje1g.trf5.jus.br%2Fpje%2Flogin.seam&state=57e0956d-e579-45ae-9b30-7e0eab386d42&login=true&scope=openid",
        tribunal="varas-justica-comum", system="PJe 1º Grau e Juizados Especiais Federais", collector="varas-justica-comum", reconcile_missing=False,
    ),
    "trs-5-regiao": PJeSourceProfile(
        code="trs-5-regiao",
        url="https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?response_type=code&client_id=pje-trf5-2g&redirect_uri=https%3A%2F%2Fpje2g.trf5.jus.br%2Fpje%2Flogin.seam&state=93319036-83bb-47d8-a30f-c5f6145d757a&login=true&scope=openid",
        tribunal="trs-5-regiao", system="Turmas recursais", collector="trs-5-regiao", reconcile_missing=False,
    ),
    "tru-5-regiao": PJeSourceProfile(
        code="tru-5-regiao",
        url="https://sso.cloud.pje.jus.br/auth/realms/pje/protocol/openid-connect/auth?response_type=code&client_id=pje-trf5-3g&redirect_uri=https%3A%2F%2Fpjett.trf5.jus.br%2Fpje%2Flogin.seam&state=5ed6bcbf-e5ac-4f15-848a-5b7ffb0864b7&login=true&scope=openid",
        tribunal="tru-5-regiao", system="2° Grau e TRU", collector="tru-5-regiao", reconcile_missing=False,
    ),
}


def get_source_profile(code):
    try:
        return SOURCE_PROFILES[code]
    except KeyError:
        raise RuntimeError(f"Fonte PJe não suportada: {code}") from None

