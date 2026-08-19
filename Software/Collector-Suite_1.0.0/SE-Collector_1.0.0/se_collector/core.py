from __future__ import annotations


def flatten_questions(form: dict) -> list[dict]:
    return [q for section in form["sections"] for q in section["questions"]]


def validate_answers(form: dict, answers: dict[str, int]) -> dict[str, int]:
    questions = flatten_questions(form)
    allowed = {int(item["value"]) for item in form["scale"]}
    expected = {q["id"] for q in questions}
    if set(answers) != expected:
        missing = sorted(expected - set(answers))
        extra = sorted(set(answers) - expected)
        raise ValueError(f"Unvollständige Antworten. Fehlend: {missing}; unbekannt: {extra}")
    normalized = {key: int(value) for key, value in answers.items()}
    invalid = {key: value for key, value in normalized.items() if value not in allowed}
    if invalid:
        raise ValueError(f"Ungültige Antwortwerte: {invalid}")
    return normalized


def grade_for_points(form: dict, total_points: int) -> tuple[str, float]:
    for row in sorted(form["grade_thresholds"], key=lambda x: int(x["min_points"]), reverse=True):
        if total_points >= int(row["min_points"]):
            return str(row["grade_label"]), float(row["grade_value"])
    raise ValueError("Notenschlüssel ist unvollständig.")


def section_totals(form: dict, answers: dict[str, int]) -> dict[str, int]:
    return {
        section["id"]: sum(int(answers[q["id"]]) for q in section["questions"])
        for section in form["sections"]
    }


def evaluate(form: dict, answers: dict[str, int]) -> tuple[dict[str, int], int, str, float, dict[str, int]]:
    normalized = validate_answers(form, answers)
    total = sum(normalized.values())
    grade_label, grade_value = grade_for_points(form, total)
    return normalized, total, grade_label, grade_value, section_totals(form, normalized)
