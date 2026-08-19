from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SourcePolicyTests(unittest.TestCase):
    def test_obsolete_table_format_is_absent(self):
        forbidden_suffix = "." + "c" + "s" + "v"
        forbidden_word = forbidden_suffix[1:]
        excluded = {".venv", "__pycache__"}
        offenders = []
        for path in ROOT.rglob("*"):
            if excluded.intersection(path.parts) or not path.is_file():
                continue
            if path.suffix.casefold() == forbidden_suffix:
                offenders.append(str(path.relative_to(ROOT)))
                continue
            if path.suffix.casefold() not in {".py", ".md", ".txt", ".sh", ".bat"}:
                continue
            if forbidden_word in path.read_text(encoding="utf-8", errors="ignore").casefold():
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
