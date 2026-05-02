import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


class _BrokenGetTextPagebreakNode:
    name = 'div'

    def get(self, key, default=None):
        if key == 'class':
            return ['pagebreak']
        return default

    def get_text(self, *args, **kwargs):
        raise RuntimeError('boom')

    @property
    def descendants(self):
        return []


class _MissingGetAttrNode:
    pass


class EpubStructureProgressRegressionTests(unittest.TestCase):
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

    def test_epub_helper_fallbacks_cover_missing_name_bad_start_and_broken_get_text(self):
        self.assertEqual(core._epub_node_attr_tokens(_MissingGetAttrNode()), [])
        self.assertFalse(core.epub_should_skip_node(_MissingGetAttrNode()))
        self.assertTrue(core.epub_pagebreak_node_is_marker(_BrokenGetTextPagebreakNode()))

        BeautifulSoup = core._require_bs4_beautifulsoup()
        soup = BeautifulSoup('<ol start="bad"><li>A</li><li>B</li></ol>', 'html.parser')
        items = soup.find_all('li')
        self.assertEqual(core._epub_list_item_prefix(items[0]), '1．　')

        detached = BeautifulSoup('<li>C</li>', 'html.parser').li
        detached.parent = soup.ol
        self.assertEqual(core._epub_list_item_prefix(detached), '1．　')

    def test_epub_indent_profile_handles_definition_term_and_description_nodes(self):
        BeautifulSoup = core._require_bs4_beautifulsoup()
        soup = BeautifulSoup('<dl><dt>語</dt><dd>説明</dd></dl>', 'html.parser')
        dt = soup.find('dt')
        dd = soup.find('dd')

        dt_profile = core.epub_node_indent_profile(dt)
        dd_profile = core.epub_node_indent_profile(dd)

        self.assertEqual(dt_profile['indent_chars'], 0)
        self.assertEqual(dt_profile['wrap_indent_chars'], 0)
        self.assertEqual(dt_profile['prefix'], '')
        self.assertGreaterEqual(dd_profile['indent_chars'], 1)
        self.assertGreaterEqual(dd_profile['wrap_indent_chars'], 1)

    def test_render_epub_chapter_pages_renders_lists_and_definition_content_in_order(self):
        args = core.ConversionArgs(
            width=320,
            height=480,
            font_size=24,
            ruby_size=12,
            line_spacing=40,
            output_format='xtc',
        )
        font, ruby_font = self._load_fonts(args)
        html = (
            '<html><body>'
            '<ol start="2"><li>甲</li><li value="7">乙</li></ol>'
            '<ul><li>丙</li></ul>'
            '<dl><dt>語</dt><dd>説明</dd></dl>'
            '</body></html>'
        )
        recorded = []
        original_draw_char_tate = core.draw_char_tate

        def recording_draw(draw, char, pos_tuple, font_obj, f_size, **kwargs):
            recorded.append((char, pos_tuple))
            return None

        try:
            core.draw_char_tate = recording_draw
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter.xhtml',
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
        rendered = ''.join(ch for ch, _ in recorded).replace(' ', '').replace('　', '')
        self.assertIn('2．甲', rendered)
        self.assertIn('7．乙', rendered)
        self.assertIn('・丙', rendered)
        self.assertIn('語説明', rendered)

        first_go_y = next(y for ch, (_, y) in recorded if ch == '語')
        first_setsu_y = next(y for ch, (_, y) in recorded if ch == '説')
        self.assertGreater(first_setsu_y, first_go_y)

    def test_render_epub_chapter_pages_keeps_table_cell_text(self):
        args = core.ConversionArgs(
            width=320,
            height=480,
            font_size=24,
            ruby_size=12,
            line_spacing=40,
            output_format='xtc',
        )
        font, ruby_font = self._load_fonts(args)
        html = (
            '<html><body>'
            '<table>'
            '<tr><th>見出</th><td>値</td></tr>'
            '<tr><td>甲</td><td>乙</td></tr>'
            '</table>'
            '</body></html>'
        )
        recorded = []
        original_draw_char_tate = core.draw_char_tate

        def recording_draw(draw, char, pos_tuple, font_obj, f_size, **kwargs):
            recorded.append(char)
            return None

        try:
            core.draw_char_tate = recording_draw
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter.xhtml',
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
        rendered = ''.join(recorded)
        self.assertIn('見出', rendered)
        self.assertIn('値', rendered)
        self.assertIn('甲乙', rendered)

    def test_process_epub_emits_progress_messages_for_parse_render_convert_and_write(self):
        fake_doc = core.EpubInputDocument(
            source_path=Path('dummy.epub'),
            book=None,
            docs=[
                _FakeEpubItem('text/chapter1.xhtml', '<html><body><p>第一章です。</p></body></html>'),
                _FakeEpubItem('text/chapter2.xhtml', '<html><body><p>第二章です。</p></body></html>'),
            ],
            image_map={},
            image_basename_map={},
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
            css_rules=[],
        )
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        progress_log = []

        def progress_cb(done, total, message):
            progress_log.append((done, total, message))

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtc'
            with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc):
                result = core.process_epub('dummy.epub', self.font_path, args, output_path=out_path, progress_cb=progress_cb)

        self.assertEqual(result.name, 'sample.xtc')
        messages = '\n'.join(message for _, _, message in progress_log)
        self.assertIn('EPUBを解析しました。', messages)
        self.assertIn('章を描画中…', messages)
        self.assertIn('ページ目', messages)
        self.assertIn('章の描画済みページを変換中…', messages)
        self.assertIn('章のページ変換が完了しました。', messages)
        self.assertIn('章の変換を完了しました。', messages)
        self.assertIn('XTCを書き出しました。', messages)


if __name__ == '__main__':
    unittest.main()
