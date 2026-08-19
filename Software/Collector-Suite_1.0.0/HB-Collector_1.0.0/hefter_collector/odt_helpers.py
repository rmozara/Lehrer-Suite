from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


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
    raise RuntimeError(
        "LibreOffice wurde nicht gefunden. Bitte LibreOffice installieren, "
        "um die Rückmeldebögen als PDF zu erzeugen."
    )


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
        raise RuntimeError(
            "LibreOffice konnte den Rückmeldebogen nicht als PDF exportieren. "
            + detail
        )
    return pdf_path
