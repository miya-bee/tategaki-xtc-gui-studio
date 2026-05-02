from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from PIL import Image

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class RendererApiRegressionTests(TestCase):
    def _load_renderer(self, args):
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        return core._VerticalPageRenderer(args, font, ruby_font)

    def test_add_full_page_image_resets_blank_page_without_private_callers(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        renderer.draw_text_run('本文', renderer.font)
        image = Image.new('L', (args.width, args.height), 200)

        renderer.add_full_page_image(image, label='挿絵ページ', page_args=args)

        self.assertEqual(len(renderer.page_entries), 2)
        self.assertEqual([entry['label'] for entry in renderer.page_entries], ['本文ページ', '挿絵ページ'])
        self.assertFalse(renderer.has_drawn_on_page)
        self.assertEqual(renderer.curr_y, args.margin_t)

    def test_has_pending_output_covers_buffered_and_current_page(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        self.assertFalse(renderer.has_pending_output)
        renderer.draw_text_run('本文', renderer.font)
        self.assertTrue(renderer.has_pending_output)
        renderer.flush_current_page()
        self.assertTrue(renderer.has_pending_output)
        renderer.pop_page_entries()
        self.assertFalse(renderer.has_pending_output)

    def test_flush_current_page_reuses_current_image_when_buffering(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        renderer.draw_text_run('本文', renderer.font)
        current_img = renderer.img

        renderer.flush_current_page()

        self.assertEqual(len(renderer.page_entries), 1)
        self.assertIs(renderer.page_entries[0]['image'], current_img)
        self.assertIsNot(renderer.img, current_img)
        self.assertFalse(renderer.has_drawn_on_page)

    def test_draw_text_run_uses_prebuilt_vertical_layout_hints(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_build_vertical_layout_hints', wraps=core._build_vertical_layout_hints) as build_hints, \
             patch.object(core, '_choose_vertical_layout_action_with_hints', wraps=core._choose_vertical_layout_action_with_hints) as choose_with_hints:
            renderer.draw_text_run('（」。本文!?', renderer.font, wrap_indent_chars=1)

        self.assertEqual(build_hints.call_count, 1)
        self.assertGreater(choose_with_hints.call_count, 0)

    def test_epub_code_block_uses_code_font(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        html = '<html><body><pre><code>code sample</code></pre><p>本文</p></body></html>'
        created = []
        original = core._VerticalPageRenderer

        class TrackingRenderer(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.code_font_used = False
                created.append(self)

            def draw_text_run(self, text, run_font, *args, **kwargs):
                if 'code' in text and run_font is self.code_font:
                    self.code_font_used = True
                return super().draw_text_run(text, run_font, *args, **kwargs)

        with patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter.xhtml',
                args,
                font,
                ruby_font,
                bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
                image_map={},
                image_basename_map={},
                css_rules=[],
            )

        self.assertEqual(len(pages), 1)
        self.assertTrue(created)
        self.assertTrue(created[0].code_font_used)


    def test_advance_column_computes_indent_step_once_for_multi_column_move(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(renderer, '_indent_step_height', wraps=renderer._indent_step_height) as mocked_indent_step:
            renderer.advance_column(3, indent_chars=2)

        self.assertEqual(mocked_indent_step.call_count, 1)

    def test_draw_text_run_reuses_wrap_indent_when_plain_draw_overflows(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        renderer.curr_y = args.height - args.margin_b - args.font_size + 1
        start_x = renderer.curr_x

        renderer.draw_text_run('本', renderer.font, wrap_indent_chars=2)

        expected_indent_step = 2 * (args.font_size + 2)
        self.assertEqual(renderer.curr_x, start_x - args.line_spacing)
        self.assertEqual(renderer.curr_y, args.margin_t + expected_indent_step + args.font_size + 2)
        self.assertTrue(renderer.has_drawn_on_page)


    def test_draw_text_run_hang_pair_uses_bottom_guard_before_raw_last_slot(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        renderer.curr_y = args.height - args.margin_b - args.font_size
        start_x = renderer.curr_x

        renderer.draw_text_run('あ。', renderer.font, wrap_indent_chars=1)

        expected_indent_step = args.font_size + 2
        line_step = args.font_size + 2
        self.assertEqual(renderer.curr_x, start_x - args.line_spacing)
        self.assertEqual(renderer.curr_y, args.margin_t + expected_indent_step + (line_step * 2))
        self.assertTrue(renderer.has_drawn_on_page)


    def test_draw_text_run_reuses_remaining_slot_count_across_plain_tokens(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_remaining_vertical_slots', wraps=core._remaining_vertical_slots) as remaining_slots:
            renderer.draw_text_run('本文本文本文', renderer.font)

        self.assertEqual(remaining_slots.call_count, 1)


    def test_draw_text_run_uses_plain_fast_path_without_overlay_capture(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path:
            renderer.draw_text_run('本文本文', renderer.font)

        self.assertEqual(plain_path.call_count, 1)


    def test_draw_text_run_skips_plain_fast_path_when_overlay_capture_is_requested(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = []

        with patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path:
            renderer.draw_text_run('本文本文', renderer.font, overlay_cells=overlay_cells)

        self.assertEqual(plain_path.call_count, 0)
        self.assertTrue(overlay_cells)


    def test_draw_text_run_uses_overlay_fast_path_without_segment_infos(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        ruby_groups = []
        overlay_cells = []

        with patch.object(renderer, '_draw_text_run_plain', wraps=renderer._draw_text_run_plain) as plain_path, \
             patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path:
            renderer.draw_text_run('本文本文', renderer.font, ruby_overlay_groups=ruby_groups, overlay_cells=overlay_cells)

        self.assertEqual(plain_path.call_count, 0)
        self.assertEqual(overlay_path.call_count, 1)
        self.assertTrue(ruby_groups)
        self.assertTrue(overlay_cells)


    def test_draw_text_run_uses_ruby_only_fast_path_without_overlay_cells(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        ruby_groups = []

        with patch.object(renderer, '_draw_text_run_ruby_only', wraps=renderer._draw_text_run_ruby_only) as ruby_path,              patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path:
            renderer.draw_text_run('本文本文', renderer.font, ruby_overlay_groups=ruby_groups)

        self.assertEqual(ruby_path.call_count, 1)
        self.assertEqual(overlay_path.call_count, 0)
        self.assertTrue(ruby_groups)


    def test_draw_text_run_uses_overlay_cells_only_fast_path_without_ruby(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = []

        with patch.object(renderer, '_draw_text_run_overlay_cells_only', wraps=renderer._draw_text_run_overlay_cells_only) as cells_path,              patch.object(renderer, '_draw_text_run_overlay_only', wraps=renderer._draw_text_run_overlay_only) as overlay_path:
            renderer.draw_text_run('本文本文', renderer.font, overlay_cells=overlay_cells)

        self.assertEqual(cells_path.call_count, 1)
        self.assertEqual(overlay_path.call_count, 0)
        self.assertTrue(overlay_cells)



    def test_draw_text_run_uses_segment_only_fast_path_without_overlay_capture(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = []

        with patch.object(renderer, '_draw_text_run_segment_only', wraps=renderer._draw_text_run_segment_only) as segment_path:
            renderer.draw_text_run('本文本文', renderer.font, segment_infos=segment_infos)

        self.assertEqual(segment_path.call_count, 1)
        self.assertTrue(segment_infos)


    def test_draw_text_run_skips_segment_only_fast_path_when_overlay_capture_is_requested(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = []
        overlay_cells = []

        with patch.object(renderer, '_draw_text_run_segment_only', wraps=renderer._draw_text_run_segment_only) as segment_path:
            renderer.draw_text_run('本文本文', renderer.font, segment_infos=segment_infos, overlay_cells=overlay_cells)

        self.assertEqual(segment_path.call_count, 0)
        self.assertTrue(segment_infos)
        self.assertTrue(overlay_cells)


    def test_draw_text_run_uses_segment_and_ruby_only_fast_path(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = []
        ruby_groups = []

        with patch.object(renderer, '_draw_text_run_segment_and_ruby_only', wraps=renderer._draw_text_run_segment_and_ruby_only) as fast_path, \
             patch.object(renderer, '_draw_text_run_segment_only', wraps=renderer._draw_text_run_segment_only) as segment_only:
            renderer.draw_text_run('本文本文', renderer.font, segment_infos=segment_infos, ruby_overlay_groups=ruby_groups)

        self.assertEqual(fast_path.call_count, 1)
        self.assertEqual(segment_only.call_count, 0)
        self.assertTrue(segment_infos)
        self.assertTrue(ruby_groups)


    def test_draw_text_run_uses_segment_and_overlay_cells_only_fast_path(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = []
        overlay_cells = []

        with patch.object(renderer, '_draw_text_run_segment_and_overlay_cells_only', wraps=renderer._draw_text_run_segment_and_overlay_cells_only) as fast_path, \
             patch.object(renderer, '_draw_text_run_segment_only', wraps=renderer._draw_text_run_segment_only) as segment_only:
            renderer.draw_text_run('本文本文', renderer.font, segment_infos=segment_infos, overlay_cells=overlay_cells)

        self.assertEqual(fast_path.call_count, 1)
        self.assertEqual(segment_only.call_count, 0)
        self.assertTrue(segment_infos)
        self.assertTrue(overlay_cells)


    def test_draw_text_run_uses_segment_and_overlay_mixed_fast_path(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = []
        ruby_groups = []
        overlay_cells = []

        with patch.object(renderer, '_draw_text_run_segment_and_overlay_mixed', wraps=renderer._draw_text_run_segment_and_overlay_mixed) as mixed_path, \
             patch.object(renderer, '_draw_text_run_segment_and_ruby_only', wraps=renderer._draw_text_run_segment_and_ruby_only) as ruby_only, \
             patch.object(renderer, '_draw_text_run_segment_and_overlay_cells_only', wraps=renderer._draw_text_run_segment_and_overlay_cells_only) as overlay_only:
            renderer.draw_text_run(
                '本文本文',
                renderer.font,
                segment_infos=segment_infos,
                ruby_overlay_groups=ruby_groups,
                overlay_cells=overlay_cells,
            )

        self.assertEqual(mixed_path.call_count, 1)
        self.assertEqual(ruby_only.call_count, 0)
        self.assertEqual(overlay_only.call_count, 0)
        self.assertTrue(segment_infos)
        self.assertTrue(ruby_groups)
        self.assertTrue(overlay_cells)


    def test_draw_text_run_uses_direct_single_char_layout_hints(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_build_single_token_vertical_layout_hints', wraps=core._build_single_token_vertical_layout_hints) as single_hint,              patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_text_run('本', renderer.font)

        self.assertEqual(single_hint.call_count, 1)
        self.assertEqual(tokenize_cached.call_count, 0)


    def test_draw_text_run_single_char_overlay_capture_still_uses_direct_layout_hints(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = []

        with patch.object(core, '_build_single_token_vertical_layout_hints', wraps=core._build_single_token_vertical_layout_hints) as single_hint,              patch.object(core, '_tokenize_vertical_text_cached', wraps=core._tokenize_vertical_text_cached) as tokenize_cached:
            renderer.draw_text_run('本', renderer.font, overlay_cells=overlay_cells)

        self.assertEqual(single_hint.call_count, 1)
        self.assertEqual(tokenize_cached.call_count, 0)
        self.assertTrue(overlay_cells)


    def test_build_vertical_layout_hints_uses_direct_two_token_fast_path(self):
        core.clear_font_entry_cache()

        with patch.object(core, '_build_two_token_vertical_layout_hints', wraps=core._build_two_token_vertical_layout_hints) as two_hint:
            hints = core._build_vertical_layout_hints(('本', '文'))

        self.assertEqual(two_hint.call_count, 1)
        self.assertEqual(len(hints['protected_group_len']), 2)


    def test_build_vertical_layout_hints_uses_direct_three_token_fast_path(self):
        core.clear_font_entry_cache()

        with patch.object(core, '_build_three_token_vertical_layout_hints', wraps=core._build_three_token_vertical_layout_hints) as three_hint:
            hints = core._build_vertical_layout_hints(('本', '文', '中'))

        self.assertEqual(three_hint.call_count, 1)
        self.assertEqual(len(hints['protected_group_len']), 3)


    def test_build_vertical_layout_hints_uses_direct_four_token_fast_path(self):
        core.clear_font_entry_cache()

        with patch.object(core, '_build_four_token_vertical_layout_hints', wraps=core._build_four_token_vertical_layout_hints) as four_hint:
            hints = core._build_vertical_layout_hints(('本', '文', 'で', 'す'))

        self.assertEqual(four_hint.call_count, 1)
        self.assertEqual(len(hints['protected_group_len']), 4)


    def test_draw_char_tate_skips_draw_spec_for_ascii_center_glyph(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_char_tate(renderer.draw, 'A', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(compute_spec.call_count, 0)


    def test_draw_char_tate_reuses_preclassified_kind_for_uncached_spec(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_resolve_cacheable_font_spec', return_value=None), \
             patch.object(core, '_classify_tate_draw_char', wraps=core._classify_tate_draw_char) as classify:
            core.draw_char_tate(renderer.draw, '漢', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(classify.call_count, 1)


    def test_draw_char_tate_reuses_preclassified_kind_for_cached_spec(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        core._cached_tate_draw_spec.cache_clear()

        with patch.object(core, '_classify_tate_draw_char', wraps=core._classify_tate_draw_char) as classify:
            core.draw_char_tate(renderer.draw, '漢', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(classify.call_count, 1)

    def test_draw_char_tate_skips_draw_spec_for_default_unmapped_glyph(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_char_tate(renderer.draw, '漢', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(compute_spec.call_count, 0)



    def test_draw_char_tate_uses_dot_leader_helper_without_draw_spec_for_ellipsis(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, 'draw_vertical_dot_leader', wraps=core.draw_vertical_dot_leader) as dot_leader, \
             patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_char_tate(renderer.draw, '…', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(dot_leader.call_count, 1)
        self.assertEqual(compute_spec.call_count, 0)


    def test_draw_char_tate_skips_draw_spec_for_unmapped_punctuation_glyph(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_char_tate(renderer.draw, '，', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(compute_spec.call_count, 0)


    def test_draw_char_tate_uses_punctuation_helper_for_mapped_punctuation_glyph(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_resolve_tate_punctuation_draw', wraps=core._resolve_tate_punctuation_draw) as resolve_punct, \
             patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_char_tate(renderer.draw, '、', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(resolve_punct.call_count, 1)
        self.assertEqual(compute_spec.call_count, 0)


    def test_draw_hanging_punctuation_skips_draw_spec_for_unmapped_punctuation_glyph(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_hanging_punctuation(renderer.draw, '，', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size, args.height)

        self.assertEqual(compute_spec.call_count, 0)


    def test_draw_hanging_punctuation_uses_punctuation_helper_for_mapped_punctuation_glyph(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_resolve_tate_punctuation_draw', wraps=core._resolve_tate_punctuation_draw) as resolve_punct, \
             patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_hanging_punctuation(renderer.draw, '。', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size, args.height)

        self.assertEqual(resolve_punct.call_count, 1)
        self.assertEqual(compute_spec.call_count, 0)


    def test_draw_char_tate_skips_draw_spec_for_small_kana_glyph(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_char_tate(renderer.draw, 'ぁ', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(compute_spec.call_count, 0)


    def test_draw_char_tate_uses_horizontal_bracket_helper_without_draw_spec(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        with patch.object(core, '_resolve_horizontal_bracket_draw', wraps=core._resolve_horizontal_bracket_draw) as resolve_bracket, \
             patch.object(core, '_compute_tate_draw_spec', wraps=core._compute_tate_draw_spec) as compute_spec:
            core.draw_char_tate(renderer.draw, '「', (renderer.curr_x, renderer.curr_y), renderer.font, args.font_size)

        self.assertEqual(resolve_bracket.call_count, 1)
        self.assertEqual(compute_spec.call_count, 0)



    def test_resolve_default_tate_draw_reuses_cached_helper_for_cacheable_font(self):
        args = core.ConversionArgs(width=160, height=200, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        core._cached_default_tate_draw.cache_clear()

        with patch.object(core, '_cached_resolve_vertical_glyph_char', wraps=core._cached_resolve_vertical_glyph_char) as resolve_cached:
            first = core._resolve_default_tate_draw('…', renderer.font)
            second = core._resolve_default_tate_draw('…', renderer.font)

        self.assertEqual(first, '︙')
        self.assertEqual(second, '︙')
        self.assertEqual(resolve_cached.call_count, 1)


    def test_build_vertical_layout_hints_reuses_tuple_input_without_copy(self):
        tokens = ('本', '文')
        captured = []
        original = core._build_vertical_layout_hints_cached

        def record(tokens_arg):
            captured.append(tokens_arg)
            return original(tokens_arg)

        with patch.object(core, '_build_vertical_layout_hints_cached', side_effect=record):
            hints = core._build_vertical_layout_hints(tokens)

        self.assertTrue(hints['protected_group_len'])
        self.assertEqual(len(captured), 1)
        self.assertIs(captured[0], tokens)


    def test_build_vertical_layout_hints_single_token_uses_direct_fast_path(self):
        with patch.object(core, '_is_line_head_forbidden', wraps=core._is_line_head_forbidden) as line_head,              patch.object(core, '_is_line_end_forbidden', wraps=core._is_line_end_forbidden) as line_end,              patch.object(core, '_is_hanging_punctuation', wraps=core._is_hanging_punctuation) as hanging,              patch.object(core, '_is_continuous_punctuation_pair', wraps=core._is_continuous_punctuation_pair) as pair_check:
            hints = core._build_vertical_layout_hints_cached(('。',))

        self.assertEqual(line_head.call_count, 1)
        self.assertEqual(line_end.call_count, 1)
        self.assertEqual(hanging.call_count, 1)
        self.assertEqual(pair_check.call_count, 0)
        self.assertEqual(hints['continuous_pair_with_next'], (False,))
        self.assertEqual(hints['protected_group_len'], (1,))


    def test_draw_text_run_refreshes_draw_target_after_page_flush_wrap(self):
        args = core.ConversionArgs(width=60, height=46, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        draw_ids = []

        def fake_draw_char(draw, char, pos_tuple, font, f_size, **kwargs):
            draw_ids.append(id(draw))

        with patch.object(core, 'draw_char_tate', side_effect=fake_draw_char):
            renderer.draw_text_run('本文', renderer.font)

        self.assertEqual(len(draw_ids), 2)
        self.assertNotEqual(draw_ids[0], draw_ids[1])
        self.assertEqual(len(renderer.page_entries), 1)
        self.assertTrue(renderer.has_drawn_on_page)



