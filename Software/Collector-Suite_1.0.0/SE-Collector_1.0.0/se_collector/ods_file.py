from __future__ import annotations

import copy
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from .core import flatten_questions

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

MAX_STUDENTS = 34
NAME_FIRST_ROW = 5
RAW_FIRST_ROW = 5


@dataclass(frozen=True)
class OdsRoster:
    class_id: str
    students: tuple[dict, ...]


@dataclass(frozen=True)
class OdsParameters:
    subject: str
    teacher_abbreviation: str
    school_name: str
    section_maxima: tuple[int, int, int, int]
    total_maximum: int
    grade_thresholds: tuple[dict, ...]


def _read_package(path: Path) -> tuple[dict[str, tuple[zipfile.ZipInfo, bytes]], ET.Element]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Selbstevaluation.ods nicht gefunden: {path}")
    with zipfile.ZipFile(path, "r") as source:
        entries = {info.filename: (info, source.read(info.filename)) for info in source.infolist()}
    if "content.xml" not in entries:
        raise ValueError("Die Datei ist keine gültige ODS-Datei: content.xml fehlt.")
    return entries, ET.fromstring(entries["content.xml"][1])


def _table(root: ET.Element, name: str) -> ET.Element:
    found = next((item for item in root.iter(T + "table") if item.get(T + "name") == name), None)
    if found is None:
        raise ValueError(f"Tabellenblatt {name!r} fehlt in Selbstevaluation.ods.")
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
            parent = table
            index = list(parent).index(row)
            parent.remove(row)
            for offset, replacement in enumerate(replacements):
                parent.insert(index + offset, replacement)
            return target
        logical += repeat
    raise IndexError(f"Zeile {row_number} fehlt in der ODS-Datei.")


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
    paragraphs = []
    for p in cell.findall(X + "p"):
        paragraphs.append("".join(p.itertext()))
    return "\n".join(paragraphs).strip()


def _value(cell: ET.Element):
    value_type = cell.get(O + "value-type") or cell.get(C + "value-type")
    if value_type == "float":
        raw = cell.get(O + "value")
        if raw is None:
            return None
        number = float(raw)
        return int(number) if number.is_integer() else number
    if value_type == "boolean":
        return cell.get(O + "boolean-value") == "true"
    if value_type in ("date", "time"):
        return cell.get(O + f"{value_type}-value")
    text = _text(cell)
    if text == "":
        return None
    return text


def _clear_value(cell: ET.Element) -> None:
    for key in list(cell.attrib):
        if key in VALUE_ATTRS:
            cell.attrib.pop(key, None)
    # Keep table:formula and table:style-name. Remove displayed paragraphs only.
    for child in list(cell):
        cell.remove(child)


def _set_value(cell: ET.Element, value) -> None:
    _clear_value(cell)
    p = ET.SubElement(cell, X + "p")
    if isinstance(value, bool):
        cell.set(O + "value-type", "boolean")
        cell.set(C + "value-type", "boolean")
        cell.set(O + "boolean-value", "true" if value else "false")
        p.text = "WAHR" if value else "FALSCH"
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        cell.set(O + "value-type", "float")
        cell.set(C + "value-type", "float")
        cell.set(O + "value", format(number, ".15g"))
        p.text = str(int(number)) if number.is_integer() else format(number, "g")
    else:
        cell.set(O + "value-type", "string")
        cell.set(C + "value-type", "string")
        p.text = str(value)


def _invalidate_formula_cache(root: ET.Element) -> None:
    """Remove cached results while preserving formulas and styles.

    Direct XML updates do not mark Calc's dependency graph as dirty. Without
    invalidation, LibreOffice may initially show the old cached results even
    though Rohdaten has changed. Empty formula caches force Calc to evaluate
    the existing formulas on load; the Collector still does not calculate or
    write any result values itself.
    """
    for cell in root.iter(T + "table-cell"):
        if not cell.get(T + "formula"):
            continue
        for key in list(cell.attrib):
            if key in VALUE_ATTRS:
                cell.attrib.pop(key, None)
        for child in list(cell):
            cell.remove(child)


def _write_package(entries: dict[str, tuple[zipfile.ZipInfo, bytes]], root: ET.Element, target: Path) -> None:
    content_xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    if b"xmlns:of=" not in content_xml:
        marker = b"<office:document-content "
        content_xml = content_xml.replace(
            marker,
            marker + b'xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2" ',
            1,
        )
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="selbstevaluation-", suffix=".ods", dir=target.parent, delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        with zipfile.ZipFile(temp_path, "w") as out:
            # ODS requires mimetype first and uncompressed.
            mimetype = entries.get("mimetype")
            if mimetype:
                out.writestr("mimetype", mimetype[1], compress_type=zipfile.ZIP_STORED)
            for name, (info, data) in entries.items():
                if name == "mimetype":
                    continue
                payload = content_xml if name == "content.xml" else data
                out.writestr(name, payload, compress_type=info.compress_type)
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)


