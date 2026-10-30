#!/usr/bin/env python3
"""Offline unit tests for metadata and timing structure; does not hit GitHub."""
import unittest
from check_release import check_names, validate_timings


class AssetCheckerTests(unittest.TestCase):
    def test_names(self):
        assets = [{'name': f'{i:03d}.mp3', 'size': 2048} for i in range(1, 115)]
        assets += [{'name': f'timings-{i:03d}.json', 'size': 100} for i in range(1, 115)]
        self.assertEqual(len(check_names(assets)), 228)

    def test_missing(self):
        with self.assertRaises(ValueError):
            check_names([{'name': '001.mp3', 'size': 100}])

    def test_timings(self):
        rows = [{'ayah': i, 'start_time': (i - 1) * 1000, 'end_time': i * 1000} for i in range(1, 8)]
        self.assertEqual(validate_timings(rows, 1, 7), 7)
        rows[3]['ayah'] = 99
        with self.assertRaises(ValueError):
            validate_timings(rows, 1, 7)

    def test_bad_order(self):
        with self.assertRaises(ValueError):
            validate_timings([
                {'ayah': 1, 'start_time': 2000, 'end_time': 3000},
                {'ayah': 2, 'start_time': 1000, 'end_time': 4000},
            ], 2)


if __name__ == '__main__':
    unittest.main()
