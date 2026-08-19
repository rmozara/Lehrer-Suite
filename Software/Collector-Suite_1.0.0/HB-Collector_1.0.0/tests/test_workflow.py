import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from hefter_collector.db import Database
from hefter_collector.permutation import generate_derangement

try:
    from hefter_collector.web import workflow_bar
except ImportError:  # pragma: no cover - core-only test environment
    workflow_bar = None


class WorkflowTests(unittest.TestCase):
    def test_sessions_receive_six_digit_codes(self):
        with tempfile.TemporaryDirectory() as temporary:
            db = Database(Path(temporary) / "hb.sqlite3")
            db.import_students(self.sample_students())
            first = db.create_session("8a", "H1", "Hefterbewertung")
            second = db.create_session("8a", "H2", "Hefterbewertung")
            codes = [str(db.session(item)["session_code"]) for item in (first, second)]
            self.assertTrue(all(len(code) == 6 and code.isdigit() for code in codes))
            self.assertNotEqual(codes[0], codes[1])

    @staticmethod
    def sample_students():
        return [
            {"class_id": "8a", "list_position": i, "name": f"Person {i}"}
            for i in range(1, 4)
        ]

    def test_same_class_and_period_can_be_repeated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            self.assertIsNone(db.last_migration_backup)
            db.import_students(self.sample_students())
            first = db.create_session("8a", "H1", "Erster Versuch")
            second = db.create_session("8a", "H1", "Wiederholung")
            self.assertNotEqual(first, second)
            self.assertEqual(len(db.sessions()), 2)

    def test_sessions_are_separated_by_working_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.sqlite3"
            first_db = Database(path, "workspace-a")
            second_db = Database(path, "workspace-b")
            first_db.import_students(self.sample_students())
            first = first_db.create_session("8a", "H1", "Mappe A")
            second = second_db.create_session("8a", "H1", "Mappe B")

            self.assertNotEqual(first, second)
            self.assertEqual([row["id"] for row in first_db.sessions()], [first])
            self.assertEqual([row["id"] for row in second_db.sessions()], [second])
            self.assertIsNone(first_db.session(second))
            self.assertIsNone(second_db.session(first))

    def test_existing_sessions_are_assigned_to_first_selected_workspace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "old.sqlite3"
            conn = sqlite3.connect(path)
            conn.executescript(
                """
                CREATE TABLE sessions(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  class_id TEXT NOT NULL,
                  period TEXT NOT NULL,
                  title TEXT NOT NULL,
                  phase TEXT NOT NULL DEFAULT 'setup',
                  teacher_review_opened INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL
                );
                INSERT INTO sessions(
                  class_id,period,title,phase,teacher_review_opened,created_at
                ) VALUES('8a','H1','Bestehende Bewertung','self',0,'2026-07-30T20:00:00+02:00');
                """
            )
            conn.close()

            backup_dir = Path(temp_dir) / "backups"
            migrated = Database(
                path,
                "erster-arbeitsordner",
                migration_backup_dir=backup_dir,
            )
            self.assertEqual(migrated.session(1)["workspace_id"], "erster-arbeitsordner")
            self.assertIsNotNone(migrated.last_migration_backup)
            self.assertTrue(migrated.last_migration_backup.exists())
            with sqlite3.connect(migrated.last_migration_backup) as backup:
                self.assertEqual(
                    backup.execute("SELECT title FROM sessions").fetchone()[0],
                    "Bestehende Bewertung",
                )
            self.assertEqual(len(Database(path, "anderer-arbeitsordner").sessions()), 0)

    def test_existing_database_loses_old_unique_constraint_without_data_loss(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "old.sqlite3"
            conn = sqlite3.connect(path)
            conn.executescript(
                """
                PRAGMA foreign_keys=ON;
                CREATE TABLE students(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  class_id TEXT NOT NULL,
                  list_position INTEGER NOT NULL,
                  student_code TEXT NOT NULL,
                  name TEXT NOT NULL,
                  token TEXT NOT NULL UNIQUE,
                  active INTEGER NOT NULL DEFAULT 1,
                  UNIQUE(class_id, list_position),
                  UNIQUE(class_id, student_code)
                );
                CREATE TABLE sessions(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  class_id TEXT NOT NULL,
                  period TEXT NOT NULL,
                  title TEXT NOT NULL,
                  phase TEXT NOT NULL DEFAULT 'setup',
                  teacher_review_opened INTEGER NOT NULL DEFAULT 0,
                  created_at TEXT NOT NULL,
                  UNIQUE(class_id, period)
                );
                INSERT INTO sessions(
                  class_id, period, title, phase,
                  teacher_review_opened, created_at
                ) VALUES('8a','H1','Abgebrochener Versuch','self',1,'2026-07-30T20:00:00+02:00');
                """
            )
            conn.close()

            db = Database(path)
            self.assertEqual(db.session(1)["title"], "Abgebrochener Versuch")
            self.assertEqual(db.session(1)["archived"], 0)
            db.import_students(self.sample_students())
            second = db.create_session("8a", "H1", "Neuer Versuch")
            self.assertEqual(second, 2)

    def test_closed_session_can_be_repeated_with_fresh_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            db.import_students(self.sample_students())
            original = db.create_session("8a", "H1", "Hefterbewertung")
            db.add_exclusion(original, 1, 3)
            db.set_phase(original, "closed")

            repeated = db.repeat_session(original)

            self.assertNotEqual(repeated, original)
            self.assertEqual(db.session(repeated)["class_id"], "8a")
            self.assertEqual(db.session(repeated)["period"], "H1")
            self.assertEqual(db.session(repeated)["title"], "Hefterbewertung")
            self.assertEqual(db.session(repeated)["phase"], "setup")
            self.assertEqual(len(db.roster(repeated)), 3)
            repeated_exclusions = db.exclusions(repeated)
            self.assertEqual(
                [
                    (row["student_a_no"], row["student_b_no"])
                    for row in repeated_exclusions
                ],
                [(1, 3)],
            )

    def test_new_exclusion_invalidates_assignment_and_is_locked_in_peer_phase(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            db.import_students(
                [
                    {"class_id": "8a", "list_position": i, "name": f"Person {i}"}
                    for i in range(1, 7)
                ]
            )
            session_id = db.create_session("8a", "H1", "Hefterbewertung")
            ids = [row["student_id"] for row in db.roster(session_id)]
            db.save_assignments(session_id, generate_derangement(ids))
            self.assertEqual(len(db.assignment_mapping(session_id)), 6)

            db.add_exclusion(session_id, 1, 2)
            self.assertEqual(db.assignment_mapping(session_id), {})
            self.assertEqual(len(db.exclusions(session_id)), 1)

            mapping = generate_derangement(
                ids,
                excluded_pairs=db.exclusion_pairs(session_id),
            )
            db.save_assignments(session_id, mapping)
            db.set_phase(session_id, "peer")
            with self.assertRaisesRegex(ValueError, "vor Beginn"):
                db.add_exclusion(session_id, 3, 4)

    def test_archive_hides_session_and_restore_brings_it_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            db.import_students(self.sample_students())
            session_id = db.create_session("8a", "H1", "Hefterbewertung")
            db.set_phase(session_id, "closed")

            db.archive_session(session_id)
            self.assertEqual(db.sessions(), [])
            self.assertEqual([row["id"] for row in db.sessions(archived=True)], [session_id])

            db.restore_session(session_id)
            self.assertEqual([row["id"] for row in db.sessions()], [session_id])
            self.assertEqual(db.sessions(archived=True), [])

    def test_unfinished_session_cannot_be_archived_or_repeated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            db.import_students(self.sample_students())
            session_id = db.create_session("8a", "H1", "Hefterbewertung")
            with self.assertRaisesRegex(ValueError, "abgeschlossen"):
                db.archive_session(session_id)
            with self.assertRaisesRegex(ValueError, "abgeschlossen"):
                db.repeat_session(session_id)

    def test_only_archived_session_is_deleted_and_backup_keeps_it(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db = Database(root / "test.sqlite3")
            db.import_students(self.sample_students())
            session_id = db.create_session("8a", "H1", "Hefterbewertung")
            roster = db.roster(session_id)
            values = {"zustand": 3}
            db.save_rating(session_id, roster[0]["student_id"], None, "teacher", values)
            db.set_phase(session_id, "closed")
            db.archive_session(session_id)

            backup = db.backup_to(root / "backup.sqlite3")
            db.delete_archived_session(session_id)

            self.assertIsNone(db.session(session_id))
            with sqlite3.connect(db.path) as conn:
                self.assertEqual(
                    conn.execute(
                        "SELECT COUNT(*) FROM ratings WHERE session_id=?",
                        (session_id,),
                    ).fetchone()[0],
                    0,
                )
            with sqlite3.connect(backup) as conn:
                self.assertEqual(
                    conn.execute(
                        "SELECT archived FROM sessions WHERE id=?",
                        (session_id,),
                    ).fetchone()[0],
                    1,
                )

    def test_explicit_phase_completion_states(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            rows = [
                {"class_id": "8a", "list_position": i, "student_code": f"8a-{i:02d}", "name": f"Person {i}"}
                for i in range(1, 4)
            ]
            db.import_students(rows)
            session_id = db.create_session("8a", "1. Halbjahr", "Hefterbewertung")
            for phase in (
                "self", "self_closed", "peer", "peer_closed",
                "teacher", "teacher_closed", "closed",
            ):
                db.set_phase(session_id, phase)
                self.assertEqual(db.session(session_id)["phase"], phase)

    def test_teacher_review_must_be_opened_before_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            db.import_students([
                {"class_id": "8a", "list_position": i, "name": f"Person {i}"}
                for i in range(1, 4)
            ])
            session_id = db.create_session("8a", "H1", "Hefterbewertung")
            self.assertEqual(db.session(session_id)["teacher_review_opened"], 0)
            db.mark_teacher_review_opened(session_id)
            self.assertEqual(db.session(session_id)["teacher_review_opened"], 1)

    @unittest.skipIf(workflow_bar is None, "FastAPI-Testabhängigkeiten sind nicht installiert.")
    def test_teacher_completion_is_separate_from_final_close(self):
        locked = workflow_bar(1, "teacher", True, False)
        self.assertIn("zuerst Lehrerprüfung öffnen", locked)
        self.assertNotIn("value='teacher_closed'", locked)

        unlocked = workflow_bar(1, "teacher", True, True)
        self.assertIn("value='teacher_closed'", unlocked)
        self.assertIn("Lehrerbewertung abschließen", unlocked)
        self.assertIn("zum Öffnen klicken", unlocked)

        pending = workflow_bar(1, "peer_closed", True, False)
        self.assertIn("zum Aktivieren klicken", pending)
        self.assertNotIn("zum Öffnen klicken", pending)

        intermediate = workflow_bar(1, "teacher_closed", True, True)
        self.assertIn("value='teacher'", intermediate)
        self.assertIn("value='closed'", intermediate)
        self.assertIn("zum Abschließen klicken", intermediate)
        self.assertIn("noch offen", intermediate)
        self.assertNotIn("noch nicht abgeschlossen", intermediate)
        self.assertIn("Wieder öffnen", intermediate)
        self.assertNotIn("done clickable", intermediate)

    @unittest.skipIf(workflow_bar is None, "FastAPI-Testabhängigkeiten sind nicht installiert.")
    def test_peer_start_waits_for_assignment(self):
        without_assignment = workflow_bar(1, "self_closed", False)
        self.assertIn("zuerst Zuordnung erzeugen", without_assignment)
        self.assertNotIn("name='phase' value='peer'", without_assignment)

        with_assignment = workflow_bar(1, "self_closed", True)
        self.assertIn("zum Start klicken", with_assignment)
        self.assertIn("name='phase' value='peer'", with_assignment)

    def test_complete_three_role_workflow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db = Database(Path(temp_dir) / "test.sqlite3")
            rows = [
                {"class_id": "8a", "list_position": i, "student_code": f"8a-{i:02d}", "name": f"Person {i}"}
                for i in range(1, 7)
            ]
            self.assertEqual(db.import_students(rows), 6)
            session_id = db.create_session("8a", "1. Halbjahr", "Hefterbewertung")
            roster = db.roster(session_id)
            ids = [row["student_id"] for row in roster]
            db.save_assignments(session_id, generate_derangement(ids))
            self.assertEqual(len(db.assignments(session_id)), 6)

            values = {key: 3 for key in ("zustand", "struktur", "datum")}
            for student_id in ids:
                db.save_rating(session_id, student_id, student_id, "self", values)
            for assignment in db.assignments(session_id):
                db.save_rating(session_id, assignment["subject_id"], assignment["reviewer_id"], "peer", values)
            for student_id in ids:
                db.save_rating(session_id, student_id, None, "teacher", values)

            comparisons = db.comparisons(session_id)
            self.assertEqual(len(comparisons), 6)
            self.assertTrue(all(row["self_total"] == 9 for row in comparisons))
            self.assertTrue(all(row["peer_total"] == 9 for row in comparisons))
            self.assertTrue(all(row["teacher_total"] == 9 for row in comparisons))
            self.assertEqual(json.loads(comparisons[0]["teacher_values"]), values)
