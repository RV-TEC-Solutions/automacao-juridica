import asyncio
from datetime import datetime, time
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import SynchronousOnlyOperation
from django.test import TestCase
from rest_framework.test import APIClient
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .models import AutomationRun, AutomationSource, Notice, NoticeSource, UserProfile
from .queue import enqueue_due_runs, enqueue_run, recover_interrupted_runs
from .services.pje.browser import (
    abrir_pje,
    clicar_certificado,
    entrar_com_pdpj,
    abrir_link_trf5_pje,
    obter_url_pje,
    salvar_diagnostico_pje,
    tratar_quadro_avisos,
    tratar_quadro_avisos_trt21,
)
from .services.pje.runner import executar_coleta
from .services.pje.sources import PJE_SOURCE_ORDER, TRF5_PORTAL_URL, get_source_profile
from .services.pje.trt21 import TRT21Collection, collect_trt21_expedientes
from .services.pje.notices import parse_notice_card, persist_notices


class QueueTests(TestCase):
    def setUp(self):
        self.source = AutomationSource.objects.get(code="pje-tjrn")

    def test_prevents_concurrent_runs_per_source(self):
        enqueue_run(self.source, AutomationRun.Trigger.MANUAL)
        with self.assertRaisesMessage(ValueError, "Já existe"):
            enqueue_run(self.source, AutomationRun.Trigger.MANUAL)

    def test_catch_up_is_enqueued_after_configured_time_once(self):
        user = get_user_model().objects.create_user("user")
        UserProfile.objects.create(user=user, display_name="User", collection_time=time(6))
        now = datetime(2026, 8, 25, 7, tzinfo=ZoneInfo("America/Fortaleza"))
        self.assertEqual(len(enqueue_due_runs(now)), 1)
        self.assertEqual(len(enqueue_due_runs(now)), 0)

    def test_scheduler_enqueues_only_the_first_degree_source(self):
        user = get_user_model().objects.create_user("user")
        UserProfile.objects.create(user=user, display_name="User", collection_time=time(6))
        second_degree = AutomationSource.objects.get(code="pje2g-tjrn")
        now = datetime(2026, 8, 25, 7, tzinfo=ZoneInfo("America/Fortaleza"))

        runs = enqueue_due_runs(now)

        self.assertEqual([run.source for run in runs], [self.source])
        self.assertFalse(second_degree.runs.exists())

    def test_scheduler_starts_with_the_first_enabled_source(self):
        self.source.enabled = False
        self.source.save(update_fields=("enabled",))
        second_degree = AutomationSource.objects.get(code="pje2g-tjrn")
        second_degree.enabled = False
        second_degree.save(update_fields=("enabled",))
        user = get_user_model().objects.create_user("user")
        UserProfile.objects.create(user=user, display_name="User", collection_time=time(6))
        now = datetime(2026, 8, 25, 7, tzinfo=ZoneInfo("America/Fortaleza"))

        runs = enqueue_due_runs(now)

        self.assertEqual([run.source.code for run in runs], ["trt21"])

    def test_recovers_a_run_left_running_by_an_interrupted_worker(self):
        run = AutomationRun.objects.create(
            source=self.source,
            status=AutomationRun.Status.RUNNING,
        )

        recovered = recover_interrupted_runs()

        self.assertEqual(recovered, 1)
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Status.FAILED)
        self.assertIsNotNone(run.finalizada_em)
        self.assertEqual(
            run.mensagem_erro,
            "Coleta interrompida antes da conclusão; recupere-a executando novamente.",
        )
        next_run = enqueue_run(self.source, AutomationRun.Trigger.MANUAL)
        self.assertEqual(next_run.status, AutomationRun.Status.PENDING)


