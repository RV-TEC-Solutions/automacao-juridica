from django.contrib import admin

from .models import Expediente, ExpedienteEvent, Processo

admin.site.register(ExpedienteEvent)


@admin.register(Processo)
class ProcessoAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "tribunal",
        "classe",
        "assunto",
        "unidade_judiciaria",
        "atualizado_em",
    )
    search_fields = (
        "numero",
        "tribunal",
        "classe",
        "assunto",
        "partes_texto",
        "unidade_judiciaria",
    )
    list_filter = ("tribunal", "classe",)
    ordering = ("numero",)


@admin.register(Expediente)
class ExpedienteAdmin(admin.ModelAdmin):
    list_display = (
        "identificador_pje",
        "processo",
        "tipo_documento",
        "tipo_pendencia",
        "acao_pje",
        "caixa",
        "prazo_fatal",
        "capturado_em",
    )
    list_filter = (
        "tipo_pendencia",
        "acao_pje",
        "status_prazo_fatal",
        "meio_comunicacao",
    )
    search_fields = (
        "identificador_pje",
        "processo__numero",
        "destinatario",
    )
    autocomplete_fields = ("processo",)
    date_hierarchy = "data_expedicao"
    list_select_related = ("processo",)
    ordering = ("prazo_fatal", "-data_expedicao")
    fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "processo",
                    "identificador_pje",
                    "tipo_documento",
                    "meio_comunicacao",
                    "caixa",
                    "destinatario",
                )
            },
        ),
        (
            "Prazo",
            {
                "fields": (
                    "prazo_texto",
                    "status_prazo_fatal",
                    "prazo_fatal",
                )
            },
        ),
        (
            "Expedição e ciência",
            {
                "fields": (
                    "data_expedicao",
                    "ciencia_texto",
                )
            },
        ),
    )
