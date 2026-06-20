from __future__ import annotations

"""Preview source/display resolution and success/failure context helpers.

For ``tategakiXTC_gui_studio``.  The entry module keeps the public
``MainWindow`` wrapper methods so existing monkey patches and unbound test
calls remain compatible.  The implementations here receive the window object
and call back through its methods (``window._runtime_preview_pages`` etc.) and
drive Qt widget state through ``window``, so instance-level overrides installed
by tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``; the only ``QApplication`` dependency
(``processEvents`` during the pending-progress refresh) is passed in by the
entry wrapper as a callable.
"""

from collections.abc import Mapping
from typing import Any, Callable

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_preview_controller as preview_controller
import tategakiXTC_gui_results_controller as results_controller

from tategakiXTC_gui_studio_constants import DEFAULT_PREVIEW_PAGE_LIMIT


def _normalized_preview_page_cache_tokens(window: Any, tokens: object, *, expected_len: int) -> list[int] | None:
    return studio_logic.normalize_preview_page_cache_tokens(tokens, expected_len=expected_len)


def _normalized_right_pane_source_value(window: Any, value: object, *, default: str = 'xtc') -> str:
    return studio_logic.normalize_right_pane_source_value(value, default=default)


def _normalized_device_view_source_value(window: Any, value: object, *, default: str = 'xtc') -> str:
    """Legacy wrapper for older device-view source terminology."""
    return window._normalized_right_pane_source_value(value, default=default)


def _effective_right_pane_source(window: Any, value: object = None) -> str:
    source = window._normalized_right_pane_source_value(
        getattr(window, 'device_view_source', 'xtc') if value is None else value,
        default='xtc',
    )
    has_preview_pages = bool(window._runtime_device_preview_pages()) if source == 'preview' else False
    return studio_logic.resolve_effective_right_pane_source(
        source,
        has_preview_pages=has_preview_pages,
    )


def _effective_device_view_source(window: Any, value: object = None) -> str:
    """Legacy wrapper for older device-view source terminology."""
    return window._effective_right_pane_source(value)


def _is_preview_display_active(window: Any) -> bool:
    mode = window._normalized_main_view_mode(getattr(window, 'main_view_mode', 'font'))
    has_font_preview_pages = bool(window._runtime_preview_pages()) if mode == 'font' else False
    effective_right_pane_source = window._effective_right_pane_source() if mode != 'font' else 'xtc'
    return studio_logic.is_right_pane_preview_display_active(
        mode,
        has_font_preview_pages=has_font_preview_pages,
        effective_right_pane_source=effective_right_pane_source,
    )


def _apply_preview_page_cache_tokens_context(window: Any, context: Mapping[str, object] | None) -> None:
    preview_pages = window._runtime_preview_pages()
    device_pages = window._runtime_device_preview_pages()
    tokens_state = studio_logic.build_preview_page_cache_tokens_state(
        context,
        preview_page_count=len(preview_pages),
        device_preview_page_count=len(device_pages),
    )
    if tokens_state.get('should_rebuild'):
        window._rebuild_preview_page_cache_tokens()
        return
    window._preview_page_cache_tokens = list(tokens_state.get('preview_page_cache_tokens', []))
    window._device_preview_page_cache_tokens = list(tokens_state.get('device_preview_page_cache_tokens', []))


def _apply_preview_button_context(window: Any, context: Mapping[str, object] | None) -> None:
    progress_context = context
    try:
        progress_state = studio_logic.build_preview_progress_context_state(context)
        has_pending_followup = bool(
            getattr(window, '_settings_preview_refresh_pending', False)
            or getattr(window, '_target_preview_refresh_scheduled', False)
        )
        if has_pending_followup and not bool(progress_state.get('progress_visible', False)):
            progress_context = preview_controller.build_preview_pending_context(
                message='次のプレビュー更新を準備しています…'
            )
    except Exception:
        progress_context = context
    window._apply_preview_progress_bar_context(progress_context)
    window._refresh_preview_update_button_for_current_state(context)


