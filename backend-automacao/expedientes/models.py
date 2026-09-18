from django.db import models


class Processo(models.Model):
    numero = models.CharField(
        max_length=30,
        unique=True,
    )

    tribunal = models.CharField(
        max_length=30,
        default="TJRN",
    )

    # Exemplos: "CumSenFaz", "ProceComCiv", "ExFis".
    classe = models.CharField(
        max_length=150,
        blank=True,
    )

    # Ex.: "Obrigação de Fazer / Não Fazer", "Juros".
    assunto = models.CharField(
        max_length=255,
        blank=True,
    )

    # Ex.: "PARTE A X MUNICÍPIO DE NATAL".
    partes_texto = models.TextField(
        blank=True,
    )

    # Ex.: "Vara Única da Comarca de Caraúbas".
    unidade_judiciaria = models.CharField(
        max_length=255,
        blank=True,
    )

    criado_em = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        blank=True,
        null=True,
    )

    def __str__(self):
        return self.numero


class Expediente(models.Model):

    class TipoPendencia(models.TextChoices):
        CIENCIA = "ciencia", "Pendente de ciência"
        RESPOSTA = "resposta", "Pendente de resposta"
        NAO_IDENTIFICADA = "nao_identificada", "Não identificada"

    class AcaoPJe(models.TextChoices):
        TOMAR_CIENCIA = "tomar_ciencia", "Tomar ciência"
        SEM_INTERESSE = "sem_interesse", "Sem interesse"
        RESPONDER = "responder", "Responder"

    class StatusPrazoFatal(models.TextChoices):
        CALCULADO = "calculado", "Calculado"
        EM_CALCULO = "em_calculo", "Em cálculo"
        SEM_PRAZO = "sem_prazo", "Sem prazo"

    processo = models.ForeignKey(
        Processo,
        on_delete=models.PROTECT,
        related_name="expedientes",
    )

    source = models.ForeignKey(
        "automation.AutomationSource",
        on_delete=models.PROTECT,
        related_name="expedientes",
        null=True,
        blank=True,
    )

    tipo_pendencia = models.CharField(
        max_length=20,
        choices=TipoPendencia.choices,
        blank=True,
        null=True,
    )

    acao_pje = models.CharField(
        max_length=20,
        choices=AcaoPJe.choices,
        blank=True,
        null=True,
    )

    # Identificador do expediente no PJe.
    # Ex.: Intimação (29908000) -> "29908000".
    identificador_pje = models.CharField(
        max_length=50,
    )

    caixa = models.CharField(
        max_length=255,
        blank=True,
    )

    destinatario = models.CharField(
        max_length=255,
        blank=True,
    )

    # Ex.: "Intimação", "Citação".
    tipo_documento = models.CharField(
        max_length=100,
        blank=True,
    )

    # Ex.: "Diário Eletrônico", "Correios",
    # "Expedição eletrônica", "Central de Mandados".
    meio_comunicacao = models.CharField(
        max_length=100,
        blank=True,
    )

    # Momento em que o expediente foi expedido segundo o PJe.
    data_expedicao = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Texto original exibido pelo PJe:
    # "10 dias", "30 dias", "2 meses", "sem prazo".
    prazo_texto = models.CharField(
        max_length=100,
        blank=True,
    )

    # Distingue os casos em que prazo_fatal é nulo:
    # prazo em cálculo ou expediente sem prazo.
    status_prazo_fatal = models.CharField(
        max_length=20,
        choices=StatusPrazoFatal.choices,
    )

    prazo_fatal = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Ex.: "FULANO tomou ciência em ...".
    ciencia_texto = models.TextField(
        blank=True,
    )

    capturado_em = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
    )

    atualizado_em = models.DateTimeField(
        auto_now=True,
        blank=True,
        null=True,
    )

    ativo = models.BooleanField(default=True)
    visto_na_ultima_coleta_em = models.DateTimeField(null=True, blank=True)
    arquivado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.processo.numero} — "
            f"{self.tipo_documento} ({self.identificador_pje})"
        )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source", "identificador_pje"),
                name="unique_expediente_per_source",
            )
        ]


class ExpedienteEvent(models.Model):
    class Kind(models.TextChoices):
        NEW = "new", "Novo"
        UPDATED = "updated", "Alterado"
        RESOLVED = "resolved", "Resolvido"

    expediente = models.ForeignKey(
        Expediente,
        on_delete=models.CASCADE,
        related_name="events",
    )
    run = models.ForeignKey(
        "automation.AutomationRun",
        on_delete=models.SET_NULL,
        related_name="events",
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("kind", "created_at")),
            models.Index(fields=("read_at", "created_at")),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.expediente}"
