import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceTests(unittest.TestCase):
    def _inspect(self, work_dir: Path) -> dict:
        env = dict(os.environ)
        env["SE_COLLECTOR_WORKDIR"] = str(work_dir)
        code = """
import json
from se_collector.config import (
    BACKUP_DIR, DATA_DIR, DB_FILE, ODS_FILE, OUTPUT_DIR,
    WORKSPACE_ID, WORK_DIR, ensure_workspace,
)
created = ensure_workspace()
print(json.dumps({
    "created": created,
    "work_dir": str(WORK_DIR),
    "ods": str(ODS_FILE),
    "backup": str(BACKUP_DIR),
    "output": str(OUTPUT_DIR),
    "data": str(DATA_DIR),
    "db": str(DB_FILE),
    "workspace_id": WORKSPACE_ID,
}))
"""
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_one_central_installation_serves_separate_lesson_folders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self._inspect(root / "8a" / "Stunde 01")
            second = self._inspect(root / "10b" / "Stunde 04")
            self.assertNotEqual(first["workspace_id"], second["workspace_id"])
            self.assertNotEqual(first["ods"], second["ods"])
            self.assertEqual(first["data"], second["data"])
            self.assertEqual(first["db"], second["db"])
            self.assertEqual(Path(first["output"]), root / "8a" / "Stunde 01")
            self.assertEqual(
                Path(first["backup"]),
                root / "8a" / "Stunde 01" / "SE-Collector-Sicherungen",
            )
            self.assertTrue(Path(first["ods"]).exists())
            self.assertTrue(Path(second["ods"]).exists())

    def test_existing_ods_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            work_dir = Path(temporary)
            first = self._inspect(work_dir)
            self.assertTrue(first["created"])
            ods = Path(first["ods"])
            original = ods.read_bytes()
            second = self._inspect(work_dir)
            self.assertFalse(second["created"])
            self.assertEqual(ods.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
