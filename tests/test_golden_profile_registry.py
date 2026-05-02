import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.golden_case_registry import (
    CASE_SPECS,
    THRESHOLD_PROFILES,
    expected_profile_prefix_for_case,
    resolve_case_thresholds,
    validate_threshold_profile_registry,
)


class GoldenProfileRegistryTests(unittest.TestCase):
    def test_every_case_resolves_thresholds(self):
        for name, spec in CASE_SPECS.items():
            with self.subTest(case=name):
                thresholds = resolve_case_thresholds(spec)
                self.assertIn('threshold_ratio', thresholds)
                self.assertIn('threshold_mean', thresholds)

    def test_registry_has_no_missing_or_unused_profiles(self):
        result = validate_threshold_profile_registry(CASE_SPECS, THRESHOLD_PROFILES)
        self.assertEqual(result['missing_profile_cases'], [])
        self.assertEqual(result['unused_profiles'], [])

    def test_case_family_matches_profile_family(self):
        result = validate_threshold_profile_registry(CASE_SPECS, THRESHOLD_PROFILES)
        self.assertEqual(result['family_mismatch_cases'], [])

    def test_expected_profile_prefix_for_case(self):
        self.assertEqual(expected_profile_prefix_for_case('glyph_ichi'), 'glyph_')
        self.assertEqual(expected_profile_prefix_for_case('tatechuyoko_2025'), 'tatechuyoko_')
        self.assertEqual(expected_profile_prefix_for_case('page_heading_spacing'), 'page_')
        self.assertEqual(expected_profile_prefix_for_case('misc_custom_case'), '')


if __name__ == '__main__':
    unittest.main()
