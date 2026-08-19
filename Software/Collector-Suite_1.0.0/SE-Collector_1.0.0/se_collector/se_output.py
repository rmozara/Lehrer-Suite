from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

from pypdf import PdfReader, PdfWriter

from .core import evaluate, flatten_questions
from .ods_file import (
    MAX_STUDENTS,
    RAW_FIRST_ROW,
    X,
    T,
    _cell,
    _read_package,
    _table,
    _value,
    apply_parameters_to_form,
    read_parameters,
    read_roster,
)

OFFICE = "urn:oasis:names:tc:opendocument:xmlns:office:1.0"
DRAW = "urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"
STYLE = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
FO = "urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
NS = {
    "office": OFFICE,
    "table": T[1:-1],
    "text": X[1:-1],
    "draw": DRAW,
    "style": STYLE,
    "fo": FO,
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


@dataclass(frozen=True)
class EvaluationSheet:
    class_id: str
    date: str
    period_id: str
    name: str
    answers: dict[str, int]
    section_points: tuple[int, int, int, int]
    total_points: int
    total_maximum: int
    percent: float
    grade_label: str
    subject: str = "Physik"
    teacher_abbreviation: str = "KÜR"
    school_name: str = "Beispielschule"


def _sheet_date(root: ET.Element) -> str:
    header = _value(_cell(_table(root, "Auswertung"), 3, 4))
    text = "" if header is None else str(header).strip()
    match = re.search(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b", text)
    if not match:
        raise ValueError(
            "Das Sitzungsdatum konnte nicht automatisch in das Blatt „Auswertung“ übernommen werden."
        )
    return match.group(1)


def read_evaluation_sheets(ods_path: Path, form: dict) -> list[EvaluationSheet]:
    _, root = _read_package(ods_path)
    roster = read_roster(ods_path)
    parameters = read_parameters(ods_path)
    apply_parameters_to_form(form, parameters)
    date = _sheet_date(root)
    raw = _table(root, "Rohdaten")
    question_ids = [item["id"] for item in flatten_questions(form)]
    sheets: list[EvaluationSheet] = []

    roster_by_position = {int(item["list_position"]): item for item in roster.students}
    for position in range(1, MAX_STUDENTS + 1):
        student = roster_by_position.get(position)
        if not student:
            continue
        row_no = RAW_FIRST_ROW + position - 1
        period = _value(_cell(raw, row_no, 5))
        values = [_value(_cell(raw, row_no, column)) for column in range(7, 29)]
        if period in (None, "", -1, "-1") or any(value in (None, "", -1, "-1") for value in values):
            continue
        answers = {question_id: int(value) for question_id, value in zip(question_ids, values)}
        _, total, grade_label, _, totals = evaluate(form, answers)
        section_points = tuple(int(totals[section["id"]]) for section in form["sections"])
        sheets.append(
            EvaluationSheet(
                subject=parameters.subject,
                teacher_abbreviation=parameters.teacher_abbreviation,
                school_name=parameters.school_name,
                class_id=roster.class_id,
                date=date,
                period_id=str(period),
                name=str(student["name"]),
                answers=answers,
                section_points=section_points,
                total_points=total,
                total_maximum=parameters.total_maximum,
                percent=100 * total / parameters.total_maximum,
                grade_label=grade_label,
            )
        )
    if not sheets:
        raise ValueError("In Selbstevaluation.ods sind keine vollständigen Abgaben vorhanden.")
    return sheets


def _named_table(root: ET.Element, name: str) -> ET.Element:
    for table in root.iter(T + "table"):
        if table.get(T + "name") == name:
            return table
    raise ValueError(f"Vorlage: Tabelle {name!r} fehlt.")


def _direct_text_elements(element: ET.Element) -> list[ET.Element]:
    return [item for item in element.iter() if item.text]


def _replace_text(element: ET.Element, old: str, new: str) -> None:
    for item in _direct_text_elements(element):
        if old in (item.text or ""):
            item.text = item.text.replace(old, new)
            return
    raise ValueError(f"Vorlage: Text {old!r} fehlt.")


def _set_cell_text(cell: ET.Element, value: str) -> None:
    paragraphs = list(cell.iter(X + "p"))
    if not paragraphs:
        paragraph = ET.SubElement(cell, X + "p")
    else:
        paragraph = paragraphs[0]
    for item in cell.iter():
        if item.text:
            item.text = ""
        if item.tail:
            item.tail = ""
    paragraph.text = value


def _row_cells(row: ET.Element) -> list[ET.Element]:
    return [
        item
        for item in list(row)
        if item.tag in (T + "table-cell", T + "covered-table-cell")
    ]


def _cell_text(cell: ET.Element) -> str:
    return " ".join("".join(cell.itertext()).split())


def _minimize_trailing_empty_paragraph(root: ET.Element) -> None:
    """Keep Writer's mandatory final paragraph small enough for page one."""
    body = root.find(f".//{{{OFFICE}}}text")
    if body is None or not len(body):
        return
    last = body[-1]
    if last.tag != X + "p" or "".join(last.itertext()).strip():
        last = ET.SubElement(body, X + "p")
    last.set(X + "style-name", "SEEnd")

    automatic = root.find(f"./{{{OFFICE}}}automatic-styles")
    if automatic is None:
        return
    style = ET.SubElement(
        automatic,
        f"{{{STYLE}}}style",
        {f"{{{STYLE}}}name": "SEEnd", f"{{{STYLE}}}family": "paragraph"},
    )
    ET.SubElement(
        style,
        f"{{{STYLE}}}paragraph-properties",
        {
            f"{{{FO}}}margin-top": "0in",
            f"{{{FO}}}margin-bottom": "0in",
            f"{{{FO}}}line-height": "0.01in",
        },
    )
    ET.SubElement(
        style,
        f"{{{STYLE}}}text-properties",
        {f"{{{FO}}}font-size": "1pt"},
    )


def fill_template(template_path: Path, output_path: Path, sheet: EvaluationSheet, form: dict) -> None:
    with zipfile.ZipFile(template_path, "r") as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    content = next((data for info, data in entries if info.filename == "content.xml"), None)
    if content is None:
        raise ValueError("Vorlage: content.xml fehlt.")
    root = ET.fromstring(content)
    styles = next((data for info, data in entries if info.filename == "styles.xml"), None)
    styles_root = ET.fromstring(styles) if styles is not None else None
    if styles_root is not None:
        _replace_text(styles_root, "[Kürzel]", sheet.teacher_abbreviation)
        _replace_text(styles_root, "[Schulname]", sheet.school_name)

    header = _named_table(root, "Table2")
    _replace_text(header, "PHYSIK", sheet.subject.upper())
    _replace_text(header, "Q1 2026/27", sheet.period_id)

    fields = _named_table(root, "SEFields")
    _replace_text(fields, "Anna Beispiel", sheet.name)
    _replace_text(fields, "8a", sheet.class_id)
    _replace_text(fields, "23.07.2026", sheet.date)

    evaluation = _named_table(root, "SE1Evaluation")
    question_by_text = {item["text"]: item["id"] for item in flatten_questions(form)}
    seen: set[str] = set()
    for row in evaluation.findall(T + "table-row"):
        cells = _row_cells(row)
        if len(cells) != 5:
            continue
        question_id = question_by_text.get(_cell_text(cells[0]))
        if not question_id:
            continue
        score = int(sheet.answers[question_id])
        for index, cell in enumerate(cells[1:]):
            _set_cell_text(cell, "●" if index == 3 - score else "")
        seen.add(question_id)
    missing = set(question_by_text.values()) - seen
    if missing:
        raise ValueError(f"Vorlage: Fragen fehlen: {', '.join(sorted(missing))}")

    maxima = [int(section["max_points"]) for section in form["sections"]]
    summary = _named_table(root, "SESummary")
    summary_spans = [
        item
        for item in summary.iter(X + "span")
        if item.get(X + "style-name") == "T7"
    ]
    if len(summary_spans) != 7:
        raise ValueError("Vorlage: Die sieben Ergebnisfelder fehlen.")
    summary_values = [
        *(f"{value} / {maximum}" for value, maximum in zip(sheet.section_points, maxima)),
        f"{sheet.total_points} / {sheet.total_maximum}",
        f"{sheet.percent:.1f}".replace(".", ",") + " %",
        sheet.grade_label,
    ]
    for span, value in zip(summary_spans, summary_values):
        span.text = value

    grade_table = _named_table(root, "SEGradeScale")
    rows = grade_table.findall(T + "table-row")
    thresholds = sorted(form["grade_thresholds"], key=lambda item: int(item["min_points"]), reverse=True)
    if len(rows) >= 2 and len(thresholds) == 16:
        label_cells = _row_cells(rows[0])[1:]
        point_cells = _row_cells(rows[1])[1:]
        for cell, threshold in zip(label_cells, thresholds):
            _set_cell_text(cell, str(threshold["grade_label"]))
        for cell, threshold in zip(point_cells, thresholds):
            _set_cell_text(cell, str(threshold["min_points"]))

    _minimize_trailing_empty_paragraph(root)
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


def _soffice() -> str:
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
        "LibreOffice wurde nicht gefunden. Bitte LibreOffice installieren oder „soffice“ zum PATH hinzufügen."
    )


def _convert_to_pdf(odt_path: Path, output_dir: Path, profile_dir: Path) -> Path:
    command = [
        _soffice(),
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
        raise RuntimeError(f"LibreOffice konnte das Ausgabeblatt nicht als PDF exportieren. {detail}")
    return pdf_path


def generate_pdf(ods_path: Path, template_path: Path, output_path: Path, form: dict) -> int:
    sheets = read_evaluation_sheets(ods_path, form)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="se1-ausgabe-") as temporary:
        temp = Path(temporary)
        pdfs: list[Path] = []
        for index, sheet in enumerate(sheets, start=1):
            odt_path = temp / f"{index:02d}_{sheet.name}.odt"
            fill_template(template_path, odt_path, sheet, form)
            pdfs.append(_convert_to_pdf(odt_path, temp, temp / f"profile-{index}"))

        writer = PdfWriter()
        for pdf_path in pdfs:
            reader = PdfReader(pdf_path)
            if len(reader.pages) != 1:
                raise RuntimeError(
                    f"Das Blatt für {pdf_path.stem} umfasst unerwartet {len(reader.pages)} Seiten."
                )
            writer.append(reader)
        with output_path.open("wb") as stream:
            writer.write(stream)
    return len(sheets)
