from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.test import APIClient

from expedientes.models import Processo
from .models import AutomationSource, DjenAttorney, DjenCommunication, DjenRecipient


LOCAL_TZ = ZoneInfo("America/Fortaleza")


class PublicationReportTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("relatorios", password="senha-segura")
        self.client = APIClient()
        self.client.force_authenticate(user)
        source = AutomationSource.objects.get(code="djen")
        process = Processo.objects.create(numero="0800000-00.2026.8.20.0001")
        self.publication = DjenCommunication.objects.create(
            source=source, processo=process, numero_comunicacao=123,
            data_disponibilizacao=timezone.localdate(timezone=LOCAL_TZ),
            tribunal="TJRN", texto="Publicação com acentuação: ciência e intimação.",
            orgao="1ª Vara", link_inteiro_teor="https://example.com/documento",
        )
        DjenRecipient.objects.create(communication=self.publication, name="Maria", pole="Autora")
        DjenAttorney.objects.create(communication=self.publication, name="Ana", oab_number="123", oab_state="RN")

    def test_export_respects_collection_date_and_search_not_pagination(self):
        today = timezone.localdate(timezone=LOCAL_TZ)
        with patch("automation.reports.pdf_response") as create_pdf:
            create_pdf.side_effect = lambda **kwargs: Response({"count": kwargs["count"], "records": list(kwargs["records"])})
            response = self.client.get(f"/api/djen/communications/export.pdf/?q=Maria&collected_from={today}&collected_to={today}&page=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        fields = dict(response.data["records"][0][1])
        self.assertIn("Maria", fields["Partes e destinatários"])
        self.assertIn("Ana", fields["Advogados"])
        self.assertIn("ciência", fields["Texto publicado"])

        old = today - timedelta(days=1)
        DjenCommunication.objects.filter(pk=self.publication.pk).update(
            collected_at=datetime.combine(old, datetime.min.time(), tzinfo=LOCAL_TZ)
        )
        self.assertEqual(self.client.get(f"/api/djen/communications/export.pdf/?collected_from={today}&collected_to={today}").status_code, 404)

    def test_export_auth_dates_and_pdf(self):
        self.assertIn(APIClient().get("/api/djen/communications/export.pdf/").status_code, (401, 403))
        self.assertEqual(self.client.get("/api/djen/communications/export.pdf/?collected_from=bad").status_code, 400)
        old = timezone.localdate(timezone=LOCAL_TZ) - timedelta(days=30)
        self.assertEqual(self.client.get(f"/api/djen/communications/export.pdf/?scope=history&collected_from={old}").status_code, 400)
        response = self.client.get("/api/djen/communications/export.pdf/?scope=overview")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))
