import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SharedIdentityTests(unittest.TestCase):
    def run_code(self, project: Path, code: str, registry: Path) -> str:
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=project,
            env={**os.environ, "COLLECTOR_IDENTITY_FILE": str(registry)},
            capture_output=True,
            text=True,
            check=True,
        )
        return completed.stdout.strip()

    def test_generator_token_is_used_by_both_collectors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = root / "identities.sqlite3"
            generator_token = self.run_code(
                ROOT / "QR-Generator_1.0.0",
                f"""
from pathlib import Path
from qr_generator.registry import Registry
r=Registry(Path({str(registry)!r}))
r.import_students('2026/27',[{{'class_id':'8a','student_id':'8a-01','name':'Anna','list_position':1}}])
print(r.students('8a')[0]['public_token'])
""",
                registry,
            )
            se_token = self.run_code(
                ROOT / "SE-Collector_1.0.0",
                f"""
from pathlib import Path
from se_collector.db import Database
db=Database(Path({str(root / 'se.sqlite3')!r}),identity_file=Path({str(registry)!r}))
db.import_students([{{'class_id':'8a','student_id':'8a-01','name':'Anna','list_position':1}}])
print(db.students_for_class('8a')[0]['public_token'])
""",
                registry,
            )
            hb_token = self.run_code(
                ROOT / "HB-Collector_1.0.0",
                f"""
from pathlib import Path
from hefter_collector.db import Database
db=Database(Path({str(root / 'hb.sqlite3')!r}),identity_file=Path({str(registry)!r}))
db.import_students([{{'class_id':'8a','student_code':'8a-01','name':'Anna','list_position':1}}])
print(db.students('8a')[0]['token'])
""",
                registry,
            )
            self.assertEqual(generator_token, se_token)
            self.assertEqual(generator_token, hb_token)

    def test_collectors_cannot_create_missing_shared_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = root / "identities.sqlite3"
            self.run_code(
                ROOT / "QR-Generator_1.0.0",
                f"""
from pathlib import Path
from qr_generator.registry import Registry
Registry(Path({str(registry)!r})).set_active_school_year('2026/27')
""",
                registry,
            )
            completed = subprocess.run(
                [sys.executable, "-c", f"""
from pathlib import Path
from hefter_collector.db import Database
db=Database(Path({str(root / 'hb.sqlite3')!r}),identity_file=Path({str(registry)!r}))
db.import_students([{{'class_id':'8a','student_code':'8a-99','name':'Fehlt','list_position':1}}])
"""],
                cwd=ROOT / "HB-Collector_1.0.0",
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("fehlt im gemeinsamen QR-Register", completed.stderr)

    def test_new_school_year_gets_new_token(self):
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / "identities.sqlite3"
            output = self.run_code(
                ROOT / "QR-Generator_1.0.0",
                f"""
from pathlib import Path
from qr_generator.registry import Registry
r=Registry(Path({str(registry)!r}))
row={{'class_id':'8a','student_id':'8a-01','name':'Anna','list_position':1}}
r.import_students('2026/27',[row]); first=r.students('8a')[0]['public_token']
r.import_students('2027/28',[row]); second=r.students('8a')[0]['public_token']
print(first == second)
""",
                registry,
            )
            self.assertEqual(output, "False")

    def test_generator_code_resolves_in_both_collectors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            registry = root / "identities.sqlite3"
            code = self.run_code(
                ROOT / "QR-Generator_1.0.0",
                f"""
from pathlib import Path
from qr_generator.registry import Registry
r=Registry(Path({str(registry)!r}))
r.import_students('2026/27',[{{'class_id':'8a','student_id':'8a-01','name':'Anna','list_position':1}}])
print(r.students('8a')[0]['short_code'])
""",
                registry,
            )
            for project, module in (
                (ROOT / "HB-Collector_1.0.0", "hefter_collector"),
                (ROOT / "SE-Collector_1.0.0", "se_collector"),
            ):
                resolved = self.run_code(
                    project,
                    f"""
from pathlib import Path
from {module}.identity_registry import IdentityRegistry
print(bool(IdentityRegistry(Path({str(registry)!r})).token_by_short_code({code.lower()!r})))
""",
                    registry,
                )
                self.assertEqual(resolved, "True")


if __name__ == "__main__":
    unittest.main()
