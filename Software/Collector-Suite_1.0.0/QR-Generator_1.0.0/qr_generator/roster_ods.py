from __future__ import annotations

import copy
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
T = f"{{{NS['table']}}}"
O = f"{{{NS['office']}}}"
X = f"{{{NS['text']}}}"


@dataclass(frozen=True)
class Roster:
    school_year: str
    class_id: str
    subject: str
    teacher_abbreviation: str
    school_name: str
    students: list[dict]


def _text(cell: ET.Element) -> str:
    return "\n".join("".join(item.itertext()) for item in cell.findall(X + "p")).strip()


def _value(cell: ET.Element):
    if cell.get(O + "value-type") == "float" and cell.get(O + "value") is not None:
        number = float(cell.get(O + "value"))
        return int(number) if number.is_integer() else number
    return _text(cell)


def _expanded_rows(table: ET.Element, max_columns: int = 12):
    for source_row in table.findall(T + "table-row"):
        row_repeat = int(source_row.get(T + "number-rows-repeated", "1"))
        values = []
        for cell in source_row:
            if cell.tag not in (T + "table-cell", T + "covered-table-cell"):
                continue
            repeat = int(cell.get(T + "number-columns-repeated", "1"))
            values.extend([_value(cell)] * min(repeat, max_columns - len(values)))
            if len(values) >= max_columns:
                break
        values.extend([""] * (max_columns - len(values)))
        for _ in range(min(row_repeat, 500)):
            yield values[:]


def _normalized(value) -> str:
    return str(value or "").strip().casefold().replace(". ", "").replace(".", "")


def _right_of_label(rows: list[list], label: str) -> str:
    wanted = label.casefold()
    for row in rows:
        for index, value in enumerate(row[:-1]):
            if _normalized(value) == wanted:
                result = str(row[index + 1] or "").strip()
                if result and result != "-1":
                    return result
    raise ValueError(f"In Namensliste.ods fehlt die Angabe „{label.capitalize()}“.")


def read_roster(path: Path) -> Roster:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Namensliste.ods wurde im gewählten Ordner nicht gefunden: {path}")
    try:
        with zipfile.ZipFile(path) as package:
            content = package.read("content.xml")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("Namensliste.ods ist keine gültige ODS-Datei.") from exc
    root = ET.fromstring(content)
    table = next(
        (item for item in root.iter(T + "table") if item.get(T + "name") == "Namensliste"),
        None,
    )
    if table is None:
        raise ValueError("Das Tabellenblatt „Namensliste“ fehlt.")
    parameter_table = next(
        (item for item in root.iter(T + "table") if item.get(T + "name") == "Parameter"),
        None,
    )
    if parameter_table is None:
        raise ValueError("Das Tabellenblatt „Parameter“ fehlt.")
    parameter_rows = list(_expanded_rows(parameter_table))
    school_year = _right_of_label(parameter_rows, "schuljahr")
    class_id = _right_of_label(parameter_rows, "klasse")
    subject = _right_of_label(parameter_rows, "fach")
    teacher_abbreviation = _right_of_label(parameter_rows, "kürzel")
    school_name = _right_of_label(parameter_rows, "schulname")
    rows = list(_expanded_rows(table))

    header_index = None
    columns = None
    for index, row in enumerate(rows):
        normalized = [_normalized(value) for value in row]
        try:
            candidate = (
                normalized.index("nr"),
                normalized.index("name"),
                normalized.index("schüler-id"),
            )
        except ValueError:
            continue
        header_index, columns = index, candidate
        break
    if header_index is None or columns is None:
        raise ValueError("Im Blatt „Namensliste“ fehlen die Spalten Nr., Name und Schüler-ID.")

    raw_students: list[tuple[int, str, str]] = []
    positions: set[int] = set()
    keys: set[str] = set()
    for row in rows[header_index + 1 :]:
        raw_position, raw_name, raw_key = (row[column] for column in columns)
        name = str(raw_name or "").strip()
        student_key = str(raw_key or "").strip()
        if name in {"", "-1"} and student_key in {"", "-1"}:
            continue
        try:
            position = int(float(str(raw_position)))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Ungültige Nummer für {name or student_key}.") from exc
        if not name or name == "-1" or not student_key or student_key == "-1":
            raise ValueError(f"In Zeile mit Nr. {position} müssen Name und Schüler-ID ausgefüllt sein.")
        folded = student_key.casefold()
        if position in positions:
            raise ValueError(f"Nummer doppelt: {position}")
        if folded in keys:
            raise ValueError(f"Schüler-ID doppelt: {student_key}")
        positions.add(position)
        keys.add(folded)
        raw_students.append((position, name, student_key))
    if not raw_students:
        raise ValueError("Die Namensliste enthält keine aktiven Schülerinnen oder Schüler.")
    students = [
        {
            "class_id": class_id,
            "student_id": student_key,
            "list_position": position,
            "name": name,
        }
        for position, name, student_key in raw_students
    ]
    students.sort(key=lambda item: item["list_position"])
    return Roster(school_year=school_year, class_id=class_id, subject=subject, teacher_abbreviation=teacher_abbreviation, school_name=school_name, students=students)


