import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


def _write_epub(path: Path, entries: dict[str, bytes | str]) -> None:
    with zipfile.ZipFile(path, 'w') as zf:
        for name, payload in entries.items():
            if isinstance(payload, str):
                payload = payload.encode('utf-8')
            zf.writestr(name, payload)


CONTAINER = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''


def _opf(manifest: str, spine: str) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>dummy</dc:title></metadata>
  <manifest>{manifest}</manifest>
  <spine>{spine}</spine>
</package>'''


class EpubDiagnosticsRegressionV13610Tests(unittest.TestCase):
    def test_preflight_reports_not_zip_epub(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'not_zip.epub'
            epub_path.write_text('not a zip', encoding='utf-8')
            with self.assertRaises(RuntimeError) as ctx:
                core._preflight_epub_package(epub_path)
        self.assertIn('ZIPとして開けませんでした', str(ctx.exception))

    def test_preflight_reports_missing_container_xml(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'missing_container.epub'
            _write_epub(epub_path, {'mimetype': 'application/epub+zip'})
            with self.assertRaises(RuntimeError) as ctx:
                core._preflight_epub_package(epub_path)
        self.assertIn('META-INF/container.xml が見つかりません', str(ctx.exception))

    def test_preflight_reports_missing_opf(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'missing_opf.epub'
            _write_epub(epub_path, {'META-INF/container.xml': CONTAINER})
            with self.assertRaises(RuntimeError) as ctx:
                core._preflight_epub_package(epub_path)
        self.assertIn('OPF パッケージ文書が見つかりません', str(ctx.exception))

    def test_preflight_reports_empty_spine(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'empty_spine.epub'
            _write_epub(epub_path, {
                'META-INF/container.xml': CONTAINER,
                'OEBPS/content.opf': _opf('<item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>', ''),
                'OEBPS/chap1.xhtml': '<html><body><p>本文</p></body></html>',
            })
            with self.assertRaises(RuntimeError) as ctx:
                core._preflight_epub_package(epub_path)
        self.assertIn('読み順情報 spine が見つかりません', str(ctx.exception))

    def test_preflight_reports_spine_manifest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'bad_idref.epub'
            _write_epub(epub_path, {
                'META-INF/container.xml': CONTAINER,
                'OEBPS/content.opf': _opf('<item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>', '<itemref idref="missing"/>'),
                'OEBPS/chap1.xhtml': '<html><body><p>本文</p></body></html>',
            })
            with self.assertRaises(RuntimeError) as ctx:
                core._preflight_epub_package(epub_path)
        self.assertIn('manifest に存在しない項目', str(ctx.exception))

    def test_preflight_reports_missing_spine_xhtml_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'missing_chapter.epub'
            _write_epub(epub_path, {
                'META-INF/container.xml': CONTAINER,
                'OEBPS/content.opf': _opf('<item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>', '<itemref idref="chap1"/>'),
            })
            with self.assertRaises(RuntimeError) as ctx:
                core._preflight_epub_package(epub_path)
        self.assertIn('spine が参照する本文ファイルが見つかりません', str(ctx.exception))

    def test_conversion_error_report_specializes_epub_structure_failures(self) -> None:
        report = core.build_conversion_error_report('bad.epub', RuntimeError('EPUB の読み順情報 spine が見つかりません。本文の順番を判断できません。'), stage='EPUB読込')
        self.assertEqual(report['headline'], 'EPUB の読み順情報 spine に問題があります。')
        self.assertIn('linear="no"', report['hint'])

    def test_encryption_descriptor_is_detected_without_rejecting_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'encrypted_marker.epub'
            _write_epub(epub_path, {
                'META-INF/container.xml': CONTAINER,
                'META-INF/encryption.xml': '<encryption/>',
                'OEBPS/content.opf': _opf('<item id="chap1" href="chap1.xhtml" media-type="application/xhtml+xml"/>', '<itemref idref="chap1"/>'),
                'OEBPS/chap1.xhtml': '<html><body><p>本文</p></body></html>',
            })
            core._preflight_epub_package(epub_path)
            self.assertTrue(core._epub_package_has_encryption_descriptor(epub_path))


if __name__ == '__main__':
    unittest.main()
