import unittest

from hefter_collector.testdata import peer_values, sample_students, self_values


class TestDataTests(unittest.TestCase):
    def test_full_class_is_reproducible(self):
        first = sample_students(34, "9b")
        second = sample_students(34, "9b")
        self.assertEqual(first, second)
        self.assertEqual(first[0]["student_code"], "9b-01")
        self.assertEqual(first[-1]["student_code"], "9b-34")

    def test_peer_values_are_mixed_but_in_range(self):
        ids = [f"c{i}" for i in range(8)]
        differences = []
        for index in range(12):
            own = self_values(index, ids)
            peer = peer_values(index, ids, own)
            self.assertTrue(all(value in {1, 2, 3, 4} for value in peer.values()))
            differences.append(sum(own[key] != peer[key] for key in ids))
        self.assertEqual(set(differences), {0, 1, 2, 3})

