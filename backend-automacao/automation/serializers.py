from rest_framework import serializers

from .models import DjenCommunication, Notice


class NoticeSerializer(serializers.ModelSerializer):
    sources = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()

    class Meta:
        model = Notice
        fields = (
            "id", "title", "included_by", "included_at", "published_at",
            "content_html", "content_text", "links", "read_at", "created_at",
            "updated_at", "sources", "unread",
        )

    def get_sources(self, obj):
        return [
            {
                "code": link.source.code,
                "system": link.source.system,
                "tribunal": link.source.tribunal,
                "pje_confirmed_at": link.pje_confirmed_at,
            }
            for link in obj.source_links.all()
        ]

    def get_unread(self, obj):
        return obj.read_at is None


class DjenCommunicationSerializer(serializers.ModelSerializer):
    processo = serializers.SerializerMethodField()
    recipients = serializers.SerializerMethodField()
    attorneys = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()

    class Meta:
        model = DjenCommunication
        fields = (
            "id", "api_id", "numero_comunicacao", "hash", "data_disponibilizacao",
            "tribunal", "orgao", "tipo_comunicacao", "meio", "link_inteiro_teor",
            "tipo_documento", "nome_classe", "codigo_classe", "texto", "read_at",
            "collected_at", "updated_at", "unread", "processo", "recipients", "attorneys",
        )

    def get_processo(self, obj):
        return {"id": obj.processo_id, "numero": obj.processo.numero}

    def get_recipients(self, obj):
        return [{"name": item.name, "pole": item.pole} for item in obj.recipients.all()]

    def get_attorneys(self, obj):
        return [
            {"name": item.name, "oab_number": item.oab_number, "oab_state": item.oab_state}
            for item in obj.attorneys.all()
        ]

    def get_unread(self, obj):
        return obj.read_at is None
