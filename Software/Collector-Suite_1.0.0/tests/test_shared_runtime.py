from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = (
    ROOT / "QR-Generator_1.0.0",
    ROOT / "HB-Collector_1.0.0",
    ROOT / "SE-Collector_1.0.0",
)
REQUIRED = {
    "fastapi", "uvicorn", "jinja2", "python-multipart", "psutil", "pypdf",
    "qrcode[pil]", "opencv-python-headless",
}


class SharedRuntimeTests(unittest.TestCase):
    def test_central_requirements_cover_all_components(self):
        central = {
            line.split(">", 1)[0].strip()
            for line in (ROOT / "requirements.txt").read_text().splitlines()
            if line.strip()
        }
        self.assertEqual(central, REQUIRED)
        for component in COMPONENTS:
            local = {
                line.split(">", 1)[0].strip()
                for line in (component / "requirements.txt").read_text().splitlines()
                if line.strip()
            }
            self.assertTrue(local <= central)

    def test_linux_launchers_use_only_suite_environment(self):
        for component in COMPONENTS:
            launcher = component / "run_on_linux.sh"
            text = launcher.read_text()
            self.assertIn('suite_dir="$(cd "$software_dir/.." && pwd)"', text)
            self.assertIn('$suite_dir/.venv/bin/python', text)
            self.assertIn('$suite_dir/requirements.txt', text)
            self.assertNotIn("python3 -m venv .venv", text)
            subprocess.run(["bash", "-n", launcher], check=True)

    def test_windows_launchers_use_only_suite_environment(self):
        for component in COMPONENTS:
            text = (component / "run_on_windows.bat").read_text()
            self.assertIn('set "SUITE_DIR=%~dp0.."', text)
            self.assertIn(r"%SUITE_DIR%\.venv\Scripts\python.exe", text)
            self.assertIn(r"%SUITE_DIR%\requirements.txt", text)
            self.assertNotIn(r"venv .venv", text)

    def test_se_output_checks_use_the_shared_environment_and_quote_paths(self):
        se = ROOT / "SE-Collector_1.0.0"
        linux = (se / "TEST_AUSGABE_LINUX.sh").read_text(encoding="utf-8")
        windows = (se / "TEST_AUSGABE_WINDOWS.bat").read_text(encoding="utf-8")
        self.assertIn('$suite_dir/.venv/bin/python', linux)
        self.assertIn('exec "$python_bin" test_ausgabe.py', linux)
        subprocess.run(["bash", "-n", se / "TEST_AUSGABE_LINUX.sh"], check=True)
        self.assertIn(r"%SOFTWARE_DIR%..\.venv\Scripts\python.exe", windows)
        self.assertIn('cd /d "%SOFTWARE_DIR%"', windows)
        self.assertIn('"%PYTHON_BIN%" test_ausgabe.py', windows)


if __name__ == "__main__":
    unittest.main()
