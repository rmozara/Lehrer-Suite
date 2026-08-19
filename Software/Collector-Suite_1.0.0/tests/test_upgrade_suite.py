import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from upgrade_suite import apply, plan


def database(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sample(value TEXT)")
        connection.execute("INSERT INTO sample VALUES (?)", (value,))


def suite(root: Path, version: str, hb: str, se: str) -> Path:
    result = root / f"Collector-Suite_{version}"
    (result / "Collector-Daten").mkdir(parents=True)
    (result / f"HB-Collector_{hb}" / "data").mkdir(parents=True)
    (result / f"SE-Collector_{se}" / "data").mkdir(parents=True)
    (result / "QR-Generator_1.0.0").mkdir()
    return result


class UpgradeSuiteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.old = suite(root, "1.6.0", "1.6.0", "1.5.0")
        self.new = suite(root, "1.7.0", "1.7.0", "1.6.0")

    def tearDown(self):
        self.temp.cleanup()

    def populate_old(self):
        database(self.old / "Collector-Daten/identities.sqlite3", "identity")
        database(self.old / "HB-Collector_1.6.0/data/hefter_collector.sqlite3", "hb")
        database(self.old / "SE-Collector_1.5.0/data/se_collector.sqlite3", "se")
        (self.old / "Collector-Daten/generator_settings.json").write_text('{"ip":"old"}')
        (self.old / "Collector-Daten/teacher_settings.json").write_text('{"admin_password_hash":"abc"}')
        (self.old / "HB-Collector_1.6.0/data/settings.json").write_text('{"hb":1}')
        (self.old / "SE-Collector_1.5.0/data/settings.json").write_text('{"se":1}')
        (self.old / "QR-Ausgaben").mkdir()
        (self.old / "QR-Ausgaben/8a.pdf").write_bytes(b"pdf")

    def test_plan_is_read_only(self):
        self.populate_old()
        labels = [item.label for item in plan(self.old, self.new)]
        self.assertIn("gemeinsames QR-Register", labels)
        self.assertFalse((self.new / "Collector-Daten/identities.sqlite3").exists())

    def test_apply_transfers_all_allowed_data(self):
        self.populate_old()
        labels, backup = apply(self.old, self.new)
        self.assertEqual(len(labels), 8)
        self.assertIsNone(backup)
        for relative, value in (
            ("Collector-Daten/identities.sqlite3", "identity"),
            ("HB-Collector_1.7.0/data/hefter_collector.sqlite3", "hb"),
            ("SE-Collector_1.6.0/data/se_collector.sqlite3", "se"),
        ):
            with sqlite3.connect(self.new / relative) as connection:
                self.assertEqual(connection.execute("SELECT value FROM sample").fetchone()[0], value)
        self.assertEqual((self.new / "QR-Ausgaben/8a.pdf").read_bytes(), b"pdf")
        self.assertEqual(
            (self.new / "Collector-Daten/teacher_settings.json").read_text(),
            '{"admin_password_hash":"abc"}',
        )

    def test_existing_target_is_backed_up(self):
        self.populate_old()
        target = self.new / "Collector-Daten/generator_settings.json"
        target.write_text('{"ip":"new"}')
        _, backup = apply(self.old, self.new)
        self.assertIsNotNone(backup)
        self.assertEqual((backup / "Collector-Daten/generator_settings.json").read_text(), '{"ip":"new"}')
        self.assertEqual(json.loads(target.read_text())["ip"], "old")

    def test_corrupt_database_stops_before_any_change(self):
        self.populate_old()
        (self.old / "HB-Collector_1.6.0/data/hefter_collector.sqlite3").write_bytes(b"broken")
        with self.assertRaises(ValueError):
            apply(self.old, self.new)
        self.assertFalse((self.new / "Collector-Daten/identities.sqlite3").exists())

    def test_program_files_and_virtual_environment_are_ignored(self):
        self.populate_old()
        (self.old / ".venv").mkdir()
        (self.old / ".venv/secret").write_text("no")
        (self.old / "HB-Collector_1.6.0/app.py").write_text("old code")
        apply(self.old, self.new)
        self.assertFalse((self.new / ".venv").exists())
        self.assertFalse((self.new / "HB-Collector_1.7.0/app.py").exists())

    def test_rejects_same_or_newer_source(self):
        with self.assertRaises(ValueError):
            plan(self.new, self.new)
        newer = suite(Path(self.temp.name), "1.8.0", "1.8.0", "1.7.0")
        with self.assertRaises(ValueError):
            plan(newer, self.new)


if __name__ == "__main__":
    unittest.main()
