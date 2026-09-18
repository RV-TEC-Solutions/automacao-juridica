from datetime import time

from django.conf import settings
from django.db import models


class AutomationSource(models.Model):
    code = models.SlugField(max_length=50, unique=True)
    system = models.CharField(max_length=80)
    tribunal = models.CharField(max_length=80)
    enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.system} / {self.tribunal}"


class UserProfile(models.Model):
    class Theme(models.TextChoices):
        LIGHT = "light", "Claro"
        DARK = "dark", "Escuro"
        SYSTEM = "system", "Seguir sistema"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="app_profile",
    )
    display_name = models.CharField(max_length=150)
    theme = models.CharField(
        max_length=10,
        choices=Theme.choices,
        default=Theme.SYSTEM,
    )
    collection_time = models.TimeField(default=time(6, 0))
    last_dashboard_visit = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.display_name


# faz a coleta do exped.
class AutomationRun(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        RUNNING = "running", "Executando"
        SUCCESS = "success", "Sucesso"
        FAILED = "failed", "Erro"

    class Trigger(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        MANUAL = "manual", "Manual"
        CATCH_UP = "catch_up", "Recuperação"

    source = models.ForeignKey(
        AutomationSource,
        on_delete=models.PROTECT,
        related_name="runs",
        null=True,
        blank=True,
    )
    trigger = models.CharField(
        max_length=20,
        choices=Trigger.choices,
        default=Trigger.MANUAL,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="requested_automation_runs",
        null=True,
        blank=True,
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    iniciada_em = models.DateTimeField(
        null=True,
        blank=True,
    )

    finalizada_em = models.DateTimeField(
        null=True,
        blank=True,
    )

    expedientes_encontrados = models.PositiveIntegerField(
        default=0,
    )

    capturas_html = models.PositiveIntegerField(
        default=0,
    )

    expedientes_criados = models.PositiveIntegerField(
        default=0,
    )

    expedientes_atualizados = models.PositiveIntegerField(
        default=0,
    )

    expedientes_resolvidos = models.PositiveIntegerField(default=0)

    mensagem_erro = models.TextField(
        blank=True,
    )

    criada_em = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return f"Execução {self.pk} - {self.get_status_display()}"

    class Meta:
        ordering = ("-criada_em",)
        constraints = [
            models.UniqueConstraint(
                fields=("source",),
                condition=models.Q(status__in=("pending", "running")),
                name="one_active_run_per_source",
            )
        ]
