import datetime

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_source(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    Run = apps.get_model("automation", "AutomationRun")
    source, _ = Source.objects.get_or_create(
        code="pje-tjrn",
        defaults={"system": "PJe", "tribunal": "TJRN", "enabled": True},
    )
    Run.objects.filter(source__isnull=True).update(source=source)


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0002_automationrun_result_counts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="AutomationSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=50, unique=True)),
                ("system", models.CharField(max_length=80)),
                ("tribunal", models.CharField(max_length=80)),
                ("enabled", models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("display_name", models.CharField(max_length=150)),
                ("theme", models.CharField(choices=[("light", "Claro"), ("dark", "Escuro"), ("system", "Seguir sistema")], default="system", max_length=10)),
                ("collection_time", models.TimeField(default=datetime.time(6, 0))),
                ("last_dashboard_visit", models.DateTimeField(blank=True, null=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="app_profile", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(model_name="automationrun", name="expedientes_resolvidos", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="automationrun", name="requested_by", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="requested_automation_runs", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="automationrun", name="scheduled_for", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="automationrun", name="source", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="runs", to="automation.automationsource")),
        migrations.AddField(model_name="automationrun", name="trigger", field=models.CharField(choices=[("scheduled", "Agendada"), ("manual", "Manual"), ("catch_up", "Recuperação")], default="manual", max_length=20)),
        migrations.RunPython(seed_source, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="automationrun",
            constraint=models.UniqueConstraint(condition=models.Q(("status__in", ("pending", "running"))), fields=("source",), name="one_active_run_per_source"),
        ),
        migrations.AlterModelOptions(name="automationrun", options={"ordering": ("-criada_em",)}),
    ]
