from datetime import datetime, time
import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import AutomationRun, AutomationSource, UserProfile
from .queue import enqueue_due_runs, enqueue_run, recover_interrupted_runs
from .services.pje.browser import clicar_certificado, entrar_com_pdpj, obter_url_pje
from .services.pje.runner import executar_coleta
from .services.pje.sources import PJE_SOURCE_ORDER
from .services.pje.trt21 import TRT21Collection


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

    def test_second_degree_is_not_enqueued_when_first_degree_fails(self):
        run = AutomationRun.objects.create(source=self.first_degree)

        with (
            patch(
                "automation.services.pje.runner.abrir_pje",
                side_effect=RuntimeError("Falha no PJe 1º grau"),
            ),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
            self.assertRaisesMessage(RuntimeError, "Falha no PJe 1º grau"),
        ):
            executar_coleta(run)

        enqueue.assert_not_called()

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
            patch("automation.services.pje.runner.enqueue_run"),
        ):
            executar_coleta(run)
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Status.SUCCESS)
        self.assertEqual(run.mensagem_info, "Nenhum expediente novo encontrado.")


class PJeBrowserTests(TestCase):
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
        self.assertEqual(PJE_SOURCE_ORDER, ("pje-tjrn", "pje2g-tjrn", "trt21", "trt21-2g"))
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
