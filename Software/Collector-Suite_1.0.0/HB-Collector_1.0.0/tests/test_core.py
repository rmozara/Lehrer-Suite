import random
import unittest

from hefter_collector.permutation import generate_derangement, swap_subjects, valid_assignment
from hefter_collector.core import (
    difference_level,
    format_percent,
    grade_for_percent,
    parse_rating,
    rating_difference,
)


class PermutationTests(unittest.TestCase):
    def test_derangement_is_bijective_without_self_or_reciprocal_pairs(self):
        ids = list(range(1, 35))
        mapping = generate_derangement(ids, random.Random(42))
        self.assertEqual(set(mapping), set(ids))
        self.assertEqual(set(mapping.values()), set(ids))
        self.assertTrue(valid_assignment(list(mapping), [mapping[key] for key in mapping]))
        for reviewer, subject in mapping.items():
            self.assertNotEqual(reviewer, subject)
            self.assertNotEqual(mapping[subject], reviewer)

    def test_three_students_are_supported(self):
        mapping = generate_derangement([1, 2, 3], random.Random(4))
        self.assertTrue(valid_assignment(list(mapping), [mapping[key] for key in mapping]))

    def test_full_class_respects_bidirectional_exclusions(self):
        ids = list(range(1, 35))
        excluded = {
            frozenset((1, 2)),
            frozenset((3, 17)),
            frozenset((20, 34)),
        }
        mapping = generate_derangement(
            ids,
            random.Random(23),
            excluded_pairs=excluded,
        )
        self.assertTrue(
            valid_assignment(
                list(mapping),
                [mapping[key] for key in mapping],
                excluded,
            )
        )
        self.assertNotEqual(mapping[1], 2)
        self.assertNotEqual(mapping[2], 1)

    def test_impossible_exclusions_are_reported(self):
        with self.assertRaisesRegex(ValueError, "keine vollständige"):
            generate_derangement(
                [1, 2, 3],
                random.Random(1),
                excluded_pairs={frozenset((1, 2))},
            )

    def test_invalid_swap_is_rejected(self):
        mapping = {1: 2, 2: 3, 3: 1}
        with self.assertRaises(ValueError):
            swap_subjects(mapping, 1, 2)

    def test_swap_cannot_create_excluded_pair(self):
        mapping = {1: 2, 2: 3, 3: 4, 4: 1}
        with self.assertRaisesRegex(ValueError, "ausgeschlossene"):
            swap_subjects(
                mapping,
                1,
                2,
                {frozenset((1, 3))},
            )

    def test_percentage_and_grade_format(self):
        self.assertEqual(format_percent(100), "100,00")
        self.assertEqual(format_percent(47.1875), "47,19")
        self.assertEqual(grade_for_percent(47.1875), 4)

    def test_all_grade_boundaries(self):
        cases = [
            (100, 1), (90, 1), (89.99, 2), (75, 2), (74.99, 3),
            (60, 3), (59.99, 4), (45, 4), (44.99, 5),
            (30, 5), (29.99, 6), (0, 6),
        ]
        for percent, expected in cases:
            with self.subTest(percent=percent):
                self.assertEqual(grade_for_percent(percent), expected)

    def test_rating_validation_requires_every_known_criterion(self):
        self.assertEqual(parse_rating({"c_a": "1", "c_b": "4"}, ["a", "b"]), {"a": 1, "b": 4})
        with self.assertRaisesRegex(ValueError, "alle Kriterien"):
            parse_rating({"c_a": "1"}, ["a", "b"])
        with self.assertRaisesRegex(ValueError, "zwischen 1 und 4"):
            parse_rating({"c_a": "5"}, ["a"])

    def test_difference_levels_match_review_list_thresholds(self):
        criterion_ids = ["a", "b", "c", "d"]
        self.assertEqual(rating_difference(
            {"a": 1, "b": 2, "c": 3, "d": 4},
            {"a": 4, "b": 2, "c": 2, "d": 4},
            criterion_ids,
        ), 4)
        self.assertEqual(difference_level(4), "good")
        self.assertEqual(difference_level(5), "medium")
        self.assertEqual(difference_level(12), "medium")
        self.assertEqual(difference_level(13), "bad")
