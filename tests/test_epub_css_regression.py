import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class _FakeCssItem:
    def __init__(self, file_name, css_text, media_type='text/css'):
        self.file_name = file_name
        self.media_type = media_type
        self._css_text = css_text

    def get_content(self):
        return self._css_text.encode('utf-8')


class _FakeBook:
    def __init__(self, items):
        self._items = list(items)

    def get_items(self):
        return list(self._items)


class EpubCssRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.BeautifulSoup = core._require_bs4_beautifulsoup()
        except Exception as exc:
            raise unittest.SkipTest(f'BeautifulSoup unavailable: {exc}')

    def _soup(self, html):
        return self.BeautifulSoup(html, 'html.parser')

    def test_extract_epub_css_rules_parses_simple_and_compound_selectors(self):
        book = _FakeBook([
            _FakeCssItem('styles/main.css', '.hidden { display: none; } p.pb { page-break-before: always; } .note { margin-left: 1em; } .strongish { font-weight: 700; }')
        ])
        rules = core.extract_epub_css_rules(book)
        selectors = {rule['selector'] for rule in rules}
        self.assertIn('.hidden', selectors)
        self.assertIn('p.pb', selectors)
        self.assertIn('.note', selectors)
        self.assertIn('.strongish', selectors)

    def test_css_rules_drive_skip_pagebreak_indent_and_bold(self):
        book = _FakeBook([
            _FakeCssItem('styles/main.css', '.hidden { display: none; } p.pb { page-break-before: always; } .note { margin-left: 1em; } .strongish { font-weight: 700; }')
        ])
        css_rules = core.extract_epub_css_rules(book)
        soup = self._soup('<body><p class="hidden">x</p><p class="pb">y</p><div class="note">z</div><span class="strongish">w</span></body>')
        hidden, pagebreak, note, strongish = soup.find_all(['p', 'p', 'div', 'span'])

        self.assertTrue(core.epub_should_skip_node(hidden, css_rules=css_rules))
        self.assertTrue(core.epub_node_requests_pagebreak(pagebreak, css_rules=css_rules))
        note_profile = core.epub_node_indent_profile(note, css_rules=css_rules, font_size=24)
        self.assertGreaterEqual(note_profile['indent_chars'], 1)
        self.assertGreaterEqual(note_profile['wrap_indent_chars'], 1)
        self.assertTrue(core.node_is_bold(strongish, False, {'classes': set(), 'ids': set(), 'tags': set()}, css_rules=css_rules))


if __name__ == '__main__':
    unittest.main()
