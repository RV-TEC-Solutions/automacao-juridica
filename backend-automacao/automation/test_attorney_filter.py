from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from automation.models import AutomationRun, AutomationSource, DjenAttorney, DjenCommunication
from automation.services.djen.persistence import save_communications
from automation.services.pje.persistence import salvar_expedientes
from automation.test_djen import record
from expedientes.models import Expediente
from expedientes.tests import payload


@override_settings(DJEN_OAB_NUMBER="5691", DJEN_OAB_STATE="RN", DJEN_CRISTIANO_OAB_NUMBER="5695", DJEN_CRISTIANO_OAB_STATE="RN")
class AttorneyFilterTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(get_user_model().objects.create_user("operador"))
        self.pje = AutomationSource.objects.get(code="pje-tjrn")
        self.djen = AutomationSource.objects.get(code="djen")
        salvar_expedientes([payload(identifier="shared"), payload(identifier="murilo")], source=self.pje)
        Expediente.objects.filter(identificador_pje="shared").update(collection_accounts={"murilo": False, "cristiano": True})
        Expediente.objects.filter(identificador_pje="murilo").update(collection_accounts={"murilo": True})
        save_communications([record(42), record(43)], source=self.djen)
        DjenAttorney.objects.create(communication=DjenCommunication.objects.get(numero_comunicacao=42), name="Cristiano", oab_number="5695", oab_state="RN")
        self.murilo = AutomationRun.objects.create(source=self.pje, collector="murilo", status="success")
        self.cristiano = AutomationRun.objects.create(source=self.pje, collector="cristiano", status="success")
        AutomationRun.objects.create(source=self.djen, collector="murilo", status="success")

    def test_expedientes_and_history_include_shared_and_former_accounts(self):
        self.assertEqual(self.client.get("/api/expedientes/?attorney=murilo").data["count"], 2)
        self.assertEqual(self.client.get("/api/expedientes/?attorney=cristiano").data["count"], 1)
        self.assertEqual(self.client.get("/api/history/?attorney=cristiano").data["count"], 1)
        with patch("expedientes.reports.pdf_response", return_value=HttpResponse()) as pdf:
            self.client.get("/api/expedientes/export.pdf/?scope=history&attorney=cristiano")
            self.assertEqual(pdf.call_args.kwargs["count"], 1)

    def test_djen_filters_list_history_and_export_by_oab(self):
        self.assertEqual(self.client.get("/api/djen/communications/?attorney=murilo").data["count"], 2)
        self.assertEqual(self.client.get("/api/djen/communications/?attorney=cristiano").data["count"], 1)
        self.assertEqual(self.client.get("/api/djen/history/?attorney=cristiano").data["count"], 1)
        with patch("automation.reports.pdf_response", return_value=HttpResponse()) as pdf:
            self.client.get("/api/djen/communications/export.pdf/?scope=history&attorney=cristiano")
            self.assertEqual(pdf.call_args.kwargs["count"], 1)

    def test_collection_history_excludes_shared_djen_and_invalid_filters(self):
        response = self.client.get("/api/automation/history/?attorney=cristiano")
        ids = [run["id"] for day in response.data["days"] for run in day["runs"]]
        self.assertEqual(ids, [self.cristiano.id])
        for url in ("/api/automation/history/", "/api/history/", "/api/expedientes/", "/api/djen/history/", "/api/djen/communications/"):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url, {"attorney": "invalid"}).status_code, 400)
