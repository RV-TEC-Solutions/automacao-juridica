"""Navegação e leitura do painel Angular do PJe TRT21."""

import re
from dataclasses import dataclass
from datetime import datetime

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


PROCESS_NUMBER = re.compile(r"\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}")
DATE = re.compile(r"\d{2}/\d{2}/\d{4}")
ID_ATTRIBUTES = ("data-expediente-id", "data-id", "expediente-id", "id")
ID_FROM_URL = re.compile(r"(?:expediente(?:Id)?|idExpediente)[=/]([A-Za-z0-9_-]+)", re.I)


@dataclass(frozen=True)
class TRT21Collection:
    records: list[dict]
    empty_message: str = ""


def _text(locator):
    return locator.inner_text().strip()


def _value_after_label(text, label):
    match = re.search(rf"{re.escape(label)}\s*:\s*([^\n]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _date_value(value):
    match = DATE.search(value or "")
    if not match:
        return None
    return datetime.strptime(match.group(0), "%d/%m/%Y").isoformat()


def _stable_identifier(row, modal):
    """Retorna o número CNJ, que identifica a pendência TRT21 por processo."""
    process = PROCESS_NUMBER.search(_text(row))
    if process:
        return process.group(0)

    # Mantemos os atributos abaixo como alternativa para páginas que não
    # renderizem o número CNJ no texto visível da linha.
    for locator in (modal, row):
        for attribute in ID_ATTRIBUTES:
            value = locator.get_attribute(attribute)
            if value and value.strip() and not value.startswith(("mat-", "cdk-")):
                return value.strip()
        descendants = locator.locator(
            "[data-expediente-id], [expediente-id], [data-id]"
        )
        for index in range(descendants.count()):
            child = descendants.nth(index)
            for attribute in ID_ATTRIBUTES[:3]:
                value = child.get_attribute(attribute)
                if value and value.strip():
                    return value.strip()
        links = locator.locator("a[href]")
        for index in range(links.count()):
            href = links.nth(index).get_attribute("href") or ""
            match = ID_FROM_URL.search(href)
            if match:
                return match.group(1)

    raise RuntimeError("O TRT21 não expôs o número CNJ do processo.")


def _row_record(row, modal, columns):
    row_text = _text(row)
    modal_text = _text(modal)
    process = PROCESS_NUMBER.search(row_text)
    if not process:
        raise RuntimeError("O TRT21 não expôs o número CNJ do processo.")
    prazo_final = columns.get("prazo final", "")
    data_ciencia = columns.get("data de ciência", "")
    data_criacao = columns.get("data de criação", "")
    meio = _value_after_label(modal_text, "Meio de Expedição")
    destinatario = _value_after_label(modal_text, "Destinatário")
    tipo_documento = "Intimação" if "Intimação" in modal_text else "Expediente"
    prazo = _value_after_label(modal_text, "Contagem de Prazo") or prazo_final
    return {
        "identificador_pje": _stable_identifier(row, modal),
        "numero_processo": process.group(0),
        "tribunal": "TRT21",
        "classe": "",
        "assunto": "",
        "partes_texto": "",
        "unidade_judiciaria": columns.get("órgão julgador", ""),
        "caixa": "Meus Expedientes",
        "tipo_pendencia": "resposta" if "Sem Resposta" in modal_text else "nao_identificada",
        "acao_pje": "responder" if "Sem Resposta" in modal_text else None,
        "destinatario": destinatario,
        "tipo_documento": tipo_documento,
        "meio_comunicacao": meio,
        "data_expedicao": _date_value(data_criacao),
        "prazo_texto": prazo,
        "ciencia_texto": data_ciencia,
        "prazo_fatal": _date_value(prazo_final),
        "status_prazo_fatal": "calculado" if prazo_final else "sem_prazo",
    }


def _normalise_header(value):
    return re.sub(r"\s+", " ", value).strip().lower()


def _columns_for_row(page, row):
    headers = page.locator("table thead th")
    cells = row.locator("td")
    # A primeira coluna contém ícones, enquanto o cabeçalho correspondente
    # pode estar vazio; mantemos o alinhamento por índice.
    return {
        _normalise_header(headers.nth(index).inner_text()): cells.nth(index).inner_text().strip()
        for index in range(min(headers.count(), cells.count()))
        if _normalise_header(headers.nth(index).inner_text())
    }


def collect_trt21_expedientes(page):
    """Lê apenas a página de resultados exibida pelo painel TRT21."""
    page.get_by_text("Meus Expedientes", exact=True).click()
    page.wait_for_url("**/pendentes-manifestacao", timeout=15000)
    page.wait_for_timeout(500)

    table_rows = page.locator("table tbody tr")
    if table_rows.count() == 0:
        return TRT21Collection([], "Nenhum expediente novo encontrado.")

    records = []
    for index in range(table_rows.count()):
        row = table_rows.nth(index)
        detail = row.get_by_role(
            "button", name=re.compile(r"^Detalhar Expediente, processo")
        )
        if detail.count() != 1:
            raise RuntimeError("Botão 'Detalhar Expediente' não encontrado de forma única.")
        detail.click()
        modal = page.get_by_role("dialog")
        try:
            modal.wait_for(state="visible", timeout=10000)
            records.append(_row_record(row, modal, _columns_for_row(page, row)))
        finally:
            close = modal.locator("a.btn-fechar-link[role='button']")
            if close.count() != 1:
                raise RuntimeError("Não foi possível fechar os detalhes do expediente TRT21.")
            close.click()
            try:
                modal.wait_for(state="hidden", timeout=5000)
            except PlaywrightTimeoutError:
                raise RuntimeError("Os detalhes do expediente TRT21 não fecharam.") from None
    return TRT21Collection(records)
