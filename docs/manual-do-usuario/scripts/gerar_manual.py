"""Gera Markdown e PDF a partir de conteudo.json e dos prints capturados.

Uso: .venv/bin/python docs/manual-do-usuario/scripts/gerar_manual.py
Dependência: ReportLab (já usado pelo backend) e fontes DejaVu Sans.
"""
import json
import re
import unicodedata
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "conteudo.json").read_text())


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def markdown():
    lines = [f"# {DATA['title']} — {DATA['subtitle']}", "",
             f"Versão {DATA['version']} · {DATA['date']} · Idioma: português (Brasil)", "",
             "[Baixar o manual em PDF](RYV-Expedientes-Manual-do-Usuario.pdf)", "",
             "## Índice", ""]
    for i, section in enumerate(DATA["sections"], 1):
        title = f"{i:02}. {section['title']}"
        lines.append(f"{i}. [{section['title']}](#{slug(title)})")
    for i, section in enumerate(DATA["sections"], 1):
        title = f"{i:02}. {section['title']}"
        lines.extend(["", f'<a id="{slug(title)}"></a>', "", f"## {title}", "", section["intro"], ""])
        for n, step in enumerate(section.get("steps", []), 1):
            lines.append(f"{n}. {step}")
        if "rows" in section:
            lines.append("")
            for r, row in enumerate(section["rows"]):
                lines.append("| " + " | ".join(row) + " |")
                if r == 0: lines.append("| --- | --- |")
        if "image" in section:
            lines.extend(["", f"![Tela de {section['title']} com destaques vermelhos numerados](imagens/{section['image']})", "",
                          "*Captura da interface real com dados fictícios de demonstração.*", ""])
            for n, legend in enumerate(section.get("legend", []), 1):
                lines.append(f"- **Destaque {n}:** {legend}")
        for note in section.get("notes", []):
            lines.extend(["", f"> **Atenção:** {note}"])
    (ROOT / "MANUAL_DO_USUARIO.md").write_text("\n".join(lines) + "\n")


