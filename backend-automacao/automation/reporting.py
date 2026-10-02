"""Shared date handling and printable PDF layout for collection exports."""

from datetime import date, datetime, timedelta
from collections import Counter
from html import escape
from tempfile import SpooledTemporaryFile
from zoneinfo import ZoneInfo

from django.http import FileResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer


LOCAL_TZ = ZoneInfo("America/Fortaleza")


def collection_range(params, *, history=False, default_today=False, from_key="date_from", to_key="date_to"):
    """Return inclusive local dates and exclusive aware datetime bounds."""
    today = timezone.localdate(timezone=LOCAL_TZ)
    first_allowed = today - timedelta(days=29)
    try:
        start = date.fromisoformat(params.get(from_key) or (today.isoformat() if default_today else first_allowed.isoformat()))
        end = date.fromisoformat(params.get(to_key) or today.isoformat())
    except ValueError as exc:
        raise ValueError("Informe datas válidas no formato AAAA-MM-DD.") from exc
    if start > end:
        raise ValueError("A data inicial não pode ser posterior à data final.")
    if history and (start < first_allowed or end > today):
        raise ValueError("O Histórico permite apenas datas dos últimos 30 dias.")
    try:
        end_exclusive = end + timedelta(days=1)
    except OverflowError as exc:
        raise ValueError("Data final inválida.") from exc
    return start, end, datetime.combine(start, datetime.min.time(), tzinfo=LOCAL_TZ), datetime.combine(end_exclusive, datetime.min.time(), tzinfo=LOCAL_TZ)


def local_datetime(value):
    if not value:
        return "Não informado"
    return timezone.localtime(value, LOCAL_TZ).strftime("%d/%m/%Y %H:%M")


def local_date(value):
    return value.strftime("%d/%m/%Y") if value else "Não informado"


def _text(value):
    if value is None or value == "":
        return "Não informado"
    cleaned = "".join(char for char in str(value) if char in "\n\t" or ord(char) >= 32)
    return escape(cleaned).replace("\n", "<br/>")


