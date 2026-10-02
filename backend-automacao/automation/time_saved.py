"""Estimativa acumulada do trabalho manual substituído por coletas concluídas.

Os tempos são premissas de uma simulação operacional, não tempos cronometrados.
Cada valor fixo já desconta cerca de dois minutos de conferência da automação.
Reexecuções da mesma fonte no mesmo dia não repetem o trabalho fixo e, no PJe,
usam o maior volume observado para não contar os mesmos expedientes duas vezes.
"""

from collections import defaultdict
from zoneinfo import ZoneInfo

from django.utils import timezone

from .models import AutomationRun
from .services.pje.sources import SOURCE_PROFILES


LOCAL_TZ = ZoneInfo("America/Fortaleza")
FIXED_SECONDS = {"direct": 360, "portal": 480, "trt21": 360, "djen": 720}
ITEM_SECONDS = {"direct": 75, "portal": 75, "trt21": 120, "djen": 90}
TAB_SECONDS = 45
DAILY_MAX_SECONDS = 4 * 60 * 60


def _kind(code):
    if code == "djen":
        return "djen"
    profile = SOURCE_PROFILES.get(code)
    if profile is None:
        return None
    if profile.collector == "trt21":
        return "trt21"
    return "portal" if profile.portal_flow else "direct"


def time_saved_summary():
    """Agrupa execuções bem sucedidas por fonte e dia local, sem limite de período."""
    days = defaultdict(lambda: {"seconds": 0, "sources": 0, "items": 0, "tabs": 0})
    source_days = {}
    runs = AutomationRun.objects.filter(
        status=AutomationRun.Status.SUCCESS,
        descartada_em__isnull=True,
        source__isnull=False,
        finalizada_em__isnull=False,
    ).values_list("source__code", "finalizada_em", "expedientes_encontrados", "expedientes_criados", "capturas_html")

    for code, finished_at, found, created, captures in runs.iterator():
        kind = _kind(code)
        if kind is None:
            continue
        day = timezone.localtime(finished_at, LOCAL_TZ).date()
        key = (day, code)
        if key not in source_days:
            source_days[key] = {"kind": kind, "items": 0, "tabs": 0}
        if kind == "djen":
            # A persistência única da comunicação faz "criados" representar
            # apenas publicações novas em cada reexecução.
            source_days[key]["items"] += created
        else:
            source_days[key]["items"] = max(source_days[key]["items"], found)
            source_days[key]["tabs"] = max(source_days[key]["tabs"], captures)

    for (day, _), entry in source_days.items():
        daily = days[day]
        daily["sources"] += 1
        daily["items"] += entry["items"]
        daily["tabs"] += entry["tabs"]
        daily["seconds"] += (FIXED_SECONDS[entry["kind"]]
                             + ITEM_SECONDS[entry["kind"]] * entry["items"]
                             + TAB_SECONDS * entry["tabs"])

    today = timezone.localdate(timezone=LOCAL_TZ)
    return {
        "total_seconds": sum(min(day["seconds"], DAILY_MAX_SECONDS) for day in days.values()),
        "today_seconds": min(days[today]["seconds"], DAILY_MAX_SECONDS),
        "source_days": sum(day["sources"] for day in days.values()),
        "items": sum(day["items"] for day in days.values()),
        "tabs": sum(day["tabs"] for day in days.values()),
    }
