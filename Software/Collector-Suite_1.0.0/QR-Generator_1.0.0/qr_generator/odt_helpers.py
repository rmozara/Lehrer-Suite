from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET


TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"


def named_table(root: ET.Element, name: str) -> ET.Element:
    for table in root.iter(TABLE + "table"):
        if table.get(TABLE + "name") == name:
            return table
    raise ValueError(f"Vorlage: Tabelle {name!r} fehlt.")


def replace_text(element: ET.Element, old: str, new: str) -> None:
    for item in element.iter():
        if old in (item.text or ""):
            item.text = item.text.replace(old, new)
            return
    raise ValueError(f"Vorlage: Text {old!r} fehlt.")


def soffice() -> str:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    for path in (
        Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
        Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"),
    ):
        if path.exists():
            return str(path)
    raise RuntimeError("LibreOffice wurde nicht gefunden.")


def convert_to_pdf(odt_path: Path, output_dir: Path, profile_dir: Path) -> Path:
    command = [
        soffice(),
        f"-env:UserInstallation={profile_dir.resolve().as_uri()}",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(odt_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=90)
    pdf_path = output_dir / f"{odt_path.stem}.pdf"
    if completed.returncode or not pdf_path.exists():
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"LibreOffice konnte die QR-Karte nicht als PDF exportieren. {detail}")
    return pdf_path

