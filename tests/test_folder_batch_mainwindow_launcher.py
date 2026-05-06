from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tategakiXTC_folder_batch_mainwindow_launcher as launcher_module
from tategakiXTC_folder_batch_mainwindow_launcher import (
    append_log_best_effort,
    extract_folder_batch_output_root_from_summary,
    folder_batch_suffixes_from_mainwindow,
    folder_batch_completion_dialog_best_effort,
    information_dialog_best_effort,
    install_folder_batch_menu_action_best_effort,
    make_folder_batch_inner_progress_callback,
    open_folder_in_desktop_best_effort,
    open_folder_batch_dialog_for_mainwindow_dry_run,
    make_folder_batch_after_execute_callback,
    make_folder_batch_before_execute_callback,
    make_folder_batch_progress_callback,
    open_folder_batch_dialog_for_mainwindow_real_or_warn,
    output_format_from_mainwindow,
    request_folder_batch_cancel_best_effort,
    should_cancel_folder_batch_from_mainwindow,
)
from tategakiXTC_folder_batch_plan import build_folder_batch_plan


class FakeCombo:
    def __init__(self, data: object = None, text: object = None) -> None:
        self.data = data
        self.text = text

    def currentData(self) -> object:
        return self.data

    def currentText(self) -> object:
        return self.text


class FakeSignal:
    def __init__(self) -> None:
        self.connected = None

    def connect(self, callback) -> None:
        self.connected = callback


class FakeAction:
    def __init__(self, title: str) -> None:
        self.title = title
        self.triggered = FakeSignal()
        self.enabled: bool | None = None

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)


class FakeMenuBar:
    def __init__(self) -> None:
        self.actions: list[FakeAction] = []

    def addAction(self, title: str) -> FakeAction:
        action = FakeAction(title)
        self.actions.append(action)
        return action


class FakeLabel:
    def __init__(self) -> None:
        self.text = ''

    def setText(self, text: str) -> None:
        self.text = text


class FakeButton(FakeLabel):
    def __init__(self) -> None:
        super().__init__()
        self.enabled: bool | None = None

    def setEnabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)


class FakeProgressBar:
    def __init__(self) -> None:
        self.range: tuple[int, int] | None = None
        self.value: int | None = None

    def setRange(self, minimum: int, maximum: int) -> None:
        self.range = (minimum, maximum)

    def setValue(self, value: int) -> None:
        self.value = value


class FakeMainWindow:
    def __init__(self) -> None:
        self.logs: list[str] = []
        self.info: list[tuple[str, str]] = []
        self.warn: list[tuple[str, str]] = []
        self.settings_store: dict[str, object] = {}
        self.output_format_combo = FakeCombo('.xtch')
        self.menu = FakeMenuBar()
        self.run_btn = FakeButton()
        self.folder_batch_btn = FakeButton()
        self.folder_batch_action = FakeAction('フォルダ一括変換...')
        self.stop_btn = FakeButton()
        self.busy_badge = FakeLabel()
        self.progress_label = FakeLabel()
        self.progress_bar = FakeProgressBar()
        self.statuses: list[tuple[str, object]] = []

    def _append_log_without_status_best_effort(self, message: str) -> None:
        self.logs.append(message)

    def _show_information_dialog_with_status_fallback(self, title: str, body: str) -> None:
        self.info.append((title, body))

    def _show_warning_dialog_with_status_fallback(self, title: str, body: str) -> None:
        self.warn.append((title, body))

    def _show_ui_status_message_with_reflection_or_direct_fallback(self, message: str, timeout_ms=None) -> None:
        self.statuses.append((message, timeout_ms))

    def menuBar(self) -> FakeMenuBar:
        return self.menu

    def _open_folder_batch_dialog(self) -> None:
        self.logs.append('opened')


class FakeDialogResult:
    def __init__(self, plan) -> None:
        self.input_root = plan.input_root
        self.output_root = plan.output_root
        self.include_subfolders = plan.include_subfolders
        self.preserve_structure = plan.preserve_structure
        self.existing_policy = plan.existing_policy
        self.output_format = plan.output_format
        self.plan = plan


