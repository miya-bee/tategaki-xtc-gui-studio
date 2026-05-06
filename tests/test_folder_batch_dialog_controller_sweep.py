from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from tategakiXTC_folder_batch_controller import (
    describe_folder_batch_no_work,
    describe_folder_batch_partial_skip_notice,
    folder_batch_plan_can_execute,
    open_folder_batch_dialog_and_execute,
)
from tategakiXTC_folder_batch_plan import FolderBatchPlan, build_folder_batch_plan
from tategakiXTC_folder_batch_safety import (
    analyze_folder_batch_roots,
    format_folder_batch_safety_warnings,
    summarize_folder_batch_root_safety,
)


@dataclass(frozen=True)
class FakeDialogResult:
    input_root: Path
    output_root: Path
    include_subfolders: bool
    preserve_structure: bool
    existing_policy: str
    output_format: str
    plan: FolderBatchPlan


class FakeAcceptedDialog:
    result_obj: FakeDialogResult | None = None

    def __init__(self, parent: object = None, **kwargs: object) -> None:
        self.parent = parent
        self.kwargs = kwargs

    def exec(self) -> int:
        return 1

    def result_options(self) -> object | None:
        return type(self).result_obj


class FailingSettings:
    def setValue(self, key: str, value: object) -> None:  # noqa: N802 - QSettings compatibility
        raise RuntimeError('settings write failed')

    def value(self, key: str, default: object = None) -> object:
        return default


class FolderBatchDialogControllerSweepTests(unittest.TestCase):
    def test_controller_rejects_zero_target_plan_even_if_dialog_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            plan = build_folder_batch_plan(root, out)
            FakeAcceptedDialog.result_obj = FakeDialogResult(root, out, True, True, 'skip', 'xtc', plan)
            called = False
            warnings: list[tuple[str, str]] = []

            def converter(source: Path, output: Path, item) -> None:
                nonlocal called
                called = True

            run = open_folder_batch_dialog_and_execute(
                object(),
                settings={},
                converter=converter,
                dialog_cls=FakeAcceptedDialog,
                warning_cb=lambda title, body: warnings.append((title, body)),
            )

            self.assertIsNone(run)
            self.assertFalse(called)
            self.assertTrue(any('変換対象ファイルが見つかりません' in body for _, body in warnings))
            self.assertFalse(folder_batch_plan_can_execute(plan))
            self.assertIn('対象ファイル形式', describe_folder_batch_no_work(plan))

    def test_controller_rejects_all_skipped_plan_and_explains_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            (out / 'book.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')
            FakeAcceptedDialog.result_obj = FakeDialogResult(root, out, True, True, 'skip', 'xtc', plan)
            warnings: list[tuple[str, str]] = []

            run = open_folder_batch_dialog_and_execute(
                object(),
                settings={},
                converter=lambda source, output, item: output.write_text('new', encoding='utf-8'),
                dialog_cls=FakeAcceptedDialog,
                warning_cb=lambda title, body: warnings.append((title, body)),
            )

            self.assertIsNone(run)
            self.assertEqual((out / 'book.xtc').read_text(encoding='utf-8'), 'old')
            self.assertTrue(any('すべて既存ファイル扱いによりスキップ' in body for _, body in warnings))
            self.assertIn('すべて既存ファイル扱いによりスキップ', describe_folder_batch_no_work(plan))


    def test_controller_partial_skip_notice_explains_mixed_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'done.txt').write_text('hello', encoding='utf-8')
            (root / 'new.txt').write_text('hello', encoding='utf-8')
            (out / 'done.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')

        self.assertTrue(folder_batch_plan_can_execute(plan))
        message = describe_folder_batch_partial_skip_notice(plan)
        self.assertIn('一部のファイルは既存ファイルがあるためスキップされます。', message)
        self.assertIn('変換予定のファイルのみ処理します。', message)

    def test_settings_save_failure_warns_but_does_not_block_conversion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            FakeAcceptedDialog.result_obj = FakeDialogResult(root, out, True, True, 'skip', 'xtc', plan)
            warnings: list[tuple[str, str]] = []

            run = open_folder_batch_dialog_and_execute(
                object(),
                settings=FailingSettings(),
                converter=lambda source, output, item: output.write_text('converted', encoding='utf-8'),
                dialog_cls=FakeAcceptedDialog,
                warning_cb=lambda title, body: warnings.append((title, body)),
            )

            self.assertIsNotNone(run)
            self.assertTrue((out / 'book.xtc').exists())
            self.assertTrue(any('前回設定の保存に失敗' in body for _, body in warnings))

    def test_progress_callback_failure_is_logged_without_crashing_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            FakeAcceptedDialog.result_obj = FakeDialogResult(root, out, True, True, 'skip', 'xtc', plan)
            warnings: list[tuple[str, str]] = []
            logs: list[str] = []

            run = open_folder_batch_dialog_and_execute(
                object(),
                settings={},
                converter=lambda source, output, item: output.write_text('converted', encoding='utf-8'),
                dialog_cls=FakeAcceptedDialog,
                log_cb=logs.append,
                progress_cb=lambda index, total, item: (_ for _ in ()).throw(RuntimeError('progress failed')),
                warning_cb=lambda title, body: warnings.append((title, body)),
            )

            self.assertIsNotNone(run)
            self.assertTrue((out / 'book.xtc').exists())
            self.assertFalse(warnings)
            self.assertTrue(any('[WARN]' in line and 'progress failed' in line for line in logs))

    def test_safety_warning_formatter_is_shared_and_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'books'
            out = root / 'out'
            out.mkdir(parents=True)
            report = analyze_folder_batch_roots(root, out)
            lines = format_folder_batch_safety_warnings(report)
            summary_lines = summarize_folder_batch_root_safety(root, out)

        self.assertTrue(lines)
        self.assertEqual(lines, summary_lines)
        self.assertTrue(all(line.startswith('注意: ') for line in lines))
        self.assertTrue(any('配下' in line for line in lines))


if __name__ == '__main__':
    unittest.main()
