from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from suite_check import ROOT, check_database, run_checks


class SuiteCheckTests(unittest.TestCase):
    def test_packaged_suite_passes_structure_check(self):
        ok, notes, errors = run_checks(ROOT)
        self.assertFalse(errors)
        self.assertTrue(any("Programmdateien" in item for item in ok))

    def test_valid_database_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "valid.sqlite3"
            with sqlite3.connect(path) as conn:
                conn.execute("CREATE TABLE example(id INTEGER PRIMARY KEY)")
            self.assertEqual(check_database(path), [])

    def test_corrupt_database_is_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broken.sqlite3"
            path.write_bytes(b"keine sqlite-datenbank")
            self.assertTrue(check_database(path))


if __name__ == "__main__":
    unittest.main()
