import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import dotenv_values

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AutomationRun, AutomationSource, DjenCommunication, Notice, UserProfile
from .serializers import DjenCommunicationSerializer, NoticeSerializer
from .queue import enqueue_run, first_enabled_source
from .services.pjeoffice.physical_token import TokenFisicoError, validar_token_fisico
from expedientes.models import Expediente, ExpedienteEvent, Processo


LOCAL_TZ = ZoneInfo("America/Fortaleza")
COLLECTION_HISTORY_DAYS = 30


def _profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"display_name": user.get_full_name() or user.username},
    )
    return profile


def _user_payload(user):
    profile = _profile(user)
    return {
        "id": user.id, "username": user.username,
        "display_name": profile.display_name, "theme": profile.theme,
        "collection_time": profile.collection_time.strftime("%H:%M"),
    }


@ensure_csrf_cookie
@api_view(["GET"])
@permission_classes([AllowAny])
def csrf(request):
    return Response({"detail": "CSRF cookie set"})


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    user = authenticate(
        request, username=request.data.get("username", ""),
        password=request.data.get("password", ""),
    )
    if not user:
        return Response({"detail": "Usuário ou senha inválidos."}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response(_user_payload(user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(_user_payload(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    if not request.user.check_password(request.data.get("current_password", "")):
        return Response({"current_password": "Senha atual incorreta."}, status=status.HTTP_400_BAD_REQUEST)
    password = request.data.get("new_password", "")
    if len(password) < 8:
        return Response({"new_password": "Use pelo menos 8 caracteres."}, status=status.HTTP_400_BAD_REQUEST)
    request.user.set_password(password)
    request.user.save(update_fields=("password",))
    update_session_auth_hash(request, request.user)
    return Response({"detail": "Senha alterada."})


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def settings_view(request):
    profile = _profile(request.user)
    if request.method == "PATCH":
        if "display_name" in request.data:
            value = str(request.data["display_name"]).strip()
            if not value:
                return Response({"display_name": "Informe um nome."}, status=status.HTTP_400_BAD_REQUEST)
            profile.display_name = value
        if request.data.get("theme") in {"light", "dark", "system"}:
            profile.theme = request.data["theme"]
        if "collection_time" in request.data:
            from datetime import time
            try:
                hour, minute = map(int, request.data["collection_time"].split(":"))
                profile.collection_time = time(hour, minute)
            except (ValueError, TypeError):
                return Response({"collection_time": "Horário inválido."}, status=status.HTTP_400_BAD_REQUEST)
        profile.save()

    credential_file = Path.home() / ".config/pje-automacao/.env"
    credential_values = dotenv_values(credential_file) if credential_file.exists() else {}
    return Response({
        **_user_payload(request.user), "timezone": "America/Fortaleza",
        "credential_status": {
            "credential_file": credential_file.exists(),
            "pin": bool(os.environ.get("PJE_CERT_PIN") or credential_values.get("PJE_CERT_PIN")),
            "totp": bool(os.environ.get("PJE_TOTP_SECRET") or credential_values.get("PJE_TOTP_SECRET")),
            "pjeoffice": "Verificado durante a coleta",
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sources(request):
    return Response([
        {"code": item.code, "system": item.system, "tribunal": item.tribunal, "enabled": item.enabled}
        for item in AutomationSource.objects.all()
    ])


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def source_detail(request, code):
    source = AutomationSource.objects.filter(code=code).first()
    if not source:
        return Response({"detail": "Fonte não encontrada."}, status=status.HTTP_404_NOT_FOUND)
    if "enabled" in request.data:
        source.enabled = bool(request.data["enabled"])
        source.save(update_fields=("enabled",))
        if not source.enabled:
            source.runs.filter(status=AutomationRun.Status.PENDING).update(
                status=AutomationRun.Status.FAILED,
                mensagem_erro="Fonte desativada antes da execução.",
                finalizada_em=timezone.now(),
            )
    return Response({"code": source.code, "system": source.system, "tribunal": source.tribunal, "enabled": source.enabled})


def _run_payload(run):
    return {
        "id": run.id, "cycle_id": str(run.cycle_id),
        "status": run.status, "trigger": run.trigger,
        "created_at": run.criada_em, "started_at": run.iniciada_em,
        "finished_at": run.finalizada_em, "error": run.mensagem_erro,
        "message": run.mensagem_info,
        "found": run.expedientes_encontrados, "created": run.expedientes_criados,
        "updated": run.expedientes_atualizados, "resolved": run.expedientes_resolvidos,
        "source": run.source.code if run.source else None,
    }


def _local_day_window():
    day = timezone.localdate(timezone=LOCAL_TZ)
    start = datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_TZ)
    end = start + timedelta(days=1)
    return day, start, end


def _restore_event(event, window_start):
    """Restaura os valores anteriores registrados em um evento de coleta."""
    changes = event.changes or {}
    expediente_values = {}
    processo_values = {}
    expediente_fields = {
        key: field
        for field in Expediente._meta.fields
        if field.name not in {"id", "atualizado_em", "capturado_em", "visto_na_ultima_coleta_em"}
        for key in (field.name, field.attname)
    }
    processo_fields = {
        field.name: field
        for field in Processo._meta.fields
        if field.name not in {"id", "criado_em", "atualizado_em"}
    }

    for field_name, values in changes.items():
        if not isinstance(values, dict) or "before" not in values:
            continue
        before = values["before"]
        if field_name.startswith("processo."):
            name = field_name.removeprefix("processo.")
            field = processo_fields.get(name)
            if field:
                processo_values[name] = field.to_python(before)
            continue
        field = expediente_fields.get(field_name)
        if field:
            expediente_values[field_name] = field.to_python(before)

    if processo_values:
        Processo.objects.filter(pk=event.expediente.processo_id).update(**processo_values)

    if "ativo" in expediente_values:
        if expediente_values["ativo"]:
            expediente_values["arquivado_em"] = None
        else:
            previous_resolution = (
                ExpedienteEvent.objects.filter(
                    expediente_id=event.expediente_id,
                    kind=ExpedienteEvent.Kind.RESOLVED,
                    created_at__lt=window_start,
                )
                .order_by("-created_at", "-id")
                .first()
            )
            expediente_values["arquivado_em"] = (
                previous_resolution.created_at if previous_resolution else event.expediente.arquivado_em
            )

    if expediente_values:
        Expediente.objects.filter(pk=event.expediente_id).update(**expediente_values)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def discard_today_collection(request):
    day, window_start, window_end = _local_day_window()
    with transaction.atomic():
        if AutomationRun.objects.select_for_update().filter(
            status=AutomationRun.Status.RUNNING,
        ).exists():
            return Response(
                {"detail": "Não é possível descartar dados enquanto há uma coleta em andamento."},
                status=status.HTTP_409_CONFLICT,
            )
        today_runs = AutomationRun.objects.select_for_update().filter(
            descartada_em__isnull=True,
        ).filter(
            Q(iniciada_em__gte=window_start, iniciada_em__lt=window_end)
            | Q(
                iniciada_em__isnull=True,
                criada_em__gte=window_start,
                criada_em__lt=window_end,
            )
        )
        # As próximas fontes de um ciclo ainda não começaram. Elas podem ser
        # canceladas e descartadas com segurança junto com os dados do dia.
        today_runs.filter(status=AutomationRun.Status.PENDING).update(
            status=AutomationRun.Status.CANCELLED,
            mensagem_info="Coleta descartada pelo usuário antes da execução.",
            finalizada_em=timezone.now(),
        )
        deleted_djen = DjenCommunication.objects.filter(run__in=today_runs).delete()[0]
        events = list(
            ExpedienteEvent.objects.select_for_update()
            .filter(
                run__isnull=False,
                created_at__gte=window_start,
                created_at__lt=window_end,
            )
            .select_related("expediente__processo")
            .order_by("-created_at", "-id")
        )
        new_expediente_ids = {
            event.expediente_id
            for event in events
            if event.kind == ExpedienteEvent.Kind.NEW
        }
        reverted_updates = 0
        reactivated = 0
        event_ids_to_delete = []

        for event in events:
            if event.expediente_id in new_expediente_ids:
                continue
            if event.kind == ExpedienteEvent.Kind.UPDATED:
                _restore_event(event, window_start)
                reverted_updates += 1
                event_ids_to_delete.append(event.id)
            elif event.kind == ExpedienteEvent.Kind.RESOLVED:
                _restore_event(event, window_start)
                reactivated += 1
                event_ids_to_delete.append(event.id)

        if event_ids_to_delete:
            ExpedienteEvent.objects.filter(pk__in=event_ids_to_delete).delete()
        deleted_expedientes = len(new_expediente_ids)
        if new_expediente_ids:
            new_process_ids = set(
                Expediente.objects.filter(pk__in=new_expediente_ids).values_list("processo_id", flat=True)
            )
            Expediente.objects.filter(pk__in=new_expediente_ids).delete()
            Processo.objects.filter(
                pk__in=new_process_ids,
                expedientes__isnull=True,
            ).delete()
        cleared_runs = today_runs.update(descartada_em=timezone.now())

    return Response({
        "date": day.isoformat(),
        "deleted_expedientes": deleted_expedientes,
        "reverted_updates": reverted_updates,
        "reactivated_expedientes": reactivated,
        "cleared_runs": cleared_runs,
        "deleted_djen_communications": deleted_djen,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def collection_history(request):
    day, _, window_end = _local_day_window()
    window_start = datetime.combine(
        day - timedelta(days=COLLECTION_HISTORY_DAYS - 1),
        datetime.min.time(),
        tzinfo=LOCAL_TZ,
    )
    runs = list(
        AutomationRun.objects.select_related("source").filter(
            descartada_em__isnull=True,
        ).filter(
            Q(iniciada_em__gte=window_start, iniciada_em__lt=window_end)
            | Q(iniciada_em__isnull=True, criada_em__gte=window_start, criada_em__lt=window_end)
        )
    )
    grouped = {}
    for run in runs:
        occurred_at = run.iniciada_em or run.criada_em
        local_day = timezone.localtime(occurred_at, LOCAL_TZ).date()
        duration_seconds = (
            max(0, int((run.finalizada_em - run.iniciada_em).total_seconds()))
            if run.iniciada_em and run.finalizada_em else None
        )
        grouped.setdefault(local_day, []).append({
            "id": run.id,
            "cycle_id": str(run.cycle_id),
            "status": run.status,
            "status_label": run.get_status_display(),
            "trigger": run.trigger,
            "trigger_label": run.get_trigger_display(),
            "created_at": run.criada_em,
            "started_at": run.iniciada_em,
            "finished_at": run.finalizada_em,
            "duration_seconds": duration_seconds,
            "found": run.expedientes_encontrados,
            "created": run.expedientes_criados,
            "updated": run.expedientes_atualizados,
            "resolved": run.expedientes_resolvidos,
            "error": run.mensagem_erro,
            "message": run.mensagem_info,
            "source": {
                "code": run.source.code,
                "system": run.source.system,
                "tribunal": run.source.tribunal,
            } if run.source else None,
        })
    days = []
    for date, day_runs in sorted(grouped.items(), reverse=True):
        day_runs.sort(key=lambda item: (item["started_at"] or item["created_at"], item["id"]))
        days.append({"date": date.isoformat(), "runs": day_runs})
    return Response({
        "period_start": window_start.date().isoformat(),
        "period_end": day.isoformat(),
        "days": days,
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def runs(request):
    if request.method == "POST":
        requested_code = request.data.get("source", "pje-tjrn")
        rerun = request.data.get("rerun") is True
        requested_source = AutomationSource.objects.filter(code=requested_code).first()
        if not requested_source:
            return Response({"detail": "Fonte não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        if requested_code != "djen":
            try:
                validar_token_fisico()
            except TokenFisicoError as error:
                return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        if rerun and not requested_source.enabled:
            return Response(
                {"detail": "A fonte está desativada."},
                status=status.HTTP_409_CONFLICT,
            )
        source = (
            requested_source
            if requested_source.enabled
            else first_enabled_source(requested_source.code)
        )
        if source is None:
            return Response(
                {"detail": "Não há fontes habilitadas para coleta."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            trigger = (
                AutomationRun.Trigger.RERUN
                if rerun
                else AutomationRun.Trigger.MANUAL
            )
            run = enqueue_run(source, trigger, requested_by=request.user)
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(_run_payload(run), status=status.HTTP_202_ACCEPTED)
    return Response([_run_payload(run) for run in AutomationRun.objects.select_related("source")[:20]])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def token_status(request):
    try:
        validar_token_fisico()
    except TokenFisicoError as error:
        return Response({"available": False, "message": str(error)})
    return Response({"available": True, "message": "Token físico conectado."})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_run(request, pk):
    """Interrompe uma coleta pendente ou sinaliza a interrupção da coleta em curso."""
    run = AutomationRun.objects.filter(pk=pk).first()
    if not run:
        return Response({"detail": "Coleta não encontrada."}, status=status.HTTP_404_NOT_FOUND)

    if run.status not in {AutomationRun.Status.PENDING, AutomationRun.Status.RUNNING}:
        return Response({"detail": "Esta coleta já foi finalizada."}, status=status.HTTP_409_CONFLICT)

    run.status = AutomationRun.Status.CANCELLED
    run.mensagem_info = "Coleta interrompida pelo usuário."
    run.finalizada_em = timezone.now()
    run.save(update_fields=("status", "mensagem_info", "finalizada_em"))
    return Response(_run_payload(run))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notices(request):
    queryset = Notice.objects.prefetch_related("source_links__source")
    if request.query_params.get("read") == "unread":
        queryset = queryset.filter(read_at__isnull=True)
    try:
        page = max(int(request.query_params.get("page", 1)), 1)
    except ValueError:
        return Response({"detail": "Página inválida."}, status=status.HTTP_400_BAD_REQUEST)
    page_size = 25
    start = (page - 1) * page_size
    total = queryset.count()
    items = queryset[start:start + page_size]
    return Response({
        "count": total,
        "next": page + 1 if start + page_size < total else None,
        "previous": page - 1 if page > 1 else None,
        "results": NoticeSerializer(items, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notice_detail(request, pk):
    notice = Notice.objects.prefetch_related("source_links__source").filter(pk=pk).first()
    if not notice:
        return Response({"detail": "Aviso não encontrado."}, status=status.HTTP_404_NOT_FOUND)
    return Response(NoticeSerializer(notice).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notice_read(request, pk):
    notice = Notice.objects.filter(pk=pk).first()
    if not notice:
        return Response({"detail": "Aviso não encontrado."}, status=status.HTTP_404_NOT_FOUND)
    if notice.read_at is None:
        notice.read_at = timezone.now()
        notice.save(update_fields=("read_at", "updated_at"))
    return Response(NoticeSerializer(Notice.objects.prefetch_related("source_links__source").get(pk=pk)).data)


def _djen_queryset():
    return DjenCommunication.objects.select_related("processo", "source").prefetch_related(
        "recipients", "attorneys"
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def djen_communications(request):
    queryset = _djen_queryset()
    query = request.query_params.get("q", "").strip()
    tribunal = request.query_params.get("tribunal", "").strip()
    date_from = request.query_params.get("date_from", "").strip()
    date_to = request.query_params.get("date_to", "").strip()
    if date_from:
        queryset = queryset.filter(data_disponibilizacao__gte=date_from)
    if date_to:
        queryset = queryset.filter(data_disponibilizacao__lte=date_to)
    if query:
        queryset = queryset.filter(
            Q(processo__numero__icontains=query)
            | Q(texto__icontains=query)
            | Q(recipients__name__icontains=query)
            | Q(attorneys__name__icontains=query)
        ).distinct()
    if tribunal:
        queryset = queryset.filter(tribunal=tribunal)
    if request.query_params.get("read") == "unread":
        queryset = queryset.filter(read_at__isnull=True)
    try:
        page = max(int(request.query_params.get("page", 1)), 1)
    except ValueError:
        return Response({"detail": "Página inválida."}, status=status.HTTP_400_BAD_REQUEST)
    page_size = 20
    total = queryset.count()
    start = (page - 1) * page_size
    items = queryset[start:start + page_size]
    return Response({
        "count": total,
        "next": page + 1 if start + page_size < total else None,
        "previous": page - 1 if page > 1 else None,
        "results": DjenCommunicationSerializer(items, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def djen_communication_detail(request, pk):
    communication = _djen_queryset().filter(pk=pk).first()
    if not communication:
        return Response({"detail": "Publicação não encontrada."}, status=status.HTTP_404_NOT_FOUND)
    return Response(DjenCommunicationSerializer(communication).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_djen_read(request, pk):
    communication = _djen_queryset().filter(pk=pk).first()
    if not communication:
        return Response({"detail": "Publicação não encontrada."}, status=status.HTTP_404_NOT_FOUND)
    if communication.read_at is None:
        communication.read_at = timezone.now()
        communication.save(update_fields=("read_at", "updated_at"))
    return Response(DjenCommunicationSerializer(communication).data)
