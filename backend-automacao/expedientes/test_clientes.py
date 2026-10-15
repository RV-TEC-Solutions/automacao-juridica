from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIClient

from automation.models import AutomationRun, AutomationSource
from automation.services.pje.persistence import salvar_expedientes
from .models import Cliente, Expediente, ExpedienteEvent
from .tests import payload


class ClienteTests(TestCase):
    def setUp(self):
        self.source = AutomationSource.objects.get(code="pje-tjrn")
        self.deadline = (timezone.now() + timedelta(days=2)).isoformat()
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user("clientes"))

    def collect(self, *names, run=None):
        return salvar_expedientes([
            payload(identifier=str(i), destinatario=name, prazo_fatal=self.deadline) for i, name in enumerate(names)
        ], source=self.source, run=run)

    def test_normalization_preserves_original_and_keeps_abbreviations_separate(self):
        self.collect("  Caixa   Econômica Federal ", "CAIXA ECONOMICA FEDERAL", "CAIXA", " \n ")
        self.assertEqual(Cliente.objects.count(), 2)
        first, second, short, empty = Expediente.objects.order_by("identificador_pje")
        self.assertEqual(first.cliente_id, second.cliente_id)
        self.assertNotEqual(first.cliente_id, short.cliente_id)
        self.assertIsNone(empty.cliente_id)
        self.assertEqual(first.destinatario, "  Caixa   Econômica Federal ")
        self.assertEqual(first.cliente.nome, "Caixa Econômica Federal")

    def test_repeated_collection_and_empty_recipient_update(self):
        self.collect("CAIXA")
        events = ExpedienteEvent.objects.count()
        self.collect("CAIXA")
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(ExpedienteEvent.objects.count(), events)
        self.collect("")
        self.assertIsNone(Expediente.objects.get().cliente_id)
        self.assertEqual(Cliente.objects.count(), 1)

    def test_backfill_includes_resolved_and_does_not_create_events(self):
        self.collect("Caixa Econômica Federal", "CAIXA ECONOMICA FEDERAL", "")
        Expediente.objects.update(cliente=None, ativo=False)
        Cliente.objects.all().delete()
        events = ExpedienteEvent.objects.count()
        migration = import_module("expedientes.migrations.0007_popular_clientes")
        editor = SimpleNamespace(connection=connection)
        migration.popular_clientes(apps, editor)
        migration.popular_clientes(apps, editor)
        self.assertEqual(Cliente.objects.count(), 1)
        self.assertEqual(Expediente.objects.filter(cliente__isnull=False).count(), 2)
        self.assertEqual(ExpedienteEvent.objects.count(), events)

    def test_discard_restores_recipient_and_keeps_catalog(self):
        self.collect("CAIXA")
        run = AutomationRun.objects.create(source=self.source, status="success", iniciada_em=timezone.now())
        self.collect("Outro cliente", run=run)
        response = self.client.post("/api/automation/collections/today/discard/")
        self.assertEqual(response.status_code, 200)
        expediente = Expediente.objects.get()
        self.assertEqual(expediente.destinatario, "CAIXA")
        self.assertEqual(expediente.cliente.nome, "CAIXA")
        self.assertEqual(Cliente.objects.count(), 2)

    def test_discard_legacy_event_derives_missing_client(self):
        self.collect("Outro cliente")
        run = AutomationRun.objects.create(source=self.source, status="success", iniciada_em=timezone.now())
        ExpedienteEvent.objects.create(expediente=Expediente.objects.get(), run=run, kind="updated",
            changes={"destinatario": {"before": "Cliente antigo", "after": "Outro cliente"}})
        self.assertEqual(self.client.post("/api/automation/collections/today/discard/").status_code, 200)
        self.assertEqual(Expediente.objects.get().cliente.nome, "Cliente antigo")

    def test_catalog_is_authenticated_sorted_and_retains_resolved_clients(self):
        self.collect("Zeta", "Álfa", "CAIXA")
        self.collect()
        response = self.client.get("/api/expedientes/clientes/")
        self.assertEqual([row["nome"] for row in response.data], ["Álfa", "CAIXA", "Zeta"])
        self.assertEqual(set(response.data[0]), {"id", "nome"})
        self.assertIn(APIClient().get("/api/expedientes/clientes/").status_code, (401, 403))

    def test_multi_filter_combines_sources_deadlines_and_pagination(self):
        self.collect("CAIXA", "Outro", "Terceiro")
        caixa = Cliente.objects.get(nome="CAIXA").pk
        other = Cliente.objects.get(nome="Outro").pk
        query = f"client={caixa}&client={other}"
        self.assertEqual(self.client.get(f"/api/expedientes/?{query}").data["count"], 2)
        self.assertEqual(self.client.get(f"/api/expedientes/?client={caixa}").data["count"], 1)
        self.assertEqual(self.client.get("/api/expedientes/?client=").data["count"], 3)
        limit = (timezone.now() + timedelta(days=3)).date().isoformat()
        response = self.client.get(f"/api/expedientes/?{query}&source=pje-tjrn&deadline_to={limit}&page_size=1")
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(self.client.get(response.data["next"]).data["count"], 2)
        self.assertEqual(self.client.get(f"/api/expedientes/?{query}&source=tre-rn-1g").data["count"], 0)
        for value in ("bad", "-1", "999999999999999999999999"):
            self.assertEqual(self.client.get(f"/api/expedientes/?client={value}").status_code, 400)

    def test_pdf_uses_selected_clients_and_names(self):
        self.collect("CAIXA", "Outro", "Terceiro")
        ids = list(Cliente.objects.exclude(nome="Terceiro").values_list("id", flat=True))
        with patch("expedientes.reports.pdf_response", return_value=Response({})) as pdf:
            response = self.client.get(f"/api/expedientes/export.pdf/?scope=list&client={ids[0]}&client={ids[1]}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(pdf.call_args.kwargs["count"], 2)
        self.assertIn("clientes: CAIXA, Outro", pdf.call_args.kwargs["subtitle"])
