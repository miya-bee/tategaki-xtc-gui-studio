from __future__ import annotations

"""Page-navigation payload and UI-application helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._runtime_xtc_pages`` etc.), so instance-level overrides installed by
tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``; navigation UI is applied by calling widget methods
through ``window``.
"""

from collections.abc import Mapping
from typing import Any

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_layouts as gui_layouts


def _xtc_page_count(window: Any) -> int:
    if window._effective_device_view_source() == 'preview':
        return len(window._runtime_device_preview_pages())
    return len(window._runtime_xtc_pages())


def _normalized_device_preview_page_index(window: Any, index: object = None, *, total: object = None) -> int:
    default_total = len(window._runtime_device_preview_pages())
    total_pages = default_total if total is None else worker_logic._int_config_value({'value': total}, 'value', default_total)
    raw_value = getattr(window, 'current_device_preview_page_index', 0) if index is None else index
    current_index = worker_logic._int_config_value({'value': raw_value}, 'value', 0)
    return studio_logic.normalize_navigation_index(total_pages, current_index)


def _normalized_xtc_page_index(window: Any, index: object = None, *, total: object = None) -> int:
    total_pages = window._xtc_page_count() if total is None else worker_logic._int_config_value({'value': total}, 'value', window._xtc_page_count())
    raw_value = getattr(window, 'current_page_index', 0) if index is None else index
    current_index = worker_logic._int_config_value({'value': raw_value}, 'value', 0)
    return studio_logic.normalize_navigation_index(total_pages, current_index)


def _xtc_page_state_payload(window: Any, index: object = None) -> dict[str, object]:
    if window._effective_device_view_source() == 'preview':
        pages = window._runtime_device_preview_pages()
        total = len(pages)
        current_index = window._normalized_device_preview_page_index(index, total=total)
        return studio_logic.build_xtc_page_state_payload(pages, current_index)
    pages = window._runtime_xtc_pages()
    total = len(pages)
    current_index = window._normalized_xtc_page_index(index, total=total)
    return studio_logic.build_xtc_page_state_payload(pages, current_index)


def _xtc_navigation_payload(window: Any) -> dict[str, object]:
    view_mode = window._normalized_main_view_mode(getattr(window, 'main_view_mode', 'font'))
    if view_mode == 'font':
        if window._is_file_viewer_mode_active():
            xtc_pages = window._runtime_xtc_pages()
            total = len(xtc_pages)
            current_index = worker_logic._int_config_value({'value': getattr(window, 'current_page_index', 0)}, 'value', 0)
            if total > 0:
                current_index = max(0, min(total - 1, current_index))
            else:
                current_index = 0
            payload = studio_logic.build_navigation_display_state(
                view_mode='font',
                total=total,
                current_index=current_index,
                truncated=False,
            )
            payload = dict(payload)
            payload['file_viewer_navigation'] = True
            payload['current_page'] = current_index + 1 if total > 0 else 0
            return payload
        preview_pages = window._runtime_preview_pages()
        total = len(preview_pages)
        current_index = worker_logic._int_config_value({'value': getattr(window, 'current_preview_page_index', 0)}, 'value', 0)
        if total > 0:
            current_index = max(0, min(total - 1, current_index))
        else:
            current_index = 0
        payload = studio_logic.build_navigation_display_state(
            view_mode='font',
            total=total,
            current_index=current_index,
            truncated=bool(getattr(window, 'preview_pages_truncated', False)),
        )
        return payload

    is_preview = window._effective_device_view_source() == 'preview'
    if is_preview:
        total = len(window._runtime_device_preview_pages())
        current_index = window._normalized_device_preview_page_index(total=total)
        current_page = current_index + 1 if total > 0 else 0
    else:
        page_payload = window._xtc_page_state_payload()
        total = max(0, worker_logic._int_config_value(page_payload, 'total', 0))
        current_index = worker_logic._int_config_value(page_payload, 'current_index', 0)
        current_page = worker_logic._int_config_value(page_payload, 'current_page', 0)
    return studio_logic.build_right_pane_navigation_payload(
        view_mode=view_mode,
        total=total,
        current_index=current_index,
        current_page=current_page,
        is_preview=is_preview,
        truncated=getattr(window, 'device_preview_pages_truncated', False),
    )


def _apply_xtc_navigation_ui(window: Any, payload: Mapping[str, object]) -> None:
    if not hasattr(window, 'prev_btn'):
        return
    total = max(0, window._payload_int_value(payload, 'total', 0))
    view_mode = str(payload.get('view_mode', 'device') or 'device').strip().lower()
    is_preview = window._effective_device_view_source() == 'preview'
    if is_preview:
        index_default = getattr(window, 'current_device_preview_page_index', 0)
        current_index = window._normalized_device_preview_page_index(payload.get('current_index', index_default), total=total)
    else:
        index_default = getattr(window, 'current_page_index', 0)
        current_index = window._normalized_xtc_page_index(payload.get('current_index', index_default), total=total)
    nav_state = studio_logic.build_navigation_display_state(
        view_mode=view_mode,
        total=total,
        current_index=current_index,
        truncated=False,
    )
    nav_state_mapping = nav_state if isinstance(nav_state, Mapping) else {}
    nav_bar_plan = window._localized_plan(gui_layouts.build_nav_bar_plan())
    total_label_format = nav_bar_plan.get('page_total_label_format', '/ {total}')
    fallback_total_label = total_label_format.format(total=total)
    apply_state = studio_logic.build_navigation_apply_state(
        payload,
        nav_state_mapping,
        total_label_format=total_label_format,
        nav_buttons_reversed=getattr(window, 'nav_buttons_reversed', False),
    )
    active = window._payload_bool_value(apply_state, 'active', False)
    current_page = window._payload_int_value(apply_state, 'current_page', 0)
    if view_mode != 'font':
        if is_preview:
            if getattr(window, 'current_device_preview_page_index', 0) != current_index:
                window.current_device_preview_page_index = current_index
        elif getattr(window, 'current_page_index', 0) != current_index:
            window.current_page_index = current_index
            window._refresh_loaded_xtc_viewer_profile_cache()
    window.prev_btn.setEnabled(window._payload_bool_value(apply_state, 'prev_enabled', False))
    window.next_btn.setEnabled(window._payload_bool_value(apply_state, 'next_enabled', False))
    if hasattr(window, 'page_input'):
        window.page_input.setEnabled(active)
    if hasattr(window, 'page_total_label'):
        window.page_total_label.setText(str(apply_state.get('total_label', fallback_total_label)))
    if view_mode == 'font':
        if window._payload_bool_value(payload, 'file_viewer_navigation', False):
            current_xtc_index = max(0, min(total - 1, current_index)) if total > 0 else 0
            if getattr(window, 'current_page_index', 0) != current_xtc_index:
                window.current_page_index = current_xtc_index
                window._refresh_loaded_xtc_viewer_profile_cache()
        else:
            current_preview_index = max(0, min(total - 1, current_index)) if total > 0 else 0
            if getattr(window, 'current_preview_page_index', 0) != current_preview_index:
                window.current_preview_page_index = current_preview_index
    window._reset_xtc_page_input(total, current_page)
    if not window._apply_file_viewer_mode_preview_button_state():
        window._restore_preview_update_button_from_file_viewer_state()


def update_navigation_ui(window: Any) -> None:
    window._apply_xtc_navigation_ui(window._xtc_navigation_payload())
