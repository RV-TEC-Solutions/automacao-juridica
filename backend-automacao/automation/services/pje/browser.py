import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from django.conf import settings

import pyotp
from dotenv import load_dotenv
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

PYTHON_ATSPI = "/usr/bin/python3"

PJE_URLS = {
    "pje-tjrn": "https://pje1g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam",
    "pje2g-tjrn": "https://pje2g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam",
}

CREDENCIAIS = Path.home() / ".config/pje-automacao/.env"

PASTA_RESPOSTAS = settings.BASE_DIR / "respostas_expedientes"

load_dotenv(CREDENCIAIS)

# Essa função gera o mesmo código que apareceria no Google Authenticator
def gerar_codigo_totp(segredo):
    autenticador = pyotp.TOTP(segredo)

    segundos_restantes = (
        autenticador.interval - (time.time() % autenticador.interval)
    )

    if segundos_restantes < 5:
        time.sleep(segundos_restantes)

    return autenticador.now()


def localizar_arvore_pendencias(pagina):
    """Retorna a árvore irmã da opção ``Pendentes de ciência ou de resposta``."""
    texto_aba = "Pendentes de ciência ou de resposta"
    painel = pagina.locator("#divResultadoMenuContexto")
    menu_contexto = painel.locator(
        '[id="formAbaExpediente:divMenuContexto"]'
    )
    aba_pendencias = menu_contexto.locator(
        "div.containerDocumentos.nivel1"
    ).get_by_text(
        texto_aba, exact=True
    ).locator("xpath=ancestor::a[1]")
    linha_n1 = aba_pendencias.locator(
        'xpath=ancestor::div[parent::div['
        '@id="formAbaExpediente:divMenuContexto"]][1]'
    )
    linha_n2 = linha_n1.locator("xpath=following-sibling::div[1]")
    arvore = linha_n2.locator(
        "div.rich-tree.nivel2.treeExpedientes"
    )

    if painel.count() != 1 or menu_contexto.count() != 1:
        raise RuntimeError(
            "O painel ou o contêiner comum não foi encontrado "
            "de forma única."
        )
    if linha_n1.count() != 1 or aba_pendencias.count() != 1:
        raise RuntimeError(
            "A opção principal não foi encontrada "
            "de forma única."
        )

    aba_pendencias.click()
    arvore.wait_for(state="visible")

    if linha_n2.count() != 1 or arvore.count() != 1:
        raise RuntimeError(
            "A árvore irmã da opção principal não foi encontrada "
            "de forma única."
        )

    return arvore


def localizar_opcao_filha(pagina, texto_opcao):
    """Retorna o link clicável de uma opção dentro da árvore de pendências."""
    arvore = localizar_arvore_pendencias(pagina)
    texto = arvore.get_by_text(texto_opcao, exact=True)
    link = texto.locator("xpath=ancestor::a[1]")

    if link.count() != 1:
        raise RuntimeError(
            f"A opção filha {texto_opcao!r} não foi encontrada de forma única."
        )

    return link


def localizar_abas_filhas(pagina):
    """Retorna os links das opções de primeiro nível da árvore de pendências."""
    arvore = localizar_arvore_pendencias(pagina)
    opcoes = arvore.locator(
        ":scope > div > table.rich-tree-node "
        "> tbody > tr > td.rich-tree-node-text.treeNodeItem > a"
    )

    if opcoes.count() == 0:
        raise RuntimeError(
            "Nenhuma opção de primeiro nível foi encontrada na árvore."
        )

    return opcoes


def esperar_view_expedientes(pagina):
    """Dá tempo para a view carregada por AJAX terminar de renderizar."""
    try:
        pagina.wait_for_load_state(
            "networkidle",
            timeout=5000
        )
    except PlaywrightTimeoutError:
        # O PJe pode manter requisições abertas; nesse caso, seguimos
        # após uma pequena margem para a renderização do DOM.
        pass

    pagina.wait_for_timeout(1000)


