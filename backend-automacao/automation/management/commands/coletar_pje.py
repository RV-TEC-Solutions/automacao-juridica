from django.core.management.base import BaseCommand, CommandError

from automation.services.pje.runner import executar_coleta
from automation.models import AutomationRun
from automation.queue import enqueue_run, first_enabled_source


class Command(BaseCommand):
    help = "Executa a coleta de expedientes do PJe."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando coleta do PJe...")
        source = first_enabled_source("pje-tjrn")
        if source is None:
            raise CommandError("Não há fontes habilitadas para coleta.")
        run = enqueue_run(source, AutomationRun.Trigger.MANUAL)
        resultado = executar_coleta(run)
        self.stdout.write(
            self.style.SUCCESS(
                "Coleta concluída. "
                f"Total: {resultado['total']}; "
                f"novos: {resultado['criados']}; "
                f"atualizados: {resultado['atualizados']}."
            )
        )
