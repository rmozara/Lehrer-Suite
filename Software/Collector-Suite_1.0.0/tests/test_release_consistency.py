from __future__ import annotations

import ast
import os
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseConsistencyTests(unittest.TestCase):
    def test_qr_page_calls_match_helper_signature(self):
        source = (ROOT / "QR-Generator_1.0.0" / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        page_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "page"
        ]
        self.assertTrue(page_calls)
        self.assertTrue(all(len(call.args) == 2 for call in page_calls))

    def text_sources(self) -> str:
        suffixes = {".py", ".md", ".txt", ".sh", ".bat", ".html", ".css", ".js"}
        return "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in ROOT.rglob("*")
            if path.is_file() and path.suffix.lower() in suffixes and path.resolve() != Path(__file__).resolve()
        )

    def test_public_names_and_launchers_are_consistent(self):
        expected = (
            ROOT / "QR-Generator_1.0.0/run_on_linux.sh",
            ROOT / "QR-Generator_1.0.0/run_on_windows.bat",
            ROOT / "SE-Collector_1.0.0/run_on_linux.sh",
            ROOT / "SE-Collector_1.0.0/run_on_windows.bat",
            ROOT / "HB-Collector_1.0.0/run_on_linux.sh",
            ROOT / "HB-Collector_1.0.0/run_on_windows.bat",
            ROOT / "check_on_linux.sh",
            ROOT / "check_on_windows.bat",
            ROOT / "upgrade_on_linux.sh",
            ROOT / "upgrade_on_windows.bat",
        )
        self.assertTrue(all(path.is_file() for path in expected))
        self.assertTrue(all(os.access(path, os.X_OK) for path in expected if path.suffix == ".sh"))
        source = self.text_sources()
        for obsolete in (
            "run_linux.sh", "run_windows.bat", "check_linux.sh", "check_windows.bat",
            "upgrade_linux.sh", "upgrade_windows.bat", "Vorlage_Namensliste.ods",
        ):
            self.assertNotIn(obsolete, source)
        self.assertTrue((ROOT / "QR-Generator_1.0.0/templates/Namensliste.ods").is_file())

    def test_gitignore_protects_runtime_data_without_hiding_templates(self):
        rules = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        required = {
            ".venv/", "__pycache__/", "*.py[cod]", ".pytest_cache/", ".~lock.*#",
            "/Collector-Daten/identities.sqlite3", "/Collector-Daten/teacher_settings.json",
            "/Collector-Daten/generator_settings.json", "/HB-Collector_1.0.0/data/",
            "/SE-Collector_1.0.0/data/*", "*.pdf", "*.sqlite3", "*.log",
        }
        self.assertTrue(required.issubset(set(rules)))
        self.assertIn("!/SE-Collector_1.0.0/data/.gitkeep", rules)
        self.assertIn("!/Beispiel-Durchlauf/**/*.pdf", rules)
        self.assertNotIn("*.ods", rules)
        self.assertNotIn("*.odt", rules)
        self.assertNotIn("*.ott", rules)

    def test_first_run_password_policy_is_shared_and_non_random(self):
        qr = (ROOT / "QR-Generator_1.0.0" / "app.py").read_text(encoding="utf-8")
        se = (ROOT / "SE-Collector_1.0.0" / "se_collector/config.py").read_text(encoding="utf-8")
        hb = (ROOT / "HB-Collector_1.0.0" / "hefter_collector/config.py").read_text(encoding="utf-8")
        self.assertIn('"admin_user": "lehrkraft"', qr)
        self.assertIn("hashlib.sha256(password.encode", qr)
        self.assertIn("Noch kein gemeinsames Lehrerpasswort eingerichtet", qr)
        for collector in (se, hb):
            self.assertIn('"admin_user": "lehrkraft"', collector)
            self.assertIn('"admin_password_hash": ""', collector)
            self.assertNotIn("token_urlsafe", collector)

    def test_example_student_ids_are_consistent(self):
        self.assertNotIn("Kl-01", self.text_sources())
        for path in (
            ROOT / "QR-Generator_1.0.0/templates/Namensliste.ods",
            ROOT / "SE-Collector_1.0.0/templates/Selbstevaluation.ods",
            ROOT / "HB-Collector_1.0.0/templates/Hefterbewertung.ods",
        ):
            with zipfile.ZipFile(path) as package:
                content = package.read("content.xml").decode("utf-8")
            for student_id in ("8a-01", "8a-02", "8a-03"):
                self.assertIn(student_id, content, path.name)
            self.assertNotIn("Kl-0", content)

    def test_qr_se_hb_wording_and_version_are_visible(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("QR → SE → HB", readme)
        self.assertIn("QR · QR-Karten 1.0.0", readme)
        self.assertIn("SE · Selbstevaluation 1.0.0", readme)
        self.assertIn("HB · Hefterbewertung 1.0.0", readme)
        self.assertNotIn("QR-Generator →", self.text_sources())

    def test_replacement_card_views_share_core_structure(self):
        se = (ROOT / "SE-Collector_1.0.0/se_collector/templates/cards.html").read_text(encoding="utf-8")
        hb = (ROOT / "HB-Collector_1.0.0/hefter_collector/web.py").read_text(encoding="utf-8")
        common = (
            "Ausweichhilfe", "QR-Karte anzeigen", "Nur für SuS, die ihre persönliche QR-Karte vergessen haben.",
            "Schülerin oder Schüler", "Bitte auswählen", "replacement-card", "Schüler-ID",
            "Am Schülergerät scannen.", "Mit dem Klassen-WLAN verbinden und VPN ausschalten.",
            "<noscript>", "Anzeigen", "Zur Lehrerübersicht",
        )
        for text in common:
            self.assertIn(text, se)
            self.assertIn(text, hb)

    def test_se_and_hb_use_parallel_header_and_archive_terms(self):
        se_css = (ROOT / "SE-Collector_1.0.0/se_collector/static/app.css").read_text(encoding="utf-8")
        hb = (ROOT / "HB-Collector_1.0.0/hefter_collector/web.py").read_text(encoding="utf-8")
        self.assertIn("--blue:#c6d9f1", se_css)
        self.assertIn("--grid:#9da7ad", se_css)
        self.assertIn("background:#c6d9f1", hb)
        self.assertIn("border:1px solid #9da7ad", hb)
        for declaration in ("border-radius:5px", "padding:16px 18px"):
            self.assertIn(declaration, se_css)
            self.assertIn(declaration, hb)
        self.assertIn("Wiederherstellen", hb)
        self.assertNotIn("Wieder einblenden", hb)

    def test_example_run_contains_no_live_state(self):
        example = ROOT / "Beispiel-Durchlauf"
        self.assertTrue((example / "README.md").is_file())
        files = [path for path in example.rglob("*") if path.is_file()]
        self.assertEqual(sum(path.name == "Namensliste.ods" for path in files), 1)
        self.assertEqual(sum(path.name == "Selbstevaluation.ods" for path in files), 1)
        self.assertEqual(sum(path.name == "Hefterbewertung.ods" for path in files), 1)
        forbidden_names = {"teacher_settings.json", "generator_settings.json"}
        self.assertFalse(any(path.name in forbidden_names for path in files))
        self.assertFalse(any(path.suffix in {".sqlite", ".sqlite3", ".log", ".pyc"} for path in files))
        self.assertFalse(any("Sicherungen" in path.parts or path.name.startswith(".~lock.") for path in files))


if __name__ == "__main__":
    unittest.main()
