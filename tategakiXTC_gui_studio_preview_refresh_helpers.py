from __future__ import annotations

"""Preview refresh orchestration helpers for TategakiXTC GUI Studio.

The functions in this module intentionally keep the MainWindow method behavior
unchanged while moving the larger preview refresh / dirty-state control flow out
of ``tategakiXTC_gui_studio.py``.
"""

from typing import Any, Callable, Mapping

from PySide6.QtWidgets import QApplication

import tategakiXTC_gui_core as core
import tategakiXTC_gui_preview_controller as preview_controller
import tategakiXTC_gui_results_controller as results_controller
import tategakiXTC_gui_studio_logic as studio_logic
from tategakiXTC_gui_studio_settings_save_helpers import DEFAULT_PREVIEW_PAGE_LIMIT


def mark_preview_dirty_for_target_change(self: Any) -> None:
    """Mark preview stale after target-path changes without heavy side effects.

    This path intentionally avoids EPUB/archive probing, preview generation,
    XTC/XTCH reading, results-list synchronization, and device-page rendering.
    Target selection should only update lightweight UI state; the preview is
    generated later by manual_refresh_preview().
    """
    self.preview_dirty = True
    self.preview_pages_b64 = []
    self.device_preview_pages_b64 = []
    self.preview_pages_truncated = False
    self.device_preview_pages_truncated = False
    self.current_preview_page_index = 0
    self.current_device_preview_page_index = 0
    self.device_view_source = 'xtc'
    try:
        self._clear_font_preview_page_pixmap_cache()
    except Exception:
        pass
    try:
        self._clear_device_preview_page_qimage_cache()
    except Exception:
        pass
    placeholder = 'プレビューを生成してください'
    if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'font':
        try:
            self._show_preview_message(placeholder)
        except Exception:
            pass
    try:
        self._update_preview_status_label(placeholder)
    except Exception:
        pass
    try:
        self.update_navigation_ui()
    except Exception:
        pass

def mark_preview_dirty(self: Any) -> None:
    try:
        if self._is_file_viewer_mode_active():
            self.preview_dirty = False
            previous_device_source = getattr(self, 'device_view_source', 'xtc')
            if previous_device_source == 'preview':
                self.device_view_source = 'xtc'
                self.current_device_preview_page_index = 0
            try:
                self._sync_loaded_xtc_display_context_for_device_view()
            except Exception:
                pass
            try:
                if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'device' and previous_device_source == 'preview':
                    self.render_current_page(refresh_navigation=True)
            except Exception:
                try:
                    self._clear_xtc_viewer_page(refresh_navigation=True)
                except Exception:
                    pass
            self._apply_file_viewer_mode_preview_button_state()
            return
    except Exception:
        pass
    self.preview_dirty = True
    has_runtime_preview = False
    try:
        has_runtime_preview = bool(self._runtime_preview_pages() or self._runtime_device_preview_pages())
    except Exception:
        has_runtime_preview = False
    if not has_runtime_preview:
        placeholder = 'プレビューを生成してください'
        try:
            self._set_current_xtc_display_name(self._preview_failure_display_name())
        except Exception:
            pass
        try:
            restored_path = self._preview_failure_loaded_path()
            if restored_path:
                self._sync_results_selection_for_loaded_path_with_fallback(restored_path)
            else:
                self._clear_results_selection_with_fallback(
                    results_controller.build_results_clear_selection_context()
                )
        except Exception:
            pass
        normalized_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        previous_device_source = getattr(self, 'device_view_source', 'xtc')
        if previous_device_source == 'preview':
            self.device_view_source = 'xtc'
        self.current_device_preview_page_index = 0
        if normalized_mode == 'font':
            self._show_preview_message(placeholder)
            try:
                self.update_navigation_ui()
            except Exception:
                pass
        if normalized_mode == 'device' and previous_device_source == 'preview':
            try:
                if self._runtime_xtc_pages():
                    self.render_current_page(refresh_navigation=True)
                else:
                    self._clear_xtc_viewer_page(refresh_navigation=True)
            except Exception:
                try:
                    self._clear_xtc_viewer_page(refresh_navigation=True)
                except Exception:
                    pass
        self._update_preview_status_label(placeholder)
        return
    self._mark_preview_update_button_pending()
    self._update_preview_status_label(studio_logic.build_preview_status_message('dirty', language=self.current_ui_language_value()))

