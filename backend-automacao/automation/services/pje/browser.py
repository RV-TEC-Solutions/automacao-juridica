import logging
import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse
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

CERTIFICATE_EXPIRY_CLICK_RETRY_TIMEOUT_MS = 10000
AJAX_TIMEOUT_MS = 30000
LOGIN_TIMEOUT_MS = 30000
AJAX_STATUS = '[id="_viewRoot:status.start"]'

load_dotenv(CREDENCIAIS)


def url_segura(url):
    """Mantém domínio/caminho; descarta parâmetros de sessão e credenciais."""
    parsed = urlparse(str(url))
    if parsed.scheme not in ("https", "http"):
        return "<indisponível>"
    return f"{parsed.scheme}://{parsed.hostname}{parsed.path.split(';')[0]}"


def texto_diagnostico_seguro(texto):
    texto = re.sub(r'onclick="[^"]*"', 'onclick="[omitido]"', str(texto))
    texto = re.sub(r'\b(state|token|session_code|nonce|codigoSeguranca)=\S+', r'\1=[omitido]', texto)
    texto = re.sub(r'https?://[^\s<>\"\x27]+', lambda m: url_segura(m[0]), str(texto))
    for name in ("PJE_CERT_PIN", "PJE_TOTP_SECRET"):
        secret = os.environ.get(name)
        if secret:
            texto = texto.replace(secret, "[omitido]")
    return texto[:1500]


def recurso_auxiliar(url):
    host = urlparse(str(url)).hostname or ""
    return any(host == domain or host.endswith("." + domain) for domain in (
        "google-analytics.com", "analytics.google.com", "googletagmanager.com",
    ))


def evidencias_relevantes(eventos):
    return [e for e in eventos if not e.get("auxiliar") and e["tipo"] != "console"]