class PJePipelineTests(TestCase):
    def setUp(self):
        self.first_degree = AutomationSource.objects.get(code="pje-tjrn")
        self.second_degree = AutomationSource.objects.get(code="pje2g-tjrn")

    def test_second_degree_is_enqueued_only_after_first_degree_succeeds(self):
        run = AutomationRun.objects.create(
            source=self.first_degree,
            trigger=AutomationRun.Trigger.MANUAL,
        )

        def assert_first_degree_was_finalized(*args, **kwargs):
            run.refresh_from_db()
            self.assertEqual(run.status, AutomationRun.Status.SUCCESS)
            self.assertIsNotNone(run.finalizada_em)

        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch(
                "automation.services.pje.runner.salvar_expedientes",
                return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0},
            ),
            patch(
                "automation.services.pje.runner.enqueue_run",
                side_effect=assert_first_degree_was_finalized,
            ) as enqueue,
        ):
            executar_coleta(run)

        enqueue.assert_called_once_with(
            self.second_degree,
            trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,
            scheduled_for=None,
        )

    def test_chain_continues_when_a_source_fails(self):
        run = AutomationRun.objects.create(source=self.first_degree)
        next_source = AutomationSource.objects.get(code="pje2g-tjrn")

        with (
            patch(
                "automation.services.pje.runner.abrir_pje",
                side_effect=RuntimeError("Falha no PJe 1º grau"),
            ),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
            self.assertRaisesMessage(RuntimeError, "Falha no PJe 1º grau"),
        ):
            executar_coleta(run)

        enqueue.assert_called_once_with(
            next_source,
            trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,
            scheduled_for=None,
        )

    def test_failure_persists_safe_message_and_logs_traceback_with_run_context(self):
        run = AutomationRun.objects.create(source=self.first_degree)

        with (
            patch(
                "automation.services.pje.runner.abrir_pje",
                side_effect=RuntimeError("Falha de automação segura"),
            ),
            self.assertLogs("automation", level="ERROR") as logs,
            self.assertRaisesMessage(RuntimeError, "Falha de automação segura"),
        ):
            executar_coleta(run)

        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Status.FAILED)
        self.assertEqual(run.mensagem_erro, "Falha de automação segura")
        self.assertTrue(logs.records[0].exc_info)
        self.assertIn(f"Coleta #{run.pk} falhou", logs.output[0])
        self.assertIn("fonte=pje-tjrn", logs.output[0])

    def test_chain_continues_from_second_degree_to_trt21(self):
        run = AutomationRun.objects.create(source=self.second_degree)
        trt21 = AutomationSource.objects.get(code="trt21")
        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        enqueue.assert_called_once_with(
            trt21, trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None, scheduled_for=None,
        )

    def test_chain_skips_disabled_sources(self):
        self.second_degree.enabled = False
        self.second_degree.save(update_fields=("enabled",))
        run = AutomationRun.objects.create(source=self.first_degree)
        trt21 = AutomationSource.objects.get(code="trt21")
        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        enqueue.assert_called_once_with(
            trt21, trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None, scheduled_for=None,
        )

    def test_empty_trt21_collection_is_successful_and_informative(self):
        trt21 = AutomationSource.objects.get(code="trt21")
        run = AutomationRun.objects.create(source=trt21)
        with (
            patch(
                "automation.services.pje.runner.abrir_pje",
                return_value=TRT21Collection([], "Nenhum expediente novo encontrado."),
            ),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Status.SUCCESS)
        self.assertEqual(run.mensagem_info, "Nenhum expediente novo encontrado.")
        enqueue.assert_called_once_with(
            AutomationSource.objects.get(code="trt21-2g"),
            trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,
            scheduled_for=None,
        )


class AutomationRunApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("operador")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_manual_run_starts_at_first_enabled_source_when_requested_source_is_disabled(self):
        first_degree = AutomationSource.objects.get(code="pje-tjrn")
        first_degree.enabled = False
        first_degree.save(update_fields=("enabled",))
        second_degree = AutomationSource.objects.get(code="pje2g-tjrn")
        second_degree.enabled = False
        second_degree.save(update_fields=("enabled",))

        response = self.client.post(
            "/api/automation/runs/", {"source": "pje-tjrn"}, format="json"
        )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["source"], "trt21")


