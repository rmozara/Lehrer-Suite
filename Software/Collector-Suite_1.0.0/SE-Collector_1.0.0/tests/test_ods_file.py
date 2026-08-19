from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from se_collector.config import ODS_TEMPLATE_FILE, ROOT, load_form
from se_collector.ods_file import (
    _cell,
    _read_package,
    _set_value,
    _table,
    _value,
    _write_package,
    apply_parameters_to_form,
    read_parameters,
    read_roster,
    update_raw_data,
)


def populate_test_roster(path: Path) -> None:
    entries, root = _read_package(path)
    table = _table(root, "Namensliste")
    for row, name, student_id in (
        (5, "Anna Beispiel", "8a-01"),
        (6, "Ben Beispiel", "8a-02"),
        (7, "Carla Beispiel", "8a-03"),
    ):
        _set_value(_cell(table, row, 3), name)
        _set_value(_cell(table, row, 4), student_id)
    _write_package(entries, root, path)


class OdsFileTests(unittest.TestCase):
    def test_distributed_workbook_is_in_null_state(self):
        _, root = _read_package(ODS_TEMPLATE_FILE)
        roster = _table(root, "Namensliste")
        raw = _table(root, "Rohdaten")
        evaluation = _table(root, "Auswertung")
        examples = {5: ("Anna Beispiel", "8a-01"), 6: ("Ben Beispiel", "8a-02"), 7: ("Carla Beispiel", "8a-03")}
        for position in range(34):
            row = 5 + position
            self.assertEqual(
                [_value(_cell(roster, row, column)) for column in (3, 4)],
                list(examples.get(row, (-1, -1))),
            )
            self.assertEqual([_value(_cell(raw, row, column)) for column in range(5, 29)], [-1] * 24)
            self.assertEqual([_value(_cell(evaluation, row, column)) for column in range(3, 11)], [-1] * 8)
        self.assertIn(_value(_cell(evaluation, 2, 4)), (None, ""))
        self.assertEqual(_value(_cell(evaluation, 3, 4)), "Datum")

    def test_roster_is_read_from_final_workbook(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Selbstevaluation.ods"
            shutil.copy2(ODS_TEMPLATE_FILE, path)
            populate_test_roster(path)
            roster = read_roster(path)
            self.assertEqual(roster.class_id, "8a")
            self.assertEqual(
                [row["student_id"] for row in roster.students[:3]],
                ["8a-01", "8a-02", "8a-03"],
            )
            self.assertEqual(
                [row["name"] for row in roster.students[:3]],
                ["Anna Beispiel", "Ben Beispiel", "Carla Beispiel"],
            )

    def test_parameters_are_read_from_final_layout(self):
        parameters = read_parameters(ODS_TEMPLATE_FILE)
        self.assertEqual(parameters.section_maxima, (27, 9, 12, 18))
        self.assertEqual(parameters.total_maximum, 66)
        self.assertEqual(parameters.grade_thresholds[0]["min_points"], 0)
        self.assertEqual(parameters.grade_thresholds[0]["grade_value"], 6.0)
        self.assertEqual(parameters.grade_thresholds[-1]["grade_label"], "1+")

        form = load_form("SE1")
        apply_parameters_to_form(form, parameters)
        self.assertEqual(form["max_points"], 66)
        self.assertEqual(form["grade_thresholds"][7]["grade_value"], 3.3)

    def test_parameter_total_is_derived_from_four_maxima(self):
        import inspect

        source = inspect.getsource(read_parameters)
        self.assertIn("total = sum(maxima)", source)
        self.assertNotIn("_cell(table, 9, 6)", source)

    def test_raw_payload_is_matched_by_student_id_and_time_is_numeric(self):
        form = load_form("SE1")
        apply_parameters_to_form(form, read_parameters(ODS_TEMPLATE_FILE))
        anna_answers = {f"q{i:02d}": (i - 1) % 4 for i in range(1, 23)}
        # Deliberately reverse the rows and provide a wrong Nr. to prove that
        # the writer uses Schüler-ID rather than list position.
        rows = [
            {
                "Nr.": 99,
                "Name": "Ben Beispiel",
                "Schüler-ID": "8a-02",
                "Zeitraum": "Q1",
                "answers": None,
                "raw": None,
            },
            {
                "Nr.": 88,
                "Name": "Anna Beispiel",
                "Schüler-ID": "8a-01",
                "Zeitraum": "Q1",
                "answers": anna_answers,
                "raw": {"submitted_at": "2026-07-20T12:00:00+02:00"},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Selbstevaluation.ods"
            shutil.copy2(ODS_TEMPLATE_FILE, path)
            populate_test_roster(path)
            backup = update_raw_data(
                path,
                {"period_id": "Q1", "started_at": "2026-07-20T09:00:00+02:00"},
                rows,
                form,
                Path(tmp) / "backups",
            )
            self.assertTrue(backup.exists())

            _, root = _read_package(path)
            raw = _table(root, "Rohdaten")
            evaluation = _table(root, "Auswertung")
            self.assertIn(_value(_cell(raw, 2, 4)), (None, ""))
            self.assertIn(_value(_cell(evaluation, 2, 4)), (None, ""))
            self.assertEqual(_value(_cell(evaluation, 3, 4)), "20.07.2026")
            self.assertIn("[Auswertung.D3]", _cell(raw, 3, 4).attrib.get("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}formula", ""))
            self.assertEqual(_value(_cell(raw, 5, 5)), "Q1")
            self.assertAlmostEqual(float(_value(_cell(raw, 5, 6))), 0.5)
            self.assertEqual(
                [_value(_cell(raw, 5, col)) for col in range(7, 29)],
                list(anna_answers.values()),
            )
            # Ben is active for the session, but has not submitted.
            self.assertEqual(_value(_cell(raw, 6, 5)), "Q1")
            self.assertEqual([_value(_cell(raw, 6, col)) for col in range(6, 29)], [-1] * 23)
            # Carla is not part of the provided session snapshot and is reset.
            self.assertEqual([_value(_cell(raw, 7, col)) for col in range(5, 29)], [-1] * 24)


    def test_second_update_works_after_formula_cache_invalidation(self):
        """A prior export may leave Rohdaten formula cells without caches.

        Student-row matching must therefore use Namensliste, not the cached
        values of the formulas in Rohdaten!D.
        """
        form = load_form("SE1")
        apply_parameters_to_form(form, read_parameters(ODS_TEMPLATE_FILE))
        anna_answers = {f"q{i:02d}": (i - 1) % 4 for i in range(1, 23)}
        rows = [{
            "Nr.": 1,
            "Name": "Anna Beispiel",
            "Schüler-ID": "8a-01",
            "Zeitraum": "Q1",
            "answers": anna_answers,
            "raw": {"submitted_at": "2026-07-20T12:00:00+02:00"},
        }]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Selbstevaluation.ods"
            shutil.copy2(ODS_TEMPLATE_FILE, path)
            populate_test_roster(path)

            update_raw_data(path, {"period_id": "Q1"}, rows, form, Path(tmp) / "backups")

            # The formula cache in Rohdaten!D is now absent by design.
            _, root = _read_package(path)
            raw = _table(root, "Rohdaten")
            self.assertIsNone(_value(_cell(raw, 5, 4)))

            # A second transfer must nevertheless find 8a-01 via Namensliste.
            rows[0]["raw"] = {"submitted_at": "2026-07-20T13:30:00+02:00"}
            update_raw_data(path, {"period_id": "Q2"}, rows, form, Path(tmp) / "backups")

            _, root = _read_package(path)
            raw = _table(root, "Rohdaten")
            self.assertEqual(_value(_cell(raw, 5, 5)), "Q2")
            self.assertAlmostEqual(float(_value(_cell(raw, 5, 6))), 13.5 / 24)

    def test_formula_and_style_outside_payload_are_preserved(self):
        form = load_form("SE1")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Selbstevaluation.ods"
            shutil.copy2(ODS_TEMPLATE_FILE, path)
            _, before_root = _read_package(path)
            before_out = _table(before_root, "Auswertung")
            before_formula = _cell(before_out, 5, 10).get(
                "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}formula"
            )
            before_raw = _table(before_root, "Rohdaten")
            before_style = _cell(before_raw, 5, 6).get(
                "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}style-name"
            )

            update_raw_data(path, {"period_id": "Q2"}, [], form, Path(tmp) / "backups")
            _, after_root = _read_package(path)
            after_out = _table(after_root, "Auswertung")
            after_formula = _cell(after_out, 5, 10).get(
                "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}formula"
            )
            after_raw = _table(after_root, "Rohdaten")
            after_style = _cell(after_raw, 5, 6).get(
                "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}style-name"
            )
            self.assertEqual(before_formula, after_formula)
            self.assertEqual(before_style, after_style)
            # Cached formula results are intentionally removed so Calc
            # recalculates from the newly written raw inputs on next open.
            self.assertIsNone(_value(_cell(after_out, 5, 10)))

    def test_open_libreoffice_lock_is_rejected(self):
        form = load_form("SE1")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Selbstevaluation.ods"
            shutil.copy2(ODS_TEMPLATE_FILE, path)
            path.with_name(f".~lock.{path.name}#").write_text("locked", encoding="utf-8")
            with self.assertRaises(PermissionError):
                update_raw_data(path, {"period_id": "Q1"}, [], form, Path(tmp) / "backups")

    def test_required_sheet_order(self):
        _, root = _read_package(ODS_TEMPLATE_FILE)
        table_ns = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
        sheets = [item.get(table_ns + "name") for item in root.iter(table_ns + "table")]
        self.assertEqual(sheets[:4], ["Namensliste", "Parameter", "Rohdaten", "Auswertung"])


if __name__ == "__main__":
    unittest.main()
