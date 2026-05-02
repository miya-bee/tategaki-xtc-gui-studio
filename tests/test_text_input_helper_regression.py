import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class TextInputHelperRegressionTests(unittest.TestCase):
    def setUp(self):
        core.clear_input_document_cache()

    def test_compact_error_text_normalizes_spaces_and_truncates(self):
        value = '  a　b\n' + ('x' * 20)
        compact = core._compact_error_text(value, max_len=10)
        self.assertEqual(compact, 'a b xxxxx…')

    def test_build_conversion_error_report_dependency_and_unicode_and_markdown(self):
        dep = core.build_conversion_error_report('book.epub', RuntimeError('ebooklib が必要です。 pip install ebooklib'))
        self.assertEqual(dep['headline'], '必要なライブラリが不足しているため変換できませんでした。')
        self.assertIn('requirements.txt', dep['display'])

        uni = core.build_conversion_error_report('plain.txt', UnicodeDecodeError('utf-8', b'\xff', 0, 1, 'bad'))
        self.assertEqual(uni['headline'], 'テキストの文字コードを判定できませんでした。')
        self.assertIn('UTF-8 / UTF-8 BOM / CP932', uni['display'])

        md = core.build_conversion_error_report('note.md', ValueError('bad markdown'))
        self.assertEqual(md['headline'], 'Markdown の読み込みまたは整形中に失敗しました。')
        self.assertIn('入力注意', md['display'])

    def test_build_conversion_error_report_file_not_found_and_archive_extract(self):
        missing = core.build_conversion_error_report('missing.txt', FileNotFoundError('gone'))
        self.assertEqual(missing['headline'], '入力ファイルを開けませんでした。')
        self.assertIn('移動・削除', missing['display'])

        archive = core.build_conversion_error_report('bad.cbz', RuntimeError('extract failed'))
        self.assertEqual(archive['headline'], 'アーカイブの展開に失敗しました。')
        self.assertIn('patool', archive['display'])

    def test_try_decode_bytes_and_guess_utf16_without_bom(self):
        self.assertEqual(core._try_decode_bytes('テスト'.encode('utf-8'), 'utf-8'), ('テスト', 'utf-8'))
        self.assertIsNone(core._try_decode_bytes(b'\xff', 'utf-8'))
        self.assertEqual(core._guess_utf16_without_bom('AB'.encode('utf-16-le')), 'utf-16-le')
        self.assertEqual(core._guess_utf16_without_bom('AB'.encode('utf-16-be')), 'utf-16-be')
        self.assertIsNone(core._guess_utf16_without_bom(b'abc'))

    def test_detect_text_with_charset_normalizer_import_error_and_detection(self):
        original_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == 'charset_normalizer':
                raise ImportError('missing')
            return original_import(name, *args, **kwargs)

        with mock.patch('builtins.__import__', side_effect=fake_import):
            self.assertIsNone(core._detect_text_with_charset_normalizer('abc'.encode('utf-8')))

        class FakeBest:
            encoding = 'UTF_8_SIG'

            def __str__(self):
                return '本文'

        class FakeResult:
            def best(self):
                return FakeBest()

        fake_module = mock.Mock(from_bytes=mock.Mock(return_value=FakeResult()))
        with mock.patch.dict(sys.modules, {'charset_normalizer': fake_module}):
            detected = core._detect_text_with_charset_normalizer('本文'.encode('utf-8'))
        self.assertEqual(detected, ('本文', 'utf-8-sig'))

    def test_detect_text_with_charset_normalizer_handles_runtime_error_and_missing_best(self):
        fake_module = mock.Mock(from_bytes=mock.Mock(side_effect=RuntimeError('boom')))
        with mock.patch.dict(sys.modules, {'charset_normalizer': fake_module}):
            self.assertIsNone(core._detect_text_with_charset_normalizer(b'abc'))

        class FakeResult:
            def best(self):
                return None

        fake_module2 = mock.Mock(from_bytes=mock.Mock(return_value=FakeResult()))
        with mock.patch.dict(sys.modules, {'charset_normalizer': fake_module2}):
            self.assertIsNone(core._detect_text_with_charset_normalizer(b'abc'))

    def test_output_name_helpers_cover_fallback_paths(self):
        self.assertEqual(core._encode_output_name_part('a_b~c'), 'a_ub_tc')
        self.assertEqual(core._build_flat_output_stem_from_relative(Path('.')), 'output')

        with mock.patch('pathlib.Path.resolve', side_effect=RuntimeError('no resolve')):
            fallback = core._build_fallback_output_stem('dir/sample.epub')
        self.assertTrue(fallback.startswith('_outside_sample_'))

    def test_process_text_file_emits_warnings_and_progress_before_render(self):
        args = core.ConversionArgs(width=8, height=8, output_format='xtc')
        document = core.TextInputDocument(
            source_path=Path('sample.txt'),
            text='x',
            encoding='utf-8',
            blocks=[{'kind': 'paragraph', 'runs': [{'text': '本文'}]}],
            format_label='テキスト',
            parser_key='plain',
            support_summary='簡易対応',
            warnings=['見出し記法があります'],
        )
        progress_calls = []
        with mock.patch.object(core, 'load_text_input_document', return_value=document), \
             mock.patch.object(core, '_render_text_blocks_to_xtc', return_value=Path('out.xtc')) as render_mock, \
             mock.patch.object(core.LOGGER, 'info') as info_mock, \
             mock.patch.object(core.LOGGER, 'warning') as warning_mock:
            out_path = core.process_text_file('sample.txt', 'font.ttf', args, progress_cb=lambda c, t, m: progress_calls.append((c, t, m)))
        self.assertEqual(out_path, Path('out.xtc'))
        info_mock.assert_called_once()
        warning_mock.assert_called_once()
        self.assertEqual(progress_calls, [(0, 1, 'テキストファイルを読み込みました。')])
        render_mock.assert_called_once()

    def test_process_markdown_file_emits_warnings_and_progress_before_render(self):
        args = core.ConversionArgs(width=8, height=8, output_format='xtc')
        document = core.TextInputDocument(
            source_path=Path('sample.md'),
            text='x',
            encoding='utf-8',
            blocks=[{'kind': 'heading', 'runs': [{'text': '見出し'}]}],
            format_label='Markdown',
            parser_key='markdown',
            support_summary='簡易対応',
            warnings=['生 HTML が含まれています'],
        )
        progress_calls = []
        with mock.patch.object(core, 'load_text_input_document', return_value=document), \
             mock.patch.object(core, '_render_text_blocks_to_xtc', return_value=Path('out.xtc')) as render_mock, \
             mock.patch.object(core.LOGGER, 'info') as info_mock, \
             mock.patch.object(core.LOGGER, 'warning') as warning_mock:
            out_path = core.process_markdown_file('sample.md', 'font.ttf', args, progress_cb=lambda c, t, m: progress_calls.append((c, t, m)))
        self.assertEqual(out_path, Path('out.xtc'))
        info_mock.assert_called_once()
        warning_mock.assert_called_once()
        self.assertEqual(progress_calls, [(0, 1, 'Markdownファイルを読み込みました。')])
        render_mock.assert_called_once()



    def test_process_text_and_markdown_file_skip_log_when_summary_and_warning_are_empty(self):
        args = core.ConversionArgs(width=8, height=8, output_format='xtc')
        plain_doc = core.TextInputDocument(
            source_path=Path('sample.txt'),
            text='x',
            encoding='utf-8',
            blocks=[{'kind': 'paragraph', 'runs': [{'text': '本文'}]}],
            format_label='テキスト',
            parser_key='plain',
            support_summary='',
            warnings=[],
        )
        md_doc = core.TextInputDocument(
            source_path=Path('sample.md'),
            text='x',
            encoding='utf-8',
            blocks=[{'kind': 'heading', 'runs': [{'text': '見出し'}]}],
            format_label='Markdown',
            parser_key='markdown',
            support_summary='',
            warnings=[],
        )
        for func, source, doc in (
            (core.process_text_file, 'sample.txt', plain_doc),
            (core.process_markdown_file, 'sample.md', md_doc),
        ):
            with mock.patch.object(core, 'load_text_input_document', return_value=doc), \
                 mock.patch.object(core, '_render_text_blocks_to_xtc', return_value=Path('out.xtc')), \
                 mock.patch.object(core.LOGGER, 'info') as info_mock, \
                 mock.patch.object(core.LOGGER, 'warning') as warning_mock:
                out = func(source, 'font.ttf', args)
            self.assertEqual(out, Path('out.xtc'))
            info_mock.assert_not_called()
            warning_mock.assert_not_called()

    def test_process_text_file_and_markdown_file_honor_cancellation_before_load(self):
        args = core.ConversionArgs(width=8, height=8, output_format='xtc')
        for func in (core.process_text_file, core.process_markdown_file):
            with self.assertRaises(core.ConversionCancelled):
                func('sample.txt', 'font.ttf', args, should_cancel=lambda: True)

    def test_read_text_file_with_fallback_prefers_utf8_before_charset_normalizer(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'sample.txt'
            path.write_text('本文', encoding='utf-8')
            with mock.patch.object(core, '_detect_text_with_charset_normalizer', side_effect=AssertionError('charset_normalizer should not be used')):
                text_value, encoding = core.read_text_file_with_fallback(path)
        self.assertEqual(text_value, '本文')
        self.assertEqual(encoding, 'utf-8')

    def test_load_text_input_document_reuses_cache_until_source_changes(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'sample.txt'
            path.write_text('一行目\n二行目', encoding='utf-8')
            with mock.patch.object(core, 'read_text_file_with_fallback', wraps=core.read_text_file_with_fallback) as read_mock:
                doc1 = core.load_text_input_document(path, parser='plain')
                doc2 = core.load_text_input_document(path, parser='plain')
                self.assertIs(doc1, doc2)
                self.assertEqual(read_mock.call_count, 1)
                path.write_text('更新後', encoding='utf-8')
                doc3 = core.load_text_input_document(path, parser='plain')
        self.assertEqual(read_mock.call_count, 2)
        self.assertIsNot(doc1, doc3)
        self.assertEqual(doc3.text, '更新後')

    def test_load_text_input_document_keeps_plain_and_markdown_cache_entries_separate(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'sample.md'
            path.write_text('# 見出し\n\n本文', encoding='utf-8')
            with mock.patch.object(core, 'read_text_file_with_fallback', wraps=core.read_text_file_with_fallback) as read_mock:
                plain_doc = core.load_text_input_document(path, parser='plain')
                markdown_doc = core.load_text_input_document(path, parser='markdown')
                markdown_doc_cached = core.load_text_input_document(path, parser='markdown')
        self.assertEqual(read_mock.call_count, 2)
        self.assertEqual(plain_doc.format_label, 'テキスト')
        self.assertEqual(markdown_doc.format_label, 'Markdown')
        self.assertIs(markdown_doc, markdown_doc_cached)


if __name__ == '__main__':
    unittest.main()
