from getpass import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from automation.models import AutomationSource, UserProfile


class Command(BaseCommand):
    help = "Cria ou atualiza a conta única do Painel de Expedientes."

    def add_arguments(self, parser):
        parser.add_argument("--username")
        parser.add_argument("--name")

    def handle(self, *args, **options):
        username = options["username"] or input("Usuário: ").strip()
        name = options["name"] or input("Nome de exibição: ").strip()
        if not username or not name:
            raise CommandError("Usuário e nome são obrigatórios.")
        password = getpass("Senha: ")
        confirmation = getpass("Confirme a senha: ")
        if password != confirmation:
            raise CommandError("As senhas não coincidem.")
        User = get_user_model()
        user, _ = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.first_name = name.split()[0]
        user.save()
        UserProfile.objects.update_or_create(
            user=user, defaults={"display_name": name}
        )
        AutomationSource.objects.get_or_create(
            code="pje-tjrn",
            defaults={"system": "PJe", "tribunal": "TJRN", "enabled": True},
        )
        AutomationSource.objects.get_or_create(
            code="trt21",
            defaults={"system": "PJe 1º Grau", "tribunal": "TRT21", "enabled": True},
        )
        AutomationSource.objects.get_or_create(
            code="trt21-2g",
            defaults={"system": "PJe 2º Grau", "tribunal": "TRT21", "enabled": True},
        )
        AutomationSource.objects.get_or_create(
            code="pje2g-tjrn",
            defaults={
                "system": "PJe 2° Grau",
                "tribunal": "TJRN",
                "enabled": True
            },
        )
        self.stdout.write(self.style.SUCCESS("Conta configurada com sucesso."))
