from __future__ import annotations

import random


def _excluded(reviewer: int, subject: int, excluded_pairs) -> bool:
    return frozenset((reviewer, subject)) in excluded_pairs


def valid_assignment(
    reviewers: list[int],
    subjects: list[int],
    excluded_pairs=(),
) -> bool:
    if len(reviewers) != len(subjects) or set(reviewers) != set(subjects):
        return False
    excluded = {frozenset(pair) for pair in excluded_pairs}
    mapping = dict(zip(reviewers, subjects))
    for reviewer, subject in mapping.items():
        if reviewer == subject:
            return False
        if mapping.get(subject) == reviewer:
            return False
        if _excluded(reviewer, subject, excluded):
            return False
    return True


def generate_derangement(
    student_ids: list[int],
    rng: random.Random | None = None,
    excluded_pairs=(),
) -> dict[int, int]:
    """Create a bijection without self, reciprocal or excluded pairs."""
    if len(student_ids) < 3:
        raise ValueError("Für eine Peerzuordnung werden mindestens drei Personen benötigt.")
    rng = rng or random.SystemRandom()
    reviewers = list(student_ids)
    excluded = {frozenset(pair) for pair in excluded_pairs}
    for _ in range(5000):
        subjects = list(student_ids)
        rng.shuffle(subjects)
        if valid_assignment(reviewers, subjects, excluded):
            return dict(zip(reviewers, subjects))

    # Exact fallback: a constrained backtracking search avoids reporting a
    # solvable exclusion list as impossible merely because random attempts
    # happened to miss it.
    mapping: dict[int, int] = {}
    unused = set(student_ids)

    def candidates(reviewer: int) -> list[int]:
        result = [
            subject
            for subject in unused
            if subject != reviewer
            and not _excluded(reviewer, subject, excluded)
            and mapping.get(subject) != reviewer
        ]
        rng.shuffle(result)
        return result

    def solve() -> bool:
        if len(mapping) == len(reviewers):
            return True
        remaining = [reviewer for reviewer in reviewers if reviewer not in mapping]
        reviewer = min(remaining, key=lambda item: len(candidates(item)))
        for subject in candidates(reviewer):
            mapping[reviewer] = subject
            unused.remove(subject)
            if all(candidates(other) for other in remaining if other != reviewer) and solve():
                return True
            unused.add(subject)
            del mapping[reviewer]
        return False

    if solve() and valid_assignment(
        reviewers,
        [mapping[reviewer] for reviewer in reviewers],
        excluded,
    ):
        return mapping
    raise ValueError(
        "Mit diesen Ausschlüssen ist keine vollständige Peerzuordnung möglich."
    )


def swap_subjects(
    mapping: dict[int, int],
    reviewer_a: int,
    reviewer_b: int,
    excluded_pairs=(),
) -> dict[int, int]:
    candidate = dict(mapping)
    candidate[reviewer_a], candidate[reviewer_b] = candidate[reviewer_b], candidate[reviewer_a]
    if not valid_assignment(
        list(candidate),
        [candidate[key] for key in candidate],
        excluded_pairs,
    ):
        raise ValueError(
            "Dieser Tausch würde eine Selbst-, gegenseitige oder ausgeschlossene "
            "Bewertung erzeugen."
        )
    return candidate