def _apply_preview_progress_bar_context(window: Any, context: Mapping[str, object] | None) -> None:
    progress_bar = getattr(window, 'preview_progress_bar', None)
    if progress_bar is None:
        return
    progress_state = studio_logic.build_preview_progress_context_state(context)
    visible = bool(progress_state.get('progress_visible', False))
    try:
        progress_bar.setVisible(visible)
    except Exception:
        pass
    if not visible:
        try:
            progress_bar.setRange(0, 1)
            progress_bar.setValue(0)
            if hasattr(progress_bar, 'setFormat'):
                progress_bar.setFormat('')
        except Exception:
            pass
        return
    busy = bool(progress_state.get('progress_busy', False))
    current = max(0, window._payload_int_value(progress_state, 'progress_current', 0))
    total = max(0, window._payload_int_value(progress_state, 'progress_total', 0))
    try:
        if busy or total <= 0:
            progress_bar.setRange(0, 0)
            progress_bar.setValue(0)
            if hasattr(progress_bar, 'setFormat'):
                progress_bar.setFormat(window._ui_text('更新中…'))
        else:
            safe_total = max(1, total)
            progress_bar.setRange(0, safe_total)
            progress_bar.setValue(min(current, safe_total))
            if hasattr(progress_bar, 'setFormat'):
                progress_bar.setFormat('%p%')
    except Exception:
        pass


def _apply_preview_progress_context(window: Any, context: Mapping[str, object] | None) -> None:
    progress_state = studio_logic.build_preview_progress_context_state(context)
    window._update_preview_status_label(str(progress_state.get('status_message', '')))
    window._apply_preview_progress_bar_context(context)


def _apply_preview_pending_progress_context(
    window: Any,
    message: object = 'プレビュー更新を準備しています…',
    *,
    process_events: Callable[[], None] | None = None,
) -> None:
    """Show a busy preview-progress indicator before a debounced refresh starts."""
    try:
        context = preview_controller.build_preview_pending_context(message=message)
        window._apply_preview_progress_context(context)
        if callable(process_events):
            process_events()
    except Exception:
        pass


def _apply_preview_finish_context_after_running_flags_clear(window: Any) -> None:
    """Restore preview button/progress after all running flags are down.

    v1.3.6.37 introduced a state-reconcile helper that correctly treats
    active preview/target-refresh flags as authoritative.  However, the
    old finish path applied the idle context *before* those flags were
    cleared, so startup/deferred previews could leave the UI looking stuck
    at 「生成中…」.  Keep one final reconciliation point after the flags have
    been cleared.
    """
    try:
        window._apply_preview_button_context(preview_controller.build_preview_finish_context())
    except Exception:
        pass


def _apply_preview_success_context(window: Any, context: Mapping[str, object] | None) -> bool:
    context = window._coerce_mapping_payload(context)
    window.preview_pages_b64 = window._normalized_preview_pages_for_runtime(context.get('preview_pages_b64'))
    window.preview_pages_truncated = window._payload_bool_value(context, 'preview_pages_truncated', False)
    window.device_preview_pages_b64 = window._normalized_preview_pages_for_runtime(context.get('device_preview_pages_b64'))
    window._clear_font_preview_page_pixmap_cache()
    window._clear_device_preview_page_qimage_cache()
    window._apply_preview_page_cache_tokens_context(context)
    window.device_preview_pages_truncated = window._payload_bool_value(context, 'device_preview_pages_truncated', False)
    window.device_view_source = window._normalized_device_view_source_value(
        context.get('device_view_source', 'preview'),
        default='preview',
    )
    window.last_preview_requested_limit = max(
        0,
        window._payload_int_value(
            context,
            'last_preview_requested_limit',
            DEFAULT_PREVIEW_PAGE_LIMIT,
        ),
    )
    raw_last_applied_preview_payload = context.get('last_applied_preview_payload', {})
    window.last_applied_preview_payload = (
        dict(raw_last_applied_preview_payload)
        if isinstance(raw_last_applied_preview_payload, Mapping)
        else {}
    )
    window.current_preview_page_index = preview_controller._clamp_preview_index(
        context.get('current_preview_page_index', 0),
        total=len(window.preview_pages_b64),
    )
    window.current_device_preview_page_index = preview_controller._clamp_preview_index(
        context.get('current_device_preview_page_index', 0),
        total=len(window.device_preview_pages_b64),
    )
    status_message = str(context.get('status_message', studio_logic.build_preview_status_message('empty')))
    has_pages = window._payload_bool_value(context, 'has_pages', False)
    clear_device_page = window._payload_bool_value(context, 'clear_device_page', False)
    if not has_pages:
        window._show_preview_message(status_message)
        window._update_preview_status_label(status_message)
        window.device_view_source = 'xtc'
        window.current_device_preview_page_index = 0
        restored_display_name = window._preview_failure_display_name()
        if restored_display_name is not None:
            window._set_current_xtc_display_name(restored_display_name)
            try:
                window.render_current_page(refresh_navigation=True)
            except Exception:
                if clear_device_page:
                    window._clear_xtc_viewer_page(refresh_navigation=True)
                else:
                    window.update_navigation_ui()
        else:
            window._set_current_xtc_display_name_with_fallback(None)
            if clear_device_page:
                window._clear_xtc_viewer_page(refresh_navigation=True)
            else:
                window.update_navigation_ui()
        restored_path = window._preview_failure_loaded_path()
        if restored_path:
            window._sync_results_selection_for_loaded_path_with_fallback(restored_path)
        else:
            window._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
        window._update_top_status()
        return False
    window.render_current_preview_page()
    window.render_current_page(refresh_navigation=True)
    window._update_preview_status_label(status_message)
    window._set_current_xtc_display_name(str(context.get('display_name', 'プレビュー') or 'プレビュー'))
    window._clear_results_selection_with_fallback(
        results_controller.build_results_clear_selection_context()
    )
    window._update_top_status()
    return True


