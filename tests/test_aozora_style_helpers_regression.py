import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class AozoraStyleHelperRegressionTests(unittest.TestCase):
    def test_apply_emphasis_marks_recent_runs_and_splits_boundary_run(self):
        runs = [
            {'text': '青空', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
            {'text': '文庫テスト', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
        ]
        applied = core._apply_emphasis_to_recent_runs(runs, 'テスト', 'sesame')
        self.assertTrue(applied)
        self.assertEqual([run['text'] for run in runs], ['青空文庫', 'テスト'])
        self.assertEqual(runs[-1]['emphasis'], 'sesame')
        self.assertEqual(runs[0]['emphasis'], '')

    def test_apply_emphasis_rejects_partial_split_when_ruby_exists(self):
        runs = [
            {'text': '本文テスト', 'ruby': 'ほんぶん', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
        ]
        applied = core._apply_emphasis_to_recent_runs(runs, 'テスト', 'circle')
        self.assertFalse(applied)
        self.assertEqual(runs[0]['emphasis'], '')

    def test_apply_side_line_marks_recent_runs_and_splits_boundary_run(self):
        runs = [
            {'text': '傍線', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
            {'text': '対象文字列', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
        ]
        applied = core._apply_side_line_to_recent_runs(runs, '文字列', 'double')
        self.assertTrue(applied)
        self.assertEqual([run['text'] for run in runs], ['傍線対象', '文字列'])
        self.assertEqual(runs[-1]['side_line'], 'double')
        self.assertEqual(runs[0]['side_line'], '')


if __name__ == '__main__':
    unittest.main()
