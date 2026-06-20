from __future__ import annotations

"""Runtime UI helpers for conversion start/stop/progress handling.

The functions in this module operate on ``MainWindow``-like objects.  Keeping
these defensive UI update paths outside the large entry module makes the
conversion runtime flow easier to audit while preserving the existing
``MainWindow`` method names as compatibility wrappers.
"""

import logging
from typing import Any

import tategakiXTC_gui_studio_logic as studio_logic
from tategakiXTC_gui_studio_constants import LOG_TAB_INDEX
from tategakiXTC_gui_studio_ui_helpers import (
    _coerce_ui_message_text,
    _safe_delete_qobject_later,
)
from tategakiXTC_gui_studio_worker import _coerce_progress_number

APP_LOGGER = logging.getLogger('tategaki_xtc')


def set_worker_controls_running(window: Any, running: bool) -> None:
    if hasattr(window, 'run_btn'):
        try:
            window.run_btn.setEnabled(not running)
        except Exception:
            pass
        try:
            window.run_btn.setText(window._ui_text('変換中…') if running else window._ui_text('▶  変換実行'))
        except Exception:
            pass
    for name in ('folder_batch_btn', 'folder_batch_action'):
        widget = getattr(window, name, None)
        setter = getattr(widget, 'setEnabled', None)
        if callable(setter):
            try:
                setter(not running)
            except Exception:
                pass
    if hasattr(window, 'stop_btn'):
        try:
            window.stop_btn.setEnabled(running)
        except Exception:
            pass


def prepare_conversion_ui_for_run(window: Any, settings: Any) -> None:
    try:
        window.__dict__['_conversion_stop_requested'] = False
    except Exception:
        pass
    try:
        window._hide_conversion_completion_card()
    except Exception:
        pass
    try:
        window._clear_results_view(studio_logic.build_running_results_summary(window.current_ui_language_value()))
    except Exception:
        pass
    try:
        window._clear_loaded_xtc_state()
    except Exception:
        pass
    window._set_worker_controls_running(True)
    target_count = len(window._supported_targets_for_path(str(settings.get('target', ''))))
    try:
        window._append_log_without_status_best_effort(
            studio_logic.build_start_log_message(window.current_output_format(), target_count, window.current_ui_language_value()),
        )
    except Exception:
        pass
    if hasattr(window, 'progress_bar'):
        try:
            window.progress_bar.setRange(0, 0)
            window.progress_bar.setValue(0)
        except Exception:
            pass
    if hasattr(window, 'progress_label'):
        try:
            window.progress_label.setText(window._ui_text('変換中…'))
        except Exception:
            pass
    if hasattr(window, 'busy_badge'):
        try:
            window.busy_badge.setText(window._ui_text('変換中'))
        except Exception:
            pass
    try:
        window._show_ui_status_message_with_reflection_or_direct_fallback(window._ui_text('変換中…'), None)
    except Exception:
        pass
    if hasattr(window, 'bottom_tabs'):
        try:
            window._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
        except Exception:
            pass


def apply_direct_conversion_terminal_fallback(
    window: Any,
    message: object,
    *,
    badge_text: object,
    status_message: object = None,
    status_timeout: int | None = None,
) -> bool:
    normalized_message = window._ui_text(_coerce_ui_message_text(message))
    normalized_badge_text = window._ui_text(_coerce_ui_message_text(badge_text))
    status_text = normalized_message if status_message is None else window._ui_text(_coerce_ui_message_text(status_message))
    terminal_visible = False
    if hasattr(window, 'progress_bar'):
        try:
            window.progress_bar.setRange(0, 1)
            window.progress_bar.setValue(0)
            terminal_visible = True
        except Exception:
            pass
    if hasattr(window, 'progress_label'):
        try:
            window.progress_label.setText(normalized_message)
            terminal_visible = True
        except Exception:
            pass
    if hasattr(window, 'busy_badge'):
        try:
            window.busy_badge.setText(normalized_badge_text)
            terminal_visible = True
        except Exception:
            pass
    status_visible = False
    try:
        if window._is_render_failure_status_text(status_text):
            status_visible = window._show_ui_status_message_direct_with_reflection_best_effort(
                status_text,
                status_timeout,
            )
        else:
            status_visible = bool(
                window._show_ui_status_message_with_reflection_or_direct_fallback(
                    status_text,
                    status_timeout,
                    reuse_existing_message=False,
                )
            )
    except Exception:
        status_visible = False
    if status_visible:
        terminal_visible = True
    return terminal_visible


