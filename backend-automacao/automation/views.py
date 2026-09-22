import os
from pathlib import Path

from dotenv import dotenv_values

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AutomationRun, AutomationSource, Notice, UserProfile
from .serializers import NoticeSerializer
from .queue import enqueue_run, first_enabled_source


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
        "id": run.id, "status": run.status, "trigger": run.trigger,
        "created_at": run.criada_em, "started_at": run.iniciada_em,
        "finished_at": run.finalizada_em, "error": run.mensagem_erro,
        "message": run.mensagem_info,
        "found": run.expedientes_encontrados, "created": run.expedientes_criados,
        "updated": run.expedientes_atualizados, "resolved": run.expedientes_resolvidos,
        "source": run.source.code if run.source else None,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def runs(request):
    if request.method == "POST":
        requested_code = request.data.get("source", "pje-tjrn")
        requested_source = AutomationSource.objects.filter(code=requested_code).first()
        if not requested_source:
            return Response({"detail": "Fonte não encontrada."}, status=status.HTTP_404_NOT_FOUND)
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
            run = enqueue_run(source, AutomationRun.Trigger.MANUAL, requested_by=request.user)
        except ValueError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(_run_payload(run), status=status.HTTP_202_ACCEPTED)
    return Response([_run_payload(run) for run in AutomationRun.objects.select_related("source")[:20]])


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