def salvar_html_renderizado(pagina, pasta_respostas, indice):
    """Salva o DOM renderizado após clicar em uma aba-filha."""
    pasta_respostas.mkdir(parents=True, exist_ok=True)

    arquivo = pasta_respostas / (
        f"expedientes_{indice:03d}.html"
    )

    arquivo.write_text(
        pagina.content(),
        encoding="utf-8"
    )

    return arquivo


def coletar_expedientes(pagina, source_code):
    """Clica em cada aba-filha e salva o HTML renderizado."""
    abas_filhas = localizar_abas_filhas(pagina)
    quantidade = abas_filhas.count()
    identificador_execucao = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )
    pasta_respostas = PASTA_RESPOSTAS / source_code / identificador_execucao

    print(f"Arquivos desta execução: {pasta_respostas}")
    arquivos = []

    for indice in range(quantidade):
        aba_filha = abas_filhas.nth(indice)

        print(
            f"Processando aba filha {indice + 1}/{quantidade}..."
        )

        aba_filha.click()
        esperar_view_expedientes(pagina)

        arquivo = salvar_html_renderizado(
            pagina,
            pasta_respostas,
            indice + 1
        )
        arquivos.append(arquivo)
        print(f"HTML salvo em: {arquivo}")

    return arquivos

def preencher_pin_pjeoffice_atspi():
    pin = os.environ.get("PJE_CERT_PIN")

    if not pin:
        raise RuntimeError("PJE_CERT_PIN não foi configurado.")

    pasta_projeto = Path(__file__).resolve().parent

    helper = (
        settings.BASE_DIR
        / "automation"
        / "services"
        / "pjeoffice"
        / "atspi.py"
    )
    ambiente = os.environ.copy()
    ambiente["PJE_CERT_PIN"] = pin

    resultado = subprocess.run(
        [
            PYTHON_ATSPI,
            str(helper),
        ],
        env=ambiente,
        capture_output=True,
        text=True,
        timeout=40,
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            "O helper AT-SPI não concluiu o PIN. "
            f"Diagnóstico: {resultado.stderr.strip()}"
        )

def obter_url_pje(source_code):
    try:
        return PJE_URLS[source_code]
    except KeyError:
        raise RuntimeError(f"Fonte PJe não suportada: {source_code}") from None


def abrir_pje(source_code):
    pje_url = obter_url_pje(source_code)
    with sync_playwright() as playwright:
        navegador = playwright.chromium.launch(
            headless=False
        )

        contexto = navegador.new_context()

        contexto.grant_permissions(
            ["local-network-access"],
            origin="https://sso.cloud.pje.jus.br",
        )

        pagina = contexto.new_page()

        pagina.goto(
            pje_url,
            wait_until="domcontentloaded"
        )

        print("O navegador foi aberto.")
        print("Aguardando o login por certificado digital.")
        print("O PIN será preenchido na janela do PJeOffice.")

        segredo_totp = os.environ.get("PJE_TOTP_SECRET")
        if not segredo_totp:
            raise RuntimeError("PJE_TOTP_SECRET não foi configurado.")

        pagina.get_by_text(
            "CERTIFICADO DIGITAL",
            exact=True
        ).click()

        preencher_pin_pjeoffice_atspi()

        campo_otp = pagina.get_by_label(
            "Entre no seu aplicativo de autenticação e digite abaixo o código apresentado:",
            exact=True
        )

        campo_otp.wait_for(
            state="visible"
        )

        codigo_otp = gerar_codigo_totp(
            segredo_totp
        )

        campo_otp.fill(codigo_otp)

        pagina.get_by_text(
            "Validar",
            exact=True
        ).click()

        try:
            pagina.locator(
                "#divResultadoMenuContexto"
            ).wait_for(state="visible", timeout=15000)
        except PlaywrightTimeoutError:
            if pagina.get_by_text("Código inválido", exact=True).count():
                raise RuntimeError(
                    "O PJe rejeitou o código TOTP. "
                    "Verifique o horário do computador e o segredo configurado."
                )

            raise RuntimeError(
                f"Login não confirmou. URL atual: {pagina.url}"
            )

        arquivos = coletar_expedientes(pagina, source_code)

        navegador.close()
        return arquivos

if __name__ == "__main__":
    arquivos = abrir_pje("pje-tjrn")
