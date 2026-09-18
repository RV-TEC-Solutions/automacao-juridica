from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("automation", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="automationrun",
            name="capturas_html",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="automationrun",
            name="expedientes_atualizados",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="automationrun",
            name="expedientes_criados",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
