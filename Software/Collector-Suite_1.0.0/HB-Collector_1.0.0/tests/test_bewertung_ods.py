import shutil
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from hefter_collector import bewertung_ods
from hefter_collector.bewertung_ods import read_roster, write_hefter_results
from hefter_collector.db import Database


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "fixtures" / "Bewertung_Leer.ods"


def prepare_workbook(path: Path, names: list[str]) -> None:
    entries, root = bewertung_ods._read_package(path)
    table = bewertung_ods._table(root, "Namensliste")
    for position, name in enumerate(names, start=1):
        bewertung_ods._set_value(
            bewertung_ods._cell(table, 4 + position, 3),
            name,
        )
    bewertung_ods._write_package(entries, root, path)


def prepare_registry(path: Path, names: list[str]) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE identities(
              school_year TEXT NOT NULL,
              student_key TEXT NOT NULL COLLATE NOCASE,
              public_token TEXT NOT NULL UNIQUE,
              name TEXT NOT NULL,
              class_id TEXT NOT NULL,
              list_position INTEGER NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              PRIMARY KEY(school_year,student_key)
            );
            INSERT INTO meta(key,value) VALUES('active_school_year','2026/27');
            """
        )
        conn.executemany(
            """INSERT INTO identities(
                 school_year,student_key,public_token,name,class_id,list_position,active
               ) VALUES('2026/27',?,?,?,?,?,1)""",
            [
                (f"8a-{position:02d}", f"token-{position}", name, "8a", position)
                for position, name in enumerate(names, start=1)
            ],
        )


class BewertungOdsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workbook = self.root / "Bewertung.ods"
        shutil.copy2(TEMPLATE, self.workbook)
        self.names = ["Anna Beispiel", "Ben Beispiel", "Carla Beispiel"]
        prepare_workbook(self.workbook, self.names)

    def tearDown(self):
        self.temporary.cleanup()

    def test_roster_is_read_and_matched_to_shared_qr_registry(self):
        registry = self.root / "identities.sqlite3"
        prepare_registry(registry, self.names)
        database = Database(
            self.root / "hb.sqlite3",
            workspace_id="ods-test",
            identity_file=registry,
        )
        count = database.import_ods_roster("8a", read_roster(self.workbook))
        self.assertEqual(count, 3)
        self.assertEqual(
            [row["student_code"] for row in database.students("8a")],
            ["8a-01", "8a-02", "8a-03"],
        )
        self.assertEqual(
            [row["token"] for row in database.students("8a")],
            ["token-1", "token-2", "token-3"],
        )

    def test_results_are_written_to_selected_quarter_with_backup(self):
        backup = write_hefter_results(
            self.workbook,
            quarter=2,
            rows=[
                {
                    "list_position": position,
                    "name": name,
                    "teacher_total": total,
                }
                for position, (name, total) in enumerate(
                    zip(self.names, [31, 28, 35]),
                    start=1,
                )
            ],
            maximum=36,
            session_date=date(2026, 7, 31),
        )
        self.assertTrue(backup.exists())
        _, root = bewertung_ods._read_package(self.workbook)
        sheet = bewertung_ods._table(root, "Hefter")
        self.assertEqual(bewertung_ods._value(bewertung_ods._cell(sheet, 43, 4)), 31)
        self.assertEqual(bewertung_ods._value(bewertung_ods._cell(sheet, 43, 5)), 36)
        self.assertEqual(
            bewertung_ods._cell(sheet, 43, 6).get(bewertung_ods.T + "formula"),
            "of:=IF([.D43]=-1;-1;[.D43]/[.E43]*100)",
        )

    def test_name_mismatch_prevents_write_and_backup(self):
        with self.assertRaisesRegex(ValueError, "stimmt"):
            write_hefter_results(
                self.workbook,
                quarter=1,
                rows=[
                    {
                        "list_position": 1,
                        "name": "Falscher Name",
                        "teacher_total": 30,
                    }
                ],
                maximum=36,
                session_date=date(2026, 7, 31),
            )
        self.assertFalse((self.root / "HB-Collector-Sicherungen").exists())

    def test_full_class_reaches_last_row_of_fourth_quarter(self):
        workbook = self.root / "Bewertung_34.ods"
        shutil.copy2(TEMPLATE, workbook)
        names = [f"Person {position:02d}" for position in range(1, 35)]
        prepare_workbook(workbook, names)
        write_hefter_results(
            workbook,
            quarter=4,
            rows=[
                {
                    "list_position": position,
                    "name": name,
                    "teacher_total": 24 + position % 8,
                }
                for position, name in enumerate(names, start=1)
            ],
            maximum=32,
            session_date=date(2027, 1, 30),
        )
        _, root = bewertung_ods._read_package(workbook)
        sheet = bewertung_ods._table(root, "Hefter")
        self.assertEqual(bewertung_ods._value(bewertung_ods._cell(sheet, 152, 5)), 32)


if __name__ == "__main__":
    unittest.main()
