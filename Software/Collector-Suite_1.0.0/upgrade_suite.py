from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SUITE_RE = re.compile(r"Collector-Suite_(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Transfer:
    source: Path
    target: Path
    label: str


def version_of(path: Path) -> tuple[int, int, int]:
    match = SUITE_RE.fullmatch(path.resolve().name)
    if not match:
        raise ValueError(f"Kein gültiger Suite-Ordner: {path}")
    return tuple(int(part) for part in match.groups())


def component(root: Path, prefix: str) -> Path:
    matches = sorted(path for path in root.glob(f"{prefix}_*") if path.is_dir())
    if len(matches) != 1:
        raise ValueError(f"{root}: genau ein Ordner {prefix}_* erwartet")
    return matches[0]


def plan(source: Path, target: Path = ROOT) -> list[Transfer]:
    source, target = source.resolve(), target.resolve()
    if source == target:
        raise ValueError("Quell- und Zielordner sind identisch.")
    old_version, new_version = version_of(source), version_of(target)
    if old_version >= new_version:
        raise ValueError("Als Quelle wird eine ältere Suite-Version benötigt.")

    old_hb, new_hb = component(source, "HB-Collector"), component(target, "HB-Collector")
    old_se, new_se = component(source, "SE-Collector"), component(target, "SE-Collector")
    candidates = [
        Transfer(source / "Collector-Daten" / "identities.sqlite3",
                 target / "Collector-Daten" / "identities.sqlite3", "gemeinsames QR-Register"),
        Transfer(source / "Collector-Daten" / "generator_settings.json",
                 target / "Collector-Daten" / "generator_settings.json", "QR-Generator-Einstellung"),
        Transfer(source / "Collector-Daten" / "teacher_settings.json",
                 target / "Collector-Daten" / "teacher_settings.json", "gemeinsames Lehrerpasswort"),
        Transfer(old_hb / "data" / "hefter_collector.sqlite3",
                 new_hb / "data" / "hefter_collector.sqlite3", "HB-Datenbank"),
        Transfer(old_hb / "data" / "settings.json",
                 new_hb / "data" / "settings.json", "HB-Einstellungen"),
        Transfer(old_se / "data" / "se_collector.sqlite3",
                 new_se / "data" / "se_collector.sqlite3", "SE-Datenbank"),
        Transfer(old_se / "data" / "settings.json",
                 new_se / "data" / "settings.json", "SE-Einstellungen"),
        Transfer(source / "QR-Ausgaben", target / "QR-Ausgaben", "erzeugte QR-Karten"),
    ]
    return [item for item in candidates if item.source.exists()]


def check_sqlite(path: Path) -> None:
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            result = connection.execute("PRAGMA quick_check").fetchone()
    except sqlite3.Error as exc:
        raise ValueError(f"{path.name} ist keine intakte SQLite-Datenbank: {exc}") from exc
    if not result or result[0] != "ok":
        raise ValueError(f"{path.name} ist beschädigt ({result[0] if result else 'keine Antwort'}).")


def backup_existing(path: Path, backup_root: Path, target_root: Path) -> None:
    if not path.exists():
        return
    destination = backup_root / path.relative_to(target_root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir():
        shutil.copytree(path, destination)
    else:
        shutil.copy2(path, destination)


def atomic_file_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(descriptor)
    temporary = Path(temp_name)
    try:
        if source.suffix == ".sqlite3":
            check_sqlite(source)
            temporary.unlink()
            with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as src:
                with sqlite3.connect(temporary) as dst:
                    src.backup(dst)
            check_sqlite(temporary)
        else:
            shutil.copy2(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def apply(source: Path, target: Path = ROOT) -> tuple[list[str], Path | None]:
    transfers = plan(source, target)
    for item in transfers:
        if item.source.is_file() and item.source.suffix == ".sqlite3":
            check_sqlite(item.source)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = target.resolve() / "Upgrade-Sicherungen" / stamp
    backed_up = False
    for item in transfers:
        if item.target.exists():
            backup_existing(item.target, backup_root, target.resolve())
            backed_up = True
        if item.source.is_dir():
            item.target.mkdir(parents=True, exist_ok=True)
            for source_file in item.source.rglob("*"):
                if source_file.is_file():
                    atomic_file_copy(source_file, item.target / source_file.relative_to(item.source))
        else:
            atomic_file_copy(item.source, item.target)
    return [item.label for item in transfers], backup_root if backed_up else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Nutzdaten aus einer älteren Collector-Suite übernehmen.")
    parser.add_argument("source", type=Path, help="Ordner der bisherigen Collector-Suite")
    parser.add_argument("--apply", action="store_true", help="Übernahme wirklich durchführen")
    args = parser.parse_args()
    try:
        transfers = plan(args.source)
        if not transfers:
            print("Keine vorhandenen Nutzdaten gefunden. Es ist nichts zu übernehmen.")
            return 0
        print("Gefunden:")
        for item in transfers:
            print(f"  - {item.label}")
        if not args.apply:
            print("\nNur geprüft. Zum Übernehmen zusätzlich --apply angeben.")
            return 0
        labels, backup = apply(args.source)
        print(f"\nÜbernahme abgeschlossen: {len(labels)} Datenbereich(e).")
        if backup:
            print(f"Vorherige Zieldaten gesichert in: {backup}")
        print("Programmdateien und virtuelle Umgebungen wurden nicht kopiert.")
        return 0
    except (OSError, ValueError) as exc:
        print(f"FEHLER: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
