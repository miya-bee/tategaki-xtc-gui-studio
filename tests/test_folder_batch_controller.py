from __future__ import annotations

import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from tategakiXTC_folder_batch_controller import (
    folder_batch_convert_suffixes,
    folder_batch_dialog_kwargs,
    format_folder_batch_missing_dependency_message,
    missing_dependencies_for_folder_batch_plan,
    normalize_output_format_from_getter,
    open_folder_batch_dialog_and_execute,
    run_folder_batch_plan_with_callbacks,
)
from tategakiXTC_folder_batch_plan import FolderBatchPlan, build_folder_batch_plan
from tategakiXTC_folder_batch_settings import FolderBatchDialogDefaults


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
    last_kwargs: dict[str, object] | None = None
    result_obj: FakeDialogResult | None = None

    def __init__(self, parent: object = None, **kwargs: object) -> None:
        type(self).last_kwargs = kwargs

    def exec(self) -> int:
        return 1

    def result_options(self) -> object | None:
        return type(self).result_obj


class FakeRejectedDialog(FakeAcceptedDialog):
    def exec(self) -> int:
        return 0


class FolderBatchControllerTests(unittest.TestCase):
    def test_normalize_output_format_from_getter(self) -> None:
        self.assertEqual(normalize_output_format_from_getter(lambda: '.xtch'), 'xtch')
        self.assertEqual(normalize_output_format_from_getter(lambda: 'bad'), 'xtc')
        self.assertEqual(normalize_output_format_from_getter(lambda: 1), 'xtc')
        self.assertEqual(normalize_output_format_from_getter(None), 'xtc')

    def test_dialog_kwargs_passes_supported_suffixes_only_when_given(self) -> None:
        defaults = FolderBatchDialogDefaults(input_root='in', output_root='out')
        plain = folder_batch_dialog_kwargs(defaults, output_format='xtc')
        self.assertNotIn('supported_suffixes', plain)
        with_suffixes = folder_batch_dialog_kwargs(
            defaults,
            output_format='xtc',
            supported_suffixes=['.txt', '.epub'],
        )
        self.assertEqual(with_suffixes['supported_suffixes'], ('.txt', '.epub'))

    def test_run_plan_with_callbacks_logs_plan_and_shows_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            logs: list[str] = []
            info: list[tuple[str, str]] = []

            def converter(source: Path, output: Path, item) -> None:
                output.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')

            result = run_folder_batch_plan_with_callbacks(
                plan,
                converter,
                log_cb=logs.append,
                information_cb=lambda title, body: info.append((title, body)),
            )
            self.assertEqual(result.success_count, 1)
            self.assertTrue((out / 'book.xtc').exists())
            self.assertTrue(any(line.startswith('[PLAN] 変換対象:') for line in logs))
            self.assertTrue(any(line.startswith('[DONE] 成功 1 件') for line in logs))
            self.assertIn('成功: 1 件', info[0][1])
            self.assertIn('処理済み: 1 / 1 件', info[0][1])
            self.assertIn(f'出力先: {out}', info[0][1])


    def test_run_plan_lifecycle_callbacks_wrap_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            events: list[str] = []

            def converter(source: Path, output: Path, item) -> None:
                events.append(f'convert:{item.relative_source_path}')
                output.write_text('converted', encoding='utf-8')

            result = run_folder_batch_plan_with_callbacks(
                plan,
                converter,
                before_execute_cb=lambda batch_plan: events.append(f'before:{batch_plan.convert_count}'),
                after_execute_cb=lambda execution_result: events.append(
                    f'after:{execution_result.success_count if execution_result is not None else "none"}'
                ),
            )

            self.assertEqual(result.success_count, 1)
            self.assertEqual(events, ['before:1', 'convert:book.txt', 'after:1'])


    def test_run_plan_post_execute_notifications_do_not_mask_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            logs: list[str] = []
            after_calls: list[str] = []

            def converter(source: Path, output: Path, item) -> None:
                output.write_text('converted', encoding='utf-8')

            def after_execute(result) -> None:
                after_calls.append(str(result.success_count if result is not None else 'none'))
                raise RuntimeError('status widget disappeared')

            def information(title: str, body: str) -> None:
                raise RuntimeError('dialog closed')

            result = run_folder_batch_plan_with_callbacks(
                plan,
                converter,
                log_cb=logs.append,
                after_execute_cb=after_execute,
                information_cb=information,
            )

            self.assertEqual(result.success_count, 1)
            self.assertTrue((out / 'book.xtc').exists())
            self.assertEqual(after_calls, ['1'])
            self.assertTrue(any('[WARN] 実行後UI更新に失敗しました' in line for line in logs))
            self.assertTrue(any('[WARN] 完了通知に失敗しました' in line for line in logs))

    def test_open_dialog_returns_run_even_if_information_callback_fails_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            FakeAcceptedDialog.result_obj = FakeDialogResult(
                input_root=root,
                output_root=out,
                include_subfolders=True,
                preserve_structure=True,
                existing_policy='skip',
                output_format='xtc',
                plan=plan,
            )
            logs: list[str] = []
            warnings: list[tuple[str, str]] = []

            def converter(source: Path, output: Path, item) -> None:
                output.write_text('converted', encoding='utf-8')

            run = open_folder_batch_dialog_and_execute(
                object(),
                settings={},
                converter=converter,
                output_format_getter=lambda: 'xtc',
                supported_suffixes=['.txt'],
                log_cb=logs.append,
                information_cb=lambda title, body: (_ for _ in ()).throw(RuntimeError('dialog closed')),
                warning_cb=lambda title, body: warnings.append((title, body)),
                dialog_cls=FakeAcceptedDialog,
            )

            self.assertIsNotNone(run)
            assert run is not None
            self.assertEqual(run.execution_result.success_count, 1)
            self.assertEqual(warnings, [])
            self.assertTrue(any('[WARN] 完了通知に失敗しました' in line for line in logs))

    def test_open_dialog_executes_and_saves_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='rename')
            FakeAcceptedDialog.result_obj = FakeDialogResult(
                input_root=root,
                output_root=out,
                include_subfolders=True,
                preserve_structure=True,
                existing_policy='rename',
                output_format='xtc',
                plan=plan,
            )
            settings: dict[str, object] = {}
            logs: list[str] = []

            def converter(source: Path, output: Path, item) -> None:
                output.write_text('converted', encoding='utf-8')

            run = open_folder_batch_dialog_and_execute(
                object(),
                settings=settings,
                converter=converter,
                output_format_getter=lambda: 'xtc',
                supported_suffixes=['.txt'],
                log_cb=logs.append,
                dialog_cls=FakeAcceptedDialog,
            )
            self.assertIsNotNone(run)
            assert run is not None
            self.assertEqual(run.execution_result.success_count, 1)
            self.assertEqual(settings['folder_batch/existing_policy'], 'rename')
            self.assertEqual(FakeAcceptedDialog.last_kwargs['supported_suffixes'], ('.txt',))
            self.assertTrue((out / 'book.xtc').exists())

    def test_missing_dependency_message_includes_windows_py310_install_hint(self) -> None:
        message = format_folder_batch_missing_dependency_message([
            {'label': 'ebooklib', 'package': 'ebooklib', 'purpose': 'EPUB変換'},
            {'label': 'beautifulsoup4', 'package': 'beautifulsoup4', 'purpose': 'EPUB変換'},
        ])
        self.assertIn('ebooklib（EPUB変換）', message)
        self.assertIn('beautifulsoup4（EPUB変換）', message)
        self.assertIn('install_requirements.bat', message)
        self.assertIn('EPUB などを除外して再実行', message)
        self.assertIn('py -3.10 -m pip install ebooklib beautifulsoup4', message)
        self.assertIn('py -3.10 -m pip install -r requirements.txt', message)
        self.assertIn('処理は開始していません', message)

    def test_missing_dependencies_for_plan_checks_only_convert_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            out.mkdir()
            epub_path = root / 'book.epub'
            txt_path = root / 'note.txt'
            epub_path.write_text('epub', encoding='utf-8')
            txt_path.write_text('txt', encoding='utf-8')
            # Existing .epub is skipped, so the dependency check should only see .txt.
            (out / 'book.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')
            seen_suffixes: list[tuple[str, ...]] = []

            def getter(suffixes):
                seen_suffixes.append(tuple(suffixes))
                return [{'label': 'ebooklib', 'package': 'ebooklib', 'purpose': 'EPUB変換'}] if '.epub' in suffixes else []

            self.assertEqual(folder_batch_convert_suffixes(plan), ('.txt',))
            self.assertEqual(missing_dependencies_for_folder_batch_plan(plan, getter), [])
            self.assertEqual(seen_suffixes, [('.txt',)])

    def test_open_dialog_blocks_execution_when_dependency_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.epub').write_text('fake epub', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, supported_suffixes=['.epub'])
            FakeAcceptedDialog.result_obj = FakeDialogResult(
                input_root=root,
                output_root=out,
                include_subfolders=True,
                preserve_structure=True,
                existing_policy='skip',
                output_format='xtc',
                plan=plan,
            )
            settings: dict[str, object] = {}
            warnings: list[tuple[str, str]] = []
            calls: list[str] = []

            run = open_folder_batch_dialog_and_execute(
                object(),
                settings=settings,
                converter=lambda source, output, item: calls.append(str(source)),
                output_format_getter=lambda: 'xtc',
                supported_suffixes=['.epub'],
                warning_cb=lambda title, body: warnings.append((title, body)),
                dialog_cls=FakeAcceptedDialog,
                missing_dependency_getter=lambda suffixes: [
                    {'label': 'ebooklib', 'package': 'ebooklib', 'purpose': 'EPUB変換'},
                ],
            )
            self.assertIsNone(run)
            self.assertEqual(calls, [])
            self.assertEqual(settings, {})
            self.assertTrue(warnings)
            self.assertIn('ebooklib', warnings[0][1])
            self.assertIn('処理は開始していません', warnings[0][1])

    def test_open_dialog_returns_none_when_cancelled(self) -> None:
        run = open_folder_batch_dialog_and_execute(
            object(),
            settings={},
            converter=lambda source, output, item: None,
            dialog_cls=FakeRejectedDialog,
        )
        self.assertIsNone(run)


if __name__ == '__main__':
    unittest.main()
