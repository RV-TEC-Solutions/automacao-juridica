from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch
from rest_framework.test import APIClient
from rest_framework.response import Response

from automation.models import AutomationRun, AutomationSource, DjenCommunication
from automation.services.pje.persistence import salvar_expedientes
from .models import Expediente, ExpedienteEvent


def payload(identifier="100", **overrides):
    data = {
        "numero_processo": "0800000-00.2026.8.20.0001", "tribunal": "TJRN",
        "classe": "Procedimento", "assunto": "Obrigação de fazer",
        "partes_texto": "PARTE A X PARTE B", "unidade_judiciaria": "1ª Vara",
        "identificador_pje": identifier, "tipo_pendencia": "ciencia",
        "acao_pje": "tomar_ciencia", "caixa": "Pendentes de ciência",
        "destinatario": "Parte A", "tipo_documento": "Intimação",
        "meio_comunicacao": "Diário eletrônico", "data_expedicao": "2026-08-25T08:00:00",
        "prazo_texto": "3 dias", "status_prazo_fatal": "calculado",
        "prazo_fatal": (timezone.now() + timedelta(days=2)).isoformat(), "ciencia_texto": "",
    }
    data.update(overrides)
    return data


class PersistenceTests(TestCase):
    def setUp(self):
        self.source = AutomationSource.objects.get(code="pje-tjrn")

    def test_new_unchanged_changed_and_resolved_lifecycle(self):
        original = payload()
        first = salvar_expedientes([original], source=self.source)
        self.assertEqual(first["criados"], 1)
        self.assertEqual(ExpedienteEvent.objects.count(), 1)

        unchanged = salvar_expedientes([original], source=self.source)
        self.assertEqual(unchanged["atualizados"], 0)
        self.assertEqual(ExpedienteEvent.objects.count(), 1)

        changed = salvar_expedientes([{**original, "prazo_texto": "5 dias"}], source=self.source)
        self.assertEqual(changed["atualizados"], 1)
        self.assertIn("prazo_texto", ExpedienteEvent.objects.first().changes)

        resolved = salvar_expedientes([], source=self.source)
        self.assertEqual(resolved["resolvidos"], 1)
        self.assertFalse(Expediente.objects.get().ativo)
        self.assertEqual(ExpedienteEvent.objects.first().kind, "resolved")

    def test_repeated_collection_never_duplicates_an_expediente(self):
        original = payload()

        first = salvar_expedientes([original], source=self.source)
        repeated = salvar_expedientes([original, original], source=self.source)

        self.assertEqual(first["criados"], 1)
        self.assertEqual(repeated["criados"], 0)
        self.assertEqual(repeated["atualizados"], 0)
        self.assertEqual(Expediente.objects.filter(source=self.source).count(), 1)
        self.assertEqual(ExpedienteEvent.objects.filter(kind=ExpedienteEvent.Kind.NEW).count(), 1)

    def test_partial_trt21_capture_never_resolves_absent_expedientes(self):
        trt21 = AutomationSource.objects.get(code="trt21")
        original = payload(identifier="trt-1", numero_processo="0000001-00.2026.5.21.0001", tribunal="TRT21")
        salvar_expedientes([original], source=trt21, reconcile_missing=False)

        result = salvar_expedientes([], source=trt21, reconcile_missing=False)

        self.assertEqual(result["resolvidos"], 0)
        self.assertTrue(Expediente.objects.get(source=trt21).ativo)


class ApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("operador", password="senha-segura")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.source = AutomationSource.objects.get(code="pje-tjrn")
        salvar_expedientes([payload()], source=self.source)

    def test_dashboard_and_mark_read(self):
        dashboard = self.client.get("/api/dashboard/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["today"]["unread"], 1)
        expediente = Expediente.objects.get()
        response = self.client.post(f"/api/expedientes/{expediente.pk}/read/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(expediente.events.filter(read_at__isnull=True).exists())

    def test_dashboard_allows_discarding_a_failed_run_without_events(self):
        ExpedienteEvent.objects.all().delete()
        AutomationRun.objects.create(
            source=self.source,
            status=AutomationRun.Status.FAILED,
            iniciada_em=timezone.now(),
            finalizada_em=timezone.now(),
            mensagem_erro="Falha antes de encontrar expedientes",
        )

        dashboard = self.client.get("/api/dashboard/")

        self.assertGreater(dashboard.data["today"]["discardable"], 0)

    def test_time_saved_accumulates_successful_source_days_without_rerun_inflation(self):
        now = timezone.now()
        local_yesterday = timezone.localdate(now, timezone=ZoneInfo("America/Fortaleza")) - timedelta(days=1)
        yesterday = datetime.combine(local_yesterday, datetime.min.time(), tzinfo=ZoneInfo("America/Fortaleza")) + timedelta(hours=12)
        portal = AutomationSource.objects.get(code="tre-rn-1g")
        djen = AutomationSource.objects.get(code="djen")
        for source, finished_at, found, created, captures in (
            (self.source, now, 2, 0, 2),
            (self.source, now, 4, 0, 3),
            (portal, yesterday, 2, 0, 1),
            (djen, now, 3, 3, 0),
            (djen, now, 1, 1, 0),
        ):
            AutomationRun.objects.create(
                source=source, status=AutomationRun.Status.SUCCESS,
                iniciada_em=finished_at - timedelta(minutes=1), finalizada_em=finished_at,
                expedientes_encontrados=found, expedientes_criados=created,
                capturas_html=captures,
            )
        AutomationRun.objects.create(
            source=portal, status=AutomationRun.Status.FAILED,
            finalizada_em=now, expedientes_encontrados=99,
        )
        AutomationRun.objects.create(
            source=portal, status=AutomationRun.Status.SUCCESS,
            finalizada_em=now, expedientes_encontrados=99, descartada_em=now,
        )

        saved = self.client.get("/api/statistics/").data["time_saved"]

        self.assertEqual(saved, {
            "total_seconds": 2550,
            "today_seconds": 1875,
            "source_days": 3,
            "items": 10,
            "tabs": 4,
        })

    def test_time_saved_caps_each_day_at_four_hours(self):
        local_today = timezone.localdate(timezone=ZoneInfo("America/Fortaleza"))
        for day, found in ((local_today, 300), (local_today - timedelta(days=1), 4)):
            finished_at = datetime.combine(day, datetime.min.time(), tzinfo=ZoneInfo("America/Fortaleza")) + timedelta(hours=12)
            AutomationRun.objects.create(
                source=self.source, status=AutomationRun.Status.SUCCESS,
                iniciada_em=finished_at - timedelta(minutes=1), finalizada_em=finished_at,
                expedientes_encontrados=found,
            )

        saved = self.client.get("/api/statistics/").data["time_saved"]

        self.assertEqual(saved["today_seconds"], 4 * 60 * 60)
        self.assertEqual(saved["total_seconds"], 4 * 60 * 60 + 360 + 4 * 75)

    def test_search_filter_and_pagination_contract(self):
        response = self.client.get("/api/expedientes/?q=PARTE+A&read=unread")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

    def test_event_kind_and_date_must_match_the_same_event(self):
        local_tz = ZoneInfo("America/Fortaleza")
        today = timezone.localdate(timezone=local_tz)
        expediente = Expediente.objects.get()
        created = expediente.events.get(kind=ExpedienteEvent.Kind.NEW)
        created.created_at = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=local_tz)
        created.save(update_fields=("created_at",))
        ExpedienteEvent.objects.create(expediente=expediente, kind=ExpedienteEvent.Kind.UPDATED)

        response = self.client.get(f"/api/expedientes/?event_kind=new&date_from={today}&date_to={today}")

        self.assertEqual(response.data["count"], 0)

    def test_pdf_export_uses_all_filtered_results_and_consolidates_events(self):
        second = payload(identifier="200", numero_processo="0800001-00.2026.8.20.0001", assunto="Outro assunto")
        salvar_expedientes([second], source=self.source)
        expediente = Expediente.objects.get(identificador_pje="100")
        ExpedienteEvent.objects.create(expediente=expediente, kind=ExpedienteEvent.Kind.UPDATED,
                                       changes={"prazo_texto": {"before": "3 dias", "after": "5 dias"}})
        today = timezone.localdate(timezone=ZoneInfo("America/Fortaleza"))

        with patch("expedientes.reports.pdf_response") as create_pdf:
            create_pdf.side_effect = lambda **kwargs: Response({"count": kwargs["count"], "records": list(kwargs["records"])})
            response = self.client.get(f"/api/expedientes/export.pdf/?scope=list&q=PARTE+A&date_from={today}&date_to={today}&page=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["records"]), 2)
        first = next(fields for title, fields in response.data["records"] if "0800000-" in title)
        self.assertTrue(any(label.startswith("Prazo original · ") and "3 dias → 5 dias" in value for label, value in first))

    def test_pdf_export_rejects_bad_dates_and_history_outside_30_days(self):
        self.assertEqual(self.client.get("/api/expedientes/export.pdf/?date_from=invalid").status_code, 400)
        old = timezone.localdate(timezone=ZoneInfo("America/Fortaleza")) - timedelta(days=30)
        self.assertEqual(self.client.get(f"/api/expedientes/export.pdf/?scope=history&date_from={old}").status_code, 400)

    def test_pdf_export_requires_authentication_and_generates_pdf(self):
        self.assertIn(APIClient().get("/api/expedientes/export.pdf/").status_code, (401, 403))
        response = self.client.get("/api/expedientes/export.pdf/?scope=overview&metric=new")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("expedientes-novos-", response["Content-Disposition"])
        self.assertIn("-sintetico.pdf", response["Content-Disposition"])
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))

    def test_pdf_list_without_dates_matches_unfiltered_list_in_both_formats(self):
        event = Expediente.objects.get().events.get(kind=ExpedienteEvent.Kind.NEW)
        event.created_at = timezone.now() - timedelta(days=2)
        event.save(update_fields=("created_at",))

        self.assertEqual(self.client.get("/api/expedientes/").data["count"], 1)
        for mode in ("sintetico", "analitico"):
            response = self.client.get(f"/api/expedientes/export.pdf/?scope=list&mode={mode}")
            self.assertEqual(response.status_code, 200, getattr(response, "data", None))
            self.assertIn(f"expedientes-consulta-todos-{mode}.pdf", response["Content-Disposition"])
            self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))

    def test_pdf_history_uses_new_events_in_local_day_only(self):
        today = timezone.localdate(timezone=ZoneInfo("America/Fortaleza"))
        prior_day = today - timedelta(days=1)
        second = payload(identifier="200", numero_processo="0800001-00.2026.8.20.0001")
        salvar_expedientes([second], source=self.source)
        other = Expediente.objects.get(identificador_pje="200")
        original = other.events.get(kind="new")
        original.created_at = datetime.combine(prior_day, datetime.max.time(), tzinfo=ZoneInfo("America/Fortaleza"))
        original.save(update_fields=("created_at",))
        ExpedienteEvent.objects.create(expediente=other, kind="updated")

        with patch("expedientes.reports.pdf_response") as create_pdf:
            create_pdf.side_effect = lambda **kwargs: Response({"records": list(kwargs["records"])})
            response = self.client.get(f"/api/expedientes/export.pdf/?scope=history&date_from={today}&date_to={today}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["records"]), 1)
        self.assertIn("0800000-", response.data["records"][0][0])

    def test_djen_today_and_history_use_collection_date(self):
        today = timezone.localdate(timezone=ZoneInfo("America/Fortaleza"))
        yesterday = today - timedelta(days=1)
        publication = DjenCommunication.objects.create(
            source=AutomationSource.objects.get(code="djen"),
            processo=Expediente.objects.get().processo,
            numero_comunicacao=123456,
            data_disponibilizacao=yesterday,
            tribunal="TJRN",
        )
        today_list = self.client.get(f"/api/djen/communications/?collected_from={today}&collected_to={today}")
        history = self.client.get("/api/djen/history/")

        self.assertEqual(today_list.data["count"], 1)
        self.assertEqual(today_list.data["results"][0]["id"], publication.id)
        self.assertEqual(history.data["days"][0]["date"], today.isoformat())
        self.assertEqual(history.data["days"][0]["items"][0]["id"], publication.id)

    def test_statistics_validates_period(self):
        self.assertEqual(self.client.get("/api/statistics/?period=10").status_code, 400)
        self.assertEqual(self.client.get("/api/statistics/?period=7").status_code, 200)

    def test_next_week_deadline_filter_matches_dashboard_metric(self):
        dashboard = self.client.get("/api/dashboard/")
        response = self.client.get("/api/expedientes/?deadline=next_week")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], dashboard.data["today"]["next_week"])
        self.assertEqual(response.data["count"], 1)
    def test_history_returns_paginated_new_events(self):
        local_tz = ZoneInfo("America/Fortaleza")
        today = timezone.localdate(timezone=local_tz)
        expediente = Expediente.objects.get()
        created = expediente.events.get(kind=ExpedienteEvent.Kind.NEW)
        created.created_at = datetime.combine(today - timedelta(days=2), datetime.min.time(), tzinfo=local_tz) + timedelta(hours=9)
        created.save(update_fields=("created_at",))
        updated = ExpedienteEvent.objects.create(expediente=expediente, kind=ExpedienteEvent.Kind.UPDATED)
        updated.created_at = datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=local_tz) + timedelta(hours=9)
        updated.save(update_fields=("created_at",))

        response = self.client.get("/api/history/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["page"], 1)
        self.assertEqual(response.data["page_size"], 50)
        self.assertEqual(len(response.data["days"]), 1)
        self.assertEqual(response.data["days"][0]["date"], (today - timedelta(days=2)).isoformat())
        self.assertEqual(response.data["days"][0]["new_count"], 1)
        self.assertEqual(response.data["days"][0]["items"][0]["event"]["kind"], "new")
