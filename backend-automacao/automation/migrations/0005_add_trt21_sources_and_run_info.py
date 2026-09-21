from django.db import migrations, models


def add_trt21_sources(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    for code, system in (("trt21", "PJe 1º Grau"), ("trt21-2g", "PJe 2º Grau")):
        Source.objects.get_or_create(
            code=code,
            defaults={"system": system, "tribunal": "TRT21", "enabled": True},
        )


class Migration(migrations.Migration):
    dependencies = [("automation", "0004_add_pje2g_source")]

    operations = [
        migrations.AddField(
            model_name="automationrun",
            name="mensagem_info",
            field=models.TextField(blank=True),
        ),
        migrations.RunPython(add_trt21_sources, migrations.RunPython.noop),
    ]
