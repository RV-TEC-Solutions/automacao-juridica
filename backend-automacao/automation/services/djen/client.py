import json
import time
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


API_URL = "https://comunicaapi.pje.jus.br/api/v1/comunicacao"


class DjenAPIError(RuntimeError):
    pass


def _request(params, *, attempts=3):
    request = Request(
        f"{API_URL}?{urlencode(params)}",
        headers={"Accept": "application/json", "User-Agent": "BMR-DJEN/1.0"},
    )
    last_error = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict) and payload.get("status") == "error":
                    raise DjenAPIError(payload.get("message") or "A API do DJEN recusou a consulta.")
                return payload
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, DjenAPIError) as error:
            last_error = error
            retryable = not isinstance(error, HTTPError) or error.code in {429, 500, 502, 503, 504}
            if not retryable or attempt == attempts - 1:
                break
            time.sleep(60 if isinstance(error, HTTPError) and error.code == 429 else 2 ** attempt)
    raise DjenAPIError(f"Não foi possível consultar o DJEN: {last_error}") from last_error


def fetch_communications(day: date):
    base = {
        "numeroOab": settings.DJEN_OAB_NUMBER,
        "ufOab": settings.DJEN_OAB_STATE,
        "meio": "D",
        "dataDisponibilizacaoInicio": day.isoformat(),
        "dataDisponibilizacaoFim": day.isoformat(),
        "itensPorPagina": 100,
    }
    page = 1
    records = []
    while True:
        payload = _request({**base, "pagina": page})
        if not isinstance(payload, dict) or payload.get("status") == "error":
            raise DjenAPIError("Resposta inválida da API do DJEN.")
        items = payload.get("items")
        count = payload.get("count")
        if not isinstance(items, list) or not isinstance(count, int) or isinstance(count, bool) or count < 0 or count >= 10000:
            raise DjenAPIError("Paginação ou contagem inválida da API do DJEN.")
        if len(items) > 100 or len(records) + len(items) > count:
            raise DjenAPIError("Página inconsistente da API do DJEN.")
        records.extend(items)
        if len(records) == count:
            return records
        if not items or len(items) < 100:
            raise DjenAPIError("Consulta incompleta da API do DJEN.")
        page += 1