class AcceptedDialog:
    result_obj = None
    kwargs = None

    def __init__(self, parent=None, **kwargs) -> None:
        type(self).kwargs = kwargs

    def exec(self) -> int:
        return 1

    def result_options(self):
        return type(self).result_obj


class FolderBatchMainWindowLauncherTests(unittest.TestCase):
    def test_output_format_from_mainwindow_reads_combo_data(self) -> None:
        self.assertEqual(output_format_from_mainwindow(FakeMainWindow()), 'xtch')
        mw = FakeMainWindow()
        mw.output_format_combo = FakeCombo('bad', 'xtc')
        self.assertEqual(output_format_from_mainwindow(mw), 'xtc')

    def test_suffixes_include_text_epub_and_images(self) -> None:
        suffixes = folder_batch_suffixes_from_mainwindow(object())
        for suffix in ('.txt', '.md', '.epub', '.png', '.jpg', '.jpeg', '.webp'):
            self.assertIn(suffix, suffixes)

    def test_dialog_callbacks_fall_back_to_log(self) -> None:
        class LogOnly:
            def __init__(self) -> None:
                self.logs: list[str] = []

            def _append_log_without_status_best_effort(self, message: str) -> None:
                self.logs.append(message)

        mw = LogOnly()
        append_log_best_effort(mw, 'hello')
        information_dialog_best_effort(mw, 'info', 'body')
        self.assertEqual(mw.logs[0], 'hello')
        self.assertTrue(any('info' in line for line in mw.logs))

    def test_extract_output_root_from_folder_batch_completion_summary(self) -> None:
        body = 'フォルダ一括変換が完了しました。\n成功: 1 件\n出力先: C:/tmp3/out\n'

        self.assertEqual(
            extract_folder_batch_output_root_from_summary(body),
            Path('C:/tmp3/out'),
        )

    def test_open_folder_best_effort_reports_missing_output_root(self) -> None:
        mw = FakeMainWindow()

        opened = open_folder_in_desktop_best_effort(Path('/definitely/missing/output'), mw)

        self.assertFalse(opened)
        self.assertTrue(any('出力フォルダが見つかりません' in line for line in mw.logs))

    def test_folder_batch_completion_without_output_root_uses_normal_information_dialog(self) -> None:
        mw = FakeMainWindow()

        folder_batch_completion_dialog_best_effort(mw, '完了', '出力先行なし')

        self.assertEqual(mw.info, [('完了', '出力先行なし')])

    def test_install_menu_action_connects_opener(self) -> None:
        mw = FakeMainWindow()
        action = install_folder_batch_menu_action_best_effort(mw)
        self.assertIsNotNone(action)
        self.assertEqual(mw.menu.actions[0].title, 'フォルダ一括変換...')
        self.assertIsNotNone(mw.menu.actions[0].triggered.connected)

    def test_open_dialog_dry_run_can_be_tested_with_fake_dialog(self) -> None:
        # Directly exercise controller dialog_cls injection through the public helper's
        # lower-level module would require monkey-patching.  Keep this test focused on
        # a dry-run converter created by the helper dependencies.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, output_format='xtch')
            from tategakiXTC_folder_batch_controller import open_folder_batch_dialog_and_execute

            AcceptedDialog.result_obj = FakeDialogResult(plan)
            mw = FakeMainWindow()
            run = open_folder_batch_dialog_and_execute(
                mw,
                settings=mw.settings_store,
                converter=lambda src, dst, item: dst.write_text('dry', encoding='utf-8'),
                output_format_getter=lambda: output_format_from_mainwindow(mw),
                log_cb=mw.logs.append,
                information_cb=lambda title, body: mw.info.append((title, body)),
                warning_cb=lambda title, body: mw.warn.append((title, body)),
                dialog_cls=AcceptedDialog,
            )
            self.assertIsNotNone(run)
            self.assertTrue((out / 'book.xtch').exists())
            self.assertEqual(mw.settings_store['folder_batch/output_root'], str(out))




    def test_folder_batch_progress_callback_updates_bottom_status_widgets(self) -> None:
        mw = FakeMainWindow()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            item = plan.items[0]

            make_folder_batch_before_execute_callback(mw)(plan)
            self.assertIn('0/1 件', mw.progress_label.text)
            make_folder_batch_progress_callback(mw)(1, 1, item)
            self.assertIn('1/1 件目', mw.progress_label.text)
            self.assertIn('book.txt', mw.progress_label.text)
            make_folder_batch_after_execute_callback(mw)(type('Result', (), {
                'stopped': False,
                'success_count': 1,
                'skipped_count': 0,
                'failed_count': 0,
                'processed_count': 1,
                'plan': plan,
            })())

        self.assertEqual(mw.busy_badge.text, '待機中')
        self.assertEqual(mw.progress_bar.range, (0, 1))
        self.assertEqual(mw.progress_bar.value, 1)
        self.assertIn('完了', mw.progress_label.text)
        self.assertFalse(mw.stop_btn.enabled)
        self.assertTrue(mw.folder_batch_btn.enabled)
        self.assertTrue(mw.folder_batch_action.enabled)
        self.assertIn('成功 1 / スキップ 0 / 失敗 0 / 処理済み 1/1', mw.progress_label.text)

    def test_folder_batch_inner_progress_callback_keeps_batch_context(self) -> None:
        mw = FakeMainWindow()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)
            item = plan.items[0]

            make_folder_batch_progress_callback(mw)(1, 3, item)
            make_folder_batch_inner_progress_callback(mw)(2, 5, 'ページ生成中')

        self.assertIn('1/3 件目', mw.progress_label.text)
        self.assertIn('book.txt', mw.progress_label.text)
        self.assertIn('内部 2/5', mw.progress_label.text)
        self.assertIn('ページ生成中', mw.progress_label.text)

    def test_folder_batch_running_state_disables_reentrant_folder_batch_controls(self) -> None:
        mw = FakeMainWindow()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.txt').write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out)

            make_folder_batch_before_execute_callback(mw)(plan)

        self.assertTrue(mw._folder_batch_running)
        self.assertFalse(mw.run_btn.enabled)
        self.assertFalse(mw.folder_batch_btn.enabled)
        self.assertFalse(mw.folder_batch_action.enabled)
        self.assertTrue(mw.stop_btn.enabled)

    def test_folder_batch_after_execute_none_reports_incomplete_not_complete(self) -> None:
        mw = FakeMainWindow()

        make_folder_batch_after_execute_callback(mw)(None)

        self.assertIn('完了できませんでした', mw.progress_label.text)
        self.assertFalse(mw._folder_batch_running)
        self.assertTrue(mw.folder_batch_btn.enabled)

    def test_folder_batch_cancel_request_sets_flag_and_disables_stop_button(self) -> None:
        mw = FakeMainWindow()
        mw._folder_batch_running = True
        mw._folder_batch_cancel_requested = False

        request_folder_batch_cancel_best_effort(mw)

        self.assertTrue(should_cancel_folder_batch_from_mainwindow(mw))
        self.assertFalse(mw.stop_btn.enabled)
        self.assertIn('現在のファイルが終わりしだい', mw.progress_label.text)
        self.assertTrue(any('停止要求' in line for line in mw.logs))

    def test_folder_batch_after_execute_stopped_reports_pending_count(self) -> None:
        class Result:
            stopped = True
            failed_count = 0
            success_count = 1
            skipped_count = 1
            processed_count = 2
            stopped_pending_count = 3

            class plan:
                total_count = 5

        mw = FakeMainWindow()

        make_folder_batch_after_execute_callback(mw)(Result())

        self.assertIn('停止しました', mw.progress_label.text)
        self.assertIn('未処理 3', mw.progress_label.text)
        self.assertFalse(mw._folder_batch_running)
        self.assertTrue(mw.folder_batch_btn.enabled)

    def test_real_or_warn_forwards_progress_and_cancel_callbacks_to_controller(self) -> None:
        class HookMainWindow(FakeMainWindow):
            def _convert_single_file_for_folder_batch(self, source_path, output_path, item) -> None:
                Path(output_path).write_text('converted', encoding='utf-8')

        captured: dict[str, object] = {}
        original = launcher_module.open_folder_batch_dialog_and_execute

        def fake_open(parent, **kwargs):
            captured.update(kwargs)
            return object()

        try:
            launcher_module.open_folder_batch_dialog_and_execute = fake_open
            progress_cb = lambda index, total, item: None
            should_cancel = lambda: False
            result = open_folder_batch_dialog_for_mainwindow_real_or_warn(
                HookMainWindow(),
                progress_cb=progress_cb,
                should_cancel=should_cancel,
            )
        finally:
            launcher_module.open_folder_batch_dialog_and_execute = original

        self.assertIsNotNone(result)
        self.assertIs(captured['progress_cb'], progress_cb)
        self.assertIs(captured['should_cancel'], should_cancel)
        self.assertIn('.epub', tuple(captured['supported_suffixes']))

    def test_real_or_warn_completion_callback_uses_output_folder_dialog(self) -> None:
        class HookMainWindow(FakeMainWindow):
            def _convert_single_file_for_folder_batch(self, source_path, output_path, item) -> None:
                Path(output_path).write_text('converted', encoding='utf-8')

        captured_controller: dict[str, object] = {}
        captured_completion: list[tuple[object, str, str]] = []
        original_open = launcher_module.open_folder_batch_dialog_and_execute
        original_completion = launcher_module.folder_batch_completion_dialog_best_effort

        def fake_open(parent, **kwargs):
            captured_controller.update(kwargs)
            return object()

        def fake_completion(main_window, title, body):
            captured_completion.append((main_window, title, body))

        try:
            launcher_module.open_folder_batch_dialog_and_execute = fake_open
            launcher_module.folder_batch_completion_dialog_best_effort = fake_completion
            mw = HookMainWindow()
            result = open_folder_batch_dialog_for_mainwindow_real_or_warn(mw)
            self.assertIsNotNone(result)
            info_cb = captured_controller['information_cb']
            info_cb('フォルダ一括変換', '出力先: C:/tmp3/out')
        finally:
            launcher_module.open_folder_batch_dialog_and_execute = original_open
            launcher_module.folder_batch_completion_dialog_best_effort = original_completion

        self.assertEqual(captured_completion, [(mw, 'フォルダ一括変換', '出力先: C:/tmp3/out')])

    def test_real_or_warn_forwards_inner_progress_to_worker_bridge_fallback(self) -> None:
        captured_bridge: dict[str, object] = {}
        captured_controller: dict[str, object] = {}
        original_hook = launcher_module.build_mainwindow_converter_from_known_hook
        original_bridge = launcher_module.make_mainwindow_worker_bridge_converter
        original_open = launcher_module.open_folder_batch_dialog_and_execute

        def fake_hook(main_window):
            raise AttributeError('no hook')

        def fake_bridge(main_window, **kwargs):
            captured_bridge.update(kwargs)
            return lambda source, output, item: Path(output).write_text('converted', encoding='utf-8')

        def fake_open(parent, **kwargs):
            captured_controller.update(kwargs)
            return object()

        try:
            launcher_module.build_mainwindow_converter_from_known_hook = fake_hook
            launcher_module.make_mainwindow_worker_bridge_converter = fake_bridge
            launcher_module.open_folder_batch_dialog_and_execute = fake_open
            progress_cb = lambda index, total, item: None
            should_cancel = lambda: False
            inner_progress_cb = lambda index, total, text: None
            result = open_folder_batch_dialog_for_mainwindow_real_or_warn(
                FakeMainWindow(),
                progress_cb=progress_cb,
                should_cancel=should_cancel,
                inner_progress_cb=inner_progress_cb,
            )
        finally:
            launcher_module.build_mainwindow_converter_from_known_hook = original_hook
            launcher_module.make_mainwindow_worker_bridge_converter = original_bridge
            launcher_module.open_folder_batch_dialog_and_execute = original_open

        self.assertIsNotNone(result)
        self.assertIs(captured_bridge['inner_progress_cb'], inner_progress_cb)
        self.assertIs(captured_controller['progress_cb'], progress_cb)
        self.assertIs(captured_controller['should_cancel'], should_cancel)

    def test_real_or_warn_reports_missing_hook(self) -> None:
        mw = FakeMainWindow()
        result = open_folder_batch_dialog_for_mainwindow_real_or_warn(mw)
        self.assertIsNone(result)
        self.assertTrue(mw.warn)
        self.assertIn('hook', mw.warn[0][1])


if __name__ == '__main__':
    unittest.main()
