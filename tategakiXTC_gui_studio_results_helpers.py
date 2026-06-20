from __future__ import annotations

"""Results-view summary and selection fallback helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._clear_results_selection_state`` etc.), so instance-level overrides
installed by tests keep working.  This module intentionally does not import
PySide6 or ``tategakiXTC_gui_studio``; Qt-bound pieces such as
``_results_item_path`` (``Qt.UserRole``) stay in the entry module and are
reached through ``window``.
"""

from typing import Any

from collections.abc import Mapping
import logging

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_results_controller as results_controller

from tategakiXTC_gui_studio_ui_helpers import _coerce_ui_message_text

APP_LOGGER_NAME = 'tategaki_xtc'
APP_LOGGER = logging.getLogger(APP_LOGGER_NAME)


def _set_results_summary_text_fallback(
    window: Any,
    summary_text: object = None,
    *,
    default_text: str = '保存されたファイルはありません。',
) -> bool:
    if not hasattr(window, 'results_summary_label'):
        return False
    text = _coerce_ui_message_text(summary_text)
    visible_text = text or default_text
    try:
        window.results_summary_label.setText(visible_text)
        window._set_results_summary_placeholder_state(False)
        return True
    except Exception:
        return False


def _set_results_summary_text_with_fallback(
    window: Any,
    summary_text: object = None,
    *,
    default_text: str = '保存されたファイルはありません。',
) -> bool:
    expected_text = _coerce_ui_message_text(summary_text).strip() or default_text
    try:
        if bool(window._set_results_summary_text_fallback(summary_text, default_text=default_text)):
            if window._ui_widget_text(getattr(window, 'results_summary_label', None)) == expected_text:
                return True
            # sweep353: the primary helper may be monkey-patched or may report
            # success without mutating the visible label.  Fall through to the
            # direct label update path so tests and stubbed UI objects still see
            # the requested summary text.
    except Exception:
        pass
    if not hasattr(window, 'results_summary_label'):
        return False
    if window._ui_widget_text(getattr(window, 'results_summary_label', None)) == expected_text:
        return True
    try:
        window.results_summary_label.setText(expected_text)
        window._set_results_summary_placeholder_state(False)
    except Exception:
        return False
    return window._ui_widget_text(getattr(window, 'results_summary_label', None)) == expected_text


def _set_bottom_tab_index_with_fallback(window: Any, index: Any) -> bool:
    if not hasattr(window, 'bottom_tabs'):
        return False
    try:
        normalized_index = int(index)
    except Exception:
        return False
    tab_count = getattr(window.bottom_tabs, 'count', None)
    if callable(tab_count):
        try:
            if normalized_index < 0 or normalized_index >= max(0, int(tab_count())):
                return False
        except Exception:
            return False
    try:
        window.bottom_tabs.setCurrentIndex(normalized_index)
    except Exception:
        pass
    if window._ui_widget_index(getattr(window, 'bottom_tabs', None)) == normalized_index:
        return True
    tab_bar_getter = getattr(window.bottom_tabs, 'tabBar', None)
    if callable(tab_bar_getter):
        try:
            tab_bar = tab_bar_getter()
        except Exception:
            tab_bar = None
        set_tab_bar_index = getattr(tab_bar, 'setCurrentIndex', None)
        if callable(set_tab_bar_index):
            try:
                set_tab_bar_index(normalized_index)
            except Exception:
                pass
        if window._ui_widget_index(getattr(window, 'bottom_tabs', None)) == normalized_index:
            return True
        if window._ui_widget_index(tab_bar) == normalized_index:
            return True
    widget_getter = getattr(window.bottom_tabs, 'widget', None)
    set_current_widget = getattr(window.bottom_tabs, 'setCurrentWidget', None)
    if callable(widget_getter) and callable(set_current_widget):
        try:
            target_widget = widget_getter(normalized_index)
        except Exception:
            target_widget = None
        if target_widget is not None:
            try:
                set_current_widget(target_widget)
            except Exception:
                pass
        if window._ui_widget_index(getattr(window, 'bottom_tabs', None)) == normalized_index:
            return True
    return False


