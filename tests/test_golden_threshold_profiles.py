import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.golden_case_registry import CASE_SPECS, THRESHOLD_PROFILES, resolve_case_thresholds
from tests.golden_regression_tools import compare_case


class GoldenThresholdProfileTests(unittest.TestCase):
    def test_case_profile_resolves_expected_thresholds(self):
        thresholds = resolve_case_thresholds(CASE_SPECS['glyph_ichi'])
        self.assertEqual(thresholds, THRESHOLD_PROFILES['glyph_strict'])

    def test_device_layout_cases_share_device_profile(self):
        x4 = resolve_case_thresholds(CASE_SPECS['page_x4_profile_layout'])
        x3 = resolve_case_thresholds(CASE_SPECS['page_x3_profile_layout'])
        self.assertEqual(x4, THRESHOLD_PROFILES['page_device_profile'])
        self.assertEqual(x3, THRESHOLD_PROFILES['page_device_profile'])

    def test_compare_case_exposes_effective_thresholds(self):
        result = compare_case('page_heading_spacing')
        self.assertIn('thresholds', result)
        self.assertEqual(result['thresholds'], THRESHOLD_PROFILES['page_heading_standard'])




    def test_unknown_threshold_profile_raises_explicit_error(self):
        with self.assertRaisesRegex(KeyError, "Unknown threshold profile"):
            resolve_case_thresholds({'threshold_profile': 'missing_profile'})


if __name__ == '__main__':
    unittest.main()
