import io
import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec


class EpubChapterRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            core._require_bs4_beautifulsoup()
        except Exception as exc:
            raise unittest.SkipTest(f'BeautifulSoup unavailable: {exc}')
        cls.font_path = resolve_test_font_path()

    def _load_fonts(self, args):
        font = core.load_truetype_font(self.font_path, args.font_size)
        ruby_font = core.load_truetype_font(self.font_path, args.ruby_size)
        return font, ruby_font

    def test_render_epub_chapter_pages_from_html_splits_pagebreak_into_two_entries(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._load_fonts(args)
        html = '<html><body><p>前半の本文です。</p><hr/><p>後半の本文です。</p></body></html>'

        pages = core._render_epub_chapter_pages_from_html(
            html,
            'text/chapter1.xhtml',
            args,
            font,
            ruby_font,
            {'classes': set(), 'ids': set(), 'tags': set()},
            {},
            {},
        )

        self.assertEqual(len(pages), 2)
        self.assertEqual([page['label'] for page in pages], ['本文ページ', '本文ページ'])
        self.assertTrue(all(page['page_args'].night_mode == args.night_mode for page in pages))

    def test_render_epub_chapter_pages_from_html_marks_illustration_pages_non_night_mode(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc', night_mode=True)
        font, ruby_font = self._load_fonts(args)
        image = Image.new('L', (280, 280), 64)
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_bytes = buf.getvalue()

        pages = core._render_epub_chapter_pages_from_html(
            '<html><body><img src="images/illust.png"/></body></html>',
            'text/chapter1.xhtml',
            args,
            font,
            ruby_font,
            {'classes': set(), 'ids': set(), 'tags': set()},
            {'text/images/illust.png': image_bytes},
            {'illust.png': [('text/images/illust.png', image_bytes)]},
        )

        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]['label'], '挿絵ページ')
        self.assertFalse(pages[0]['page_args'].night_mode)
        self.assertEqual(pages[0]['image'].getpixel((0, 0)), 64)

    def test_render_epub_chapter_pages_from_html_passes_full_page_images_without_extra_copy(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._load_fonts(args)
        image = Image.new('L', (280, 280), 96)
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_bytes = buf.getvalue()

        observed_copy_flags = []
        original = core._VerticalPageRenderer.add_full_page_image

        def spy_add_full_page_image(self, img, *spy_args, **spy_kwargs):
            observed_copy_flags.append(spy_kwargs.get('copy_image', True))
            return original(self, img, *spy_args, **spy_kwargs)

        try:
            core._VerticalPageRenderer.add_full_page_image = spy_add_full_page_image
            pages = core._render_epub_chapter_pages_from_html(
                '<html><body><img src="images/illust.png"/></body></html>',
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {'text/images/illust.png': image_bytes},
                {'illust.png': [('text/images/illust.png', image_bytes)]},
            )
        finally:
            core._VerticalPageRenderer.add_full_page_image = original

        self.assertEqual(len(pages), 1)
        self.assertEqual(observed_copy_flags, [False])
        self.assertEqual(pages[0]['image'].getpixel((0, 0)), 96)


    def test_prepare_inline_epub_image_bytes_cache_reuses_processing(self):
        args = core.ConversionArgs(font_size=24)
        image = Image.new('RGB', (16, 12), (32, 64, 96))
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_bytes = buf.getvalue()

        core._prepare_inline_epub_image_bytes.cache_clear()
        first = core._prepare_inline_epub_image_bytes(image_bytes, args.font_size, False)
        info_after_first = core._prepare_inline_epub_image_bytes.cache_info()
        second = core._prepare_inline_epub_image_bytes(image_bytes, args.font_size, False)
        info_after_second = core._prepare_inline_epub_image_bytes.cache_info()

        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_render_epub_chapter_pages_from_html_reuses_cached_inline_image_processing(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._load_fonts(args)
        image = Image.new('RGB', (16, 12), (32, 64, 96))
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_bytes = buf.getvalue()
        html = '<html><body><p><img src="images/icon.png"/><img src="images/icon.png"/><img src="images/icon.png"/></p></body></html>'

        core._inspect_epub_embedded_image.cache_clear()
        core._prepare_inline_epub_image_bytes.cache_clear()
        original_open = core.Image.open
        open_calls = []

        def counting_open(*open_args, **open_kwargs):
            open_calls.append(1)
            return original_open(*open_args, **open_kwargs)

        try:
            core.Image.open = counting_open
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {'text/images/icon.png': image_bytes},
                {'icon.png': [('text/images/icon.png', image_bytes)]},
            )
        finally:
            core.Image.open = original_open

        self.assertEqual(len(pages), 1)
        self.assertLessEqual(len(open_calls), 2)

    def test_render_epub_chapter_pages_from_html_reuses_cached_image_resolution_for_duplicate_sources(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._load_fonts(args)
        image = Image.new('RGB', (16, 12), (32, 64, 96))
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_bytes = buf.getvalue()
        html = '<html><body><p><img src="images/icon.png"/><img src="images/icon.png"/><img src="images/icon.png"/></p></body></html>'
        original_resolve = core._resolve_epub_image_data
        calls = []

        def counting_resolve(*resolve_args, **resolve_kwargs):
            calls.append(resolve_args[1])
            return original_resolve(*resolve_args, **resolve_kwargs)

        try:
            core._resolve_epub_image_data = counting_resolve
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {'text/images/icon.png': image_bytes},
                {'icon.png': [('text/images/icon.png', image_bytes)]},
            )
        finally:
            core._resolve_epub_image_data = original_resolve

        self.assertEqual(len(pages), 1)
        self.assertEqual(calls, ['images/icon.png'])

    def test_render_epub_chapter_pages_text_run_uses_consistent_line_step(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._load_fonts(args)
        positions = []
        original_draw_char_tate = core.draw_char_tate

        def recording_draw(draw, char, pos_tuple, font_obj, f_size, **kwargs):
            positions.append((char, pos_tuple))
            return None

        try:
            core.draw_char_tate = recording_draw
            core._render_epub_chapter_pages_from_html(
                '<html><body><p>天地</p></body></html>',
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {},
                {},
            )
        finally:
            core.draw_char_tate = original_draw_char_tate

        self.assertGreaterEqual(len(positions), 2)
        self.assertEqual(positions[1][1][1] - positions[0][1][1], args.font_size + 2)

    def test_render_epub_chapter_pages_from_html_strips_start_text_after_frontmatter_block(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._load_fonts(args)
        html = '<html><body><h1>三四郎</h1><h2>夏目漱石</h2><h3>一</h3><p>start text</p><p>うとうととして目がさめると女は</p></body></html>'
        captured = []
        original_draw_runs = core._VerticalPageRenderer.draw_runs

        def spy_draw_runs(self, runs, *spy_args, **spy_kwargs):
            captured.append(''.join(str(run.get('text', '')) for run in runs))
            return original_draw_runs(self, runs, *spy_args, **spy_kwargs)

        try:
            core._VerticalPageRenderer.draw_runs = spy_draw_runs
            core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {},
                {},
            )
        finally:
            core._VerticalPageRenderer.draw_runs = original_draw_runs

        flattened = ''.join(captured)
        self.assertNotIn('start text', flattened.lower())
        self.assertIn('三四郎', flattened)
        self.assertIn('夏目漱石', flattened)
        self.assertIn('うとうととして目がさめると女は', flattened)

    def test_render_epub_chapter_pages_from_html_strips_start_text_prefix_after_frontmatter(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._load_fonts(args)
        html = '<html><body><h1>三四郎</h1><h2>夏目漱石</h2><h3>一</h3><p>start text うとうととして目がさめると女は</p></body></html>'
        captured = []
        original_draw_runs = core._VerticalPageRenderer.draw_runs

        def spy_draw_runs(self, runs, *spy_args, **spy_kwargs):
            captured.append(''.join(str(run.get('text', '')) for run in runs))
            return original_draw_runs(self, runs, *spy_args, **spy_kwargs)

        try:
            core._VerticalPageRenderer.draw_runs = spy_draw_runs
            core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {},
                {},
            )
        finally:
            core._VerticalPageRenderer.draw_runs = original_draw_runs

        flattened = ''.join(captured)
        self.assertNotIn('start text', flattened.lower())
        self.assertIn('うとうととして目がさめると女は', flattened)

    def test_resolve_epub_image_data_accepts_string_basename_map_entries(self):
        image_map = {'OPS/images/illust.png': b'data'}
        key, data = core._resolve_epub_image_data(
            'OPS/text/chapter.xhtml',
            '../images/illust.png',
            image_map,
            {'illust.png': ['OPS/images/illust.png']},
        )
        self.assertEqual(key, 'OPS/images/illust.png')
        self.assertEqual(data, b'data')

    def test_render_epub_chapter_pages_from_html_handles_ruby_across_multiple_pages(self):
        args = core.ConversionArgs(
            width=120,
            height=120,
            font_size=24,
            ruby_size=12,
            line_spacing=32,
            output_format='xtc',
            margin_t=8,
            margin_b=8,
            margin_l=8,
            margin_r=8,
        )
        font, ruby_font = self._load_fonts(args)
        html = (
            '<html><body><p><ruby>'
            '吾輩は猫である吾輩は猫である吾輩は猫である吾輩は猫である'
            '<rt>'
            'わがはいはねこであるわがはいはねこであるわがはいはねこであるわがはいはねこである'
            '</rt></ruby></p></body></html>'
        )

        pages = core._render_epub_chapter_pages_from_html(
            html,
            'text/chapter1.xhtml',
            args,
            font,
            ruby_font,
            {'classes': set(), 'ids': set(), 'tags': set()},
            {},
            {},
        )

        self.assertGreaterEqual(len(pages), 2)
        self.assertTrue(all(page['label'] == '本文ページ' for page in pages))

    def test_render_epub_chapter_pages_from_html_defers_streaming_until_cross_page_ruby_overlay_is_applied(self):
        args = core.ConversionArgs(
            width=120,
            height=120,
            font_size=24,
            ruby_size=12,
            line_spacing=32,
            output_format='xtc',
            margin_t=8,
            margin_b=8,
            margin_l=8,
            margin_r=8,
        )
        font, ruby_font = self._load_fonts(args)
        base_text = '吾輩は猫である吾輩は猫である吾輩は猫である吾輩は猫である'
        ruby_text = 'わがはいはねこであるわがはいはねこであるわがはいはねこであるわがはいはねこである'
        html = f'<html><body><p><ruby>{base_text}<rt>{ruby_text}</rt></ruby></p></body></html>'
        callback_pages = []

        pages = core._render_epub_chapter_pages_from_html(
            html,
            'text/chapter1.xhtml',
            args,
            font,
            ruby_font,
            {'classes': set(), 'ids': set(), 'tags': set()},
            {},
            {},
            page_created_cb=callback_pages.append,
            store_page_entries=False,
        )

        self.assertEqual(callback_pages, [])
        self.assertGreaterEqual(len(pages), 2)

        plain_pages = core._render_epub_chapter_pages_from_html(
            f'<html><body><p>{base_text}</p></body></html>',
            'text/chapter1.xhtml',
            args,
            font,
            ruby_font,
            {'classes': set(), 'ids': set(), 'tags': set()},
            {},
            {},
        )

        def right_ruby_band_dark_pixels(page_entry):
            image = page_entry['image']
            # The ruby column for this fixture is drawn on the far-right side of
            # the text column.  A cross-page ruby overlay must therefore add ink
            # to the first stored page before it is returned to the caller.
            band = image.crop((max(0, image.width - 28), 0, image.width, image.height))
            return sum(1 for pixel in band.getdata() if pixel < 240)

        self.assertGreater(
            right_ruby_band_dark_pixels(pages[0]),
            right_ruby_band_dark_pixels(plain_pages[0]) + 5,
        )

    def test_render_epub_chapter_pages_from_html_ruby_overlay_respects_effective_bottom_margin(self):
        args = core.ConversionArgs(
            width=120,
            height=100,
            font_size=20,
            ruby_size=10,
            line_spacing=34,
            output_format='xtc',
            margin_t=0,
            margin_b=12,
            margin_l=8,
            margin_r=8,
        )
        font, ruby_font = self._load_fonts(args)
        html = (
            '<html><body><p><ruby>'
            '吾輩は猫である吾輩は猫である'
            '<rt>'
            'わがはいはねこであるわがはいはねこである'
            '</rt></ruby></p></body></html>'
        )
        ruby_positions = []
        original_draw_char_tate = core.draw_char_tate

        def recording_draw(draw, char, pos_tuple, font_obj, f_size, **kwargs):
            if kwargs.get('ruby_mode'):
                ruby_positions.append(pos_tuple)
            return None

        try:
            core.draw_char_tate = recording_draw
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {},
                {},
            )
        finally:
            core.draw_char_tate = original_draw_char_tate

        self.assertGreaterEqual(len(pages), 1)
        self.assertGreater(len(ruby_positions), 0)
        effective_bottom = core._effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)
        max_ruby_y = args.height - effective_bottom - args.ruby_size
        self.assertTrue(all(y <= max_ruby_y for _x, y in ruby_positions))


if __name__ == '__main__':
    unittest.main()
