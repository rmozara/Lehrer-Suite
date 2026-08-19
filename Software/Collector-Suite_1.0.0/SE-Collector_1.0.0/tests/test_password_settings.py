from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from se_collector.config import ensure_settings, hash_password, save_admin_password


class PasswordSettingsTests(unittest.TestCase):
    def test_custom_password_is_hashed_and_other_settings_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            settings_file = data_dir / "settings.json"
            original = {
                "admin_user": "lehrkraft",
                "admin_password_hash": hash_password("AltesPasswort"),
                "base_url": "auto",
                "direct_base_url": "http://192.168.50.2:8765",
                "wifi_ssid": "SE-Lokal",
                "wifi_password": "WLAN-Passwort",
                "host": "0.0.0.0",
                "port": 8765,
            }
            settings_file.write_text(json.dumps(original), encoding="utf-8")
            with (
                patch("se_collector.config.DATA_DIR", data_dir),
                patch("se_collector.config.SETTINGS_FILE", settings_file),
                patch("se_collector.config.SHARED_TEACHER_SETTINGS_FILE", data_dir / "teacher_settings.json"),
                patch("se_collector.config.detect_lan_ip", return_value="127.0.0.1"),
            ):
                updated = save_admin_password("MeinNeuesPasswort")
            stored = json.loads(settings_file.read_text(encoding="utf-8"))
            self.assertEqual(stored["admin_password_hash"], hash_password("MeinNeuesPasswort"))
            self.assertNotIn("MeinNeuesPasswort", settings_file.read_text(encoding="utf-8"))
            self.assertEqual(updated.direct_base_url, original["direct_base_url"])
            self.assertEqual(stored["wifi_ssid"], original["wifi_ssid"])

    def test_custom_password_requires_ten_characters(self):
        with self.assertRaisesRegex(ValueError, "mindestens 10"):
            save_admin_password("zu-kurz")

    def test_fresh_se_installation_creates_no_random_password(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            shared_file = data_dir / "teacher_settings.json"
            settings_file = data_dir / "settings.json"
            with (
                patch("se_collector.config.DATA_DIR", data_dir),
                patch("se_collector.config.SETTINGS_FILE", settings_file),
                patch("se_collector.config.SHARED_TEACHER_SETTINGS_FILE", shared_file),
                patch("se_collector.config.detect_lan_ip", return_value="127.0.0.1"),
            ):
                settings, first_password = ensure_settings()
                shared_created = shared_file.exists()
        self.assertEqual(settings.admin_user, "lehrkraft")
        self.assertEqual(settings.admin_password_hash, "")
        self.assertIsNone(first_password)
        self.assertFalse(shared_created)

    def test_se_adopts_password_created_by_qr(self):
        with tempfile.TemporaryDirectory() as temporary:
            data_dir = Path(temporary)
            shared_file = data_dir / "teacher_settings.json"
            shared_hash = hash_password("GemeinsamesPasswort")
            shared_file.write_text(json.dumps({"admin_user": "lehrkraft", "admin_password_hash": shared_hash}))
            with (
                patch("se_collector.config.DATA_DIR", data_dir),
                patch("se_collector.config.SETTINGS_FILE", data_dir / "settings.json"),
                patch("se_collector.config.SHARED_TEACHER_SETTINGS_FILE", shared_file),
                patch("se_collector.config.detect_lan_ip", return_value="127.0.0.1"),
            ):
                settings, _ = ensure_settings()
        self.assertEqual(settings.admin_user, "lehrkraft")
        self.assertEqual(settings.admin_password_hash, shared_hash)


if __name__ == "__main__":
    unittest.main()
