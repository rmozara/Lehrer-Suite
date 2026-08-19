import shutil
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from hefter_collector import bewertung_ods as ods
from hefter_collector.bewertung_ods import read_roster, roster_class, read_subject, write_hefter_results


ROOT = Path(__file__).resolve().parent.parent


class HefterbewertungOdsTests(unittest.TestCase):
    def test_template_has_examples_defaults_and_hb_formulas(self):
        _, root = ods._read_package(ROOT / "templates" / "Hefterbewertung.ods")
        names = ods._table(root, "Namensliste")
        raw = ods._table(root, "Rohdaten")
        summary = ods._table(root, "Auswertung")
        parameters = ods._table(root, "Parameter")
        self.assertEqual(
            [(ods._value(ods._cell(names, row, 3)), ods._value(ods._cell(names, row, 4))) for row in range(5, 8)],
            [("Anna Beispiel", "8a-01"), ("Ben Beispiel", "8a-02"), ("Carla Beispiel", "8a-03")],
        )
        self.assertTrue(all(ods._value(ods._cell(names, row, 3)) == -1 for row in range(8, 39)))
        self.assertTrue(all(ods._value(ods._cell(raw, 5, column)) == -1 for column in range(5, 36)))
        self.assertEqual(ods._value(ods._cell(parameters, 5, 6)), 36)
        self.assertEqual(ods._value(ods._cell(summary, 3, 4)), "Datum")
        self.assertEqual(ods._value(ods._cell(summary, 5, 8)), 36)
        self.assertIn("Rohdaten.AA5:.AI5", ods._cell(summary, 5, 6).get(ods.T + "formula"))
        self.assertIn("VLOOKUP", ods._cell(summary, 5, 10).get(ods.T + "formula"))
        self.assertEqual(read_subject(ROOT / "templates" / "Hefterbewertung.ods"), "Physik")

    def test_template_keeps_the_se_visual_cell_styles(self):
        se_template = ROOT.parent / "SE-Collector_1.0.0" / "templates" / "Selbstevaluation.ods"
        _, hb_root = ods._read_package(ROOT / "templates" / "Hefterbewertung.ods")
        _, se_root = ods._read_package(se_template)
        for sheet_name, cells in {
            "Namensliste": ((3, 2), (4, 2), (5, 2), (5, 3), (5, 4)),
            "Parameter": ((3, 2), (4, 2), (5, 2), (3, 5), (4, 5), (5, 6)),
            "Rohdaten": ((3, 2), (3, 4), (4, 2), (4, 3), (4, 4), (4, 7), (5, 2), (5, 3), (5, 7)),
            "Auswertung": ((3, 2), (3, 4), (4, 2), (4, 3), (4, 4), (5, 2), (5, 3), (5, 4)),
        }.items():
            hb_sheet = ods._table(hb_root, sheet_name)
            se_sheet = ods._table(se_root, sheet_name)
            for row, column in cells:
                self.assertEqual(
                    ods._cell(hb_sheet, row, column).get(ods.T + "style-name"),
                    ods._cell(se_sheet, row, column).get(ods.T + "style-name"),
                    f"Abweichender Stil in {sheet_name}!{row}/{column}",
                )

    def test_standalone_workbook_supplies_class_and_receives_results(self):
        with tempfile.TemporaryDirectory() as temporary:
            workbook = Path(temporary) / "Hefterbewertung.ods"
            shutil.copy2(ROOT / "templates" / "Hefterbewertung.ods", workbook)
            entries, root = ods._read_package(workbook)
            names = ods._table(root, "Namensliste")
            for position, name in enumerate(("Anna Beispiel", "Ben Beispiel", "Carla Beispiel"), 1):
                ods._set_value(ods._cell(names, position + 4, 3), name)
                ods._set_value(ods._cell(names, position + 4, 4), f"8a-{position:02d}")
            ods._write_package(entries, root, workbook)

            roster = read_roster(workbook)
            self.assertEqual(roster_class(roster), "8a")
            backup = write_hefter_results(
                workbook,
                rows=[
                    {"list_position": pos, "student_code": f"8a-{pos:02d}", "name": name,
                     "self_total": 27, "peer_total": 27, "teacher_total": 30,
                     "self_values": json.dumps({key: 3 for key in (
                         "beschriftung", "zustand", "struktur", "ablage", "vollstaendigkeit",
                         "bearbeitung", "darstellungen", "lesbarkeit", "abgabe")}),
                     "peer_values": json.dumps({key: 3 for key in (
                         "beschriftung", "zustand", "struktur", "ablage", "vollstaendigkeit",
                         "bearbeitung", "darstellungen", "lesbarkeit", "abgabe")}),
                     "teacher_values": json.dumps({key: (4 if i < 3 else 3) for i, key in enumerate((
                         "beschriftung", "zustand", "struktur", "ablage", "vollstaendigkeit",
                         "bearbeitung", "darstellungen", "lesbarkeit", "abgabe"))}),
                     "self_submitted_at": "2026-08-06T09:00:00",
                     "peer_submitted_at": "2026-08-06T09:15:00",
                     "teacher_submitted_at": "2026-08-06T10:00:00"}
                    for pos, name in enumerate(("Anna Beispiel", "Ben Beispiel", "Carla Beispiel"), 1)
                ],
                maximum=36,
                session_date=date(2026, 8, 6),
                period="1. Halbjahr 2026/27",
            )
            self.assertTrue(backup.exists())
            _, updated = ods._read_package(workbook)
            raw = ods._table(updated, "Rohdaten")
            summary = ods._table(updated, "Auswertung")
            self.assertEqual(ods._cell(raw, 5, 4).get(ods.T + "formula"), "of:=[Namensliste.D5]")
            self.assertEqual(ods._value(ods._cell(raw, 5, 5)), "1. Halbjahr 2026/27")
            self.assertEqual(ods._value(ods._cell(raw, 5, 6)), "09:00")
            self.assertEqual(ods._value(ods._cell(raw, 5, 27)), 4)
            self.assertEqual(ods._value(ods._cell(summary, 3, 4)), "06.08.2026")
            self.assertIn("Rohdaten.AA5:.AI5", ods._cell(summary, 5, 6).get(ods.T + "formula"))

    def test_single_criterion_updates_maximum_and_formula_ranges(self):
        with tempfile.TemporaryDirectory() as temporary:
            workbook = Path(temporary) / "Hefterbewertung.ods"
            shutil.copy2(ROOT / "templates" / "Hefterbewertung.ods", workbook)
            write_hefter_results(
                workbook,
                rows=[{
                    "list_position": 1, "student_code": "8a-01", "name": "Anna Beispiel",
                    "self_total": 3, "peer_total": 2, "teacher_total": 4,
                    "self_values": json.dumps({"beschriftung": 3}),
                    "peer_values": json.dumps({"beschriftung": 2}),
                    "teacher_values": json.dumps({"beschriftung": 4}),
                    "self_submitted_at": "2026-08-06T09:00:00",
                    "peer_submitted_at": "2026-08-06T09:15:00",
                    "teacher_submitted_at": "2026-08-06T10:00:00",
                }],
                maximum=4,
                session_date=date(2026, 8, 6),
                period="Test",
                criterion_ids=["beschriftung"],
            )
            _, updated = ods._read_package(workbook)
            parameters = ods._table(updated, "Parameter")
            summary = ods._table(updated, "Auswertung")
            self.assertEqual(ods._value(ods._cell(parameters, 5, 6)), 4)
            self.assertEqual(ods._value(ods._cell(parameters, 6, 6)), 1)
            self.assertIn("Rohdaten.I5:.I5", ods._cell(summary, 5, 4).get(ods.T + "formula"))
            self.assertIn("Rohdaten.AA5:.AA5", ods._cell(summary, 5, 6).get(ods.T + "formula"))


if __name__ == "__main__":
    unittest.main()
