from django.db import migrations, models


def backfill(apps, schema_editor):
    Expediente = apps.get_model("expedientes", "Expediente")
    for active in (True, False):
        Expediente.objects.using(schema_editor.connection.alias).filter(ativo=active).update(
            collection_accounts={"murilo": active},
        )


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0008_djen_clientes")]
    operations = [
        migrations.AddField(
            model_name="expediente", name="collection_accounts",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
