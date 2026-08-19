import sqlite3
import tempfile
import unittest
from pathlib import Path

from qr_generator.registry import Registry


ROWS = [
    {"class_id": "8a", "student_id": "8a-01", "list_position": 1, "name": "Anna"},
    {"class_id": "8a", "student_id": "8a-02", "list_position": 2, "name": "Ben"},
    {"class_id": "8a", "student_id": "8a-03", "list_position": 3, "name": "Carla"},
]


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.registry = Registry(Path(self.temporary.name) / "identities.sqlite3")

    def tearDown(self):
        self.temporary.cleanup()

    def test_new_registry_needs_no_migration_backup(self):
        self.assertIsNone(self.registry.last_migration_backup)

    def test_reimport_keeps_tokens(self):
        self.registry.import_students("2026/27", ROWS)
        first = {row["student_key"]: row["public_token"] for row in self.registry.students("8a")}
        self.registry.import_students("2026/27", list(reversed(ROWS)))
        second = {row["student_key"]: row["public_token"] for row in self.registry.students("8a")}
        self.assertEqual(first, second)

    def test_reimport_keeps_unique_personal_codes(self):
        self.registry.import_students("2026/27", ROWS)
        first = {
            row["student_key"]: row["short_code"]
            for row in self.registry.students("8a")
        }
        self.registry.import_students("2026/27", list(reversed(ROWS)))
        second = {
            row["student_key"]: row["short_code"]
            for row in self.registry.students("8a")
        }
        self.assertEqual(first, second)
        self.assertEqual(len(set(first.values())), 3)
        self.assertTrue(all(len(code) == 8 for code in first.values()))

    def test_existing_registry_is_migrated_without_changing_token(self):
        path = Path(self.temporary.name) / "legacy.sqlite3"
        with sqlite3.connect(path) as conn:
            conn.executescript(
                """
                CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                INSERT INTO meta VALUES('active_school_year','2026/27');
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
                INSERT INTO identities VALUES(
                  '2026/27','8a-01','bestehender-token-abcdefghijklmnopqrstuvwxyz',
                  'Anna','8a',1,1
                );
                """
            )
        migrated = Registry(path)
        student = migrated.students("8a")[0]
        self.assertIsNotNone(migrated.last_migration_backup)
        self.assertTrue(migrated.last_migration_backup.exists())
        self.assertEqual(
            student["public_token"],
            "bestehender-token-abcdefghijklmnopqrstuvwxyz",
        )
        self.assertEqual(len(student["short_code"]), 8)
        with sqlite3.connect(migrated.last_migration_backup) as backup:
            columns = {
                row[1] for row in backup.execute("PRAGMA table_info(identities)")
            }
            self.assertNotIn("short_code", columns)

    def test_new_school_year_creates_new_tokens(self):
        self.registry.import_students("2026/27", ROWS)
        first = self.registry.students("8a")[0]["public_token"]
        self.registry.import_students("2027/28", ROWS)
        second = self.registry.students("8a")[0]["public_token"]
        self.assertNotEqual(first, second)

    def test_missing_or_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.registry.import_students("2026/27", [{**ROWS[0], "student_id": ""}])
        with self.assertRaisesRegex(ValueError, "doppelt"):
            self.registry.import_students("2026/27", [ROWS[0], ROWS[0]])

    def test_class_summaries_show_imported_people(self):
        self.registry.import_students("2026/27", ROWS)
        self.registry.import_students(
            "2026/27",
            [{"class_id": "9b", "student_id": "9b-01", "list_position": 1, "name": "Cem"}],
        )
        self.assertEqual(
            self.registry.class_summaries(),
            [
                {"class_id": "8a", "student_count": 3},
                {"class_id": "9b", "student_count": 1},
            ],
        )


if __name__ == "__main__":
    unittest.main()