class PJeBrowserTests(TestCase):
    def test_notice_board_accepts_the_panel_when_the_last_ajax_click_redirects(self):
        page = Mock()
        cards = Mock()
        cards.count.return_value = 1
        card = cards.nth.return_value
        card.inner_html.return_value = "<div>aviso</div>"
        button = card.get_by_text.return_value
        button.count.return_value = 1
        panel = Mock()
        panel.count.return_value = 1
        page.locator.side_effect = lambda selector: (
            cards if selector == "#avisosPannel_body > div" else panel
        )

        with patch(
            "automation.services.pje.browser._run_database_call",
            side_effect=[[Mock(pje_confirmed_at=None)], None],
        ):
            message = tratar_quadro_avisos(page, Mock())

        self.assertEqual(message, "1 aviso(s) do PJe armazenado(s) e confirmado(s).")
        button.click.assert_called_once_with()
        page.get_by_text.assert_not_called()

    def test_notice_board_persists_outside_the_playwright_event_loop(self):
        page = Mock()
        cards = Mock()
        cards.count.return_value = 2
        card = cards.nth.return_value
        card.inner_html.return_value = "<div>aviso</div>"
        button = card.get_by_text.return_value
        button.count.return_value = 1
        panel = Mock()
        panel.count.return_value = 1
        panel_after_notices = Mock()
        panel_after_notices.count.return_value = 0
        page.locator.side_effect = lambda selector: (
            cards if selector == "#avisosPannel_body > div" else panel_after_notices
        )
        page.get_by_text.return_value = panel
        links = [Mock(pje_confirmed_at=None), Mock(pje_confirmed_at=None)]

        def persist_only_outside_the_event_loop(*args):
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return links
            raise SynchronousOnlyOperation("ORM executado no loop do Playwright")

        async def collect_notices():
            return tratar_quadro_avisos(page, Mock())

        with (
            patch(
                "automation.services.pje.browser.persist_notices",
                side_effect=persist_only_outside_the_event_loop,
            ),
            patch("automation.services.pje.browser.mark_confirmed") as mark_confirmed,
        ):
            message = asyncio.run(collect_notices())

        self.assertEqual(message, "2 aviso(s) do PJe armazenado(s) e confirmado(s).")
        self.assertEqual(button.click.call_count, 2)
        self.assertEqual(mark_confirmed.call_count, 2)
        self.assertEqual(page.wait_for_function.call_count, 2)
        page.wait_for_function.assert_any_call(
            "previous => document.querySelectorAll('#avisosPannel_body > div').length < previous",
            arg=2,
            timeout=10000,
        )
        panel.click.assert_called_once_with()

    def test_trf5_sources_start_from_the_portal_with_stable_button_identifiers(self):
        expected_sources = {
            "trf5-2g-tru": ("TRF 5ª Região", "pjett.trf5.jus.br"),
            "varas-justica-comum": ("Varas da Justiça Comum", "pje1g.trf5.jus.br"),
            "jef-5-regiao": ("JEF 5ª Região", "pje1g.trf5.jus.br"),
            "trs-5-regiao": ("TR's 5ª Região", "pje2g.trf5.jus.br"),
            "tru-5-regiao": ("TRU 5ª Região", "pjett.trf5.jus.br"),
        }

        for source_code, (button_name, expected_host) in expected_sources.items():
            profile = get_source_profile(source_code)
            self.assertEqual(profile.url, TRF5_PORTAL_URL)
            self.assertEqual(profile.portal_button_name, button_name)
            self.assertEqual(profile.portal_destination_host, expected_host)
            self.assertNotIn("state=", profile.url)

    def test_trf5_portal_opens_only_the_named_pje_2x_link(self):
        page = Mock()
        access_tab = Mock()
        access_tab.count.return_value = 1
        title = Mock()
        title.count.return_value = 1
        links = Mock()
        links.count.return_value = 1
        link = Mock()
        link.count.return_value = 1
        link.get_attribute.return_value = "https://pjett.trf5.jus.br/pje/login.seam"
        page.locator.side_effect = lambda selector, **kwargs: (
            access_tab if selector == ".aba2:visible" else title
        )
        title.locator.return_value = links
        links.get_by_role.return_value = link
        abrir_link_trf5_pje(page, get_source_profile("trf5-2g-tru"))

        access_tab.click.assert_called_once_with()
        title.wait_for.assert_called_once_with(state="visible", timeout=15000)
        links.get_by_role.assert_called_once_with(
            "link", name="TRF 5ª Região", exact=True
        )
        link.evaluate.assert_called_once_with(
            "element => element.removeAttribute('target')"
        )
        link.click.assert_called_once_with()

    def test_trf5_portal_rejects_a_link_outside_the_expected_host(self):
        page = Mock()
        access_tab = Mock()
        access_tab.count.return_value = 1
        title = Mock()
        title.count.return_value = 1
        links = Mock()
        links.count.return_value = 1
        link = Mock()
        link.count.return_value = 1
        link.get_attribute.return_value = "https://example.invalid/pje/login.seam"
        page.locator.side_effect = lambda selector, **kwargs: (
            access_tab if selector == ".aba2:visible" else title
        )
        title.locator.return_value = links
        links.get_by_role.return_value = link

        with self.assertRaisesMessage(RuntimeError, "não corresponde ao destino esperado"):
            abrir_link_trf5_pje(page, get_source_profile("trf5-2g-tru"))

        link.click.assert_not_called()

    def test_trt21_zero_expedientes_finishes_without_clicking_the_disabled_card(self):
        page = Mock()
        expedientes_card = Mock()
        expedientes_card.count.return_value = 1
        expedientes_card.locator.return_value.count.return_value = 1
        page.get_by_role.return_value = expedientes_card
        page.wait_for_url.side_effect = AssertionError(
            "A coleta não deve aguardar navegação quando não há expedientes."
        )

        collection = collect_trt21_expedientes(page)

        self.assertEqual(collection, TRT21Collection([], "Nenhum expediente novo encontrado."))
        page.get_by_text.assert_not_called()
        page.wait_for_url.assert_not_called()

    def test_saves_html_and_screenshot_diagnostics_locally(self):
        page = Mock()
        page.content.return_value = "<html>diagnóstico</html>"

        def write_screenshot(*, path, full_page):
            self.assertTrue(full_page)
            Path(path).write_bytes(b"png")

        page.screenshot.side_effect = write_screenshot
        with TemporaryDirectory() as directory, patch(
            "automation.services.pje.browser.PASTA_RESPOSTAS", Path(directory)
        ):
            evidencias = salvar_diagnostico_pje(page, "trt21")

            self.assertEqual(evidencias["html"].read_text(encoding="utf-8"), "<html>diagnóstico</html>")
            self.assertEqual(evidencias["screenshot"].read_bytes(), b"png")
            self.assertEqual(evidencias["html"].parent, evidencias["screenshot"].parent)
            self.assertEqual(evidencias["html"].parent.parent.name, "diagnostico")

    def test_diagnostic_capture_failure_does_not_mask_the_collection_error(self):
        page = Mock()
        page.url = "https://pje.trt21.jus.br/primeirograu/login.seam"
        page.goto.side_effect = RuntimeError("Falha original da coleta")
        page.content.side_effect = RuntimeError("HTML indisponível")
        page.screenshot.side_effect = RuntimeError("Screenshot indisponível")
        navegador = Mock()
        navegador.new_context.return_value.new_page.return_value = page
        playwright = Mock()
        playwright.chromium.launch.return_value = navegador

        with (
            TemporaryDirectory() as directory,
            patch("automation.services.pje.browser.PASTA_RESPOSTAS", Path(directory)),
            patch(
                "automation.services.pje.browser.sync_playwright"
            ) as sync_playwright,
            self.assertLogs("automation", level="ERROR") as logs,
            self.assertRaisesMessage(RuntimeError, "Falha original da coleta"),
        ):
            sync_playwright.return_value.__enter__.return_value = playwright
            abrir_pje("trt21")

        self.assertEqual(len(logs.records), 3)
        self.assertTrue(logs.records[0].exc_info)
        self.assertTrue(logs.records[1].exc_info)
        self.assertTrue(logs.records[2].exc_info)
        self.assertIn("Falha na automação PJe", logs.output[2])

    def test_resolves_the_url_for_each_supported_source(self):
        self.assertEqual(
            obter_url_pje("pje-tjrn"),
            "https://pje1g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam",
        )
        self.assertEqual(
            obter_url_pje("pje2g-tjrn"),
            "https://pje2g.tjrn.jus.br/pje/Painel/painel_usuario/advogado.seam",
        )

    def test_rejects_an_unknown_pje_source(self):
        with self.assertRaisesMessage(RuntimeError, "Fonte PJe não suportada"):
            obter_url_pje("pje-inexistente")

    def test_resolves_trt21_urls_and_source_order(self):
        self.assertEqual(PJE_SOURCE_ORDER, (
            "pje-tjrn", "pje2g-tjrn", "trt21", "trt21-2g", "trf5-2g-tru",
            "varas-justica-comum", "jef-5-regiao", "trs-5-regiao", "tru-5-regiao",
        ))
        self.assertEqual(obter_url_pje("trt21"), "https://pje.trt21.jus.br/primeirograu/login.seam")
        self.assertEqual(obter_url_pje("trt21-2g"), "https://pje.trt21.jus.br/segundograu/login.seam")

    def test_trt21_uses_its_certificate_control(self):
        page = Mock()
        title = page.locator.return_value.get_by_text.return_value
        title.count.return_value = 1
        clicar_certificado(page, "trt21")
        page.locator.assert_called_once_with(".botao-certificado-titulo")
        title.click.assert_called_once_with()

    def test_trt21_opens_pdpj_by_clicking_its_image(self):
        page = Mock()
        image = page.locator.return_value
        image.count.return_value = 1
        entrar_com_pdpj(page)
        image.click.assert_called_once_with()
        page.locator.assert_any_call(".botao-certificado-titulo")

    def test_trt21_marks_its_angular_notice_board_as_read_before_collecting(self):
        page = Mock()
        mark_all = page.locator.return_value
        mark_all.count.return_value = 1

        confirmation = Mock()
        confirm = Mock()
        confirm.count.return_value = 1
        success = Mock()
        success_dialog = Mock()
        close_success = Mock()
        expedientes = Mock()
        painel = Mock()
        painel.count.return_value = 1
        text_locators = {
            "Deseja realmente marcar todos os avisos como lidos?": confirmation,
            "Sim": confirm,
            "Meus Expedientes": expedientes,
        }
        page.get_by_text.side_effect = lambda text, **kwargs: text_locators[text]
        page.get_by_role.side_effect = lambda role, **kwargs: (
            success_dialog
            if role == "dialog"
            else painel
        )
        success_dialog.get_by_text.return_value = success
        success_dialog.get_by_role.return_value = close_success

        tratar_quadro_avisos_trt21(page)

        mark_all.count.assert_not_called()
        mark_all.click.assert_called_once_with(timeout=30000)
        confirmation.wait_for.assert_called_once_with(state="visible", timeout=10000)
        confirm.click.assert_called_once_with()
        success_dialog.get_by_text.assert_called_once_with(
            "Todos os avisos foram marcados como lidos", exact=True
        )
        success.wait_for.assert_called_once_with(state="visible", timeout=10000)
        success_dialog.get_by_role.assert_called_once_with(
            "button", name="OK", exact=True
        )
        close_success.click.assert_called_once_with()
        success_dialog.wait_for.assert_called_once_with(state="hidden", timeout=10000)
        painel.click.assert_called_once_with()
        expedientes.wait_for.assert_called_once_with(state="visible", timeout=15000)

    def test_trt21_reports_when_its_notice_board_does_not_finish_loading(self):
        page = Mock()
        mark_all = page.locator.return_value
        mark_all.click.side_effect = PlaywrightTimeoutError("timed out")

        with self.assertRaisesMessage(
            RuntimeError,
            "O Quadro de Avisos do TRT21 não terminou de carregar.",
        ):
            tratar_quadro_avisos_trt21(page)

        mark_all.click.assert_called_once_with(timeout=30000)

    def test_trt21_logs_context_when_close_button_is_not_unique(self):
        from .services.pje.trt21 import collect_trt21_expedientes

        page = Mock()
        page.url = "https://pje.trt21.jus.br/primeirograu/pendentes-manifestacao"
        page.get_by_text.return_value.click.return_value = None
        table_rows = Mock()
        table_rows.count.return_value = 1
        row = table_rows.nth.return_value
        row.get_by_role.return_value.count.return_value = 1
        modal = Mock()
        modal.locator.return_value.count.return_value = 0
        page.locator.return_value = table_rows
        page.get_by_role.return_value = modal

        with (
            self.assertLogs("automation", level="ERROR") as logs,
            self.assertRaisesMessage(RuntimeError, "Não foi possível fechar"),
        ):
            collect_trt21_expedientes(page)

        self.assertIn("linha=1/1", logs.output[0])
        self.assertIn("encontrados=0", logs.output[0])
        self.assertIn(page.url, logs.output[0])

    def test_trt21_waits_for_loaded_close_control_before_reading_details(self):
        from .services.pje.trt21 import collect_trt21_expedientes

        page = Mock()
        table_rows = Mock()
        table_rows.count.return_value = 1
        headers = Mock()
        headers.count.return_value = 0
        row = table_rows.nth.return_value
        row.inner_text.return_value = "0000000-00.2026.5.21.0000"
        row.get_by_role.return_value.count.return_value = 1
        row.locator.return_value.count.return_value = 0
        modal = Mock()
        modal.inner_text.return_value = "Intimação"
        close = Mock()
        close.count.return_value = 1
        modal.locator.return_value = close
        page.locator.side_effect = lambda selector: (
            table_rows if selector == "table tbody tr" else headers
        )
        page.get_by_role.return_value = modal

        collect_trt21_expedientes(page)

        modal.locator.assert_called_once_with(
            ".container-botao-fechar > a[role='button']"
        )
        close.wait_for.assert_called_once_with(state="visible", timeout=10000)