def _preview_failure_display_name(window: Any) -> object:
    xtc_pages = window._runtime_xtc_pages()
    if xtc_pages:
        remembered = worker_logic._normalized_path_text(window.__dict__.get('_loaded_xtc_display_name')).strip()
        return remembered or None
    return None


def _preview_failure_loaded_path(window: Any) -> object:
    xtc_pages = window._runtime_xtc_pages()
    if xtc_pages:
        remembered = worker_logic._normalized_path_text(window.__dict__.get('_loaded_xtc_path_text')).strip()
        return remembered or None
    return None


def _apply_preview_failure_context(window: Any, context: Mapping[str, object] | None) -> bool:
    context = window._coerce_mapping_payload(context)
    window.preview_pages_b64 = window._normalized_preview_pages_for_runtime(context.get('preview_pages_b64'))
    window.device_preview_pages_b64 = window._normalized_preview_pages_for_runtime(context.get('device_preview_pages_b64'))
    window._clear_font_preview_page_pixmap_cache()
    window._clear_device_preview_page_qimage_cache()
    window._apply_preview_page_cache_tokens_context(context)
    window.preview_pages_truncated = window._payload_bool_value(context, 'preview_pages_truncated', False)
    window.device_preview_pages_truncated = window._payload_bool_value(context, 'device_preview_pages_truncated', False)
    window.device_view_source = window._normalized_device_view_source_value(
        context.get('device_view_source', 'xtc'),
        default='xtc',
    )
    clear_device_page = window._payload_bool_value(context, 'clear_device_page', False)
    window.current_preview_page_index = preview_controller._clamp_preview_index(
        context.get('current_preview_page_index', 0),
        total=len(window.preview_pages_b64),
    )
    window.current_device_preview_page_index = preview_controller._clamp_preview_index(
        context.get('current_device_preview_page_index', 0),
        total=len(window.device_preview_pages_b64),
    )
    if window._effective_device_view_source(context.get('device_view_source', 'xtc')) != 'preview':
        window.current_device_preview_page_index = 0
    try:
        window._apply_profile_runtime_state()
    except Exception:
        pass
    window._set_current_xtc_display_name(window._preview_failure_display_name())
    restored_path = window._preview_failure_loaded_path()
    raw_main_view_mode = str(getattr(window, 'main_view_mode', 'font') or 'font').strip().lower()
    preserve_loaded_file_viewer = bool(restored_path and window._runtime_xtc_pages() and raw_main_view_mode != 'font')
    try:
        window.render_current_page(refresh_navigation=True)
    except Exception:
        if clear_device_page:
            window._clear_xtc_viewer_page(refresh_navigation=True)
        else:
            window.update_navigation_ui()
    preview_pages = window._runtime_preview_pages()
    preview_error_message = str(context.get('error_message', 'プレビュー生成エラー'))
    if preserve_loaded_file_viewer:
        try:
            window._render_current_xtc_page_in_font_view(refresh_navigation=False)
        except Exception:
            window._show_preview_message(preview_error_message)
    elif preview_pages:
        try:
            window.render_current_preview_page()
        except Exception:
            window._show_preview_message(preview_error_message)
    else:
        window._show_preview_message(preview_error_message)
    window._update_preview_status_label(str(context.get('status_message', '')))
    try:
        window.update_navigation_ui()
    except Exception:
        pass
    try:
        if preserve_loaded_file_viewer:
            window._sync_results_selection_for_loaded_path_with_fallback(restored_path)
        elif window._is_preview_display_active():
            window._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
        elif restored_path:
            window._sync_results_selection_for_loaded_path_with_fallback(restored_path)
        else:
            window._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
    except Exception:
        pass
    try:
        window._update_top_status()
    except Exception:
        pass
    return False
