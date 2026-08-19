import tempfile
import unittest
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover - allows core-only test environments
    TestClient = None

from hefter_collector.config import Settings, hash_password
from hefter_collector.db import Database
from hefter_collector.testdata import sample_students


@unittest.skipIf(TestClient is None, "FastAPI-Testabhängigkeiten sind nicht installiert.")
class HttpWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary.name) / "http-test.sqlite3"
        self.settings_file = Path(self.temporary.name) / "settings.json"
        self.password = "Testpasswort-123"
        settings = Settings(
            admin_user="lehrkraft",
            admin_password_hash=hash_password(self.password),
            host="127.0.0.1",
            port=8765,
        )
        self.settings_file.write_text(
            json.dumps(
                {
                    "admin_user": "lehrkraft",
                    "admin_password_hash": hash_password(self.password),
                    "host": "127.0.0.1",
                    "port": 8765,
                    "direct_base_url": "",
                }
            ),
            encoding="utf-8",
        )
        self.settings_patch = patch(
            "hefter_collector.config.SETTINGS_FILE",
            self.settings_file,
        )
        self.data_patch = patch(
            "hefter_collector.config.DATA_DIR",
            Path(self.temporary.name),
        )
        self.shared_password_patch = patch(
            "hefter_collector.config.SHARED_TEACHER_SETTINGS_FILE",
            Path(self.temporary.name) / "teacher_settings.json",
        )
        self.settings_patch.start()
        self.data_patch.start()
        self.shared_password_patch.start()
        with (
            patch("hefter_collector.web.DB_FILE", self.db_path),
            patch("hefter_collector.web.WORKSPACE_ID", "http-tests"),
            patch("hefter_collector.web.WORK_DIR", Path(self.temporary.name)),
            patch(
                "hefter_collector.web.SHARED_IDENTITY_FILE",
                Path(self.temporary.name) / "identities.sqlite3",
            ),
        ):
            from hefter_collector.web import create_app

            self.client = TestClient(create_app(settings))
        self.auth = ("lehrkraft", self.password)
        self.db = Database(self.db_path, "http-tests")
        self.db.import_students(sample_students(6))
        self.session_id = self.db.create_session("8a", "H1", "Hefterbewertung")

    def tearDown(self):
        self.client.close()
        self.settings_patch.stop()
        self.data_patch.stop()
        self.shared_password_patch.stop()
        self.temporary.cleanup()

    def phase(self, target: str):
        return self.client.post(
            f"/admin/session/{self.session_id}/phase",
            data={"phase": target},
            auth=self.auth,
            follow_redirects=False,
        )

    def test_complete_workflow_through_real_student_routes(self):
        self.assertEqual(self.phase("self").status_code, 303)
        session_code = self.db.session(self.session_id)["session_code"]
        for student in self.db.roster(self.session_id):
            response = self.client.post(
                f"/s/{student['token']}/self?session_code={session_code}",
                data={"c_beschriftung": "3"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)
        self.assertEqual(len([row for row in self.db.comparisons(self.session_id) if row["self_total"]]), 6)

        self.assertEqual(self.phase("self_closed").status_code, 303)
        self.assertEqual(
            self.client.post(
                f"/admin/session/{self.session_id}/assign",
                auth=self.auth,
                follow_redirects=False,
            ).status_code,
            303,
        )
        self.assertEqual(self.phase("peer").status_code, 303)
        for student in self.db.roster(self.session_id):
            response = self.client.post(
                f"/s/{student['token']}/peer?session_code={session_code}",
                data={"c_beschriftung": "3"},
                follow_redirects=False,
            )
            self.assertEqual(response.status_code, 303)
        self.assertEqual(len([row for row in self.db.comparisons(self.session_id) if row["peer_total"]]), 6)

        self.assertEqual(self.phase("peer_closed").status_code, 303)
        self.assertEqual(self.phase("teacher").status_code, 303)
        blocked = self.phase("teacher_closed")
        self.assertEqual(blocked.status_code, 200)
        self.assertIn("mindestens einmal geöffnet", blocked.text)

        review = self.client.get(
            f"/admin/session/{self.session_id}/review",
            auth=self.auth,
        )
        self.assertEqual(review.status_code, 200)
        empty = self.phase("teacher_closed")
        self.assertEqual(empty.status_code, 200)
        self.assertIn("0 von 6 Personen bewertet", empty.text)
        roster = self.db.roster(self.session_id)
        self.db.save_rating(
            self.session_id,
            roster[0]["student_id"],
            None,
            "teacher",
            {"beschriftung": 3},
        )
        partial = self.phase("teacher_closed")
        self.assertEqual(partial.status_code, 200)
        self.assertIn("1 von 6 Personen bewertet", partial.text)
        self.assertIsNotNone(
            self.db.rating(self.session_id, roster[0]["student_id"], "teacher")
        )
        for student in roster[1:]:
            self.db.save_rating(
                self.session_id,
                student["student_id"],
                None,
                "teacher",
                {"beschriftung": 3},
            )
        self.assertEqual(self.phase("teacher_closed").status_code, 303)
        self.assertEqual(self.phase("closed").status_code, 303)
        self.assertEqual(self.db.session(self.session_id)["phase"], "closed")

    def test_peer_phase_cannot_start_without_assignment(self):
        self.phase("self")
        self.phase("self_closed")
        response = self.phase("peer")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Zuordnung vollständig", response.text)
        self.assertEqual(self.db.session(self.session_id)["phase"], "self_closed")

    def test_two_qr_camera_identifies_student_without_using_card_host(self):
        self.assertEqual(self.phase("self").status_code, 303)
        session = self.db.session(self.session_id)
        student = self.db.students("8a")[0]
        access = self.client.get(f"/access/{session['access_token']}")
        self.assertEqual(access.status_code, 200)
        self.assertIn("Kamera öffnen", access.text)
        self.assertIn("capture='environment'", access.text)

        old_card_url = f"http://192.168.50.10:8765/p/{student['token']}"
        with patch(
            "hefter_collector.web.decode_qr_image",
            return_value=old_card_url,
        ):
            response = self.client.post(
                f"/access/{session['access_token']}/scan",
                data={"session_code": session["session_code"]},
                files={"qr_image": ("karte.jpg", b"testbild", "image/jpeg")},
                follow_redirects=False,
            )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(
            response.headers["location"],
            f"/s/{student['token']}?session_code={session['session_code']}",
        )

        identity_file = Path(self.temporary.name) / "identities.sqlite3"
        with sqlite3.connect(identity_file) as conn:
            conn.executescript(
                """
                CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                INSERT INTO meta VALUES('active_school_year','2026/27');
                CREATE TABLE identities(
                  school_year TEXT,student_key TEXT,public_token TEXT,
                  short_code TEXT,name TEXT,class_id TEXT,
                  list_position INTEGER,active INTEGER
                );
                """
            )
            conn.execute(
                "INSERT INTO identities VALUES(?,?,?,?,?,?,?,1)",
                (
                    "2026/27",
                    student["student_code"],
                    student["token"],
                    "ABCD2345",
                    student["name"],
                    student["class_id"],
                    student["list_position"],
                ),
            )
        by_code = self.client.post(
            f"/access/{session['access_token']}/code",
            data={"personal_code": "abcd2345", "session_code": session["session_code"]},
            follow_redirects=False,
        )
        self.assertEqual(by_code.status_code, 303)
        self.assertEqual(
            by_code.headers["location"],
            f"/s/{student['token']}?session_code={session['session_code']}",
        )
        invalid = self.client.post(
            f"/access/{session['access_token']}/code",
            data={"personal_code": "ZZZZ9999", "session_code": session["session_code"]},
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertIn("Code ungültig", invalid.text)

        wrong_session_code = self.client.post(
            f"/access/{session['access_token']}/code",
            data={"personal_code": "abcd2345", "session_code": "000000"},
        )
        self.assertIn("Sitzungscode ist ungültig", wrong_session_code.text)

    def test_self_rating_can_be_reopened_during_self_phase(self):
        self.assertEqual(self.phase("self").status_code, 303)
        student = self.db.roster(self.session_id)[0]
        self.db.save_rating(
            self.session_id,
            student["student_id"],
            student["student_id"],
            "self",
            {"beschriftung": 3},
        )
        response = self.client.post(
            f"/admin/session/{self.session_id}/self/{student['student_id']}/reopen",
            auth=self.auth,
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertIsNone(self.db.rating(self.session_id, student["student_id"], "self"))

    def test_final_state_rejects_reopening(self):
        self.db.set_phase(self.session_id, "closed")
        response = self.phase("teacher")
        self.assertEqual(response.status_code, 200)
        self.assertIn("kann nicht", response.text)
        self.assertEqual(self.db.session(self.session_id)["phase"], "closed")

    def test_direct_address_and_password_can_be_changed(self):
        direct = self.client.post(
            "/admin/settings/direct-url",
            data={"direct_base_url": "http://192.168.50.10:8765/"},
            auth=self.auth,
            follow_redirects=False,
        )
        self.assertEqual(direct.status_code, 303)
        stored = json.loads(self.settings_file.read_text(encoding="utf-8"))
        self.assertEqual(stored["direct_base_url"], "http://192.168.50.10:8765")

        changed = self.client.post(
            "/admin/settings/password",
            data={
                "old_password": self.password,
                "new_password": "AnderesPasswort-456",
                "repeat_password": "AnderesPasswort-456",
            },
            auth=self.auth,
        )
        self.assertEqual(changed.status_code, 200)
        self.assertIn("Lehrerpasswort geändert", changed.text)
        self.assertNotIn("AnderesPasswort-456", self.settings_file.read_text(encoding="utf-8"))
        self.assertEqual(
            self.client.get("/admin", auth=("lehrkraft", "AnderesPasswort-456")).status_code,
            200,
        )

    def test_universal_personal_path_redirects_to_hb_student_path(self):
        student = self.db.students("8a")[0]
        response = self.client.get(
            f"/p/{student['token']}",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers["location"], f"/s/{student['token']}")

    def test_repeat_archive_restore_and_confirmed_delete_routes(self):
        self.db.set_phase(self.session_id, "closed")

        repeated = self.client.post(
            f"/admin/session/{self.session_id}/repeat",
            auth=self.auth,
            follow_redirects=False,
        )
        self.assertEqual(repeated.status_code, 303)
        repeated_id = int(repeated.headers["location"].rsplit("/", 1)[1])
        self.assertEqual(self.db.session(repeated_id)["phase"], "setup")

        archived = self.client.post(
            f"/admin/session/{self.session_id}/archive",
            auth=self.auth,
            follow_redirects=False,
        )
        self.assertEqual(archived.status_code, 303)
        self.assertEqual(self.db.session(self.session_id)["archived"], 1)

        restored = self.client.post(
            f"/admin/session/{self.session_id}/restore",
            auth=self.auth,
            follow_redirects=False,
        )
        self.assertEqual(restored.status_code, 303)
        self.assertEqual(self.db.session(self.session_id)["archived"], 0)

        self.db.archive_session(self.session_id)
        refused = self.client.post(
            f"/admin/session/{self.session_id}/delete",
            data={"confirmation": "999"},
            auth=self.auth,
        )
        self.assertEqual(refused.status_code, 200)
        self.assertIsNotNone(self.db.session(self.session_id))

        deleted = self.client.post(
            f"/admin/session/{self.session_id}/delete",
            data={"confirmation": str(self.session_id)},
            auth=self.auth,
            follow_redirects=False,
        )
        self.assertEqual(deleted.status_code, 303)
        self.assertIsNone(self.db.session(self.session_id))
        self.assertTrue(
            list(
                (Path(self.temporary.name) / "HB-Collector-Sicherungen").glob(
                    "HB-Datenbank_vor_Loeschen_*.sqlite3"
                )
            )
        )
