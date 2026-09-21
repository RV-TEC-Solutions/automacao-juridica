from datetime import datetime

from django.db import transaction
from django.utils import timezone

from expedientes.models import Expediente, ExpedienteEvent, Processo


PROCESS_FIELDS = ("tribunal", "classe", "assunto", "partes_texto", "unidade_judiciaria")
EXPEDIENT_FIELDS = (
    "tipo_pendencia", "acao_pje", "caixa", "destinatario", "tipo_documento",
    "meio_comunicacao", "data_expedicao", "prazo_texto",
    "status_prazo_fatal", "prazo_fatal", "ciencia_texto",
)


def normalizar_datetime(valor):
    """Converte ISO-8601 ou data brasileira em datetime com fuso horário."""
    if not valor:
        return None
    if isinstance(valor, datetime):
        resultado = valor
    else:
        texto = str(valor).strip()
        try:
            resultado = datetime.fromisoformat(texto)
        except ValueError:
            resultado = None
            for formato in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
                try:
                    resultado = datetime.strptime(texto, formato)
                    break
                except ValueError:
                    continue
            if resultado is None:
                raise ValueError(f"Data inválida recebida do PJe: {valor!r}")
    if timezone.is_naive(resultado):
        return timezone.make_aware(resultado)
    return resultado


def _serializar(valor):
    return valor.isoformat() if isinstance(valor, datetime) else valor


def _registrar_mudanca(changes, prefixo, campo, anterior, atual):
    if anterior != atual:
        changes[f"{prefixo}{campo}"] = {
            "before": _serializar(anterior), "after": _serializar(atual)
        }
        return True
    return False


def salvar_expediente(dado, *, source, run=None, seen_at=None):
    seen_at = seen_at or timezone.now()
    processo, _ = Processo.objects.get_or_create(
        numero=dado["numero_processo"],
        defaults={"tribunal": dado.get("tribunal", source.tribunal)},
    )
    process_changed = {}
    for campo in PROCESS_FIELDS:
        atual = dado.get(campo, source.tribunal if campo == "tribunal" else "")
        anterior = getattr(processo, campo)
        if _registrar_mudanca(process_changed, "processo.", campo, anterior, atual):
            setattr(processo, campo, atual)
    if process_changed:
        campos = tuple(key.removeprefix("processo.") for key in process_changed)
        processo.save(update_fields=campos + ("atualizado_em",))

    expediente = Expediente.objects.filter(
        source=source,
        identificador_pje=dado["identificador_pje"],
    ).first()
    created = expediente is None
    if created:
        expediente = Expediente(
            identificador_pje=dado["identificador_pje"],
            processo=processo,
            source=source,
            status_prazo_fatal=dado["status_prazo_fatal"],
        )

    changes = dict(process_changed)
    if not created and expediente.processo_id != processo.id:
        _registrar_mudanca(changes, "", "processo_id", expediente.processo_id, processo.id)
    expediente.processo = processo
    expediente.source = source
    for campo in EXPEDIENT_FIELDS:
        atual = dado.get(campo, "")
        if campo in ("data_expedicao", "prazo_fatal"):
            atual = normalizar_datetime(atual)
        anterior = getattr(expediente, campo, None)
        if not created:
            _registrar_mudanca(changes, "", campo, anterior, atual)
        setattr(expediente, campo, atual)

    if not created and not expediente.ativo:
        _registrar_mudanca(changes, "", "ativo", False, True)
    expediente.ativo = True
    expediente.arquivado_em = None
    expediente.visto_na_ultima_coleta_em = seen_at
    expediente.save()

    if created:
        ExpedienteEvent.objects.create(
            expediente=expediente, run=run, kind=ExpedienteEvent.Kind.NEW
        )
    elif changes:
        ExpedienteEvent.objects.create(
            expediente=expediente, run=run,
            kind=ExpedienteEvent.Kind.UPDATED, changes=changes,
        )
    return expediente, created, bool(changes)


def salvar_expedientes(dados, *, source, run=None, reconcile_missing=True):
    """Persiste uma captura completa e reconcilia itens que deixaram a caixa."""
    criados = atualizados = resolvidos = 0
    seen_at = timezone.now()
    identificadores = {str(dado["identificador_pje"]) for dado in dados}

    with transaction.atomic():
        for dado in dados:
            _, criado, alterado = salvar_expediente(
                dado, source=source, run=run, seen_at=seen_at
            )
            criados += int(criado)
            atualizados += int(not criado and alterado)

        if reconcile_missing:
            ausentes = Expediente.objects.filter(source=source, ativo=True)
            if identificadores:
                ausentes = ausentes.exclude(identificador_pje__in=identificadores)
            for expediente in ausentes.select_for_update():
                expediente.ativo = False
                expediente.arquivado_em = seen_at
                expediente.save(update_fields=("ativo", "arquivado_em", "atualizado_em"))
                ExpedienteEvent.objects.create(
                    expediente=expediente, run=run,
                    kind=ExpedienteEvent.Kind.RESOLVED,
                    changes={"ativo": {"before": True, "after": False}},
                )
                resolvidos += 1

    return {
        "criados": criados, "atualizados": atualizados,
        "resolvidos": resolvidos, "total": len(dados),
    }
