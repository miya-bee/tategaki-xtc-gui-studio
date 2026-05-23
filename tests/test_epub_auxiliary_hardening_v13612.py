import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class _FakeItem:
    def __init__(self, file_name: str, content: str, media_type: str = 'application/xhtml+xml'):
        self.file_name = file_name
        self.media_type = media_type
        self._content = content.encode('utf-8')

    def get_content(self):
        return self._content


class _FakeBook:
    def __init__(self, items: dict[str, _FakeItem], spine: list[tuple[str, str]]):
        self._items = dict(items)
        self.spine = list(spine)

    def get_item_with_id(self, item_id):
        return self._items.get(item_id)


class EpubAuxiliaryHardeningV13612Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.BeautifulSoup = core._require_bs4_beautifulsoup()
        except Exception as exc:
            raise unittest.SkipTest(f'BeautifulSoup unavailable: {exc}')

    def _soup(self, html: str):
        return self.BeautifulSoup(html, 'html.parser')

    def test_navigation_role_node_is_skipped_but_plain_nav_tag_stays_legacy_safe(self):
        soup = self._soup('<body><nav role="navigation">目次</nav><nav>本文扱いの可能性があるnav</nav></body>')
        nav_with_role, plain_nav = soup.find_all('nav')

        self.assertTrue(core.epub_should_skip_node(nav_with_role))
        self.assertFalse(core.epub_should_skip_node(plain_nav))

    def test_explicit_noteref_is_skipped_even_when_text_is_not_numeric_marker(self):
        soup = self._soup('<body><p>本文<a epub:type="noteref" href="#fn1">脚注へ</a>続き</p></body>')
        link = soup.find('a')

        self.assertTrue(core.epub_should_skip_node(link))

    def test_collect_spine_documents_drops_plain_nav_and_toc_filenames(self):
        book = _FakeBook(
            {
                'nav': _FakeItem('OPS/nav.xhtml', '<html><body><nav><ol><li>目次</li></ol></nav></body></html>'),
                'toc': _FakeItem('OPS/toc.xhtml', '<html><body><ol><li>章一覧</li></ol></body></html>'),
                'chap': _FakeItem('OPS/text/chapter.xhtml', '<html><body><p>本文</p></body></html>'),
            },
            [('nav', 'yes'), ('toc', 'yes'), ('chap', 'yes')],
        )

        docs = core._collect_epub_spine_documents(book)

        self.assertEqual([item.file_name for item in docs], ['OPS/text/chapter.xhtml'])

    def test_collect_spine_documents_drops_plain_footnotes_filename(self):
        book = _FakeBook(
            {
                'chap': _FakeItem('OPS/text/chapter.xhtml', '<html><body><p>本文</p></body></html>'),
                'notes': _FakeItem('OPS/text/footnotes.xhtml', '<html><body><ol><li>脚注本文</li></ol></body></html>'),
            },
            [('chap', 'yes'), ('notes', 'yes')],
        )

        docs = core._collect_epub_spine_documents(book)

        self.assertEqual([item.file_name for item in docs], ['OPS/text/chapter.xhtml'])


if __name__ == '__main__':
    unittest.main()
