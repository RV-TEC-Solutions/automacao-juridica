from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("expedientes", "0002_expediente_acao_pje_expediente_atualizado_em_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="expediente",
            name="acao_pje",
            field=models.CharField(
                blank=True,
                choices=[
                    ("tomar_ciencia", "Tomar ciência"),
                    ("sem_interesse", "Sem interesse"),
                    ("responder", "Responder"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]
