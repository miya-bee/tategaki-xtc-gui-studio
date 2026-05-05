from __future__ import annotations

"""Small MainWindow launcher helpers for folder batch conversion.

This module keeps the GUI wiring intentionally conservative.  It can be called
from ``MainWindow._open_folder_batch_dialog`` without editing the crowded layout
code.  Production wiring uses the worker bridge; the dry-run helper remains for
unit tests and smoke tests.
"""

from collections.abc import Iterable
from pathlib import Path
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
from tategakiXTC_folder_batch_plan import DEFAULT_FOLDER_BATCH_SUFFIXES, normalize_suffixes


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


def warning_dialog_best_effort(main_window: object, title: str, body: str) -> None:
    callback = _callable_attr(main_window, '_show_warning_dialog_with_status_fallback')
    if callback is not None:
        try:
            callback(title, body)
            return
        except Exception:
            pass
    append_log_best_effort(main_window, f'{title}: {body}')


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
) -> FolderBatchControllerRun | None:
    """Open the folder batch dialog using an already selected converter."""

    log_cb: LogCallback = lambda line: append_log_best_effort(main_window, line)
    return open_folder_batch_dialog_and_execute(
        main_window,
        settings=getattr(main_window, 'settings_store', {}),
        converter=converter,
        output_format_getter=lambda: output_format_from_mainwindow(main_window),
        supported_suffixes=supported_suffixes or folder_batch_suffixes_from_mainwindow(main_window),
        log_cb=log_cb,
        progress_cb=progress_cb,
        should_cancel=should_cancel,
        information_cb=lambda title, body: information_dialog_best_effort(main_window, title, body),
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

    try:
        converter = build_mainwindow_converter_from_known_hook(main_window)
    except AttributeError as hook_exc:
        try:
            converter = make_mainwindow_worker_bridge_converter(
                main_window,
                inner_progress_cb=inner_progress_cb,
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
