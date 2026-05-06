from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tategakiXTC_folder_batch_plan import (
    FOLDER_BATCH_STATUS_CONVERT,
    FOLDER_BATCH_STATUS_SKIP_DUPLICATE,
    FOLDER_BATCH_STATUS_SKIP_EXISTING,
    build_folder_batch_plan,
    describe_folder_batch_no_work,
    describe_folder_batch_partial_skip_notice,
    discover_folder_batch_targets,
)


class FolderBatchPlanTests(unittest.TestCase):
    def test_discover_direct_only_excludes_nested_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            nested = root / 'author'
            nested.mkdir(parents=True)
            (root / 'top.txt').write_text('top', encoding='utf-8')
            (nested / 'nested.txt').write_text('nested', encoding='utf-8')
            targets = discover_folder_batch_targets(root, include_subfolders=False)
        self.assertEqual([path.name for path in targets], ['top.txt'])

    def test_preserve_structure_maps_relative_paths_to_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'books'
            out = Path(tmpdir) / 'out'
            source = root / 'author_a' / 'novel1.txt'
            source.parent.mkdir(parents=True)
            source.write_text('本文', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, include_subfolders=True, preserve_structure=True)
            self.assertEqual(plan.total_count, 1)
            item = plan.items[0]
            self.assertEqual(item.status, FOLDER_BATCH_STATUS_CONVERT)
            self.assertEqual(item.output_path, out / 'author_a' / 'novel1.xtc')

    def test_supported_suffixes_include_epub_and_common_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            root.mkdir()
            for name in ['book.epub', 'cover.png', 'photo.jpg', 'scan.jpeg', 'panel.webp']:
                (root / name).write_bytes(b'x')
            plan = build_folder_batch_plan(root, Path(tmpdir) / 'out')
        self.assertEqual(plan.convert_count, 5)
        self.assertEqual({item.source_path.suffix.lower() for item in plan.items}, {'.epub', '.png', '.jpg', '.jpeg', '.webp'})

    def test_existing_file_skip_policy_skips_without_output_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            (out / 'novel.xtc').write_bytes(b'old')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')
            item = plan.items[0]
            self.assertEqual(item.status, FOLDER_BATCH_STATUS_SKIP_EXISTING)
            self.assertIsNone(item.output_path)
            self.assertEqual(plan.convert_count, 0)
            self.assertEqual(plan.existing_skip_count, 1)

    def test_describe_no_work_guides_existing_skip_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            (out / 'novel.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')
        message = describe_folder_batch_no_work(plan)
        self.assertIn('対象ファイルはありますが、すべて既存ファイル扱いによりスキップされます。', message)
        self.assertNotIn('既存ファイルによるスキップ: 1 件', message)
        self.assertIn('「上書き」または「別名で保存」', message)


    def test_describe_no_work_guides_combined_existing_and_duplicate_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            (root / 'a').mkdir(parents=True)
            (root / 'b').mkdir(parents=True)
            out.mkdir()
            (root / 'a' / 'same.txt').write_text('A', encoding='utf-8')
            (root / 'b' / 'same.txt').write_text('B', encoding='utf-8')
            (out / 'same.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(
                root,
                out,
                include_subfolders=True,
                preserve_structure=False,
                existing_policy='skip',
            )

        message = describe_folder_batch_no_work(plan)
        self.assertEqual(plan.convert_count, 0)
        self.assertEqual(plan.existing_skip_count, 1)
        self.assertEqual(plan.duplicate_skip_count, 1)
        self.assertIn('既存ファイルまたは同名衝突', message)
        self.assertIn('すべてスキップ', message)

    def test_describe_no_work_guides_empty_target_condition(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            root.mkdir()
            plan = build_folder_batch_plan(root, Path(tmpdir) / 'out')
        message = describe_folder_batch_no_work(plan)
        self.assertIn('変換対象ファイルが見つかりません。', message)
        self.assertIn('対象ファイル形式', message)


    def test_describe_partial_skip_notice_guides_mixed_existing_skip_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'done.txt').write_text('本文', encoding='utf-8')
            (root / 'new.txt').write_text('本文', encoding='utf-8')
            (out / 'done.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')
        message = describe_folder_batch_partial_skip_notice(plan)
        self.assertEqual(plan.convert_count, 1)
        self.assertEqual(plan.existing_skip_count, 1)
        self.assertIn('一部のファイルは既存ファイルがあるためスキップされます。', message)
        self.assertIn('変換予定のファイルのみ処理します。', message)

    def test_existing_file_rename_policy_uses_numbered_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            (out / 'novel.xtc').write_bytes(b'old')
            plan = build_folder_batch_plan(root, out, existing_policy='rename')
            item = plan.items[0]
            self.assertEqual(item.status, FOLDER_BATCH_STATUS_CONVERT)
            self.assertEqual(item.output_path, out / 'novel_2.xtc')
            self.assertTrue(item.renamed)

    def test_existing_file_overwrite_policy_marks_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            (out / 'novel.xtc').write_bytes(b'old')
            plan = build_folder_batch_plan(root, out, existing_policy='overwrite')
            item = plan.items[0]
            self.assertEqual(item.output_path, out / 'novel.xtc')
            self.assertTrue(item.overwritten)
            self.assertEqual(plan.overwritten_count, 1)

    def test_flattened_duplicate_with_skip_policy_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            (root / 'a').mkdir(parents=True)
            (root / 'b').mkdir(parents=True)
            (root / 'a' / '01.txt').write_text('A', encoding='utf-8')
            (root / 'b' / '01.txt').write_text('B', encoding='utf-8')
            plan = build_folder_batch_plan(
                root,
                out,
                include_subfolders=True,
                preserve_structure=False,
                existing_policy='skip',
            )
            statuses = [item.status for item in plan.items]
            self.assertIn(FOLDER_BATCH_STATUS_CONVERT, statuses)
            self.assertIn(FOLDER_BATCH_STATUS_SKIP_DUPLICATE, statuses)
            self.assertEqual(plan.convert_count, 1)
            self.assertEqual(plan.duplicate_skip_count, 1)

    def test_flattened_duplicate_with_overwrite_policy_is_renamed_to_avoid_batch_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            (root / 'a').mkdir(parents=True)
            (root / 'b').mkdir(parents=True)
            (root / 'a' / '01.txt').write_text('A', encoding='utf-8')
            (root / 'b' / '01.txt').write_text('B', encoding='utf-8')
            plan = build_folder_batch_plan(
                root,
                out,
                include_subfolders=True,
                preserve_structure=False,
                existing_policy='overwrite',
            )
            outputs = [item.output_path for item in plan.items]
            self.assertEqual(outputs, [out / '01.xtc', out / '01_2.xtc'])
            self.assertEqual(plan.convert_count, 2)
            self.assertEqual(plan.renamed_count, 1)


