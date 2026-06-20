from __future__ import annotations

"""Status-bar message and render-failure display helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._status_bar_message_text`` etc.), so instance-level overrides
installed by tests keep working.  This module intentionally does not import
PySide6 or ``tategakiXTC_gui_studio``.
"""

from typing import Any

import tategakiXTC_gui_studio_logic as studio_logic

from tategakiXTC_gui_studio_ui_helpers import _coerce_ui_message_text


def _ui_widget_text(window: Any, widget: object) -> str:
    text_getter = getattr(widget, 'text', None)
    if callable(text_getter):
        try:
            return _coerce_ui_message_text(text_getter()).strip()
        except Exception:
            return ''
    return ''


def _ui_widget_index(window: Any, widget: object) -> int | None:
    current_index_getter = getattr(widget, 'currentIndex', None)
    if callable(current_index_getter):
        try:
            return int(current_index_getter())
        except Exception:
            pass
    if hasattr(widget, 'index'):
        try:
            return int(getattr(widget, 'index'))
        except Exception:
            return None
    return None


def _is_render_failure_status_text(window: Any, text: object) -> bool:
    return studio_logic.is_render_failure_status_text(text)


def _is_preview_render_failure_status_text(window: Any, text: object) -> bool:
    return studio_logic.is_preview_render_failure_status_text(text)


def _is_device_render_failure_status_text(window: Any, text: object) -> bool:
    return studio_logic.is_device_render_failure_status_text(text)


def _display_context_name_from_label_text(window: Any, text: object) -> str:
    return studio_logic.display_context_name_from_label_text(text)


def _render_failure_preserved_display_name(window: Any, text: object) -> str:
    return studio_logic.render_failure_preserved_display_name(text)


def _device_render_failure_matches_visible_display_context(window: Any, text: object) -> bool:
    normalized = _coerce_ui_message_text(text).strip()
    if not window._is_device_render_failure_status_text(normalized):
        return False
    visible_label_text = window._ui_widget_text(getattr(window, 'current_xtc_label', None))
    visible_label_normalized = _coerce_ui_message_text(visible_label_text).strip()
    visible_display_name = ''
    if visible_label_normalized.startswith(('表示中:', 'Viewing:')):
        visible_display_name = window._display_context_name_from_label_text(visible_label_normalized)
    return studio_logic.render_failure_matches_display_context(normalized, visible_display_name)


def _preview_render_failure_matches_visible_display_context(window: Any, text: object) -> bool:
    normalized = _coerce_ui_message_text(text).strip()
    if not window._is_preview_render_failure_status_text(normalized):
        return False
    preserved_display_name = window._render_failure_preserved_display_name(normalized)
    if not preserved_display_name:
        return True
    try:
        view_mode = window._normalized_main_view_mode(getattr(window, 'main_view_mode', 'font'))
    except Exception:
        view_mode = 'font'
    visible_display_name = ''
    preview_source_active = False
    if view_mode == 'font':
        try:
            preview_pages_visible = bool(window._runtime_preview_pages())
        except Exception:
            preview_pages_visible = False
        if preview_pages_visible:
            visible_display_name = 'Preview' if window.current_ui_language_value() == 'en' else 'プレビュー'
    else:
        try:
            preview_source_active = window._normalized_device_view_source_value(
                getattr(window, 'device_view_source', 'xtc'),
                default='xtc',
            ) == 'preview'
        except Exception:
            preview_source_active = False
        if preview_source_active:
            visible_label_text = window._ui_widget_text(getattr(window, 'current_xtc_label', None))
            visible_display_name = window._display_context_name_from_label_text(visible_label_text)
            if not visible_display_name or visible_display_name == 'なし':
                visible_display_name = 'Preview' if window.current_ui_language_value() == 'en' else 'プレビュー'
    if visible_display_name:
        return preserved_display_name == visible_display_name
    if view_mode == 'device':
        return preview_source_active
    return True


