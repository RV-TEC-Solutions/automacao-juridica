from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from zoneinfo import ZoneInfo
from rest_framework.test import APIClient

from automation.models import AutomationSource
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

    def test_search_filter_and_pagination_contract(self):
        response = self.client.get("/api/expedientes/?q=PARTE+A&read=unread")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)

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