def read_generation_date(path: Path) -> str:
    """Return the visible generation date from Namensliste!D3, if present."""
    try:
        with zipfile.ZipFile(path) as package:
            root = ET.fromstring(package.read("content.xml"))
        table = next(
            item for item in root.iter(T + "table") if item.get(T + "name") == "Namensliste"
        )
        rows = list(_expanded_rows(table))
        value = str(rows[2][3] or "").strip()
        return "" if value.casefold() == "datum" else value
    except (OSError, KeyError, IndexError, StopIteration, ValueError, zipfile.BadZipFile, ET.ParseError):
        return ""


def _logical_row(table: ET.Element, number: int) -> ET.Element:
    current = 1
    for row in table.findall(T + "table-row"):
        repeat = int(row.get(T + "number-rows-repeated", "1"))
        if current <= number < current + repeat:
            before, after = number - current, repeat - (number - current) - 1
            replacements = []
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
        current += repeat
    raise ValueError("In Namensliste.ods fehlt die vorgesehene Datumszeile.")


def _logical_cell(row: ET.Element, number: int) -> ET.Element:
    current = 1
    for index, source in enumerate(list(row)):
        if source.tag not in (T + "table-cell", T + "covered-table-cell"):
            continue
        repeat = int(source.get(T + "number-columns-repeated", "1"))
        if current <= number < current + repeat:
            before, after = number - current, repeat - (number - current) - 1
            replacements = []
            if before:
                left = copy.deepcopy(source)
                left.set(T + "number-columns-repeated", str(before))
                replacements.append(left)
            target = copy.deepcopy(source)
            target.attrib.pop(T + "number-columns-repeated", None)
            replacements.append(target)
            if after:
                right = copy.deepcopy(source)
                right.set(T + "number-columns-repeated", str(after))
                replacements.append(right)
            row.remove(source)
            for offset, replacement in enumerate(replacements):
                row.insert(index + offset, replacement)
            return target
        current += repeat
    raise ValueError("In Namensliste.ods fehlt die vorgesehene Datumsspalte.")


def write_generation_date(path: Path, generated_on: date | None = None) -> None:
    generated_on = generated_on or date.today()
    with zipfile.ZipFile(path) as package:
        entries = [(info, package.read(info.filename)) for info in package.infolist()]
    content = next(data for info, data in entries if info.filename == "content.xml")
    root = ET.fromstring(content)
    table = next(
        (item for item in root.iter(T + "table") if item.get(T + "name") == "Namensliste"),
        None,
    )
    if table is None:
        raise ValueError("Das Tabellenblatt „Namensliste“ fehlt.")
    target = _logical_cell(_logical_row(table, 3), 4)
    style = target.get(T + "style-name")
    target.clear()
    if style:
        target.set(T + "style-name", style)
    target.set(O + "value-type", "string")
    ET.SubElement(target, X + "p").text = generated_on.strftime("%d.%m.%Y")
    new_content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with tempfile.NamedTemporaryFile(prefix="namensliste-", suffix=".ods", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, "w") as output:
            for info, data in entries:
                payload = new_content if info.filename == "content.xml" else data
                compression = zipfile.ZIP_STORED if info.filename == "mimetype" else info.compress_type
                output.writestr(info, payload, compress_type=compression)
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()
