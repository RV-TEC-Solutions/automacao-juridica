from django.db import migrations


def add_pje2g_source(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    Source.objects.get_or_create(
        code="pje2g-tjrn",
        defaults={
            "system": "PJe 2º Grau",
            "tribunal": "TJRN",
            "enabled": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0003_sources_profiles_and_queue"),
    ]

    operations = [
        migrations.RunPython(add_pje2g_source, migrations.RunPython.noop),
    ]
