from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from .models import AutomationRun, AutomationSource, UserProfile
from .services.pje.sources import PJE_SOURCE_ORDER
from .collectors import collector_order, get_collector


LOCAL_TZ = ZoneInfo("America/Fortaleza")
PJE_1G_SOURCE_CODE = "pje-tjrn"


def first_enabled_source(start_code=None):
    """Retorna a primeira fonte habilitada a partir da ordem de coleta."""
    source_codes = PJE_SOURCE_ORDER
    if start_code is not None:
        try:
            source_codes = source_codes[PJE_SOURCE_ORDER.index(start_code):]
        except ValueError:
            return None

    sources = {
        source.code: source
        for source in AutomationSource.objects.filter(
            code__in=source_codes,
            enabled=True,
        )
    }
    return next((sources[code] for code in source_codes if code in sources), None)


@transaction.atomic
def enqueue_run(source, trigger, requested_by=None, scheduled_for=None, cycle_id=None, collector=None):
    collector = collector or collector_order()[0]
    get_collector(collector)
    if not source.enabled:
        raise ValueError("A fonte está desativada.")
    # Shared lock across sources: two requests must not both pass the idle check.
    list(AutomationSource.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
    active_runs = AutomationRun.objects.filter(
        status__in=(AutomationRun.Status.PENDING, AutomationRun.Status.RUNNING),
    )
    isolated_triggers = (AutomationRun.Trigger.RERUN, AutomationRun.Trigger.RETRY, AutomationRun.Trigger.COLLECTOR)
    if (trigger in isolated_triggers and active_runs.exists()) or active_runs.filter(
        trigger__in=isolated_triggers,
    ).exists():
        raise ValueError("Aguarde a coleta em andamento terminar antes de iniciar outro titular. Reexecute uma fonte por vez.")
    try:
        values = {
            "source": source, "trigger": trigger, "requested_by": requested_by,
            "scheduled_for": scheduled_for, "status": AutomationRun.Status.PENDING,
            "collector": collector,
        }
        if cycle_id is not None:
            values["cycle_id"] = cycle_id
        with transaction.atomic():
            return AutomationRun.objects.create(**values)
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
    trigger = (
        AutomationRun.Trigger.SCHEDULED
        if local_now - due_at <= timedelta(minutes=5)
        else AutomationRun.Trigger.CATCH_UP
    )
    queued = []
    for source in (first_enabled_source(PJE_1G_SOURCE_CODE), AutomationSource.objects.filter(code="djen", enabled=True).first()):
        if source is None or source.runs.filter(
            trigger__in=(AutomationRun.Trigger.SCHEDULED, AutomationRun.Trigger.CATCH_UP),
            scheduled_for=due_at,
        ).exists():
            continue
        try:
            queued.append(enqueue_run(source, trigger, scheduled_for=due_at))
        except ValueError:
            pass
    return queued


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


def claim_next_run(source_code=None):
    with transaction.atomic():
        # A fila deve continuar sequencial mesmo com mais de um worker.
        list(AutomationSource.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
        if AutomationRun.objects.filter(status=AutomationRun.Status.RUNNING).exists():
            return None
        pending = (
            AutomationRun.objects.select_for_update(skip_locked=True)
            .filter(status=AutomationRun.Status.PENDING, source__enabled=True)
        )
        if source_code is not None:
            pending = pending.filter(source__code=source_code)
        run = pending.order_by("criada_em").first()
        if source_code is None:
            djen = pending.filter(source__code="djen").order_by("criada_em").first()
            run = djen or run
        if run:
            run.status = AutomationRun.Status.RUNNING
            run.iniciada_em = timezone.now()
            run.save(update_fields=("status", "iniciada_em"))
        return run


@transaction.atomic
def enqueue_due_retry(now=None):
    """Agenda no máximo uma fonte falha da janela diária ainda vigente."""
    now = now or timezone.now()
    local_now = now.astimezone(LOCAL_TZ)
    profile = UserProfile.objects.order_by("id").first()
    collection_time = profile.collection_time if profile else datetime.strptime("06:00", "%H:%M").time()
    due_at = datetime.combine(local_now.date(), collection_time, tzinfo=LOCAL_TZ)
    if local_now < due_at:
        due_at -= timedelta(days=1)

    # O mesmo bloqueio usado por enqueue_run serializa a decisão entre workers.
    list(AutomationSource.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
    if AutomationRun.objects.filter(status__in=(AutomationRun.Status.PENDING, AutomationRun.Status.RUNNING)).exists():
        return None

    runs = list(AutomationRun.objects.select_related("source").filter(
        scheduled_for=due_at,
        trigger__in=(AutomationRun.Trigger.SCHEDULED, AutomationRun.Trigger.CATCH_UP, AutomationRun.Trigger.RETRY),
    ).order_by("criada_em", "id"))
    discarded_cycles = {run.cycle_id for run in runs if run.descartada_em is not None}
    blocked = {(run.cycle_id, run.collector) for run in runs if run.credential_failure}
    latest = {}
    for run in runs:
        if run.source_id and run.cycle_id not in discarded_cycles:
            latest[(run.cycle_id, run.source_id, run.collector)] = run

    candidates = sorted(latest.values(), key=lambda run: (run.finalizada_em or now, run.pk))
    for run in candidates:
        if (run.status != AutomationRun.Status.FAILED or not run.finalizada_em
                or run.finalizada_em + timedelta(hours=2) > now or not run.source.enabled
                or (run.cycle_id, run.collector) in blocked and run.source.code != "djen"):
            continue
        # Um sucesso manual posterior também resolve a falha da rotina diária.
        if AutomationRun.objects.filter(
            source=run.source, collector=run.collector, status=AutomationRun.Status.SUCCESS,
            descartada_em__isnull=True, criada_em__gt=run.criada_em,
        ).exists():
            continue
        try:
            return enqueue_run(run.source, AutomationRun.Trigger.RETRY,
                               scheduled_for=run.scheduled_for, cycle_id=run.cycle_id,
                               collector=run.collector)
        except ValueError:
            return None
    return None


@transaction.atomic
def expire_pending_retries(now=None):
    """Libera a fila quando um retry pendente já não pode ser executado."""
    now = now or timezone.now()
    local_now = now.astimezone(LOCAL_TZ)
    profile = UserProfile.objects.order_by("id").first()
    collection_time = profile.collection_time if profile else datetime.strptime("06:00", "%H:%M").time()
    due_at = datetime.combine(local_now.date(), collection_time, tzinfo=LOCAL_TZ)
    if local_now < due_at:
        due_at -= timedelta(days=1)
    list(AutomationSource.objects.select_for_update().order_by("pk").values_list("pk", flat=True))
    return AutomationRun.objects.filter(
        trigger=AutomationRun.Trigger.RETRY, status=AutomationRun.Status.PENDING,
    ).filter(Q(scheduled_for__lt=due_at) | Q(source__enabled=False)).update(
        status=AutomationRun.Status.CANCELLED, finalizada_em=now,
        mensagem_info="Retry automático encerrado: ciclo expirado ou fonte desativada.",
    )
