from django.db import migrations, models
import django.db.models.deletion


def seed_events(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    Expediente = apps.get_model("expedientes", "Expediente")
    Event = apps.get_model("expedientes", "ExpedienteEvent")
    source = Source.objects.get(code="pje-tjrn")
    for expediente in Expediente.objects.all():
        expediente.source = source
        expediente.ativo = True
        expediente.visto_na_ultima_coleta_em = expediente.atualizado_em or expediente.capturado_em
        expediente.save(update_fields=("source", "ativo", "visto_na_ultima_coleta_em"))
        Event.objects.create(expediente=expediente, kind="new", changes={})


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0003_sources_profiles_and_queue"),
        ("expedientes", "0003_expediente_acao_pje_responder"),
    ]
    operations = [
        migrations.AddField(model_name="expediente", name="arquivado_em", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="expediente", name="ativo", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="expediente", name="source", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="expedientes", to="automation.automationsource")),
        migrations.AddField(model_name="expediente", name="visto_na_ultima_coleta_em", field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(
            name="ExpedienteEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("new", "Novo"), ("updated", "Alterado"), ("resolved", "Resolvido")], max_length=12)),
                ("changes", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("expediente", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="events", to="expedientes.expediente")),
                ("run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="events", to="automation.automationrun")),
            ],
            options={"ordering": ("-created_at",), "indexes": [models.Index(fields=["kind", "created_at"], name="expedientes_kind_44517f_idx"), models.Index(fields=["read_at", "created_at"], name="expedientes_read_at_730396_idx")]},
        ),
        migrations.RunPython(seed_events, migrations.RunPython.noop),
    ]
