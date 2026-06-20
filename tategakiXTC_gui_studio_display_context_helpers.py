from __future__ import annotations

"""Display-context synchronization helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and drive the ``current_xtc_label`` widget plus
shared status text through ``window``, so instance-level overrides installed by
tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``.
"""

from typing import Any

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_results_controller as results_controller

from tategakiXTC_gui_studio_ui_helpers import _coerce_ui_message_text


def _set_current_xtc_display_name(window: Any, display_name: object = None) -> None:
    if not hasattr(window, 'current_xtc_label'):
        return
    text = _coerce_ui_message_text(display_name, 'なし').strip() or 'なし'
    window.current_xtc_label.setText(studio_logic.build_displaying_document_label(text, fallback='なし', language=window.current_ui_language_value()))

def _set_current_xtc_display_name_with_fallback(window: Any, display_name: object = None) -> bool:
    text = _coerce_ui_message_text(display_name, 'なし').strip() or 'なし'
    expected_label = studio_logic.build_displaying_document_label(text, fallback='なし', language=window.current_ui_language_value())
    try:
        window._set_current_xtc_display_name(display_name)
    except Exception:
        pass
    if not hasattr(window, 'current_xtc_label'):
        return True
    if window._ui_widget_text(getattr(window, 'current_xtc_label', None)) == expected_label:
        return True
    try:
        window.current_xtc_label.setText(expected_label)
    except Exception:
        return False
    return window._ui_widget_text(getattr(window, 'current_xtc_label', None)) == expected_label

def _sync_loaded_xtc_display_context_for_device_view(window: Any) -> None:
    if window._effective_device_view_source() == 'preview':
        return
    if not window._runtime_xtc_pages():
        return
    path_text = worker_logic._normalized_path_text(window.__dict__.get('_loaded_xtc_path_text')).strip()
    display_name = worker_logic._normalized_path_text(window.__dict__.get('_loaded_xtc_display_name')).strip()
    if not display_name and path_text:
        display_name = worker_logic._normalized_path_text(window._xtc_display_name(path_text)).strip()
    if display_name:
        try:
            window._set_current_xtc_display_name_with_fallback(display_name)
        except Exception:
            pass
    if path_text:
        window._sync_results_selection_for_loaded_path_with_fallback(path_text)
    else:
        window._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )

def _sync_preview_display_context_for_device_view(window: Any) -> None:
    if window._effective_device_view_source() != 'preview':
        return
    if not window._runtime_device_preview_pages():
        return
    try:
        window._set_current_xtc_display_name_with_fallback('プレビュー')
    except Exception:
        pass
    window._clear_results_selection_with_fallback(
        results_controller.build_results_clear_selection_context()
    )

def _sync_blank_device_display_context(window: Any) -> None:
    try:
        window._set_current_xtc_display_name_with_fallback(None)
    except Exception:
        pass
    window._clear_results_selection_with_fallback(
        results_controller.build_results_clear_selection_context()
    )

