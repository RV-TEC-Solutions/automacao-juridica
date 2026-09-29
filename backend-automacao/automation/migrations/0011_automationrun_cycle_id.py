import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("automation", "0010_add_tse_3g_source")]

    operations = [
        migrations.AddField(
            model_name="automationrun",
            name="cycle_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False),
        ),
    ]
