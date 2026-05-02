import builtins
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
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec


class _FakeEpubItem:
    def __init__(self, file_name: str, html: str):
        self.file_name = file_name
        self._html = html

    def get_content(self):
        return self._html.encode('utf-8')


class DependencyHelperRegressionTests(unittest.TestCase):
    def test_list_optional_dependency_status_uses_module_availability(self):
        def fake_available(module_name: str) -> bool:
            return module_name in {'ebooklib', 'patoolib'}

        with mock.patch.object(core, '_is_module_available', side_effect=fake_available):
            statuses = core.list_optional_dependency_status()

        by_key = {item['key']: item for item in statuses}
        self.assertTrue(by_key['ebooklib']['available'])
        self.assertTrue(by_key['patool']['available'])
        self.assertFalse(by_key['beautifulsoup4']['available'])
        self.assertIn('numpy', by_key)
        self.assertEqual(by_key['numpy']['impact'], 'performance')
        self.assertEqual(by_key['tqdm']['impact'], 'convenience')

    def test_get_missing_dependencies_for_suffixes_deduplicates_requirements(self):
        def fake_available(module_name: str) -> bool:
            return module_name == 'ebooklib'

        with mock.patch.object(core, '_is_module_available', side_effect=fake_available):
            missing = core.get_missing_dependencies_for_suffixes(['.epub', '.rar', '.cbr', '.epub'])

        self.assertEqual([item['key'] for item in missing], ['beautifulsoup4', 'patool'])

    def test_require_patoolib_returns_module_from_sys_modules(self):
        fake_module = types.SimpleNamespace(extract_archive=lambda *a, **k: None)
        with mock.patch.dict(sys.modules, {'patoolib': fake_module}):
            loaded = core._require_patoolib()
        self.assertIs(loaded, fake_module)

    def test_require_patoolib_wraps_import_error(self):
        original_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'patoolib':
                raise ImportError('missing patoolib')
            return original_import(name, globals, locals, fromlist, level)

        with mock.patch('builtins.__import__', side_effect=fake_import):
            with self.assertRaises(RuntimeError) as ctx:
                core._require_patoolib()
        self.assertIn('patool が必要', str(ctx.exception))

    def test_iter_with_optional_tqdm_falls_back_when_wrapper_raises(self):
        fake_module = types.SimpleNamespace(tqdm=mock.Mock(side_effect=RuntimeError('boom')))
        items = [1, 2, 3]
        with mock.patch.dict(sys.modules, {'tqdm': fake_module}):
            result = core._iter_with_optional_tqdm(items, desc='x')
        self.assertIs(result, items)


class ArchiveErrorPathRegressionTests(unittest.TestCase):
    def setUp(self):
        self.args = core.ConversionArgs(width=8, height=8, output_format='xtc')

    def test_load_archive_input_document_uses_patool_for_cbr(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            archive_path = tmpdir_path / 'sample.cbr'
            archive_path.write_bytes(b'not-a-real-rar')

            def fake_extract_archive(path, outdir, verbosity=-1):
                Path(outdir).mkdir(parents=True, exist_ok=True)
                img = Image.new('L', (8, 8), 255)
                img.save(Path(outdir) / '001.png')

            fake_patool = types.SimpleNamespace(extract_archive=fake_extract_archive)
            with mock.patch.object(core, '_require_patoolib', return_value=fake_patool):
                doc = core.load_archive_input_document(archive_path, tmpdir_path / 'out')

            self.assertEqual(doc.source_path, archive_path)
            self.assertEqual([p.name for p in doc.image_files], ['001.png'])

    def test_process_archive_reports_extract_stage_on_load_failure(self):
        archive_path = Path('broken.zip')
        with mock.patch.object(core, 'load_archive_input_document', side_effect=RuntimeError('extract failed')):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: アーカイブの展開に失敗しました。', msg)
        self.assertIn('段階: アーカイブ展開', msg)


class EpubErrorPathRegressionTests(unittest.TestCase):
    def setUp(self):
        self.args = core.ConversionArgs(width=160, height=220, font_size=18, ruby_size=10, line_spacing=28, output_format='xtc')
        self.font_path = resolve_test_font_path()

    def _fake_doc(self, docs):
        return core.EpubInputDocument(
            source_path=Path('dummy.epub'),
            book=None,
            docs=docs,
            image_map={},
            image_basename_map={},
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
            css_rules=[],
        )

    def test_process_epub_reports_parse_stage_when_docs_are_missing(self):
        with mock.patch.object(core, 'load_epub_input_document', return_value=self._fake_doc([])):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_epub('dummy.epub', self.font_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: EPUB の本文が見つかりませんでした。', msg)
        self.assertIn('段階: EPUB解析', msg)

    def test_process_epub_wraps_chapter_render_errors(self):
        fake_doc = self._fake_doc([_FakeEpubItem('text/chapter1.xhtml', '<html/>')])
        with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc), \
             mock.patch.object(core, '_render_epub_chapter_pages_from_html', side_effect=ValueError('html render failed')):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_epub('dummy.epub', self.font_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: EPUB の本文描画中に失敗しました。', msg)
        self.assertIn('段階: 章描画: chapter1.xhtml', msg)

    def test_process_epub_wraps_chapter_conversion_errors(self):
        fake_doc = self._fake_doc([_FakeEpubItem('text/chapter1.xhtml', '<html/>')])
        page_entry = core._make_page_entry(Image.new('L', (self.args.width, self.args.height), 255), self.args)
        with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc), \
             mock.patch.object(core, '_render_epub_chapter_pages_from_html', return_value=[page_entry]), \
             mock.patch.object(core, '_append_page_entries_to_spool', side_effect=RuntimeError('blob convert failed')):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_epub('dummy.epub', self.font_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: EPUB の本文描画中に失敗しました。', msg)
        self.assertIn('段階: 章変換: chapter1.xhtml', msg)

    def test_process_epub_wraps_output_write_errors(self):
        fake_doc = self._fake_doc([_FakeEpubItem('text/chapter1.xhtml', '<html/>')])
        with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc), \
             mock.patch.object(core, '_render_epub_chapter_pages_from_html', return_value=[]):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_epub('dummy.epub', self.font_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: EPUB の読み込みまたは解析に失敗しました。', msg)
        self.assertIn('段階: 出力書込', msg)
        self.assertIn('詳細: 変換データがありません。', msg)


if __name__ == '__main__':
    unittest.main()