def _restore_shared_status_for_visible_display_context(window: Any) -> None:
    try:
        view_mode = window._normalized_main_view_mode(getattr(window, 'main_view_mode', 'font'))
    except Exception:
        view_mode = 'font'
    replacement = ''
    stale_progress_status = False
    stale_status_bar = False
    current_progress_status = ''
    current_status_bar_status = ''
    replacement_is_render_failure = False
    if view_mode == 'font':
        preview_status_text = window._ui_widget_text(getattr(window, 'preview_status_label', None))
        preview_status_text_is_meaningful = bool(preview_status_text) and preview_status_text.startswith('プレビュー')
        try:
            preview_pages_visible = bool(window._runtime_preview_pages())
        except Exception:
            preview_pages_visible = False
        current_progress_status = window._ui_widget_text(getattr(window, 'progress_label', None))
        current_status_bar_status = window._status_bar_message_text()
        if not preview_pages_visible:
            active_preview_progress_failure = window._preview_render_failure_matches_visible_display_context(current_progress_status)
            active_preview_status_failure = window._preview_render_failure_matches_visible_display_context(current_status_bar_status)
            active_preview_label_failure = (
                preview_status_text_is_meaningful
                and window._preview_render_failure_matches_visible_display_context(preview_status_text)
            )
            if active_preview_label_failure:
                replacement = preview_status_text
            elif preview_status_text_is_meaningful:
                replacement = preview_status_text
            else:
                return
            stale_progress_status = window._is_device_render_failure_status_text(current_progress_status) or (
                window._is_preview_render_failure_status_text(current_progress_status)
                and not active_preview_progress_failure
            )
            stale_status_bar = window._is_device_render_failure_status_text(current_status_bar_status) or (
                window._is_preview_render_failure_status_text(current_status_bar_status)
                and not active_preview_status_failure
            )
            replacement_is_render_failure = window._is_preview_render_failure_status_text(replacement)
        elif (
            window._is_preview_render_failure_status_text(preview_status_text)
            and window._preview_render_failure_matches_visible_display_context(preview_status_text)
        ):
            replacement = preview_status_text
        else:
            replacement = window._current_preview_render_status_message()
        if preview_pages_visible:
            stale_progress_status = window._is_device_render_failure_status_text(current_progress_status)
            stale_status_bar = window._is_device_render_failure_status_text(current_status_bar_status)
            replacement_is_render_failure = window._is_preview_render_failure_status_text(replacement)
    else:
        preview_source_active = window._normalized_device_view_source_value(
            getattr(window, 'device_view_source', 'xtc'),
            default='xtc',
        ) == 'preview'
        device_pages_visible = False
        if preview_source_active:
            try:
                device_pages_visible = bool(window._runtime_device_preview_pages())
            except Exception:
                device_pages_visible = False
        else:
            try:
                device_pages_visible = bool(window._runtime_xtc_pages())
            except Exception:
                device_pages_visible = False
        current_progress_status = window._ui_widget_text(getattr(window, 'progress_label', None))
        current_status_bar_status = window._status_bar_message_text()
        if preview_source_active and not device_pages_visible:
            preview_status_text = window._ui_widget_text(getattr(window, 'preview_status_label', None))
            active_preview_progress_failure = window._preview_render_failure_matches_visible_display_context(current_progress_status)
            active_preview_status_failure = window._preview_render_failure_matches_visible_display_context(current_status_bar_status)
            active_preview_label_failure = window._preview_render_failure_matches_visible_display_context(preview_status_text)
            for candidate, is_active_preview_failure in (
                (current_progress_status, active_preview_progress_failure),
                (current_status_bar_status, active_preview_status_failure),
                (preview_status_text, active_preview_label_failure),
            ):
                if is_active_preview_failure:
                    replacement = candidate
                    break
            if not replacement:
                replacement = window._ui_widget_text(getattr(window, 'current_xtc_label', None))
            if not replacement:
                return
            stale_progress_status = window._is_device_render_failure_status_text(current_progress_status) or (
                window._is_preview_render_failure_status_text(current_progress_status)
                and not active_preview_progress_failure
            )
            stale_status_bar = window._is_device_render_failure_status_text(current_status_bar_status) or (
                window._is_preview_render_failure_status_text(current_status_bar_status)
                and not active_preview_status_failure
            )
            replacement_is_render_failure = window._is_preview_render_failure_status_text(replacement)
        else:
            if not device_pages_visible:
                return
            active_device_progress_failure = window._device_render_failure_matches_visible_display_context(current_progress_status)
            active_device_status_failure = window._device_render_failure_matches_visible_display_context(current_status_bar_status)
            for candidate, is_active_device_failure in (
                (current_progress_status, active_device_progress_failure),
                (current_status_bar_status, active_device_status_failure),
            ):
                if is_active_device_failure:
                    replacement = candidate
                    break
            if not replacement:
                replacement = window._ui_widget_text(getattr(window, 'current_xtc_label', None))
            stale_progress_status = window._is_preview_render_failure_status_text(current_progress_status) or (
                window._is_device_render_failure_status_text(current_progress_status)
                and not active_device_progress_failure
            )
            stale_status_bar = window._is_preview_render_failure_status_text(current_status_bar_status) or (
                window._is_device_render_failure_status_text(current_status_bar_status)
                and not active_device_status_failure
            )
            replacement_is_render_failure = window._is_device_render_failure_status_text(replacement)
    if not replacement:
        return
    sync_status_bar_to_replacement = stale_progress_status or stale_status_bar
    if replacement_is_render_failure:
        if stale_progress_status or stale_status_bar:
            if current_progress_status != replacement:
                stale_progress_status = True
        elif current_progress_status != replacement and (
            current_status_bar_status == replacement
            or not current_status_bar_status
            or not window._is_render_failure_status_text(current_status_bar_status)
        ):
            stale_progress_status = True
        if current_status_bar_status != replacement and (
            stale_status_bar
            or (
                current_progress_status == replacement
                and current_status_bar_status
                and not window._is_render_failure_status_text(current_status_bar_status)
            )
        ):
            sync_status_bar_to_replacement = True
    elif view_mode == 'font':
        if window._is_preview_render_failure_status_text(current_progress_status):
            stale_progress_status = True
        if window._is_preview_render_failure_status_text(current_status_bar_status):
            sync_status_bar_to_replacement = True
    if stale_progress_status and hasattr(window, 'progress_label'):
        try:
            window.progress_label.setText(replacement)
        except Exception:
            pass
    if stale_progress_status or sync_status_bar_to_replacement:
        window._show_ui_status_message_direct_with_reflection_best_effort(replacement, 5000)

def _sync_active_display_context_for_visible_page(window: Any) -> None:
    try:
        view_mode = window._normalized_main_view_mode(getattr(window, 'main_view_mode', 'font'))
    except Exception:
        view_mode = 'font'
    if view_mode == 'font':
        if window._is_file_viewer_mode_active():
            try:
                window._sync_loaded_xtc_display_context_for_device_view()
            except Exception:
                pass
        elif window._runtime_preview_pages():
            window._sync_preview_display_context_for_font_view()
        try:
            window._restore_shared_status_for_visible_display_context()
        except Exception:
            pass
        return
    if window._effective_device_view_source() == 'preview':
        if window._runtime_device_preview_pages():
            window._sync_preview_display_context_for_device_view()
        else:
            window._sync_blank_device_display_context()
        try:
            window._restore_shared_status_for_visible_display_context()
        except Exception:
            pass
        return
    if window._runtime_xtc_pages():
        window._sync_loaded_xtc_display_context_for_device_view()
        try:
            window._restore_shared_status_for_visible_display_context()
        except Exception:
            pass
        return
    window._sync_blank_device_display_context()
    try:
        window._restore_shared_status_for_visible_display_context()
    except Exception:
        pass

