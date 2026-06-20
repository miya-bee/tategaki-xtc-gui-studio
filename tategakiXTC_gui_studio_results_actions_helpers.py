from __future__ import annotations

"""Result action and XTC-load flow helpers for TategakiXTC GUI Studio.

The entry module keeps the public ``MainWindow`` method names as thin wrappers.
These helpers receive the window object and call back through ``self`` so
instance-level monkeypatches used by tests remain effective.
"""

from pathlib import Path
import logging
import ntpath
import sys
from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QMessageBox

import tategakiXTC_gui_results_controller as results_controller
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_worker_logic as worker_logic
from tategakiXTC_gui_studio_constants import LOG_TAB_INDEX, RESULT_TAB_INDEX
from tategakiXTC_gui_studio_ui_helpers import _coerce_ui_message_text

APP_LOGGER_NAME = 'tategaki_xtc'
APP_LOGGER = logging.getLogger(APP_LOGGER_NAME)



def _studio_attr(name: str, default: Any = None) -> Any:
    studio_module = sys.modules.get('tategakiXTC_gui_studio')
    if studio_module is None:
        return default
    return getattr(studio_module, name, default)


def _list_widget_item(text: object) -> Any:
    item_cls = _studio_attr('QListWidgetItem', QListWidgetItem)
    return item_cls(text)


def _open_path_in_file_manager_runtime(path: object) -> bool:
    opener = _studio_attr('_open_path_in_file_manager')
    if not callable(opener):
        from tategakiXTC_gui_studio_desktop import _open_path_in_file_manager as opener
    return bool(opener(path))


def _message_box_dialog(level: object) -> Any:
    message_box_cls = _studio_attr('QMessageBox', QMessageBox)
    return getattr(message_box_cls, str(level), None)


def _load_xtc_from_path_with_result(self: Any, path: object) -> bool:
    def _report_load_failure(exc: Exception) -> None:
        try:
            self._restore_results_selection_after_xtc_load_failure()
        except Exception:
            pass
        try:
            status_message = self._xtc_load_failure_status_message(path, exc)
        except Exception:
            target = worker_logic._normalized_path_text(path).strip() or '指定ファイル'
            detail = worker_logic._normalized_path_text(exc).strip() or '不明なエラー'
            status_message = f'XTC/XTCH読込失敗: {target} / {detail}'
        reflect_failure_in_status = True
        try:
            reflect_failure_in_status = not self._visible_render_failure_status_text()
        except Exception:
            reflect_failure_in_status = True
        try:
            self._append_log_with_status_fallback(
                status_message,
                reflect_in_status=reflect_failure_in_status,
            )
        except Exception:
            if reflect_failure_in_status:
                try:
                    self._show_ui_status_message_with_reflection_or_direct_fallback(status_message, 5000)
                except Exception:
                    pass

    loader = getattr(self, 'load_xtc_from_path', None)
    if not callable(loader):
        _report_load_failure(RuntimeError('読込処理を開始できませんでした。'))
        return False
    try:
        result = loader(path)
    except Exception as exc:
        _report_load_failure(exc)
        return False
    return result is not False


def _show_conversion_results(
    self: Any,
    converted_files: list[object],
    summary_lines: list[str] | None = None,
) -> None:
    self.populate_results(converted_files, summary_lines)
    context = self._resolved_result_load_context()
    resolved_path = context.get('resolved_path') if self._payload_bool_value(context, 'has_path', False) else None
    if not worker_logic._normalized_path_text(resolved_path).strip():
        fallback_state = results_controller.build_results_view_state(converted_files, summary_lines, language=self.current_ui_language_value())
        entries = list(fallback_state.get('entries', []))
        initial_index = studio_logic.payload_optional_int_value(fallback_state, 'initial_index')
        if initial_index is not None and 0 <= initial_index < len(entries):
            resolved_path = entries[initial_index][1]
        elif entries:
            resolved_path = entries[0][1]
    result_tab_index = RESULT_TAB_INDEX
    if worker_logic._normalized_path_text(resolved_path).strip():
        if not self._load_xtc_from_path_with_result(resolved_path):
            result_tab_index = LOG_TAB_INDEX
    else:
        try:
            self._clear_loaded_xtc_state()
        except Exception:
            APP_LOGGER.exception('結果プレビュー状態クリアに失敗しました')
        selection_cleared = False
        self._clear_results_selection_with_fallback({'clear_selection': True})
    if hasattr(self, 'bottom_tabs'):
        try:
            self._set_bottom_tab_index_with_fallback(result_tab_index)
        except Exception:
            APP_LOGGER.exception('結果タブ切替に失敗しました')


def _preferred_result_path_for_action(self: Any) -> str:
    context = self._resolved_result_load_context()
    path = worker_logic._normalized_path_text(context.get('resolved_path')).strip()
    if path:
        return path
    item = self._result_item_at(0)
    return worker_logic._normalized_path_text(self._results_item_path(item)).strip() if item is not None else ''


