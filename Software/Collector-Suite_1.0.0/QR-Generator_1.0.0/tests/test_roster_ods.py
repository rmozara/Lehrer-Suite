from __future__ import annotations

import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from qr_generator.roster_ods import read_generation_date, read_roster, write_generation_date


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "Namensliste.ods"


class RosterOdsTests(unittest.TestCase):
    def test_reads_visible_metadata_and_students(self):
        roster = read_roster(TEMPLATE)
        self.assertEqual(roster.class_id, "8a")
        self.assertEqual(roster.school_year, "2026/27")
        self.assertEqual([item["list_position"] for item in roster.students], [1, 2, 3])
        self.assertEqual(roster.students[0]["student_id"], "8a-01")

    def test_generation_date_is_written_above_student_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "Namensliste.ods"
            changed.write_bytes(TEMPLATE.read_bytes())
            write_generation_date(changed, date(2026, 8, 4))
            with zipfile.ZipFile(changed) as package:
                content = package.read("content.xml")
            self.assertIn("04.08.2026", content.decode("utf-8"))
            self.assertEqual(read_generation_date(changed), "04.08.2026")
            self.assertEqual(read_roster(changed).class_id, "8a")

    def test_student_ids_do_not_have_to_contain_the_class(self):
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "Namensliste.ods"
            self._replace_content(changed, b"8a-03", b"Freie-ID")
            roster = read_roster(changed)
            self.assertEqual(roster.class_id, "8a")
            self.assertEqual(roster.students[2]["student_id"], "Freie-ID")

    def test_missing_school_year_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "Namensliste.ods"
            self._replace_content(changed, b"Schuljahr", b"Fehlende-Angabe")
            with self.assertRaisesRegex(ValueError, "Schuljahr"):
                read_roster(changed)

    def _replace_content(self, destination: Path, old: bytes, new: bytes):
        with zipfile.ZipFile(TEMPLATE) as source, zipfile.ZipFile(destination, "w") as target:
            for info in source.infolist():
                content = source.read(info.filename)
                if info.filename == "content.xml":
                    content = content.replace(old, new)
                target.writestr(info, content)


if __name__ == "__main__":
    unittest.main()
