from __future__ import annotations

"""Conversion-finish orchestration helpers for :mod:`tategakiXTC_gui_studio`.

The GUI entry module keeps the public ``MainWindow.on_conversion_finished``
method, while the detailed result-view/log/status fallback flow lives here.
This module intentionally works against the existing MainWindow-compatible
object surface so signal wiring and tests can continue to call the original
method name.
"""

import logging
import sys
from typing import Any

import tategakiXTC_gui_results_controller as results_controller
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_worker_logic as worker_logic
from tategakiXTC_gui_studio_constants import LOG_TAB_INDEX, RESULT_TAB_INDEX
from tategakiXTC_gui_studio_ui_helpers import _coerce_ui_message_text


APP_LOGGER = logging.getLogger('tategaki_xtc')



def build_conversion_completion_summary_lines(
    window: Any,
    converted_files: Any,
    summary_lines: Any,
    result: dict[str, object] | None = None,
) -> list[str]:
    base_lines = results_controller.coerce_summary_line_list(summary_lines)
    payload = result or {}
    guidance_lines = results_controller.build_conversion_completion_guidance_lines(
        converted_files,
        open_folder_target=payload.get('open_folder_target', ''),
        stopped=payload.get('stopped', False),
        language=window.current_ui_language_value(),
    )
    return studio_logic.merge_unique_message_values(base_lines, guidance_lines)


def apply_conversion_completion_guidance_to_results_view(
    window: Any,
    converted_files: Any,
    summary_lines: Any,
    result: dict[str, object] | None = None,
) -> bool:
    if not hasattr(window, 'results_summary_label'):
        return False
    enriched_lines = window._build_conversion_completion_summary_lines(
        converted_files,
        summary_lines,
        result,
    )
    base_lines = results_controller.coerce_summary_line_list(summary_lines)
    if enriched_lines == base_lines:
        return False
    entry_count = len(results_controller.coerce_result_path_list(converted_files))
    summary_text = results_controller.build_completion_summary_text(
        enriched_lines,
        entry_count,
        language=window.current_ui_language_value(),
    )
    updated = bool(window._set_results_summary_text_with_fallback(summary_text))
    try:
        window._sync_results_action_buttons_state()
    except Exception:
        pass
    return updated


def _entry_mainwindow_method(helper_name: str) -> Any:
    module = sys.modules.get('tategakiXTC_gui_studio')
    main_window = getattr(module, 'MainWindow', None) if module is not None else None
    return getattr(main_window, helper_name, None)


def _ensure_finish_helpers(self: Any, helper_names: tuple[str, ...]) -> None:
    for helper_name in helper_names:
        if hasattr(self, helper_name):
            continue
        helper = getattr(type(self), helper_name, None)
        if not callable(helper):
            helper = _entry_mainwindow_method(helper_name)
        if callable(helper):
            try:
                setattr(self, helper_name, helper.__get__(self, type(self)))
            except Exception:
                pass


def _finished_folder_warnings(self: Any, result: dict[str, object]) -> list[str]:
    opener = getattr(self, '_open_finished_conversion_folder', None)
    if not callable(opener):
        return []
    try:
        return worker_logic.coerce_postprocess_warning_messages(opener(result))
    except Exception as exc:
        APP_LOGGER.exception('螟画鋤螳御ｺ・ｾ後・繝輔か繝ｫ繝蜃ｦ逅・↓螟ｱ謨励＠縺ｾ縺励◆')
        return worker_logic.coerce_postprocess_warning_messages(f'螟画鋤螳御ｺ・ｾ後蜃ｦ逅・お繝ｩ繝ｼ: {exc}')


