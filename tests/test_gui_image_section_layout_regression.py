from __future__ import annotations

from pathlib import Path
import unittest


class GuiImageSectionLayoutRegressionTest(unittest.TestCase):
    def test_ruby_hide_checkbox_uses_same_checkbox_plus_text_order_as_other_toggles(self) -> None:
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        start = source.index('    def _section_composition(self):')
        end = source.index('    def _build_margin_rows(self):')
        section_source = source[start:end]
        self.assertIn("self.ruby_hide_check = QCheckBox(str(image_plan.get('ruby_hide_label', 'ルビ消し')))", section_source)
        self.assertNotIn("ruby_hide_label = QLabel", section_source)

    def test_image_help_text_fallback_uses_line_breaks_between_items(self) -> None:
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        self.assertIn('ルビ消し: チェックした場合だけ、親文字は残したままルビを表示しない変換モードにします。\\n白黒反転', source)
        self.assertIn('\\nディザリング:', source)
        self.assertIn('\\nしきい値:', source)

    def test_inline_help_dialog_uses_plain_text_format(self) -> None:
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        start = source.index('    def _show_inline_help(self, button: QPushButton):')
        end = source.index('    def _build_flow_guide(self) -> QFrame:')
        helper_source = source[start:end]
        self.assertIn('msg.setTextFormat(Qt.PlainText)', helper_source)


if __name__ == '__main__':
    unittest.main()
