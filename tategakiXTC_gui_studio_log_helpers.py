from __future__ import annotations

"""Log-append and postprocess-warning fallback helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._append_log_without_status`` etc.), so instance-level overrides
installed by tests keep working.  This module intentionally does not import
PySide6 or ``tategakiXTC_gui_studio``.
"""

from typing import Any

import logging

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_results_controller as results_controller

from tategakiXTC_gui_studio_constants import LOG_TAB_INDEX
from tategakiXTC_gui_studio_ui_helpers import _coerce_ui_message_text

APP_LOGGER_NAME = 'tategaki_xtc'
APP_LOGGER = logging.getLogger(APP_LOGGER_NAME)


def _merge_results_summary_lines_with_warnings(
    window: Any,
    summary_lines: object,
    warning_values: object,
) -> list[object]:
    return worker_logic.merge_postprocess_warnings_into_summary_lines(
        summary_lines,
        warning_values,
    )


def _merge_results_summary_lines_and_collect_warnings(
    window: Any,
    summary_lines: object,
    collected_warnings: object,
    warning_values: object,
) -> tuple[object, list[str]]:
    merged_warnings = studio_logic.merge_unique_message_values(
        worker_logic.coerce_postprocess_warning_messages(collected_warnings),
        worker_logic.coerce_postprocess_warning_messages(warning_values),
    )
    if not merged_warnings:
        return summary_lines, []
    return (
        window._merge_results_summary_lines_with_warnings(summary_lines, merged_warnings),
        merged_warnings,
    )


def _build_results_summary_text(
    window: Any,
    paths: object,
    summary_lines: object = None,
    *,
    fallback: object = None,
) -> str:
    try:
        context = results_controller.build_results_apply_context(paths, summary_lines, language=window.current_ui_language_value())
        summary_text = _coerce_ui_message_text(context.get('summary_text')).strip()
        if summary_text:
            return summary_text
    except Exception:
        pass
    return _coerce_ui_message_text(fallback).strip()


def _append_conversion_finish_error_log_with_fallback(
    window: Any,
    log_message: object,
    *,
    status_timeout_ms: int = 5000,
) -> bool:
    helper_succeeded = False
    try:
        helper_succeeded = bool(
            window._append_log_without_status_with_optional_status_fallback(
                log_message,
                allow_status_fallback=False,
                status_timeout_ms=status_timeout_ms,
            )
        )
    except Exception:
        helper_succeeded = False
    if helper_succeeded:
        return True
    try:
        return bool(
            window._append_log_without_status_with_optional_status_fallback(
                log_message,
                allow_status_fallback=True,
                status_timeout_ms=status_timeout_ms,
            )
        )
    except Exception:
        return False


def _handle_conversion_finish_ui_error(
    window: Any,
    msg: str,
    exc: object,
    *,
    context: str,
    badge_text: str = '完了',
    clear_results: bool = False,
) -> bool:
    error_text = _coerce_ui_message_text(exc, str(exc)).strip() or '不明なエラー'
    APP_LOGGER.exception('変換完了後の %s でエラーが発生しました', context)
    log_message = f'{context}エラー: {error_text}'
    helper_succeeded = bool(
        window._append_conversion_finish_error_log_with_fallback(
            log_message,
            status_timeout_ms=5000,
        )
    )
    status_message = f'{msg} / {context}エラー: {error_text}'
    terminal_visible = False
    if clear_results:
        clear_summary_text = f'{msg}\n{context}エラー: {error_text}'
        clear_results_succeeded = False
        try:
            clear_results_succeeded = bool(window._clear_results_view(clear_summary_text))
        except Exception:
            clear_results_succeeded = False
        if not clear_results_succeeded:
            try:
                window._set_results_summary_text_with_fallback(clear_summary_text)
            except Exception:
                pass
        try:
            window._clear_loaded_xtc_state()
        except Exception:
            pass
        window._clear_results_selection_with_fallback({'clear_selection': True})
    terminal_visible = bool(
        window._apply_direct_conversion_terminal_fallback(
            msg,
            badge_text=badge_text,
            status_message=status_message,
            status_timeout=5000,
        )
    )
    if clear_results and hasattr(window, 'bottom_tabs'):
        try:
            window._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
        except Exception:
            pass
    return bool(helper_succeeded or terminal_visible)


