from __future__ import annotations

import io
import importlib.util
import tempfile
import unittest
from pathlib import Path

from hefter_collector.db import Database
from hefter_collector.qr_access import decode_qr_image, student_token_from_qr_payload


TOKEN = "abcdefghijklmnopqrstuvwxyzABCDE12345"


class TwoQrAccessTests(unittest.TestCase):
    def test_personal_token_is_extracted_while_old_host_is_ignored(self):
        self.assertEqual(
            student_token_from_qr_payload(
                f"http://192.168.50.10:8765/p/{TOKEN}"
            ),
            TOKEN,
        )
        self.assertEqual(
            student_token_from_qr_payload(
                f"https://alter-laptop.invalid/p/{TOKEN}"
            ),
            TOKEN,
        )

    def test_non_personal_qr_is_rejected(self):
        self.assertIsNone(student_token_from_qr_payload("kein-persoenlicher-qr"))

    @unittest.skipUnless(
        importlib.util.find_spec("qrcode") and importlib.util.find_spec("cv2"),
        "QR-Testabhängigkeiten sind nicht installiert.",
    )
    def test_camera_image_is_really_decoded(self):
        import qrcode

        payload = f"http://10.0.0.20:8765/p/{TOKEN}"
        output = io.BytesIO()
        qrcode.make(payload).save(output, format="PNG")
        self.assertEqual(decode_qr_image(output.getvalue()), payload)

    def test_each_session_has_a_stable_unique_access_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            database = Database(Path(temporary) / "hb.sqlite3")
            database.import_students(
                [
                    {
                        "class_id": "8a",
                        "list_position": number,
                        "student_code": f"8a-{number:02d}",
                        "name": f"Person {number}",
                    }
                    for number in range(1, 4)
                ]
            )
            first_id = database.create_session("8a", "HJ1", "Hefter")
            second_id = database.create_session("8a", "HJ1", "Hefter")
            first = database.session(first_id)
            second = database.session(second_id)
            self.assertTrue(first["access_token"])
            self.assertNotEqual(first["access_token"], second["access_token"])
            self.assertEqual(
                database.session_by_access_token(first["access_token"])["id"],
                first_id,
            )
            student = database.students("8a")[0]
            self.assertTrue(database.student_in_session(first_id, student["id"]))

    def test_student_page_uses_direct_camera_capture(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "hefter_collector"
            / "web.py"
        ).read_text(encoding="utf-8")
        self.assertIn("capture='environment'", source)
        self.assertIn("Kamera öffnen", source)


if __name__ == "__main__":
    unittest.main()
