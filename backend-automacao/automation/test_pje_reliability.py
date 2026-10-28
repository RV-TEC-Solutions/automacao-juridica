from unittest.mock import MagicMock, Mock, call, patch
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from .services.pje import browser


class PJeReliabilityTests(SimpleTestCase):
    @patch.dict("os.environ", {"PJE_TOTP_SECRET": "configured"})
    def test_tjrn_prepares_and_clicks_the_same_certificate_input_in_both_degrees(self):
        for source_code in ("pje-tjrn", "pje2g-tjrn"):
            with self.subTest(source=source_code):
                page = MagicMock()
                certificate = page.locator.return_value
                certificate.count.return_value = 1
                with (
                    patch.object(browser, "preencher_pin_pjeoffice_atspi"),
                    patch.object(browser, "gerar_codigo_totp", return_value="123456"),
                ):
                    browser.autenticar_pje(page, source_code)

                self.assertEqual(
                    page.locator.call_args_list,
                    [call("#kc-pje-office"), call("#kc-pje-office")],
                )
                self.assertEqual(certificate.wait_for.call_count, 2)
                page.wait_for_function.assert_called_once()
                certificate.click.assert_called_once_with()
                self.assertNotIn(
                    call("CERTIFICADO DIGITAL", exact=True),
                    page.get_by_text.call_args_list,
                )

    def test_portal_accepts_committed_sso_without_waiting_for_domcontentloaded(self):
        page = Mock()
        profile = browser.get_source_profile("tre-rn-1g")
        browser.abrir_destino_pje(page, Mock(), profile)
        predicate = page.wait_for_url.call_args.args[0]
        self.assertTrue(predicate("https://sso.cloud.pje.jus.br/auth?state=secret"))
        self.assertFalse(predicate("https://example.com/"))
        self.assertEqual(page.wait_for_url.call_args.kwargs["wait_until"], "commit")
        page.wait_for_load_state.assert_not_called()

    def test_analytics_and_unattributed_console_errors_do_not_become_failure_evidence(self):
        events = [
            {"tipo": "recurso_interrompido", "detalhe": "analytics", "auxiliar": True},
            {"tipo": "console", "detalhe": "403 sem URL"},
            {"tipo": "http", "detalhe": "HTTP 403: login", "auxiliar": False},
        ]
        self.assertEqual(browser.evidencias_relevantes(events), events[2:])
        self.assertTrue(browser.recurso_auxiliar("https://analytics.google.com/g/collect"))
        self.assertFalse(browser.recurso_auxiliar("https://sso.cloud.pje.jus.br/login"))

    @patch.dict("os.environ", {"PJE_TOTP_SECRET": "configured"})
    def test_varas_login_preparation_uses_exact_certificate_text(self):
        page = MagicMock()
        with (
            patch.object(browser, "preparar_login_certificado") as prepare,
            patch.object(browser, "clicar_certificado"),
            patch.object(browser, "preencher_pin_pjeoffice_atspi"),
            patch.object(browser, "gerar_codigo_totp", return_value="123456"),
        ):
            browser.autenticar_pje(page, "varas-justica-comum")
        page.get_by_text.assert_any_call("CERTIFICADO DIGITAL", exact=True)
        prepare.assert_called_once_with(page, page.get_by_text.return_value)

    def test_login_reloads_only_once_when_scripts_never_become_ready(self):
        page = Mock(url="https://sso.cloud.pje.jus.br/login?state=secret")
        page.wait_for_function.side_effect = PlaywrightTimeoutError("script ausente")
        with self.assertRaisesMessage(browser.PJeAutomationError, "Nenhuma solicitação de PIN"):
            browser.preparar_login_certificado(page, "#kc-pje-office")
        page.reload.assert_called_once()
        self.assertEqual(page.wait_for_function.call_count, 2)

    def test_login_recovers_before_contacting_the_signer(self):
        page = Mock(url="https://sso.cloud.pje.jus.br/login")
        page.wait_for_function.side_effect = [PlaywrightTimeoutError("script ausente"), None]
        browser.preparar_login_certificado(page, "#kc-pje-office")
        page.reload.assert_called_once()

    @patch.dict("os.environ", {"PJE_TOTP_SECRET": "configured"})
    def test_no_local_request_never_starts_pin_helper(self):
        page = MagicMock()
        page.expect_request.return_value.__exit__.side_effect = PlaywrightTimeoutError("nenhuma chamada")
        with (
            patch.object(browser, "preparar_login_certificado"),
            patch.object(browser, "clicar_certificado"),
            patch.object(browser, "preencher_pin_pjeoffice_atspi") as pin,
            self.assertRaisesMessage(browser.PJeAutomationError, "O PIN ainda não foi solicitado"),
        ):
            browser.autenticar_pje(page, "tre-rn-1g")
        pin.assert_not_called()
        page.reload.assert_not_called()

    def test_local_request_filter_rejects_other_hosts_and_availability_probe(self):
        for url in ["https://example.com:8800/pjeOffice/requisicao/", "http://localhost:8800/pjeOffice/"]:
            self.assertFalse(browser.requisicao_pjeoffice(Mock(url=url)))
        self.assertTrue(browser.requisicao_pjeoffice(Mock(url="http://localhost:8800/pjeOffice/requisicao/?r=secret")))

    @patch.dict("os.environ", {"PJE_CURRENT_COLLECTOR": "murilo", "PJE_TOTP_SECRET": "configured"})
    def test_murilo_waits_for_signer_response_before_generating_totp(self):
        page = MagicMock()
        request = page.expect_request_finished.return_value.__enter__.return_value.value
        request.response.return_value.status = 200
        with (
            patch.object(browser, "preparar_login_certificado"),
            patch.object(browser, "clicar_certificado"),
            patch.object(browser, "preencher_pin_pjeoffice_atspi"),
            patch.object(browser, "release_identity") as release,
            patch.object(browser, "gerar_codigo_totp", return_value="123456") as totp,
        ):
            order = Mock()
            order.attach_mock(request.response, "response")
            order.attach_mock(release, "release")
            order.attach_mock(totp, "totp")
            browser.autenticar_pje(page, "pje-tjrn")
        self.assertEqual(order.mock_calls, [call.response(), call.release("murilo"), call.totp("configured")])
        totp.assert_called_once_with("configured")
        predicate = page.expect_request_finished.call_args.args[0]
        local_url = "http://localhost:8800/pjeOffice/requisicao/?r=secret"
        self.assertFalse(predicate(Mock(url=local_url, method="OPTIONS")))
        self.assertTrue(predicate(Mock(url=local_url, method="GET")))
        request.response.return_value.body.assert_not_called()
        request.response.return_value.finished.assert_not_called()

    @patch.dict("os.environ", {"PJE_CURRENT_COLLECTOR": "murilo", "PJE_TOTP_SECRET": "configured"})
    def test_unfinished_or_failed_signer_is_not_reported_as_missing_otp(self):
        for status in (500, None):
            with self.subTest(status=status):
                page = MagicMock()
                page.expect_request_finished.return_value.__enter__.return_value.value.response.return_value.status = status
                if status is None:
                    page.expect_request_finished.return_value.__exit__.side_effect = PlaywrightTimeoutError("sem resposta")
                with (
                    patch.object(browser, "preparar_login_certificado"),
                    patch.object(browser, "clicar_certificado"),
                    patch.object(browser, "preencher_pin_pjeoffice_atspi"),
                    patch.object(browser, "gerar_codigo_totp") as totp,
                    self.assertRaises(browser.PJeAutomationError) as raised,
                ):
                    browser.autenticar_pje(page, "pje-tjrn")
                self.assertEqual(raised.exception.etapa, "Autenticação no PJeOffice")
                page.get_by_label.assert_not_called()
                totp.assert_not_called()

    @patch.dict("os.environ", {"PJE_CURRENT_COLLECTOR": "murilo", "PJE_TOTP_SECRET": "configured"})
    def test_signer_completion_without_http_response_never_starts_totp(self):
        page = MagicMock()
        page.expect_request_finished.return_value.__enter__.return_value.value.response.return_value = None
        with (
            patch.object(browser, "preparar_login_certificado"),
            patch.object(browser, "clicar_certificado"),
            patch.object(browser, "preencher_pin_pjeoffice_atspi"),
            patch.object(browser, "release_identity") as release,
            patch.object(browser, "gerar_codigo_totp") as totp,
            self.assertRaisesMessage(browser.PJeAutomationError, "HTTP verificável"),
        ):
            browser.autenticar_pje(page, "pje-tjrn")
        release.assert_not_called()
        totp.assert_not_called()

    @patch.dict("os.environ", {"PJE_TOTP_SECRET": "configured", "PJE_CURRENT_COLLECTOR": "cristiano"})
    def test_cristiano_authentication_keeps_the_existing_flow(self):
        page = MagicMock()
        with (
            patch.object(browser, "preparar_login_certificado"),
            patch.object(browser, "clicar_certificado"),
            patch.object(browser, "preencher_pin_pjeoffice_atspi"),
            patch.object(browser, "gerar_codigo_totp", return_value="123456"),
        ):
            browser.autenticar_pje(page, "pje-tjrn")
        page.expect_response.assert_not_called()
        page.expect_request_finished.assert_not_called()

    def test_only_murilo_limits_browser_memory_and_uses_direct_official_access(self):
        for collector in ("murilo", "cristiano"):
            for code, direct in (
                ("tse-3g", "https://pje.tse.jus.br/pje/login.seam"),
                ("tre-rn-1g", "https://pje1g-rn.tse.jus.br/pje"),
                ("tre-rn-2g", "https://pje.tre-rn.jus.br/pje"),
            ):
                page = Mock()
                page.goto.side_effect = RuntimeError("fim do teste antes do login")
                playwright = MagicMock()
                playwright.chromium.launch.return_value.new_context.return_value.new_page.return_value = page
                with (
                    self.subTest(collector=collector, source=code),
                    patch.dict("os.environ", {"PJE_CURRENT_COLLECTOR": collector}),
                    patch.object(browser, "sync_playwright") as sync,
                    patch.object(browser, "release_identity"),
                    patch.object(browser, "salvar_diagnostico_pje", return_value={"html": None, "screenshot": None}),
                    self.assertLogs("automation", "ERROR"),
                    self.assertRaises(browser.PJeAutomationError),
                ):
                    sync.return_value.__enter__.return_value = playwright
                    browser.abrir_pje(code)
                expected_options = {"headless": False}
                if collector == "murilo":
                    expected_options["args"] = ["--disable-gpu", "--renderer-process-limit=2"]
                playwright.chromium.launch.assert_called_once_with(**expected_options)
                expected = direct if collector == "murilo" else browser.obter_url_pje(code)
                page.goto.assert_called_once_with(expected, wait_until="domcontentloaded")

    def test_ajax_response_is_correlated_with_the_clicked_tab(self):
        page = MagicMock()
        tab = Mock()
        tab.get_attribute.return_value = "form:tab:2"
        response = page.expect_response.return_value.__enter__.return_value.value
        response.status = 200
        response.finished.return_value = None
        with patch.object(browser, "clicar_apos_dispensar_aviso_certificado"), patch.object(browser, "esperar_view_expedientes"):
            browser.clicar_aba_expedientes(page, tab)
        predicate = page.expect_response.call_args.args[0]
        self.assertFalse(predicate(Mock(request=Mock(method="POST", post_data="form%3Atab%3A1=x"))))
        self.assertTrue(predicate(Mock(request=Mock(method="POST", post_data="form%3Atab%3A2=x"))))

    def test_ajax_failure_does_not_save_or_import_a_partial_view(self):
        page = Mock()
        tabs = Mock()
        tabs.count.return_value = 6
        with (
            patch.object(browser, "localizar_abas_filhas", return_value=tabs),
            patch.object(browser, "clicar_aba_expedientes", side_effect=PlaywrightTimeoutError("bloqueado")),
            patch.object(browser, "salvar_html_renderizado") as save,
            self.assertRaisesMessage(browser.PJeAutomationError, "aba 1/6; 0 captura(s)"),
        ):
            browser.coletar_expedientes(page, "varas-justica-comum")
        save.assert_not_called()

    def test_stuck_loading_layer_is_a_loading_failure(self):
        page = Mock()
        page.locator.return_value.wait_for.side_effect = PlaywrightTimeoutError("bloqueado")
        with self.assertRaisesMessage(browser.PJeAutomationError, "camada de carregamento AJAX"):
            browser.aguardar_ajax_pje(page)

    def test_failed_collection_records_stage_and_safe_browser_events(self):
        page = Mock(url="https://sso.cloud.pje.jus.br/login?state=secret")
        listeners = {}
        page.on.side_effect = lambda event, callback: listeners.update({event: callback})

        def fail_navigation(*args, **kwargs):
            listeners["requestfailed"](Mock(
                url="https://sso.cloud.pje.jus.br/pjeOffice.js?token=secret",
                failure="net::ERR_CONNECTION_RESET",
            ))
            raise PlaywrightTimeoutError("state=secret")

        page.goto.side_effect = fail_navigation
        playwright = MagicMock()
        playwright.chromium.launch.return_value.new_context.return_value.new_page.return_value = page
        with TemporaryDirectory() as directory:
            html = Path(directory) / "page.html"
            html.write_text("diagnóstico")
            with (
                patch.object(browser, "sync_playwright") as sync,
                patch.object(browser, "salvar_diagnostico_pje", return_value={"html": html, "screenshot": None}),
                self.assertLogs("automation", level="ERROR") as logs,
                self.assertRaisesMessage(browser.PJeAutomationError, "ERR_CONNECTION_RESET") as raised,
            ):
                sync.return_value.__enter__.return_value = playwright
                browser.abrir_pje("tre-rn-1g")
            summary = json.loads(html.with_name("diagnostico.json").read_text())
        self.assertEqual(summary["etapa"], "Abertura do site")
        self.assertNotIn("secret", str(raised.exception))
        self.assertNotIn("secret", logs.output[0])
        self.assertNotIn("secret", json.dumps(summary))

    def test_safe_diagnostics_strip_queries_fragments_sessions_and_pin(self):
        with patch.dict("os.environ", {"PJE_CERT_PIN": "987654"}):
            result = browser.texto_diagnostico_seguro(
                "erro http://localhost:8800/pjeOffice/requisicao/?r=desafio#token PIN 987654 "
                "https://user:password@sso.cloud.pje.jus.br/login;jsessionid=secret?state=secret"
            )
        for secret in ("desafio", "token", "987654", "password", "jsessionid", "state=secret"):
            self.assertNotIn(secret, result)
        self.assertIn("http://localhost/pjeOffice/requisicao/", result)
