import base64
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class EpubPreviewHelperRegressionTests(unittest.TestCase):
    def setUp(self):
        core.clear_preview_bundle_cache()

    @classmethod
    def setUpClass(cls):
        try:
            core._require_bs4_beautifulsoup()
        except Exception as exc:
            raise unittest.SkipTest(f'BeautifulSoup unavailable: {exc}')
        cls.font_value = str(FONT_PATH.resolve())

    def _conv_args(self, **overrides):
        params = dict(
            width=320,
            height=480,
            font_size=24,
            ruby_size=12,
            line_spacing=40,
            margin_t=12,
            margin_b=12,
            margin_l=12,
            margin_r=12,
            output_format='xtc',
            night_mode=False,
        )
        params.update(overrides)
        return core.ConversionArgs(**params)

    def _decode_preview_image(self, preview_b64: str) -> Image.Image:
        return Image.open(io.BytesIO(base64.b64decode(preview_b64))).convert('L')

    def test_classify_epub_embedded_image_threshold_edges(self):
        args = self._conv_args()
        self.assertFalse(core._classify_epub_embedded_image(types.SimpleNamespace(size=(0, 10)), args))
        self.assertTrue(core._classify_epub_embedded_image(Image.new('L', (200, 200), 0), args))
        self.assertFalse(core._classify_epub_embedded_image(Image.new('L', (40, 40), 0), args))

        fallback_args = self._conv_args(width=1000, height=1000, margin_t=0, margin_b=0, margin_l=0, margin_r=0, font_size=60)
        self.assertTrue(core._classify_epub_embedded_image(Image.new('L', (250, 360), 0), fallback_args))

    def test_make_inline_epub_image_scales_into_single_cell(self):
        args = self._conv_args(font_size=24)
        self.assertIsNone(core._make_inline_epub_image(types.SimpleNamespace(size=(0, 20)), args))

        inline = core._make_inline_epub_image(Image.new('L', (80, 40), 0), args)
        self.assertIsNotNone(inline)
        self.assertEqual(inline.mode, 'L')
        self.assertLessEqual(inline.width, max(4, args.font_size - 4))
        self.assertLessEqual(inline.height, max(4, args.font_size - 2))

    def test_resolve_epub_image_data_supports_relative_and_basename_fallback(self):
        image_map = {
            'OPS/images/scene.png': b'scene-bytes',
            'OPS/images/alt.png': b'alt-bytes',
        }
        basename_map = {
            'scene.png': [('OPS/images/scene.png', b'scene-bytes')],
            'alt.png': ['OPS/images/alt.png'],
            'dup.png': ['OPS/images/scene.png', 'OPS/images/alt.png'],
        }

        self.assertEqual(
            core._resolve_epub_image_data('OPS/text/chapter.xhtml', '../images/scene.png', image_map, basename_map),
            ('OPS/images/scene.png', b'scene-bytes'),
        )
        self.assertEqual(
            core._resolve_epub_image_data('OPS/text/chapter.xhtml', 'alt.png', image_map, basename_map),
            ('OPS/images/alt.png', b'alt-bytes'),
        )
        self.assertEqual(
            core._resolve_epub_image_data('OPS/text/chapter.xhtml', '', image_map, basename_map),
            (None, None),
        )
        self.assertEqual(
            core._resolve_epub_image_data('OPS/text/chapter.xhtml', 'dup.png', image_map, basename_map),
            (None, None),
        )

    def test_render_epub_chapter_pages_from_html_draws_inline_image_for_small_embed(self):
        args = self._conv_args(width=200, height=280, font_size=24, ruby_size=12, line_spacing=36)
        font = core.load_truetype_font(self.font_value, args.font_size)
        ruby_font = core.load_truetype_font(self.font_value, args.ruby_size)
        small_img = Image.new('L', (24, 24), 0)
        buf = io.BytesIO()
        small_img.save(buf, format='PNG')
        image_bytes = buf.getvalue()
        recorded = []
        original = core._VerticalPageRenderer.draw_inline_image

        def recording_draw(self, char_img, *, wrap_indent_chars=0):
            recorded.append((char_img.size, wrap_indent_chars))
            return original(self, char_img, wrap_indent_chars=wrap_indent_chars)

        with mock.patch.object(core._VerticalPageRenderer, 'draw_inline_image', autospec=True, side_effect=recording_draw):
            pages = core._render_epub_chapter_pages_from_html(
                '<html><body><p>前<img src="../images/small.png"/>後</p></body></html>',
                'OPS/text/chapter.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {'OPS/images/small.png': image_bytes},
                {'small.png': [('OPS/images/small.png', image_bytes)]},
            )

        self.assertTrue(recorded)
        self.assertTrue(all(page['label'] == '本文ページ' for page in pages))

    def test_resolve_preview_source_path_prefers_first_natural_supported_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'ignore.bin').write_bytes(b'x')
            (root / '10.txt').write_text('later', encoding='utf-8')
            (root / '2.txt').write_text('earlier', encoding='utf-8')
            resolved = core._resolve_preview_source_path(root)
            self.assertEqual(resolved.name, '2.txt')
            self.assertIsNone(core._resolve_preview_source_path(root / 'ignore.bin'))
            self.assertIsNone(core._resolve_preview_source_path(root / 'missing.txt'))

    def test_preview_font_requirement_helpers_cover_images_archives_and_text(self):
        self.assertTrue(core._preview_source_requires_font(None))
        self.assertTrue(core._preview_source_requires_font(Path('sample.txt')))
        self.assertFalse(core._preview_source_requires_font(Path('sample.png')))
        self.assertFalse(core._preview_source_requires_font(Path('sample.cbz')))

    def test_render_preview_page_from_target_returns_blank_for_empty_epub_or_archive(self):
        args = self._conv_args(width=160, height=220)
        blank_expected = Image.new('L', (args.width, args.height), 255)

        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'empty.epub'
            epub_path.write_bytes(b'placeholder')
            archive_path = Path(td) / 'empty.zip'
            archive_path.write_bytes(b'placeholder')

            empty_epub = core.EpubInputDocument(
                source_path=epub_path,
                book=None,
                docs=[],
                image_map={},
                image_basename_map={},
                bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
                css_rules=[],
            )
            empty_archive = types.SimpleNamespace(image_files=[])

            with mock.patch.object(core, 'load_epub_input_document', return_value=empty_epub):
                epub_preview = core._render_preview_page_from_target(epub_path, self.font_value, args)
            with mock.patch.object(core, 'load_archive_input_document', return_value=empty_archive):
                archive_preview = core._render_preview_page_from_target(archive_path, self.font_value, args)

        self.assertEqual(epub_preview.tobytes(), blank_expected.tobytes())
        self.assertEqual(archive_preview.tobytes(), blank_expected.tobytes())

    def test_render_preview_page_from_target_uses_default_blocks_when_path_unresolved_or_unsupported(self):
        args = self._conv_args(width=160, height=220)
        fallback_page = Image.new('L', (args.width, args.height), 240)
        with mock.patch.object(core, '_render_text_blocks_to_images', return_value=[fallback_page]) as mocked_render:
            unresolved = core._render_preview_page_from_target('', self.font_value, args)
        self.assertEqual(unresolved.tobytes(), fallback_page.tobytes())
        self.assertTrue(mocked_render.called)

        with tempfile.TemporaryDirectory() as td:
            unsupported = Path(td) / 'sample.pdf'
            unsupported.write_bytes(b'%PDF-1.4')
            with mock.patch.object(core, '_render_text_blocks_to_images', return_value=[]):
                unsupported_preview = core._render_preview_page_from_target(unsupported, self.font_value, args)
        self.assertEqual(unsupported_preview.tobytes(), Image.new('L', (args.width, args.height), 255).tobytes())

    def test_generate_preview_base64_image_mode_supports_gradient_and_invalid_uri_error(self):
        preview = self._decode_preview_image(core.generate_preview_base64({
            'mode': 'image',
            'width': '96',
            'height': '96',
            'threshold': '128',
            'output_format': 'xtch',
            'night_mode': 'true',
            'dither': 'false',
        }))
        self.assertEqual(preview.size, (96, 96))
        lo, hi = preview.getextrema()
        self.assertLess(lo, hi)

        with self.assertRaisesRegex(RuntimeError, 'プレビュー生成に失敗しました'):
            core.generate_preview_base64({
                'mode': 'image',
                'width': '96',
                'height': '96',
                'file_b64': 'not-a-data-uri',
            })


    def test_preview_bundle_cache_normalizes_single_string_and_nested_values(self):
        cache_key = ('preview-cache',)
        core._store_cached_preview_bundle(
            cache_key,
            {
                'pages': {
                    'primary': ' ZmFrZQ== ',
                    'nested': [' QkFTRTY0 ', {'tail': b'VElM'}],
                },
                'truncated': True,
                'source_count': 2,
            },
        )

        cached = core._get_cached_preview_bundle(cache_key)

        self.assertIsNotNone(cached)
        self.assertEqual(cached['pages'], ['ZmFrZQ==', 'QkFTRTY0', 'VElM'])
        self.assertEqual(cached['page_count'], 3)
        self.assertTrue(cached['truncated'])
        self.assertEqual(cached['source_count'], 2)


    def test_preview_bundle_cache_normalizes_string_flags_and_bad_counts(self):
        cache_key = ('preview-cache-bad-flags',)
        core._store_cached_preview_bundle(
            cache_key,
            {
                'pages': ' ZmFrZQ== ',
                'page_count': 'bad-count',
                'truncated': 'false',
                'source_count': 'bad-source',
            },
        )

        cached = core._get_cached_preview_bundle(cache_key)

        self.assertIsNotNone(cached)
        self.assertEqual(cached['pages'], ['ZmFrZQ=='])
        self.assertEqual(cached['page_count'], 1)
        self.assertFalse(cached['truncated'])
        self.assertEqual(cached['source_count'], 0)

    def test_preview_bundle_cache_clamps_negative_source_count_and_zero_page_count(self):
        cache_key = ('preview-cache-negative-counts',)
        core._store_cached_preview_bundle(
            cache_key,
            {
                'pages': ['ZmFrZQ==', 'bW9jaw=='],
                'page_count': 0,
                'truncated': '1',
                'source_count': -5,
            },
        )

        cached = core._get_cached_preview_bundle(cache_key)

        self.assertIsNotNone(cached)
        self.assertEqual(cached['pages'], ['ZmFrZQ==', 'bW9jaw=='])
        self.assertEqual(cached['page_count'], 2)
        self.assertTrue(cached['truncated'])
        self.assertEqual(cached['source_count'], 0)

    def test_generate_preview_bundle_reuses_cached_result_for_same_image_payload(self):
        payload = {
            'mode': 'image',
            'width': 96,
            'height': 96,
            'threshold': 128,
            'output_format': 'xtc',
            'night_mode': False,
            'dither': False,
        }

        calls: list[tuple[int, int]] = []
        original = core.apply_xtc_filter

        def _recording_filter(img, dither, threshold, w, h):
            calls.append((w, h))
            return original(img, dither, threshold, w, h)

        with mock.patch.object(core, 'apply_xtc_filter', side_effect=_recording_filter):
            bundle1 = core.generate_preview_bundle(payload)
            bundle2 = core.generate_preview_bundle(payload)

        self.assertEqual(calls, [(96, 96)])
        self.assertEqual(bundle1, bundle2)

    def test_generate_preview_bundle_cache_invalidates_when_source_timestamp_changes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'sample.txt'
            path.write_text('preview source', encoding='utf-8')
            payload = {
                'mode': 'text',
                'target_path': str(path),
                'font_file': self.font_value,
                'width': 96,
                'height': 144,
                'font_size': 20,
                'ruby_size': 10,
                'line_spacing': 28,
                'margin_t': 8,
                'margin_b': 8,
                'margin_l': 8,
                'margin_r': 8,
                'threshold': 128,
                'output_format': 'xtc',
                'night_mode': False,
                'dither': False,
                'max_pages': 1,
            }
            page = Image.new('L', (96, 144), 255)
            calls: list[str] = []

            def _fake_render(*_args, **_kwargs):
                calls.append('render')
                return [page.copy()], False

            with mock.patch.object(core, '_preview_target_requires_font', return_value=False), \
                 mock.patch.object(core, '_render_preview_pages_from_target', side_effect=_fake_render):
                bundle1 = core.generate_preview_bundle(payload)
                bundle2 = core.generate_preview_bundle(payload)
                self.assertEqual(calls, ['render'])
                path.write_text('preview source updated', encoding='utf-8')
                bundle3 = core.generate_preview_bundle(payload)

        self.assertEqual(calls, ['render', 'render'])
        self.assertEqual(bundle1, bundle2)
        self.assertEqual(bundle1, bundle3)

    def test_generate_preview_bundle_reuses_resolved_source_paths_within_single_render(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'sample.txt'
            path.write_text('preview source', encoding='utf-8')
            payload = {
                'mode': 'text',
                'target_path': str(path),
                'font_file': self.font_value,
                'width': 96,
                'height': 144,
                'font_size': 20,
                'ruby_size': 10,
                'line_spacing': 28,
                'margin_t': 8,
                'margin_b': 8,
                'margin_l': 8,
                'margin_r': 8,
                'threshold': 128,
                'output_format': 'xtc',
                'night_mode': False,
                'dither': False,
                'max_pages': 1,
            }
            page = Image.new('L', (96, 144), 255)
            calls: list[str] = []
            original_resolve = core._resolve_preview_source_paths

            def _recording_resolve(target):
                calls.append(str(target))
                return original_resolve(target)

            with mock.patch.object(core, '_resolve_preview_source_paths', side_effect=_recording_resolve), mock.patch.object(core, '_render_preview_pages_from_target', return_value=([page.copy()], False)) as render_mock:
                core.generate_preview_bundle(payload)

        self.assertEqual(calls, [str(path)])
        kwargs = render_mock.call_args.kwargs
        self.assertIn('preview_sources', kwargs)
        self.assertEqual(len(kwargs['preview_sources']), 1)

    def test_generate_preview_bundle_cache_hit_progress_uses_cached_page_count(self):
        payload = {
            'mode': 'image',
            'width': 96,
            'height': 96,
            'threshold': 128,
            'output_format': 'xtc',
            'night_mode': False,
            'dither': False,
        }
        progress_calls: list[tuple[int, int, str]] = []
        bundle1 = core.generate_preview_bundle(payload)
        bundle2 = core.generate_preview_bundle(payload, progress_cb=lambda c, t, m: progress_calls.append((c, t, m)))
        self.assertEqual(bundle1, bundle2)
        self.assertEqual(progress_calls, [(1, 1, 'キャッシュ済みのプレビューを再利用しています… (1/1 ページ)')])


if __name__ == '__main__':
    unittest.main()
