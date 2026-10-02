from datetime import date, datetime, timedelta
import re

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from automation.reporting import LOCAL_TZ, collection_range, local_datetime, pdf_response
from .models import ExpedienteEvent
from .views import expediente_queryset


METRICS = {
    "new": ("Novos", "novos", {"event_kind": "new"}),
    "updated": ("Alterados", "alterados", {"event_kind": "updated"}),
    "unread": ("Não lidos", "nao-lidos", {"read": "unread"}),
    "urgent": ("Urgentes", "urgentes", {"deadline": "urgent"}),
    "next_week": ("Até próxima semana", "ate-proxima-semana", {"deadline": "next_week"}),
    "calculating": ("Prazos em cálculo", "prazos-em-calculo", {"deadline": "calculating"}),
}

CHANGE_LABELS = {
    "tipo_pendencia": "Pendência", "acao_pje": "Ação no PJe", "caixa": "Caixa",
    "destinatario": "Destinatário", "tipo_documento": "Documento", "meio_comunicacao": "Meio",
    "data_expedicao": "Expedição", "prazo_texto": "Prazo original",
    "status_prazo_fatal": "Situação do prazo", "prazo_fatal": "Prazo fatal",
    "ciencia_texto": "Ciência", "processo.classe": "Classe", "processo.assunto": "Assunto",
    "processo.partes_texto": "Partes", "processo.unidade_judiciaria": "Unidade judiciária",
    "ativo": "Situação",
}


def _value(value):
    if isinstance(value, bool):
        return "Sim" if value else "Não"
    if value is None or value == "":
        return "Não informado"
    if isinstance(value, datetime):
        return local_datetime(value)
    return str(value)


