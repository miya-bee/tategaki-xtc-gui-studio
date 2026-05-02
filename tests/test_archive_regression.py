import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class ArchiveRegressionTests(unittest.TestCase):
    def _make_zip_archive(self, suffix):
        tmpdir = tempfile.TemporaryDirectory()
        base = Path(tmpdir.name)
        for idx, gray in enumerate((0, 255), start=1):
            img = Image.new('L', (8, 8), gray)
            img.save(base / f'{idx:03}.png')
        archive_path = base / f'sample{suffix}'
        with zipfile.ZipFile(archive_path, 'w') as zf:
            for img_path in sorted(base.glob('*.png')):
                zf.write(img_path, arcname=img_path.name)
        return tmpdir, archive_path

    def test_zip_archive_conversion_does_not_require_patool(self):
        holder, archive_path = self._make_zip_archive('.zip')
        try:
            args = core.ConversionArgs(width=8, height=8, output_format='xtc')
            with mock.patch.object(core, '_require_patoolib', side_effect=AssertionError('patool should not be used for zip')):
                with mock.patch.object(core, 'load_archive_input_document', side_effect=AssertionError('valid zip should be processed directly')):
                    out_path = core.process_archive(archive_path, args)
            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.read_bytes()[:4], b'XTC\x00')
        finally:
            holder.cleanup()

    def test_cbz_archive_conversion_does_not_require_patool(self):
        holder, archive_path = self._make_zip_archive('.cbz')
        try:
            args = core.ConversionArgs(width=8, height=8, output_format='xtc')
            with mock.patch.object(core, '_require_patoolib', side_effect=AssertionError('patool should not be used for cbz')):
                with mock.patch.object(core, 'load_archive_input_document', side_effect=AssertionError('valid cbz should be processed directly')):
                    out_path = core.process_archive(archive_path, args)
            self.assertTrue(out_path.exists())
            self.assertEqual(out_path.read_bytes()[:4], b'XTC\x00')
        finally:
            holder.cleanup()


    def test_zip_archive_conversion_counts_duplicate_member_names_as_separate_pages(self):
        holder = tempfile.TemporaryDirectory()
        base = Path(holder.name)
        archive_path = base / 'dup.zip'
        png1 = base / 'one.png'
        png2 = base / 'two.png'
        Image.new('L', (8, 8), 0).save(png1)
        Image.new('L', (8, 8), 255).save(png2)
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr('dup/page.png', png1.read_bytes())
            zf.writestr('dup/page.png', png2.read_bytes())
        try:
            args = core.ConversionArgs(width=8, height=8, output_format='xtc')
            out_path = core.process_archive(archive_path, args)
            header = out_path.read_bytes()[:48]
            import struct
            mark, version, page_count, *_ = struct.unpack('<4sHHBBBBIQQQQ', header)
            self.assertEqual(mark, b'XTC\x00')
            self.assertEqual(page_count, 2)
        finally:
            holder.cleanup()


    def test_zip_archive_extraction_sanitizes_windows_reserved_member_names(self):
        holder = tempfile.TemporaryDirectory()
        base = Path(holder.name)
        archive_path = base / 'reserved.zip'
        png = base / 'page.png'
        Image.new('L', (8, 8), 128).save(png)
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.writestr('CON.png', png.read_bytes())
            zf.writestr('AUX/COM1.png', png.read_bytes())
        try:
            extract_dir = base / 'extract'
            extracted, traversal_skipped = core._extract_zip_archive_images_to_tempdir(archive_path, extract_dir)
            self.assertEqual(traversal_skipped, 0)
            self.assertEqual(len(extracted), 2)
            rel_parts = {path.relative_to(extract_dir).as_posix() for path in extracted}
            self.assertIn('_CON.png', rel_parts)
            self.assertIn('_AUX/_COM1.png', rel_parts)
        finally:
            holder.cleanup()

if __name__ == '__main__':
    unittest.main()
