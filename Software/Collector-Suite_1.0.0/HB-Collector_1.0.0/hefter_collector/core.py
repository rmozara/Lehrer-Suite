from __future__ import annotations


def parse_rating(form: dict, criterion_ids: list[str]) -> dict[str, int]:
    values: dict[str, int] = {}
    for criterion_id in criterion_ids:
        raw = form.get(f"c_{criterion_id}")
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("Bitte alle Kriterien bewerten.") from exc
        if value not in {1, 2, 3, 4}:
            raise ValueError("Bewertungen müssen zwischen 1 und 4 liegen.")
        values[criterion_id] = value
    return values


def grade_for_percent(percent: float) -> int:
    if percent >= 90:
        return 1
    if percent >= 75:
        return 2
    if percent >= 60:
        return 3
    if percent >= 45:
        return 4
    if percent >= 30:
        return 5
    return 6


def format_percent(percent: float) -> str:
    return f"{percent:.2f}".replace(".", ",")


def rating_difference(
    self_values: dict[str, int],
    peer_values: dict[str, int],
    criterion_ids: list[str],
) -> int:
    return sum(abs(int(self_values[key]) - int(peer_values[key])) for key in criterion_ids)


def difference_level(difference: int) -> str:
    if difference <= 4:
        return "good"
    if difference <= 12:
        return "medium"
    return "bad"

