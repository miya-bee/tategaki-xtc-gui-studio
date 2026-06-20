from __future__ import annotations

from pathlib import Path
import unittest

import tategakiXTC_gui_layouts as gui_layouts


class GuiHelpTextLineBreakRegressionTest(unittest.TestCase):
    def test_layout_owned_multi_item_help_texts_use_line_breaks(self) -> None:
        display_plan = gui_layouts.build_display_section_plan()
        self.assertIn('ファイル読込時:', display_plan['preview_update_help_text'])
        self.assertIn('\n設定変更後:', display_plan['preview_update_help_text'])
        self.assertIn('\n更新対象:', display_plan['preview_update_help_text'])

        image_plan = gui_layouts.build_image_section_plan()
        self.assertIn('ルビ消し:', image_plan['help_text'])
        self.assertIn('\n白黒反転:', image_plan['help_text'])
        self.assertIn('\nディザリング:', image_plan['help_text'])
        self.assertIn('\nしきい値:', image_plan['help_text'])

        behavior_plan = gui_layouts.build_behavior_section_plan()
        self.assertIn('保存先に同名', behavior_plan['output_conflict_help_text'])
        self.assertIn('\n自動連番:', behavior_plan['output_conflict_help_text'])
        self.assertIn('\n上書き:', behavior_plan['output_conflict_help_text'])
        self.assertIn('\nエラー:', behavior_plan['output_conflict_help_text'])

    def test_inline_multi_item_help_literals_use_line_breaks(self) -> None:
        # The section-construction help literals moved into the settings-sections
        # helper module; the startup flow guide stays in the entry module.
        source = (
            Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
            + Path('tategakiXTC_gui_studio_settings_sections_helpers.py').read_text(encoding='utf-8')
        )
        expected_fragments = (
            'XTC: 2 階調（白黒）で保存します。\\nXTCH:',
            '機種: 選ぶと解像度が自動設定されます。\\nCustom:',
            'オフ: 禁則処理を行わず機械的に流し込みます。\\n簡易:',
            '対象: ぶら下がり句読点のみです。\\n下補正強/弱:',
            '対象: 文中すべての漢数字「一」です。\\n下補正強/弱:',
            '対象: 閉じ鍵括弧（」/﹂）と二重閉じ鍵括弧（』/﹄）のみです。\\n下補正強/弱:',
            '対象: 波線系記号（～/〜/〰/~ など）の描画方式です。\\n回転グリフ:',
            '対象: 波線系記号の縦位置だけを補正します。\\n標準:',
            '1. ファイルを開く\\n2. プリセットを選ぶ',
        )
        for fragment in expected_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)


if __name__ == '__main__':
    unittest.main()
