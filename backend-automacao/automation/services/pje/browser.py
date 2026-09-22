import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from django.conf import settings
from django.db import connections

import pyotp
from dotenv import load_dotenv
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)

from .sources import get_source_profile
from .trt21 import collect_trt21_expedientes
from .notices import mark_confirmed, persist_notices

PYTHON_ATSPI = "/usr/bin/python3"

CREDENCIAIS = Path.home() / ".config/pje-automacao/.env"

PASTA_RESPOSTAS = settings.BASE_DIR / "respostas_expedientes"
logger = logging.getLogger("automation")

load_dotenv(CREDENCIAIS)


@dataclass(frozen=True)
class LegacyCollection:
    files: list[Path]
    notice_message: str = ""

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


def salvar_diagnostico_pje(pagina, source_code):
    """Salva evidências locais sem substituir a exceção da coleta."""
    pasta = (
        PASTA_RESPOSTAS
        / source_code
        / "diagnostico"
        / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    )
    html = pasta / "page.html"
    screenshot = pasta / "screenshot.png"
    evidencias = {"html": None, "screenshot": None}

    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception(
            "Não foi possível criar a pasta de diagnóstico. fonte=%s pasta=%s",
            source_code,
            pasta,
        )
        return evidencias

    try:
        html.write_text(pagina.content(), encoding="utf-8")
        evidencias["html"] = html
    except Exception:
        logger.exception(
            "Não foi possível salvar o HTML de diagnóstico. fonte=%s arquivo=%s",
            source_code,
            html,
        )

    try:
        pagina.screenshot(path=str(screenshot), full_page=True)
        evidencias["screenshot"] = screenshot
    except Exception:
        logger.exception(
            "Não foi possível salvar o screenshot de diagnóstico. fonte=%s arquivo=%s",
            source_code,
            screenshot,
        )

    return evidencias


def url_atual(pagina):
    """Obtém a URL apenas para diagnóstico, inclusive após falha do navegador."""
    try:
        return pagina.url
    except Exception:
        return "<indisponível>"


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


def _notice_cards(pagina):
    return pagina.locator("#avisosPannel_body > div")


def _run_database_call(operation, *args):
    """Executa ORM fora do loop interno usado pela API síncrona do Playwright."""
    def call_in_database_thread():
        try:
            return operation(*args)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(call_in_database_thread).result()


def tratar_quadro_avisos(pagina, source):
    """Persiste todos os avisos antes de confirmá-los individualmente no PJe."""
    cards = _notice_cards(pagina)
    count = cards.count()
    if count == 0:
        raise RuntimeError("O Quadro de Avisos não apresentou cartões reconhecíveis.")

    # A leitura é feita integralmente antes de qualquer clique irreversível.
    raw_cards = [cards.nth(index).inner_html() for index in range(count)]
    notice_links = _run_database_call(persist_notices, raw_cards, source)
    if len(notice_links) != count:
        raise RuntimeError("O Quadro de Avisos retornou uma quantidade inesperada de registros.")

    for index, link in enumerate(notice_links):
        current_cards = _notice_cards(pagina)
        before = current_cards.count()
        button = current_cards.nth(0).get_by_text("Aviso lido", exact=True)
        if button.count() != 1:
            raise RuntimeError(f"Botão 'Aviso lido' não encontrado para o aviso {index + 1}.")
        button.click()
        try:
            pagina.wait_for_function(
                "previous => document.querySelectorAll('#avisosPannel_body > div').length < previous",
                arg=before,
                timeout=10000,
            )
        except PlaywrightTimeoutError as error:
            raise RuntimeError("O PJe não confirmou a leitura do aviso.") from error
        _run_database_call(mark_confirmed, link)

    # Ao confirmar o último aviso, algumas instalações do PJe voltam ao painel
    # automaticamente e removem o botão de navegação intermediário.
    if pagina.locator("#divResultadoMenuContexto").count() == 1:
        return f"{count} aviso(s) do PJe armazenado(s) e confirmado(s)."

    painel = pagina.get_by_text("Painel do usuário", exact=True)
    if painel.count() != 1:
        raise RuntimeError("Botão 'Painel do usuário' não encontrado de forma única.")
    painel.click()
    pagina.locator("#divResultadoMenuContexto").wait_for(state="visible", timeout=15000)
    return f"{count} aviso(s) do PJe armazenado(s) e confirmado(s)."


