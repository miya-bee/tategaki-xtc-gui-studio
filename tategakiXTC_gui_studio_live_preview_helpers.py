from __future__ import annotations

"""Live/debounced preview refresh helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window.mark_preview_dirty`` etc.), so instance-level overrides installed by
tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``; the ``QTimer`` single-shot scheduler
(``_queue_live_preview_refresh_timer``) and the tuning constants stay in the
entry module, the latter passed in as keyword arguments.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

import tategakiXTC_gui_preview_controller as preview_controller

from tategakiXTC_gui_studio_constants import DEFAULT_PREVIEW_PAGE_LIMIT
from tategakiXTC_gui_studio_preview_helpers import (
    _preview_page_limit_value,
    _manual_preview_required_status_message as _manual_preview_required_status_message_for_limit,
)


def _mark_preview_dirty_from_signal(window: Any, *_args: object) -> None:
    window._mark_preview_dirty_without_auto_refresh()


def _current_preview_page_limit_value(window: Any) -> int:
    return _preview_page_limit_value(
        getattr(window, 'preview_page_limit_spin', None),
        default_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
    )


def _should_auto_live_preview_refresh(window: Any, *, auto_refresh_max: int) -> bool:
    return window._current_preview_page_limit_value() <= auto_refresh_max


def _manual_preview_required_status_message(window: Any, *, auto_refresh_max: int) -> str:
    return _manual_preview_required_status_message_for_limit(
        preview_limit=window._current_preview_page_limit_value(),
        auto_refresh_max=auto_refresh_max,
    )


def _mark_preview_dirty_without_auto_refresh(window: Any, *, auto_refresh_max: int) -> None:
    try:
        window.mark_preview_dirty()
    except Exception:
        pass
    if window._current_preview_page_limit_value() > auto_refresh_max:
        try:
            window._cancel_auto_live_preview_due_to_large_limit()
        except Exception:
            pass
        try:
            window._apply_manual_preview_required_context()
        except Exception:
            pass


def _schedule_live_preview_refresh_from_signal(window: Any, *_args: object) -> None:
    window._schedule_live_preview_refresh(reset_page=False)


def _has_refreshable_preview_target(window: Any) -> bool:
    """Return True when settings changes can regenerate a preview from the current target.

    Live preview must keep working even after an intermediate UI action clears
    the cached preview pages.  In that state the presence of an existing
    target path is enough to allow a debounced settings refresh to rebuild
    the preview instead of silently falling back to a dirty placeholder.
    """
    try:
        payload = window._current_preview_payload()
    except Exception:
        payload = {}
    target_text = ''
    if isinstance(payload, Mapping):
        # build_preview_payload() exposes the selected file as ``target_path``.
        # Keep ``target`` as a compatibility fallback for older tests/helpers.
        target_text = str(payload.get('target_path') or payload.get('target') or '').strip()
    if target_text:
        try:
            return Path(target_text).exists()
        except (OSError, ValueError):
            return False
    image_data_url = ''
    if isinstance(payload, Mapping):
        # Image-preview payloads use ``file_b64``; the previous
        # ``preview_image_data_url`` key is accepted as a fallback only.
        image_data_url = str(payload.get('file_b64') or payload.get('preview_image_data_url') or '').strip()
    return bool(image_data_url)


def _has_active_preview_for_live_refresh(window: Any) -> bool:
    font_view_active = window._normalized_main_view_mode(
        getattr(window, 'main_view_mode', 'font')
    ) == 'font'
    try:
        has_font_preview = bool(window._runtime_preview_pages())
    except Exception:
        has_font_preview = False
    try:
        device_preview_active = window._effective_device_view_source() == 'preview'
    except Exception:
        device_preview_active = False
    try:
        has_device_preview = bool(window._runtime_device_preview_pages())
    except Exception:
        has_device_preview = False
    has_runtime_preview = bool((font_view_active and has_font_preview) or (device_preview_active and has_device_preview))
    return bool(has_runtime_preview or window._has_refreshable_preview_target())


def _cancel_pending_settings_live_preview_refresh(window: Any) -> None:
    # v1.3.5: 手動の「プレビュー更新」が開始された時点で、設定変更由来の
    # live-preview timer を無効化する。未処理 timer が request_preview_refresh()
    # 冒頭の processEvents() 中に発火すると、生成完了後に後続 preview を予約し、
    # 「プレビュー更新で暴走」して見えるため。QTimer.singleShot 自体はキャンセル
    # できないので generation を進め、pending/deferred 状態も明示的に落とす。
    try:
        window._settings_preview_refresh_generation = int(
            getattr(window, '_settings_preview_refresh_generation', 0) or 0
        ) + 1
    except Exception:
        window._settings_preview_refresh_generation = 1
    window._settings_preview_refresh_pending = False
    window._settings_preview_refresh_pending_reset_page = False
    window._settings_preview_refresh_scheduled = False
    window._settings_preview_refresh_deferred_until_preview_finished = False


def _schedule_live_preview_refresh(
    window: Any,
    *,
    reset_page: bool = False,
    delay_ms: int,
) -> bool:
    """Debounce appearance/layout setting changes into one preview refresh.

    Font size, ruby size, line spacing, margins, kinsoku mode, glyph-position
    correction, font choice, and output format all affect the preview image.
    Running a full preview for every spin-box step is wasteful, so keep the
    preview visibly stale immediately and let only the newest timer callback
    regenerate the preview after the event stream settles.  When no preview
    has been generated yet, fall back to the existing dirty placeholder
    instead of starting an empty refresh.
    """
    try:
        if window._is_file_viewer_mode_active():
            window._cancel_auto_live_preview_due_to_large_limit()
            window._apply_file_viewer_mode_preview_button_state()
            try:
                window._apply_preview_progress_bar_context(preview_controller.build_preview_finish_context())
            except Exception:
                pass
            return False
    except Exception:
        pass

    if not window._has_active_preview_for_live_refresh():
        try:
            window.mark_preview_dirty()
        except Exception:
            pass
        try:
            window._apply_preview_progress_bar_context(preview_controller.build_preview_finish_context())
        except Exception:
            pass
        return False

    if not window._should_auto_live_preview_refresh():
        try:
            window.mark_preview_dirty()
        except Exception:
            pass
        window._cancel_auto_live_preview_due_to_large_limit()
        try:
            window._apply_manual_preview_required_context()
        except Exception:
            pass
        return True

    try:
        window.mark_preview_dirty()
    except Exception:
        pass

    generation = int(getattr(window, '_settings_preview_refresh_generation', 0) or 0) + 1
    window._settings_preview_refresh_generation = generation
    window._settings_preview_refresh_pending = True
    window._settings_preview_refresh_pending_reset_page = bool(reset_page) or bool(
        getattr(window, '_settings_preview_refresh_pending_reset_page', False)
    )
    window._settings_preview_refresh_scheduled = True
    window._mark_preview_update_button_pending()
    window._apply_preview_pending_progress_context('設定変更を反映するプレビュー更新を準備しています…')

    def _run_live_preview_refresh(expected_generation: int) -> None:
        if expected_generation != int(getattr(window, '_settings_preview_refresh_generation', 0) or 0):
            return
        window._settings_preview_refresh_scheduled = False
        if not bool(getattr(window, '_settings_preview_refresh_pending', False)):
            return
        if bool(getattr(window, '_preview_running', False)):
            # v1.3.3.45: プレビュー生成中に設定変更が入った場合、50ms 間隔で
            # 完了待ちポーリングを積み続けない。ディザリング ON のように重い
            # プレビューでは、このポーリングが「更新状態で暴走」に見えるため、
            # 現在の生成完了後に 1 回だけ後続更新を予約する。
            window._settings_preview_refresh_scheduled = False
            window._settings_preview_refresh_deferred_until_preview_finished = True
            return
        reset_page_for_run = bool(
            getattr(window, '_settings_preview_refresh_pending_reset_page', reset_page)
        )
        window._settings_preview_refresh_pending = False
        window._settings_preview_refresh_pending_reset_page = False
        try:
            refreshed = bool(window.request_preview_refresh(reset_page=reset_page_for_run))
        except Exception:
            refreshed = False
        if not refreshed:
            try:
                window.mark_preview_dirty()
            except Exception:
                pass

    if window._queue_live_preview_refresh_timer(lambda: _run_live_preview_refresh(generation), delay_ms):
        return True
    window._settings_preview_refresh_scheduled = False
    _run_live_preview_refresh(generation)
    return True