def _visible_render_failure_status_text(window: Any) -> str:
    try:
        view_mode = window._normalized_main_view_mode(getattr(window, 'main_view_mode', 'font'))
    except Exception:
        view_mode = 'font'
    progress_text = window._ui_widget_text(getattr(window, 'progress_label', None))
    status_bar_text = window._status_bar_message_text()
    if view_mode == 'font':
        preview_status_text = window._ui_widget_text(getattr(window, 'preview_status_label', None))
        for candidate in (preview_status_text, progress_text, status_bar_text):
            if (
                window._is_preview_render_failure_status_text(candidate)
                and window._preview_render_failure_matches_visible_display_context(candidate)
            ):
                return candidate
        try:
            preview_pages_visible = bool(window._runtime_preview_pages())
        except Exception:
            preview_pages_visible = False
        if not preview_pages_visible:
            for candidate in (progress_text, status_bar_text):
                if (
                    window._is_device_render_failure_status_text(candidate)
                    and window._device_render_failure_matches_visible_display_context(candidate)
                ):
                    return candidate
        return ''
    for candidate in (progress_text, status_bar_text):
        if (
            window._is_device_render_failure_status_text(candidate)
            and window._device_render_failure_matches_visible_display_context(candidate)
        ):
            return candidate
    try:
        device_pages_visible = bool(
            window._runtime_device_preview_pages()
            if window._effective_device_view_source() == 'preview'
            else window._runtime_xtc_pages()
        )
    except Exception:
        device_pages_visible = False
    if not device_pages_visible:
        for candidate in (progress_text, status_bar_text):
            if (
                window._is_preview_render_failure_status_text(candidate)
                and window._preview_render_failure_matches_visible_display_context(candidate)
            ):
                return candidate
    return ''


def _show_ui_status_message_unless_render_failure_visible(
    window: Any,
    message: object,
    timeout: int | None = 2000,
) -> None:
    try:
        window._restore_shared_status_for_visible_display_context()
    except Exception:
        pass
    if window._visible_render_failure_status_text():
        return
    window._show_ui_status_message_direct_with_reflection_best_effort(
        message,
        timeout,
        reuse_existing_message=False,
    )


def _status_bar_message_text(window: Any) -> str:
    status_bar_getter = getattr(window, 'statusBar', None)
    if not callable(status_bar_getter):
        return ''
    try:
        status_bar = status_bar_getter()
    except Exception:
        return ''
    current_message_getter = getattr(status_bar, 'currentMessage', None)
    if callable(current_message_getter):
        try:
            return _coerce_ui_message_text(current_message_getter()).strip()
        except Exception:
            return ''
    return ''


def _show_ui_status_message_unless_render_failure_visible_with_reflection(
    window: Any,
    message: object,
    timeout: int | None = 2000,
    *,
    reuse_existing_message: bool = True,
) -> bool:
    helper = getattr(window, '_show_ui_status_message_unless_render_failure_visible', None)
    if not callable(helper):
        return False
    normalized = window._ui_text(_coerce_ui_message_text(message).strip())
    if not normalized:
        return False
    helper_status_bar = None
    helper_status_event_count_before = None
    try:
        helper_status_bar = window.statusBar()
    except Exception:
        helper_status_bar = None
    current_message = window._status_bar_message_text()
    if reuse_existing_message and current_message == normalized:
        return True
    helper_show_message_call_count_before = None
    for status_events_attr in ('messages', 'calls'):
        status_events = getattr(helper_status_bar, status_events_attr, None)
        if isinstance(status_events, list):
            helper_status_event_count_before = len(status_events)
            break
    helper_show_message = getattr(helper_status_bar, 'showMessage', None)
    if callable(helper_show_message):
        helper_show_message_call_count_before = getattr(helper_show_message, 'call_count', None)
    try:
        helper(normalized, timeout)
    except Exception:
        return False
    reflected = (
        window._status_bar_message_text() == normalized
        or bool(window._visible_render_failure_status_text())
    )
    if (
        not reflected
        and helper_status_event_count_before is not None
        and helper_status_bar is not None
    ):
        for status_events_attr in ('messages', 'calls'):
            status_events = getattr(helper_status_bar, status_events_attr, None)
            if isinstance(status_events, list):
                reflected = len(status_events) > helper_status_event_count_before
                break
    if (
        not reflected
        and helper_show_message_call_count_before is not None
        and callable(helper_show_message)
    ):
        helper_show_message_call_count_after = getattr(helper_show_message, 'call_count', None)
        if isinstance(helper_show_message_call_count_after, int):
            reflected = helper_show_message_call_count_after > helper_show_message_call_count_before
    return reflected


