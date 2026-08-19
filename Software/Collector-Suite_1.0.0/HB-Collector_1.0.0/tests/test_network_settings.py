import json
import socket
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hefter_collector.config import (
    detect_network_addresses,
    ensure_settings,
    hash_password,
    normalize_base_url,
    save_admin_password,
    save_direct_base_url,
)


class NetworkSettingsTests(unittest.TestCase):
    def test_generator_direct_address_is_adopted_when_hb_has_none(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings_file = root / "settings.json"
            teacher_file = root / "teacher_settings.json"
            generator_file = root / "generator_settings.json"
            settings_file.write_text(json.dumps({
                "admin_user": "lehrkraft",
                "admin_password_hash": hash_password("AltesPasswort"),
                "host": "0.0.0.0",
                "port": 8765,
                "direct_base_url": "",
            }), encoding="utf-8")
            teacher_file.write_text(json.dumps({
                "admin_user": "lehrkraft",
                "admin_password_hash": hash_password("AltesPasswort"),
            }), encoding="utf-8")
            generator_file.write_text(json.dumps({
                "direct_base_url": "http://192.168.50.10:8765",
            }), encoding="utf-8")
            with (
                patch("hefter_collector.config.DATA_DIR", root),
                patch("hefter_collector.config.SETTINGS_FILE", settings_file),
                patch("hefter_collector.config.SHARED_TEACHER_SETTINGS_FILE", teacher_file),
                patch("hefter_collector.config.GENERATOR_SETTINGS_FILE", generator_file),
            ):
                settings, _ = ensure_settings()
            self.assertEqual(settings.direct_base_url, "http://192.168.50.10:8765")

    def test_explicit_hb_direct_address_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            settings_file = root / "settings.json"
            teacher_file = root / "teacher_settings.json"
            generator_file = root / "generator_settings.json"
            settings_file.write_text(json.dumps({
                "admin_user": "lehrkraft",
                "admin_password_hash": hash_password("AltesPasswort"),
                "host": "0.0.0.0",
                "port": 8765,
                "direct_base_url": "http://192.168.60.20:8765",
            }), encoding="utf-8")
            teacher_file.write_text(json.dumps({
                "admin_user": "lehrkraft",
                "admin_password_hash": hash_password("AltesPasswort"),
            }), encoding="utf-8")
            generator_file.write_text(json.dumps({
                "direct_base_url": "http://192.168.50.10:8765",
            }), encoding="utf-8")
            with (
                patch("hefter_collector.config.DATA_DIR", root),
                patch("hefter_collector.config.SETTINGS_FILE", settings_file),
                patch("hefter_collector.config.SHARED_TEACHER_SETTINGS_FILE", teacher_file),
                patch("hefter_collector.config.GENERATOR_SETTINGS_FILE", generator_file),
            ):
                settings, _ = ensure_settings()
            self.assertEqual(settings.direct_base_url, "http://192.168.60.20:8765")

    def test_teacher_page_opens_automatically(self):
        source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertIn("webbrowser.open(teacher_url)", source)
        self.assertIn("Die Lehreroberfläche wird jetzt im Browser geöffnet.", source)

    def test_admin_page_has_real_shutdown_control(self):
        root = Path(__file__).resolve().parents[1]
        web = (root / "hefter_collector" / "web.py").read_text(encoding="utf-8")
        launcher = (root / "app.py").read_text(encoding="utf-8")
        self.assertIn("HB beenden", web)
        self.assertIn('@app.post("/admin/shutdown"', web)
        self.assertIn("application.state.server = server", launcher)

    def test_missing_shared_password_is_explained_in_browser(self):
        web = (Path(__file__).resolve().parents[1] / "hefter_collector" / "web.py").read_text(encoding="utf-8")
        self.assertIn("Lehrerpasswort noch nicht eingerichtet", web)
        self.assertIn("Bitte zuerst QR starten", web)
        self.assertIn("lehrkraft", web)

    def test_direct_base_url_validation(self):
        self.assertEqual(
            normalize_base_url("http://192.168.50.10:8765/"),
            "http://192.168.50.10:8765",
        )
        self.assertEqual(normalize_base_url("", allow_blank=True), "")
        with self.assertRaises(ValueError):
            normalize_base_url("192.168.50.10:8765")
        with self.assertRaises(ValueError):
            normalize_base_url("http://192.168.50.10:8765/s/falsch")

    def test_physical_address_is_preferred_and_virtual_hidden(self):
        fake_addrs = {
            "wlp2s0": [SimpleNamespace(family=socket.AF_INET, address="192.168.50.10")],
            "docker0": [SimpleNamespace(family=socket.AF_INET, address="172.17.0.1")],
            "lo": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
        }
        fake_stats = {
            "wlp2s0": SimpleNamespace(isup=True),
            "docker0": SimpleNamespace(isup=True),
            "lo": SimpleNamespace(isup=True),
        }
        fake_psutil = SimpleNamespace(
            net_if_addrs=lambda: fake_addrs,
            net_if_stats=lambda: fake_stats,
        )
        with (
            patch.dict(sys.modules, {"psutil": fake_psutil}),
            patch("hefter_collector.config.detect_lan_ip", return_value="192.168.50.10"),
        ):
            result = detect_network_addresses(8765)
        self.assertEqual([item.url for item in result], ["http://192.168.50.10:8765"])
        self.assertTrue(result[0].recommended)

    def test_settings_are_saved_without_plaintext_password(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            settings_file = data_dir / "settings.json"
            original = {
                "admin_user": "lehrkraft",
                "admin_password_hash": hash_password("AltesPasswort"),
                "host": "0.0.0.0",
                "port": 8765,
                "direct_base_url": "",
            }
            settings_file.write_text(json.dumps(original), encoding="utf-8")
            with (
                patch("hefter_collector.config.DATA_DIR", data_dir),
                patch("hefter_collector.config.SETTINGS_FILE", settings_file),
                patch("hefter_collector.config.SHARED_TEACHER_SETTINGS_FILE", data_dir / "teacher_settings.json"),
            ):
                direct = save_direct_base_url("http://192.168.50.10:8765/")
                changed = save_admin_password("NeuesPasswort-123")
            stored = settings_file.read_text(encoding="utf-8")
            self.assertEqual(direct.direct_base_url, "http://192.168.50.10:8765")
            self.assertNotIn("NeuesPasswort-123", stored)
            self.assertEqual(changed.admin_password_hash, hash_password("NeuesPasswort-123"))

    def test_password_length_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "mindestens 10"):
            save_admin_password("zu-kurz")

    def test_fresh_hb_installation_creates_no_random_password(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared_file = root / "teacher_settings.json"
            with (
                patch("hefter_collector.config.DATA_DIR", root),
                patch("hefter_collector.config.SETTINGS_FILE", root / "settings.json"),
                patch("hefter_collector.config.SHARED_TEACHER_SETTINGS_FILE", shared_file),
                patch("hefter_collector.config.GENERATOR_SETTINGS_FILE", root / "generator_settings.json"),
            ):
                settings, first_password = ensure_settings()
                shared_created = shared_file.exists()
        self.assertEqual(settings.admin_user, "lehrkraft")
        self.assertEqual(settings.admin_password_hash, "")
        self.assertIsNone(first_password)
        self.assertFalse(shared_created)

    def test_hb_adopts_password_created_by_qr(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared_hash = hash_password("GemeinsamesPasswort")
            shared_file = root / "teacher_settings.json"
            shared_file.write_text(json.dumps({"admin_user": "lehrkraft", "admin_password_hash": shared_hash}))
            with (
                patch("hefter_collector.config.DATA_DIR", root),
                patch("hefter_collector.config.SETTINGS_FILE", root / "settings.json"),
                patch("hefter_collector.config.SHARED_TEACHER_SETTINGS_FILE", shared_file),
                patch("hefter_collector.config.GENERATOR_SETTINGS_FILE", root / "generator_settings.json"),
            ):
                settings, _ = ensure_settings()
        self.assertEqual(settings.admin_user, "lehrkraft")
        self.assertEqual(settings.admin_password_hash, shared_hash)


if __name__ == "__main__":
    unittest.main()
