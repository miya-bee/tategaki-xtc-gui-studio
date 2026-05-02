import base64
import io
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
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec
from tests.sample_fixture_builders import build_sample_epub, fixture_path


class SampleFixtureRegressionTests(unittest.TestCase):
    def setUp(self):
        core.clear_input_document_cache()
        core.clear_preview_bundle_cache()

    @classmethod
    def setUpClass(cls):
        cls.font_value = resolve_test_font_spec()
        try:
            core._require_bs4_beautifulsoup()
            cls._bs4_ok = True
        except Exception:
            cls._bs4_ok = False
        try:
            core._require_ebooklib_epub()
            cls._epub_ok = True
        except Exception:
            cls._epub_ok = False

    def _base_args(self):
        return {
            'width': '160',
            'height': '220',
            'font_size': '26',
            'ruby_size': '12',
            'line_spacing': '44',
            'margin_t': '12',
            'margin_b': '14',
            'margin_r': '12',
            'margin_l': '12',
            'dither': 'false',
            'threshold': '128',
            'night_mode': 'false',
            'kinsoku_mode': 'standard',
            'output_format': 'xtc',
            'mode': 'text',
            'font_file': self.font_value,
        }

    def _conv_args(self):
        return core.ConversionArgs(
            width=160,
            height=220,
            font_size=26,
            ruby_size=12,
            line_spacing=44,
            margin_t=12,
            margin_b=14,
            margin_r=12,
            margin_l=12,
            dither=False,
            night_mode=False,
            threshold=128,
            kinsoku_mode='standard',
            output_format='xtc',
        )

    @staticmethod
    def _decode_preview_image(preview_b64: str) -> Image.Image:
        return Image.open(io.BytesIO(base64.b64decode(preview_b64))).convert('L')

    def test_aozora_fixture_preview_matches_rendered_first_page(self):
        text_path = fixture_path('sample_aozora.txt')
        args = self._base_args()
        args['target_path'] = str(text_path)
        preview_img = self._decode_preview_image(core.generate_preview_base64(args))

        document = core.load_text_input_document(text_path, parser='plain')
        self.assertTrue(any(run.get('ruby') == 'わがはい' for block in document.blocks for run in block.get('runs', [])))
        expected_pages = core._render_text_blocks_to_images(
            core._select_preview_blocks(document.blocks),
            self.font_value,
            self._conv_args(),
        )
        self.assertTrue(expected_pages)
        expected = core.apply_xtc_filter(expected_pages[0], False, 128, 160, 220).convert('L')
        self.assertEqual(preview_img.tobytes(), expected.tobytes())

    def test_markdown_fixture_preview_matches_rendered_first_page(self):
        md_path = fixture_path('sample_notes.md')
        args = self._base_args()
        args['target_path'] = str(md_path)
        preview_img = self._decode_preview_image(core.generate_preview_base64(args))

        document = core.load_text_input_document(md_path, parser='markdown')
        support_text = ''.join(document.support_summary or [])
        self.assertIn('脚注', support_text)
        expected_pages = core._render_text_blocks_to_images(
            core._select_preview_blocks(document.blocks),
            self.font_value,
            self._conv_args(),
        )
        self.assertTrue(expected_pages)
        expected = core.apply_xtc_filter(expected_pages[0], False, 128, 160, 220).convert('L')
        self.assertEqual(preview_img.tobytes(), expected.tobytes())

    def test_real_epub_fixture_loads_preview_and_processes_to_xtc(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            epub_path = build_sample_epub(tmpdir_path / 'sample_fixture.epub')

            if self._bs4_ok and self._epub_ok:
                document = core.load_epub_input_document(epub_path)
                self.assertTrue(document.docs)
                selectors = {rule['selector'] for rule in document.css_rules}
                self.assertIn('.hidden', selectors)
                self.assertIn('.pagebreak', selectors)

                args = self._base_args()
                args['target_path'] = str(epub_path)
                preview_img = self._decode_preview_image(core.generate_preview_base64(args))

                font = core.load_truetype_font(self.font_value, 26)
                ruby_font = core.load_truetype_font(self.font_value, 12)
                chapter_pages = core._render_epub_chapter_pages_from_html(
                    document.docs[0].get_content(),
                    document.docs[0].file_name,
                    self._conv_args(),
                    font,
                    ruby_font,
                    document.bold_rules,
                    document.image_map,
                    document.image_basename_map,
                    document.css_rules,
                )
                self.assertGreaterEqual(len(chapter_pages), 2)
                expected = core.apply_xtc_filter(chapter_pages[0]['image'], False, 128, 160, 220).convert('L')
                self.assertEqual(preview_img.tobytes(), expected.tobytes())

                output_path = tmpdir_path / 'sample_fixture.xtc'
                result = core.process_epub(epub_path, self.font_value, self._conv_args(), output_path=output_path)
                self.assertEqual(result, output_path)
                self.assertTrue(output_path.exists())
                self.assertEqual(output_path.read_bytes()[:4], b'XTC\x00')
            else:
                class FakeItem:
                    file_name = 'text/chapter1.xhtml'
                    def get_content(self):
                        return b'<html></html>'

                fake_doc = core.EpubInputDocument(
                    source_path=epub_path,
                    book=None,
                    docs=[FakeItem()],
                    image_map={},
                    image_basename_map={},
                    bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
                    css_rules=[{'selector': '.hidden', 'declarations': {'display': 'none'}}, {'selector': '.pagebreak', 'declarations': {'page-break-before': 'always'}}],
                )
                fallback_pages = [
                    {'image': Image.new('L', (160, 220), 255), 'args': self._conv_args(), 'label': '本文'},
                    {'image': Image.new('L', (160, 220), 240), 'args': self._conv_args(), 'label': '本文'},
                ]
                args = self._base_args()
                args['target_path'] = str(epub_path)
                with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc), \
                     mock.patch.object(core, '_render_epub_chapter_pages_from_html', return_value=fallback_pages):
                    preview_img = self._decode_preview_image(core.generate_preview_base64(args))
                    expected = core.apply_xtc_filter(fallback_pages[0]['image'], False, 128, 160, 220).convert('L')
                    self.assertEqual(preview_img.tobytes(), expected.tobytes())
                    output_path = tmpdir_path / 'sample_fixture.xtc'
                    result = core.process_epub(epub_path, self.font_value, self._conv_args(), output_path=output_path)
                    self.assertEqual(result, output_path)
                    self.assertTrue(output_path.exists())
                    self.assertEqual(output_path.read_bytes()[:4], b'XTC\x00')

    def test_load_epub_input_document_reuses_cache_until_source_changes(self):
        if not self._epub_ok:
            self.skipTest('ebooklib unavailable')
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            epub_path = build_sample_epub(tmpdir_path / 'sample_fixture.epub')

            real_epub_module = core._require_ebooklib_epub()

            class FakeEpubModule:
                def __init__(self):
                    self.calls = 0
                def read_epub(self, path_value):
                    self.calls += 1
                    return real_epub_module.read_epub(path_value)

            fake_epub = FakeEpubModule()
            with mock.patch.object(core, '_require_ebooklib_epub', return_value=fake_epub):
                doc1 = core.load_epub_input_document(epub_path)
                doc2 = core.load_epub_input_document(epub_path)
                self.assertIs(doc1, doc2)
                self.assertEqual(fake_epub.calls, 1)
                original_bytes = epub_path.read_bytes()
                epub_path.write_bytes(original_bytes + b' ')
                doc3 = core.load_epub_input_document(epub_path)

        self.assertEqual(fake_epub.calls, 2)
        self.assertIsNot(doc1, doc3)
        self.assertTrue(doc3.docs)


if __name__ == '__main__':
    unittest.main()
