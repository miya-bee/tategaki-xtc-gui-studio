from __future__ import annotations

"""Small MainWindow launcher helpers for folder batch conversion.

This module keeps the GUI wiring intentionally conservative.  It can be called
from ``MainWindow._open_folder_batch_dialog`` without editing the crowded layout
code.  Production wiring uses the worker bridge; the dry-run helper remains for
unit tests and smoke tests.
"""

from collections.abc import Iterable
from pathlib import Path
import re
from typing import Callable, Protocol

from tategakiXTC_folder_batch_controller import (
    FolderBatchControllerRun,
    make_dry_run_converter,
    open_folder_batch_dialog_and_execute,
)
from tategakiXTC_folder_batch_converter_adapter import (
    build_mainwindow_converter_from_known_hook,
)
from tategakiXTC_folder_batch_worker_bridge import (
    make_mainwindow_worker_bridge_converter,
)
from tategakiXTC_folder_batch_executor import (
    FolderBatchCancelCallback,
    FolderBatchConvertCallback,
    FolderBatchProgressCallback,
)
from tategakiXTC_folder_batch_plan import (
    DEFAULT_FOLDER_BATCH_SUFFIXES,
    FolderBatchPlan,
    FolderBatchPlanItem,
    normalize_suffixes,
)


class MainWindowLike(Protocol):
    settings_store: object


LogCallback = Callable[[str], None]
InfoCallback = Callable[[str, str], None]
WarningCallback = Callable[[str, str], None]
OutputFormatGetter = Callable[[], str]
InnerProgressCallback = Callable[[int, int, str], None]


def _callable_attr(obj: object, name: str) -> Callable[..., object] | None:
    attr = getattr(obj, name, None)
    return attr if callable(attr) else None


def append_log_best_effort(main_window: object, message: str) -> None:
    """Append to the app log if a known logging method exists."""

    for name in (
        '_append_log_without_status_best_effort',
        '_append_log_with_status_fallback',
        'append_log',
    ):
        callback = _callable_attr(main_window, name)
        if callback is None:
            continue
        try:
            callback(message)
            return
        except TypeError:
            try:
                callback(message, reflect_in_status=False)
                return
            except Exception:
                continue
        except Exception:
            continue


def information_dialog_best_effort(main_window: object, title: str, body: str) -> None:
    callback = _callable_attr(main_window, '_show_information_dialog_with_status_fallback')
    if callback is not None:
        try:
            callback(title, body)
            return
        except Exception:
            pass
    append_log_best_effort(main_window, f'{title}: {body}')


def extract_folder_batch_output_root_from_summary(body: str) -> Path | None:
    """Extract the output folder path from a folder-batch completion summary."""

    for line in str(body or '').splitlines():
        match = re.match(r'^\s*出力先\s*:\s*(.+?)\s*$', line)
        if match is None:
            continue
        text = match.group(1).strip().strip('"')
        if not text:
            return None
        return Path(text)
    return None


def open_folder_in_desktop_best_effort(path: str | Path, main_window: object | None = None) -> bool:
    """Open a folder with the desktop shell without letting errors escape."""

    try:
        folder = Path(path).expanduser()
    except Exception as exc:
        if main_window is not None:
            append_log_best_effort(main_window, f'[WARN] 出力フォルダを開けませんでした: {exc}')
        return False
    if not folder.exists() or not folder.is_dir():
        if main_window is not None:
            append_log_best_effort(main_window, f'[WARN] 出力フォルダが見つかりません: {folder}')
        return False
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        opened = bool(QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))))
        if opened:
            if main_window is not None:
                append_log_best_effort(main_window, f'[BATCH] 出力フォルダを開きました: {folder}')
            return True
    except Exception as exc:
        if main_window is not None:
            append_log_best_effort(main_window, f'[WARN] Qt 経由で出力フォルダを開けませんでした: {exc}')

    try:
        import os
        import subprocess
        import sys

        if sys.platform.startswith('win'):
            os.startfile(str(folder))  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(folder)])
        else:
            subprocess.Popen(['xdg-open', str(folder)])
        if main_window is not None:
            append_log_best_effort(main_window, f'[BATCH] 出力フォルダを開きました: {folder}')
        return True
    except Exception as exc:
        if main_window is not None:
            append_log_best_effort(main_window, f'[WARN] 出力フォルダを開けませんでした: {exc}')
        return False


