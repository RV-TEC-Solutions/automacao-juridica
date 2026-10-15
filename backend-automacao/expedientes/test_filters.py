from datetime import datetime
from zoneinfo import ZoneInfo

from django.http import QueryDict
from django.test import TestCase
from rest_framework.exceptions import ParseError

from automation.models import AutomationSource
from automation.services.pje.persistence import salvar_expedientes
from .models import Expediente
from .tests import payload
from .views import expediente_queryset


class AdvancedFilterTests(TestCase):
    def setUp(self):
        local_tz = ZoneInfo('America/Fortaleza')
        for code, identifier, deadline in (
            ('pje-tjrn', 'start', datetime(2026, 10, 13, tzinfo=local_tz)),
            ('tre-rn-1g', 'end', datetime(2026, 10, 14, 23, 59, 59, tzinfo=local_tz)),
            ('trt21', 'outside', datetime(2026, 10, 15, tzinfo=local_tz)),
        ):
            salvar_expedientes([payload(identifier=identifier, prazo_fatal=deadline.isoformat())], source=AutomationSource.objects.get(code=code))

    def test_multiple_sources_and_legacy_single_source(self):
        self.assertEqual(expediente_queryset(QueryDict('source=pje-tjrn&source=tre-rn-1g')).count(), 2)
        self.assertEqual(expediente_queryset(QueryDict('source=pje-tjrn')).count(), 1)
        self.assertEqual(expediente_queryset(QueryDict('source=')).count(), 3)

    def test_deadline_range_includes_entire_local_final_day(self):
        params = QueryDict('deadline_from=2026-10-13&deadline_to=2026-10-14')
        self.assertSetEqual(set(expediente_queryset(params).values_list('identificador_pje', flat=True)), {'start', 'end'})
        self.assertEqual(expediente_queryset(QueryDict('deadline_from=2026-10-14')).count(), 2)
        self.assertEqual(expediente_queryset(QueryDict('deadline_to=2026-10-13')).count(), 1)
        Expediente.objects.filter(identificador_pje='start').update(prazo_fatal=None)
        self.assertEqual(expediente_queryset(params).count(), 1)

    def test_sources_and_deadline_range_are_combined(self):
        params = QueryDict('source=pje-tjrn&source=trt21&deadline_to=2026-10-14')
        self.assertEqual(expediente_queryset(params).get().identificador_pje, 'start')

    def test_invalid_deadline_ranges_are_rejected(self):
        for query in ('deadline_from=invalid', 'deadline_to=2026-02-30', 'deadline_from=2026-10-15&deadline_to=2026-10-13', 'deadline_to=9999-12-31'):
            with self.subTest(query=query), self.assertRaises(ParseError):
                expediente_queryset(QueryDict(query))
