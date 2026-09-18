from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0004_events_and_lifecycle")]
    operations = [
        migrations.AlterField(
            model_name="expediente", name="identificador_pje",
            field=models.CharField(max_length=50),
        ),
        migrations.AddConstraint(
            model_name="expediente",
            constraint=models.UniqueConstraint(
                fields=("source", "identificador_pje"),
                name="unique_expediente_per_source",
            ),
        ),
    ]
