import unicodedata

from .models import Cliente


def normalizar_nome(nome):
    nome = " ".join((nome or "").split())
    chave = "".join(
        char for char in unicodedata.normalize("NFD", nome.lower())
        if unicodedata.category(char) != "Mn"
    )
    return nome, chave


def cliente_do_destinatario(destinatario):
    nome, chave = normalizar_nome(destinatario)
    if not chave:
        return None
    cliente, _ = Cliente.objects.get_or_create(
        chave_normalizada=chave, defaults={"nome": nome},
    )
    return cliente
