import asyncio
from datetime import datetime, time, timedelta
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import SynchronousOnlyOperation
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from expedientes.models import Expediente, ExpedienteEvent, Processo

from .models import AutomationRun, AutomationSource, Notice, NoticeSource, UserProfile
from .queue import enqueue_due_runs, enqueue_run, recover_interrupted_runs
from .services.pje.browser import (
    abrir_pje,
    clicar_certificado,
    entrar_com_pdpj,
    abrir_link_trf5_pje,
    abrir_link_tre_rn_1g_pje,
    abrir_link_tre_rn_2g_pje,
    abrir_link_tse_3g_pje,
    fechar_aviso_certificado_proximo_de_expirar,
    aguardar_e_fechar_aviso_certificado_proximo_de_expirar,
    coletar_expedientes,
    localizar_arvore_pendencias,
    esperar_destino_pos_login,
    obter_url_pje,
    salvar_diagnostico_pje,
    tratar_quadro_avisos,
    tratar_quadro_avisos_trt21,
)
from .pipeline import collection_pipeline_payload
from .services.pje.runner import executar_coleta
from .services.pje.sources import (
    PJE_SOURCE_ORDER,
    TSE_PORTAL_URL,
    TRE_RN_PORTAL_URL,
    TRF5_PORTAL_URL,
    get_source_profile,
)
from .services.pje.trt21 import TRT21Collection, collect_trt21_expedientes
from .services.pje.notices import mark_confirmed, parse_notice_card, persist_notices


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

        self.assertEqual([run.source.code for run in runs], ["tre-rn-1g"])

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

    def test_authenticated_user_can_cancel_an_active_run(self):
        user = get_user_model().objects.create_user("operator", password="senha-segura")
        self.client.force_login(user)
        run = AutomationRun.objects.create(
            source=self.source,
            status=AutomationRun.Status.RUNNING,
        )

        response = self.client.post(f"/api/automation/runs/{run.pk}/cancel/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], AutomationRun.Status.CANCELLED)
        run.refresh_from_db()
        self.assertEqual(run.mensagem_info, "Coleta interrompida pelo usuário.")
        self.assertIsNotNone(run.finalizada_em)

    def test_cannot_cancel_a_completed_run(self):
        user = get_user_model().objects.create_user("operator", password="senha-segura")
        self.client.force_login(user)
        run = AutomationRun.objects.create(
            source=self.source,
            status=AutomationRun.Status.SUCCESS,
        )

        response = self.client.post(f"/api/automation/runs/{run.pk}/cancel/")

        self.assertEqual(response.status_code, 409)


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
            cycle_id=run.cycle_id,
        )

    def test_rerun_does_not_enqueue_the_next_source(self):
        run = AutomationRun.objects.create(
            source=self.first_degree,
            trigger=AutomationRun.Trigger.RERUN,
        )

        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch(
                "automation.services.pje.runner.salvar_expedientes",
                return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0},
            ),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)

        enqueue.assert_not_called()

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
            cycle_id=run.cycle_id,
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

    def test_chain_continues_from_second_degree_to_tre_rn(self):
        run = AutomationRun.objects.create(source=self.second_degree)
        tre_rn = AutomationSource.objects.get(code="tre-rn-1g")
        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        enqueue.assert_called_once_with(
            tre_rn,
            trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,

            scheduled_for=None,
            cycle_id=run.cycle_id,
        )

    def test_chain_continues_from_tre_rn_first_to_second_degree(self):
        tre_rn = AutomationSource.objects.get(code="tre-rn-1g")
        run = AutomationRun.objects.create(source=tre_rn)
        tre_rn_2g = AutomationSource.objects.get(code="tre-rn-2g")
        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        enqueue.assert_called_once_with(
            tre_rn_2g,
            trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,

            scheduled_for=None,
            cycle_id=run.cycle_id,
        )

    def test_chain_continues_from_tre_rn_second_degree_to_tse(self):
        tre_rn_2g = AutomationSource.objects.get(code="tre-rn-2g")
        run = AutomationRun.objects.create(source=tre_rn_2g)
        tse = AutomationSource.objects.get(code="tse-3g")
        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        enqueue.assert_called_once_with(
            tse,
            trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,

            scheduled_for=None,
            cycle_id=run.cycle_id,
        )

    def test_chain_continues_from_tse_to_trt21(self):
        tse = AutomationSource.objects.get(code="tse-3g")
        run = AutomationRun.objects.create(source=tse)
        trt21 = AutomationSource.objects.get(code="trt21")
        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        enqueue.assert_called_once_with(
            trt21,
            trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,

            scheduled_for=None,
            cycle_id=run.cycle_id,
        )

    def test_chain_skips_disabled_sources(self):
        self.second_degree.enabled = False
        self.second_degree.save(update_fields=("enabled",))
        run = AutomationRun.objects.create(source=self.first_degree)
        tre_rn = AutomationSource.objects.get(code="tre-rn-1g")
        with (
            patch("automation.services.pje.runner.abrir_pje", return_value=[]),
            patch("automation.services.pje.runner.salvar_expedientes", return_value={"criados": 0, "atualizados": 0, "resolvidos": 0, "total": 0}),
            patch("automation.services.pje.runner.enqueue_run") as enqueue,
        ):
            executar_coleta(run)
        enqueue.assert_called_once_with(
            tre_rn, trigger=AutomationRun.Trigger.MANUAL,
            requested_by=None,
            scheduled_for=None,
            cycle_id=run.cycle_id,
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
            cycle_id=run.cycle_id,
        )


class AutomationRunApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("operador")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_sources_include_the_enabled_tre_rn_first_degree_profile(self):
        response = self.client.get("/api/sources/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            {
                "code": "tre-rn-1g",
                "system": "PJe 1º Grau",
                "tribunal": "TRE-RN",
                "enabled": True,
            },
            response.data,
        )
        self.assertIn(
            {
                "code": "tse-3g",
                "system": "PJe 3º Grau",
                "tribunal": "TSE",
                "enabled": True,
            },
            response.data,
        )
        self.assertIn(
            {
                "code": "tre-rn-2g",
                "system": "PJe 2º Grau",
                "tribunal": "TRE-RN",
                "enabled": True,
            },
            response.data,
        )

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
        self.assertEqual(response.data["source"], "tre-rn-1g")
        self.assertTrue(response.data["cycle_id"])

    def test_rerun_enqueues_only_the_requested_source(self):
        source = AutomationSource.objects.get(code="pje2g-tjrn")

        response = self.client.post(
            "/api/automation/runs/",
            {"source": source.code, "rerun": True},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        run = AutomationRun.objects.get(pk=response.data["id"])
        self.assertEqual(run.source, source)
        self.assertEqual(run.trigger, AutomationRun.Trigger.RERUN)

    def test_rerun_rejects_a_disabled_source_instead_of_running_another(self):
        source = AutomationSource.objects.get(code="pje2g-tjrn")
        source.enabled = False
        source.save(update_fields=("enabled",))

        response = self.client.post(
            "/api/automation/runs/",
            {"source": source.code, "rerun": True},
            format="json",
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(AutomationRun.objects.exists())


class CollectionAuditApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("operator")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.source = AutomationSource.objects.get(code="pje-tjrn")
        self.previous_run = AutomationRun.objects.create(
            source=self.source,
            status=AutomationRun.Status.SUCCESS,
            iniciada_em=timezone.now() - timedelta(days=1),
            finalizada_em=timezone.now() - timedelta(days=1) + timedelta(minutes=1),
        )
        self.run = AutomationRun.objects.create(
            source=self.source,
            status=AutomationRun.Status.SUCCESS,
            iniciada_em=timezone.now() - timedelta(minutes=5),
            finalizada_em=timezone.now() - timedelta(minutes=3),
            expedientes_encontrados=3,
            expedientes_criados=1,
            expedientes_atualizados=2,
            expedientes_resolvidos=1,
        )

    def expediente(self, identifier, *, active=True, prazo="3 dias", subject="Assunto anterior"):
        process = Processo.objects.create(
            numero=f"0800000-00.2026.8.20.{identifier:04d}",
            tribunal="TJRN",
            assunto=subject,
        )
        return Expediente.objects.create(
            processo=process,
            source=self.source,
            identificador_pje=str(identifier),
            status_prazo_fatal="calculado",
            prazo_texto=prazo,
            ativo=active,
            arquivado_em=None if active else timezone.now(),
        )

    def test_discard_reverses_today_and_keeps_execution_audit(self):
        unrelated_orphan = Processo.objects.create(numero="0800000-00.2026.8.20.9999")
        updated = self.expediente(1, prazo="5 dias", subject="Assunto atual")
        ExpedienteEvent.objects.create(
            expediente=updated, run=self.previous_run,
            kind=ExpedienteEvent.Kind.NEW,
        ).created_at = timezone.now() - timedelta(days=1)
        ExpedienteEvent.objects.filter(expediente=updated, run=self.previous_run).update(
            created_at=timezone.now() - timedelta(days=1)
        )
        first_update = ExpedienteEvent.objects.create(
            expediente=updated, run=self.run,
            kind=ExpedienteEvent.Kind.UPDATED,
            changes={"prazo_texto": {"before": "3 dias", "after": "4 dias"}},
        )
        second_update = ExpedienteEvent.objects.create(
            expediente=updated, run=self.run,
            kind=ExpedienteEvent.Kind.UPDATED,
            changes={
                "prazo_texto": {"before": "4 dias", "after": "5 dias"},
                "processo.assunto": {"before": "Assunto anterior", "after": "Assunto atual"},
            },
        )
        resolved = self.expediente(2, active=False)
        resolution = ExpedienteEvent.objects.create(
            expediente=resolved, run=self.run,
            kind=ExpedienteEvent.Kind.RESOLVED,
            changes={"ativo": {"before": True, "after": False}},
        )
        new = self.expediente(3)
        created = ExpedienteEvent.objects.create(
            expediente=new, run=self.run, kind=ExpedienteEvent.Kind.NEW,
        )

        response = self.client.post("/api/automation/collections/today/discard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deleted_expedientes"], 1)
        self.assertEqual(response.data["reverted_updates"], 2)
        self.assertEqual(response.data["reactivated_expedientes"], 1)
        updated.refresh_from_db()
        updated.processo.refresh_from_db()
        resolved.refresh_from_db()
        self.assertEqual(updated.prazo_texto, "3 dias")
        self.assertEqual(updated.processo.assunto, "Assunto anterior")
        self.assertTrue(resolved.ativo)
        self.assertIsNone(resolved.arquivado_em)
        self.assertFalse(Expediente.objects.filter(pk=new.pk).exists())
        self.assertTrue(Processo.objects.filter(pk=unrelated_orphan.pk).exists())
        self.assertTrue(AutomationRun.objects.filter(pk=self.run.pk).exists())
        self.run.refresh_from_db()
        self.assertIsNotNone(self.run.descartada_em)
        self.assertEqual(response.data["cleared_runs"], 1)
        self.assertEqual(collection_pipeline_payload()["status"], "idle")
        history = self.client.get("/api/automation/history/")
        history_ids = [
            run["id"] for day in history.data["days"] for run in day["runs"]
        ]
        self.assertNotIn(self.run.id, history_ids)
        self.assertIn(self.previous_run.id, history_ids)
        self.assertTrue(ExpedienteEvent.objects.filter(expediente=updated, run=self.previous_run).exists())
        self.assertFalse(ExpedienteEvent.objects.filter(pk__in=[first_update.pk, second_update.pk, resolution.pk, created.pk]).exists())

        repeated = self.client.post("/api/automation/collections/today/discard/")
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.data["deleted_expedientes"], 0)
        self.assertEqual(repeated.data["cleared_runs"], 0)

    def test_discard_rejects_when_a_collection_is_active(self):
        AutomationRun.objects.create(source=AutomationSource.objects.get(code="pje2g-tjrn"))

        response = self.client.post("/api/automation/collections/today/discard/")

        self.assertEqual(response.status_code, 409)

    def test_collection_history_groups_runs_and_exposes_error_details(self):
        failed = AutomationRun.objects.create(
            source=AutomationSource.objects.get(code="pje2g-tjrn"),
            trigger=AutomationRun.Trigger.RERUN,
            status=AutomationRun.Status.FAILED,
            iniciada_em=timezone.now() - timedelta(minutes=2),
            finalizada_em=timezone.now() - timedelta(minutes=1),
            mensagem_erro="Falha de autenticação",
        )

        response = self.client.get("/api/automation/history/")

        self.assertEqual(response.status_code, 200)
        today = timezone.localdate(timezone=ZoneInfo("America/Fortaleza")).isoformat()
        day = next(item for item in response.data["days"] if item["date"] == today)
        payload = next(item for item in day["runs"] if item["id"] == failed.id)
        self.assertEqual(payload["source"]["code"], "pje2g-tjrn")
        self.assertEqual(payload["trigger"], AutomationRun.Trigger.RERUN)
        self.assertEqual(payload["status"], AutomationRun.Status.FAILED)
        self.assertEqual(payload["error"], "Falha de autenticação")
        self.assertEqual(payload["duration_seconds"], 60)

        expired = AutomationRun.objects.create(source=self.source, status=AutomationRun.Status.SUCCESS)
        AutomationRun.objects.filter(pk=expired.pk).update(
            criada_em=timezone.now() - timedelta(days=31),
            iniciada_em=timezone.now() - timedelta(days=31),
        )
        refreshed = self.client.get("/api/automation/history/")
        run_ids = [run["id"] for day in refreshed.data["days"] for run in day["runs"]]
        self.assertNotIn(expired.id, run_ids)


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
            message = tratar_quadro_avisos(page, SimpleNamespace(code="pje-tjrn"))

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
            return tratar_quadro_avisos(page, SimpleNamespace(code="pje-tjrn"))

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
            """previous => document.querySelectorAll("#avisosPannel_body > div").length < previous""",
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

    def test_tre_rn_first_degree_starts_from_the_stable_portal(self):
        profile = get_source_profile("tre-rn-1g")

        self.assertEqual(profile.url, TRE_RN_PORTAL_URL)
        self.assertEqual(profile.portal_flow, "tre-rn-1g")
        self.assertEqual(profile.portal_destination_host, "pje1g-rn.tse.jus.br")
        self.assertEqual(profile.notice_board_strategy, "tre-rn")
        self.assertEqual(profile.collector, "tjrn")
        self.assertTrue(profile.reconcile_missing)
        self.assertNotIn("state=", profile.url)

    def test_tre_rn_portal_opens_the_pje_zonas_link(self):
        page = Mock()
        first_degree_link = Mock()
        first_degree_link.count.return_value = 1
        pje_zonas_link = Mock()
        pje_zonas_link.count.return_value = 1
        pje_zonas_link.get_attribute.return_value = (
            "https://pje1g-rn.tse.jus.br/pje/login.seam?state=dinamico"
        )
        page.get_by_role.side_effect = [first_degree_link, pje_zonas_link]

        abrir_link_tre_rn_1g_pje(page, get_source_profile("tre-rn-1g"))

        page.get_by_role.assert_has_calls([
            call("link", name="PJe - 1º Grau", exact=True),
            call("link", name="Clique aqui para acessar o PJE-Zonas", exact=True),
        ])
        first_degree_link.click.assert_called_once_with()
        pje_zonas_link.evaluate.assert_called_once_with(
            "element => element.removeAttribute('target')"
        )
        pje_zonas_link.click.assert_called_once_with()
        self.assertEqual(page.wait_for_load_state.call_count, 2)

    def test_tre_rn_second_degree_starts_from_the_stable_portal(self):
        profile = get_source_profile("tre-rn-2g")

        self.assertEqual(profile.url, TRE_RN_PORTAL_URL)
        self.assertEqual(profile.portal_flow, "tre-rn-2g")
        self.assertEqual(profile.portal_destination_host, "pje.tre-rn.jus.br")
        self.assertEqual(profile.notice_board_strategy, "tre-rn")
        self.assertEqual(profile.collector, "tjrn")
        self.assertTrue(profile.reconcile_missing)
        self.assertNotIn("state=", profile.url)

    def test_tre_rn_second_degree_portal_opens_the_system_link(self):
        page = Mock()
        second_degree_link = Mock()
        second_degree_link.count.return_value = 1
        system_link = Mock()
        system_link.count.return_value = 1
        system_link.get_attribute.return_value = (
            "https://pje.tre-rn.jus.br/pje/login.seam?state=dinamico"
        )
        page.get_by_role.side_effect = [second_degree_link, system_link]

        abrir_link_tre_rn_2g_pje(page, get_source_profile("tre-rn-2g"))

        page.get_by_role.assert_has_calls([
            call("link", name="PJe - 2º Grau", exact=True),
            call("link", name="Acesso ao sistema", exact=True),
        ])
        second_degree_link.click.assert_called_once_with()
        system_link.evaluate.assert_called_once_with(
            "element => element.removeAttribute('target')"
        )
        system_link.click.assert_called_once_with()
        self.assertEqual(page.wait_for_load_state.call_count, 2)

    def test_tre_rn_portal_rejects_a_link_outside_the_expected_host(self):
        page = Mock()
        first_degree_link = Mock()
        first_degree_link.count.return_value = 1
        pje_zonas_link = Mock()
        pje_zonas_link.count.return_value = 1
        pje_zonas_link.get_attribute.return_value = "https://example.invalid/pje/login.seam"
        page.get_by_role.side_effect = [first_degree_link, pje_zonas_link]

        with self.assertRaisesMessage(RuntimeError, "não corresponde ao destino esperado"):
            abrir_link_tre_rn_1g_pje(page, get_source_profile("tre-rn-1g"))

        pje_zonas_link.click.assert_not_called()

    def test_tse_third_degree_starts_from_the_stable_portal(self):
        profile = get_source_profile("tse-3g")

        self.assertEqual(profile.url, TSE_PORTAL_URL)
        self.assertEqual(profile.portal_flow, "tse-3g")
        self.assertEqual(profile.portal_destination_host, "pje.tse.jus.br")
        self.assertEqual(profile.certificate_button_selector, "#kc-pje-office")
        self.assertEqual(profile.notice_board_strategy, "legacy")
        self.assertEqual(profile.collector, "tjrn")
        self.assertTrue(profile.reconcile_missing)
        self.assertNotIn("state=", profile.url)

    def test_tse_portal_opens_the_third_degree_link(self):
        page = Mock()
        third_degree_section = Mock()
        third_degree_section.count.return_value = 1
        third_degree_section.is_visible.return_value = False
        third_degree_trigger = Mock()
        third_degree_trigger.count.return_value = 1
        tse_link = Mock()
        tse_link.count.return_value = 1
        tse_link.get_attribute.return_value = "https://pje.tse.jus.br/pje/login.seam"
        page.locator.side_effect = [third_degree_section, third_degree_trigger]
        third_degree_section.get_by_role.return_value = tse_link

        abrir_link_tse_3g_pje(page, get_source_profile("tse-3g"))

        self.assertEqual(
            page.locator.call_args_list,
            [
                call("#collapse-pje-3o-grau"),
                call('[aria-controls="collapse-pje-3o-grau"]'),
            ],
        )
        third_degree_trigger.click.assert_called_once_with()
        third_degree_section.wait_for.assert_called_once_with(
            state="visible", timeout=15000
        )
        third_degree_section.get_by_role.assert_called_once_with(
            "link", name="Tribunal Superior Eleitoral", exact=True
        )
        tse_link.wait_for.assert_called_once_with(state="visible", timeout=15000)
        tse_link.evaluate.assert_called_once_with(
            "element => element.removeAttribute('target')"
        )
        tse_link.click.assert_called_once_with()
        page.wait_for_load_state.assert_called_once_with(
            "domcontentloaded", timeout=15000
        )

    def test_tse_portal_rejects_a_link_outside_the_expected_host(self):
        page = Mock()
        third_degree_section = Mock()
        third_degree_section.count.return_value = 1
        third_degree_section.is_visible.return_value = True
        third_degree_trigger = Mock()
        third_degree_trigger.count.return_value = 1
        tse_link = Mock()
        tse_link.count.return_value = 1
        tse_link.get_attribute.return_value = "https://example.invalid/pje/login.seam"
        page.locator.side_effect = [third_degree_section, third_degree_trigger]
        third_degree_section.get_by_role.return_value = tse_link

        with self.assertRaisesMessage(RuntimeError, "não corresponde ao destino esperado"):
            abrir_link_tse_3g_pje(page, get_source_profile("tse-3g"))

        third_degree_trigger.click.assert_not_called()
        tse_link.click.assert_not_called()

    def test_closes_the_certificate_expiry_warning_before_collecting(self):
        page = Mock()
        title = Mock()
        title.count.return_value = 1
        dialog = Mock()
        dialog.count.return_value = 1
        close = Mock()
        close.count.return_value = 1
        page.locator.return_value.count.return_value = 0
        page.get_by_text.return_value = title
        title.locator.return_value = dialog
        dialog.locator.return_value = close

        self.assertTrue(fechar_aviso_certificado_proximo_de_expirar(page))

        close.click.assert_called_once_with()
        dialog.wait_for.assert_called_once_with(state="hidden", timeout=10000)

    def test_closes_the_richfaces_certificate_expiry_warning_by_its_stable_id(self):
        page = Mock()
        dialog = Mock()
        dialog.count.return_value = 1
        dialog.is_visible.return_value = False
        close = Mock()
        close.count.return_value = 1
        close.is_visible.return_value = True
        page.locator.return_value = dialog
        dialog.locator.return_value = close

        self.assertTrue(fechar_aviso_certificado_proximo_de_expirar(page))

        page.locator.assert_called_once_with(
            "#popupAlertaCertificadoProximoDeExpirarContainer"
        )
        dialog.locator.assert_called_once_with("span.btn-fechar")
        close.click.assert_called_once_with()
        close.wait_for.assert_called_once_with(state="hidden", timeout=10000)
        page.get_by_text.assert_not_called()

    def test_closes_the_certificate_popup_before_processing_tre_rn_notices(self):
        page = Mock()
        source = SimpleNamespace(code="tre-rn-1g")
        board = Mock()
        board.count.return_value = 1
        page.locator.side_effect = lambda selector: (
            board if selector == "#avisosPannel" else Mock()
        )
        calls = Mock()

        with (
            patch(
                "automation.services.pje.browser.fechar_aviso_certificado_proximo_de_expirar",
                side_effect=[True, False],
            ) as close_popup,
            patch(
                "automation.services.pje.browser.tratar_quadro_avisos",
                return_value="aviso tratado",
            ) as treat_notices,
        ):
            calls.attach_mock(close_popup, "close_popup")
            calls.attach_mock(treat_notices, "treat_notices")
            message = esperar_destino_pos_login(page, source)

        self.assertEqual(message, "aviso tratado")
        self.assertEqual(
            calls.mock_calls,
            [
                call.close_popup(page),
                call.close_popup(page),
                call.treat_notices(page, source),
            ],
        )


    def test_tre_rn_notice_board_scrolls_then_opens_the_panel_without_touching_notices(self):
        page = Mock()
        source = SimpleNamespace(code="tre-rn-1g")
        panel = Mock()
        panel.count.return_value = 1
        panel_destination = Mock()
        page.locator.side_effect = lambda selector: {
            "input[type=submit][value=\"Painel do usuário\"]": panel,
            "#divResultadoMenuContexto": panel_destination,
        }.get(selector, Mock())

        with patch(
            "automation.services.pje.browser.aguardar_e_fechar_aviso_certificado_proximo_de_expirar",
            return_value=True,
        ) as close_late_popup:
            message = tratar_quadro_avisos(page, source)

        self.assertEqual(
            message, "Avisos institucionais TRE-RN ignorados; Painel do usuário aberto."
        )
        page.evaluate.assert_called_once_with("window.scrollTo(0, document.body.scrollHeight)")
        panel.scroll_into_view_if_needed.assert_called_once_with()
        panel.click.assert_called_once_with()
        panel_destination.wait_for.assert_called_once_with(state="visible", timeout=15000)
        close_late_popup.assert_called_once_with(page)
        page.get_by_text.assert_not_called()

    def test_tre_rn_notice_board_reports_a_missing_panel_button(self):
        page = Mock()
        source = SimpleNamespace(code="tre-rn-2g")
        page.locator.return_value.count.return_value = 0

        with self.assertRaisesMessage(
            RuntimeError, "Botão Painel do usuário TRE-RN não encontrado de forma única."
        ):
            tratar_quadro_avisos(page, source)

    def test_waits_for_and_closes_a_late_certificate_popup(self):
        page = Mock()
        close = Mock()
        page.locator.return_value = close

        with patch(
            "automation.services.pje.browser.fechar_aviso_certificado_proximo_de_expirar",
            return_value=True,
        ) as close_popup:
            self.assertTrue(aguardar_e_fechar_aviso_certificado_proximo_de_expirar(page))

        page.locator.assert_called_once_with(
            "#popupAlertaCertificadoProximoDeExpirarContainer span.btn-fechar"
        )
        close.wait_for.assert_called_once_with(state="visible", timeout=5000)
        close_popup.assert_called_once_with(page)

    def test_closes_a_late_popup_before_opening_the_pendencies_tree(self):
        page = Mock()
        panel = Mock()
        menu = Mock()
        aba = Mock()
        linha_n1 = Mock()
        linha_n2 = Mock()
        tree = Mock()
        for locator in (panel, menu, aba, linha_n1, linha_n2, tree):
            locator.count.return_value = 1
        page.locator.return_value = panel
        panel.locator.return_value = menu
        menu.locator.return_value.get_by_text.return_value.locator.return_value = aba
        aba.locator.return_value = linha_n1
        linha_n1.locator.return_value = linha_n2
        linha_n2.locator.return_value = tree
        calls = Mock()

        with patch(
            "automation.services.pje.browser.fechar_aviso_certificado_proximo_de_expirar",
            return_value=True,
        ) as close_popup:
            calls.attach_mock(close_popup, "close_popup")
            calls.attach_mock(aba.click, "open_tree")
            localizar_arvore_pendencias(page)

        self.assertEqual(
            calls.mock_calls,
            [call.close_popup(page), call.open_tree(timeout=1000)],
        )

    def test_retries_the_pendencies_tree_click_when_the_certificate_popup_appears_late(self):
        page = Mock()
        panel = Mock()
        menu = Mock()
        aba = Mock()
        linha_n1 = Mock()
        linha_n2 = Mock()
        tree = Mock()
        for locator in (panel, menu, aba, linha_n1, linha_n2, tree):
            locator.count.return_value = 1
        page.locator.return_value = panel
        panel.locator.return_value = menu
        menu.locator.return_value.get_by_text.return_value.locator.return_value = aba
        aba.locator.return_value = linha_n1
        linha_n1.locator.return_value = linha_n2
        linha_n2.locator.return_value = tree
        aba.click.side_effect = [PlaywrightTimeoutError("alerta bloqueou o clique"), None]
        calls = Mock()

        with patch(
            "automation.services.pje.browser.fechar_aviso_certificado_proximo_de_expirar",
            side_effect=[False, True],
        ) as close_popup:
            calls.attach_mock(close_popup, "close_popup")
            calls.attach_mock(aba.click, "open_tree")
            localizar_arvore_pendencias(page)

        self.assertEqual(
            calls.mock_calls,
            [
                call.close_popup(page),
                call.open_tree(timeout=1000),
                call.close_popup(page),
                call.open_tree(),
            ],
        )

    def test_closes_a_late_popup_before_each_pendencies_child_click(self):
        page = Mock()
        child_tabs = Mock()
        first_tab = Mock()
        second_tab = Mock()
        child_tabs.count.return_value = 2
        child_tabs.nth.side_effect = [first_tab, second_tab]

        with (
            patch(
                "automation.services.pje.browser.localizar_abas_filhas",
                return_value=child_tabs,
            ),
            patch(
                "automation.services.pje.browser.clicar_apos_dispensar_aviso_certificado"
            ) as click_after_closing,
            patch("automation.services.pje.browser.esperar_view_expedientes"),
            patch(
                "automation.services.pje.browser.salvar_html_renderizado",
                side_effect=[Path("first.html"), Path("second.html")],
            ),
        ):
            files = coletar_expedientes(page, "tre-rn-2g")

        self.assertEqual(files, [Path("first.html"), Path("second.html")])
        self.assertEqual(
            click_after_closing.call_args_list,
            [call(page, first_tab), call(page, second_tab)],
        )
        first_tab.click.assert_not_called()
        second_tab.click.assert_not_called()

    def test_zero_pendencies_without_a_link_produces_an_empty_collection(self):
        page = Mock()
        panel = Mock()
        menu = Mock()
        containers = Mock()
        label = Mock()
        link = Mock()
        empty_item = Mock()
        counter = Mock()
        panel.count.return_value = 1
        menu.count.return_value = 1
        label.count.return_value = 1
        link.count.return_value = 0
        empty_item.count.return_value = 1
        counter.count.return_value = 1
        counter.inner_text.return_value = "0"
        page.locator.return_value = panel
        panel.locator.return_value = menu
        menu.locator.return_value = containers
        containers.get_by_text.return_value = label
        label.locator.side_effect = [link, empty_item]
        empty_item.locator.return_value = counter

        self.assertEqual(coletar_expedientes(page, "tse-3g"), [])

        containers.get_by_text.assert_called_once_with(
            "Pendentes de ciência ou de resposta", exact=True
        )
        label.locator.assert_has_calls([
            call("xpath=ancestor::a[1]"),
            call(
                "xpath=ancestor::div["
                "contains(concat(' ', normalize-space(@class), ' '), "
                "' itemSemLink ')][1]"
            ),
        ])
        empty_item.locator.assert_called_once_with("span.pull-right")

    def test_ignores_absent_certificate_expiry_warning(self):
        page = Mock()
        page.locator.return_value.count.return_value = 0
        page.get_by_text.return_value.count.return_value = 0

        self.assertFalse(fechar_aviso_certificado_proximo_de_expirar(page))
        page.get_by_text.assert_called_once_with(
            "Certificado próximo de expirar", exact=True
        )

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
            "pje-tjrn", "pje2g-tjrn", "tre-rn-1g", "tre-rn-2g", "tse-3g", "trt21", "trt21-2g", "trf5-2g-tru",
            "varas-justica-comum", "jef-5-regiao", "trs-5-regiao", "tru-5-regiao",
        ))
        self.assertEqual(obter_url_pje("tre-rn-1g"), TRE_RN_PORTAL_URL)
        self.assertEqual(obter_url_pje("tre-rn-2g"), TRE_RN_PORTAL_URL)
        self.assertEqual(obter_url_pje("tse-3g"), TSE_PORTAL_URL)
        self.assertEqual(obter_url_pje("trt21"), "https://pje.trt21.jus.br/primeirograu/login.seam")
        self.assertEqual(obter_url_pje("trt21-2g"), "https://pje.trt21.jus.br/segundograu/login.seam")

    def test_trt21_uses_its_certificate_control(self):
        page = Mock()
        title = page.locator.return_value.get_by_text.return_value
        title.count.return_value = 1
        clicar_certificado(page, "trt21")
        page.locator.assert_called_once_with(".botao-certificado-titulo")
        title.click.assert_called_once_with()

    def test_tre_rn_uses_the_sso_certificate_input(self):
        page = Mock()
        certificate = page.locator.return_value
        certificate.count.return_value = 1

        clicar_certificado(page, "tre-rn-1g")

        certificate.wait_for.assert_called_once_with(
            state="visible", timeout=15000
        )
        page.locator.assert_called_once_with("#kc-pje-office")
        certificate.click.assert_called_once_with()

    def test_tse_uses_the_sso_certificate_input(self):
        page = Mock()
        certificate = page.locator.return_value
        certificate.count.return_value = 1

        clicar_certificado(page, "tse-3g")

        certificate.wait_for.assert_called_once_with(
            state="visible", timeout=15000
        )
        page.locator.assert_called_once_with("#kc-pje-office")
        certificate.click.assert_called_once_with()

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


