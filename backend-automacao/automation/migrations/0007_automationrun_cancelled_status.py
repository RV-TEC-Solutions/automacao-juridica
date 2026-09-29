from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0006_trf5_sources_and_notices"),
    ]

    operations = [
        migrations.AlterField(
            model_name="automationrun",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pendente"),
                    ("running", "Executando"),
                    ("success", "Sucesso"),
                    ("failed", "Erro"),
                    ("cancelled", "Interrompida"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
