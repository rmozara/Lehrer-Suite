from __future__ import annotations

import tempfile
import unittest
import json
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

if importlib.util.find_spec("fastapi") is None:
    raise unittest.SkipTest("FastAPI-Testabhängigkeit ist nicht installiert.")

from fastapi.testclient import TestClient

import app
from qr_generator.registry import Registry


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "Namensliste.ods"


class UiFlowTests(unittest.TestCase):
    def test_ods_roster_is_loaded_automatically(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = Registry(root / "identities.sqlite3")
            with patch.object(app, "registry", registry), patch.object(
                app, "ROSTER_FILE", TEMPLATE
            ), patch.object(app, "SETTINGS_FILE", root / "settings.json"), patch.object(
                app, "TEACHER_SETTINGS_FILE", root / "teacher_settings.json"
            ), patch.object(
                app, "detect_network_addresses", return_value=[]
            ):
                response = TestClient(app.app).get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Namensliste automatisch geladen", response.text)
        self.assertIn("3 Personen", response.text)
        self.assertIn("Klasse 8a", response.text)
        self.assertIn("2026/27", response.text)
        self.assertIn("Für diese Klasse wurden noch keine Karten erzeugt", response.text)
        self.assertIn("QR beenden", response.text)

    def test_first_run_requires_visible_password_setup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(app, "registry", Registry(root / "identities.sqlite3")), patch.object(
                app, "ROSTER_FILE", TEMPLATE
            ), patch.object(app, "SETTINGS_FILE", root / "settings.json"), patch.object(
                app, "TEACHER_SETTINGS_FILE", root / "teacher_settings.json"
            ), patch.object(
                app, "detect_network_addresses", return_value=[SimpleNamespace(
                    url="http://192.168.50.10:8765",
                    ip="192.168.50.10",
                    interface="wlan0",
                    recommended=True,
                )]
            ):
                response = TestClient(app.app).get("/")
        self.assertNotIn("Namensliste übernehmen", response.text)
        self.assertIn("name='class_id' value='8a'", response.text)
        self.assertNotIn("<select required name='class_id'>", response.text)
        self.assertIn("Benutzername: <code>lehrkraft</code>", response.text)
        self.assertIn("Noch kein gemeinsames Lehrerpasswort eingerichtet", response.text)
        self.assertIn("<button disabled>Karten erzeugen</button>", response.text)

    def test_card_endpoints_are_blocked_before_password_setup(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(app, "TEACHER_SETTINGS_FILE", root / "teacher_settings.json"):
                response = TestClient(app.app).get(
                    "/cards.pdf",
                    params={"class_id": "8a", "direct_base_url": "http://192.168.50.10:8765"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Ohne abgeschlossene Ersteinrichtung", response.text)

    def test_generation_ends_on_clear_completion_page(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            roster_file = root / "Namensliste.ods"
            roster_file.write_bytes(TEMPLATE.read_bytes())
            registry = Registry(root / "identities.sqlite3")
            from qr_generator.roster_ods import read_roster

            roster = read_roster(roster_file)
            registry.import_students(roster.school_year, roster.students)
            with patch.object(app, "registry", registry), patch.object(
                app, "ROSTER_FILE", roster_file
            ), patch.object(app, "SETTINGS_FILE", root / "settings.json"), patch.object(
                app, "OUTPUT_DIR", root
            ), patch.object(app, "teacher_password_configured", return_value=True), patch.object(
                app, "generate_qr_cards_pdf", return_value=3
            ):
                response = TestClient(app.app).get(
                    "/cards.pdf",
                    params={"class_id": "8a", "direct_base_url": "http://192.168.50.10:8765"},
                )
        self.assertEqual(response.status_code, 200)
        self.assertIn("QR-Karten fertig", response.text)
        self.assertIn("QR-Karten_8a_2026-27.pdf", response.text)
        self.assertIn("QR beenden", response.text)
        self.assertIn("Weitere Klasse auswählen", response.text)

    def test_teacher_password_is_saved_for_the_suite(self):
        with tempfile.TemporaryDirectory() as temporary:
            settings_file = Path(temporary) / "teacher_settings.json"
            with patch.object(app, "TEACHER_SETTINGS_FILE", settings_file):
                response = TestClient(app.app).post(
                    "/teacher-password",
                    data={"password": "SicheresPasswort", "repeat": "SicheresPasswort"},
                    follow_redirects=False,
                )
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            settings_text = settings_file.read_text(encoding="utf-8")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(data["admin_user"], "lehrkraft")
        self.assertNotEqual(data["admin_password_hash"], "SicheresPasswort")
        self.assertEqual(len(data["admin_password_hash"]), 64)
        self.assertNotIn("SicheresPasswort", settings_text)

    def test_shutdown_button_stops_server(self):
        server = SimpleNamespace(should_exit=False)
        with patch.object(app.app.state, "server", server, create=True), patch.object(
            app.threading, "Timer"
        ) as timer:
            response = TestClient(app.app).post("/shutdown")
        self.assertEqual(response.status_code, 200)
        self.assertIn("QR beendet", response.text)
        timer.return_value.start.assert_called_once_with()

    def test_switch_class_requests_launcher_restart(self):
        server = SimpleNamespace(should_exit=False)
        app.app.state.switch_class_requested = False
        with patch.object(app.app.state, "server", server, create=True), patch.object(
            app.threading, "Timer"
        ) as timer:
            response = TestClient(app.app).post("/switch-class")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(app.app.state.switch_class_requested)
        self.assertIn("Ordnerdialog wird geöffnet", response.text)
        timer.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