def apply_conversion_terminal_state(
    window: Any,
    message: str,
    *,
    badge_text: str,
    status_message: str | None = None,
    status_timeout: int | None = None,
) -> None:
    window._apply_direct_conversion_terminal_fallback(
        message,
        badge_text=badge_text,
        status_message=status_message,
        status_timeout=status_timeout,
    )


def build_conversion_failure_summary_text(window: Any, prefix: object, message: object) -> str:
    return studio_logic.build_conversion_failure_summary_text(prefix, message, window.current_ui_language_value())


def apply_conversion_failure_ui(
    window: Any,
    summary_text: object,
    *,
    status_message: object,
    log_error_context: str,
    terminal_state_error_context: str,
    clear_results_error_context: str,
    clear_preview_error_context: str,
    progress_error_context: str,
    tab_error_context: str,
) -> None:
    clear_results_succeeded = False
    try:
        clear_results_succeeded = bool(window._clear_results_view(summary_text))
    except Exception:
        APP_LOGGER.exception(clear_results_error_context)
        clear_results_succeeded = False
    if not clear_results_succeeded:
        try:
            window._set_results_summary_text_with_fallback(summary_text)
        except Exception:
            pass
    try:
        window._clear_loaded_xtc_state()
    except Exception:
        APP_LOGGER.exception(clear_preview_error_context)
    try:
        window._clear_results_selection_with_fallback({'clear_selection': True})
    except Exception:
        APP_LOGGER.exception('%s_selection_direct', clear_results_error_context)
    if hasattr(window, 'progress_bar'):
        try:
            window.progress_bar.setRange(0, 1)
            window.progress_bar.setValue(0)
        except Exception:
            APP_LOGGER.exception(progress_error_context)
    try:
        window._append_log_without_status_or_status_bar(summary_text)
    except Exception:
        APP_LOGGER.exception(log_error_context)
    normalized_summary_text = _coerce_ui_message_text(summary_text)
    normalized_status_message = _coerce_ui_message_text(status_message, '不明なエラー')
    try:
        window._apply_conversion_terminal_state(
            normalized_summary_text,
            badge_text='エラー',
            status_message=normalized_status_message,
        )
    except Exception:
        APP_LOGGER.exception(terminal_state_error_context)
        window._apply_direct_conversion_terminal_fallback(
            normalized_summary_text,
            badge_text='エラー',
            status_message=normalized_status_message,
        )
    if hasattr(window, 'bottom_tabs'):
        try:
            window._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
        except Exception:
            APP_LOGGER.exception(tab_error_context)


