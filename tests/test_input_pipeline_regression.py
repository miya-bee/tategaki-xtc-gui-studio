import sys
import tempfile
import unittest
from unittest import mock
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class InputPipelineRegressionTests(unittest.TestCase):
    def test_load_text_input_document_plain_keeps_text_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = Path(tmpdir) / 'sample.txt'
            text_path.write_text('一行目\n二行目', encoding='utf-8')
            document = core.load_text_input_document(text_path, parser='plain')
        self.assertEqual(document.source_path.name, 'sample.txt')
        self.assertEqual(document.format_label, 'テキスト')
        self.assertEqual(document.encoding, 'utf-8')
        self.assertTrue(any(block.get('kind') == 'paragraph' for block in document.blocks))

    def test_load_text_input_document_markdown_builds_heading_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            text_path = Path(tmpdir) / 'sample.md'
            text_path.write_text('# 見出し\n\n本文', encoding='utf-8')
            document = core.load_text_input_document(text_path, parser='markdown')
        self.assertEqual(document.format_label, 'Markdown')
        self.assertEqual(document.blocks[0].get('kind'), 'heading')
        self.assertEqual(document.blocks[0].get('runs')[0].get('text'), '見出し')

    def test_iter_conversion_targets_recurses_into_subfolders(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            nested = base / 'nested' / 'deeper'
            nested.mkdir(parents=True)
            (base / 'root.txt').write_text('root', encoding='utf-8')
            (nested / 'child.md').write_text('child', encoding='utf-8')
            targets = core.iter_conversion_targets(base)
        self.assertEqual([p.name for p in targets], ['child.md', 'root.txt'])


    def test_iter_conversion_targets_uses_natural_path_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / 'a').mkdir()
            (base / 'b').mkdir()
            (base / 'a' / '10.txt').write_text('ten', encoding='utf-8')
            (base / 'a' / '2.txt').write_text('two', encoding='utf-8')
            (base / 'b' / '1.txt').write_text('one', encoding='utf-8')
            targets = core.iter_conversion_targets(base)
        self.assertEqual(
            [str(p.relative_to(base)).replace('\\', '/') for p in targets],
            ['a/2.txt', 'a/10.txt', 'b/1.txt'],
        )

    def test_get_output_path_for_target_flattens_nested_batch_output_to_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            nested = base / 'nested' / 'deeper'
            nested.mkdir(parents=True)
            src = nested / 'book.epub'
            src.write_text('dummy', encoding='utf-8')
            out_path = core.get_output_path_for_target(src, 'xtc', output_root=base)
        self.assertEqual(out_path, base / 'nested~~deeper~~book.xtc')


    def test_get_output_path_for_target_distinguishes_double_underscore_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            src1 = base / 'sub__dir' / 'book.epub'
            src2 = base / 'sub' / 'dir__book.epub'
            src1.parent.mkdir(parents=True)
            src2.parent.mkdir(parents=True)
            src1.write_text('a', encoding='utf-8')
            src2.write_text('b', encoding='utf-8')
            out1 = core.get_output_path_for_target(src1, 'xtc', output_root=base)
            out2 = core.get_output_path_for_target(src2, 'xtc', output_root=base)
        self.assertNotEqual(out1, out2)
        self.assertEqual(out1.parent, base)
        self.assertEqual(out2.parent, base)

    def test_get_output_path_for_target_keeps_output_root_on_relative_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            other = base / 'output'
            other.mkdir()
            src = base / 'src' / 'book.epub'
            src.parent.mkdir(parents=True)
            src.write_text('dummy', encoding='utf-8')
            out_path = core.get_output_path_for_target(src, 'xtc', output_root=other)
        self.assertEqual(out_path.parent, other)
        self.assertTrue(out_path.name.startswith('_outside_'))

    def test_iter_conversion_targets_skips_generated_output_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / 'book.epub').write_text('epub', encoding='utf-8')
            (base / 'book.xtc').write_bytes(b'XTC\x00')
            (base / 'book.xtch').write_bytes(b'XTH\x00')
            targets = core.iter_conversion_targets(base)
        self.assertEqual([p.name for p in targets], ['book.epub'])

    def test_load_archive_input_document_collects_images_in_natural_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            src_dir = base / 'src'
            src_dir.mkdir()
            for name in ('10.png', '2.png', 'note.txt'):
                if name.endswith('.png'):
                    Image.new('L', (4, 4), 255).save(src_dir / name)
                else:
                    (src_dir / name).write_text('skip', encoding='utf-8')
            archive_path = base / 'sample.zip'
            with zipfile.ZipFile(archive_path, 'w') as zf:
                for item in sorted(src_dir.iterdir()):
                    zf.write(item, arcname=item.name)
            extract_dir = base / 'extract'
            extract_dir.mkdir()
            document = core.load_archive_input_document(archive_path, extract_dir)
        self.assertEqual([p.name for p in document.image_files], ['2.png', '10.png'])

    def test_zip_image_member_listing_is_reused_until_input_cache_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_path = base / 'sample.zip'
            png_path = base / 'safe.png'
            Image.new('L', (4, 4), 255).save(png_path)
            with zipfile.ZipFile(archive_path, 'w') as zf:
                zf.write(png_path, arcname='safe.png')
                zf.writestr('note.txt', 'skip')

            core.clear_input_document_cache()
            with mock.patch.object(core.zipfile, 'ZipFile', wraps=zipfile.ZipFile) as zipfile_cls:
                first = core._list_zip_archive_image_members(archive_path)
                second = core._list_zip_archive_image_members(archive_path)
                self.assertEqual(first, ['safe.png'])
                self.assertEqual(second, ['safe.png'])
                self.assertEqual(zipfile_cls.call_count, 1)

                core.clear_input_document_cache()
                third = core._list_zip_archive_image_members(archive_path)
                self.assertEqual(third, ['safe.png'])
                self.assertEqual(zipfile_cls.call_count, 2)


    def test_load_archive_input_document_skips_traversal_image_members(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_path = base / 'sample.zip'
            png_path = base / 'safe.png'
            Image.new('L', (4, 4), 255).save(png_path)
            with zipfile.ZipFile(archive_path, 'w') as zf:
                zf.write(png_path, arcname='safe.png')
                zf.writestr('../escape.png', png_path.read_bytes())
                zf.writestr('/abs.png', png_path.read_bytes())
                zf.writestr('note.txt', 'skip')
            extract_dir = base / 'extract'
            extract_dir.mkdir()
            document = core.load_archive_input_document(archive_path, extract_dir)
        self.assertEqual([p.name for p in document.image_files], ['safe.png'])
        self.assertEqual(document.traversal_skipped, 2)
        self.assertEqual(document.extracted_member_count, 1)
        self.assertFalse((base / 'escape.png').exists())


    def test_load_archive_input_document_preserves_duplicate_zip_image_members(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_path = base / 'sample.zip'
            png1 = base / 'one.png'
            png2 = base / 'two.png'
            Image.new('L', (4, 4), 0).save(png1)
            Image.new('L', (4, 4), 255).save(png2)
            with zipfile.ZipFile(archive_path, 'w') as zf:
                zf.writestr('dup/page.png', png1.read_bytes())
                zf.writestr('dup/page.png', png2.read_bytes())
            extract_dir = base / 'extract'
            extract_dir.mkdir()
            document = core.load_archive_input_document(archive_path, extract_dir)
        self.assertEqual([str(p.relative_to(extract_dir)).replace('\\', '/') for p in document.image_files], ['dup/page.png', 'dup/page(1).png'])
        self.assertEqual(document.extracted_member_count, 2)



    def test_load_archive_input_document_renames_case_only_duplicate_zip_members(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_path = base / 'sample.zip'
            png1 = base / 'one.png'
            png2 = base / 'two.png'
            Image.new('L', (4, 4), 0).save(png1)
            Image.new('L', (4, 4), 255).save(png2)
            with zipfile.ZipFile(archive_path, 'w') as zf:
                zf.writestr('dup/Page.png', png1.read_bytes())
                zf.writestr('dup/page.png', png2.read_bytes())
            extract_dir = base / 'extract'
            extract_dir.mkdir()
            document = core.load_archive_input_document(archive_path, extract_dir)
        relative_paths = [str(p.relative_to(extract_dir)).replace('\\', '/') for p in document.image_files]
        self.assertEqual(len(relative_paths), 2)
        self.assertEqual(len({item.casefold() for item in relative_paths}), 2)
        self.assertIn('dup/Page.png', relative_paths)
        self.assertTrue(any(item.endswith('page(1).png') for item in relative_paths))

    def test_load_archive_input_document_removes_partial_file_when_zip_extraction_is_cancelled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            archive_path = base / 'sample.zip'
            payload = (b'X' * (1024 * 512)) + b'end'
            with zipfile.ZipFile(archive_path, 'w') as zf:
                zf.writestr('dup/page.png', payload)
            extract_dir = base / 'extract'
            extract_dir.mkdir()

            def fake_copy(src_fp, dst_fp, *, should_cancel=None, chunk_size=1024 * 1024):
                dst_fp.write(src_fp.read(128))
                raise core.ConversionCancelled('cancelled')

            with mock.patch.object(core, '_copy_fileobj_with_cancel', side_effect=fake_copy):
                with self.assertRaises(core.ConversionCancelled):
                    core.load_archive_input_document(archive_path, extract_dir, should_cancel=lambda: False)
        self.assertEqual(list(extract_dir.rglob('*')), [])

if __name__ == '__main__':
    unittest.main()
