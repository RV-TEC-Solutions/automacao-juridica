from django.db import migrations, models
import django.db.models.deletion


TRF5_SOURCES = (
    ("trf5-2g-tru", "PJe 2º Grau / TRU"),
    ("varas-justica-comum", "PJe 1º Grau — Varas Federais"),
    ("jef-5-regiao", "PJe 1º Grau — JEF"),
    ("trs-5-regiao", "PJe — Turmas Recursais"),
    ("tru-5-regiao", "PJe 2º Grau / TRU — perfil alternativo"),
)


def add_trf5_sources(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    for code, system in TRF5_SOURCES:
        Source.objects.update_or_create(
            code=code,
            defaults={"system": system, "tribunal": "TRF5", "enabled": True},
        )


class Migration(migrations.Migration):
    dependencies = [("automation", "0005_add_trt21_sources_and_run_info")]

    operations = [
        migrations.CreateModel(
            name="Notice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fingerprint", models.CharField(max_length=64, unique=True)),
                ("title", models.CharField(max_length=500)),
                ("included_by", models.CharField(blank=True, max_length=255)),
                ("included_at", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateField(blank=True, null=True)),
                ("raw_html", models.TextField()),
                ("content_html", models.TextField()),
                ("content_text", models.TextField()),
                ("links", models.JSONField(blank=True, default=list)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-published_at", "-created_at")},
        ),
        migrations.CreateModel(
            name="NoticeSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("collected_at", models.DateTimeField(auto_now=True)),
                ("pje_confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("notice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="source_links", to="automation.notice")),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="notice_links", to="automation.automationsource")),
            ],
        ),
        migrations.AddConstraint(
            model_name="noticesource",
            constraint=models.UniqueConstraint(fields=("notice", "source"), name="unique_notice_per_source"),
        ),
        migrations.RunPython(add_trf5_sources, migrations.RunPython.noop),
    ]