def request_preview_refresh(
    self: Any,
    *,
    reset_page: bool = False,
    preview_payload: dict[str, object] | None = None,
) -> bool:
    if getattr(self, '_preview_running', False):
        # プレビュー実行中の追加要求はキューに積まない。
        # ボタン連打や設定 signal の連鎖で、指定ページ数の生成が終わった直後に
        # もう一度プレビューが走ると「暴走」に見えるため、現在の1回だけで止める。
        self._pending_preview_refresh_request = None
        self.preview_dirty = True
        return False
    self._cancel_pending_settings_live_preview_refresh()
    self._preview_running = True
    try:
        self._flush_pending_ui_changes()
        request_plan = preview_controller.build_preview_request_plan(
            dict(preview_payload) if isinstance(preview_payload, Mapping) else self._current_preview_payload(),
            current_output_format=self.current_output_format(),
            default_preview_page_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
        )
        raw_request_payload = request_plan.get('payload', {}) if isinstance(request_plan, Mapping) else {}
        payload = dict(raw_request_payload) if isinstance(raw_request_payload, Mapping) else {}
        preview_limit = max(
            1,
            self._payload_int_value(
                request_plan if isinstance(request_plan, Mapping) else {},
                'preview_limit',
                DEFAULT_PREVIEW_PAGE_LIMIT,
            ),
        )
        self.preview_dirty = False
        process_events = getattr(QApplication, 'processEvents', None)

        def _preview_progress_cb(current: int, total: int, message: str) -> None:
            progress_context = preview_controller.build_preview_progress_context(
                current,
                total,
                message,
                preview_limit=preview_limit,
            )
            self._apply_preview_progress_context(progress_context)
            if callable(process_events):
                process_events()

        try:
            start_context = preview_controller.build_preview_start_context(preview_limit=preview_limit)
            self._apply_preview_button_context(start_context)
            self._apply_preview_progress_context(start_context)
            if callable(process_events):
                process_events()
            bundle = core.generate_preview_bundle(payload, progress_cb=_preview_progress_cb)
            apply_context = preview_controller.build_preview_apply_context(
                bundle,
                reset_page=reset_page,
                current_preview_index=getattr(self, 'current_preview_page_index', 0),
                current_device_index=getattr(self, 'current_device_preview_page_index', 0),
                preview_limit=preview_limit,
                payload=payload,
            )
            return self._apply_preview_success_context(apply_context)
        except Exception as exc:
            error_context = preview_controller.build_preview_failure_context(
                previous_device_source=self._effective_device_view_source(
                    getattr(self, 'device_view_source', 'xtc'),
                ),
                error=exc,
                previous_preview_pages=self._runtime_preview_pages(),
                previous_device_preview_pages=self._runtime_device_preview_pages(),
                previous_preview_page_cache_tokens=list(self.__dict__.get('_preview_page_cache_tokens', []) or []),
                previous_device_preview_page_cache_tokens=list(self.__dict__.get('_device_preview_page_cache_tokens', []) or []),
                previous_preview_pages_truncated=getattr(self, 'preview_pages_truncated', False),
                previous_device_preview_pages_truncated=getattr(self, 'device_preview_pages_truncated', False),
                current_preview_index=getattr(self, 'current_preview_page_index', 0),
                current_device_index=getattr(self, 'current_device_preview_page_index', 0),
            )
            return self._apply_preview_failure_context(error_context)
        finally:
            pass
    finally:
        self._preview_running = False
        self._pending_preview_refresh_request = None
        self._apply_preview_finish_context_after_running_flags_clear()
        try:
            deferred_live_refresh = bool(
                getattr(self, '_settings_preview_refresh_deferred_until_preview_finished', False)
            )
            self._settings_preview_refresh_deferred_until_preview_finished = False
            if deferred_live_refresh and bool(getattr(self, '_settings_preview_refresh_pending', False)):
                reset_page_for_followup = bool(
                    getattr(self, '_settings_preview_refresh_pending_reset_page', False)
                )

                def _run_deferred_live_refresh() -> None:
                    self._schedule_live_preview_refresh(
                        reset_page=reset_page_for_followup,
                        delay_ms=0,
                    )

                if not self._queue_live_preview_refresh_timer(_run_deferred_live_refresh, 0):
                    _run_deferred_live_refresh()
        except Exception:
            pass



