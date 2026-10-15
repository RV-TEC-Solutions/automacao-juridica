from datetime import datetime
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIClient

from expedientes.clientes import cliente_do_destinatario
from expedientes.models import Cliente
from .models import AutomationSource, DjenCommunication, DjenRecipient
from .services.djen.persistence import save_communications
from .test_djen import record


class DjenFilterTests(TestCase):
    def setUp(self):
        self.source = AutomationSource.objects.get(code="djen")
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user("djen-filtros"))
        self.first = self.save(1, ["Caixa Econômica Federal", "Outra parte"], "TJRN", "Intimação")
        self.second = self.save(2, ["CAIXA ECONOMICA FEDERAL"], "TRF5", "Citação")
        self.third = self.save(3, ["Terceiro"], "TRF5", "Intimação")
        self.caixa = Cliente.objects.get(chave_normalizada="caixa economica federal")

    def save(self, number, recipients, tribunal="TRF5", kind="Intimação"):
        data = record(number)
        data.update(siglaTribunal=tribunal, tipoComunicacao=kind, destinatarios=[{"nome": name, "polo": "A"} for name in recipients])
        save_communications([data], source=self.source)
        return DjenCommunication.objects.get(numero_comunicacao=number)

    def test_catalog_is_authenticated_and_uses_djen_recipients(self):
        cliente_do_destinatario("Cliente apenas do PJe")
        response = self.client.get("/api/djen/filters/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tribunais"], ["TJRN", "TRF5"])
        self.assertEqual(response.data["tipos_comunicacao"], ["Citação", "Intimação"])
        self.assertEqual(len(response.data["clientes"]), 3)
        self.assertIn(APIClient().get("/api/djen/filters/").status_code, (401, 403))

    def test_multiple_clients_and_tribunals_intersect_without_duplicate_publications(self):
        other = Cliente.objects.get(nome="Outra parte")
        url = f"/api/djen/communications/?client={self.caixa.pk}&client={other.pk}&tribunal=TJRN&tribunal=TRF5"
        response = self.client.get(url)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(self.client.get(url + "&tipo_comunicacao=Citação").data["count"], 1)
        self.assertEqual(self.client.get(url + "&q=Intimação").data["count"], 2)
        self.assertEqual(self.client.get("/api/djen/communications/?client=&tribunal=").data["count"], 3)

    def test_uf_pairs_publications_with_state_and_federal_origin(self):
        def publication(number, tribunal, process):
            data = record(number)
            data.update(siglaTribunal=tribunal, numero_processo=process)
            save_communications([data], source=self.source)
            return DjenCommunication.objects.get(numero_comunicacao=number).pk

        sp = [publication(10, "TJSP", "1000001-00.2026.8.26.0100"),
              publication(11, "TRF3", "1000002-00.2026.4.03.6100"),
              publication(12, "TRF3", "10000030020264036301"),
              publication(13, "TRT15", "1000004-00.2026.5.15.0001")]
        ms = publication(14, "TRF3", "1000005-00.2026.4.03.6000")
        df = publication(15, "TJDFT", "1000006-00.2026.8.07.0001")
        publication(16, "TRF3", "1000007-00.2026.4.03.0000")
        publication(17, "STJ", "sem-numero-cnj")
        for query, expected in (("uf=SP", sp), ("uf=sp", sp), ("uf=MS", [ms]),
                                ("uf=DF", [df]), ("uf=SP&uf=MS", sp + [ms]),
                                ("uf=SP&tribunal=TRF3", sp[1:3])):
            with self.subTest(query=query):
                response = self.client.get("/api/djen/communications/?" + query)
                self.assertEqual(response.status_code, 200)
                self.assertCountEqual([item["id"] for item in response.data["results"]], expected)
        # All existing records originate in RN; the configured OAB is also RN,
        # but must not make any of the SP/MS/DF records match RN.
        self.assertEqual(self.client.get("/api/djen/communications/?uf=RN").data["count"], 3)
        with patch("automation.reports.pdf_response", return_value=Response({})) as pdf:
            self.assertEqual(self.client.get("/api/djen/communications/export.pdf/?uf=SP").status_code, 200)
            self.assertEqual(pdf.call_args.kwargs["count"], len(sp))
            self.assertIn("UFs: SP", pdf.call_args.kwargs["subtitle"])

    def test_read_states_and_publication_dates(self):
        from django.utils import timezone
        DjenCommunication.objects.filter(pk=self.first.pk).update(read_at=timezone.now())
        self.assertEqual(self.client.get("/api/djen/communications/?read=read").data["count"], 1)
        self.assertEqual(self.client.get("/api/djen/communications/?read=unread").data["count"], 2)
        self.assertEqual(self.client.get("/api/djen/communications/?date_from=2026-10-01&date_to=2026-10-01").data["count"], 3)
        self.assertEqual(self.client.get("/api/djen/communications/?date_from=2026-10-02").data["count"], 0)

    def test_collection_dates_use_local_whole_days_and_pagination_keeps_count(self):
        tz = ZoneInfo("America/Fortaleza")
        DjenCommunication.objects.filter(pk=self.first.pk).update(collected_at=datetime(2026, 10, 1, 23, 59, 59, tzinfo=tz))
        DjenCommunication.objects.exclude(pk=self.first.pk).update(collected_at=datetime(2026, 10, 2, tzinfo=tz))
        response = self.client.get("/api/djen/communications/?collected_from=2026-10-01&collected_to=2026-10-01")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.first.pk)
        for i in range(4, 25):
            self.save(i, ["Caixa Econômica Federal"])
        response = self.client.get(f"/api/djen/communications/?client={self.caixa.pk}&page=2")
        self.assertEqual(response.data["count"], 23)
        self.assertEqual(len(response.data["results"]), 3)

    def test_invalid_dates_ids_and_read_state_return_400_for_list_and_pdf(self):
        for query in ("uf=XX", "uf=SP&uf=XX", "client=bad", "client=-1", "client=999999999999999999999999", "read=bad",
                      "date_from=invalid", "date_from=2026-10-03&date_to=2026-10-01",
                      "collected_from=2026-10-03&collected_to=2026-10-01", "collected_to=9999-12-31"):
            for endpoint in ("", "export.pdf/"):
                with self.subTest(query=query, endpoint=endpoint):
                    self.assertEqual(self.client.get(f"/api/djen/communications/{endpoint}?{query}").status_code, 400)

    def test_pdf_matches_all_filtered_results_and_includes_filter_labels(self):
        with patch("automation.reports.pdf_response", return_value=Response({})) as pdf:
            response = self.client.get(f"/api/djen/communications/export.pdf/?client={self.caixa.pk}&tribunal=TJRN&tribunal=TRF5&ordering=publication&page=2")
            records = list(pdf.call_args.kwargs["records"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(pdf.call_args.kwargs["count"], 2)
        self.assertEqual(len(records), 2)
        self.assertIn("clientes: Caixa Econômica Federal", pdf.call_args.kwargs["subtitle"])
        self.assertIn("tribunais: TJRN, TRF5", pdf.call_args.kwargs["subtitle"])
        self.assertEqual(self.client.get("/api/djen/communications/export.pdf/?tribunal=INEXISTENTE").status_code, 404)

    def test_recipient_only_changes_refresh_clients_and_preserve_read_state(self):
        from django.utils import timezone
        self.first.read_at = timezone.now()
        self.first.save(update_fields=("read_at",))
        result = self.save(1, ["Novo cliente"])
        self.assertIsNotNone(result.read_at)
        self.assertEqual(result.recipients.get().cliente.nome, "Novo cliente")
        self.assertEqual(self.client.get(f"/api/djen/communications/?client={self.caixa.pk}").data["count"], 1)
        old = result.updated_at
        self.save(1, ["Novo cliente"])
        result.refresh_from_db()
        self.assertEqual(result.updated_at, old)

    def test_backfill_is_idempotent_handles_long_and_empty_names(self):
        self.save(4, ["Nome " + "x" * 400, " \n "])
        DjenRecipient.objects.update(cliente=None)
        migration = import_module("automation.migrations.0016_popular_clientes_djen")
        editor = SimpleNamespace(connection=connection)
        migration.popular_clientes(apps, editor)
        count = Cliente.objects.count()
        migration.popular_clientes(apps, editor)
        self.assertEqual(Cliente.objects.count(), count)
        self.assertIsNone(DjenRecipient.objects.get(name=" \n ").cliente_id)
        self.assertEqual(self.first.recipients.first().cliente_id, self.caixa.pk)
