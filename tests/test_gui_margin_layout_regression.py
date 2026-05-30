from __future__ import annotations

from pathlib import Path
import unittest


class GuiMarginLayoutRegressionTest(unittest.TestCase):
    def test_margin_controls_are_built_on_single_row_in_requested_left_to_right_order(self) -> None:
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        start = source.index('    def _build_margin_rows(self):')
        end = source.index('    # ── プレビュー更新コントロール（セクション外）')
        margin_source = source[start:end]
        self.assertIn("row = self._make_hbox_layout_from_plan(row_plan)", margin_source)
        self.assertNotIn('row1 = self._make_hbox_layout_from_plan(row_plan)', margin_source)
        self.assertNotIn('row2 = self._make_hbox_layout_from_plan(row_plan)', margin_source)
        self.assertIn("margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[0]", margin_source)
        self.assertIn('row.addWidget(self.margin_r_spin)', margin_source)
        self.assertIn("margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[1]", margin_source)
        self.assertIn('row.addWidget(self.margin_l_spin)', margin_source)
        self.assertIn("margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[2]", margin_source)
        self.assertIn('row.addWidget(self.margin_l_spin)', margin_source)
        self.assertIn("margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[3]", margin_source)
        self.assertIn('row.addWidget(self.margin_r_spin)', margin_source)
        self.assertIn('lay.addLayout(row)', margin_source)


if __name__ == '__main__':
    unittest.main()