def esperar_destino_pos_login(pagina, source):
    """Aceita diretamente o painel ou trata o bloqueio do Quadro de Avisos."""
    for _ in range(30):
        if pagina.locator("#avisosPannel").count() == 1:
            return tratar_quadro_avisos(pagina, source)
        if pagina.locator("#divResultadoMenuContexto").count() == 1:
            return ""
        pagina.wait_for_timeout(500)
    if pagina.get_by_text("Código inválido", exact=True).count():
        raise RuntimeError(
            "O PJe rejeitou o código TOTP. "
            "Verifique o horário do computador e o segredo configurado."
        )
    raise RuntimeError(f"Login não confirmou. URL atual: {pagina.url}")


TRT21_NOTICE_BOARD = "pje-visualizar-avisos"
TRT21_MARK_ALL_NOTICES = (
    "pje-visualizar-avisos "
    "mat-checkbox.btn-marcar-todos-como-lido:visible"
)
TRT21_NOTICE_CONFIRMATION = "Deseja realmente marcar todos os avisos como lidos?"
TRT21_NOTICE_SUCCESS = "Todos os avisos foram marcados como lidos"
TRT21_NOTICE_LOAD_TIMEOUT_MS = 30000


def tratar_quadro_avisos_trt21(pagina):
    """Dispensa o mural Angular do TRT21 antes de abrir os expedientes.

    O PJe do TRT21 não usa o painel legado tratado em ``tratar_quadro_avisos``:
    ele apresenta um mural Angular que bloqueia a navegação após o login. Como
    os avisos são institucionais e não expedientes, confirmamos a leitura de
    todos para a coleta poder continuar normalmente.
    """
    marcar_todos = pagina.locator(TRT21_MARK_ALL_NOTICES)
    try:
        # O Angular pode desmontar e remontar o componente enquanto recebe os
        # avisos. O clique do Playwright espera por um controle visível, estável
        # e habilitado numa única operação, sem a corrida entre wait_for/count.
        marcar_todos.click(timeout=TRT21_NOTICE_LOAD_TIMEOUT_MS)
    except PlaywrightTimeoutError as error:
        raise RuntimeError(
            "O Quadro de Avisos do TRT21 não terminou de carregar."
        ) from error

    confirmacao = pagina.get_by_text(TRT21_NOTICE_CONFIRMATION, exact=True)
    try:
        confirmacao.wait_for(state="visible", timeout=10000)
    except PlaywrightTimeoutError as error:
        raise RuntimeError("O TRT21 não exibiu a confirmação para marcar os avisos como lidos.") from error

    confirmar = pagina.get_by_text("Sim", exact=True)
    if confirmar.count() != 1:
        raise RuntimeError("Botão de confirmação dos avisos do TRT21 não encontrado de forma única.")
    confirmar.click()

    dialogo_sucesso = pagina.get_by_role("dialog")
    sucesso = dialogo_sucesso.get_by_text(TRT21_NOTICE_SUCCESS, exact=True)
    try:
        sucesso.wait_for(state="visible", timeout=10000)
    except PlaywrightTimeoutError as error:
        raise RuntimeError("O TRT21 não confirmou a leitura dos avisos.") from error

    fechar_sucesso = dialogo_sucesso.get_by_role("button", name="OK", exact=True)
    fechar_sucesso.click()
    try:
        dialogo_sucesso.wait_for(state="hidden", timeout=10000)
    except PlaywrightTimeoutError as error:
        raise RuntimeError("A confirmação dos avisos do TRT21 não foi fechada.") from error

    painel = pagina.get_by_role("button", name="Meu Painel", exact=True)
    if painel.count() != 1:
        raise RuntimeError("Botão 'Meu Painel' do TRT21 não encontrado de forma única.")
    painel.click()
    pagina.get_by_text("Meus Expedientes", exact=True).wait_for(
        state="visible", timeout=15000
    )


def esperar_destino_pos_login_trt21(pagina):
    """Espera o painel TRT21, dispensando seu mural de avisos quando exibido."""
    for _ in range(30):
        if pagina.locator(TRT21_NOTICE_BOARD).count() == 1:
            tratar_quadro_avisos_trt21(pagina)
            return
        if pagina.get_by_text("Meus Expedientes", exact=True).count() == 1:
            return
        pagina.wait_for_timeout(500)
    raise RuntimeError(f"Login TRT21 não confirmou. URL atual: {pagina.url}")

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
    return get_source_profile(source_code).url


