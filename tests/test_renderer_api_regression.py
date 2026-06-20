from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from PIL import Image, ImageChops

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

    def test_render_text_blocks_preserves_leading_blank_before_first_content(self):
        args = core.ConversionArgs(width=160, height=220, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        blocks_without_blank = core._blocks_from_plain_text('本文')
        blocks_with_blank = core._blocks_from_plain_text('\n本文')
        blocks_with_two_blanks = core._blocks_from_plain_text('\n\n本文')
        blocks_with_three_blanks = core._blocks_from_plain_text('\n\n\n本文')
        self.assertEqual(blocks_with_blank[0].get('kind'), 'blank')

        def draw_starts(blocks):
            starts = []
            original_renderer = core._VerticalPageRenderer

            class TrackingRenderer(original_renderer):
                def draw_runs(self, runs, *draw_args, **draw_kwargs):
                    if runs:
                        starts.append((self.curr_x, self.curr_y))
                    return super().draw_runs(runs, *draw_args, **draw_kwargs)

            with patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
                core._render_text_blocks_to_page_entries(blocks, FONT_PATH, args)
            return starts

        baseline_starts = draw_starts(blocks_without_blank)
        leading_blank_starts = draw_starts(blocks_with_blank)
        leading_two_blank_starts = draw_starts(blocks_with_two_blanks)
        leading_three_blank_starts = draw_starts(blocks_with_three_blanks)
        in_document_blank_starts = draw_starts(core._blocks_from_plain_text('あ\n\nい'))
        in_document_two_blank_starts = draw_starts(core._blocks_from_plain_text('あ\n\n\nい'))

        self.assertEqual(len(baseline_starts), 1)
        self.assertEqual(len(leading_blank_starts), 1)
        self.assertEqual(len(leading_two_blank_starts), 1)
        self.assertEqual(len(leading_three_blank_starts), 1)
        self.assertGreaterEqual(len(in_document_blank_starts), 2)
        self.assertGreaterEqual(len(in_document_two_blank_starts), 2)

        baseline_x, baseline_y = baseline_starts[0]
        leading_blank_x, leading_blank_y = leading_blank_starts[0]
        leading_two_blank_x, leading_two_blank_y = leading_two_blank_starts[0]
        leading_three_blank_x, leading_three_blank_y = leading_three_blank_starts[0]
        in_document_blank_delta = in_document_blank_starts[0][0] - in_document_blank_starts[1][0]
        in_document_two_blank_delta = in_document_two_blank_starts[0][0] - in_document_two_blank_starts[1][0]

        self.assertEqual(leading_blank_x, baseline_x - args.line_spacing)
        self.assertEqual(leading_two_blank_x, baseline_x - args.line_spacing * 2)
        self.assertEqual(leading_three_blank_x, baseline_x - args.line_spacing * 3)
        self.assertEqual(leading_blank_y, baseline_y)
        self.assertEqual(leading_two_blank_y, baseline_y)
        self.assertEqual(leading_three_blank_y, baseline_y)
        self.assertEqual(in_document_blank_delta, args.line_spacing * 2)
        self.assertEqual(in_document_two_blank_delta, args.line_spacing * 3)


    def test_blank_lines_after_aozora_pagebreak_are_preserved_on_fresh_page(self):
        args = core.ConversionArgs(width=160, height=220, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        blocks_without_blank = core._blocks_from_plain_text('一\n［＃改ページ］\n二')
        blocks_with_blank = core._blocks_from_plain_text('一\n［＃改ページ］\n\n二')
        blocks_with_two_blanks = core._blocks_from_plain_text('一\n［＃改ページ］\n\n\n二')

        def draw_starts(blocks):
            starts = []
            original_renderer = core._VerticalPageRenderer

            class TrackingRenderer(original_renderer):
                def draw_runs(self, runs, *draw_args, **draw_kwargs):
                    if runs:
                        starts.append((self.curr_x, self.curr_y, len(self.page_entries)))
                    return super().draw_runs(runs, *draw_args, **draw_kwargs)

            with patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
                core._render_text_blocks_to_page_entries(blocks, FONT_PATH, args)
            return starts

        baseline_starts = draw_starts(blocks_without_blank)
        one_blank_starts = draw_starts(blocks_with_blank)
        two_blank_starts = draw_starts(blocks_with_two_blanks)

        self.assertEqual(len(baseline_starts), 2)
        self.assertEqual(len(one_blank_starts), 2)
        self.assertEqual(len(two_blank_starts), 2)
        baseline_x = baseline_starts[1][0]
        self.assertEqual(one_blank_starts[1][0], baseline_x - args.line_spacing)
        self.assertEqual(two_blank_starts[1][0], baseline_x - args.line_spacing * 2)
        self.assertEqual(one_blank_starts[1][1], baseline_starts[1][1])
        self.assertEqual(two_blank_starts[1][1], baseline_starts[1][1])


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


    def test_draw_text_run_consumes_token_at_overindented_wrapped_column_top(self):
        args = core.ConversionArgs(width=160, height=120, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        wrap_indent_chars = 6
        wrap_indent_step = wrap_indent_chars * (args.font_size + 2)
        renderer.curr_y = args.margin_t + wrap_indent_step
        start_x = renderer.curr_x

        renderer.draw_text_run('（', renderer.font, wrap_indent_chars=wrap_indent_chars)

        self.assertEqual(renderer.curr_x, start_x - args.line_spacing)
        expected_indent_step = renderer._clamp_indent_step_height(wrap_indent_step)
        self.assertEqual(renderer.curr_y, args.margin_t + expected_indent_step + args.font_size + 2)
        self.assertTrue(renderer.has_drawn_on_page)


    def test_draw_text_run_overlarge_wrap_indent_keeps_glyph_visible(self):
        args = core.ConversionArgs(width=160, height=120, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        renderer.advance_column(1, indent_chars=99)

        renderer.draw_text_run('「大きな字下げでも見える', renderer.font, wrap_indent_chars=99)

        white = Image.new('L', renderer.img.size, 255)
        bbox = ImageChops.difference(renderer.img, white).getbbox()
        self.assertIsNotNone(bbox)
        assert bbox is not None
        self.assertLess(bbox[1], int(args.height * 0.80))
        self.assertLessEqual(renderer.curr_y, args.height + args.font_size + 2)
        self.assertTrue(renderer.has_drawn_on_page)

    def test_draw_text_run_overlarge_indent_starts_at_column_head_on_x4_page(self):
        args = core.ConversionArgs(width=480, height=800, font_size=26, ruby_size=12, line_spacing=41, output_format='xtc')
        renderer = self._load_renderer(args)
        renderer.advance_column(1, indent_chars=99)

        renderer.draw_text_run('「大きな折り返し字下げでも列頭付近から始める', renderer.font, wrap_indent_chars=99)

        white = Image.new('L', renderer.img.size, 255)
        bbox = ImageChops.difference(renderer.img, white).getbbox()
        self.assertIsNotNone(bbox)
        assert bbox is not None
        self.assertLess(bbox[1], args.margin_t + (args.font_size + 2))
        self.assertEqual(renderer._clamp_indent_step_height(99 * (args.font_size + 2)), 0)
        self.assertTrue(renderer.has_drawn_on_page)

    def test_overlarge_indent_is_ignored_on_tall_pages_too(self):
        for height in (800, 1200, 2000, 4000):
            with self.subTest(height=height):
                args = core.ConversionArgs(width=480, height=height, font_size=26, ruby_size=12, line_spacing=41, output_format='xtc')
                renderer = self._load_renderer(args)
                renderer.advance_column(1, indent_chars=99)

                renderer.draw_text_run('「大きな折り返し字下げでも列頭付近から始める', renderer.font, wrap_indent_chars=99)

                white = Image.new('L', renderer.img.size, 255)
                bbox = ImageChops.difference(renderer.img, white).getbbox()
                self.assertIsNotNone(bbox)
                assert bbox is not None
                self.assertLess(bbox[1], args.margin_t + (args.font_size + 2))
                self.assertEqual(renderer._clamp_indent_step_height(99 * (args.font_size + 2)), 0)


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
        core._build_vertical_layout_hints_cached.cache_clear()
        core._build_single_token_vertical_layout_hints.cache_clear()
        with patch.object(core, '_is_line_head_forbidden', wraps=core._is_line_head_forbidden) as line_head,              patch.object(core, '_is_line_end_forbidden', wraps=core._is_line_end_forbidden) as line_end,              patch.object(core, '_is_hanging_punctuation', wraps=core._is_hanging_punctuation) as hanging,              patch.object(core, '_is_continuous_punctuation_pair', wraps=core._is_continuous_punctuation_pair) as pair_check:
            hints = core._build_vertical_layout_hints_cached(('。',))
        core._build_vertical_layout_hints_cached.cache_clear()
        core._build_single_token_vertical_layout_hints.cache_clear()

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