def _register_fonts():
    if "DejaVu" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
        pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold")
    if "Liberation" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("Liberation", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"))
        pdfmetrics.registerFont(TTFont("Liberation-Bold", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"))
        pdfmetrics.registerFontFamily("Liberation", normal="Liberation", bold="Liberation-Bold")


def _compact_records(records, urgent, styles):
    """Lay out expedition fields as short document entries; preserve exceptional facts."""
    ink = colors.HexColor("#171717")
    rule = colors.HexColor("#cccccc")
    rows = list(records)
    if urgent:
        today = timezone.localdate(timezone=LOCAL_TZ)

        def group(record):
            deadline = dict(record[1]).get("Prazo fatal", "")
            try:
                due = datetime.strptime(deadline[:10], "%d/%m/%Y").date()
            except (ValueError, TypeError):
                return 3
            return 0 if due < today else 1 if due == today else 2 if due == today + timedelta(days=1) else 3

        rows.sort(key=lambda record: (group(record), dict(record[1]).get("Prazo fatal", "")))
        totals = Counter(group(record) for record in rows)
        groups = ("VENCIDOS", "VENCEM HOJE", "VENCEM AMANHÃ", "DEMAIS URGENTES")
    story = []
    last_group = None
    pages = max(1, (len(rows) + 5) // 6)
    larger_pages = len(rows) % pages
    page_size = len(rows) // pages
    break_after = {sum(page_size + (page < larger_pages) for page in range(end))
                   for end in range(1, pages)}
    for index, (heading, fields) in enumerate(rows, 1):
        values = dict(fields)
        group_heading = []
        if urgent:
            current_group = group((heading, fields))
            if current_group != last_group:
                group_heading = [Paragraph(f"{groups[current_group]}  ·  {totals[current_group]}", styles["section"]),
                                 HRFlowable(width="100%", thickness=.6, color=ink, spaceAfter=5)]
                last_group = current_group

        def line(*parts):
            return "  ·  ".join(_text(part) for part in parts if part and part != "Não informado")

        title = f"{index:02d}. {_text(heading)}"
        context = line(values.get("Partes"))
        subject = line(values.get("Assunto"), values.get("Unidade judiciária"))
        deadline = values.get("Prazo fatal")
        status = values.get("Situação do prazo")
        due = f"Prazo fatal: {deadline}" if deadline and deadline != "Não informado" else (
            f"Prazo fatal não informado ({status})" if status == "Calculado" else f"Prazo: {status or 'não informado'}"
        )
        operation = line(values.get("Pendência"), values.get("Ação no PJe"), due)
        origin = line(
            f"Expedido: {values['Expedido em']}" if values.get("Expedido em") not in (None, "Não informado") else None,
            f"Prazo: {values['Prazo original']}" if values.get("Prazo original") else None,
            f"Tribunal: {values['Tribunal']}" if values.get("Tribunal") and values["Tribunal"] not in (values.get("Fonte") or "") else None,
            values.get("Fonte") or values.get("Tribunal"),
            f"ID {values['Identificador no PJe']}" if values.get("Identificador no PJe") else None,
        )
        extras = line(
            f"Destinatário: {values['Destinatário']}" if values.get("Destinatário") else None,
            f"Caixa: {values['Caixa']}" if values.get("Caixa") else None,
            values.get("Registro de ciência") if values.get("Registro de ciência", "").lower().startswith("ciência")
            else f"Ciência: {values['Registro de ciência']}" if values.get("Registro de ciência") else None,
            "Resolvido" if values.get("Situação atual") == "Resolvido" else None,
            f"Arquivado: {values['Arquivado em']}" if values.get("Arquivado em") not in (None, "Não informado") else None,
        )
        entry = [Paragraph(title, styles["entry"])]
        entry += [Paragraph(content, styles["body"]) for content in (context, subject, operation, origin) if content]
        if extras:
            entry.append(Paragraph(extras, styles["small"]))
        entry.append(HRFlowable(width="100%", thickness=.35, color=rule, spaceBefore=7, spaceAfter=10))
        story.append(KeepTogether(group_heading + entry))
        if index in break_after:
            story.append(PageBreak())
    return story


def pdf_response(*, title, subtitle, count, filename, records, compact=False, urgent=False):
    """Build a readable multi-page report from (heading, fields) records."""
    _register_fonts()
    font = "Liberation" if compact else "DejaVu"
    body = ParagraphStyle("body", fontName=font, fontSize=8.5, leading=11 if compact else 13,
                          textColor=colors.HexColor("#171717" if compact else "#243042"), spaceAfter=1 if compact else 5)
    small = ParagraphStyle("small", parent=body, fontSize=7.5, leading=11)
    heading = ParagraphStyle("heading", parent=body, fontName=f"{font}-Bold", fontSize=11, leading=16, spaceBefore=12, spaceAfter=9)
    title_style = ParagraphStyle("title", parent=heading, fontSize=14 if compact else 16, leading=18 if compact else 22, spaceBefore=0)
    story = [Paragraph(_text(title), title_style), Paragraph(_text(subtitle), body),
             Paragraph(f"Posição em {local_datetime(timezone.now())}  ·  {count} expediente{'s' if count != 1 else ''}" if compact
                       else f"Gerado em {local_datetime(timezone.now())} · {count} registros" if count != 1
                       else f"Gerado em {local_datetime(timezone.now())} · 1 registro", small),
             HRFlowable(width="100%", thickness=1, color=colors.HexColor("#777777" if compact else "#cbd5e1")), Spacer(1, 3 * mm if compact else 5 * mm)]
    if compact:
        styles = {"body": body, "small": small,
                  "entry": ParagraphStyle("entry", parent=body, fontName="Liberation-Bold", fontSize=9, leading=12, spaceAfter=2),
                  "section": ParagraphStyle("section", parent=heading, fontSize=10, spaceBefore=9, spaceAfter=3)}
        story.extend(_compact_records(records, urgent, styles))
    else:
        for index, (record_title, fields) in enumerate(records, 1):
            story.append(Paragraph(f"{index}. {_text(record_title)}", heading))
            for label, value in fields:
                content = _text(value)
                if label == "Link para o inteiro teor" and isinstance(value, str) and value.startswith(("https://", "http://")):
                    content = f'<link href="{escape(value, quote=True)}" color="#164e93">{content}</link>'
                story.append(Paragraph(f"<b>{_text(label)}:</b> {content}", body))
            story.append(Spacer(1, 2 * mm))
            story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#e2e8f0")))

    output = SpooledTemporaryFile(max_size=2 * 1024 * 1024)
    margin = 13 * mm if compact else 18 * mm
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=margin, leftMargin=margin,
                                 topMargin=14 * mm if compact else 20 * mm,
                                 bottomMargin=15 * mm if compact else 19 * mm, title=title)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 7)
        canvas.setFillColor(colors.HexColor("#555555" if compact else "#64748b"))
        canvas.drawString(margin, 9 * mm, "BMR · Relatório de expedientes" if compact else "BMR · Relatório de coletas")
        canvas.drawRightString(A4[0] - margin, 9 * mm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    return FileResponse(output, as_attachment=True, filename=filename, content_type="application/pdf")
