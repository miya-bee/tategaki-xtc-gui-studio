import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


CONTAINER_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''


def _write_epub(path: Path, entries: dict[str, bytes | str]) -> Path:
    with zipfile.ZipFile(path, 'w') as zf:
        zf.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        for name, payload in entries.items():
            if isinstance(payload, str):
                payload = payload.encode('utf-8')
            zf.writestr(name, payload)
    return path


def _opf(manifest: str, spine: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">generated-v13611-fixture</dc:identifier>
    <dc:title>generated fixture</dc:title>
    <dc:language>ja</dc:language>
  </metadata>
  <manifest>{manifest}</manifest>
  <spine>{spine}</spine>
</package>'''


class _FakeItem:
    def __init__(self, file_name: str, content: str):
        self.file_name = file_name
        self.media_type = 'application/xhtml+xml'
        self._content = content.encode('utf-8')

    def get_content(self):
        return self._content


class _FakeBook:
    def __init__(self, items: dict[str, _FakeItem], spine: list[tuple[str, str]]):
        self._items = dict(items)
        self.spine = list(spine)

    def get_item_with_id(self, item_id):
        return self._items.get(item_id)


class EpubGeneratedFixtureSetV13611Tests(unittest.TestCase):
    def _make_fixture(self, entries: dict[str, bytes | str]) -> Path:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        epub_path = Path(tmpdir.name) / 'fixture.epub'
        return _write_epub(epub_path, entries)

    def test_generated_epub_fixture_with_nav_page_passes_preflight(self):
        epub_path = self._make_fixture({
            'META-INF/container.xml': CONTAINER_XML,
            'OPS/content.opf': _opf(
                '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
                '<item id="chap1" href="text/chapter1.xhtml" media-type="application/xhtml+xml"/>',
                '<itemref idref="nav"/><itemref idref="chap1"/>',
            ),
            'OPS/nav.xhtml': '<html xmlns:epub="http://www.idpf.org/2007/ops"><body><nav epub:type="toc"><ol><li>目次項目</li></ol></nav></body></html>',
            'OPS/text/chapter1.xhtml': '<html><body><p>本文だけを変換対象にする。</p></body></html>',
        })

        core._preflight_epub_package(epub_path)

    def test_generated_epub_fixture_with_standalone_footnote_page_passes_preflight(self):
        epub_path = self._make_fixture({
            'META-INF/container.xml': CONTAINER_XML,
            'OPS/content.opf': _opf(
                '<item id="chap1" href="text/chapter1.xhtml" media-type="application/xhtml+xml"/>'
                '<item id="notes" href="text/footnotes.xhtml" media-type="application/xhtml+xml"/>',
                '<itemref idref="chap1"/><itemref idref="notes"/>',
            ),
            'OPS/text/chapter1.xhtml': '<html><body><p>本文<a epub:type="noteref" href="footnotes.xhtml#fn1">[1]</a></p></body></html>',
            'OPS/text/footnotes.xhtml': '<html xmlns:epub="http://www.idpf.org/2007/ops"><body><section epub:type="footnote" id="fn1">脚注本文<a epub:type="backlink" href="chapter1.xhtml#ref1">戻る</a></section></body></html>',
        })

        core._preflight_epub_package(epub_path)

    def test_collect_spine_documents_keeps_chapter_but_drops_generated_nav_and_footnote_docs(self):
        book = _FakeBook(
            {
                'nav': _FakeItem('OPS/nav.xhtml', '<html><body><nav epub:type="toc"><ol><li>目次</li></ol></nav></body></html>'),
                'chap1': _FakeItem('OPS/text/chapter1.xhtml', '<html><body><p>本文</p></body></html>'),
                'notes': _FakeItem('OPS/text/footnotes.xhtml', '<html><body><section epub:type="footnote">脚注本文</section></body></html>'),
            },
            [('nav', 'yes'), ('chap1', 'yes'), ('notes', 'yes')],
        )

        docs = core._collect_epub_spine_documents(book)
        self.assertEqual([item.file_name for item in docs], ['OPS/text/chapter1.xhtml'])


if __name__ == '__main__':
    unittest.main()