def folder_batch_completion_dialog_best_effort(main_window: object, title: str, body: str) -> None:
    """Show folder-batch completion with an optional open-output-folder button."""

    output_root = extract_folder_batch_output_root_from_summary(body)
    if output_root is None:
        information_dialog_best_effort(main_window, title, body)
        return
    try:
        from PySide6.QtWidgets import QMessageBox

        dialog = QMessageBox(main_window if hasattr(main_window, 'window') else None)
        dialog.setIcon(QMessageBox.Information)
        dialog.setWindowTitle(title)
        dialog.setText(body)
        ok_button = dialog.addButton(QMessageBox.Ok)
        open_button = dialog.addButton('出力フォルダを開く', QMessageBox.ActionRole)
        dialog.setDefaultButton(ok_button)
        dialog.exec()
        if dialog.clickedButton() is open_button:
            open_folder_in_desktop_best_effort(output_root, main_window)
    except Exception as exc:
        append_log_best_effort(main_window, f'[WARN] 出力フォルダボタン付き完了通知に失敗しました: {exc}')
        information_dialog_best_effort(main_window, title, body)


def warning_dialog_best_effort(main_window: object, title: str, body: str) -> None:
    callback = _callable_attr(main_window, '_show_warning_dialog_with_status_fallback')
    if callback is not None:
        try:
            callback(title, body)
            return
        except Exception:
            pass
    append_log_best_effort(main_window, f'{title}: {body}')


def process_gui_events_best_effort() -> None:
    """Let Qt process pending button/status events during synchronous batch steps."""

    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.processEvents()
    except Exception:
        pass


def _set_widget_enabled(widget: object, enabled: bool) -> None:
    setter = getattr(widget, 'setEnabled', None)
    if callable(setter):
        try:
            setter(bool(enabled))
        except Exception:
            pass


def _set_widget_text(widget: object, text: str) -> None:
    setter = getattr(widget, 'setText', None)
    if callable(setter):
        try:
            setter(text)
        except Exception:
            pass


def _set_progress_bar(widget: object, current: int, total: int) -> None:
    try:
        total_value = max(1, int(total))
        current_value = max(0, min(int(current), total_value))
    except Exception:
        total_value = 1
        current_value = 0
    set_range = getattr(widget, 'setRange', None)
    set_value = getattr(widget, 'setValue', None)
    if callable(set_range):
        try:
            set_range(0, total_value)
        except Exception:
            pass
    if callable(set_value):
        try:
            set_value(current_value)
        except Exception:
            pass