def pdf():
    fontroot = Path("/usr/share/fonts/truetype/dejavu")
    for name, file in [("Manual", "DejaVuSans.ttf"), ("ManualBold", "DejaVuSans-Bold.ttf")]:
        pdfmetrics.registerFont(TTFont(name, str(fontroot/file)))
    pdfmetrics.registerFontFamily("Manual", normal="Manual", bold="ManualBold", italic="Manual", boldItalic="ManualBold")
    navy = colors.HexColor("#102c46")
    red = colors.HexColor("#c62828")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TextManual", fontName="Manual",fontSize=9.4,leading=14,spaceAfter=7,textColor=navy))
    styles.add(ParagraphStyle(name="TitleManual", fontName="ManualBold",fontSize=20,leading=27,spaceAfter=14,textColor=navy))
    styles.add(ParagraphStyle(name="CaptionManual",fontName="Manual",fontSize=7.8,leading=11,spaceAfter=5,textColor=colors.HexColor("#64748b")))
    styles.add(ParagraphStyle(name="LegendManual",fontName="Manual",fontSize=8.4,leading=12,spaceAfter=4,textColor=navy))
    styles.add(ParagraphStyle(name="NoteManual",fontName="Manual",fontSize=8.8,leading=13,spaceBefore=8,spaceAfter=7,borderPadding=9,backColor=colors.HexColor("#fff1f2"),textColor=navy))
    styles.add(ParagraphStyle(name="TableManual",fontName="Manual",fontSize=8.5,leading=12,textColor=navy))
    width, height = A4
    margin = 42
    available = width - 2*margin

    class ManualDoc(BaseDocTemplate):
        def afterFlowable(self, flowable):
            if isinstance(flowable, Paragraph) and getattr(flowable, "manual_key", None):
                key = flowable.manual_key
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(flowable.getPlainText(), key, level=0)
                self.notify("TOCEntry", (0, flowable.getPlainText(), self.page, key))

    def decoration(canvas, doc):
        canvas.saveState()
        if doc.page > 1:
            canvas.setFont("ManualBold", 8)
            canvas.setFillColor(navy)
            canvas.drawString(margin, height-25, "RYV Expedientes  |  Manual do usuário")
            canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
            canvas.line(margin, height-32, width-margin, height-32)
        canvas.setFont("Manual", 7.5)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(margin, 23, f"Versão {DATA['version']} · {DATA['date']} · Dados fictícios nas capturas")
        canvas.drawRightString(width-margin, 23, str(doc.page))
        canvas.restoreState()

    target = ROOT / "RYV-Expedientes-Manual-do-Usuario.pdf"
    doc = ManualDoc(str(target),pagesize=A4,leftMargin=margin,rightMargin=margin,topMargin=48,bottomMargin=42,
                    title="RYV Expedientes — Manual do usuário",author="RYV Expedientes",subject="Manual de uso com capturas anotadas e dados fictícios",lang="pt-BR")
    doc.addPageTemplates(PageTemplate(id="manual",frames=Frame(margin,42,available,height-90,id="content",leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0),onPage=decoration))
    p = lambda text, style="TextManual": Paragraph(escape(text),styles[style])
    story = [Spacer(1,95),p("RYV EXPEDIENTES","TitleManual"),Spacer(1,12),
             Paragraph("Manual do<br/>usuário",ParagraphStyle(name="Cover",fontName="ManualBold",fontSize=42,leading=52,textColor=navy)),
             Spacer(1,30),p("Consulta, monitoramento e organização de expedientes PJe e publicações DJEN."),
             Spacer(1,22),p("Visão geral · Expedientes · Publicações DJEN · Histórico · Avisos · Estatísticas · Configurações"),
             Spacer(1,65),p(f"Versão {DATA['version']}  |  {DATA['date']}"),p("Capturas da interface real com destaques vermelhos e dados fictícios."),PageBreak(),
             p("Índice","TitleManual"),p("Clique no capítulo desejado para navegar. Os marcadores laterais do PDF também dão acesso às partes do manual.")]
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle(name="Index",fontName="Manual",fontSize=9.2,leading=13,spaceBefore=0,textColor=navy)]
    story.extend([toc, PageBreak()])
    figure=0
    for i, section in enumerate(DATA["sections"],1):
        if i>1: story.append(PageBreak())
        title=p(f"{i:02}. {section['title']}","TitleManual")
        title.manual_key = f"chapter-{i}"
        story.extend([title,p(section["intro"])])
        for n, step in enumerate(section.get("steps", []),1):
            story.append(Paragraph(f"<b>{n}.</b> {escape(step)}",styles["TextManual"]))
        if "rows" in section:
            rows=[]
            for idx,row in enumerate(section["rows"]):
                rows.append([Paragraph(("<b>"+escape(cell)+"</b>") if idx==0 else escape(cell),styles["TableManual"]) for cell in row])
            table=Table(rows,colWidths=[available*.29,available*.71],repeatRows=1,hAlign="LEFT")
            table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e2e8f0")),
                                      ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),
                                      ("LINEBELOW",(0,0),(-1,-1),.4,colors.HexColor("#cbd5e1")),
                                      ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),8),
                                      ("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
            story.extend([Spacer(1,5),table,Spacer(1,9)])
        if "image" in section:
            figure+=1
            path=ROOT/"imagens"/section["image"]
            image=Image(str(path))
            scale=min(available/image.imageWidth,section.get("image_max_height",350)/image.imageHeight)
            image.drawWidth=image.imageWidth*scale
            image.drawHeight=image.imageHeight*scale
            image.hAlign="CENTER"
            story.extend([Spacer(1,7),KeepTogether([image,Spacer(1,5),p(f"Figura {figure:02} — {section['title']}. Interface real; dados fictícios.","CaptionManual")])])
            for n, legend in enumerate(section.get("legend", []),1):
                story.append(Paragraph(f'<font color="#c62828"><b>{n}.</b></font> {escape(legend)}',styles["LegendManual"]))
        for note in section.get("notes",[]):
            story.append(Paragraph(f'<font color="#c62828"><b>Atenção:</b></font> {escape(note)}',styles["NoteManual"]))
    doc.multiBuild(story)
    print(f"PDF gerado: {target}")


if __name__ == "__main__":
    missing = [s["image"] for s in DATA["sections"] if "image" in s and not (ROOT/"imagens"/s["image"]).is_file()]
    if missing: raise SystemExit("Capturas ausentes: "+", ".join(missing))
    markdown()
    pdf()
