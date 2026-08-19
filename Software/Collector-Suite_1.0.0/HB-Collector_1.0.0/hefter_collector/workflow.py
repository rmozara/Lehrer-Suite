from __future__ import annotations


PHASES = (
    "setup",
    "self",
    "self_closed",
    "peer",
    "peer_closed",
    "teacher",
    "teacher_closed",
    "closed",
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "setup": frozenset({"self"}),
    "self": frozenset({"self_closed"}),
    "self_closed": frozenset({"peer"}),
    "peer": frozenset({"peer_closed"}),
    "peer_closed": frozenset({"teacher"}),
    "teacher": frozenset({"teacher_closed"}),
    "teacher_closed": frozenset({"teacher", "closed"}),
    "closed": frozenset(),
}


class WorkflowError(ValueError):
    pass


def validate_transition(
    current: str,
    target: str,
    *,
    has_complete_assignment: bool = False,
    teacher_review_opened: bool = False,
    teacher_ratings_complete: bool = False,
) -> None:
    if current not in ALLOWED_TRANSITIONS or target not in ALLOWED_TRANSITIONS:
        raise WorkflowError("Unbekannter Bewertungszustand.")
    if target == current:
        return
    if target not in ALLOWED_TRANSITIONS[current]:
        raise WorkflowError(f"Von {current} kann nicht zu {target} gewechselt werden.")
    if target == "peer" and not has_complete_assignment:
        raise WorkflowError("Vor Beginn der Peerbewertung muss die Zuordnung vollständig sein.")
    if target == "teacher_closed" and not teacher_review_opened:
        raise WorkflowError("Die Lehrerprüfung muss vor ihrem Abschluss mindestens einmal geöffnet werden.")
    if target == "teacher_closed" and not teacher_ratings_complete:
        raise WorkflowError("Die Lehrerbewertung muss für alle aktiven Personen vollständig gespeichert sein.")
