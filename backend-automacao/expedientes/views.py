from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Exists, Max, OuterRef, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from automation.models import AutomationRun, UserProfile
from .models import Expediente, ExpedienteEvent
from .serializers import EventSerializer, ExpedienteSerializer


LOCAL_TZ = ZoneInfo("America/Fortaleza")


def _base_queryset():
    return Expediente.objects.select_related("processo", "source").prefetch_related("events")


class ExpedientePagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = None


class ExpedienteViewSet(ReadOnlyModelViewSet):
    serializer_class = ExpedienteSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = ExpedientePagination

    def get_queryset(self):
        params = self.request.query_params
        queryset = _base_queryset().annotate(
            has_unread=Exists(ExpedienteEvent.objects.filter(expediente=OuterRef("pk"), read_at__isnull=True)),
            latest_event_at=Max("events__created_at"),
        )
        query = params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                Q(processo__numero__icontains=query)
                | Q(processo__partes_texto__icontains=query)
                | Q(processo__assunto__icontains=query)
            )
        if source := params.get("source"):
            queryset = queryset.filter(source__code=source)
        if pending := params.get("pending_type"):
            queryset = queryset.filter(tipo_pendencia=pending)
        if read := params.get("read"):
            queryset = queryset.filter(has_unread=(read == "unread"))
        if date_from := params.get("date_from"):
            queryset = queryset.filter(events__created_at__date__gte=date_from)
        if date_to := params.get("date_to"):
            queryset = queryset.filter(events__created_at__date__lte=date_to)

        now = timezone.now()
        urgent_limit = now + timedelta(hours=72)
        deadline = params.get("deadline")
        if deadline == "urgent":
            queryset = queryset.filter(ativo=True, status_prazo_fatal="calculado", prazo_fatal__lte=urgent_limit)
        elif deadline == "overdue":
            queryset = queryset.filter(ativo=True, status_prazo_fatal="calculado", prazo_fatal__lt=now)
        elif deadline == "future":
            queryset = queryset.filter(ativo=True, prazo_fatal__gt=urgent_limit)
        elif deadline == "calculating":
            queryset = queryset.filter(ativo=True, status_prazo_fatal="em_calculo")
        elif deadline == "none":
            queryset = queryset.filter(ativo=True, status_prazo_fatal="sem_prazo")
        elif deadline == "resolved":
            queryset = queryset.filter(ativo=False)

        orderings = {
            "recent": "-latest_event_at", "deadline": "prazo_fatal",
            "expedition": "-data_expedicao", "process": "processo__numero",
        }
        return queryset.order_by(orderings.get(params.get("ordering", "recent"), "-latest_event_at")).distinct()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_read(request, pk):
    expediente = get_object_or_404(Expediente, pk=pk)
    read_at = timezone.now()
    count = expediente.events.filter(read_at__isnull=True).update(read_at=read_at)
    return Response({"read_at": read_at, "events_marked": count})


def _latest_run_data():
    run = AutomationRun.objects.select_related("source").first()
    if not run:
        return None
    return {
        "id": run.id, "status": run.status, "trigger": run.trigger,
        "started_at": run.iniciada_em, "finished_at": run.finalizada_em,
        "found": run.expedientes_encontrados, "created": run.expedientes_criados,
        "updated": run.expedientes_atualizados, "resolved": run.expedientes_resolvidos,
        "error": run.mensagem_erro, "message": run.mensagem_info,
        "source": str(run.source) if run.source else None,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"display_name": request.user.get_full_name() or request.user.username},
    )
    if request.method == "POST":
        previous = profile.last_dashboard_visit
        profile.last_dashboard_visit = timezone.now()
        profile.save(update_fields=("last_dashboard_visit",))
        return Response({"previous_visit": previous, "visited_at": profile.last_dashboard_visit})

    now = timezone.now()
    local_now = now.astimezone(LOCAL_TZ)
    today_start = datetime.combine(local_now.date(), datetime.min.time(), tzinfo=LOCAL_TZ)
    events_today = ExpedienteEvent.objects.filter(created_at__gte=today_start)
    active = Expediente.objects.filter(ativo=True)
    unread = Expediente.objects.filter(events__read_at__isnull=True).distinct().count()
    urgent = active.filter(status_prazo_fatal="calculado", prazo_fatal__lte=now + timedelta(hours=72)).count()
    calculating = active.filter(status_prazo_fatal="em_calculo").count()
    since = profile.last_dashboard_visit
    since_events = ExpedienteEvent.objects.filter(created_at__gt=since) if since else ExpedienteEvent.objects.all()
    recent = _base_queryset().filter(events__isnull=False).annotate(
        latest_event_at=Max("events__created_at")
    ).order_by("-latest_event_at")[:8]
    return Response({
        "display_name": profile.display_name,
        "today": {
            "new": events_today.filter(kind="new").values("expediente_id").distinct().count(),
            "updated": events_today.filter(kind="updated").values("expediente_id").distinct().count(),
            "unread": unread, "urgent": urgent, "calculating": calculating,
        },
        "since_last_visit": {
            "since": since,
            "new": since_events.filter(kind="new").count(),
            "updated": since_events.filter(kind="updated").count(),
            "resolved": since_events.filter(kind="resolved").count(),
        },
        "latest_run": _latest_run_data(),
        "recent": ExpedienteSerializer(recent, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def statistics(request):
    period = int(request.query_params.get("period", 7))
    if period not in (7, 30):
        return Response({"detail": "Período deve ser 7 ou 30 dias."}, status=status.HTTP_400_BAD_REQUEST)
    now = timezone.now()
    current_start = now - timedelta(days=period)
    previous_start = current_start - timedelta(days=period)
    events = ExpedienteEvent.objects.filter(created_at__gte=current_start)
    previous = ExpedienteEvent.objects.filter(created_at__gte=previous_start, created_at__lt=current_start)
    timeline_rows = events.annotate(day=TruncDate("created_at", tzinfo=LOCAL_TZ)).values("day", "kind").annotate(total=Count("id")).order_by("day")
    by_kind = {row["kind"]: row["total"] for row in events.values("kind").annotate(total=Count("id"))}
    current_total, previous_total = events.count(), previous.count()
    comparison = None if previous_total == 0 else round((current_total - previous_total) / previous_total * 100, 1)
    active = Expediente.objects.filter(ativo=True)
    return Response({
        "period": period,
        "totals": {"current": current_total, "previous": previous_total, "change_percent": comparison, **by_kind},
        "timeline": list(timeline_rows),
        "pending_distribution": list(active.values("tipo_pendencia").annotate(total=Count("id")).order_by("tipo_pendencia")),
        "deadline_distribution": list(active.values("status_prazo_fatal").annotate(total=Count("id")).order_by("status_prazo_fatal")),
    })