def refresh_active_view_after_mode_change(self: Any, mode: object) -> None:
    normalized = self._normalized_main_view_mode(mode)
    try:
        if normalized == 'font':
            self._refresh_font_preview_display_if_needed(refresh_navigation=False)
        else:
            self.render_current_page(refresh_navigation=False)
    except Exception:
        pass


def refresh_font_preview_display_if_needed(
    self: Any,
    refresh_navigation: bool = True,
) -> None:
    if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) != 'font':
        return
    try:
        if self._is_file_viewer_mode_active():
            if self._render_current_xtc_page_in_font_view(refresh_navigation=refresh_navigation):
                return
        if self._runtime_preview_pages():
            try:
                self._set_current_xtc_display_name_with_fallback('プレビュー')
            except Exception:
                pass
            self._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
            self.render_current_preview_page()
        else:
            placeholder = 'プレビューを生成してください'
            try:
                self._set_current_xtc_display_name(self._preview_failure_display_name())
            except Exception:
                pass
            try:
                restored_path = self._preview_failure_loaded_path()
                if restored_path:
                    self._sync_results_selection_for_loaded_path_with_fallback(restored_path)
                else:
                    self._clear_results_selection_with_fallback(
                        results_controller.build_results_clear_selection_context()
                    )
            except Exception:
                pass
            self._show_preview_message(placeholder)
            self._update_preview_status_label(placeholder)
            if refresh_navigation:
                try:
                    self.update_navigation_ui()
                except Exception:
                    pass
    except Exception:
        pass

def schedule_target_preview_refresh(self: Any, *, reset_page: bool = True, timer_class: Any) -> None:
    """Schedule preview refresh after target changes without blocking the picker handler.

    File/folder selection is a UI operation.  Running preview generation
    inline in the same slot can make large EPUB/archive/folder selections
    look like the window froze before labels/buttons have a chance to
    repaint.  Mark the preview stale immediately, then start the bounded
    preview on the next event-loop turn.  Multiple target-change signals
    can be emitted in quick succession, so keep only one deferred preview
    job pending and merge the reset-page flag safely.  If another target
    change arrives while that deferred refresh is already running, queue one
    follow-up refresh instead of starting a nested preview refresh.
    """
    try:
        self.mark_preview_dirty_for_target_change()
    except Exception:
        try:
            self.mark_preview_dirty()
        except Exception:
            pass

    self._apply_preview_pending_progress_context('プレビュー対象を読み込んでいます…')

    pending_reset_page = bool(reset_page) or bool(
        getattr(self, '_target_preview_refresh_pending_reset_page', False)
    )
    self._target_preview_refresh_pending_reset_page = pending_reset_page
    if getattr(self, '_target_preview_refresh_running', False):
        self._target_preview_refresh_rerun_requested = True
        return
    if getattr(self, '_target_preview_refresh_scheduled', False):
        return
    self._target_preview_refresh_scheduled = True

    def _queue_target_preview_refresh_run(callback: Callable[[], None]) -> None:
        single_shot = getattr(timer_class, 'singleShot', None)
        if callable(single_shot):
            try:
                single_shot(0, callback)
                return
            except Exception:
                # If Qt rejects the deferred callback, fall back to an inline
                # run using the pending state that was already merged above.
                # Do not clear flags here: _run_target_preview_refresh() is
                # the single cleanup point.
                pass
        callback()

    def _run_target_preview_refresh() -> None:
        reset_page_for_run = bool(
            getattr(self, '_target_preview_refresh_pending_reset_page', reset_page)
        )
        self._target_preview_refresh_scheduled = False
        self._target_preview_refresh_pending_reset_page = False
        self._target_preview_refresh_running = True
        try:
            self.request_preview_refresh(reset_page=reset_page_for_run)
        finally:
            self._target_preview_refresh_running = False
            rerun_requested = bool(
                getattr(self, '_target_preview_refresh_rerun_requested', False)
            )
            self._target_preview_refresh_rerun_requested = False
            if rerun_requested:
                self._target_preview_refresh_scheduled = True
                _queue_target_preview_refresh_run(_run_target_preview_refresh)
            else:
                self._apply_preview_finish_context_after_running_flags_clear()

    _queue_target_preview_refresh_run(_run_target_preview_refresh)
