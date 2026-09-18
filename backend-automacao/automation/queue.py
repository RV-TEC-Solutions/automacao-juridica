from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import AutomationRun, AutomationSource, UserProfile


LOCAL_TZ = ZoneInfo("America/Fortaleza")
PJE_1G_SOURCE_CODE = "pje-tjrn"


def enqueue_run(source, trigger, requested_by=None, scheduled_for=None):
    if not source.enabled:
        raise ValueError("A fonte está desativada.")
    try:
        return AutomationRun.objects.create(
            source=source,
            trigger=trigger,
            requested_by=requested_by,
            scheduled_for=scheduled_for,
            status=AutomationRun.Status.PENDING,
        )
    except IntegrityError as error:
        raise ValueError("Já existe uma coleta pendente ou em execução.") from error


def enqueue_due_runs(now=None):
    now = now or timezone.now()
    local_now = now.astimezone(LOCAL_TZ)
    profile = UserProfile.objects.order_by("id").first()
    collection_time = profile.collection_time if profile else datetime.strptime("06:00", "%H:%M").time()
    due_at = datetime.combine(local_now.date(), collection_time, tzinfo=LOCAL_TZ)
    if local_now < due_at:
        return []

    day_start = datetime.combine(local_now.date(), datetime.min.time(), tzinfo=LOCAL_TZ)
    source = AutomationSource.objects.filter(
        code=PJE_1G_SOURCE_CODE,
        enabled=True,
    ).first()
    if source is None or source.runs.filter(criada_em__gte=day_start).exists():
        return []

    try:
        trigger = (
            AutomationRun.Trigger.SCHEDULED
            if local_now - due_at <= timedelta(minutes=5)
            else AutomationRun.Trigger.CATCH_UP
        )
        return [enqueue_run(source, trigger, scheduled_for=due_at)]
    except ValueError:
        return []


def recover_interrupted_runs():
    """Libera coletas que ficaram em execução quando o worker anterior caiu."""
    return AutomationRun.objects.filter(
        status=AutomationRun.Status.RUNNING
    ).update(
        status=AutomationRun.Status.FAILED,
        mensagem_erro=(
            "Coleta interrompida antes da conclusão; "
            "recupere-a executando novamente."
        ),
        finalizada_em=timezone.now(),
    )


def claim_next_run():
    with transaction.atomic():
        run = (
            AutomationRun.objects.select_for_update(skip_locked=True)
            .filter(status=AutomationRun.Status.PENDING, source__enabled=True)
            .order_by("criada_em")
            .first()
        )
        if run:
            run.status = AutomationRun.Status.RUNNING
            run.iniciada_em = timezone.now()
            run.save(update_fields=("status", "iniciada_em"))
        return run
