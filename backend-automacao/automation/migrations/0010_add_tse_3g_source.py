from django.db import migrations


def add_tse_3g_source(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    Source.objects.update_or_create(
        code="tse-3g",
        defaults={
            "system": "PJe 3º Grau",
            "tribunal": "TSE",
            "enabled": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("automation", "0009_add_tre_rn_2g_source")]

    operations = [
        migrations.RunPython(add_tse_3g_source, migrations.RunPython.noop),
    ]