def handle_conversion_startup_failure(window: Any, message: object) -> None:
    window._clear_active_conversion_run_token()
    message_text = _coerce_ui_message_text(message, '不明なエラー')
    APP_LOGGER.error('変換開始エラー: %s', message_text)
    if window.worker:
        _safe_delete_qobject_later(window.worker, context='変換開始エラー時の worker 解放')
        window.worker = None
    if window.worker_thread:
        _safe_delete_qobject_later(window.worker_thread, context='変換開始エラー時の thread 解放')
        window.worker_thread = None
    try:
        window._set_worker_controls_running(False)
    except Exception:
        APP_LOGGER.exception('変換開始エラー時の実行中UI解除に失敗しました')
    failure_summary_text = window._build_conversion_failure_summary_text('開始エラー', message_text)
    window._apply_conversion_failure_ui(
        failure_summary_text,
        status_message=message_text,
        log_error_context='変換開始エラー時のログ追記に失敗しました',
        terminal_state_error_context='変換開始エラー時の終端状態反映に失敗しました',
        clear_results_error_context='変換開始エラー時の結果表示クリアに失敗しました',
        clear_preview_error_context='変換開始エラー時の実機ビュー状態クリアに失敗しました',
        progress_error_context='変換開始エラー時の進捗バー更新に失敗しました',
        tab_error_context='変換開始エラー時のタブ切替に失敗しました',
    )
    try:
        window._show_critical_dialog_with_status_fallback(
            '変換開始エラー',
            message_text,
            fallback_status_message=message_text,
        )
    except Exception:
        APP_LOGGER.exception('変換開始エラーダイアログの表示に失敗しました')



def next_conversion_run_token(window: Any) -> int:
    try:
        current_token = int(window.__dict__.get('_conversion_run_token', 0) or 0)
    except Exception:
        current_token = 0
    token = current_token + 1
    window._conversion_run_token = token
    window._active_conversion_run_token = token
    return token


def clear_active_conversion_run_token(window: Any) -> None:
    window._active_conversion_run_token = 0


def is_active_conversion_run_token(window: Any, token: object) -> bool:
    try:
        token_value = int(token)
        active_token = int(window.__dict__.get('_active_conversion_run_token', 0) or 0)
    except Exception:
        return False
    return token_value == active_token


def connect_worker_dispatch_signals(
    window: Any,
    *,
    connect_signal_best_effort_func: Any,
) -> None:
    if bool(window.__dict__.get('_worker_dispatch_signals_connected', False)):
        return
    window._worker_dispatch_signals_connected = True
    connect_signal_best_effort_func(window._worker_finished_requested, window._dispatch_conversion_finished, queued=True)
    connect_signal_best_effort_func(window._worker_error_requested, window._dispatch_conversion_error, queued=True)
    connect_signal_best_effort_func(window._worker_log_requested, window._dispatch_worker_log, queued=True)
    connect_signal_best_effort_func(window._worker_progress_requested, window._dispatch_conversion_progress, queued=True)
    connect_signal_best_effort_func(window._worker_cleanup_requested, window._dispatch_worker_cleanup, queued=True)


def emit_worker_finished_request(window: Any, run_token: object, result: object) -> None:
    if not bool(window.__dict__.get('_worker_dispatch_signals_connected', False)):
        window._dispatch_conversion_finished(run_token, result)
        return
    try:
        window._worker_finished_requested.emit(run_token, result)
    except Exception:
        window._dispatch_conversion_finished(run_token, result)


def emit_worker_error_request(window: Any, run_token: object, message: object) -> None:
    if not bool(window.__dict__.get('_worker_dispatch_signals_connected', False)):
        window._dispatch_conversion_error(run_token, message)
        return
    try:
        window._worker_error_requested.emit(run_token, message)
    except Exception:
        window._dispatch_conversion_error(run_token, message)


def emit_worker_log_request(window: Any, run_token: object, text: object) -> None:
    if not bool(window.__dict__.get('_worker_dispatch_signals_connected', False)):
        window._dispatch_worker_log(run_token, text)
        return
    try:
        window._worker_log_requested.emit(run_token, text)
    except Exception:
        window._dispatch_worker_log(run_token, text)


def emit_worker_progress_request(window: Any, run_token: object, current: object, total: object, message: object) -> None:
    if not bool(window.__dict__.get('_worker_dispatch_signals_connected', False)):
        window._dispatch_conversion_progress(run_token, current, total, message)
        return
    try:
        window._worker_progress_requested.emit(run_token, current, total, message)
    except Exception:
        window._dispatch_conversion_progress(run_token, current, total, message)


