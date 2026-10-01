from datetime import date, datetime

from django.db import transaction

from automation.models import DjenAttorney, DjenCommunication, DjenRecipient
from expedientes.models import Processo


FIELDS = {
    "hash": "hash",
    "tribunal": "siglaTribunal",
    "orgao": "nomeOrgao",
    "tipo_comunicacao": "tipoComunicacao",
    "meio": "meiocompleto",
    "link_inteiro_teor": "link",
    "tipo_documento": "tipoDocumento",
    "nome_classe": "nomeClasse",
    "codigo_classe": "codigoClasse",
    "texto": "texto",
}


def _date(value):
    if isinstance(value, date):
        return value
    text = str(value or "")[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text, "%d/%m/%Y").date()
        except ValueError as error:
            raise ValueError(f"Data de disponibilização inválida no DJEN: {value!r}") from error


def save_communications(records, *, source, run=None):
    created_count = updated_count = 0
    with transaction.atomic():
        for record in records:
            number = record.get("numeroComunicacao")
            process_number = record.get("numeroprocessocommascara") or record.get("numero_processo")
            if number is None or not process_number:
                raise ValueError("Comunicação do DJEN sem número identificador ou processo.")
            tribunal = str(record.get("siglaTribunal") or "")
            process, _ = Processo.objects.get_or_create(
                numero=str(process_number), defaults={"tribunal": tribunal or "Nacional"}
            )
            values = {
                field: record.get(api_field) or ""
                for field, api_field in FIELDS.items()
            }
            values["api_id"] = record.get("id")
            values.update({
                "processo": process,
                "data_disponibilizacao": _date(
                    record.get("data_disponibilizacao") or record.get("datadisponibilizacao")
                ),
            })
            communication, created = DjenCommunication.objects.get_or_create(
                source=source, numero_comunicacao=int(number),
                defaults={**values, "run": run},
            )
            changed = False
            if not created:
                for field, value in values.items():
                    field_name = f"{field}_id" if field == "processo" else field
                    comparable = value.pk if field == "processo" else value
                    if getattr(communication, field_name) != comparable:
                        setattr(communication, field, value)
                        changed = True
                if changed:
                    communication.save()
            if created or changed:
                communication.recipients.all().delete()
                communication.attorneys.all().delete()
                DjenRecipient.objects.bulk_create([
                    DjenRecipient(
                        communication=communication,
                        name=str(item.get("nome") or ""),
                        pole=str(item.get("polo") or ""),
                    )
                    for item in record.get("destinatarios") or [] if item.get("nome")
                ])
                DjenAttorney.objects.bulk_create([
                    DjenAttorney(
                        communication=communication,
                        name=str((item.get("advogado") or {}).get("nome") or ""),
                        oab_number=str((item.get("advogado") or {}).get("numero_oab") or ""),
                        oab_state=str((item.get("advogado") or {}).get("uf_oab") or "")[:2],
                    )
                    for item in record.get("destinatarioadvogados") or []
                    if (item.get("advogado") or {}).get("nome")
                ])
            created_count += int(created)
            updated_count += int(not created and changed)
    return {"criados": created_count, "atualizados": updated_count, "resolvidos": 0, "total": len(records)}