class NoticeTests(TestCase):
    card = """
        <div><h3>Indisponibilidade programada</h3>
        <em>Incluída por Equipe PJe em18/09/2026 10:31<br>Publicado em 18/09/2026</em>
        <p>Leia o <strong>comunicado</strong> <a href='https://example.test/ato'>aqui</a>.</p>
        <script>alert('não deve sobreviver')</script>
        <form><input value='Aviso lido'></form></div>
    """

    def setUp(self):
        self.source = AutomationSource.objects.get(code="trf5-2g-tru")
        self.other_source = AutomationSource.objects.get(code="jef-5-regiao")

    def test_parses_and_sanitizes_notice_card(self):
        notice = parse_notice_card(self.card)
        self.assertEqual(notice.title, "Indisponibilidade programada")
        self.assertEqual(notice.included_by, "Equipe PJe")
        self.assertEqual(notice.published_at.date().isoformat(), "2026-09-18")
        self.assertEqual(notice.links, ["https://example.test/ato"])
        self.assertIn("<strong>comunicado</strong>", notice.content_html)
        self.assertNotIn("script", notice.content_html)
        self.assertNotIn("alert", notice.content_text)

    def test_deduplicates_notice_and_keeps_source_links(self):
        persist_notices([self.card], self.source)
        persist_notices([self.card], self.other_source)
        self.assertEqual(Notice.objects.count(), 1)
        self.assertEqual(NoticeSource.objects.count(), 2)

    def test_notice_api_requires_auth_and_marks_read(self):
        persist_notices([self.card], self.source)
        notice = Notice.objects.get()
        self.assertIn(self.client.get("/api/notices/").status_code, (401, 403))
        user = get_user_model().objects.create_user("notices", password="senha-segura")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/notices/").json()["count"], 1)
        response = self.client.post(f"/api/notices/{notice.pk}/read/")
        self.assertEqual(response.status_code, 200)
        notice.refresh_from_db()
        self.assertIsNotNone(notice.read_at)


