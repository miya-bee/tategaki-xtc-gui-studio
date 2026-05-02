import base64
import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec


class _FakeEpubItem:
    def __init__(self, file_name, html):
        self.file_name = file_name
        self._html = html

    def get_content(self):
        return self._html.encode('utf-8')


class RealFilePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_value = resolve_test_font_spec()
        try:
            core._require_bs4_beautifulsoup()
            cls._bs4_ok = True
        except Exception:
            cls._bs4_ok = False

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

    @staticmethod
    def _decode_preview_image(preview_b64: str) -> Image.Image:
        return Image.open(io.BytesIO(base64.b64decode(preview_b64))).convert('L')

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

    def test_preview_uses_selected_plain_text_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = Path(tmpdir) / 'sample.txt'
            text_path.write_text('第一段落です。\n\n｜吾輩《わがはい》は猫である。\n第二段落です。', encoding='utf-8')

            args = self._base_args()
            args['target_path'] = str(text_path)
            preview_img = self._decode_preview_image(core.generate_preview_base64(args))

            document = core.load_text_input_document(text_path, parser='plain')
            expected_pages = core._render_text_blocks_to_images(
                core._select_preview_blocks(document.blocks),
                self.font_value,
                self._conv_args(),
            )
            self.assertTrue(expected_pages)
            expected = core.apply_xtc_filter(expected_pages[0], False, 128, 160, 220).convert('L')

            self.assertEqual(preview_img.tobytes(), expected.tobytes())

    def test_preview_uses_selected_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = Path(tmpdir) / 'sample.md'
            text_path.write_text('# 見出し\n\n- 項目A\n- 項目B\n\n本文です。', encoding='utf-8')

            args = self._base_args()
            args['target_path'] = str(text_path)
            preview_img = self._decode_preview_image(core.generate_preview_base64(args))

            document = core.load_text_input_document(text_path, parser='markdown')
            expected_pages = core._render_text_blocks_to_images(
                core._select_preview_blocks(document.blocks),
                self.font_value,
                self._conv_args(),
            )
            self.assertTrue(expected_pages)
            expected = core.apply_xtc_filter(expected_pages[0], False, 128, 160, 220).convert('L')

            self.assertEqual(preview_img.tobytes(), expected.tobytes())


    def test_preview_uses_selected_image_without_font(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / 'sample.png'
            src = Image.new('L', (80, 40), 255)
            src.paste(0, (20, 10, 60, 30))
            src.save(image_path)

            args = self._base_args()
            args['target_path'] = str(image_path)
            args['font_file'] = ''
            preview_img = self._decode_preview_image(core.generate_preview_base64(args))

            with Image.open(image_path) as img:
                expected_page = core._preview_fit_image(img, self._conv_args())
            expected = core.apply_xtc_filter(expected_page, False, 128, 160, 220).convert('L')
            self.assertEqual(preview_img.tobytes(), expected.tobytes())

    def test_preview_uses_selected_zip_without_font(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / '001.png'
            archive_path = Path(tmpdir) / 'sample.zip'
            src = Image.new('L', (90, 50), 255)
            src.paste(0, (15, 10, 75, 40))
            src.save(image_path)
            with zipfile.ZipFile(archive_path, 'w') as zf:
                zf.write(image_path, arcname='001.png')

            args = self._base_args()
            args['target_path'] = str(archive_path)
            args['font_file'] = ''
            with mock.patch.object(core, 'load_archive_input_document', side_effect=AssertionError('zip preview should not extract the archive')):
                preview_img = self._decode_preview_image(core.generate_preview_base64(args))

            with Image.open(image_path) as img:
                expected_page = core._preview_fit_image(img, self._conv_args())
            expected = core.apply_xtc_filter(expected_page, False, 128, 160, 220).convert('L')
            self.assertEqual(preview_img.tobytes(), expected.tobytes())

    def test_preview_uses_selected_epub_file_first_chapter(self):
        fake_doc = core.EpubInputDocument(
            source_path=Path('dummy.epub'),
            book=None,
            docs=[_FakeEpubItem('text/chapter1.xhtml', '<html><body><p>前半の本文です。</p><hr/><p>後半の本文です。</p></body></html>')],
            image_map={},
            image_basename_map={},
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
            css_rules=[],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            epub_path = Path(tmpdir) / 'dummy.epub'
            epub_path.write_bytes(b'not-a-real-epub')
            args = self._base_args()
            args['target_path'] = str(epub_path)
            with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc):
                if self._bs4_ok:
                    preview_img = self._decode_preview_image(core.generate_preview_base64(args))
                    font = core.load_truetype_font(self.font_value, 26)
                    ruby_font = core.load_truetype_font(self.font_value, 12)
                    chapter_pages = core._render_epub_chapter_pages_from_html(
                        fake_doc.docs[0].get_content(),
                        fake_doc.docs[0].file_name,
                        self._conv_args(),
                        font,
                        ruby_font,
                        fake_doc.bold_rules,
                        fake_doc.image_map,
                        fake_doc.image_basename_map,
                        fake_doc.css_rules,
                    )
                else:
                    fallback_page = Image.new('L', (160, 220), 255)
                    chapter_pages = [{'image': fallback_page, 'args': self._conv_args(), 'label': '本文'}]
                    with mock.patch.object(core, '_render_epub_chapter_pages_from_html', return_value=chapter_pages):
                        preview_img = self._decode_preview_image(core.generate_preview_base64(args))
            self.assertTrue(chapter_pages)
            expected = core.apply_xtc_filter(chapter_pages[0]['image'], False, 128, 160, 220).convert('L')
            self.assertEqual(preview_img.tobytes(), expected.tobytes())

    def test_preview_bundle_exact_max_pages_is_not_truncated_for_plain_text(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = Path(tmpdir) / 'sample.txt'
            text_path.write_text('第一段落です。', encoding='utf-8')
            args = self._base_args()
            args['target_path'] = str(text_path)
            args['max_pages'] = '1'
            fake_page = Image.new('L', (160, 220), 255)
            with mock.patch.object(core, '_render_text_blocks_to_images', return_value=[fake_page]):
                bundle = core.generate_preview_bundle(args)

        self.assertFalse(bundle.get('truncated'))




if __name__ == '__main__':
    unittest.main()
