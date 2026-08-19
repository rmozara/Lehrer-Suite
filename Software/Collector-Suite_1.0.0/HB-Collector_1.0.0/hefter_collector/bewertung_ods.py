from __future__ import annotations

import copy
import json
import math
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    "calcext": "urn:org:documentfoundation:names:experimental:calc:xmlns:calcext:1.0",
    "of": "urn:oasis:names:tc:opendocument:xmlns:of:1.2",
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

T = f"{{{NS['table']}}}"
O = f"{{{NS['office']}}}"
X = f"{{{NS['text']}}}"
C = f"{{{NS['calcext']}}}"

MAX_STUDENTS = 34
NAME_FIRST_ROW = 5
QUARTER_HEADER_ROWS = {1: 3, 2: 41, 3: 79, 4: 117}
VALUE_ATTRS = {
    O + "value-type",
    O + "value",
    O + "string-value",
    O + "boolean-value",
    O + "date-value",
    O + "time-value",
    O + "currency",
    C + "value-type",
}


@dataclass(frozen=True)
class OdsStudent:
    list_position: int
    name: str
    student_code: str = ""


def _column_name(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _read_package(path: Path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Hefterbewertung.ods wurde im Arbeitsordner nicht gefunden: {path}")
    with zipfile.ZipFile(path) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    content = next((data for info, data in entries if info.filename == "content.xml"), None)
    if content is None:
        raise ValueError("Die Datei ist keine gültige ODS-Datei: content.xml fehlt.")
    return entries, ET.fromstring(content)


def _table(root: ET.Element, name: str) -> ET.Element:
    found = next(
        (item for item in root.iter(T + "table") if item.get(T + "name") == name),
        None,
    )
    if found is None:
        raise ValueError(f"Tabellenblatt {name!r} fehlt in Hefterbewertung.ods.")
    return found


def _logical_row(table: ET.Element, row_number: int) -> ET.Element:
    logical = 1
    for row in table.findall(T + "table-row"):
        repeat = int(row.get(T + "number-rows-repeated", "1"))
        if logical <= row_number < logical + repeat:
            if repeat == 1:
                return row
            before = row_number - logical
            after = repeat - before - 1
            replacements: list[ET.Element] = []
            if before:
                left = copy.deepcopy(row)
                left.set(T + "number-rows-repeated", str(before))
                replacements.append(left)
            target = copy.deepcopy(row)
            target.attrib.pop(T + "number-rows-repeated", None)
            replacements.append(target)
            if after:
                right = copy.deepcopy(row)
                right.set(T + "number-rows-repeated", str(after))
                replacements.append(right)
            index = list(table).index(row)
            table.remove(row)
            for offset, replacement in enumerate(replacements):
                table.insert(index + offset, replacement)
            return target
        logical += repeat
    raise IndexError(f"Zeile {row_number} fehlt in Hefterbewertung.ods.")


def _ensure_cell(row: ET.Element, column_number: int) -> ET.Element:
    logical = 1
    for index, cell in enumerate(list(row)):
        if cell.tag not in (T + "table-cell", T + "covered-table-cell"):
            continue
        repeat = int(cell.get(T + "number-columns-repeated", "1"))
        if logical <= column_number < logical + repeat:
            if repeat == 1:
                return cell
            before = column_number - logical
            after = repeat - before - 1
            replacements: list[ET.Element] = []
            if before:
                left = copy.deepcopy(cell)
                left.set(T + "number-columns-repeated", str(before))
                replacements.append(left)
            target = copy.deepcopy(cell)
            target.attrib.pop(T + "number-columns-repeated", None)
            replacements.append(target)
            if after:
                right = copy.deepcopy(cell)
                right.set(T + "number-columns-repeated", str(after))
                replacements.append(right)
            row.remove(cell)
            for offset, replacement in enumerate(replacements):
                row.insert(index + offset, replacement)
            return target
        logical += repeat
    while logical <= column_number:
        cell = ET.Element(T + "table-cell")
        row.append(cell)
        if logical == column_number:
            return cell
        logical += 1
    raise IndexError(column_number)


def _cell(table: ET.Element, row_number: int, column_number: int) -> ET.Element:
    return _ensure_cell(_logical_row(table, row_number), column_number)


def _text(cell: ET.Element) -> str:
    return "\n".join("".join(item.itertext()) for item in cell.findall(X + "p")).strip()


def _value(cell: ET.Element):
    if (cell.get(O + "value-type") or cell.get(C + "value-type")) == "float":
        raw = cell.get(O + "value")
        if raw is not None:
            number = float(raw)
            return int(number) if number.is_integer() else number
    text = _text(cell)
    return None if text == "" else text


def _set_value(cell: ET.Element, value) -> None:
    cell.attrib.pop(T + "formula", None)
    for key in list(cell.attrib):
        if key in VALUE_ATTRS:
            cell.attrib.pop(key, None)
    for child in list(cell):
        cell.remove(child)
    paragraph = ET.SubElement(cell, X + "p")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        cell.set(O + "value-type", "float")
        cell.set(C + "value-type", "float")
        cell.set(O + "value", format(number, ".15g"))
        paragraph.text = str(int(number)) if number.is_integer() else format(number, "g")
    elif isinstance(value, date):
        cell.set(O + "value-type", "date")
        cell.set(C + "value-type", "date")
        cell.set(O + "date-value", value.isoformat())
        paragraph.text = value.strftime("%d.%m.%Y")
    else:
        cell.set(O + "value-type", "string")
        cell.set(C + "value-type", "string")
        paragraph.text = str(value)


def _invalidate_formula_cache(root: ET.Element) -> None:
    for cell in root.iter(T + "table-cell"):
        if not cell.get(T + "formula"):
            continue
        for key in list(cell.attrib):
            if key in VALUE_ATTRS:
                cell.attrib.pop(key, None)
        for child in list(cell):
            cell.remove(child)


def _write_package(entries, root: ET.Element, target: Path) -> None:
    content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if b"xmlns:of=" not in content:
        marker = b"<office:document-content "
        content = content.replace(
            marker,
            marker + b'xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" ',
            1,
        )
    with tempfile.NamedTemporaryFile(
        prefix="bewertung-", suffix=".ods", dir=target.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, "w") as output:
            for info, data in entries:
                payload = content if info.filename == "content.xml" else data
                compression = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
                output.writestr(info, payload, compress_type=compression)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


def read_roster(path: Path) -> tuple[OdsStudent, ...]:
    _, root = _read_package(path)
    names = _table(root, "Namensliste")
    result: list[OdsStudent] = []
    for position in range(1, MAX_STUDENTS + 1):
        name = _value(_cell(names, NAME_FIRST_ROW + position - 1, 3))
        if name in (None, "", -1, "-1"):
            continue
        student_code = _value(_cell(names, NAME_FIRST_ROW + position - 1, 4))
        result.append(OdsStudent(position, str(name).strip(), "" if student_code in (None, "", -1, "-1") else str(student_code).strip()))
    if not result:
        raise ValueError("In Hefterbewertung.ods sind noch keine Namen eingetragen.")
    return tuple(result)


def roster_class(students: tuple[OdsStudent, ...]) -> str:
    classes = {
        student.student_code.rsplit("-", 1)[0]
        for student in students
        if "-" in student.student_code
    }
    if len(classes) != 1:
        raise ValueError("Die Schüler-IDs müssen genau einer Klasse zugeordnet sein, z. B. 8a-01 bis 8a-30.")
    return next(iter(classes))


def read_subject(path: Path) -> str:
    return read_document_parameters(path)["subject"]


def read_document_parameters(path: Path) -> dict[str, str]:
    _, root = _read_package(path)
    table = _table(root, "Parameter")
    result: dict[str, str] = {}
    for key, label in (("subject", "Fach"), ("teacher_abbreviation", "Kürzel"), ("school_name", "Schulname")):
        for row in range(1, 60):
            for column in range(1, 12):
                if str(_value(_cell(table, row, column)) or "").strip().casefold() == label.casefold():
                    result[key] = str(_value(_cell(table, row, column + 1)) or "").strip()
                    break
            if result.get(key):
                break
        if not result.get(key):
            raise ValueError(f"Im Blatt Parameter fehlt neben ‚{label}‘ die Angabe.")
    return result


def write_hefter_results(
    path: Path,
    rows: list[dict],
    maximum: int,
    session_date: date,
    period: str = "",
    quarter: int | None = None,
    criterion_ids: list[str] | None = None,
) -> Path:
    if any(row.get("teacher_total") is None for row in rows):
        raise ValueError("Es fehlen noch verbindliche Lehrerbewertungen.")

    entries, root = _read_package(path)
    workbook_roster = {item.list_position: item for item in read_roster(path)}
    for row in rows:
        position = int(row["list_position"])
        expected = workbook_roster.get(position)
        if expected is None or expected.name != str(row["name"]).strip():
            raise ValueError(
                f"Namensliste stimmt bei Listenplatz {position} nicht überein "
                f"({expected.name if expected else None!r} statt {row['name']!r})."
            )
        if row.get("student_code") and expected.student_code != str(row["student_code"]).strip():
            raise ValueError(f"Schüler-ID stimmt bei Listenplatz {position} nicht überein.")

    try:
        raw = _table(root, "Rohdaten")
        summary = _table(root, "Auswertung")
    except ValueError:
        if quarter not in QUARTER_HEADER_ROWS:
            raise
        sheet = _table(root, "Hefter")
        header_row = QUARTER_HEADER_ROWS[quarter]
        _set_value(_cell(sheet, header_row, 4), session_date)
        for row in rows:
            target_row = header_row + 2 + int(row["list_position"]) - 1
            _set_value(_cell(sheet, target_row, 4), int(row["teacher_total"]))
            _set_value(_cell(sheet, target_row, 5), int(maximum))
        _invalidate_formula_cache(root)
        backup_dir = path.parent / "HB-Collector-Sicherungen"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = backup_dir / f"Bewertung_vor_HB_{stamp}.ods"
        shutil.copy2(path, backup)
        _write_package(entries, root, path)
        return backup
    criterion_ids = criterion_ids or [
        "beschriftung", "zustand", "struktur", "ablage", "vollstaendigkeit",
        "bearbeitung", "darstellungen", "lesbarkeit", "abgabe",
    ]
    if not 1 <= len(criterion_ids) <= 9:
        raise ValueError("Hefterbewertung.ods unterstützt ein bis neun Kriterien.")
    parameters = _table(root, "Parameter")
    _set_value(_cell(parameters, 5, 6), maximum)
    _set_value(_cell(parameters, 6, 6), len(criterion_ids))
    _set_value(_cell(parameters, 8, 6), maximum)
    thresholds = [0, math.ceil(maximum * .30), math.ceil(maximum * .45),
                  math.ceil(maximum * .60), math.ceil(maximum * .75),
                  math.ceil(maximum * .90)]
    for parameter_row, threshold in enumerate(thresholds, start=5):
        _set_value(_cell(parameters, parameter_row, 2), threshold)
    date_text = session_date.strftime("%d.%m.%Y")
    # Exactly as in SE: one authoritative date in the green merged header.
    # Rohdaten!D3 mirrors it by formula; obsolete free-floating date cells stay empty.
    _set_value(_cell(raw, 2, 4), "")
    _set_value(_cell(summary, 2, 4), "")
    _set_value(_cell(summary, 3, 4), date_text)
    for target_row in range(5, NAME_FIRST_ROW + MAX_STUDENTS):
        for column in range(5, 36):
            _set_value(_cell(raw, target_row, column), -1)
        sheet_row = target_row
        for summary_column, raw_first_column in ((4, 9), (5, 18), (6, 27)):
            first_letter = _column_name(raw_first_column)
            last_letter = _column_name(raw_first_column + len(criterion_ids) - 1)
            summary_cell = _cell(summary, target_row, summary_column)
            summary_cell.set(
                T + "formula",
                f"of:=IF(MIN([Rohdaten.{first_letter}{sheet_row}:.{last_letter}{sheet_row}])<0;-1;"
                f"SUM([Rohdaten.{first_letter}{sheet_row}:.{last_letter}{sheet_row}]))",
            )
    for row in rows:
        target_row = NAME_FIRST_ROW + int(row["list_position"]) - 1
        _set_value(_cell(raw, target_row, 5), period)
        role_columns = {"self": (6, 9), "peer": (7, 18), "teacher": (8, 27)}
        for role, (submitted_column, first_value_column) in role_columns.items():
            raw_json = row.get(f"{role}_values")
            if not raw_json:
                continue
            values = json.loads(str(raw_json))
            submitted = row.get(f"{role}_submitted_at") or "erfasst"
            try:
                submitted_text = datetime.fromisoformat(str(submitted)).strftime("%H:%M")
            except ValueError:
                submitted_text = str(submitted)
            _set_value(_cell(raw, target_row, submitted_column), submitted_text)
            for offset, criterion_id in enumerate(criterion_ids):
                value = int(values[criterion_id])
                if value not in {1, 2, 3, 4}:
                    raise ValueError(f"Ungültiger Wert für {criterion_id}: {value}")
                _set_value(_cell(raw, target_row, first_value_column + offset), value)
    _invalidate_formula_cache(root)

    backup_dir = path.parent / "HB-Collector-Sicherungen"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = backup_dir / f"Hefterbewertung_vor_Aktualisierung_{stamp}.ods"
    shutil.copy2(path, backup)
    _write_package(entries, root, path)
    return backup
