from rest_framework import serializers

from .models import Expediente, ExpedienteEvent, Processo


class ProcessoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Processo
        fields = ("id", "numero", "tribunal", "classe", "assunto", "partes_texto", "unidade_judiciaria")


class EventSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ExpedienteEvent
        fields = ("id", "kind", "kind_label", "changes", "created_at", "read_at")


class ExpedienteSerializer(serializers.ModelSerializer):
    processo = ProcessoSerializer(read_only=True)
    source = serializers.SerializerMethodField()
    latest_event = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()
    tipo_pendencia_label = serializers.CharField(source="get_tipo_pendencia_display", read_only=True)
    acao_pje_label = serializers.CharField(source="get_acao_pje_display", read_only=True)
    status_prazo_fatal_label = serializers.CharField(source="get_status_prazo_fatal_display", read_only=True)

    class Meta:
        model = Expediente
        fields = (
            "id", "processo", "source", "tipo_pendencia", "tipo_pendencia_label",
            "acao_pje", "acao_pje_label", "identificador_pje", "caixa",
            "destinatario", "tipo_documento", "meio_comunicacao", "data_expedicao",
            "prazo_texto", "status_prazo_fatal", "status_prazo_fatal_label",
            "prazo_fatal", "ciencia_texto", "capturado_em", "atualizado_em",
            "ativo", "arquivado_em", "latest_event", "unread",
        )

    def get_source(self, obj):
        if not obj.source:
            return None
        return {"code": obj.source.code, "system": obj.source.system, "tribunal": obj.source.tribunal}

    def get_latest_event(self, obj):
        event = next(iter(obj.events.all()), None)
        return EventSerializer(event).data if event else None

    def get_unread(self, obj):
        return any(event.read_at is None for event in obj.events.all())
