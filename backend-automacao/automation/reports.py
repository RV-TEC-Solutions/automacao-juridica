from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .reporting import collection_range, local_date, local_datetime, pdf_response
from .views import filtered_djen_queryset
from expedientes.models import Cliente


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
        if scope == "list":
            params = request.query_params
            queryset = filtered_djen_queryset(params)
            start = params.get("collected_from") or ""
            end = params.get("collected_to") or ""
        else:
            first, last, _, _ = collection_range(
                request.query_params, history=scope == "history", default_today=scope != "history",
                from_key="collected_from", to_key="collected_to",
            )
            start, end = first.isoformat(), last.isoformat()
            params = {"collected_from": start, "collected_to": end}
            queryset = filtered_djen_queryset(params)
    except (ValueError, OverflowError) as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    count = queryset.count()
    if not count:
        return Response({"detail": "Nenhuma publicação encontrada para a exportação."}, status=status.HTTP_404_NOT_FOUND)
    description = "Publicações Processuais"
    if start or end:
        description += f" · coleta: {start or 'início'} a {end or 'hoje'}"
    if scope == "list":
        for key, label in (("q", "busca"), ("tipo_comunicacao", "comunicação"), ("read", "leitura"),
                           ("date_from", "disponibilização de"), ("date_to", "disponibilização até"), ("ordering", "ordenação")):
            if value := request.query_params.get(key):
                description += f" · {label}: {value}"
        if tribunals := request.query_params.getlist("tribunal"):
            description += " · tribunais: " + ", ".join(tribunals)
        if states := [value for value in request.query_params.getlist("uf") if value]:
            description += " · UFs: " + ", ".join(value.strip().upper() for value in states)
        if clients := [value for value in request.query_params.getlist("client") if value]:
            description += " · clientes: " + ", ".join(Cliente.objects.filter(pk__in=clients).values_list("nome", flat=True))
    records = (_record(item) for item in queryset.iterator(chunk_size=200))
    return pdf_response(title="Publicações Processuais", subtitle=description, count=count,
                        filename=f"publicacoes-processuais-{start or 'inicio'}-{end or 'todos'}.pdf", records=records)
