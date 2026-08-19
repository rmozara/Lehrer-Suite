from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from se_collector.config import ODS_TEMPLATE_FILE, ROOT, SE1_TEMPLATE_FILE
from se_collector.ods_file import (
    _cell,
    _read_package,
    _set_value,
    _table,
    _write_package,
    read_roster,
    update_raw_data,
)
from se_collector.se_output import generate_pdf


def main() -> None:
    form = json.loads((ROOT / "config" / "se1.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="se1-lokaltest-") as temporary:
        temp = Path(temporary)
        ods = temp / "Selbstevaluation.ods"
        ods.write_bytes(ODS_TEMPLATE_FILE.read_bytes())
        entries, root = _read_package(ods)
        roster_table = _table(root, "Namensliste")
        _set_value(_cell(roster_table, 5, 3), "Anna Beispiel")
        _set_value(_cell(roster_table, 5, 4), "8a-01")
        _write_package(entries, root, ods)
        student = read_roster(ods).students[0]
        answers = {f"q{index:02d}": (index - 1) % 4 for index in range(1, 23)}
        rows = [{
            "Nr.": student["list_position"],
            "Name": student["name"],
            "Schüler-ID": student["student_id"],
            "Zeitraum": "LOKALTEST",
            "answers": answers,
            "raw": {"submitted_at": "2026-07-23T10:15:00+02:00"},
        }]
        update_raw_data(
            ods,
            {"period_id": "LOKALTEST", "started_at": "2026-07-23T09:00:00+02:00"},
            rows,
            copy.deepcopy(form),
            temp / "backups",
        )
        output = ROOT / "Testausgabe_Evaluation_SE1.pdf"
        count = generate_pdf(ods, SE1_TEMPLATE_FILE, output, copy.deepcopy(form))
    print(f"Lokaler Test erfolgreich: {output} ({count} Seite)")


if __name__ == "__main__":
    main()
