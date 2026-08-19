"""Build the HB workbook from the SE workbook's exact visual baseline."""

from __future__ import annotations

import copy
import shutil
from pathlib import Path

from hefter_collector import bewertung_ods as ods


ROOT = Path(__file__).resolve().parent.parent
SUITE = ROOT.parent
SOURCE = SUITE / "SE-Collector_1.0.0" / "templates" / "Selbstevaluation.ods"
TARGET = ROOT / "templates" / "Hefterbewertung.ods"


def set_formula(cell, formula: str, cached=-1) -> None:
    ods._set_value(cell, cached)
    cell.set(ods.T + "formula", formula)


def style_like(target, source) -> None:
    style = source.get(ods.T + "style-name")
    if style:
        target.set(ods.T + "style-name", style)


def extend_raw_columns(table) -> None:
    columns = table.findall(ods.T + "table-column")
    # The SE template has 22 narrow response columns G:AB. HB needs 27
    # criterion columns I:AI and therefore 32 used columns D:AI in total.
    timestamp = columns[-3]
    timestamp.set(ods.T + "number-columns-repeated", "3")
    response = columns[-2]
    response.set(ods.T + "number-columns-repeated", "27")
    tail = columns[-1]
    tail.set(ods.T + "number-columns-repeated", "16349")


def build() -> None:
    shutil.copy2(SOURCE, TARGET)
    entries, root = ods._read_package(TARGET)
    names = ods._table(root, "Namensliste")
    parameters = ods._table(root, "Parameter")
    raw = ods._table(root, "Rohdaten")
    summary = ods._table(root, "Auswertung")

    examples = (("Anna Beispiel", "8a-01"), ("Ben Beispiel", "8a-02"), ("Carla Beispiel", "8a-03"))
    for position in range(1, ods.MAX_STUDENTS + 1):
        row = ods.NAME_FIRST_ROW + position - 1
        name, student_id = examples[position - 1] if position <= len(examples) else (-1, -1)
        ods._set_value(ods._cell(names, row, 2), position)
        ods._set_value(ods._cell(names, row, 3), name)
        ods._set_value(ods._cell(names, row, 4), student_id)

    # Parameter: same two-block layout as SE, but the HB scale has nine
    # criteria with four points each and whole-number grades.
    for row in range(3, 25):
        for column in range(2, 7):
            if row == 3 and column in (3, 6):
                continue
            ods._set_value(ods._cell(parameters, row, column), "")
    ods._set_value(ods._cell(parameters, 3, 2), "Notenstufen")
    ods._set_value(ods._cell(parameters, 3, 5), "Maximalpunkte")
    ods._set_value(ods._cell(parameters, 4, 2), "Min")
    ods._set_value(ods._cell(parameters, 4, 3), "Note")
    ods._set_value(ods._cell(parameters, 4, 5), "Bereich")
    ods._set_value(ods._cell(parameters, 4, 6), "Max")
    for row, (minimum, grade) in enumerate(((0, 6), (11, 5), (17, 4), (22, 3), (27, 2), (33, 1)), start=5):
        ods._set_value(ods._cell(parameters, row, 2), minimum)
        ods._set_value(ods._cell(parameters, row, 3), grade)
    ods._set_value(ods._cell(parameters, 5, 5), "Hefterbew.")
    ods._set_value(ods._cell(parameters, 5, 6), 36)
    ods._set_value(ods._cell(parameters, 6, 5), "Kriterien")
    ods._set_value(ods._cell(parameters, 6, 6), 9)
    ods._set_value(ods._cell(parameters, 7, 5), "Punkte/Krit.")
    ods._set_value(ods._cell(parameters, 7, 6), 4)
    ods._set_value(ods._cell(parameters, 8, 5), "Gesamt")
    set_formula(ods._cell(parameters, 8, 6), "of:=[.F6]*[.F7]", 36)
    ods._set_value(ods._cell(parameters, 14, 5), "Fach")
    ods._set_value(ods._cell(parameters, 14, 6), "Physik")

    extend_raw_columns(raw)
    ods._set_value(ods._cell(raw, 3, 2), "Rohdaten")
    date_cell = ods._cell(raw, 3, 4)
    date_cell.set(ods.T + "number-columns-spanned", "32")
    set_formula(date_cell, "of:=[Auswertung.D3]", "Datum")
    for column in range(29, 36):
        covered = ods._cell(raw, 3, column)
        covered.tag = ods.T + "covered-table-cell"
        style_like(covered, ods._cell(raw, 3, 28))
    raw_headers = [
        "Nr.", "Name", "Schüler-ID", "Zeitraum", "Abgabe Selbst", "Abgabe Peer", "Abgabe Lehrkraft",
        *[f"S{i:02d}" for i in range(1, 10)],
        *[f"P{i:02d}" for i in range(1, 10)],
        *[f"L{i:02d}" for i in range(1, 10)],
    ]
    for column, label in enumerate(raw_headers, start=2):
        cell = ods._cell(raw, 4, column)
        if column > 28:
            style_like(cell, ods._cell(raw, 4, 28))
        ods._set_value(cell, label)
    for position in range(1, ods.MAX_STUDENTS + 1):
        row = ods.NAME_FIRST_ROW + position - 1
        ods._set_value(ods._cell(raw, row, 2), position)
        set_formula(ods._cell(raw, row, 3), f"of:=[Namensliste.C{row}]", examples[position - 1][0] if position <= 3 else -1)
        set_formula(ods._cell(raw, row, 4), f"of:=[Namensliste.D{row}]", examples[position - 1][1] if position <= 3 else -1)
        for column in range(5, 36):
            cell = ods._cell(raw, row, column)
            if column > 28:
                style_like(cell, ods._cell(raw, row, 28))
            ods._set_value(cell, -1)

    ods._set_value(ods._cell(summary, 3, 2), "Hefterbewertung")
    ods._set_value(ods._cell(summary, 3, 4), "Datum")
    headers = ["Nr.", "Name", "Selbst", "Peer", "Lehrkraft", "Abw. S/L", "Max", "Prozent", "Note"]
    for column, label in enumerate(headers, start=2):
        ods._set_value(ods._cell(summary, 4, column), label)
    for position in range(1, ods.MAX_STUDENTS + 1):
        row = ods.NAME_FIRST_ROW + position - 1
        ods._set_value(ods._cell(summary, row, 2), position)
        set_formula(ods._cell(summary, row, 3), f"of:=[Namensliste.C{row}]", examples[position - 1][0] if position <= 3 else -1)
        formulas = (
            f"of:=IF(MIN([Rohdaten.I{row}:.Q{row}])<0;-1;SUM([Rohdaten.I{row}:.Q{row}]))",
            f"of:=IF(MIN([Rohdaten.R{row}:.Z{row}])<0;-1;SUM([Rohdaten.R{row}:.Z{row}]))",
            f"of:=IF(MIN([Rohdaten.AA{row}:.AI{row}])<0;-1;SUM([Rohdaten.AA{row}:.AI{row}]))",
            f"of:=IF(OR([.D{row}]<0;[.F{row}]<0);-1;[.F{row}]-[.D{row}])",
            "of:=[Parameter.$F$8]",
            f"of:=IF([.F{row}]<0;-1;100*[.F{row}]/[.H{row}])",
            f"of:=IF([.F{row}]<0;-1;VLOOKUP([.F{row}];[Parameter.$B$5:.$C$10];2;1))",
        )
        for column, formula in enumerate(formulas, start=4):
            set_formula(ods._cell(summary, row, column), formula, 36 if column == 8 else -1)

    ods._write_package(entries, root, TARGET)


if __name__ == "__main__":
    build()
