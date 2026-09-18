from django.core.management.base import BaseCommand

from automation.services.pje.runner import executar_coleta
from automation.models import AutomationRun, AutomationSource
from automation.queue import enqueue_run


class Command(BaseCommand):
    help = "Executa a coleta de expedientes do PJe."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando coleta do PJe...")
        source = AutomationSource.objects.get(code="pje-tjrn")
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
