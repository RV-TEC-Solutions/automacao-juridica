import uuid
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


class Notice(models.Model):
    """Comunicado canônico exibido pelo Quadro de Avisos do PJe."""

    fingerprint = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=500)
    included_by = models.CharField(max_length=255, blank=True)
    included_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateField(null=True, blank=True)
    raw_html = models.TextField()
    content_html = models.TextField()
    content_text = models.TextField()
    links = models.JSONField(default=list, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-published_at", "-created_at")

    def __str__(self):
        return self.title


class NoticeSource(models.Model):
    """Rastreia a descoberta e a confirmação externa de um aviso por fonte."""

    notice = models.ForeignKey(
        Notice, on_delete=models.CASCADE, related_name="source_links"
    )
    source = models.ForeignKey(
        AutomationSource, on_delete=models.PROTECT, related_name="notice_links"
    )
    collected_at = models.DateTimeField(auto_now=True)
    pje_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("notice", "source"), name="unique_notice_per_source"
            )
        ]


class DjenCommunication(models.Model):
    """Publicação imutável consultada na API pública do DJEN."""

    source = models.ForeignKey(
        AutomationSource, on_delete=models.PROTECT, related_name="djen_communications"
    )
    run = models.ForeignKey(
        "AutomationRun", on_delete=models.SET_NULL, related_name="djen_communications",
        null=True, blank=True,
    )
    processo = models.ForeignKey(
        "expedientes.Processo", on_delete=models.PROTECT,
        related_name="djen_communications",
    )
    api_id = models.BigIntegerField(null=True, blank=True)
    numero_comunicacao = models.BigIntegerField()
    hash = models.CharField(max_length=128, blank=True)
    data_disponibilizacao = models.DateField()
    tribunal = models.CharField(max_length=30)
    orgao = models.CharField(max_length=255, blank=True)
    tipo_comunicacao = models.CharField(max_length=120, blank=True)
    meio = models.CharField(max_length=120, blank=True)
    link_inteiro_teor = models.URLField(max_length=1000, blank=True)
    tipo_documento = models.CharField(max_length=120, blank=True)
    nome_classe = models.CharField(max_length=255, blank=True)
    codigo_classe = models.CharField(max_length=50, blank=True)
    texto = models.TextField(blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-data_disponibilizacao", "-numero_comunicacao")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "numero_comunicacao"),
                name="unique_djen_communication_per_source",
            )
        ]
        indexes = [
            models.Index(fields=("data_disponibilizacao", "tribunal"), name="automation__data_di_98e3e9_idx"),
            models.Index(fields=("read_at", "data_disponibilizacao"), name="automation__read_at_0b4038_idx"),
        ]

    def __str__(self):
        return f"{self.processo.numero} — {self.tipo_comunicacao}"


class DjenRecipient(models.Model):
    communication = models.ForeignKey(
        DjenCommunication, on_delete=models.CASCADE, related_name="recipients"
    )
    name = models.CharField(max_length=500)
    pole = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ("id",)


class DjenAttorney(models.Model):
    communication = models.ForeignKey(
        DjenCommunication, on_delete=models.CASCADE, related_name="attorneys"
    )
    name = models.CharField(max_length=500)
    oab_number = models.CharField(max_length=30, blank=True)
    oab_state = models.CharField(max_length=2, blank=True)

    class Meta:
        ordering = ("id",)


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
        CANCELLED = "cancelled", "Interrompida"

    class Trigger(models.TextChoices):
        SCHEDULED = "scheduled", "Agendada"
        MANUAL = "manual", "Manual"
        RERUN = "rerun", "Reexecução de fonte"
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
    cycle_id = models.UUIDField(default=uuid.uuid4, db_index=True, editable=False)

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

    descartada_em = models.DateTimeField(null=True, blank=True, db_index=True)

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

    mensagem_info = models.TextField(
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
