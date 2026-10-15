import unicodedata

from django.db import migrations


def popular_clientes(apps, schema_editor):
    Cliente = apps.get_model("expedientes", "Cliente")
    Expediente = apps.get_model("expedientes", "Expediente")
    alias = schema_editor.connection.alias
    for expediente in Expediente.objects.using(alias).only("id", "destinatario").order_by("id").iterator(chunk_size=1000):
        nome = " ".join((expediente.destinatario or "").split())
        chave = "".join(
            char for char in unicodedata.normalize("NFD", nome.lower())
            if unicodedata.category(char) != "Mn"
        )
        if chave:
            cliente, _ = Cliente.objects.using(alias).get_or_create(
                chave_normalizada=chave, defaults={"nome": nome},
            )
            Expediente.objects.using(alias).filter(pk=expediente.pk).update(cliente_id=cliente.pk)


class Migration(migrations.Migration):
    dependencies = [("expedientes", "0006_clientes")]
    operations = [migrations.RunPython(popular_clientes, migrations.RunPython.noop)]