def handle_conversion_finished(window: Any, result: dict[str, object]) -> None:
    """Handle a worker completion payload for an existing MainWindow object."""
    self = window
    self._clear_active_conversion_run_token()
    msg = worker_logic._str_config_value(result, 'message', '変換完了しました。').strip() or '変換完了しました。'
    _ensure_finish_helpers(self, (
        '_open_finished_conversion_folder',
        '_merge_results_summary_lines_with_warnings',
        '_merge_results_summary_lines_and_collect_warnings',
        '_append_log_without_status_best_effort',
        '_append_log_without_status_or_status_bar',
        '_append_log_without_status_with_optional_status_fallback',
        '_emit_postprocess_warning_via_log_and_optional_status_fallback',
        '_emit_postprocess_warnings_and_collect',
        '_emit_unique_postprocess_warnings_with_fallback',
        '_append_unique_postprocess_warnings_to_log_with_fallback',
        '_emit_unique_postprocess_warnings_or_append_to_log',
        '_build_results_summary_text',
        '_build_conversion_completion_summary_lines',
        '_apply_conversion_completion_guidance_to_results_view',
        '_coerce_mapping_payload',
        '_clear_results_selection_with_fallback',
        '_ui_widget_index',
        '_set_bottom_tab_index_with_fallback',
        '_set_results_summary_text_with_fallback',
        '_show_ui_status_message_with_reflection_or_direct_fallback',
    ))
    stopped = worker_logic._bool_config_value(result, 'stopped', False)
    converted_files = results_controller.coerce_result_path_list(result.get('converted_files'))
    try:
        self._last_conversion_open_folder_target = self._resolve_conversion_open_folder_target(
            converted_files,
            result,
        )
    except Exception:
        self._last_conversion_open_folder_target = ''
    postprocess_warnings = worker_logic.coerce_postprocess_warning_messages(
        result.get('postprocess_warnings')
    )
    postprocess_warnings = worker_logic.coerce_postprocess_warning_messages(
        list(postprocess_warnings) + _finished_folder_warnings(self, result)
    )
    terminal_state_fallback_warnings: list[str] = []

    emitted_postprocess_warnings: set[str] = set()

    try:
        self._apply_conversion_terminal_state(msg, badge_text='停止' if stopped else '完了')
    except Exception as exc:
        finish_error_visible = bool(
            self._handle_conversion_finish_ui_error(
                msg,
                exc,
                context='完了表示',
                badge_text='停止' if stopped else '完了',
                clear_results=False,
            )
        )
        if not finish_error_visible:
            finish_error_text = _coerce_ui_message_text(exc, str(exc)).strip() or '不明なエラー'
            terminal_state_fallback_warnings = worker_logic.coerce_postprocess_warning_messages(
                f'完了表示エラー: {finish_error_text}'
            )
    if stopped and not converted_files:
        try:
            result.setdefault('show_without_paths', True)
            result.setdefault('completion_title', '変換を中止しました')
        except Exception:
            pass
    summary_lines = result.get('summary_lines')
    show_postprocess_warning_status = not stopped
    summary_lines, final_postprocess_warnings = self._merge_results_summary_lines_and_collect_warnings(
        summary_lines,
        terminal_state_fallback_warnings,
        postprocess_warnings,
    )
    try:
        self._show_conversion_results(converted_files, summary_lines)
        try:
            self._apply_conversion_completion_guidance_to_results_view(
                converted_files,
                summary_lines,
                result,
            )
        except Exception:
            APP_LOGGER.exception('変換完了後の確認導線表示に失敗しました')
        try:
            self._show_conversion_completion_card(converted_files, result)
        except Exception:
            APP_LOGGER.exception('変換完了カード表示に失敗しました')
        if hasattr(self, 'bottom_tabs'):
            try:
                if stopped and not converted_files:
                    self._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
                elif self._ui_widget_index(self.bottom_tabs) is None:
                    self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX)
            except Exception:
                pass
    except Exception as exc:
        try:
            status_message = self._render_failure_status_message('変換結果表示エラー', exc)
        except Exception as render_exc:
            status_message = f'変換結果表示エラー: {_coerce_ui_message_text(render_exc, str(render_exc)).strip() or _coerce_ui_message_text(exc, str(exc)).strip() or "不明なエラー"}'
        fallback_warnings = worker_logic.coerce_postprocess_warning_messages(status_message)
        if fallback_warnings:
            summary_lines, final_postprocess_warnings = self._merge_results_summary_lines_and_collect_warnings(
                summary_lines,
                final_postprocess_warnings,
                fallback_warnings,
            )
            self._emit_unique_postprocess_warnings_or_append_to_log(
                fallback_warnings,
                emitted_postprocess_warnings,
                duration_ms=5000,
                show_status=show_postprocess_warning_status,
            )
        else:
            try:
                self._append_log_without_status_with_optional_status_fallback(status_message)
            except Exception:
                pass
            if show_postprocess_warning_status:
                try:
                    self._show_ui_status_message_with_reflection_or_direct_fallback(status_message, 5000)
                except Exception:
                    pass
        fallback_summary_text = _coerce_ui_message_text(status_message).strip()
        fallback_results_visible = False
        try:
            self.populate_results(converted_files, summary_lines)
            fallback_results_visible = not hasattr(self, 'results_list')
        except Exception:
            try:
                fallback_summary_text = self._build_results_summary_text(
                    converted_files,
                    summary_lines,
                    fallback=status_message,
                )
            except Exception:
                fallback_summary_text = _coerce_ui_message_text(status_message).strip()
            try:
                clear_results_succeeded = bool(self._clear_results_view(fallback_summary_text))
            except Exception:
                clear_results_succeeded = False
            if not clear_results_succeeded:
                try:
                    self._set_results_summary_text_with_fallback(fallback_summary_text)
                except Exception:
                    pass
        try:
            self._clear_loaded_xtc_state()
        except Exception:
            pass
        selection_cleared = False
        self._clear_results_selection_with_fallback({'clear_selection': True})
        if hasattr(self, 'bottom_tabs'):
            try:
                self._set_bottom_tab_index_with_fallback(
                    RESULT_TAB_INDEX if fallback_results_visible else LOG_TAB_INDEX
                )
            except Exception:
                pass
    self._emit_unique_postprocess_warnings_or_append_to_log(
        final_postprocess_warnings,
        emitted_postprocess_warnings,
        duration_ms=5000,
        show_status=show_postprocess_warning_status,
    )
    try:
        self.__dict__['_conversion_stop_requested'] = False
    except Exception:
        pass