def open_results_folder_from_results(self: Any) -> None:
    folder_override = ''
    for candidate in (
        self.__dict__.get('_last_conversion_open_folder_target', ''),
        self.__dict__.get('_completion_card_open_folder_target', ''),
        self.__dict__.get('_active_conversion_open_folder_target', ''),
    ):
        folder_override = self._meaningful_open_folder_target_text(candidate)
        if folder_override:
            break
    if folder_override:
        if _open_path_in_file_manager_runtime(folder_override):
            return
        self._show_result_load_dialog_with_status_fallback('warning', '保存先', f'保存先を開けませんでした。\n{folder_override}')
        return

    path = self._preferred_result_path_for_action()
    if not path:
        self._show_result_load_dialog_with_status_fallback('information', '保存先', '開ける変換結果がありません。')
        return
    try:
        if worker_logic._is_windows_like_path(path):
            folder = ntpath.dirname(ntpath.normpath(path))
        else:
            folder = str(Path(path).parent)
    except Exception:
        folder = ''
    # _meaningful_open_folder_target_text と同じ基準でフォルダを
    # 検証する。これにより ``'./'``/``'.\\'``/``'..'`` 等の相対
    # 表記が ``os.startfile`` に届いてアプリのある cwd を開いて
    # しまう不具合を、フォールバック経路でも防ぐ。
    target = self._meaningful_open_folder_target_text(folder)
    if not target:
        self._show_result_load_dialog_with_status_fallback('warning', '保存先', f'保存先フォルダを特定できませんでした。\n{path}')
        return
    if _open_path_in_file_manager_runtime(target):
        return
    self._show_result_load_dialog_with_status_fallback('warning', '保存先', f'保存先を開けませんでした。\n{target}')


def open_selected_result_from_results(self: Any) -> None:
    item = self._resolved_results_item_for_loading() or self._result_item_at(0)
    if item is None:
        self._show_result_load_dialog_with_status_fallback('information', '右ペイン', '確認できる変換結果がありません。')
        return
    self.on_result_item_clicked(item)


def _result_display_name(self: Any, path_text: str) -> str:
    return studio_logic.build_result_display_name(path_text)


def _normalized_result_entries(self: Any, paths: list[object]) -> list[tuple[str, str]]:
    return results_controller.build_results_entries(paths)


def _apply_results_entries_to_ui(
    self: Any,
    entries: list[tuple[str, str]],
    summary_text: object = None,
    initial_index: object = None,
) -> None:
    self._clear_results_view()
    if hasattr(self, 'results_summary_label'):
        normalized_summary = _coerce_ui_message_text(summary_text)
        if normalized_summary:
            self._set_results_summary_text_with_fallback(normalized_summary)
    if not hasattr(self, 'results_list'):
        return
    for display_name, raw in entries:
        item = _list_widget_item(display_name)
        item.setData(Qt.UserRole, raw)
        self.results_list.addItem(item)
    try:
        self._sync_results_action_buttons_state()
    except Exception:
        pass
    try:
        self._bind_bottom_panel_external_scrollbar()
    except Exception:
        pass
    try:
        normalized_index = int(initial_index)
    except Exception:
        normalized_index = None
    if normalized_index is not None:
        self._set_results_current_index_with_fallback(normalized_index)


def populate_results(self: Any, paths: list[object], summary_lines: list[str] | None = None) -> None:
    context = results_controller.build_results_apply_context(paths, summary_lines, language=self.current_ui_language_value())
    self._apply_results_entries_to_ui(
        context.get('entries', []),
        context.get('summary_text', ''),
        context.get('initial_index'),
    )
    remembered_path = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_path_text')).strip()
    if not remembered_path or self._result_item_count() <= 0:
        return
    selection_context = results_controller.build_results_selection_context(
        remembered_path,
        self._result_item_paths(),
    )
    if studio_logic.payload_optional_int_value(selection_context, 'matched_index') is None:
        return
    self._apply_results_selection_context_with_fallback(selection_context)


