from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("automation", "0017_automationrun_collector")]
    operations = [migrations.AddField(
        model_name="automationrun", name="credential_failure",
        field=models.BooleanField(default=False),
    )]
