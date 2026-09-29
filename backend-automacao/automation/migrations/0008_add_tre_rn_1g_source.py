from django.db import migrations


def add_tre_rn_1g_source(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    Source.objects.update_or_create(
        code="tre-rn-1g",
        defaults={
            "system": "PJe 1º Grau",
            "tribunal": "TRE-RN",
            "enabled": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("automation", "0007_automationrun_cancelled_status")]

    operations = [
        migrations.RunPython(add_tre_rn_1g_source, migrations.RunPython.noop),
    ]
