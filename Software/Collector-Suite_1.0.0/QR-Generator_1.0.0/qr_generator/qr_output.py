from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import qrcode
from pypdf import PdfReader, PdfWriter

from .odt_helpers import convert_to_pdf, named_table, replace_text


QR_IMAGE_PATH = "Pictures/QR_PERSONAL.png"


def _qr_png(payload: str) -> bytes:
    qr = qrcode.QRCode(version=None, box_size=14, border=4)
    qr.add_data(payload)
    qr.make(fit=True)
    output = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(output, format="PNG")
    return output.getvalue()


def fill_qr_template(
    template_path: Path,
    output_path: Path,
    student: dict,
    subject: str,
    direct_base_url: str,
    teacher_abbreviation: str = "KÜR",
    school_name: str = "Beispielschule",
) -> None:
    with zipfile.ZipFile(template_path) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    content = next((data for info, data in entries if info.filename == "content.xml"), None)
    if content is None:
        raise ValueError("QR-Vorlage: content.xml fehlt.")
    root = ET.fromstring(content)
    styles = next((data for info, data in entries if info.filename == "styles.xml"), None)
    styles_root = ET.fromstring(styles) if styles is not None else None

    header = named_table(root, "Table2")
    replace_text(header, "FACH", subject.upper())
    if styles_root is not None:
        replace_text(styles_root, "[Kürzel]", teacher_abbreviation)
        replace_text(styles_root, "[Schulname]", school_name)
    replace_text(header, "Klasse 8a", f"Klasse {student['class_id']}")
    replace_text(
        root,
        "SE-Collector · Klasse 8a",
        f"Klasse {student['class_id']} · Schuljahr {student.get('school_year', 'nicht angegeben')}",
    )
    replace_text(root, "Anna Beispiel", str(student["name"]))
    replace_text(
        root,
        "Klasse 8a · Schüler-ID 8a-01",
        f"Klasse {student['class_id']} · Schüler-ID {student['student_id']} · "
        f"Code {student['short_code']}",
    )
    replace_text(
        root,
        "Scannen und den aktuellen Sitzungscode eingeben.",
        "Mit dem Klassen-WLAN verbinden, VPN ausschalten, scannen und den Sitzungscode eingeben.",
    )

    qr_payload = f"{direct_base_url.rstrip('/')}/p/{student['public_token']}"
    replacements = {
        "content.xml": ET.tostring(root, encoding="utf-8", xml_declaration=True),
        "styles.xml": ET.tostring(styles_root, encoding="utf-8", xml_declaration=True) if styles_root is not None else styles,
        QR_IMAGE_PATH: _qr_png(qr_payload),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as target:
        for info, data in entries:
            payload = replacements.get(info.filename, data)
            compression = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
            target.writestr(info, payload, compress_type=compression)


def generate_qr_cards_pdf(
    students: list[dict],
    subject: str,
    direct_base_url: str,
    template_path: Path,
    output_path: Path,
    teacher_abbreviation: str = "KÜR",
    school_name: str = "Beispielschule",
) -> int:
    if not direct_base_url.strip():
        raise ValueError("Vor dem Kartendruck muss eine feste Direktadresse eingerichtet sein.")
    if not students:
        raise ValueError("Für diese Klasse sind keine aktiven Schülerinnen oder Schüler vorhanden.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="se-qr-karten-") as temporary:
        temp = Path(temporary)
        pdfs: list[Path] = []
        for index, student in enumerate(students, start=1):
            odt_path = temp / f"{index:02d}_{student['student_id']}.odt"
            fill_qr_template(template_path, odt_path, student, subject, direct_base_url, teacher_abbreviation, school_name)
            pdfs.append(convert_to_pdf(odt_path, temp, temp / f"profile-{index}"))

        writer = PdfWriter()
        for pdf_path in pdfs:
            reader = PdfReader(pdf_path)
            if len(reader.pages) != 1:
                raise RuntimeError(f"QR-Blatt {pdf_path.stem} umfasst nicht genau eine Seite.")
            page = reader.pages[0]
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            if abs(width - 595.3) > 2 or abs(height - 420.9) > 2:
                raise RuntimeError(f"QR-Blatt {pdf_path.stem} ist nicht A5 im Querformat.")
            writer.append(reader)
        with output_path.open("wb") as stream:
            writer.write(stream)
    return len(students)
