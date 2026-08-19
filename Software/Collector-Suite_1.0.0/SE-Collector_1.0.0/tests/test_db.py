import sqlite3
import tempfile
import unittest
from pathlib import Path

from se_collector.db import Database


ROWS_NEW = [
    {"class_id": "8a", "student_id": "8a-01", "name": "Anna Beispiel", "list_position": 1},
    {"class_id": "8a", "student_id": "8a-02", "name": "Ben Beispiel", "list_position": 2},
    {"class_id": "8a", "student_id": "8a-03", "name": "Carla Beispiel", "list_position": 3},
]

ROWS_OLD = [
    {"class_id": "8a", "student_id": "S001", "name": "Anna Beispiel", "list_position": 1},
    {"class_id": "8a", "student_id": "S002", "name": "Ben Beispiel", "list_position": 2},
    {"class_id": "8a", "student_id": "S003", "name": "Carla Beispiel", "list_position": 3},
]


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.sqlite3"
        self.db = Database(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_database_needs_no_migration_backup(self):
        self.assertIsNone(self.db.last_migration_backup)

    def test_closed_session_can_be_archived_restored_and_deleted(self):
        self.db.import_students(ROWS_NEW)
        session, _ = self.db.start_or_resume_session("8a", "SE1", "1.0.0", "Q1")
        self.db.close_session(session["id"])
        self.db.archive_session(session["id"])
        self.assertEqual([row["id"] for row in self.db.recent_sessions(archived=True)], [session["id"]])
        self.db.restore_session(session["id"])
        self.assertEqual(self.db.recent_sessions(archived=True), [])
        self.db.archive_session(session["id"])
        self.db.delete_session(session["id"])
        self.assertIsNone(self.db.session_by_id(session["id"]))

    def test_import_replaces_active_roster_without_duplicates(self):
        self.db.import_students(ROWS_OLD)
        self.db.import_students(ROWS_NEW)
        students = self.db.students_for_class("8a")
        self.assertEqual(len(students), 3)
        self.assertEqual([row["student_id"] for row in students], ["8a-01", "8a-02", "8a-03"])

    def test_legacy_database_is_backed_up_before_workspace_migration(self):
        legacy = Path(self.tmp.name) / "legacy.sqlite3"
        with sqlite3.connect(legacy) as conn:
            conn.executescript(
                """
                CREATE TABLE sessions(
                  id INTEGER PRIMARY KEY,
                  public_token TEXT NOT NULL UNIQUE,
                  class_id TEXT NOT NULL,
                  form_id TEXT NOT NULL,
                  form_version TEXT NOT NULL,
                  period_id TEXT NOT NULL,
                  session_code TEXT NOT NULL,
                  started_at TEXT NOT NULL,
                  closed_at TEXT,
                  active INTEGER NOT NULL DEFAULT 1
                );
                INSERT INTO sessions VALUES(
                  1,'session-token','8a','SE1','1.0','Q1','123456',
                  '2026-07-31T10:00:00+02:00',NULL,1
                );
                """
            )
        backup_dir = Path(self.tmp.name) / "backups"
        migrated = Database(
            legacy,
            "arbeitsordner",
            migration_backup_dir=backup_dir,
        )
        self.assertIsNotNone(migrated.last_migration_backup)
        self.assertTrue(migrated.last_migration_backup.exists())
        self.assertEqual(
            migrated.session_by_id(1)["workspace_id"],
            "arbeitsordner",
        )
        with sqlite3.connect(migrated.last_migration_backup) as backup:
            columns = {
                row[1] for row in backup.execute("PRAGMA table_info(sessions)")
            }
            self.assertNotIn("workspace_id", columns)

    def test_new_roster_deactivates_previous_class(self):
        self.db.import_students([
            {"class_id": "8a", "student_id": "8a-01", "name": "Anna", "list_position": 1}
        ])
        self.db.import_students([
            {"class_id": "9b", "student_id": "9b-01", "name": "Bela", "list_position": 1}
        ])
        self.assertEqual(self.db.classes(), ["9b"])

    def test_same_period_reuses_same_session(self):
        self.db.import_students(ROWS_NEW)
        first, created_first = self.db.start_or_resume_session("8a", "SE1", "0.5.0", "Q1 2026/27")
        second, created_second = self.db.start_or_resume_session("8a", "SE1", "0.5.0", "Q1 2026/27")
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first["id"], second["id"])

    def test_sessions_are_separated_by_working_folder(self):
        first_db = Database(self.path, "workspace-a")
        second_db = Database(self.path, "workspace-b")
        first_db.import_students(ROWS_NEW)
        first, _ = first_db.start_or_resume_session("8a", "SE1", "1.0.0", "Q1")
        second, _ = second_db.start_or_resume_session("8a", "SE1", "1.0.0", "Q1")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual([row["id"] for row in first_db.recent_sessions()], [first["id"]])
        self.assertEqual([row["id"] for row in second_db.recent_sessions()], [second["id"]])
        self.assertIsNone(first_db.session_by_id(second["id"]))

    def test_reset_keeps_session_id_and_clears_submission(self):
        self.db.import_students(ROWS_NEW)
        session, _ = self.db.start_or_resume_session("8a", "SE1", "0.5.0", "Q1")
        student = self.db.students_for_class("8a")[0]
        answers = {f"q{i:02d}": 3 for i in range(1, 23)}
        self.db.save_submission(session["id"], student["id"], answers, 66, "1+", 0.7)
        reset = self.db.reset_session(session["id"])
        self.assertEqual(reset["id"], session["id"])
        self.assertIsNone(self.db.submission_for(session["id"], student["id"]))
        self.assertEqual(self.db.session_progress(session["id"])["submitted"], 0)

    def test_only_one_active_session_per_class(self):
        self.db.import_students(ROWS_NEW)
        first, _ = self.db.start_or_resume_session("8a", "SE1", "0.5.0", "Q1")
        second, _ = self.db.start_or_resume_session("8a", "SE1", "0.5.0", "Q2")
        self.assertFalse(self.db.session_by_id(first["id"])["active"])
        self.assertTrue(self.db.session_by_id(second["id"])["active"])

    def test_reopen_session_preserves_submissions_and_uses_new_code(self):
        self.db.import_students(ROWS_NEW)
        session, _ = self.db.start_or_resume_session("8a", "SE1", "0.5.0", "Q1")
        student = self.db.students_for_class("8a")[0]
        answers = {f"q{i:02d}": 3 for i in range(1, 23)}
        self.db.save_submission(session["id"], student["id"], answers, 66, "1+", 0.7)
        old_code = session["session_code"]
        self.db.close_session(session["id"])

        reopened = self.db.reopen_session(session["id"])

        self.assertTrue(reopened["active"])
        self.assertIsNone(reopened["closed_at"])
        self.assertNotEqual(reopened["session_code"], old_code)
        self.assertIsNotNone(self.db.submission_for(session["id"], student["id"]))


if __name__ == "__main__":
    unittest.main()
