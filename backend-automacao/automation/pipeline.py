"""Serialização explícita do ciclo sequencial de coleta do PJe."""

from django.db.models import Max, Min

from .models import AutomationRun, AutomationSource
from .services.pje.sources import PJE_SOURCE_ORDER, get_source_profile


GROUPS = {
    "pje-tjrn": "TJRN", "pje2g-tjrn": "TJRN",
    "tre-rn-1g": "Justiça Eleitoral", "tre-rn-2g": "Justiça Eleitoral",
    "tse-3g": "Justiça Eleitoral", "trt21": "TRT21", "trt21-2g": "TRT21",
    "trf5-2g-tru": "TRF5", "varas-justica-comum": "TRF5",
    "jef-5-regiao": "TRF5", "trs-5-regiao": "TRF5", "tru-5-regiao": "TRF5",
}

LABELS = {
    "pje-tjrn": "1º Grau", "pje2g-tjrn": "2º Grau",
    "tre-rn-1g": "TRE-RN · 1º Grau", "tre-rn-2g": "TRE-RN · 2º Grau",
    "tse-3g": "TSE · 3º Grau", "trt21": "1º Grau", "trt21-2g": "2º Grau",
    "trf5-2g-tru": "2º Grau / TRU", "varas-justica-comum": "Varas federais",
    "jef-5-regiao": "JEF · 5ª Região", "trs-5-regiao": "Turmas recursais",
    "tru-5-regiao": "TRU · perfil alternativo",
}


def _runs_for_cycle(latest):
    if latest is None:
        return []
    return list(
        AutomationRun.objects.select_related("source")
        .filter(cycle_id=latest.cycle_id, descartada_em__isnull=True)
        .order_by("criada_em", "id")
    )


def _steps_for_cycle(sources, cycle_runs):
    runs_by_source = {run.source.code: run for run in cycle_runs if run.source}
    active = any(
        run.status in (AutomationRun.Status.PENDING, AutomationRun.Status.RUNNING)
        for run in cycle_runs
    )
    start_index = min(
        (PJE_SOURCE_ORDER.index(code) for code in runs_by_source), default=0
    )

    steps = []
    for index, code in enumerate(PJE_SOURCE_ORDER):
        source = sources.get(code)
        run = runs_by_source.get(code)
        if source and not source.enabled:
            step_status = "disabled"
        elif run:
            step_status = run.status
        elif cycle_runs and (index < start_index or not active):
            step_status = "skipped"
        else:
            step_status = "pending"
        steps.append({
            "code": code,
            "group": GROUPS[code],
            "label": LABELS.get(code, get_source_profile(code).system),
            "status": step_status,
            "run_id": run.id if run else None,
            "error": run.mensagem_erro if run else "",
            "message": run.mensagem_info if run else "",
        })
    return steps


def _replace_step_with_run(steps_by_code, run, sources):
    if (
        run.source is None
        or run.source.code not in steps_by_code
        or not sources.get(run.source.code, run.source).enabled
    ):
        return
    steps_by_code[run.source.code].update({
        "status": run.status,
        "run_id": run.id,
        "error": run.mensagem_erro,
        "message": run.mensagem_info,
    })


def _cycle_status(cycle_runs, active):
    if not cycle_runs:
        return "idle"
    if active:
        return "running"
    if any(run.status == AutomationRun.Status.CANCELLED for run in cycle_runs):
        return "cancelled"
    if any(run.status == AutomationRun.Status.FAILED for run in cycle_runs):
        return "failed"
    return "success"


def collection_pipeline_payload():
    latest_record = AutomationRun.objects.select_related("source").first()
    latest = (
        None
        if latest_record and latest_record.descartada_em is not None
        else latest_record
    )
    sources = {
        source.code: source
        for source in AutomationSource.objects.filter(code__in=PJE_SOURCE_ORDER)
    }
    cycle_runs = _runs_for_cycle(latest)
    active = any(
        run.status in (AutomationRun.Status.PENDING, AutomationRun.Status.RUNNING)
        for run in cycle_runs
    )

    if latest and latest.trigger == AutomationRun.Trigger.RERUN:
        previous_cycle = (
            AutomationRun.objects.select_related("source")
            .filter(descartada_em__isnull=True)
            .exclude(trigger=AutomationRun.Trigger.RERUN)
            .filter(criada_em__lt=latest.criada_em)
            .first()
        )
        steps = _steps_for_cycle(sources, _runs_for_cycle(previous_cycle))
        reruns = AutomationRun.objects.select_related("source").filter(
            trigger=AutomationRun.Trigger.RERUN,
            descartada_em__isnull=True,
        )
        if previous_cycle:
            reruns = reruns.filter(criada_em__gt=previous_cycle.criada_em)
        steps_by_code = {step["code"]: step for step in steps}
        for rerun in reruns.order_by("criada_em", "id"):
            _replace_step_with_run(steps_by_code, rerun, sources)
    else:
        steps = _steps_for_cycle(sources, cycle_runs)

    completed = sum(step["status"] == AutomationRun.Status.SUCCESS for step in steps)
    relevant = sum(step["status"] != "disabled" for step in steps)
    timestamps = AutomationRun.objects.filter(
        cycle_id=latest.cycle_id,
        descartada_em__isnull=True,
    ).aggregate(
        started_at=Min("iniciada_em"), finished_at=Max("finalizada_em")
    ) if latest else {"started_at": None, "finished_at": None}
    if latest and latest.trigger == AutomationRun.Trigger.RERUN:
        active_run = next(
            (run for run in cycle_runs if run.status in ("running", "pending")), None
        )
        current_code = active_run.source.code if active_run and active_run.source else None
    else:
        current = next(
            (step for step in steps if step["status"] in ("running", "pending")), None
        )
        current_code = current["code"] if current else None
    return {
        "cycle_id": str(latest.cycle_id) if latest else None,
        "status": _cycle_status(cycle_runs, active), "active": active,
        "completed": completed, "total": relevant,
        "started_at": timestamps["started_at"],
        "finished_at": None if active else timestamps["finished_at"],
        "current_step": current_code,
        "steps": steps,
    }
