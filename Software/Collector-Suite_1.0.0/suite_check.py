from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def check_database(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as conn:
            quick = str(conn.execute("PRAGMA quick_check").fetchone()[0])
            foreign = conn.execute("PRAGMA foreign_key_check").fetchall()
    except sqlite3.Error as exc:
        return [f"{path.name}: nicht lesbar ({exc})"]
    problems = []
    if quick != "ok":
        problems.append(f"{path.name}: Integritätsprüfung meldet {quick}")
    if foreign:
        problems.append(f"{path.name}: {len(foreign)} ungültige Verweise")
    return problems


def libreoffice_path() -> str | None:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    for candidate in (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def run_checks(root: Path = ROOT) -> tuple[list[str], list[str], list[str]]:
    ok: list[str] = []
    notes: list[str] = []
    errors: list[str] = []
    if sys.version_info >= (3, 10):
        ok.append(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    else:
        errors.append("Python 3.10 oder neuer wird benötigt.")

    required = (
        "requirements.txt",
        "upgrade_suite.py",
        "upgrade_on_linux.sh",
        "upgrade_on_windows.bat",
        "QR-Generator_1.0.0/run_on_linux.sh",
        "QR-Generator_1.0.0/run_on_windows.bat",
        "QR-Generator_1.0.0/templates/IB_QR-Karten.odt",
        "QR-Generator_1.0.0/templates/Namensliste.ods",
        "HB-Collector_1.0.0/run_on_linux.sh",
        "HB-Collector_1.0.0/run_on_windows.bat",
        "HB-Collector_1.0.0/templates/IB_Hefterbewertung.odt",
        "HB-Collector_1.0.0/templates/Hefterbewertung.ods",
        "SE-Collector_1.0.0/run_on_linux.sh",
        "SE-Collector_1.0.0/run_on_windows.bat",
        "SE-Collector_1.0.0/templates/Selbstevaluation.ods",
        "SE-Collector_1.0.0/templates/IB_Selbstbewertung1.odt",
    )
    missing = [relative for relative in required if not (root / relative).exists()]
    if missing:
        errors.extend(f"Datei fehlt: {relative}" for relative in missing)
    else:
        ok.append("Programmdateien und Vorlagen vollständig")

    office = libreoffice_path()
    if office:
        ok.append(f"LibreOffice gefunden: {office}")
    else:
        errors.append("LibreOffice wurde nicht gefunden.")

    databases = [
        root / "Collector-Daten" / "identities.sqlite3",
        root / "HB-Collector_1.0.0" / "data" / "hefter_collector.sqlite3",
        root / "SE-Collector_1.0.0" / "data" / "se_collector.sqlite3",
    ]
    existing = [path for path in databases if path.exists()]
    for path in existing:
        errors.extend(check_database(path))
    if existing and not any(path.name in error for path in existing for error in errors):
        ok.append(f"{len(existing)} vorhandene Datenbank(en) intakt")
    if not existing:
        notes.append("Noch keine Nutzdaten vorhanden – sauberer Ausgangszustand.")
    return ok, notes, errors


def main() -> int:
    ok, notes, errors = run_checks()
    print("Collector-Suite · Systemprüfung\n")
    for message in ok:
        print(f"[OK] {message}")
    for message in notes:
        print(f"[HINWEIS] {message}")
    for message in errors:
        print(f"[FEHLER] {message}")
    print()
    if errors:
        print("Ergebnis: Bitte die genannten Fehler vor dem Einsatz beheben.")
        return 1
    print("Ergebnis: Grundprüfung erfolgreich. Vor dem Einsatz bitte einen manuellen Funktionstest durchführen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
