from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .client import fetch_communications
from .persistence import save_communications


def collect_djen(*, source, run):
    day = timezone.localdate()
    records = []
    for offset in range(6, -1, -1):
        records.extend(fetch_communications(day - timedelta(days=offset)))
    with transaction.atomic():
        result = save_communications(records, source=source, run=run)
    return result, f"Consulta DJEN de {day - timedelta(days=6):%d/%m/%Y} a {day:%d/%m/%Y} concluída."