def append_log(
    window: Any,
    text: str,
    *,
    reflect_in_status: bool = True,
) -> None:
    message_text = _coerce_ui_message_text(text)
    if not message_text:
        return
    try:
        APP_LOGGER.info(message_text)
    except Exception:
        pass
    try:
        log_widget = getattr(window, 'log_edit', None)
        if log_widget is not None and hasattr(log_widget, 'append'):
            log_widget.append(message_text)
    except Exception:
        pass
    try:
        visible_render_failure = bool(window._visible_render_failure_status_text())
    except Exception:
        visible_render_failure = False
    try:
        message_is_render_failure = window._is_render_failure_status_text(message_text)
    except Exception:
        message_is_render_failure = False
    preserve_visible_render_failure = visible_render_failure and not message_is_render_failure
    if (
        reflect_in_status
        and not getattr(window, 'worker', None)
        and not preserve_visible_render_failure
        and hasattr(window, 'progress_label')
    ):
        try:
            window.progress_label.setText(message_text)
        except Exception:
            pass
    if reflect_in_status and not preserve_visible_render_failure:
        if message_is_render_failure:
            window._show_ui_status_message_direct_with_reflection_best_effort(message_text, 5000)
        else:
            try:
                window._show_ui_status_message_with_reflection_or_direct_fallback(message_text, 5000)
            except Exception:
                pass



def open_log_folder(
    window: Any,
    *,
    resolve_log_dir_func: Any,
    log_dir: object,
    open_path_in_file_manager_func: Any,
) -> None:
    try:
        target_dir = resolve_log_dir_func()
    except Exception:
        target_dir = log_dir
    if open_path_in_file_manager_func(target_dir):
        return
    try:
        window._show_information_dialog_with_status_fallback(
            'ログフォルダ',
            str(target_dir),
            fallback_status_message=f'ログフォルダ: {target_dir}',
        )
    except Exception:
        try:
            window._show_ui_status_message_with_reflection_or_direct_fallback(f'ログフォルダ: {target_dir}', 5000)
        except Exception:
            pass

def _append_log_without_status(window: Any, text: object) -> bool:
    message = _coerce_ui_message_text(text)
    if not message:
        return False
    try:
        window.append_log(message, reflect_in_status=False)
        return True
    except TypeError:
        pass
    except Exception:
        pass
    try:
        APP_LOGGER.info(message)
    except Exception:
        pass
    try:
        if hasattr(window, 'log_edit'):
            window.log_edit.append(message)
            return True
    except Exception:
        pass
    try:
        log_widget = getattr(window, 'log_edit', None)
        if log_widget is not None and hasattr(log_widget, 'append'):
            log_widget.append(message)
            return True
    except Exception:
        pass
    return False


def _append_log_with_status_fallback(
    window: Any,
    text: object,
    *,
    reflect_in_status: bool = False,
    status_timeout_ms: int = 5000,
) -> bool:
    message = _coerce_ui_message_text(text)
    if not message:
        return False
    try:
        window.append_log(message, reflect_in_status=reflect_in_status)
        return True
    except TypeError:
        pass
    except Exception:
        pass
    append_log_succeeded = False
    try:
        append_log_succeeded = bool(window._append_log_without_status(message))
    except Exception:
        append_log_succeeded = False
        try:
            window.append_log(message, reflect_in_status=False)
            append_log_succeeded = True
        except TypeError:
            pass
        except Exception:
            pass
        if not append_log_succeeded:
            try:
                APP_LOGGER.info(message)
            except Exception:
                pass
            try:
                log_widget = getattr(window, 'log_edit', None)
                if log_widget is not None and hasattr(log_widget, 'append'):
                    log_widget.append(message)
                    append_log_succeeded = True
            except Exception:
                pass
    if reflect_in_status or not append_log_succeeded:
        try:
            if window._is_render_failure_status_text(message):
                if window._show_ui_status_message_direct_with_reflection_best_effort(message, status_timeout_ms):
                    return True
        except Exception:
            pass
        try:
            if window._show_ui_status_message_with_reflection_or_direct_fallback(message, status_timeout_ms):
                return True
        except Exception:
            pass
    return append_log_succeeded


