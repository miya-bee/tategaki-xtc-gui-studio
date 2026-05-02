from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests import studio_import_helper
from tategakiXTC_gui_core import ConversionArgs


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

        with mock.patch.object(self.studio.core, 'process_image_data', return_value=b'NEW-BLOB'):
            result = self.studio._process_single_image_file(source, '', ConversionArgs(font_size=26), output_path)

        self.assertEqual(result, output_path)
        self.assertEqual(output_path.read_bytes(), b'NEW-BLOB')
        self.assertFalse(any(path.suffix == '.partial' for path in work_dir.iterdir()))

    def test_process_single_image_file_removes_partial_temp_when_replace_fails(self) -> None:
        work_dir = Path(tempfile.mkdtemp(prefix='gui_image_atomic_fail_'))
        source = work_dir / 'sample.png'
        source.write_bytes(b'png')
        output_path = work_dir / 'sample.xtc'
        output_path.write_bytes(b'OLD')

        def failing_replace(src: str | Path, dst: str | Path) -> None:
            raise OSError('replace failed')

        with mock.patch.object(self.studio.core, 'process_image_data', return_value=b'NEW-BLOB'), \
             mock.patch.object(self.studio.os, 'replace', side_effect=failing_replace):
            with self.assertRaisesRegex(OSError, 'replace failed'):
                self.studio._process_single_image_file(source, '', ConversionArgs(font_size=26), output_path)

        self.assertEqual(output_path.read_bytes(), b'OLD')
        self.assertFalse(any(path.suffix == '.partial' for path in work_dir.iterdir()))
