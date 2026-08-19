from __future__ import annotations

import shutil
import tempfile
import unittest
import zipfile
import importlib.util
from pathlib import Path

if any(importlib.util.find_spec(package) is None for package in ("qrcode", "pypdf")):
    raise unittest.SkipTest("QR-/PDF-Testabhängigkeit ist nicht installiert.")

from pypdf import PdfReader

from qr_generator.qr_output import fill_qr_template, generate_qr_cards_pdf


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "IB_QR-Karten.odt"


def student(number: int) -> dict:
    return {
        "class_id": "8a",
        "student_id": f"8a-{number:02d}",
        "name": f"Testperson {number}",
        "public_token": f"abcdefghijklmnopqrstuvwxyzABCDE{number:02d}",
        "short_code": f"ABCD{number:04d}",
        "list_position": number,
    }


class QrOutputTests(unittest.TestCase):
    def test_personal_code_is_written_below_card_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "karte.odt"
            fill_qr_template(
                TEMPLATE,
                output,
                student(1),
                "Collector",
                "http://192.168.50.10:8765",
            )
            with zipfile.ZipFile(output) as package:
                content = package.read("content.xml").decode("utf-8")
        self.assertIn("Code ABCD0001", content)
        self.assertIn("Schüler-ID 8a-01", content)

    @unittest.skipUnless(
        shutil.which("soffice") or shutil.which("libreoffice"),
        "LibreOffice ist für den echten PDF-Test erforderlich.",
    )
    def test_real_pdf_keeps_one_a5_page_per_card_with_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "karten.pdf"
            self.assertEqual(
                generate_qr_cards_pdf(
                    [student(1), student(2), student(3)],
                    "Collector",
                    "http://192.168.50.10:8765",
                    TEMPLATE,
                    output,
                ),
                3,
            )
            reader = PdfReader(output)
            self.assertEqual(len(reader.pages), 3)
            self.assertIn("ABCD0001", reader.pages[0].extract_text())


if __name__ == "__main__":
    unittest.main()