def _derive_class_id(student_ids: list[str]) -> str:
    prefixes: set[str] = set()
    for student_id in student_ids:
        match = re.fullmatch(r"(.+?)-\d+", student_id.strip())
        if not match:
            raise ValueError(
                f"Schüler-ID {student_id!r} hat nicht das erwartete Format, z. B. 8a-01."
            )
        prefixes.add(match.group(1))
    if len(prefixes) != 1:
        raise ValueError("Alle aktiven Schüler-IDs müssen zur selben Klasse gehören.")
    return next(iter(prefixes))


def read_roster(path: Path) -> OdsRoster:
    _, root = _read_package(path)
    table = _table(root, "Namensliste")
    students: list[dict] = []
    for position in range(1, MAX_STUDENTS + 1):
        row = NAME_FIRST_ROW + position - 1
        number = _value(_cell(table, row, 2))
        name = _value(_cell(table, row, 3))
        student_id = _value(_cell(table, row, 4))
        if name in (None, "", -1, "-1"):
            continue
        if student_id in (None, "", -1, "-1"):
            raise ValueError(f"In Namensliste Zeile {row} fehlt die Schüler-ID.")
        list_position = int(number) if number not in (None, "") else position
        students.append(
            {
                "class_id": "",  # filled after class derivation
                "student_id": str(student_id).strip(),
                "name": str(name).strip(),
                "list_position": list_position,
            }
        )
    if not students:
        raise ValueError("Die Namensliste enthält keine aktiven Schülerinnen oder Schüler.")
    class_id = _derive_class_id([item["student_id"] for item in students])
    for item in students:
        item["class_id"] = class_id
    return OdsRoster(class_id=class_id, students=tuple(students))



GRADE_LABELS = {
    0.7: "1+", 1.0: "1", 1.3: "1-",
    1.7: "2+", 2.0: "2", 2.3: "2-",
    2.7: "3+", 3.0: "3", 3.3: "3-",
    3.7: "4+", 4.0: "4", 4.3: "4-",
    4.7: "5+", 5.0: "5", 5.3: "5-",
    6.0: "6",
}


def _grade_label(value: float) -> str:
    rounded = round(float(value), 1)
    try:
        return GRADE_LABELS[rounded]
    except KeyError as exc:
        raise ValueError(
            f"Parameter: Für den Notenwert {value!r} ist keine Notenstufe definiert."
        ) from exc


def read_parameters(path: Path) -> OdsParameters:
    """Read maxima and the numeric grade key from the user's Parameter sheet.

    The finalized layout is:
      B5:B20 = Mindestpunkte, C5:C20 = numerischer Notenwert
      E5:E9  = Bereich,       F5:F9  = Maximalpunkte
    The text grade labels needed only for the unchanged smartphone result page
    are derived from the numeric values and are not written into the workbook.
    """
    _, root = _read_package(path)
    table = _table(root, "Parameter")

    def labeled_value(label: str) -> str:
        for row in range(1, 60):
            for column in range(1, 12):
                if str(_value(_cell(table, row, column)) or "").strip().casefold() == label.casefold():
                    value = str(_value(_cell(table, row, column + 1)) or "").strip()
                    if value:
                        return value
        raise ValueError(f"Parameter: Neben der Angabe „{label}“ fehlt der Wert.")

    subject = labeled_value("Fach")
    teacher_abbreviation = labeled_value("Kürzel")
    school_name = labeled_value("Schulname")

    maxima = tuple(int(_value(_cell(table, row, 6))) for row in range(5, 9))
    # F9 is a formula cell. Its cached value can be absent after an ODS update,
    # so the authoritative total is calculated from the four input cells.
    total = sum(maxima)

    thresholds: list[dict] = []
    for row in range(5, 21):
        minimum = _value(_cell(table, row, 2))
        grade_value = _value(_cell(table, row, 3))
        if minimum in (None, ""):
            continue
        if grade_value in (None, ""):
            raise ValueError(f"Parameter: In Zeile {row} fehlt der Notenwert.")
        value = float(grade_value)
        thresholds.append({
            "min_points": int(minimum),
            "grade_label": _grade_label(value),
            "grade_value": value,
        })

    if not thresholds or min(item["min_points"] for item in thresholds) != 0:
        raise ValueError("Parameter: Der Notenschlüssel muss bei 0 Punkten beginnen.")
    if len({item["min_points"] for item in thresholds}) != len(thresholds):
        raise ValueError("Parameter: Mindestpunktzahlen dürfen nicht doppelt vorkommen.")
    return OdsParameters(subject, teacher_abbreviation, school_name, maxima, total, tuple(thresholds))


def apply_parameters_to_form(form: dict, parameters: OdsParameters) -> None:
    if len(form.get("sections", [])) != 4:
        raise ValueError("SE1 muss genau vier Bereiche enthalten.")
    for section, maximum in zip(form["sections"], parameters.section_maxima):
        section["max_points"] = int(maximum)
    form["max_points"] = int(parameters.total_maximum)
    form["grade_thresholds"] = [dict(item) for item in parameters.grade_thresholds]