class FolderBatchPlanBugSweepTests(unittest.TestCase):
    def test_empty_input_root_is_rejected_instead_of_scanning_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(ValueError, '入力元フォルダ'):
                build_folder_batch_plan('', Path(tmpdir) / 'out')

    def test_empty_output_root_is_rejected_instead_of_using_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            root.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '出力先フォルダ'):
                build_folder_batch_plan(root, '')

    def test_uppercase_supported_suffixes_are_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            root.mkdir()
            for name in ['NOVEL.TXT', 'BOOK.EPUB', 'SCAN.JPG']:
                (root / name).write_bytes(b'x')
            plan = build_folder_batch_plan(root, Path(tmpdir) / 'out')
        self.assertEqual(plan.convert_count, 3)
        self.assertEqual([item.output_path.name for item in plan.items], ['BOOK.xtc', 'NOVEL.xtc', 'SCAN.xtc'])

    def test_japanese_relative_paths_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / '入力'
            out = Path(tmpdir) / '出力'
            source = root / '芥川龍之介' / '羅生門.txt'
            source.parent.mkdir(parents=True)
            source.write_text('本文', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, include_subfolders=True, preserve_structure=True)
        self.assertEqual(plan.items[0].relative_source_path, Path('芥川龍之介') / '羅生門.txt')
        self.assertEqual(plan.items[0].output_path, out / '芥川龍之介' / '羅生門.xtc')

    def test_japanese_rename_policy_alias_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            (out / 'novel.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='別名保存')
        self.assertEqual(plan.existing_policy, 'rename')
        self.assertEqual(plan.items[0].output_path, out / 'novel_2.xtc')

if __name__ == '__main__':
    unittest.main()
