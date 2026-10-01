from django.db import migrations, models
import django.db.models.deletion


def add_djen_source(apps, schema_editor):
    Source = apps.get_model("automation", "AutomationSource")
    Source.objects.update_or_create(
        code="djen",
        defaults={"system": "DJEN", "tribunal": "Nacional", "enabled": True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("automation", "0013_automationrun_descartada_em"),
        ("expedientes", "0005_source_identifier_unique"),
    ]
    operations = [
        migrations.CreateModel(
            name="DjenCommunication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("api_id", models.BigIntegerField(blank=True, null=True)),
                ("numero_comunicacao", models.BigIntegerField()),
                ("hash", models.CharField(blank=True, max_length=128)),
                ("data_disponibilizacao", models.DateField()),
                ("tribunal", models.CharField(max_length=30)),
                ("orgao", models.CharField(blank=True, max_length=255)),
                ("tipo_comunicacao", models.CharField(blank=True, max_length=120)),
                ("meio", models.CharField(blank=True, max_length=120)),
                ("link_inteiro_teor", models.URLField(blank=True, max_length=1000)),
                ("tipo_documento", models.CharField(blank=True, max_length=120)),
                ("nome_classe", models.CharField(blank=True, max_length=255)),
                ("codigo_classe", models.CharField(blank=True, max_length=50)),
                ("texto", models.TextField(blank=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("collected_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("processo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="djen_communications", to="expedientes.processo")),
                ("run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="djen_communications", to="automation.automationrun")),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="djen_communications", to="automation.automationsource")),
            ],
            options={"ordering": ("-data_disponibilizacao", "-numero_comunicacao")},
        ),
        migrations.CreateModel(
            name="DjenRecipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=500)),
                ("pole", models.CharField(blank=True, max_length=80)),
                ("communication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recipients", to="automation.djencommunication")),
            ],
            options={"ordering": ("id",)},
        ),
        migrations.CreateModel(
            name="DjenAttorney",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=500)),
                ("oab_number", models.CharField(blank=True, max_length=30)),
                ("oab_state", models.CharField(blank=True, max_length=2)),
                ("communication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attorneys", to="automation.djencommunication")),
            ],
            options={"ordering": ("id",)},
        ),
        migrations.AddConstraint(
            model_name="djencommunication",
            constraint=models.UniqueConstraint(fields=("source", "numero_comunicacao"), name="unique_djen_communication_per_source"),
        ),
        migrations.AddIndex(
            model_name="djencommunication",
            index=models.Index(fields=["data_disponibilizacao", "tribunal"], name="automation__data_di_98e3e9_idx"),
        ),
        migrations.AddIndex(
            model_name="djencommunication",
            index=models.Index(fields=["read_at", "data_disponibilizacao"], name="automation__read_at_0b4038_idx"),
        ),
        migrations.RunPython(add_djen_source, migrations.RunPython.noop),
    ]
