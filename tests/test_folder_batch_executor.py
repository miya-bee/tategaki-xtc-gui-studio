from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tategakiXTC_folder_batch_executor import execute_folder_batch_plan
from tategakiXTC_folder_batch_plan import build_folder_batch_plan


class FolderBatchExecutorTests(unittest.TestCase):
    def test_executor_converts_planned_items_and_creates_output_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            source = root / 'author' / 'novel.txt'
            source.parent.mkdir(parents=True)
            source.write_text('本文', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, include_subfolders=True, preserve_structure=True)

            def converter(src: Path, dst: Path, item: object) -> None:
                dst.write_text(src.read_text(encoding='utf-8') + '\nconverted', encoding='utf-8')

            result = execute_folder_batch_plan(plan, converter)
            self.assertEqual(result.success_count, 1)
            self.assertEqual(result.failed_count, 0)
            self.assertTrue((out / 'author' / 'novel.xtc').exists())
            self.assertIn('converted', (out / 'author' / 'novel.xtc').read_text(encoding='utf-8'))


    def test_executor_logs_success_once_per_converted_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            (root / 'a.txt').write_text('A', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            logs: list[str] = []

            def converter(src: Path, dst: Path, item: object) -> None:
                dst.write_text('ok', encoding='utf-8')

            result = execute_folder_batch_plan(plan, converter, log_cb=logs.append)

            self.assertEqual(result.success_count, 1)
            ok_logs = [line for line in logs if line.startswith('[OK] a.txt ->')]
            self.assertEqual(len(ok_logs), 1)

    def test_executor_logs_skips_from_existing_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            (out / 'novel.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')
            logs: list[str] = []
            result = execute_folder_batch_plan(
                plan,
                lambda src, dst, item: self.fail('skipped item must not be converted'),
                log_cb=logs.append,
            )
            self.assertEqual(result.success_count, 0)
            self.assertEqual(result.skipped_count, 1)
            self.assertTrue(any('[SKIP]' in line for line in logs))

    def test_executor_continues_after_one_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            (root / 'a.txt').write_text('A', encoding='utf-8')
            (root / 'b.txt').write_text('B', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)

            def converter(src: Path, dst: Path, item: object) -> None:
                if src.name == 'a.txt':
                    raise RuntimeError('boom')
                dst.write_text('ok', encoding='utf-8')

            logs: list[str] = []
            result = execute_folder_batch_plan(plan, converter, log_cb=logs.append)
            self.assertEqual(result.success_count, 1)
            self.assertEqual(result.failed_count, 1)
            self.assertTrue((out / 'b.xtc').exists())
            self.assertTrue(any('[ERROR]' in line and 'boom' in line for line in logs))


    def test_progress_callback_receives_planned_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            (root / 'a.txt').write_text('A', encoding='utf-8')
            (root / 'b.txt').write_text('B', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            progress: list[tuple[int, int, str]] = []

            def converter(src: Path, dst: Path, item: object) -> None:
                dst.write_text('ok', encoding='utf-8')

            result = execute_folder_batch_plan(
                plan,
                converter,
                progress_cb=lambda index, total, item: progress.append((index, total, item.source_path.name)),
            )

            self.assertEqual(result.success_count, 2)
            self.assertEqual(progress, [(1, 2, 'a.txt'), (2, 2, 'b.txt')])

    def test_progress_callback_failure_is_logged_and_does_not_abort_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            (root / 'a.txt').write_text('A', encoding='utf-8')
            (root / 'b.txt').write_text('B', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            logs: list[str] = []

            def converter(src: Path, dst: Path, item: object) -> None:
                dst.write_text('ok', encoding='utf-8')

            def progress_cb(index: int, total: int, item: object) -> None:
                raise RuntimeError('progress target disappeared')

            result = execute_folder_batch_plan(
                plan,
                converter,
                log_cb=logs.append,
                progress_cb=progress_cb,
            )

            self.assertEqual(result.success_count, 2)
            self.assertEqual(result.failed_count, 0)
            self.assertTrue((out / 'a.xtc').exists())
            self.assertTrue((out / 'b.xtc').exists())
            self.assertTrue(any('[WARN]' in line and 'progress target disappeared' in line for line in logs))



    def test_summary_lines_include_failed_file_names_and_messages(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            (root / 'bad.txt').write_text('bad', encoding='utf-8')
            (root / 'good.txt').write_text('good', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)

            def converter(src: Path, dst: Path, item: object) -> None:
                if src.name == 'bad.txt':
                    raise RuntimeError('broken text')
                dst.write_text('ok', encoding='utf-8')

            result = execute_folder_batch_plan(plan, converter)
            lines = result.summary_lines()

            self.assertIn('失敗内訳:', lines)
            self.assertIn('表示: 1 件中 1 件（詳細はログ欄の [ERROR] を確認）', lines)
            self.assertIn('- bad.txt: broken text', lines)
            self.assertIn('失敗したファイルはログ欄の [ERROR] 行を確認してください。', lines)

    def test_failure_summary_lines_show_visible_limit_and_remaining_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            for index in range(7):
                (root / f'bad{index}.txt').write_text('bad', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)

            def converter(src: Path, dst: Path, item: object) -> None:
                raise RuntimeError('x' * 160)

            result = execute_folder_batch_plan(plan, converter)
            lines = result.failure_summary_lines(max_items=3, max_message_chars=30)

            self.assertEqual(lines[0], '失敗内訳:')
            self.assertEqual(lines[1], '表示: 7 件中 3 件（詳細はログ欄の [ERROR] を確認）')
            self.assertTrue(any(line.endswith('…') for line in lines if line.startswith('- bad')))
            self.assertIn('- 他 4 件（ログ欄に失敗一覧を出力しました）', lines)

    def test_executor_logs_failure_summary_after_done_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            (root / 'bad.txt').write_text('bad', encoding='utf-8')
            (root / 'good.txt').write_text('good', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            logs: list[str] = []

            def converter(src: Path, dst: Path, item: object) -> None:
                if src.name == 'bad.txt':
                    raise RuntimeError('broken text')
                dst.write_text('ok', encoding='utf-8')

            result = execute_folder_batch_plan(plan, converter, log_cb=logs.append)

            self.assertEqual(result.failed_count, 1)
            done_index = next(index for index, line in enumerate(logs) if line.startswith('[DONE]'))
            summary_index = next(index for index, line in enumerate(logs) if line.startswith('[ERROR-SUMMARY] 失敗ファイル一覧'))
            self.assertGreater(summary_index, done_index)
            self.assertTrue(any(line == '[ERROR-SUMMARY] - bad.txt — broken text' for line in logs))

    def test_summary_lines_include_output_root_and_skip_breakdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'novel.txt').write_text('本文', encoding='utf-8')
            (out / 'novel.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')

            result = execute_folder_batch_plan(
                plan,
                lambda src, dst, item: self.fail('skipped item must not be converted'),
            )
            lines = result.summary_lines()

            self.assertIn('成功: 0 件', lines)
            self.assertIn('スキップ: 1 件', lines)
            self.assertIn('失敗: 0 件', lines)
            self.assertIn('処理済み: 1 / 1 件', lines)
            self.assertIn(f'出力先: {out}', lines)
            self.assertIn('スキップ内訳: 既存ファイル 1 件', lines)

    def test_summary_lines_include_rename_and_overwrite_counts_only_for_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'rename.txt').write_text('A', encoding='utf-8')
            (root / 'overwrite.txt').write_text('B', encoding='utf-8')
            (out / 'rename.xtc').write_text('old', encoding='utf-8')
            (out / 'overwrite.xtc').write_text('old', encoding='utf-8')
            rename_plan = build_folder_batch_plan(root, out, existing_policy='rename')
            overwrite_plan = build_folder_batch_plan(root, out, existing_policy='overwrite')

            def converter(src: Path, dst: Path, item: object) -> None:
                dst.write_text('ok', encoding='utf-8')

            renamed = execute_folder_batch_plan(rename_plan, converter)
            overwritten = execute_folder_batch_plan(overwrite_plan, converter)

            self.assertIn('別名で保存: 2 件', renamed.summary_lines())
            self.assertIn('上書き保存: 2 件', overwritten.summary_lines())

    def test_executor_stops_before_next_item_when_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            (root / 'a.txt').write_text('A', encoding='utf-8')
            (root / 'b.txt').write_text('B', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            calls = {'cancel_checks': 0}

            def should_cancel() -> bool:
                calls['cancel_checks'] += 1
                return calls['cancel_checks'] >= 2

            def converter(src: Path, dst: Path, item: object) -> None:
                dst.write_text('ok', encoding='utf-8')

            logs: list[str] = []
            result = execute_folder_batch_plan(plan, converter, log_cb=logs.append, should_cancel=should_cancel)
            self.assertTrue(result.stopped)
            self.assertEqual(result.success_count, 1)
            self.assertFalse((out / 'b.xtc').exists())
            self.assertIn('未処理: 1 件', result.summary_lines())
            self.assertIn('停止要求により、現在のファイル完了後に一括変換を停止しました。', result.summary_lines())
            self.assertTrue(any(line.startswith('[STOP] 成功 1 件') for line in logs))
            self.assertTrue(any('未処理 1 件' in line for line in logs))

    def test_stopped_pending_count_ignores_preplanned_skips(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'input'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'a.txt').write_text('A', encoding='utf-8')
            (root / 'b.txt').write_text('B', encoding='utf-8')
            (root / '0_skip.txt').write_text('skip', encoding='utf-8')
            (out / '0_skip.xtc').write_text('existing', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')
            calls = {'cancel_checks': 0}

            def should_cancel() -> bool:
                calls['cancel_checks'] += 1
                return calls['cancel_checks'] >= 2

            def converter(src: Path, dst: Path, item: object) -> None:
                dst.write_text('ok', encoding='utf-8')

            result = execute_folder_batch_plan(plan, converter, should_cancel=should_cancel)

            self.assertTrue(result.stopped)
            self.assertEqual(result.skipped_count, 1)
            self.assertEqual(result.success_count, 1)
            self.assertEqual(result.stopped_pending_count, 1)
            lines = result.summary_lines()
            self.assertIn('未処理: 1 件', lines)
            self.assertIn('変換前に判定済みのスキップ項目は集計に含めています。', lines)


if __name__ == '__main__':
    unittest.main()
