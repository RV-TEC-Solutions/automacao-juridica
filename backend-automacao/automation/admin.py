from django.contrib import admin

from .models import AutomationRun, AutomationSource, UserProfile

admin.site.register(AutomationSource)
admin.site.register(UserProfile)


@admin.register(AutomationRun)
class AutomationRunAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "source",
        "trigger",
        "status",
        "iniciada_em",
        "finalizada_em",
        "capturas_html",
        "expedientes_encontrados",
        "expedientes_criados",
        "expedientes_atualizados",
        "expedientes_resolvidos",
    )
    list_filter = ("status",)
    ordering = ("-criada_em",)