def abrir_destino_pje(pagina, link, profile):
    """Espera o destino confirmado, sem depender do carregamento de recursos externos."""
    link.evaluate("element => element.removeAttribute('target')")
    try:
        link.click(no_wait_after=True, timeout=LOGIN_TIMEOUT_MS)
        pagina.wait_for_url(
            lambda url: urlparse(str(url)).hostname in (
                profile.portal_destination_host, "sso.cloud.pje.jus.br",
            ),
            wait_until="commit", timeout=LOGIN_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError as error:
        raise PJeAutomationError(
            "Acesso ao PJe pelo portal",
            f"o acesso não confirmou o destino {profile.portal_destination_host} ou o SSO "
            f"em 30 segundos. Página atual: {url_segura(url_atual(pagina))}.",
        ) from error


class PJeAutomationError(RuntimeError):
    def __init__(self, etapa, motivo):
        self.etapa = etapa
        self.motivo = motivo
        super().__init__(f"{etapa}: {motivo}")


def aguardar_ajax_pje(pagina):
    try:
        pagina.locator(AJAX_STATUS).wait_for(state="hidden", timeout=AJAX_TIMEOUT_MS)
    except PlaywrightTimeoutError as error:
        raise PJeAutomationError(
            "Carregamento dos expedientes",
            "o PJe permaneceu com a camada de carregamento AJAX ativa por 30 segundos. "
            "A coleta foi interrompida para evitar importar dados incompletos.",
        ) from error


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
    texto_pendencias = menu_contexto.locator(
        "div.containerDocumentos.nivel1"
    ).get_by_text(
        texto_aba, exact=True
    )
    aba_pendencias = texto_pendencias.locator("xpath=ancestor::a[1]")
    if aba_pendencias.count() == 0:
        item_vazio = texto_pendencias.locator(
            "xpath=ancestor::div["
            "contains(concat(' ', normalize-space(@class), ' '), "
            "' itemSemLink ')][1]"
        )
        contador = item_vazio.locator("span.pull-right")
        if (
            texto_pendencias.count() == 1
            and item_vazio.count() == 1
            and contador.count() == 1
            and contador.inner_text().strip() == "0"
        ):
            return None
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

    clicar_apos_dispensar_aviso_certificado(pagina, aba_pendencias)
    arvore.wait_for(state="visible")

    if linha_n2.count() != 1 or arvore.count() != 1:
        raise RuntimeError(
            "A árvore irmã da opção principal não foi encontrada "
            "de forma única."
        )

    return arvore


def clicar_apos_dispensar_aviso_certificado(pagina, alvo):
    """Clica novamente apenas se o alerta RichFaces tardio bloquear o primeiro clique.

    Aguarda a camada AJAX e tolera carregamento tardio durante o clique.
    Um segundo clique só é permitido após fechar o alerta conhecido.
    """
    fechar_aviso_certificado_proximo_de_expirar(pagina)
    aguardar_ajax_pje(pagina)
    try:
        alvo.click(timeout=CERTIFICATE_EXPIRY_CLICK_RETRY_TIMEOUT_MS)
        return
    except PlaywrightTimeoutError:
        if not fechar_aviso_certificado_proximo_de_expirar(pagina):
            raise
    alvo.click()


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
    if arvore is None:
        return None
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
    aguardar_ajax_pje(pagina)


def clicar_aba_expedientes(pagina, aba):
    """Correlaciona a resposta AJAX com a aba para não salvar o conteúdo anterior."""
    identifier = aba.get_attribute("id")
    if not identifier:
        raise PJeAutomationError("Coleta dos expedientes", "a aba não possui identificador AJAX.")

    def corresponde(response):
        request = response.request
        return (
            request.method == "POST"
            and identifier in parse_qs(request.post_data or "")
        )

    try:
        with pagina.expect_response(corresponde, timeout=AJAX_TIMEOUT_MS) as pending:
            clicar_apos_dispensar_aviso_certificado(pagina, aba)
        response = pending.value
        if response.status >= 400:
            raise PJeAutomationError(
                "Coleta dos expedientes", f"o carregamento da aba retornou HTTP {response.status}."
            )
        response.body()  # Aguarda todo o corpo antes de verificar a renderização do DOM.
        esperar_view_expedientes(pagina)
    except PlaywrightTimeoutError as error:
        raise PJeAutomationError(
            "Coleta dos expedientes",
            "o PJe não concluiu o clique ou a resposta AJAX da aba no prazo de 30 segundos.",
        ) from error


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
    if abas_filhas is None:
        print("Nenhum expediente pendente encontrado.")
        return []
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

        try:
            clicar_aba_expedientes(pagina, aba_filha)
        except Exception as error:
            raise PJeAutomationError(
                "Coleta dos expedientes",
                f"falha na aba {indice + 1}/{quantidade}; {len(arquivos)} captura(s) parcial(is) "
                f"salva(s), sem importar os resultados desta tentativa. {texto_diagnostico_seguro(error)}",
            ) from error

        arquivo = salvar_html_renderizado(
            pagina,
            pasta_respostas,
            indice + 1
        )
        arquivos.append(arquivo)
        print(f"HTML salvo em: {arquivo}")

    return arquivos


TRE_RN_PANEL_BUTTON = "input[type=submit][value=\"Painel do usuário\"]"
CERTIFICATE_EXPIRY_DIALOG = "#popupAlertaCertificadoProximoDeExpirarContainer"
CERTIFICATE_EXPIRY_CLOSE = f"{CERTIFICATE_EXPIRY_DIALOG} span.btn-fechar"
CERTIFICATE_EXPIRY_APPEAR_TIMEOUT_MS = 5000


LEGACY_NOTICE_CARDS = "#avisosPannel_body > div"
def _notice_cards(pagina):
    return pagina.locator(LEGACY_NOTICE_CARDS)



def _run_database_call(operation, *args):
    """Executa ORM fora do loop interno usado pela API síncrona do Playwright."""
    def call_in_database_thread():
        try:
            return operation(*args)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(call_in_database_thread).result()


def _persist_notice_cards(cards, source):
    count = cards.count()
    if count == 0:
        raise RuntimeError("O Quadro de Avisos não apresentou cartões reconhecíveis.")

    raw_cards = [cards.nth(index).inner_html() for index in range(count)]
    notice_links = _run_database_call(persist_notices, raw_cards, source)
    if len(notice_links) != count:
        raise RuntimeError("O Quadro de Avisos retornou uma quantidade inesperada de registros.")
    return count, notice_links


def _abrir_painel_do_usuario(pagina, count, action, *, allow_already_open=False):
    if allow_already_open and pagina.locator("#divResultadoMenuContexto").count() == 1:
        return f"{count} aviso(s) do PJe armazenado(s) e {action}(s)."

    painel = pagina.get_by_text("Painel do usuário", exact=True)
    if painel.count() != 1:
        raise RuntimeError("Botão Painel do usuário não encontrado de forma única.")
    painel.click()
    try:
        pagina.locator("#divResultadoMenuContexto").wait_for(
            state="visible", timeout=15000
        )
    except PlaywrightTimeoutError as error:
        raise RuntimeError("O Painel do usuário não abriu após os avisos do PJe.") from error
    return f"{count} aviso(s) do PJe armazenado(s) e {action}(s)."


def _tratar_quadro_avisos_legado(pagina, source):
    cards = _notice_cards(pagina)
    count, notice_links = _persist_notice_cards(cards, source)

    for index, link in enumerate(notice_links):
        current_cards = _notice_cards(pagina)
        before = current_cards.count()
        button = current_cards.nth(0).get_by_text("Aviso lido", exact=True)
        if button.count() != 1:
            raise RuntimeError(f"Botão Aviso lido não encontrado para o aviso {index + 1}.")
        button.click()
        try:
            pagina.wait_for_function(
                """previous => document.querySelectorAll("#avisosPannel_body > div").length < previous""",
                arg=before,
                timeout=10000,
            )
        except PlaywrightTimeoutError as error:
            raise RuntimeError("O PJe não confirmou a leitura do aviso.") from error
        _run_database_call(mark_confirmed, link)

    return _abrir_painel_do_usuario(
        pagina, count, "confirmado", allow_already_open=True
    )


def _tratar_quadro_avisos_tre_rn(pagina, source):
    """Ignora avisos institucionais TRE-RN e abre o painel de expedientes."""
    pagina.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    painel = pagina.locator(TRE_RN_PANEL_BUTTON)
    if painel.count() != 1:
        raise RuntimeError("Botão Painel do usuário TRE-RN não encontrado de forma única.")
    painel.scroll_into_view_if_needed()
    painel.click()
    try:
        pagina.locator("#divResultadoMenuContexto").wait_for(
            state="visible", timeout=15000
        )
    except PlaywrightTimeoutError as error:
        raise RuntimeError("O Painel do usuário TRE-RN não abriu.") from error

    aguardar_e_fechar_aviso_certificado_proximo_de_expirar(pagina)
    return "Avisos institucionais TRE-RN ignorados; Painel do usuário aberto."

def tratar_quadro_avisos(pagina, source):
    """Persiste e confirma avisos conforme a estratégia da fonte PJe."""
    profile = get_source_profile(source.code)
    if profile.notice_board_strategy == "tre-rn":
        return _tratar_quadro_avisos_tre_rn(pagina, source)
    return _tratar_quadro_avisos_legado(pagina, source)

CERTIFICATE_EXPIRY_TITLE = "Certificado próximo de expirar"

def fechar_aviso_certificado_proximo_de_expirar(pagina):
    """Fecha o alerta RichFaces por ID estável, mantendo o fallback jQuery UI."""
    richfaces_dialog = pagina.locator(
        CERTIFICATE_EXPIRY_DIALOG
    )
    richfaces_count = richfaces_dialog.count()
    if richfaces_count > 1:
        raise RuntimeError("O alerta RichFaces de expiração não foi encontrado de forma única.")
    if richfaces_count == 1:
        close = richfaces_dialog.locator("span.btn-fechar")
        if close.count() != 1:
            raise RuntimeError("O botão para fechar o alerta RichFaces não foi encontrado.")
        # O contêiner externo do RichFaces mede 0x0 mesmo quando a máscara e o
        # conteúdo estão visíveis. A visibilidade deve ser lida no controle que
        # recebe o clique, não no contêiner.
        if not close.is_visible():
            return False
        close.click()
        try:
            close.wait_for(state="hidden", timeout=10000)
        except PlaywrightTimeoutError as error:
            raise RuntimeError("O alerta RichFaces do certificado não foi fechado.") from error
        return True

    title = pagina.get_by_text(CERTIFICATE_EXPIRY_TITLE, exact=True)
    if title.count() == 0:
        return False
    if title.count() != 1:
        raise RuntimeError("O aviso de expiração do certificado não foi encontrado de forma única.")

    dialog = title.locator("""xpath=ancestor::*[contains(@class, "ui-dialog")][1]""")
    if dialog.count() != 1:
        raise RuntimeError("O contêiner do aviso de expiração do certificado não foi encontrado.")
    if not dialog.is_visible():
        return False
    close = dialog.locator(".ui-dialog-titlebar-close")
    if close.count() != 1:
        raise RuntimeError("O botão para fechar o aviso de expiração do certificado não foi encontrado.")
    close.click()
    try:
        dialog.wait_for(state="hidden", timeout=10000)
    except PlaywrightTimeoutError as error:
        raise RuntimeError("O aviso de expiração do certificado não foi fechado.") from error
    return True


def aguardar_e_fechar_aviso_certificado_proximo_de_expirar(pagina):
    """Espera o alerta RichFaces tardio antes de interagir com expedientes."""
    close = pagina.locator(CERTIFICATE_EXPIRY_CLOSE)
    try:
        close.wait_for(state="visible", timeout=CERTIFICATE_EXPIRY_APPEAR_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        return False
    return fechar_aviso_certificado_proximo_de_expirar(pagina)


def esperar_destino_pos_login(pagina, source):
    """Aceita o painel após dispensar aviso de certificado e Quadro de Avisos."""
    for _ in range(30):
        if fechar_aviso_certificado_proximo_de_expirar(pagina):
            continue
        if pagina.locator("#avisosPannel").count() == 1:
            return tratar_quadro_avisos(pagina, source)
        if pagina.locator("#divResultadoMenuContexto").count() == 1:
            if get_source_profile(source.code).notice_board_strategy == "tre-rn":
                aguardar_e_fechar_aviso_certificado_proximo_de_expirar(pagina)
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


def _abrir_link_tre_rn_pje(pagina, profile, portal_link_name, access_link_name):
    """Chega ao PJe TRE-RN por links estáveis do portal institucional."""
    if not profile.portal_destination_host:
        raise RuntimeError(f"A fonte {profile.code} não possui destino PJe esperado.")

    portal_link = pagina.get_by_role("link", name=portal_link_name, exact=True)
    if portal_link.count() != 1:
        raise RuntimeError(
            f"O acesso {portal_link_name!r} do portal TRE-RN não foi encontrado "
            "de forma única."
        )
    portal_link.click(no_wait_after=True, timeout=LOGIN_TIMEOUT_MS)

    access_link = pagina.get_by_role("link", name=access_link_name, exact=True)
    try:
        access_link.wait_for(state="visible", timeout=LOGIN_TIMEOUT_MS)
    except PlaywrightTimeoutError as error:
        raise PJeAutomationError(
            "Acesso ao PJe pelo portal", f"o portal não apresentou o link {access_link_name!r} em 30 segundos."
        ) from error
    if access_link.count() != 1:
        raise RuntimeError(
            f"O acesso {access_link_name!r} não foi encontrado de forma única."
        )
    destination = access_link.get_attribute("href") or ""
    if urlparse(destination).hostname != profile.portal_destination_host:
        raise RuntimeError(
            f"O acesso {access_link_name!r} não corresponde ao destino esperado "
            f"({profile.portal_destination_host})."
        )

    abrir_destino_pje(pagina, access_link, profile)


def abrir_link_tre_rn_1g_pje(pagina, profile):
    return _abrir_link_tre_rn_pje(
        pagina, profile, "PJe - 1º Grau", "Clique aqui para acessar o PJE-Zonas"
    )


def abrir_link_tre_rn_2g_pje(pagina, profile):
    return _abrir_link_tre_rn_pje(
        pagina, profile, "PJe - 2º Grau", "Acesso ao sistema"
    )


def abrir_link_tse_3g_pje(pagina, profile):
    """Abre o PJe 3º grau pelo acesso estável do portal institucional do TSE."""
    if not profile.portal_destination_host:
        raise RuntimeError(f"A fonte {profile.code} não possui destino PJe esperado.")

    # O ícone +/- do acordeão é inserido por CSS e passa a integrar o nome
    # acessível calculado pelo Chromium. Por isso, um get_by_role com o texto
    # exato visível não encontra o botão. O id do painel e seu aria-controls
    # formam o contrato estrutural estável publicado pelo portal.
    secao = pagina.locator("#collapse-pje-3o-grau")
    if secao.count() != 1:
        raise RuntimeError(
            "A seção PJE 3º grau do portal TSE não foi encontrada de forma única."
        )
    acionador = pagina.locator('[aria-controls="collapse-pje-3o-grau"]')
    if acionador.count() != 1:
        raise RuntimeError(
            "O controle da seção PJE 3º grau do portal TSE não foi encontrado "
            "de forma única."
        )
    if not secao.is_visible():
        acionador.click()
        secao.wait_for(state="visible", timeout=15000)

    link = secao.get_by_role(
        "link", name="Tribunal Superior Eleitoral", exact=True
    )
    link.wait_for(state="visible", timeout=15000)
    if link.count() != 1:
        raise RuntimeError(
            "O acesso ao PJe do TSE não foi encontrado de forma única."
        )
    destination = link.get_attribute("href") or ""
    if urlparse(destination).hostname != profile.portal_destination_host:
        raise RuntimeError(
            "O acesso ao PJe do TSE não corresponde ao destino esperado "
            f"({profile.portal_destination_host})."
        )

    link.evaluate("element => element.removeAttribute('target')")
    link.click()
    pagina.wait_for_load_state("domcontentloaded", timeout=15000)


def clicar_certificado(pagina, source_code):
    """Seleciona o controle de certificado específico da fonte PJe."""
    profile = get_source_profile(source_code)
    if profile.certificate_button_selector:
        botao = pagina.locator(profile.certificate_button_selector)
        selector = profile.certificate_button_selector
    elif profile.collector == "trt21":
        botao = pagina.locator(".botao-certificado-titulo").get_by_text(
            "Seu certificado digital", exact=True
        )
        selector = ".botao-certificado-titulo >> text=Seu certificado digital"
    else:
        botao = pagina.get_by_text("CERTIFICADO DIGITAL", exact=True)
        selector = "text=CERTIFICADO DIGITAL"

    try:
        botao.wait_for(state="visible", timeout=15000)
    except PlaywrightTimeoutError as error:
        raise RuntimeError(
            "Botão de certificado digital não ficou visível no prazo. "
            f"fonte={source_code} seletor={selector!r} url={url_segura(pagina.url)!r} "
            f"quantidade={botao.count()}"
        ) from error
    if botao.count() != 1:
        raise RuntimeError(
            "Botão de certificado digital não encontrado de forma única. "
            f"fonte={source_code} seletor={selector!r} url={url_segura(pagina.url)!r} "
            f"quantidade={botao.count()}"
        )
    botao.click()


def entrar_com_pdpj(pagina):
    """Abre o SSO PDPJ a partir da tela simples de login do TRT21."""
    imagem = pagina.locator(
        "img[alt*='PDPJ' i], img[title*='PDPJ' i], img[src*='pdpj' i]"
    )
    if imagem.count() != 1:
        raise RuntimeError("Imagem do botão 'Entrar com PDPJ' não encontrada de forma única.")
    imagem.click()
    preparar_login_certificado(pagina, ".botao-certificado-titulo")


def preparar_login_certificado(pagina, selector):
    """Uma recarga limitada apenas antes de qualquer solicitação ao assinador."""
    for tentativa in range(2):
        try:
            botao = pagina.locator(selector) if isinstance(selector, str) else selector
            botao.wait_for(state="visible", timeout=LOGIN_TIMEOUT_MS)
            pagina.wait_for_function(
                "window.location.hostname === 'sso.cloud.pje.jus.br' ? "
                "(typeof window.autenticar === 'function' && "
                "typeof window.PJeOffice?.executar === 'function') : document.readyState === 'complete'",
                timeout=LOGIN_TIMEOUT_MS,
            )
            return
        except PlaywrightTimeoutError as error:
            if tentativa:
                raise PJeAutomationError(
                    "Preparação do login",
                    "a tela de autenticação ou o script do certificado não ficou pronto, "
                    "mesmo após uma recarga. Nenhuma solicitação de PIN foi iniciada.",
                ) from error
            logger.warning("Tela de autenticação incompleta; recarregando uma vez. url=%s", url_segura(pagina.url))
            try:
                pagina.reload(wait_until="domcontentloaded", timeout=LOGIN_TIMEOUT_MS)
            except PlaywrightTimeoutError:
                # A segunda tentativa verifica os controles, inclusive se o DOM veio parcialmente.
                pass


def requisicao_pjeoffice(request):
    parsed = urlparse(request.url)
    return parsed.hostname in ("localhost", "127.0.0.1") and parsed.port == 8800 and parsed.path == "/pjeOffice/requisicao/"


def autenticar_pje(pagina, source_code):
    segredo_totp = os.environ.get("PJE_TOTP_SECRET")
    if not segredo_totp:
        raise RuntimeError("PJE_TOTP_SECRET não foi configurado.")

    if get_source_profile(source_code).collector == "trt21":
        entrar_com_pdpj(pagina)
    else:
        profile = get_source_profile(source_code)
        botao = (
            pagina.locator(profile.certificate_button_selector)
            if profile.certificate_button_selector
            else pagina.get_by_text("CERTIFICADO DIGITAL", exact=True)
        )
        preparar_login_certificado(pagina, botao)
    try:
        with pagina.expect_request(requisicao_pjeoffice, timeout=10000):
            clicar_certificado(pagina, source_code)
    except PlaywrightTimeoutError as error:
        raise PJeAutomationError(
            "Comunicação com o PJeOffice",
            "o botão de certificado não iniciou a chamada ao assinador em 10 segundos. "
            "Verifique o carregamento da página e a permissão de acesso à rede local. "
            "O PIN ainda não foi solicitado.",
        ) from error
    logger.info("Chamada de autenticação ao PJeOffice iniciada pela página. fonte=%s", source_code)
    try:
        preencher_pin_pjeoffice_atspi()
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        raise PJeAutomationError(
            "Autenticação no PJeOffice",
            "a página iniciou a chamada ao assinador, mas o preenchimento do PIN não foi concluído. "
            + texto_diagnostico_seguro(error),
        ) from error

    campo_otp = pagina.get_by_label(
        "Entre no seu aplicativo de autenticação e digite abaixo o código apresentado:",
        exact=True,
    )
    try:
        campo_otp.wait_for(state="visible", timeout=LOGIN_TIMEOUT_MS)
    except PlaywrightTimeoutError as error:
        raise PJeAutomationError(
            "Validação em duas etapas",
            "o PIN foi preenchido, mas a página não apresentou o campo do código de autenticação em 30 segundos.",
        ) from error
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
        eventos = []
        etapa = "Abertura do site"
        inicio = time.monotonic()

        def registrar(tipo, detalhe, *, url=None):
            evento = {"tipo": tipo, "detalhe": texto_diagnostico_seguro(detalhe)}
            if url is not None:
                evento.update(url=url_segura(url), auxiliar=recurso_auxiliar(url))
            eventos.append(evento)
            del eventos[:-20]

        pagina.on("pageerror", lambda error: registrar("javascript", error))
        pagina.on("requestfailed", lambda request: registrar(
            "recurso_interrompido", f"{url_segura(request.url)}: {request.failure}", url=request.url
        ))
        pagina.on("response", lambda response: registrar(
            "http", f"HTTP {response.status}: {url_segura(response.url)}", url=response.url
        ) if response.status >= 400 else None)
        def registrar_console(message):
            if message.type == "error":
                location = message.location or {}
                url = location.get("url")
                registrar("console", message.text, url=url if isinstance(url, str) and url else None)

        pagina.on("console", registrar_console)

        try:
            pagina.goto(
                pje_url,
                wait_until="domcontentloaded"
            )

            profile = get_source_profile(source_code)
            etapa = "Navegação pelo portal"
            if profile.portal_flow == "trf5":
                abrir_link_trf5_pje(pagina, profile)
            elif profile.portal_flow == "tre-rn-1g":
                abrir_link_tre_rn_1g_pje(pagina, profile)
            elif profile.portal_flow == "tre-rn-2g":
                abrir_link_tre_rn_2g_pje(pagina, profile)
            elif profile.portal_flow == "tse-3g":
                abrir_link_tse_3g_pje(pagina, profile)
            elif profile.portal_flow:
                raise RuntimeError(
                    f"Fluxo de portal PJe não suportado: {profile.portal_flow}."
                )

            print("O navegador foi aberto.")
            print("Aguardando o login por certificado digital.")
            print("O PIN será preenchido na janela do PJeOffice.")

            etapa = "Autenticação"
            autenticar_pje(pagina, source_code)

            etapa = "Abertura do painel e coleta dos expedientes"
            if profile.collector == "trt21":
                esperar_destino_pos_login_trt21(pagina)
                return collect_trt21_expedientes(pagina)
            if source is None:
                from automation.models import AutomationSource
                source = AutomationSource.objects.get(code=source_code)
            notice_message = esperar_destino_pos_login(pagina, source)
            return LegacyCollection(coletar_expedientes(pagina, source_code), notice_message)
        except Exception as error:
            evidencias = salvar_diagnostico_pje(pagina, source_code)
            etapa = getattr(error, "etapa", etapa)
            motivo = texto_diagnostico_seguro(getattr(error, "motivo", error))
            if isinstance(error, PlaywrightTimeoutError):
                # A primeira linha identifica a operação, sem reproduzir atributos/chaves do DOM.
                motivo = "o site não concluiu a operação no prazo esperado. " + texto_diagnostico_seguro(str(error).splitlines()[0])
            relevantes = evidencias_relevantes(eventos)
            if relevantes:
                observados = "; ".join(f"{e['tipo']}: {e['detalhe']}" for e in relevantes[-3:])
                motivo += f" Eventos associados à página (causa não confirmada): {observados[:700]}"
            mensagem = f"Fonte {source_code} — {etapa}: {motivo}"
            resumo = {
                "fonte": source_code, "etapa": etapa,
                "duracao_segundos": round(time.monotonic() - inicio, 1),
                "url": url_segura(url_atual(pagina)), "erro": mensagem,
                "tipo_erro": type(error).__name__, "eventos": eventos,
                "operacao": texto_diagnostico_seguro(str(error).splitlines()[0]),
                "html": str(evidencias["html"]) if evidencias["html"] else None,
                "screenshot": str(evidencias["screenshot"]) if evidencias["screenshot"] else None,
            }
            if evidencias["html"]:
                try:
                    evidencias["html"].with_name("diagnostico.json").write_text(
                        json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8"
                    )
                except OSError:
                    logger.error("Não foi possível salvar o resumo de diagnóstico. fonte=%s", source_code)
            logger.error("Falha na automação PJe. diagnostico=%s", json.dumps(resumo, ensure_ascii=False))
            # Não propaga URLs com parâmetros/desafios no traceback registrado pelo runner.
            raise PJeAutomationError(etapa, f"Fonte {source_code} — {motivo}") from None
        finally:
            navegador.close()

if __name__ == "__main__":
    arquivos = abrir_pje("pje-tjrn")