class AuthApiTests(TestCase):
    def test_private_api_requires_authentication(self):
        self.assertIn(self.client.get("/api/dashboard/").status_code, (401, 403))

    def test_login_and_settings(self):
        get_user_model().objects.create_user("operador", password="senha-segura")
        response = self.client.post(
            "/api/auth/login/", {"username": "operador", "password": "senha-segura"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(
            "/api/settings/", {"display_name": "Victor", "theme": "dark", "collection_time": "06:30"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["display_name"], "Victor")


class PJeOfficeTests(TestCase):
    def test_pin_helper_uses_system_python_with_pyatspi(self):
        from .services.pje.browser import preencher_pin_pjeoffice_atspi

        with (
            patch.dict("os.environ", {"PJE_CERT_PIN": "1234"}, clear=True),
            patch(
                "automation.services.pje.browser.subprocess.run",
                return_value=SimpleNamespace(returncode=0, stderr=""),
            ) as run,
        ):
            preencher_pin_pjeoffice_atspi()

        self.assertEqual(run.call_args.args[0][0], "/usr/bin/python3")

    def test_pin_helper_confirms_with_enter_when_no_known_button_exists(self):
        helper_path = (
            __file__.replace("automation/tests.py", "automation/services/pjeoffice/atspi.py")
        )
        fake_pyatspi = SimpleNamespace(
            Registry=SimpleNamespace(generateKeyboardEvent=Mock()),
            KEY_SYM="symbolic-key",
        )

        with patch.dict(sys.modules, {"pyatspi": fake_pyatspi}):
            spec = importlib.util.spec_from_file_location("pjeoffice_atspi_test", helper_path)
            helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)

        campo = Mock()
        componente = campo.queryComponent.return_value
        componente.grabFocus.return_value = True

        helper.confirmar_com_enter(campo)

        fake_pyatspi.Registry.generateKeyboardEvent.assert_called_once_with(
            0xFF0D, None, "symbolic-key"
        )

    def test_pin_helper_locates_ok_button_by_accessible_name(self):
        helper_path = (
            __file__.replace("automation/tests.py", "automation/services/pjeoffice/atspi.py")
        )
        fake_pyatspi = SimpleNamespace(
            ROLE_PUSH_BUTTON="push-button",
            STATE_SHOWING="showing",
            STATE_SENSITIVE="sensitive",
        )

        with patch.dict(sys.modules, {"pyatspi": fake_pyatspi}):
            spec = importlib.util.spec_from_file_location("pjeoffice_atspi_button_test", helper_path)
            helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(helper)

        class State:
            def __init__(self, values):
                self.values = values

            def contains(self, value):
                return value in self.values

        class Node:
            def __init__(self, role, name, states, children=()):
                self.role = role
                self.name = name
                self.states = State(states)
                self.children = children

            def getRole(self):
                return self.role

            def getState(self):
                return self.states

            def __iter__(self):
                return iter(self.children)

        botao_ok = Node(
            "push-button", "OK", {"showing", "sensitive"}
        )
        janela = Node("dialog", "Informe a senha", set(), [botao_ok])

        self.assertIs(helper.localizar_botao_confirmar(janela), botao_ok)
