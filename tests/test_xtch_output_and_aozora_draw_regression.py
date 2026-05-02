import struct
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class XtchOutputAndAozoraDrawRegressionTests(unittest.TestCase):
    def _load_renderer(self, args):
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        return core._VerticalPageRenderer(args, font, ruby_font)

    def test_page_image_to_xt_bytes_selects_xth_for_xtch(self):
        img = Image.new('L', (4, 4), 255)
        xtc_args = core.ConversionArgs(width=4, height=4, output_format='xtc')
        xtch_args = core.ConversionArgs(width=4, height=4, output_format='xtch')

        xtc_blob = core.page_image_to_xt_bytes(img, 4, 4, xtc_args)
        xtch_blob = core.page_image_to_xt_bytes(img, 4, 4, xtch_args)

        self.assertEqual(xtc_blob[:4], b'XTG\x00')
        self.assertEqual(xtch_blob[:4], b'XTH\x00')
        self.assertNotEqual(xtc_blob, xtch_blob)

    def test_build_xtc_writes_xtch_container_header(self):
        args = core.ConversionArgs(width=4, height=4, output_format='xtch')
        page_blob = core.page_image_to_xt_bytes(Image.new('L', (4, 4), 255), 4, 4, args)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtch'
            core.build_xtc([page_blob], out_path, 4, 4, output_format='xtch')
            data = out_path.read_bytes()

        self.assertEqual(data[:4], b'XTCH')
        self.assertEqual(struct.unpack_from('<H', data, 6)[0], 1)
        self.assertIn(page_blob, data)

    def test_build_xtc_self_verifies_written_pages_before_publish(self):
        args = core.ConversionArgs(width=4, height=4, output_format='xtch')
        page_blob = core.page_image_to_xt_bytes(Image.new('L', (4, 4), 255), 4, 4, args)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtch'
            core.build_xtc([page_blob, page_blob], out_path, 4, 4, output_format='xtch')
            verified = core._verify_xt_container_file(out_path, 4, 4, 'xtch', expected_count=2)

        self.assertEqual(verified, 2)

    def test_build_xtc_self_verification_rejects_truncated_temp_output(self):
        args = core.ConversionArgs(width=4, height=4, output_format='xtch')
        page_blob = core.page_image_to_xt_bytes(Image.new('L', (4, 4), 255), 4, 4, args)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtch'
            out_path.write_bytes(b'OLD')

            original_atomic = core._atomic_replace_xt_container

            def broken_atomic(dst_path, writer, verifier=None):
                def broken_writer(handle):
                    writer(handle)
                    handle.truncate(max(0, handle.tell() - len(page_blob)))
                return original_atomic(dst_path, broken_writer, verifier=verifier)

            with mock.patch.object(core, '_atomic_replace_xt_container', side_effect=broken_atomic):
                with self.assertRaisesRegex(RuntimeError, '自己検証に失敗しました'):
                    core.build_xtc([page_blob, page_blob], out_path, 4, 4, output_format='xtch')
            self.assertEqual(b'OLD', out_path.read_bytes())

    def test_verify_xt_container_file_rejects_trailing_garbage_after_last_page(self):
        args = core.ConversionArgs(width=4, height=4, output_format='xtch')
        page_blob = core.page_image_to_xt_bytes(Image.new('L', (4, 4), 255), 4, 4, args)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtch'
            core.build_xtc([page_blob, page_blob], out_path, 4, 4, output_format='xtch')
            with open(out_path, 'ab') as fh:
                fh.write(b'GARBAGE')
            with self.assertRaisesRegex(RuntimeError, '最終ページ終端とファイルサイズが一致しません'):
                core._verify_xt_container_file(out_path, 4, 4, 'xtch', expected_count=2)

    def test_build_xtc_does_not_replace_existing_file_when_atomic_swap_fails(self):
        args = core.ConversionArgs(width=4, height=4, output_format='xtch')
        page_blob = core.page_image_to_xt_bytes(Image.new('L', (4, 4), 255), 4, 4, args)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtch'
            out_path.write_bytes(b'OLD')
            with mock.patch.object(core, '_atomic_replace_xt_container', side_effect=RuntimeError('abort mid write')):
                with self.assertRaisesRegex(RuntimeError, 'abort mid write'):
                    core.build_xtc([page_blob, page_blob], out_path, 4, 4, output_format='xtch')
            self.assertEqual(b'OLD', out_path.read_bytes())

    def test_xtc_spooled_pages_finalize_writes_xtch_container_header(self):
        args = core.ConversionArgs(width=4, height=4, output_format='xtch')
        page_blob = core.page_image_to_xt_bytes(Image.new('L', (4, 4), 170), 4, 4, args)
        spool = core.XTCSpooledPages()
        try:
            spool.add_blob(page_blob)
            with tempfile.TemporaryDirectory() as tmpdir:
                out_path = Path(tmpdir) / 'spooled.xtch'
                spool.finalize(out_path, 4, 4, output_format='xtch')
                data = out_path.read_bytes()
            self.assertEqual(data[:4], b'XTCH')
            self.assertIn(page_blob, data)
        finally:
            spool.cleanup()

    def test_xtc_spooled_pages_finalize_preserves_existing_file_when_atomic_swap_fails(self):
        args = core.ConversionArgs(width=4, height=4, output_format='xtch')
        page_blob = core.page_image_to_xt_bytes(Image.new('L', (4, 4), 170), 4, 4, args)
        spool = core.XTCSpooledPages()
        try:
            spool.add_blob(page_blob)
            spool.add_blob(page_blob)
            with tempfile.TemporaryDirectory() as tmpdir:
                out_path = Path(tmpdir) / 'spooled.xtch'
                out_path.write_bytes(b'OLD')
                with mock.patch.object(core, '_atomic_replace_xt_container', side_effect=RuntimeError('abort mid write')):
                    with self.assertRaisesRegex(RuntimeError, 'abort mid write'):
                        spool.finalize(out_path, 4, 4, output_format='xtch')
                self.assertEqual(b'OLD', out_path.read_bytes())
        finally:
            spool.cleanup()

    def test_draw_emphasis_marks_places_marker_on_requested_side(self):
        args = core.ConversionArgs(width=120, height=160, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = [{'page_index': 0, 'x': 50, 'y': 20, 'cell_text': '漢'}]

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def textbbox(self, xy, text, font=None):
                return (0, 0, 8, 8)

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, fill))

        right_draw = DummyDraw()
        left_draw = DummyDraw()

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, right_draw)):
            renderer.draw_emphasis_marks(segment_infos, '白丸傍点')
        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, left_draw)):
            renderer.draw_emphasis_marks(segment_infos, '白丸傍点', prefer_left=True)


        self.assertEqual(len(right_draw.calls), 1)
        self.assertEqual(len(left_draw.calls), 1)
        self.assertGreater(right_draw.calls[0][0][0], segment_infos[0]['x'])
        self.assertLess(left_draw.calls[0][0][0], segment_infos[0]['x'])

    def test_draw_emphasis_marks_reuses_marker_metrics_within_same_call(self):
        args = core.ConversionArgs(width=120, height=160, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = [
            {'page_index': 0, 'x': 50, 'y': 20, 'cell_text': '漢'},
            {'page_index': 0, 'x': 50, 'y': 44, 'cell_text': '字'},
        ]

        class DummyFont:
            def __init__(self):
                self.calls = 0

            def getbbox(self, text):
                self.calls += 1
                return (0, 0, 8, 8)

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, fill))

        dummy_font = DummyFont()
        dummy_draw = DummyDraw()
        renderer._emphasis_font_cache_key = ('', max(8, int(round(args.font_size * 0.48))), id(renderer.font))
        renderer._emphasis_font_cache = dummy_font
        renderer._emphasis_metrics_cache.clear()

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, dummy_draw)):
            renderer.draw_emphasis_marks(segment_infos, '白丸傍点')

        self.assertEqual(dummy_font.calls, 1)
        self.assertEqual(len(dummy_draw.calls), 2)


    def test_draw_split_ruby_groups_reuses_page_draw_within_same_page(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        grouped = [
            {'page_index': 0, 'x': 40, 'start_y': 20, 'end_y': 20, 'base_len': 1},
            {'page_index': 0, 'x': 40, 'start_y': 44, 'end_y': 44, 'base_len': 1},
        ]

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())) as get_draw_mock:
            with mock.patch.object(core, 'draw_char_tate'):
                renderer.draw_split_ruby_groups(grouped, 'ルビ')

        self.assertEqual(get_draw_mock.call_count, 1)

    def test_draw_split_ruby_groups_single_segment_skips_split_helper(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        grouped = [
            {'page_index': 0, 'x': 40, 'start_y': 20, 'end_y': 44, 'base_len': 2},
        ]

        with mock.patch.object(core, '_split_ruby_text_segments', side_effect=AssertionError('split helper should not run for single segment')):
            with mock.patch.object(renderer, '_ruby_group_capacity', side_effect=AssertionError('capacity helper should not run for single segment')):
                with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())):
                    with mock.patch.object(core, 'draw_char_tate') as draw_char_mock:
                        renderer.draw_split_ruby_groups(grouped, 'ルビ')

        self.assertEqual(draw_char_mock.call_count, len('ルビ'))

    def test_draw_split_ruby_groups_clamps_ruby_glyph_bbox_to_effective_bottom_margin(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_t=10,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        guarded_bottom_y = args.height - effective_bottom
        last_legal_y = guarded_bottom_y - args.font_size
        grouped = [{'page_index': 0, 'x': 40, 'start_y': last_legal_y, 'end_y': last_legal_y, 'base_len': 1}]

        drawn = []
        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())), \
             mock.patch.object(core, '_get_text_bbox', return_value=(0, 5, 8, 24)), \
             mock.patch.object(core, 'draw_char_tate', side_effect=lambda _draw, char, pos, _font, f_size, **_kwargs: drawn.append((char, pos, f_size))):
            renderer.draw_split_ruby_groups(grouped, '底')

        self.assertEqual(len(drawn), 1)
        _char, pos, _size = drawn[0]
        self.assertGreaterEqual(pos[1] + 5, args.margin_t)
        self.assertLessEqual(pos[1] + 24, guarded_bottom_y)

    def test_draw_split_ruby_groups_clamps_ruby_glyph_bbox_inside_canvas_width(self):
        args = core.ConversionArgs(
            width=60,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_t=10,
            margin_b=12,
            margin_r=0,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        grouped = [{'page_index': 0, 'x': 54, 'start_y': 20, 'end_y': 20, 'base_len': 1}]

        drawn = []
        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())), \
             mock.patch.object(core, '_get_text_bbox', return_value=(-3, 0, 11, 9)), \
             mock.patch.object(core, 'draw_char_tate', side_effect=lambda _draw, char, pos, _font, f_size, **_kwargs: drawn.append((char, pos, f_size))):
            renderer.draw_split_ruby_groups(grouped, '右')

        self.assertEqual(len(drawn), 1)
        _char, pos, _size = drawn[0]
        self.assertGreaterEqual(pos[0] - 3, 0)
        self.assertLessEqual(pos[0] + 11, args.width)

    def test_draw_emphasis_marks_cells_reuses_page_draw_within_same_page(self):
        args = core.ConversionArgs(width=120, height=160, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = [
            (0, 50, 20, '漢'),
            (0, 50, 44, '字'),
        ]

        class DummyDraw:
            def text(self, xy, text, font=None, fill=None):
                pass

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, DummyDraw())) as get_draw_mock:
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点')

        self.assertEqual(get_draw_mock.call_count, 1)

    def test_draw_emphasis_marks_cells_places_mark_on_expected_side(self):
        args = core.ConversionArgs(width=120, height=160, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = [
            (0, 50, 20, '漢'),
        ]

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, fill))

        right_draw = DummyDraw()
        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, right_draw)):
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点', prefer_left=False)

        left_draw = DummyDraw()
        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, left_draw)):
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点', prefer_left=True)

        self.assertEqual(len(right_draw.calls), 1)
        self.assertEqual(len(left_draw.calls), 1)
        self.assertGreater(right_draw.calls[0][0][0], overlay_cells[0][1])
        self.assertLess(left_draw.calls[0][0][0], overlay_cells[0][1])

    def test_draw_emphasis_marks_cells_reuses_marker_bbox_between_left_and_right(self):
        args = core.ConversionArgs(width=120, height=160, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = [(0, 50, 20, '漢')]

        class DummyFont:
            def __init__(self):
                self.calls = 0

            def getbbox(self, marker):
                self.calls += 1
                return (0, 0, 10, 10)

        class DummyDraw:
            def text(self, xy, text, font=None, fill=None):
                pass

        dummy_font = DummyFont()
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=dummy_font),              mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, DummyDraw())):
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点', prefer_left=False)
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点', prefer_left=True)

        self.assertEqual(dummy_font.calls, 1)

    def test_draw_emphasis_marks_cells_clamps_tall_marker_to_effective_bottom_margin(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        guarded_bottom_y = args.height - effective_bottom
        last_legal_y = guarded_bottom_y - args.font_size
        overlay_cells = [(0, 50, last_legal_y, '漢')]

        class DummyFont:
            def getbbox(self, marker):
                return (0, 0, 12, 32)

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, font, fill))

        dummy_draw = DummyDraw()
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=DummyFont()), \
             mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, dummy_draw)):
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点')

        self.assertEqual(len(dummy_draw.calls), 1)
        mark_y = dummy_draw.calls[0][0][1]
        self.assertLessEqual(mark_y + 32, guarded_bottom_y)
        self.assertGreaterEqual(mark_y, args.margin_t)

    def test_draw_emphasis_marks_cells_keeps_last_marker_inside_effective_bottom_margin(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        last_legal_y = args.height - effective_bottom - args.font_size
        overlay_cells = [(0, 50, last_legal_y, '漢')]

        class DummyFont:
            def getbbox(self, marker):
                return (0, 0, 10, 10)

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, font, fill))

        dummy_draw = DummyDraw()
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=DummyFont()), \
             mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, dummy_draw)):
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点')

        self.assertEqual(len(dummy_draw.calls), 1)
        mark_y = dummy_draw.calls[0][0][1]
        self.assertLessEqual(mark_y + 10, args.height - effective_bottom)

    def test_draw_emphasis_marks_cells_clamps_marker_bbox_origin_to_effective_bottom_margin(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        guarded_bottom_y = args.height - effective_bottom
        last_legal_y = guarded_bottom_y - args.font_size
        overlay_cells = [(0, 50, last_legal_y, '漢')]

        class DummyFont:
            def getbbox(self, marker):
                return (-3, 5, 9, 37)

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, font, fill))

        dummy_draw = DummyDraw()
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=DummyFont()), \
             mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, dummy_draw)):
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点')

        self.assertEqual(len(dummy_draw.calls), 1)
        mark_y = dummy_draw.calls[0][0][1]
        self.assertGreaterEqual(mark_y + 5, args.margin_t)
        self.assertLessEqual(mark_y + 37, guarded_bottom_y)

    def test_draw_emphasis_marks_cells_clamps_marker_bbox_inside_canvas_width(self):
        args = core.ConversionArgs(
            width=60,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_l=0,
            margin_r=0,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        overlay_cells = [(0, 40, 30, '漢')]

        class DummyFont:
            def getbbox(self, marker):
                return (-4, 0, 8, 12)

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, font, fill))

        right_draw = DummyDraw()
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=DummyFont()), \
             mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, right_draw)):
            renderer.draw_emphasis_marks_cells(overlay_cells, '白丸傍点', prefer_left=False)

        left_draw = DummyDraw()
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=DummyFont()), \
             mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, left_draw)):
            renderer.draw_emphasis_marks_cells([(0, 0, 30, '漢')], '白丸傍点', prefer_left=True)

        right_x = right_draw.calls[0][0][0]
        left_x = left_draw.calls[0][0][0]
        self.assertGreaterEqual(right_x - 4, 0)
        self.assertLessEqual(right_x + 8, args.width)
        self.assertGreaterEqual(left_x - 4, 0)
        self.assertLessEqual(left_x + 8, args.width)

    def test_bottom_boundary_policy_guards_overlays_but_allows_hanging_punctuation_margin_overhang(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        guarded_bottom_y = args.height - effective_bottom
        last_legal_y = guarded_bottom_y - args.font_size

        # Ruby / emphasis / side-line overlays share the vertical-layout bottom guard.
        ruby_drawn = []
        ruby_group = {'page_index': 0, 'x': 40, 'start_y': last_legal_y, 'end_y': last_legal_y, 'base_len': 1}
        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())), \
             mock.patch.object(core, 'draw_char_tate', side_effect=lambda _draw, char, pos, _font, f_size, **_kwargs: ruby_drawn.append((char, pos, f_size))):
            renderer.draw_split_ruby_groups([ruby_group], '底')
        self.assertEqual(len(ruby_drawn), 1)
        self.assertLessEqual(ruby_drawn[0][1][1] + args.ruby_size, guarded_bottom_y)

        class DummyFont:
            def getbbox(self, marker):
                return (0, 0, 10, 10)

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, font, fill))

        emphasis_draw = DummyDraw()
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=DummyFont()), \
             mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, emphasis_draw)):
            renderer.draw_emphasis_marks_cells([(0, 50, last_legal_y, '漢')], '白丸傍点')
        self.assertEqual(len(emphasis_draw.calls), 1)
        self.assertLessEqual(emphasis_draw.calls[0][0][1] + 10, guarded_bottom_y)

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())), \
             mock.patch.object(renderer, '_draw_single_side_line') as mocked_draw_line:
            renderer.draw_side_lines_cells([(0, 60, last_legal_y, '漢')], 'solid')
        self.assertEqual(mocked_draw_line.call_count, 1)
        self.assertLessEqual(mocked_draw_line.call_args.args[3], guarded_bottom_y)

        # Hanging punctuation is the exception: it may enter the bottom margin,
        # but must still stay inside the physical canvas.
        img = Image.new('L', (args.width, args.height), 255)
        draw = core.create_image_draw(img)
        glyph_img = Image.new('L', (10, 20), 255)
        glyph_mask = Image.new('L', (10, 20), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 0, 8, 19), fill=255)
        pasted = []
        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)), \
             mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)):
            core.draw_hanging_punctuation(draw, '，', (10, last_legal_y), object(), args.font_size, args.height)
        self.assertEqual(len(pasted), 1)
        pasted_bottom = pasted[0][1] + glyph_img.height
        self.assertGreater(pasted_bottom, guarded_bottom_y)
        self.assertLessEqual(pasted_bottom, args.height - 1)

    def test_page_local_overlay_helpers_keep_page_break_y_resets_separate(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_t=10,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        last_legal_y = args.height - effective_bottom - args.font_size

        page_draws = {0: object(), 1: object()}
        draw_to_page = {id(draw): page for page, draw in page_draws.items()}

        def get_page_draw(page_index):
            return None, page_draws[int(page_index)]

        ruby_drawn = []
        ruby_groups = [
            {'page_index': 0, 'x': 40, 'start_y': last_legal_y, 'end_y': last_legal_y, 'base_len': 1},
            {'page_index': 1, 'x': 40, 'start_y': args.margin_t, 'end_y': args.margin_t + args.font_size + 2, 'base_len': 2},
        ]

        def capture_ruby(draw_obj, char, pos, _font, f_size, **_kwargs):
            ruby_drawn.append((draw_to_page[id(draw_obj)], char, pos, f_size))

        with mock.patch.object(renderer, 'get_page_image_draw', side_effect=get_page_draw), \
             mock.patch.object(core, 'draw_char_tate', side_effect=capture_ruby):
            renderer.draw_split_ruby_groups(ruby_groups, '天地人')

        self.assertEqual([page for page, _char, _pos, _size in ruby_drawn], [0, 1, 1])
        self.assertTrue(all(args.margin_t <= pos[1] < args.height - effective_bottom for _page, _char, pos, _size in ruby_drawn))

        class DummyFont:
            def getbbox(self, marker):
                return (0, 0, 10, 10)

        class DummyDraw:
            def __init__(self, page_index):
                self.page_index = page_index
                self.calls = []

            def text(self, xy, text, font=None, fill=None):
                self.calls.append((xy, text, font, fill))

        emphasis_draws = {0: DummyDraw(0), 1: DummyDraw(1)}
        with mock.patch.object(renderer, '_get_emphasis_font', return_value=DummyFont()), \
             mock.patch.object(renderer, 'get_page_image_draw', side_effect=lambda page_index: (None, emphasis_draws[int(page_index)])):
            renderer.draw_emphasis_marks_cells([
                (0, 50, last_legal_y, '漢'),
                (1, 50, args.margin_t, '字'),
                (1, 50, args.margin_t + args.font_size + 2, '文'),
            ], '白丸傍点')

        self.assertEqual(len(emphasis_draws[0].calls), 1)
        self.assertEqual(len(emphasis_draws[1].calls), 2)

        side_line_calls = []
        with mock.patch.object(renderer, 'get_page_image_draw', side_effect=get_page_draw), \
             mock.patch.object(renderer, '_draw_single_side_line', side_effect=lambda draw_obj, x, y1, y2, kind, width=1: side_line_calls.append((draw_to_page[id(draw_obj)], x, y1, y2, kind, width))):
            renderer.draw_side_lines_cells([
                (0, 60, last_legal_y, '漢'),
                (1, 60, args.margin_t, '字'),
                (1, 60, args.margin_t + args.font_size + 2, '文'),
            ], 'solid')

        self.assertEqual([call[0] for call in side_line_calls], [0, 1])
        self.assertLess(side_line_calls[1][2], side_line_calls[1][3])
        self.assertLess(side_line_calls[1][3], side_line_calls[0][3])

        # Hanging punctuation is page-local by construction: each page passes its
        # own canvas height to the low-level clamp.  It may enter bottom margin,
        # but the pasted glyph must remain inside that page canvas.
        glyph_img = Image.new('L', (10, 20), 255)
        glyph_mask = Image.new('L', (10, 20), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 0, 8, 19), fill=255)
        for y_pos in (last_legal_y, args.margin_t):
            draw = core.create_image_draw(Image.new('L', (args.width, args.height), 255))
            pasted = []
            with mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)), \
                 mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)):
                core.draw_hanging_punctuation(draw, '，', (10, y_pos), object(), args.font_size, args.height)
            self.assertEqual(len(pasted), 1)
            self.assertLessEqual(pasted[0][1] + glyph_img.height, args.height - 1)

    def test_draw_side_lines_cells_reuses_page_draw_for_multiple_groups_same_page(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = [
            (0, 60, 20, '漢'),
            (0, 60, 42, '字'),
            (0, 60, 64, ' '),
            (0, 60, 86, '本'),
            (0, 60, 108, '文'),
        ]

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())) as get_draw_mock:
            with mock.patch.object(renderer, '_draw_single_side_line'):
                renderer.draw_side_lines_cells(overlay_cells, 'solid')

        self.assertEqual(get_draw_mock.call_count, 1)

    def test_iter_side_line_spans_cells_iter_matches_list_wrapper(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = [
            (0, 60, 20, '漢'),
            (0, 60, 42, '字'),
            (0, 60, 64, ' '),
            (0, 60, 86, '本'),
            (0, 60, 108, '文'),
        ]

        self.assertEqual(
            list(renderer._iter_side_line_spans_cells_iter(overlay_cells)),
            renderer._iter_side_line_spans_cells(overlay_cells),
        )

    def test_draw_side_lines_cells_uses_span_iterator_helper(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        overlay_cells = [
            (0, 60, 20, '漢'),
            (0, 60, 42, '字'),
        ]

        with mock.patch.object(renderer, '_iter_side_line_spans_cells_iter', wraps=renderer._iter_side_line_spans_cells_iter) as iter_mock,              mock.patch.object(renderer, '_draw_single_side_line'):
            renderer.draw_side_lines_cells(overlay_cells, 'solid')

        self.assertEqual(iter_mock.call_count, 1)

    def test_iter_side_line_spans_cells_splits_same_page_y_reset(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = core._VerticalPageRenderer(args, object(), object())
        overlay_cells = [
            (0, 60, 130, '前'),
            (0, 60, 152, '頁'),
            (0, 60, 20, '後'),
            (0, 60, 42, '続'),
        ]

        spans = renderer._iter_side_line_spans_cells(overlay_cells)

        self.assertEqual(spans, [(0, 60, 130, 152), (0, 60, 20, 42)])

    def test_draw_side_lines_cells_keeps_last_span_inside_effective_bottom_margin(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        last_legal_y = args.height - effective_bottom - args.font_size
        overlay_cells = [
            (0, 60, last_legal_y - (args.font_size + 2), '本'),
            (0, 60, last_legal_y, '文'),
        ]

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())), \
             mock.patch.object(renderer, '_draw_single_side_line') as mocked_draw_line:
            renderer.draw_side_lines_cells(overlay_cells, 'solid')

        self.assertEqual(mocked_draw_line.call_count, 1)
        y2 = mocked_draw_line.call_args.args[3]
        self.assertLessEqual(y2, args.height - effective_bottom)

    def test_draw_side_lines_cells_clamps_out_of_range_span_to_effective_bottom_margin(self):
        args = core.ConversionArgs(
            width=120,
            height=140,
            font_size=20,
            ruby_size=10,
            line_spacing=28,
            margin_t=10,
            margin_b=12,
            output_format='xtc',
        )
        renderer = core._VerticalPageRenderer(args, object(), object())
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        bottom_guard = args.height - effective_bottom
        out_of_range_y = bottom_guard + 8

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())),              mock.patch.object(renderer, '_draw_single_side_line') as mocked_draw_line:
            renderer.draw_side_lines_cells([(0, 60, out_of_range_y, '漢')], 'solid')

        self.assertEqual(mocked_draw_line.call_count, 1)
        _draw_obj, _x, y1, y2, _kind = mocked_draw_line.call_args.args[:5]
        self.assertLessEqual(y2, bottom_guard)
        self.assertLessEqual(y1, y2)
        self.assertGreaterEqual(y1, args.margin_t)

    def test_draw_side_lines_cells_clamps_line_x_inside_canvas_width(self):
        args = core.ConversionArgs(width=80, height=140, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = core._VerticalPageRenderer(args, object(), object())

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())),              mock.patch.object(renderer, '_draw_single_side_line') as right_draw:
            renderer.draw_side_lines_cells([(0, 76, 20, '漢')], 'wavy')

        self.assertEqual(right_draw.call_count, 1)
        _draw_obj, wavy_x, _y1, _y2, wavy_kind = right_draw.call_args.args[:5]
        amplitude, _wavelength, _unused = core._get_side_line_pattern(args.font_size, 'wavy')
        self.assertEqual(wavy_kind, 'wavy')
        self.assertGreaterEqual(wavy_x - amplitude, 0)
        self.assertLessEqual(wavy_x + amplitude, args.width - 1)

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())),              mock.patch.object(renderer, '_draw_single_side_line') as left_draw:
            renderer.draw_side_lines_cells([(0, 0, 20, '漢')], 'double', emphasis_kind='白丸傍点')

        self.assertEqual(left_draw.call_count, 2)
        for call in left_draw.call_args_list:
            line_x = call.args[1]
            self.assertGreaterEqual(line_x, 0)
            self.assertLessEqual(line_x, args.width - 1)

    def test_draw_side_lines_cells_keeps_double_line_pair_separated_at_canvas_edges(self):
        args = core.ConversionArgs(width=80, height=140, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = core._VerticalPageRenderer(args, object(), object())

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())), \
             mock.patch.object(renderer, '_draw_single_side_line') as right_draw:
            renderer.draw_side_lines_cells([(0, 76, 20, '漢')], 'double')

        self.assertEqual(right_draw.call_count, 2)
        right_primary_x = right_draw.call_args_list[0].args[1]
        right_secondary_x = right_draw.call_args_list[1].args[1]
        self.assertGreater(right_secondary_x, right_primary_x)
        for call in right_draw.call_args_list:
            line_x = call.args[1]
            self.assertGreaterEqual(line_x, 0)
            self.assertLessEqual(line_x, args.width - 1)

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())), \
             mock.patch.object(renderer, '_draw_single_side_line') as left_draw:
            renderer.draw_side_lines_cells([(0, 0, 20, '漢')], 'double', emphasis_kind='白丸傍点')

        self.assertEqual(left_draw.call_count, 2)
        left_primary_x = left_draw.call_args_list[0].args[1]
        left_secondary_x = left_draw.call_args_list[1].args[1]
        self.assertLess(left_secondary_x, left_primary_x)
        for call in left_draw.call_args_list:
            line_x = call.args[1]
            self.assertGreaterEqual(line_x, 0)
            self.assertLessEqual(line_x, args.width - 1)

    def test_draw_side_lines_uses_left_side_for_emphasis_and_two_lines_for_double(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = [
            {'page_index': 0, 'x': 60, 'y': 20, 'cell_text': '漢'},
            {'page_index': 0, 'x': 60, 'y': 42, 'cell_text': '字'},
        ]

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())):
            with mock.patch.object(renderer, '_draw_single_side_line') as mocked_draw_line:
                renderer.draw_side_lines(segment_infos, 'double', emphasis_kind='白丸傍点')

        self.assertEqual(mocked_draw_line.call_count, 2)
        first_x = mocked_draw_line.call_args_list[0].args[1]
        second_x = mocked_draw_line.call_args_list[1].args[1]
        self.assertLess(first_x, segment_infos[0]['x'])
        self.assertLess(second_x, segment_infos[0]['x'])
        self.assertLess(second_x, first_x)

    def test_draw_side_lines_uses_right_side_for_double_without_emphasis(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = [
            {'page_index': 0, 'x': 40, 'y': 20, 'cell_text': '本'},
            {'page_index': 0, 'x': 40, 'y': 42, 'cell_text': '文'},
        ]

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())):
            with mock.patch.object(renderer, '_draw_single_side_line') as mocked_draw_line:
                renderer.draw_side_lines(segment_infos, 'double')

        self.assertEqual(mocked_draw_line.call_count, 2)
        first_x = mocked_draw_line.call_args_list[0].args[1]
        second_x = mocked_draw_line.call_args_list[1].args[1]
        self.assertGreater(first_x, segment_infos[0]['x'])
        self.assertGreater(second_x, segment_infos[0]['x'])
        self.assertGreater(second_x, first_x)

    def test_draw_side_lines_adds_right_padding_for_ruby_text(self):
        args = core.ConversionArgs(width=120, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        segment_infos = [
            {'page_index': 0, 'x': 40, 'y': 20, 'cell_text': '本'},
            {'page_index': 0, 'x': 40, 'y': 42, 'cell_text': '文'},
        ]

        with mock.patch.object(renderer, 'get_page_image_draw', return_value=(None, object())):
            with mock.patch.object(renderer, '_draw_single_side_line') as plain_draw:
                renderer.draw_side_lines(segment_infos, 'solid')
            with mock.patch.object(renderer, '_draw_single_side_line') as ruby_draw:
                renderer.draw_side_lines(segment_infos, 'solid', ruby_text='ルビ')

        plain_x = plain_draw.call_args.args[1]
        ruby_x = ruby_draw.call_args.args[1]
        self.assertGreater(ruby_x, plain_x)

    def test_draw_single_side_line_draws_pixels_for_wavy_dashed_and_chain(self):
        args = core.ConversionArgs(width=80, height=120, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)

        for line_kind in ('wavy', 'dashed', 'chain'):
            with self.subTest(line_kind=line_kind):
                img = Image.new('L', (40, 60), 255)
                draw = ImageDraw.Draw(img)
                renderer._draw_single_side_line(draw, 20, 5, 45, line_kind, width=1)
                pixels = img.load()
                dark_pixels = sum(1 for y in range(img.height) for x in range(img.width) if pixels[x, y] < 255)
                self.assertGreater(dark_pixels, 0)

    def test_draw_single_side_line_uses_two_endpoint_line_for_degenerate_wavy_span(self):
        args = core.ConversionArgs(width=80, height=120, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = core._VerticalPageRenderer(args, object(), object())

        class DummyDraw:
            def __init__(self):
                self.calls = []

            def line(self, xy, fill=None, width=1):
                self.calls.append((xy, fill, width))

        draw = DummyDraw()

        renderer._draw_single_side_line(draw, 20, 45, 45, 'wavy', width=1)

        self.assertEqual(draw.calls, [((20, 45, 20, 45), 0, 1)])

    def test_draw_single_side_line_skips_pattern_lookup_for_solid(self):
        args = core.ConversionArgs(width=80, height=120, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        img = Image.new('L', (40, 60), 255)
        draw = ImageDraw.Draw(img)

        with mock.patch.object(core, '_get_side_line_pattern', wraps=core._get_side_line_pattern) as pattern_mock:
            renderer._draw_single_side_line(draw, 20, 5, 45, 'solid', width=1)

        self.assertEqual(pattern_mock.call_count, 0)

    def test_side_line_helpers_reuse_cached_pattern_and_style(self):
        core._get_side_line_pattern.cache_clear()
        core._get_side_line_style.cache_clear()

        pattern1 = core._get_side_line_pattern(20, 'wavy')
        pattern2 = core._get_side_line_pattern(20, 'wavy')
        style1 = core._get_side_line_style(20, 10, 'double', True, False, False)
        style2 = core._get_side_line_style(20, 10, 'double', True, False, False)

        self.assertEqual(pattern1, pattern2)
        self.assertEqual(style1, style2)
        self.assertGreaterEqual(core._get_side_line_pattern.cache_info().hits, 1)
        self.assertGreaterEqual(core._get_side_line_style.cache_info().hits, 1)


    def test_get_text_bbox_falls_back_for_mock_font_without_getbbox(self):
        self.assertEqual(core._get_text_bbox(object(), '底'), (0, 0, 1, 1))

    def test_get_text_bbox_normalizes_mock_bbox_for_overlay_guards(self):
        class ShortBBoxFont:
            def getbbox(self, text, stroke_width=0):
                return (0, 0)

        class ZeroBBoxFont:
            def getbbox(self, text, stroke_width=0):
                return (3, 4, 3, 4)

        self.assertEqual(core._get_text_bbox(ShortBBoxFont(), '底'), (0, 0, 1, 1))
        self.assertEqual(core._get_text_bbox(ZeroBBoxFont(), '底'), (3, 4, 4, 5))
        self.assertEqual(core._get_text_bbox_dims(object(), '底'), (1, 1))

    def test_cached_text_bbox_normalizes_cacheable_font_bbox_result(self):
        class ZeroBBoxFont:
            def getbbox(self, text, stroke_width=0):
                return (4, 5, 4, 5)

        core._cached_text_bbox.cache_clear()
        core._cached_text_bbox_dims.cache_clear()
        try:
            with mock.patch.object(core, 'load_truetype_font', return_value=ZeroBBoxFont()):
                self.assertEqual(core._cached_text_bbox('dummy.ttf', 0, 10, '底', False), (4, 5, 5, 6))
                self.assertEqual(core._cached_text_bbox_dims('dummy.ttf', 0, 10, '底', False), (1, 1))
        finally:
            core._cached_text_bbox.cache_clear()
            core._cached_text_bbox_dims.cache_clear()


    def test_get_text_bbox_falls_back_when_getbbox_rejects_all_signatures(self):
        class TypeErrorBBoxFont:
            def getbbox(self, *args, **kwargs):
                raise TypeError('unsupported getbbox signature')

        self.assertEqual(core._get_text_bbox(TypeErrorBBoxFont(), '底'), (0, 0, 1, 1))
        self.assertEqual(core._get_text_bbox_dims(TypeErrorBBoxFont(), '底'), (1, 1))

    def test_cached_text_bbox_falls_back_when_getbbox_rejects_all_signatures(self):
        class TypeErrorBBoxFont:
            def getbbox(self, *args, **kwargs):
                raise TypeError('unsupported getbbox signature')

        core._cached_text_bbox.cache_clear()
        core._cached_text_bbox_dims.cache_clear()
        try:
            with mock.patch.object(core, 'load_truetype_font', return_value=TypeErrorBBoxFont()):
                self.assertEqual(core._cached_text_bbox('dummy.ttf', 0, 10, '底', False), (0, 0, 1, 1))
                self.assertEqual(core._cached_text_bbox_dims('dummy.ttf', 0, 10, '底', False), (1, 1))
        finally:
            core._cached_text_bbox.cache_clear()
            core._cached_text_bbox_dims.cache_clear()


    def test_text_bbox_paths_delegate_to_shared_getbbox_helper(self):
        font = object()

        with mock.patch.object(core, '_call_font_getbbox', return_value=(2, 3, 7, 11)) as helper_mock:
            self.assertEqual(core._get_text_bbox(font, '底', is_bold=True), (2, 3, 7, 11))

        helper_mock.assert_called_once_with(font, '底', 1)

        core._cached_text_bbox.cache_clear()
        try:
            loaded_font = object()
            with mock.patch.object(core, 'load_truetype_font', return_value=loaded_font),                  mock.patch.object(core, '_call_font_getbbox', return_value=(4, 5, 10, 12)) as cached_helper_mock:
                self.assertEqual(core._cached_text_bbox('dummy.ttf', 0, 10, '底', False), (4, 5, 10, 12))

            cached_helper_mock.assert_called_once_with(loaded_font, '底', 0)
        finally:
            core._cached_text_bbox.cache_clear()



if __name__ == '__main__':
    unittest.main()
