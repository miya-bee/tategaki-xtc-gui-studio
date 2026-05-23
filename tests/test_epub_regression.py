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
    def __init__(self, file_name, html, media_type='application/xhtml+xml'):
        self.file_name = file_name
        self.media_type = media_type
        self._html = html

    def get_content(self):
        return self._html.encode('utf-8')


class _FakeSpineBook:
    def __init__(self, spine, items):
        self.spine = spine
        self._items = dict(items)

    def get_item_with_id(self, item_id):
        return self._items.get(item_id)


class EpubRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.BeautifulSoup = core._require_bs4_beautifulsoup()
        except Exception as exc:
            raise unittest.SkipTest(f'BeautifulSoup unavailable: {exc}')

    def _soup(self, html):
        return self.BeautifulSoup(html, 'html.parser')

    def test_collect_epub_spine_documents_skips_explicit_linear_no(self):
        main = _FakeEpubItem('text/main.xhtml', '<html><body>Main</body></html>')
        aux = _FakeEpubItem('text/aux.xhtml', '<html><body>Aux</body></html>')
        dict_aux = _FakeEpubItem('text/dict_aux.xhtml', '<html><body>DictAux</body></html>')
        html_by_suffix = _FakeEpubItem('text/suffix.html', '<html><body>Suffix</body></html>', media_type='')
        image = _FakeEpubItem('images/cover.png', '', media_type='image/png')
        book = _FakeSpineBook(
            [('main', 'yes'), ('aux', 'no'), ('dict_aux', {'linear': 'no'}), 'suffix', ('cover', 'yes')],
            {'main': main, 'aux': aux, 'dict_aux': dict_aux, 'suffix': html_by_suffix, 'cover': image},
        )

        docs = core._collect_epub_spine_documents(book)

        self.assertEqual(docs, [main, html_by_suffix])
        self.assertTrue(core._epub_spine_entry_is_linear(('main', 'yes')))
        self.assertFalse(core._epub_spine_entry_is_linear(('aux', 'no')))

    def test_extract_epub_ruby_parts_does_not_leak_rtc_into_body(self):
        soup = self._soup(
            '<ruby>'
            '<rb>振</rb><rb>仮</rb><rb>名</rb>'
            '<rtc><rt>ふ</rt><rt>り</rt><rt>がな</rt></rtc>'
            '</ruby>'
        )

        rb, rt = core._extract_epub_ruby_parts(soup.ruby)

        self.assertEqual(rb, '振仮名')
        self.assertEqual(rt, 'ふりがな')

    def test_extract_epub_ruby_parts_handles_simple_ruby_and_rp(self):
        soup = self._soup('<ruby>吾輩<rp>（</rp><rt>わがはい</rt><rp>）</rp></ruby>')

        rb, rt = core._extract_epub_ruby_parts(soup.ruby)

        self.assertEqual(rb, '吾輩')
        self.assertEqual(rt, 'わがはい')

    def test_epub_image_node_source_accepts_svg_href(self):
        soup = self._soup('<svg><image href="../images/fig.png" /></svg>')

        self.assertEqual(core._epub_image_node_source(soup.image), '../images/fig.png')


    def test_data_uri_and_srcset_helpers(self):
        import base64
        payload = b'png-bytes'
        uri = 'data:image/png;base64,' + base64.b64encode(payload).decode('ascii')
        soup = self._soup('<img srcset="../images/a.png 1x, ../images/b.png 2x"/>')

        self.assertEqual(core._first_epub_srcset_candidate(soup.img.get('srcset')), '../images/a.png')
        self.assertEqual(core._decode_epub_data_image_uri(uri), payload)
        self.assertEqual(core._resolve_epub_image_data('OPS/text/ch.xhtml', uri, {}, {}), ('data:image', payload))

    def test_background_and_picture_image_sources(self):
        soup = self._soup(
            '<body>'
            '<picture><source srcset="../images/hi.png 2x"><img src="../images/fallback.png"></picture>'
            '<div class="cover"></div>'
            '</body>'
        )
        css_rules = [{'selector': '.cover', 'declarations': {'background-image': 'url("../images/bg.png")'}}]

        self.assertEqual(core._epub_picture_node_source(soup.picture), '../images/fallback.png')
        self.assertEqual(core._epub_background_image_source(soup.div, css_rules), '../images/bg.png')

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