def _clear_results_view(window: Any, summary_text: object = None) -> bool:
    has_results_list = hasattr(window, 'results_list')
    list_cleared = False
    if has_results_list:
        try:
            window.results_list.clear()
            list_cleared = True
        except Exception:
            APP_LOGGER.exception('結果一覧クリアに失敗しました')
    selection_cleared = False
    if has_results_list:
        try:
            selection_cleared = bool(window._clear_results_selection_state())
        except Exception:
            APP_LOGGER.exception('結果一覧選択状態クリアに失敗しました')
    summary_updated = False
    normalized_summary_text = _coerce_ui_message_text(summary_text)
    summary_requested = bool(normalized_summary_text) or hasattr(window, 'results_summary_label')
    try:
        summary_updated = bool(window._set_results_summary_text_with_fallback(summary_text))
    except Exception:
        APP_LOGGER.exception('結果一覧サマリ更新に失敗しました')
    try:
        window._sync_results_action_buttons_state()
    except Exception:
        pass
    if summary_requested and not summary_updated:
        return False
    return bool(list_cleared or selection_cleared or summary_updated)


def _sync_results_action_buttons_state(window: Any) -> bool:
    has_results = False
    try:
        has_results = window._result_item_count() > 0
    except Exception:
        has_results = False
    for attr_name in ('open_results_folder_btn', 'open_selected_result_btn'):
        button = getattr(window, attr_name, None)
        if button is None or not hasattr(button, 'setEnabled'):
            continue
        try:
            button.setEnabled(has_results)
        except Exception:
            pass
    return has_results


def _normalize_results_path_key(window: Any, path: object) -> str:
    return results_controller.normalize_results_path_key(path)


def _clear_results_selection_state(window: Any) -> bool:
    if not hasattr(window, 'results_list'):
        return False
    selection_cleared = False
    clear_selection = getattr(window.results_list, 'clearSelection', None)
    if callable(clear_selection):
        try:
            clear_selection()
            selection_cleared = True
        except Exception:
            pass
    set_current_item = getattr(window.results_list, 'setCurrentItem', None)
    if callable(set_current_item):
        try:
            set_current_item(None)
            return True
        except Exception:
            pass
    set_current_row = getattr(window.results_list, 'setCurrentRow', None)
    if callable(set_current_row):
        try:
            set_current_row(-1)
            return True
        except Exception:
            pass
    return selection_cleared


def _clear_results_selection_with_fallback(
    window: Any,
    context: Mapping[str, object] | object = None,
) -> bool:
    selection_context = window._coerce_mapping_payload(context)
    if not selection_context:
        selection_context = results_controller.build_results_clear_selection_context()
    try:
        window._apply_results_selection_context(selection_context)
    except Exception:
        pass
    try:
        return bool(window._clear_results_selection_state())
    except Exception:
        return False


def _apply_results_selection_context_with_fallback(
    window: Any,
    context: Mapping[str, object] | object,
) -> bool:
    selection_context = window._coerce_mapping_payload(context)
    if not selection_context:
        return window._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )
    if window._payload_bool_value(selection_context, 'clear_selection', False):
        return window._clear_results_selection_with_fallback(selection_context)
    matched_index = studio_logic.payload_optional_int_value(selection_context, 'matched_index')
    if matched_index is None:
        return window._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )
    try:
        window._apply_results_selection_context(selection_context)
        current_index = window._current_results_index()
        if current_index == matched_index:
            return True
        if matched_index in window._selected_result_indexes():
            return True
    except Exception:
        pass
    return window._clear_results_selection_with_fallback(
        results_controller.build_results_clear_selection_context()
    )


def _sync_results_selection_for_loaded_path_with_fallback(
    window: Any,
    path: object,
) -> bool:
    normalized_path = worker_logic._normalized_path_text(path).strip()
    if not normalized_path:
        return window._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )
    selection_context = results_controller.build_results_selection_context(
        normalized_path,
        window._result_item_paths(),
    )
    matched_index = studio_logic.payload_optional_int_value(selection_context, 'matched_index')
    try:
        window._sync_results_selection_for_loaded_path(normalized_path)
        if matched_index is None:
            return window._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
        current_index = window._current_results_index()
        if current_index == matched_index:
            return True
        if matched_index in window._selected_result_indexes():
            return True
    except Exception:
        pass
    return window._clear_results_selection_with_fallback(
        results_controller.build_results_clear_selection_context()
    )


def _result_item_count(window: Any) -> int:
    if not hasattr(window, 'results_list'):
        return 0
    count = getattr(window.results_list, 'count', None)
    if not callable(count):
        return 0
    try:
        return max(0, int(count()))
    except Exception:
        return 0


def _result_item_at(window: Any, index: Any) -> object:
    if not hasattr(window, 'results_list'):
        return None
    item_at = getattr(window.results_list, 'item', None)
    if not callable(item_at):
        return None
    try:
        normalized_index = int(index)
    except Exception:
        return None
    if normalized_index < 0 or normalized_index >= window._result_item_count():
        return None
    try:
        return item_at(normalized_index)
    except Exception:
        return None


