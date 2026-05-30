from __future__ import annotations

from pathlib import Path
import unittest


class GuiRubyHideLayoutRegressionTest(unittest.TestCase):
    def test_composition_section_places_compact_ruby_hide_controls_in_first_row(self) -> None:
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        start = source.index('    def _section_composition(self):')
        end = source.index('    def _build_margin_rows(self):')
        image_source = source[start:end]
        self.assertNotIn('ruby_row = self._make_hbox_layout_from_plan()', image_source)
        self.assertIn("self.ruby_hide_check = QCheckBox(str(image_plan.get('ruby_hide_label', 'ルビ消し')))", image_source)
        self.assertIn('row.addWidget(self.ruby_hide_check)', image_source)
        self.assertNotIn('row.addWidget(ruby_hide_label)', image_source)
        self.assertNotIn("self.ruby_hide_check = QCheckBox(str(image_plan.get('ruby_hide_text', 'ルビを表示しない')))", image_source)
        self.assertNotIn("ruby_hide_help_text", image_source)
        self.assertIn("row.addSpacing(self._plan_int_value(image_plan, 'night_mode_spacing', 16))", image_source)
        ruby_idx = image_source.index('row.addWidget(self.ruby_hide_check)')
        night_idx = image_source.index("self.night_check = QCheckBox(str(image_plan.get('night_mode_text', '白黒反転')))")
        self.assertLess(ruby_idx, night_idx)


    def test_ruby_hide_label_color_matches_checkbox_text_styles(self) -> None:
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        self.assertIn('QCheckBox { color: #35506A; spacing: 6px; }', source)
        self.assertIn('QLabel#checkboxTextLabel { color: #35506A; }', source)
        self.assertIn('QCheckBox { color: #A8C8E0; spacing: 6px; }', source)
        self.assertIn('QLabel#checkboxTextLabel { color: #A8C8E0; }', source)


if __name__ == '__main__':
    unittest.main()
