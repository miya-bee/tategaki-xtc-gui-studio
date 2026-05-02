"""ゴールデン画像との比較で、見た目の回帰を検出するテスト。"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.golden_regression_tools import (
    CASE_SPECS,
    save_golden,
    should_update_goldens,
    strip_update_flag,
    summarize_result,
    compare_case,
)

# unittest 実行時に未知オプション扱いされないよう、モジュール読込時に除去する。
sys.argv[:] = strip_update_flag()


class ImageGoldenRegressionTests(unittest.TestCase):
    def _assert_matches_golden(self, name: str) -> None:
        result = compare_case(name)
        if should_update_goldens():
            if result['stale']:
                path = save_golden(name, result['actual'])
                print(f'updated golden: {path}')
            return

        self.assertFalse(
            result['stale'],
            (
                summarize_result(result)
                + '。ゴールデン画像を更新するには '
                + '.venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --update '
                + 'または TATEGAKI_UPDATE_GOLDEN=1 を付けてテストを実行してください。'
            ),
        )
        self.assertIn(name, CASE_SPECS)

    def test_renderings_match_golden_images(self):
        for name in CASE_SPECS:
            with self.subTest(case=name):
                self._assert_matches_golden(name)


if __name__ == '__main__':
    unittest.main()