def on_result_item_clicked(self: Any, item: QListWidgetItem) -> None:
    def _load_result_path_with_tab_fallback(path_value: object) -> None:
        load_succeeded = self._load_xtc_from_path_with_result(path_value)
        if hasattr(self, 'bottom_tabs'):
            try:
                self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX if load_succeeded else LOG_TAB_INDEX)
            except Exception:
                APP_LOGGER.exception('結果項目クリック時のタブ切替に失敗しました')

    path = worker_logic._normalized_path_text(self._results_item_path(item)).strip()
    if path:
        matched_index = results_controller.find_matching_loaded_path_index(path, self._result_item_paths())
        if matched_index is not None:
            self._apply_results_selection_context_with_fallback({'matched_index': matched_index, 'clear_selection': False})
            _load_result_path_with_tab_fallback(path)
            return
        if self._result_item_count() <= 0:
            _load_result_path_with_tab_fallback(path)
            return
    resolved_context = self._resolved_result_load_context()
    resolved_path = worker_logic._normalized_path_text(resolved_context.get('resolved_path')).strip()
    preferred_index = studio_logic.payload_optional_int_value(resolved_context, 'preferred_index')
    if resolved_path and self._payload_bool_value(resolved_context, 'has_path', False) and preferred_index is not None:
        self._apply_results_selection_context_with_fallback({'matched_index': preferred_index, 'clear_selection': False})
        _load_result_path_with_tab_fallback(resolved_path)
        return
    remembered_path = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_path_text')).strip()
    try:
        if remembered_path:
            self._sync_results_selection_for_loaded_path_with_fallback(remembered_path)
        else:
            self._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
    except Exception:
        pass
    try:
        self._sync_active_display_context_for_visible_page()
    except Exception:
        pass
    self._show_result_load_dialog_with_status_fallback(
        'warning',
        '右ペイン',
        '選択した項目のファイルパスを取得できませんでした。',
    )



def _results_item_path(self: Any, item: object) -> object:
    data = getattr(item, 'data', None)
    if callable(data):
        try:
            return data(Qt.UserRole)
        except Exception:
            return None
    return None

def _show_result_load_dialog_with_status_fallback(
    self: Any,
    level: str,
    title: str,
    message: str,
) -> None:
    dialog = _message_box_dialog(level)
    if callable(dialog):
        try:
            dialog(self, title, message)
            return
        except Exception:
            pass
    try:
        self._show_ui_status_message_with_reflection_or_direct_fallback(
            message,
            5000,
            reuse_existing_message=False,
        )
    except Exception:
        pass


def load_selected_result(self: Any) -> None:
    context = self._resolved_result_load_context()
    preferred_index = studio_logic.payload_optional_int_value(context, 'preferred_index')
    if self._payload_bool_value(context, 'should_warn_no_selection', False) or preferred_index is None:
        try:
            self._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        self._show_result_load_dialog_with_status_fallback('information', '右ペイン', '表示する変換結果を選択してください。')
        return
    effective_context = dict(context)
    effective_index = preferred_index
    if self._payload_bool_value(context, 'should_warn_missing_path', False) or not self._payload_bool_value(context, 'has_path', False):
        fallback_context = self._fallback_loaded_result_load_context()
        fallback_index = studio_logic.payload_optional_int_value(fallback_context, 'preferred_index')
        if fallback_index is not None and self._payload_bool_value(fallback_context, 'has_path', False):
            effective_context = fallback_context
            effective_index = fallback_index
        else:
            try:
                self._sync_active_display_context_for_visible_page()
            except Exception:
                pass
            self._show_result_load_dialog_with_status_fallback('warning', '右ペイン', '選択した項目のファイルパスを取得できませんでした。')
            return
    path = effective_context.get('resolved_path')
    if not self._payload_bool_value(effective_context, 'has_path', False):
        try:
            self._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        self._show_result_load_dialog_with_status_fallback('warning', '右ペイン', '選択した項目のファイルパスを取得できませんでした。')
        return
    self._apply_results_selection_context_with_fallback({'matched_index': effective_index, 'clear_selection': False})
    load_succeeded = self._load_xtc_from_path_with_result(path)
    if hasattr(self, 'bottom_tabs'):
        try:
            self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX if load_succeeded else LOG_TAB_INDEX)
        except Exception:
            APP_LOGGER.exception('結果選択読込時のタブ切替に失敗しました')


def _apply_loaded_xtc_ui_context(self: Any, context: Mapping[str, object] | object) -> None:
    context = self._coerce_mapping_payload(context)
    if self._payload_bool_value(context, 'clear_loaded_state', False):
        self._clear_loaded_xtc_state()
    device_view_source = self._normalized_device_view_source_value(
        context.get('device_view_source'),
        default='',
    )
    if device_view_source:
        self.device_view_source = device_view_source
    selection_context = context.get('selection_context')
    if isinstance(selection_context, Mapping):
        self._apply_results_selection_context_with_fallback(selection_context)
    log_message = worker_logic._normalized_path_text(context.get('log_message')).strip()
    if log_message:
        try:
            self._append_log_without_status_or_status_bar(log_message)
        except Exception:
            pass
    if 'path_text' in context:
        normalized_path_text = worker_logic._normalized_path_text(context.get('path_text')).strip()
        self._loaded_xtc_path_text = normalized_path_text or None
    if 'display_name' in context:
        display_name = context.get('display_name')
        normalized_display_name = worker_logic._normalized_path_text(display_name).strip()
        self._loaded_xtc_display_name = normalized_display_name or None
        self._set_current_xtc_display_name(display_name)
    self._apply_loaded_xtc_view_mode(
        context.get('view_mode'),
        safe=self._payload_bool_value(context, 'safe_view_mode', False),
    )
