import builtins
import hashlib
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


def _legacy_xtch_dither(img: Image.Image, threshold: int, w: int, h: int) -> Image.Image:
    background = core._prepare_canvas_image(img, w, h)
    bias = max(-48, min(48, int(threshold) - 128))
    t1 = max(16, min(96, 64 + bias // 2))
    t2 = max(t1 + 16, min(176, 128 + bias))
    t3 = max(t2 + 16, min(240, 192 + bias // 2))
    work = background.copy()
    px = work.load()
    for y in range(h):
        for x in range(w):
            assert px is not None
            old = int(px[x, y])
            if old <= t1:
                newv = 0
            elif old <= t2:
                newv = 85
            elif old <= t3:
                newv = 170
            else:
                newv = 255
            err = old - newv
            px[x, y] = newv
            if x + 1 < w:
                px[x + 1, y] = max(0, min(255, int(px[x + 1, y] + err * 7 / 16)))
            if y + 1 < h:
                if x > 0:
                    px[x - 1, y + 1] = max(0, min(255, int(px[x - 1, y + 1] + err * 3 / 16)))
                px[x, y + 1] = max(0, min(255, int(px[x, y + 1] + err * 5 / 16)))
                if x + 1 < w:
                    px[x + 1, y + 1] = max(0, min(255, int(px[x + 1, y + 1] + err * 1 / 16)))
    return work


class _FakeBookItem:
    def __init__(self, file_name='', media_type='', content=b'img'):
        self.file_name = file_name
        self.media_type = media_type
        self._content = content

    def get_content(self):
        return self._content


class _FakeBook:
    def __init__(self, items, spine):
        self._items = items
        self.spine = spine
        self._items_by_id = {}

    def get_items(self):
        return list(self._items)

    def get_item_with_id(self, item_id):
        return self._items_by_id.get(item_id)


class MiscConversionHelperRegressionTests(unittest.TestCase):
    def _args(self, **overrides):
        params = dict(width=4, height=1, font_size=16, ruby_size=8, line_spacing=24, output_format='xtc', threshold=128, dither=False)
        params.update(overrides)
        return core.ConversionArgs(**params)

    def test_build_conversion_error_report_covers_archive_image_missing_and_text_paths(self):
        report = core.build_conversion_error_report('sample.cbz', RuntimeError('画像ファイルが見つかりませんでした'))
        self.assertEqual(report['headline'], 'アーカイブ内に変換対象の画像が見つかりませんでした。')
        self.assertIn('対応画像は', report['hint'])

        report = core.build_conversion_error_report('sample.cbr', RuntimeError('decoder exploded'))
        self.assertEqual(report['headline'], 'アーカイブ内画像の変換に失敗しました。')

        report = core.build_conversion_error_report('sample.txt', RuntimeError('odd control chars'))
        self.assertEqual(report['headline'], 'テキストファイルの読み込みまたは変換に失敗しました。')

        report = core.build_conversion_error_report(None, RuntimeError('generic'))
        self.assertNotIn('対象:', report['display'])

    def test_require_import_helpers_and_module_availability_cover_error_paths(self):
        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'ebooklib':
                raise ImportError('missing ebooklib')
            if name == 'bs4':
                raise ImportError('missing bs4')
            return real_import(name, globals, locals, fromlist, level)

        with mock.patch('builtins.__import__', side_effect=fake_import):
            with self.assertRaisesRegex(RuntimeError, 'ebooklib が必要です'):
                core._require_ebooklib_epub()
            with self.assertRaisesRegex(RuntimeError, 'beautifulsoup4 が必要です'):
                core._require_bs4_beautifulsoup()

        self.assertTrue(core._is_module_available('hashlib'))
        self.assertFalse(core._is_module_available('surely_missing_module_xyz'))

    def test_build_epub_image_maps_and_collect_spine_documents_filter_supported_items(self):
        items = [
            _FakeBookItem('OPS/images/pic.png', 'image/png', b'png'),
            _FakeBookItem('OPS/images/photo.jpg', 'application/octet-stream', b'jpg'),
            _FakeBookItem('OPS/text/ch1.xhtml', 'application/xhtml+xml', b'<p>1</p>'),
            _FakeBookItem('OPS/text/ch2.html', 'text/html', b'<p>2</p>'),
            _FakeBookItem('OPS/text/skip.txt', 'text/plain', b'skip'),
        ]
        book = _FakeBook(items, [('ch1', ''), 'ch2', 'missing'])
        book._items_by_id = {'ch1': items[2], 'ch2': items[3]}

        image_map, basename_map = core._build_epub_image_maps(book)
        self.assertEqual(sorted(image_map), ['OPS/images/photo.jpg', 'OPS/images/pic.png'])
        self.assertEqual(len(basename_map['pic.png']), 1)

        docs = core._collect_epub_spine_documents(book)
        self.assertEqual([doc.file_name for doc in docs], ['OPS/text/ch1.xhtml', 'OPS/text/ch2.html'])

    def test_has_renderable_text_blocks_and_append_page_entries_cover_cancel_and_callable_completion(self):
        self.assertFalse(core._has_renderable_text_blocks([{'kind': 'blank'}]))
        self.assertTrue(core._has_renderable_text_blocks([{'kind': 'paragraph', 'runs': [{'text': '本文'}]}]))
        with self.assertRaises(core.ConversionCancelled):
            core._has_renderable_text_blocks([{'kind': 'paragraph', 'runs': [{'text': '本文'}]}], should_cancel=lambda: True)

        args = self._args()
        raw_image = Image.new('L', (args.width, args.height), 255)
        progress = []
        with core.XTCSpooledPages() as spooled:
            with mock.patch.object(core, 'page_image_to_xt_bytes', return_value=b'blob') as mocked_page_to_xt:
                core._append_page_entries_to_spool(
                    [raw_image, {'image': None, 'label': 'skip-me'}],
                    spooled,
                    args,
                    progress_cb=lambda cur, total, msg: progress.append((cur, total, msg)),
                    complete_message=lambda page_count, total_pages, last_message: f'done {page_count}/{total_pages} ({last_message})',
                )
        mocked_page_to_xt.assert_called_once()
        self.assertEqual(progress[-1][2], 'done 1/2 (ページを変換中… (1/2 ページ))')


    def test_prepare_canvas_image_reuses_exact_l_mode_image(self):
        img = Image.new('L', (4, 1), 200)
        prepared = core._prepare_canvas_image(img, 4, 1)
        self.assertIs(prepared, img)



    def test_render_text_blocks_to_images_reuses_page_entry_images_without_copy(self):
        args = self._args(width=120, height=160, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        img = Image.new('L', (args.width, args.height), 180)
        entry = core._make_page_entry(img, page_args=args, label='本文ページ')
        with mock.patch.object(core, '_render_text_blocks_to_page_entries', return_value=[entry]) as render_mock:
            pages = core._render_text_blocks_to_images(
                [{'kind': 'paragraph', 'runs': [{'text': '本文'}], 'blank_before': 1}],
                str(FONT_PATH),
                args,
            )
        render_mock.assert_called_once()
        self.assertEqual(len(pages), 1)
        self.assertIs(pages[0], img)

    def test_render_text_blocks_to_images_reuses_buffered_page_objects(self):
        args = core.ConversionArgs(width=120, height=160, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        created = []

        class FakeRenderer:
            def __init__(self, *renderer_args, **renderer_kwargs):
                self.args = renderer_args[0]
                self.font = renderer_args[1]
                self.ruby_font = renderer_args[2]
                self.code_font = renderer_kwargs.get('code_font', self.font)
                self.has_started_document = False
                self.has_drawn_on_page = False
                self._entries = []
                self.img = Image.new('L', (self.args.width, self.args.height), 255)
                self.prepared = Image.new('L', (self.args.width, self.args.height), 180)
                created.append(self)

            @property
            def has_pending_output(self):
                return bool(self._entries or self.has_drawn_on_page)

            def draw_runs(self, runs, default_font=None, wrap_indent_chars=0):
                if not self._entries:
                    self._entries.append({'image': self.prepared, 'page_args': self.args, 'label': '本文ページ'})

            def pop_page_entries(self):
                entries = self._entries
                self._entries = []
                return entries

            def advance_column(self, count=1, indent_chars=0):
                return None

            def insert_paragraph_indent(self, indent_chars=0, continuation_indent_chars=None):
                return None

        with mock.patch.object(core, '_VerticalPageRenderer', FakeRenderer):
            pages = core._render_text_blocks_to_images(
                [{'kind': 'paragraph', 'runs': [{'text': '本文'}], 'blank_before': 1}],
                str(FONT_PATH),
                args,
            )

        self.assertEqual(len(pages), 1)
        self.assertTrue(created)
        self.assertIs(pages[0], created[0].prepared)

    def test_process_image_data_uses_prepared_canvas_path_without_repreparing(self):
        args = self._args(width=4, height=4)
        src = Image.new('L', (4, 4), 128)
        buf = io.BytesIO()
        src.save(buf, format='PNG')

        with mock.patch.object(core, '_prepare_canvas_image', wraps=core._prepare_canvas_image) as mocked_prepare:
            with mock.patch.object(core, 'canvas_image_to_xt_bytes', wraps=core.canvas_image_to_xt_bytes) as mocked_canvas_to_xt:
                blob = core.process_image_data(buf.getvalue(), args)

        self.assertIsInstance(blob, (bytes, bytearray))
        self.assertEqual(mocked_prepare.call_count, 1)
        self.assertEqual(mocked_canvas_to_xt.call_count, 1)
        self.assertTrue(mocked_canvas_to_xt.call_args.kwargs.get('prepared'))


    def test_process_image_data_accepts_pathlike_without_reading_bytes_first(self):
        args = self._args(width=4, height=4)
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / 'sample.png'
            Image.new('L', (4, 4), 96).save(image_path)
            with mock.patch.object(core, '_prepare_canvas_image', wraps=core._prepare_canvas_image) as mocked_prepare:
                blob = core.process_image_data(image_path, args)

        self.assertIsInstance(blob, (bytes, bytearray))
        self.assertEqual(mocked_prepare.call_count, 1)

    def test_process_image_data_accepts_binary_stream_without_copying_to_bytes(self):
        args = self._args(width=4, height=4)
        src = Image.new('L', (4, 4), 144)
        buf = io.BytesIO()
        src.save(buf, format='PNG')
        buf.seek(0)
        with mock.patch.object(core, '_prepare_canvas_image', wraps=core._prepare_canvas_image) as mocked_prepare:
            blob = core.process_image_data(buf, args)

        self.assertIsInstance(blob, (bytes, bytearray))
        self.assertEqual(mocked_prepare.call_count, 1)


    def test_apply_preview_postprocess_reuses_prepared_preview_canvas(self):
        page = Image.new('L', (4, 4), 200)
        with mock.patch.object(core, '_prepare_canvas_image', wraps=core._prepare_canvas_image) as mocked_prepare:
            result = core._apply_preview_postprocess(
                page,
                mode='text',
                output_format='xtc',
                dither=False,
                threshold=128,
                width=4,
                height=4,
                night_mode=False,
            )

        self.assertEqual(mocked_prepare.call_count, 0)
        self.assertEqual(result.size, (4, 4))


    def test_png_to_xtg_bytes_keeps_padding_bits_cleared_in_night_mode(self):
        img = Image.new('L', (5, 1), 255)
        img.putpixel((0, 0), 0)
        xtg = core.png_to_xtg_bytes(img, 5, 1, self._args(width=5, height=1, night_mode=True))
        self.assertEqual(xtg[22:], bytes([0b1000_0000]))


    def test_png_to_xtg_bytes_numpy_fast_path_matches_fallback(self):
        img = Image.new('L', (16, 16), 255)
        for x in range(16):
            img.putpixel((x, x), 0)
        args = self._args(width=16, height=16, threshold=128, dither=False)
        out_fast = core.png_to_xtg_bytes(img, 16, 16, args)
        with mock.patch.object(core, 'np', None):
            out_fallback = core.png_to_xtg_bytes(img, 16, 16, args)
        self.assertEqual(out_fast, out_fallback)


    def test_png_to_xth_bytes_numpy_fast_path_matches_fallback(self):
        img = Image.new('L', (16, 16), 255)
        for x in range(16):
            img.putpixel((x, x), 0)
        args = self._args(width=16, height=16, output_format='xtch', threshold=128, dither=False)
        out_fast = core.png_to_xth_bytes(img, 16, 16, args)
        with mock.patch.object(core, 'np', None):
            out_fallback = core.png_to_xth_bytes(img, 16, 16, args)
        self.assertEqual(out_fast, out_fallback)


    def test_xtc_threshold_lut_matches_legacy_lambda_behavior(self):
        expected = tuple(255 if value > 140 else 0 for value in range(256))
        self.assertEqual(core._xtc_threshold_lut(140), expected)
        self.assertIs(core._xtc_threshold_lut(140), core._xtc_threshold_lut(140))


    def test_xtch_quantization_lut_matches_legacy_quantizer(self):
        t1, t2, t3 = core._compute_xtch_thresholds(140)
        expected = tuple(core._quantize_xtch_value(value, t1, t2, t3) for value in range(256))
        self.assertEqual(core._xtch_quantization_lut(140), expected)
        self.assertIs(core._xtch_quantization_lut(140), core._xtch_quantization_lut(140))

    def test_xtch_plane_value_lut_matches_legacy_plane_mapping(self):
        expected = tuple(0 if value >= 213 else 2 if value >= 128 else 1 if value >= 43 else 3 for value in range(256))
        self.assertEqual(core._xtch_plane_value_lut(), expected)
        self.assertIs(core._xtch_plane_value_lut(), core._xtch_plane_value_lut())


    def test_png_to_xtg_bytes_numpy_night_fast_path_matches_fallback(self):
        img = Image.new('L', (13, 17), 255)
        for x in range(13):
            img.putpixel((x, x % 17), 0)
        args = self._args(width=13, height=17, threshold=128, dither=False, night_mode=True)
        out_fast = core.png_to_xtg_bytes(img, 13, 17, args)
        with mock.patch.object(core, 'np', None):
            out_fallback = core.png_to_xtg_bytes(img, 13, 17, args)
        self.assertEqual(out_fast, out_fallback)


    def test_apply_xtch_filter_dither_matches_legacy_pixel_loop(self):
        img = Image.new('L', (8, 6))
        img.putdata([
            0, 32, 64, 96, 128, 160, 192, 224,
            255, 230, 205, 180, 155, 130, 105, 80,
            12, 45, 78, 111, 144, 177, 210, 243,
            250, 210, 170, 130, 90, 50, 10, 0,
            33, 66, 99, 132, 165, 198, 231, 255,
            17, 51, 85, 119, 153, 187, 221, 240,
        ])
        expected = _legacy_xtch_dither(img, 128, 8, 6)
        actual = core.apply_xtch_filter(img, True, 128, 8, 6)
        self.assertEqual(actual.mode, 'L')
        self.assertEqual(actual.tobytes(), expected.tobytes())

    def test_png_to_xth_bytes_dither_matches_legacy_filter_output(self):
        img = Image.new('L', (8, 8))
        img.putdata([(x * 19 + y * 27) % 256 for y in range(8) for x in range(8)])
        args = self._args(width=8, height=8, output_format='xtch', threshold=140, dither=True)
        expected_img = _legacy_xtch_dither(img, 140, 8, 8)
        expected_bytes = core._prepared_canvas_to_xth_bytes(expected_img, 8, 8, self._args(width=8, height=8, output_format='xtch', threshold=140, dither=False))
        actual_bytes = core.png_to_xth_bytes(img, 8, 8, args)
        self.assertEqual(actual_bytes, expected_bytes)

    def test_png_encoders_cover_night_mode_and_xth_value_mapping(self):
        img = Image.new('L', (4, 1))
        img.putdata([255, 170, 85, 0])

        xtg_args = self._args(night_mode=True)
        xtg = core.png_to_xtg_bytes(img, 4, 1, xtg_args)
        magic, w, h, _, _, data_len, _ = struct.unpack('<4sHHBBI8s', xtg[:22])
        self.assertEqual((magic, w, h, data_len), (b'XTG\x00', 4, 1, 1))
        self.assertEqual(xtg[22:], bytes([0b0011_0000]))

        xth_args = self._args(output_format='xtch', night_mode=False)
        xth = core.png_to_xth_bytes(img, 4, 1, xth_args)
        magic, w, h, _, _, data_len, md5 = struct.unpack('<4sHHBBI8s', xth[:22])
        payload = xth[22:]
        self.assertEqual((magic, w, h, data_len), (b'XTH\x00', 4, 1, 2))
        self.assertEqual(md5, hashlib.md5(payload).digest()[:8])
        self.assertEqual(payload, bytes([0b1010_0000, 0b1100_0000]))


if __name__ == '__main__':
    unittest.main()
