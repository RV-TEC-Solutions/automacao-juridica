# vai orquestrar browser -> parser -> persistence
from django.utils import timezone

from automation.models import AutomationRun, AutomationSource
from automation.queue import enqueue_run

from .browser import abrir_pje
from .parser import extrair_expedientes_arquivo
from .persistence import salvar_expedientes

PJE_1G_SOURCE_CODE = "pje-tjrn"
PJE_2G_SOURCE_CODE = "pje2g-tjrn"

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
        execucao.save(update_fields=("status", "iniciada_em", "mensagem_erro"))

    try:
        arquivos = abrir_pje(source.code)

        expedientes_por_id = {}

        for arquivo in arquivos:
            dados = extrair_expedientes_arquivo(
                arquivo
            )

            for dado in dados:
                identificador = dado[
                    "identificador_pje"
                ]
                expedientes_por_id[
                    identificador
                ] = dado

        dados_unicos = list(
            expedientes_por_id.values()
        )

        resultado = salvar_expedientes(dados_unicos, source=source, run=execucao)
        execucao.status = (
            AutomationRun.Status.SUCCESS
        )

        execucao.capturas_html = len(
            arquivos
        )

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

        if source.code == PJE_1G_SOURCE_CODE:
            second_degree = AutomationSource.objects.get(code=PJE_2G_SOURCE_CODE)
            if second_degree.enabled:
                enqueue_run(
                    second_degree,
                    trigger=execucao.trigger,
                    requested_by=execucao.requested_by,
                    scheduled_for=execucao.scheduled_for,
                )

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
