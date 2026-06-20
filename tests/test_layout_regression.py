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

    def test_latin_orientation_split_is_inert_for_vertical_mode(self):
        self.assertEqual(
            core._split_latin_orientation_runs('これは TategakiXTC です。', 'vertical'),
            (('text', 'これは TategakiXTC です。'),),
        )
        self.assertEqual(core._normalize_latin_orientation_mode('bad-value'), 'vertical')

    def test_latin_orientation_split_detects_short_ascii_words(self):
        self.assertEqual(
            core._split_latin_orientation_runs('これは TategakiXTC GUI Studio です。', 'horizontal'),
            (
                ('text', 'これは '),
                ('latin_horizontal', 'TategakiXTC GUI Studio'),
                ('text', ' です。'),
            ),
        )

    def test_latin_orientation_split_keeps_latin_punctuation_but_not_japanese_punctuation(self):
        self.assertEqual(
            core._split_latin_orientation_runs('HTML, GitHub. HTML、', 'horizontal'),
            (
                ('latin_horizontal', 'HTML, GitHub.'),
                ('text', ' '),
                ('latin_horizontal', 'HTML'),
                ('text', '、'),
            ),
        )
        self.assertEqual(
            core._split_latin_orientation_runs('「HTML.」と"GUI."', 'horizontal'),
            (('text', '「'), ('latin_horizontal', 'HTML.'), ('text', '」と'), ('latin_horizontal', '"GUI."')),
        )

    def test_latin_orientation_split_preserves_digit_only_runs_for_existing_digit_layout(self):
        self.assertEqual(
            core._split_latin_orientation_runs('2026年 X4 v1.5.0 Python3 3.10', 'horizontal'),
            (
                ('text', '2026年 '),
                ('latin_horizontal', 'X4 v1.5.0 Python3'),
                ('text', ' 3.10'),
            ),
        )

    def test_latin_orientation_split_falls_back_for_long_non_url_words(self):
        self.assertEqual(
            core._split_latin_orientation_runs('Supercalifragilisticexpialidocious', 'horizontal'),
            (('text', 'Supercalifragilisticexpialidocious'),),
        )

    def test_latin_orientation_split_detects_url_like_runs(self):
        self.assertEqual(
            core._split_latin_orientation_runs('https://example.com を見る', 'horizontal'),
            (('latin_horizontal', 'https://example.com'), ('text', ' を見る')),
        )
        self.assertEqual(
            core._split_latin_orientation_runs('参照 www.example.com/path?x=1&y=2 です', 'horizontal'),
            (('text', '参照 '), ('latin_horizontal', 'www.example.com/path?x=1&y=2'), ('text', ' です')),
        )
        self.assertEqual(
            core._split_latin_orientation_runs('example.com/foo_bar#top', 'horizontal'),
            (('latin_horizontal', 'example.com/foo_bar#top'),),
        )

    def test_latin_orientation_split_rejects_incomplete_url_prefixes(self):
        for text in ('https://', 'http://', 'www.'):
            with self.subTest(text=text):
                self.assertEqual(
                    core._split_latin_orientation_runs(text, 'horizontal'),
                    (('text', text),),
                )

        self.assertEqual(
            core._split_latin_orientation_runs('参照 https:// です', 'horizontal'),
            (('text', '参照 https:// です'),),
        )

    def test_latin_horizontal_url_wraps_at_url_delimiters(self):
        font_value = resolve_test_font_path()
        font = core.load_truetype_font(font_value, 20)
        long_url = 'https://example.com/very/long/path/to/resource_name?alpha=1&beta=2#section'
        chunks = core._split_latin_horizontal_text_for_column(
            long_url,
            font,
            20,
            160,
        )
        self.assertGreater(len(chunks), 1)
        self.assertEqual(''.join(chunks), long_url)
        for chunk in chunks:
            self.assertTrue(core._is_horizontal_latin_run_candidate(chunk))

    def test_latin_orientation_split_detects_short_english_phrase(self):
        self.assertEqual(
            core._split_latin_orientation_runs("Pity's akin to love.", 'horizontal'),
            (("latin_horizontal", "Pity's akin to love."),),
        )

    def test_latin_orientation_split_detects_kusamakura_verse_lines(self):
        self.assertEqual(
            core._split_latin_orientation_runs("Sadder than is the moon’s lost light,", 'horizontal'),
            (("latin_horizontal", "Sadder than is the moon’s lost light,"),),
        )
        self.assertEqual(
            core._split_latin_orientation_runs("The shutting of thy fair face from my sight.*", 'horizontal'),
            (("latin_horizontal", "The shutting of thy fair face from my sight.*"),),
        )
        self.assertEqual(
            core._split_latin_orientation_runs("Our sweetest songs are those that tell of saddest thought", 'horizontal'),
            (("latin_horizontal", "Our sweetest songs are those that tell of saddest thought"),),
        )

    def test_latin_orientation_split_does_not_use_fixed_phrase_length_limit(self):
        long_line = (
            "Our sweetest songs are those that tell of saddest thought and continue "
            "with another English phrase beyond the old fixed threshold"
        )
        self.assertEqual(
            core._split_latin_orientation_runs(long_line, 'horizontal'),
            (("latin_horizontal", long_line),),
        )

    def test_latin_horizontal_long_line_wraps_to_column_fitting_chunks(self):
        font_value = resolve_test_font_path()
        font = core.load_truetype_font(font_value, 20)
        long_line = (
            "Our sweetest songs are those that tell of saddest thought and continue "
            "with another English phrase beyond one vertical column"
        )
        chunks = core._split_latin_horizontal_text_for_column(
            long_line,
            font,
            20,
            160,
        )
        self.assertGreater(len(chunks), 1)
        self.assertEqual(' '.join(chunks), long_line)
        for chunk in chunks:
            self.assertTrue(core._is_horizontal_latin_run_candidate(chunk))

    def test_latin_horizontal_mode_changes_plain_latin_rendering(self):
        font_value = resolve_test_font_path()
        blocks = [{
            'indent': False,
            'blank_before': 0,
            'runs': [{'text': "草枕 Pity's akin to love. 余韻", 'ruby': '', 'bold': False}],
        }]
        base_args = dict(width=240, height=320, font_size=22, ruby_size=10, line_spacing=34, margin_t=12, margin_b=12, margin_r=12, margin_l=12, output_format='xtc')
        vertical_args = core.ConversionArgs(**base_args, latin_orientation_mode='vertical')
        horizontal_args = core.ConversionArgs(**base_args, latin_orientation_mode='horizontal')
        vertical_img = core._render_text_blocks_to_images(blocks, font_value, vertical_args, max_output_pages=1)[0]
        horizontal_img = core._render_text_blocks_to_images(blocks, font_value, horizontal_args, max_output_pages=1)[0]
        self.assertNotEqual(vertical_img.tobytes(), horizontal_img.tobytes())


    def test_latin_horizontal_mode_changes_kusamakura_verse_rendering(self):
        font_value = resolve_test_font_path()
        blocks = [{
            'indent': False,
            'blank_before': 0,
            'runs': [{'text': "草枕 Our sweetest songs are those that tell of saddest thought 余韻", 'ruby': '', 'bold': False}],
        }]
        base_args = dict(width=260, height=720, font_size=20, ruby_size=9, line_spacing=32, margin_t=12, margin_b=12, margin_r=12, margin_l=12, output_format='xtc')
        vertical_args = core.ConversionArgs(**base_args, latin_orientation_mode='vertical')
        horizontal_args = core.ConversionArgs(**base_args, latin_orientation_mode='horizontal')
        vertical_img = core._render_text_blocks_to_images(blocks, font_value, vertical_args, max_output_pages=1)[0]
        horizontal_img = core._render_text_blocks_to_images(blocks, font_value, horizontal_args, max_output_pages=1)[0]
        self.assertNotEqual(vertical_img.tobytes(), horizontal_img.tobytes())



    def test_plain_text_consecutive_dialogue_lines_mark_compact_gap_without_length_limit(self):
        long_dialogue = '「これは六十五文字程度の会話文で、空行なしで次の鍵括弧行へ続く場合を想定するための文です」'
        blocks = core._blocks_from_plain_text(
            f'{long_dialogue}\n'
            '「へえ」\n'
            '「それで、どうなりました」'
        )
        paragraphs = [block for block in blocks if block.get('kind') == 'paragraph']

        self.assertGreaterEqual(len(long_dialogue), 40)
        self.assertTrue(paragraphs[0].get('compact_after'))
        self.assertTrue(paragraphs[1].get('suppress_paragraph_gap_before'))
        self.assertTrue(paragraphs[1].get('compact_after'))
        self.assertTrue(paragraphs[2].get('suppress_paragraph_gap_before'))
        self.assertNotIn('suppress_paragraph_gap_before', paragraphs[0])

    def test_plain_text_dialogue_compaction_respects_blank_and_non_dialogue_boundaries(self):
        blank_blocks = core._blocks_from_plain_text('「へえ」\n\n「それで、どうなりました」')
        blank_paragraphs = [block for block in blank_blocks if block.get('kind') == 'paragraph']
        self.assertFalse(blank_paragraphs[0].get('compact_after', False))
        self.assertFalse(blank_paragraphs[1].get('suppress_paragraph_gap_before', False))

        mixed_blocks = core._blocks_from_plain_text('「へえ」\n地の文です。\n「それで、どうなりました」')
        mixed_paragraphs = [block for block in mixed_blocks if block.get('kind') == 'paragraph']
        self.assertFalse(mixed_paragraphs[0].get('compact_after', False))
        self.assertFalse(mixed_paragraphs[2].get('suppress_paragraph_gap_before', False))

    def test_plain_text_dialogue_compaction_excludes_indented_and_non_dialogue_blocks(self):
        explicit_indent_blocks = core._blocks_from_plain_text('　「明示字下げの会話」\n「次の会話」')
        explicit_paragraphs = [block for block in explicit_indent_blocks if block.get('kind') == 'paragraph']
        self.assertFalse(explicit_paragraphs[0].get('compact_after', False))
        self.assertFalse(explicit_paragraphs[1].get('suppress_paragraph_gap_before', False))

        heading_like_blocks = core._blocks_from_plain_text('【確認ページ】\n「次の会話」')
        heading_like_paragraphs = [block for block in heading_like_blocks if block.get('kind') == 'paragraph']
        self.assertFalse(heading_like_paragraphs[0].get('compact_after', False))
        self.assertFalse(heading_like_paragraphs[1].get('suppress_paragraph_gap_before', False))

        aozora_indent_blocks = core._blocks_from_plain_text(
            '［＃ここから2字下げ］\n'
            '「字下げ内の会話」\n'
            '「字下げ内の次会話」\n'
            '［＃ここで字下げ終わり］'
        )
        aozora_indent_paragraphs = [block for block in aozora_indent_blocks if block.get('kind') == 'paragraph']
        self.assertFalse(aozora_indent_paragraphs[0].get('compact_after', False))
        self.assertFalse(aozora_indent_paragraphs[1].get('suppress_paragraph_gap_before', False))


    def test_opening_bracket_indent_mode_defaults_to_no_indent_and_can_indent_one_char(self):
        font_value = resolve_test_font_path()
        base_args = dict(
            width=220, height=260, font_size=20, ruby_size=10,
            line_spacing=28, margin_t=12, margin_b=12, margin_l=12, margin_r=12,
            output_format='xtc',
        )

        def first_start_y(args):
            starts = []
            original_renderer = core._VerticalPageRenderer

            class TrackingRenderer(original_renderer):
                def draw_runs(self, runs, *draw_args, **draw_kwargs):
                    if runs:
                        starts.append((self.curr_x, self.curr_y))
                    return super().draw_runs(runs, *draw_args, **draw_kwargs)

            with mock.patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
                core._render_text_blocks_to_page_entries(core._blocks_from_plain_text('「あ」'), font_value, args)
            self.assertTrue(starts)
            return starts[0][1]

        default_args = core.ConversionArgs(**base_args)
        indented_args = core.ConversionArgs(**base_args, opening_bracket_indent_mode='one_char')

        self.assertEqual(default_args.opening_bracket_indent_mode, 'none')
        self.assertEqual(first_start_y(default_args), default_args.margin_t)
        self.assertEqual(first_start_y(indented_args), indented_args.margin_t + indented_args.font_size + 2)

    def test_consecutive_dialogue_gap_suppression_keeps_line_break_without_extra_blank_column(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=220, height=260, font_size=20, ruby_size=10,
            line_spacing=28, margin_t=12, margin_b=12, margin_l=12, margin_r=12,
            output_format='xtc',
        )
        starts = []
        original_renderer = core._VerticalPageRenderer

        class TrackingRenderer(original_renderer):
            def draw_runs(self, runs, *draw_args, **draw_kwargs):
                if runs:
                    starts.append((self.curr_x, self.curr_y))
                return super().draw_runs(runs, *draw_args, **draw_kwargs)

        with mock.patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            core._render_text_blocks_to_page_entries(core._blocks_from_plain_text('「あ」\n「い」'), font_value, args)

        self.assertEqual(len(starts), 2)
        self.assertEqual(starts[0][0] - starts[1][0], args.line_spacing)
        self.assertEqual(starts[1][1], starts[0][1])

    def test_consecutive_dialogue_gap_suppression_does_not_merge_after_hanging_punctuation(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=220, height=260, font_size=20, ruby_size=10,
            line_spacing=28, margin_t=12, margin_b=12, margin_l=12, margin_r=12,
            output_format='xtc', kinsoku_mode='standard',
        )
        starts = []
        original_renderer = core._VerticalPageRenderer

        class TrackingRenderer(original_renderer):
            def draw_runs(self, runs, *draw_args, **draw_kwargs):
                if runs:
                    starts.append((self.curr_x, self.curr_y))
                return super().draw_runs(runs, *draw_args, **draw_kwargs)

        with mock.patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            core._render_text_blocks_to_page_entries(core._blocks_from_plain_text('「あ。」\n「い」'), font_value, args)

        self.assertEqual(len(starts), 2)
        self.assertEqual(starts[0][0] - starts[1][0], args.line_spacing)
        self.assertEqual(starts[1][1], starts[0][1])

    def test_blank_between_dialogue_lines_keeps_existing_column_advance(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=220, height=260, font_size=20, ruby_size=10,
            line_spacing=28, margin_t=12, margin_b=12, margin_l=12, margin_r=12,
            output_format='xtc',
        )
        starts = []
        original_renderer = core._VerticalPageRenderer

        class TrackingRenderer(original_renderer):
            def draw_runs(self, runs, *draw_args, **draw_kwargs):
                if runs:
                    starts.append((self.curr_x, self.curr_y))
                return super().draw_runs(runs, *draw_args, **draw_kwargs)

        with mock.patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            core._render_text_blocks_to_page_entries(core._blocks_from_plain_text('「あ」\n\n「い」'), font_value, args)

        self.assertEqual(len(starts), 2)
        self.assertEqual(starts[0][0] - starts[1][0], args.line_spacing * 2)
        self.assertEqual(starts[1][1], args.margin_t)

    def test_blank_after_terminal_hanging_punctuation_is_not_counted_twice(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=220, height=90, font_size=20, ruby_size=10,
            line_spacing=28, margin_t=10, margin_b=10, margin_l=10, margin_r=10,
            output_format='xtc', kinsoku_mode='standard',
        )
        starts = []
        original_renderer = core._VerticalPageRenderer

        class TrackingRenderer(original_renderer):
            def draw_runs(self, runs, *draw_args, **draw_kwargs):
                if runs:
                    starts.append((self.curr_x, self.curr_y))
                return super().draw_runs(runs, *draw_args, **draw_kwargs)

        with mock.patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            core._render_text_blocks_to_page_entries(core._blocks_from_plain_text('ある、\n\n次'), font_value, args)

        self.assertEqual(len(starts), 2)
        self.assertEqual(starts[0][0] - starts[1][0], args.line_spacing * 2)
        self.assertEqual(starts[1][1], args.font_size + 2 + args.margin_t)

    def test_line_break_after_terminal_hanging_punctuation_reuses_auto_advanced_column(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=220, height=90, font_size=20, ruby_size=10,
            line_spacing=28, margin_t=10, margin_b=10, margin_l=10, margin_r=10,
            output_format='xtc', kinsoku_mode='standard',
        )
        starts = []
        original_renderer = core._VerticalPageRenderer

        class TrackingRenderer(original_renderer):
            def draw_runs(self, runs, *draw_args, **draw_kwargs):
                if runs:
                    starts.append((self.curr_x, self.curr_y))
                return super().draw_runs(runs, *draw_args, **draw_kwargs)

        with mock.patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            core._render_text_blocks_to_page_entries(core._blocks_from_plain_text('ある、\n次'), font_value, args)

        self.assertEqual(len(starts), 2)
        self.assertEqual(starts[0][0] - starts[1][0], args.line_spacing)
        self.assertEqual(starts[1][1], args.font_size + 2 + args.margin_t)

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

    def test_current_line_head_forbidden_token_is_not_pushed_to_next_column_head(self):
        tokens = ['あ', '、', '？', 'い', 'い']
        # The preceding body character has left exactly one slot.  The current
        # token is already line-head-forbidden, so advancing it would move ``、``
        # to the next column head.  Draw it here instead, even if the following
        # punctuation tail can no longer be fully protected on this extreme grid.
        self.assertEqual(
            core._choose_vertical_layout_action(
                tokens, 1, 70, 10, 105, 10, 20, kinsoku_mode='standard'),
            'draw',
        )
        hints = core._build_vertical_layout_hints(tuple(tokens))
        self.assertEqual(
            core._choose_vertical_layout_action_with_hints(
                hints, 1, 1, True, kinsoku_mode='standard'),
            'draw',
        )

    def test_tiny_grid_does_not_move_hanging_punctuation_to_column_head(self):
        import tategakiXTC_gui_core_renderer as renderer
        from tests.image_golden_cases import render_page_blocks_case

        args = dict(
            width=320, height=240, font_size=72, ruby_size=24,
            margin_l=20, margin_r=20, margin_t=80, margin_b=0,
            line_spacing=80, output_format='xtc', kinsoku_mode='standard',
        )
        captured = []
        original = renderer.draw_char_tate

        def spy(draw, token, pos, font, f_size, **kwargs):
            if token == '、' and pos[1] == args['margin_t']:
                captured.append((token, pos))
            return original(draw, token, pos, font, f_size, **kwargs)

        blocks = [{'kind': 'paragraph', 'runs': [{'text': 'あ、？いい'}]}]
        with mock.patch.object(renderer, 'draw_char_tate', side_effect=spy):
            render_page_blocks_case(args, blocks, page_mode='strip')
        self.assertEqual(captured, [])

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

    def test_long_ruby_reserve_keeps_following_punctuation_attached_to_parent(self):
        import tategakiXTC_gui_core_renderer as renderer

        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=300, height=760, font_size=22, ruby_size=11,
            margin_l=12, margin_r=12, margin_t=14, margin_b=14,
            line_spacing=26, output_format='xtc', kinsoku_mode='standard',
        )
        blocks = [{
            'kind': 'paragraph',
            'runs': [
                {'text': '独坐幽篁裏', 'ruby': 'ゆうこうのうちにざしながい'},
                {'text': '、弾琴'},
            ],
        }]
        captured = []
        original = renderer.draw_char_tate

        def spy(draw, token, pos, font, f_size, **kwargs):
            if not kwargs.get('ruby_mode') and token in {'裏', '、', '弾'}:
                captured.append((token, pos))
            return original(draw, token, pos, font, f_size, **kwargs)

        with mock.patch.object(renderer, 'draw_char_tate', side_effect=spy):
            core._render_text_blocks_to_images(blocks, font_value, args, max_output_pages=1)

        positions = {token: pos for token, pos in captured}
        self.assertIn('裏', positions)
        self.assertIn('、', positions)
        self.assertIn('弾', positions)
        line_step = args.font_size + 2
        self.assertEqual(positions['、'][1], positions['裏'][1] + line_step)
        self.assertGreater(positions['弾'][1], positions['、'][1] + line_step)


    def test_ruby_tail_punctuation_keeps_gap_before_following_ruby(self):
        import tategakiXTC_gui_core_renderer as renderer

        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=300, height=760, font_size=22, ruby_size=11,
            margin_l=12, margin_r=12, margin_t=14, margin_b=14,
            line_spacing=26, output_format='xtc', kinsoku_mode='standard',
        )
        blocks = [{
            'kind': 'paragraph',
            'runs': [
                {'text': '独坐幽篁裏', 'ruby': 'ゆうこうのうちにざし'},
                {'text': '、'},
                {'text': '弾琴', 'ruby': 'きんをだんじて'},
            ],
        }]
        captured = []
        original = renderer.draw_char_tate

        def spy(draw, token, pos, font, f_size, **kwargs):
            if not kwargs.get('ruby_mode') and token in {'裏', '、', '弾'}:
                captured.append((token, pos))
            return original(draw, token, pos, font, f_size, **kwargs)

        with mock.patch.object(renderer, 'draw_char_tate', side_effect=spy):
            core._render_text_blocks_to_images(blocks, font_value, args, max_output_pages=1)

        positions = {token: pos for token, pos in captured}
        self.assertIn('裏', positions)
        self.assertIn('、', positions)
        self.assertIn('弾', positions)
        line_step = args.font_size + 2
        self.assertEqual(positions['、'][1], positions['裏'][1] + line_step)
        self.assertGreater(positions['弾'][1], positions['、'][1] + line_step)


    def test_short_ruby_before_tail_punctuation_starts_beside_parent(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=300, height=760, font_size=22, ruby_size=11,
            margin_l=12, margin_r=12, margin_t=14, margin_b=14,
            line_spacing=26, output_format='xtc', kinsoku_mode='standard',
        )
        blocks = [{
            'kind': 'paragraph',
            'runs': [
                {'text': '画として'},
                {'text': '観', 'ruby': 'かん'},
                {'text': '、一巻の詩として読むからである。'},
            ],
        }]
        body_draws = []
        ruby_draws = []
        original = core.draw_char_tate

        def spy(draw, token, pos, font, f_size, **kwargs):
            if kwargs.get('ruby_mode') and token in {'か', 'ん'}:
                ruby_draws.append((token, pos))
            elif token in {'観', '、'}:
                body_draws.append((token, pos))
            return original(draw, token, pos, font, f_size, **kwargs)

        with mock.patch.object(core, 'draw_char_tate', side_effect=spy):
            core._render_text_blocks_to_images(blocks, font_value, args, max_output_pages=1)

        body_positions = {token: pos for token, pos in body_draws}
        self.assertIn('観', body_positions)
        self.assertIn('、', body_positions)
        self.assertTrue(ruby_draws)
        self.assertEqual(ruby_draws[0][0], 'か')
        # The comma after the ruby parent is a following body cell, not part of
        # the ruby display anchor.  The reading should start beside 観.
        self.assertLessEqual(abs(ruby_draws[0][1][1] - body_positions['観'][1]), 4)
        self.assertGreater(body_positions['、'][1], body_positions['観'][1])


    def test_kanbun_ruby_display_joins_adjacent_ruby_inside_punctuation_clause(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=300, height=760, font_size=22, ruby_size=11,
            margin_l=12, margin_r=12, margin_t=14, margin_b=14,
            line_spacing=26, output_format='xtc', kinsoku_mode='standard',
        )
        blocks = [{
            'kind': 'paragraph',
            'runs': [
                {'text': '独坐幽篁裏', 'ruby': 'ゆうこうのうちにざし'},
                {'text': '、'},
                {'text': '弾琴', 'ruby': 'きんをだんじて'},
                {'text': '復長嘯', 'ruby': 'またちょうしょうす'},
                {'text': '、'},
            ],
        }]
        ruby_draws = []
        original = core.draw_char_tate

        def spy(draw, token, pos, font, f_size, **kwargs):
            if kwargs.get('ruby_mode'):
                ruby_draws.append((token, pos))
            return original(draw, token, pos, font, f_size, **kwargs)

        with mock.patch.object(core, 'draw_char_tate', side_effect=spy):
            core._render_text_blocks_to_images(blocks, font_value, args, max_output_pages=1)

        ruby_text = ''.join(token for token, _pos in ruby_draws)
        self.assertIn('ゆうこうのうちにざしきんをだんじてまたちょうしょうす'.replace('', '　'), ruby_text)
        y_by_index = {idx: pos[1] for idx, (_token, pos) in enumerate(ruby_draws)}
        joined = ''.join(token for token, _pos in ruby_draws)
        boundary = joined.index('きんをだんじてまた') + len('きんをだんじて') - 1
        self.assertEqual(ruby_draws[boundary][0], 'て')
        self.assertEqual(ruby_draws[boundary + 1][0], 'ま')
        self.assertEqual(y_by_index[boundary + 1] - y_by_index[boundary], args.ruby_size + 2)

    def test_kanbun_ruby_sequence_starts_at_first_parent_after_prefix_text(self):
        font_value = resolve_test_font_path()
        args = core.ConversionArgs(
            width=300, height=760, font_size=22, ruby_size=11,
            margin_l=12, margin_r=12, margin_t=14, margin_b=14,
            line_spacing=26, output_format='xtc', kinsoku_mode='standard',
        )
        blocks = [{
            'kind': 'paragraph',
            'runs': [
                {'text': 'れる。'},
                {'text': '独坐幽篁裏', 'ruby': 'ゆうこうのうちにざし'},
                {'text': '、'},
                {'text': '弾琴', 'ruby': 'きんをだんじて'},
                {'text': '復長嘯', 'ruby': 'またちょうしょうす'},
                {'text': '、'},
                {'text': '深林', 'ruby': 'しんりん'},
                {'text': '人不知', 'ruby': 'ひとしらず'},
                {'text': '、'},
                {'text': '明月', 'ruby': 'めいげつ'},
                {'text': '来', 'ruby': 'きたりて'},
                {'text': '相照', 'ruby': 'あいてらす'},
                {'text': '。'},
            ],
        }]
        body_draws = []
        ruby_draws = []
        original = core.draw_char_tate

        def spy(draw, token, pos, font, f_size, **kwargs):
            if kwargs.get('ruby_mode'):
                ruby_draws.append((token, pos))
            elif token == '独':
                body_draws.append((token, pos))
            return original(draw, token, pos, font, f_size, **kwargs)

        with mock.patch.object(core, 'draw_char_tate', side_effect=spy):
            core._render_text_blocks_to_images(blocks, font_value, args, max_output_pages=1)

        self.assertTrue(body_draws)
        self.assertTrue(ruby_draws)
        self.assertEqual(ruby_draws[0][0], 'ゆ')
        # The first ruby reading should start beside 独, not be pulled downward
        # by later groups in the same kanbun clause.
        self.assertLessEqual(abs(ruby_draws[0][1][1] - body_draws[0][1][1]), 4)

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
