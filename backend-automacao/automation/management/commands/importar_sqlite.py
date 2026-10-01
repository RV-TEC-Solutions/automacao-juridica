"""Importa uma única vez o SQLite legado para um PostgreSQL vazio."""

import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections


EXCLUDED_MODELS = {"contenttypes.ContentType", "auth.Permission"}


class Command(BaseCommand):
    help = "Faz backup do SQLite legado e importa seus dados para PostgreSQL vazio."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sqlite",
            type=Path,
            default=settings.BASE_DIR / "db.sqlite3",
            help="Caminho do SQLite original.",
        )

    def handle(self, *args, **options):
        source = options["sqlite"].resolve()
        root = settings.BASE_DIR.parent
        marker = root / ".postgres-import-incomplete"
        if marker.exists():
            raise CommandError(
                "Há uma importação anterior incompleta. Inspecione o PostgreSQL "
                "e restaure um destino vazio antes de tentar novamente."
            )
        if not source.is_file():
            raise CommandError(f"SQLite não encontrado: {source}")
        if connections["default"].introspection.table_names():
            raise CommandError(
                "O PostgreSQL precisa estar completamente vazio antes da importação."
            )

        backup_dir = root / "backups"
        backup_dir.mkdir(mode=0o700, exist_ok=True)
        backup = backup_dir / f"sqlite-before-postgres-{datetime.now():%Y%m%d-%H%M%S}.sqlite3"
        if backup.exists():
            raise CommandError(f"Backup já existe: {backup}")
        try:
            with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as original:
                with sqlite3.connect(backup) as copy:
                    original.backup(copy)
                    result = copy.execute("PRAGMA integrity_check").fetchone()[0]
                    if result != "ok":
                        raise CommandError(f"Backup SQLite inválido: {result}")
            backup.chmod(0o600)
            self.stdout.write(f"Backup preservado em {backup}")

            connections.databases["legacy_sqlite"] = connections.configure_settings({
                "default": settings.DATABASES["default"],
                "legacy_sqlite": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": str(backup),
                },
            })["legacy_sqlite"]
            models = [
                model for model in apps.get_models()
                if model._meta.managed and model._meta.label not in EXCLUDED_MODELS
            ]
            counts = {
                model._meta.label: model._base_manager.using("legacy_sqlite").count()
                for model in models
            }
            with tempfile.TemporaryDirectory(prefix="pje-import-") as tmp:
                fixture = Path(tmp) / "data.json"
                call_command(
                    "dumpdata",
                    all=True,
                    database="legacy_sqlite",
                    exclude=["contenttypes", "auth.Permission"],
                    use_natural_foreign_keys=True,
                    use_natural_primary_keys=True,
                    output=str(fixture),
                    verbosity=0,
                )
                marker.write_text(f"Importação de {backup} em andamento.\n")
                call_command("migrate", database="default", interactive=False, verbosity=0)
                # Migrations de dados criam fontes iniciais. Limpar o destino
                # depois do esquema evita colisões com IDs e códigos importados.
                call_command("flush", database="default", interactive=False, verbosity=0)
                call_command("loaddata", str(fixture), database="default", verbosity=0)

            sql = connections["default"].ops.sequence_reset_sql(no_style(), models)
            with connections["default"].cursor() as cursor:
                for statement in sql:
                    cursor.execute(statement)

            differences = {
                label: (expected, actual)
                for label, expected in counts.items()
                if (actual := apps.get_model(label)._base_manager.using("default").count())
                != expected
            }
            if differences:
                raise CommandError(f"Contagens diferentes após importação: {differences}")
            with connections["default"].cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            marker.unlink()
            self.stdout.write(self.style.SUCCESS(
                f"Importação concluída; {len(models)} modelos conferidos. "
                f"SQLite original preservado em {source}."
            ))
        except Exception:
            if marker.exists():
                self.stderr.write(
                    "Importação incompleta: não inicie a aplicação. "
                    "O backup SQLite foi preservado; recrie um PostgreSQL vazio "
                    "antes de tentar novamente."
                )
            raise
