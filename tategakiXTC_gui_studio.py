from __future__ import annotations

"""
tategakiXTC_gui_studio.py — GUI 本体

PySide6 ベースの縦書き XTC 変換ツール。
変換ロジックは tategakiXTC_gui_core.py に分離されています。
"""

import base64
import math
from collections import OrderedDict
import logging
import locale
import os
import ntpath
import subprocess
import sys
import shutil
import threading
import tempfile
from datetime import datetime
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from tategakiXTC_gui_studio_logging import (
    DEFAULT_LOG_RETENTION_DAYS as LOG_RETENTION_DAYS,
    DEFAULT_LOG_RETENTION_MAX_FILES as LOG_RETENTION_MAX_FILES,
    cleanup_old_session_logs as _cleanup_old_session_logs,
)

from tategakiXTC_gui_studio_startup import (
    collect_missing_startup_dependencies as _collect_missing_startup_dependencies_impl,
    show_startup_dependency_alert as _show_startup_dependency_alert_impl,
)

_STARTUP_DEPENDENCIES = [
    ('PySide6', 'PySide6'),
    ('Pillow', 'PIL'),
]


def _collect_missing_startup_dependencies() -> list[str]:
    return _collect_missing_startup_dependencies_impl(_STARTUP_DEPENDENCIES)


def _show_startup_dependency_alert(missing_packages: list[str]) -> None:
    _show_startup_dependency_alert_impl(missing_packages)


_missing_startup_packages = _collect_missing_startup_dependencies()
if _missing_startup_packages:
    _show_startup_dependency_alert(_missing_startup_packages)
    sys.exit(1)

APP_LOGGER_NAME = 'tategaki_xtc'
LOG_DIR = Path(__file__).resolve().parent / 'logs'
FALLBACK_LOG_DIR = Path(tempfile.gettempdir()) / 'tategaki_xtc_logs'
ACTIVE_LOG_DIR: Path | None = None
SESSION_LOG_PATH: Path | None = None
_XTC_PAGE_QIMAGE_CACHE_LIMIT = 8
_DEVICE_PREVIEW_PAGE_QIMAGE_CACHE_LIMIT = 8
_FONT_PREVIEW_PAGE_PIXMAP_CACHE_LIMIT = 8
_SETTINGS_PREVIEW_REFRESH_DELAY_MS = 350
_AUTO_LIVE_PREVIEW_PAGE_LIMIT_MAX = 20


def _log_dir_accepts_log_file(candidate: Path) -> bool:
    """Return whether a directory can actually create a log file.

    Some readonly deployments can have an existing ``logs/`` directory, so
    mkdir(success) is not enough.  Probe a tiny file before selecting the app
    local log folder; otherwise fall back to the temporary log folder and keep
    the GUI startable.
    """

    probe = candidate / f'.tategaki_log_write_test_{os.getpid()}'
    try:
        with probe.open('w', encoding='utf-8') as fp:
            fp.write('')
    except Exception:
        try:
            probe.unlink(missing_ok=True)
        except Exception:
            pass
        return False
    try:
        probe.unlink(missing_ok=True)
    except Exception:
        pass
    return True


def _resolve_log_dir() -> Path:
    global ACTIVE_LOG_DIR
    if isinstance(ACTIVE_LOG_DIR, Path):
        return ACTIVE_LOG_DIR
    last_error: Exception | None = None
    for candidate in (LOG_DIR, FALLBACK_LOG_DIR):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if not _log_dir_accepts_log_file(candidate):
                raise PermissionError(f'ログ保存先へ書き込めません: {candidate}')
        except Exception as exc:
            last_error = exc
            continue
        ACTIVE_LOG_DIR = candidate
        return candidate
    if last_error is not None:
        raise last_error
    raise RuntimeError('ログ保存先を作成できませんでした。')


def _new_session_log_path(log_dir: Path) -> Path:
    return log_dir / f'tategakiXTC_gui_studio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'


def _session_log_path_for_display() -> Path:
    """Return a log path safe to show in the UI without raising.

    ``_resolve_session_log_path`` re-resolves the log directory and intentionally
    raises when neither the app ``logs/`` folder nor the temporary fallback is
    writable.  When the app has fallen back to stderr-only logging, building the
    log tab must not crash, so degrade to the active (or default) log directory
    for display purposes only.
    """

    try:
        return _resolve_session_log_path()
    except Exception:
        APP_LOGGER.exception('ログ保存先の解決に失敗しました。既定のログフォルダを表示します。')
        return ACTIVE_LOG_DIR or LOG_DIR


def _resolve_session_log_path() -> Path:
    global SESSION_LOG_PATH
    if isinstance(SESSION_LOG_PATH, Path):
        return SESSION_LOG_PATH
    log_dir = _resolve_log_dir()
    SESSION_LOG_PATH = log_dir / f'tategakiXTC_gui_studio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    return SESSION_LOG_PATH