def _record(item, start_at, end_at):
    process = item.processo
    source = item.source
    events = sorted((event for event in item.events.all() if start_at <= event.created_at < end_at),
                    key=lambda event: (event.created_at, event.pk))
    fields = [
        ("Número do processo", process.numero),
        ("Tribunal", process.tribunal),
        ("Classe", process.classe), ("Assunto", process.assunto),
        ("Partes", process.partes_texto), ("Unidade judiciária", process.unidade_judiciaria),
        ("Fonte", f"{source.system} · {source.tribunal}" if source else None),
        ("Identificador no PJe", item.identificador_pje),
        ("Tipo de documento", item.tipo_documento), ("Destinatário", item.destinatario),
        ("Caixa", item.caixa), ("Meio de comunicação", item.meio_comunicacao),
        ("Pendência", item.get_tipo_pendencia_display() if item.tipo_pendencia else None),
        ("Ação no PJe", item.get_acao_pje_display() if item.acao_pje else None),
        ("Expedido em", local_datetime(item.data_expedicao)),
        ("Prazo original", re.sub(r"\b1 dias\b", "1 dia", item.prazo_texto, flags=re.IGNORECASE)),
        ("Situação do prazo", item.get_status_prazo_fatal_display()),
        ("Prazo fatal", local_datetime(item.prazo_fatal)),
        ("Situação atual", "Ativo" if item.ativo else "Resolvido"),
        ("Coletado inicialmente em", local_datetime(item.capturado_em)),
        ("Atualizado em", local_datetime(item.atualizado_em)),
        ("Arquivado em", local_datetime(item.arquivado_em)),
        ("Leitura", "Não lido" if any(event.read_at is None for event in item.events.all()) else "Lido"),
        ("Registro de ciência", item.ciencia_texto),
    ]
    if events:
        fields.append(("Eventos no período", "; ".join(f"{event.get_kind_display()} em {local_datetime(event.created_at)}" for event in events)))
    for event in events:
        for key, change in event.changes.items():
            if isinstance(change, dict):
                fields.append((f"{CHANGE_LABELS.get(key, key)} · {local_datetime(event.created_at)}",
                               f"{_value(change.get('before'))} → {_value(change.get('after'))}"))
    return f"{process.numero} · {item.tipo_documento or 'Expediente'}", fields


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_expedientes(request):
    scope = request.query_params.get("scope", "list")
    mode = request.query_params.get("mode", "sintetico")
    if mode not in ("sintetico", "analitico"):
        return Response({"detail": "Formato inválido."}, status=status.HTTP_400_BAD_REQUEST)
    if scope not in ("list", "overview", "history"):
        return Response({"detail": "Escopo inválido."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        if scope == "history":
            start, end, start_at, end_at = collection_range(request.query_params, history=True)
            event_ids = ExpedienteEvent.objects.filter(kind="new", created_at__gte=start_at, created_at__lt=end_at).values("expediente_id")
            queryset = expediente_queryset({}).filter(pk__in=event_ids)
            description = f"Histórico de novos expedientes · {start:%d/%m/%Y} a {end:%d/%m/%Y}"
            file_suffix = f"historico-{start:%Y%m%d}-{end:%Y%m%d}"
        elif scope == "overview":
            metric = request.query_params.get("metric", "new")
            if metric not in METRICS:
                return Response({"detail": "Card inválido."}, status=status.HTTP_400_BAD_REQUEST)
            label, filename_label, filters = METRICS[metric]
            today = timezone.localdate(timezone=LOCAL_TZ)
            start_at = datetime.combine(today, datetime.min.time(), tzinfo=LOCAL_TZ)
            end_at = start_at + timedelta(days=1)
            if metric in ("new", "updated"):
                filters = {**filters, "date_from": today.isoformat(), "date_to": today.isoformat()}
            queryset = expediente_queryset(filters)
            description = f"Visão geral · {label} · " + (f"eventos de {today:%d/%m/%Y}" if metric in ("new", "updated") else f"estado atual, alterações de {today:%d/%m/%Y}")
            file_suffix = f"{filename_label}-{today:%Y%m%d}"
        else:
            start = date.fromisoformat(request.query_params["date_from"]) if request.query_params.get("date_from") else None
            end = date.fromisoformat(request.query_params["date_to"]) if request.query_params.get("date_to") else None
            if start and end and start > end:
                raise ValueError("A data inicial não pode ser posterior à data final.")
            if end == date.max:
                raise ValueError("Data final inválida.")
            start_at = datetime.combine(start, datetime.min.time(), tzinfo=LOCAL_TZ) if start else datetime.min.replace(tzinfo=LOCAL_TZ)
            end_at = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=LOCAL_TZ) if end else datetime.max.replace(tzinfo=LOCAL_TZ)
            queryset = expediente_queryset(request.query_params)
            description = "Consulta de expedientes"
            if start and end:
                description += f" · coleta de {start:%d/%m/%Y} a {end:%d/%m/%Y}"
            elif start:
                description += f" · coleta a partir de {start:%d/%m/%Y}"
            elif end:
                description += f" · coleta até {end:%d/%m/%Y}"
            file_suffix = f"consulta-{start:%Y%m%d}" if start else "consulta-todos"
            if end:
                file_suffix += f"-{end:%Y%m%d}"
            active_filters = [(label, request.query_params.get(key)) for key, label in (
                ("q", "busca"), ("source", "fonte"), ("pending_type", "pendência"),
                ("deadline", "prazo"), ("read", "leitura"), ("event_kind", "evento"),
            ) if request.query_params.get(key)]
            if active_filters:
                description += " · " + ", ".join(f"{label}: {value}" for label, value in active_filters)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    count = queryset.count()
    if not count:
        return Response({"detail": "Nenhum expediente encontrado para a exportação."}, status=status.HTTP_404_NOT_FOUND)
    queryset = queryset.prefetch_related(None).prefetch_related(
        Prefetch("events", queryset=ExpedienteEvent.objects.order_by("created_at", "id"))
    )
    records = (_record(item, start_at, end_at) for item in queryset.iterator(chunk_size=200))
    urgent = (scope == "overview" and request.query_params.get("metric") == "urgent") or (
        scope == "list" and request.query_params.get("deadline") == "urgent"
    )
    return pdf_response(title="RELATÓRIO DE EXPEDIENTES" + (" URGENTES" if urgent else ""),
                        subtitle=description, count=count,
                        filename=f"expedientes-{file_suffix}-{mode}.pdf", records=records,
                        compact=mode == "sintetico", urgent=urgent)