def _append_log_without_status_best_effort(window: Any, text: object) -> bool:
    message = _coerce_ui_message_text(text)
    if not message:
        return False
    helper = getattr(window, '_append_log_with_status_fallback', None)
    if callable(helper):
        try:
            helper_result = helper(message, reflect_in_status=False)
            if helper_result is not False:
                return True
        except TypeError:
            try:
                helper_result = helper(message)
                if helper_result is not False:
                    return True
            except Exception:
                pass
        except Exception:
            pass
    fallback_helper = getattr(window, '_append_log_without_status', None)
    if callable(fallback_helper):
        try:
            if bool(fallback_helper(message)):
                return True
        except Exception:
            pass
    try:
        window.append_log(message, reflect_in_status=False)
        return True
    except TypeError:
        pass
    except Exception:
        pass
    try:
        APP_LOGGER.info(message)
    except Exception:
        pass
    try:
        log_widget = getattr(window, 'log_edit', None)
        if log_widget is not None and hasattr(log_widget, 'append'):
            log_widget.append(message)
            return True
    except Exception:
        pass
    return False


def _append_log_without_status_or_status_bar(
    window: Any,
    text: object,
    *,
    status_timeout_ms: int = 5000,
) -> bool:
    message = _coerce_ui_message_text(text)
    if not message:
        return False
    try:
        if window._append_log_without_status_best_effort(message):
            return True
    except Exception:
        pass
    try:
        if window._show_ui_status_message_with_reflection_or_direct_fallback(message, status_timeout_ms):
            return True
    except Exception:
        pass
    return False


def _append_log_without_status_with_optional_status_fallback(
    window: Any,
    log_message: object,
    *,
    allow_status_fallback: bool = False,
    status_timeout_ms: int = 5000,
) -> bool:
    message_text = _coerce_ui_message_text(log_message)
    if not message_text:
        return False
    try:
        if allow_status_fallback:
            return bool(
                window._append_log_without_status_or_status_bar(
                    message_text,
                    status_timeout_ms=status_timeout_ms,
                )
            )
        return bool(window._append_log_without_status_best_effort(message_text))
    except Exception:
        return False


def _emit_postprocess_warning(
    window: Any,
    warning_message: object,
    duration_ms: int = 5000,
    *,
    show_status: bool = True,
) -> bool:
    message = _coerce_ui_message_text(warning_message).strip()
    if not message:
        return False
    try:
        APP_LOGGER.warning('非致命後処理警告: %s', message)
    except Exception:
        pass
    helper_succeeded = False
    try:
        helper_succeeded = bool(window._append_log_without_status_best_effort(message))
    except Exception:
        helper_succeeded = False
    if show_status and not helper_succeeded:
        try:
            helper_succeeded = bool(
                window._append_log_without_status_or_status_bar(
                    message,
                    status_timeout_ms=duration_ms,
                )
            )
        except Exception:
            helper_succeeded = False
    if not show_status:
        return helper_succeeded
    status_succeeded = False
    try:
        status_succeeded = bool(
            window._show_ui_status_message_with_reflection_or_direct_fallback(
                message,
                duration_ms,
            )
        )
    except Exception:
        status_succeeded = False
    return bool(helper_succeeded or status_succeeded)


def _emit_postprocess_warning_via_log_and_optional_status_fallback(
    window: Any,
    warning_message: object,
    duration_ms: int = 5000,
    *,
    show_status: bool = True,
) -> bool:
    message_text = _coerce_ui_message_text(warning_message).strip()
    if not message_text:
        return False
    try:
        APP_LOGGER.warning('非致命後処理警告: %s', message_text)
    except Exception:
        pass
    log_succeeded = False
    try:
        log_succeeded = bool(window._append_log_without_status_best_effort(message_text))
    except Exception:
        log_succeeded = False
    helper_succeeded = log_succeeded
    if show_status and not log_succeeded:
        try:
            helper_succeeded = bool(
                window._append_log_without_status_or_status_bar(
                    message_text,
                    status_timeout_ms=duration_ms,
                )
            )
        except Exception:
            helper_succeeded = False
    if not show_status:
        return log_succeeded
    status_succeeded = False
    try:
        status_succeeded = bool(
            window._show_ui_status_message_with_reflection_or_direct_fallback(
                message_text,
                duration_ms,
            )
        )
    except Exception:
        status_succeeded = False
    return bool(log_succeeded or helper_succeeded or status_succeeded)


