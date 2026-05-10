from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from tests import studio_import_helper
from tategakiXTC_gui_core import ConversionArgs
import tategakiXTC_gui_core_xtc as core_xtc


class GuiImageAtomicWriteRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.studio = studio_import_helper.load_studio_module(force_reload=True)

    def test_process_single_image_file_writes_output_atomically(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix='gui_image_atomic_'))
        source = work_dir / 'sample.png'
        source.write_bytes(b'png')
        output_path = work_dir / 'sample.xtc'
        output_path.write_bytes(b'OLD')
        args = ConversionArgs(font_size=26)
        page_image = Image.new('L', (args.width, args.height), 255)
        page_blob = self.studio.core.canvas_image_to_xt_bytes(page_image, args.width, args.height, args)

        with mock.patch.object(self.studio.core, 'process_image_data', return_value=page_blob):
            result = self.studio._process_single_image_file(source, '', args, output_path)

        self.assertEqual(result, output_path)
        self.assertTrue(output_path.read_bytes().startswith(b'XTC\x00'))
        self.assertFalse(any(path.suffix == '.partial' for path in work_dir.iterdir()))

    def test_process_single_image_file_removes_partial_temp_when_replace_fails(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix='gui_image_atomic_fail_'))
        source = work_dir / 'sample.png'
        source.write_bytes(b'png')
        output_path = work_dir / 'sample.xtc'
        output_path.write_bytes(b'OLD')
        args = ConversionArgs(font_size=26)
        page_image = Image.new('L', (args.width, args.height), 255)
        page_blob = self.studio.core.canvas_image_to_xt_bytes(page_image, args.width, args.height, args)

        def failing_replace(src: str | Path, dst: str | Path) -> None:
            raise OSError('replace failed')

        with mock.patch.object(self.studio.core, 'process_image_data', return_value=page_blob), \
             mock.patch.object(core_xtc.os, 'replace', side_effect=failing_replace):
            with self.assertRaisesRegex(OSError, 'replace failed'):
                self.studio._process_single_image_file(source, '', args, output_path)

        self.assertEqual(output_path.read_bytes(), b'OLD')
        self.assertFalse(any(path.suffix == '.partial' for path in work_dir.iterdir()))
