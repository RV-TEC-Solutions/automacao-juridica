from unittest.mock import patch

from django.test import SimpleTestCase
from reportlab.platypus import KeepTogether, Paragraph

from .reporting import pdf_response


class DeadlineLayoutTests(SimpleTestCase):
    def test_generates_pdf_in_both_formats_with_multiple_date_groups(self):
        for compact in (True, False):
            with self.subTest(compact=compact):
                records = [(f"Processo {index}", [("Prazo fatal", f"{index + 1:02d}/10/2026 08:00"),
                                                   ("Partes", "Maria & João <Silva>")])
                           for index in range(12)]
                response = pdf_response(title="Relatório", subtitle="Consulta", count=len(records),
                                        filename="relatorio.pdf", records=reversed(records),
                                        compact=compact, group_by_deadline=True)
                self.assertTrue(b"".join(response.streaming_content).startswith(b"%PDF-"))
                response.close()

    def test_both_formats_group_and_sort_deadlines_chronologically(self):
        records = [
            ("Sem data", [("Prazo fatal", "Não informado"), ("Situação do prazo", "Em cálculo")]),
            ("Novembro", [("Prazo fatal", "01/11/2026 08:00"), ("Prazo original", "5 dias")]),
            ("Mais tarde", [("Prazo fatal", "14/10/2026 18:00")]),
            ("Mais cedo", [("Prazo fatal", "14/10/2026 08:00")]),
            ("Ano anterior", [("Prazo fatal", "31/12/2025 08:00")]),
        ]

        def paragraphs(story):
            for item in story:
                if isinstance(item, Paragraph):
                    yield item
                elif isinstance(item, KeepTogether):
                    yield from paragraphs(item._content)

        for compact in (True, False):
            with self.subTest(compact=compact), patch("automation.reporting.SimpleDocTemplate.build") as build:
                response = pdf_response(
                    title="Relatório", subtitle="Consulta", count=len(records),
                    filename="relatorio.pdf", records=iter(records),
                    compact=compact, urgent=True, group_by_deadline=True,
                )
                items = list(paragraphs(build.call_args.args[0]))
                texts = [item.getPlainText() for item in items]
                titles = [text for text in texts if any(text.endswith(title) for title, _ in records)]
                self.assertEqual(
                    [text.split(". ", 1)[1] for text in titles],
                    ["Ano anterior", "Mais cedo", "Mais tarde", "Novembro", "Sem data"],
                )
                for label in ("31/12/25", "14/10/26", "01/11/26", "Sem prazo fatal informado"):
                    self.assertEqual(texts.count(label), 1)
                    section = next(item for item in items if item.getPlainText() == label)
                    self.assertTrue(section.style.fontName.endswith("-Bold"))
                for _, fields in records:
                    deadline = dict(fields)["Prazo fatal"]
                    if deadline != "Não informado":
                        self.assertTrue(any(deadline in text for text in texts))
                due_lines = [item for item in items if "Prazo fatal:" in item.getPlainText()]
                self.assertTrue(due_lines)
                for item in due_lines:
                    self.assertTrue(any("Prazo fatal:" in fragment.text and fragment.fontName.endswith("-Bold")
                                        for fragment in item.frags if hasattr(fragment, "text")))
                if compact:
                    for content in ("Prazo: 5 dias", "Prazo: Em cálculo"):
                        item = next(item for item in items if content in item.getPlainText())
                        self.assertTrue(any("Prazo:" in fragment.text and fragment.fontName.endswith("-Bold")
                                            for fragment in item.frags if hasattr(fragment, "text")))
                response.close()

    def test_reports_without_deadline_grouping_keep_their_original_layout(self):
        with patch("automation.reporting.SimpleDocTemplate.build") as build:
            response = pdf_response(title="Publicações", subtitle="Consulta", count=1,
                                    filename="publicacoes.pdf", records=[("Processo", [("Texto", "Publicação")])])
            texts = [item.getPlainText() for item in build.call_args.args[0] if isinstance(item, Paragraph)]
            self.assertNotIn("Sem prazo fatal informado", texts)
            response.close()
