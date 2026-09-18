import time

from django.core.management.base import BaseCommand

from automation.queue import claim_next_run, enqueue_due_runs, recover_interrupted_runs
from automation.services.pje.runner import executar_coleta


class Command(BaseCommand):
    help = "Processa a fila local e agenda a coleta diária."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write("Worker de coletas iniciado.")
        recovered = recover_interrupted_runs()
        if recovered:
            self.stdout.write(
                self.style.WARNING(
                    f"{recovered} coleta(s) interrompida(s) foram liberadas."
                )
            )
        while True:
            enqueue_due_runs()
            run = claim_next_run()
            if run:
                self.stdout.write(f"Executando coleta #{run.pk}...")
                try:
                    executar_coleta(run)
                except Exception as error:
                    self.stderr.write(f"Coleta #{run.pk} falhou: {error}")
            if options["once"]:
                break
            time.sleep(5)
