from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("automation", "0016_popular_clientes_djen")]
    operations = [migrations.AddField(
        model_name="automationrun", name="collector",
        field=models.CharField(default="murilo", max_length=30),
    )]
