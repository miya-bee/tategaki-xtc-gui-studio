import sys
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class RubyRendererHelperRegressionTests(unittest.TestCase):
    def _args(self, **overrides):
        params = dict(
            width=160,
            height=220,
            font_size=24,
            ruby_size=12,
            line_spacing=34,
            margin_t=10,
            margin_b=10,
            margin_l=10,
            margin_r=10,
            output_format='xtc',
        )
        params.update(overrides)
        return core.ConversionArgs(**params)

    def _renderer(self, args=None):
        args = args or self._args()
        font = core.load_truetype_font(str(FONT_PATH), args.font_size)
        ruby_font = core.load_truetype_font(str(FONT_PATH), args.ruby_size)
        return core._VerticalPageRenderer(args, font, ruby_font)

    def test_split_ruby_text_segments_covers_rounding_caps_and_empty_segments(self):
        self.assertEqual(core._split_ruby_text_segments('', [2, 1]), ['', ''])

        positive_diff = core._split_ruby_text_segments('abcdefg', [1, 1, 1])
        self.assertEqual(''.join(positive_diff), 'abcdefg')
        self.assertEqual(len(positive_diff), 3)

        negative_diff = core._split_ruby_text_segments('ab', [1, 1, 1])
        self.assertEqual(''.join(negative_diff), 'ab')
        self.assertEqual(len(negative_diff), 3)

        capped = core._split_ruby_text_segments('abcde', [2, 2, 1], segment_capacities=[1, 1, None])
        self.assertEqual(''.join(capped), 'abcde')
        self.assertLessEqual(len(capped[0]), 1)
        self.assertLessEqual(len(capped[1]), 1)

        overflow_fallback = core._split_ruby_text_segments('abcde', [2, 2, 1], segment_capacities=[1, 1, 1])
        self.assertEqual(''.join(overflow_fallback), 'abcde')
        self.assertEqual(len(overflow_fallback), 3)

        self.assertEqual(core._split_ruby_text_segments('xyz', []), ['xyz'])

    def test_split_ruby_text_segments_cache_reuses_same_tuple_result(self):
        info_before = core._split_ruby_text_segments_cached.cache_info()
        first = core._split_ruby_text_segments('abcdef', [2, 2, 2], segment_capacities=[None, 2, None])
        second = core._split_ruby_text_segments('abcdef', [2, 2, 2], segment_capacities=[None, 2, None])
        info_after = core._split_ruby_text_segments_cached.cache_info()

        self.assertEqual(first, second)
        self.assertGreaterEqual(info_after.hits, info_before.hits + 1)

    def test_ruby_group_capacity_reserves_effective_bottom_margin(self):
        args = self._args(height=100, margin_t=0, margin_b=12, font_size=20, ruby_size=10)
        group = {'page_index': 0, 'x': 20, 'start_y': 78, 'end_y': 78, 'base_len': 1}

        capacity = core._ruby_group_capacity_for_args(group, 0, 1, args)
        slot_h = args.ruby_size + 2
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        expected_capacity = ((args.height - effective_bottom - 1) // slot_h) + 1
        raw_margin_capacity = ((args.height - args.margin_b - 1) // slot_h) + 1

        self.assertEqual(capacity, expected_capacity)
        self.assertLess(capacity, raw_margin_capacity)

    def test_draw_split_ruby_groups_clamps_to_effective_bottom_margin(self):
        args = self._args(height=100, margin_t=0, margin_b=12, font_size=20, ruby_size=10)
        renderer = self._renderer(args)
        group = {'page_index': 0, 'x': 20, 'start_y': 88, 'end_y': 88, 'base_len': 1}
        drawn = []

        def capture_ruby(_draw, char, pos, _font, f_size, **_kwargs):
            drawn.append((char, pos, f_size))

        with mock.patch.object(core, 'draw_char_tate', side_effect=capture_ruby):
            renderer.draw_split_ruby_groups([group], '底')

        self.assertEqual([char for char, _pos, _size in drawn], ['底'])
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        self.assertLessEqual(drawn[0][1][1], args.height - effective_bottom - args.ruby_size)

    def test_build_ruby_overlay_groups_compacts_segment_infos(self):
        groups = core._build_ruby_overlay_groups([
            {'page_index': 0, 'x': 20, 'y': 30, 'base_len': 1},
            {'page_index': 0, 'x': 20, 'y': 56, 'base_len': 2},
            {'page_index': 1, 'x': 24, 'y': 18, 'base_len': 1},
        ])

        self.assertEqual(groups, [
            {'page_index': 0, 'x': 20, 'start_y': 30, 'end_y': 56, 'base_len': 3},
            {'page_index': 1, 'x': 24, 'start_y': 18, 'end_y': 18, 'base_len': 1},
        ])

    def test_build_ruby_overlay_groups_keeps_page_local_y_resets_separate(self):
        groups = core._build_ruby_overlay_groups([
            {'page_index': 0, 'x': 20, 'y': 70, 'base_len': 1},
            {'page_index': 0, 'x': 20, 'y': 22, 'base_len': 1},
            {'page_index': 1, 'x': 20, 'y': 10, 'base_len': 1},
        ])

        self.assertEqual(groups, [
            {'page_index': 0, 'x': 20, 'start_y': 70, 'end_y': 70, 'base_len': 1},
            {'page_index': 0, 'x': 20, 'start_y': 22, 'end_y': 22, 'base_len': 1},
            {'page_index': 1, 'x': 20, 'start_y': 10, 'end_y': 10, 'base_len': 1},
        ])

    def test_draw_text_run_captures_ruby_groups_across_page_boundaries(self):
        args = self._args(
            width=80,
            height=90,
            font_size=20,
            ruby_size=8,
            line_spacing=80,
            margin_t=5,
            margin_b=5,
            margin_l=5,
            margin_r=5,
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        groups = []

        with mock.patch.object(core, 'draw_char_tate'), \
             mock.patch.object(core, 'draw_hanging_punctuation'), \
             mock.patch.object(core, 'draw_hanging_closing_bracket'):
            renderer.draw_text_run('ABCDEFGHIJKL', object(), ruby_overlay_groups=groups)

        self.assertGreaterEqual(len(renderer.page_entries), 1)
        self.assertGreaterEqual(len(groups), 2)
        self.assertEqual([group['page_index'] for group in groups], sorted(group['page_index'] for group in groups))
        self.assertEqual({group['start_y'] for group in groups}, {args.margin_t})
        self.assertTrue(all(group['start_y'] <= group['end_y'] for group in groups))
        self.assertEqual(sum(group['base_len'] for group in groups), 12)

    def test_ruby_group_capacity_accepts_compact_group_shape(self):
        args = self._args(height=100, margin_t=10, margin_b=10, font_size=16, ruby_size=8)
        compact_group = {'page_index': 0, 'x': 20, 'start_y': 30, 'end_y': 46, 'base_len': 2}
        legacy_group = {'chars': [{'y': 30}, {'y': 46}]}
        self.assertEqual(
            core._ruby_group_capacity_for_args(compact_group, 0, 1, args),
            core._ruby_group_capacity_for_args(legacy_group, 0, 1, args),
        )


    def test_ruby_group_capacity_and_draw_split_ruby_cover_zero_and_multi_group_paths(self):
        args = self._args(height=80, margin_t=20, margin_b=20, font_size=16, ruby_size=8)
        zero_group = {'chars': [{'y': 0}, {'y': 0}]}
        self.assertEqual(core._ruby_group_capacity_for_args(zero_group, 0, 2, args), 0)

        renderer = self._renderer(self._args())
        renderer.add_page(Image.new('L', (renderer.args.width, renderer.args.height), 255), label='stored-1')
        renderer.add_page(Image.new('L', (renderer.args.width, renderer.args.height), 255), label='stored-2')
        segment_infos = [
            {'page_index': 0, 'x': 20, 'y': 20, 'cell_text': '甲', 'base_len': 1},
            {'page_index': 1, 'x': 24, 'y': 40, 'cell_text': '乙', 'base_len': 1},
            {'page_index': 2, 'x': 28, 'y': 60, 'cell_text': '丙', 'base_len': 1},
        ]

        calls = []

        def record_draw(target_draw, ch, pos, font, size, **kwargs):
            calls.append((ch, pos, size, kwargs.get('ruby_mode', False)))

        with mock.patch.object(core, 'draw_char_tate', side_effect=record_draw):
            renderer.draw_split_ruby([], 'ルビ')
            renderer.draw_split_ruby(segment_infos, '')
            renderer.draw_split_ruby(segment_infos, 'ルビ', is_bold=True, is_italic=True)

        self.assertEqual([c[0] for c in calls], list('ルビ'))
        self.assertTrue(all(c[3] for c in calls))

    def test_vertical_renderer_api_edges_cover_noop_and_grouping_paths(self):
        renderer = self._renderer()
        start_pos = (renderer.curr_x, renderer.curr_y)
        renderer.flush_current_page()
        self.assertEqual(renderer.page_entries, [])
        self.assertEqual((renderer.curr_x, renderer.curr_y), start_pos)

        current_img, _ = renderer.get_page_image_draw(0)
        self.assertEqual(current_img.size, (renderer.args.width, renderer.args.height))

        renderer.add_page(Image.new('L', (renderer.args.width, renderer.args.height), 255), label='cached-draw-page')
        stored_img, stored_draw_1 = renderer.get_page_image_draw(0)
        _stored_img_again, stored_draw_2 = renderer.get_page_image_draw(0)
        self.assertEqual(stored_img.size, (renderer.args.width, renderer.args.height))
        self.assertIs(stored_draw_1, stored_draw_2)


        self.assertFalse(renderer.apply_pending_paragraph_indent(0))
        before_y = renderer.curr_y
        renderer.insert_paragraph_indent(0)
        self.assertEqual(renderer.curr_y, before_y)
        renderer.draw_text_run('', renderer.font)
        renderer.draw_runs([{'text': ''}], default_font=renderer.font)
        renderer.draw_inline_image(None)
        self.assertFalse(renderer.has_drawn_on_page)

        renderer.emphasis_font_value = 'missing-font.ttf'
        self.assertIs(renderer._get_emphasis_font(), renderer.font)
        self.assertFalse(renderer._should_draw_emphasis_for_cell('　 '))
        self.assertFalse(renderer._should_draw_side_line_for_cell(' '))

        groups = renderer._iter_side_line_groups([
            {'page_index': 0, 'x': 10, 'y': 10, 'cell_text': 'A'},
            {'page_index': 0, 'x': 10, 'y': 36, 'cell_text': ' '},
            {'page_index': 0, 'x': 10, 'y': 62, 'cell_text': 'B'},
        ])
        self.assertEqual(len(groups), 2)

        spans = renderer._iter_side_line_spans_cells([
            (0, 10, 10, 'A'),
            (0, 10, 36, ' '),
            (0, 10, 62, 'B'),
            (0, 10, 88, 'C'),
        ])
        self.assertEqual(spans, [
            (0, 10, 10, 10),
            (0, 10, 62, 88),
        ])

    def test_draw_runs_skips_segment_capture_for_plain_runs(self):
        renderer = self._renderer()
        seen_kwargs = []

        def fake_draw_text_run(text, run_font, **kwargs):
            seen_kwargs.append(kwargs)

        with mock.patch.object(renderer, 'draw_text_run', side_effect=fake_draw_text_run), \
             mock.patch.object(renderer, 'draw_split_ruby_groups') as ruby_mock, \
             mock.patch.object(renderer, 'draw_emphasis_marks_cells') as emphasis_mock, \
             mock.patch.object(renderer, 'draw_side_lines_cells') as side_line_mock:
            renderer.draw_runs([
                {'text': '素の本文ですよね続'},
                {'text': 'ルビ付き本文ですよ', 'ruby': 'るび'},
                {'text': '傍点付き本文ですよ', 'emphasis': '白丸傍点'},
                {'text': '側線付き本文ですよ', 'side_line': 'solid'},
                {'text': '全部付き本文ですよ', 'ruby': 'るび', 'emphasis': '白丸傍点', 'side_line': 'solid'},
            ], default_font=renderer.font)

        self.assertIsNone(seen_kwargs[0].get('segment_infos'))
        self.assertFalse(seen_kwargs[0].get('segment_info_needs_base_len', False))
        self.assertFalse(seen_kwargs[0].get('segment_info_needs_cell_text', False))

        self.assertIsNone(seen_kwargs[1].get('segment_infos'))
        self.assertIsInstance(seen_kwargs[1].get('ruby_overlay_groups'), list)
        self.assertFalse(seen_kwargs[1].get('segment_info_needs_base_len', False))
        self.assertFalse(seen_kwargs[1].get('segment_info_needs_cell_text', False))

        self.assertIsNone(seen_kwargs[2].get('segment_infos'))
        self.assertIsInstance(seen_kwargs[2].get('overlay_cells'), list)
        self.assertFalse(seen_kwargs[2].get('segment_info_needs_base_len'))
        self.assertFalse(seen_kwargs[2].get('segment_info_needs_cell_text'))

        self.assertIsNone(seen_kwargs[3].get('segment_infos'))
        self.assertIsInstance(seen_kwargs[3].get('overlay_cells'), list)
        self.assertFalse(seen_kwargs[3].get('segment_info_needs_base_len'))
        self.assertFalse(seen_kwargs[3].get('segment_info_needs_cell_text'))

        self.assertIsNone(seen_kwargs[4].get('segment_infos'))
        self.assertIsInstance(seen_kwargs[4].get('ruby_overlay_groups'), list)
        self.assertIsInstance(seen_kwargs[4].get('overlay_cells'), list)
        self.assertFalse(seen_kwargs[4].get('segment_info_needs_base_len', False))
        self.assertFalse(seen_kwargs[4].get('segment_info_needs_cell_text'))
        ruby_mock.assert_not_called()
        emphasis_mock.assert_not_called()
        side_line_mock.assert_not_called()

    def test_draw_runs_plain_runs_use_minimal_draw_text_run_kwargs(self):
        renderer = self._renderer()
        seen_kwargs = []

        def fake_draw_text_run(text, run_font, **kwargs):
            seen_kwargs.append(kwargs)

        with mock.patch.object(renderer, 'draw_text_run', side_effect=fake_draw_text_run):
            renderer.draw_runs([
                {'text': '素の本文ですよね続', 'bold': True},
            ], default_font=renderer.font)

        self.assertEqual(len(seen_kwargs), 1)
        self.assertEqual(set(seen_kwargs[0].keys()), {'wrap_indent_chars', 'is_bold', 'is_italic'})
        self.assertTrue(seen_kwargs[0]['is_bold'])
        self.assertFalse(seen_kwargs[0]['is_italic'])

    def test_draw_runs_only_resolves_code_font_for_code_runs(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, '_get_code_font', wraps=renderer._get_code_font) as get_code_font:
            renderer.draw_runs([
                {'text': '素の本文ですよね続'},
                {'text': 'code', 'code': True},
                {'text': '別の本文'},
            ], default_font=renderer.font)

        self.assertEqual(get_code_font.call_count, 1)

    def test_draw_runs_reuses_code_font_for_multiple_code_runs(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, '_get_code_font', wraps=renderer._get_code_font) as get_code_font:
            renderer.draw_runs([
                {'text': 'code', 'code': True},
                {'text': 'more', 'code': True},
                {'text': '本文です'},
                {'text': 'tail', 'code': True},
            ], default_font=renderer.font)

        self.assertEqual(get_code_font.call_count, 1)

    def test_draw_runs_single_char_plain_uses_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path:
            renderer.draw_runs([
                {'text': '本'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        plain_path.assert_called_once()

    def test_draw_runs_single_char_ruby_and_overlay_use_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path:
            renderer.draw_runs([
                {'text': '本', 'ruby': 'ほん', 'side_line': 'solid'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        overlay_path.assert_called_once()

    def test_draw_runs_two_char_plain_uses_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run, \
             mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path, \
             mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '本文'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        plain_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)

    def test_draw_runs_two_char_ruby_and_overlay_use_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run, \
             mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path, \
             mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '本文', 'ruby': 'ほんぶん', 'side_line': 'solid'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        overlay_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)

    def test_draw_runs_three_char_plain_uses_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '本文中'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        plain_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)

    def test_draw_runs_four_char_ruby_and_overlay_use_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '本文です', 'ruby': 'ほんぶんです', 'side_line': 'solid'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        overlay_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)

    def test_draw_runs_five_char_plain_uses_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '本文です。'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        plain_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)

    def test_draw_runs_eight_char_plain_uses_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '縦書き本文です'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        plain_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)

    def test_draw_runs_eight_char_overlay_use_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '縦書き本文です', 'ruby': 'たてがき', 'side_line': 'solid'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        overlay_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)

    def test_draw_runs_six_char_ruby_and_overlay_use_direct_renderer_fast_path(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_runs([
                {'text': '本文です！！', 'ruby': 'ほんぶんです', 'side_line': 'solid'},
            ], default_font=renderer.font)

        draw_text_run.assert_not_called()
        overlay_path.assert_called_once()
        self.assertEqual(tokenize_cached.call_count, 1)


    def test_collect_repeated_run_texts_filters_medium_long_repeats(self):
        renderer = self._renderer()

        repeated = renderer._collect_repeated_run_texts([
            {'text': '短文'},
            {'text': 'これは中くらいの本文です'},
            {'text': 'これは中くらいの本文です'},
            {'text': 'x' * 40},
            {'text': 'x' * 40},
            {'text': 'y' * 70},
            {'text': 'y' * 70},
            {'text': 'z' * 140},
            {'text': 'z' * 140},
            {'text': 'q' * 220},
            {'text': 'q' * 220},
            {'text': 'w' * 280},
            {'text': 'w' * 280},
            {'text': ''},
            None,
        ], min_len=7, max_len=256)

        self.assertEqual(repeated, {'これは中くらいの本文です', 'x' * 40, 'y' * 70, 'z' * 140, 'q' * 220})

    def test_draw_runs_reuses_medium_run_tokens_and_hints_within_single_call(self):
        renderer = self._renderer()
        repeated_text = 'これは中くらいの本文です'

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text},
                {'text': repeated_text},
                {'text': '別の本文ですよね続'},
            ], default_font=renderer.font)

        draw_text_run.assert_called_once_with(
            '別の本文ですよね続',
            renderer.font,
            wrap_indent_chars=0,
            is_bold=False,
            is_italic=False,
        )
        self.assertEqual(plain_path.call_count, 2)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_reuses_repeated_long_plain_runs_within_single_call(self):
        renderer = self._renderer()
        repeated_text = '長めの本文です。' * 4

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text},
                {'text': repeated_text},
                {'text': '別の長い本文です。' * 5},
            ], default_font=renderer.font)

        self.assertEqual(draw_text_run.call_count, 1)
        self.assertEqual(plain_path.call_count, 2)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_reuses_repeated_long_overlay_runs_within_single_call(self):
        renderer = self._renderer()
        repeated_text = '長めの本文です。' * 4

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text, 'ruby': 'るび', 'side_line': 'solid'},
                {'text': repeated_text, 'ruby': 'るび', 'side_line': 'solid'},
                {'text': '別の長い本文です。' * 5, 'ruby': 'るび', 'side_line': 'solid'},
            ], default_font=renderer.font)

        self.assertEqual(draw_text_run.call_count, 1)
        self.assertEqual(overlay_path.call_count, 2)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_reuses_repeated_ultra_long_plain_runs_within_single_call(self):
        renderer = self._renderer()
        repeated_text = '長めの本文です。' * 18

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text},
                {'text': repeated_text},
                {'text': '別の長い本文です。' * 30},
            ], default_font=renderer.font)

        self.assertEqual(draw_text_run.call_count, 1)
        self.assertEqual(plain_path.call_count, 2)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_reuses_repeated_ultra_long_overlay_runs_within_single_call(self):
        renderer = self._renderer()
        repeated_text = '長めの本文です。' * 18

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text, 'ruby': 'るび', 'side_line': 'solid'},
                {'text': repeated_text, 'ruby': 'るび', 'side_line': 'solid'},
                {'text': '別の長い本文です。' * 30, 'ruby': 'るび', 'side_line': 'solid'},
            ], default_font=renderer.font)

        self.assertEqual(draw_text_run.call_count, 1)
        self.assertEqual(overlay_path.call_count, 2)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_reuses_repeated_very_long_plain_runs_within_single_call(self):
        renderer = self._renderer()
        repeated_text = '長めの本文です。' * 10

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text},
                {'text': repeated_text},
                {'text': '別の長い本文です。' * 15},
            ], default_font=renderer.font)

        self.assertEqual(draw_text_run.call_count, 1)
        self.assertEqual(plain_path.call_count, 2)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_reuses_medium_overlay_run_tokens_and_hints_within_single_call(self):
        renderer = self._renderer()
        repeated_text = 'これは中くらいの本文です'

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text, 'ruby': 'るび', 'side_line': 'solid'},
                {'text': repeated_text, 'ruby': 'るび', 'side_line': 'solid'},
                {'text': '別の本文ですよね続', 'ruby': 'るび', 'side_line': 'solid'},
            ], default_font=renderer.font)

        self.assertEqual(draw_text_run.call_count, 1)
        self.assertEqual(overlay_path.call_count, 2)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_reuses_short_run_tokens_and_hints_within_single_call(self):
        renderer = self._renderer()

        with mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': '本文'},
                {'text': '本文', 'side_line': 'solid'},
                {'text': '本文'},
            ], default_font=renderer.font)

        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_repeated_medium_text_warmup_skips_single_hint_fast_path(self):
        renderer = self._renderer()
        repeated_text = 'これは中くらいの本文です'

        with mock.patch.object(core, '_build_single_token_vertical_layout_hints', wraps=core._build_single_token_vertical_layout_hints) as single_hint,              mock.patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached,              mock.patch.object(core, '_build_vertical_layout_hints_cached', wraps=core._build_vertical_layout_hints_cached) as build_cached:
            renderer.draw_runs([
                {'text': repeated_text},
                {'text': repeated_text},
            ], default_font=renderer.font)

        self.assertEqual(single_hint.call_count, 0)
        self.assertEqual(tokenize_cached.call_count, 1)
        self.assertEqual(build_cached.call_count, 1)

    def test_draw_runs_skips_falsy_entries_before_resolving_fonts(self):
        renderer = self._renderer()

        with mock.patch.object(renderer, 'draw_text_run') as draw_text_run,              mock.patch.object(renderer, '_get_code_font', wraps=renderer._get_code_font) as get_code_font:
            renderer.draw_runs([
                None,
                {},
                {'text': ''},
                {'text': '通常本文ですよね続'},
            ], default_font=renderer.font)

        draw_text_run.assert_called_once()
        self.assertEqual(get_code_font.call_count, 0)

    def test_draw_runs_overlay_paths_keep_draw_text_run_kwargs_compact(self):
        renderer = self._renderer()
        seen_kwargs = []

        def fake_draw_text_run(text, run_font, **kwargs):
            seen_kwargs.append(kwargs)

        with mock.patch.object(renderer, 'draw_text_run', side_effect=fake_draw_text_run):
            renderer.draw_runs([
                {'text': 'ルビのみ本文ですよ', 'ruby': 'るび'},
                {'text': '傍点のみ本文ですよ', 'emphasis': '白丸傍点'},
                {'text': '本文併用ですよ続編', 'ruby': 'るび', 'side_line': 'solid'},
            ], default_font=renderer.font)

        self.assertEqual(set(seen_kwargs[0].keys()), {'wrap_indent_chars', 'ruby_overlay_groups', 'is_bold', 'is_italic'})
        self.assertEqual(set(seen_kwargs[1].keys()), {'wrap_indent_chars', 'overlay_cells', 'is_bold', 'is_italic'})
        self.assertEqual(set(seen_kwargs[2].keys()), {'wrap_indent_chars', 'ruby_overlay_groups', 'overlay_cells', 'is_bold', 'is_italic'})

    def test_draw_runs_ruby_plus_side_line_uses_compact_run_mode(self):
        renderer = self._renderer()

        def fake_draw_text_run(text, run_font, **kwargs):
            ruby_groups = kwargs.get('ruby_overlay_groups')
            if ruby_groups is not None:
                ruby_groups.append({'page_index': 0, 'x': 10, 'start_y': 20, 'end_y': 42, 'base_len': len(text)})
            overlay_cells = kwargs.get('overlay_cells')
            if overlay_cells is not None:
                overlay_cells.append((0, 10, 20, '本'))

        with mock.patch.object(renderer, 'draw_text_run', side_effect=fake_draw_text_run),              mock.patch.object(renderer, 'draw_split_ruby_groups') as ruby_mock,              mock.patch.object(renderer, 'draw_emphasis_marks_cells') as emphasis_mock,              mock.patch.object(renderer, 'draw_side_lines_cells') as side_line_mock:
            renderer.draw_runs([
                {'text': '併用本文です', 'ruby': 'るび', 'side_line': 'double'},
            ], default_font=renderer.font)

        ruby_mock.assert_called_once()
        emphasis_mock.assert_not_called()
        side_line_mock.assert_called_once_with(mock.ANY, 'double', ruby_text='るび', emphasis_kind='')


    def test_draw_runs_ruby_overlay_post_processing_uses_compact_overlay_mask(self):
        renderer = self._renderer()

        def fake_draw_text_run(text, run_font, **kwargs):
            ruby_groups = kwargs.get('ruby_overlay_groups')
            if ruby_groups is not None:
                ruby_groups.append({'page_index': 0, 'x': 10, 'start_y': 20, 'end_y': 42, 'base_len': len(text)})
            overlay_cells = kwargs.get('overlay_cells')
            if overlay_cells is not None:
                overlay_cells.append((0, 10, 20, '本'))

        with mock.patch.object(renderer, 'draw_text_run', side_effect=fake_draw_text_run),              mock.patch.object(renderer, 'draw_split_ruby_groups') as ruby_mock,              mock.patch.object(renderer, 'draw_emphasis_marks_cells') as emphasis_mock,              mock.patch.object(renderer, 'draw_side_lines_cells') as side_line_mock:
            renderer.draw_runs([
                {'text': '併用本文です', 'ruby': 'るび', 'emphasis': '白丸傍点', 'side_line': 'double'},
            ], default_font=renderer.font)

        ruby_mock.assert_called_once()
        emphasis_mock.assert_called_once()
        side_line_mock.assert_called_once_with(mock.ANY, 'double', ruby_text='るび', emphasis_kind='白丸傍点')
        self.assertTrue(emphasis_mock.call_args.kwargs['prefer_left'])

    def test_draw_text_run_can_capture_compact_ruby_overlay_groups(self):
        renderer = self._renderer()
        ruby_groups = []
        start_x = renderer.curr_x
        start_y = renderer.curr_y

        renderer.draw_text_run('本文', renderer.font, ruby_overlay_groups=ruby_groups)

        self.assertEqual(ruby_groups, [
            {'page_index': 0, 'x': start_x, 'start_y': start_y, 'end_y': start_y + renderer.args.font_size + 2, 'base_len': 2},
        ])

    def test_draw_text_run_can_capture_compact_overlay_cells(self):
        renderer = self._renderer()
        overlay_cells = []
        start_x = renderer.curr_x
        start_y = renderer.curr_y

        renderer.draw_text_run('本文', renderer.font, overlay_cells=overlay_cells)

        self.assertEqual(overlay_cells, [
            (0, start_x, start_y, '本'),
            (0, start_x, start_y + renderer.args.font_size + 2, '文'),
        ])

    def test_draw_text_run_can_omit_unused_segment_info_fields(self):
        renderer = self._renderer()
        ruby_infos = []
        emphasis_infos = []

        renderer.draw_text_run('本文', renderer.font, segment_infos=ruby_infos, segment_info_needs_base_len=True, segment_info_needs_cell_text=False)
        renderer._new_blank_page()
        renderer.draw_text_run('本文', renderer.font, segment_infos=emphasis_infos, segment_info_needs_base_len=False, segment_info_needs_cell_text=True)

        self.assertTrue(ruby_infos)
        self.assertIn('base_len', ruby_infos[0])
        self.assertNotIn('cell_text', ruby_infos[0])

        self.assertTrue(emphasis_infos)
        self.assertNotIn('base_len', emphasis_infos[0])
        self.assertIn('cell_text', emphasis_infos[0])

    def test_render_text_blocks_to_images_handles_code_font_failure_and_pagebreak(self):
        args = self._args(width=180, height=180, font_size=20, ruby_size=10, line_spacing=28)
        progress = []
        real_load = core.load_truetype_font

        def fake_load(font_value, size, *load_args, **load_kwargs):
            if font_value == 'code-font.ttf':
                raise OSError('bad code font')
            return real_load(font_value, size, *load_args, **load_kwargs)

        blocks = [
            {'kind': 'paragraph', 'runs': [{'text': '一頁目'}], 'blank_before': 1},
            {'kind': 'pagebreak'},
            {'kind': 'paragraph', 'runs': [{'text': '二頁目'}], 'blank_before': 1},
        ]
        with mock.patch.object(core, 'get_code_font_value', return_value='code-font.ttf'), \
             mock.patch.object(core, 'load_truetype_font', side_effect=fake_load):
            pages = core._render_text_blocks_to_images(
                blocks,
                str(FONT_PATH),
                args,
                progress_cb=lambda cur, total, msg: progress.append((cur, total, msg)),
            )

        self.assertGreaterEqual(len(pages), 2)
        self.assertTrue(any('テキストを描画中' in msg for _, _, msg in progress))
        self.assertIn('テキスト描画が完了しました。', progress[-1][2])


if __name__ == '__main__':
    unittest.main()
