import unittest

from hefter_collector.workflow import PHASES, WorkflowError, validate_transition


class PhaseMachineTests(unittest.TestCase):
    def test_complete_normal_path(self):
        path = (
            "setup", "self", "self_closed", "peer", "peer_closed",
            "teacher", "teacher_closed", "closed",
        )
        for current, target in zip(path, path[1:]):
            validate_transition(
                current,
                target,
                has_complete_assignment=True,
                teacher_review_opened=True,
                teacher_ratings_complete=True,
            )

    def test_every_unlisted_transition_is_rejected(self):
        allowed = {
            ("setup", "self"), ("self", "self_closed"),
            ("self_closed", "peer"), ("peer", "peer_closed"),
            ("peer_closed", "teacher"), ("teacher", "teacher_closed"),
            ("teacher_closed", "teacher"), ("teacher_closed", "closed"),
        }
        for current in PHASES:
            for target in PHASES:
                if current == target or (current, target) in allowed:
                    continue
                with self.subTest(current=current, target=target):
                    with self.assertRaises(WorkflowError):
                        validate_transition(
                            current,
                            target,
                            has_complete_assignment=True,
                            teacher_review_opened=True,
                            teacher_ratings_complete=True,
                        )

    def test_peer_phase_requires_complete_assignment(self):
        with self.assertRaisesRegex(WorkflowError, "Zuordnung vollständig"):
            validate_transition("self_closed", "peer")

    def test_teacher_phase_must_have_been_opened_before_completion(self):
        with self.assertRaisesRegex(WorkflowError, "mindestens einmal geöffnet"):
            validate_transition("teacher", "teacher_closed")

    def test_teacher_phase_requires_complete_teacher_ratings(self):
        with self.assertRaisesRegex(WorkflowError, "alle aktiven Personen"):
            validate_transition(
                "teacher",
                "teacher_closed",
                teacher_review_opened=True,
                teacher_ratings_complete=False,
            )
        validate_transition(
            "teacher",
            "teacher_closed",
            teacher_review_opened=True,
            teacher_ratings_complete=True,
        )

    def test_teacher_review_can_be_reopened_but_final_close_cannot(self):
        validate_transition("teacher_closed", "teacher", teacher_review_opened=True)
        validate_transition("teacher_closed", "closed", teacher_review_opened=True)
        with self.assertRaises(WorkflowError):
            validate_transition("closed", "teacher", teacher_review_opened=True)
