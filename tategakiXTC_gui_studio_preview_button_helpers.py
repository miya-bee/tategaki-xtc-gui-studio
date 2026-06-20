from __future__ import annotations

"""Preview-update button state and file-viewer-mode helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and drive the ``preview_update_btn`` widget plus
related preview-state attributes through ``window``, so instance-level overrides
installed by tests keep working.  This module intentionally does not import
PySide6 or ``tategakiXTC_gui_studio``.
"""

from collections.abc import Mapping
from typing import Any

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_preview_controller as preview_controller


def _apply_manual_preview_required_context(window: Any) -> None:
    message = window._manual_preview_required_status_message()
    try:
        window._apply_preview_progress_bar_context(preview_controller.build_preview_finish_context())
    except Exception:
        pass
    try:
        window._mark_preview_update_button_pending()
    except Exception:
        pass
    try:
        window._update_preview_status_label(message)
    except Exception:
        pass
    progress_label = getattr(window, 'progress_label', None)
    setter = getattr(progress_label, 'setText', None)
    if callable(setter):
        try:
            setter(message)
        except Exception:
            pass


def _cancel_auto_live_preview_due_to_large_limit(window: Any) -> None:
    try:
        window._cancel_pending_settings_live_preview_refresh()
    except Exception:
        pass
    window._settings_preview_refresh_pending = False
    window._settings_preview_refresh_pending_reset_page = False
    window._settings_preview_refresh_scheduled = False
    window._settings_preview_refresh_deferred_until_preview_finished = False


def _set_preview_update_button_visual_state(window: Any, state: object) -> None:
    """Apply a lightweight visual state to the Preview Update button."""
    button = getattr(window, 'preview_update_btn', None)
    if button is None:
        return
    normalized = str(state or 'idle').strip().lower()
    if normalized not in {'idle', 'pending', 'refreshing', 'viewer'}:
        normalized = 'idle'
    window._preview_update_button_visual_state = normalized
    try:
        button.setProperty('previewState', normalized)
    except Exception:
        return
    try:
        style = button.style()
        if hasattr(style, 'unpolish'):
            style.unpolish(button)
        if hasattr(style, 'polish'):
            style.polish(button)
    except Exception:
        pass
    try:
        button.update()
    except Exception:
        pass


def _has_loaded_xtc_viewer_document(window: Any) -> bool:
    """Return True when a user-opened XTC/XTCH document is loaded.

    Generated preview pages can remain cached, and some view/display-only
    controls may temporarily leave ``device_view_source`` set to ``preview``.
    A loaded file-viewer document must therefore be detected from the loaded
    XTC/XTCH identity plus XTC pages, not from the current preview source.
    """
    try:
        if not window._runtime_xtc_pages():
            return False
    except Exception:
        return False
    loaded_path = worker_logic._normalized_path_text(
        window.__dict__.get('_loaded_xtc_path_text')
    ).strip()
    loaded_name = worker_logic._normalized_path_text(
        window.__dict__.get('_loaded_xtc_display_name')
    ).strip()
    return bool(loaded_path or loaded_name)


def _is_file_viewer_mode_active(window: Any) -> bool:
    """Return True when a user-opened XTC/XTCH document is being shown.

    Generated conversion results can also populate ``xtc_pages``.  Treating
    bare XTC pages as file-viewer mode would incorrectly neutralize preview
    refresh state.  Require the loaded-file identity that the XTC/XTCH
    viewer path stores alongside the page data.
    """
    try:
        return window._has_loaded_xtc_viewer_document()
    except Exception:
        return False