def _emit_postprocess_warnings_and_collect(
    window: Any,
    warning_values: object,
    duration_ms: int = 5000,
    *,
    show_status: bool = True,
) -> list[str]:
    emitted_messages: list[str] = []
    for message in worker_logic.coerce_postprocess_warning_messages(warning_values):
        emitted_here = False
        try:
            try:
                emitted_result = window._emit_postprocess_warning(
                    message,
                    duration_ms=duration_ms,
                    show_status=show_status,
                )
            except TypeError:
                if show_status:
                    emitted_result = window._emit_postprocess_warning(message, duration_ms=duration_ms)
                else:
                    raise
            emitted_here = emitted_result is not False
        except Exception:
            emitted_here = False
        if not emitted_here:
            emitted_here = bool(
                window._emit_postprocess_warning_via_log_and_optional_status_fallback(
                    message,
                    duration_ms=duration_ms,
                    show_status=show_status,
                )
            )
        if emitted_here:
            emitted_messages.append(message)
    return emitted_messages


def _emit_postprocess_warnings(
    window: Any,
    warning_values: object,
    duration_ms: int = 5000,
    *,
    show_status: bool = True,
) -> bool:
    return bool(
        window._emit_postprocess_warnings_and_collect(
            warning_values,
            duration_ms=duration_ms,
            show_status=show_status,
        )
    )


def _emit_unique_postprocess_warnings_with_fallback(
    window: Any,
    warning_values: object,
    emitted_messages: set[str] | None = None,
    duration_ms: int = 5000,
    *,
    show_status: bool = True,
) -> list[str]:
    normalized_warnings = worker_logic.coerce_postprocess_warning_messages(warning_values)
    if emitted_messages is None:
        emitted_messages = set()
    unique_warnings = [
        warning_message for warning_message in normalized_warnings
        if warning_message not in emitted_messages
    ]
    if not unique_warnings:
        return []

    emitted_now = window._emit_postprocess_warnings_and_collect(
        unique_warnings,
        duration_ms=duration_ms,
        show_status=show_status,
    )
    emitted_messages.update(emitted_now)
    return emitted_now


def _append_unique_postprocess_warnings_to_log_with_fallback(
    window: Any,
    warning_values: object,
    emitted_messages: set[str] | None = None,
    *,
    allow_status_fallback: bool = False,
    status_timeout_ms: int = 5000,
) -> list[str]:
    normalized_warnings = worker_logic.coerce_postprocess_warning_messages(warning_values)
    if emitted_messages is None:
        emitted_messages = set()
    appended_now: list[str] = []
    for warning_message in normalized_warnings:
        if warning_message in emitted_messages:
            continue
        try:
            APP_LOGGER.warning('非致命後処理警告: %s', warning_message)
        except Exception:
            pass
        appended_here = False
        try:
            appended_here = bool(
                window._append_log_without_status_with_optional_status_fallback(
                    warning_message,
                    allow_status_fallback=allow_status_fallback,
                    status_timeout_ms=status_timeout_ms,
                )
            )
        except Exception:
            appended_here = False
        if appended_here:
            appended_now.append(warning_message)
            emitted_messages.add(warning_message)
    return appended_now


def _emit_unique_postprocess_warnings_or_append_to_log(
    window: Any,
    warning_values: object,
    emitted_messages: set[str] | None = None,
    *,
    duration_ms: int = 5000,
    show_status: bool = True,
) -> list[str]:
    effective_emitted_messages = emitted_messages if emitted_messages is not None else set()
    emitted_now: list[str] = []
    try:
        emitted_now = window._emit_unique_postprocess_warnings_with_fallback(
            warning_values,
            effective_emitted_messages,
            duration_ms=duration_ms,
            show_status=show_status,
        )
    except Exception:
        emitted_now = []
    appended_now: list[str] = []
    try:
        appended_now = window._append_unique_postprocess_warnings_to_log_with_fallback(
            warning_values,
            effective_emitted_messages,
            allow_status_fallback=show_status,
            status_timeout_ms=duration_ms,
        )
    except Exception:
        appended_now = []
    combined_messages: list[str] = []
    seen_messages: set[str] = set()
    for warning_message in list(emitted_now) + list(appended_now):
        if warning_message in seen_messages:
            continue
        seen_messages.add(warning_message)
        combined_messages.append(warning_message)
    return combined_messages
