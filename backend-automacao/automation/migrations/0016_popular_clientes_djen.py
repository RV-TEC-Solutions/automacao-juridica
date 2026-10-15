import unicodedata

from django.db import migrations


def popular_clientes(apps, schema_editor):
    Cliente = apps.get_model("expedientes", "Cliente")
    Recipient = apps.get_model("automation", "DjenRecipient")
    alias = schema_editor.connection.alias
    for recipient in Recipient.objects.using(alias).only("id", "name").order_by("id").iterator(chunk_size=1000):
        nome = " ".join((recipient.name or "").split())
        chave = "".join(char for char in unicodedata.normalize("NFD", nome.lower()) if unicodedata.category(char) != "Mn")
        if chave:
            cliente, _ = Cliente.objects.using(alias).get_or_create(chave_normalizada=chave, defaults={"nome": nome})
            Recipient.objects.using(alias).filter(pk=recipient.pk).update(cliente_id=cliente.pk)


class Migration(migrations.Migration):
    dependencies = [("automation", "0015_djen_clientes")]
    operations = [migrations.RunPython(popular_clientes, migrations.RunPython.noop)]