def abrir_link_trf5_pje(pagina, profile):
    """Abre o acesso autenticado da seção PJe 2.X do portal do TRF5."""
    if not profile.portal_button_name or not profile.portal_destination_host:
        raise RuntimeError(f"A fonte {profile.code} não possui acesso pelo portal TRF5.")

    aba_acessos = pagina.locator(".aba2:visible")
    if aba_acessos.count() != 1:
        raise RuntimeError("A aba 'ACESSOS AO PJE' do portal TRF5 não foi encontrada de forma única.")
    aba_acessos.click()

    # O texto exato evita confundir as subseções de consulta e autenticação.
    titulo = pagina.locator('div.titulo:visible:text-is("PJe 2.X")')
    titulo.wait_for(state="visible", timeout=15000)
    if titulo.count() != 1:
        raise RuntimeError("A seção 'PJe 2.X' do portal TRF5 não foi encontrada de forma única.")
    links = titulo.locator(
        "xpath=parent::div[contains(@class, 'row')]/"
        "following-sibling::div[contains(@class, 'boxes')][1]"
    )
    if links.count() != 1:
        raise RuntimeError("Os acessos da seção 'PJe 2.X' do portal TRF5 não foram encontrados.")

    link = links.get_by_role("link", name=profile.portal_button_name, exact=True)
    if link.count() != 1:
        raise RuntimeError(
            f"O botão {profile.portal_button_name!r} do PJe 2.X não foi encontrado de forma única."
        )
    destination = link.get_attribute("href") or ""
    if urlparse(destination).hostname != profile.portal_destination_host:
        raise RuntimeError(
            f"O botão {profile.portal_button_name!r} não corresponde ao destino esperado "
            f"({profile.portal_destination_host})."
        )

    # O portal abre o destino em outra aba. Mantemos a mesma página para que a
    # sessão recém-criada siga até o SSO e possa ser acompanhada pela coleta.
    link.evaluate("element => element.removeAttribute('target')")
    link.click()
    pagina.wait_for_load_state("domcontentloaded", timeout=15000)


def clicar_certificado(pagina, source_code):
    """Seleciona o controle de certificado da tela de login da fonte."""
    if get_source_profile(source_code).collector == "trt21":
        botao = pagina.locator(".botao-certificado-titulo").get_by_text(
            "Seu certificado digital", exact=True
        )
    else:
        botao = pagina.get_by_text("CERTIFICADO DIGITAL", exact=True)
    if botao.count() != 1:
        raise RuntimeError("Botão de certificado digital não encontrado de forma única.")
    botao.click()


def entrar_com_pdpj(pagina):
    """Abre o SSO PDPJ a partir da tela simples de login do TRT21."""
    imagem = pagina.locator(
        "img[alt*='PDPJ' i], img[title*='PDPJ' i], img[src*='pdpj' i]"
    )
    if imagem.count() != 1:
        raise RuntimeError("Imagem do botão 'Entrar com PDPJ' não encontrada de forma única.")
    imagem.click()
    pagina.locator(".botao-certificado-titulo").wait_for(
        state="visible", timeout=15000
    )


def autenticar_pje(pagina, source_code):
    segredo_totp = os.environ.get("PJE_TOTP_SECRET")
    if not segredo_totp:
        raise RuntimeError("PJE_TOTP_SECRET não foi configurado.")

    if get_source_profile(source_code).collector == "trt21":
        entrar_com_pdpj(pagina)
    clicar_certificado(pagina, source_code)
    preencher_pin_pjeoffice_atspi()

    campo_otp = pagina.get_by_label(
        "Entre no seu aplicativo de autenticação e digite abaixo o código apresentado:",
        exact=True,
    )
    campo_otp.wait_for(state="visible")
    campo_otp.fill(gerar_codigo_totp(segredo_totp))
    pagina.get_by_text("Validar", exact=True).click()


def abrir_pje(source_code, source=None):
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

        try:
            pagina.goto(
                pje_url,
                wait_until="domcontentloaded"
            )

            profile = get_source_profile(source_code)
            if profile.portal_button_name:
                abrir_link_trf5_pje(pagina, profile)

            print("O navegador foi aberto.")
            print("Aguardando o login por certificado digital.")
            print("O PIN será preenchido na janela do PJeOffice.")

            autenticar_pje(pagina, source_code)

            if profile.collector == "trt21":
                esperar_destino_pos_login_trt21(pagina)
                return collect_trt21_expedientes(pagina)
            if source is None:
                from automation.models import AutomationSource
                source = AutomationSource.objects.get(code=source_code)
            notice_message = esperar_destino_pos_login(pagina, source)
            return LegacyCollection(coletar_expedientes(pagina, source_code), notice_message)
        except Exception:
            evidencias = salvar_diagnostico_pje(pagina, source_code)
            logger.exception(
                "Falha na automação PJe. fonte=%s url=%s diagnostico_html=%s "
                "diagnostico_screenshot=%s",
                source_code,
                url_atual(pagina),
                evidencias["html"],
                evidencias["screenshot"],
            )
            raise
        finally:
            navegador.close()

if __name__ == "__main__":
    arquivos = abrir_pje("pje-tjrn")
