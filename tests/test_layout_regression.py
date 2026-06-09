import struct
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
            ['2025', '年', 'A', 'I', '!?', 'A', 'B', 'C', 'D'],
        )

    def test_tokenize_vertical_text_keeps_three_ascii_chars_together(self):
        self.assertEqual(core._tokenize_vertical_text('ver2'), ['v', 'e', 'r', '2'])
        self.assertEqual(core._tokenize_vertical_text('123'), ['123'])
        self.assertEqual(core._tokenize_vertical_text('ABC'), ['A', 'B', 'C'])

    def test_tokenize_vertical_text_honors_tatechuyoko_digit_mode(self):
        text = '12年123年2025年AI'
        self.assertEqual(core._tokenize_vertical_text(text, '4'), ['12', '年', '123', '年', '2025', '年', 'A', 'I'])
        self.assertEqual(core._tokenize_vertical_text(text, '3'), ['12', '年', '123', '年', '2', '0', '2', '5', '年', 'A', 'I'])
        self.assertEqual(core._tokenize_vertical_text(text, '2'), ['12', '年', '1', '2', '3', '年', '2', '0', '2', '5', '年', 'A', 'I'])
        self.assertEqual(core._tokenize_vertical_text(text, 'none'), ['1', '2', '年', '1', '2', '3', '年', '2', '0', '2', '5', '年', 'A', 'I'])

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

    def test_leading_line_head_forbidden_chars_scans_only_the_forbidden_prefix(self):
        import tategakiXTC_gui_core_renderer as renderer
        self.assertEqual(renderer._leading_line_head_forbidden_chars('」』だね'), ('」', '』'))
        self.assertEqual(renderer._leading_line_head_forbidden_chars('。」あ'), ('。', '」'))
        self.assertEqual(renderer._leading_line_head_forbidden_chars('本文'), ())
        self.assertEqual(renderer._leading_line_head_forbidden_chars(''), ())
        self.assertEqual(len(renderer._leading_line_head_forbidden_chars('」' * 20)), 8)

    def test_line_head_forbidden_token_is_not_advanced_to_protect_a_short_tail(self):
        # ``」`` exactly fills the last cell of a ``「あ」`` group.  The short-tail
        # orphan guard must not advance it (that would put ``」`` on the next
        # column head).  The body character before a tail is still advanced.
        tokens = ['「', 'あ', '」', 'あ', '、']
        self.assertEqual(
            core._choose_vertical_layout_action(
                tokens, 2, 70, 10, 105, 10, 20, kinsoku_mode='standard'),
            'draw',
        )
        hints = core._build_vertical_layout_hints(tuple(tokens))
        self.assertEqual(
            core._choose_vertical_layout_action_with_hints(
                hints, 2, 1, True, kinsoku_mode='standard'),
            'draw',
        )
        # Regression guard: a real body character before a compact punctuation
        # tail is still pulled forward.
        self.assertEqual(
            core._choose_vertical_layout_action(
                ['す', 'か', '？', '」', '、', '「'], 0, 70, 10, 105, 10, 20, kinsoku_mode='standard'),
            'advance',
        )

    def test_quoted_clause_among_punctuation_never_starts_a_column_with_a_bracket(self):
        args = dict(
            width=300, height=760, font_size=22, ruby_size=11,
            margin_l=12, margin_r=12, margin_t=14, margin_b=14,
            line_spacing=26, output_format='xtc', kinsoku_mode='standard',
        )
        for n in range(0, 40):
            text = 'あ' * n + 'あ、あ。あ「あ」あ、あ。' * 3
            blocks = [{'kind': 'paragraph', 'runs': [{'text': text}]}]
            heads = self._closing_brackets_at_column_head(blocks, args)
            self.assertEqual(heads, [], msg=f'closing bracket at column head: n={n} -> {heads}')

    def _closing_brackets_at_column_head(self, blocks, args):
        """Render blocks and return any closing-bracket glyph drawn at a column top."""
        import tategakiXTC_gui_core_renderer as renderer
        from tests.image_golden_cases import render_page_blocks_case
        closing = core.CLOSING_BRACKET_CHARS
        margin_t = args['margin_t']
        captured = []
        original = renderer.draw_char_tate

        def spy(draw, token, pos, font, f_size, **kwargs):
            if token and token[0] in closing and pos[1] == margin_t:
                captured.append((token, pos))
            return original(draw, token, pos, font, f_size, **kwargs)

        with mock.patch.object(renderer, 'draw_char_tate', side_effect=spy):
            render_page_blocks_case(args, blocks, page_mode='strip')
        return captured

    def test_closing_bracket_run_after_ruby_run_never_starts_a_column(self):
        # The closing brackets live in a separate (plain) run, right after a ruby
        # word.  Sweeping the leading offset forces the bracket run to land at
        # every column boundary; none of them may start a wrapped column.
        args = dict(
            width=260, height=190, font_size=24, ruby_size=12,
            margin_l=12, margin_r=12, margin_t=12, margin_b=12,
            line_spacing=28, output_format='xtc',
        )
        for boundary in ('ruby', 'bold', 'plain'):
            for tail in ('」', '」』', '）」', '。」』'):
                for n in range(0, 16):
                    first = {'text': 'あ' * n + ('会話' if boundary == 'ruby' else '本文の会話')}
                    if boundary == 'ruby':
                        first['ruby'] = 'かいわ'
                    elif boundary == 'bold':
                        first['bold'] = True
                    blocks = [{'kind': 'paragraph', 'runs': [first, {'text': tail + 'だね。'}]}]
                    heads = self._closing_brackets_at_column_head(blocks, args)
                    self.assertEqual(
                        heads, [],
                        msg=f'closing bracket at column head: boundary={boundary} tail={tail} n={n} -> {heads}',
                    )

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
            payload = b'page'
            return struct.pack('<4sHHBBI8s', b'XTG\x00', width, height, 0, 0, len(payload), b'\x00' * 8) + payload

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