def emit_worker_cleanup_request(window: Any, expected_worker: object = None, expected_thread: object = None) -> None:
    if not bool(window.__dict__.get('_worker_dispatch_signals_connected', False)):
        window.cleanup_worker(expected_worker=expected_worker, expected_thread=expected_thread)
        return
    try:
        window._worker_cleanup_requested.emit(expected_worker, expected_thread)
    except Exception:
        window.cleanup_worker(expected_worker=expected_worker, expected_thread=expected_thread)


def dispatch_worker_cleanup(window: Any, expected_worker: object = None, expected_thread: object = None) -> None:
    try:
        window.cleanup_worker(expected_worker=expected_worker, expected_thread=expected_thread)
    except Exception:
        APP_LOGGER.exception('worker後始末のUIスレッド反映に失敗しました')


def dispatch_worker_log(window: Any, run_token: object, text: object) -> None:
    if not window._is_active_conversion_run_token(run_token):
        return
    try:
        window._append_log_without_status_best_effort(window._ui_text(_coerce_ui_message_text(text, '').rstrip()))
    except Exception:
        APP_LOGGER.exception('workerログのUI反映に失敗しました')


def dispatch_conversion_progress(window: Any, run_token: object, current: object, total: object, message: object) -> None:
    if not window._is_active_conversion_run_token(run_token):
        return
    try:
        window.update_conversion_progress(current, total, message)
    except Exception:
        APP_LOGGER.exception('worker進捗のUI反映に失敗しました')


def dispatch_conversion_finished(window: Any, run_token: object, result: object) -> None:
    if not window._is_active_conversion_run_token(run_token):
        return
    try:
        window.on_conversion_finished(result)
    except Exception:
        APP_LOGGER.exception('worker完了シグナルのUI反映に失敗しました')


def dispatch_conversion_error(window: Any, run_token: object, message: object) -> None:
    if not window._is_active_conversion_run_token(run_token):
        return
    try:
        window.on_conversion_error(window._ui_text(_coerce_ui_message_text(message, '不明なエラー')))
    except Exception:
        APP_LOGGER.exception('workerエラーシグナルのUI反映に失敗しました')

def stop_conversion(window: Any) -> None:
    if bool(window.__dict__.get('_folder_batch_running', False)) and not window.worker:
        try:
            from tategakiXTC_folder_batch_mainwindow_launcher import (
                request_folder_batch_cancel_best_effort,
            )

            request_folder_batch_cancel_best_effort(window)
        except Exception:
            window.__dict__['_folder_batch_cancel_requested'] = True
            APP_LOGGER.exception('フォルダ一括変換の停止要求に失敗しました')
        return
    if not window.worker:
        return
    try:
        window.__dict__['_conversion_stop_requested'] = True
    except Exception:
        pass
    try:
        window.worker.stop()
    except Exception as exc:
        message_text = _coerce_ui_message_text(exc, str(exc)).strip() or '不明なエラー'
        APP_LOGGER.exception('停止要求の送信に失敗しました')
        log_message = f'停止要求の送信に失敗しました: {message_text}'
        helper_succeeded = False
        try:
            helper_succeeded = bool(window._append_log_without_status_best_effort(log_message))
        except Exception:
            helper_succeeded = False
        if not helper_succeeded:
            try:
                window._show_ui_status_message_with_reflection_or_direct_fallback(log_message, 5000)
            except Exception:
                pass
        return
    try:
        stop_btn = getattr(window, 'stop_btn', None)
        if stop_btn is not None:
            stop_btn.setEnabled(False)
    except Exception:
        APP_LOGGER.exception('停止ボタンの更新に失敗しました')
    log_message = '停止要求を送りました。現在の変換単位が終わりしだい停止します。'
    try:
        if hasattr(window, 'progress_bar'):
            window.progress_bar.setRange(0, 1)
            window.progress_bar.setValue(0)
        if hasattr(window, 'progress_label'):
            window.progress_label.setText(log_message)
        if hasattr(window, 'busy_badge'):
            window.busy_badge.setText(window._ui_text('停止中'))
        window._show_ui_status_message_with_reflection_or_direct_fallback(log_message, 5000)
    except Exception:
        APP_LOGGER.exception('停止要求後の進捗表示停止に失敗しました')
    helper_succeeded = False
    try:
        helper_succeeded = bool(window._append_log_without_status_best_effort(log_message))
    except Exception:
        helper_succeeded = False
    if not helper_succeeded:
        try:
            APP_LOGGER.warning('停止ログを通常ログへ追記できなかったため status helper にフォールバックします')
        except Exception:
            pass
        try:
            window._show_ui_status_message_with_reflection_or_direct_fallback(log_message, 5000)
        except Exception:
            pass