def _compact_folder_batch_status_text(text: object, *, max_chars: int = 64) -> str:
    """Return a one-line, middle-truncated status fragment for compact labels."""

    value = ' '.join(str(text or '').replace('\\', '/').split())
    if not value:
        return ''
    limit = max(16, int(max_chars))
    if len(value) <= limit:
        return value
    head = max(6, (limit - 1) // 2)
    tail = max(6, limit - head - 1)
    return value[:head].rstrip() + '…' + value[-tail:].lstrip()


def _relative_path_from_folder_batch_item(item: FolderBatchPlanItem | object | None) -> str:
    if item is None:
        return ''
    for name in ('relative_source_path', 'source_path'):
        try:
            value = getattr(item, name)
        except Exception:
            continue
        if value:
            return str(value)
    return str(item or '')


def format_folder_batch_progress_text(
    index: int,
    total: int,
    item: FolderBatchPlanItem | object | None = None,
    *,
    detail: object = '',
) -> str:
    """Format the folder-batch progress label in a stable, readable way."""

    try:
        total_value = max(1, int(total))
    except Exception:
        total_value = 1
    try:
        current_value = max(0, min(int(index), total_value))
    except Exception:
        current_value = 0
    if current_value <= 0:
        base = f'フォルダ一括変換中… 0/{total_value} 件｜準備中'
    else:
        rel = _compact_folder_batch_status_text(
            _relative_path_from_folder_batch_item(item),
            max_chars=60,
        )
        if rel:
            base = f'フォルダ一括変換中… {current_value}/{total_value} 件目｜{rel}'
        else:
            base = f'フォルダ一括変換中… {current_value}/{total_value} 件目'
    detail_text = _compact_folder_batch_status_text(detail, max_chars=60)
    if detail_text:
        return f'{base}｜{detail_text}'
    return base


def show_status_best_effort(main_window: object, message: str, timeout_ms: int | None = None) -> None:
    callback = _callable_attr(main_window, '_show_ui_status_message_with_reflection_or_direct_fallback')
    if callback is not None:
        try:
            callback(message, timeout_ms)
            return
        except TypeError:
            try:
                callback(message)
                return
            except Exception:
                pass
        except Exception:
            pass


def set_folder_batch_running_state_best_effort(
    main_window: object,
    running: bool,
    *,
    message: str | None = None,
    total: int = 1,
) -> None:
    """Reflect folder-batch running state in the existing bottom status strip."""

    try:
        setattr(main_window, '_folder_batch_running', bool(running))
        if running:
            setattr(main_window, '_folder_batch_cancel_requested', False)
    except Exception:
        pass

    # Disable the normal conversion button while the synchronous folder batch is
    # active.  Reuse the existing stop button as a cancel-request entry point.
    _set_widget_enabled(getattr(main_window, 'run_btn', None), not running)
    _set_widget_enabled(getattr(main_window, 'folder_batch_btn', None), not running)
    _set_widget_enabled(getattr(main_window, 'folder_batch_action', None), not running)
    _set_widget_enabled(getattr(main_window, 'stop_btn', None), running)
    if running:
        _set_widget_text(getattr(main_window, 'run_btn', None), '一括変換中…')
        _set_widget_text(getattr(main_window, 'busy_badge', None), '一括変換中')
        _set_progress_bar(getattr(main_window, 'progress_bar', None), 0, max(1, total))
        status_text = message or 'フォルダ一括変換中…'
        _set_widget_text(getattr(main_window, 'progress_label', None), status_text)
        append_log_best_effort(main_window, '[BATCH] フォルダ一括変換を開始しました。')
        show_status_best_effort(main_window, status_text, None)
    else:
        _set_widget_text(getattr(main_window, 'run_btn', None), '▶  変換実行')
        _set_widget_text(getattr(main_window, 'busy_badge', None), '待機中')
        status_text = message or 'フォルダ一括変換が終了しました。'
        _set_widget_text(getattr(main_window, 'progress_label', None), status_text)
        show_status_best_effort(main_window, status_text, 5000)
    process_gui_events_best_effort()


def request_folder_batch_cancel_best_effort(main_window: object) -> None:
    """Request cancellation for the currently running folder-batch conversion."""

    try:
        setattr(main_window, '_folder_batch_cancel_requested', True)
    except Exception:
        pass
    _set_widget_enabled(getattr(main_window, 'stop_btn', None), False)
    message = '停止要求を受け付けました。現在のファイルが終わりしだい、フォルダ一括変換を停止します。'
    append_log_best_effort(main_window, f'[STOP] {message}')
    _set_widget_text(getattr(main_window, 'progress_label', None), message)
    show_status_best_effort(main_window, message, 5000)
    process_gui_events_best_effort()


def should_cancel_folder_batch_from_mainwindow(main_window: object) -> bool:
    process_gui_events_best_effort()
    try:
        return bool(getattr(main_window, '_folder_batch_cancel_requested', False))
    except Exception:
        return False


def make_folder_batch_before_execute_callback(main_window: object) -> Callable[[FolderBatchPlan], None]:
    def _before(plan: FolderBatchPlan) -> None:
        total = max(1, int(getattr(plan, 'convert_count', 0) or 0))
        set_folder_batch_running_state_best_effort(
            main_window,
            True,
            message=format_folder_batch_progress_text(0, total),
            total=total,
        )
    return _before


def make_folder_batch_after_execute_callback(main_window: object) -> Callable[[object | None], None]:
    def _after(result: object | None) -> None:
        stopped = bool(getattr(result, 'stopped', False)) if result is not None else False
        failed_count = int(getattr(result, 'failed_count', 0) or 0) if result is not None else 0
        success_count = int(getattr(result, 'success_count', 0) or 0) if result is not None else 0
        skipped_count = int(getattr(result, 'skipped_count', 0) or 0) if result is not None else 0
        processed_count = int(getattr(result, 'processed_count', 0) or 0) if result is not None else 0
        total_count = int(getattr(getattr(result, 'plan', None), 'total_count', 1) or 1) if result is not None else 1
        _set_progress_bar(getattr(main_window, 'progress_bar', None), processed_count, max(1, total_count))
        if result is None:
            message = 'フォルダ一括変換を完了できませんでした。'
        else:
            pending_count = 0
            if stopped:
                try:
                    pending_count = int(getattr(result, 'stopped_pending_count', 0) or 0)
                except Exception:
                    pending_count = max(0, total_count - processed_count)
            count_text = (
                f'成功 {success_count} / スキップ {skipped_count} / 失敗 {failed_count} / '
                f'処理済み {processed_count}/{total_count}'
            )
            if stopped:
                message = f'フォルダ一括変換を停止しました。{count_text} / 未処理 {pending_count}'
            elif failed_count:
                message = f'フォルダ一括変換が完了しました。{count_text}'
            else:
                message = f'フォルダ一括変換が完了しました。{count_text}'
        set_folder_batch_running_state_best_effort(main_window, False, message=message, total=max(1, total_count))
        for name in (
            '_folder_batch_progress_index',
            '_folder_batch_progress_total',
            '_folder_batch_progress_item_text',
        ):
            try:
                setattr(main_window, name, None)
            except Exception:
                pass
        try:
            setattr(main_window, '_folder_batch_cancel_requested', False)
        except Exception:
            pass
    return _after


def make_folder_batch_progress_callback(main_window: object) -> FolderBatchProgressCallback:
    def _progress(index: int, total: int, item: FolderBatchPlanItem) -> None:
        try:
            total_value = max(1, int(total))
            current_value = max(0, min(int(index), total_value))
        except Exception:
            total_value = 1
            current_value = 0
        item_text = _relative_path_from_folder_batch_item(item)
        for name, value in (
            ('_folder_batch_progress_index', current_value),
            ('_folder_batch_progress_total', total_value),
            ('_folder_batch_progress_item_text', item_text),
        ):
            try:
                setattr(main_window, name, value)
            except Exception:
                pass
        text = format_folder_batch_progress_text(current_value, total_value, item)
        _set_progress_bar(getattr(main_window, 'progress_bar', None), current_value, total_value)
        _set_widget_text(getattr(main_window, 'progress_label', None), text)
        show_status_best_effort(main_window, text, None)
        process_gui_events_best_effort()
    return _progress


def make_folder_batch_inner_progress_callback(main_window: object) -> InnerProgressCallback:
    def _progress(index: int, total: int, text: str) -> None:
        detail_parts: list[str] = []
        try:
            inner_total = int(total)
            inner_index = int(index)
        except Exception:
            inner_total = 0
            inner_index = 0
        if inner_total > 1 and inner_index >= 0:
            detail_parts.append(f'内部 {inner_index}/{inner_total}')
        if text:
            detail_parts.append(str(text))
        detail = ' / '.join(part for part in detail_parts if part)
        current_index = getattr(main_window, '_folder_batch_progress_index', 0) or 0
        current_total = getattr(main_window, '_folder_batch_progress_total', 1) or 1
        current_item = getattr(main_window, '_folder_batch_progress_item_text', '') or ''
        if current_item or current_index:
            status_text = format_folder_batch_progress_text(
                int(current_index),
                int(current_total),
                current_item,
                detail=detail,
            )
        else:
            status_text = _compact_folder_batch_status_text(detail or text, max_chars=96)
        if status_text:
            _set_widget_text(getattr(main_window, 'progress_label', None), status_text)
            show_status_best_effort(main_window, status_text, None)
        process_gui_events_best_effort()
    return _progress


def output_format_from_mainwindow(main_window: object, default: str = 'xtc') -> str:
    """Read the current output format combo in a tolerant way."""

    combo = getattr(main_window, 'output_format_combo', None)
    for method_name in ('currentData', 'currentText'):
        method = getattr(combo, method_name, None)
        if not callable(method):
            continue
        try:
            value = str(method() or '').strip().lower().lstrip('.')
        except Exception:
            continue
        if value in {'xtc', 'xtch'}:
            return value
    return default


def folder_batch_suffixes_from_mainwindow(
    main_window: object,
    fallback: Iterable[str] = DEFAULT_FOLDER_BATCH_SUFFIXES,
) -> tuple[str, ...]:
    """Return supported suffixes from constants if available, with safe fallback.

    The v1.3.0 target includes at least text, EPUB, and common image formats.
    ``SUPPORTED_INPUT_SUFFIXES`` in the existing app may be narrower/wider; this
    helper merges both while preserving deterministic order.
    """

    candidates = list(fallback)
    existing = getattr(main_window, 'SUPPORTED_INPUT_SUFFIXES', None)
    if existing is None:
        # In the current project this constant is imported at module level rather
        # than stored on MainWindow, so also check the defining module via globals
        # when tests monkey-patch it onto the function module.
        existing = globals().get('SUPPORTED_INPUT_SUFFIXES', None)
    if existing is not None:
        try:
            candidates.extend(str(item) for item in existing)
        except Exception:
            pass
    return normalize_suffixes(candidates)


def open_folder_batch_dialog_for_mainwindow_with_converter(
    main_window: MainWindowLike,
    *,
    converter: FolderBatchConvertCallback,
    supported_suffixes: Iterable[str] | None = None,
    progress_cb: FolderBatchProgressCallback | None = None,
    should_cancel: FolderBatchCancelCallback | None = None,
    before_execute_cb: Callable[[FolderBatchPlan], None] | None = None,
    after_execute_cb: Callable[[object | None], None] | None = None,
) -> FolderBatchControllerRun | None:
    """Open the folder batch dialog using an already selected converter."""

    log_cb: LogCallback = lambda line: append_log_best_effort(main_window, line)
    actual_progress_cb = progress_cb or make_folder_batch_progress_callback(main_window)
    actual_should_cancel = should_cancel or (lambda: should_cancel_folder_batch_from_mainwindow(main_window))
    actual_before_execute_cb = before_execute_cb or make_folder_batch_before_execute_callback(main_window)
    actual_after_execute_cb = after_execute_cb or make_folder_batch_after_execute_callback(main_window)
    return open_folder_batch_dialog_and_execute(
        main_window,
        settings=getattr(main_window, 'settings_store', {}),
        converter=converter,
        output_format_getter=lambda: output_format_from_mainwindow(main_window),
        supported_suffixes=supported_suffixes or folder_batch_suffixes_from_mainwindow(main_window),
        log_cb=log_cb,
        progress_cb=actual_progress_cb,
        should_cancel=actual_should_cancel,
        before_execute_cb=actual_before_execute_cb,
        after_execute_cb=actual_after_execute_cb,
        information_cb=lambda title, body: folder_batch_completion_dialog_best_effort(main_window, title, body),
        warning_cb=lambda title, body: warning_dialog_best_effort(main_window, title, body),
    )


def open_folder_batch_dialog_for_mainwindow_dry_run(
    main_window: MainWindowLike,
    *,
    converter: FolderBatchConvertCallback | None = None,
    supported_suffixes: Iterable[str] | None = None,
    progress_cb: FolderBatchProgressCallback | None = None,
    should_cancel: FolderBatchCancelCallback | None = None,
) -> FolderBatchControllerRun | None:
    """Open the folder batch dialog from MainWindow using a dry-run converter.

    ``converter`` is kept as a compatibility escape hatch for older smoke tests.
    Production code should call ``open_folder_batch_dialog_for_mainwindow_with_converter``
    when a real converter has already been selected.
    """

    log_cb: LogCallback = lambda line: append_log_best_effort(main_window, line)
    actual_converter = converter or make_dry_run_converter(log_cb)
    return open_folder_batch_dialog_for_mainwindow_with_converter(
        main_window,
        converter=actual_converter,
        supported_suffixes=supported_suffixes,
        progress_cb=progress_cb,
        should_cancel=should_cancel,
    )


def open_folder_batch_dialog_for_mainwindow_real_or_warn(
    main_window: MainWindowLike,
    *,
    supported_suffixes: Iterable[str] | None = None,
    progress_cb: FolderBatchProgressCallback | None = None,
    should_cancel: FolderBatchCancelCallback | None = None,
    inner_progress_cb: InnerProgressCallback | None = None,
) -> FolderBatchControllerRun | None:
    """Open folder batch dialog using the real MainWindow conversion hook.

    v1.2.2.19 first prefers an explicit MainWindow conversion hook when one
    exists, then falls back to the worker bridge that collects current GUI
    settings and calls ``ConversionWorker._process_target`` with the planned
    output path.  If neither route is available, the user gets a warning instead
    of silently running dry-run output.
    """

    actual_inner_progress_cb = inner_progress_cb or make_folder_batch_inner_progress_callback(main_window)
    try:
        converter = build_mainwindow_converter_from_known_hook(main_window)
    except AttributeError as hook_exc:
        try:
            converter = make_mainwindow_worker_bridge_converter(
                main_window,
                inner_progress_cb=actual_inner_progress_cb,
                log_cb=lambda line: append_log_best_effort(main_window, line),
            )
        except AttributeError as settings_exc:
            warning_dialog_best_effort(
                main_window,
                'フォルダ一括変換',
                str(hook_exc) + '\n\n' + str(settings_exc),
            )
            return None
    return open_folder_batch_dialog_for_mainwindow_with_converter(
        main_window,
        converter=converter,
        supported_suffixes=supported_suffixes,
        progress_cb=progress_cb,
        should_cancel=should_cancel,
    )


def install_folder_batch_menu_action_best_effort(main_window: object) -> object | None:
    """Install a menu action as a safe first GUI entry point.

    This is deliberately less invasive than editing the crowded left pane.  The
    final GUI can still replace or supplement it with a proper
    ``[フォルダ一括変換...]`` button once the concrete release tree is available.
    """

    menu_bar_getter = _callable_attr(main_window, 'menuBar')
    opener = _callable_attr(main_window, '_open_folder_batch_dialog')
    if menu_bar_getter is None or opener is None:
        return None
    try:
        menu_bar = menu_bar_getter()
        action = menu_bar.addAction('フォルダ一括変換...')
        action.triggered.connect(opener)
        setattr(main_window, 'folder_batch_action', action)
        append_log_best_effort(main_window, 'フォルダ一括変換メニューを追加しました。')
        return action
    except Exception as exc:
        append_log_best_effort(main_window, f'フォルダ一括変換メニューの追加をスキップしました: {exc}')
        return None
