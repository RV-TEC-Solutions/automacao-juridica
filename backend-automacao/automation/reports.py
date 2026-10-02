from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .reporting import collection_range, local_date, local_datetime, pdf_response
from .views import filtered_djen_queryset


def _record(item):
    fields = [
        ("Número do processo", item.processo.numero),
        ("Número da comunicação", item.numero_comunicacao),
        ("Tribunal", item.tribunal), ("Órgão", item.orgao),
        ("Tipo de comunicação", item.tipo_comunicacao), ("Meio", item.meio),
        ("Tipo de documento", item.tipo_documento), ("Classe", item.nome_classe),
        ("Código da classe", item.codigo_classe),
        ("Disponibilizado em", local_date(item.data_disponibilizacao)),
        ("Coletado em", local_datetime(item.collected_at)),
        ("Situação de leitura", "Não lida" if item.read_at is None else "Lida"),
        ("Partes e destinatários", "; ".join(f"{person.name} ({person.pole})" if person.pole else person.name for person in item.recipients.all())),
        ("Advogados", "; ".join(f"{lawyer.name} · OAB {lawyer.oab_state}-{lawyer.oab_number}" for lawyer in item.attorneys.all())),
        ("Texto publicado", item.texto),
        ("Link para o inteiro teor", item.link_inteiro_teor),
    ]
    return f"{item.processo.numero} · Comunicação {item.numero_comunicacao}", fields


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_publications(request):
    scope = request.query_params.get("scope", "list")
    if scope not in ("list", "overview", "history"):
        return Response({"detail": "Escopo inválido."}, status=status.HTTP_400_BAD_REQUEST)
    try:
        start, end, _, _ = collection_range(
            request.query_params, history=scope == "history", default_today=scope != "history",
            from_key="collected_from", to_key="collected_to",
        )
        if scope == "overview":
            params = {"collected_from": start.isoformat(), "collected_to": end.isoformat()}
        elif scope == "history":
            params = {"collected_from": start.isoformat(), "collected_to": end.isoformat()}
        else:
            params = request.query_params.copy()
            params["collected_from"] = start.isoformat()
            params["collected_to"] = end.isoformat()
        queryset = filtered_djen_queryset(params).order_by("-collected_at", "-id")
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    count = queryset.count()
    if not count:
        return Response({"detail": "Nenhuma publicação encontrada para a exportação."}, status=status.HTTP_404_NOT_FOUND)
    description = f"Publicações Processuais · coletas de {start:%d/%m/%Y} a {end:%d/%m/%Y}"
    if scope == "list" and request.query_params.get("q"):
        description += f" · busca: {request.query_params['q']}"
    records = (_record(item) for item in queryset.iterator(chunk_size=200))
    return pdf_response(title="Publicações Processuais", subtitle=description, count=count,
                        filename=f"publicacoes-processuais-{start:%Y%m%d}-{end:%Y%m%d}.pdf", records=records)
