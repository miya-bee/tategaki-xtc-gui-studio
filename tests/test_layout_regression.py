import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import ImageOps

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec


class LayoutRegressionTests(unittest.TestCase):
    def test_tokenize_vertical_text_preserves_tatechuyoko_and_double_punctuation(self):
        text = '2025年AI!?ABCD'
        self.assertEqual(
            core._tokenize_vertical_text(text),
            ['2025', '年', 'AI', '!?', 'A', 'B', 'C', 'D'],
        )

    def test_tokenize_vertical_text_keeps_three_ascii_chars_together(self):
        self.assertEqual(core._tokenize_vertical_text('ver2'), ['v', 'e', 'r', '2'])
        self.assertEqual(core._tokenize_vertical_text('123'), ['123'])
        self.assertEqual(core._tokenize_vertical_text('ABC'), ['ABC'])

    def test_choose_vertical_layout_action_advances_before_line_end_forbidden(self):
        action = core._choose_vertical_layout_action(
            tokens=['（'],
            idx=0,
            curr_y=70,
            margin_t=10,
            height=100,
            margin_b=10,
            font_size=20,
            kinsoku_mode='standard',
        )
        self.assertEqual(action, 'advance')

    def test_choose_vertical_layout_action_hangs_punctuation_pair(self):
        action = core._choose_vertical_layout_action(
            tokens=['あ', '、'],
            idx=0,
            curr_y=70,
            margin_t=10,
            height=105,
            margin_b=10,
            font_size=20,
            kinsoku_mode='standard',
        )
        self.assertEqual(action, 'hang_pair')

    def test_choose_vertical_layout_action_advances_before_line_head_forbidden(self):
        action = core._choose_vertical_layout_action(
            tokens=['あ', '」'],
            idx=0,
            curr_y=70,
            margin_t=10,
            height=100,
            margin_b=10,
            font_size=20,
            kinsoku_mode='standard',
        )
        self.assertEqual(action, 'advance')

    def test_choose_vertical_layout_action_protects_continuous_punctuation_run(self):
        action = core._choose_vertical_layout_action(
            tokens=['！', '！', '！'],
            idx=0,
            curr_y=40,
            margin_t=10,
            height=100,
            margin_b=10,
            font_size=20,
            kinsoku_mode='standard',
        )
        self.assertEqual(action, 'advance')

    def test_choose_vertical_layout_action_protects_closing_bracket_group(self):
        action = core._choose_vertical_layout_action(
            tokens=['」', '』', '。'],
            idx=0,
            curr_y=40,
            margin_t=10,
            height=100,
            margin_b=10,
            font_size=20,
            kinsoku_mode='standard',
        )
        self.assertEqual(action, 'advance')

    def test_simple_mode_does_not_apply_group_protection(self):
        action = core._choose_vertical_layout_action(
            tokens=['」', '』', '。'],
            idx=0,
            curr_y=40,
            margin_t=10,
            height=100,
            margin_b=10,
            font_size=20,
            kinsoku_mode='simple',
        )
        self.assertEqual(action, 'draw')

    def test_blank_separated_paragraph_after_pagebreak_consumes_remaining_blank_columns(self):
        font_path = resolve_test_font_path()
        args = core.ConversionArgs(
            width=120,
            height=80,
            font_size=20,
            ruby_size=10,
            margin_l=46,
            margin_r=10,
            margin_t=10,
            margin_b=10,
            line_spacing=30,
            output_format='xtc',
        )
        blocks = [
            {'kind': 'paragraph', 'runs': [{'text': 'AAAA', 'bold': False}]},
            {'kind': 'blank'},
            {'kind': 'paragraph', 'runs': [{'text': 'B', 'bold': False}]},
        ]
        captured_pages = []

        def fake_page_image_to_xt_bytes(image, width, height, page_args):
            captured_pages.append(image.copy())
            return b'page'

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'layout.xtc'
            with mock.patch.object(core, 'page_image_to_xt_bytes', side_effect=fake_page_image_to_xt_bytes):
                result = core._render_text_blocks_to_xtc(blocks, Path('sample.txt'), font_path, args, output_path=out_path)
            self.assertEqual(result, out_path)

        self.assertGreaterEqual(len(captured_pages), 2)
        second_bbox = ImageOps.invert(captured_pages[1]).getbbox()
        self.assertIsNotNone(second_bbox)
        self.assertLess(second_bbox[0], 60)


if __name__ == '__main__':
    unittest.main()