def _result_item_paths(window: Any) -> list[object]:
    paths: list[object] = []
    for idx in range(window._result_item_count()):
        item = window._result_item_at(idx)
        paths.append(window._results_item_path(item) if item is not None else None)
    return paths


def _result_item_path_keys(window: Any) -> list[str]:
    return [window._normalize_results_path_key(path) for path in window._result_item_paths()]


def _set_results_current_index_with_fallback(window: Any, index: Any) -> bool:
    if not hasattr(window, 'results_list'):
        return False
    try:
        normalized_index = int(index)
    except Exception:
        return False
    if normalized_index < 0 or normalized_index >= window._result_item_count():
        return False
    matched_item = window._result_item_at(normalized_index)
    if matched_item is None:
        return False
    current_item_getter = getattr(window.results_list, 'currentItem', None)
    selected_items_getter = getattr(window.results_list, 'selectedItems', None)
    can_verify_current_index = callable(current_item_getter) or callable(selected_items_getter)
    set_current_row = getattr(window.results_list, 'setCurrentRow', None)
    if callable(set_current_row):
        try:
            set_current_row(normalized_index)
        except Exception:
            pass
    if window._current_results_index() == normalized_index:
        return True
    if normalized_index in window._selected_result_indexes():
        return True
    set_current_item = getattr(window.results_list, 'setCurrentItem', None)
    if callable(set_current_item):
        try:
            set_current_item(matched_item)
        except Exception:
            pass
    if window._current_results_index() == normalized_index:
        return True
    if normalized_index in window._selected_result_indexes():
        return True
    if callable(set_current_item) and not can_verify_current_index:
        return True
    if callable(set_current_row) and not can_verify_current_index:
        return True
    return False


def _apply_results_selection_context(window: Any, context: Any) -> object:
    context = window._coerce_mapping_payload(context)
    if not hasattr(window, 'results_list'):
        return None
    if window._payload_bool_value(context, 'clear_selection', False):
        window._clear_results_selection_state()
        return None
    matched_index = studio_logic.payload_optional_int_value(context, 'matched_index')
    if matched_index is None:
        window._clear_results_selection_state()
        return None
    matched_item = window._result_item_at(matched_index)
    if matched_item is None:
        window._clear_results_selection_state()
        return None
    if window._set_results_current_index_with_fallback(matched_index):
        return matched_item
    window._clear_results_selection_state()
    return None


def _sync_results_selection_for_loaded_path(window: Any, path: object) -> None:
    if not hasattr(window, 'results_list'):
        return
    context = results_controller.build_results_selection_context(path, window._result_item_paths())
    window._apply_results_selection_context(context)


def _selected_result_indexes(window: Any) -> list[int]:
    if not hasattr(window, 'results_list'):
        return []
    selected_items = getattr(window.results_list, 'selectedItems', None)
    row = getattr(window.results_list, 'row', None)
    if not callable(selected_items) or not callable(row):
        return []
    try:
        selected = selected_items()
    except Exception:
        return []
    indexes: list[int] = []
    for item in selected or []:
        try:
            indexes.append(int(row(item)))
        except Exception:
            continue
    return indexes


def _current_results_index(window: Any) -> int | None:
    if not hasattr(window, 'results_list'):
        return None
    current_item = getattr(window.results_list, 'currentItem', None)
    if not callable(current_item):
        return None
    try:
        item = current_item()
    except Exception:
        item = None
    if item is None:
        return None
    row = getattr(window.results_list, 'row', None)
    if not callable(row):
        return None
    try:
        return int(row(item))
    except Exception:
        return None


def _resolved_result_load_context(window: Any) -> dict[str, object]:
    return results_controller.build_results_load_context(
        selected_indexes=window._selected_result_indexes(),
        current_index=window._current_results_index(),
        item_paths=window._result_item_paths(),
        loaded_path=window.__dict__.get('_loaded_xtc_path_text'),
    )


def _resolved_results_item_for_loading(window: Any) -> object:
    context = window._resolved_result_load_context()
    preferred_index = studio_logic.payload_optional_int_value(context, 'preferred_index')
    if preferred_index is None:
        return None
    return window._result_item_at(preferred_index)


def _fallback_loaded_result_load_context(window: Any) -> dict[str, object]:
    return results_controller.build_fallback_loaded_result_load_context(
        window.__dict__.get('_loaded_xtc_path_text'),
        window._result_item_paths(),
    )