def _submitted_time_fraction(value: str) -> float:
    """Convert an ISO timestamp to a Calc-compatible fraction of one day."""
    try:
        stamp = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Ungültiger Abgabezeitpunkt: {value!r}") from exc
    seconds = stamp.hour * 3600 + stamp.minute * 60 + stamp.second
    return seconds / 86400


def _session_date(session) -> str | None:
    """Return the classroom-session date, never the later print date."""
    try:
        value = session["started_at"]
    except (KeyError, IndexError):
        # Kept for callers/tests using the older minimal session mapping.
        # Production sessions always contain started_at.
        return None
    try:
        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y")
    except ValueError as exc:
        raise ValueError(f"Ungültiges Sitzungsdatum: {value!r}") from exc


def _assert_not_locked(path: Path) -> None:
    # LibreOffice creates .~lock.<filename># next to an opened document.
    lock_file = path.with_name(f".~lock.{path.name}#")
    if lock_file.exists():
        raise PermissionError(
            "Selbstevaluation.ods ist offenbar in LibreOffice geöffnet. "
            "Bitte speichern, schließen und die Aktualisierung erneut starten."
        )


def update_raw_data(
    path: Path,
    session,
    summary_rows: list[dict],
    form: dict,
    backup_dir: Path,
) -> Path:
    """Write the session date plus Quartal, Abgabezeit and q01..q22.

    Students are matched by Schüler-ID, never by name or row number. Formatting,
    formulas, column widths and every other sheet remain untouched.
    """
    path = Path(path)
    _assert_not_locked(path)
    entries, root = _read_package(path)
    raw = _table(root, "Rohdaten")
    evaluation = _table(root, "Auswertung")
    session_date = _session_date(session)
    if session_date:
        date_text = session_date
        # The visible date belongs in the green, merged table header D3.
        # Rohdaten!D3 mirrors Auswertung!D3 by formula, so keep that formula
        # intact and update only its authoritative source. D2 was an obsolete,
        # free-floating manual input left over from the old template.
        _set_value(_cell(raw, 2, 4), "")
        _set_value(_cell(evaluation, 2, 4), "")
        _set_value(_cell(evaluation, 3, 4), date_text)
    question_ids = [q["id"] for q in flatten_questions(form)]

    by_student_id: dict[str, dict] = {}
    for item in summary_rows:
        student_id = str(item["Schüler-ID"]).strip()
        if student_id in by_student_id:
            raise ValueError(f"Doppelte Schüler-ID in den Sitzungsdaten: {student_id}")
        by_student_id[student_id] = item

    # Rohdaten!D contains formulas that mirror Namensliste!D. After a prior
    # XML update their cached results are deliberately invalidated so Calc
    # recalculates the workbook on opening. Therefore the Collector must not
    # depend on those caches when a later ODS update is performed. The fixed
    # row association is read from the authoritative Namensliste instead.
    roster = _table(root, "Namensliste")
    raw_rows: dict[str, int] = {}
    for position in range(1, MAX_STUDENTS + 1):
        name_row = NAME_FIRST_ROW + position - 1
        raw_row = RAW_FIRST_ROW + position - 1
        name = _value(_cell(roster, name_row, 3))
        student_id = _value(_cell(roster, name_row, 4))
        if name in (None, "", -1, "-1"):
            continue
        if student_id in (None, "", -1, "-1"):
            raise ValueError(f"In Namensliste Zeile {name_row} fehlt die Schüler-ID.")
        key = str(student_id).strip()
        if key in raw_rows:
            raise ValueError(f"Doppelte Schüler-ID in Namensliste: {key}")
        raw_rows[key] = raw_row

    missing_ids = sorted(set(by_student_id) - set(raw_rows))
    if missing_ids:
        raise ValueError(
            "Folgende Schüler-IDs der Sitzung fehlen im Blatt Rohdaten: "
            + ", ".join(missing_ids)
        )

    # Reset only the payload cells E:AB, then fill active roster rows by ID.
    for position in range(1, MAX_STUDENTS + 1):
        row_no = RAW_FIRST_ROW + position - 1
        for column in range(5, 29):
            _set_value(_cell(raw, row_no, column), -1)

    for student_id, item in by_student_id.items():
        row_no = raw_rows[student_id]
        _set_value(_cell(raw, row_no, 5), session["period_id"])

        if not item.get("raw") or item.get("answers") is None:
            continue

        _set_value(
            _cell(raw, row_no, 6),
            _submitted_time_fraction(item["raw"]["submitted_at"]),
        )
        answers = item["answers"]
        for column, question_id in enumerate(question_ids, start=7):
            _set_value(_cell(raw, row_no, column), int(answers[question_id]))

    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = backup_dir / f"Selbstevaluation_{stamp}.ods"
    shutil.copy2(path, backup)
    # Preserve formulas but discard stale cached results so Calc recomputes
    # Auswertung after the changed raw inputs are loaded.
    _invalidate_formula_cache(root)
    try:
        _write_package(entries, root, path)
    except PermissionError as exc:
        raise PermissionError(
            "Selbstevaluation.ods konnte nicht überschrieben werden. "
            "Bitte prüfen, ob die Datei noch geöffnet ist."
        ) from exc
    return backup