def _try_create_session_file_handler(
    log_dir: Path,
    formatter: logging.Formatter,
) -> tuple[logging.FileHandler | None, Path | None, Exception | None]:
    global ACTIVE_LOG_DIR, SESSION_LOG_PATH
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        if not _log_dir_accepts_log_file(log_dir):
            raise PermissionError(f'ログ保存先へ書き込めません: {log_dir}')
        active_log_dir = log_dir
        session_log_path = _new_session_log_path(active_log_dir)
        _cleanup_old_session_logs(active_log_dir, active_log_path=session_log_path)
        file_handler = logging.FileHandler(session_log_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
    except Exception as exc:
        return None, None, exc
    ACTIVE_LOG_DIR = log_dir
    SESSION_LOG_PATH = session_log_path
    return file_handler, session_log_path, None


def _configure_app_logging() -> logging.Logger:
    global ACTIVE_LOG_DIR, SESSION_LOG_PATH
    logger = logging.getLogger(APP_LOGGER_NAME)
    if getattr(logger, '_tategaki_configured', False):
        return logger

    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler: logging.FileHandler | None = None
    session_log_path: Path | None = None
    log_error: Exception | None = None
    for candidate in (LOG_DIR, FALLBACK_LOG_DIR):
        file_handler, session_log_path, log_error = _try_create_session_file_handler(candidate, formatter)
        if file_handler is not None:
            logger.addHandler(file_handler)
            break

    logger.propagate = False
    logger._tategaki_configured = True
    active_log_dir = ACTIVE_LOG_DIR
    if file_handler is None:
        logger.warning('ログファイルを作成できなかったため、標準エラー出力のみで続行します: %s', log_error)
    elif active_log_dir != LOG_DIR:
        logger.warning('既定のログフォルダへ書き込めなかったため、一時フォルダへ退避します: %s', active_log_dir)
    logger.info('ログ初期化: %s', session_log_path if session_log_path is not None else 'stderr-only')
    return logger


APP_LOGGER = logging.getLogger(APP_LOGGER_NAME)


from PySide6.QtCore import Qt, QObject, QThread, Signal, QSize, QSettings, QRect, QRectF, QTimer, QEvent, QPoint
from PySide6.QtGui import QActionGroup, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QScrollBar,
    QSplitter,
    QStackedWidget,
    QSpinBox,
    QStyle,
    QStyleOptionSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import tategakiXTC_gui_core as core
import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_layouts as gui_layouts
import tategakiXTC_gui_preview_controller as preview_controller
import tategakiXTC_gui_results_controller as results_controller
import tategakiXTC_gui_settings_controller as settings_controller
import tategakiXTC_gui_widget_factory as gui_widget_factory
from tategakiXTC_gui_core import ConversionArgs

WorkerConversionSettings = worker_logic.WorkerConversionSettings
ConversionErrorItem = worker_logic.ConversionErrorItem

from tategakiXTC_gui_studio_ui_helpers import (
    _bulk_block_signals,
    _coerce_ui_message_text,
    _connect_signal_best_effort,
    flush_pending_ui_changes as _flush_pending_ui_changes_impl,
    _safe_delete_qobject_later,
)

from tategakiXTC_gui_studio_dependency_helpers import (
    check_conversion_dependencies as _check_conversion_dependencies_impl,
    log_optional_dependency_status as _log_optional_dependency_status_impl,
    missing_dependencies_for_targets as _missing_dependencies_for_targets_impl,
)

from tategakiXTC_gui_studio_dialog_helpers import (
    ask_question_dialog_with_status_fallback as _ask_question_dialog_with_status_fallback_impl,
    get_existing_directory_with_status_fallback as _get_existing_directory_with_status_fallback_impl,
    get_open_file_name_with_status_fallback as _get_open_file_name_with_status_fallback_impl,
    show_critical_dialog_with_status_fallback as _show_critical_dialog_with_status_fallback_impl,
    show_information_dialog_with_status_fallback as _show_information_dialog_with_status_fallback_impl,
    show_warning_dialog_with_status_fallback as _show_warning_dialog_with_status_fallback_impl,
)

from tategakiXTC_gui_studio_desktop import (
    _open_path_in_file_manager,
)

from tategakiXTC_gui_studio_display_settings_menu_helpers import (
    show_display_settings_popup as _show_display_settings_popup_impl,
)

from tategakiXTC_gui_studio_top_bar_helpers import (
    build_top_bar as _build_top_bar_impl,
    _install_folder_batch_menu_action as _install_folder_batch_menu_action_impl,
    _open_folder_batch_dialog as _open_folder_batch_dialog_impl,
)

from tategakiXTC_gui_studio_preview_controls_helpers import (
    build_margin_rows as _build_margin_rows_impl,
    section_preview_controls as _section_preview_controls_impl,
)

from tategakiXTC_gui_studio_settings_sections_helpers import (
    _section_output as _section_output_impl,
    _section_composition as _section_composition_impl,
    _section_position as _section_position_impl,
    _section_language as _section_language_impl,
    _section_preset as _section_preset_impl,
    _make_position_mode_combo as _make_position_mode_combo_impl,
    _make_glyph_position_combo as _make_glyph_position_combo_impl,
    _add_glyph_position_control as _add_glyph_position_control_impl,
    _ensure_behavior_controls as _ensure_behavior_controls_impl,
    _section_behavior as _section_behavior_impl,
    _section_file_viewer as _section_file_viewer_impl,
)

from tategakiXTC_gui_studio_font_combo_helpers import (
    current_font_value as current_font_value_impl,
    _available_font_entries as _available_font_entries_impl,
    _populate_font_combo as _populate_font_combo_impl,
    _missing_font_combo_label as _missing_font_combo_label_impl,
    _ensure_font_combo_value as _ensure_font_combo_value_impl,
    _set_current_font_value as _set_current_font_value_impl,
    _default_font_name as _default_font_name_impl,
    _apply_default_font_selection as _apply_default_font_selection_impl,
)

from tategakiXTC_gui_studio_target_select_helpers import (
    _apply_dropped_target_path as _apply_dropped_target_path_impl,
    _default_output_folder_start_dir as _default_output_folder_start_dir_impl,
    _selected_output_dir_label_text as _selected_output_dir_label_text_impl,
    _announce_selected_output_dir as _announce_selected_output_dir_impl,
    reset_output_folder as reset_output_folder_impl,
    select_output_folder as select_output_folder_impl,
    select_target_path as select_target_path_impl,
    select_font_file as select_font_file_impl,
)


from tategakiXTC_gui_studio_sns_export_helpers import (
    export_current_preview_share_png as export_current_preview_share_png_impl,
)

from tategakiXTC_gui_studio_preview_pixmap_helpers import (
    _decorate_font_view_pixmap as _decorate_font_view_pixmap_impl,
    _preview_pixmap_from_png_bytes as _preview_pixmap_from_png_bytes_impl,
    _apply_preview_pixmap as _apply_preview_pixmap_impl,
    _apply_preview_png_bytes as _apply_preview_png_bytes_impl,
    _apply_preview_page_base64_to_label as _apply_preview_page_base64_to_label_impl,
    _render_current_xtc_page_in_font_view as _render_current_xtc_page_in_font_view_impl,
    render_current_preview_page as render_current_preview_page_impl,
)

from tategakiXTC_gui_studio_bottom_panel_helpers import (
    build_bottom_panel as _build_bottom_panel_impl,
    build_results_tab as _build_results_tab_impl,
    build_log_tab as _build_log_tab_impl,
    active_bottom_panel_scrollbar as _active_bottom_panel_scrollbar_impl,
    bind_bottom_panel_external_scrollbar as _bind_bottom_panel_external_scrollbar_impl,
    set_bottom_panel_external_scrollbar_range as _set_bottom_panel_external_scrollbar_range_impl,
    sync_bottom_panel_external_scrollbar as _sync_bottom_panel_external_scrollbar_impl,
    apply_bottom_panel_external_scroll_value as _apply_bottom_panel_external_scroll_value_impl,
)

from tategakiXTC_gui_studio_preview_helpers import (
    _coerce_preview_base64_text,
    _coerce_preview_data_url,
    _manual_preview_required_status_message as _manual_preview_required_status_message_for_limit,
    _preview_page_limit_value,
    _preview_widget_limit_value,
)

from tategakiXTC_gui_studio_path_helpers import (
    _supported_targets_for_path,
    _default_output_name_for_target,
)

from tategakiXTC_gui_styles import (
    dark_stylesheet,
    light_stylesheet,
)
from tategakiXTC_gui_help_texts import (
    usage_help_text,
)

from tategakiXTC_gui_preset_helpers import (
    normalize_preset_display_name,
    preset_combo_entries,
    preset_display_name_settings_key,
    preset_settings_prefix,
    preset_side_summary_text,
    selected_preset_key_from_combo,
)

from tategakiXTC_gui_completion_helpers import (
    build_conversion_completion_card_message,
    completion_card_parent_texts,
    completion_card_result_item_texts,
)

from tategakiXTC_gui_studio_conversion_finish_helpers import (
    handle_conversion_finished as _handle_conversion_finished_impl,
    build_conversion_completion_summary_lines as _build_conversion_completion_summary_lines_impl,
    apply_conversion_completion_guidance_to_results_view as _apply_conversion_completion_guidance_to_results_view_impl,
)

from tategakiXTC_gui_studio_conversion_runtime_helpers import (
    set_worker_controls_running as _set_worker_controls_running_impl,
    prepare_conversion_ui_for_run as _prepare_conversion_ui_for_run_impl,
    apply_direct_conversion_terminal_fallback as _apply_direct_conversion_terminal_fallback_impl,
    apply_conversion_terminal_state as _apply_conversion_terminal_state_impl,
    build_conversion_failure_summary_text as _build_conversion_failure_summary_text_impl,
    apply_conversion_failure_ui as _apply_conversion_failure_ui_impl,
    handle_conversion_startup_failure as _handle_conversion_startup_failure_impl,
    next_conversion_run_token as _next_conversion_run_token_impl,
    clear_active_conversion_run_token as _clear_active_conversion_run_token_impl,
    is_active_conversion_run_token as _is_active_conversion_run_token_impl,
    connect_worker_dispatch_signals as _connect_worker_dispatch_signals_impl,
    emit_worker_finished_request as _emit_worker_finished_request_impl,
    emit_worker_error_request as _emit_worker_error_request_impl,
    emit_worker_log_request as _emit_worker_log_request_impl,
    emit_worker_progress_request as _emit_worker_progress_request_impl,
    emit_worker_cleanup_request as _emit_worker_cleanup_request_impl,
    dispatch_worker_cleanup as _dispatch_worker_cleanup_impl,
    dispatch_worker_log as _dispatch_worker_log_impl,
    dispatch_conversion_progress as _dispatch_conversion_progress_impl,
    dispatch_conversion_finished as _dispatch_conversion_finished_impl,
    dispatch_conversion_error as _dispatch_conversion_error_impl,
    start_conversion as _start_conversion_impl,
    stop_conversion as _stop_conversion_impl,
    schedule_cleanup_worker as _schedule_cleanup_worker_impl,
    cleanup_worker as _cleanup_worker_impl,
    handle_conversion_error as _handle_conversion_error_impl,
    update_conversion_progress as _update_conversion_progress_impl,
)

from tategakiXTC_gui_studio_startup_preview_helpers import (
    _startup_target_text as _startup_target_text_impl,
    _startup_target_path_exists as _startup_target_path_exists_impl,
    _startup_previous_target_display_text as _startup_previous_target_display_text_impl,
    _confirm_startup_previous_target_preview as _confirm_startup_previous_target_preview_impl,
    _set_target_path_for_normal_preview as _set_target_path_for_normal_preview_impl,
    on_target_text_changed as on_target_text_changed_impl,
    _clear_startup_target_for_sample_preview as _clear_startup_target_for_sample_preview_impl,
    _show_startup_sample_preview_status as _show_startup_sample_preview_status_impl,
    _request_startup_sample_preview as _request_startup_sample_preview_impl,
    _schedule_startup_preview_idle_reconcile as _schedule_startup_preview_idle_reconcile_impl,
    _reconcile_startup_preview_idle_state as _reconcile_startup_preview_idle_state_impl,
    _request_startup_preview_after_restore as _request_startup_preview_after_restore_impl,
    _request_startup_sample_preview_if_no_target as _request_startup_sample_preview_if_no_target_impl,
    _startup_font_combo_scroll_reset as _startup_font_combo_scroll_reset_impl,
)

from tategakiXTC_gui_studio_view_helpers import (
    _normalized_main_view_mode,
    _preview_view_help_text,
    _main_view_mode_help_text,
    _main_view_mode_status_text,
)

from tategakiXTC_gui_studio_settings_helpers import (
    _settings_raw_value as _settings_raw_value_from_store,
    _settings_contains_key as _settings_contains_key_in_store,
    _settings_int_value as _settings_int_value_from_store,
    _settings_bool_value as _settings_bool_value_from_store,
    _settings_str_value as _settings_str_value_from_store,
    _coerce_mapping_payload as _coerce_mapping_payload_value,
    _plan_int_value as _plan_int_value_from_payload,
    _plan_bool_value as _plan_bool_value_from_payload,
    _plan_int_tuple_value as _plan_int_tuple_value_from_payload,
    _plan_token_value as _plan_token_value_from_payload,
    _combo_find_data_index as _combo_find_data_index_for_widget,
)

from tategakiXTC_gui_studio_runtime import (
    _iter_runtime_xtc_page_items,
    _normalize_runtime_xtc_pages,
)

from tategakiXTC_gui_studio_render_status_helpers import (
    _current_preview_success_status_message as _current_preview_success_status_message_impl,
    _current_preview_render_status_message as _current_preview_render_status_message_impl,
    _refresh_successful_preview_render_status as _refresh_successful_preview_render_status_impl,
    _refresh_successful_device_render_status as _refresh_successful_device_render_status_impl,
    _render_failure_status_message as _render_failure_status_message_impl,
    _handle_xtc_render_failure as _handle_xtc_render_failure_impl,
)

from tategakiXTC_gui_studio_display_context_helpers import (
    _set_current_xtc_display_name as _set_current_xtc_display_name_impl,
    _set_current_xtc_display_name_with_fallback as _set_current_xtc_display_name_with_fallback_impl,
    _sync_loaded_xtc_display_context_for_device_view as _sync_loaded_xtc_display_context_for_device_view_impl,
    _sync_preview_display_context_for_device_view as _sync_preview_display_context_for_device_view_impl,
    _sync_blank_device_display_context as _sync_blank_device_display_context_impl,
    _restore_shared_status_for_visible_display_context as _restore_shared_status_for_visible_display_context_impl,
    _sync_active_display_context_for_visible_page as _sync_active_display_context_for_visible_page_impl,
)

from tategakiXTC_gui_studio_preview_context_helpers import (
    _normalized_preview_page_cache_tokens as _normalized_preview_page_cache_tokens_impl,
    _normalized_right_pane_source_value as _normalized_right_pane_source_value_impl,
    _normalized_device_view_source_value as _normalized_device_view_source_value_impl,
    _effective_right_pane_source as _effective_right_pane_source_impl,
    _effective_device_view_source as _effective_device_view_source_impl,
    _is_preview_display_active as _is_preview_display_active_impl,
    _apply_preview_page_cache_tokens_context as _apply_preview_page_cache_tokens_context_impl,
    _apply_preview_button_context as _apply_preview_button_context_impl,
    _apply_preview_progress_bar_context as _apply_preview_progress_bar_context_impl,
    _apply_preview_progress_context as _apply_preview_progress_context_impl,
    _apply_preview_pending_progress_context as _apply_preview_pending_progress_context_impl,
    _apply_preview_finish_context_after_running_flags_clear as _apply_preview_finish_context_after_running_flags_clear_impl,
    _apply_preview_success_context as _apply_preview_success_context_impl,
    _preview_failure_display_name as _preview_failure_display_name_impl,
    _preview_failure_loaded_path as _preview_failure_loaded_path_impl,
    _apply_preview_failure_context as _apply_preview_failure_context_impl,
)

from tategakiXTC_gui_studio_preview_refresh_helpers import (
    mark_preview_dirty_for_target_change as _mark_preview_dirty_for_target_change_impl,
    mark_preview_dirty as _mark_preview_dirty_impl,
    request_preview_refresh as _request_preview_refresh_impl,
    schedule_target_preview_refresh as _schedule_target_preview_refresh_impl,
    refresh_active_view_after_mode_change as _refresh_active_view_after_mode_change_impl,
    refresh_font_preview_display_if_needed as _refresh_font_preview_display_if_needed_impl,
)

from tategakiXTC_gui_studio_preview_button_helpers import (
    _apply_manual_preview_required_context as _apply_manual_preview_required_context_impl,
    _cancel_auto_live_preview_due_to_large_limit as _cancel_auto_live_preview_due_to_large_limit_impl,
    _set_preview_update_button_visual_state as _set_preview_update_button_visual_state_impl,
    _has_loaded_xtc_viewer_document as _has_loaded_xtc_viewer_document_impl,
    _is_file_viewer_mode_active as _is_file_viewer_mode_active_impl,
    _apply_file_viewer_mode_preview_button_state as _apply_file_viewer_mode_preview_button_state_impl,
    _restore_preview_update_button_from_file_viewer_state as _restore_preview_update_button_from_file_viewer_state_impl,
    _refresh_preview_update_button_for_current_state as _refresh_preview_update_button_for_current_state_impl,
    _mark_preview_update_button_pending as _mark_preview_update_button_pending_impl,
)

from tategakiXTC_gui_studio_overlay_margin_helpers import (
    _minimum_bottom_overlay_margin as _minimum_bottom_overlay_margin_impl,
    _effective_bottom_overlay_margin as _effective_bottom_overlay_margin_impl,
    _current_bottom_overlay_margin_auto_state as _current_bottom_overlay_margin_auto_state_impl,
    _restore_bottom_overlay_margin_auto_state_from_payload as _restore_bottom_overlay_margin_auto_state_from_payload_impl,
    _bottom_overlay_margin_auto_save_payload as _bottom_overlay_margin_auto_save_payload_impl,
    _clear_bottom_overlay_margin_auto_state_if_bottom_margin_was_edited as _clear_bottom_overlay_margin_auto_state_if_bottom_margin_was_edited_impl,
    _sync_bottom_overlay_margin_to_ui as _sync_bottom_overlay_margin_to_ui_impl,
)

from tategakiXTC_gui_studio_live_preview_helpers import (
    _mark_preview_dirty_from_signal as _mark_preview_dirty_from_signal_impl,
    _current_preview_page_limit_value as _current_preview_page_limit_value_impl,
    _should_auto_live_preview_refresh as _should_auto_live_preview_refresh_impl,
    _manual_preview_required_status_message as _manual_preview_required_status_message_impl,
    _mark_preview_dirty_without_auto_refresh as _mark_preview_dirty_without_auto_refresh_impl,
    _schedule_live_preview_refresh_from_signal as _schedule_live_preview_refresh_from_signal_impl,
    _has_refreshable_preview_target as _has_refreshable_preview_target_impl,
    _has_active_preview_for_live_refresh as _has_active_preview_for_live_refresh_impl,
    _cancel_pending_settings_live_preview_refresh as _cancel_pending_settings_live_preview_refresh_impl,
    _schedule_live_preview_refresh as _schedule_live_preview_refresh_impl,
)

from tategakiXTC_gui_studio_settings_save_helpers import (
    _current_render_settings_base as _current_render_settings_base_impl,
    current_settings_dict as current_settings_dict_impl,
    _folder_batch_worker_settings as _folder_batch_worker_settings_impl,
    _window_state_save_payload as _window_state_save_payload_impl,
    _settings_save_payload as _settings_save_payload_impl,
    prepare_conversion_settings as _prepare_conversion_settings_impl,
)

from tategakiXTC_gui_studio_settings_restore_helpers import (
    apply_settings_payload_to_ui as _apply_settings_payload_to_ui_impl,
    restore_settings as _restore_settings_impl,
    _has_restorable_user_settings as _has_restorable_user_settings_impl,
    _window_state_restore_payload as _window_state_restore_payload_impl,
    _settings_restore_payload as _settings_restore_payload_impl,
    _startup_preview_defaults_payload as _startup_preview_defaults_payload_impl,
)

from tategakiXTC_gui_studio_navigation_helpers import (
    _xtc_page_count as _xtc_page_count_impl,
    _normalized_device_preview_page_index as _normalized_device_preview_page_index_impl,
    _normalized_xtc_page_index as _normalized_xtc_page_index_impl,
    _xtc_page_state_payload as _xtc_page_state_payload_impl,
    _xtc_navigation_payload as _xtc_navigation_payload_impl,
    _apply_xtc_navigation_ui as _apply_xtc_navigation_ui_impl,
    update_navigation_ui as update_navigation_ui_impl,
)

from tategakiXTC_gui_studio_preset_actions_helpers import (
    verify_preset_save_readback as _verify_preset_save_readback_impl,
    show_preset_save_failed as _show_preset_save_failed_impl,
    request_preview_refresh_after_preset_apply as _request_preview_refresh_after_preset_apply_impl,
    preset_save_confirmation_text as _preset_save_confirmation_text_impl,
    preset_rename_dialog_result as _preset_rename_dialog_result_impl,
    rename_preset_display_name as rename_preset_display_name_impl,
    save_preset as save_preset_impl,
    apply_preset as apply_preset_impl,
)

from tategakiXTC_gui_studio_navigation_action_helpers import (
    update_nav_button_texts as _update_nav_button_texts_impl,
    on_nav_reverse_toggled as _on_nav_reverse_toggled_impl,
    on_nav_button_clicked as _on_nav_button_clicked_impl,
    on_page_input_changed as _on_page_input_changed_impl,
    change_page as _change_page_impl,
)

from tategakiXTC_gui_studio_preview_zoom_helpers import (
    _normalize_preview_zoom_pct as _normalize_preview_zoom_pct_impl,
    _preview_zoom_factor as _preview_zoom_factor_impl,
    _actual_size_uses_preview_zoom_calibration as _actual_size_uses_preview_zoom_calibration_impl,
    _actual_size_calibration_factor as _actual_size_calibration_factor_impl,
    _sync_legacy_calibration_control_state as _sync_legacy_calibration_control_state_impl,
    _sync_preview_zoom_control_state as _sync_preview_zoom_control_state_impl,
    _preview_zoom_left_bias as _preview_zoom_left_bias_impl,
    _viewport_width_for_scroll_area as _viewport_width_for_scroll_area_impl,
    _font_preview_leading_gap as _font_preview_leading_gap_impl,
    _viewer_preview_leading_gap as _viewer_preview_leading_gap_impl,
)


from tategakiXTC_gui_studio_wheel_guard_helpers import (
    _combo_popup_is_visible as _combo_popup_is_visible_impl,
    _is_open_combo_popup_wheel_target as _is_open_combo_popup_wheel_target_impl,
    _wheel_value_change_control_for_event_object as _wheel_value_change_control_for_event_object_impl,
    _should_suppress_center_settings_wheel_value_change as _should_suppress_center_settings_wheel_value_change_impl,
    _should_suppress_left_settings_wheel_value_change as _should_suppress_left_settings_wheel_value_change_impl,
    _should_scroll_center_settings_from_wheel_event as _should_scroll_center_settings_from_wheel_event_impl,
    _should_scroll_left_settings_from_wheel_event as _should_scroll_left_settings_from_wheel_event_impl,
    _install_center_settings_wheel_value_guards as _install_center_settings_wheel_value_guards_impl,
    _install_left_settings_wheel_value_guards as _install_left_settings_wheel_value_guards_impl,
    _scroll_center_settings_from_wheel_event as _scroll_center_settings_from_wheel_event_impl,
    _scroll_left_settings_from_wheel_event as _scroll_left_settings_from_wheel_event_impl,
    _is_widget_descendant_of as _is_widget_descendant_of_impl,
    _clear_startup_input_focus as _clear_startup_input_focus_impl,
)

from tategakiXTC_gui_studio_preview_layout_helpers import (
    _set_horizontal_scrollbar_to_zoom_bias_later as _set_horizontal_scrollbar_to_zoom_bias_later_impl,
    _set_horizontal_scrollbar_to_center_later as _set_horizontal_scrollbar_to_center_later_impl,
    _set_horizontal_scrollbar_to_minimum_later as _set_horizontal_scrollbar_to_minimum_later_impl,
    _sync_font_preview_scroll_placement as _sync_font_preview_scroll_placement_impl,
    _sync_preview_size as _sync_preview_size_impl,
    _sync_viewer_size as _sync_viewer_size_impl,
)

from tategakiXTC_gui_studio_right_pane_build_helpers import (
    _build_right_preview as _build_right_preview_impl,
    _build_view_toggle_bar as _build_view_toggle_bar_impl,
    _add_preview_display_toggles_to_layout as _add_preview_display_toggles_to_layout_impl,
    _build_conversion_completion_card as _build_conversion_completion_card_impl,
    _hide_conversion_completion_card as _hide_conversion_completion_card_impl,
    _show_results_tab_from_completion_card as _show_results_tab_from_completion_card_impl,
    _completion_card_parent_texts as _completion_card_parent_texts_impl,
    _completion_card_result_item_texts as _completion_card_result_item_texts_impl,
    _build_conversion_completion_card_message as _build_conversion_completion_card_message_impl,
    _meaningful_open_folder_target_text as _meaningful_open_folder_target_text_impl,
    _source_target_parent_text as _source_target_parent_text_impl,
    _planned_open_folder_target_from_settings as _planned_open_folder_target_from_settings_impl,
    _resolve_conversion_open_folder_target as _resolve_conversion_open_folder_target_impl,
    _show_conversion_completion_card as _show_conversion_completion_card_impl,
    _build_nav_bar as _build_nav_bar_impl,
    _ensure_nav_reverse_control as _ensure_nav_reverse_control_impl,
    _add_nav_controls_to_layout as _add_nav_controls_to_layout_impl,
    _nav_section_separator as _nav_section_separator_impl,
    _add_preview_zoom_controls_to_layout as _add_preview_zoom_controls_to_layout_impl,
)

from tategakiXTC_gui_studio_viewer_profile_helpers import (
    _current_viewer_profile as _current_viewer_profile_impl,
    _preview_viewer_profile as _preview_viewer_profile_impl,
    _loaded_xtc_document_viewer_profile as _loaded_xtc_document_viewer_profile_impl,
    _refresh_loaded_xtc_viewer_profile_cache as _refresh_loaded_xtc_viewer_profile_cache_impl,
    _sync_loaded_xtc_profile_ui_override as _sync_loaded_xtc_profile_ui_override_impl,
    _active_device_viewer_profile as _active_device_viewer_profile_impl,
    _font_preview_viewer_profile as _font_preview_viewer_profile_impl,
    _apply_viewer_display_runtime_state as _apply_viewer_display_runtime_state_impl,
    _apply_profile_runtime_state as _apply_profile_runtime_state_impl,
    _page_image_dimensions as _page_image_dimensions_impl,
    _viewer_profile_for_dimensions as _viewer_profile_for_dimensions_impl,
    _custom_viewer_profile_for_dimensions as _custom_viewer_profile_for_dimensions_impl,
    _viewer_profile_for_xtc_pages as _viewer_profile_for_xtc_pages_impl,
    _viewer_profile_for_page_image as _viewer_profile_for_page_image_impl,
    _viewer_profile_for_preview_payload as _viewer_profile_for_preview_payload_impl,
)

from tategakiXTC_gui_studio_xtc_load_helpers import (
    _xtc_source_payload as _xtc_source_payload_impl,
    _normalized_xtc_bytes as _normalized_xtc_bytes_impl,
    _xtc_document_payload as _xtc_document_payload_impl,
    _xtc_source_document_payload as _xtc_source_document_payload_impl,
    _xtc_display_name as _xtc_display_name_impl,
    _reset_xtc_page_input as _reset_xtc_page_input_impl,
    _apply_xtc_document_payload as _apply_xtc_document_payload_impl,
    _apply_loaded_xtc_document as _apply_loaded_xtc_document_impl,
    _current_xtc_page_blob as _current_xtc_page_blob_impl,
    _clear_xtc_viewer_page as _clear_xtc_viewer_page_impl,
    _apply_rendered_xtc_page as _apply_rendered_xtc_page_impl,
    _set_current_device_preview_page_index as _set_current_device_preview_page_index_impl,
    _set_current_page_index as _set_current_page_index_impl,
    load_xtc_from_path as load_xtc_from_path_impl,
    load_xtc_from_bytes as load_xtc_from_bytes_impl,
    render_current_page as render_current_page_impl,
    clear_loaded_xtc_state as clear_loaded_xtc_state_impl,
    leave_file_viewer_mode_for_target_change as leave_file_viewer_mode_for_target_change_impl,
    _apply_loaded_xtc_view_mode as _apply_loaded_xtc_view_mode_impl,
    open_xtc_file as open_xtc_file_impl,
    _apply_loaded_xtc_path_success as _apply_loaded_xtc_path_success_impl,
    _apply_loaded_xtc_path_failure as _apply_loaded_xtc_path_failure_impl,
    _restore_results_selection_after_xtc_load_failure as _restore_results_selection_after_xtc_load_failure_impl,
    _xtc_load_failure_preserved_display_name as _xtc_load_failure_preserved_display_name_impl,
    _xtc_load_failure_status_message as _xtc_load_failure_status_message_impl,
    _apply_loaded_xtc_bytes_success as _apply_loaded_xtc_bytes_success_impl,
)

from tategakiXTC_gui_studio_preview_cache_helpers import (
    _rebuild_preview_page_cache_tokens as _rebuild_preview_page_cache_tokens_impl,
    _clear_font_preview_page_pixmap_cache as _clear_font_preview_page_pixmap_cache_impl,
    _font_preview_page_pixmap_cache_key as _font_preview_page_pixmap_cache_key_impl,
    _cached_font_preview_page_pixmap as _cached_font_preview_page_pixmap_impl,
    _store_font_preview_page_pixmap as _store_font_preview_page_pixmap_impl,
    _clear_xtc_page_qimage_cache as _clear_xtc_page_qimage_cache_impl,
    _clear_device_preview_page_qimage_cache as _clear_device_preview_page_qimage_cache_impl,
    _device_preview_page_qimage_cache_key as _device_preview_page_qimage_cache_key_impl,
    _cached_device_preview_page_qimage as _cached_device_preview_page_qimage_impl,
    _store_device_preview_page_qimage as _store_device_preview_page_qimage_impl,
    _xtc_page_qimage_cache_key as _xtc_page_qimage_cache_key_impl,
    _cached_xtc_page_qimage as _cached_xtc_page_qimage_impl,
    _store_xtc_page_qimage as _store_xtc_page_qimage_impl,
)

from tategakiXTC_gui_studio_preset_payload_helpers import (
    _live_preset_widget_payload as _live_preset_widget_payload_impl,
    _normalize_preset_payload as _normalize_preset_payload_impl,
    _default_preset_display_name as _default_preset_display_name_impl,
    _load_preset_definitions as _load_preset_definitions_impl,
    _preset_display_name as _preset_display_name_impl,
    _preset_summary_plain_text as _preset_summary_plain_text_impl,
    _preset_summary_text as _preset_summary_text_impl,
    _current_settings_summary_payload as _current_settings_summary_payload_impl,
)

from tategakiXTC_gui_studio_preset_summary_layout_helpers import (
    preset_summary_label_measurement_width as _preset_summary_label_measurement_width_impl,
    queue_preset_summary_label_layout_retry as _queue_preset_summary_label_layout_retry_impl,
    update_preset_summary_label_layout as _update_preset_summary_label_layout_impl,
    sync_summary_payload as _sync_summary_payload_impl,
    sync_current_settings_summary as _sync_current_settings_summary_impl,
    sync_selected_preset_summary as _sync_selected_preset_summary_impl,
    refresh_preset_ui as _refresh_preset_ui_impl,
)

from tategakiXTC_gui_studio_results_helpers import (
    _set_results_summary_text_fallback as _set_results_summary_text_fallback_impl,
    _set_results_summary_text_with_fallback as _set_results_summary_text_with_fallback_impl,
    _set_bottom_tab_index_with_fallback as _set_bottom_tab_index_with_fallback_impl,
    _clear_results_view as _clear_results_view_impl,
    _sync_results_action_buttons_state as _sync_results_action_buttons_state_impl,
    _normalize_results_path_key as _normalize_results_path_key_impl,
    _clear_results_selection_state as _clear_results_selection_state_impl,
    _clear_results_selection_with_fallback as _clear_results_selection_with_fallback_impl,
    _apply_results_selection_context_with_fallback as _apply_results_selection_context_with_fallback_impl,
    _sync_results_selection_for_loaded_path_with_fallback as _sync_results_selection_for_loaded_path_with_fallback_impl,
    _result_item_count as _result_item_count_impl,
    _result_item_at as _result_item_at_impl,
    _result_item_paths as _result_item_paths_impl,
    _result_item_path_keys as _result_item_path_keys_impl,
    _set_results_current_index_with_fallback as _set_results_current_index_with_fallback_impl,
    _apply_results_selection_context as _apply_results_selection_context_impl,
    _sync_results_selection_for_loaded_path as _sync_results_selection_for_loaded_path_impl,
    _selected_result_indexes as _selected_result_indexes_impl,
    _current_results_index as _current_results_index_impl,
    _resolved_result_load_context as _resolved_result_load_context_impl,
    _resolved_results_item_for_loading as _resolved_results_item_for_loading_impl,
    _fallback_loaded_result_load_context as _fallback_loaded_result_load_context_impl,
)

from tategakiXTC_gui_studio_results_actions_helpers import (
    _load_xtc_from_path_with_result as _load_xtc_from_path_with_result_impl,
    _show_conversion_results as _show_conversion_results_impl,
    _preferred_result_path_for_action as _preferred_result_path_for_action_impl,
    open_results_folder_from_results as open_results_folder_from_results_impl,
    open_selected_result_from_results as open_selected_result_from_results_impl,
    _result_display_name as _result_display_name_impl,
    _normalized_result_entries as _normalized_result_entries_impl,
    _apply_results_entries_to_ui as _apply_results_entries_to_ui_impl,
    populate_results as populate_results_impl,
    on_result_item_clicked as on_result_item_clicked_impl,
    _show_result_load_dialog_with_status_fallback as _show_result_load_dialog_with_status_fallback_impl,
    load_selected_result as load_selected_result_impl,
    _results_item_path as _results_item_path_impl,
    _apply_loaded_xtc_ui_context as _apply_loaded_xtc_ui_context_impl,
)

from tategakiXTC_gui_studio_status_helpers import (
    _ui_widget_text as _ui_widget_text_impl,
    _ui_widget_index as _ui_widget_index_impl,
    _is_render_failure_status_text as _is_render_failure_status_text_impl,
    _is_preview_render_failure_status_text as _is_preview_render_failure_status_text_impl,
    _is_device_render_failure_status_text as _is_device_render_failure_status_text_impl,
    _display_context_name_from_label_text as _display_context_name_from_label_text_impl,
    _render_failure_preserved_display_name as _render_failure_preserved_display_name_impl,
    _device_render_failure_matches_visible_display_context as _device_render_failure_matches_visible_display_context_impl,
    _preview_render_failure_matches_visible_display_context as _preview_render_failure_matches_visible_display_context_impl,
    _visible_render_failure_status_text as _visible_render_failure_status_text_impl,
    _show_ui_status_message_unless_render_failure_visible as _show_ui_status_message_unless_render_failure_visible_impl,
    _status_bar_message_text as _status_bar_message_text_impl,
    _show_ui_status_message_unless_render_failure_visible_with_reflection as _show_ui_status_message_unless_render_failure_visible_with_reflection_impl,
    _show_ui_status_message_with_reflection_or_direct_fallback as _show_ui_status_message_with_reflection_or_direct_fallback_impl,
    _show_ui_status_message_direct_with_reflection_best_effort as _show_ui_status_message_direct_with_reflection_best_effort_impl,
    _show_ui_status_message_direct_with_reflection as _show_ui_status_message_direct_with_reflection_impl,
)

from tategakiXTC_gui_studio_log_helpers import (
    _merge_results_summary_lines_with_warnings as _merge_results_summary_lines_with_warnings_impl,
    _merge_results_summary_lines_and_collect_warnings as _merge_results_summary_lines_and_collect_warnings_impl,
    _build_results_summary_text as _build_results_summary_text_impl,
    _append_conversion_finish_error_log_with_fallback as _append_conversion_finish_error_log_with_fallback_impl,
    _handle_conversion_finish_ui_error as _handle_conversion_finish_ui_error_impl,
    append_log as append_log_impl,
    open_log_folder as open_log_folder_impl,
    _append_log_without_status as _append_log_without_status_impl,
    _append_log_with_status_fallback as _append_log_with_status_fallback_impl,
    _append_log_without_status_best_effort as _append_log_without_status_best_effort_impl,
    _append_log_without_status_or_status_bar as _append_log_without_status_or_status_bar_impl,
    _append_log_without_status_with_optional_status_fallback as _append_log_without_status_with_optional_status_fallback_impl,
    _emit_postprocess_warning as _emit_postprocess_warning_impl,
    _emit_postprocess_warning_via_log_and_optional_status_fallback as _emit_postprocess_warning_via_log_and_optional_status_fallback_impl,
    _emit_postprocess_warnings_and_collect as _emit_postprocess_warnings_and_collect_impl,
    _emit_postprocess_warnings as _emit_postprocess_warnings_impl,
    _emit_unique_postprocess_warnings_with_fallback as _emit_unique_postprocess_warnings_with_fallback_impl,
    _append_unique_postprocess_warnings_to_log_with_fallback as _append_unique_postprocess_warnings_to_log_with_fallback_impl,
    _emit_unique_postprocess_warnings_or_append_to_log as _emit_unique_postprocess_warnings_or_append_to_log_impl,
)

MissingDependencyItem = dict[str, object]
OutputPlan = dict[str, object]
PresetDefinition = dict[str, object]
PresetDefinitions = dict[str, PresetDefinition]
ConversionResult = dict[str, object]



from tategakiXTC_gui_studio_constants import (
    APP_BASE_NAME,
    APP_VERSION,
    APP_NAME,
    SETTINGS_FILE,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_LEFT_PANEL_WIDTH,
    DEFAULT_STARTUP_PRESET_KEY,
    DEFAULT_TOP_PATH_BUTTON_WIDTH,
    DEFAULT_LEFT_SPLITTER_TOP,
    DEFAULT_LEFT_SPLITTER_BOTTOM,
    CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY,
    CENTER_SETTINGS_LEGACY_SPLITTER_SIZES_KEY,
    CENTER_SETTINGS_LEGACY_SPLITTER_TOP_KEY,
    CENTER_SETTINGS_LEGACY_SPLITTER_BOTTOM_KEY,
    PRESET_PANEL_WIDTH_KEY,
    CENTER_SETTINGS_PANEL_WIDTH_KEY,
    PREVIEW_PANEL_WIDTH_KEY,
    MAIN_THREE_PANE_SPLITTER_STATE_KEY,
    MAIN_THREE_PANE_SPLITTER_SIZES_KEY,
    THREE_PANE_PANEL_WIDTH_KEYS,
    THREE_PANE_SPLITTER_KEYS,
    DEFAULT_PREVIEW_PAGE_LIMIT,
    DEFAULT_UI_LANGUAGE,
    UI_LANGUAGE_OPTIONS,
    UI_LANGUAGE_LABELS,
    SETTINGS_SCHEMA_VERSION,
    DEFAULT_RENDER_SETTINGS,
    RESULT_TAB_INDEX,
    LOG_TAB_INDEX,
    SUPPORTED_INPUT_SUFFIXES,
    TEXT_OR_MARKDOWN_LABEL,
    FONT_REQUIRED_SUFFIXES,
    DeviceProfile,
    DEVICE_PROFILES,
    _make_preset,
    DEFAULT_PRESET_DEFINITIONS,
    PRESET_FIELDS,
    KINSOKU_MODE_OPTIONS,
    KINSOKU_MODE_LABELS,
    TATECHUYOKO_DIGIT_MODE_OPTIONS,
    TATECHUYOKO_DIGIT_MODE_LABELS,
    PROGRESS_BAR_POSITION_OPTIONS,
    PROGRESS_BAR_POSITION_LABELS,
    GLYPH_POSITION_MODE_OPTIONS,
    GLYPH_POSITION_MODE_LABELS,
    OPENING_BRACKET_INDENT_MODE_LABELS,
    CLOSING_BRACKET_POSITION_MODE_OPTIONS,
    CLOSING_BRACKET_POSITION_MODE_LABELS,
    WAVE_DASH_DRAWING_MODE_OPTIONS,
    WAVE_DASH_DRAWING_MODE_LABELS,
    WAVE_DASH_POSITION_MODE_OPTIONS,
    WAVE_DASH_POSITION_MODE_LABELS,
    OUTPUT_FORMAT_OPTIONS,
    OUTPUT_FORMAT_LABELS,
    OUTPUT_CONFLICT_OPTIONS,
    OUTPUT_CONFLICT_LABELS,
)

from tategakiXTC_gui_studio_xtc_io import (
    XtcPage,
    parse_xtc_pages,
    xt_page_blob_to_qimage,
    xtg_blob_to_qimage,
    xth_blob_to_qimage,
)

from tategakiXTC_gui_studio_widgets import (
    _scroll_combo_popup_to_top_now,
    FontPopupTopComboBox,
    SourceDropLineEdit,
    VisibleArrowSpinBox,
    XtcViewerWidget,
)

from tategakiXTC_gui_studio_worker import (
    _coerce_progress_number,
    _write_output_bytes_atomic,
    _process_single_image_file,
    PROCESSOR_BY_SUFFIX,
    _format_missing_dependency_message,
    _summarize_error_headlines,
    build_conversion_args,
    resolve_supported_conversion_targets,
    sanitize_output_stem,
    plan_output_path_for_target,
    build_conversion_summary,
    ConversionWorker,
)

# ─────────────────────────────────────────────────────────
# メインウィンドウ
# ─────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    _worker_finished_requested = Signal(object, object)
    _worker_error_requested = Signal(object, object)
    _worker_log_requested = Signal(object, object)
    _worker_progress_requested = Signal(object, object, object, object)
    _worker_cleanup_requested = Signal(object, object)

    # ── 初期化 ────────────────────────────────────────────

    def __init__(self: MainWindow) -> None:
        super().__init__()
        _configure_app_logging()
        self.settings_store = QSettings(str(SETTINGS_FILE), QSettings.IniFormat)
        self.current_ui_language = self._initial_ui_language()
        self._previous_shutdown_clean = self._settings_bool_value('last_shutdown_clean', True)
        if not self._previous_shutdown_clean and not self._has_restorable_user_settings():
            APP_LOGGER.warning(
                '前回終了フラグだけが残っており復元対象のUI設定がないため、通常起動として扱います'
            )
            self._previous_shutdown_clean = True
        self._mark_shutdown_clean(False)
        self.preset_definitions = self._load_preset_definitions()
        self.setWindowTitle(self._app_window_title())
        initial_size = self._default_window_size()
        self.resize(initial_size.width(), initial_size.height())

        self.current_profile_key = 'x4'
        self.current_preview_mode = 'text'
        self.preview_image_data_url = None
        self.preview_pages_b64: list[str] = []
        self.preview_pages_truncated = False
        self.device_preview_pages_b64: list[str] = []
        self.device_preview_pages_truncated = False
        self.device_view_source = 'xtc'
        self.last_preview_requested_limit = DEFAULT_PREVIEW_PAGE_LIMIT
        self.last_applied_preview_payload: dict[str, object] | None = None
        self.current_preview_page_index = 0
        self.current_device_preview_page_index = 0
        self.preview_dirty = False
        self._preview_running = False
        self._pending_preview_refresh_request: dict[str, object] | None = None
        self.xtc_bytes: bytes | None = None
        self.xtc_pages: list[XtcPage] = []
        self.loaded_xtc_viewer_profile: DeviceProfile | None = None
        self.loaded_xtc_profile_ui_override = False
        self._xtc_page_qimage_cache: OrderedDict[tuple[int, int, int], object] = OrderedDict()
        self._device_preview_page_qimage_cache: OrderedDict[tuple[int, int], object] = OrderedDict()
        self._font_preview_page_pixmap_cache: OrderedDict[tuple[int, int], object] = OrderedDict()
        self._preview_page_cache_tokens: list[int] = []
        self._device_preview_page_cache_tokens: list[int] = []
        self.current_page_index = 0
        self.nav_buttons_reversed = False
        self.selected_output_dir = ''
        self.current_ui_theme = 'light'
        self.panel_button_visible = True
        self.worker_thread: QThread | None = None
        self.worker: ConversionWorker | None = None
        self._conversion_run_token = 0
        self._active_conversion_run_token = 0
        self._connect_worker_dispatch_signals()
        self._startup_pending = True
        self._preview_resize_sync_pending = False
        self._preview_resize_sync_active = False
        self._settings_preview_refresh_scheduled = False
        self._settings_preview_refresh_pending = False
        self._settings_preview_refresh_pending_reset_page = False
        self._settings_preview_refresh_generation = 0
        self._preview_update_button_visual_state = 'idle'
        self._pending_left_panel_width: int | None = None
        self._initialized = False  # 初期化完了前の save_ui_state を抑制

        self._build_ui()
        try:
            self._append_log_with_status_fallback(
                f'ログ保存先: {_resolve_session_log_path()}',
                reflect_in_status=False,
            )
        except Exception:
            APP_LOGGER.exception('ログ保存先のUI反映に失敗しました')
        self._log_optional_dependency_status()
        QApplication.instance().installEventFilter(self)
        self._setup_global_navigation_shortcuts()
        self._apply_styles()
        self._restore_settings()

    def _log_optional_dependency_status(self: MainWindow) -> None:
        return _log_optional_dependency_status_impl(self, core.list_optional_dependency_status)

    def _missing_dependencies_for_targets(self: MainWindow, targets: list[Path]) -> list[MissingDependencyItem]:
        return _missing_dependencies_for_targets_impl(targets, core.get_missing_dependencies_for_suffixes)

    def _show_warning_dialog_with_status_fallback(
        self: MainWindow,
        title: str,
        message: str,
        *,
        duration_ms: int = 5000,
    ) -> None:
        ui_text = getattr(self, '_ui_text', lambda value: str(value if value is not None else ''))
        _show_warning_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'warning', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            ui_text(title),
            ui_text(message),
            duration_ms=duration_ms,
        )

    def _ask_question_dialog_with_status_fallback(
        self: MainWindow,
        title: str,
        message: str,
        buttons: object,
        default_button: object,
        *,
        duration_ms: int = 5000,
        fallback_status_message: str = '',
        fallback_answer: object = None,
    ) -> object:
        ui_text = getattr(self, '_ui_text', lambda value: str(value if value is not None else ''))
        return _ask_question_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'question', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            _coerce_ui_message_text,
            ui_text(title),
            ui_text(message),
            buttons,
            default_button,
            duration_ms=duration_ms,
            fallback_status_message=ui_text(fallback_status_message),
            fallback_answer=fallback_answer,
        )

    def _show_information_dialog_with_status_fallback(
        self: MainWindow,
        title: str,
        message: str,
        *,
        duration_ms: int = 5000,
        fallback_status_message: str = '',
    ) -> None:
        ui_text = getattr(self, '_ui_text', lambda value: str(value if value is not None else ''))
        _show_information_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'information', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            _coerce_ui_message_text,
            ui_text(title),
            ui_text(message),
            duration_ms=duration_ms,
            fallback_status_message=ui_text(fallback_status_message),
        )

    def _show_critical_dialog_with_status_fallback(
        self: MainWindow,
        title: str,
        message: str,
        *,
        duration_ms: int = 5000,
        fallback_status_message: str = '',
    ) -> None:
        ui_text = getattr(self, '_ui_text', lambda value: str(value if value is not None else ''))
        _show_critical_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'critical', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            _coerce_ui_message_text,
            ui_text(title),
            ui_text(message),
            duration_ms=duration_ms,
            fallback_status_message=ui_text(fallback_status_message),
        )

    def _get_open_file_name_with_status_fallback(
        self: MainWindow,
        title: str,
        start_dir: str,
        filter_text: str,
        *,
        warning_title: str = 'ファイル選択エラー',
        fallback_status_message: str = '',
    ) -> tuple[str, str]:
        return _get_open_file_name_with_status_fallback_impl(
            self,
            getattr(QFileDialog, 'getOpenFileName', None),
            self._show_warning_dialog_with_status_fallback,
            _coerce_ui_message_text,
            (getattr(self, '_ui_text', lambda value: str(value if value is not None else '')))(title),
            start_dir,
            filter_text,
            warning_title=(getattr(self, '_ui_text', lambda value: str(value if value is not None else '')))(warning_title),
            fallback_status_message=(getattr(self, '_ui_text', lambda value: str(value if value is not None else '')))(fallback_status_message),
        )

    def _get_existing_directory_with_status_fallback(
        self: MainWindow,
        title: str,
        start_dir: str,
        *,
        warning_title: str = 'フォルダ選択エラー',
        fallback_status_message: str = '',
    ) -> str:
        return _get_existing_directory_with_status_fallback_impl(
            self,
            getattr(QFileDialog, 'getExistingDirectory', None),
            self._show_warning_dialog_with_status_fallback,
            _coerce_ui_message_text,
            (getattr(self, '_ui_text', lambda value: str(value if value is not None else '')))(title),
            start_dir,
            warning_title=(getattr(self, '_ui_text', lambda value: str(value if value is not None else '')))(warning_title),
            fallback_status_message=(getattr(self, '_ui_text', lambda value: str(value if value is not None else '')))(fallback_status_message),
        )

    def _install_folder_batch_menu_action(self: MainWindow) -> None:
        return _install_folder_batch_menu_action_impl(self)

    def _open_folder_batch_dialog(self: MainWindow) -> None:
        return _open_folder_batch_dialog_impl(self)

    def _check_conversion_dependencies(self: MainWindow, cfg: WorkerConversionSettings) -> bool:
        return _check_conversion_dependencies_impl(self, cfg, _format_missing_dependency_message)

    def _settings_raw_value(self: MainWindow, key: str, default: object = None) -> object:
        return _settings_raw_value_from_store(self.settings_store, key, default)

    def _settings_contains_key(self: MainWindow, key: str) -> bool:
        return _settings_contains_key_in_store(self.settings_store, key)

    def _settings_int_value(self: MainWindow, key: str, default: int) -> int:
        return _settings_int_value_from_store(self.settings_store, key, default)

    def _settings_bool_value(self: MainWindow, key: str, default: bool) -> bool:
        return _settings_bool_value_from_store(self.settings_store, key, default)

    def _has_restorable_user_settings(self: MainWindow) -> bool:
        return _has_restorable_user_settings_impl(self)

    def _settings_str_value(self: MainWindow, key: str, default: str = '') -> str:
        return _settings_str_value_from_store(self.settings_store, key, default)

    def _os_default_ui_language(self: MainWindow) -> str:
        locale_name = ''
        try:
            locale_name = str(locale.getlocale()[0] or '').strip().lower()
        except Exception:
            locale_name = ''
        if not locale_name:
            for env_name in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
                locale_name = str(os.environ.get(env_name, '') or '').strip().lower()
                if locale_name:
                    break
        return 'ja' if locale_name.startswith('ja') else 'en'

    def _normalize_ui_language(self: MainWindow, value: object, default: str | None = None) -> str:
        fallback = default or DEFAULT_UI_LANGUAGE
        return studio_logic.normalize_ui_language(value, fallback)

    def _initial_ui_language(self: MainWindow) -> str:
        fallback = self._os_default_ui_language()
        if self._settings_contains_key('ui_language'):
            return self._normalize_ui_language(self._settings_str_value('ui_language', fallback), fallback)
        return self._normalize_ui_language(fallback, DEFAULT_UI_LANGUAGE)

    def current_ui_language_value(self: MainWindow) -> str:
        combo = getattr(self, 'language_combo', None)
        data_getter = getattr(combo, 'currentData', None)
        if callable(data_getter):
            try:
                return self._normalize_ui_language(data_getter(), getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE))
            except Exception:
                pass
        return self._normalize_ui_language(getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE), DEFAULT_UI_LANGUAGE)

    def _app_window_title(self: MainWindow) -> str:
        return f'{self._ui_text(APP_BASE_NAME)} {APP_VERSION}'

    def _ui_text(self: MainWindow, text: object) -> str:
        return studio_logic.translate_ui_text(text, getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE))

    def _localized_plan(self: MainWindow, plan: object) -> object:
        return studio_logic.translate_ui_structure(plan, getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE))

    def _set_language_combo_value(self: MainWindow, language: object) -> str:
        normalized = self._normalize_ui_language(language, getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE))
        self.current_ui_language = normalized
        combo = getattr(self, 'language_combo', None)
        if combo is not None:
            self._set_combo_to_data(combo, normalized)
        return normalized

    def _update_language_restart_note_label(self: MainWindow, language: object) -> None:
        label = getattr(self, 'language_restart_note_label', None)
        setter = getattr(label, 'setText', None)
        if not callable(setter):
            return
        try:
            setter(studio_logic.build_language_restart_notice(language).get('note', ''))
        except Exception:
            pass

    def on_language_combo_changed(self: MainWindow, _index: int = 0) -> None:
        previous = self._normalize_ui_language(getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE), DEFAULT_UI_LANGUAGE)
        selected = self.current_ui_language_value()
        self.current_ui_language = selected
        self._update_language_restart_note_label(selected)
        if getattr(self, '_initialized', False):
            self.save_ui_state()
            if selected != previous:
                notice = studio_logic.build_language_restart_notice(selected)
                try:
                    self._show_information_dialog_with_status_fallback(
                        notice.get('title', ''),
                        notice.get('message', ''),
                        fallback_status_message=notice.get('status', ''),
                    )
                except Exception:
                    try:
                        self._show_ui_status_message_with_reflection_or_direct_fallback(
                            notice.get('status', ''),
                            5000,
                        )
                    except Exception:
                        try:
                            self.statusBar().showMessage(notice.get('status', ''), 5000)
                        except Exception:
                            pass

    def _mark_shutdown_clean(self: MainWindow, clean: bool) -> None:
        try:
            self.settings_store.setValue('last_shutdown_clean', bool(clean))
            self.settings_store.setValue('settings_schema_version', SETTINGS_SCHEMA_VERSION)
            self.settings_store.setValue('last_app_version', APP_VERSION)
            self.settings_store.sync()
        except Exception:
            APP_LOGGER.exception('終了状態フラグの保存に失敗しました')

    def _normalize_choice_value(self: MainWindow, value: object, default: str, allowed_values: object) -> str:
        return studio_logic.normalize_choice_value(value, default, allowed_values)

    def _set_combo_to_data(self: MainWindow, combo: object, data: str) -> bool:
        idx = combo.findData(data)
        if idx >= 0:
            combo.setCurrentIndex(idx)
            return True
        combo.setCurrentIndex(-1)
        return False

    def _restore_combo_from_settings(self: MainWindow, key: str, default: str, combo: object, allowed_values: object) -> str:
        normalized = self._normalize_choice_value(self._settings_str_value(key, default), default, allowed_values)
        self._set_combo_to_data(combo, normalized)
        return normalized

    def _default_startup_preset_key(self: MainWindow) -> str:
        definitions = getattr(self, 'preset_definitions', None) or DEFAULT_PRESET_DEFINITIONS
        candidate = str(DEFAULT_STARTUP_PRESET_KEY or '').strip()
        if candidate in definitions:
            return candidate
        if getattr(self, 'preset_combo', None) is not None and hasattr(self.preset_combo, 'count') and self.preset_combo.count() > 0:
            data = self.preset_combo.itemData(0) if hasattr(self.preset_combo, 'itemData') else None
            if data:
                return str(data)
        if definitions:
            return next(iter(definitions))
        return 'preset_1'

    def _startup_preset_payload(self: MainWindow) -> PresetDefinition:
        definitions = getattr(self, 'preset_definitions', None) or DEFAULT_PRESET_DEFINITIONS
        key = self._default_startup_preset_key()
        return dict(definitions.get(key) or DEFAULT_PRESET_DEFINITIONS.get(key) or {})

    def _settings_default_value(self: MainWindow, key: str, fallback: object) -> object:
        if self._settings_contains_key(key):
            return self._settings_raw_value(key, fallback)
        preset_payload = self._startup_preset_payload()
        if key in preset_payload:
            return preset_payload.get(key, fallback)
        return fallback

    def _restore_preset_selection(self: MainWindow) -> None:
        saved_preset_key = self._settings_str_value('preset_key', '').strip()
        if saved_preset_key and self._set_combo_to_data(self.preset_combo, saved_preset_key):
            return
        saved_preset_index = self._settings_int_value('preset_index', 0)
        if self._settings_contains_key('preset_index'):
            if 0 <= saved_preset_index < self.preset_combo.count():
                self.preset_combo.setCurrentIndex(saved_preset_index)
                return
            self.preset_combo.setCurrentIndex(-1)
            return
        startup_key = self._default_startup_preset_key()
        if startup_key and self._set_combo_to_data(self.preset_combo, startup_key):
            return
        if 0 <= saved_preset_index < self.preset_combo.count():
            self.preset_combo.setCurrentIndex(saved_preset_index)
            return
        self.preset_combo.setCurrentIndex(-1)

    def _restore_font_value_from_settings(self: MainWindow) -> None:
        font_value = self._normalize_font_setting_value(
            self._settings_default_value('font_file', self._default_font_name()),
            self._default_font_name(),
        )
        if font_value:
            self._set_current_font_value(font_value)

    def _payload_int_value(self: MainWindow, payload: Mapping[str, object], key: str, default: int) -> int:
        return worker_logic._int_config_value(dict(payload), key, default)

    def _payload_bool_value(self: MainWindow, payload: Mapping[str, object], key: str, default: bool) -> bool:
        return worker_logic._bool_config_value(dict(payload), key, default)

    def _payload_optional_int_value(self: MainWindow, payload: Mapping[str, object], key: str) -> int | None:
        return studio_logic.payload_optional_int_value(payload, key)

    def _coerce_mapping_payload(self: MainWindow, value: object) -> dict[str, object]:
        return _coerce_mapping_payload_value(value)

    def _plan_int_value(self: MainWindow, payload_obj: object, key: str, default: int) -> int:
        return _plan_int_value_from_payload(payload_obj, key, default)

    def _plan_bool_value(self: MainWindow, payload_obj: object, key: str, default: bool) -> bool:
        return _plan_bool_value_from_payload(payload_obj, key, default)

    def _plan_int_tuple_value(
        self: MainWindow,
        payload_obj: object,
        key: str,
        default: Sequence[int],
        *,
        expected_length: int | None = None,
    ) -> tuple[int, ...]:
        return _plan_int_tuple_value_from_payload(
            payload_obj,
            key,
            default,
            expected_length=expected_length,
        )

    def _plan_token_value(self: MainWindow, payload_obj: object, key: str, default: str) -> str:
        return _plan_token_value_from_payload(payload_obj, key, default)

    def _qt_constant(self: MainWindow, name: str, fallback: object = 0):
        # PySide6 versions differ on whether enum values are exposed directly
        # as Qt.ScrollBarAlwaysOn / Qt.AlignCenter or only under nested enum
        # classes such as Qt.ScrollBarPolicy.ScrollBarAlwaysOn. Avoid falling
        # back to 0, because that silently becomes ScrollBarAlwaysOff on real
        # Windows/PySide6 builds.
        candidates = (
            Qt,
            getattr(Qt, 'ScrollBarPolicy', None),
            getattr(Qt, 'AlignmentFlag', None),
            getattr(Qt, 'FocusPolicy', None),
            getattr(Qt, 'Orientation', None),
            getattr(Qt, 'KeyboardModifier', None),
            getattr(Qt, 'TextFlag', None),
            getattr(Qt, 'PenStyle', None),
        )
        for owner in candidates:
            if owner is None:
                continue
            try:
                return getattr(owner, name)
            except Exception:
                continue
        return fallback

    def _plan_alignment_value(self: MainWindow, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        default_token = str(default or '').strip().lower().replace('-', '_')
        align_center = self._qt_constant('AlignCenter', 0)
        align_top = self._qt_constant('AlignTop', align_center)
        align_left = self._qt_constant('AlignLeft', align_center)
        align_left_top = align_left | align_top
        alignments = {
            'center': align_center,
            'align_center': align_center,
            'left_top': align_left_top,
            'align_left_top': align_left_top,
        }
        return alignments.get(token, alignments.get(default_token, align_center))

    def _plan_scroll_bar_policy_value(self: MainWindow, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        always_off = self._qt_constant('ScrollBarAlwaysOff', 0)
        always_on = self._qt_constant('ScrollBarAlwaysOn', always_off)
        as_needed = self._qt_constant('ScrollBarAsNeeded', always_off)
        return {
            'always_off': always_off,
            'always_on': always_on,
            'as_needed': as_needed,
        }.get(token, always_off if default == 'always_off' else as_needed)

    def _qframe_shape_constant(self: MainWindow, name: str, fallback: object = 0):
        return getattr(QFrame, name, fallback)

    def _plan_frame_shape_value(self: MainWindow, payload_obj: object, key: str, default: str):
        no_frame = self._qframe_shape_constant('NoFrame', 0)
        hline = self._qframe_shape_constant('HLine', no_frame)
        token = self._plan_token_value(payload_obj, key, default)
        return {
            'hline': hline,
            'no_frame': no_frame,
        }.get(token, no_frame if default == 'no_frame' else hline)

    def _plan_focus_policy_value(self: MainWindow, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {
            'no_focus': Qt.NoFocus,
            'strong_focus': Qt.StrongFocus,
        }.get(token, Qt.StrongFocus if default == 'strong_focus' else Qt.NoFocus)

    def _plan_spin_button_symbols_value(self: MainWindow, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {
            'up_down_arrows': QSpinBox.UpDownArrows,
            'no_buttons': QSpinBox.NoButtons,
        }.get(token, QSpinBox.UpDownArrows if default == 'up_down_arrows' else QSpinBox.NoButtons)

    def _plan_list_selection_mode_value(self: MainWindow, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {
            'single_selection': QListWidget.SingleSelection,
            'no_selection': QListWidget.NoSelection,
            'multi_selection': QListWidget.MultiSelection,
            'extended_selection': QListWidget.ExtendedSelection,
        }.get(token, QListWidget.SingleSelection)

    def _add_optional_widget_to_layout(self: MainWindow, lay: QHBoxLayout, attr_name: str) -> None:
        widget = getattr(self, attr_name, None)
        if widget is not None:
            lay.addWidget(widget)

    def _payload_splitter_sizes_value(
        self: MainWindow,
        payload: Mapping[str, object],
        key: str,
        default: Sequence[int],
    ) -> list[int]:
        return studio_logic.payload_splitter_sizes_value(
            payload,
            key,
            default,
            min_top=280,
            min_bottom=92,
        )

    def _payload_three_pane_splitter_sizes_value(
        self: MainWindow,
        payload: Mapping[str, object],
        key: str,
        default: Sequence[int],
    ) -> list[int]:
        fallback = list(default[:3])
        if len(fallback) < 3:
            fallback = [300, 680, 560]
        mins = [220, 360, 320]
        raw = payload.get(key)
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            return [max(mins[i], int(fallback[i])) for i in range(3)]
        raw_list = list(raw)
        if len(raw_list) < 3:
            return [max(mins[i], int(fallback[i])) for i in range(3)]
        result: list[int] = []
        for i in range(3):
            value = studio_logic.payload_optional_int_value({'value': raw_list[i]}, 'value')
            if value is None:
                value = int(fallback[i])
            result.append(max(mins[i], int(value)))
        return result

    def _window_state_restore_payload(self: MainWindow) -> dict[str, object]:
        return _window_state_restore_payload_impl(self)

    def _settings_restore_payload(self: MainWindow) -> dict[str, object]:
        return _settings_restore_payload_impl(self)

    def _startup_preview_defaults_payload(self: MainWindow, payload: Mapping[str, object]) -> dict[str, object]:
        return _startup_preview_defaults_payload_impl(self, payload)

    def _existing_widgets(self: MainWindow, *names: str) -> tuple[object, ...]:
        widgets: list[object] = []
        for name in names:
            if hasattr(self, name):
                widgets.append(getattr(self, name))
        return tuple(widgets)

    def _safe_widget_value(self: MainWindow, name: str, default: object) -> object:
        widget = getattr(self, name, None)
        value_getter = getattr(widget, 'value', None)
        if callable(value_getter):
            try:
                return value_getter()
            except Exception:
                pass
        return default

    def _safe_widget_checked(self: MainWindow, name: str, default: bool = False) -> bool:
        widget = getattr(self, name, None)
        checked_getter = getattr(widget, 'isChecked', None)
        if callable(checked_getter):
            try:
                return bool(checked_getter())
            except Exception:
                pass
        return bool(default)

    def _safe_combo_data(self: MainWindow, name: str, default: object = None) -> object:
        widget = getattr(self, name, None)
        data_getter = getattr(widget, 'currentData', None)
        if callable(data_getter):
            try:
                return data_getter()
            except Exception:
                pass
        return default

    def _current_profile_key_or_default(self: MainWindow) -> str:
        raw = getattr(self, 'current_profile_key', 'x4')
        return self._normalize_choice_value(raw or 'x4', 'x4', DEVICE_PROFILES)

    def _restore_settings_widgets(self: MainWindow) -> tuple[object, ...]:
        return self._existing_widgets(
            'language_combo',
            'profile_combo', 'actual_size_check', 'guides_check', 'calib_spin', 'preview_zoom_spin', 'nav_reverse_check',
            'font_combo', 'font_size_spin', 'ruby_size_spin', 'line_spacing_spin',
            'margin_t_spin', 'margin_b_spin', 'margin_r_spin', 'margin_l_spin',
            'threshold_spin', 'width_spin', 'height_spin', 'preview_page_limit_spin', 'ruby_hide_check', 'page_number_check', 'page_number_font_size_spin', 'progress_bar_check', 'progress_bar_position_combo', 'dither_check', 'night_check',
            'open_folder_check', 'output_conflict_combo', 'output_format_combo',
            'kinsoku_mode_combo', 'tatechuyoko_digit_mode_combo', 'latin_orientation_combo', 'opening_bracket_indent_combo', 'punctuation_position_combo', 'ichi_position_combo', 'halfwidth_digit_position_combo', 'halfwidth_alpha_position_combo', 'middle_dot_position_combo', 'tatechuyoko_symbol_position_combo', 'lower_closing_bracket_position_combo', 'wave_dash_drawing_combo', 'wave_dash_position_combo', 'target_edit', 'preset_combo',
        )

    def _preset_apply_widgets(self: MainWindow) -> tuple[object, ...]:
        return self._existing_widgets(
            'profile_combo', 'width_spin', 'height_spin', 'font_combo',
            'font_size_spin', 'ruby_size_spin', 'line_spacing_spin',
            'margin_t_spin', 'margin_b_spin', 'margin_r_spin', 'margin_l_spin',
            'ruby_hide_check', 'page_number_check', 'page_number_font_size_spin', 'progress_bar_check', 'progress_bar_position_combo', 'night_check', 'dither_check', 'kinsoku_mode_combo', 'tatechuyoko_digit_mode_combo', 'latin_orientation_combo', 'opening_bracket_indent_combo', 'punctuation_position_combo', 'ichi_position_combo', 'halfwidth_digit_position_combo', 'halfwidth_alpha_position_combo', 'middle_dot_position_combo', 'tatechuyoko_symbol_position_combo', 'lower_closing_bracket_position_combo', 'wave_dash_drawing_combo', 'wave_dash_position_combo', 'output_format_combo',
        )

    def _apply_profile_dimensions_to_ui(
        self: MainWindow,
        profile_key: object,
        width: object = None,
        height: object = None,
    ) -> tuple[str, DeviceProfile, int, int]:
        resolved_key, profile, resolved_width, resolved_height = self._resolved_profile_and_dimensions(
            profile_key,
            width,
            height,
        )
        profile_combo = getattr(self, 'profile_combo', None)
        if profile_combo is not None and not self._set_combo_to_data(profile_combo, resolved_key):
            resolved_key, profile, resolved_width, resolved_height = self._resolved_profile_and_dimensions('x4')
            self._set_combo_to_data(profile_combo, resolved_key)
        self.current_profile_key = resolved_key
        if hasattr(self, 'custom_size_row'):
            self.custom_size_row.setVisible(resolved_key == 'custom')
        if hasattr(self, 'width_spin'):
            self.width_spin.setValue(int(resolved_width))
        if hasattr(self, 'height_spin'):
            self.height_spin.setValue(int(resolved_height))
        return resolved_key, profile, resolved_width, resolved_height

    def _apply_settings_payload_to_ui(self: MainWindow, payload: dict[str, object]) -> None:
        _apply_settings_payload_to_ui_impl(self, payload)

    def _apply_render_option_ui_state(self: MainWindow, checked: object = None) -> None:
        if not hasattr(self, 'threshold_spin'):
            return
        if checked is None:
            if hasattr(self, 'dither_check') and hasattr(self.dither_check, 'isChecked'):
                checked = self.dither_check.isChecked()
            else:
                checked = False
        self.threshold_spin.setEnabled(not bool(checked))

    def _apply_viewer_display_runtime_state(self: MainWindow) -> None:
        _apply_viewer_display_runtime_state_impl(self)

    def _apply_profile_runtime_state(self: MainWindow) -> None:
        _apply_profile_runtime_state_impl(self)

    def _finalize_setting_change(
        self: MainWindow,
        *,
        update_status: bool = False,
        refresh_preview: bool = True,
        persist: bool = True,
    ) -> None:
        if update_status:
            self._update_top_status()
        if persist:
            self.save_ui_state()
        if refresh_preview:
            try:
                if self._is_file_viewer_mode_active():
                    # File-viewer mode shows already-rendered XTC/XTCH pages.
                    # Display-only controls such as the device approximation
                    # button must not mark the conversion preview stale or turn
                    # the Preview Update button into the pending beige state.
                    self._apply_file_viewer_mode_preview_button_state()
                    return
            except Exception:
                pass
            self.mark_preview_dirty()

    def _normalize_font_setting_value(self: MainWindow, value: object, fallback: str = '') -> str:
        font_value = worker_logic._str_config_value({'font_file': value}, 'font_file', fallback)
        font_value = core.build_font_spec(*core.parse_font_spec(font_value))
        lower = str(core.parse_font_spec(font_value)[0]).lower()
        if any(token in lower for token in ('msgothic', 'msmincho', 'ms gothic', 'ms mincho')):
            font_value = core.build_font_spec(*core.parse_font_spec(fallback))
        return font_value

    def _available_window_rect(self: MainWindow) -> QRect | None:
        screen_obj = None
        try:
            screen_getter = getattr(self, 'screen', None)
            screen_obj = screen_getter() if callable(screen_getter) else None
        except Exception:
            screen_obj = None
        if screen_obj is None:
            try:
                screen_obj = QApplication.primaryScreen()
            except Exception:
                screen_obj = None
        available_getter = getattr(screen_obj, 'availableGeometry', None)
        if not callable(available_getter):
            return None
        try:
            available = available_getter()
        except Exception:
            return None
        try:
            if int(available.width()) <= 0 or int(available.height()) <= 0:
                return None
        except Exception:
            return None
        return available

    def _clamp_window_size_to_available(self: MainWindow, width: int, height: int) -> QSize:
        available = self._available_window_rect()
        if available is None:
            return QSize(int(width), int(height))
        try:
            # resize() takes the client size, while availableGeometry() is the
            # desktop work area excluding the Windows taskbar.  Keep a small
            # safety margin so a restored normal window does not slip under a
            # permanently visible taskbar. Maximized windows are still handled
            # by the window manager.
            safe_width = max(1100, int(available.width()) - 24)
            safe_height = max(760, int(available.height()) - 48)
            return QSize(min(int(width), safe_width), min(int(height), safe_height))
        except Exception:
            return QSize(int(width), int(height))

    def _ensure_window_inside_available_area(self: MainWindow) -> None:
        available = self._available_window_rect()
        if available is None:
            return
        try:
            if self.isMaximized():
                # QMainWindow::showMaximized normally respects the taskbar on
                # Windows.  Do not fight the native maximized geometry unless
                # the platform reports a clearly invalid frame.
                frame = self.frameGeometry()
                if available.contains(frame):
                    return
                # If a saved geometry or show() ordering leaves the frame below
                # the work area, re-apply the native maximized state once.
                self.showMaximized()
                return
            geom = self.geometry()
            w = min(int(geom.width()), max(1100, int(available.width()) - 24))
            h = min(int(geom.height()), max(760, int(available.height()) - 48))
            x = max(int(available.left()), min(int(geom.x()), int(available.right()) - w + 1))
            y = max(int(available.top()), min(int(geom.y()), int(available.bottom()) - h + 1))
            if (x, y, w, h) != (int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())):
                self.setGeometry(x, y, w, h)
        except Exception:
            return

    def _default_window_size(self: MainWindow) -> QSize:
        width = max(1100, self._settings_int_value('window_width', DEFAULT_WINDOW_WIDTH))
        height = max(760, self._settings_int_value('window_height', DEFAULT_WINDOW_HEIGHT))
        return self._clamp_window_size_to_available(width, height)

    def _default_center_settings_splitter_sizes(self: MainWindow) -> list[int]:
        """Return default top/bottom sizes for the center settings splitter.

        The saved INI keys intentionally keep the older ``left_splitter_*``
        names for compatibility with v1.3.6+ user settings.
        """
        top = max(280, self._settings_int_value(CENTER_SETTINGS_LEGACY_SPLITTER_TOP_KEY, DEFAULT_LEFT_SPLITTER_TOP))
        bottom = max(92, self._settings_int_value(CENTER_SETTINGS_LEGACY_SPLITTER_BOTTOM_KEY, DEFAULT_LEFT_SPLITTER_BOTTOM))

        has_saved_top = self._settings_contains_key(CENTER_SETTINGS_LEGACY_SPLITTER_TOP_KEY)
        has_saved_state = self._settings_contains_key(CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY)
        if not has_saved_top and not has_saved_state:
            content_height = self._center_settings_content_height_hint()
            if content_height > 0:
                top = max(280, content_height)
                available_height = self._default_center_settings_splitter_available_height()
                if available_height > 0:
                    bottom = max(92, available_height - top)
        return [top, bottom]

    def _default_left_splitter_sizes(self: MainWindow) -> list[int]:
        """Legacy alias for center-settings splitter defaults."""
        return self._default_center_settings_splitter_sizes()

    def _default_preset_settings_splitter_sizes(self: MainWindow) -> list[int]:
        # Legacy compatibility for v1.3.8.4-v1.3.8.8 nested splitter INI keys.
        preset = max(220, self._settings_int_value(PRESET_PANEL_WIDTH_KEY, 300))
        settings = max(360, self._settings_int_value(CENTER_SETTINGS_PANEL_WIDTH_KEY, 680))
        return [preset, settings]

    def _default_three_pane_splitter_sizes(self: MainWindow) -> list[int]:
        preset_default, center_default = self._default_preset_settings_splitter_sizes()
        preset = max(220, self._settings_int_value(PRESET_PANEL_WIDTH_KEY, preset_default))
        center = max(360, self._settings_int_value(CENTER_SETTINGS_PANEL_WIDTH_KEY, center_default))
        preview = max(320, self._settings_int_value(PREVIEW_PANEL_WIDTH_KEY, 560))

        # If only the legacy v1.3.8.4-v1.3.8.8 combined width exists, reuse
        # it as a soft hint for preset + center without pinning the right pane.
        if (
            not self._settings_contains_key(PRESET_PANEL_WIDTH_KEY)
            and not self._settings_contains_key(CENTER_SETTINGS_PANEL_WIDTH_KEY)
            and self._settings_contains_key('left_panel_width')
        ):
            legacy_total = self._settings_int_value('left_panel_width', preset + center)
            if legacy_total > 0:
                preset = min(max(220, preset), 360)
                center = max(360, legacy_total - preset)
        return [preset, center, preview]

    def showEvent(self: MainWindow, event: object) -> None:
        super().showEvent(event)
        if self._startup_pending:
            self._startup_pending = False
            QTimer.singleShot(0, self._apply_initial_sizes)
            # 起動直後は右ペインが空白で残らないよう、
            # 保存済み target の復元可否を確認してからプレビューを初期化する。
            QTimer.singleShot(0, self._request_startup_preview_after_restore)
            QTimer.singleShot(0, self._startup_font_combo_scroll_reset)
            QTimer.singleShot(0, self._schedule_deferred_preview_size_sync)
            QTimer.singleShot(0, self._ensure_window_inside_available_area)
            # v1.3.8.15: avoid leaving a text caret in path/spin inputs
            # immediately after startup.  This is intentionally startup-only;
            # normal user clicks still focus and edit input widgets as before.
            QTimer.singleShot(0, self._clear_startup_input_focus)
        else:
            QTimer.singleShot(0, self._sync_preview_size)
            QTimer.singleShot(0, self._ensure_window_inside_available_area)

    def _startup_target_text(self: MainWindow) -> str:
        return _startup_target_text_impl(self)

    def _startup_target_path_exists(self: MainWindow, target_text: str) -> bool:
        return _startup_target_path_exists_impl(self, target_text)

    def _startup_previous_target_display_text(self: MainWindow, target_text: str) -> str:
        return _startup_previous_target_display_text_impl(self, target_text)

    def _confirm_startup_previous_target_preview(self: MainWindow, target_text: str) -> bool:
        return _confirm_startup_previous_target_preview_impl(self, target_text)

    def _set_target_path_for_normal_preview(self: MainWindow, path: object, *, block_signals: bool = True, exit_file_viewer: bool = True) -> str:
        return _set_target_path_for_normal_preview_impl(self, path, block_signals=block_signals, exit_file_viewer=exit_file_viewer)

    def on_target_text_changed(self: MainWindow, text: object = '') -> None:
        return on_target_text_changed_impl(self, text)

    def _clear_startup_target_for_sample_preview(self: MainWindow) -> None:
        return _clear_startup_target_for_sample_preview_impl(self)

    def _show_startup_sample_preview_status(self: MainWindow, message: str) -> None:
        return _show_startup_sample_preview_status_impl(self, message)

    def _request_startup_sample_preview(self: MainWindow) -> bool:
        return _request_startup_sample_preview_impl(self)

    def _schedule_startup_preview_idle_reconcile(self: MainWindow) -> None:
        return _schedule_startup_preview_idle_reconcile_impl(self)

    def _reconcile_startup_preview_idle_state(self: MainWindow, *, remaining_retries: int = 0) -> None:
        return _reconcile_startup_preview_idle_state_impl(self, remaining_retries=remaining_retries)

    def _request_startup_preview_after_restore(self: MainWindow) -> None:
        return _request_startup_preview_after_restore_impl(self)

    def _request_startup_sample_preview_if_no_target(self: MainWindow) -> None:
        return _request_startup_sample_preview_if_no_target_impl(self)

    def _startup_font_combo_scroll_reset(self: MainWindow) -> None:
        return _startup_font_combo_scroll_reset_impl(self)

    def resizeEvent(self: MainWindow, event: object) -> None:
        super().resizeEvent(event)
        # Windows/PySide6 の実機環境では、ライブリサイズ中に
        # preview_label / viewer_widget の最小サイズやレイアウトを更新すると、
        # 変換直後の重いプレビュー保持状態で Qt 側が落ちることがある。
        # リサイズ中は子ウィジェットのジオメトリを直接触らず、
        # 次回の表示更新・設定変更・起動時同期に任せる。
        return

    def _schedule_deferred_preview_size_sync(self: MainWindow) -> None:
        if getattr(self, '_preview_resize_sync_pending', False):
            return
        self._preview_resize_sync_pending = True
        try:
            QTimer.singleShot(75, self._run_deferred_preview_size_sync)
        except Exception:
            self._preview_resize_sync_pending = False
            self._run_deferred_preview_size_sync()

    def _run_deferred_preview_size_sync(self: MainWindow) -> None:
        self._preview_resize_sync_pending = False
        if getattr(self, '_preview_resize_sync_active', False):
            return
        self._preview_resize_sync_active = True
        try:
            self._sync_preview_size()
        except Exception:
            APP_LOGGER.exception('遅延プレビューサイズ同期に失敗しました')
        finally:
            self._preview_resize_sync_active = False

    def closeEvent(self: MainWindow, event: object) -> None:
        try:
            self.save_ui_state()
        except Exception:
            APP_LOGGER.exception('終了時のUI状態保存に失敗しました')
        worker = getattr(self, 'worker', None)
        if worker is not None:
            try:
                worker.stop()
            except Exception:
                pass
        worker_thread = getattr(self, 'worker_thread', None)
        if worker_thread is not None:
            try:
                worker_thread.quit()
            except Exception:
                pass
            wait_failed = False
            try:
                finished = worker_thread.wait(3000)
            except Exception:
                wait_failed = True
                is_running = getattr(worker_thread, 'isRunning', None)
                if callable(is_running):
                    try:
                        finished = not bool(is_running())
                    except Exception:
                        finished = False
                else:
                    finished = False
            if finished is False:
                self._show_information_dialog_with_status_fallback(
                    '変換停止中',
                    '変換の停止を待っています。停止完了後にもう一度閉じてください。',
                    fallback_status_message='変換停止中のため終了を保留しました。停止完了後にもう一度閉じてください。',
                )
                ignore = getattr(event, 'ignore', None)
                if callable(ignore):
                    ignore()
                return
            if wait_failed:
                APP_LOGGER.exception('終了時の変換スレッド待機状態の確認に失敗しました')
        self._mark_shutdown_clean(True)
        super().closeEvent(event)

    def _setup_global_navigation_shortcuts(self: MainWindow) -> None:
        # 左右キーは eventFilter 側で一元処理する。
        # 以前は QShortcut と KeyPress の両方で反応し、1回の押下で2ページ送られることがあった。
        self.left_arrow_shortcut = None
        self.right_arrow_shortcut = None

    def eventFilter(self: MainWindow, obj: object, event: object) -> bool:
        # v1.3.8.10: keep the center settings pane scrollable everywhere.
        # ComboBox / SpinBox-like controls still must not change their value by
        # wheel, so all wheel input inside the upper settings container is
        # redirected to the surrounding QScrollArea instead.
        if event.type() == QEvent.Wheel:
            if self._is_open_combo_popup_wheel_target(obj):
                return False
            if self._should_suppress_center_settings_wheel_value_change(obj):
                accept = getattr(event, 'accept', None)
                if callable(accept):
                    accept()
                self._scroll_center_settings_from_wheel_event(event)
                return True
            if self._should_scroll_center_settings_from_wheel_event(obj):
                accept = getattr(event, 'accept', None)
                if callable(accept):
                    accept()
                self._scroll_center_settings_from_wheel_event(event)
                return True

        # 実機ビュー由来の内部ページ送り：左右矢印キー対応
        if event.type() == QEvent.ShortcutOverride:
            key = event.key()
            if key in (Qt.Key_Left, Qt.Key_Right) and self._can_handle_right_pane_arrow_key():
                event.accept()
                return True
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Left, Qt.Key_Right):
                if self._handle_right_pane_arrow_key(key):
                    event.accept()
                    return True
        return super().eventFilter(obj, event)


    def _combo_popup_is_visible(self: MainWindow, combo: object) -> bool:
        return _combo_popup_is_visible_impl(self, combo)


    def _is_open_combo_popup_wheel_target(self: MainWindow, obj: object) -> bool:
        return _is_open_combo_popup_wheel_target_impl(self, obj)


    def _wheel_value_change_control_for_event_object(self: MainWindow, obj: object) -> object | None:
        return _wheel_value_change_control_for_event_object_impl(self, obj)


    def _should_suppress_center_settings_wheel_value_change(self: MainWindow, obj: object) -> bool:
        return _should_suppress_center_settings_wheel_value_change_impl(self, obj)


    def _should_suppress_left_settings_wheel_value_change(self: MainWindow, obj: object) -> bool:
        return _should_suppress_left_settings_wheel_value_change_impl(self, obj)


    def _should_scroll_center_settings_from_wheel_event(self: MainWindow, obj: object) -> bool:
        return _should_scroll_center_settings_from_wheel_event_impl(self, obj)


    def _should_scroll_left_settings_from_wheel_event(self: MainWindow, obj: object) -> bool:
        return _should_scroll_left_settings_from_wheel_event_impl(self, obj)


    def _install_center_settings_wheel_value_guards(self: MainWindow) -> None:
        _install_center_settings_wheel_value_guards_impl(self)


    def _install_left_settings_wheel_value_guards(self: MainWindow) -> None:
        _install_left_settings_wheel_value_guards_impl(self)


    def _scroll_center_settings_from_wheel_event(self: MainWindow, event: object) -> None:
        _scroll_center_settings_from_wheel_event_impl(self, event)


    def _scroll_left_settings_from_wheel_event(self: MainWindow, event: object) -> None:
        _scroll_left_settings_from_wheel_event_impl(self, event)


    @staticmethod
    def _is_widget_descendant_of(widget: object, ancestor: object) -> bool:
        return _is_widget_descendant_of_impl(widget, ancestor)


    def _center_settings_container_widget(self: MainWindow) -> object | None:
        """Return the v1.3.8 center settings container.

        The legacy ``left_settings_*`` attributes remain as compatibility
        aliases because many older tests and helpers still refer to the
        pre-three-pane layout.  New v1.3.8 code should prefer this helper.
        """
        attrs = getattr(self, '__dict__', {})
        return attrs.get('center_settings_container') or attrs.get('left_settings_container')

    def _center_settings_scroll_area(self: MainWindow) -> object | None:
        """Return the v1.3.8 center settings QScrollArea.

        Keep ``left_settings_scroll`` as a legacy alias, but avoid spreading
        the old two-pane name through new wheel/focus cleanup code.
        """
        attrs = getattr(self, '__dict__', {})
        return attrs.get('center_settings_scroll') or attrs.get('left_settings_scroll')

    def _set_center_settings_widget_aliases(self: MainWindow, *, container: object, scroll: object) -> None:
        """Register center-settings widgets and legacy aliases in one place.

        v1.3.8 turned the former left settings pane into the center pane.
        Keeping the legacy attributes is deliberate for older tests, saved-state
        helpers, and maintenance scripts; new code should resolve the widgets
        through the center-named helpers above.
        """
        self.center_settings_container = container
        self.center_settings_scroll = scroll
        self.left_settings_container = container
        self.left_settings_scroll = scroll

    def _center_settings_splitter_widget(self: MainWindow) -> object | None:
        """Return the v1.3.8 center settings splitter.

        ``left_splitter`` remains as a compatibility alias because the INI keys
        and many older tests still use the pre-three-pane name.
        """
        attrs = getattr(self, '__dict__', {})
        return attrs.get('center_settings_splitter') or attrs.get('left_splitter')

    def _set_center_settings_splitter_aliases(self: MainWindow, splitter: object) -> None:
        """Register the center settings splitter and its legacy alias."""
        self.center_settings_splitter = splitter
        self.left_splitter = splitter

    def _center_settings_splitter_state_value(self: MainWindow) -> object | None:
        """Return the splitter state for the historical left_splitter_state key."""
        splitter = self._center_settings_splitter_widget()
        if splitter is None:
            return None
        try:
            return splitter.saveState()
        except Exception:
            return None

    def _center_settings_splitter_sizes_value(self: MainWindow) -> list[int]:
        """Return current center-settings splitter sizes, if available."""
        splitter = self._center_settings_splitter_widget()
        if splitter is None:
            return []
        try:
            return list(splitter.sizes())
        except Exception:
            return []

    def _set_center_settings_splitter_sizes(self: MainWindow, sizes: Sequence[int]) -> None:
        """Apply sizes to the center-settings splitter through the center alias."""
        splitter = self._center_settings_splitter_widget()
        if splitter is None:
            return
        try:
            splitter.setSizes(list(sizes))
        except Exception:
            return

    def _restore_center_settings_splitter_from_payload(
        self: MainWindow,
        *,
        splitter_state: object | None,
        splitter_sizes: Sequence[int],
    ) -> None:
        """Restore the center-settings splitter while keeping old INI keys."""
        splitter = self._center_settings_splitter_widget()
        if splitter is None:
            return
        splitter_restored = False
        if splitter_state is not None:
            try:
                splitter_restored = bool(splitter.restoreState(splitter_state))
            except Exception:
                splitter_restored = False
        if not splitter_restored:
            self._set_center_settings_splitter_sizes(splitter_sizes)

    def _clear_startup_input_focus(self: MainWindow) -> None:
        _clear_startup_input_focus_impl(self)



    def _can_handle_right_pane_arrow_key(self: MainWindow) -> bool:
        view_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        if view_mode == 'font':
            if self._is_file_viewer_mode_active():
                if not self._runtime_xtc_pages():
                    return False
            elif not self._runtime_preview_pages():
                return False
        elif view_mode == 'device':
            if self._effective_right_pane_source() == 'preview':
                if not self._runtime_device_preview_pages():
                    return False
            elif self._xtc_page_count() <= 0:
                return False
        else:
            return False

        fw = QApplication.focusWidget()
        # 入力・選択系ウィジェットでは矢印キー本来の挙動を優先
        widget = fw
        visited_widget_ids: set[int] = set()
        while widget is not None and id(widget) not in visited_widget_ids:
            visited_widget_ids.add(id(widget))
            if isinstance(widget, (QLineEdit, QTextEdit, QSpinBox, QComboBox, QListWidget)):
                return False
            class_names = {cls.__name__ for cls in type(widget).__mro__}
            if class_names & {'QPlainTextEdit', 'QAbstractSpinBox', 'QAbstractItemView', 'QListView'}:
                return False
            parent_getter = getattr(widget, 'parent', None)
            widget = parent_getter() if callable(parent_getter) else None
        return True

    def _can_handle_device_view_arrow_key(self: MainWindow) -> bool:
        """Legacy wrapper for older device-view key-handler terminology."""
        return self._can_handle_right_pane_arrow_key()

    def _handle_right_pane_arrow_key(self: MainWindow, key: int) -> bool:
        if not self._can_handle_right_pane_arrow_key():
            return False

        if hasattr(self, 'viewer_widget'):
            self.viewer_widget.setFocus(Qt.ShortcutFocusReason)

        logical_delta = -1 if key == Qt.Key_Left else 1
        delta = -logical_delta if bool(getattr(self, 'nav_buttons_reversed', False)) else logical_delta
        self.change_page(delta)
        return True

    def _handle_device_view_arrow_key(self: MainWindow, key: int) -> bool:
        """Legacy wrapper for older device-view key-handler terminology."""
        return self._handle_right_pane_arrow_key(key)

    def _apply_initial_sizes(self: MainWindow) -> None:
        if self._pending_left_panel_width is not None:
            left_panel_visible = True
            if hasattr(self, 'left_panel') and hasattr(self.left_panel, 'isVisible'):
                try:
                    left_panel_visible = bool(self.left_panel.isVisible())
                except Exception:
                    left_panel_visible = True
            if left_panel_visible:
                self._apply_left_panel_width(self._pending_left_panel_width)
                self._pending_left_panel_width = None
        if not self._settings_contains_key(CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY):
            self._set_center_settings_splitter_sizes(self._default_center_settings_splitter_sizes())
        if not self._settings_contains_key(MAIN_THREE_PANE_SPLITTER_STATE_KEY):
            try:
                self.main_splitter.setSizes(self._default_three_pane_splitter_sizes())
            except Exception:
                pass
        self._sync_preview_size()

    def _on_main_three_pane_splitter_moved(self: MainWindow, *_args: object) -> None:
        """Refresh width-sensitive preset summary sizing after pane resize."""
        try:
            self._update_preset_summary_label_layout(queue_retry=True)
        except Exception:
            pass


    # ── UI 構築 ────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_top_bar())

        sep = QFrame()
        sep.setFrameShape(
            self._qframe_shape_constant('HLine', self._qframe_shape_constant('NoFrame', 0))
        )
        sep.setObjectName('topSep')
        root.addWidget(sep)

        self.preset_panel = self._build_preset_side_panel()
        self.preset_panel.setObjectName('presetSidePanel')
        self.preset_panel.setMinimumWidth(220)
        self.preset_panel.setMaximumWidth(360)
        # Keep the legacy attribute name for panel visibility actions, but do
        # not wrap preset + center in a nested splitter. v1.3.8.9 uses one
        # three-way splitter so the left/center and center/right handles feel
        # independent.
        self.left_panel = self.preset_panel

        self.center_settings_panel = self._build_center_settings_panel()
        self.center_settings_panel.setMinimumWidth(360)

        right = self._build_right_preview()
        try:
            right.setMinimumWidth(320)
        except Exception:
            pass

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setObjectName('mainThreePaneSplitter')
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.addWidget(self.preset_panel)
        self.main_splitter.addWidget(self.center_settings_panel)
        self.main_splitter.addWidget(right)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 2)
        self.main_splitter.setSizes(self._default_three_pane_splitter_sizes())
        try:
            self.main_splitter.splitterMoved.connect(self._on_main_three_pane_splitter_moved)
        except Exception:
            pass

        root.addWidget(self.main_splitter, 1)
        self.main_view_mode = 'font'
        self._show_ui_status_message_with_reflection_or_direct_fallback(self._ui_text('準備完了'), None)

    # ── トップバー ─────────────────────────────────────────

    def _build_top_bar(self):
        return _build_top_bar_impl(self)

    @staticmethod
    def _v_sep():
        line = QFrame()
        vline = getattr(QFrame, 'VLine', getattr(QFrame, 'HLine', getattr(QFrame, 'NoFrame', 0)))
        line.setFrameShape(vline)
        line.setObjectName('vSep')
        line.setFixedWidth(1)
        return line

    # ── 左プリセットパネル ────────────────────────────────

    def _build_preset_side_panel(self):
        preset_plan = self._localized_plan(gui_layouts.build_preset_side_panel_plan())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(self._plan_frame_shape_value(preset_plan, 'scroll_frame_shape', 'no_frame'))
        scroll.setHorizontalScrollBarPolicy(
            self._plan_scroll_bar_policy_value(preset_plan, 'scroll_horizontal_scroll_bar_policy', 'as_needed')
        )
        scroll.setVerticalScrollBarPolicy(
            self._plan_scroll_bar_policy_value(preset_plan, 'scroll_vertical_scroll_bar_policy', 'as_needed')
        )

        container = QWidget()
        container.setObjectName(str(preset_plan.get('container_object_name', 'presetSideContainer')))
        container.setMinimumWidth(self._plan_int_value(preset_plan, 'minimum_content_width', 280))
        lay = QVBoxLayout(container)
        lay.setContentsMargins(*self._plan_int_tuple_value(preset_plan, 'contents_margins', (10, 9, 10, 9), expected_length=4))
        lay.setSpacing(self._plan_int_value(preset_plan, 'spacing', 8))
        lay.addWidget(self._section_language())
        lay.addWidget(self._section_preset())
        lay.addStretch(1)
        scroll.setWidget(container)
        return scroll

    # ── 中央設定パネル ────────────────────────────────────

    def _build_center_settings_panel(self):
        return self._build_center_settings()

    def _build_center_settings(self):
        container_plan = gui_layouts.build_center_settings_container_plan()
        self._set_center_settings_splitter_aliases(QSplitter(Qt.Vertical))
        self.center_settings_splitter.setChildrenCollapsible(
            self._plan_bool_value(container_plan, 'splitter_children_collapsible', False)
        )
        self.center_settings_splitter.setHandleWidth(self._plan_int_value(container_plan, 'splitter_handle_width', 5))

        scroll = QScrollArea()
        scroll.setWidgetResizable(self._plan_bool_value(container_plan, 'scroll_widget_resizable', True))
        scroll.setFrameShape(self._plan_frame_shape_value(container_plan, 'scroll_frame_shape', 'no_frame'))
        scroll.setHorizontalScrollBarPolicy(
            self._plan_scroll_bar_policy_value(container_plan, 'scroll_horizontal_scroll_bar_policy', 'as_needed')
        )
        scroll.setVerticalScrollBarPolicy(
            self._plan_scroll_bar_policy_value(container_plan, 'scroll_vertical_scroll_bar_policy', 'as_needed')
        )

        container = QWidget()
        container.setObjectName(str(container_plan.get('container_object_name', 'leftSettingsContainer')))
        container.setMinimumWidth(self._plan_int_value(container_plan, 'scroll_minimum_content_width', 560))
        self._set_center_settings_widget_aliases(container=container, scroll=scroll)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(*self._plan_int_tuple_value(container_plan, 'contents_margins', (10, 9, 10, 9), expected_length=4))
        lay.setSpacing(self._plan_int_value(container_plan, 'spacing', 5))
        self._ensure_behavior_controls()
        for section in self._center_settings_sections():
            lay.addWidget(section)
        lay.addWidget(self._build_center_settings_bottom_separator(container_plan))
        scroll.setWidget(container)
        self._install_center_settings_wheel_value_guards()

        self.bottom_panel = self._build_bottom_panel()
        self.bottom_panel.setMinimumHeight(self._plan_int_value(container_plan, 'bottom_panel_min_height', 92))

        self.center_settings_splitter.addWidget(scroll)
        self.center_settings_splitter.addWidget(self.bottom_panel)
        self.center_settings_splitter.setStretchFactor(
            0, self._plan_int_value(container_plan, 'splitter_top_stretch_factor', 3)
        )
        self.center_settings_splitter.setStretchFactor(
            1, self._plan_int_value(container_plan, 'splitter_bottom_stretch_factor', 1)
        )
        self._set_center_settings_splitter_sizes(self._default_center_settings_splitter_sizes())
        return self.center_settings_splitter

    def _build_left_settings(self):
        """Legacy alias for the v1.3.8 center settings pane builder."""
        return self._build_center_settings()

    def _build_center_settings_bottom_separator(self: MainWindow, container_plan: Mapping[str, Any]) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(
            self._plan_frame_shape_value(container_plan, 'bottom_separator_frame_shape', 'hline')
        )
        sep.setObjectName(str(container_plan.get('bottom_separator_object_name', 'leftSettingsBottomSep')))
        sep.setFixedHeight(self._plan_int_value(container_plan, 'bottom_separator_height', 1))
        return sep

    def _build_left_settings_bottom_separator(self: MainWindow, container_plan: Mapping[str, Any]) -> QFrame:
        """Legacy alias for the center settings bottom separator builder."""
        return self._build_center_settings_bottom_separator(container_plan)

    def _center_settings_content_height_hint(self: MainWindow) -> int:
        container = self._center_settings_container_widget()
        if container is None:
            return 0
        try:
            height = int(container.sizeHint().height())
        except Exception:
            return 0
        return max(0, height)

    def _left_settings_content_height_hint(self: MainWindow) -> int:
        """Legacy alias for the center settings content height hint."""
        return self._center_settings_content_height_hint()

    def _default_center_settings_splitter_available_height(self: MainWindow) -> int:
        splitter = self._center_settings_splitter_widget()
        if splitter is None:
            return 0
        try:
            return max(0, int(splitter.height()))
        except Exception:
            return 0

    def _default_left_splitter_available_height(self: MainWindow) -> int:
        """Legacy alias for center-settings splitter height lookup."""
        return self._default_center_settings_splitter_available_height()

    def _center_settings_section_factories(self):
        return {
            'preset': self._section_preset,
            'output': self._section_output,
            'composition': self._section_composition,
            'position': self._section_position,
            'preview_controls': self._section_preview_controls,
            # Keep only active section keys here. Legacy factory aliases are
            # intentionally not registered because these section factories are
            # not idempotent and recreate widget attributes when called twice.
            'fileviewer': self._section_file_viewer,
            'behavior': self._section_behavior,
        }

    def _center_settings_sections(self):
        factories = self._center_settings_section_factories()
        sections = []
        for section_key in gui_layouts.build_center_settings_section_keys():
            factory = factories.get(str(section_key).strip().lower())
            if factory is not None:
                sections.append(factory())
        return sections

    def _left_settings_section_factories(self):
        """Legacy alias for the v1.3.8 center settings section factories."""
        return self._center_settings_section_factories()

    def _left_settings_sections(self):
        """Legacy alias for the v1.3.8 center settings sections."""
        return self._center_settings_sections()

    def _build_section_box_layout(
        self,
        section_key: object,
        fallback_title: str,
        *,
        default_margins: tuple[int, int, int, int],
        default_spacing: int,
    ) -> tuple[QGroupBox, QVBoxLayout, dict[str, Any]]:
        section_plan = self._localized_plan(gui_layouts.build_center_settings_section_layout_plan(section_key))
        title = self._ui_text(str(section_plan.get('title', fallback_title)))
        return gui_widget_factory.make_section_box_layout(
            title,
            section_plan,
            default_margins=default_margins,
            default_spacing=default_spacing,
        )

    # ── 設定セクション：出力先 ──────────────────────────

    def _section_output(self):
        return _section_output_impl(self)

    # ── 設定セクション：組版 ────────────────────────────

    def _section_composition(self):
        return _section_composition_impl(self)

    # Backward-compatible alias for older tests/probes. v1.3.8.6 splits
    # the old combined section into 出力先 + 組版.
    def _section_font(self):
        """Legacy probe hook; section factories recreate widgets and are not idempotent."""
        return self._section_composition()

    def _build_margin_rows(self):
        return _build_margin_rows_impl(self)

    def _section_preview_controls(self):
        return _section_preview_controls_impl(self)

    def _section_display(self):
        """Legacy probe hook; section factories recreate widgets and are not idempotent."""
        return self._section_preview_controls()

    # ── 設定セクション：位置補正 ──────────────────────────

    def _section_position(self):
        return _section_position_impl(self)

    # Backward-compatible alias for older tests/probes. v1.3.8.6 moved the
    # image-processing toggles into _section_composition() and kept this slot
    # for position correction only.
    def _section_image(self):
        """Legacy probe hook; section factories recreate widgets and are not idempotent."""
        return self._section_position()

    # ── 設定セクション：表示言語 ────────────────────────

    def _section_language(self):
        return _section_language_impl(self)

    # ── 設定セクション：プリセット ────────────────────────

    def _section_preset(self):
        return _section_preset_impl(self)

    def _make_position_mode_combo(self, options, changed_slot) -> QComboBox:
        return _make_position_mode_combo_impl(self, options, changed_slot)

    def _make_glyph_position_combo(self) -> QComboBox:
        return _make_glyph_position_combo_impl(self)

    def _add_glyph_position_control(self, row, label: str, combo: QComboBox, help_text: str) -> None:
        return _add_glyph_position_control_impl(self, row, label, combo, help_text)

    def _ensure_behavior_controls(self):
        return _ensure_behavior_controls_impl(self)

    # ── 設定セクション：その他オプション ────────────────────────

    def _section_behavior(self):
        return _section_behavior_impl(self)

    def _section_file_viewer(self):
        return _section_file_viewer_impl(self)

    # ── 右プレビューパネル ────────────────────────────────

    def _build_right_preview(self):
        return _build_right_preview_impl(self)

    def _build_view_toggle_bar(self):
        return _build_view_toggle_bar_impl(self)

    def _add_preview_display_toggles_to_layout(self, lay: QHBoxLayout) -> None:
        return _add_preview_display_toggles_to_layout_impl(self, lay)

    def _build_conversion_completion_card(self):
        return _build_conversion_completion_card_impl(self)

    def _hide_conversion_completion_card(self: MainWindow) -> None:
        return _hide_conversion_completion_card_impl(self)

    def _show_results_tab_from_completion_card(self: MainWindow) -> None:
        return _show_results_tab_from_completion_card_impl(self)

    def _completion_card_parent_texts(self: MainWindow, paths: object) -> list[str]:
        return _completion_card_parent_texts_impl(self, paths)

    def _completion_card_result_item_texts(
        self: MainWindow,
        paths: object,
        *,
        base_path: object = '',
        max_items: int = 5,
    ) -> list[str]:
        return _completion_card_result_item_texts_impl(
            self,
            paths,
            base_path=base_path,
            max_items=max_items,
        )

    def _build_conversion_completion_card_message(
        self: MainWindow,
        converted_files: object,
        result: Mapping[str, object] | None = None,
    ) -> str:
        return _build_conversion_completion_card_message_impl(self, converted_files, result)

    def _meaningful_open_folder_target_text(self: MainWindow, value: object) -> str:
        return _meaningful_open_folder_target_text_impl(self, value)

    def _source_target_parent_text(self: MainWindow) -> str:
        return _source_target_parent_text_impl(self)

    def _planned_open_folder_target_from_settings(self: MainWindow, cfg: Mapping[str, object] | None = None) -> str:
        return _planned_open_folder_target_from_settings_impl(self, cfg)

    def _resolve_conversion_open_folder_target(
        self: MainWindow,
        converted_files: object,
        result: Mapping[str, object] | None = None,
    ) -> str:
        return _resolve_conversion_open_folder_target_impl(self, converted_files, result)

    def _show_conversion_completion_card(
        self: MainWindow,
        converted_files: object,
        result: Mapping[str, object] | None = None,
    ) -> bool:
        return _show_conversion_completion_card_impl(self, converted_files, result)

    def _build_nav_bar(self):
        return _build_nav_bar_impl(self)

    def _ensure_nav_reverse_control(self: MainWindow, nav_bar_plan: dict | None = None):
        return _ensure_nav_reverse_control_impl(self, nav_bar_plan)

    def _add_nav_controls_to_layout(self, lay: QHBoxLayout, *, nav_bar_plan: dict | None = None, current_label_stretch: int = 0) -> None:
        return _add_nav_controls_to_layout_impl(
            self,
            lay,
            nav_bar_plan=nav_bar_plan,
            current_label_stretch=current_label_stretch,
        )

    def _nav_section_separator(self, nav_bar_plan: Mapping[str, Any]) -> QFrame:
        return _nav_section_separator_impl(self, nav_bar_plan)

    def _add_preview_zoom_controls_to_layout(self, lay: QHBoxLayout, *, toggle_plan: dict | None = None) -> None:
        return _add_preview_zoom_controls_to_layout_impl(self, lay, toggle_plan=toggle_plan)

    # ── 下部パネル（ステータス + 結果/ログ）────────────────

    def _build_bottom_panel(self):
        return _build_bottom_panel_impl(self)

    def _build_results_tab(self):
        return _build_results_tab_impl(self)

    def _build_log_tab(self):
        return _build_log_tab_impl(self, _session_log_path_for_display())

    def _active_bottom_panel_scrollbar(self: MainWindow) -> object | None:
        return _active_bottom_panel_scrollbar_impl(self)

    def _bind_bottom_panel_external_scrollbar(self: MainWindow) -> None:
        _bind_bottom_panel_external_scrollbar_impl(self)

    def _set_bottom_panel_external_scrollbar_range(
        self: MainWindow,
        minimum: int,
        maximum: int,
        value: int,
        page_step: int,
        single_step: int,
    ) -> None:
        _set_bottom_panel_external_scrollbar_range_impl(
            self,
            minimum,
            maximum,
            value,
            page_step,
            single_step,
        )

    def _sync_bottom_panel_external_scrollbar(self: MainWindow, *_args: object) -> None:
        _sync_bottom_panel_external_scrollbar_impl(self, *_args)

    def _apply_bottom_panel_external_scroll_value(self: MainWindow, value: int) -> None:
        _apply_bottom_panel_external_scroll_value_impl(self, value)

    # ── ヘルパー ───────────────────────────────────────────

    @staticmethod
    def _apply_button_widget_plan(button: QPushButton, plan: Mapping[str, Any]) -> QPushButton:
        return gui_widget_factory.apply_button_widget_plan(button, plan, no_focus_policy=Qt.NoFocus)

    def _make_button_from_plan(
        self,
        plan: Mapping[str, Any],
        clicked: Callable[..., Any] | None = None,
    ) -> QPushButton:
        return gui_widget_factory.make_button_from_plan(
            plan,
            clicked,
            no_focus_policy=Qt.NoFocus,
        )

    @staticmethod
    def _make_hbox_layout_from_plan(
        plan: Mapping[str, Any] | None = None,
        *,
        default_spacing: int = 0,
        default_margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    ) -> QHBoxLayout:
        return gui_widget_factory.make_hbox_layout_from_plan(
            plan,
            default_spacing=default_spacing,
            default_margins=default_margins,
        )

    def _build_labeled_widget_row(
        self,
        pairs: Sequence[tuple[str, QWidget]],
        *,
        spacing: int = 3,
        pair_spacing: int = 6,
        label_object_name: str = 'dimLabel',
        trailing_stretch: bool = True,
    ) -> QHBoxLayout:
        return gui_widget_factory.build_labeled_widget_row(
            pairs,
            spacing=spacing,
            pair_spacing=pair_spacing,
            label_object_name=label_object_name,
            trailing_stretch=trailing_stretch,
        )

    @staticmethod
    def _make_section(title: str) -> QGroupBox:
        return gui_widget_factory.make_section(title)

    @staticmethod
    def _dim_label(text: str) -> QLabel:
        return gui_widget_factory.make_dim_label(text)


    @staticmethod
    def _note_label(text: str) -> QLabel:
        return gui_widget_factory.make_note_label(text)

    def _help_icon_button(self, text: str, *, tooltip: str | None = None, title: str | None = None) -> QPushButton:
        return gui_widget_factory.make_help_icon_button(
            self._ui_text(text),
            tooltip=self._ui_text(tooltip) if tooltip is not None else None,
            dialog_title=self._ui_text(title) if title is not None else None,
            clicked_with_button=lambda button, self=self: self._show_inline_help(button),
            no_focus_policy=Qt.NoFocus,
        )

    def _show_inline_help(self, button: QPushButton):
        text = self._ui_text(str(button.property('helpText') or '').strip())
        if not text:
            return
        title = self._ui_text(str(button.property('helpTitle') or '説明').strip() or '説明')
        try:
            msg = QMessageBox(self)
            msg.setWindowTitle(title)
            msg.setIcon(QMessageBox.Information)
            msg.setTextFormat(Qt.PlainText)
            msg.setText(text)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setDefaultButton(QMessageBox.Ok)
            msg.exec()
            return
        except Exception:
            pass
        try:
            self._show_ui_status_message_with_reflection_or_direct_fallback(text, 5000)
        except Exception:
            pass

    def _build_flow_guide(self) -> QFrame:
        box = QFrame()
        box.setObjectName('flowGuide')
        lay = QVBoxLayout(box)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        title_row = self._make_hbox_layout_from_plan(
            gui_layouts.build_row_layout_plan(spacing=6, contents_margins=(0, 0, 0, 0))
        )
        title = QLabel('使い方')
        title.setObjectName('flowGuideTitle')
        title_row.addWidget(title)
        title_row.addWidget(self._help_icon_button('1. ファイルを開く\n2. プリセットを選ぶ\n3. 必要なら微調整\n4. 変換実行\n5. 右ペインで確認'))
        title_row.addStretch(1)
        lay.addLayout(title_row)
        return box

    def _spin(self, minimum: int, maximum: int, value: int, *, compact: bool = False, buttons: bool = False) -> QSpinBox:
        s = VisibleArrowSpinBox()
        s.setRange(minimum, maximum)
        s.setValue(value)
        s.setAccelerated(True)
        s.setProperty('showSpinButtons', buttons)
        s.setProperty('uiTheme', self.current_ui_theme)
        if buttons:
            s.setButtonSymbols(QSpinBox.UpDownArrows)
            s.setFixedWidth(74 if compact else 80)
        else:
            s.setButtonSymbols(QSpinBox.NoButtons)
            s.setFixedWidth(56)
        if compact:
            s.setProperty('compactField', True)
            s.setFixedHeight(24)
        return s

    def _spin_row(self, pairs: list[tuple[str, QWidget]]) -> QHBoxLayout:
        return self._build_labeled_widget_row(
            pairs,
            spacing=3,
            pair_spacing=6,
            label_object_name='dimLabel',
            trailing_stretch=True,
        )

    # ── スタイルシート ─────────────────────────────────────

    def _apply_styles(self):
        stylesheet = self._dark_stylesheet() if self.current_ui_theme == 'dark' else self._light_stylesheet()
        try:
            spin_boxes = list(self.findChildren(QSpinBox))
        except Exception:
            spin_boxes = []
        for s in spin_boxes:
            try:
                s.setProperty('uiTheme', self.current_ui_theme)
                s.style().unpolish(s)
                s.style().polish(s)
                s.update()
            except Exception:
                pass
        try:
            self.setStyleSheet(stylesheet)
        except Exception:
            pass
        if hasattr(self, 'viewer_widget'):
            try:
                self.viewer_widget.set_ui_theme(self.current_ui_theme)
            except Exception:
                pass

    def _light_stylesheet(self) -> str:
        return light_stylesheet()

    def _dark_stylesheet(self) -> str:
        return dark_stylesheet()

    # ── ビュー切替 ────────────────────────────────────────

    def _normalized_main_view_mode(self: MainWindow, mode: object) -> str:
        return _normalized_main_view_mode(mode)

    def _preview_view_help_text(self: MainWindow) -> str:
        # Keep this small wrapper source-compatible with legacy regression tests
        # that assert the help text is owned by build_view_toggle_bar_plan(), while
        # still delegating to the split helper as the fallback implementation.
        localizer = getattr(self, '_localized_plan', None)
        toggle_plan = gui_layouts.build_view_toggle_bar_plan()
        if callable(localizer):
            toggle_plan = localizer(toggle_plan)
        if 'help_text' in toggle_plan:
            return str(toggle_plan.get('help_text'))
        return _preview_view_help_text()

    def _main_view_mode_help_text(self: MainWindow, mode: object) -> str:
        return _main_view_mode_help_text(mode)

    def _main_view_mode_status_text(self: MainWindow, mode: object) -> str:
        return _main_view_mode_status_text(mode)

    def _sync_preview_view_page_index_for_mode(self: MainWindow, mode: object) -> None:
        normalized = self._normalized_main_view_mode(mode)
        effective_source = self._effective_right_pane_source()
        preview_pages = self._runtime_preview_pages() if normalized == 'font' else []
        device_pages = self._runtime_device_preview_pages() if normalized != 'font' else []
        sync_state = studio_logic.build_right_pane_preview_page_sync_state(
            mode=normalized,
            effective_right_pane_source=effective_source,
            preview_page_count=len(preview_pages),
            device_preview_page_count=len(device_pages),
            current_preview_index=getattr(self, 'current_preview_page_index', 0),
            current_device_preview_index=getattr(self, 'current_device_preview_page_index', 0),
        )
        if not bool(sync_state.get('should_sync')):
            return
        target_index = worker_logic._int_config_value({'value': sync_state.get('target_index')}, 'value', 0)
        if sync_state.get('target') == 'font':
            if getattr(self, 'current_preview_page_index', 0) != target_index:
                self.current_preview_page_index = target_index
            return
        if sync_state.get('target') == 'device':
            if getattr(self, 'current_device_preview_page_index', 0) != target_index:
                self.current_device_preview_page_index = target_index

    def _apply_main_view_mode_ui(self: MainWindow, mode: object) -> str:
        normalized = self._normalized_main_view_mode(mode)
        is_font = normalized == 'font'
        self.main_view_mode = normalized
        self._sync_preview_view_page_index_for_mode(normalized)
        preview_stack = getattr(self, 'preview_stack', None)
        set_current_index = getattr(preview_stack, 'setCurrentIndex', None)
        if callable(set_current_index):
            set_current_index(0 if is_font else 1)
        for button_name, checked in (('font_view_btn', is_font), ('device_view_btn', not is_font)):
            button = getattr(self, button_name, None)
            setter = getattr(button, 'setChecked', None)
            if callable(setter):
                setter(checked)
        view_tip = self._ui_text(self._main_view_mode_help_text(normalized))
        view_help_btn = getattr(self, 'view_help_btn', None)
        tooltip_setter = getattr(view_help_btn, 'setToolTip', None)
        if callable(tooltip_setter):
            tooltip_setter(view_tip)
        property_setter = getattr(view_help_btn, 'setProperty', None)
        if callable(property_setter):
            property_setter('helpText', view_tip)
        self._sync_preview_zoom_control_state()
        if hasattr(self, 'update_navigation_ui'):
            self.update_navigation_ui()
        return normalized

    def _focus_main_view_mode_widget_later(self: MainWindow, mode: object) -> None:
        normalized = self._normalized_main_view_mode(mode)
        if normalized != 'device' or not hasattr(self, 'viewer_widget'):
            return
        QTimer.singleShot(0, lambda: self.viewer_widget.setFocus(Qt.OtherFocusReason))

    def _resync_device_preview_layout_now_and_later(self: MainWindow) -> None:
        """Synchronize device-view geometry after the scroll viewport settles.

        v1.3.3.23: when switching from font view to device view immediately
        after startup, Qt can report the device scroll viewport before the
        stacked page has its final width.  That made preview_leading_gap look
        like zero and caused the device mockup to jump to the splitter side.
        Run the same sync immediately and again on the next event-loop turns so
        device view / actual-size approximation get the same settled placement
        that font view already receives after pixmap refresh.
        """
        if not hasattr(self, 'viewer_widget'):
            return

        def _sync() -> None:
            try:
                self._sync_viewer_size()
            except Exception:
                APP_LOGGER.exception('実機ビューの遅延レイアウト同期に失敗しました')

        _sync()
        single_shot = getattr(QTimer, 'singleShot', None)
        if callable(single_shot):
            for delay_ms in (0, 50):
                try:
                    single_shot(delay_ms, _sync)
                except Exception:
                    pass

    def _refresh_active_view_after_mode_change(self: MainWindow, mode: object) -> None:
        return _refresh_active_view_after_mode_change_impl(self, mode)

    def set_main_view_mode(self: MainWindow, mode: str, initial: bool = False) -> None:
        normalized = self._apply_main_view_mode_ui(mode)
        self._refresh_active_view_after_mode_change(normalized)
        self._focus_main_view_mode_widget_later(normalized)
        if not initial:
            self._show_ui_status_message_unless_render_failure_visible(
                self._main_view_mode_status_text(normalized),
                2000,
            )
            self.save_ui_state()

    def toggle_left_panel(self: MainWindow) -> None:
        vis = not self.left_panel.isVisible()
        if not vis:
            try:
                sizes = self.main_splitter.sizes()
            except Exception:
                sizes = []
            if sizes and sizes[0] > 0:
                self._pending_left_panel_width = sizes[0]
        self.left_panel.setVisible(vis)
        if vis:
            width = self._pending_left_panel_width
            if not width:
                width = self._settings_int_value('left_panel_width', DEFAULT_LEFT_PANEL_WIDTH)
            if width and width > 0:
                self._apply_left_panel_width(width)
            self._pending_left_panel_width = None
        self._show_ui_status_message_unless_render_failure_visible(
            '設定パネルを表示しました。' if vis else '設定パネルを非表示にしました。',
            2000,
        )
        self.save_ui_state()

    def set_ui_theme(self: MainWindow, theme: str, persist: bool = True) -> None:
        normalized = 'dark' if theme == 'dark' else 'light'
        if self.__dict__.get('current_ui_theme', 'light') == normalized and hasattr(self, 'viewer_widget'):
            self.viewer_widget.set_ui_theme(normalized)
            if persist:
                self.settings_store.setValue('ui_theme', normalized)
                self.settings_store.sync()
            return

        self.current_ui_theme = normalized
        self._apply_styles()
        try:
            if self._runtime_preview_pages():
                self.render_current_preview_page()
        except Exception:
            pass
        if persist:
            self.settings_store.setValue('ui_theme', normalized)
            self.settings_store.sync()
            self._show_ui_status_message_unless_render_failure_visible(
                '外観をダークに切り替えました。' if normalized == 'dark' else '外観を白基調に切り替えました。',
                2000,
            )

    def set_panel_button_visible(self: MainWindow, visible: bool, persist: bool = True) -> None:
        self.panel_button_visible = bool(visible)
        if hasattr(self, 'panel_btn'):
            self.panel_btn.setVisible(self.panel_button_visible)
        if persist:
            self.settings_store.setValue('panel_button_visible', self.panel_button_visible)
            self.settings_store.sync()
            self._show_ui_status_message_unless_render_failure_visible(
                '三本線ボタンを表示しました。' if self.panel_button_visible else '三本線ボタンを非表示にしました。',
                2000,
            )

    def show_display_settings_popup(self: MainWindow) -> None:
        # Delegated helper keeps the localized appearance section contract:
        # menu.addSection(self._ui_text('外観'))
        _show_display_settings_popup_impl(
            self,
            menu_class=QMenu,
            action_group_class=QActionGroup,
            point_class=QPoint,
            application_class=QApplication,
            output_conflict_options=OUTPUT_CONFLICT_OPTIONS,
        )

    def _apply_left_panel_width(self: MainWindow, width: int) -> None:
        """main_splitter の左プリセットペイン幅を確実にセットする。"""
        total = self.main_splitter.width()
        if total <= 0:
            QTimer.singleShot(50, lambda: self._apply_left_panel_width(width))
            return
        if width <= 0:
            return
        # Values above the preset pane's realistic maximum are legacy
        # combined left+center widths from the old two/nested splitter layout.
        # Keep accepting them for tests/INI compatibility, but apply only the
        # preset-pane portion in the single three-way splitter.
        if width > 500:
            width = self._settings_int_value(PRESET_PANEL_WIDTH_KEY, 300)
        current_sizes = list(self.main_splitter.sizes())
        if len(current_sizes) < 3:
            current_sizes = self._default_three_pane_splitter_sizes()
        left_min = 220
        center_min = 360
        right_min = 320
        left = max(left_min, min(width, max(left_min, total - center_min - right_min)))
        remaining = max(center_min + right_min, total - left)
        center = max(center_min, current_sizes[1] if len(current_sizes) >= 2 else 680)
        right = max(right_min, current_sizes[2] if len(current_sizes) >= 3 else remaining - center)
        scale_base = max(1, center + right)
        center = max(center_min, int(round(remaining * center / scale_base)))
        right = max(right_min, remaining - center)
        if center + right > remaining:
            center = max(center_min, remaining - right_min)
            right = max(right_min, remaining - center)
        self.main_splitter.setSizes([left, center, right])

    # ── プレビュー ─────────────────────────────────────────

    def _clear_preview_label_pixmap(self: MainWindow) -> None:
        if not hasattr(self, 'preview_label'):
            return
        self._last_font_preview_scaled_size = None
        try:
            self.preview_label.setContentsMargins(0, 0, 0, 0)
        except Exception:
            pass
        try:
            self.preview_label.setMaximumSize(16777215, 16777215)
        except Exception:
            pass
        clear = getattr(self.preview_label, 'clear', None)
        if callable(clear):
            try:
                clear()
                return
            except Exception:
                pass
        set_pixmap = getattr(self.preview_label, 'setPixmap', None)
        if callable(set_pixmap):
            try:
                set_pixmap(QPixmap())
            except Exception:
                try:
                    set_pixmap(None)
                except Exception:
                    pass

    def _current_preview_payload(self: MainWindow) -> dict[str, object]:
        base = self._current_render_settings_base()
        preview_limit = self.preview_page_limit_spin.value() if hasattr(self, 'preview_page_limit_spin') else DEFAULT_PREVIEW_PAGE_LIMIT
        return preview_controller.build_preview_payload(
            render_settings_base=base,
            current_preview_mode=getattr(self, 'current_preview_mode', 'text'),
            selected_profile_key=self._selected_profile_key(),
            preview_image_data_url=getattr(self, 'preview_image_data_url', None),
            preview_page_limit=preview_limit,
            default_preview_page_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
        )

    _coerce_preview_data_url = staticmethod(_coerce_preview_data_url)
    _coerce_preview_base64_text = staticmethod(_coerce_preview_base64_text)

    def _show_preview_message(self: MainWindow, message: str) -> None:
        self._clear_preview_label_pixmap()
        preview_label = getattr(self, 'preview_label', None)
        try:
            if preview_label is not None:
                preview_label.setAlignment(Qt.AlignCenter)
        except Exception:
            pass
        setter = getattr(preview_label, 'setText', None)
        if callable(setter):
            setter(self._ui_text(message))

    def on_target_editing_finished(self: MainWindow) -> None:
        # 対象パスを手入力で確定した場合も、ファイル選択と同じくプレビューを更新する。
        # ファイルビューワーで XTC/XTCH を直接表示した直後でも、手入力で通常
        # ターゲットへ戻した場合は、ファイル選択・ドロップと同じくビューワー
        # 状態を解除してから通常プレビューへ切り替える。
        # ただし重い生成処理は editingFinished / dialog handler の中で直接走らせず、
        # UI イベントループへ戻してから開始する。
        self._leave_file_viewer_mode_for_target_change()
        self._schedule_target_preview_refresh(reset_page=True)

    def _schedule_target_preview_refresh(self: MainWindow, *, reset_page: bool = True) -> None:
        _schedule_target_preview_refresh_impl(self, reset_page=reset_page, timer_class=QTimer)

    def _mark_preview_dirty_from_signal(self: MainWindow, *_args: object) -> None:
        _mark_preview_dirty_from_signal_impl(self, *_args)

    def _current_preview_page_limit_value(self: MainWindow) -> int:
        return _current_preview_page_limit_value_impl(self)

    def _should_auto_live_preview_refresh(self: MainWindow) -> bool:
        return _should_auto_live_preview_refresh_impl(self, auto_refresh_max=_AUTO_LIVE_PREVIEW_PAGE_LIMIT_MAX)

    def _manual_preview_required_status_message(self: MainWindow) -> str:
        return _manual_preview_required_status_message_impl(self, auto_refresh_max=_AUTO_LIVE_PREVIEW_PAGE_LIMIT_MAX)

    def _mark_preview_dirty_without_auto_refresh(self: MainWindow) -> None:
        _mark_preview_dirty_without_auto_refresh_impl(self, auto_refresh_max=_AUTO_LIVE_PREVIEW_PAGE_LIMIT_MAX)

    def _apply_manual_preview_required_context(self: MainWindow) -> None:
        _apply_manual_preview_required_context_impl(self)

    def _cancel_auto_live_preview_due_to_large_limit(self: MainWindow) -> None:
        _cancel_auto_live_preview_due_to_large_limit_impl(self)

    def _set_preview_update_button_visual_state(self: MainWindow, state: object) -> None:
        _set_preview_update_button_visual_state_impl(self, state)

    def _has_loaded_xtc_viewer_document(self: MainWindow) -> bool:
        return _has_loaded_xtc_viewer_document_impl(self)

    def _is_file_viewer_mode_active(self: MainWindow) -> bool:
        return _is_file_viewer_mode_active_impl(self)

    def _apply_file_viewer_mode_preview_button_state(self: MainWindow) -> bool:
        return _apply_file_viewer_mode_preview_button_state_impl(self)

    def _restore_preview_update_button_from_file_viewer_state(self: MainWindow) -> None:
        _restore_preview_update_button_from_file_viewer_state_impl(self)

    def _refresh_preview_update_button_for_current_state(
        self: MainWindow,
        context: Mapping[str, object] | None = None,
    ) -> None:
        _refresh_preview_update_button_for_current_state_impl(self, context)

    def _mark_preview_update_button_pending(self: MainWindow) -> None:
        _mark_preview_update_button_pending_impl(self)

    def _schedule_live_preview_refresh_from_signal(self: MainWindow, *_args: object) -> None:
        _schedule_live_preview_refresh_from_signal_impl(self, *_args)

    def _has_refreshable_preview_target(self: MainWindow) -> bool:
        return _has_refreshable_preview_target_impl(self)

    def _has_active_preview_for_live_refresh(self: MainWindow) -> bool:
        return _has_active_preview_for_live_refresh_impl(self)

    def _queue_live_preview_refresh_timer(self: MainWindow, callback: Callable[[], None], delay_ms: int) -> bool:
        single_shot = getattr(QTimer, 'singleShot', None)
        if callable(single_shot):
            try:
                single_shot(max(0, int(delay_ms)), callback)
                return True
            except Exception:
                pass
        return False

    def _cancel_pending_settings_live_preview_refresh(self: MainWindow) -> None:
        _cancel_pending_settings_live_preview_refresh_impl(self)

    def _schedule_live_preview_refresh(
        self: MainWindow,
        *,
        reset_page: bool = False,
        delay_ms: int = _SETTINGS_PREVIEW_REFRESH_DELAY_MS,
    ) -> bool:
        return _schedule_live_preview_refresh_impl(self, reset_page=reset_page, delay_ms=delay_ms)

    def mark_preview_dirty_for_target_change(self: MainWindow) -> None:
        _mark_preview_dirty_for_target_change_impl(self)

    def mark_preview_dirty(self: MainWindow) -> None:
        _mark_preview_dirty_impl(self)

    def _update_preview_status_label(self: MainWindow, text: object) -> None:
        if hasattr(self, 'preview_status_label'):
            label_text = self._ui_text(str(text or '').strip())
            try:
                self.preview_status_label.setText(label_text)
            except Exception:
                pass
            try:
                if hasattr(self.preview_status_label, 'setToolTip'):
                    self.preview_status_label.setToolTip(label_text)
            except Exception:
                pass

    def _set_results_summary_placeholder_state(self: MainWindow, is_placeholder: object) -> None:
        label = getattr(self, 'results_summary_label', None)
        if label is None:
            return
        placeholder = bool(is_placeholder)
        try:
            label.setProperty('placeholderState', 'empty' if placeholder else 'content')
        except Exception:
            pass
        try:
            label.setAlignment(self._plan_alignment_value(None, None, 'center' if placeholder else 'left_top'))
        except Exception:
            pass
        try:
            style = label.style()
            if hasattr(style, 'unpolish'):
                style.unpolish(label)
            if hasattr(style, 'polish'):
                style.polish(label)
        except Exception:
            pass
        try:
            label.update()
        except Exception:
            pass

    def _minimum_bottom_overlay_margin(
        self: MainWindow,
        enabled_override: bool | None = None,
    ) -> int:
        return _minimum_bottom_overlay_margin_impl(self, enabled_override)

    def _effective_bottom_overlay_margin(
        self: MainWindow,
        margin_b: int | None = None,
        *,
        enabled_override: bool | None = None,
    ) -> int:
        return _effective_bottom_overlay_margin_impl(self, margin_b, enabled_override=enabled_override)

    def _current_bottom_overlay_margin_auto_state(self: MainWindow) -> dict[str, int | bool] | None:
        return _current_bottom_overlay_margin_auto_state_impl(self)

    def _restore_bottom_overlay_margin_auto_state_from_payload(self: MainWindow, payload: Mapping[str, object]) -> None:
        _restore_bottom_overlay_margin_auto_state_from_payload_impl(self, payload)

    def _bottom_overlay_margin_auto_save_payload(self: MainWindow) -> dict[str, object]:
        return _bottom_overlay_margin_auto_save_payload_impl(self)

    def _clear_bottom_overlay_margin_auto_state_if_bottom_margin_was_edited(self: MainWindow) -> None:
        _clear_bottom_overlay_margin_auto_state_if_bottom_margin_was_edited_impl(self)

    def _sync_bottom_overlay_margin_to_ui(
        self: MainWindow,
        enabled_override: bool | None = None,
    ) -> bool:
        return _sync_bottom_overlay_margin_to_ui_impl(self, enabled_override)

    def _current_guide_margins(self: MainWindow) -> tuple[int, int, int, int]:
        values: list[int] = []
        for attr_name in ('margin_t_spin', 'margin_b_spin', 'margin_r_spin', 'margin_l_spin'):
            widget = getattr(self, attr_name, None)
            if widget is None or not hasattr(widget, 'value'):
                values.append(0)
                continue
            try:
                values.append(max(0, int(widget.value())))
            except Exception:
                values.append(0)
        if len(values) != 4:
            return (0, 0, 0, 0)
        values[1] = self._effective_bottom_overlay_margin(values[1])
        return tuple(values)

    def _guide_rect_for_preview_rect(self: MainWindow, rect: QRect, page_width: int, page_height: int) -> QRect:
        margin_t, margin_b, margin_r, margin_l = self._current_guide_margins()
        if not any((margin_t, margin_b, margin_r, margin_l)):
            return rect
        width = max(1, int(page_width or rect.width() or 1))
        height = max(1, int(page_height or rect.height() or 1))
        rect_width = max(1, int(rect.width()))
        rect_height = max(1, int(rect.height()))
        left_inset = int(round(rect_width * margin_l / width))
        right_inset = int(round(rect_width * margin_r / width))
        top_inset = int(round(rect_height * margin_t / height))
        bottom_inset = int(round(rect_height * margin_b / height))
        left_inset = max(0, min(left_inset, max(0, rect_width - 1)))
        right_inset = max(0, min(right_inset, max(0, rect_width - left_inset - 1)))
        top_inset = max(0, min(top_inset, max(0, rect_height - 1)))
        bottom_inset = max(0, min(bottom_inset, max(0, rect_height - top_inset - 1)))
        return rect.adjusted(left_inset, top_inset, -right_inset, -bottom_inset)

    def _decorate_font_view_pixmap(
        self: MainWindow,
        pix: object,
        *,
        page_width: int = 0,
        page_height: int = 0,
    ) -> object:
        return _decorate_font_view_pixmap_impl(
            self,
            pix,
            page_width=page_width,
            page_height=page_height,
        )

    def _preview_pixmap_from_png_bytes(self: MainWindow, raw: bytes) -> object:
        return _preview_pixmap_from_png_bytes_impl(self, raw, qimage_cls=QImage, qpixmap_cls=QPixmap)

    def _apply_preview_pixmap(self: MainWindow, pix: object) -> None:
        return _apply_preview_pixmap_impl(self, pix)

    def _apply_preview_png_bytes(self: MainWindow, raw: bytes) -> None:
        return _apply_preview_png_bytes_impl(self, raw)

    def _apply_preview_page_base64_to_label(self: MainWindow, page_b64: object, *, cache_key: object = None) -> None:
        return _apply_preview_page_base64_to_label_impl(self, page_b64, cache_key=cache_key)

    def _render_current_xtc_page_in_font_view(self: MainWindow, *, refresh_navigation: bool = True) -> bool:
        return _render_current_xtc_page_in_font_view_impl(
            self,
            refresh_navigation=refresh_navigation,
            qpixmap_cls=QPixmap,
            xt_page_blob_to_qimage_func=xt_page_blob_to_qimage,
        )

    def _sync_preview_display_context_for_font_view(self: MainWindow) -> None:
        if not self._runtime_preview_pages():
            return
        try:
            self._set_current_xtc_display_name_with_fallback('プレビュー')
        except Exception:
            pass
        self._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )

    def _ui_widget_text(self: MainWindow, widget: object) -> str:
        return _ui_widget_text_impl(self, widget)

    def _ui_widget_index(self: MainWindow, widget: object) -> int | None:
        return _ui_widget_index_impl(self, widget)

    def _is_render_failure_status_text(self: MainWindow, text: object) -> bool:
        return _is_render_failure_status_text_impl(self, text)

    def _is_preview_render_failure_status_text(self: MainWindow, text: object) -> bool:
        return _is_preview_render_failure_status_text_impl(self, text)

    def _is_device_render_failure_status_text(self: MainWindow, text: object) -> bool:
        return _is_device_render_failure_status_text_impl(self, text)

    def _display_context_name_from_label_text(self: MainWindow, text: object) -> str:
        return _display_context_name_from_label_text_impl(self, text)

    def _render_failure_preserved_display_name(self: MainWindow, text: object) -> str:
        return _render_failure_preserved_display_name_impl(self, text)

    def _device_render_failure_matches_visible_display_context(self: MainWindow, text: object) -> bool:
        return _device_render_failure_matches_visible_display_context_impl(self, text)

    def _preview_render_failure_matches_visible_display_context(self: MainWindow, text: object) -> bool:
        return _preview_render_failure_matches_visible_display_context_impl(self, text)

    def _visible_render_failure_status_text(self: MainWindow) -> str:
        return _visible_render_failure_status_text_impl(self)

    def _show_ui_status_message_unless_render_failure_visible(
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
    ) -> None:
        _show_ui_status_message_unless_render_failure_visible_impl(self, message, timeout)

    def _status_bar_message_text(self: MainWindow) -> str:
        return _status_bar_message_text_impl(self)

    def _show_ui_status_message_unless_render_failure_visible_with_reflection(
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
        *,
        reuse_existing_message: bool = True,
    ) -> bool:
        return _show_ui_status_message_unless_render_failure_visible_with_reflection_impl(
            self,
            message,
            timeout,
            reuse_existing_message=reuse_existing_message,
        )

    def _show_ui_status_message_with_reflection_or_direct_fallback(
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
        *,
        reuse_existing_message: bool = True,
    ) -> bool:
        return _show_ui_status_message_with_reflection_or_direct_fallback_impl(
            self,
            message,
            timeout,
            reuse_existing_message=reuse_existing_message,
        )

    def _show_ui_status_message_direct_with_reflection_best_effort(
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
        *,
        reuse_existing_message: bool = True,
    ) -> bool:
        return _show_ui_status_message_direct_with_reflection_best_effort_impl(
            self,
            message,
            timeout,
            reuse_existing_message=reuse_existing_message,
        )

    def _show_ui_status_message_direct_with_reflection(
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
        *,
        reuse_existing_message: bool = True,
    ) -> bool:
        return _show_ui_status_message_direct_with_reflection_impl(
            self,
            message,
            timeout,
            reuse_existing_message=reuse_existing_message,
        )

    def _current_preview_success_status_message(self: MainWindow) -> str:
        return _current_preview_success_status_message_impl(self)

    def _current_preview_render_status_message(self: MainWindow) -> str:
        return _current_preview_render_status_message_impl(self)

    def _refresh_successful_preview_render_status(self: MainWindow) -> None:
        _refresh_successful_preview_render_status_impl(self)

    def render_current_preview_page(self: MainWindow) -> None:
        return render_current_preview_page_impl(self)

    def _normalized_preview_page_cache_tokens(self: MainWindow, tokens: object, *, expected_len: int) -> list[int] | None:
        return _normalized_preview_page_cache_tokens_impl(self, tokens, expected_len=expected_len)

    def _normalized_right_pane_source_value(self: MainWindow, value: object, *, default: str = 'xtc') -> str:
        return _normalized_right_pane_source_value_impl(self, value, default=default)

    def _normalized_device_view_source_value(self: MainWindow, value: object, *, default: str = 'xtc') -> str:
        return _normalized_device_view_source_value_impl(self, value, default=default)

    def _effective_right_pane_source(self: MainWindow, value: object = None) -> str:
        return _effective_right_pane_source_impl(self, value)

    def _effective_device_view_source(self: MainWindow, value: object = None) -> str:
        return _effective_device_view_source_impl(self, value)

    def _is_preview_display_active(self: MainWindow) -> bool:
        return _is_preview_display_active_impl(self)

    def _apply_preview_page_cache_tokens_context(self: MainWindow, context: Mapping[str, object] | None) -> None:
        _apply_preview_page_cache_tokens_context_impl(self, context)

    def _apply_preview_button_context(self: MainWindow, context: Mapping[str, object] | None) -> None:
        _apply_preview_button_context_impl(self, context)

    def _apply_preview_progress_bar_context(self: MainWindow, context: Mapping[str, object] | None) -> None:
        _apply_preview_progress_bar_context_impl(self, context)

    def _apply_preview_progress_context(self: MainWindow, context: Mapping[str, object] | None) -> None:
        _apply_preview_progress_context_impl(self, context)

    def _apply_preview_pending_progress_context(self: MainWindow, message: object = 'プレビュー更新を準備しています…') -> None:
        _apply_preview_pending_progress_context_impl(self, message, process_events=getattr(QApplication, 'processEvents', None))

    def _apply_preview_finish_context_after_running_flags_clear(self: MainWindow) -> None:
        _apply_preview_finish_context_after_running_flags_clear_impl(self)

    def _normalized_preview_pages_for_runtime(self: MainWindow, value: object) -> list[str]:
        try:
            return preview_controller._normalize_preview_pages(value)
        except Exception:
            return []

    def _runtime_preview_pages(self: MainWindow) -> list[str]:
        pages = self._normalized_preview_pages_for_runtime(self.__dict__.get('preview_pages_b64'))
        if self.__dict__.get('preview_pages_b64') != pages:
            self.preview_pages_b64 = list(pages)
        return list(pages)

    def _runtime_device_preview_pages(self: MainWindow) -> list[str]:
        pages = self._normalized_preview_pages_for_runtime(self.__dict__.get('device_preview_pages_b64'))
        if self.__dict__.get('device_preview_pages_b64') != pages:
            self.device_preview_pages_b64 = list(pages)
        return list(pages)

    def _normalized_xtc_pages_for_runtime(self: MainWindow, value: object) -> list[object]:
        try:
            return _normalize_runtime_xtc_pages(value)
        except Exception:
            return []

    def _runtime_xtc_pages(self: MainWindow) -> list[object]:
        pages = self._normalized_xtc_pages_for_runtime(self.__dict__.get('xtc_pages'))
        if self.__dict__.get('xtc_pages') != pages:
            self.xtc_pages = list(pages)
        return list(pages)

    def _apply_preview_success_context(self: MainWindow, context: Mapping[str, object] | None) -> bool:
        return _apply_preview_success_context_impl(self, context)

    def _preview_failure_display_name(self: MainWindow) -> object:
        return _preview_failure_display_name_impl(self)

    def _preview_failure_loaded_path(self: MainWindow) -> object:
        return _preview_failure_loaded_path_impl(self)

    def _apply_preview_failure_context(self: MainWindow, context: Mapping[str, object] | None) -> bool:
        return _apply_preview_failure_context_impl(self, context)

    def request_preview_refresh(
        self: MainWindow,
        *,
        reset_page: bool = False,
        preview_payload: dict[str, object] | None = None,
    ) -> bool:
        return _request_preview_refresh_impl(
            self,
            reset_page=reset_page,
            preview_payload=preview_payload,
        )

    def refresh_preview(self: MainWindow) -> None:
        self.request_preview_refresh(reset_page=False)

    def _current_viewer_profile(self: MainWindow) -> DeviceProfile:
        return _current_viewer_profile_impl(self)

    def _preview_viewer_profile(self: MainWindow, payload: object = None) -> DeviceProfile:
        return _preview_viewer_profile_impl(self, payload)

    def _loaded_xtc_document_viewer_profile(self: MainWindow) -> DeviceProfile | None:
        return _loaded_xtc_document_viewer_profile_impl(self)

    def _refresh_loaded_xtc_viewer_profile_cache(self: MainWindow) -> DeviceProfile | None:
        return _refresh_loaded_xtc_viewer_profile_cache_impl(self)

    def _sync_loaded_xtc_profile_ui_override(self: MainWindow) -> bool:
        return _sync_loaded_xtc_profile_ui_override_impl(self)

    def _active_device_viewer_profile(self: MainWindow, image: object = None) -> DeviceProfile:
        return _active_device_viewer_profile_impl(self, image)

    def _font_preview_viewer_profile(self: MainWindow) -> DeviceProfile:
        return _font_preview_viewer_profile_impl(self)

    def _normalize_preview_zoom_pct(self: MainWindow, value: object = None) -> int:
        return _normalize_preview_zoom_pct_impl(self, value)

    def _preview_zoom_factor(self: MainWindow) -> float:
        return _preview_zoom_factor_impl(self)

    def _actual_size_uses_preview_zoom_calibration(self: MainWindow) -> bool:
        return _actual_size_uses_preview_zoom_calibration_impl(self)

    def _actual_size_calibration_factor(self: MainWindow) -> float:
        return _actual_size_calibration_factor_impl(self)

    def _sync_legacy_calibration_control_state(self: MainWindow) -> None:
        _sync_legacy_calibration_control_state_impl(self)

    def _sync_preview_zoom_control_state(self: MainWindow) -> None:
        _sync_preview_zoom_control_state_impl(self)

    def _font_preview_target_size(self: MainWindow) -> QSize:
        profile = self._font_preview_viewer_profile()
        actual_size = self.actual_size_check.isChecked()
        px_per_mm = self._preview_px_per_mm() if actual_size else 1.0
        viewport_width = 0
        viewport_height = 0
        zoom = 1.0
        if not actual_size and hasattr(self, 'preview_scroll'):
            vp = self.preview_scroll.viewport().size()
            viewport_width = vp.width()
            viewport_height = vp.height()
            if viewport_width >= 10 and viewport_height >= 10:
                zoom = self._preview_zoom_factor()
        width, height = studio_logic.build_font_preview_target_size(
            actual_size=actual_size,
            screen_w_mm=getattr(profile, 'screen_w_mm', 0),
            screen_h_mm=getattr(profile, 'screen_h_mm', 0),
            px_per_mm=px_per_mm,
            viewport_width=viewport_width,
            viewport_height=viewport_height,
            zoom_factor=zoom,
        )
        return QSize(width, height)

    def _preview_px_per_mm(self: MainWindow) -> float:
        screen = self.screen() or QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen else 96
        return max(1.0, dpi / 25.4) * self._actual_size_calibration_factor()

    def _safe_preview_layout_size(self: MainWindow, size: object, *, fallback: tuple[int, int] = (480, 720)) -> QSize:
        width, height = studio_logic.build_safe_preview_layout_size(size, fallback=fallback)
        return QSize(width, height)

    def _preview_zoom_left_bias(self: MainWindow) -> float:
        return _preview_zoom_left_bias_impl(self)

    def _viewport_width_for_scroll_area(self: MainWindow, scroll_area: object) -> int:
        return _viewport_width_for_scroll_area_impl(self, scroll_area)

    def _font_preview_leading_gap(self: MainWindow, content_width: int) -> int:
        return _font_preview_leading_gap_impl(self, content_width)

    def _viewer_preview_leading_gap(self: MainWindow, content_width: int) -> int:
        return _viewer_preview_leading_gap_impl(self, content_width)

    def _set_horizontal_scrollbar_to_zoom_bias_later(
        self: MainWindow,
        scroll_area: object,
    ) -> None:
        _set_horizontal_scrollbar_to_zoom_bias_later_impl(self, scroll_area)

    def _set_horizontal_scrollbar_to_center_later(
        self: MainWindow,
        scroll_area: object,
    ) -> None:
        _set_horizontal_scrollbar_to_center_later_impl(self, scroll_area)

    def _set_horizontal_scrollbar_to_minimum_later(
        self: MainWindow,
        scroll_area: object,
    ) -> None:
        _set_horizontal_scrollbar_to_minimum_later_impl(self, scroll_area)

    def _sync_font_preview_scroll_placement(
        self: MainWindow,
        *,
        reset_horizontal: bool = False,
    ) -> None:
        _sync_font_preview_scroll_placement_impl(self, reset_horizontal=reset_horizontal)

    def _sync_preview_size(self: MainWindow) -> None:
        _sync_preview_size_impl(self)

    def _sync_viewer_size(self: MainWindow) -> None:
        _sync_viewer_size_impl(self)

    # ── ナビゲーション ─────────────────────────────────────

    def _update_nav_button_texts(self: MainWindow) -> None:
        _update_nav_button_texts_impl(self)

    def on_nav_reverse_toggled(self: MainWindow, checked: object) -> None:
        _on_nav_reverse_toggled_impl(self, checked)

    def on_nav_button_clicked(self: MainWindow, logical_step: int) -> None:
        _on_nav_button_clicked_impl(self, logical_step)

    # ── XTCビューア: 状態 / ナビゲーション ─────────────────

    def _xtc_page_count(self: MainWindow) -> int:
        return _xtc_page_count_impl(self)

    def _normalized_device_preview_page_index(self: MainWindow, index: object = None, *, total: object = None) -> int:
        return _normalized_device_preview_page_index_impl(self, index, total=total)

    def _normalized_xtc_page_index(self: MainWindow, index: object = None, *, total: object = None) -> int:
        return _normalized_xtc_page_index_impl(self, index, total=total)

    def _xtc_page_state_payload(self: MainWindow, index: object = None) -> dict[str, object]:
        return _xtc_page_state_payload_impl(self, index)

    def _xtc_navigation_payload(self: MainWindow) -> dict[str, object]:
        return _xtc_navigation_payload_impl(self)

    def _apply_xtc_navigation_ui(self: MainWindow, payload: Mapping[str, object]) -> None:
        _apply_xtc_navigation_ui_impl(self, payload)

    def update_navigation_ui(self: MainWindow) -> None:
        update_navigation_ui_impl(self)

    def on_page_input_changed(self: MainWindow, value: int) -> None:
        _on_page_input_changed_impl(self, value)

    def change_page(self: MainWindow, delta: int) -> None:
        _change_page_impl(self, delta)

    # ── プロファイル・設定変更ハンドラ ─────────────────────

    def _refresh_preview_after_profile_change(self: MainWindow, *, update_status: bool = False, persist: bool = True) -> None:
        if update_status:
            self._update_top_status()
        if persist:
            self.save_ui_state()
        preview_pages = self._runtime_preview_pages()
        device_preview_pages = self._runtime_device_preview_pages()
        should_refresh_now = bool(preview_pages or device_preview_pages or self._effective_device_view_source() == 'preview')
        if should_refresh_now:
            refreshed = self.request_preview_refresh(reset_page=True)
            if refreshed:
                return
        self.mark_preview_dirty()

    def on_profile_changed(self: MainWindow) -> None:
        self._apply_profile_dimensions_to_ui(
            self.profile_combo.currentData() if hasattr(self, 'profile_combo') else self._current_profile_key_or_default(),
        )
        self._sync_loaded_xtc_profile_ui_override()
        self._apply_profile_runtime_state()
        self._refresh_font_preview_display_if_needed()
        self._refresh_preview_after_profile_change(update_status=True)

    def _on_custom_size_changed(self: MainWindow) -> None:
        if self._selected_profile_key() != 'custom':
            return
        self._sync_loaded_xtc_profile_ui_override()
        self._apply_profile_runtime_state()
        self._refresh_font_preview_display_if_needed()
        self._refresh_preview_after_profile_change()

    def _refresh_font_preview_display_if_needed(self: MainWindow, refresh_navigation: bool = True) -> None:
        return _refresh_font_preview_display_if_needed_impl(
            self,
            refresh_navigation=refresh_navigation,
        )

    def on_actual_size_toggled(self: MainWindow, checked: bool) -> None:
        self._apply_viewer_display_runtime_state()
        self._sync_preview_zoom_control_state()
        self._sync_preview_size()
        self._refresh_font_preview_display_if_needed()
        self._finalize_setting_change()

    def on_calibration_changed(self: MainWindow, value: int) -> None:
        self._apply_viewer_display_runtime_state()
        self._sync_preview_size()
        self._refresh_font_preview_display_if_needed()
        self._finalize_setting_change()

    def on_preview_zoom_changed(self: MainWindow, value: int) -> None:
        # 表示倍率は右ペイン上の見え方だけを変える UI で、本文組版・XTC/XTCH
        # 生成内容には影響しない。ここで preview_dirty を立てると、スピン操作の
        # 連続 signal 後に「プレビュー更新」待ちが残り、暴走して見えるため、
        # 保存だけ行い、再生成予約や dirty 表示は作らない。
        self._sync_preview_zoom_control_state()
        self._sync_preview_size()
        if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'font':
            self._refresh_font_preview_display_if_needed(refresh_navigation=False)
        self._finalize_setting_change(refresh_preview=False)

    def on_night_toggled(self: MainWindow, checked: bool) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def on_ruby_hide_toggled(self: MainWindow, checked: bool) -> None:
        # ルビ消しは組版内容を再生成するが、閲覧中ページは維持する。
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def on_guides_toggled(self: MainWindow, checked: bool) -> None:
        self._apply_viewer_display_runtime_state()
        # フォントビュー側もガイド表示に追従（見た目を実機ビューへ寄せる）
        if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'font':
            try:
                if self._runtime_preview_pages():
                    self.render_current_preview_page()
            except Exception:
                pass
        self._finalize_setting_change(refresh_preview=False)

    def on_page_number_setting_changed(self: MainWindow, *args: object) -> None:
        enabled_override = args[0] if args and isinstance(args[0], bool) else None
        self._sync_bottom_overlay_margin_to_ui(enabled_override=enabled_override)
        self._apply_viewer_display_runtime_state()
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def on_progress_bar_setting_changed(self: MainWindow, *args: object) -> None:
        self._sync_bottom_overlay_margin_to_ui()
        self._apply_viewer_display_runtime_state()
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def _request_preview_refresh_after_margin_change(self: MainWindow) -> bool:
        """Compatibility wrapper for margin-driven live preview refreshes."""
        return self._schedule_live_preview_refresh(reset_page=False)

    def on_margin_changed(self: MainWindow, value: int) -> None:
        self._clear_bottom_overlay_margin_auto_state_if_bottom_margin_was_edited()
        self._apply_viewer_display_runtime_state()
        refreshed = self._request_preview_refresh_after_margin_change()
        if not refreshed:
            self._refresh_font_preview_display_if_needed()
        self._finalize_setting_change(refresh_preview=False)

    def on_threshold_changed(self: MainWindow, value: int) -> None:
        self._finalize_setting_change()

    def on_dither_toggled(self: MainWindow, checked: bool) -> None:
        self._apply_render_option_ui_state(checked)
        # ディザリングはプレビュー画像に影響するため、他の表示系設定と同じ
        # debounced live refresh 経路に寄せる。プレビュー生成中なら 50ms
        # ポーリングせず、完了後に 1 回だけ再更新する。
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def _on_kinsoku_mode_changed(self: MainWindow) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def current_kinsoku_mode(self: MainWindow) -> str:
        if not hasattr(self, 'kinsoku_mode_combo'):
            return 'standard'
        value = str(self.kinsoku_mode_combo.currentData() or 'standard').strip().lower()
        return value if value in KINSOKU_MODE_LABELS else 'standard'

    def _on_tatechuyoko_digit_mode_changed(self: MainWindow) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def current_tatechuyoko_digit_mode(self: MainWindow) -> str:
        combo = self.__dict__.get('tatechuyoko_digit_mode_combo')
        if combo is None:
            return '2'
        current_data = getattr(combo, 'currentData', None)
        raw_value = current_data() if callable(current_data) else None
        return studio_logic.normalize_tatechuyoko_digit_mode(raw_value, '2')

    def _on_latin_orientation_mode_changed(self: MainWindow) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def current_latin_orientation_mode(self: MainWindow) -> str:
        combo = self.__dict__.get('latin_orientation_combo')
        if combo is None:
            return 'vertical'
        current_data = getattr(combo, 'currentData', None)
        raw_value = current_data() if callable(current_data) else None
        value = str(raw_value or 'vertical').strip().lower()
        return value if value in {'vertical', 'horizontal'} else 'vertical'

    def _on_opening_bracket_indent_mode_changed(self: MainWindow) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def current_opening_bracket_indent_mode(self: MainWindow) -> str:
        combo = self.__dict__.get('opening_bracket_indent_combo')
        if combo is None:
            return 'none'
        current_data = getattr(combo, 'currentData', None)
        raw_value = current_data() if callable(current_data) else None
        value = str(raw_value or 'none').strip().lower()
        return value if value in OPENING_BRACKET_INDENT_MODE_LABELS else 'none'

    def _on_glyph_position_mode_changed(self: MainWindow) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def _current_glyph_position_mode(self: MainWindow, combo_name: str, allowed_values: object = None) -> str:
        combo = self.__dict__.get(combo_name)
        if combo is None:
            return 'standard'
        current_data = getattr(combo, 'currentData', None)
        raw_value = current_data() if callable(current_data) else None
        value = str(raw_value or 'standard').strip().lower()
        allowed = allowed_values if allowed_values is not None else GLYPH_POSITION_MODE_LABELS
        return value if value in allowed else 'standard'

    def current_punctuation_position_mode(self: MainWindow) -> str:
        return self._current_glyph_position_mode('punctuation_position_combo')

    def current_ichi_position_mode(self: MainWindow) -> str:
        return self._current_glyph_position_mode('ichi_position_combo')

    def current_halfwidth_digit_position_mode(self: MainWindow) -> str:
        return self._current_glyph_position_mode('halfwidth_digit_position_combo')

    def current_halfwidth_alpha_position_mode(self: MainWindow) -> str:
        return self._current_glyph_position_mode('halfwidth_alpha_position_combo')

    def current_middle_dot_position_mode(self: MainWindow) -> str:
        return self._current_glyph_position_mode('middle_dot_position_combo')

    def current_tatechuyoko_symbol_position_mode(self: MainWindow) -> str:
        return self._current_glyph_position_mode('tatechuyoko_symbol_position_combo')

    def current_lower_closing_bracket_position_mode(self: MainWindow) -> str:
        return self._current_glyph_position_mode(
            'lower_closing_bracket_position_combo',
            CLOSING_BRACKET_POSITION_MODE_LABELS,
        )

    def _on_wave_dash_mode_changed(self: MainWindow) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def current_wave_dash_drawing_mode(self: MainWindow) -> str:
        combo = self.__dict__.get('wave_dash_drawing_combo')
        if combo is None:
            return 'rotate'
        current_data = getattr(combo, 'currentData', None)
        raw_value = current_data() if callable(current_data) else None
        return studio_logic.normalize_wave_dash_drawing_mode(raw_value, 'rotate')

    def current_wave_dash_position_mode(self: MainWindow) -> str:
        combo = self.__dict__.get('wave_dash_position_combo')
        if combo is None:
            return 'standard'
        current_data = getattr(combo, 'currentData', None)
        raw_value = current_data() if callable(current_data) else None
        return studio_logic.normalize_wave_dash_position_mode(raw_value, 'standard')

    def current_output_format(self: MainWindow) -> str:
        combo = self.__dict__.get('output_format_combo')
        if combo is None:
            return 'xtch'
        current_data = getattr(combo, 'currentData', None)
        raw_value = current_data() if callable(current_data) else None
        value = str(raw_value or '').strip().lower()
        if value in OUTPUT_FORMAT_LABELS:
            return value
        current_text = getattr(combo, 'currentText', None)
        text_value = str(current_text() if callable(current_text) else '').strip().lower()
        for key, label in OUTPUT_FORMAT_LABELS.items():
            if text_value in {str(key).strip().lower(), str(label).strip().lower()}:
                return key
        return 'xtch'

    def current_output_conflict_mode(self: MainWindow) -> str:
        if not hasattr(self, 'output_conflict_combo'):
            return 'rename'
        value = str(self.output_conflict_combo.currentData() or 'rename').strip().lower()
        return value if value in OUTPUT_CONFLICT_LABELS else 'rename'

    def on_font_changed(self: MainWindow, _value: object) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def manual_refresh_preview(self: MainWindow) -> None:
        self._flush_pending_ui_changes()
        refresh_context = preview_controller.build_manual_preview_refresh_context(
            self._current_preview_payload(),
            current_output_format=self.current_output_format(),
            default_preview_page_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
            reset_page=False,
        )
        preview_payload_obj = refresh_context.get('preview_payload', {})
        preview_payload = dict(preview_payload_obj) if isinstance(preview_payload_obj, Mapping) else {}
        self.request_preview_refresh(
            reset_page=self._payload_bool_value(refresh_context, 'reset_page', False),
            preview_payload=preview_payload,
        )
        if self._payload_bool_value(refresh_context, 'should_update_top_status', False):
            self._update_top_status()
        if self._payload_bool_value(refresh_context, 'should_save_ui_state', False):
            self.save_ui_state()

    # ── プリセット ─────────────────────────────────────────

    def on_preset_selection_changed(self: MainWindow) -> None:
        self._refresh_preset_ui()
        key = self.selected_preset_key()
        p = self.preset_definitions.get(key) if key else None
        if p:
            self._show_ui_status_message_unless_render_failure_visible(
                settings_controller.build_preset_selection_status_message(p.get('button_text')),
                2500,
            )
        self.save_ui_state()

    def selected_preset_key(self: MainWindow) -> str | None:
        return selected_preset_key_from_combo(getattr(self, 'preset_combo', None))

    def apply_selected_preset(self: MainWindow) -> None:
        self._flush_pending_ui_changes()
        key = self.selected_preset_key()
        if key:
            self.apply_preset(key)

    def save_selected_preset(self: MainWindow) -> None:
        self._flush_pending_ui_changes()
        key = self.selected_preset_key()
        if key:
            self.save_preset(key)

    def rename_selected_preset(self: MainWindow) -> None:
        self._flush_pending_ui_changes()
        key = self.selected_preset_key()
        if not key:
            self._show_warning_dialog_with_status_fallback(
                'プリセット名称変更',
                '名称を変更するプリセットが選択されていません。',
            )
            return
        self.rename_preset_display_name(key)

    def _flush_pending_ui_changes(self: MainWindow) -> None:
        _flush_pending_ui_changes_impl(
            getattr(QApplication, 'focusWidget', None),
            getattr(QApplication, 'processEvents', None),
        )

    def _preset_combo_entries(self: MainWindow) -> tuple[tuple[str, object], ...]:
        return preset_combo_entries(getattr(self, 'preset_combo', None))

    def _live_preset_widget_payload(self: MainWindow) -> PresetDefinition:
        return _live_preset_widget_payload_impl(self)

    def _preset_settings_prefix(self: MainWindow, key: str) -> str:
        return preset_settings_prefix(key)

    def _normalize_preset_payload(
        self: MainWindow,
        payload: object,
        *,
        fallback: PresetDefinition | None = None,
        fallback_font: str = '',
        fallback_night_mode: bool = False,
        fallback_dither: bool = False,
        fallback_ruby_hide: bool = False,
        fallback_kinsoku_mode: str = 'standard',
        fallback_tatechuyoko_digit_mode: str = '2',
        fallback_punctuation_position_mode: str = 'standard',
        fallback_ichi_position_mode: str = 'standard',
        fallback_halfwidth_digit_position_mode: str = 'standard',
        fallback_halfwidth_alpha_position_mode: str = 'standard',
        fallback_latin_orientation_mode: str = 'vertical',
        fallback_opening_bracket_indent_mode: str = 'none',
        fallback_middle_dot_position_mode: str = 'standard',
        fallback_tatechuyoko_symbol_position_mode: str = 'standard',
        fallback_lower_closing_bracket_position_mode: str = 'standard',
        fallback_wave_dash_drawing_mode: str = 'rotate',
        fallback_wave_dash_position_mode: str = 'standard',
        fallback_output_format: str = 'xtch',
    ) -> PresetDefinition:
        return _normalize_preset_payload_impl(
            self,
            payload,
            fallback=fallback,
            fallback_font=fallback_font,
            fallback_night_mode=fallback_night_mode,
            fallback_dither=fallback_dither,
            fallback_ruby_hide=fallback_ruby_hide,
            fallback_kinsoku_mode=fallback_kinsoku_mode,
            fallback_tatechuyoko_digit_mode=fallback_tatechuyoko_digit_mode,
            fallback_punctuation_position_mode=fallback_punctuation_position_mode,
            fallback_ichi_position_mode=fallback_ichi_position_mode,
            fallback_halfwidth_digit_position_mode=fallback_halfwidth_digit_position_mode,
            fallback_halfwidth_alpha_position_mode=fallback_halfwidth_alpha_position_mode,
            fallback_latin_orientation_mode=fallback_latin_orientation_mode,
            fallback_opening_bracket_indent_mode=fallback_opening_bracket_indent_mode,
            fallback_middle_dot_position_mode=fallback_middle_dot_position_mode,
            fallback_tatechuyoko_symbol_position_mode=fallback_tatechuyoko_symbol_position_mode,
            fallback_lower_closing_bracket_position_mode=fallback_lower_closing_bracket_position_mode,
            fallback_wave_dash_drawing_mode=fallback_wave_dash_drawing_mode,
            fallback_wave_dash_position_mode=fallback_wave_dash_position_mode,
            fallback_output_format=fallback_output_format,
        )

    def _preset_display_name_settings_key(self: MainWindow, key: str) -> str:
        return preset_display_name_settings_key(key)

    def _default_preset_display_name(self: MainWindow, key: str) -> str:
        return _default_preset_display_name_impl(self, key)

    def _normalize_preset_display_name(self: MainWindow, value: object, *, fallback: str) -> str:
        return normalize_preset_display_name(value, fallback=fallback)

    def _load_preset_definitions(self: MainWindow) -> PresetDefinitions:
        return _load_preset_definitions_impl(self)


    def _preset_display_name(self: MainWindow, p: PresetDefinition) -> str:
        return _preset_display_name_impl(self, p)

    def _preset_summary_plain_text(
        self: MainWindow,
        p: PresetDefinition,
        *,
        summary_tag: str = '',
        include_name_line: bool = True,
    ) -> str:
        return _preset_summary_plain_text_impl(self, p, summary_tag=summary_tag, include_name_line=include_name_line)

    def _preset_summary_text(
        self: MainWindow,
        p: PresetDefinition,
        *,
        summary_tag: str = '',
        include_name_line: bool = True,
    ) -> str:
        return _preset_summary_text_impl(self, p, summary_tag=summary_tag, include_name_line=include_name_line)

    def _preset_side_summary_text(self: MainWindow, summary: object) -> str:
        return preset_side_summary_text(summary)

    def _current_settings_summary_payload(self: MainWindow, key: str | None = None) -> PresetDefinition:
        return _current_settings_summary_payload_impl(self, key)

    def _preset_summary_label_measurement_width(self: MainWindow, label: object) -> int:
        return _preset_summary_label_measurement_width_impl(self, label)

    def _queue_preset_summary_label_layout_retry(self: MainWindow) -> None:
        _queue_preset_summary_label_layout_retry_impl(self, timer_class=QTimer)

    def _update_preset_summary_label_layout(self: MainWindow, *, queue_retry: bool = True) -> None:
        _update_preset_summary_label_layout_impl(
            self,
            queue_retry=queue_retry,
            qt_namespace=Qt,
            rect_class=QRect,
        )

    def _sync_summary_payload(self: MainWindow, payload: PresetDefinition | None, *, summary_tag: str = '') -> None:
        _sync_summary_payload_impl(self, payload, summary_tag=summary_tag)

    def _sync_current_settings_summary(self: MainWindow, key: str | None = None) -> None:
        _sync_current_settings_summary_impl(self, key)

    def _sync_selected_preset_summary(self: MainWindow, key: str | None = None) -> None:
        _sync_selected_preset_summary_impl(self, key)

    def _refresh_preset_ui(self: MainWindow) -> None:
        _refresh_preset_ui_impl(self, bulk_block_signals=_bulk_block_signals)

    def _selected_profile_key(self: MainWindow) -> str:
        current_key = self._current_profile_key_or_default()
        raw = self.profile_combo.currentData() if hasattr(self, 'profile_combo') else current_key
        return self._normalize_choice_value(raw or current_key or 'x4', 'x4', DEVICE_PROFILES)

    def _resolved_profile_and_dimensions(
        self: MainWindow,
        profile_key: object = None,
        width: object = None,
        height: object = None,
    ) -> tuple[str, DeviceProfile, int, int]:
        key = self._normalize_choice_value(
            self._selected_profile_key() if profile_key is None else profile_key,
            'x4',
            DEVICE_PROFILES,
        )
        profile = DEVICE_PROFILES.get(key, DEVICE_PROFILES['x4'])
        if key != 'custom':
            return key, profile, profile.width_px, profile.height_px

        if width is None and hasattr(self, 'width_spin'):
            width = self.width_spin.value()
        if height is None and hasattr(self, 'height_spin'):
            height = self.height_spin.value()

        resolved_width = max(240, worker_logic._int_config_value({'width': width}, 'width', profile.width_px))
        resolved_height = max(240, worker_logic._int_config_value({'height': height}, 'height', profile.height_px))
        return key, profile, resolved_width, resolved_height

    def _effective_output_dimensions(self: MainWindow) -> tuple[int, int]:
        _key, _profile, width, height = self._resolved_profile_and_dimensions()
        return width, height

    def current_preset_payload(self: MainWindow) -> PresetDefinition:
        return settings_controller.build_current_preset_payload(
            render_settings_base=self._current_render_settings_base(),
            profile=self._selected_profile_key(),
            fallback_font=self.current_font_value() or self._default_font_name(),
            fallback_night_mode=self.night_check.isChecked(),
            fallback_dither=self.dither_check.isChecked(),
            fallback_kinsoku_mode=self.current_kinsoku_mode(),
            fallback_output_format=self.current_output_format(),
            normalize_preset_payload=self._normalize_preset_payload,
            fallback_wave_dash_drawing_mode=self.current_wave_dash_drawing_mode(),
            fallback_wave_dash_position_mode=self.current_wave_dash_position_mode(),
        )

    def _settings_no_error_value(self: MainWindow) -> object | None:
        status_enum = getattr(QSettings, 'Status', None)
        if status_enum is not None:
            no_error = getattr(status_enum, 'NoError', None)
            if no_error is not None:
                return no_error
        return getattr(QSettings, 'NoError', None)

    def _settings_status_text(self: MainWindow, settings_store: object | None = None) -> str:
        store = settings_store if settings_store is not None else self.settings_store
        status_getter = getattr(store, 'status', None)
        if not callable(status_getter):
            return 'NoError'
        try:
            status = status_getter()
        except Exception:
            return 'NoError'
        name = getattr(status, 'name', None)
        if name:
            return str(name)
        return str(status)

    def _settings_status_is_ok(self: MainWindow, settings_store: object | None = None) -> bool:
        store = settings_store if settings_store is not None else self.settings_store
        status_getter = getattr(store, 'status', None)
        if not callable(status_getter):
            return True
        try:
            status = status_getter()
        except Exception:
            return True
        no_error = self._settings_no_error_value()
        if no_error is not None:
            try:
                return status == no_error
            except Exception:
                pass
        try:
            return int(status) == 0
        except Exception:
            pass
        text = self._settings_status_text(store)
        if 'NoError' in text:
            return True
        if 'AccessError' in text or 'FormatError' in text or text.endswith('Error'):
            return False
        return True

    def _settings_store_for_disk_readback(self: MainWindow) -> object:
        file_name_getter = getattr(self.settings_store, 'fileName', None)
        if callable(file_name_getter):
            try:
                file_name = str(file_name_getter() or '').strip()
            except Exception:
                file_name = ''
            if file_name:
                try:
                    readback_store = QSettings(file_name, QSettings.IniFormat)
                    readback_sync = getattr(readback_store, 'sync', None)
                    if callable(readback_sync):
                        readback_sync()
                    # Unit-test stubs may not implement QSettings.contains().
                    # Real Qt QSettings does, so only use a fresh disk readback
                    # store when it supports the same key-existence check.
                    if callable(getattr(readback_store, 'contains', None)):
                        return readback_store
                except Exception:
                    APP_LOGGER.exception('プリセット保存確認用の設定ファイル再読込に失敗しました')
        return self.settings_store

    def _settings_store_contains_key(self: MainWindow, settings_store: object, key: str) -> bool:
        return _settings_contains_key_in_store(settings_store, key)

    def _settings_store_raw_value(self: MainWindow, settings_store: object, key: str, default: object = None) -> object:
        return _settings_raw_value_from_store(settings_store, key, default)

    def _verify_preset_save_readback(
        self: MainWindow,
        key: str,
        payload: Mapping[str, object],
    ) -> tuple[bool, str]:
        return _verify_preset_save_readback_impl(self, key, payload)

    def _show_preset_save_failed(self: MainWindow, reason: str) -> None:
        _show_preset_save_failed_impl(self, reason)

    def _request_preview_refresh_after_preset_apply(self: MainWindow) -> bool:
        return _request_preview_refresh_after_preset_apply_impl(self)

    def _preset_save_confirmation_text(self: MainWindow, preset: Mapping[str, object], preset_name: str) -> str:
        return _preset_save_confirmation_text_impl(self, preset, preset_name)

    def _preset_rename_dialog_result(
        self: MainWindow,
        *,
        current_name: str,
        default_name: str,
    ) -> tuple[str, str | None]:
        return _preset_rename_dialog_result_impl(
            self,
            current_name=current_name,
            default_name=default_name,
            dialog_cls=QDialog,
            vbox_layout_cls=QVBoxLayout,
            label_cls=QLabel,
            line_edit_cls=QLineEdit,
            hbox_layout_cls=QHBoxLayout,
            push_button_cls=QPushButton,
        )

    def rename_preset_display_name(self: MainWindow, key: str) -> None:
        rename_preset_display_name_impl(self, key)

    def save_preset(self: MainWindow, key: str) -> None:
        save_preset_impl(self, key)

    def apply_preset(self: MainWindow, key: str) -> None:
        apply_preset_impl(self, key)

    # ── ファイル選択 ───────────────────────────────────────

    def _apply_dropped_target_path(self: MainWindow, path: object) -> None:
        return _apply_dropped_target_path_impl(self, path)

    def _default_output_folder_start_dir(self: MainWindow) -> str:
        return _default_output_folder_start_dir_impl(self)

    def _selected_output_dir_label_text(self: MainWindow) -> str:
        return _selected_output_dir_label_text_impl(self)

    def _announce_selected_output_dir(self: MainWindow, timeout: int = 5000) -> None:
        return _announce_selected_output_dir_impl(self, timeout)

    def reset_output_folder(self: MainWindow) -> None:
        return reset_output_folder_impl(self)

    def select_output_folder(self: MainWindow) -> None:
        return select_output_folder_impl(self)

    def select_target_path(self: MainWindow, as_file: bool) -> None:
        return select_target_path_impl(self, as_file)


    def export_current_preview_share_png(self: MainWindow) -> bool:
        return export_current_preview_share_png_impl(self)

    def select_font_file(self: MainWindow) -> None:
        return select_font_file_impl(self)

    def current_font_value(self: MainWindow) -> str:
        return current_font_value_impl(self)

    def _available_font_entries(self: MainWindow) -> list[dict[str, str]]:
        return _available_font_entries_impl(self)

    def _populate_font_combo(self: MainWindow) -> None:
        return _populate_font_combo_impl(self)

    def _missing_font_combo_label(self: MainWindow, font_value: str) -> str:
        return _missing_font_combo_label_impl(self, font_value)

    def _combo_find_data_index(self: MainWindow, combo: object, value: object) -> int:
        return _combo_find_data_index_for_widget(combo, value)

    def _ensure_font_combo_value(self: MainWindow, font_value: str) -> None:
        return _ensure_font_combo_value_impl(self, font_value)

    def _set_current_font_value(self: MainWindow, font_value: str) -> None:
        return _set_current_font_value_impl(self, font_value)

    def _default_font_name(self: MainWindow) -> str:
        return _default_font_name_impl(self)

    def _apply_default_font_selection(self: MainWindow) -> None:
        return _apply_default_font_selection_impl(self)

    def _update_top_status(self: MainWindow) -> None:
        if self.__dict__.get('worker') is not None:
            return
        _profile_key, profile, _width, _height = self._resolved_profile_and_dimensions(self._current_profile_key_or_default())
        message = studio_logic.build_top_status_message(
            worker_logic.normalize_target_path_text(self._safe_line_edit_text('target_edit')),
            profile.name,
            worker_logic._int_config_value({'font_size': self._safe_widget_value('font_size_spin', 26)}, 'font_size', 26),
            worker_logic._int_config_value({'line_spacing': self._safe_widget_value('line_spacing_spin', 44)}, 'line_spacing', 44),
            self.current_ui_language_value(),
        )
        selected_output_dir = worker_logic.normalize_target_path_text(self.__dict__.get('selected_output_dir', ''))
        if selected_output_dir:
            folder_label = 'Save folder' if self.current_ui_language_value() == 'en' else '保存先'
            message = f'{message} / {folder_label}: {selected_output_dir}'
        self._show_ui_status_message_unless_render_failure_visible(message, None)

    def _safe_line_edit_text(self: MainWindow, name: str, default: str = '') -> str:
        widget = getattr(self, name, None)
        text_getter = getattr(widget, 'text', None)
        if callable(text_getter):
            try:
                return _coerce_ui_message_text(text_getter(), default)
            except Exception:
                pass
        return default

    def _current_render_settings_base(self: MainWindow) -> WorkerConversionSettings:
        return _current_render_settings_base_impl(self)

    # ── 変換 ──────────────────────────────────────────────

    def current_settings_dict(self: MainWindow) -> WorkerConversionSettings:
        return current_settings_dict_impl(self)

    def _folder_batch_worker_settings(
        self: MainWindow,
        source_path: object = None,
        output_path: object = None,
        item: object = None,
    ) -> WorkerConversionSettings:
        return _folder_batch_worker_settings_impl(self, source_path, output_path, item)

    def _window_state_save_payload(self: MainWindow) -> dict[str, object]:
        return _window_state_save_payload_impl(self)

    def _settings_save_payload(self: MainWindow) -> dict[str, object]:
        return _settings_save_payload_impl(self)

    def _supported_targets_for_path(self: MainWindow, target_raw: str) -> list[Path]:
        return _supported_targets_for_path(target_raw, ConversionWorker._resolve_supported_targets)

    def _default_output_name_for_target(self: MainWindow, path: Path) -> str:
        return _default_output_name_for_target(
            path,
            self.current_output_format(),
            get_output_path_for_target=core.get_output_path_for_target,
            sanitize_output_stem=ConversionWorker._sanitize_output_stem,
        )

    def _prepare_conversion_settings(self: MainWindow) -> WorkerConversionSettings | None:
        return _prepare_conversion_settings_impl(
            self,
            qinputdialog_cls=QInputDialog,
            path_cls=Path,
            sanitize_output_stem_func=ConversionWorker._sanitize_output_stem,
        )

    def _preview_page_cache_token(self: MainWindow, page_b64: object) -> int:
        return preview_controller._preview_page_cache_token(page_b64)

    def _rebuild_preview_page_cache_tokens(self: MainWindow) -> None:
        _rebuild_preview_page_cache_tokens_impl(self)

    def _clear_font_preview_page_pixmap_cache(self: MainWindow) -> None:
        _clear_font_preview_page_pixmap_cache_impl(self)

    def _font_preview_page_pixmap_cache_key(self: MainWindow, index: object = None) -> tuple[int, int] | None:
        return _font_preview_page_pixmap_cache_key_impl(self, index)

    def _cached_font_preview_page_pixmap(self: MainWindow, key: object) -> object | None:
        return _cached_font_preview_page_pixmap_impl(self, key)

    def _store_font_preview_page_pixmap(self: MainWindow, key: object, pixmap: object) -> None:
        _store_font_preview_page_pixmap_impl(self, key, pixmap, cache_limit=_FONT_PREVIEW_PAGE_PIXMAP_CACHE_LIMIT)

    def _clear_xtc_page_qimage_cache(self: MainWindow) -> None:
        _clear_xtc_page_qimage_cache_impl(self)

    def _clear_device_preview_page_qimage_cache(self: MainWindow) -> None:
        _clear_device_preview_page_qimage_cache_impl(self)

    def _device_preview_page_qimage_cache_key(self: MainWindow, index: object = None) -> tuple[int, int] | None:
        return _device_preview_page_qimage_cache_key_impl(self, index)

    def _cached_device_preview_page_qimage(self: MainWindow, key: object) -> object | None:
        return _cached_device_preview_page_qimage_impl(self, key)

    def _store_device_preview_page_qimage(self: MainWindow, key: object, image: object) -> None:
        _store_device_preview_page_qimage_impl(self, key, image, cache_limit=_DEVICE_PREVIEW_PAGE_QIMAGE_CACHE_LIMIT)

    def _xtc_page_qimage_cache_key(self: MainWindow, index: object = None) -> tuple[int, int, int] | None:
        return _xtc_page_qimage_cache_key_impl(self, index)

    def _cached_xtc_page_qimage(self: MainWindow, key: object) -> object | None:
        return _cached_xtc_page_qimage_impl(self, key)

    def _store_xtc_page_qimage(self: MainWindow, key: object, image: object) -> None:
        _store_xtc_page_qimage_impl(self, key, image, cache_limit=_XTC_PAGE_QIMAGE_CACHE_LIMIT)

    def _clear_loaded_xtc_state(self: MainWindow) -> None:
        clear_loaded_xtc_state_impl(self)

    def _leave_file_viewer_mode_for_target_change(self: MainWindow) -> None:
        leave_file_viewer_mode_for_target_change_impl(self)

    def _set_current_xtc_display_name(self: MainWindow, display_name: object = None) -> None:
        _set_current_xtc_display_name_impl(self, display_name)

    def _set_current_xtc_display_name_with_fallback(self: MainWindow, display_name: object = None) -> bool:
        return _set_current_xtc_display_name_with_fallback_impl(self, display_name)

    def _sync_loaded_xtc_display_context_for_device_view(self: MainWindow) -> None:
        _sync_loaded_xtc_display_context_for_device_view_impl(self)

    def _sync_preview_display_context_for_device_view(self: MainWindow) -> None:
        _sync_preview_display_context_for_device_view_impl(self)

    def _sync_blank_device_display_context(self: MainWindow) -> None:
        _sync_blank_device_display_context_impl(self)

    def _restore_shared_status_for_visible_display_context(self: MainWindow) -> None:
        _restore_shared_status_for_visible_display_context_impl(self)

    def _sync_active_display_context_for_visible_page(self: MainWindow) -> None:
        _sync_active_display_context_for_visible_page_impl(self)

    def _set_worker_controls_running(self: MainWindow, running: bool) -> None:
        _set_worker_controls_running_impl(self, running)

    def _prepare_conversion_ui_for_run(self: MainWindow, settings: WorkerConversionSettings) -> None:
        _prepare_conversion_ui_for_run_impl(self, settings)

    def _apply_direct_conversion_terminal_fallback(
        self: MainWindow,
        message: object,
        *,
        badge_text: object,
        status_message: object = None,
        status_timeout: int | None = None,
    ) -> bool:
        return _apply_direct_conversion_terminal_fallback_impl(
            self,
            message,
            badge_text=badge_text,
            status_message=status_message,
            status_timeout=status_timeout,
        )

    def _apply_conversion_terminal_state(
        self: MainWindow,
        message: str,
        *,
        badge_text: str,
        status_message: str | None = None,
        status_timeout: int | None = None,
    ) -> None:
        _apply_conversion_terminal_state_impl(
            self,
            message,
            badge_text=badge_text,
            status_message=status_message,
            status_timeout=status_timeout,
        )

    def _load_xtc_from_path_with_result(self: MainWindow, path: object) -> bool:
        return _load_xtc_from_path_with_result_impl(self, path)

    def _show_conversion_results(
        self: MainWindow,
        converted_files: list[object],
        summary_lines: list[str] | None = None,
    ) -> None:
        return _show_conversion_results_impl(self, converted_files, summary_lines)

    def _build_conversion_failure_summary_text(
        self: MainWindow,
        prefix: object,
        message: object,
    ) -> str:
        return _build_conversion_failure_summary_text_impl(self, prefix, message)

    def _apply_conversion_failure_ui(
        self: MainWindow,
        summary_text: object,
        *,
        status_message: object,
        log_error_context: str,
        terminal_state_error_context: str,
        clear_results_error_context: str,
        clear_preview_error_context: str,
        progress_error_context: str,
        tab_error_context: str,
    ) -> None:
        _apply_conversion_failure_ui_impl(
            self,
            summary_text,
            status_message=status_message,
            log_error_context=log_error_context,
            terminal_state_error_context=terminal_state_error_context,
            clear_results_error_context=clear_results_error_context,
            clear_preview_error_context=clear_preview_error_context,
            progress_error_context=progress_error_context,
            tab_error_context=tab_error_context,
        )

    def _handle_conversion_startup_failure(self: MainWindow, message: object) -> None:
        _handle_conversion_startup_failure_impl(self, message)

    def _next_conversion_run_token(self: MainWindow) -> int:
        return _next_conversion_run_token_impl(self)

    def _clear_active_conversion_run_token(self: MainWindow) -> None:
        return _clear_active_conversion_run_token_impl(self)

    def _is_active_conversion_run_token(self: MainWindow, token: object) -> bool:
        return _is_active_conversion_run_token_impl(self, token)

    def _connect_worker_dispatch_signals(self: MainWindow) -> None:
        return _connect_worker_dispatch_signals_impl(
            self,
            connect_signal_best_effort_func=_connect_signal_best_effort,
        )

    def _emit_worker_finished_request(self: MainWindow, run_token: object, result: object) -> None:
        return _emit_worker_finished_request_impl(self, run_token, result)

    def _emit_worker_error_request(self: MainWindow, run_token: object, message: object) -> None:
        return _emit_worker_error_request_impl(self, run_token, message)

    def _emit_worker_log_request(self: MainWindow, run_token: object, text: object) -> None:
        return _emit_worker_log_request_impl(self, run_token, text)

    def _emit_worker_progress_request(self: MainWindow, run_token: object, current: object, total: object, message: object) -> None:
        return _emit_worker_progress_request_impl(self, run_token, current, total, message)

    def _emit_worker_cleanup_request(self: MainWindow, expected_worker: object = None, expected_thread: object = None) -> None:
        return _emit_worker_cleanup_request_impl(self, expected_worker, expected_thread)

    def _dispatch_worker_cleanup(self: MainWindow, expected_worker: object = None, expected_thread: object = None) -> None:
        return _dispatch_worker_cleanup_impl(self, expected_worker, expected_thread)

    def _dispatch_worker_log(self: MainWindow, run_token: object, text: object) -> None:
        return _dispatch_worker_log_impl(self, run_token, text)

    def _dispatch_conversion_progress(self: MainWindow, run_token: object, current: object, total: object, message: object) -> None:
        return _dispatch_conversion_progress_impl(self, run_token, current, total, message)

    def _dispatch_conversion_finished(self: MainWindow, run_token: object, result: ConversionResult) -> None:
        return _dispatch_conversion_finished_impl(self, run_token, result)

    def _dispatch_conversion_error(self: MainWindow, run_token: object, message: object) -> None:
        return _dispatch_conversion_error_impl(self, run_token, message)

    def start_conversion(self: MainWindow) -> None:
        return _start_conversion_impl(
            self,
            qthread_cls=QThread,
            conversion_worker_cls=ConversionWorker,
            safe_delete_qobject_later_func=_safe_delete_qobject_later,
        )

    def stop_conversion(self: MainWindow) -> None:
        _stop_conversion_impl(self)

    def _schedule_cleanup_worker(
        self: MainWindow,
        expected_worker: object = None,
        expected_thread: object = None,
    ) -> None:
        return _schedule_cleanup_worker_impl(
            self,
            qtimer_cls=QTimer,
            expected_worker=expected_worker,
            expected_thread=expected_thread,
        )

    def cleanup_worker(
        self: MainWindow,
        *,
        expected_worker: object = None,
        expected_thread: object = None,
    ) -> None:
        return _cleanup_worker_impl(
            self,
            expected_worker=expected_worker,
            expected_thread=expected_thread,
            safe_delete_qobject_later_func=_safe_delete_qobject_later,
        )

    def _merge_results_summary_lines_with_warnings(
        self: MainWindow,
        summary_lines: object,
        warning_values: object,
    ) -> list[object]:
        return _merge_results_summary_lines_with_warnings_impl(self, summary_lines, warning_values)

    def _merge_results_summary_lines_and_collect_warnings(
        self: MainWindow,
        summary_lines: object,
        collected_warnings: object,
        warning_values: object,
    ) -> tuple[object, list[str]]:
        return _merge_results_summary_lines_and_collect_warnings_impl(
            self,
            summary_lines,
            collected_warnings,
            warning_values,
        )

    def _build_results_summary_text(
        self: MainWindow,
        paths: object,
        summary_lines: object = None,
        *,
        fallback: object = None,
    ) -> str:
        return _build_results_summary_text_impl(self, paths, summary_lines, fallback=fallback)

    def _append_conversion_finish_error_log_with_fallback(
        self: MainWindow,
        log_message: object,
        *,
        status_timeout_ms: int = 5000,
    ) -> bool:
        return _append_conversion_finish_error_log_with_fallback_impl(
            self,
            log_message,
            status_timeout_ms=status_timeout_ms,
        )

    def _handle_conversion_finish_ui_error(
        self: MainWindow,
        msg: str,
        exc: object,
        *,
        context: str,
        badge_text: str = '完了',
        clear_results: bool = False,
    ) -> bool:
        return _handle_conversion_finish_ui_error_impl(
            self,
            msg,
            exc,
            context=context,
            badge_text=badge_text,
            clear_results=clear_results,
        )

    def _append_log_without_status(self: MainWindow, text: object) -> bool:
        return _append_log_without_status_impl(self, text)

    def _append_log_with_status_fallback(
        self: MainWindow,
        text: object,
        *,
        reflect_in_status: bool = False,
        status_timeout_ms: int = 5000,
    ) -> bool:
        return _append_log_with_status_fallback_impl(
            self,
            text,
            reflect_in_status=reflect_in_status,
            status_timeout_ms=status_timeout_ms,
        )

    def _append_log_without_status_best_effort(self: MainWindow, text: object) -> bool:
        return _append_log_without_status_best_effort_impl(self, text)

    def _append_log_without_status_or_status_bar(
        self: MainWindow,
        text: object,
        *,
        status_timeout_ms: int = 5000,
    ) -> bool:
        return _append_log_without_status_or_status_bar_impl(
            self,
            text,
            status_timeout_ms=status_timeout_ms,
        )

    def _append_log_without_status_with_optional_status_fallback(
        self: MainWindow,
        log_message: object,
        *,
        allow_status_fallback: bool = False,
        status_timeout_ms: int = 5000,
    ) -> bool:
        return _append_log_without_status_with_optional_status_fallback_impl(
            self,
            log_message,
            allow_status_fallback=allow_status_fallback,
            status_timeout_ms=status_timeout_ms,
        )

    def _emit_postprocess_warning(
        self: MainWindow,
        warning_message: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> bool:
        return _emit_postprocess_warning_impl(
            self,
            warning_message,
            duration_ms=duration_ms,
            show_status=show_status,
        )

    def _emit_postprocess_warning_via_log_and_optional_status_fallback(
        self: MainWindow,
        warning_message: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> bool:
        return _emit_postprocess_warning_via_log_and_optional_status_fallback_impl(
            self,
            warning_message,
            duration_ms=duration_ms,
            show_status=show_status,
        )

    def _emit_postprocess_warnings_and_collect(
        self: MainWindow,
        warning_values: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> list[str]:
        return _emit_postprocess_warnings_and_collect_impl(
            self,
            warning_values,
            duration_ms=duration_ms,
            show_status=show_status,
        )

    def _emit_postprocess_warnings(
        self: MainWindow,
        warning_values: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> bool:
        return _emit_postprocess_warnings_impl(
            self,
            warning_values,
            duration_ms=duration_ms,
            show_status=show_status,
        )

    def _emit_unique_postprocess_warnings_with_fallback(
        self: MainWindow,
        warning_values: object,
        emitted_messages: set[str] | None = None,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> list[str]:
        return _emit_unique_postprocess_warnings_with_fallback_impl(
            self,
            warning_values,
            emitted_messages,
            duration_ms=duration_ms,
            show_status=show_status,
        )

    def _append_unique_postprocess_warnings_to_log_with_fallback(
        self: MainWindow,
        warning_values: object,
        emitted_messages: set[str] | None = None,
        *,
        allow_status_fallback: bool = False,
        status_timeout_ms: int = 5000,
    ) -> list[str]:
        return _append_unique_postprocess_warnings_to_log_with_fallback_impl(
            self,
            warning_values,
            emitted_messages,
            allow_status_fallback=allow_status_fallback,
            status_timeout_ms=status_timeout_ms,
        )

    def _emit_unique_postprocess_warnings_or_append_to_log(
        self: MainWindow,
        warning_values: object,
        emitted_messages: set[str] | None = None,
        *,
        duration_ms: int = 5000,
        show_status: bool = True,
    ) -> list[str]:
        return _emit_unique_postprocess_warnings_or_append_to_log_impl(
            self,
            warning_values,
            emitted_messages,
            duration_ms=duration_ms,
            show_status=show_status,
        )

    def _build_conversion_completion_summary_lines(
        self: MainWindow,
        converted_files: object,
        summary_lines: object,
        result: Mapping[str, object] | None = None,
    ) -> list[str]:
        return _build_conversion_completion_summary_lines_impl(
            self,
            converted_files,
            summary_lines,
            result,
        )

    def _apply_conversion_completion_guidance_to_results_view(
        self: MainWindow,
        converted_files: object,
        summary_lines: object,
        result: Mapping[str, object] | None = None,
    ) -> bool:
        return _apply_conversion_completion_guidance_to_results_view_impl(
            self,
            converted_files,
            summary_lines,
            result,
        )

    def _open_finished_conversion_folder(self: MainWindow, result: ConversionResult) -> list[str]:
        """変換完了後のフォルダ自動オープンは行わない。"""
        return []

    def on_conversion_finished(self: MainWindow, result: ConversionResult) -> None:
        _handle_conversion_finished_impl(self, result)

    def on_conversion_error(self: MainWindow, message: str) -> None:
        return _handle_conversion_error_impl(self, message)

    def append_log(
        self: MainWindow,
        text: str,
        *,
        reflect_in_status: bool = True,
    ) -> None:
        return append_log_impl(self, text, reflect_in_status=reflect_in_status)

    def _progress_status_text(self: MainWindow, current: int, total: int, message: object) -> str:
        return studio_logic.build_progress_status_text(current, total, message, self.current_ui_language_value())

    def update_conversion_progress(self: MainWindow, current: int, total: int, message: str) -> None:
        _update_conversion_progress_impl(self, current, total, message)

    def open_log_folder(self: MainWindow) -> None:
        return open_log_folder_impl(
            self,
            resolve_log_dir_func=_resolve_log_dir,
            log_dir=LOG_DIR,
            open_path_in_file_manager_func=_open_path_in_file_manager,
        )

    def _set_results_summary_text_fallback(
        self: MainWindow,
        summary_text: object = None,
        *,
        default_text: str = '保存されたファイルはありません。',
    ) -> bool:
        return _set_results_summary_text_fallback_impl(self, summary_text, default_text=default_text)

    def _set_results_summary_text_with_fallback(
        self: MainWindow,
        summary_text: object = None,
        *,
        default_text: str = '保存されたファイルはありません。',
    ) -> bool:
        return _set_results_summary_text_with_fallback_impl(self, summary_text, default_text=default_text)

    def _set_bottom_tab_index_with_fallback(self: MainWindow, index: object) -> bool:
        return _set_bottom_tab_index_with_fallback_impl(self, index)

    def _clear_results_view(self: MainWindow, summary_text: object = None) -> bool:
        return _clear_results_view_impl(self, summary_text)

    def _sync_results_action_buttons_state(self: MainWindow) -> bool:
        return _sync_results_action_buttons_state_impl(self)

    def _preferred_result_path_for_action(self: MainWindow) -> str:
        return _preferred_result_path_for_action_impl(self)

    def open_results_folder_from_results(self: MainWindow) -> None:
        return open_results_folder_from_results_impl(self)

    def open_selected_result_from_results(self: MainWindow) -> None:
        return open_selected_result_from_results_impl(self)

    def _result_display_name(self: MainWindow, path_text: str) -> str:
        return _result_display_name_impl(self, path_text)

    def _normalized_result_entries(self: MainWindow, paths: list[object]) -> list[tuple[str, str]]:
        return _normalized_result_entries_impl(self, paths)

    def _apply_results_entries_to_ui(
        self: MainWindow,
        entries: list[tuple[str, str]],
        summary_text: object = None,
        initial_index: object = None,
    ) -> None:
        return _apply_results_entries_to_ui_impl(self, entries, summary_text, initial_index)

    def populate_results(self: MainWindow, paths: list[object], summary_lines: list[str] | None = None) -> None:
        return populate_results_impl(self, paths, summary_lines)

    def on_result_item_clicked(self: MainWindow, item: QListWidgetItem) -> None:
        return on_result_item_clicked_impl(self, item)

    def _normalize_results_path_key(self: MainWindow, path: object) -> str:
        return _normalize_results_path_key_impl(self, path)

    def _clear_results_selection_state(self: MainWindow) -> bool:
        return _clear_results_selection_state_impl(self)

    def _clear_results_selection_with_fallback(
        self: MainWindow,
        context: Mapping[str, object] | object = None,
    ) -> bool:
        return _clear_results_selection_with_fallback_impl(self, context)

    def _apply_results_selection_context_with_fallback(
        self: MainWindow,
        context: Mapping[str, object] | object,
    ) -> bool:
        return _apply_results_selection_context_with_fallback_impl(self, context)

    def _sync_results_selection_for_loaded_path_with_fallback(
        self: MainWindow,
        path: object,
    ) -> bool:
        return _sync_results_selection_for_loaded_path_with_fallback_impl(self, path)

    def _result_item_count(self: MainWindow) -> int:
        return _result_item_count_impl(self)

    def _result_item_at(self: MainWindow, index: object) -> QListWidgetItem | None:
        return _result_item_at_impl(self, index)

    def _result_item_paths(self: MainWindow) -> list[object]:
        return _result_item_paths_impl(self)

    def _result_item_path_keys(self: MainWindow) -> list[str]:
        return _result_item_path_keys_impl(self)

    def _set_results_current_index_with_fallback(self: MainWindow, index: object) -> bool:
        return _set_results_current_index_with_fallback_impl(self, index)

    def _apply_results_selection_context(self: MainWindow, context: Mapping[str, object] | object) -> QListWidgetItem | None:
        return _apply_results_selection_context_impl(self, context)

    def _sync_results_selection_for_loaded_path(self: MainWindow, path: object) -> None:
        _sync_results_selection_for_loaded_path_impl(self, path)

    def _selected_result_indexes(self: MainWindow) -> list[int]:
        return _selected_result_indexes_impl(self)

    def _current_results_index(self: MainWindow) -> int | None:
        return _current_results_index_impl(self)

    def _resolved_result_load_context(self: MainWindow) -> dict[str, object]:
        return _resolved_result_load_context_impl(self)

    def _resolved_results_item_for_loading(self: MainWindow) -> QListWidgetItem | None:
        return _resolved_results_item_for_loading_impl(self)

    def _fallback_loaded_result_load_context(self: MainWindow) -> dict[str, object]:
        return _fallback_loaded_result_load_context_impl(self)

    def _results_item_path(self: MainWindow, item: object) -> object:
        return _results_item_path_impl(self, item)

    def _show_result_load_dialog_with_status_fallback(
        self: MainWindow,
        level: str,
        title: str,
        message: str,
    ) -> None:
        return _show_result_load_dialog_with_status_fallback_impl(self, level, title, message)

    def load_selected_result(self: MainWindow) -> None:
        return load_selected_result_impl(self)

    # ── XTCビューア ───────────────────────────────────────

    def _xtc_source_payload(self: MainWindow, path: object) -> dict[str, str]:
        return _xtc_source_payload_impl(self, path)

    def _normalized_xtc_bytes(self: MainWindow, data: object) -> bytes:
        return _normalized_xtc_bytes_impl(self, data)

    def _xtc_document_payload(self: MainWindow, data: object) -> dict[str, object]:
        return _xtc_document_payload_impl(self, data, parse_xtc_pages=parse_xtc_pages)

    def _xtc_source_document_payload(self: MainWindow, path: object) -> dict[str, object]:
        return _xtc_source_document_payload_impl(self, path)

    def _xtc_display_name(self: MainWindow, path: object) -> str:
        return _xtc_display_name_impl(self, path)

    def _reset_xtc_page_input(self: MainWindow, total_pages: object, current_page: object = 0) -> None:
        _reset_xtc_page_input_impl(
            self,
            total_pages,
            current_page,
            bulk_block_signals=_bulk_block_signals,
            build_nav_bar_plan=gui_layouts.build_nav_bar_plan,
        )

    def _apply_xtc_document_payload(self: MainWindow, payload: Mapping[str, object]) -> None:
        _apply_xtc_document_payload_impl(self, payload)

    def _apply_loaded_xtc_document(self: MainWindow, data: bytes, pages: list[PageInfo]) -> None:
        _apply_loaded_xtc_document_impl(self, data, pages)

    def _current_xtc_page_blob(self: MainWindow, *, force_loaded_xtc: bool = False) -> bytes | None:
        return _current_xtc_page_blob_impl(self, force_loaded_xtc=force_loaded_xtc)

    def _clear_xtc_viewer_page(self: MainWindow, *, refresh_navigation: bool = True) -> None:
        _clear_xtc_viewer_page_impl(self, refresh_navigation=refresh_navigation)

    def _page_image_dimensions(self: MainWindow, image: object) -> tuple[int, int]:
        return _page_image_dimensions_impl(self, image)

    def _viewer_profile_for_dimensions(self: MainWindow, width: object, height: object) -> DeviceProfile:
        return _viewer_profile_for_dimensions_impl(self, width, height)

    def _custom_viewer_profile_for_dimensions(self: MainWindow, width: int, height: int) -> DeviceProfile:
        return _custom_viewer_profile_for_dimensions_impl(self, width, height)

    def _viewer_profile_for_xtc_pages(self: MainWindow, pages: object) -> DeviceProfile | None:
        return _viewer_profile_for_xtc_pages_impl(self, pages)

    def _viewer_profile_for_page_image(self: MainWindow, image: object) -> DeviceProfile:
        return _viewer_profile_for_page_image_impl(self, image)

    def _viewer_profile_for_preview_payload(self: MainWindow, payload: object = None) -> DeviceProfile:
        return _viewer_profile_for_preview_payload_impl(self, payload)

    def _refresh_successful_device_render_status(self: MainWindow) -> None:
        _refresh_successful_device_render_status_impl(self)

    def _apply_rendered_xtc_page(
        self: MainWindow,
        image: QImage,
        *,
        refresh_navigation: bool = True,
        profile: DeviceProfile | None = None,
    ) -> None:
        _apply_rendered_xtc_page_impl(
            self,
            image,
            refresh_navigation=refresh_navigation,
            profile=profile,
        )

    def _render_failure_status_message(self: MainWindow, title: object, exc: Exception) -> str:
        return _render_failure_status_message_impl(self, title, exc)

    def _handle_xtc_render_failure(self: MainWindow, exc: Exception, *, refresh_navigation: bool = True) -> None:
        _handle_xtc_render_failure_impl(self, exc, refresh_navigation=refresh_navigation)

    def _set_current_device_preview_page_index(self: MainWindow, index: object, *, refresh_navigation: bool = False) -> bool:
        return _set_current_device_preview_page_index_impl(self, index, refresh_navigation=refresh_navigation)

    def _set_current_page_index(self: MainWindow, index: object, *, refresh_navigation: bool = False) -> bool:
        return _set_current_page_index_impl(self, index, refresh_navigation=refresh_navigation)

    def _apply_loaded_xtc_view_mode(self: MainWindow, mode: object, *, safe: bool = False) -> None:
        return _apply_loaded_xtc_view_mode_impl(self, mode, safe=safe)

    def _apply_loaded_xtc_ui_context(self: MainWindow, context: Mapping[str, object] | object) -> None:
        return _apply_loaded_xtc_ui_context_impl(self, context)

    def _apply_loaded_xtc_path_success(self: MainWindow, path_text: str, display_name: str) -> None:
        _apply_loaded_xtc_path_success_impl(self, path_text, display_name)

    def _apply_loaded_xtc_path_failure(self: MainWindow) -> None:
        _apply_loaded_xtc_path_failure_impl(self)

    def _restore_results_selection_after_xtc_load_failure(self: MainWindow) -> None:
        _restore_results_selection_after_xtc_load_failure_impl(self)

    def _xtc_load_failure_preserved_display_name(self: MainWindow) -> str:
        return _xtc_load_failure_preserved_display_name_impl(self)

    def _xtc_load_failure_status_message(self: MainWindow, path: object, exc: Exception) -> str:
        return _xtc_load_failure_status_message_impl(self, path, exc)

    def _apply_loaded_xtc_bytes_success(self: MainWindow) -> None:
        _apply_loaded_xtc_bytes_success_impl(self)

    def open_xtc_file(self: MainWindow) -> None:
        return open_xtc_file_impl(
            self,
            home_path=Path.home(),
            result_tab_index=RESULT_TAB_INDEX,
            log_tab_index=LOG_TAB_INDEX,
        )

    def load_xtc_from_path(self: MainWindow, path: object) -> bool:
        return load_xtc_from_path_impl(self, path)

    def load_xtc_from_bytes(self: MainWindow, data: bytes) -> None:
        load_xtc_from_bytes_impl(self, data)

    def render_current_page(self: MainWindow, *, refresh_navigation: bool = True) -> None:
        render_current_page_impl(
            self,
            refresh_navigation=refresh_navigation,
            decode_preview_png=lambda raw, fmt: QImage.fromData(raw, fmt),
            decode_preview_base64=base64.b64decode,
            xt_page_blob_to_qimage=xt_page_blob_to_qimage,
        )

    # ── 設定の保存 / 読み込み ──────────────────────────────

    def _restore_settings(self: MainWindow) -> None:
        _restore_settings_impl(self)

    def save_ui_state(self: MainWindow) -> None:
        if not getattr(self, '_initialized', False):
            return
        try:
            for key, value in self._window_state_save_payload().items():
                self.settings_store.setValue(key, value)
            for key, value in self._settings_save_payload().items():
                self.settings_store.setValue(key, value)
            self.settings_store.sync()
        except Exception:
            APP_LOGGER.exception('UI状態保存に失敗しました')

    # ── ヘルプ ─────────────────────────────────────────────

    def show_help_dialog(self: MainWindow) -> None:
        help_message = self._ui_text('使い方ダイアログを開けませんでした。')
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle(self._ui_text('使い方'))
            dlg.resize(640, 500)
            lay = QVBoxLayout(dlg)
            tv = QTextEdit(dlg)
            tv.setReadOnly(True)
            current_language = self._normalize_ui_language(
                getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE),
                DEFAULT_UI_LANGUAGE,
            )
            tv.setPlainText(usage_help_text(current_language))
            lay.addWidget(tv)
            close_btn = QPushButton(self._ui_text('閉じる'))
            close_btn.clicked.connect(dlg.accept)
            lay.addWidget(close_btn)
            dlg.exec()
            return
        except Exception:
            pass
        try:
            self._show_ui_status_message_with_reflection_or_direct_fallback(help_message, 5000)
        except Exception:
            try:
                self.statusBar().showMessage(help_message, 5000)
            except Exception:
                pass



# ─────────────────────────────────────────────────────────
# エントリーポイント
# ─────────────────────────────────────────────────────────

def main():
    _configure_app_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
