from __future__ import annotations

"""Startup preview/target restore helpers for :mod:`tategakiXTC_gui_studio`.

The entry module keeps the MainWindow method names for signal wiring and
regression tests.  The detailed startup-target restore and sample-preview
workflow lives here to keep the large GUI entry module smaller.
"""

import logging
from pathlib import Path
import sys
from typing import Any

from PySide6.QtCore import QTimer as _QTimer
from PySide6.QtWidgets import QMessageBox as _QMessageBox

import tategakiXTC_gui_preview_controller as preview_controller
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_worker_logic as worker_logic
from tategakiXTC_gui_studio_constants import DEFAULT_UI_LANGUAGE
from tategakiXTC_gui_studio_ui_helpers import _bulk_block_signals
from tategakiXTC_gui_studio_widgets import _scroll_combo_popup_to_top_now

APP_LOGGER = logging.getLogger('tategaki_xtc')


def _studio_symbol(name: str, default: Any) -> Any:
    # Keep compatibility with existing tests that monkey-patch symbols on the
    # entry module rather than this helper module.
    module = sys.modules.get('tategakiXTC_gui_studio')
    if module is None:
        return default
    return getattr(module, name, default)


def _qmessage_box() -> Any:
    return _studio_symbol('QMessageBox', _QMessageBox)


def _qtimer() -> Any:
    return _studio_symbol('QTimer', _QTimer)


def _startup_target_text(self: MainWindow) -> str:
    try:
        return worker_logic.normalize_target_path_text(self.target_edit.text())
    except Exception:
        return ''

def _startup_target_path_exists(self: MainWindow, target_text: str) -> bool:
    if not target_text:
        return False
    try:
        return Path(target_text).exists()
    except (OSError, ValueError):
        return False

def _startup_previous_target_display_text(self: MainWindow, target_text: str) -> str:
    try:
        name = Path(target_text).name
    except (OSError, ValueError):
        name = ''
    return name or target_text or self._ui_text('前回の作業ファイル')

def _confirm_startup_previous_target_preview(self: MainWindow, target_text: str) -> bool:
    question = getattr(_qmessage_box(), 'question', None)
    standard_buttons = getattr(_qmessage_box(), 'StandardButton', None)
    yes_button = getattr(_qmessage_box(), 'Yes', getattr(standard_buttons, 'Yes', None))
    no_button = getattr(_qmessage_box(), 'No', getattr(standard_buttons, 'No', None))
    if not callable(question) or yes_button is None or no_button is None:
        return False
    display_name = self._startup_previous_target_display_text(target_text)
    if self._normalize_ui_language(getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE), DEFAULT_UI_LANGUAGE) == 'en':
        dialog_title = 'Previous Work'
        message = (
            'A previous work file was found.\n\n'
            f'{display_name}\n'
            f'{target_text}\n\n'
            'Do you want to continue from the previous work?'
        )
    else:
        dialog_title = '前回の作業'
        message = (
            '前回の作業ファイルが見つかりました。\n\n'
            f'{display_name}\n'
            f'{target_text}\n\n'
            '前回の作業の続きを行いますか？'
        )
    try:
        buttons = yes_button | no_button
    except Exception:
        buttons = yes_button
    try:
        response = question(self, dialog_title, message, buttons, yes_button)
    except TypeError:
        try:
            response = question(self, dialog_title, message)
        except Exception:
            return False
    except Exception:
        return False
    return response == yes_button

def _set_target_path_for_normal_preview(
    self: MainWindow,
    path: object,
    *,
    block_signals: bool = True,
    exit_file_viewer: bool = True,
) -> str:
    """Set the normal conversion target through one guarded path.

    Target changes are initiated by several UI routes: file dialog, drag
    and drop, manual entry, preset restore, and startup helpers.  The
    XTC/XTCH file viewer owns the right-pane page source while it is
    active, so every normal target change must first leave viewer mode.
    Keeping the setText + viewer-exit sequence here prevents the same
    cleanup from being forgotten by a future target-change route.
    """
    normalized_path = worker_logic.normalize_target_path_text(path)
    if exit_file_viewer:
        self._leave_file_viewer_mode_for_target_change()
    target_edit = getattr(self, 'target_edit', None)
    setter = getattr(target_edit, 'setText', None)
    if not callable(setter):
        return normalized_path
    if block_signals:
        try:
            with _bulk_block_signals(target_edit):
                setter(normalized_path)
            return normalized_path
        except Exception:
            pass
    try:
        setter(normalized_path)
    except Exception:
        pass
    return normalized_path

def on_target_text_changed(self: MainWindow, text: object = '') -> None:
    """Leave XTC/XTCH viewer mode as soon as the target field changes.

    Programmatic target updates should normally use
    _set_target_path_for_normal_preview(), but this signal-level guard is
    a low-cost safety net for manual edits or future UI paths that touch
    target_edit directly.
    """
    del text
    try:
        if self._is_file_viewer_mode_active():
            self._leave_file_viewer_mode_for_target_change()
    except Exception:
        APP_LOGGER.exception('変換対象テキスト変更時のファイルビューワー状態解除に失敗しました')

def _clear_startup_target_for_sample_preview(self: MainWindow) -> None:
    self._set_target_path_for_normal_preview('', exit_file_viewer=False)

