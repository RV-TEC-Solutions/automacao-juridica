from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import TestCase, override_settings

from automation.models import AutomationRun, AutomationSource, DjenCommunication
from automation.services.djen.client import DjenAPIError, _request, fetch_communications
from automation.services.djen.runner import collect_djen
from automation.services.djen.persistence import save_communications


def record(number=42, text="Intimação publicada"):
    return {
        "id": 99,
        "numeroComunicacao": number,
        "hash": "abc",
        "data_disponibilizacao": "2026-10-01",
        "siglaTribunal": "TRF5",
        "tipoComunicacao": "Intimação",
        "nomeOrgao": "1ª Vara Federal RN",
        "texto": text,
        "numero_processo": "0800000-00.2026.4.05.8400",
        "meio": "D",
        "meiocompleto": "Diário de Justiça Eletrônico Nacional",
        "link": "https://example.test/inteiro-teor",
        "nomeClasse": "Procedimento Comum",
        "codigoClasse": "7",
        "destinatarios": [{"nome": "PARTE A", "polo": "A"}],
        "destinatarioadvogados": [{"advogado": {"nome": "ADVOGADO", "numero_oab": "5691", "uf_oab": "RN"}}],
    }


class DjenPersistenceTests(TestCase):
    def setUp(self):
        self.source = AutomationSource.objects.get(code="djen")
        self.run = AutomationRun.objects.create(source=self.source)

    def test_persists_and_updates_without_duplicating_publication(self):
        first = save_communications([record()], source=self.source, run=self.run)
        second = save_communications([record(text="Texto corrigido")], source=self.source, run=self.run)

        self.assertEqual(first["criados"], 1)
        self.assertEqual(second["atualizados"], 1)
        self.assertEqual(DjenCommunication.objects.count(), 1)
        communication = DjenCommunication.objects.get()
        self.assertEqual(communication.texto, "Texto corrigido")
        self.assertEqual(communication.recipients.get().name, "PARTE A")
        self.assertEqual(communication.attorneys.get().oab_number, "5691")

    def test_reconsulting_preserves_read_state(self):
        save_communications([record()], source=self.source, run=self.run)
        communication = DjenCommunication.objects.get()
        from django.utils import timezone
        communication.read_at = timezone.now()
        communication.save(update_fields=("read_at",))
        save_communications([record(text="Corrigido")], source=self.source, run=self.run)
        communication.refresh_from_db()
        self.assertIsNotNone(communication.read_at)
        self.assertEqual(communication.texto, "Corrigido")

    @patch("automation.services.djen.runner.fetch_communications")
    def test_collects_seven_days_before_saving(self, fetch):
        fetch.return_value = []
        collect_djen(source=self.source, run=self.run)
        self.assertEqual(fetch.call_count, 7)
        self.assertEqual((fetch.call_args_list[-1].args[0] - fetch.call_args_list[0].args[0]).days, 6)


@override_settings(DJEN_OAB_NUMBER="5691", DJEN_OAB_STATE="RN")
class DjenClientTests(TestCase):
    @patch("automation.services.djen.client.time.sleep")
    @patch("automation.services.djen.client.urlopen")
    def test_rate_limit_waits_one_minute_before_retry(self, urlopen, sleep):
        urlopen.side_effect = HTTPError("https://example.test", 429, "rate limit", {}, None)
        with self.assertRaises(DjenAPIError):
            _request({"numeroOab": "5691"}, attempts=2)
        sleep.assert_called_once_with(60)

    @patch("automation.services.djen.client._request")
    def test_fetches_all_pages_with_official_filters(self, request):
        request.side_effect = [
            {"count": 101, "items": [{"id": value} for value in range(100)]},
            {"count": 101, "items": [{"id": 100}]},
        ]

        items = fetch_communications(date(2026, 10, 1))

        self.assertEqual(len(items), 101)
        self.assertEqual(request.call_count, 2)
        params = request.call_args_list[0].args[0]
        self.assertEqual(params["numeroOab"], "5691")
        self.assertEqual(params["ufOab"], "RN")
        self.assertEqual(params["dataDisponibilizacaoInicio"], "2026-10-01")
        self.assertEqual(params["pagina"], 1)
        self.assertEqual(params["meio"], "D")

    @patch("automation.services.djen.client._request")
    def test_rejects_incomplete_and_capped_responses(self, request):
        request.return_value = {"count": 101, "items": [{"id": 1}]}
        with self.assertRaises(DjenAPIError):
            fetch_communications(date(2026, 10, 1))
        request.return_value = {"count": 10000, "items": []}
        with self.assertRaises(DjenAPIError):
            fetch_communications(date(2026, 10, 1))