def _show_ui_status_message_with_reflection_or_direct_fallback(
    window: Any,
    message: object,
    timeout: int | None = 2000,
    *,
    reuse_existing_message: bool = True,
) -> bool:
    normalized = window._ui_text(_coerce_ui_message_text(message).strip())
    if not normalized:
        return False
    reflected = False
    try:
        reflected = bool(
            window._show_ui_status_message_unless_render_failure_visible_with_reflection(
                normalized,
                timeout,
                reuse_existing_message=reuse_existing_message,
            )
        )
    except Exception:
        reflected = False
    if reflected:
        return True
    return window._show_ui_status_message_direct_with_reflection_best_effort(
        normalized,
        timeout,
        reuse_existing_message=reuse_existing_message,
    )


def _show_ui_status_message_direct_with_reflection_best_effort(
    window: Any,
    message: object,
    timeout: int | None = 2000,
    *,
    reuse_existing_message: bool = True,
) -> bool:
    try:
        if reuse_existing_message:
            return bool(
                window._show_ui_status_message_direct_with_reflection(
                    message,
                    timeout,
                )
            )
        return bool(
            window._show_ui_status_message_direct_with_reflection(
                message,
                timeout,
                reuse_existing_message=False,
            )
        )
    except Exception:
        return False


def _show_ui_status_message_direct_with_reflection(
    window: Any,
    message: object,
    timeout: int | None = 2000,
    *,
    reuse_existing_message: bool = True,
) -> bool:
    normalized = window._ui_text(_coerce_ui_message_text(message).strip())
    status_bar = None
    status_bar_message_before = window._status_bar_message_text()
    if reuse_existing_message and status_bar_message_before == normalized:
        return True
    status_event_count_before = None
    show_message_call_count_before = None
    try:
        status_bar = window.statusBar()
    except Exception:
        status_bar = None
    if status_bar is not None:
        for status_events_attr in ('messages', 'calls'):
            status_events = getattr(status_bar, status_events_attr, None)
            if isinstance(status_events, list):
                status_event_count_before = len(status_events)
                break
        show_message = getattr(status_bar, 'showMessage', None)
        if callable(show_message):
            show_message_call_count_before = getattr(show_message, 'call_count', None)
    try:
        if status_bar is None:
            return False
        if timeout is None:
            status_bar.showMessage(normalized)
        else:
            status_bar.showMessage(normalized, int(timeout))
    except Exception:
        return False
    reflected = window._status_bar_message_text() == normalized
    if (
        not reflected
        and status_bar is not None
        and status_event_count_before is not None
    ):
        for status_events_attr in ('messages', 'calls'):
            status_events = getattr(status_bar, status_events_attr, None)
            if isinstance(status_events, list):
                reflected = len(status_events) > status_event_count_before
                break
    if (
        not reflected
        and status_bar is not None
        and show_message_call_count_before is not None
    ):
        show_message = getattr(status_bar, 'showMessage', None)
        if callable(show_message):
            show_message_call_count_after = getattr(show_message, 'call_count', None)
            if isinstance(show_message_call_count_after, int):
                reflected = show_message_call_count_after > show_message_call_count_before
    return reflected