def start_conversion(
    window: Any,
    *,
    qthread_cls: Any,
    conversion_worker_cls: Any,
    safe_delete_qobject_later_func: Any = _safe_delete_qobject_later,
) -> None:
    cfg = window._prepare_conversion_settings()
    if not cfg:
        return
    if not window._check_conversion_dependencies(cfg):
        return
    window._prepare_conversion_ui_for_run(cfg)
    try:
        window._active_conversion_open_folder_target = window._planned_open_folder_target_from_settings(cfg)
    except Exception:
        window._active_conversion_open_folder_target = ''

    worker_thread = None
    worker = None
    run_token = window._next_conversion_run_token()
    try:
        worker_thread = qthread_cls(window)
        window.worker_thread = worker_thread
        worker = conversion_worker_cls(cfg)
        window.worker = worker
        worker.moveToThread(worker_thread)
        worker_thread.started.connect(worker.run)
        worker.finished.connect(lambda result, token=run_token: window._emit_worker_finished_request(token, result))
        worker.error.connect(lambda message, token=run_token: window._emit_worker_error_request(token, message))
        worker.log.connect(lambda text, token=run_token: window._emit_worker_log_request(token, text))
        worker.progress.connect(
            lambda current, total, message, token=run_token: window._emit_worker_progress_request(
                token,
                current,
                total,
                message,
            )
        )
        if hasattr(worker, 'deleteLater'):
            worker.finished.connect(worker.deleteLater)
            worker.error.connect(worker.deleteLater)
        worker.finished.connect(worker_thread.quit)
        worker.error.connect(worker_thread.quit)
        worker_thread.finished.connect(
            lambda worker_ref=worker, thread_ref=worker_thread: window._emit_worker_cleanup_request(
                worker_ref,
                thread_ref,
            )
        )
        worker_thread.start()
    except Exception as exc:
        if window.__dict__.get('worker_thread') is None and worker_thread is not None:
            safe_delete_qobject_later_func(worker_thread, context='変換開始失敗時の thread 解放')
        if window.__dict__.get('worker') is None and worker is not None:
            safe_delete_qobject_later_func(worker, context='変換開始失敗時の worker 解放')
        window._handle_conversion_startup_failure(str(exc))


def schedule_cleanup_worker(
    window: Any,
    *,
    qtimer_cls: Any,
    expected_worker: object = None,
    expected_thread: object = None,
) -> None:
    callback = window.cleanup_worker
    if expected_worker is not None or expected_thread is not None:
        callback = lambda worker=expected_worker, thread=expected_thread: window.cleanup_worker(
            expected_worker=worker,
            expected_thread=thread,
        )
    try:
        qtimer_cls.singleShot(0, callback)
    except Exception:
        callback()


