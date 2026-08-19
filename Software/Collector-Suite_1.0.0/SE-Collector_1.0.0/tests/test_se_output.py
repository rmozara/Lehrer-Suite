import copy
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

from se_collector.ods_file import (
    _cell,
    _read_package,
    _set_value,
    _table,
    _write_package,
    read_roster,
    update_raw_data,
)
from se_collector.config import ODS_TEMPLATE_FILE
from se_collector.se_output import X, T, fill_template, read_evaluation_sheets


ROOT = Path(__file__).resolve().parents[1]


class SeOutputTests(unittest.TestCase):
    def setUp(self):
        self.form = json.loads((ROOT / "config" / "se1.json").read_text(encoding="utf-8"))

    def test_reads_class_and_session_date_from_ods(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ods = root / "Selbstevaluation.ods"
            shutil.copy2(ODS_TEMPLATE_FILE, ods)
            entries, ods_root = _read_package(ods)
            roster_table = _table(ods_root, "Namensliste")
            _set_value(_cell(roster_table, 5, 3), "Anna Beispiel")
            _set_value(_cell(roster_table, 5, 4), "8a-01")
            _write_package(entries, ods_root, ods)
            student = read_roster(ods).students[0]
            answers = {f"q{index:02d}": index % 4 for index in range(1, 23)}
            rows = [{
                "Nr.": student["list_position"],
                "Name": student["name"],
                "Schüler-ID": student["student_id"],
                "Zeitraum": "Q1",
                "answers": answers,
                "raw": {"submitted_at": "2026-07-23T10:00:00+02:00"},
            }]
            update_raw_data(
                ods,
                {"period_id": "Q1", "started_at": "2026-07-23T09:00:00+02:00"},
                rows,
                self.form,
                root / "backups",
            )
            sheets = read_evaluation_sheets(ods, copy.deepcopy(self.form))
            self.assertEqual(len(sheets), 1)
            self.assertEqual(sheets[0].class_id, "8a")
            self.assertEqual(sheets[0].date, "23.07.2026")

    def test_template_has_correct_summary_and_no_visible_second_page_content(self):
        from se_collector.se_output import EvaluationSheet

        sheet = EvaluationSheet(
            class_id="8a",
            date="23.07.2026",
            period_id="Q1",
            name="Anna Beispiel",
            answers={f"q{index:02d}": index % 4 for index in range(1, 23)},
            section_points=(14, 6, 6, 7),
            total_points=33,
            total_maximum=66,
            percent=50.0,
            grade_label="3-",
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "sheet.odt"
            fill_template(ROOT / "templates" / "IB_Selbstbewertung1.odt", output, sheet, self.form)
            with zipfile.ZipFile(output) as package:
                root = ET.fromstring(package.read("content.xml"))
            summary = next(
                item for item in root.iter(T + "table") if item.get(T + "name") == "SESummary"
            )
            values = [
                item.text
                for item in summary.iter(X + "span")
                if item.get(X + "style-name") == "T7"
            ]
            self.assertEqual(
                values,
                ["14 / 27", "6 / 9", "6 / 12", "7 / 18", "33 / 66", "50,0 %", "3-"],
            )


if __name__ == "__main__":
    unittest.main()
