from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .client import fetch_communications
from .persistence import save_communications


def collect_djen(*, source, run):
    day = timezone.localdate()
    records = {}
    oabs = [(settings.DJEN_OAB_NUMBER, settings.DJEN_OAB_STATE)]
    if settings.DJEN_CRISTIANO_OAB_NUMBER:
        oabs.append((settings.DJEN_CRISTIANO_OAB_NUMBER, settings.DJEN_CRISTIANO_OAB_STATE))
    for number, state in dict.fromkeys(oabs):
        for offset in range(6, -1, -1):
            for record in fetch_communications(day - timedelta(days=offset), oab_number=number, oab_state=state):
                key = record.get("numeroComunicacao")
                records[key if key is not None else object()] = record
    with transaction.atomic():
        result = save_communications(records.values(), source=source, run=run)
    return result, f"Consulta DJEN de {day - timedelta(days=6):%d/%m/%Y} a {day:%d/%m/%Y} concluída."