def _apply_file_viewer_mode_preview_button_state(window: Any) -> bool:
    """Neutralize the Preview Update button while loaded XTC/XTCH is shown.

    Returning True means file-viewer mode handled the button state.
    """
    if not window._is_file_viewer_mode_active():
        return False
    button = getattr(window, 'preview_update_btn', None)
    if button is not None:
        try:
            button.setEnabled(False)
        except Exception:
            pass
        try:
            button.setText(window._ui_text('ファイル表示中'))
        except Exception:
            pass
        try:
            button.setToolTip(window._ui_text('ファイルビューワーモードではXTC/XTCHを直接表示しているため、プレビュー更新は不要です。'))
        except Exception:
            pass
        window._set_preview_update_button_visual_state('viewer')
    try:
        window._update_preview_status_label(window._ui_text('ファイルビューワーモード: XTC/XTCHを直接表示中です'))
    except Exception:
        pass
    return True


def _restore_preview_update_button_from_file_viewer_state(window: Any) -> None:
    button = getattr(window, 'preview_update_btn', None)
    if button is None:
        return
    current_visual = str(getattr(window, '_preview_update_button_visual_state', 'idle') or 'idle')
    current_text = str(getattr(button, 'text_value', '') or '')
    text_getter = getattr(button, 'text', None)
    if callable(text_getter):
        try:
            current_text = str(text_getter() or '')
        except Exception:
            current_text = str(getattr(button, 'text_value', '') or '')
    if current_visual != 'viewer' and current_text not in {'ファイル表示中', window._ui_text('ファイル表示中')}:
        return
    try:
        button.setEnabled(True)
    except Exception:
        pass
    try:
        button.setText(window._ui_text('プレビュー更新'))
    except Exception:
        pass
    try:
        button.setToolTip('')
    except Exception:
        pass
    window._set_preview_update_button_visual_state('idle')


def _refresh_preview_update_button_for_current_state(
    window: Any,
    context: Mapping[str, object] | None = None,
) -> None:
    """Reconcile Preview Update button from current state in one place.

    Older code paths pushed button text/state directly, which made stale
    viewer labels such as 「ファイル表示中」 easy to leave behind when a
    normal target change escaped one of the explicit cleanup calls.  This
    helper keeps the operation pull-like: file-viewer state wins, then
    running/pending flags, then the worker-provided idle context.
    """
    button = getattr(window, 'preview_update_btn', None)
    if button is None:
        return
    if window._apply_file_viewer_mode_preview_button_state():
        return

    button_state = studio_logic.build_preview_button_state(context)
    button_enabled = bool(button_state.get('button_enabled', True))
    button_text = str(button_state.get('button_text', 'プレビュー更新'))

    running = bool(
        getattr(window, '_preview_running', False)
        or getattr(window, '_target_preview_refresh_running', False)
    )
    if running or (not button_enabled) or button_text == '生成中…' or button_text == window._ui_text('生成中…'):
        try:
            button.setEnabled(False if running else button_enabled)
        except Exception:
            pass
        try:
            button.setText(window._ui_text('生成中…') if running else window._ui_text(button_text))
        except Exception:
            pass
        window._set_preview_update_button_visual_state('refreshing')
        return

    pending = bool(getattr(window, '_settings_preview_refresh_pending', False))
    if pending:
        try:
            button.setEnabled(True)
        except Exception:
            pass
        try:
            button.setText('● ' + window._ui_text('プレビュー更新'))
        except Exception:
            pass
        try:
            button.setToolTip('')
        except Exception:
            pass
        window._set_preview_update_button_visual_state('pending')
        return

    try:
        button.setEnabled(button_enabled)
    except Exception:
        pass
    try:
        button.setText(window._ui_text(button_text or 'プレビュー更新'))
    except Exception:
        pass
    try:
        button.setToolTip('')
    except Exception:
        pass
    window._set_preview_update_button_visual_state('idle')


def _mark_preview_update_button_pending(window: Any) -> None:
    """Show that a debounced live preview refresh has been queued."""
    if window._apply_file_viewer_mode_preview_button_state():
        return
    button = getattr(window, 'preview_update_btn', None)
    if button is None:
        return
    try:
        button.setEnabled(True)
    except Exception:
        pass
    try:
        button.setText('● ' + window._ui_text('プレビュー更新'))
    except Exception:
        pass
    window._set_preview_update_button_visual_state('pending')
