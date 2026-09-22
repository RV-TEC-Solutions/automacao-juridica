from rest_framework import serializers

from .models import Notice


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
