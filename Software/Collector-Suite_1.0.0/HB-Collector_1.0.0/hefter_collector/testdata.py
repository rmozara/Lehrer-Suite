from __future__ import annotations


def sample_students(count: int = 6, class_id: str = "8a") -> list[dict]:
    if count < 1:
        raise ValueError("Die Testklasse muss mindestens eine Person enthalten.")
    return [
        {
            "class_id": class_id,
            "list_position": number,
            "student_code": f"{class_id}-{number:02d}",
            "name": f"Testperson {number:02d}",
        }
        for number in range(1, count + 1)
    ]


def self_values(person_index: int, criterion_ids: list[str]) -> dict[str, int]:
    return {
        criterion_id: 2 + ((person_index + criterion_index) % 3)
        for criterion_index, criterion_id in enumerate(criterion_ids)
    }


def peer_values(
    person_index: int,
    criterion_ids: list[str],
    source: dict[str, int],
) -> dict[str, int]:
    values = dict(source)
    for criterion_index in range(person_index % 4):
        criterion_id = criterion_ids[(person_index + criterion_index) % len(criterion_ids)]
        values[criterion_id] = 3 if int(values[criterion_id]) != 3 else 2
    return values

