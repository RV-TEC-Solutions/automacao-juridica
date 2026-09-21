# vai orquestrar browser -> parser -> persistence
from django.utils import timezone

from automation.models import AutomationRun, AutomationSource
from automation.queue import enqueue_run

from .browser import abrir_pje
from .parser import extrair_expedientes_arquivo
from .persistence import salvar_expedientes
from .sources import PJE_SOURCE_ORDER, get_source_profile

def executar_coleta(execucao=None):
    if execucao is None:
        source = AutomationSource.objects.get(code="pje-tjrn")
        execucao = AutomationRun.objects.create(
            source=source, status=AutomationRun.Status.RUNNING,
            iniciada_em=timezone.now(),
        )
    else:
        source = execucao.source
        execucao.status = AutomationRun.Status.RUNNING
        execucao.iniciada_em = timezone.now()
        execucao.mensagem_erro = ""
        execucao.mensagem_info = ""
        execucao.save(update_fields=("status", "iniciada_em", "mensagem_erro", "mensagem_info"))

    try:
        capture = abrir_pje(source.code)
        profile = get_source_profile(source.code)
        if profile.collector == "trt21":
            dados_unicos = capture.records
            mensagem_info = capture.empty_message
            capturas_html = 0
        else:
            expedientes_por_id = {}
            for arquivo in capture:
                for dado in extrair_expedientes_arquivo(arquivo):
                    expedientes_por_id[dado["identificador_pje"]] = dado
            dados_unicos = list(expedientes_por_id.values())
            mensagem_info = ""
            capturas_html = len(capture)

        resultado = salvar_expedientes(
            dados_unicos, source=source, run=execucao,
            reconcile_missing=profile.reconcile_missing,
        )
        execucao.status = (
            AutomationRun.Status.SUCCESS
        )

        execucao.capturas_html = capturas_html
        execucao.mensagem_info = mensagem_info

        execucao.expedientes_encontrados = (
            len(dados_unicos)
        )

        execucao.expedientes_criados = (
            resultado["criados"]
        )

        execucao.expedientes_atualizados = (
            resultado["atualizados"]
        )

        execucao.expedientes_resolvidos = resultado["resolvidos"]

        execucao.finalizada_em = (
            timezone.now()
        )

        execucao.save()

        try:
            current_index = PJE_SOURCE_ORDER.index(source.code)
        except ValueError:
            current_index = len(PJE_SOURCE_ORDER)
        for next_code in PJE_SOURCE_ORDER[current_index + 1:]:
            next_source = AutomationSource.objects.get(code=next_code)
            if next_source.enabled:
                enqueue_run(
                    next_source,
                    trigger=execucao.trigger,
                    requested_by=execucao.requested_by,
                    scheduled_for=execucao.scheduled_for,
                )
                break

        return resultado

    except Exception as erro:
        execucao.status = (
            AutomationRun.Status.FAILED
        )

        execucao.mensagem_erro = str(erro)
        execucao.finalizada_em = (
            timezone.now()
        )

        execucao.save()

        raise
