from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("automation", "0018_automationrun_credential_failure")]

    operations = [
        migrations.AlterField(
            model_name="automationrun",
            name="trigger",
            field=models.CharField(
                choices=[
                    ("scheduled", "Agendada"),
                    ("manual", "Manual"),
                    ("collector", "Coleta de titular"),
                    ("rerun", "Reexecução de fonte"),
                    ("catch_up", "Recuperação"),
                ],
                default="manual",
                max_length=20,
            ),
        ),
    ]
