import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class AozoraInlineEdgeRegressionTests(unittest.TestCase):
    def test_explicit_ruby_falls_back_to_literal_when_base_or_ruby_is_invalid(self):
        runs = core._aozora_inline_to_runs('前｜青空《》後')
        self.assertEqual(''.join(run['text'] for run in runs), '前｜青空《》後')
        self.assertTrue(all(not run.get('ruby') for run in runs))

        runs = core._aozora_inline_to_runs('前｜《るび》後')
        self.assertEqual(''.join(run['text'] for run in runs), '前｜《るび》後')
        self.assertTrue(all(not run.get('ruby') for run in runs))

    def test_explicit_ruby_with_missing_closer_is_left_literal(self):
        runs = core._aozora_inline_to_runs('前｜青空《あおぞら後')
        self.assertEqual(''.join(run['text'] for run in runs), '前｜青空《あおぞら後')
        self.assertTrue(all(not run.get('ruby') for run in runs))

    def test_implicit_ruby_without_match_or_empty_ruby_text_stays_literal(self):
        runs = core._aozora_inline_to_runs('abc《るび》')
        self.assertEqual(''.join(run['text'] for run in runs), 'abc《るび》')
        self.assertTrue(all(not run.get('ruby') for run in runs))

        runs = core._aozora_inline_to_runs('東京《》へ')
        self.assertEqual(''.join(run['text'] for run in runs), '東京《》へ')
        self.assertTrue(all(not run.get('ruby') for run in runs))

    def test_inline_note_with_missing_closer_is_preserved_as_literal(self):
        runs = core._aozora_inline_to_runs('本文［＃「本文」に丸傍点')
        self.assertEqual(''.join(run['text'] for run in runs), '本文［＃「本文」に丸傍点')

    def test_inline_runs_respect_bold_and_italic_flags(self):
        runs = core._aozora_inline_to_runs('｜青空《あおぞら》文庫', bold=True, italic=True)
        self.assertEqual([run['text'] for run in runs], ['青空', '文庫'])
        self.assertTrue(all(run['bold'] for run in runs))
        self.assertTrue(all(run['italic'] for run in runs))
        self.assertEqual(runs[0]['ruby'], 'あおぞら')


class ArchiveEdgeRegressionTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)
        self.args = core.ConversionArgs(width=8, height=8, output_format='xtc')

    def tearDown(self):
        self._tmpdir.cleanup()

    def _make_png_bytes(self, value: int = 128) -> bytes:
        buf = io.BytesIO()
        Image.new('L', (8, 8), value).save(buf, format='PNG')
        return buf.getvalue()

    def _make_zip_with(self, entries: dict[str, bytes]) -> Path:
        archive_path = self.tmpdir / 'edge.zip'
        with zipfile.ZipFile(archive_path, 'w') as zf:
            for name, data in entries.items():
                zf.writestr(name, data)
        return archive_path

    def test_archive_exception_path_reports_representative_error(self):
        archive_path = self._make_zip_with({'001.png': self._make_png_bytes()})
        with patch.object(core, 'process_image_data', side_effect=OSError('decode boom')):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: アーカイブ内画像の変換に失敗しました。', msg)
        self.assertIn('変換失敗: 1 件', msg)
        self.assertIn('代表エラー: decode boom', msg)

    def test_archive_reports_both_conversion_failure_and_traversal_skip(self):
        archive_path = self.tmpdir / 'mixed.zip'
        archive_path.write_bytes(b'dummy')

        def fake_load(_archive_path, tmpdir_path):
            inside = Path(tmpdir_path) / 'inside.png'
            inside.write_bytes(self._make_png_bytes())
            outside = self.tmpdir / 'outside.png'
            outside.write_bytes(self._make_png_bytes())
            return core.ArchiveInputDocument(
                source_path=archive_path,
                image_files=[outside, inside],
            )

        with patch.object(core, 'load_archive_input_document', side_effect=fake_load):
            with patch.object(core, 'process_image_data', side_effect=RuntimeError('bad page')):
                with self.assertRaises(RuntimeError) as ctx:
                    core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: アーカイブ内画像の変換に失敗しました。', msg)
        self.assertIn('変換失敗: 1 件', msg)
        self.assertIn('代表エラー: bad page', msg)
        self.assertIn('安全のためスキップしたパス: 1 件', msg)

    def test_collect_archive_image_files_sorts_naturally_in_nested_dirs(self):
        base = self.tmpdir / 'images'
        (base / 'sub').mkdir(parents=True)
        (base / '10.png').write_bytes(b'x')
        (base / '2.png').write_bytes(b'x')
        (base / 'sub' / '1.jpg').write_bytes(b'x')
        (base / 'sub' / '20.jpg').write_bytes(b'x')
        files = core._collect_archive_image_files(base)
        self.assertEqual([p.relative_to(base).as_posix() for p in files], ['2.png', '10.png', 'sub/1.jpg', 'sub/20.jpg'])


class ProgressAndDependencyEdgeTests(unittest.TestCase):
    def test_emit_progress_coerces_invalid_values_and_ignores_callback_errors(self):
        calls = []
        core._emit_progress(lambda c, t, m: calls.append((c, t, m)), current='9', total='x', message=None)
        self.assertEqual(calls, [(1, 1, '')])

        # callback failure should be swallowed
        core._emit_progress(lambda *_: (_ for _ in ()).throw(RuntimeError('boom')), current='y', total=0, message='msg')

    def test_missing_dependencies_deduplicates_required_keys(self):
        def fake_available(module_name):
            return module_name == 'ebooklib'

        with patch.object(core, '_is_module_available', side_effect=fake_available):
            missing = core.get_missing_dependencies_for_suffixes(['.epub', '.rar', '.cbr', '.epub'])
        self.assertEqual([item['key'] for item in missing], ['beautifulsoup4', 'patool'])


if __name__ == '__main__':
    unittest.main()
