from __future__ import annotations

import json
import re
import tempfile
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader, PdfWriter

from .core import format_percent, grade_for_percent
from .odt_helpers import convert_to_pdf

TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"


def _replace_text(root: ET.Element, old: str, new: str) -> None:
    found = False
    for item in root.iter():
        if old in (item.text or ""):
            item.text = item.text.replace(old, new)
            found = True
        if old in (item.tail or ""):
            item.tail = item.tail.replace(old, new)
            found = True
    if not found:
        raise ValueError(f"Rückmeldevorlage: Platzhalter {old!r} fehlt.")


def _values(raw: str | None) -> dict[str, int]:
    return {} if not raw else {str(key): int(value) for key, value in json.loads(raw).items()}


def fill_feedback_template(
    template_path: Path,
    output_path: Path,
    row: dict,
    criteria: list[dict],
    session: dict,
) -> None:
    if not row.get("teacher_values"):
        raise ValueError(f"Für {row['name']} fehlt die verbindliche Lehrerbewertung.")
    if not 1 <= len(criteria) <= 9:
        raise ValueError("Die Rückmeldevorlage unterstützt ein bis neun Kriterien.")

    with zipfile.ZipFile(template_path) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    content = next((data for info, data in entries if info.filename == "content.xml"), None)
    if content is None:
        raise ValueError("Rückmeldevorlage: content.xml fehlt.")
    root = ET.fromstring(content)
    styles = next((data for info, data in entries if info.filename == "styles.xml"), None)
    styles_root = ET.fromstring(styles) if styles is not None else None
    if styles_root is not None:
        _replace_text(styles_root, "[Kürzel]", str(session.get("teacher_abbreviation") or "KÜR"))
        _replace_text(styles_root, "[Schulname]", str(session.get("school_name") or "Beispielschule"))

    feedback_table = next(
        item for item in root.iter(TABLE + "table")
        if item.get(TABLE + "name") == "HBFeedback"
    )
    feedback_rows = feedback_table.findall(TABLE + "table-row")
    for unused_row in feedback_rows[len(criteria) + 1:]:
        feedback_table.remove(unused_row)

    self_values = _values(row.get("self_values"))
    peer_values = _values(row.get("peer_values"))
    teacher_values = _values(row.get("teacher_values"))
    total = sum(teacher_values[str(item["id"])] for item in criteria)
    maximum = len(criteria) * 4
    percent = total / maximum * 100
    created = date.fromisoformat(str(session["created_at"])[:10]).strftime("%d.%m.%Y")

    replacements = {
        "FACH": str(session.get("subject") or "Fach").upper(),
        "Anna Beispiel": str(row["name"]),
        "8a": str(session["class_id"]),
        "ZEITRAUM": str(session["period"]),
        "23.07.2026": created,
        "GESAMT_PUNKTE": str(total),
        "MAX_PUNKTE": str(maximum),
        "PROZENT": format_percent(percent),
        "NOTE": str(grade_for_percent(percent)),
    }
    for index, criterion in enumerate(criteria, start=1):
        criterion_id = str(criterion["id"])
        replacements.update(
            {
                f"KRITERIUM_{index}": f"{index}. {criterion['label']}",
                f"SELBST_{index}": str(self_values.get(criterion_id, "–")),
                f"PEER_{index}": str(peer_values.get(criterion_id, "–")),
                f"LEHRKRAFT_{index}": str(teacher_values[criterion_id]),
            }
        )
    for old, new in replacements.items():
        _replace_text(root, old, new)

    content_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as target:
        for info, data in entries:
            payload = content_xml if info.filename == "content.xml" else (
                ET.tostring(styles_root, encoding="utf-8", xml_declaration=True)
                if info.filename == "styles.xml" and styles_root is not None else data
            )
            compression = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
            target.writestr(info, payload, compress_type=compression)


def safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß_-]+", "_", value.strip())
    return cleaned.strip("_") or "Klasse"


def generate_feedback_pdf(
    rows: list[dict],
    criteria: list[dict],
    session: dict,
    template_path: Path,
    output_path: Path,
) -> int:
    if not rows:
        raise ValueError("Die Bewertung enthält keine Personen.")
    missing = [str(row["name"]) for row in rows if not row.get("teacher_values")]
    if missing:
        raise ValueError(
            "Es fehlen verbindliche Lehrerbewertungen für: " + ", ".join(missing)
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hb-rueckmeldungen-") as temporary:
        temp = Path(temporary)
        pdfs: list[Path] = []
        for index, row in enumerate(rows, start=1):
            odt_path = temp / f"{index:03d}_{safe_filename(str(row['name']))}.odt"
            fill_feedback_template(template_path, odt_path, row, criteria, session)
            pdfs.append(convert_to_pdf(odt_path, temp, temp / f"profile-{index}"))

        writer = PdfWriter()
        for pdf_path in pdfs:
            reader = PdfReader(pdf_path)
            if len(reader.pages) != 1:
                raise RuntimeError(
                    f"Rückmeldebogen {pdf_path.stem} umfasst nicht genau eine Seite."
                )
            page = reader.pages[0]
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            if abs(width - 595.3) > 2 or abs(height - 841.9) > 2:
                raise RuntimeError(
                    f"Rückmeldebogen {pdf_path.stem} ist nicht A4 im Hochformat."
                )
            writer.append(reader)
        with output_path.open("wb") as stream:
            writer.write(stream)
    return len(rows)
