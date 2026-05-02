import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class ConversionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.args = core.ConversionArgs(width=8, height=8, output_format='xtc')

    def test_build_conversion_error_report_for_epub_load(self):
        report = core.build_conversion_error_report('broken.epub', ValueError('bad spine entry'), stage='EPUB読込')
        self.assertEqual(report['headline'], 'EPUB の読み込みまたは解析に失敗しました。')
        self.assertIn('対象: broken.epub', report['display'])
        self.assertIn('段階: EPUB読込', report['display'])
        self.assertIn('確認:', report['display'])

    def test_process_epub_wraps_load_failure(self):
        with mock.patch.object(core, 'load_epub_input_document', side_effect=ValueError('bad spine entry')):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_epub('broken.epub', 'dummy.ttf', self.args)
        msg = str(ctx.exception)
        self.assertIn('対象: broken.epub', msg)
        self.assertIn('内容: EPUB の読み込みまたは解析に失敗しました。', msg)
        self.assertIn('段階: EPUB読込', msg)
        self.assertIn('詳細: bad spine entry', msg)


    def test_generate_preview_base64_rejects_invalid_image_data_uri(self):
        with self.assertRaises(RuntimeError) as ctx:
            core.generate_preview_base64({
                'mode': 'image',
                'width': '16',
                'height': '16',
                'file_b64': 'not-a-data-uri',
            })
        self.assertIn('画像プレビュー用データURIが不正です', str(ctx.exception))

    def test_generate_preview_base64_accepts_bool_like_flags(self):
        preview_true = core.generate_preview_base64({
            'mode': 'image',
            'width': 16,
            'height': 16,
            'dither': True,
            'night_mode': '1',
            'output_format': 'xtc',
        })
        preview_false = core.generate_preview_base64({
            'mode': 'image',
            'width': 16,
            'height': 16,
            'dither': 0,
            'night_mode': False,
            'output_format': 'xtc',
        })
        self.assertIsInstance(preview_true, str)
        self.assertTrue(preview_true)
        self.assertIsInstance(preview_false, str)
        self.assertTrue(preview_false)
        self.assertNotEqual(preview_true, preview_false)

    def test_archive_suffixes_do_not_include_epub(self):
        self.assertNotIn('.epub', core.ARCHIVE_INPUT_SUFFIXES)
        self.assertIn('.epub', core.SUPPORTED_INPUT_SUFFIXES)

    def test_archive_without_images_reports_supported_formats(self):
        with tempfile.TemporaryDirectory() as td:
            archive_path = Path(td) / 'no_images.zip'
            with zipfile.ZipFile(archive_path, 'w') as zf:
                zf.writestr('readme.txt', 'hello')
            with self.assertRaises(RuntimeError) as ctx:
                core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('対象: no_images.zip', msg)
        self.assertIn('内容: 変換できる画像が見つかりませんでした。', msg)
        self.assertIn('.jpg, .jpeg, .png, .webp', msg)


if __name__ == '__main__':
    unittest.main()
