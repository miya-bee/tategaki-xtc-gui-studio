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


class _FakeEpubItem:
    def __init__(self, file_name, html):
        self.file_name = file_name
        self._html = html

    def get_content(self):
        return self._html.encode('utf-8')


class EpubRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.BeautifulSoup = core._require_bs4_beautifulsoup()
        except Exception as exc:
            raise unittest.SkipTest(f'BeautifulSoup unavailable: {exc}')

    def _soup(self, html):
        return self.BeautifulSoup(html, 'html.parser')

    def test_pagebreak_detection_covers_hr_class_and_style(self):
        soup = self._soup(
            '<body>'
            '<hr/>'
            '<div class="mbp_pagebreak"></div>'
            '<section style="page-break-before: always"></section>'
            '<section style="break-before: page-region"></section>'
            '</body>'
        )
        nodes = soup.find_all(['hr', 'div', 'section'])
        self.assertTrue(core.epub_node_requests_pagebreak(nodes[0]))
        self.assertTrue(core.epub_node_requests_pagebreak(nodes[1]))
        self.assertTrue(core.epub_node_requests_pagebreak(nodes[2]))
        self.assertFalse(core.epub_node_requests_pagebreak(nodes[3]))
        self.assertTrue(core.epub_pagebreak_node_is_marker(nodes[1]))

    def test_skip_node_hides_toc_nav_and_display_none(self):
        soup = self._soup(
            '<body>'
            '<nav epub:type="toc">...</nav>'
            '<div style="display: none">hidden</div>'
            '<p>visible</p>'
            '</body>'
        )
        nav, hidden, para = soup.find_all(['nav', 'div', 'p'])
        self.assertTrue(core.epub_should_skip_node(nav))
        self.assertTrue(core.epub_should_skip_node(hidden))
        self.assertFalse(core.epub_should_skip_node(para))

    def test_indent_profile_marks_headings_notes_and_lists(self):
        soup = self._soup('''<body><h1>章題</h1><aside class="note">注記</aside><ol start="3">
<li>項目</li>
<li value="7">別項目</li>
</ol></body>''')
        heading = soup.find('h1')
        aside = soup.find('aside')
        items = soup.find_all('li')

        heading_profile = core.epub_node_indent_profile(heading)
        self.assertEqual(heading_profile['heading_level'], 1)
        self.assertEqual(heading_profile['blank_before'], 2)

        aside_profile = core.epub_node_indent_profile(aside)
        self.assertEqual(aside_profile['indent_chars'], 1)
        self.assertEqual(aside_profile['wrap_indent_chars'], 1)
        self.assertTrue(core.epub_node_is_note_like(aside))

        first_li_profile = core.epub_node_indent_profile(items[0])
        second_li_profile = core.epub_node_indent_profile(items[1])
        self.assertEqual(first_li_profile['prefix'], '3．　')
        self.assertEqual(second_li_profile['prefix'], '7．　')
        self.assertEqual(first_li_profile['wrap_indent_chars'], 1)

    def test_process_epub_respects_pagebreak_marker(self):
        fake_doc = core.EpubInputDocument(
            source_path=Path('dummy.epub'),
            book=None,
            docs=[_FakeEpubItem('text/chapter1.xhtml', '<html><body><p>前半の本文です。</p><hr/><p>後半の本文です。</p></body></html>')],
            image_map={},
            image_basename_map={},
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
        )
        font_path = resolve_test_font_path()
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtc'
            with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc):
                result = core.process_epub('dummy.epub', font_path, args, output_path=out_path)
            self.assertEqual(result, out_path)
            header = out_path.read_bytes()[:48]
            mark, version, page_count, *_ = struct.unpack('<4sHHBBBBIQQQQ', header)
            self.assertEqual(mark, b'XTC\x00')
            self.assertEqual(version, 1)
            self.assertEqual(page_count, 2)

    def test_process_epub_nested_inline_text_does_not_gain_spurious_indent(self):
        fake_doc = core.EpubInputDocument(
            source_path=Path('dummy.epub'),
            book=None,
            docs=[_FakeEpubItem('text/chapter1.xhtml', '<html><body><p><span>甲</span>乙</p></body></html>')],
            image_map={},
            image_basename_map={},
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
        )
        font_path = resolve_test_font_path()
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        captured_pages = []

        def fake_page_image_to_xt_bytes(image, width, height, page_args):
            captured_pages.append(image.copy())
            return b'page'

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtc'
            with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc), \
                 mock.patch.object(core, 'page_image_to_xt_bytes', side_effect=fake_page_image_to_xt_bytes):
                result = core.process_epub('dummy.epub', font_path, args, output_path=out_path)
            self.assertEqual(result, out_path)

        self.assertTrue(captured_pages)
        first_bbox = ImageOps.invert(captured_pages[0]).getbbox()
        self.assertIsNotNone(first_bbox)
        self.assertLess(first_bbox[1], 25)


if __name__ == '__main__':
    unittest.main()
