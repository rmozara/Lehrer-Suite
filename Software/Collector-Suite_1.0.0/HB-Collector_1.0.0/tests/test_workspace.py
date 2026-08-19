import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceTests(unittest.TestCase):
    def inspect(self, work_dir: Path) -> dict:
        env = dict(os.environ)
        env["HB_COLLECTOR_WORKDIR"] = str(work_dir)
        code = """
import json
from hefter_collector.config import (
    DATA_DIR, DB_FILE, WORKSPACE_ID, WORKSPACE_MARKER, WORK_DIR, ensure_workspace,
)
created = ensure_workspace()
print(json.dumps({
    "created": created,
    "work_dir": str(WORK_DIR),
    "marker": str(WORKSPACE_MARKER),
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

    def test_one_installation_serves_separate_working_folders(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = self.inspect(root / "8a" / "Hefter H1")
            second = self.inspect(root / "8a" / "Hefter H2")
            self.assertNotEqual(first["workspace_id"], second["workspace_id"])
            self.assertEqual(first["data"], second["data"])
            self.assertEqual(first["db"], second["db"])
            self.assertTrue(Path(first["marker"]).exists())
            self.assertTrue(Path(second["marker"]).exists())

    def test_existing_workspace_marker_is_not_recreated(self):
        with tempfile.TemporaryDirectory() as temporary:
            work_dir = Path(temporary)
            first = self.inspect(work_dir)
            marker = Path(first["marker"])
            original = marker.read_bytes()
            second = self.inspect(work_dir)
            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(marker.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