def cleanup_worker(
    window: Any,
    *,
    expected_worker: object = None,
    expected_thread: object = None,
    safe_delete_qobject_later_func: Any = _safe_delete_qobject_later,
) -> None:
    active_worker = getattr(window, 'worker', None)
    active_thread = getattr(window, 'worker_thread', None)
    worker_ref = expected_worker if expected_worker is not None else active_worker
    thread_ref = expected_thread if expected_thread is not None else active_thread

    if expected_worker is None or active_worker is expected_worker:
        window.worker = None
    if expected_thread is None or active_thread is expected_thread:
        window.worker_thread = None

    # worker.finished で worker.deleteLater が既に予約済みのことがあるため、
    # 二重 deleteLater や破棄済み wrapper 参照で完了直後に落ちないよう安全化する。
    safe_delete_qobject_later_func(worker_ref, context='worker後始末')
    safe_delete_qobject_later_func(thread_ref, context='thread後始末')

    if getattr(window, 'worker', None) is None and getattr(window, 'worker_thread', None) is None:
        try:
            window._set_worker_controls_running(False)
        except Exception:
            APP_LOGGER.exception('worker後始末後のUI解除に失敗しました')



def handle_conversion_error(window: Any, message: object) -> None:
    window._clear_active_conversion_run_token()
    try:
        window._hide_conversion_completion_card()
    except Exception:
        pass
    message_text = _coerce_ui_message_text(message, '不明なエラー')
    APP_LOGGER.error('変換エラー: %s', message_text)
    try:
        window._show_critical_dialog_with_status_fallback(
            '変換エラー',
            message_text,
            fallback_status_message=message_text,
        )
    except Exception:
        APP_LOGGER.exception('変換エラーダイアログの表示に失敗しました')
    failure_summary_text = window._build_conversion_failure_summary_text('エラー', message_text)
    window._apply_conversion_failure_ui(
        failure_summary_text,
        status_message=message_text,
        log_error_context='変換エラー時のログ追記に失敗しました',
        terminal_state_error_context='変換エラー時の終端状態反映に失敗しました',
        clear_results_error_context='変換エラー時の結果表示クリアに失敗しました',
        clear_preview_error_context='変換エラー時の実機ビュー状態クリアに失敗しました',
        progress_error_context='変換エラー時の進捗バー更新に失敗しました',
        tab_error_context='変換エラー時のタブ切替に失敗しました',
    )
    try:
        window.__dict__['_conversion_stop_requested'] = False
    except Exception:
        pass

def update_conversion_progress(window: Any, current: int, total: int, message: str) -> None:
    stop_requested = False
    try:
        stop_requested = bool(window.__dict__.get('_conversion_stop_requested', False))
        worker_obj = getattr(window, 'worker', None)
        is_stop_requested = getattr(worker_obj, '_is_stop_requested', None)
        if callable(is_stop_requested):
            stop_requested = stop_requested or bool(is_stop_requested())
    except Exception:
        stop_requested = bool(window.__dict__.get('_conversion_stop_requested', False))
    if stop_requested:
        text = window._ui_text('停止要求を受け付けました。現在の変換単位が終わりしだい停止します。')
        if hasattr(window, 'progress_bar'):
            try:
                window.progress_bar.setRange(0, 1)
                window.progress_bar.setValue(0)
            except Exception:
                pass
        if hasattr(window, 'progress_label'):
            try:
                window.progress_label.setText(text)
            except Exception:
                pass
        if hasattr(window, 'busy_badge'):
            try:
                window.busy_badge.setText(window._ui_text('停止中'))
            except Exception:
                pass
        try:
            window._show_ui_status_message_with_reflection_or_direct_fallback(text, 5000)
        except Exception:
            pass
        return
    total_value = max(1, _coerce_progress_number(total, 1))
    current_value = max(0, min(_coerce_progress_number(current, 0), total_value))
    text = window._progress_status_text(current_value, total_value, message)
    if hasattr(window, 'progress_bar'):
        try:
            window.progress_bar.setRange(0, 0)
            window.progress_bar.setValue(0)
        except Exception:
            pass
    try:
        visible_render_failure = bool(window._visible_render_failure_status_text())
    except Exception:
        visible_render_failure = False
    if hasattr(window, 'progress_label') and not visible_render_failure:
        try:
            window.progress_label.setText(text)
        except Exception:
            pass
    if not visible_render_failure:
        try:
            window._show_ui_status_message_with_reflection_or_direct_fallback(text, None)
        except Exception:
            pass
