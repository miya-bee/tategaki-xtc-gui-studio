from __future__ import annotations

"""Preview/device render status refresh helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._current_preview_render_status_message`` etc.), so instance-level
overrides installed by tests keep working.  This module intentionally does not
import PySide6 or ``tategakiXTC_gui_studio``.
"""

from typing import Any

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic

from tategakiXTC_gui_studio_preview_helpers import _preview_widget_limit_value


def _current_preview_success_status_message(window: Any) -> str:
    pages = window._runtime_preview_pages()
    status_state = studio_logic.build_preview_success_status_state(
        page_count=len(pages),
        requested_limit=getattr(window, 'last_preview_requested_limit', 0),
        truncated=getattr(window, 'preview_pages_truncated', False),
        language=window.current_ui_language_value(),
    )
    return str(status_state.get('status_message', ''))


def _current_preview_render_status_message(window: Any) -> str:
    pages = window._runtime_preview_pages()
    return studio_logic.build_preview_render_status_message(
        page_count=len(pages),
        requested_limit=getattr(window, 'last_preview_requested_limit', 0),
        truncated=getattr(window, 'preview_pages_truncated', False),
        running=getattr(window, '_preview_running', False),
        dirty=getattr(window, 'preview_dirty', False),
        widget_limit=_preview_widget_limit_value(getattr(window, 'preview_page_limit_spin', None)),
        language=window.current_ui_language_value(),
    )


def _refresh_successful_preview_render_status(window: Any) -> None:
    preview_replacement = window._current_preview_render_status_message()
    if not preview_replacement:
        return
    view_mode = window._normalized_main_view_mode(
        getattr(window, 'main_view_mode', 'font')
    )
    visible_font_preview_active = view_mode == 'font' and bool(window._runtime_preview_pages())
    preview_status_text = ''
    progress_status_text = ''
    if hasattr(window, 'preview_status_label'):
        preview_status_text = window._ui_widget_text(window.preview_status_label)
    if hasattr(window, 'progress_label'):
        progress_status_text = window._ui_widget_text(window.progress_label)
    status_state = studio_logic.build_successful_preview_render_status_refresh_state(
        preview_replacement=preview_replacement,
        view_mode=view_mode,
        visible_font_preview_active=visible_font_preview_active,
        preview_status_text=preview_status_text,
        progress_status_text=progress_status_text,
        status_bar_text=window._status_bar_message_text(),
        current_label_text=window._ui_widget_text(getattr(window, 'current_xtc_label', None)),
    )
    if status_state.get('stale_preview_status') and hasattr(window, 'preview_status_label'):
        try:
            window._update_preview_status_label(str(status_state.get('preview_replacement', preview_replacement)))
        except Exception:
            pass
    progress_replacement = str(status_state.get('progress_replacement', preview_replacement))
    if status_state.get('stale_progress_status') and hasattr(window, 'progress_label'):
        try:
            window.progress_label.setText(progress_replacement)
        except Exception:
            pass
    if status_state.get('should_notify_status_bar'):
        window._show_ui_status_message_direct_with_reflection_best_effort(progress_replacement, 5000)


def _refresh_successful_device_render_status(window: Any) -> None:
    view_mode = window._normalized_main_view_mode(
        getattr(window, 'main_view_mode', 'font')
    )
    has_font_preview_pages = bool(window._runtime_preview_pages()) if view_mode == 'font' else False
    preview_replacement = window._current_preview_render_status_message() if has_font_preview_pages else ''
    progress_status_text = ''
    if hasattr(window, 'progress_label'):
        progress_status_text = window._ui_widget_text(window.progress_label)
    status_state = studio_logic.build_successful_device_render_status_refresh_state(
        view_mode=view_mode,
        current_label_text=window._ui_widget_text(getattr(window, 'current_xtc_label', None)),
        preview_replacement=preview_replacement,
        has_font_preview_pages=has_font_preview_pages,
        progress_status_text=progress_status_text,
        status_bar_text=window._status_bar_message_text(),
    )
    replacement = str(status_state.get('replacement', ''))
    if not replacement:
        return
    stale_progress_status = bool(status_state.get('stale_progress_status'))
    if stale_progress_status and hasattr(window, 'progress_label'):
        try:
            window.progress_label.setText(replacement)
        except Exception:
            pass
    if status_state.get('should_notify_status_bar'):
        window._show_ui_status_message_direct_with_reflection_best_effort(replacement, 5000)


def _render_failure_status_message(window: Any, title: object, exc: Exception) -> str:
    title_text = worker_logic._normalized_path_text(title).strip() or '表示エラー'
    detail = worker_logic._normalized_path_text(exc).strip()
    preserved = window._xtc_load_failure_preserved_display_name()
    return studio_logic.build_render_failure_status_message(
        title_text,
        detail,
        preserved,
        language=window.current_ui_language_value(),
    )


def _handle_xtc_render_failure(window: Any, exc: Exception, *, refresh_navigation: bool = True) -> None:
    try:
        window._sync_active_display_context_for_visible_page()
    except Exception:
        pass
    window._clear_xtc_viewer_page(refresh_navigation=refresh_navigation)
    status_message = window._render_failure_status_message('ページ表示エラー', exc)
    device_view_visible = window._normalized_main_view_mode(
        getattr(window, 'main_view_mode', 'font')
    ) == 'device'
    reflect_failure_in_status = device_view_visible or not window._visible_render_failure_status_text()
    window._append_log_with_status_fallback(
        status_message,
        reflect_in_status=reflect_failure_in_status,
    )
    if not device_view_visible:
        return
    try:
        window._show_critical_dialog_with_status_fallback(
            'ページ表示エラー',
            str(exc),
            fallback_status_message=status_message,
        )
    except Exception:
        pass