def _show_startup_sample_preview_status(self: MainWindow, message: str) -> None:
    try:
        self._show_ui_status_message_with_reflection_or_direct_fallback(message, 5000)
    except Exception:
        APP_LOGGER.info(message)

def _request_startup_sample_preview(self: MainWindow) -> bool:
    try:
        refreshed = bool(self.request_preview_refresh(reset_page=True))
    except Exception:
        APP_LOGGER.exception('起動時サンプルプレビューの生成に失敗しました')
        refreshed = False
    try:
        self._schedule_startup_preview_idle_reconcile()
    except Exception:
        pass
    return refreshed

def _schedule_startup_preview_idle_reconcile(self: MainWindow) -> None:
    """Finalize startup preview UI after delayed showEvent work has settled.

    The startup sample/restore preview runs from ``showEvent`` through a
    deferred ``_qtimer().singleShot(0, ...)`` path.  On Windows/PySide6, early
    repaint/resize events can leave the preview progress controls showing
    the start-context text even after the synchronous preview bundle was
    applied.  Keep this guard scoped to startup preview: it only runs after
    the initial sample/restore request and reconciles the controls once all
    running flags are down.
    """

    def _run() -> None:
        self._reconcile_startup_preview_idle_state(remaining_retries=3)

    single_shot = getattr(QTimer, 'singleShot', None)
    if callable(single_shot):
        try:
            single_shot(0, _run)
            return
        except Exception:
            pass
    _run()

def _reconcile_startup_preview_idle_state(
    self: MainWindow, *, remaining_retries: int = 0
) -> None:
    """Force startup preview controls out of stale generating state safely."""
    running = bool(
        getattr(self, '_preview_running', False)
        or getattr(self, '_target_preview_refresh_running', False)
    )
    if running and remaining_retries > 0:
        single_shot = getattr(QTimer, 'singleShot', None)
        if callable(single_shot):
            try:
                single_shot(80, lambda: self._reconcile_startup_preview_idle_state(remaining_retries=remaining_retries - 1))
                return
            except Exception:
                pass
    if running:
        return

    finish_context = preview_controller.build_preview_finish_context()
    try:
        self._apply_preview_progress_bar_context(finish_context)
    except Exception:
        pass
    try:
        self._refresh_preview_update_button_for_current_state(finish_context)
    except Exception:
        pass

    try:
        preview_pages = self._runtime_preview_pages()
    except Exception:
        preview_pages = []
    if preview_pages:
        try:
            requested_limit = max(
                len(preview_pages),
                int(getattr(self, 'last_preview_requested_limit', 0) or 0),
            )
        except Exception:
            requested_limit = len(preview_pages)
        status_state = studio_logic.build_preview_success_status_state(
            page_count=len(preview_pages),
            requested_limit=requested_limit,
            truncated=getattr(self, 'preview_pages_truncated', False),
            language=self.current_ui_language_value(),
        )
        try:
            self._update_preview_status_label(str(status_state.get('status_message', '')))
        except Exception:
            pass
        self.preview_dirty = False

def _request_startup_preview_after_restore(self: MainWindow) -> None:
    target_text = self._startup_target_text()
    if not target_text:
        self._request_startup_sample_preview()
        return

    if not self._startup_target_path_exists(target_text):
        self._clear_startup_target_for_sample_preview()
        self._request_startup_sample_preview()
        self._show_startup_sample_preview_status('前回の作業ファイルが見つからないため、サンプルを表示しました。')
        try:
            self.save_ui_state()
        except Exception:
            pass
        return

    if not self._confirm_startup_previous_target_preview(target_text):
        self._clear_startup_target_for_sample_preview()
        self._request_startup_sample_preview()
        self._show_startup_sample_preview_status('サンプルを表示しました。')
        try:
            self.save_ui_state()
        except Exception:
            pass
        return

    try:
        if self.request_preview_refresh(reset_page=True):
            try:
                self._schedule_startup_preview_idle_reconcile()
            except Exception:
                pass
            return
    except Exception:
        APP_LOGGER.exception('前回作業ファイルの起動時プレビュー生成に失敗しました')

    self._clear_startup_target_for_sample_preview()
    self._request_startup_sample_preview()
    self._show_startup_sample_preview_status('前回の作業ファイルをプレビューできなかったため、サンプルを表示しました。')
    try:
        self.save_ui_state()
    except Exception:
        pass

def _request_startup_sample_preview_if_no_target(self: MainWindow) -> None:
    # 旧テスト/互換用の薄い wrapper。現在は target 復元時の確認もここで扱う。
    self._request_startup_preview_after_restore()

def _startup_font_combo_scroll_reset(self: MainWindow) -> None:
    """起動直後にフォントコンボの内部ビューを先頭へ戻す。"""
    font_combo = getattr(self, 'font_combo', None)
    if font_combo is None:
        return
    scroll_now = _studio_symbol('_scroll_combo_popup_to_top_now', _scroll_combo_popup_to_top_now)
    if callable(scroll_now):
        scroll_now(font_combo)
    reset_popup_scroll = getattr(font_combo, '_reset_popup_scroll_to_top', None)
    if callable(reset_popup_scroll):
        try:
            _qtimer().singleShot(50, reset_popup_scroll)
        except Exception:
            pass
