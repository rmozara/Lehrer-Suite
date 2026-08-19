from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

if importlib.util.find_spec("pypdf") is None:
    raise unittest.SkipTest("PDF-Testabhängigkeit ist nicht installiert.")

from pypdf import PdfReader

from hefter_collector.feedback_output import (
    fill_feedback_template,
    generate_feedback_pdf,
    safe_filename,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "IB_Hefterbewertung.odt"
CRITERIA = json.loads((ROOT / "config" / "criteria.json").read_text(encoding="utf-8"))["criteria"]
TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def row(name: str = "Anna Beispiel") -> dict:
    self_values = {str(item["id"]): (index % 4) + 1 for index, item in enumerate(CRITERIA)}
    peer_values = {str(item["id"]): ((index + 1) % 4) + 1 for index, item in enumerate(CRITERIA)}
    teacher_values = {str(item["id"]): 3 for item in CRITERIA}
    return {
        "name": name,
        "self_values": json.dumps(self_values),
        "peer_values": json.dumps(peer_values),
        "teacher_values": json.dumps(teacher_values),
    }


class FeedbackOutputTests(unittest.TestCase):
    def test_template_contains_nine_criteria_rows(self):
        with zipfile.ZipFile(TEMPLATE) as source:
            root = ET.fromstring(source.read("content.xml"))
        table = next(
            item
            for item in root.iter(TABLE + "table")
            if item.get(TABLE + "name") == "HBFeedback"
        )
        rows = list(table.findall(TABLE + "table-row"))
        self.assertEqual(len(rows), 10)
        self.assertEqual(len(CRITERIA), 9)

    def test_identity_line_preserves_base_template_underlines(self):
        with zipfile.ZipFile(TEMPLATE) as source:
            root = ET.fromstring(source.read("content.xml"))
        paragraph = next(
            item for item in root.iter(TEXT + "p")
            if "Name:" in "".join(item.itertext()) and "Klasse/Kurs:" in "".join(item.itertext())
        )
        self.assertIn("Anna Beispiel", "".join(paragraph.itertext()))
        self.assertIn("8a", "".join(paragraph.itertext()))
        self.assertIn("23.07.2026", "".join(paragraph.itertext()))
        underlined = [item for item in paragraph.iter(TEXT + "span") if item.get(TEXT + "style-name") == "T1"]
        self.assertEqual(len(underlined), 4)

    def test_subtitle_does_not_repeat_class(self):
        with zipfile.ZipFile(TEMPLATE) as source:
            content = source.read("content.xml").decode("utf-8")
        self.assertIn("Rückmeldung · ZEITRAUM", content)
        self.assertNotIn("Rückmeldung · Klasse KLASSE", content)

    def test_filled_document_contains_results_without_reviewer_name(self):
        session = {
            "class_id": "8a",
            "period": "1. Halbjahr 2026/27",
            "created_at": "2026-07-31T09:30:00",
            "subject": "Physik",
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "feedback.odt"
            fill_feedback_template(
                TEMPLATE,
                output,
                row("Anna Beispiel"),
                CRITERIA,
                session,
            )
            with zipfile.ZipFile(output) as source:
                content = source.read("content.xml").decode("utf-8")
        self.assertIn("Anna Beispiel", content)
        self.assertIn("Anna Beispiel", content)
        self.assertIn("PHYSIK", content)
        self.assertIn("EVALUATION", content)
        self.assertIn("Gesamt: 27 / 36", content)
        self.assertIn("Anteil: 75,00 %", content)
        self.assertIn("Note: 2", content)
        self.assertNotIn("Prüfer", content)
        self.assertNotIn("Reviewer", content)
        self.assertNotIn("KRITERIUM_", content)
        self.assertNotIn("KRITERIUM_2", content)

    def test_missing_teacher_rating_is_rejected(self):
        incomplete = row()
        incomplete["teacher_values"] = None
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Lehrerbewertung"):
                fill_feedback_template(
                    TEMPLATE,
                    Path(temporary) / "feedback.odt",
                    incomplete,
                    CRITERIA,
                    {
                        "class_id": "8a",
                        "period": "1. Halbjahr",
                        "created_at": "2026-07-31",
                    },
                )

    def test_safe_filename(self):
        self.assertEqual(safe_filename(" 8 a / Deutsch "), "8_a_Deutsch")

    @unittest.skipUnless(
        shutil.which("soffice") or shutil.which("libreoffice"),
        "LibreOffice ist für den echten PDF-Integrationstest erforderlich.",
    )
    def test_real_pdf_contains_one_a4_page_for_each_of_34_students(self):
        rows = [row(f"Testperson {index:02d}") for index in range(1, 35)]
        session = {
            "class_id": "8a",
            "period": "1. Halbjahr 2026/27",
            "created_at": "2026-07-31T09:30:00",
        }
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "rueckmeldungen.pdf"
            self.assertEqual(
                generate_feedback_pdf(rows, CRITERIA, session, TEMPLATE, output),
                34,
            )
            reader = PdfReader(output)
            self.assertEqual(len(reader.pages), 34)
            for page in reader.pages:
                self.assertAlmostEqual(float(page.mediabox.width), 595.3, delta=2)
                self.assertAlmostEqual(float(page.mediabox.height), 841.9, delta=2)


if __name__ == "__main__":
    unittest.main()