class CollectionPipelinePayloadTests(TestCase):
    def setUp(self):
        self.first = AutomationSource.objects.get(code="pje-tjrn")
        self.second = AutomationSource.objects.get(code="pje2g-tjrn")

    def test_exposes_official_order_and_real_cycle_states(self):
        first_run = AutomationRun.objects.create(
            source=self.first, status=AutomationRun.Status.SUCCESS,
            finalizada_em=timezone.now(),
        )
        AutomationRun.objects.create(
            source=self.second, status=AutomationRun.Status.RUNNING,
            iniciada_em=timezone.now(), cycle_id=first_run.cycle_id,
        )
        AutomationSource.objects.filter(code="tse-3g").update(enabled=False)

        payload = collection_pipeline_payload()

        self.assertEqual([step["code"] for step in payload["steps"]], list(PJE_SOURCE_ORDER))
        self.assertEqual(payload["cycle_id"], str(first_run.cycle_id))
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["current_step"], "pje2g-tjrn")
        self.assertEqual(payload["steps"][0]["status"], "success")
        self.assertEqual(payload["steps"][1]["status"], "running")
        self.assertEqual(payload["steps"][2]["status"], "pending")
        self.assertEqual(payload["steps"][4]["status"], "disabled")

    def test_marks_unreached_steps_skipped_after_cancellation(self):
        AutomationRun.objects.create(
            source=self.second, status=AutomationRun.Status.CANCELLED,
            finalizada_em=timezone.now(),
        )

        payload = collection_pipeline_payload()

        self.assertEqual(payload["status"], "cancelled")
        self.assertFalse(payload["active"])
        self.assertEqual(payload["steps"][0]["status"], "skipped")
        self.assertEqual(payload["steps"][1]["status"], "cancelled")
        self.assertEqual(payload["steps"][2]["status"], "skipped")

    def test_rerun_replaces_only_the_requested_source_state(self):
        previous = AutomationRun.objects.create(
            source=self.first,
            status=AutomationRun.Status.SUCCESS,
            finalizada_em=timezone.now(),
        )
        AutomationRun.objects.create(
            source=self.second,
            status=AutomationRun.Status.FAILED,
            mensagem_erro="Falha anterior",
            finalizada_em=timezone.now(),
            cycle_id=previous.cycle_id,
        )
        rerun = AutomationRun.objects.create(
            source=self.first,
            trigger=AutomationRun.Trigger.RERUN,
            status=AutomationRun.Status.RUNNING,
            iniciada_em=timezone.now(),
        )

        payload = collection_pipeline_payload()

        self.assertEqual(payload["cycle_id"], str(rerun.cycle_id))
        self.assertEqual(payload["steps"][0]["status"], "running")
        self.assertEqual(payload["steps"][0]["run_id"], rerun.id)
        self.assertEqual(payload["steps"][1]["status"], "failed")
        self.assertEqual(payload["steps"][1]["error"], "Falha anterior")
