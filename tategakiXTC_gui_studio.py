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
from typing import Any, Callable, Mapping, Sequence, cast

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
def _resolve_log_dir() -> Path:
    global ACTIVE_LOG_DIR
    if isinstance(ACTIVE_LOG_DIR, Path):
        return ACTIVE_LOG_DIR
    last_error: Exception | None = None
    for candidate in (LOG_DIR, FALLBACK_LOG_DIR):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            last_error = exc
            continue
        ACTIVE_LOG_DIR = candidate
        return candidate
    if last_error is not None:
        raise last_error
    raise RuntimeError('ログ保存先を作成できませんでした。')


def _resolve_session_log_path() -> Path:
    global SESSION_LOG_PATH
    if isinstance(SESSION_LOG_PATH, Path):
        return SESSION_LOG_PATH
    log_dir = _resolve_log_dir()
    SESSION_LOG_PATH = log_dir / f'tategakiXTC_gui_studio_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    return SESSION_LOG_PATH



def _configure_app_logging() -> logging.Logger:
    logger = logging.getLogger(APP_LOGGER_NAME)
    if getattr(logger, '_tategaki_configured', False):
        return logger

    session_log_path = _resolve_session_log_path()
    active_log_dir = _resolve_log_dir()
    _cleanup_old_session_logs(active_log_dir, active_log_path=session_log_path)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    file_handler = logging.FileHandler(session_log_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger.propagate = False
    logger._tategaki_configured = True
    if active_log_dir != LOG_DIR:
        logger.warning('既定のログフォルダを作成できなかったため、一時フォルダへ退避します: %s', active_log_dir)
    logger.info('ログ初期化: %s', session_log_path)
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
    _safe_delete_qobject_later,
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

from tategakiXTC_gui_studio_preview_helpers import (
    _coerce_preview_base64_text,
    _coerce_preview_data_url,
)

from tategakiXTC_gui_studio_path_helpers import (
    _supported_targets_for_path,
    _default_output_name_for_target,
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
    DEFAULT_PREVIEW_PAGE_LIMIT,
    SETTINGS_SCHEMA_VERSION,
    DEFAULT_RENDER_SETTINGS,
    RESULT_TAB_INDEX,
    LOG_TAB_INDEX,
    SUPPORTED_INPUT_SUFFIXES,
    UI_ASSETS_DIR,
    SPIN_UP_ICON,
    SPIN_DOWN_ICON,
    SPIN_UP_ICON_DARK,
    SPIN_DOWN_ICON_DARK,
    TEXT_OR_MARKDOWN_LABEL,
    FONT_REQUIRED_SUFFIXES,
    DeviceProfile,
    DEVICE_PROFILES,
    _make_preset,
    DEFAULT_PRESET_DEFINITIONS,
    PRESET_FIELDS,
    KINSOKU_MODE_OPTIONS,
    KINSOKU_MODE_LABELS,
    GLYPH_POSITION_MODE_OPTIONS,
    GLYPH_POSITION_MODE_LABELS,
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
        self._previous_shutdown_clean = self._settings_bool_value('last_shutdown_clean', True)
        self._mark_shutdown_clean(False)
        self.preset_definitions = self._load_preset_definitions()
        self.setWindowTitle(APP_NAME)
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
        statuses = core.list_optional_dependency_status()
        missing = [item for item in statuses if not item.get('available')]
        if not missing:
            return

        grouped: dict[str, list[MissingDependencyItem]] = {
            'feature': [],
            'performance': [],
            'convenience': [],
        }
        for item in missing:
            impact = str(item.get('impact') or 'feature')
            grouped.setdefault(impact, []).append(item)

        lines: list[str] = []
        if grouped.get('feature'):
            lines.append('一部の追加ライブラリが未導入です。使えない機能があります。')
            for item in grouped['feature']:
                lines.append(f"- {item['label']}（{item['purpose']}）")
        if grouped.get('performance'):
            lines.append('高速化用の追加ライブラリが未導入です。変換速度が低下することがあります。')
            for item in grouped['performance']:
                lines.append(f"- {item['label']}（{item['purpose']}）")
        if grouped.get('convenience'):
            lines.append('任意の補助ライブラリが未導入です。進捗表示などが簡略化される場合があります。')
            for item in grouped['convenience']:
                lines.append(f"- {item['label']}（{item['purpose']}）")
        self._append_log_without_status_best_effort(' / '.join(lines))

    def _missing_dependencies_for_targets(self: MainWindow, targets: list[Path]) -> list[MissingDependencyItem]:
        suffixes = {p.suffix.lower() for p in targets}
        return core.get_missing_dependencies_for_suffixes(suffixes)

    def _show_warning_dialog_with_status_fallback(
        self: MainWindow,
        title: str,
        message: str,
        *,
        duration_ms: int = 5000,
    ) -> None:
        _show_warning_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'warning', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            title,
            message,
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
        return _ask_question_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'question', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            _coerce_ui_message_text,
            title,
            message,
            buttons,
            default_button,
            duration_ms=duration_ms,
            fallback_status_message=fallback_status_message,
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
        _show_information_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'information', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            _coerce_ui_message_text,
            title,
            message,
            duration_ms=duration_ms,
            fallback_status_message=fallback_status_message,
        )

    def _show_critical_dialog_with_status_fallback(
        self: MainWindow,
        title: str,
        message: str,
        *,
        duration_ms: int = 5000,
        fallback_status_message: str = '',
    ) -> None:
        _show_critical_dialog_with_status_fallback_impl(
            self,
            getattr(QMessageBox, 'critical', None),
            self._show_ui_status_message_with_reflection_or_direct_fallback,
            _coerce_ui_message_text,
            title,
            message,
            duration_ms=duration_ms,
            fallback_status_message=fallback_status_message,
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
            title,
            start_dir,
            filter_text,
            warning_title=warning_title,
            fallback_status_message=fallback_status_message,
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
            title,
            start_dir,
            warning_title=warning_title,
            fallback_status_message=fallback_status_message,
        )

    def _install_folder_batch_menu_action(self: MainWindow) -> None:
        """Add the first low-risk UI entry point for folder batch conversion."""
        try:
            from tategakiXTC_folder_batch_mainwindow_launcher import (
                install_folder_batch_menu_action_best_effort,
            )

            install_folder_batch_menu_action_best_effort(self)
        except Exception:
            APP_LOGGER.exception('フォルダ一括変換メニューの追加に失敗しました')

    def _open_folder_batch_dialog(self: MainWindow) -> None:
        """Open the folder batch dialog and run it through the worker bridge."""
        try:
            from tategakiXTC_folder_batch_mainwindow_launcher import (
                open_folder_batch_dialog_for_mainwindow_real_or_warn,
            )

            open_folder_batch_dialog_for_mainwindow_real_or_warn(self)
        except Exception as exc:
            APP_LOGGER.exception('フォルダ一括変換ダイアログの起動に失敗しました')
            self._show_warning_dialog_with_status_fallback(
                'フォルダ一括変換',
                f'フォルダ一括変換を開始できませんでした: {exc}',
            )

    def _check_conversion_dependencies(self: MainWindow, cfg: WorkerConversionSettings) -> bool:
        supported = self._supported_targets_for_path(cfg.get('target', ''))
        missing = self._missing_dependencies_for_targets(supported)
        if not missing:
            return True
        self._show_warning_dialog_with_status_fallback('ライブラリ不足', _format_missing_dependency_message(missing))
        missing_log_message = '不足ライブラリ: ' + ', '.join(item['label'] for item in missing)
        self._append_log_without_status_best_effort(missing_log_message)
        return False

    def _settings_raw_value(self: MainWindow, key: str, default: object = None) -> object:
        return _settings_raw_value_from_store(self.settings_store, key, default)

    def _settings_contains_key(self: MainWindow, key: str) -> bool:
        return _settings_contains_key_in_store(self.settings_store, key)

    def _settings_int_value(self: MainWindow, key: str, default: int) -> int:
        return _settings_int_value_from_store(self.settings_store, key, default)

    def _settings_bool_value(self: MainWindow, key: str, default: bool) -> bool:
        return _settings_bool_value_from_store(self.settings_store, key, default)

    def _settings_str_value(self: MainWindow, key: str, default: str = '') -> str:
        return _settings_str_value_from_store(self.settings_store, key, default)

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
        return getattr(Qt, name, fallback)

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

    def _window_state_restore_payload(self: MainWindow) -> dict[str, object]:
        default_size = self._default_window_size()
        default_width = int(default_size.width())
        default_height = int(default_size.height())
        raw_payload = {
            'geometry': self._settings_raw_value('geometry', None),
            'window_width': self._settings_raw_value('window_width', default_width),
            'window_height': self._settings_raw_value('window_height', default_height),
            'is_maximized': self._settings_raw_value('is_maximized', False),
            'left_panel_width': self._settings_raw_value('left_panel_width', DEFAULT_LEFT_PANEL_WIDTH),
            'left_splitter_state': self._settings_raw_value('left_splitter_state', None),
            'left_splitter_sizes': self._default_left_splitter_sizes(),
            'left_panel_visible': self._settings_raw_value('left_panel_visible', True),
        }
        return studio_logic.build_window_state_restore_payload(
            raw_payload,
            default_width=default_width,
            default_height=default_height,
            default_left_panel_width=DEFAULT_LEFT_PANEL_WIDTH,
            default_left_splitter_sizes=self._default_left_splitter_sizes(),
        )

    def _settings_restore_payload(self: MainWindow) -> dict[str, object]:
        payload = settings_controller.build_settings_restore_payload(
            read_default_value=self._settings_default_value,
            default_font_name=self._default_font_name(),
            default_preview_page_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
            allowed_view_modes={'font', 'device'},
            allowed_profiles=DEVICE_PROFILES,
            allowed_kinsoku_modes=KINSOKU_MODE_LABELS,
            allowed_glyph_position_modes=GLYPH_POSITION_MODE_LABELS,
            allowed_output_formats=OUTPUT_FORMAT_LABELS,
            allowed_output_conflicts=OUTPUT_CONFLICT_LABELS,
            normalize_font_setting_value=self._normalize_font_setting_value,
            normalize_target_path_text=worker_logic.normalize_target_path_text,
            resolve_profile_dimensions=self._resolved_profile_and_dimensions,
        )
        payload['preview_zoom_pct'] = self._normalize_preview_zoom_pct(
            self._settings_raw_value('preview_zoom_pct', 100)
        )
        return payload

    def _startup_preview_defaults_payload(self: MainWindow, payload: Mapping[str, object]) -> dict[str, object]:
        # sweep348: 通常倍率UIは実寸近似OFFのフォントビュー用。
        # 起動直後に保存済みの実寸近似/実機ビューを復元すると、倍率ボタンが
        # 近くにあるのに効かない状態に見えるため、起動時だけ右ペインを
        # 通常フォントビューへ戻す。通常倍率値そのものは別途復元する。
        return studio_logic.build_startup_preview_defaults_payload(payload)

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
            'profile_combo', 'actual_size_check', 'guides_check', 'calib_spin', 'preview_zoom_spin', 'nav_reverse_check',
            'font_combo', 'font_size_spin', 'ruby_size_spin', 'line_spacing_spin',
            'margin_t_spin', 'margin_b_spin', 'margin_r_spin', 'margin_l_spin',
            'threshold_spin', 'width_spin', 'height_spin', 'preview_page_limit_spin', 'dither_check', 'night_check',
            'open_folder_check', 'output_conflict_combo', 'output_format_combo',
            'kinsoku_mode_combo', 'punctuation_position_combo', 'ichi_position_combo', 'lower_closing_bracket_position_combo', 'wave_dash_drawing_combo', 'wave_dash_position_combo', 'target_edit', 'preset_combo',
        )

    def _preset_apply_widgets(self: MainWindow) -> tuple[object, ...]:
        return self._existing_widgets(
            'profile_combo', 'width_spin', 'height_spin', 'font_combo',
            'font_size_spin', 'ruby_size_spin', 'line_spacing_spin',
            'margin_t_spin', 'margin_b_spin', 'margin_r_spin', 'margin_l_spin',
            'night_check', 'dither_check', 'kinsoku_mode_combo', 'punctuation_position_combo', 'ichi_position_combo', 'lower_closing_bracket_position_combo', 'wave_dash_drawing_combo', 'wave_dash_position_combo', 'output_format_combo',
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
        apply_defaults = settings_controller.build_settings_ui_apply_defaults(
            actual_size=self._safe_widget_checked('actual_size_check'),
            show_guides=self._safe_widget_checked('guides_check'),
            calibration_pct=self._safe_widget_value('calib_spin', 100),
            nav_buttons_reversed=getattr(self, 'nav_buttons_reversed', False),
            font_size=self._safe_widget_value('font_size_spin', 26),
            ruby_size=self._safe_widget_value('ruby_size_spin', 12),
            line_spacing=self._safe_widget_value('line_spacing_spin', 44),
            margin_t=self._safe_widget_value('margin_t_spin', 12),
            margin_b=self._safe_widget_value('margin_b_spin', 14),
            margin_r=self._safe_widget_value('margin_r_spin', 12),
            margin_l=self._safe_widget_value('margin_l_spin', 12),
            threshold=self._safe_widget_value('threshold_spin', 128),
            preview_page_limit=self._safe_widget_value('preview_page_limit_spin', DEFAULT_PREVIEW_PAGE_LIMIT),
            dither=self._safe_widget_checked('dither_check'),
            night_mode=self._safe_widget_checked('night_check'),
            open_folder=self._safe_widget_checked('open_folder_check'),
            output_conflict=self._safe_combo_data('output_conflict_combo', 'rename'),
            output_format=self._safe_combo_data('output_format_combo', 'xtc'),
            kinsoku_mode=self._safe_combo_data('kinsoku_mode_combo', 'standard'),
            punctuation_position_mode=self._safe_combo_data('punctuation_position_combo', 'standard'),
            ichi_position_mode=self._safe_combo_data('ichi_position_combo', 'standard'),
            lower_closing_bracket_position_mode=self._safe_combo_data('lower_closing_bracket_position_combo', 'standard'),
            wave_dash_drawing_mode=self._safe_combo_data('wave_dash_drawing_combo', 'rotate'),
            wave_dash_position_mode=self._safe_combo_data('wave_dash_position_combo', 'standard'),
            main_view_mode=getattr(self, 'main_view_mode', 'font'),
        )
        apply_plan = settings_controller.build_settings_ui_apply_plan(
            raw_payload=payload,
            defaults=apply_defaults,
            allowed_view_modes={'font', 'device'},
            allowed_kinsoku_modes=KINSOKU_MODE_LABELS,
            allowed_glyph_position_modes=GLYPH_POSITION_MODE_LABELS,
            allowed_output_formats=OUTPUT_FORMAT_LABELS,
            allowed_output_conflicts=OUTPUT_CONFLICT_LABELS,
            bottom_tab_count=self.bottom_tabs.count() if hasattr(self, 'bottom_tabs') else 0,
        )

        profile_value = apply_plan.get('profile', self._current_profile_key_or_default())
        width = apply_plan.get('width')
        height = apply_plan.get('height')
        if any(key in apply_plan for key in ('profile', 'width', 'height')):
            self._apply_profile_dimensions_to_ui(profile_value, width, height)

        if 'actual_size' in apply_plan:
            getattr(self, 'actual_size_check', None) is not None and self.actual_size_check.setChecked(bool(apply_plan['actual_size']))
        if 'show_guides' in apply_plan:
            getattr(self, 'guides_check', None) is not None and self.guides_check.setChecked(bool(apply_plan['show_guides']))
        if 'calibration_pct' in apply_plan:
            getattr(self, 'calib_spin', None) is not None and self.calib_spin.setValue(int(apply_plan['calibration_pct']))
        if 'preview_zoom_pct' in payload:
            zoom_spin = getattr(self, 'preview_zoom_spin', None)
            if zoom_spin is not None:
                zoom_spin.setValue(self._normalize_preview_zoom_pct(payload.get('preview_zoom_pct')))
        self._sync_preview_zoom_control_state()
        if 'nav_buttons_reversed' in apply_plan:
            nav_reversed = bool(apply_plan['nav_buttons_reversed'])
            self.nav_buttons_reversed = nav_reversed
            getattr(self, 'nav_reverse_check', None) is not None and self.nav_reverse_check.setChecked(nav_reversed)
            self._update_nav_button_texts()

        if 'font_file' in apply_plan:
            font_value = self._normalize_font_setting_value(
                apply_plan.get('font_file'),
                self._default_font_name(),
            ) or self._default_font_name()
            if font_value:
                font_combo = getattr(self, 'font_combo', None)
                signals_blocked_getter = getattr(font_combo, 'signalsBlocked', None)
                signals_blocked = False
                if callable(signals_blocked_getter):
                    try:
                        signals_blocked = bool(signals_blocked_getter())
                    except Exception:
                        signals_blocked = False
                if signals_blocked and font_combo is not None:
                    self._ensure_font_combo_value(font_value)
                    find_data = getattr(font_combo, 'findData', None)
                    idx = find_data(font_value) if callable(find_data) else -1
                    if isinstance(idx, int) and idx >= 0:
                        font_combo.setCurrentIndex(idx)
                        reset_popup_scroll = getattr(font_combo, '_reset_popup_scroll_to_top', None)
                        if callable(reset_popup_scroll):
                            reset_popup_scroll()
                    else:
                        self._set_current_font_value(font_value)
                else:
                    self._set_current_font_value(font_value)

        for key, widget in [
            ('font_size', getattr(self, 'font_size_spin', None)),
            ('ruby_size', getattr(self, 'ruby_size_spin', None)),
            ('line_spacing', getattr(self, 'line_spacing_spin', None)),
            ('margin_t', getattr(self, 'margin_t_spin', None)),
            ('margin_b', getattr(self, 'margin_b_spin', None)),
            ('margin_r', getattr(self, 'margin_r_spin', None)),
            ('margin_l', getattr(self, 'margin_l_spin', None)),
            ('threshold', getattr(self, 'threshold_spin', None)),
            ('preview_page_limit', getattr(self, 'preview_page_limit_spin', None)),
        ]:
            if key in apply_plan and widget is not None:
                widget.setValue(int(apply_plan[key]))

        if 'dither' in apply_plan:
            getattr(self, 'dither_check', None) is not None and self.dither_check.setChecked(bool(apply_plan['dither']))
        self._apply_render_option_ui_state()
        if 'night_mode' in apply_plan:
            getattr(self, 'night_check', None) is not None and self.night_check.setChecked(bool(apply_plan['night_mode']))
        if 'open_folder' in apply_plan:
            getattr(self, 'open_folder_check', None) is not None and self.open_folder_check.setChecked(bool(apply_plan['open_folder']))
        if 'output_conflict' in apply_plan:
            getattr(self, 'output_conflict_combo', None) is not None and self._set_combo_to_data(self.output_conflict_combo, str(apply_plan['output_conflict']))
        if 'output_format' in apply_plan:
            getattr(self, 'output_format_combo', None) is not None and self._set_combo_to_data(self.output_format_combo, str(apply_plan['output_format']))
        if 'kinsoku_mode' in apply_plan:
            getattr(self, 'kinsoku_mode_combo', None) is not None and self._set_combo_to_data(self.kinsoku_mode_combo, str(apply_plan['kinsoku_mode']))
        if 'punctuation_position_mode' in apply_plan:
            getattr(self, 'punctuation_position_combo', None) is not None and self._set_combo_to_data(self.punctuation_position_combo, str(apply_plan['punctuation_position_mode']))
        if 'ichi_position_mode' in apply_plan:
            getattr(self, 'ichi_position_combo', None) is not None and self._set_combo_to_data(self.ichi_position_combo, str(apply_plan['ichi_position_mode']))
        if 'lower_closing_bracket_position_mode' in apply_plan:
            getattr(self, 'lower_closing_bracket_position_combo', None) is not None and self._set_combo_to_data(self.lower_closing_bracket_position_combo, str(apply_plan['lower_closing_bracket_position_mode']))
        if 'wave_dash_drawing_mode' in apply_plan:
            getattr(self, 'wave_dash_drawing_combo', None) is not None and self._set_combo_to_data(self.wave_dash_drawing_combo, str(apply_plan['wave_dash_drawing_mode']))
        if 'wave_dash_position_mode' in apply_plan:
            getattr(self, 'wave_dash_position_combo', None) is not None and self._set_combo_to_data(self.wave_dash_position_combo, str(apply_plan['wave_dash_position_mode']))

        if 'target' in apply_plan:
            getattr(self, 'target_edit', None) is not None and self.target_edit.setText(str(apply_plan.get('target') or '').strip())

        if 'main_view_mode' in apply_plan:
            hasattr(self, 'set_main_view_mode') and self.set_main_view_mode(str(apply_plan['main_view_mode']), initial=True)

        if 'bottom_tab_index' in apply_plan:
            hasattr(self, '_set_bottom_tab_index_with_fallback') and self._set_bottom_tab_index_with_fallback(int(apply_plan['bottom_tab_index']))

        if 'nav_buttons_reversed' in apply_plan:
            hasattr(self, 'update_navigation_ui') and self.update_navigation_ui()

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
        if not hasattr(self, 'viewer_widget'):
            return

        actual_size = False
        if hasattr(self, 'actual_size_check') and hasattr(self.actual_size_check, 'isChecked'):
            actual_size = bool(self.actual_size_check.isChecked())

        calibration_pct = 100
        if hasattr(self, 'calib_spin') and hasattr(self.calib_spin, 'value'):
            try:
                calibration_pct = int(self.calib_spin.value())
            except Exception:
                calibration_pct = 100

        show_guides = False
        if hasattr(self, 'guides_check') and hasattr(self.guides_check, 'isChecked'):
            show_guides = bool(self.guides_check.isChecked())

        margin_t, margin_b, margin_r, margin_l = self._current_guide_margins()

        self.viewer_widget.set_actual_size(actual_size)
        self.viewer_widget.set_calibration(1.0 if actual_size else calibration_pct / 100.0)
        if hasattr(self.viewer_widget, 'set_preview_zoom_factor'):
            self.viewer_widget.set_preview_zoom_factor(self._preview_zoom_factor())
        self.viewer_widget.set_show_guides(show_guides)
        self.viewer_widget.set_guide_margins(margin_t, margin_b, margin_r, margin_l)
        try:
            self.viewer_widget.set_profile(self._active_device_viewer_profile())
        except Exception:
            pass

    def _apply_profile_runtime_state(self: MainWindow) -> None:
        profile_key, profile, _width, _height = self._resolved_profile_and_dimensions()
        self.current_profile_key = profile_key
        if hasattr(self, 'viewer_widget'):
            self.viewer_widget.set_profile(self._active_device_viewer_profile())
        try:
            self._sync_preview_size()
        except Exception:
            pass
        if hasattr(self, 'profile_hint'):
            self.profile_hint.setText(profile.tagline)
            self.profile_hint.setVisible(bool(profile.tagline))

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
            self.mark_preview_dirty()

    def _normalize_font_setting_value(self: MainWindow, value: object, fallback: str = '') -> str:
        font_value = worker_logic._str_config_value({'font_file': value}, 'font_file', fallback)
        font_value = core.build_font_spec(*core.parse_font_spec(font_value))
        lower = str(core.parse_font_spec(font_value)[0]).lower()
        if any(token in lower for token in ('msgothic', 'msmincho', 'ms gothic', 'ms mincho')):
            font_value = core.build_font_spec(*core.parse_font_spec(fallback))
        return font_value

    def _default_window_size(self: MainWindow) -> QSize:
        width = max(1100, self._settings_int_value('window_width', DEFAULT_WINDOW_WIDTH))
        height = max(760, self._settings_int_value('window_height', DEFAULT_WINDOW_HEIGHT))
        return QSize(width, height)

    def _default_left_splitter_sizes(self: MainWindow) -> list[int]:
        top = max(280, self._settings_int_value('left_splitter_top', DEFAULT_LEFT_SPLITTER_TOP))
        bottom = max(92, self._settings_int_value('left_splitter_bottom', DEFAULT_LEFT_SPLITTER_BOTTOM))

        has_saved_top = self._settings_contains_key('left_splitter_top')
        has_saved_state = self._settings_contains_key('left_splitter_state')
        if not has_saved_top and not has_saved_state:
            content_height = self._left_settings_content_height_hint()
            if content_height > 0:
                top = max(280, content_height)
                available_height = self._default_left_splitter_available_height()
                if available_height > 0:
                    bottom = max(92, available_height - top)
        return [top, bottom]

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
        else:
            QTimer.singleShot(0, self._sync_preview_size)

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
        return name or target_text or '前回の作業ファイル'

    def _confirm_startup_previous_target_preview(self: MainWindow, target_text: str) -> bool:
        question = getattr(QMessageBox, 'question', None)
        standard_buttons = getattr(QMessageBox, 'StandardButton', None)
        yes_button = getattr(QMessageBox, 'Yes', getattr(standard_buttons, 'Yes', None))
        no_button = getattr(QMessageBox, 'No', getattr(standard_buttons, 'No', None))
        if not callable(question) or yes_button is None or no_button is None:
            return False
        display_name = self._startup_previous_target_display_text(target_text)
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
            response = question(self, '前回の作業', message, buttons, yes_button)
        except TypeError:
            try:
                response = question(self, '前回の作業', message)
            except Exception:
                return False
        except Exception:
            return False
        return response == yes_button

    def _clear_startup_target_for_sample_preview(self: MainWindow) -> None:
        target_edit = getattr(self, 'target_edit', None)
        setter = getattr(target_edit, 'setText', None)
        if not callable(setter):
            return
        try:
            with _bulk_block_signals(target_edit):
                setter('')
        except Exception:
            try:
                setter('')
            except Exception:
                pass

    def _show_startup_sample_preview_status(self: MainWindow, message: str) -> None:
        try:
            self._show_ui_status_message_with_reflection_or_direct_fallback(message, 5000)
        except Exception:
            APP_LOGGER.info(message)

    def _request_startup_sample_preview(self: MainWindow) -> bool:
        try:
            return bool(self.request_preview_refresh(reset_page=True))
        except Exception:
            APP_LOGGER.exception('起動時サンプルプレビューの生成に失敗しました')
            return False

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
        _scroll_combo_popup_to_top_now(font_combo)
        reset_popup_scroll = getattr(font_combo, '_reset_popup_scroll_to_top', None)
        if callable(reset_popup_scroll):
            try:
                QTimer.singleShot(50, reset_popup_scroll)
            except Exception:
                pass

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
        # 実機ビューのページ送り：左右矢印キー対応
        if event.type() == QEvent.ShortcutOverride:
            key = event.key()
            if key in (Qt.Key_Left, Qt.Key_Right) and self._can_handle_device_view_arrow_key():
                event.accept()
                return True
        if event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Left, Qt.Key_Right):
                if self._handle_device_view_arrow_key(key):
                    event.accept()
                    return True
        return super().eventFilter(obj, event)

    def _can_handle_device_view_arrow_key(self: MainWindow) -> bool:
        view_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        if view_mode == 'font':
            if not self._runtime_preview_pages():
                return False
        elif view_mode == 'device':
            if self._effective_device_view_source() == 'preview':
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

    def _handle_device_view_arrow_key(self: MainWindow, key: int) -> bool:
        if not self._can_handle_device_view_arrow_key():
            return False

        if hasattr(self, 'viewer_widget'):
            self.viewer_widget.setFocus(Qt.ShortcutFocusReason)

        logical_delta = -1 if key == Qt.Key_Left else 1
        delta = -logical_delta if bool(getattr(self, 'nav_buttons_reversed', False)) else logical_delta
        self.change_page(delta)
        return True

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
        if not self._settings_contains_key('left_splitter_state'):
            self.left_splitter.setSizes(self._default_left_splitter_sizes())
        self._sync_preview_size()

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

        self.left_panel = self._build_left_settings()
        self.left_panel.setMinimumWidth(380)

        right = self._build_right_preview()

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(6)
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(right)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)

        root.addWidget(self.main_splitter, 1)
        self.main_view_mode = 'font'
        self._show_ui_status_message_with_reflection_or_direct_fallback('準備完了', None)

    # ── トップバー ─────────────────────────────────────────

    def _build_top_bar(self):
        top_bar_plan = gui_layouts.build_top_bar_plan(path_button_width=DEFAULT_TOP_PATH_BUTTON_WIDTH)
        bar = QFrame()
        bar.setObjectName('topBar')
        bar.setFixedHeight(self._plan_int_value(top_bar_plan, 'bar_height', 56))
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(*self._plan_int_tuple_value(top_bar_plan, 'contents_margins', (16, 0, 12, 0), expected_length=4))
        lay.setSpacing(self._plan_int_value(top_bar_plan, 'spacing', 10))

        title = QLabel(APP_NAME)
        title.setObjectName('appTitle')
        lay.addWidget(title)
        lay.addWidget(self._v_sep())

        btn_file = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                top_bar_plan.get('file_button_text', 'ファイル'),
                object_name='topBtn',
                fixed_width=top_bar_plan.get('path_button_width', DEFAULT_TOP_PATH_BUTTON_WIDTH),
            ),
            lambda: self.select_target_path(True),
        )

        btn_folder = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                top_bar_plan.get('folder_button_text', 'フォルダ'),
                object_name='topBtn',
                fixed_width=top_bar_plan.get('path_button_width', DEFAULT_TOP_PATH_BUTTON_WIDTH),
            ),
            lambda: self.select_target_path(False),
        )

        btn_file_batch = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                'ファイル一括変換',
                object_name='topBtn',
                fixed_width=132,
            ),
            self._open_folder_batch_dialog,
        )

        lay.addWidget(btn_file)
        lay.addWidget(btn_folder)
        lay.addWidget(btn_file_batch)

        self.target_edit = QLineEdit()
        self.target_edit.setObjectName('targetEdit')
        self.target_edit.setPlaceholderText(str(top_bar_plan.get('target_placeholder', 'EPUB / ZIP / CBZ / CBR / RAR / TXT / Markdown / 画像 / フォルダ')))
        self.target_edit.editingFinished.connect(self._update_top_status)
        self.target_edit.editingFinished.connect(self.save_ui_state)
        self.target_edit.editingFinished.connect(self.on_target_editing_finished)
        lay.addWidget(self.target_edit, 1)

        lay.addWidget(self._v_sep())

        self.run_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                top_bar_plan.get('run_button_text', '▶  変換実行'),
                object_name='runBtn',
                fixed_width=top_bar_plan.get('run_button_width', 130),
            ),
            self.start_conversion,
        )
        lay.addWidget(self.run_btn)

        self.stop_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                top_bar_plan.get('stop_button_text', '■  停止'),
                object_name='stopBtn',
                fixed_width=top_bar_plan.get('stop_button_width', 90),
                enabled=False,
            ),
            self.stop_conversion,
        )
        lay.addWidget(self.stop_btn)
        lay.addWidget(self._v_sep())

        self.panel_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                top_bar_plan.get('panel_button_text', '≡'),
                object_name='iconBtn',
                tooltip=top_bar_plan.get('panel_button_tooltip', '左パネルの表示/非表示'),
                fixed_size=top_bar_plan.get('panel_button_size', (36, 36)),
                focus_policy='no_focus',
            ),
            self.toggle_left_panel,
        )
        lay.addWidget(self.panel_btn)

        help_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                top_bar_plan.get('help_button_text', '?'),
                object_name='iconBtn',
                tooltip=top_bar_plan.get('help_button_tooltip', '使い方の流れ'),
                fixed_size=top_bar_plan.get('help_button_size', (36, 36)),
                focus_policy='no_focus',
            ),
            self.show_help_dialog,
        )
        lay.addWidget(help_btn)

        self.settings_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                top_bar_plan.get('settings_button_text', '⚙'),
                object_name='iconBtn',
                tooltip=top_bar_plan.get('settings_button_tooltip', '表示設定'),
                fixed_size=top_bar_plan.get('settings_button_size', (36, 36)),
                focus_policy='no_focus',
            ),
            self.show_display_settings_popup,
        )
        lay.addWidget(self.settings_btn)

        return bar

    @staticmethod
    def _v_sep():
        line = QFrame()
        vline = getattr(QFrame, 'VLine', getattr(QFrame, 'HLine', getattr(QFrame, 'NoFrame', 0)))
        line.setFrameShape(vline)
        line.setObjectName('vSep')
        line.setFixedWidth(1)
        return line

    # ── 左設定パネル ──────────────────────────────────────

    def _build_left_settings(self):
        container_plan = gui_layouts.build_left_settings_container_plan()
        self.left_splitter = QSplitter(Qt.Vertical)
        self.left_splitter.setChildrenCollapsible(
            self._plan_bool_value(container_plan, 'splitter_children_collapsible', False)
        )
        self.left_splitter.setHandleWidth(self._plan_int_value(container_plan, 'splitter_handle_width', 5))

        scroll = QScrollArea()
        scroll.setWidgetResizable(self._plan_bool_value(container_plan, 'scroll_widget_resizable', True))
        scroll.setFrameShape(self._plan_frame_shape_value(container_plan, 'scroll_frame_shape', 'no_frame'))
        scroll.setHorizontalScrollBarPolicy(
            self._plan_scroll_bar_policy_value(container_plan, 'scroll_horizontal_scroll_bar_policy', 'always_off')
        )

        container = QWidget()
        container.setObjectName(str(container_plan.get('container_object_name', 'leftSettingsContainer')))
        self.left_settings_container = container
        self.left_settings_scroll = scroll
        lay = QVBoxLayout(container)
        lay.setContentsMargins(*self._plan_int_tuple_value(container_plan, 'contents_margins', (10, 9, 10, 9), expected_length=4))
        lay.setSpacing(self._plan_int_value(container_plan, 'spacing', 5))
        self._ensure_behavior_controls()
        for section in self._left_settings_sections():
            lay.addWidget(section)
        lay.addWidget(self._build_left_settings_bottom_separator(container_plan))
        scroll.setWidget(container)

        self.bottom_panel = self._build_bottom_panel()
        self.bottom_panel.setMinimumHeight(self._plan_int_value(container_plan, 'bottom_panel_min_height', 92))

        self.left_splitter.addWidget(scroll)
        self.left_splitter.addWidget(self.bottom_panel)
        self.left_splitter.setStretchFactor(
            0, self._plan_int_value(container_plan, 'splitter_top_stretch_factor', 3)
        )
        self.left_splitter.setStretchFactor(
            1, self._plan_int_value(container_plan, 'splitter_bottom_stretch_factor', 1)
        )
        self.left_splitter.setSizes(self._default_left_splitter_sizes())
        return self.left_splitter

    def _build_left_settings_bottom_separator(self: MainWindow, container_plan: Mapping[str, Any]) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(
            self._plan_frame_shape_value(container_plan, 'bottom_separator_frame_shape', 'hline')
        )
        sep.setObjectName(str(container_plan.get('bottom_separator_object_name', 'leftSettingsBottomSep')))
        sep.setFixedHeight(self._plan_int_value(container_plan, 'bottom_separator_height', 1))
        return sep

    def _left_settings_content_height_hint(self: MainWindow) -> int:
        container = getattr(self, 'left_settings_container', None)
        if container is None:
            return 0
        try:
            height = int(container.sizeHint().height())
        except Exception:
            return 0
        return max(0, height)

    def _default_left_splitter_available_height(self: MainWindow) -> int:
        splitter = getattr(self, 'left_splitter', None)
        if splitter is None:
            return 0
        try:
            return max(0, int(splitter.height()))
        except Exception:
            return 0

    def _left_settings_section_factories(self):
        return {
            'preset': self._section_preset,
            'font': self._section_font,
            'image': self._section_image,
            'display': self._section_display,
            'fileviewer': self._section_file_viewer,
            'behavior': self._section_behavior,
        }

    def _left_settings_sections(self):
        factories = self._left_settings_section_factories()
        sections = []
        for section_key in gui_layouts.build_left_settings_section_keys():
            factory = factories.get(str(section_key).strip().lower())
            if factory is not None:
                sections.append(factory())
        return sections

    def _build_section_box_layout(
        self,
        section_key: object,
        fallback_title: str,
        *,
        default_margins: tuple[int, int, int, int],
        default_spacing: int,
    ) -> tuple[QGroupBox, QVBoxLayout, dict[str, Any]]:
        section_plan = gui_layouts.build_left_settings_section_layout_plan(section_key)
        return gui_widget_factory.make_section_box_layout(
            str(section_plan.get('title', fallback_title)),
            section_plan,
            default_margins=default_margins,
            default_spacing=default_spacing,
        )

    # ── 設定セクション：フォントと組版 ────────────────────

    def _section_font(self):
        font_plan = gui_layouts.build_font_section_plan()
        display_plan = gui_layouts.build_display_section_plan()
        box, lay, _section_plan = self._build_section_box_layout(
            'font',
            '出力・フォント・組版',
            default_margins=(8, 12, 8, 7),
            default_spacing=6,
        )

        font_row = self._make_hbox_layout_from_plan()
        self.font_combo = FontPopupTopComboBox()
        self._populate_font_combo()
        self._apply_default_font_selection()
        self.font_combo.currentIndexChanged.connect(self.on_font_changed)
        font_row.addWidget(self.font_combo, 1)
        browse_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                font_plan.get('browse_button_text', '参照'),
                object_name='smallBtn',
            ),
            self.select_font_file,
        )
        font_row.addWidget(browse_btn)
        lay.addLayout(font_row)

        self.font_size_spin = self._spin(18, 72, 26, compact=True, buttons=True)
        self.ruby_size_spin = self._spin(8, 32, 12, compact=True, buttons=True)
        self.line_spacing_spin = self._spin(24, 80, 44, compact=True, buttons=True)
        lay.addLayout(self._spin_row([
            ('本文', self.font_size_spin),
            ('ルビ', self.ruby_size_spin),
            ('行間', self.line_spacing_spin),
        ]))

        self.margin_t_spin = self._spin(0, 80, 12, compact=True, buttons=True)
        self.margin_b_spin = self._spin(0, 80, 14, compact=True, buttons=True)
        self.margin_r_spin = self._spin(0, 80, 12, compact=True, buttons=True)
        self.margin_l_spin = self._spin(0, 80, 12, compact=True, buttons=True)
        lay.addWidget(self._build_margin_rows())

        format_kinsoku_row = self._make_hbox_layout_from_plan(
            gui_layouts.build_row_layout_plan(spacing=font_plan.get('format_kinsoku_row_spacing', 6))
        )
        format_kinsoku_row.addWidget(self._dim_label('出力形式'))
        self.output_format_combo = QComboBox()
        for key, label in OUTPUT_FORMAT_LABELS.items():
            self.output_format_combo.addItem(label, key)
        self.output_format_combo.currentIndexChanged.connect(self._schedule_live_preview_refresh_from_signal)
        self.output_format_combo.currentIndexChanged.connect(lambda _i, self=self: self.save_ui_state())
        format_kinsoku_row.addWidget(self.output_format_combo)
        format_kinsoku_row.addWidget(self._help_icon_button('XTC は 2 階調（白黒）、XTCH は 4 階調（白黒 4 段階）です。通常の白黒表示なら XTC、階調を残したい画像寄りの用途では XTCH を選びます。'))
        format_kinsoku_row.addSpacing(10)

        # sweep366_layout_trial: 機種選択を試験的に「出力形式」と同じ左ペイン行へ移動する。
        # 保存キーと既存ロジック互換のため、ウィジェット名 profile_combo は維持する。
        format_kinsoku_row.addWidget(self._dim_label('機種'))
        self.profile_combo = QComboBox()
        for label, key in tuple(display_plan.get('profile_items', ())):
            self.profile_combo.addItem(str(label), key)
        self.profile_combo.setMinimumWidth(self._plan_int_value(display_plan, 'profile_combo_min_width', 130))
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        format_kinsoku_row.addWidget(self.profile_combo)
        format_kinsoku_row.addWidget(self._help_icon_button('機種を選ぶと解像度が自動設定されます。Custom では手動で幅・高さを指定します。'))
        format_kinsoku_row.addSpacing(10)

        self._ensure_behavior_controls()
        format_kinsoku_row.addWidget(self._dim_label('禁則処理'))
        format_kinsoku_row.addWidget(self.kinsoku_mode_combo)
        format_kinsoku_row.addWidget(self._help_icon_button('オフ: 禁則処理を行わず機械的に流し込みます。簡易: 行頭禁則・行末禁則・句読点のぶら下げのみ行います。標準: 連続約物や閉じ括弧＋句読点のまとまりも含めて、現在の禁則処理を有効にします。'))
        format_kinsoku_row.addStretch(1)
        lay.addLayout(format_kinsoku_row)

        self.profile_hint = QLabel(DEVICE_PROFILES['x4'].tagline)
        self.profile_hint.setObjectName('hintLabel')
        self.profile_hint.setVisible(bool(DEVICE_PROFILES['x4'].tagline))
        lay.addWidget(self.profile_hint)

        for w in [
            self.font_size_spin, self.ruby_size_spin, self.line_spacing_spin,
        ]:
            w.valueChanged.connect(self._schedule_live_preview_refresh_from_signal)
            w.valueChanged.connect(lambda _v, self=self: self.save_ui_state())
        for w in [
            self.margin_t_spin, self.margin_b_spin, self.margin_r_spin, self.margin_l_spin,
        ]:
            w.valueChanged.connect(self.on_margin_changed)
        return box

    def _build_margin_rows(self):
        font_plan = gui_layouts.build_font_section_plan()
        margin_rows_plan = gui_layouts.build_margin_rows_plan(
            row_spacing=font_plan.get('margin_rows_spacing', 2),
            pair_spacing=font_plan.get('margin_pair_spacing', 16),
        )
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(*self._plan_int_tuple_value(margin_rows_plan, 'container_margins', (0, 0, 0, 0), expected_length=4))
        lay.setSpacing(self._plan_int_value(margin_rows_plan, 'row_spacing', 2))

        row_plan = gui_layouts.build_row_layout_plan(
            contents_margins=margin_rows_plan.get('row_contents_margins', (0, 0, 0, 0))
        )
        row1 = self._make_hbox_layout_from_plan(row_plan)
        row1.addWidget(self._dim_label(str(margin_rows_plan.get('top_labels', ('上余白', '下余白'))[0])))
        row1.addWidget(self.margin_t_spin)
        row1.addSpacing(self._plan_int_value(margin_rows_plan, 'pair_spacing', 16))
        row1.addWidget(self._dim_label(str(margin_rows_plan.get('top_labels', ('上余白', '下余白'))[1])))
        row1.addWidget(self.margin_b_spin)
        if self._plan_bool_value(margin_rows_plan, 'trailing_stretch', True):
            row1.addStretch(1)

        row2 = self._make_hbox_layout_from_plan(row_plan)
        row2.addWidget(self._dim_label(str(margin_rows_plan.get('side_labels', ('右余白', '左余白'))[0])))
        row2.addWidget(self.margin_r_spin)
        row2.addSpacing(self._plan_int_value(margin_rows_plan, 'pair_spacing', 16))
        row2.addWidget(self._dim_label(str(margin_rows_plan.get('side_labels', ('右余白', '左余白'))[1])))
        row2.addWidget(self.margin_l_spin)
        if self._plan_bool_value(margin_rows_plan, 'trailing_stretch', True):
            row2.addStretch(1)

        lay.addLayout(row1)
        lay.addLayout(row2)
        return w

    # ── 設定セクション：プレビュー ────────────────────────

    def _section_display(self):
        display_plan = gui_layouts.build_display_section_plan()
        box, lay, _section_plan = self._build_section_box_layout(
            'display',
            'プレビュー',
            default_margins=(8, 14, 8, 8),
            default_spacing=8,
        )

        # sweep363: 実寸近似/ガイドは右ペインの表示ツールバーへ集約する。
        # sweep365: 実寸近似はビュー切替に近い表示状態として、
        # フォントビュー/実機ビューと同系統のチェック可能ボタンにする。
        # 保存キーと既存ロジック互換のため、ウィジェット名自体は維持する。
        preview_toggle_plan = gui_layouts.build_preview_display_toggle_plan()
        self.actual_size_check = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                preview_toggle_plan.get('actual_size_text', '実寸近似'),
                object_name=preview_toggle_plan.get('actual_size_object_name', 'viewToggleBtn'),
                checkable=self._plan_bool_value(preview_toggle_plan, 'actual_size_checkable', True),
                focus_policy=preview_toggle_plan.get('actual_size_focus_policy', 'no_focus'),
            ),
        )
        actual_size_help_text = str(preview_toggle_plan.get('actual_size_help_text', '実寸近似の表示モードです。'))
        self.actual_size_check.setToolTip(actual_size_help_text)
        self.actual_size_help_btn = self._help_icon_button(actual_size_help_text)
        self.actual_size_check.toggled.connect(self.on_actual_size_toggled)

        guide_help_text = str(preview_toggle_plan.get('guide_help_text', 'ガイド表示の切り替えです。'))
        self.guides_check = QCheckBox(str(preview_toggle_plan.get('guide_text', 'ガイド')))
        self.guides_check.setObjectName(str(preview_toggle_plan.get('guide_object_name', 'previewToolbarToggle')))
        self.guides_check.setFocusPolicy(
            self._plan_focus_policy_value(preview_toggle_plan, 'guide_focus_policy', 'no_focus')
        )
        self.guides_check.setToolTip(guide_help_text)
        self.guides_check.setChecked(self._plan_bool_value(preview_toggle_plan, 'guide_checked_default', True))
        self.guides_help_btn = self._help_icon_button(guide_help_text)

        # 旧左ペインの実寸補正UIは、設定互換用に保持するが表示しない。
        self.calib_label = self._dim_label(str(display_plan.get('calibration_label_text', '実寸補正')))
        calibration_button_object_name = str(display_plan.get('calibration_button_object_name', 'stepBtn'))
        self.calib_down_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                display_plan.get('calibration_down_text', '−'),
                object_name=calibration_button_object_name,
                fixed_size=display_plan.get('calibration_button_size', (24, 24)),
            ),
        )
        self.calib_spin = QSpinBox()
        self.calib_spin.setRange(
            self._plan_int_value(display_plan, 'calibration_spin_minimum', 50),
            self._plan_int_value(display_plan, 'calibration_spin_maximum', 300),
        )
        self.calib_spin.setSingleStep(self._plan_int_value(display_plan, 'calibration_spin_step', 5))
        self.calib_spin.setAccelerated(
            self._plan_bool_value(display_plan, 'calibration_spin_accelerated', True)
        )
        self.calib_spin.setButtonSymbols(
            self._plan_spin_button_symbols_value(display_plan, 'calibration_spin_button_symbols', 'no_buttons')
        )
        self.calib_spin.setValue(self._plan_int_value(display_plan, 'calibration_spin_default', 100))
        self.calib_spin.setSuffix(str(display_plan.get('calibration_spin_suffix', '%')))
        self.calib_spin.setFixedWidth(self._plan_int_value(display_plan, 'calibration_spin_width', 62))
        self.calib_spin.valueChanged.connect(self.on_calibration_changed)
        self.calib_up_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                display_plan.get('calibration_up_text', '+'),
                object_name=calibration_button_object_name,
                fixed_size=display_plan.get('calibration_button_size', (24, 24)),
            ),
        )
        self.calib_help_btn = self._help_icon_button(
            str(display_plan.get('calibration_help_text', '実寸補正は右ペインの倍率UIで調整します。'))
        )
        self._sync_legacy_calibration_control_state()

        row3 = self._make_hbox_layout_from_plan()
        self.width_spin = self._spin(240, 2000, 480)
        self.height_spin = self._spin(240, 2000, 800)
        self.custom_size_row = QWidget()
        self.custom_size_row.setVisible(False)
        cs_lay = QHBoxLayout(self.custom_size_row)
        cs_lay.setContentsMargins(*tuple(display_plan.get('custom_size_row_margins', (0, 0, 0, 0))))
        cs_lay.setSpacing(self._plan_int_value(display_plan, 'custom_size_row_spacing', 8))
        cs_lay.addWidget(self._dim_label(str(display_plan.get('custom_width_label', '幅'))))
        cs_lay.addWidget(self.width_spin)
        cs_lay.addSpacing(self._plan_int_value(display_plan, 'custom_size_pair_spacing', 8))
        cs_lay.addWidget(self._dim_label(str(display_plan.get('custom_height_label', '高さ'))))
        cs_lay.addWidget(self.height_spin)
        row3.addWidget(self.custom_size_row)
        row3.addStretch(1)
        lay.addLayout(row3)

        row4 = self._make_hbox_layout_from_plan()
        row4.addWidget(self._dim_label(str(display_plan.get('preview_page_limit_label', '更新対象'))))
        self.preview_page_limit_spin = self._spin(1, 99, DEFAULT_PREVIEW_PAGE_LIMIT, compact=True, buttons=True)
        self.preview_page_limit_spin.setProperty('miniSpinButtons', True)
        self.preview_page_limit_spin.setFixedWidth(self._plan_int_value(display_plan, 'preview_page_limit_width', 68))
        self.preview_page_limit_spin.valueChanged.connect(self._mark_preview_dirty_from_signal)
        self.preview_page_limit_spin.valueChanged.connect(lambda _v, self=self: self.save_ui_state())
        row4.addWidget(self.preview_page_limit_spin)
        page_limit_unit_label = QLabel(str(display_plan.get('preview_page_limit_unit_text', 'ページ')))
        page_limit_unit_label.setObjectName(str(display_plan.get('preview_page_limit_unit_object_name', 'dimLabel')))
        row4.addWidget(page_limit_unit_label)
        self.preview_update_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                display_plan.get('preview_update_button_text', 'プレビュー更新'),
                object_name=display_plan.get('preview_update_button_object_name', 'smallBtn'),
            ),
            self.manual_refresh_preview,
        )
        row4.addWidget(self.preview_update_btn)
        self.preview_refresh_btn = self.preview_update_btn
        self.preview_status_label = QLabel(str(display_plan.get('preview_status_text', '')))
        self.preview_status_label.setObjectName(str(display_plan.get('preview_status_object_name', 'hintLabel')))
        self.preview_status_label.setMinimumWidth(self._plan_int_value(display_plan, 'preview_status_min_width', 260))
        row4.addWidget(self.preview_status_label, 1)
        row4.addSpacing(self._plan_int_value(display_plan, 'preview_status_help_spacing', 4))
        row4.addWidget(self._help_icon_button(str(display_plan.get('preview_update_help_text', 'ファイル読込時にプレビューを自動生成します。文字サイズ・余白・禁則処理・保存形式などの見た目に関わる設定は、操作が止まったタイミングで自動的にプレビューへ反映します。手動で確実に再生成したい場合は［プレビュー更新］を押してください。プレビュー上限を増やすほど確認範囲は広がりますが、読込と再描画は重くなります。'))))
        lay.addLayout(row4)

        self.guides_check.toggled.connect(self.on_guides_toggled)
        self.calib_down_btn.clicked.connect(lambda: self.calib_spin.stepBy(-1))
        self.calib_up_btn.clicked.connect(lambda: self.calib_spin.stepBy(1))
        self.width_spin.valueChanged.connect(self._on_custom_size_changed)
        self.height_spin.valueChanged.connect(self._on_custom_size_changed)
        return box

    # ── 設定セクション：画像処理 ──────────────────────────

    def _section_image(self):
        image_plan = gui_layouts.build_image_section_plan()
        box, lay, _section_plan = self._build_section_box_layout(
            'image',
            '画像処理',
            default_margins=(8, 12, 8, 7),
            default_spacing=5,
        )

        row = self._make_hbox_layout_from_plan()
        self.night_check = QCheckBox(str(image_plan.get('night_mode_text', '白黒反転（出力）')))
        self.night_check.toggled.connect(self.on_night_toggled)
        row.addWidget(self.night_check)
        row.addSpacing(self._plan_int_value(image_plan, 'night_mode_spacing', 16))
        self.dither_check = QCheckBox(str(image_plan.get('dither_text', 'ディザリング')))
        self.dither_check.setChecked(self._plan_bool_value(image_plan, 'dither_checked_default', False))
        self.dither_check.toggled.connect(self.on_dither_toggled)
        row.addWidget(self.dither_check)
        row.addSpacing(self._plan_int_value(image_plan, 'dither_spacing', 16))
        row.addWidget(self._dim_label(str(image_plan.get('threshold_label', 'しきい値'))))
        self.threshold_spin = self._spin(0, 255, 128, compact=True)
        self.threshold_spin.setEnabled(self._plan_bool_value(image_plan, 'threshold_enabled', False))
        self.threshold_spin.valueChanged.connect(self.on_threshold_changed)
        row.addWidget(self.threshold_spin)
        row.addSpacing(self._plan_int_value(image_plan, 'threshold_help_spacing', 6))
        row.addWidget(self._help_icon_button(str(image_plan.get('help_text', '白黒反転（出力）: 白と黒を入れ替えて出力します。プレビューにも反映されます。しきい値: 白と黒の分かれ目を調整します。ディザリング: 粒状感と引き換えに濃淡感を残します。'))))
        if self._plan_bool_value(image_plan, 'trailing_stretch', True):
            row.addStretch(1)
        lay.addLayout(row)

        self._ensure_behavior_controls()
        image_glyph_position_row = self._make_hbox_layout_from_plan(
            gui_layouts.build_row_layout_plan(spacing=image_plan.get('glyph_position_row_spacing', 6))
        )
        image_glyph_position_row.addWidget(self._dim_label('句読点'))
        image_glyph_position_row.addWidget(self.punctuation_position_combo)
        image_glyph_position_row.addWidget(self._help_icon_button('ぶら下がり句読点のみ対象です。下補正 強/弱: 標準より下へ寄せます。標準: これまでと同じ位置で描画します。上補正 弱/強: 標準より上へ寄せます。'))
        image_glyph_position_row.addSpacing(10)
        image_glyph_position_row.addWidget(self._dim_label('漢数字「一」'))
        image_glyph_position_row.addWidget(self.ichi_position_combo)
        image_glyph_position_row.addWidget(self._help_icon_button('文中すべての漢数字「一」が対象です。下補正 強/弱: 標準より下へ寄せます。標準: これまでと同じ位置で描画します。上補正 弱/強: 標準より上へ寄せます。'))
        image_glyph_position_row.addSpacing(10)
        image_glyph_position_row.addWidget(self._dim_label('下鍵括弧'))
        image_glyph_position_row.addWidget(self.lower_closing_bracket_position_combo)
        image_glyph_position_row.addWidget(self._help_icon_button('閉じ鍵括弧（」/﹂）と二重閉じ鍵括弧（』/﹄）のみ対象です。標準: これまでと同じ位置で描画します。上補正 弱/強: 標準より上へ寄せます。'))
        image_glyph_position_row.addStretch(1)
        lay.addLayout(image_glyph_position_row)

        image_wave_dash_row = self._make_hbox_layout_from_plan(
            gui_layouts.build_row_layout_plan(spacing=image_plan.get('wave_dash_row_spacing', 6))
        )
        image_wave_dash_row.addWidget(self._dim_label('波線描画'))
        image_wave_dash_row.addWidget(self.wave_dash_drawing_combo)
        image_wave_dash_row.addWidget(self._help_icon_button('波線系記号（～/〜/〰/~ など）の描画方式です。回転グリフ: フォントの質感を保って90度回転します。別描画: アプリ側で縦波線を描きます。回転グリフに失敗した場合は別描画へ自動フォールバックします。'))
        image_wave_dash_row.addSpacing(10)
        image_wave_dash_row.addWidget(self._dim_label('波線位置'))
        image_wave_dash_row.addWidget(self.wave_dash_position_combo)
        image_wave_dash_row.addWidget(self._help_icon_button('波線系記号の縦位置だけを下方向へ補正します。標準: これまでの位置、下補正弱/強: 標準より下へ寄せます。'))
        image_wave_dash_row.addStretch(1)
        lay.addLayout(image_wave_dash_row)
        return box

    # ── 設定セクション：プリセット ────────────────────────

    def _section_preset(self):
        preset_plan = gui_layouts.build_preset_section_plan(minimum_button_width=104)
        box, lay, section_plan = self._build_section_box_layout(
            'preset',
            'プリセット',
            default_margins=(8, 14, 8, 2),
            default_spacing=4,
        )

        row = self._make_hbox_layout_from_plan()
        row.setSpacing(self._plan_int_value(preset_plan, 'row_spacing', self._plan_int_value(section_plan, 'row_spacing', 8)))
        self.preset_combo = QComboBox()
        for key, p in self.preset_definitions.items():
            self.preset_combo.addItem(p['button_text'], key)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selection_changed)
        row.addWidget(self.preset_combo, 1)

        self.preset_apply_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                preset_plan.get('apply_button_text', 'プリセット適用'),
                object_name=preset_plan.get('button_object_name', 'smallBtn'),
                tooltip=preset_plan.get('apply_tooltip', '選択中のプリセットを現在の組版へ反映'),
            ),
            self.apply_selected_preset,
        )

        self.preset_save_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                preset_plan.get('save_button_text', '組版保存'),
                object_name=preset_plan.get('button_object_name', 'smallBtn'),
                tooltip=preset_plan.get('save_tooltip', '現在の組版設定をこのプリセットへ上書き保存'),
            ),
            self.save_selected_preset,
        )

        preset_button_plan = gui_layouts.build_uniform_button_row_plan(
            [
                self.preset_apply_btn.sizeHint().width(),
                self.preset_save_btn.sizeHint().width(),
            ],
            minimum_width=self._plan_int_value(preset_plan, 'button_min_width', 104),
        )
        preset_button_width = self._plan_int_value(preset_button_plan, 'button_min_width', 104)
        for button in (self.preset_apply_btn, self.preset_save_btn):
            button.setMinimumWidth(preset_button_width)
            row.addWidget(button)
        lay.addLayout(row)

        self.preset_summary_label = QLabel(str(preset_plan.get('summary_text', '')))
        self.preset_summary_label.setObjectName(str(preset_plan.get('summary_label_object_name', 'presetSummaryLabel')))
        self.preset_summary_label.setWordWrap(
            self._plan_bool_value(preset_plan, 'summary_label_word_wrap', True)
        )
        self.preset_summary_label.setAlignment(
            self._plan_alignment_value(preset_plan, 'summary_label_alignment', 'left_top')
        )
        self.preset_summary_label.setContentsMargins(0, 0, 0, 0)
        self.preset_summary_label.setMargin(0)
        set_indent = getattr(self.preset_summary_label, 'setIndent', None)
        if callable(set_indent):
            set_indent(0)
        set_text_format = getattr(self.preset_summary_label, 'setTextFormat', None)
        if callable(set_text_format):
            set_text_format(Qt.PlainText)
        lay.addWidget(self.preset_summary_label)
        return box

    def _ensure_behavior_controls(self):
        if hasattr(self, 'open_folder_check'):
            return
        behavior_plan = gui_layouts.build_behavior_section_plan()
        self.open_folder_check = QCheckBox(str(behavior_plan.get('open_folder_text', '完了後フォルダを開く')))
        self.open_folder_check.setChecked(self._plan_bool_value(behavior_plan, 'open_folder_checked_default', True))
        self.open_folder_check.toggled.connect(self.save_ui_state)

        self.kinsoku_mode_combo = QComboBox()
        for key, label in KINSOKU_MODE_OPTIONS:
            self.kinsoku_mode_combo.addItem(label, key)
        self.kinsoku_mode_combo.currentIndexChanged.connect(self._on_kinsoku_mode_changed)

        self.punctuation_position_combo = QComboBox()
        for key, label in GLYPH_POSITION_MODE_OPTIONS:
            self.punctuation_position_combo.addItem(label, key)
        self.punctuation_position_combo.currentIndexChanged.connect(self._on_glyph_position_mode_changed)

        self.ichi_position_combo = QComboBox()
        for key, label in GLYPH_POSITION_MODE_OPTIONS:
            self.ichi_position_combo.addItem(label, key)
        self.ichi_position_combo.currentIndexChanged.connect(self._on_glyph_position_mode_changed)

        self.lower_closing_bracket_position_combo = QComboBox()
        for key, label in CLOSING_BRACKET_POSITION_MODE_OPTIONS:
            self.lower_closing_bracket_position_combo.addItem(label, key)
        self.lower_closing_bracket_position_combo.currentIndexChanged.connect(self._on_glyph_position_mode_changed)

        self.wave_dash_drawing_combo = QComboBox()
        for key, label in WAVE_DASH_DRAWING_MODE_OPTIONS:
            self.wave_dash_drawing_combo.addItem(label, key)
        self.wave_dash_drawing_combo.currentIndexChanged.connect(self._on_wave_dash_mode_changed)

        self.wave_dash_position_combo = QComboBox()
        for key, label in WAVE_DASH_POSITION_MODE_OPTIONS:
            self.wave_dash_position_combo.addItem(label, key)
        self.wave_dash_position_combo.currentIndexChanged.connect(self._on_wave_dash_mode_changed)

        self.output_conflict_combo = QComboBox()
        for key, label in OUTPUT_CONFLICT_OPTIONS:
            self.output_conflict_combo.addItem(label, key)
        self.output_conflict_combo.currentIndexChanged.connect(lambda _i, self=self: self.save_ui_state())

    # ── 設定セクション：その他オプション ────────────────────────

    def _section_behavior(self):
        behavior_plan = gui_layouts.build_behavior_section_plan()
        box, lay, _section_plan = self._build_section_box_layout(
            'behavior',
            'その他オプション',
            default_margins=(8, 14, 8, 8),
            default_spacing=6,
        )

        self._ensure_behavior_controls()

        row1 = self._make_hbox_layout_from_plan()
        row1.addWidget(self.open_folder_check)
        if self._plan_bool_value(behavior_plan, 'open_folder_row_stretch', True):
            row1.addStretch(1)
        lay.addLayout(row1)

        row2 = self._make_hbox_layout_from_plan()
        row2.addWidget(self._dim_label(str(behavior_plan.get('output_conflict_label', '同名出力'))))
        row2.addWidget(self.output_conflict_combo, 1)
        row2.addWidget(self._help_icon_button(str(behavior_plan.get('output_conflict_help_text', '保存先に同名の .xtc / .xtch があるときの動作を選びます。自動連番: foo(1).xtc 形式で保存 / 上書き: 既存ファイルを置き換え / エラー: そのファイルを保存せずエラーとして記録します。'))))
        lay.addLayout(row2)
        return box

    def _section_file_viewer(self):
        file_viewer_plan = gui_layouts.build_file_viewer_section_plan()
        box, lay, _section_plan = self._build_section_box_layout(
            'fileviewer',
            'ファイルビューワー',
            default_margins=(8, 10, 8, 8),
            default_spacing=6,
        )

        row = self._make_hbox_layout_from_plan()
        self.open_xtc_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                file_viewer_plan.get('open_xtc_button_text', 'XTC/XTCHを開く'),
                object_name=file_viewer_plan.get('open_xtc_button_object_name', 'smallBtn'),
            ),
            self.open_xtc_file,
        )
        row.addWidget(self.open_xtc_btn)
        if self._plan_bool_value(file_viewer_plan, 'open_xtc_trailing_stretch', True):
            row.addStretch(1)
        row.addWidget(self._help_icon_button(
            file_viewer_plan.get(
                'open_xtc_help_text',
                '既存の .xtc / .xtch ファイルを右ペインの実機ビューへ読み込んで確認します。',
            )
        ))
        lay.addLayout(row)
        return box

    # ── 右プレビューパネル ────────────────────────────────

    def _build_right_preview(self):
        preview_panel_plan = gui_layouts.build_right_preview_panel_plan()
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(*tuple(preview_panel_plan.get('panel_contents_margins', (0, 0, 0, 0))))
        lay.setSpacing(self._plan_int_value(preview_panel_plan, 'panel_spacing', 0))

        lay.addWidget(self._build_view_toggle_bar())

        self.preview_stack = QStackedWidget()

        font_page = QWidget()
        fl = QVBoxLayout(font_page)
        fl.setContentsMargins(*tuple(preview_panel_plan.get('font_page_margins', (8, 8, 8, 8))))
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(
            self._plan_bool_value(preview_panel_plan, 'font_scroll_widget_resizable', False)
        )
        self.preview_scroll.setAlignment(
            self._plan_alignment_value(preview_panel_plan, 'font_scroll_alignment', 'center')
        )
        self.preview_scroll.setFrameShape(
            self._plan_frame_shape_value(preview_panel_plan, 'font_scroll_frame_shape', 'no_frame')
        )
        self.preview_label = QLabel()
        self.preview_label.setAlignment(
            self._plan_alignment_value(preview_panel_plan, 'font_preview_alignment', 'center')
        )
        self.preview_label.setMinimumSize(*self._plan_int_tuple_value(preview_panel_plan, 'font_preview_min_size', (360, 600), expected_length=2))
        self.preview_label.setWordWrap(self._plan_bool_value(preview_panel_plan, 'font_preview_word_wrap', True))
        self.preview_scroll.setWidget(self.preview_label)
        fl.addWidget(self.preview_scroll)
        self.preview_stack.addWidget(font_page)

        device_page = QWidget()
        dl = QVBoxLayout(device_page)
        dl.setContentsMargins(*self._plan_int_tuple_value(preview_panel_plan, 'device_page_margins', (8, 8, 8, 8), expected_length=4))
        self.viewer_scroll = QScrollArea()
        self.viewer_scroll.setWidgetResizable(
            self._plan_bool_value(preview_panel_plan, 'device_scroll_widget_resizable', False)
        )
        self.viewer_scroll.setAlignment(
            self._plan_alignment_value(preview_panel_plan, 'device_scroll_alignment', 'center')
        )
        self.viewer_scroll.setFrameShape(
            self._plan_frame_shape_value(preview_panel_plan, 'device_scroll_frame_shape', 'no_frame')
        )
        self.viewer_scroll.setFocusPolicy(
            self._plan_focus_policy_value(preview_panel_plan, 'device_scroll_focus_policy', 'strong_focus')
        )
        self.viewer_widget = XtcViewerWidget()
        self.viewer_widget.setMinimumSize(*self._plan_int_tuple_value(preview_panel_plan, 'device_preview_min_size', (360, 600), expected_length=2))
        self.viewer_scroll.setWidget(self.viewer_widget)
        dl.addWidget(self.viewer_scroll)
        self.preview_stack.addWidget(device_page)

        lay.addWidget(self.preview_stack, 1)

        self.preview_stack.setCurrentIndex(self._plan_int_value(preview_panel_plan, 'preview_stack_index', 0))
        self._sync_preview_size()
        return panel

    def _build_view_toggle_bar(self):
        toggle_plan = gui_layouts.build_view_toggle_bar_plan()
        bar = QFrame()
        bar.setObjectName(str(toggle_plan.get('object_name', 'viewToggleBar')))
        bar.setFixedHeight(self._plan_int_value(toggle_plan, 'bar_height', 88))
        outer_lay = QVBoxLayout(bar)
        outer_lay.setContentsMargins(*self._plan_int_tuple_value(toggle_plan, 'contents_margins', (12, 4, 12, 4), expected_length=4))
        outer_lay.setSpacing(self._plan_int_value(toggle_plan, 'row_spacing', 2))

        top_lay = QHBoxLayout()
        top_lay.setContentsMargins(*self._plan_int_tuple_value(toggle_plan, 'top_row_contents_margins', (0, 0, 0, 0), expected_length=4))
        top_lay.setSpacing(self._plan_int_value(toggle_plan, 'spacing', 6))

        self.font_view_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                toggle_plan.get('font_view_text', 'フォントビュー'),
                object_name=str(toggle_plan.get('view_button_object_name', 'viewToggleBtn')),
                checkable=self._plan_bool_value(toggle_plan, 'view_button_checkable', True),
                checked=self._plan_bool_value(toggle_plan, 'font_view_checked_default', True),
                focus_policy=str(toggle_plan.get('view_button_focus_policy', 'no_focus')),
            ),
            lambda: self.set_main_view_mode('font'),
        )

        self.device_view_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                toggle_plan.get('device_view_text', '実機ビュー'),
                object_name=str(toggle_plan.get('view_button_object_name', 'viewToggleBtn')),
                checkable=self._plan_bool_value(toggle_plan, 'view_button_checkable', True),
                checked=self._plan_bool_value(toggle_plan, 'device_view_checked_default', False),
                focus_policy=str(toggle_plan.get('view_button_focus_policy', 'no_focus')),
            ),
            lambda: self.set_main_view_mode('device'),
        )

        top_lay.addWidget(self.font_view_btn)
        top_lay.addWidget(self.device_view_btn)

        self.view_help_btn = self._help_icon_button(self._preview_view_help_text())
        top_lay.addWidget(self.view_help_btn)
        top_lay.addSpacing(self._plan_int_value(toggle_plan, 'display_toggle_spacing', 10))
        self._add_preview_display_toggles_to_layout(top_lay)
        top_lay.addStretch(1)
        outer_lay.addLayout(top_lay)

        sep = QFrame()
        sep.setFrameShape(self._qframe_shape_constant('HLine', self._qframe_shape_constant('NoFrame', 0)))
        sep.setObjectName(str(toggle_plan.get('top_separator_object_name', 'topSep')))
        outer_lay.addWidget(sep)

        bottom_lay = QHBoxLayout()
        bottom_lay.setContentsMargins(*self._plan_int_tuple_value(toggle_plan, 'bottom_row_contents_margins', (0, 0, 0, 0), expected_length=4))
        bottom_lay.setSpacing(self._plan_int_value(toggle_plan, 'bottom_row_spacing', self._plan_int_value(toggle_plan, 'spacing', 6)))
        self._add_nav_controls_to_layout(bottom_lay, current_label_stretch=0)
        self._add_preview_zoom_controls_to_layout(bottom_lay, toggle_plan=toggle_plan)
        bottom_lay.addStretch(1)
        outer_lay.addLayout(bottom_lay)
        return bar

    def _add_preview_display_toggles_to_layout(self, lay: QHBoxLayout) -> None:
        """右ペイン表示ツールバーへ表示系トグルを配置する。"""
        self._add_optional_widget_to_layout(lay, 'actual_size_check')
        self._add_optional_widget_to_layout(lay, 'actual_size_help_btn')
        preview_toggle_plan = gui_layouts.build_preview_display_toggle_plan()
        lay.addSpacing(self._plan_int_value(preview_toggle_plan, 'toggle_spacing', 18))
        self._add_optional_widget_to_layout(lay, 'guides_check')
        self._add_optional_widget_to_layout(lay, 'guides_help_btn')

    def _build_nav_bar(self):
        nav_bar_plan = gui_layouts.build_nav_bar_plan()
        bar = QFrame()
        bar.setObjectName(str(nav_bar_plan.get('object_name', 'navBar')))
        bar.setFixedHeight(self._plan_int_value(nav_bar_plan, 'bar_height', 48))
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(*self._plan_int_tuple_value(nav_bar_plan, 'contents_margins', (12, 0, 12, 0), expected_length=4))
        lay.setSpacing(self._plan_int_value(nav_bar_plan, 'spacing', 8))
        self._add_nav_controls_to_layout(lay, nav_bar_plan=nav_bar_plan, current_label_stretch=1)
        return bar

    def _add_nav_controls_to_layout(self, lay: QHBoxLayout, *, nav_bar_plan: dict | None = None, current_label_stretch: int = 0) -> None:
        nav_bar_plan = nav_bar_plan or gui_layouts.build_nav_bar_plan()

        self.current_xtc_label = QLabel(str(nav_bar_plan.get('current_xtc_label_text', '表示中: なし')))
        self.current_xtc_label.setObjectName(str(nav_bar_plan.get('current_xtc_label_object_name', 'hintLabel')))
        self.current_xtc_label.setMinimumWidth(self._plan_int_value(nav_bar_plan, 'current_xtc_label_min_width', 0))
        self.current_xtc_label.setMaximumWidth(self._plan_int_value(nav_bar_plan, 'current_xtc_label_max_width', 220))
        lay.addWidget(self.current_xtc_label, current_label_stretch)

        self.nav_reverse_check = QCheckBox(str(nav_bar_plan.get('nav_reverse_text', 'ボタン反転')))
        self.nav_reverse_check.setObjectName(str(nav_bar_plan.get('nav_reverse_object_name', 'navToggle')))
        self.nav_reverse_check.setFocusPolicy(
            self._plan_focus_policy_value(nav_bar_plan, 'nav_reverse_focus_policy', 'no_focus')
        )
        self.nav_reverse_check.toggled.connect(self.on_nav_reverse_toggled)
        lay.addWidget(self.nav_reverse_check)
        lay.addWidget(self._nav_section_separator(nav_bar_plan))
        lay.addSpacing(self._plan_int_value(nav_bar_plan, 'nav_button_side_spacing', 10))

        self.prev_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                nav_bar_plan.get('prev_button_text', '前'),
                object_name=str(nav_bar_plan.get('nav_button_object_name', 'navBtn')),
                focus_policy=str(nav_bar_plan.get('nav_button_focus_policy', 'no_focus')),
            ),
            lambda: self.on_nav_button_clicked(-1),
        )
        lay.addWidget(self.prev_btn)

        lay.addWidget(self._dim_label(str(nav_bar_plan.get('page_label_text', 'ページ'))))
        self.page_input = QSpinBox()
        self.page_input.setRange(
            self._plan_int_value(nav_bar_plan, 'page_input_minimum', 0),
            self._plan_int_value(nav_bar_plan, 'page_input_maximum', 0),
        )
        self.page_input.setButtonSymbols(
            self._plan_spin_button_symbols_value(nav_bar_plan, 'page_input_button_symbols', 'no_buttons')
        )
        self.page_input.setKeyboardTracking(
            self._plan_bool_value(nav_bar_plan, 'page_input_keyboard_tracking', False)
        )
        self.page_input.setFixedWidth(self._plan_int_value(nav_bar_plan, 'page_input_width', 60))
        self.page_input.valueChanged.connect(self.on_page_input_changed)
        lay.addWidget(self.page_input)

        self.page_total_label = QLabel(str(nav_bar_plan.get('page_total_label_text', '/ 0')))
        self.page_total_label.setObjectName(str(nav_bar_plan.get('page_total_label_object_name', 'hintLabel')))
        lay.addWidget(self.page_total_label)

        self.next_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                nav_bar_plan.get('next_button_text', '次'),
                object_name=str(nav_bar_plan.get('nav_button_object_name', 'navBtn')),
                focus_policy=str(nav_bar_plan.get('nav_button_focus_policy', 'no_focus')),
            ),
            lambda: self.on_nav_button_clicked(1),
        )
        lay.addWidget(self.next_btn)
        lay.addSpacing(self._plan_int_value(nav_bar_plan, 'nav_button_side_spacing', 10))
        lay.addWidget(self._nav_section_separator(nav_bar_plan))

        self._update_nav_button_texts()

    def _nav_section_separator(self, nav_bar_plan: Mapping[str, Any]) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(self._qframe_shape_constant('VLine', self._qframe_shape_constant('NoFrame', 0)))
        sep.setObjectName(str(nav_bar_plan.get('nav_section_separator_object_name', 'navSectionSep')))
        return sep

    def _add_preview_zoom_controls_to_layout(self, lay: QHBoxLayout, *, toggle_plan: dict | None = None) -> None:
        toggle_plan = toggle_plan or gui_layouts.build_view_toggle_bar_plan()
        lay.addSpacing(self._plan_int_value(toggle_plan, 'preview_zoom_spacing', 8))
        self.preview_zoom_label = self._dim_label(str(toggle_plan.get('preview_zoom_label_text', '表示倍率')))
        lay.addWidget(self.preview_zoom_label)
        preview_zoom_button_object_name = str(toggle_plan.get('preview_zoom_button_object_name', 'stepBtn'))
        self.preview_zoom_down_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                toggle_plan.get('preview_zoom_down_text', '−'),
                object_name=preview_zoom_button_object_name,
                fixed_size=toggle_plan.get('preview_zoom_button_size', (24, 24)),
            ),
        )
        lay.addWidget(self.preview_zoom_down_btn)
        self.preview_zoom_spin = QSpinBox()
        self.preview_zoom_spin.setRange(
            self._plan_int_value(toggle_plan, 'preview_zoom_min', 50),
            self._plan_int_value(toggle_plan, 'preview_zoom_max', 300),
        )
        self.preview_zoom_spin.setSingleStep(self._plan_int_value(toggle_plan, 'preview_zoom_step', 10))
        self.preview_zoom_spin.setAccelerated(
            self._plan_bool_value(toggle_plan, 'preview_zoom_spin_accelerated', True)
        )
        self.preview_zoom_spin.setButtonSymbols(
            self._plan_spin_button_symbols_value(toggle_plan, 'preview_zoom_spin_button_symbols', 'no_buttons')
        )
        self.preview_zoom_spin.setValue(self._plan_int_value(toggle_plan, 'preview_zoom_default', 100))
        self.preview_zoom_spin.setSuffix(str(toggle_plan.get('preview_zoom_spin_suffix', '%')))
        self.preview_zoom_spin.setFixedWidth(self._plan_int_value(toggle_plan, 'preview_zoom_spin_width', 78))
        self.preview_zoom_spin.setToolTip(str(toggle_plan.get('preview_zoom_tooltip', '表示倍率です。')))
        self.preview_zoom_spin.valueChanged.connect(self.on_preview_zoom_changed)
        lay.addWidget(self.preview_zoom_spin)
        self.preview_zoom_up_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(
                toggle_plan.get('preview_zoom_up_text', '+'),
                object_name=preview_zoom_button_object_name,
                fixed_size=toggle_plan.get('preview_zoom_button_size', (24, 24)),
            ),
        )
        lay.addWidget(self.preview_zoom_up_btn)
        self.preview_zoom_down_btn.clicked.connect(lambda: self.preview_zoom_spin.stepBy(-1))
        self.preview_zoom_up_btn.clicked.connect(lambda: self.preview_zoom_spin.stepBy(1))
        self._sync_preview_zoom_control_state()

    # ── 下部パネル（ステータス + 結果/ログ）────────────────

    def _build_bottom_panel(self):
        bottom_panel_plan = gui_layouts.build_bottom_panel_layout_plan()
        panel = QFrame()
        panel.setObjectName(str(bottom_panel_plan.get('panel_object_name', 'bottomPanel')))
        outer_lay = QHBoxLayout(panel)
        outer_lay.setContentsMargins(*self._plan_int_tuple_value(bottom_panel_plan, 'panel_contents_margins', (0, 0, 0, 0), expected_length=4))
        outer_lay.setSpacing(self._plan_int_value(bottom_panel_plan, 'panel_spacing', 0))

        content = QFrame()
        content.setObjectName(str(bottom_panel_plan.get('content_object_name', 'bottomPanelContent')))
        lay = QVBoxLayout(content)
        lay.setContentsMargins(*self._plan_int_tuple_value(bottom_panel_plan, 'content_contents_margins', (0, 0, 0, 0), expected_length=4))
        lay.setSpacing(self._plan_int_value(bottom_panel_plan, 'content_spacing', 0))

        strip = QFrame()
        strip.setObjectName(str(bottom_panel_plan.get('status_strip_object_name', 'statusStrip')))
        strip.setFixedHeight(self._plan_int_value(bottom_panel_plan, 'status_strip_height', 34))
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(*self._plan_int_tuple_value(bottom_panel_plan, 'status_strip_margins', (14, 0, 14, 0), expected_length=4))
        sl.setSpacing(self._plan_int_value(bottom_panel_plan, 'status_strip_spacing', 10))

        status_strip_plan = gui_layouts.build_bottom_status_strip_plan()

        self.busy_badge = QLabel(str(status_strip_plan.get('badge_text', '待機中')))
        self.busy_badge.setObjectName(str(status_strip_plan.get('badge_object_name', 'badge')))
        sl.addWidget(self.busy_badge)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(
            self._plan_int_value(status_strip_plan, 'progress_minimum', 0),
            self._plan_int_value(status_strip_plan, 'progress_maximum', 1),
        )
        self.progress_bar.setValue(self._plan_int_value(status_strip_plan, 'progress_value', 0))
        self.progress_bar.setTextVisible(self._plan_bool_value(status_strip_plan, 'progress_text_visible', False))
        self.progress_bar.setFixedHeight(self._plan_int_value(status_strip_plan, 'progress_fixed_height', 6))
        self.progress_bar.setMaximumWidth(self._plan_int_value(status_strip_plan, 'progress_max_width', 200))
        sl.addWidget(self.progress_bar)

        self.progress_label = QLabel(str(status_strip_plan.get('progress_text', '待機中です。')))
        self.progress_label.setObjectName(str(status_strip_plan.get('progress_label_object_name', 'hintLabel')))
        sl.addWidget(self.progress_label, 1)

        lay.addWidget(strip)

        sep = QFrame()
        sep.setFrameShape(self._plan_frame_shape_value(bottom_panel_plan, 'bottom_separator_frame_shape', 'hline'))
        sep.setObjectName(str(bottom_panel_plan.get('bottom_separator_object_name', 'bottomPanelSep')))
        lay.addWidget(sep)

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self._build_results_tab(), str(bottom_panel_plan.get('results_tab_title', '変換結果')))
        self.bottom_tabs.addTab(self._build_log_tab(), str(bottom_panel_plan.get('log_tab_title', 'ログ')))
        self.bottom_tabs.currentChanged.connect(lambda _index: self._bind_bottom_panel_external_scrollbar())
        lay.addWidget(self.bottom_tabs, 1)

        outer_lay.addWidget(content, 1)
        self.bottom_panel_scrollbar = QScrollBar(Qt.Vertical)
        self.bottom_panel_scrollbar.setObjectName(
            str(bottom_panel_plan.get('external_scrollbar_object_name', 'bottomPanelScrollBar'))
        )
        self.bottom_panel_scrollbar.setSingleStep(
            self._plan_int_value(bottom_panel_plan, 'external_scrollbar_single_step', 20)
        )
        self.bottom_panel_scrollbar.valueChanged.connect(self._apply_bottom_panel_external_scroll_value)
        outer_lay.addWidget(self.bottom_panel_scrollbar, 0)
        self._bind_bottom_panel_external_scrollbar()
        return panel

    def _build_results_tab(self):
        results_tab_plan = gui_layouts.build_results_tab_plan()
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(*self._plan_int_tuple_value(results_tab_plan, 'contents_margins', (6, 6, 6, 6), expected_length=4))
        lay.setSpacing(self._plan_int_value(results_tab_plan, 'spacing', 4))
        self.results_summary_label = QLabel(str(results_tab_plan.get('summary_text', '変換結果の概要をここに表示します。')))
        self.results_summary_label.setObjectName(str(results_tab_plan.get('summary_label_object_name', 'hintLabel')))
        self.results_summary_label.setWordWrap(self._plan_bool_value(results_tab_plan, 'summary_label_word_wrap', True))
        lay.addWidget(self.results_summary_label, 0)

        self.results_list = QListWidget()
        self.results_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.results_list.setSelectionMode(
            self._plan_list_selection_mode_value(results_tab_plan, 'results_list_selection_mode', 'single_selection')
        )
        self.results_list.itemClicked.connect(self.on_result_item_clicked)
        self.results_list.itemActivated.connect(self.on_result_item_clicked)
        lay.addWidget(self.results_list, 1)
        return w

    def _build_log_tab(self):
        log_tab_plan = gui_layouts.build_log_tab_plan(log_path=_resolve_session_log_path())
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(*self._plan_int_tuple_value(log_tab_plan, 'contents_margins', (6, 6, 6, 6), expected_length=4))
        lay.setSpacing(self._plan_int_value(log_tab_plan, 'spacing', 6))

        top = QHBoxLayout()
        top.setContentsMargins(*self._plan_int_tuple_value(log_tab_plan, 'top_row_margins', (0, 0, 0, 0), expected_length=4))
        top.setSpacing(self._plan_int_value(log_tab_plan, 'top_row_spacing', 8))
        label = QLabel(str(log_tab_plan.get('path_label_text', '保存先:')))
        label.setObjectName(str(log_tab_plan.get('path_label_object_name', 'logPathLabel')))
        top.addWidget(label, 0)

        self.log_path_edit = QLineEdit(str(log_tab_plan.get('log_path', str(_resolve_session_log_path()))))
        log_path_read_only = self._plan_bool_value(log_tab_plan, 'log_path_edit_read_only', True)
        self.log_path_edit.setReadOnly(log_path_read_only)
        top.addWidget(self.log_path_edit, 1)

        open_btn = self._make_button_from_plan(
            gui_layouts.build_button_widget_plan(log_tab_plan.get('open_folder_button_text', 'ログフォルダを開く')),
            self.open_log_folder,
        )
        top.addWidget(open_btn, 0)
        lay.addLayout(top)

        self.log_edit = QTextEdit()
        self.log_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.log_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        log_edit_read_only = self._plan_bool_value(log_tab_plan, 'log_edit_read_only', True)
        self.log_edit.setReadOnly(log_edit_read_only)
        lay.addWidget(self.log_edit, 1)
        return w


    def _active_bottom_panel_scrollbar(self: MainWindow) -> object | None:
        tabs = getattr(self, 'bottom_tabs', None)
        try:
            index = int(tabs.currentIndex()) if tabs is not None else 0
        except Exception:
            index = 0
        if index == 1:
            widget = getattr(self, 'log_edit', None)
        else:
            widget = getattr(self, 'results_list', None)
        if widget is None or not hasattr(widget, 'verticalScrollBar'):
            return None
        try:
            return widget.verticalScrollBar()
        except Exception:
            return None

    def _bind_bottom_panel_external_scrollbar(self: MainWindow) -> None:
        external = getattr(self, 'bottom_panel_scrollbar', None)
        if external is None:
            return
        source = self._active_bottom_panel_scrollbar()
        previous = getattr(self, '_bottom_panel_bound_scrollbar', None)
        if previous is not None and previous is not source:
            for signal_name in ('rangeChanged', 'valueChanged'):
                signal = getattr(previous, signal_name, None)
                if signal is None:
                    continue
                try:
                    signal.disconnect(self._sync_bottom_panel_external_scrollbar)
                except Exception:
                    pass
        if source is None:
            self._bottom_panel_bound_scrollbar = None
            self._set_bottom_panel_external_scrollbar_range(0, 0, 0, 0, 0)
            return
        if previous is not source:
            for signal_name in ('rangeChanged', 'valueChanged'):
                signal = getattr(source, signal_name, None)
                if signal is None:
                    continue
                try:
                    signal.connect(self._sync_bottom_panel_external_scrollbar)
                except Exception:
                    pass
            self._bottom_panel_bound_scrollbar = source
        self._sync_bottom_panel_external_scrollbar()

    def _set_bottom_panel_external_scrollbar_range(
        self: MainWindow,
        minimum: int,
        maximum: int,
        value: int,
        page_step: int,
        single_step: int,
    ) -> None:
        external = getattr(self, 'bottom_panel_scrollbar', None)
        if external is None:
            return
        self._bottom_panel_scrollbar_syncing = True
        try:
            external.blockSignals(True)
            external.setRange(max(0, int(minimum)), max(0, int(maximum)))
            external.setPageStep(max(1, int(page_step or 1)))
            external.setSingleStep(max(1, int(single_step or 1)))
            external.setValue(max(external.minimum(), min(external.maximum(), int(value))))
            external.setEnabled(external.maximum() > external.minimum())
        finally:
            try:
                external.blockSignals(False)
            except Exception:
                pass
            self._bottom_panel_scrollbar_syncing = False

    def _sync_bottom_panel_external_scrollbar(self: MainWindow, *_args: object) -> None:
        if bool(getattr(self, '_bottom_panel_scrollbar_syncing', False)):
            return
        source = self._active_bottom_panel_scrollbar()
        if source is None:
            self._set_bottom_panel_external_scrollbar_range(0, 0, 0, 0, 0)
            return
        try:
            minimum = int(source.minimum())
            maximum = int(source.maximum())
            value = int(source.value())
            page_step = int(source.pageStep())
            single_step = int(source.singleStep())
        except Exception:
            self._set_bottom_panel_external_scrollbar_range(0, 0, 0, 0, 0)
            return
        self._set_bottom_panel_external_scrollbar_range(minimum, maximum, value, page_step, single_step)

    def _apply_bottom_panel_external_scroll_value(self: MainWindow, value: int) -> None:
        if bool(getattr(self, '_bottom_panel_scrollbar_syncing', False)):
            return
        source = self._active_bottom_panel_scrollbar()
        if source is None:
            return
        self._bottom_panel_scrollbar_syncing = True
        try:
            try:
                source.setValue(int(value))
            except Exception:
                pass
        finally:
            self._bottom_panel_scrollbar_syncing = False
        self._sync_bottom_panel_external_scrollbar()

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

    def _help_icon_button(self, text: str, *, tooltip: str | None = None) -> QPushButton:
        return gui_widget_factory.make_help_icon_button(
            text,
            tooltip=tooltip,
            clicked_with_button=lambda button, self=self: self._show_inline_help(button),
            no_focus_policy=Qt.NoFocus,
        )

    def _show_inline_help(self, button: QPushButton):
        text = str(button.property('helpText') or '').strip()
        if not text:
            return
        try:
            msg = QMessageBox(self)
            msg.setWindowTitle('説明')
            msg.setIcon(QMessageBox.Information)
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
        title_row.addWidget(self._help_icon_button('1. ファイルを開く → 2. プリセットを選ぶ → 3. 必要なら微調整 → 4. 変換実行 → 5. 実機ビューで確認'))
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
        stylesheet = """
        /* ── ベース ── */
        QMainWindow, QWidget {
            background: #F4F7FB;
            color: #243648;
            font-family: 'Meiryo', 'Yu Gothic UI', sans-serif;
            font-size: 15px;
        }

        /* ── トップバー ── */
        QFrame#topBar {
            background: #FFFFFF;
            border: none;
        }
        QFrame#vSep { background: #D5E0EB; }
        QFrame#topSep { background: #DDE6EF; border: none; max-height: 1px; }
        QFrame#leftSettingsBottomSep { background: #DDE6EF; border: none; max-height: 1px; }
        QFrame#bottomPanelSep { background: #DDE6EF; border: none; max-height: 1px; }

        QLabel#appTitle {
            font-size: 17px;
            font-weight: 700;
            color: #1F3A56;
            letter-spacing: 0.5px;
        }

        QLineEdit#targetEdit {
            background: #FFFFFF;
            border: 1px solid #C9D6E3;
            border-radius: 8px;
            padding: 6px 10px;
            color: #2B4056;
        }
        QLineEdit#targetEdit:focus { border-color: #77AEEB; }

        QPushButton#topBtn {
            background: #FFFFFF;
            border: 1px solid #C8D6E5;
            border-radius: 8px;
            padding: 5px 10px;
            color: #335A82;
            font-size: 14px;
        }
        QPushButton#topBtn:hover { background: #EEF5FC; }

        QPushButton#runBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4F8FEF, stop:1 #69B8FF);
            border: none;
            border-radius: 8px;
            color: #F9FCFF;
            font-weight: 700;
            font-size: 15px;
            letter-spacing: 0.3px;
        }
        QPushButton#runBtn:hover { background: #5B9CF4; }
        QPushButton#runBtn:disabled { background: #D5DEE8; color: #7C8B99; }

        QPushButton#stopBtn {
            background: #FFF5F2;
            border: 1px solid #EDC2BA;
            border-radius: 8px;
            color: #C15A48;
            font-size: 14px;
        }
        QPushButton#stopBtn:hover { background: #FFEAE4; }
        QPushButton#stopBtn:disabled {
            background: #EEF2F6;
            color: #9AA7B3;
            border-color: #D6DEE6;
        }

        QPushButton#iconBtn {
            background: #FFFFFF;
            border: 1px solid #C8D6E5;
            border-radius: 8px;
            color: #7B95AC;
            font-size: 18px;
            font-weight: 700;
        }
        QPushButton#iconBtn:hover { background: #EEF5FC; color: #3E607F; }

        /* ── 設定パネル ── */
        QScrollBar:vertical {
            background: #E9EFF5;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #C6D4E2;
            min-height: 24px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover { background: #B5C7D8; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

        QGroupBox#settingsSection {
            background: #FFFFFF;
            border: 1px solid #D6E0EA;
            border-radius: 10px;
            margin-top: 0;
            padding-top: 14px;
            font-size: 14px;
            font-weight: 700;
            color: #6D89A6;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }
        QGroupBox#settingsSection::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 10px;
            top: 6px;
            background: #FFFFFF;
        }

        QLabel#dimLabel { color: #5E7893; font-size: 14px; }
        QLabel#hintLabel { color: #788FA4; font-size: 13px; }
        QLabel#presetSummaryLabel { color: #275C9A; font-size: 15px; font-weight: 400; }
        QLabel#subNoteLabel { color: #4F6982; font-size: 12px; line-height: 1.35em; }
        QLabel#flowGuideTitle { color: #1F3D5A; font-size: 13px; font-weight: 700; }
        QLabel#flowGuideText { color: #3E5771; font-size: 12px; }
        QLabel#viewRoleLabel { color: #163B63; font-size: 13px; font-weight: 700; }
        QPushButton#miniHelpBtn { background: #EAF3FB; color: #1C4D7C; border: 1px solid #8FB0CD; border-radius: 10px; font-size: 12px; font-weight: 700; padding: 0; }
        QPushButton#miniHelpBtn:hover { background: #DCECF9; border-color: #6F96BB; }
        QPushButton#miniHelpBtn:pressed { background: #CFE3F4; }

        /* ── 左ペインの密度調整 ── */
        QWidget#leftSettingsContainer QGroupBox#settingsSection {
            border-radius: 9px;
            padding-top: 12px;
        }
        QWidget#leftSettingsContainer QGroupBox#settingsSection::title {
            left: 8px;
            top: 5px;
            padding: 0 6px;
        }
        QWidget#leftSettingsContainer QLabel#dimLabel { font-size: 13px; }
        QWidget#leftSettingsContainer QLabel#hintLabel { font-size: 12px; }
        QWidget#leftSettingsContainer QLabel#subNoteLabel { font-size: 11px; }
        QWidget#leftSettingsContainer QLabel#flowGuideTitle { font-size: 12px; }
        QWidget#leftSettingsContainer QLabel#flowGuideText { font-size: 11px; }
        QFrame#flowGuide { background: #EDF4FB; border: 1px solid #C7D8E8; border-radius: 10px; }
        QWidget#viewRoleBox { background: transparent; }
        QWidget#leftSettingsContainer QLabel#presetSummaryLabel { font-size: 14px; font-weight: 400; }
        QWidget#leftSettingsContainer QComboBox,
        QWidget#leftSettingsContainer QSpinBox,
        QWidget#leftSettingsContainer QLineEdit {
            padding: 3px 7px;
            min-height: 18px;
            border-radius: 7px;
        }
        QWidget#leftSettingsContainer QComboBox::drop-down { width: 18px; }
        QWidget#leftSettingsContainer QSpinBox[compactField="true"] {
            padding: 2px 6px;
            min-height: 16px;
            max-height: 24px;
            border-radius: 6px;
        }
        QWidget#leftSettingsContainer QCheckBox { spacing: 4px; }
        QWidget#leftSettingsContainer QCheckBox::indicator { width: 14px; height: 14px; }
        QWidget#leftSettingsContainer QPushButton#smallBtn {
            padding: 3px 10px;
            min-height: 18px;
            border-radius: 7px;
        }
        QWidget#leftSettingsContainer QPushButton#stepBtn {
            border-radius: 5px;
            font-size: 15px;
        }

        QComboBox {
            background: #FFFFFF;
            border: 1px solid #C9D6E3;
            border-radius: 8px;
            padding: 5px 8px;
            color: #2B4056;
        }
        QComboBox:hover { border-color: #9ABFE4; }
        QComboBox::drop-down { border: none; width: 22px; }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #6B86A0;
        }
        QComboBox QAbstractItemView {
            background: #FFFFFF;
            border: 1px solid #C9D6E3;
            selection-background-color: #DCEBFA;
            color: #2B4056;
        }

        QSpinBox {
            background: #FFFFFF;
            border: 1px solid #C9D6E3;
            border-radius: 8px;
            padding: 5px 8px;
            color: #2B4056;
            min-height: 22px;
        }
        QSpinBox:hover { border-color: #9ABFE4; }
        QSpinBox:focus { border-color: #77AEEB; }
        QSpinBox::up-button, QSpinBox::down-button { width: 0; }
        QSpinBox[showSpinButtons="true"] {
            padding-right: 23px;
            border-color: #7D9FBE;
        }
        QSpinBox[showSpinButtons="true"]::up-button,
        QSpinBox[showSpinButtons="true"]::down-button {
            width: 24px;
            background: #E5EEF8;
            border-left: 1px solid #6F93B6;
            border-right: 1px solid #AEC6DD;
        }
        QSpinBox[showSpinButtons="true"]::up-button:hover,
        QSpinBox[showSpinButtons="true"]::down-button:hover {
            background: #D6E5F5;
        }
        QSpinBox[showSpinButtons="true"]::up-button:pressed,
        QSpinBox[showSpinButtons="true"]::down-button:pressed {
            background: #C8DCF1;
        }
        QSpinBox[showSpinButtons="true"]::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            border-top-right-radius: 7px;
            border-bottom: 1px solid #6F93B6;
        }
        QSpinBox[showSpinButtons="true"]::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            border-bottom-right-radius: 7px;
        }
        QSpinBox[showSpinButtons="true"]::up-arrow {
            image: url({SPIN_UP_ICON});
            width: 14px;
            height: 10px;
        }
        QSpinBox[showSpinButtons="true"]::down-arrow {
            image: url({SPIN_DOWN_ICON});
            width: 14px;
            height: 10px;
        }
        QSpinBox[miniSpinButtons="true"] {
            padding-right: 12px;
        }
        QSpinBox[miniSpinButtons="true"]::up-button,
        QSpinBox[miniSpinButtons="true"]::down-button {
            width: 12px;
        }
        QSpinBox[miniSpinButtons="true"]::up-arrow,
        QSpinBox[miniSpinButtons="true"]::down-arrow {
            width: 7px;
            height: 5px;
        }

        QCheckBox { color: #35506A; spacing: 6px; }
        QCheckBox::indicator {
            width: 16px; height: 16px;
            border: 1px solid #AFC1D2;
            border-radius: 4px;
            background: #FFFFFF;
        }
        QCheckBox::indicator:hover { border-color: #77AEEB; }
        QCheckBox::indicator:checked {
            background-color: #5B9BED;
            border: 1px solid #4C8FE3;
        }

        QPushButton#smallBtn {
            background: #FFFFFF;
            border: 1px solid #C8D6E5;
            border-radius: 8px;
            padding: 5px 12px;
            color: #355A80;
            font-size: 14px;
            min-height: 20px;
        }
        QPushButton#smallBtn:hover { background: #EEF5FC; }
        QPushButton#smallBtn[previewState="pending"] {
            background: #FFF1DF;
            border: 1px solid #F0A84F;
            color: #8A4D00;
            font-weight: 700;
        }
        QPushButton#smallBtn[previewState="pending"]:hover { background: #FFE5C2; }
        QPushButton#smallBtn[previewState="refreshing"],
        QPushButton#smallBtn[previewState="refreshing"]:disabled {
            background: #F59E0B;
            border: 1px solid #D97706;
            color: #FFFFFF;
            font-weight: 700;
        }

        QPushButton#stepBtn {
            background: #FFFFFF;
            border: 1px solid #C8D6E5;
            border-radius: 6px;
            color: #5D7EA0;
            font-size: 16px;
            font-weight: 700;
        }
        QPushButton#stepBtn:hover { background: #EEF5FC; }

        QLineEdit {
            background: #FFFFFF;
            border: 1px solid #C9D6E3;
            border-radius: 8px;
            padding: 5px 9px;
            color: #2B4056;
        }
        QLineEdit:focus { border-color: #77AEEB; }

        /* ── プレビューパネル ── */
        QFrame#viewToggleBar {
            background: #F5F8FC;
            border: none;
        }
        QPushButton#viewToggleBtn {
            background: transparent;
            border: 1px solid #C8D6E5;
            border-radius: 8px;
            padding: 6px 16px;
            color: #6C86A0;
            font-size: 15px;
        }
        QPushButton#viewToggleBtn:hover { background: #EEF4FB; color: #37597C; }
        QPushButton#viewToggleBtn:checked {
            background: #E8F1FD;
            border: 1px solid #C3D7EE;
            color: #23435F;
            font-weight: 700;
        }

        /* ── ナビゲーションバー ── */
        QFrame#navBar {
            background: #F5F8FC;
            border: none;
            border-top: 1px solid #DCE5EE;
        }
        QPushButton#navBtn {
            background: #FFFFFF;
            border: 1px solid #C8D6E5;
            border-radius: 8px;
            padding: 5px 14px;
            color: #355A80;
            font-size: 14px;
        }
        QPushButton#navBtn:hover { background: #EEF5FC; }
        QPushButton#navBtn:disabled { color: #A4B3C0; border-color: #D6DFE8; }
        QFrame#navSectionSep {
            color: #D2DEE9;
            background: transparent;
        }
        QCheckBox#navToggle, QCheckBox#previewToolbarToggle {
            color: #35506A;
            spacing: 6px;
            padding-right: 4px;
        }
        QCheckBox#navToggle::indicator, QCheckBox#previewToolbarToggle::indicator {
            width: 34px;
            height: 18px;
            border: 1px solid #AFC1D2;
            border-radius: 9px;
            background: #FFFFFF;
        }
        QCheckBox#navToggle::indicator:hover, QCheckBox#previewToolbarToggle::indicator:hover { border-color: #77AEEB; }
        QCheckBox#navToggle::indicator:checked, QCheckBox#previewToolbarToggle::indicator:checked {
            background: #5B9BED;
            border: 1px solid #4C8FE3;
        }

        /* ── 下部パネル ── */
        QFrame#bottomPanel { background: #F6F9FC; border: none; }
        QFrame#bottomPanel QTabBar::tab { min-height: 24px; padding: 4px 10px; }
        QFrame#statusStrip { background: #FAFCFE; border: none; }

        QLabel#badge {
            background: #EDF3F8;
            border: 1px solid #D4DFEA;
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 13px;
            font-weight: 700;
            color: #627E99;
        }

        QProgressBar {
            background: #E7EEF5;
            border: none;
            border-radius: 3px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4F8FEF, stop:1 #67C0FF);
            border-radius: 3px;
        }

        QTabWidget::pane {
            background: #F6F9FC;
            border: none;
            border-top: 1px solid #DCE5EE;
        }
        QTabBar::tab {
            background: #F6F9FC;
            border: none;
            border-top: 2px solid transparent;
            padding: 7px 18px;
            color: #708BA6;
            font-size: 14px;
        }
        QTabBar::tab:selected {
            color: #25435F;
            border-top: 2px solid #6FA7E7;
            background: #FFFFFF;
        }
        QTabBar::tab:hover { color: #4D6F90; }

        QListWidget {
            background: #FFFFFF;
            border: none;
            border-radius: 6px;
            color: #35506A;
            font-size: 14px;
        }
        QListWidget::item:hover { background: #EEF5FC; }
        QListWidget::item:selected { background: #DCEBFA; }

        QTextEdit {
            background: #FFFFFF;
            border: 1px solid #E0E7EF;
            border-radius: 6px;
            color: #5D7892;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            padding: 6px;
        }

        /* ── スプリッタ ── */
        QSplitter::handle { background: #DCE5EE; }
        QSplitter::handle:horizontal {
            width: 6px;
            margin: 0 2px;
        }
        QSplitter::handle:vertical {
            height: 6px;
            margin: 2px 0;
        }

        /* ── ポップアップメニュー ── */
        QMenu#gearPopupMenu {
            background: #FFFFFF;
            color: #24415C;
            border: 1px solid #C8D5E1;
            padding: 6px;
            border-radius: 8px;
        }
        QMenu#gearPopupMenu::item {
            padding: 7px 28px 7px 12px;
            border-radius: 6px;
            font-size: 14px;
        }
        QMenu#gearPopupMenu::item:selected { background: #EAF4FF; }
        QMenu#gearPopupMenu::indicator { width: 14px; height: 14px; }
        QMenu#gearPopupMenu::separator { height: 1px; background: #D7E1EA; margin: 6px 4px; }

        /* ── ステータスバー ── */
        QStatusBar { background: #F6F9FC; color: #5F7992; font-size: 13px; }
        """
        return (stylesheet
                .replace("{SPIN_UP_ICON}", SPIN_UP_ICON)
                .replace("{SPIN_DOWN_ICON}", SPIN_DOWN_ICON))

    def _dark_stylesheet(self) -> str:
        stylesheet = """
        /* ── ベース ── */
        QMainWindow, QWidget {
            background: #0D1520;
            color: #D8EAF8;
            font-family: 'Meiryo', 'Yu Gothic UI', sans-serif;
            font-size: 15px;
        }

        /* ── トップバー ── */
        QFrame#topBar {
            background: #111F2E;
            border: none;
        }
        QFrame#vSep { background: #1E3040; }
        QFrame#topSep { background: #1A2D3F; border: none; max-height: 1px; }
        QFrame#leftSettingsBottomSep { background: #1A2D3F; border: none; max-height: 1px; }
        QFrame#bottomPanelSep { background: #1A2D3F; border: none; max-height: 1px; }

        QLabel#appTitle {
            font-size: 17px;
            font-weight: 700;
            color: #E8F6FF;
            letter-spacing: 0.5px;
        }

        QLineEdit#targetEdit {
            background: #0A1520;
            border: 1px solid #1E3040;
            border-radius: 8px;
            padding: 6px 10px;
            color: #C8DFF0;
        }
        QLineEdit#targetEdit:focus { border-color: #3A6A9A; }

        QPushButton#topBtn {
            background: #182C3E;
            border: 1px solid #233D55;
            border-radius: 8px;
            padding: 5px 10px;
            color: #B8D4E8;
            font-size: 14px;
        }
        QPushButton#topBtn:hover { background: #1E3850; }

        QPushButton#runBtn {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2A6FCC, stop:1 #1A9AE0);
            border: none;
            border-radius: 8px;
            color: #F0F8FF;
            font-weight: 700;
            font-size: 15px;
            letter-spacing: 0.3px;
        }
        QPushButton#runBtn:hover { background: #3A80DD; }
        QPushButton#runBtn:disabled { background: #1A2D3F; color: #4A6070; }

        QPushButton#stopBtn {
            background: #2A1A1A;
            border: 1px solid #5A2A2A;
            border-radius: 8px;
            color: #E07060;
            font-size: 14px;
        }
        QPushButton#stopBtn:hover { background: #3A2020; }
        QPushButton#stopBtn:disabled {
            background: #161E26;
            color: #3A4A54;
            border-color: #1E2D3A;
        }

        QPushButton#iconBtn {
            background: #182C3E;
            border: 1px solid #233D55;
            border-radius: 8px;
            color: #88AABF;
            font-size: 18px;
            font-weight: 700;
        }
        QPushButton#iconBtn:hover { background: #1E3850; color: #C8E4F8; }

        /* ── 設定パネル ── */
        QScrollBar:vertical {
            background: #0A1520;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #253D52;
            min-height: 24px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover { background: #3A5870; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

        QGroupBox#settingsSection {
            background: #101D2B;
            border: 1px solid #1A2E40;
            border-radius: 10px;
            margin-top: 0;
            padding-top: 14px;
            font-size: 14px;
            font-weight: 700;
            color: #6A9AB8;
            letter-spacing: 0.8px;
            text-transform: uppercase;
        }
        QGroupBox#settingsSection::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 8px;
            left: 10px;
            top: 6px;
            background: #101D2B;
        }

        QLabel#dimLabel { color: #7A9BB2; font-size: 14px; }
        QLabel#hintLabel { color: #6485A0; font-size: 13px; }
        QLabel#presetSummaryLabel { color: #8BB6E8; font-size: 15px; font-weight: 400; }
        QLabel#subNoteLabel { color: #83A0BD; font-size: 12px; line-height: 1.35em; }
        QLabel#flowGuideTitle { color: #D6E6F6; font-size: 13px; font-weight: 700; }
        QLabel#flowGuideText { color: #A8C0D7; font-size: 12px; }
        QLabel#viewRoleLabel { color: #E2F0FF; font-size: 13px; font-weight: 700; }
        QPushButton#miniHelpBtn { background: #203749; color: #F1F7FE; border: 1px solid #5E7D99; border-radius: 10px; font-size: 12px; font-weight: 700; padding: 0; }
        QPushButton#miniHelpBtn:hover { background: #28455C; border-color: #7D9BB7; }
        QPushButton#miniHelpBtn:pressed { background: #31526D; }

        /* ── 左ペインの密度調整 ── */
        QWidget#leftSettingsContainer QGroupBox#settingsSection {
            border-radius: 9px;
            padding-top: 12px;
        }
        QWidget#leftSettingsContainer QGroupBox#settingsSection::title {
            left: 8px;
            top: 5px;
            padding: 0 6px;
        }
        QWidget#leftSettingsContainer QLabel#dimLabel { font-size: 13px; }
        QWidget#leftSettingsContainer QLabel#hintLabel { font-size: 12px; }
        QWidget#leftSettingsContainer QLabel#subNoteLabel { font-size: 11px; }
        QWidget#leftSettingsContainer QLabel#flowGuideTitle { font-size: 12px; }
        QWidget#leftSettingsContainer QLabel#flowGuideText { font-size: 11px; }
        QFrame#flowGuide { background: #14283B; border: 1px solid #314A62; border-radius: 10px; }
        QWidget#viewRoleBox { background: transparent; }
        QWidget#leftSettingsContainer QLabel#presetSummaryLabel { font-size: 14px; font-weight: 400; }
        QWidget#leftSettingsContainer QComboBox,
        QWidget#leftSettingsContainer QSpinBox,
        QWidget#leftSettingsContainer QLineEdit {
            padding: 3px 7px;
            min-height: 18px;
            border-radius: 7px;
        }
        QWidget#leftSettingsContainer QComboBox::drop-down { width: 18px; }
        QWidget#leftSettingsContainer QSpinBox[compactField="true"] {
            padding: 2px 6px;
            min-height: 16px;
            max-height: 24px;
            border-radius: 6px;
        }
        QWidget#leftSettingsContainer QCheckBox { spacing: 4px; }
        QWidget#leftSettingsContainer QCheckBox::indicator { width: 14px; height: 14px; }
        QWidget#leftSettingsContainer QPushButton#smallBtn {
            padding: 3px 10px;
            min-height: 18px;
            border-radius: 7px;
        }
        QWidget#leftSettingsContainer QPushButton#stepBtn {
            border-radius: 5px;
            font-size: 15px;
        }

        QComboBox {
            background: #0A1520;
            border: 1px solid #1E3040;
            border-radius: 8px;
            padding: 5px 8px;
            color: #C8DFF0;
        }
        QComboBox:hover { border-color: #2E5070; }
        QComboBox::drop-down { border: none; width: 22px; }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #7AA0BB;
        }
        QComboBox QAbstractItemView {
            background: #0F1E2C;
            border: 1px solid #1E3040;
            selection-background-color: #1A3D5A;
            color: #D8EAF8;
        }

        QSpinBox {
            background: #0A1520;
            border: 1px solid #1E3040;
            border-radius: 8px;
            padding: 5px 8px;
            color: #C8DFF0;
            min-height: 22px;
        }
        QSpinBox:hover { border-color: #2E5070; }
        QSpinBox:focus { border-color: #3A6A9A; }
        QSpinBox::up-button, QSpinBox::down-button { width: 0; }
        QSpinBox[showSpinButtons="true"] {
            padding-right: 23px;
            border-color: #6D88A4;
        }
        QSpinBox[showSpinButtons="true"]::up-button,
        QSpinBox[showSpinButtons="true"]::down-button {
            width: 24px;
            background: #22415E;
            border-left: 1px solid #88A7C4;
            border-right: 1px solid #35516E;
        }
        QSpinBox[showSpinButtons="true"]::up-button:hover,
        QSpinBox[showSpinButtons="true"]::down-button:hover {
            background: #2A4A69;
        }
        QSpinBox[showSpinButtons="true"]::up-button:pressed,
        QSpinBox[showSpinButtons="true"]::down-button:pressed {
            background: #31577A;
        }
        QSpinBox[showSpinButtons="true"]::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            border-top-right-radius: 7px;
            border-bottom: 1px solid #88A7C4;
        }
        QSpinBox[showSpinButtons="true"]::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            border-bottom-right-radius: 7px;
        }
        QSpinBox[showSpinButtons="true"]::up-arrow {
            image: url({SPIN_UP_ICON_DARK});
            width: 14px;
            height: 10px;
        }
        QSpinBox[showSpinButtons="true"]::down-arrow {
            image: url({SPIN_DOWN_ICON_DARK});
            width: 14px;
            height: 10px;
        }
        QSpinBox[miniSpinButtons="true"] {
            padding-right: 12px;
        }
        QSpinBox[miniSpinButtons="true"]::up-button,
        QSpinBox[miniSpinButtons="true"]::down-button {
            width: 12px;
        }
        QSpinBox[miniSpinButtons="true"]::up-arrow,
        QSpinBox[miniSpinButtons="true"]::down-arrow {
            width: 7px;
            height: 5px;
        }

        QCheckBox { color: #A8C8E0; spacing: 6px; }
        QCheckBox::indicator {
            width: 16px; height: 16px;
            border: 1px solid #2A4A60;
            border-radius: 4px;
            background: #0A1520;
        }
        QCheckBox::indicator:hover { border-color: #3A6A9A; }
        QCheckBox::indicator:checked {
            background-color: #2A6FCC;
            border: 1px solid #3A80DD;
        }

        QPushButton#smallBtn {
            background: #182C3E;
            border: 1px solid #233D55;
            border-radius: 8px;
            padding: 5px 12px;
            color: #A8C8E0;
            font-size: 14px;
            min-height: 20px;
        }
        QPushButton#smallBtn:hover { background: #1E3850; }
        QPushButton#smallBtn[previewState="pending"] {
            background: #4A2B10;
            border: 1px solid #B7791F;
            color: #FFE1B8;
            font-weight: 700;
        }
        QPushButton#smallBtn[previewState="pending"]:hover { background: #5C3514; }
        QPushButton#smallBtn[previewState="refreshing"],
        QPushButton#smallBtn[previewState="refreshing"]:disabled {
            background: #A16207;
            border: 1px solid #D97706;
            color: #FFF7ED;
            font-weight: 700;
        }

        QPushButton#stepBtn {
            background: #182C3E;
            border: 1px solid #233D55;
            border-radius: 6px;
            color: #88AACC;
            font-size: 16px;
            font-weight: 700;
        }
        QPushButton#stepBtn:hover { background: #1E3850; }

        QLineEdit {
            background: #0A1520;
            border: 1px solid #1E3040;
            border-radius: 8px;
            padding: 5px 9px;
            color: #C8DFF0;
        }
        QLineEdit:focus { border-color: #3A6A9A; }

        /* ── プレビューパネル ── */
        QFrame#viewToggleBar {
            background: #0F1C28;
            border: none;
        }
        QPushButton#viewToggleBtn {
            background: transparent;
            border: 1px solid #29455D;
            border-radius: 8px;
            padding: 6px 16px;
            color: #7EA4BE;
            font-size: 15px;
        }
        QPushButton#viewToggleBtn:hover { background: #14283A; color: #A8C8E0; }
        QPushButton#viewToggleBtn:checked {
            background: #1A3550;
            border: 1px solid #2A5070;
            color: #E0F2FF;
            font-weight: 700;
        }

        /* ── ナビゲーションバー ── */
        QFrame#navBar {
            background: #0F1C28;
            border: none;
            border-top: 1px solid #1A2D3F;
        }
        QPushButton#navBtn {
            background: #182C3E;
            border: 1px solid #233D55;
            border-radius: 8px;
            padding: 5px 14px;
            color: #A8C8E0;
            font-size: 14px;
        }
        QPushButton#navBtn:hover { background: #1E3850; }
        QPushButton#navBtn:disabled { color: #4D6475; border-color: #172030; }
        QFrame#navSectionSep {
            color: #243C52;
            background: transparent;
        }
        QCheckBox#navToggle, QCheckBox#previewToolbarToggle {
            color: #A8C8E0;
            spacing: 6px;
            padding-right: 4px;
        }
        QCheckBox#navToggle::indicator, QCheckBox#previewToolbarToggle::indicator {
            width: 34px;
            height: 18px;
            border: 1px solid #2A4A60;
            border-radius: 9px;
            background: #0A1520;
        }
        QCheckBox#navToggle::indicator:hover, QCheckBox#previewToolbarToggle::indicator:hover { border-color: #3A6A9A; }
        QCheckBox#navToggle::indicator:checked, QCheckBox#previewToolbarToggle::indicator:checked {
            background: #215EA8;
            border: 1px solid #3A80DD;
        }

        /* ── 下部パネル ── */
        QFrame#bottomPanel { background: #0D1824; border: none; }
        QFrame#bottomPanel QTabBar::tab { min-height: 24px; padding: 4px 10px; }
        QFrame#statusStrip { background: #0F1C28; border: none; }

        QLabel#badge {
            background: #182C3E;
            border: 1px solid #1E3A50;
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 13px;
            font-weight: 700;
            color: #7AAAC0;
        }

        QProgressBar {
            background: #0A1520;
            border: none;
            border-radius: 3px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #2A6FCC, stop:1 #1ABBE0);
            border-radius: 3px;
        }

        QTabWidget::pane {
            background: #0D1824;
            border: none;
            border-top: 1px solid #1A2D3F;
        }
        QTabBar::tab {
            background: #0D1824;
            border: none;
            border-top: 2px solid transparent;
            padding: 7px 18px;
            color: #6A8CAA;
            font-size: 14px;
        }
        QTabBar::tab:selected {
            color: #A8D4F0;
            border-top: 2px solid #3A7AAA;
            background: #101E2C;
        }
        QTabBar::tab:hover { color: #80B0D0; }

        QListWidget {
            background: #0A1520;
            border: none;
            border-radius: 6px;
            color: #A8C8E0;
            font-size: 14px;
        }
        QListWidget::item:hover { background: #1A2E40; }
        QListWidget::item:selected { background: #1A3D5A; }

        QTextEdit {
            background: #080F18;
            border: 1px solid #152434;
            border-radius: 6px;
            color: #8EB1C8;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 13px;
            padding: 6px;
        }

        /* ── スプリッタ ── */
        QSplitter::handle { background: #1A2D3F; }
        QSplitter::handle:horizontal {
            width: 6px;
            margin: 0 2px;
        }
        QSplitter::handle:vertical {
            height: 6px;
            margin: 2px 0;
        }
        QSplitter::handle:hover { background: #2A4560; }

        /* ── ポップアップメニュー ── */
        QMenu#gearPopupMenu {
            background: #10202F;
            color: #D7E7F5;
            border: 1px solid #29445C;
            padding: 6px;
            border-radius: 8px;
        }
        QMenu#gearPopupMenu::item {
            padding: 7px 28px 7px 12px;
            border-radius: 6px;
            font-size: 14px;
        }
        QMenu#gearPopupMenu::item:selected { background: #173249; }
        QMenu#gearPopupMenu::indicator { width: 14px; height: 14px; }
        QMenu#gearPopupMenu::separator { height: 1px; background: #29445C; margin: 6px 4px; }

        /* ── ステータスバー ── */
        QStatusBar { background: #0D1824; color: #6E92AD; font-size: 13px; }
        """
        return (stylesheet
                .replace("{SPIN_UP_ICON_DARK}", SPIN_UP_ICON_DARK)
                .replace("{SPIN_DOWN_ICON_DARK}", SPIN_DOWN_ICON_DARK))

    # ── ビュー切替 ────────────────────────────────────────

    def _normalized_main_view_mode(self: MainWindow, mode: object) -> str:
        return _normalized_main_view_mode(mode)

    def _preview_view_help_text(self: MainWindow) -> str:
        # Keep this small wrapper source-compatible with legacy regression tests
        # that assert the help text is owned by build_view_toggle_bar_plan(), while
        # still delegating to the split helper as the fallback implementation.
        toggle_plan = gui_layouts.build_view_toggle_bar_plan()
        if 'help_text' in toggle_plan:
            return str(toggle_plan.get('help_text'))
        return _preview_view_help_text()

    def _main_view_mode_help_text(self: MainWindow, mode: object) -> str:
        return _main_view_mode_help_text(mode)

    def _main_view_mode_status_text(self: MainWindow, mode: object) -> str:
        return _main_view_mode_status_text(mode)

    def _sync_preview_view_page_index_for_mode(self: MainWindow, mode: object) -> None:
        normalized = self._normalized_main_view_mode(mode)
        effective_source = self._effective_device_view_source()
        preview_pages = self._runtime_preview_pages() if normalized == 'font' else []
        device_pages = self._runtime_device_preview_pages() if normalized != 'font' else []
        sync_state = studio_logic.build_preview_view_page_sync_state(
            mode=normalized,
            effective_device_view_source=effective_source,
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
        view_tip = self._main_view_mode_help_text(normalized)
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

    def _refresh_active_view_after_mode_change(self: MainWindow, mode: object) -> None:
        normalized = self._normalized_main_view_mode(mode)
        try:
            if normalized == 'font':
                self._refresh_font_preview_display_if_needed(refresh_navigation=False)
            else:
                self.render_current_page(refresh_navigation=False)
        except Exception:
            pass

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
        menu = QMenu(self)
        menu.setObjectName('gearPopupMenu')
        menu.setToolTipsVisible(True)
        menu.addSection('外観')

        theme_group = QActionGroup(menu)
        theme_group.setExclusive(True)

        light_action = menu.addAction('白基調')
        light_action.setCheckable(True)
        light_action.setChecked(self.current_ui_theme != 'dark')
        light_action.triggered.connect(lambda checked: checked and self.set_ui_theme('light'))
        theme_group.addAction(light_action)

        dark_action = menu.addAction('ダーク')
        dark_action.setCheckable(True)
        dark_action.setChecked(self.current_ui_theme == 'dark')
        dark_action.triggered.connect(lambda checked: checked and self.set_ui_theme('dark'))
        theme_group.addAction(dark_action)

        menu.addSeparator()
        menu.addSection('その他オプション')

        open_folder_action = menu.addAction('完了後フォルダを開く')
        open_folder_action.setCheckable(True)
        open_folder_action.setChecked(self.open_folder_check.isChecked())
        open_folder_action.toggled.connect(lambda checked: self.open_folder_check.setChecked(bool(checked)))

        panel_button_action = menu.addAction('三本線ボタンを表示')
        panel_button_action.setCheckable(True)
        panel_button_action.setChecked(bool(getattr(self, 'panel_button_visible', True)))
        panel_button_action.toggled.connect(lambda checked: self.set_panel_button_visible(bool(checked)))

        conflict_menu = menu.addMenu('同名出力')
        conflict_group = QActionGroup(conflict_menu)
        conflict_group.setExclusive(True)
        for key, label in OUTPUT_CONFLICT_OPTIONS:
            action = conflict_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.current_output_conflict_mode() == key)
            action.triggered.connect(lambda checked, key=key: checked and self.output_conflict_combo.setCurrentIndex(self.output_conflict_combo.findData(key)))
            conflict_group.addAction(action)

        menu_size = menu.sizeHint()
        button_global = self.settings_btn.mapToGlobal(QPoint(0, 0))
        x = button_global.x() + self.settings_btn.width() - menu_size.width()
        y = button_global.y() + self.settings_btn.height()

        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            x = max(available.left(), min(x, available.right() - menu_size.width() + 1))
            y = max(available.top(), min(y, available.bottom() - menu_size.height() + 1))

        try:
            menu.exec(QPoint(x, y))
            return
        except Exception:
            pass
        self._show_information_dialog_with_status_fallback(
            '表示設定',
            '表示設定メニューを開けませんでした。',
            fallback_status_message='表示設定メニューを開けませんでした。',
        )

    def _apply_left_panel_width(self: MainWindow, width: int) -> None:
        """main_splitter の左パネル幅を確実にセットする。"""
        total = self.main_splitter.width()
        if total <= 0:
            QTimer.singleShot(50, lambda: self._apply_left_panel_width(width))
            return
        if width <= 0:
            return
        left = max(380, min(width, total - 200))
        self.main_splitter.setSizes([left, max(200, total - left)])

    # ── プレビュー ─────────────────────────────────────────

    def _clear_preview_label_pixmap(self: MainWindow) -> None:
        if not hasattr(self, 'preview_label'):
            return
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
        setter = getattr(preview_label, 'setText', None)
        if callable(setter):
            setter(message)

    def on_target_editing_finished(self: MainWindow) -> None:
        # 対象パスを手入力で確定した場合も、ファイル選択と同じくプレビューを更新する。
        # ただし重い生成処理は editingFinished / dialog handler の中で直接走らせず、
        # UI イベントループへ戻してから開始する。
        self._schedule_target_preview_refresh(reset_page=True)

    def _schedule_target_preview_refresh(self: MainWindow, *, reset_page: bool = True) -> None:
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
            single_shot = getattr(QTimer, 'singleShot', None)
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

        _queue_target_preview_refresh_run(_run_target_preview_refresh)

    def _mark_preview_dirty_from_signal(self: MainWindow, *_args: object) -> None:
        self.mark_preview_dirty()

    def _set_preview_update_button_visual_state(self: MainWindow, state: object) -> None:
        """Apply a lightweight visual state to the Preview Update button."""
        button = getattr(self, 'preview_update_btn', None)
        if button is None:
            return
        normalized = str(state or 'idle').strip().lower()
        if normalized not in {'idle', 'pending', 'refreshing'}:
            normalized = 'idle'
        self._preview_update_button_visual_state = normalized
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

    def _mark_preview_update_button_pending(self: MainWindow) -> None:
        """Show that a debounced live preview refresh has been queued."""
        button = getattr(self, 'preview_update_btn', None)
        if button is None:
            return
        try:
            button.setEnabled(True)
        except Exception:
            pass
        try:
            button.setText('更新待ち…')
        except Exception:
            pass
        self._set_preview_update_button_visual_state('pending')

    def _schedule_live_preview_refresh_from_signal(self: MainWindow, *_args: object) -> None:
        self._schedule_live_preview_refresh(reset_page=False)

    def _has_refreshable_preview_target(self: MainWindow) -> bool:
        """Return True when settings changes can regenerate a preview from the current target.

        Live preview must keep working even after an intermediate UI action clears
        the cached preview pages.  In that state the presence of an existing
        target path is enough to allow a debounced settings refresh to rebuild
        the preview instead of silently falling back to a dirty placeholder.
        """
        try:
            payload = self._current_preview_payload()
        except Exception:
            payload = {}
        target_text = str(payload.get('target', '') if isinstance(payload, Mapping) else '').strip()
        if target_text:
            try:
                return Path(target_text).exists()
            except (OSError, ValueError):
                return False
        image_data_url = ''
        if isinstance(payload, Mapping):
            image_data_url = str(payload.get('preview_image_data_url', '') or '').strip()
        return bool(image_data_url)

    def _has_active_preview_for_live_refresh(self: MainWindow) -> bool:
        font_view_active = self._normalized_main_view_mode(
            getattr(self, 'main_view_mode', 'font')
        ) == 'font'
        try:
            has_font_preview = bool(self._runtime_preview_pages())
        except Exception:
            has_font_preview = False
        try:
            device_preview_active = self._effective_device_view_source() == 'preview'
        except Exception:
            device_preview_active = False
        try:
            has_device_preview = bool(self._runtime_device_preview_pages())
        except Exception:
            has_device_preview = False
        has_runtime_preview = bool((font_view_active and has_font_preview) or (device_preview_active and has_device_preview))
        return bool(has_runtime_preview or self._has_refreshable_preview_target())

    def _queue_live_preview_refresh_timer(self: MainWindow, callback: Callable[[], None], delay_ms: int) -> bool:
        single_shot = getattr(QTimer, 'singleShot', None)
        if callable(single_shot):
            try:
                single_shot(max(0, int(delay_ms)), callback)
                return True
            except Exception:
                pass
        return False

    def _schedule_live_preview_refresh(
        self: MainWindow,
        *,
        reset_page: bool = False,
        delay_ms: int = _SETTINGS_PREVIEW_REFRESH_DELAY_MS,
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
        if not self._has_active_preview_for_live_refresh():
            try:
                self.mark_preview_dirty()
            except Exception:
                pass
            return False

        try:
            self.mark_preview_dirty()
        except Exception:
            pass

        generation = int(getattr(self, '_settings_preview_refresh_generation', 0) or 0) + 1
        self._settings_preview_refresh_generation = generation
        self._settings_preview_refresh_pending = True
        self._settings_preview_refresh_pending_reset_page = bool(reset_page) or bool(
            getattr(self, '_settings_preview_refresh_pending_reset_page', False)
        )
        self._settings_preview_refresh_scheduled = True
        self._mark_preview_update_button_pending()

        def _run_live_preview_refresh(expected_generation: int) -> None:
            if expected_generation != int(getattr(self, '_settings_preview_refresh_generation', 0) or 0):
                return
            self._settings_preview_refresh_scheduled = False
            if not bool(getattr(self, '_settings_preview_refresh_pending', False)):
                return
            if bool(getattr(self, '_preview_running', False)):
                rerun_generation = int(getattr(self, '_settings_preview_refresh_generation', 0) or 0) + 1
                self._settings_preview_refresh_generation = rerun_generation
                self._settings_preview_refresh_scheduled = True
                if self._queue_live_preview_refresh_timer(
                    lambda: _run_live_preview_refresh(rerun_generation),
                    50,
                ):
                    return
                self._settings_preview_refresh_scheduled = False
                return
            reset_page_for_run = bool(
                getattr(self, '_settings_preview_refresh_pending_reset_page', reset_page)
            )
            self._settings_preview_refresh_pending = False
            self._settings_preview_refresh_pending_reset_page = False
            try:
                refreshed = bool(self.request_preview_refresh(reset_page=reset_page_for_run))
            except Exception:
                refreshed = False
            if not refreshed:
                try:
                    self.mark_preview_dirty()
                except Exception:
                    pass

        if self._queue_live_preview_refresh_timer(lambda: _run_live_preview_refresh(generation), delay_ms):
            return True
        self._settings_preview_refresh_scheduled = False
        _run_live_preview_refresh(generation)
        return True

    def mark_preview_dirty_for_target_change(self: MainWindow) -> None:
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

    def mark_preview_dirty(self: MainWindow) -> None:
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
        self._update_preview_status_label(studio_logic.build_preview_status_message('dirty'))

    def _update_preview_status_label(self: MainWindow, text: object) -> None:
        if hasattr(self, 'preview_status_label'):
            label_text = str(text or '').strip()
            try:
                self.preview_status_label.setText(label_text)
            except Exception:
                pass
            try:
                if hasattr(self.preview_status_label, 'setToolTip'):
                    self.preview_status_label.setToolTip(label_text)
            except Exception:
                pass

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
        return tuple(values) if len(values) == 4 else (0, 0, 0, 0)

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
        """Fontビューのプレビューを実機に近い見た目へ寄せるための装飾。

        - ガイドOFF: 青い帯は出さない（枠線だけ）
        - ガイドON : 実機ビューと同様に非描画域の帯 + 点線ガイドを重ねる

        Qt が無い環境（回帰テスト用スタブ）では、そのまま返す。
        """
        dark = bool(getattr(self, 'current_ui_theme', 'light') == 'dark')
        show_guides = False
        try:
            if hasattr(self, 'guides_check') and hasattr(self.guides_check, 'isChecked'):
                show_guides = bool(self.guides_check.isChecked())
        except Exception:
            show_guides = False

        try:
            out = pix.copy()
        except Exception:
            out = pix

        try:
            painter = QPainter(out)
            painter.setRenderHint(QPainter.Antialiasing, True)
            screen_border = QColor('#6D8295') if dark else QColor('#94A3B3')
            painter.setPen(QPen(screen_border, 1.0))
            rect = out.rect().adjusted(0, 0, -1, -1)
            painter.drawRect(rect)

            if show_guides:
                ref_w = max(1, int(page_width or out.width() or 1))
                ref_h = max(1, int(page_height or out.height() or 1))
                guide_rect = self._guide_rect_for_preview_rect(rect, ref_w, ref_h)
                if guide_rect != rect:
                    guide_band = QPainterPath()
                    guide_band.addRect(rect)
                    guide_band.addRect(guide_rect)
                    painter.fillPath(
                        guide_band,
                        QColor(75, 152, 255, 48) if not dark else QColor(114, 173, 255, 40),
                    )
                    guide_color = QColor(114, 173, 255, 120) if dark else QColor(75, 152, 255, 110)
                    painter.setPen(QPen(guide_color, 1, Qt.DashLine))
                    painter.drawRect(guide_rect)
            try:
                painter.end()
            except Exception:
                pass
        except Exception:
            return out
        return out


    def _preview_pixmap_from_png_bytes(self: MainWindow, raw: bytes) -> object:
        qimg = QImage.fromData(raw, 'PNG')
        qimg_is_null = getattr(qimg, 'isNull', None)
        if callable(qimg_is_null) and qimg_is_null():
            raise RuntimeError('プレビュー画像の読み込みに失敗しました。')
        pix = QPixmap.fromImage(qimg)
        pix_is_null = getattr(pix, 'isNull', None)
        if callable(pix_is_null) and pix_is_null():
            raise RuntimeError('プレビュー画像の描画準備に失敗しました。')
        return pix

    def _apply_preview_pixmap(self: MainWindow, pix: object) -> None:
        try:
            orig_w = max(1, int(pix.width()))
            orig_h = max(1, int(pix.height()))
        except Exception:
            orig_w = orig_h = 0
        target = self._font_preview_target_size()
        if target.width() < 10 or target.height() < 10:
            target = QSize(480, 720)
        scaled = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        scaled = self._decorate_font_view_pixmap(scaled, page_width=orig_w, page_height=orig_h)
        self.preview_label.resize(scaled.size())
        try:
            self.preview_label.setMinimumSize(0, 0)
        except Exception:
            pass
        self.preview_label.setPixmap(scaled)
        self.preview_label.setText('')

    def _apply_preview_png_bytes(self: MainWindow, raw: bytes) -> None:
        self._apply_preview_pixmap(self._preview_pixmap_from_png_bytes(raw))

    def _apply_preview_page_base64_to_label(self: MainWindow, page_b64: object, *, cache_key: object = None) -> None:
        img_b64 = self._coerce_preview_base64_text(page_b64)
        if not img_b64:
            self._show_preview_message('プレビューを生成できませんでした')
            return
        pix = self._cached_font_preview_page_pixmap(cache_key)
        if pix is None:
            raw = base64.b64decode(img_b64, validate=True)
            pix = self._preview_pixmap_from_png_bytes(raw)
            self._store_font_preview_page_pixmap(cache_key, pix)
        self._apply_preview_pixmap(pix)

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
        text_getter = getattr(widget, 'text', None)
        if callable(text_getter):
            try:
                return _coerce_ui_message_text(text_getter()).strip()
            except Exception:
                return ''
        return ''

    def _ui_widget_index(self: MainWindow, widget: object) -> int | None:
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

    def _is_render_failure_status_text(self: MainWindow, text: object) -> bool:
        return studio_logic.is_render_failure_status_text(text)

    def _is_preview_render_failure_status_text(self: MainWindow, text: object) -> bool:
        return studio_logic.is_preview_render_failure_status_text(text)

    def _is_device_render_failure_status_text(self: MainWindow, text: object) -> bool:
        return studio_logic.is_device_render_failure_status_text(text)

    def _display_context_name_from_label_text(self: MainWindow, text: object) -> str:
        return studio_logic.display_context_name_from_label_text(text)

    def _render_failure_preserved_display_name(self: MainWindow, text: object) -> str:
        return studio_logic.render_failure_preserved_display_name(text)

    def _device_render_failure_matches_visible_display_context(self: MainWindow, text: object) -> bool:
        normalized = _coerce_ui_message_text(text).strip()
        if not self._is_device_render_failure_status_text(normalized):
            return False
        visible_label_text = self._ui_widget_text(getattr(self, 'current_xtc_label', None))
        visible_label_normalized = _coerce_ui_message_text(visible_label_text).strip()
        visible_display_name = ''
        if visible_label_normalized.startswith('表示中:'):
            visible_display_name = self._display_context_name_from_label_text(visible_label_normalized)
        return studio_logic.render_failure_matches_display_context(normalized, visible_display_name)

    def _preview_render_failure_matches_visible_display_context(self: MainWindow, text: object) -> bool:
        normalized = _coerce_ui_message_text(text).strip()
        if not self._is_preview_render_failure_status_text(normalized):
            return False
        preserved_display_name = self._render_failure_preserved_display_name(normalized)
        if not preserved_display_name:
            return True
        try:
            view_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        except Exception:
            view_mode = 'font'
        visible_display_name = ''
        preview_source_active = False
        if view_mode == 'font':
            try:
                preview_pages_visible = bool(self._runtime_preview_pages())
            except Exception:
                preview_pages_visible = False
            if preview_pages_visible:
                visible_display_name = 'プレビュー'
        else:
            try:
                preview_source_active = self._normalized_device_view_source_value(
                    getattr(self, 'device_view_source', 'xtc'),
                    default='xtc',
                ) == 'preview'
            except Exception:
                preview_source_active = False
            if preview_source_active:
                visible_label_text = self._ui_widget_text(getattr(self, 'current_xtc_label', None))
                visible_display_name = self._display_context_name_from_label_text(visible_label_text)
                if not visible_display_name or visible_display_name == 'なし':
                    visible_display_name = 'プレビュー'
        if visible_display_name:
            return preserved_display_name == visible_display_name
        if view_mode == 'device':
            return preview_source_active
        return True

    def _visible_render_failure_status_text(self: MainWindow) -> str:
        try:
            view_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        except Exception:
            view_mode = 'font'
        progress_text = self._ui_widget_text(getattr(self, 'progress_label', None))
        status_bar_text = self._status_bar_message_text()
        if view_mode == 'font':
            preview_status_text = self._ui_widget_text(getattr(self, 'preview_status_label', None))
            for candidate in (preview_status_text, progress_text, status_bar_text):
                if (
                    self._is_preview_render_failure_status_text(candidate)
                    and self._preview_render_failure_matches_visible_display_context(candidate)
                ):
                    return candidate
            try:
                preview_pages_visible = bool(self._runtime_preview_pages())
            except Exception:
                preview_pages_visible = False
            if not preview_pages_visible:
                for candidate in (progress_text, status_bar_text):
                    if (
                        self._is_device_render_failure_status_text(candidate)
                        and self._device_render_failure_matches_visible_display_context(candidate)
                    ):
                        return candidate
            return ''
        for candidate in (progress_text, status_bar_text):
            if (
                self._is_device_render_failure_status_text(candidate)
                and self._device_render_failure_matches_visible_display_context(candidate)
            ):
                return candidate
        try:
            device_pages_visible = bool(
                self._runtime_device_preview_pages()
                if self._effective_device_view_source() == 'preview'
                else self._runtime_xtc_pages()
            )
        except Exception:
            device_pages_visible = False
        if not device_pages_visible:
            for candidate in (progress_text, status_bar_text):
                if (
                    self._is_preview_render_failure_status_text(candidate)
                    and self._preview_render_failure_matches_visible_display_context(candidate)
                ):
                    return candidate
        return ''

    def _show_ui_status_message_unless_render_failure_visible(
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
    ) -> None:
        try:
            self._restore_shared_status_for_visible_display_context()
        except Exception:
            pass
        if self._visible_render_failure_status_text():
            return
        self._show_ui_status_message_direct_with_reflection_best_effort(
            message,
            timeout,
            reuse_existing_message=False,
        )

    def _status_bar_message_text(self: MainWindow) -> str:
        status_bar_getter = getattr(self, 'statusBar', None)
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
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
        *,
        reuse_existing_message: bool = True,
    ) -> bool:
        helper = getattr(self, '_show_ui_status_message_unless_render_failure_visible', None)
        if not callable(helper):
            return False
        normalized = _coerce_ui_message_text(message).strip()
        if not normalized:
            return False
        helper_status_bar = None
        helper_status_event_count_before = None
        try:
            helper_status_bar = self.statusBar()
        except Exception:
            helper_status_bar = None
        current_message = self._status_bar_message_text()
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
            self._status_bar_message_text() == normalized
            or bool(self._visible_render_failure_status_text())
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
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
        *,
        reuse_existing_message: bool = True,
    ) -> bool:
        normalized = _coerce_ui_message_text(message).strip()
        if not normalized:
            return False
        reflected = False
        try:
            reflected = bool(
                self._show_ui_status_message_unless_render_failure_visible_with_reflection(
                    normalized,
                    timeout,
                    reuse_existing_message=reuse_existing_message,
                )
            )
        except Exception:
            reflected = False
        if reflected:
            return True
        return self._show_ui_status_message_direct_with_reflection_best_effort(
            normalized,
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
        try:
            if reuse_existing_message:
                return bool(
                    self._show_ui_status_message_direct_with_reflection(
                        message,
                        timeout,
                    )
                )
            return bool(
                self._show_ui_status_message_direct_with_reflection(
                    message,
                    timeout,
                    reuse_existing_message=False,
                )
            )
        except Exception:
            return False

    def _show_ui_status_message_direct_with_reflection(
        self: MainWindow,
        message: object,
        timeout: int | None = 2000,
        *,
        reuse_existing_message: bool = True,
    ) -> bool:
        normalized = _coerce_ui_message_text(message).strip()
        status_bar = None
        status_bar_message_before = self._status_bar_message_text()
        if reuse_existing_message and status_bar_message_before == normalized:
            return True
        status_event_count_before = None
        show_message_call_count_before = None
        try:
            status_bar = self.statusBar()
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
        reflected = self._status_bar_message_text() == normalized
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

    def _current_preview_success_status_message(self: MainWindow) -> str:
        pages = self._runtime_preview_pages()
        status_state = studio_logic.build_preview_success_status_state(
            page_count=len(pages),
            requested_limit=getattr(self, 'last_preview_requested_limit', 0),
            truncated=getattr(self, 'preview_pages_truncated', False),
        )
        return str(status_state.get('status_message', ''))

    def _current_preview_render_status_message(self: MainWindow) -> str:
        pages = self._runtime_preview_pages()
        widget_limit = 0
        limit_widget = getattr(self, 'preview_page_limit_spin', None)
        value_getter = getattr(limit_widget, 'value', None)
        if callable(value_getter):
            try:
                widget_limit = int(value_getter())
            except Exception:
                widget_limit = 0
        return studio_logic.build_preview_render_status_message(
            page_count=len(pages),
            requested_limit=getattr(self, 'last_preview_requested_limit', 0),
            truncated=getattr(self, 'preview_pages_truncated', False),
            running=getattr(self, '_preview_running', False),
            dirty=getattr(self, 'preview_dirty', False),
            widget_limit=widget_limit,
        )

    def _refresh_successful_preview_render_status(self: MainWindow) -> None:
        preview_replacement = self._current_preview_render_status_message()
        if not preview_replacement:
            return
        view_mode = self._normalized_main_view_mode(
            getattr(self, 'main_view_mode', 'font')
        )
        visible_font_preview_active = view_mode == 'font' and bool(self._runtime_preview_pages())
        preview_status_text = ''
        progress_status_text = ''
        if hasattr(self, 'preview_status_label'):
            preview_status_text = self._ui_widget_text(self.preview_status_label)
        if hasattr(self, 'progress_label'):
            progress_status_text = self._ui_widget_text(self.progress_label)
        status_state = studio_logic.build_successful_preview_render_status_refresh_state(
            preview_replacement=preview_replacement,
            view_mode=view_mode,
            visible_font_preview_active=visible_font_preview_active,
            preview_status_text=preview_status_text,
            progress_status_text=progress_status_text,
            status_bar_text=self._status_bar_message_text(),
            current_label_text=self._ui_widget_text(getattr(self, 'current_xtc_label', None)),
        )
        if status_state.get('stale_preview_status') and hasattr(self, 'preview_status_label'):
            try:
                self._update_preview_status_label(str(status_state.get('preview_replacement', preview_replacement)))
            except Exception:
                pass
        progress_replacement = str(status_state.get('progress_replacement', preview_replacement))
        if status_state.get('stale_progress_status') and hasattr(self, 'progress_label'):
            try:
                self.progress_label.setText(progress_replacement)
            except Exception:
                pass
        if status_state.get('should_notify_status_bar'):
            self._show_ui_status_message_direct_with_reflection_best_effort(progress_replacement, 5000)

    def render_current_preview_page(self: MainWindow) -> None:
        pages = self._runtime_preview_pages()
        if not pages:
            self._show_preview_message('プレビューを生成できませんでした')
            return
        should_sync_display_context = self._normalized_main_view_mode(
            getattr(self, 'main_view_mode', 'font')
        ) == 'font'
        if should_sync_display_context:
            try:
                self._sync_preview_display_context_for_font_view()
            except Exception:
                pass
        current_index = worker_logic._int_config_value({'value': getattr(self, 'current_preview_page_index', 0)}, 'value', 0)
        current_index = max(0, min(len(pages) - 1, current_index))
        self.current_preview_page_index = current_index
        try:
            self._apply_preview_page_base64_to_label(
                pages[current_index],
                cache_key=self._font_preview_page_pixmap_cache_key(current_index),
            )
            self._refresh_successful_preview_render_status()
        except Exception as exc:
            self._show_preview_message(f'プレビュー表示エラー\n{exc}')
            status_message = self._render_failure_status_message('プレビュー表示エラー', exc)
            font_view_visible = self._normalized_main_view_mode(
                getattr(self, 'main_view_mode', 'font')
            ) == 'font'
            reflect_failure_in_status = font_view_visible or not self._visible_render_failure_status_text()
            try:
                self._update_preview_status_label(status_message)
            except Exception:
                pass
            self._append_log_with_status_fallback(
                status_message,
                reflect_in_status=reflect_failure_in_status,
            )

    def _normalized_preview_page_cache_tokens(self: MainWindow, tokens: object, *, expected_len: int) -> list[int] | None:
        return studio_logic.normalize_preview_page_cache_tokens(tokens, expected_len=expected_len)

    def _normalized_device_view_source_value(self: MainWindow, value: object, *, default: str = 'xtc') -> str:
        return studio_logic.normalize_device_view_source_value(value, default=default)

    def _effective_device_view_source(self: MainWindow, value: object = None) -> str:
        source = self._normalized_device_view_source_value(
            getattr(self, 'device_view_source', 'xtc') if value is None else value,
            default='xtc',
        )
        has_preview_pages = bool(self._runtime_device_preview_pages()) if source == 'preview' else False
        return studio_logic.resolve_effective_device_view_source(
            source,
            has_preview_pages=has_preview_pages,
        )

    def _is_preview_display_active(self: MainWindow) -> bool:
        mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        has_font_preview_pages = bool(self._runtime_preview_pages()) if mode == 'font' else False
        effective_device_view_source = self._effective_device_view_source() if mode != 'font' else 'xtc'
        return studio_logic.is_preview_display_active(
            mode,
            has_font_preview_pages=has_font_preview_pages,
            effective_device_view_source=effective_device_view_source,
        )

    def _apply_preview_page_cache_tokens_context(self: MainWindow, context: Mapping[str, object] | None) -> None:
        preview_pages = self._runtime_preview_pages()
        device_pages = self._runtime_device_preview_pages()
        tokens_state = studio_logic.build_preview_page_cache_tokens_state(
            context,
            preview_page_count=len(preview_pages),
            device_preview_page_count=len(device_pages),
        )
        if tokens_state.get('should_rebuild'):
            self._rebuild_preview_page_cache_tokens()
            return
        self._preview_page_cache_tokens = list(tokens_state.get('preview_page_cache_tokens', []))
        self._device_preview_page_cache_tokens = list(tokens_state.get('device_preview_page_cache_tokens', []))

    def _apply_preview_button_context(self: MainWindow, context: Mapping[str, object] | None) -> None:
        button_state = studio_logic.build_preview_button_state(context)
        if not hasattr(self, 'preview_update_btn'):
            return
        button_enabled = bool(button_state.get('button_enabled', True))
        button_text = str(button_state.get('button_text', 'プレビュー更新'))
        if not button_enabled or button_text == '生成中…':
            self.preview_update_btn.setEnabled(button_enabled)
            self.preview_update_btn.setText(button_text)
            self._set_preview_update_button_visual_state('refreshing')
            return
        if bool(getattr(self, '_settings_preview_refresh_pending', False)):
            self._mark_preview_update_button_pending()
            return
        self.preview_update_btn.setEnabled(button_enabled)
        self.preview_update_btn.setText(button_text)
        self._set_preview_update_button_visual_state('idle')

    def _apply_preview_progress_context(self: MainWindow, context: Mapping[str, object] | None) -> None:
        progress_state = studio_logic.build_preview_progress_context_state(context)
        self._update_preview_status_label(str(progress_state.get('status_message', '')))

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
        context = self._coerce_mapping_payload(context)
        self.preview_pages_b64 = self._normalized_preview_pages_for_runtime(context.get('preview_pages_b64'))
        self.preview_pages_truncated = self._payload_bool_value(context, 'preview_pages_truncated', False)
        self.device_preview_pages_b64 = self._normalized_preview_pages_for_runtime(context.get('device_preview_pages_b64'))
        self._clear_font_preview_page_pixmap_cache()
        self._clear_device_preview_page_qimage_cache()
        self._apply_preview_page_cache_tokens_context(context)
        self.device_preview_pages_truncated = self._payload_bool_value(context, 'device_preview_pages_truncated', False)
        self.device_view_source = self._normalized_device_view_source_value(
            context.get('device_view_source', 'preview'),
            default='preview',
        )
        self.last_preview_requested_limit = max(
            0,
            self._payload_int_value(
                context,
                'last_preview_requested_limit',
                DEFAULT_PREVIEW_PAGE_LIMIT,
            ),
        )
        raw_last_applied_preview_payload = context.get('last_applied_preview_payload', {})
        self.last_applied_preview_payload = (
            dict(raw_last_applied_preview_payload)
            if isinstance(raw_last_applied_preview_payload, Mapping)
            else {}
        )
        self.current_preview_page_index = preview_controller._clamp_preview_index(
            context.get('current_preview_page_index', 0),
            total=len(self.preview_pages_b64),
        )
        self.current_device_preview_page_index = preview_controller._clamp_preview_index(
            context.get('current_device_preview_page_index', 0),
            total=len(self.device_preview_pages_b64),
        )
        status_message = str(context.get('status_message', studio_logic.build_preview_status_message('empty')))
        has_pages = self._payload_bool_value(context, 'has_pages', False)
        clear_device_page = self._payload_bool_value(context, 'clear_device_page', False)
        if not has_pages:
            self._show_preview_message(status_message)
            self._update_preview_status_label(status_message)
            self.device_view_source = 'xtc'
            self.current_device_preview_page_index = 0
            restored_display_name = self._preview_failure_display_name()
            if restored_display_name is not None:
                self._set_current_xtc_display_name(restored_display_name)
                try:
                    self.render_current_page(refresh_navigation=True)
                except Exception:
                    if clear_device_page:
                        self._clear_xtc_viewer_page(refresh_navigation=True)
                    else:
                        self.update_navigation_ui()
            else:
                self._set_current_xtc_display_name_with_fallback(None)
                if clear_device_page:
                    self._clear_xtc_viewer_page(refresh_navigation=True)
                else:
                    self.update_navigation_ui()
            restored_path = self._preview_failure_loaded_path()
            if restored_path:
                self._sync_results_selection_for_loaded_path_with_fallback(restored_path)
            else:
                self._clear_results_selection_with_fallback(
                    results_controller.build_results_clear_selection_context()
                )
            self._update_top_status()
            return False
        self.render_current_preview_page()
        self.render_current_page(refresh_navigation=True)
        self._update_preview_status_label(status_message)
        self._set_current_xtc_display_name(str(context.get('display_name', 'プレビュー') or 'プレビュー'))
        self._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )
        self._update_top_status()
        return True

    def _preview_failure_display_name(self: MainWindow) -> object:
        xtc_pages = self._runtime_xtc_pages()
        if xtc_pages:
            remembered = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_display_name')).strip()
            return remembered or None
        return None

    def _preview_failure_loaded_path(self: MainWindow) -> object:
        xtc_pages = self._runtime_xtc_pages()
        if xtc_pages:
            remembered = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_path_text')).strip()
            return remembered or None
        return None

    def _apply_preview_failure_context(self: MainWindow, context: Mapping[str, object] | None) -> bool:
        context = self._coerce_mapping_payload(context)
        self.preview_pages_b64 = self._normalized_preview_pages_for_runtime(context.get('preview_pages_b64'))
        self.device_preview_pages_b64 = self._normalized_preview_pages_for_runtime(context.get('device_preview_pages_b64'))
        self._clear_font_preview_page_pixmap_cache()
        self._clear_device_preview_page_qimage_cache()
        self._apply_preview_page_cache_tokens_context(context)
        self.preview_pages_truncated = self._payload_bool_value(context, 'preview_pages_truncated', False)
        self.device_preview_pages_truncated = self._payload_bool_value(context, 'device_preview_pages_truncated', False)
        self.device_view_source = self._normalized_device_view_source_value(
            context.get('device_view_source', 'xtc'),
            default='xtc',
        )
        clear_device_page = self._payload_bool_value(context, 'clear_device_page', False)
        self.current_preview_page_index = preview_controller._clamp_preview_index(
            context.get('current_preview_page_index', 0),
            total=len(self.preview_pages_b64),
        )
        self.current_device_preview_page_index = preview_controller._clamp_preview_index(
            context.get('current_device_preview_page_index', 0),
            total=len(self.device_preview_pages_b64),
        )
        if self._effective_device_view_source(context.get('device_view_source', 'xtc')) != 'preview':
            self.current_device_preview_page_index = 0
        try:
            self._apply_profile_runtime_state()
        except Exception:
            pass
        self._set_current_xtc_display_name(self._preview_failure_display_name())
        restored_path = self._preview_failure_loaded_path()
        try:
            self.render_current_page(refresh_navigation=True)
        except Exception:
            if clear_device_page:
                self._clear_xtc_viewer_page(refresh_navigation=True)
            else:
                self.update_navigation_ui()
        preview_pages = self._runtime_preview_pages()
        preview_error_message = str(context.get('error_message', 'プレビュー生成エラー'))
        if preview_pages:
            try:
                self.render_current_preview_page()
            except Exception:
                self._show_preview_message(preview_error_message)
        else:
            self._show_preview_message(preview_error_message)
        self._update_preview_status_label(str(context.get('status_message', '')))
        try:
            self.update_navigation_ui()
        except Exception:
            pass
        try:
            if self._is_preview_display_active():
                self._clear_results_selection_with_fallback(
                    results_controller.build_results_clear_selection_context()
                )
            elif restored_path:
                self._sync_results_selection_for_loaded_path_with_fallback(restored_path)
            else:
                self._clear_results_selection_with_fallback(
                    results_controller.build_results_clear_selection_context()
                )
        except Exception:
            pass
        try:
            self._update_top_status()
        except Exception:
            pass
        return False

    def request_preview_refresh(
        self: MainWindow,
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
                finish_context = preview_controller.build_preview_finish_context()
                self._apply_preview_button_context(finish_context)
        finally:
            self._preview_running = False
            self._pending_preview_refresh_request = None

    def refresh_preview(self: MainWindow) -> None:
        self.request_preview_refresh(reset_page=False)

    def _current_viewer_profile(self: MainWindow) -> DeviceProfile:
        profile_key, profile, width, height = self._resolved_profile_and_dimensions()
        if profile_key != 'custom':
            return profile

        px_per_mm = max(1e-6, float(profile.ppi) / 25.4)
        screen_w_mm = width / px_per_mm
        screen_h_mm = height / px_per_mm
        body_w_ratio = profile.body_w_mm / max(profile.screen_w_mm, 1e-6)
        body_h_ratio = profile.body_h_mm / max(profile.screen_h_mm, 1e-6)
        return replace(
            profile,
            width_px=width,
            height_px=height,
            screen_w_mm=screen_w_mm,
            screen_h_mm=screen_h_mm,
            body_w_mm=screen_w_mm * body_w_ratio,
            body_h_mm=screen_h_mm * body_h_ratio,
        )

    def _preview_viewer_profile(self: MainWindow, payload: object = None) -> DeviceProfile:
        preview_profile = self._viewer_profile_for_preview_payload(payload)
        named_key = str(getattr(preview_profile, 'key', '') or '').strip().lower()
        if named_key and named_key != 'custom' and named_key in DEVICE_PROFILES:
            named_profile = DEVICE_PROFILES.get(named_key)
            if named_profile is not None:
                return named_profile
        width = max(0, int(getattr(preview_profile, 'width_px', 0) or 0))
        height = max(0, int(getattr(preview_profile, 'height_px', 0) or 0))
        for key in ('x4', 'x3'):
            profile = DEVICE_PROFILES.get(key)
            if profile and int(profile.width_px) == width and int(profile.height_px) == height:
                return profile
        if width > 0 and height > 0:
            return self._custom_viewer_profile_for_dimensions(width, height)
        return preview_profile

    def _loaded_xtc_document_viewer_profile(self: MainWindow) -> DeviceProfile | None:
        page_profile = self._viewer_profile_for_xtc_pages(self._runtime_xtc_pages())
        if page_profile is not None:
            return page_profile
        loaded_profile = self.__dict__.get('loaded_xtc_viewer_profile')
        if loaded_profile is not None:
            return loaded_profile
        return None

    def _refresh_loaded_xtc_viewer_profile_cache(self: MainWindow) -> DeviceProfile | None:
        profile = self._viewer_profile_for_xtc_pages(self._runtime_xtc_pages())
        self.loaded_xtc_viewer_profile = profile
        return profile

    def _sync_loaded_xtc_profile_ui_override(self: MainWindow) -> bool:
        document_profile = self._loaded_xtc_document_viewer_profile()
        if document_profile is None:
            self.loaded_xtc_profile_ui_override = False
            return False
        current_profile = self._current_viewer_profile()
        current_key = str(getattr(self, 'current_profile_key', '') or '').strip().lower()
        document_key = str(getattr(document_profile, 'key', '') or '').strip().lower()
        if current_key and current_key != 'custom':
            override = document_key != current_key
        else:
            override = (
                int(getattr(document_profile, 'width_px', 0) or 0) != int(getattr(current_profile, 'width_px', 0) or 0)
                or int(getattr(document_profile, 'height_px', 0) or 0) != int(getattr(current_profile, 'height_px', 0) or 0)
            )
        self.loaded_xtc_profile_ui_override = bool(override)
        return bool(override)

    def _active_device_viewer_profile(self: MainWindow, image: object = None) -> DeviceProfile:
        if self._effective_device_view_source() == 'preview':
            current_profile = self._current_viewer_profile()
            current_key = str(getattr(self, 'current_profile_key', '') or '').strip().lower()
            current_named_profile = None
            if current_key and current_key != 'custom':
                current_named_profile = DEVICE_PROFILES.get(current_key)

            preview_profile = self._preview_viewer_profile()

            candidate_image = image
            if candidate_image is None:
                viewer_widget = getattr(self, 'viewer_widget', None)
                candidate_image = getattr(viewer_widget, 'page_image', None) if viewer_widget is not None else None

            preview_width = max(0, int(getattr(preview_profile, 'width_px', 0) or 0))
            preview_height = max(0, int(getattr(preview_profile, 'height_px', 0) or 0))

            width, height = self._page_image_dimensions(candidate_image)
            if width > 0 and height > 0:
                if current_named_profile is not None:
                    if int(current_named_profile.width_px) == width and int(current_named_profile.height_px) == height:
                        return current_named_profile

                current_width = max(0, int(getattr(current_profile, 'width_px', 0) or 0))
                current_height = max(0, int(getattr(current_profile, 'height_px', 0) or 0))
                if current_width == width and current_height == height:
                    return current_profile

                if preview_width == width and preview_height == height:
                    return preview_profile

                for key in ('x4', 'x3'):
                    profile = DEVICE_PROFILES.get(key)
                    if profile and int(profile.width_px) == width and int(profile.height_px) == height:
                        return profile

                if preview_width > 0 and preview_height > 0:
                    return preview_profile
                return self._custom_viewer_profile_for_dimensions(width, height)

            if preview_width > 0 and preview_height > 0:
                return preview_profile

            if current_named_profile is not None:
                return current_named_profile

            current_width = max(0, int(getattr(current_profile, 'width_px', 0) or 0))
            current_height = max(0, int(getattr(current_profile, 'height_px', 0) or 0))
            if current_width > 0 and current_height > 0:
                return current_profile

            return current_profile

        if bool(getattr(self, 'loaded_xtc_profile_ui_override', False)):
            current_key = str(getattr(self, 'current_profile_key', '') or '').strip().lower()
            if current_key and current_key != 'custom':
                named_profile = DEVICE_PROFILES.get(current_key)
                if named_profile is not None:
                    return named_profile
            return self._current_viewer_profile()

        document_profile = self._loaded_xtc_document_viewer_profile()
        if document_profile is not None:
            if image is not None:
                width, height = self._page_image_dimensions(image)
                image_profile = self._viewer_profile_for_dimensions(width, height)
                if (
                    width > 0
                    and height > 0
                    and (
                        int(getattr(image_profile, 'width_px', 0) or 0) != int(getattr(document_profile, 'width_px', 0) or 0)
                        or int(getattr(image_profile, 'height_px', 0) or 0) != int(getattr(document_profile, 'height_px', 0) or 0)
                    )
                ):
                    return image_profile
            return document_profile
        if image is not None:
            return self._viewer_profile_for_page_image(image)
        return self._current_viewer_profile()

    def _font_preview_viewer_profile(self: MainWindow) -> DeviceProfile:
        preview_pages = self._runtime_preview_pages()
        if preview_pages:
            try:
                return self._preview_viewer_profile()
            except Exception:
                pass
        return self._current_viewer_profile()

    def _normalize_preview_zoom_pct(self: MainWindow, value: object = None) -> int:
        if value is None:
            value = self._safe_widget_value('preview_zoom_spin', 100)
        return studio_logic.normalize_preview_zoom_pct(value)

    def _preview_zoom_factor(self: MainWindow) -> float:
        return self._normalize_preview_zoom_pct() / 100.0

    def _actual_size_uses_preview_zoom_calibration(self: MainWindow) -> bool:
        return self._safe_widget_checked('actual_size_check')

    def _actual_size_calibration_factor(self: MainWindow) -> float:
        return studio_logic.build_actual_size_calibration_factor(
            uses_preview_zoom=self._actual_size_uses_preview_zoom_calibration(),
            preview_zoom_pct=self._safe_widget_value('preview_zoom_spin', 100),
            calibration_pct=self._safe_widget_value('calib_spin', 100),
        )

    def _sync_legacy_calibration_control_state(self: MainWindow) -> None:
        # sweep361: 実寸近似ON時の補正は右ペインの倍率UIへ集約する。
        # 既存設定との互換のため左側の実寸補正ウィジェットは保持し、
        # UI上は非表示にして二重操作に見えないようにする。
        for widget_name in ('calib_label', 'calib_down_btn', 'calib_spin', 'calib_up_btn', 'calib_help_btn'):
            widget = getattr(self, widget_name, None)
            if widget is None:
                continue
            try:
                widget.setVisible(False)
            except Exception:
                pass
            try:
                widget.setEnabled(False)
            except Exception:
                pass

    def _sync_preview_zoom_control_state(self: MainWindow) -> None:
        actual_size = self._actual_size_uses_preview_zoom_calibration()
        toggle_plan = gui_layouts.build_view_toggle_bar_plan()
        zoom_control_state = studio_logic.build_preview_zoom_control_state(
            toggle_plan,
            actual_size=actual_size,
            label_key='preview_zoom_actual_size_label_text' if actual_size else 'preview_zoom_label_text',
            tooltip_key='preview_zoom_actual_size_tooltip' if actual_size else 'preview_zoom_normal_tooltip',
        )
        label_text = zoom_control_state['label_text']
        tooltip = zoom_control_state['tooltip']
        label = getattr(self, 'preview_zoom_label', None)
        if label is not None:
            try:
                label.setText(label_text)
            except Exception:
                pass
            try:
                label.setToolTip(tooltip)
            except Exception:
                pass
        for widget_name in ('preview_zoom_down_btn', 'preview_zoom_spin', 'preview_zoom_up_btn'):
            widget = getattr(self, widget_name, None)
            if widget is None:
                continue
            try:
                widget.setEnabled(True)
            except Exception:
                pass
            try:
                widget.setToolTip(tooltip)
            except Exception:
                pass
        self._sync_legacy_calibration_control_state()

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

    def _sync_preview_size(self: MainWindow) -> None:
        self._sync_viewer_size()
        preview_label = getattr(self, 'preview_label', None)
        if preview_label is None:
            return
        target = self._safe_preview_layout_size(self._font_preview_target_size())
        try:
            preview_label.setMinimumSize(target)
        except Exception:
            APP_LOGGER.exception('フォントプレビューの最小サイズ更新に失敗しました')
        try:
            preview_label.updateGeometry()
        except Exception:
            APP_LOGGER.exception('フォントプレビューのレイアウト更新に失敗しました')

    def _sync_viewer_size(self: MainWindow) -> None:
        try:
            if hasattr(self.viewer_widget, 'set_preview_zoom_factor'):
                self.viewer_widget.set_preview_zoom_factor(self._preview_zoom_factor())
        except Exception:
            APP_LOGGER.exception('実機ビューの表示倍率更新に失敗しました')
        hint = self.viewer_widget.sizeHint()
        w, h = studio_logic.build_viewer_minimum_size(hint)
        try:
            self.viewer_widget.setMinimumSize(w, h)
        except Exception:
            APP_LOGGER.exception('実機ビューの最小サイズ更新に失敗しました')
        try:
            resize = getattr(self.viewer_widget, 'resize', None)
            if callable(resize):
                resize(w, h)
        except Exception:
            APP_LOGGER.exception('実機ビューの表示サイズ更新に失敗しました')
        try:
            self.viewer_widget.updateGeometry()
        except Exception:
            APP_LOGGER.exception('実機ビューのレイアウト更新に失敗しました')
        try:
            self.viewer_widget.update()
        except Exception:
            APP_LOGGER.exception('実機ビューの再描画要求に失敗しました')

    # ── ナビゲーション ─────────────────────────────────────

    def _update_nav_button_texts(self: MainWindow) -> None:
        if not hasattr(self, 'prev_btn') or not hasattr(self, 'next_btn'):
            return
        nav_bar_plan = gui_layouts.build_nav_bar_plan()
        prev_text = str(nav_bar_plan.get('prev_button_text', '前'))
        next_text = str(nav_bar_plan.get('next_button_text', '次'))
        if bool(getattr(self, 'nav_buttons_reversed', False)):
            self.prev_btn.setText(next_text)
            self.next_btn.setText(prev_text)
        else:
            self.prev_btn.setText(prev_text)
            self.next_btn.setText(next_text)

    def on_nav_reverse_toggled(self: MainWindow, checked: object) -> None:
        self.nav_buttons_reversed = bool(checked)
        self._update_nav_button_texts()
        self.update_navigation_ui()
        self.save_ui_state()

    def on_nav_button_clicked(self: MainWindow, logical_step: int) -> None:
        delta = -logical_step if bool(getattr(self, 'nav_buttons_reversed', False)) else logical_step
        self.change_page(delta)

    # ── XTCビューア: 状態 / ナビゲーション ─────────────────

    def _xtc_page_count(self: MainWindow) -> int:
        if self._effective_device_view_source() == 'preview':
            return len(self._runtime_device_preview_pages())
        return len(self._runtime_xtc_pages())

    def _normalized_device_preview_page_index(self: MainWindow, index: object = None, *, total: object = None) -> int:
        default_total = len(self._runtime_device_preview_pages())
        total_pages = default_total if total is None else worker_logic._int_config_value({'value': total}, 'value', default_total)
        raw_value = getattr(self, 'current_device_preview_page_index', 0) if index is None else index
        current_index = worker_logic._int_config_value({'value': raw_value}, 'value', 0)
        return studio_logic.normalize_navigation_index(total_pages, current_index)

    def _normalized_xtc_page_index(self: MainWindow, index: object = None, *, total: object = None) -> int:
        total_pages = self._xtc_page_count() if total is None else worker_logic._int_config_value({'value': total}, 'value', self._xtc_page_count())
        raw_value = getattr(self, 'current_page_index', 0) if index is None else index
        current_index = worker_logic._int_config_value({'value': raw_value}, 'value', 0)
        return studio_logic.normalize_navigation_index(total_pages, current_index)

    def _xtc_page_state_payload(self: MainWindow, index: object = None) -> dict[str, object]:
        if self._effective_device_view_source() == 'preview':
            pages = self._runtime_device_preview_pages()
            total = len(pages)
            current_index = self._normalized_device_preview_page_index(index, total=total)
            return studio_logic.build_xtc_page_state_payload(pages, current_index)
        pages = self._runtime_xtc_pages()
        total = len(pages)
        current_index = self._normalized_xtc_page_index(index, total=total)
        return studio_logic.build_xtc_page_state_payload(pages, current_index)

    def _xtc_navigation_payload(self: MainWindow) -> dict[str, object]:
        view_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        if view_mode == 'font':
            total = len(self._runtime_preview_pages())
            current_index = worker_logic._int_config_value({'value': getattr(self, 'current_preview_page_index', 0)}, 'value', 0)
            if total > 0:
                current_index = max(0, min(total - 1, current_index))
            else:
                current_index = 0
            payload = studio_logic.build_navigation_display_state(
                view_mode='font',
                total=total,
                current_index=current_index,
                truncated=bool(getattr(self, 'preview_pages_truncated', False)),
            )
            return payload

        is_preview = self._effective_device_view_source() == 'preview'
        if is_preview:
            total = len(self._runtime_device_preview_pages())
            current_index = self._normalized_device_preview_page_index(total=total)
            current_page = current_index + 1 if total > 0 else 0
        else:
            page_payload = self._xtc_page_state_payload()
            total = max(0, worker_logic._int_config_value(page_payload, 'total', 0))
            current_index = worker_logic._int_config_value(page_payload, 'current_index', 0)
            current_page = worker_logic._int_config_value(page_payload, 'current_page', 0)
        return studio_logic.build_device_navigation_payload(
            view_mode=view_mode,
            total=total,
            current_index=current_index,
            current_page=current_page,
            is_preview=is_preview,
            truncated=getattr(self, 'device_preview_pages_truncated', False),
        )

    def _apply_xtc_navigation_ui(self: MainWindow, payload: Mapping[str, object]) -> None:
        if not hasattr(self, 'prev_btn'):
            return
        total = max(0, self._payload_int_value(payload, 'total', 0))
        view_mode = str(payload.get('view_mode', 'device') or 'device').strip().lower()
        is_preview = self._effective_device_view_source() == 'preview'
        if is_preview:
            index_default = getattr(self, 'current_device_preview_page_index', 0)
            current_index = self._normalized_device_preview_page_index(payload.get('current_index', index_default), total=total)
        else:
            index_default = getattr(self, 'current_page_index', 0)
            current_index = self._normalized_xtc_page_index(payload.get('current_index', index_default), total=total)
        nav_state = studio_logic.build_navigation_display_state(
            view_mode=view_mode,
            total=total,
            current_index=current_index,
            truncated=False,
        )
        nav_state_mapping = nav_state if isinstance(nav_state, Mapping) else {}
        nav_bar_plan = gui_layouts.build_nav_bar_plan()
        total_label_format = nav_bar_plan.get('page_total_label_format', '/ {total}')
        fallback_total_label = total_label_format.format(total=total)
        apply_state = studio_logic.build_navigation_apply_state(
            payload,
            nav_state_mapping,
            total_label_format=total_label_format,
            nav_buttons_reversed=getattr(self, 'nav_buttons_reversed', False),
        )
        active = self._payload_bool_value(apply_state, 'active', False)
        current_page = self._payload_int_value(apply_state, 'current_page', 0)
        if view_mode != 'font':
            if is_preview:
                if getattr(self, 'current_device_preview_page_index', 0) != current_index:
                    self.current_device_preview_page_index = current_index
            elif getattr(self, 'current_page_index', 0) != current_index:
                self.current_page_index = current_index
                self._refresh_loaded_xtc_viewer_profile_cache()
        self.prev_btn.setEnabled(self._payload_bool_value(apply_state, 'prev_enabled', False))
        self.next_btn.setEnabled(self._payload_bool_value(apply_state, 'next_enabled', False))
        if hasattr(self, 'page_input'):
            self.page_input.setEnabled(active)
        if hasattr(self, 'page_total_label'):
            self.page_total_label.setText(str(apply_state.get('total_label', fallback_total_label)))
        if view_mode == 'font':
            current_preview_index = max(0, min(total - 1, current_index)) if total > 0 else 0
            if getattr(self, 'current_preview_page_index', 0) != current_preview_index:
                self.current_preview_page_index = current_preview_index
        self._reset_xtc_page_input(total, current_page)

    def update_navigation_ui(self: MainWindow) -> None:
        self._apply_xtc_navigation_ui(self._xtc_navigation_payload())

    def on_page_input_changed(self: MainWindow, value: int) -> None:
        if 'main_view_mode' in self.__dict__ and self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'font':
            pages = self._runtime_preview_pages()
            if pages:
                nav_state = studio_logic.build_navigation_input_state(
                    total=len(pages),
                    current_index=getattr(self, 'current_preview_page_index', 0),
                    input_page=value,
                )
                if self._payload_bool_value(nav_state, 'is_valid', False):
                    new_idx = self._payload_int_value(nav_state, 'target_index', 0)
                    if new_idx != getattr(self, 'current_preview_page_index', 0):
                        self.current_preview_page_index = new_idx
                        self.render_current_preview_page()
                    else:
                        self._sync_active_display_context_for_visible_page()
                    self.update_navigation_ui()
                    return
                self._sync_active_display_context_for_visible_page()
                self.update_navigation_ui()
                return
            self._sync_active_display_context_for_visible_page()
            self.update_navigation_ui()
            return

        is_device_preview = self._effective_device_view_source() == 'preview'
        total = len(self._runtime_device_preview_pages()) if is_device_preview else self._xtc_page_count()
        current_device_index = getattr(self, 'current_device_preview_page_index', 0) if is_device_preview else getattr(self, 'current_page_index', 0)
        nav_state = studio_logic.build_navigation_input_state(
            total=total,
            current_index=current_device_index,
            input_page=value,
        )
        if self._payload_bool_value(nav_state, 'is_valid', False):
            if is_device_preview:
                self._set_current_device_preview_page_index(
                    self._payload_int_value(nav_state, 'target_index', 0),
                    refresh_navigation=True,
                )
            else:
                self._set_current_page_index(
                    self._payload_int_value(nav_state, 'target_index', 0),
                    refresh_navigation=True,
                )
            return
        self._sync_active_display_context_for_visible_page()
        self.update_navigation_ui()

    def change_page(self: MainWindow, delta: int) -> None:
        if 'main_view_mode' in self.__dict__ and self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'font':
            pages = self._runtime_preview_pages()
            if pages:
                nav_state = studio_logic.build_navigation_delta_state(
                    total=len(pages),
                    current_index=getattr(self, 'current_preview_page_index', 0),
                    delta=delta,
                )
                new_idx = self._payload_int_value(nav_state, 'target_index', 0)
                if new_idx != getattr(self, 'current_preview_page_index', 0):
                    self.current_preview_page_index = new_idx
                    self.render_current_preview_page()
                else:
                    self._sync_active_display_context_for_visible_page()
                self.update_navigation_ui()
                return
            self._sync_active_display_context_for_visible_page()
            self.update_navigation_ui()
            return

        is_device_preview = self._effective_device_view_source() == 'preview'
        total = len(self._runtime_device_preview_pages()) if is_device_preview else self._xtc_page_count()
        if total <= 0:
            self._sync_active_display_context_for_visible_page()
            self.update_navigation_ui()
            return
        current_device_index = getattr(self, 'current_device_preview_page_index', 0) if is_device_preview else getattr(self, 'current_page_index', 0)
        nav_state = studio_logic.build_navigation_delta_state(
            total=total,
            current_index=current_device_index,
            delta=delta,
        )
        target_index = self._payload_int_value(nav_state, 'target_index', current_device_index)
        if is_device_preview:
            self._set_current_device_preview_page_index(target_index, refresh_navigation=True)
        else:
            self._set_current_page_index(target_index, refresh_navigation=True)

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
        if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) != 'font':
            return
        try:
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
        self._sync_preview_zoom_control_state()
        self._sync_preview_size()
        if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'font':
            self._refresh_font_preview_display_if_needed(refresh_navigation=False)
        self._finalize_setting_change()

    def on_night_toggled(self: MainWindow, checked: bool) -> None:
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

    def _request_preview_refresh_after_margin_change(self: MainWindow) -> bool:
        """Compatibility wrapper for margin-driven live preview refreshes."""
        return self._schedule_live_preview_refresh(reset_page=False)

    def on_margin_changed(self: MainWindow, value: int) -> None:
        self._apply_viewer_display_runtime_state()
        refreshed = self._request_preview_refresh_after_margin_change()
        if not refreshed:
            self._refresh_font_preview_display_if_needed()
        self._finalize_setting_change(refresh_preview=False)

    def on_threshold_changed(self: MainWindow, value: int) -> None:
        self._finalize_setting_change()

    def on_dither_toggled(self: MainWindow, checked: bool) -> None:
        self._apply_render_option_ui_state(checked)
        self._finalize_setting_change()

    def _on_kinsoku_mode_changed(self: MainWindow) -> None:
        self._schedule_live_preview_refresh(reset_page=False)
        self._finalize_setting_change(refresh_preview=False)

    def current_kinsoku_mode(self: MainWindow) -> str:
        if not hasattr(self, 'kinsoku_mode_combo'):
            return 'standard'
        value = str(self.kinsoku_mode_combo.currentData() or 'standard').strip().lower()
        return value if value in KINSOKU_MODE_LABELS else 'standard'

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
            return 'xtc'
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
        return 'xtc'

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
        if not hasattr(self, 'preset_combo'):
            return None
        key = self.preset_combo.currentData()
        if key:
            return str(key)
        idx = self.preset_combo.currentIndex()
        if idx >= 0:
            data = self.preset_combo.itemData(idx)
            if data:
                return str(data)
            text = self.preset_combo.itemText(idx).strip()
            if text.startswith('プリセット'):
                suffix = text.replace('プリセット', '').strip()
                if suffix.isdigit():
                    return f'preset_{suffix}'
        return None

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

    def _flush_pending_ui_changes(self: MainWindow) -> None:
        focus_widget = getattr(QApplication, 'focusWidget', None)
        current_focus = focus_widget() if callable(focus_widget) else None
        clear_focus = getattr(current_focus, 'clearFocus', None)
        process_events = getattr(QApplication, 'processEvents', None)

        if callable(clear_focus):
            try:
                clear_focus()
            except Exception:
                pass

        if callable(process_events):
            for _ in range(2):
                try:
                    process_events()
                except Exception:
                    break

    def _preset_combo_entries(self: MainWindow) -> tuple[tuple[str, object], ...]:
        combo = getattr(self, 'preset_combo', None)
        if combo is None or not hasattr(combo, 'count'):
            return ()
        entries: list[tuple[str, object]] = []
        try:
            count = int(combo.count())
        except Exception:
            return ()
        for index in range(max(0, count)):
            item_text = combo.itemText(index) if hasattr(combo, 'itemText') else ''
            item_data = combo.itemData(index) if hasattr(combo, 'itemData') else None
            entries.append((str(item_text or ''), item_data))
        return tuple(entries)

    def _live_preset_widget_payload(self: MainWindow) -> PresetDefinition:
        profile_widget_present = self.__dict__.get('profile_combo') is not None or 'current_profile_key' in self.__dict__
        dimension_widget_present = self.__dict__.get('width_spin') is not None or self.__dict__.get('height_spin') is not None

        selected_profile = None
        resolved_width = None
        resolved_height = None
        if profile_widget_present or dimension_widget_present:
            selected_profile = self._selected_profile_key()
            _profile_key, _profile, resolved_width, resolved_height = self._resolved_profile_and_dimensions(selected_profile)

        def _widget_value(name: str) -> object:
            widget = self.__dict__.get(name)
            if widget is None or not hasattr(widget, 'value'):
                return None
            try:
                return widget.value()
            except Exception:
                return None

        night_mode = None
        if self.__dict__.get('night_check') is not None:
            try:
                night_mode = bool(self.night_check.isChecked())
            except Exception:
                night_mode = None

        dither = None
        if self.__dict__.get('dither_check') is not None:
            try:
                dither = bool(self.dither_check.isChecked())
            except Exception:
                dither = None

        font_value = self.current_font_value() if self.__dict__.get('font_combo') is not None else None
        return settings_controller.build_live_preset_widget_payload(
            profile=selected_profile,
            width=resolved_width,
            height=resolved_height,
            font_size=_widget_value('font_size_spin'),
            ruby_size=_widget_value('ruby_size_spin'),
            line_spacing=_widget_value('line_spacing_spin'),
            margin_t=_widget_value('margin_t_spin'),
            margin_b=_widget_value('margin_b_spin'),
            margin_r=_widget_value('margin_r_spin'),
            margin_l=_widget_value('margin_l_spin'),
            threshold=_widget_value('threshold_spin'),
            night_mode=night_mode,
            dither=dither,
            kinsoku_mode=self.current_kinsoku_mode() if self.__dict__.get('kinsoku_mode_combo') is not None else None,
            output_format=self.current_output_format() if self.__dict__.get('output_format_combo') is not None else None,
            punctuation_position_mode=self.current_punctuation_position_mode() if self.__dict__.get('punctuation_position_combo') is not None else None,
            ichi_position_mode=self.current_ichi_position_mode() if self.__dict__.get('ichi_position_combo') is not None else None,
            lower_closing_bracket_position_mode=self.current_lower_closing_bracket_position_mode() if self.__dict__.get('lower_closing_bracket_position_combo') is not None else None,
            wave_dash_drawing_mode=self.current_wave_dash_drawing_mode() if self.__dict__.get('wave_dash_drawing_combo') is not None else None,
            wave_dash_position_mode=self.current_wave_dash_position_mode() if self.__dict__.get('wave_dash_position_combo') is not None else None,
            font_file=font_value,
            default_font_name=self._default_font_name(),
            allowed_profiles=DEVICE_PROFILES,
            allowed_kinsoku_modes=KINSOKU_MODE_LABELS,
            allowed_glyph_position_modes=GLYPH_POSITION_MODE_LABELS,
            allowed_output_formats=OUTPUT_FORMAT_LABELS,
            normalize_choice_value=self._normalize_choice_value,
            normalize_font_setting_value=self._normalize_font_setting_value,
        )

    def _preset_settings_prefix(self: MainWindow, key: str) -> str:
        return f'presets/{key}'

    def _normalize_preset_payload(
        self: MainWindow,
        payload: object,
        *,
        fallback: PresetDefinition | None = None,
        fallback_font: str = '',
        fallback_night_mode: bool = False,
        fallback_dither: bool = False,
        fallback_kinsoku_mode: str = 'standard',
        fallback_punctuation_position_mode: str = 'standard',
        fallback_ichi_position_mode: str = 'standard',
        fallback_lower_closing_bracket_position_mode: str = 'standard',
        fallback_wave_dash_drawing_mode: str = 'rotate',
        fallback_wave_dash_position_mode: str = 'standard',
        fallback_output_format: str = 'xtc',
    ) -> PresetDefinition:
        source = payload if isinstance(payload, dict) else {}
        fallback_payload = fallback if isinstance(fallback, dict) else {}
        normalized = dict(fallback_payload)
        normalized.update(source)

        default_font = self._default_font_name()
        font_fallback = self._normalize_font_setting_value(
            fallback_font or fallback_payload.get('font_file') or default_font,
            default_font,
        ) or default_font

        normalized['profile'] = self._normalize_choice_value(
            source.get('profile', fallback_payload.get('profile', 'x4')),
            'x4',
            DEVICE_PROFILES,
        )
        normalized['font_file'] = self._normalize_font_setting_value(
            source.get('font_file', fallback_payload.get('font_file')),
            font_fallback,
        ) or font_fallback

        numeric_defaults = {
            'font_size': 26,
            'ruby_size': 12,
            'line_spacing': 44,
            'margin_t': 12,
            'margin_b': 14,
            'margin_r': 12,
            'margin_l': 12,
            'width': 480,
            'height': 800,
        }
        for field, default in numeric_defaults.items():
            base_default = worker_logic._int_config_value(fallback_payload, field, default)
            normalized[field] = worker_logic._int_config_value(source, field, base_default)

        normalized['night_mode'] = worker_logic._bool_config_value(
            source,
            'night_mode',
            worker_logic._bool_config_value(fallback_payload, 'night_mode', bool(fallback_night_mode)),
        )
        normalized['dither'] = worker_logic._bool_config_value(
            source,
            'dither',
            worker_logic._bool_config_value(fallback_payload, 'dither', bool(fallback_dither)),
        )
        normalized['kinsoku_mode'] = self._normalize_choice_value(
            source.get('kinsoku_mode', fallback_payload.get('kinsoku_mode', fallback_kinsoku_mode)),
            'standard',
            KINSOKU_MODE_LABELS,
        )
        normalized['output_format'] = self._normalize_choice_value(
            source.get('output_format', fallback_payload.get('output_format', fallback_output_format)),
            'xtc',
            OUTPUT_FORMAT_LABELS,
        )
        normalized['punctuation_position_mode'] = self._normalize_choice_value(
            source.get('punctuation_position_mode', fallback_payload.get('punctuation_position_mode', fallback_punctuation_position_mode)),
            'standard',
            GLYPH_POSITION_MODE_LABELS,
        )
        normalized['ichi_position_mode'] = self._normalize_choice_value(
            source.get('ichi_position_mode', fallback_payload.get('ichi_position_mode', fallback_ichi_position_mode)),
            'standard',
            GLYPH_POSITION_MODE_LABELS,
        )
        normalized['lower_closing_bracket_position_mode'] = self._normalize_choice_value(
            source.get('lower_closing_bracket_position_mode', fallback_payload.get('lower_closing_bracket_position_mode', fallback_lower_closing_bracket_position_mode)),
            'standard',
            CLOSING_BRACKET_POSITION_MODE_LABELS,
        )
        normalized['wave_dash_drawing_mode'] = studio_logic.normalize_wave_dash_drawing_mode(
            source.get('wave_dash_drawing_mode', fallback_payload.get('wave_dash_drawing_mode', fallback_wave_dash_drawing_mode)),
            'rotate',
        )
        normalized['wave_dash_position_mode'] = studio_logic.normalize_wave_dash_position_mode(
            source.get('wave_dash_position_mode', fallback_payload.get('wave_dash_position_mode', fallback_wave_dash_position_mode)),
            'standard',
        )

        candidate_width = worker_logic._int_config_value(source, 'width', int(normalized['width']))
        candidate_height = worker_logic._int_config_value(source, 'height', int(normalized['height']))
        profile_key, _profile, resolved_width, resolved_height = self._resolved_profile_and_dimensions(
            normalized.get('profile', 'x4'),
            candidate_width,
            candidate_height,
        )
        normalized['profile'] = profile_key
        normalized['width'] = resolved_width
        normalized['height'] = resolved_height

        return normalized

    def _load_preset_definitions(self: MainWindow) -> PresetDefinitions:
        presets = deepcopy(DEFAULT_PRESET_DEFINITIONS)
        stored_font = self._normalize_font_setting_value(
            self._settings_default_value('font_file', self._default_font_name()),
            self._default_font_name(),
        ) or self._default_font_name()
        stored_night = worker_logic._bool_config_value({'night_mode': self._settings_default_value('night_mode', False)}, 'night_mode', False)
        stored_dither = worker_logic._bool_config_value({'dither': self._settings_default_value('dither', False)}, 'dither', False)
        stored_kinsoku_mode = self._normalize_choice_value(
            worker_logic._str_config_value({'kinsoku_mode': self._settings_default_value('kinsoku_mode', 'standard')}, 'kinsoku_mode', 'standard'),
            'standard',
            KINSOKU_MODE_LABELS,
        )
        stored_output_format = self._normalize_choice_value(
            worker_logic._str_config_value({'output_format': self._settings_default_value('output_format', 'xtc')}, 'output_format', 'xtc'),
            'xtc',
            OUTPUT_FORMAT_LABELS,
        )
        for key in list(presets):
            preset = presets[key]
            prefix = self._preset_settings_prefix(key)
            for field in PRESET_FIELDS:
                sk = f'{prefix}/{field}'
                if self._settings_contains_key(sk):
                    dv = preset.get(field)
                    preset[field] = self._settings_raw_value(sk, dv)
            presets[key] = self._normalize_preset_payload(
                preset,
                fallback=DEFAULT_PRESET_DEFINITIONS.get(key),
                fallback_font=stored_font,
                fallback_night_mode=bool(stored_night),
                fallback_dither=bool(stored_dither),
                fallback_kinsoku_mode=stored_kinsoku_mode,
                fallback_wave_dash_drawing_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_drawing_mode', 'rotate')),
                fallback_wave_dash_position_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_position_mode', 'standard')),
                fallback_output_format=stored_output_format,
            )
        return presets


    def _preset_display_name(self: MainWindow, p: PresetDefinition) -> str:
        return studio_logic.build_preset_display_name(p)

    def _preset_summary_plain_text(
        self: MainWindow,
        p: PresetDefinition,
        *,
        summary_tag: str = '',
        include_name_line: bool = True,
    ) -> str:
        font_text = core.describe_font_value(p.get('font_file') or self._default_font_name())
        return studio_logic.build_preset_summary_text(
            p,
            font_text=font_text,
            device_profile_keys=DEVICE_PROFILES.keys(),
            kinsoku_mode_labels=KINSOKU_MODE_LABELS,
            output_format_labels=OUTPUT_FORMAT_LABELS,
            summary_tag=summary_tag,
            include_name_line=include_name_line,
        )

    def _preset_summary_text(
        self: MainWindow,
        p: PresetDefinition,
        *,
        summary_tag: str = '',
        include_name_line: bool = True,
    ) -> str:
        font_text = core.describe_font_value(p.get('font_file') or self._default_font_name())
        return studio_logic.build_preset_summary_html(
            p,
            font_text=font_text,
            device_profile_keys=DEVICE_PROFILES.keys(),
            kinsoku_mode_labels=KINSOKU_MODE_LABELS,
            output_format_labels=OUTPUT_FORMAT_LABELS,
            summary_tag=summary_tag,
            include_name_line=include_name_line,
        )

    def _current_settings_summary_payload(self: MainWindow, key: str | None = None) -> PresetDefinition:
        selected_key = key or self.selected_preset_key()
        base_preset = dict(self.preset_definitions.get(selected_key) or {}) if selected_key else {}
        current_payload = dict(self.current_preset_payload())
        if base_preset:
            merged = dict(base_preset)
            merged.update(current_payload)
            return merged
        return current_payload

    def _preset_summary_label_measurement_width(self: MainWindow, label: object) -> int:
        """Return the best available real QLabel width for compact summary height."""
        candidate_widths: list[int] = []

        contents_rect_getter = getattr(label, 'contentsRect', None)
        if callable(contents_rect_getter):
            try:
                contents_width = int(contents_rect_getter().width())
                if contents_width > 0:
                    candidate_widths.append(contents_width)
            except Exception:
                pass

        label_width_getter = getattr(label, 'width', None)
        if callable(label_width_getter):
            try:
                label_width = int(label_width_getter())
                if label_width > 0:
                    candidate_widths.append(label_width)
            except Exception:
                pass

        parent_getter = getattr(label, 'parentWidget', None)
        parent = None
        if callable(parent_getter):
            try:
                parent = parent_getter()
            except Exception:
                parent = None
        parent_width_getter = getattr(parent, 'width', None)
        if callable(parent_width_getter):
            try:
                parent_width = int(parent_width_getter())
                if parent_width > 0:
                    margin_total = 0
                    layout_getter = getattr(parent, 'layout', None)
                    layout = None
                    if callable(layout_getter):
                        try:
                            layout = layout_getter()
                        except Exception:
                            layout = None
                    margins_getter = getattr(layout, 'contentsMargins', None)
                    if callable(margins_getter):
                        try:
                            margins = margins_getter()
                            margin_total = int(margins.left()) + int(margins.right())
                        except Exception:
                            margin_total = 0
                    candidate_widths.append(max(1, parent_width - margin_total))
            except Exception:
                pass

        reliable_widths = [width for width in candidate_widths if width >= 240]
        if reliable_widths:
            return max(reliable_widths)
        if candidate_widths:
            return max(candidate_widths)
        return 320

    def _queue_preset_summary_label_layout_retry(self: MainWindow) -> None:
        """Re-measure the preset summary after Qt has assigned the real label width."""
        if getattr(self, '_preset_summary_layout_retry_queued', False):
            return
        timer_single_shot = getattr(QTimer, 'singleShot', None)
        if not callable(timer_single_shot):
            return
        self._preset_summary_layout_retry_queued = True

        def _retry() -> None:
            self._preset_summary_layout_retry_queued = False
            self._update_preset_summary_label_layout(queue_retry=False)

        try:
            timer_single_shot(0, _retry)
        except Exception:
            self._preset_summary_layout_retry_queued = False

    def _update_preset_summary_label_layout(self: MainWindow, *, queue_retry: bool = True) -> None:
        label = getattr(self, 'preset_summary_label', None)
        if label is None:
            return
        text = ''
        text_getter = getattr(label, 'text', None)
        if callable(text_getter):
            try:
                text = str(text_getter() or '')
            except Exception:
                text = ''
        compact_text = studio_logic.compact_multiline_label_text(text)
        if compact_text != text:
            set_text = getattr(label, 'setText', None)
            if callable(set_text):
                try:
                    set_text(compact_text)
                    text = compact_text
                except Exception:
                    text = compact_text
            else:
                text = compact_text
        height = 0
        if text.strip():
            width_value = self._preset_summary_label_measurement_width(label)
            used_precise_metrics = False
            font_metrics_getter = getattr(label, 'fontMetrics', None)
            if callable(font_metrics_getter) and width_value > 0:
                try:
                    metrics = font_metrics_getter()
                    text_word_wrap = getattr(Qt, 'TextWordWrap', 0)
                    align_top = getattr(Qt, 'AlignTop', 0)
                    align_left = getattr(Qt, 'AlignLeft', 0)
                    flags = int(text_word_wrap) | int(align_top) | int(align_left)
                    line_spacing_value = 0
                    line_spacing_getter = getattr(metrics, 'lineSpacing', None)
                    if callable(line_spacing_getter):
                        try:
                            line_spacing_value = max(1, int(line_spacing_getter()))
                        except Exception:
                            line_spacing_value = 0
                    if line_spacing_value > 0:
                        measured_height = 0
                        for line in text.splitlines():
                            rect = metrics.boundingRect(QRect(0, 0, width_value, 10000), flags, line)
                            measured_height += max(line_spacing_value, int(rect.height()))
                        if measured_height > 0:
                            height = measured_height
                            used_precise_metrics = True
                    if height <= 0:
                        rect = metrics.boundingRect(QRect(0, 0, width_value, 10000), flags, text)
                        height = int(rect.height())
                        if height > 0:
                            used_precise_metrics = True
                except Exception:
                    height = 0
            if height <= 0:
                height_for_width = getattr(label, 'heightForWidth', None)
                if callable(height_for_width) and width_value > 0:
                    try:
                        height = int(height_for_width(width_value))
                    except Exception:
                        height = 0
            if height <= 0:
                size_hint = getattr(label, 'sizeHint', None)
                if callable(size_hint):
                    try:
                        height = int(size_hint().height())
                    except Exception:
                        height = 0
            if height > 0 and not used_precise_metrics:
                height = max(1, height - 2)
        fixed_height_applied = False
        if height > 0:
            set_fixed_height = getattr(label, 'setFixedHeight', None)
            if callable(set_fixed_height):
                try:
                    set_fixed_height(height)
                    fixed_height_applied = True
                except Exception:
                    fixed_height_applied = False
            if not fixed_height_applied:
                for setter_name in ('setMinimumHeight', 'setMaximumHeight'):
                    setter = getattr(label, setter_name, None)
                    if callable(setter):
                        try:
                            setter(height)
                        except Exception:
                            pass
        update_geometry = getattr(label, 'updateGeometry', None)
        if callable(update_geometry):
            update_geometry()
        if queue_retry:
            self._queue_preset_summary_label_layout_retry()

    def _sync_summary_payload(self: MainWindow, payload: PresetDefinition | None, *, summary_tag: str = '') -> None:
        if not hasattr(self, 'preset_summary_label') or not hasattr(self, 'preset_combo'):
            return
        if not payload:
            return
        summary = studio_logic.compact_multiline_label_text(
            self._preset_summary_plain_text(payload, summary_tag=summary_tag, include_name_line=False)
        )
        self.preset_summary_label.setText(summary)
        self.preset_combo.setToolTip(summary)
        self._update_preset_summary_label_layout()

    def _sync_current_settings_summary(self: MainWindow, key: str | None = None) -> None:
        summary_payload = self._current_settings_summary_payload(key)
        if not summary_payload:
            return
        self._sync_summary_payload(summary_payload, summary_tag='（現在の設定）')

    def _sync_selected_preset_summary(self: MainWindow, key: str | None = None) -> None:
        if not hasattr(self, 'preset_summary_label') or not hasattr(self, 'preset_combo'):
            return
        selected_key = key or self.selected_preset_key()
        preset = self.preset_definitions.get(selected_key) if selected_key else None
        if not preset:
            self.preset_summary_label.setText('')
            self.preset_combo.setToolTip('')
            return
        summary = studio_logic.compact_multiline_label_text(
            self._preset_summary_plain_text(preset, include_name_line=False)
        )
        self.preset_summary_label.setText(summary)
        self.preset_combo.setToolTip(summary)
        adjust = getattr(self.preset_summary_label, 'adjustSize', None)
        if callable(adjust):
            adjust()
        update = getattr(self.preset_summary_label, 'update', None)
        if callable(update):
            update()
        self._update_preset_summary_label_layout()

    def _refresh_preset_ui(self: MainWindow) -> None:
        if not hasattr(self, 'preset_combo'):
            return
        current_key = self.preset_combo.currentData()
        with _bulk_block_signals(self.preset_combo):
            self.preset_combo.clear()
            for key, p in self.preset_definitions.items():
                self.preset_combo.addItem(p['button_text'], key)
            if current_key:
                idx = self.preset_combo.findData(current_key)
                if idx >= 0:
                    self.preset_combo.setCurrentIndex(idx)
        self._sync_selected_preset_summary()

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

    def _request_preview_refresh_after_preset_apply(self: MainWindow) -> bool:
        """Run the same lightweight preview refresh as the Preview Update button once.

        Preset application touches many UI widgets at once.  The individual
        value-change signals are blocked during the bulk update, so this method
        intentionally performs a single manual preview refresh after the preset
        has fully settled.  Guarding on an instance-created preview button keeps headless unit
        stubs from accidentally invoking the heavy renderer before the UI has
        been built.
        """
        instance_attrs = getattr(self, '__dict__', {})
        has_preview_button = False
        if isinstance(instance_attrs, Mapping):
            has_preview_button = any(
                instance_attrs.get(name) is not None
                for name in ('preview_update_btn', 'preview_refresh_btn')
            )
        if not has_preview_button:
            return False
        refresh = getattr(self, 'manual_refresh_preview', None)
        if not callable(refresh):
            return False
        try:
            refresh()
            return True
        except Exception:
            try:
                APP_LOGGER.exception('プリセット適用後のプレビュー自動更新に失敗しました')
            except Exception:
                pass
            try:
                self.mark_preview_dirty()
            except Exception:
                pass
            return False

    def save_preset(self: MainWindow, key: str) -> None:
        p = self.preset_definitions.get(key)
        if not p:
            return
        payload = settings_controller.build_preset_save_payload(
            current_preset=self.current_preset_payload(),
            live_widget_payload=self._live_preset_widget_payload(),
        )
        summary_payload = settings_controller.build_preset_summary_payload(
            stored_preset=p,
            pending_payload=payload,
        )
        preset_name = self._preset_display_name(p)
        summary = self._preset_summary_plain_text(summary_payload)
        yes_button = getattr(QMessageBox, 'Yes', 1)
        no_button = getattr(QMessageBox, 'No', 0)
        ans = self._ask_question_dialog_with_status_fallback(
            'プリセット保存',
            f"現在の設定を{preset_name}へ保存しますか？\n\n{summary}",
            yes_button | no_button,
            yes_button,
            fallback_status_message='プリセット保存の確認ダイアログを表示できませんでした。',
            fallback_answer=no_button,
        )
        if ans != yes_button:
            return
        updated = deepcopy(p)
        updated.update(payload)
        self.preset_definitions[key] = updated
        prefix = self._preset_settings_prefix(key)
        for field, value in payload.items():
            self.settings_store.setValue(f'{prefix}/{field}', value)
        self.settings_store.sync()
        self._refresh_preset_ui()
        self._sync_selected_preset_summary(key)
        self._show_ui_status_message_unless_render_failure_visible(
            settings_controller.build_preset_status_message('save', preset_name),
            4000,
        )

    def apply_preset(self: MainWindow, key: str) -> None:
        p = self.preset_definitions.get(key)
        if not p:
            self._show_ui_status_message_unless_render_failure_visible(
                '適用するプリセットが見つかりませんでした。',
                3000,
            )
            return

        apply_context_obj = settings_controller.build_preset_apply_context(
            preset_key=key,
            stored_preset=p,
            fallback_preset=DEFAULT_PRESET_DEFINITIONS.get(key),
            fallback_font=self._default_font_name(),
            combo_entries=self._preset_combo_entries(),
            normalize_preset_payload=self._normalize_preset_payload,
            preset_display_name=self._preset_display_name,
        )
        apply_context = apply_context_obj if isinstance(apply_context_obj, Mapping) else {}
        idx = self._payload_optional_int_value(apply_context, 'combo_index')
        if idx is None:
            idx = -1
        preset_combo = getattr(self, 'preset_combo', None)
        if idx >= 0 and preset_combo is not None and preset_combo.currentIndex() != idx:
            with _bulk_block_signals(preset_combo):
                preset_combo.setCurrentIndex(idx)

        payload_obj = apply_context.get('payload', {})
        payload = dict(payload_obj) if isinstance(payload_obj, Mapping) else {}
        with _bulk_block_signals(*self._preset_apply_widgets()):
            self._apply_settings_payload_to_ui(payload)

        self._sync_loaded_xtc_profile_ui_override()
        self._apply_profile_runtime_state()
        self._apply_viewer_display_runtime_state()
        mode = getattr(self, 'main_view_mode', 'font')
        normalized_mode = self._normalized_main_view_mode(mode)
        self._refresh_preset_ui()
        self._finalize_setting_change(update_status=True)
        self._sync_selected_preset_summary(key)

        # sweep350: プリセット適用後の自動プレビュー更新は、手動の
        # 「プレビュー更新」と同じ経路を優先し、1回だけ走らせる。
        # これが使える実GUIでは、ここで古い runtime preview を先に再描画
        # しない。ヘッドレス/旧スタブで手動更新経路が無い場合だけ、従来の
        # 表示中ページ再描画へフォールバックする。
        auto_refresh_requested = self._request_preview_refresh_after_preset_apply()
        if not auto_refresh_requested:
            try:
                if normalized_mode == 'device':
                    self._refresh_active_view_after_mode_change(mode)
                elif self._runtime_preview_pages():
                    self._refresh_font_preview_display_if_needed()
                else:
                    self._refresh_font_preview_display_if_needed()
                    self._refresh_active_view_after_mode_change(mode)
            except Exception:
                pass

        status_message = _coerce_ui_message_text(apply_context.get('status_message'))
        self._show_ui_status_message_unless_render_failure_visible(status_message, 3000)

    # ── ファイル選択 ───────────────────────────────────────

    def select_target_path(self: MainWindow, as_file: bool) -> None:
        current = worker_logic.normalize_target_path_text(self.target_edit.text()) or str(Path.home())
        if as_file:
            path, _ = self._get_open_file_name_with_status_fallback(
                '変換対象を選択',
                current,
                'Supported (*.epub *.zip *.rar *.cbz *.cbr *.txt *.md *.markdown *.png *.jpg *.jpeg *.webp);;All Files (*.*)',
                fallback_status_message='変換対象のファイル選択ダイアログを開けませんでした。',
            )
        else:
            start_dir = current
            # 対象ファイルが入力済みの場合は、フォルダ選択ダイアログの
            # 初期位置だけ親フォルダへ寄せる。ここでは Path(current).parent を
            # 使わず、文字列だけで処理する。Windows では Path が "C:/..." を
            # "C:\\..." に変換するため、テストや保存値が揺れるうえ、将来の
            # stat 系呼び出し混入を見落としやすくなる。対象指定時は軽量処理に限定する。
            lower_current = current.lower()
            if lower_current.endswith((
                '.epub', '.zip', '.rar', '.cbz', '.cbr',
                '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
                '.xtc', '.xtch',
            )):
                slash_pos = max(current.rfind('/'), current.rfind('\\'))
                if slash_pos > 0:
                    start_dir = current[:slash_pos] or current
            path = self._get_existing_directory_with_status_fallback(
                '変換対象フォルダを選択',
                start_dir,
                fallback_status_message='変換対象フォルダの選択ダイアログを開けませんでした。',
            )
        if path:
            normalized_path = worker_logic.normalize_target_path_text(path)
            with _bulk_block_signals(getattr(self, 'target_edit', None)):
                self.target_edit.setText(normalized_path)
            self._update_top_status()
            self.save_ui_state()
            # ファイル／フォルダ指定直後はプレビューを更新する。
            # ただし handler 内では重い生成を直接走らせず、UI イベントループへ
            # 一度戻してから preview_page_limit_spin の指定ページ数だけを生成する。
            # 全文変換・本変換ルートへは入らない。
            self._schedule_target_preview_refresh(reset_page=True)

    def select_font_file(self: MainWindow) -> None:
        path, _ = self._get_open_file_name_with_status_fallback(
            'フォントファイルを選択',
            str(Path.home()),
            'Fonts (*.ttf *.ttc *.otf);;All Files (*.*)',
            fallback_status_message='フォントファイル選択ダイアログを開けませんでした。',
        )
        if path:
            preserved_night_mode = None
            if hasattr(self, 'night_check') and hasattr(self.night_check, 'isChecked'):
                try:
                    preserved_night_mode = bool(self.night_check.isChecked())
                except Exception:
                    preserved_night_mode = None
            normalized = self._normalize_font_setting_value(
                path,
                self.current_font_value() or self._default_font_name(),
            )
            if not normalized:
                return
            self._ensure_font_combo_value(normalized)
            self._set_current_font_value(normalized)
            if preserved_night_mode is not None and bool(self.night_check.isChecked()) != preserved_night_mode:
                self.night_check.setChecked(preserved_night_mode)
            self._finalize_setting_change()

    def current_font_value(self: MainWindow) -> str:
        if not hasattr(self, 'font_combo'):
            return ''
        value = self.font_combo.currentData()
        if value in (None, ''):
            value = self.font_combo.currentText()
        fallback = self._default_font_name() if hasattr(self, '_default_font_name') else ''
        normalized = self._normalize_font_setting_value(value, fallback)
        return normalized or fallback or str(value or '').strip()

    def _available_font_entries(self: MainWindow) -> list[dict[str, str]]:
        fonts = []
        for entry in core.get_font_entries():
            path_value, _font_index = core.parse_font_spec(entry.get('value', ''))
            lower = str(path_value).lower()
            if any(t in lower for t in ('msgothic', 'msmincho', 'ms gothic', 'ms mincho')):
                continue
            fonts.append({'label': str(entry.get('label', '')), 'value': str(entry.get('value', ''))})

        def sort_key(entry: dict):
            path_value, font_index = core.parse_font_spec(entry.get('value', ''))
            base = Path(path_value).name.lower()
            label = str(entry.get('label', '')).lower()

            def weight_priority(text: str) -> int:
                if 'thin' in text or 'hairline' in text:
                    return 0
                if 'extralight' in text or 'ultralight' in text or 'extra-light' in text or 'ultra-light' in text:
                    return 1
                if 'light' in text:
                    return 2
                if 'regular' in text or 'normal' in text or 'book' in text:
                    return 3
                if 'medium' in text:
                    return 4
                if 'demibold' in text or 'demi-bold' in text:
                    return 5
                if 'semibold' in text or 'semi-bold' in text:
                    return 6
                if 'bold' in text:
                    return 7
                if 'extrabold' in text or 'ultrabold' in text or 'extra-bold' in text or 'ultra-bold' in text:
                    return 8
                if 'black' in text or 'heavy' in text:
                    return 9
                return 50

            family_key = base
            for token in (
                'hairline', 'thin', 'ultralight', 'ultra-light', 'extralight', 'extra-light',
                'light', 'regular', 'normal', 'book', 'medium', 'demibold', 'demi-bold',
                'semibold', 'semi-bold', 'bold', 'extrabold', 'extra-bold', 'ultrabold',
                'ultra-bold', 'black', 'heavy'
            ):
                family_key = family_key.replace(token, '')
            family_key = family_key.replace('--', '-').replace('__', '_').replace('  ', ' ').strip(' -_')
            combined = f'{base} {label}'
            return (family_key or base, weight_priority(combined), base, label, int(font_index or 0))

        return sorted(fonts, key=sort_key)

    def _populate_font_combo(self: MainWindow) -> None:
        core.clear_font_entry_cache()
        self.font_combo.clear()
        for entry in self._available_font_entries():
            self.font_combo.addItem(entry['label'], entry['value'])

    def _missing_font_combo_label(self: MainWindow, font_value: str) -> str:
        path_value, _font_index = core.parse_font_spec(font_value)
        base_label = core.describe_font_value(font_value) or Path(path_value or font_value).name
        suffix = '（プリセット値 / 未検出）'
        if suffix in base_label:
            return base_label
        return f'{base_label}{suffix}'

    def _combo_find_data_index(self: MainWindow, combo: object, value: object) -> int:
        return _combo_find_data_index_for_widget(combo, value)

    def _ensure_font_combo_value(self: MainWindow, font_value: str) -> None:
        font_value = core.build_font_spec(*core.parse_font_spec(font_value))
        if not font_value or not hasattr(self, 'font_combo'):
            return
        if self._combo_find_data_index(self.font_combo, font_value) >= 0:
            return
        added = False
        path_value, _font_index = core.parse_font_spec(font_value)
        candidate_entries = core.get_font_entries_for_value(path_value or font_value)
        exact_detected = False
        for entry in candidate_entries:
            value = str(entry.get('value', '')).strip()
            if not value:
                continue
            if value == font_value:
                exact_detected = True
            if self._combo_find_data_index(self.font_combo, value) >= 0:
                continue
            self.font_combo.addItem(str(entry.get('label', value)), value)
            added = True
        if self._combo_find_data_index(self.font_combo, font_value) < 0:
            label = self._missing_font_combo_label(font_value) if not exact_detected else (core.describe_font_value(font_value) or Path(path_value or font_value).name)
            self.font_combo.addItem(label, font_value)
        elif added:
            ordered_entries = self._available_font_entries()
            ordered_values = {entry['value'] for entry in ordered_entries}
            existing_values = {self.font_combo.itemData(i): self.font_combo.itemText(i) for i in range(self.font_combo.count())}
            self.font_combo.clear()
            for entry in ordered_entries:
                self.font_combo.addItem(entry['label'], entry['value'])
            for value, label in existing_values.items():
                if value not in ordered_values:
                    self.font_combo.addItem(label, value)

    def _set_current_font_value(self: MainWindow, font_value: str) -> None:
        font_value = core.build_font_spec(*core.parse_font_spec(font_value))
        if not font_value or not hasattr(self, 'font_combo'):
            return
        preserved_night_mode = None
        if hasattr(self, 'night_check') and hasattr(self.night_check, 'isChecked'):
            try:
                preserved_night_mode = bool(self.night_check.isChecked())
            except Exception:
                preserved_night_mode = None
        self._ensure_font_combo_value(font_value)
        idx = self._combo_find_data_index(self.font_combo, font_value)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
            reset_popup_scroll = getattr(self.font_combo, '_reset_popup_scroll_to_top', None)
            if callable(reset_popup_scroll):
                reset_popup_scroll()
        if preserved_night_mode is not None and bool(self.night_check.isChecked()) != preserved_night_mode:
            self.night_check.setChecked(preserved_night_mode)

    def _default_font_name(self: MainWindow) -> str:
        preferred = ['NotoSansJP-SemiBold.ttf', 'NotoSansJP-SemiBold.otf', 'NotoSansJP-SemiBold.ttc']
        available = self._available_font_entries()
        for preferred_name in preferred:
            for entry in available:
                path_value, _font_index = core.parse_font_spec(entry['value'])
                base = Path(path_value).name
                label = entry['label'].lower()
                if base == preferred_name and (not preferred_name.lower().endswith('.ttc') or 'semibold' in label or 'semi-bold' in label):
                    return entry['value']
        for entry in available:
            if 'semibold' in entry['label'].lower():
                return entry['value']
        return available[0]['value'] if available else ''

    def _apply_default_font_selection(self: MainWindow) -> None:
        name = self._default_font_name()
        if name:
            self._set_current_font_value(name)

    def _update_top_status(self: MainWindow) -> None:
        if self.__dict__.get('worker') is not None:
            return
        _profile_key, profile, _width, _height = self._resolved_profile_and_dimensions(self._current_profile_key_or_default())
        message = studio_logic.build_top_status_message(
            worker_logic.normalize_target_path_text(self._safe_line_edit_text('target_edit')),
            profile.name,
            worker_logic._int_config_value({'font_size': self._safe_widget_value('font_size_spin', 26)}, 'font_size', 26),
            worker_logic._int_config_value({'line_spacing': self._safe_widget_value('line_spacing_spin', 44)}, 'line_spacing', 44),
        )
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
        width, height = self._effective_output_dimensions()
        defaults = DEFAULT_RENDER_SETTINGS
        return {
            'target': worker_logic.normalize_target_path_text(self._safe_line_edit_text('target_edit')),
            'font_file': self.current_font_value() if hasattr(self, 'current_font_value') else str(defaults['font_file']),
            'font_size': self._safe_widget_value('font_size_spin', defaults['font_size']),
            'ruby_size': self._safe_widget_value('ruby_size_spin', defaults['ruby_size']),
            'line_spacing': self._safe_widget_value('line_spacing_spin', defaults['line_spacing']),
            'margin_t': self._safe_widget_value('margin_t_spin', defaults['margin_t']),
            'margin_b': self._safe_widget_value('margin_b_spin', defaults['margin_b']),
            'margin_r': self._safe_widget_value('margin_r_spin', defaults['margin_r']),
            'margin_l': self._safe_widget_value('margin_l_spin', defaults['margin_l']),
            'dither': self._safe_widget_checked('dither_check', bool(defaults['dither'])),
            'threshold': self._safe_widget_value('threshold_spin', defaults['threshold']),
            'night_mode': self._safe_widget_checked('night_check', bool(defaults['night_mode'])),
            'kinsoku_mode': self.current_kinsoku_mode() if hasattr(self, 'current_kinsoku_mode') else str(defaults['kinsoku_mode']),
            'punctuation_position_mode': self.current_punctuation_position_mode() if hasattr(self, 'current_punctuation_position_mode') else str(defaults['punctuation_position_mode']),
            'ichi_position_mode': self.current_ichi_position_mode() if hasattr(self, 'current_ichi_position_mode') else str(defaults['ichi_position_mode']),
            'lower_closing_bracket_position_mode': self.current_lower_closing_bracket_position_mode() if hasattr(self, 'current_lower_closing_bracket_position_mode') else str(defaults['lower_closing_bracket_position_mode']),
            'wave_dash_drawing_mode': self.current_wave_dash_drawing_mode() if hasattr(self, 'current_wave_dash_drawing_mode') else str(defaults['wave_dash_drawing_mode']),
            'wave_dash_position_mode': self.current_wave_dash_position_mode() if hasattr(self, 'current_wave_dash_position_mode') else str(defaults['wave_dash_position_mode']),
            'output_format': self.current_output_format() if hasattr(self, 'current_output_format') else str(defaults['output_format']),
            'width': width,
            'height': height,
        }

    # ── 変換 ──────────────────────────────────────────────

    def current_settings_dict(self: MainWindow) -> WorkerConversionSettings:
        return settings_controller.build_current_settings_payload(
            render_settings_base=self._current_render_settings_base(),
            output_conflict=self.current_output_conflict_mode(),
            open_folder=self.open_folder_check.isChecked(),
        )

    def _folder_batch_worker_settings(
        self: MainWindow,
        source_path: object = None,
        output_path: object = None,
        item: object = None,
    ) -> WorkerConversionSettings:
        """Return current worker settings for one folder-batch item.

        The folder-batch worker bridge overrides target/output fields per item,
        so this hook deliberately avoids the normal single-file output-name
        prompt used by ``_prepare_conversion_settings()``.
        """
        return dict(self.current_settings_dict())

    def _window_state_save_payload(self: MainWindow) -> dict[str, object]:
        normal_geom = self.normalGeometry() if self.isMaximized() else self.geometry()
        raw_payload: dict[str, object] = {
            'window_width': int(normal_geom.width()),
            'window_height': int(normal_geom.height()),
            'is_maximized': bool(self.isMaximized()),
            'left_splitter_state': self.left_splitter.saveState(),
            'left_panel_visible': self.left_panel.isVisible(),
        }
        if not self.isMaximized():
            raw_payload['geometry'] = self.saveGeometry()
        sizes = self.main_splitter.sizes()
        left_panel_width = 0
        if sizes and sizes[0] > 0:
            left_panel_width = sizes[0]
        elif not self.left_panel.isVisible():
            pending_width = getattr(self, '_pending_left_panel_width', None)
            if pending_width and pending_width > 0:
                left_panel_width = pending_width
        if left_panel_width > 0:
            raw_payload['left_panel_width'] = left_panel_width
        left_splitter_sizes = self.left_splitter.sizes()
        if len(left_splitter_sizes) >= 2:
            raw_payload['left_splitter_top'] = left_splitter_sizes[0]
            raw_payload['left_splitter_bottom'] = left_splitter_sizes[1]
        return studio_logic.build_window_state_save_payload(raw_payload)

    def _settings_save_payload(self: MainWindow) -> dict[str, object]:
        ui_state = settings_controller.build_settings_save_ui_state(
            bottom_tab_index=int(self.bottom_tabs.currentIndex()),
            main_view_mode=getattr(self, 'main_view_mode', 'font'),
            ui_theme=str(getattr(self, 'current_ui_theme', 'light') or 'light'),
            panel_button_visible=bool(getattr(self, 'panel_button_visible', True)),
            preset_index=int(self.preset_combo.currentIndex()),
            preset_key=self.selected_preset_key() or '',
            profile=self._selected_profile_key(),
            actual_size=self.actual_size_check.isChecked(),
            show_guides=self.guides_check.isChecked(),
            calibration_pct=int(self.calib_spin.value()),
            nav_buttons_reversed=self.nav_reverse_check.isChecked(),
            preview_page_limit=self.preview_page_limit_spin.value() if hasattr(self, 'preview_page_limit_spin') else DEFAULT_PREVIEW_PAGE_LIMIT,
        )
        payload = settings_controller.build_settings_save_payload(
            current_settings=self.current_settings_dict(),
            ui_state=ui_state,
            allowed_view_modes={'font', 'device'},
            allowed_profiles=DEVICE_PROFILES,
            allowed_kinsoku_modes=KINSOKU_MODE_LABELS,
            allowed_glyph_position_modes=GLYPH_POSITION_MODE_LABELS,
            allowed_output_formats=OUTPUT_FORMAT_LABELS,
            allowed_output_conflicts=OUTPUT_CONFLICT_LABELS,
            default_preview_page_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
        )
        payload['preview_zoom_pct'] = self._normalize_preview_zoom_pct()
        return payload

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
        cfg = self.current_settings_dict()
        target_value = str(cfg.get('target', '')).strip()
        supported = self._supported_targets_for_path(target_value)
        is_file_target = Path(target_value).is_file() if target_value else False
        if not studio_logic.should_prompt_for_output_name(len(supported), is_file_target):
            return cfg

        current_name = ConversionWorker._sanitize_output_stem(self._settings_str_value('last_output_name', ''))
        default_name = self._default_output_name_for_target(supported[0])
        suggested = studio_logic.suggest_output_name_for_target(
            current_name,
            default_name,
            target_path=supported[0],
            last_output_source=self._settings_str_value('last_output_source', ''),
        )
        new_name, ok = QInputDialog.getText(
            self, '出力ファイル名', '保存する .xtc / .xtch のファイル名を入力してください', text=suggested,
        )
        if not ok:
            try:
                self._sync_active_display_context_for_visible_page()
            except Exception:
                pass
            try:
                self._show_ui_status_message_with_reflection_or_direct_fallback('変換をキャンセルしました。', 3000)
            except Exception:
                pass
            return None

        sanitized = ConversionWorker._sanitize_output_stem(new_name)
        if not sanitized:
            try:
                self._sync_active_display_context_for_visible_page()
            except Exception:
                pass
            self._show_warning_dialog_with_status_fallback('出力ファイル名', '空の名前は使えません。')
            return None

        cfg['output_name'] = sanitized
        self.settings_store.setValue('last_output_name', sanitized)
        try:
            self.settings_store.setValue('last_output_source', str(supported[0]))
        except Exception:
            APP_LOGGER.exception('最終出力名の入力元保存に失敗しました')
        self.settings_store.sync()
        return cfg

    def _preview_page_cache_token(self: MainWindow, page_b64: object) -> int:
        return preview_controller._preview_page_cache_token(page_b64)

    def _rebuild_preview_page_cache_tokens(self: MainWindow) -> None:
        self._preview_page_cache_tokens = preview_controller._preview_page_cache_tokens(
            self._runtime_preview_pages()
        )
        self._device_preview_page_cache_tokens = preview_controller._preview_page_cache_tokens(
            self._runtime_device_preview_pages()
        )

    def _clear_font_preview_page_pixmap_cache(self: MainWindow) -> None:
        cache = self.__dict__.get('_font_preview_page_pixmap_cache')
        if isinstance(cache, OrderedDict):
            cache.clear()
        else:
            self._font_preview_page_pixmap_cache = OrderedDict()

    def _font_preview_page_pixmap_cache_key(self: MainWindow, index: object = None) -> tuple[int, int] | None:
        pages = self._runtime_preview_pages()
        if not pages:
            return None
        current_index = worker_logic._int_config_value(
            {'value': self.__dict__.get('current_preview_page_index', 0) if index is None else index},
            'value',
            0,
        )
        current_index = max(0, min(len(pages) - 1, current_index))
        tokens = self.__dict__.get('_preview_page_cache_tokens')
        if not isinstance(tokens, list) or len(tokens) != len(pages):
            self._rebuild_preview_page_cache_tokens()
            tokens = self.__dict__.get('_preview_page_cache_tokens', [])
        token = int(tokens[current_index]) if current_index < len(tokens) else self._preview_page_cache_token(pages[current_index])
        return (current_index, token)

    def _cached_font_preview_page_pixmap(self: MainWindow, key: object) -> object | None:
        if key is None:
            return None
        cache = self.__dict__.get('_font_preview_page_pixmap_cache')
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict()
            self._font_preview_page_pixmap_cache = cache
        pixmap = cache.get(key)
        if pixmap is not None:
            cache.move_to_end(key)
        return pixmap

    def _store_font_preview_page_pixmap(self: MainWindow, key: object, pixmap: object) -> None:
        if key is None or pixmap is None:
            return
        cache = self.__dict__.get('_font_preview_page_pixmap_cache')
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict()
            self._font_preview_page_pixmap_cache = cache
        cache[key] = pixmap
        cache.move_to_end(key)
        while len(cache) > _FONT_PREVIEW_PAGE_PIXMAP_CACHE_LIMIT:
            cache.popitem(last=False)

    def _clear_xtc_page_qimage_cache(self: MainWindow) -> None:
        cache = self.__dict__.get('_xtc_page_qimage_cache')
        if isinstance(cache, OrderedDict):
            cache.clear()
        else:
            self._xtc_page_qimage_cache = OrderedDict()

    def _clear_device_preview_page_qimage_cache(self: MainWindow) -> None:
        cache = self.__dict__.get('_device_preview_page_qimage_cache')
        if isinstance(cache, OrderedDict):
            cache.clear()
        else:
            self._device_preview_page_qimage_cache = OrderedDict()

    def _device_preview_page_qimage_cache_key(self: MainWindow, index: object = None) -> tuple[int, int] | None:
        if self._effective_device_view_source(self.__dict__.get('device_view_source', 'xtc')) != 'preview':
            return None
        pages = self._runtime_device_preview_pages()
        if not pages:
            return None
        current_index = self._normalized_device_preview_page_index(
            self.__dict__.get('current_device_preview_page_index', 0) if index is None else index,
            total=len(pages),
        )
        tokens = self.__dict__.get('_device_preview_page_cache_tokens')
        if not isinstance(tokens, list) or len(tokens) != len(pages):
            self._rebuild_preview_page_cache_tokens()
            tokens = self.__dict__.get('_device_preview_page_cache_tokens', [])
        token = int(tokens[current_index]) if current_index < len(tokens) else self._preview_page_cache_token(pages[current_index])
        if token == 0:
            return None
        return (int(current_index), token)

    def _cached_device_preview_page_qimage(self: MainWindow, key: object) -> object | None:
        if key is None:
            return None
        cache = self.__dict__.get('_device_preview_page_qimage_cache')
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict()
            self._device_preview_page_qimage_cache = cache
        image = cache.get(key)
        if image is not None:
            cache.move_to_end(key)
        return image

    def _store_device_preview_page_qimage(self: MainWindow, key: object, image: object) -> None:
        if key is None or image is None:
            return
        cache = self.__dict__.get('_device_preview_page_qimage_cache')
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict()
            self._device_preview_page_qimage_cache = cache
        cache[key] = image
        cache.move_to_end(key)
        while len(cache) > _DEVICE_PREVIEW_PAGE_QIMAGE_CACHE_LIMIT:
            cache.popitem(last=False)

    def _xtc_page_qimage_cache_key(self: MainWindow, index: object = None) -> tuple[int, int, int] | None:
        if self._effective_device_view_source(self.__dict__.get('device_view_source', 'xtc')) != 'xtc':
            return None
        payload = self._xtc_page_state_payload(index)
        page = payload.get('page')
        if page is None:
            return None
        current_index = worker_logic._int_config_value(payload, 'current_index', 0)
        offset = max(0, worker_logic._int_config_value({'value': getattr(page, 'offset', 0)}, 'value', 0))
        length = max(0, worker_logic._int_config_value({'value': getattr(page, 'length', 0)}, 'value', 0))
        return (current_index, offset, length)

    def _cached_xtc_page_qimage(self: MainWindow, key: object) -> object | None:
        if not isinstance(key, tuple):
            return None
        cache = self.__dict__.get('_xtc_page_qimage_cache')
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict()
            self._xtc_page_qimage_cache = cache
        image = cache.get(key)
        if image is not None:
            cache.move_to_end(key)
        return image

    def _store_xtc_page_qimage(self: MainWindow, key: object, image: object) -> None:
        if not isinstance(key, tuple) or image is None:
            return
        cache = self.__dict__.get('_xtc_page_qimage_cache')
        if not isinstance(cache, OrderedDict):
            cache = OrderedDict()
            self._xtc_page_qimage_cache = cache
        cache[key] = image
        cache.move_to_end(key)
        while len(cache) > _XTC_PAGE_QIMAGE_CACHE_LIMIT:
            cache.popitem(last=False)

    def _clear_loaded_xtc_state(self: MainWindow) -> None:
        self.xtc_bytes = b''
        self.xtc_pages = []
        self._clear_xtc_page_qimage_cache()
        self.current_page_index = 0
        self.device_preview_pages_b64 = []
        self._clear_font_preview_page_pixmap_cache()
        self._clear_device_preview_page_qimage_cache()
        self._preview_page_cache_tokens = []
        self._device_preview_page_cache_tokens = []
        self.device_preview_pages_truncated = False
        self.current_device_preview_page_index = 0
        self.device_view_source = 'xtc'
        self.loaded_xtc_viewer_profile = None
        self.loaded_xtc_profile_ui_override = False
        self._loaded_xtc_display_name = None
        self._loaded_xtc_path_text = None
        self._set_current_xtc_display_name(None)
        self._clear_xtc_viewer_page(refresh_navigation=False)
        self.update_navigation_ui()

    def _set_current_xtc_display_name(self: MainWindow, display_name: object = None) -> None:
        if not hasattr(self, 'current_xtc_label'):
            return
        text = _coerce_ui_message_text(display_name, 'なし').strip() or 'なし'
        self.current_xtc_label.setText(studio_logic.build_displaying_document_label(text, fallback='なし'))

    def _set_current_xtc_display_name_with_fallback(self: MainWindow, display_name: object = None) -> bool:
        text = _coerce_ui_message_text(display_name, 'なし').strip() or 'なし'
        expected_label = studio_logic.build_displaying_document_label(text, fallback='なし')
        try:
            self._set_current_xtc_display_name(display_name)
        except Exception:
            pass
        if not hasattr(self, 'current_xtc_label'):
            return True
        if self._ui_widget_text(getattr(self, 'current_xtc_label', None)) == expected_label:
            return True
        try:
            self.current_xtc_label.setText(expected_label)
        except Exception:
            return False
        return self._ui_widget_text(getattr(self, 'current_xtc_label', None)) == expected_label

    def _sync_loaded_xtc_display_context_for_device_view(self: MainWindow) -> None:
        if self._effective_device_view_source() == 'preview':
            return
        if not self._runtime_xtc_pages():
            return
        path_text = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_path_text')).strip()
        display_name = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_display_name')).strip()
        if not display_name and path_text:
            display_name = worker_logic._normalized_path_text(self._xtc_display_name(path_text)).strip()
        if display_name:
            try:
                self._set_current_xtc_display_name_with_fallback(display_name)
            except Exception:
                pass
        if path_text:
            self._sync_results_selection_for_loaded_path_with_fallback(path_text)
        else:
            self._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )

    def _sync_preview_display_context_for_device_view(self: MainWindow) -> None:
        if self._effective_device_view_source() != 'preview':
            return
        if not self._runtime_device_preview_pages():
            return
        try:
            self._set_current_xtc_display_name_with_fallback('プレビュー')
        except Exception:
            pass
        self._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )

    def _sync_blank_device_display_context(self: MainWindow) -> None:
        try:
            self._set_current_xtc_display_name_with_fallback(None)
        except Exception:
            pass
        self._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )

    def _restore_shared_status_for_visible_display_context(self: MainWindow) -> None:
        try:
            view_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        except Exception:
            view_mode = 'font'
        replacement = ''
        stale_progress_status = False
        stale_status_bar = False
        current_progress_status = ''
        current_status_bar_status = ''
        replacement_is_render_failure = False
        if view_mode == 'font':
            preview_status_text = self._ui_widget_text(getattr(self, 'preview_status_label', None))
            preview_status_text_is_meaningful = bool(preview_status_text) and preview_status_text.startswith('プレビュー')
            try:
                preview_pages_visible = bool(self._runtime_preview_pages())
            except Exception:
                preview_pages_visible = False
            current_progress_status = self._ui_widget_text(getattr(self, 'progress_label', None))
            current_status_bar_status = self._status_bar_message_text()
            if not preview_pages_visible:
                active_preview_progress_failure = self._preview_render_failure_matches_visible_display_context(current_progress_status)
                active_preview_status_failure = self._preview_render_failure_matches_visible_display_context(current_status_bar_status)
                active_preview_label_failure = (
                    preview_status_text_is_meaningful
                    and self._preview_render_failure_matches_visible_display_context(preview_status_text)
                )
                if active_preview_label_failure:
                    replacement = preview_status_text
                elif preview_status_text_is_meaningful:
                    replacement = preview_status_text
                else:
                    return
                stale_progress_status = self._is_device_render_failure_status_text(current_progress_status) or (
                    self._is_preview_render_failure_status_text(current_progress_status)
                    and not active_preview_progress_failure
                )
                stale_status_bar = self._is_device_render_failure_status_text(current_status_bar_status) or (
                    self._is_preview_render_failure_status_text(current_status_bar_status)
                    and not active_preview_status_failure
                )
                replacement_is_render_failure = self._is_preview_render_failure_status_text(replacement)
            elif (
                self._is_preview_render_failure_status_text(preview_status_text)
                and self._preview_render_failure_matches_visible_display_context(preview_status_text)
            ):
                replacement = preview_status_text
            else:
                replacement = self._current_preview_render_status_message()
            if preview_pages_visible:
                stale_progress_status = self._is_device_render_failure_status_text(current_progress_status)
                stale_status_bar = self._is_device_render_failure_status_text(current_status_bar_status)
                replacement_is_render_failure = self._is_preview_render_failure_status_text(replacement)
        else:
            preview_source_active = self._normalized_device_view_source_value(
                getattr(self, 'device_view_source', 'xtc'),
                default='xtc',
            ) == 'preview'
            device_pages_visible = False
            if preview_source_active:
                try:
                    device_pages_visible = bool(self._runtime_device_preview_pages())
                except Exception:
                    device_pages_visible = False
            else:
                try:
                    device_pages_visible = bool(self._runtime_xtc_pages())
                except Exception:
                    device_pages_visible = False
            current_progress_status = self._ui_widget_text(getattr(self, 'progress_label', None))
            current_status_bar_status = self._status_bar_message_text()
            if preview_source_active and not device_pages_visible:
                preview_status_text = self._ui_widget_text(getattr(self, 'preview_status_label', None))
                active_preview_progress_failure = self._preview_render_failure_matches_visible_display_context(current_progress_status)
                active_preview_status_failure = self._preview_render_failure_matches_visible_display_context(current_status_bar_status)
                active_preview_label_failure = self._preview_render_failure_matches_visible_display_context(preview_status_text)
                for candidate, is_active_preview_failure in (
                    (current_progress_status, active_preview_progress_failure),
                    (current_status_bar_status, active_preview_status_failure),
                    (preview_status_text, active_preview_label_failure),
                ):
                    if is_active_preview_failure:
                        replacement = candidate
                        break
                if not replacement:
                    replacement = self._ui_widget_text(getattr(self, 'current_xtc_label', None))
                if not replacement:
                    return
                stale_progress_status = self._is_device_render_failure_status_text(current_progress_status) or (
                    self._is_preview_render_failure_status_text(current_progress_status)
                    and not active_preview_progress_failure
                )
                stale_status_bar = self._is_device_render_failure_status_text(current_status_bar_status) or (
                    self._is_preview_render_failure_status_text(current_status_bar_status)
                    and not active_preview_status_failure
                )
                replacement_is_render_failure = self._is_preview_render_failure_status_text(replacement)
            else:
                if not device_pages_visible:
                    return
                active_device_progress_failure = self._device_render_failure_matches_visible_display_context(current_progress_status)
                active_device_status_failure = self._device_render_failure_matches_visible_display_context(current_status_bar_status)
                for candidate, is_active_device_failure in (
                    (current_progress_status, active_device_progress_failure),
                    (current_status_bar_status, active_device_status_failure),
                ):
                    if is_active_device_failure:
                        replacement = candidate
                        break
                if not replacement:
                    replacement = self._ui_widget_text(getattr(self, 'current_xtc_label', None))
                stale_progress_status = self._is_preview_render_failure_status_text(current_progress_status) or (
                    self._is_device_render_failure_status_text(current_progress_status)
                    and not active_device_progress_failure
                )
                stale_status_bar = self._is_preview_render_failure_status_text(current_status_bar_status) or (
                    self._is_device_render_failure_status_text(current_status_bar_status)
                    and not active_device_status_failure
                )
                replacement_is_render_failure = self._is_device_render_failure_status_text(replacement)
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
                or not self._is_render_failure_status_text(current_status_bar_status)
            ):
                stale_progress_status = True
            if current_status_bar_status != replacement and (
                stale_status_bar
                or (
                    current_progress_status == replacement
                    and current_status_bar_status
                    and not self._is_render_failure_status_text(current_status_bar_status)
                )
            ):
                sync_status_bar_to_replacement = True
        elif view_mode == 'font':
            if self._is_preview_render_failure_status_text(current_progress_status):
                stale_progress_status = True
            if self._is_preview_render_failure_status_text(current_status_bar_status):
                sync_status_bar_to_replacement = True
        if stale_progress_status and hasattr(self, 'progress_label'):
            try:
                self.progress_label.setText(replacement)
            except Exception:
                pass
        if stale_progress_status or sync_status_bar_to_replacement:
            self._show_ui_status_message_direct_with_reflection_best_effort(replacement, 5000)

    def _sync_active_display_context_for_visible_page(self: MainWindow) -> None:
        try:
            view_mode = self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font'))
        except Exception:
            view_mode = 'font'
        if view_mode == 'font':
            if self._runtime_preview_pages():
                self._sync_preview_display_context_for_font_view()
            try:
                self._restore_shared_status_for_visible_display_context()
            except Exception:
                pass
            return
        if self._effective_device_view_source() == 'preview':
            if self._runtime_device_preview_pages():
                self._sync_preview_display_context_for_device_view()
            else:
                self._sync_blank_device_display_context()
            try:
                self._restore_shared_status_for_visible_display_context()
            except Exception:
                pass
            return
        if self._runtime_xtc_pages():
            self._sync_loaded_xtc_display_context_for_device_view()
            try:
                self._restore_shared_status_for_visible_display_context()
            except Exception:
                pass
            return
        self._sync_blank_device_display_context()
        try:
            self._restore_shared_status_for_visible_display_context()
        except Exception:
            pass

    def _set_worker_controls_running(self: MainWindow, running: bool) -> None:
        if hasattr(self, 'run_btn'):
            try:
                self.run_btn.setEnabled(not running)
            except Exception:
                pass
            try:
                self.run_btn.setText('変換中…' if running else '▶  変換実行')
            except Exception:
                pass
        if hasattr(self, 'stop_btn'):
            try:
                self.stop_btn.setEnabled(running)
            except Exception:
                pass

    def _prepare_conversion_ui_for_run(self: MainWindow, settings: WorkerConversionSettings) -> None:
        try:
            self._clear_results_view(studio_logic.build_running_results_summary())
        except Exception:
            pass
        try:
            self._clear_loaded_xtc_state()
        except Exception:
            pass
        self._set_worker_controls_running(True)
        target_count = len(self._supported_targets_for_path(str(settings.get('target', ''))))
        try:
            self._append_log_without_status_best_effort(
                studio_logic.build_start_log_message(self.current_output_format(), target_count),
            )
        except Exception:
            pass
        if hasattr(self, 'progress_bar'):
            try:
                self.progress_bar.setRange(0, 0)
                self.progress_bar.setValue(0)
            except Exception:
                pass
        if hasattr(self, 'progress_label'):
            try:
                self.progress_label.setText('変換中…')
            except Exception:
                pass
        if hasattr(self, 'busy_badge'):
            try:
                self.busy_badge.setText('変換中')
            except Exception:
                pass
        try:
            self._show_ui_status_message_with_reflection_or_direct_fallback('変換中…', None)
        except Exception:
            pass
        if hasattr(self, 'bottom_tabs'):
            try:
                self._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
            except Exception:
                pass

    def _apply_direct_conversion_terminal_fallback(
        self: MainWindow,
        message: object,
        *,
        badge_text: object,
        status_message: object = None,
        status_timeout: int | None = None,
    ) -> bool:
        normalized_message = _coerce_ui_message_text(message)
        normalized_badge_text = _coerce_ui_message_text(badge_text)
        status_text = normalized_message if status_message is None else _coerce_ui_message_text(status_message)
        terminal_visible = False
        if hasattr(self, 'progress_bar'):
            try:
                self.progress_bar.setRange(0, 1)
                self.progress_bar.setValue(0)
                terminal_visible = True
            except Exception:
                pass
        if hasattr(self, 'progress_label'):
            try:
                self.progress_label.setText(normalized_message)
                terminal_visible = True
            except Exception:
                pass
        if hasattr(self, 'busy_badge'):
            try:
                self.busy_badge.setText(normalized_badge_text)
                terminal_visible = True
            except Exception:
                pass
        status_visible = False
        try:
            if self._is_render_failure_status_text(status_text):
                status_visible = self._show_ui_status_message_direct_with_reflection_best_effort(
                    status_text,
                    status_timeout,
                )
            else:
                status_visible = bool(
                    self._show_ui_status_message_with_reflection_or_direct_fallback(
                        status_text,
                        status_timeout,
                        reuse_existing_message=False,
                    )
                )
        except Exception:
            status_visible = False
        if status_visible:
            terminal_visible = True
        return terminal_visible

    def _apply_conversion_terminal_state(
        self: MainWindow,
        message: str,
        *,
        badge_text: str,
        status_message: str | None = None,
        status_timeout: int | None = None,
    ) -> None:
        self._apply_direct_conversion_terminal_fallback(
            message,
            badge_text=badge_text,
            status_message=status_message,
            status_timeout=status_timeout,
        )

    def _load_xtc_from_path_with_result(self: MainWindow, path: object) -> bool:
        def _report_load_failure(exc: Exception) -> None:
            try:
                self._restore_results_selection_after_xtc_load_failure()
            except Exception:
                pass
            try:
                status_message = self._xtc_load_failure_status_message(path, exc)
            except Exception:
                target = worker_logic._normalized_path_text(path).strip() or '指定ファイル'
                detail = worker_logic._normalized_path_text(exc).strip() or '不明なエラー'
                status_message = f'XTC/XTCH読込失敗: {target} / {detail}'
            reflect_failure_in_status = True
            try:
                reflect_failure_in_status = not self._visible_render_failure_status_text()
            except Exception:
                reflect_failure_in_status = True
            try:
                self._append_log_with_status_fallback(
                    status_message,
                    reflect_in_status=reflect_failure_in_status,
                )
            except Exception:
                if reflect_failure_in_status:
                    try:
                        self._show_ui_status_message_with_reflection_or_direct_fallback(status_message, 5000)
                    except Exception:
                        pass

        loader = getattr(self, 'load_xtc_from_path', None)
        if not callable(loader):
            _report_load_failure(RuntimeError('読込処理を開始できませんでした。'))
            return False
        try:
            result = loader(path)
        except Exception as exc:
            _report_load_failure(exc)
            return False
        return result is not False

    def _show_conversion_results(
        self: MainWindow,
        converted_files: list[object],
        summary_lines: list[str] | None = None,
    ) -> None:
        self.populate_results(converted_files, summary_lines)
        context = self._resolved_result_load_context()
        resolved_path = context.get('resolved_path') if self._payload_bool_value(context, 'has_path', False) else None
        if not worker_logic._normalized_path_text(resolved_path).strip():
            fallback_state = results_controller.build_results_view_state(converted_files, summary_lines)
            entries = list(fallback_state.get('entries', []))
            initial_index = studio_logic.payload_optional_int_value(fallback_state, 'initial_index')
            if initial_index is not None and 0 <= initial_index < len(entries):
                resolved_path = entries[initial_index][1]
            elif entries:
                resolved_path = entries[0][1]
        result_tab_index = RESULT_TAB_INDEX
        if worker_logic._normalized_path_text(resolved_path).strip():
            if not self._load_xtc_from_path_with_result(resolved_path):
                result_tab_index = LOG_TAB_INDEX
        else:
            try:
                self._clear_loaded_xtc_state()
            except Exception:
                APP_LOGGER.exception('結果プレビュー状態クリアに失敗しました')
            selection_cleared = False
            self._clear_results_selection_with_fallback({'clear_selection': True})
        if hasattr(self, 'bottom_tabs'):
            try:
                self._set_bottom_tab_index_with_fallback(result_tab_index)
            except Exception:
                APP_LOGGER.exception('結果タブ切替に失敗しました')

    def _build_conversion_failure_summary_text(
        self: MainWindow,
        prefix: object,
        message: object,
    ) -> str:
        return studio_logic.build_conversion_failure_summary_text(prefix, message)

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
        clear_results_succeeded = False
        try:
            clear_results_succeeded = bool(self._clear_results_view(summary_text))
        except Exception:
            APP_LOGGER.exception(clear_results_error_context)
            clear_results_succeeded = False
        if not clear_results_succeeded:
            try:
                self._set_results_summary_text_with_fallback(summary_text)
            except Exception:
                pass
        try:
            self._clear_loaded_xtc_state()
        except Exception:
            APP_LOGGER.exception(clear_preview_error_context)
        selection_cleared = False
        try:
            self._clear_results_selection_with_fallback({'clear_selection': True})
        except Exception:
            APP_LOGGER.exception('%s_selection_direct', clear_results_error_context)
        if hasattr(self, 'progress_bar'):
            try:
                self.progress_bar.setRange(0, 1)
                self.progress_bar.setValue(0)
            except Exception:
                APP_LOGGER.exception(progress_error_context)
        try:
            self._append_log_without_status_or_status_bar(summary_text)
        except Exception:
            APP_LOGGER.exception(log_error_context)
        normalized_summary_text = _coerce_ui_message_text(summary_text)
        normalized_status_message = _coerce_ui_message_text(status_message, '不明なエラー')
        try:
            self._apply_conversion_terminal_state(
                normalized_summary_text,
                badge_text='エラー',
                status_message=normalized_status_message,
            )
        except Exception:
            APP_LOGGER.exception(terminal_state_error_context)
            self._apply_direct_conversion_terminal_fallback(
                normalized_summary_text,
                badge_text='エラー',
                status_message=normalized_status_message,
            )
        if hasattr(self, 'bottom_tabs'):
            try:
                self._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
            except Exception:
                APP_LOGGER.exception(tab_error_context)

    def _handle_conversion_startup_failure(self: MainWindow, message: object) -> None:
        self._clear_active_conversion_run_token()
        message_text = _coerce_ui_message_text(message, '不明なエラー')
        APP_LOGGER.error('変換開始エラー: %s', message_text)
        if self.worker:
            _safe_delete_qobject_later(self.worker, context='変換開始エラー時の worker 解放')
            self.worker = None
        if self.worker_thread:
            _safe_delete_qobject_later(self.worker_thread, context='変換開始エラー時の thread 解放')
            self.worker_thread = None
        try:
            self._set_worker_controls_running(False)
        except Exception:
            APP_LOGGER.exception('変換開始エラー時の実行中UI解除に失敗しました')
        failure_summary_text = self._build_conversion_failure_summary_text('開始エラー', message_text)
        self._apply_conversion_failure_ui(
            failure_summary_text,
            status_message=message_text,
            log_error_context='変換開始エラー時のログ追記に失敗しました',
            terminal_state_error_context='変換開始エラー時の終端状態反映に失敗しました',
            clear_results_error_context='変換開始エラー時の結果表示クリアに失敗しました',
            clear_preview_error_context='変換開始エラー時の実機ビュー状態クリアに失敗しました',
            progress_error_context='変換開始エラー時の進捗バー更新に失敗しました',
            tab_error_context='変換開始エラー時のタブ切替に失敗しました',
        )
        try:
            self._show_critical_dialog_with_status_fallback(
                '変換開始エラー',
                message_text,
                fallback_status_message=message_text,
            )
        except Exception:
            APP_LOGGER.exception('変換開始エラーダイアログの表示に失敗しました')

    def _next_conversion_run_token(self: MainWindow) -> int:
        try:
            current_token = int(self.__dict__.get('_conversion_run_token', 0) or 0)
        except Exception:
            current_token = 0
        token = current_token + 1
        self._conversion_run_token = token
        self._active_conversion_run_token = token
        return token

    def _clear_active_conversion_run_token(self: MainWindow) -> None:
        self._active_conversion_run_token = 0

    def _is_active_conversion_run_token(self: MainWindow, token: object) -> bool:
        try:
            token_value = int(token)
            active_token = int(self.__dict__.get('_active_conversion_run_token', 0) or 0)
        except Exception:
            return False
        return token_value == active_token

    def _connect_worker_dispatch_signals(self: MainWindow) -> None:
        if bool(self.__dict__.get('_worker_dispatch_signals_connected', False)):
            return
        self._worker_dispatch_signals_connected = True
        _connect_signal_best_effort(self._worker_finished_requested, self._dispatch_conversion_finished, queued=True)
        _connect_signal_best_effort(self._worker_error_requested, self._dispatch_conversion_error, queued=True)
        _connect_signal_best_effort(self._worker_log_requested, self._dispatch_worker_log, queued=True)
        _connect_signal_best_effort(self._worker_progress_requested, self._dispatch_conversion_progress, queued=True)
        _connect_signal_best_effort(self._worker_cleanup_requested, self._dispatch_worker_cleanup, queued=True)

    def _emit_worker_finished_request(self: MainWindow, run_token: object, result: object) -> None:
        if not bool(self.__dict__.get('_worker_dispatch_signals_connected', False)):
            self._dispatch_conversion_finished(run_token, cast(ConversionResult, result))
            return
        try:
            self._worker_finished_requested.emit(run_token, result)
        except Exception:
            self._dispatch_conversion_finished(run_token, cast(ConversionResult, result))

    def _emit_worker_error_request(self: MainWindow, run_token: object, message: object) -> None:
        if not bool(self.__dict__.get('_worker_dispatch_signals_connected', False)):
            self._dispatch_conversion_error(run_token, message)
            return
        try:
            self._worker_error_requested.emit(run_token, message)
        except Exception:
            self._dispatch_conversion_error(run_token, message)

    def _emit_worker_log_request(self: MainWindow, run_token: object, text: object) -> None:
        if not bool(self.__dict__.get('_worker_dispatch_signals_connected', False)):
            self._dispatch_worker_log(run_token, text)
            return
        try:
            self._worker_log_requested.emit(run_token, text)
        except Exception:
            self._dispatch_worker_log(run_token, text)

    def _emit_worker_progress_request(self: MainWindow, run_token: object, current: object, total: object, message: object) -> None:
        if not bool(self.__dict__.get('_worker_dispatch_signals_connected', False)):
            self._dispatch_conversion_progress(run_token, current, total, message)
            return
        try:
            self._worker_progress_requested.emit(run_token, current, total, message)
        except Exception:
            self._dispatch_conversion_progress(run_token, current, total, message)

    def _emit_worker_cleanup_request(self: MainWindow, expected_worker: object = None, expected_thread: object = None) -> None:
        if not bool(self.__dict__.get('_worker_dispatch_signals_connected', False)):
            self.cleanup_worker(expected_worker=expected_worker, expected_thread=expected_thread)
            return
        try:
            self._worker_cleanup_requested.emit(expected_worker, expected_thread)
        except Exception:
            self.cleanup_worker(expected_worker=expected_worker, expected_thread=expected_thread)

    def _dispatch_worker_cleanup(self: MainWindow, expected_worker: object = None, expected_thread: object = None) -> None:
        try:
            self.cleanup_worker(expected_worker=expected_worker, expected_thread=expected_thread)
        except Exception:
            APP_LOGGER.exception('worker後始末のUIスレッド反映に失敗しました')

    def _dispatch_worker_log(self: MainWindow, run_token: object, text: object) -> None:
        if not self._is_active_conversion_run_token(run_token):
            return
        try:
            self._append_log_without_status_best_effort(_coerce_ui_message_text(text, '').rstrip())
        except Exception:
            APP_LOGGER.exception('workerログのUI反映に失敗しました')

    def _dispatch_conversion_progress(self: MainWindow, run_token: object, current: object, total: object, message: object) -> None:
        if not self._is_active_conversion_run_token(run_token):
            return
        try:
            self.update_conversion_progress(current, total, message)
        except Exception:
            APP_LOGGER.exception('worker進捗のUI反映に失敗しました')

    def _dispatch_conversion_finished(self: MainWindow, run_token: object, result: ConversionResult) -> None:
        if not self._is_active_conversion_run_token(run_token):
            return
        try:
            self.on_conversion_finished(result)
        except Exception:
            APP_LOGGER.exception('worker完了シグナルのUI反映に失敗しました')

    def _dispatch_conversion_error(self: MainWindow, run_token: object, message: object) -> None:
        if not self._is_active_conversion_run_token(run_token):
            return
        try:
            self.on_conversion_error(_coerce_ui_message_text(message, '不明なエラー'))
        except Exception:
            APP_LOGGER.exception('workerエラーシグナルのUI反映に失敗しました')

    def start_conversion(self: MainWindow) -> None:
        cfg = self._prepare_conversion_settings()
        if not cfg:
            return
        if not self._check_conversion_dependencies(cfg):
            return
        self._prepare_conversion_ui_for_run(cfg)

        worker_thread = None
        worker = None
        run_token = self._next_conversion_run_token()
        try:
            worker_thread = QThread(self)
            self.worker_thread = worker_thread
            worker = ConversionWorker(cfg)
            self.worker = worker
            worker.moveToThread(worker_thread)
            worker_thread.started.connect(worker.run)
            worker.finished.connect(lambda result, token=run_token: self._emit_worker_finished_request(token, result))
            worker.error.connect(lambda message, token=run_token: self._emit_worker_error_request(token, message))
            worker.log.connect(lambda text, token=run_token: self._emit_worker_log_request(token, text))
            worker.progress.connect(lambda current, total, message, token=run_token: self._emit_worker_progress_request(token, current, total, message))
            if hasattr(worker, 'deleteLater'):
                worker.finished.connect(worker.deleteLater)
                worker.error.connect(worker.deleteLater)
            worker.finished.connect(worker_thread.quit)
            worker.error.connect(worker_thread.quit)
            worker_thread.finished.connect(
                lambda worker_ref=worker, thread_ref=worker_thread: self._emit_worker_cleanup_request(worker_ref, thread_ref)
            )
            worker_thread.start()
        except Exception as exc:
            if self.__dict__.get('worker_thread') is None and worker_thread is not None:
                _safe_delete_qobject_later(worker_thread, context='変換開始失敗時の thread 解放')
            if self.__dict__.get('worker') is None and worker is not None:
                _safe_delete_qobject_later(worker, context='変換開始失敗時の worker 解放')
            self._handle_conversion_startup_failure(str(exc))

    def stop_conversion(self: MainWindow) -> None:
        if not self.worker:
            return
        try:
            self.worker.stop()
        except Exception as exc:
            message_text = _coerce_ui_message_text(exc, str(exc)).strip() or '不明なエラー'
            APP_LOGGER.exception('停止要求の送信に失敗しました')
            log_message = f'停止要求の送信に失敗しました: {message_text}'
            helper_succeeded = False
            try:
                helper_succeeded = bool(self._append_log_without_status_best_effort(log_message))
            except Exception:
                helper_succeeded = False
            if not helper_succeeded:
                try:
                    self._show_ui_status_message_with_reflection_or_direct_fallback(log_message, 5000)
                except Exception:
                    pass
            return
        try:
            stop_btn = getattr(self, 'stop_btn', None)
            if stop_btn is not None:
                stop_btn.setEnabled(False)
        except Exception:
            APP_LOGGER.exception('停止ボタンの更新に失敗しました')
        log_message = '停止要求を送りました。現在の変換単位が終わりしだい停止します。'
        helper_succeeded = False
        try:
            helper_succeeded = bool(self._append_log_without_status_best_effort(log_message))
        except Exception:
            helper_succeeded = False
        if not helper_succeeded:
            try:
                APP_LOGGER.warning('停止ログを通常ログへ追記できなかったため status helper にフォールバックします')
            except Exception:
                pass
            try:
                self._show_ui_status_message_with_reflection_or_direct_fallback(log_message, 5000)
            except Exception:
                pass

    def _schedule_cleanup_worker(
        self: MainWindow,
        expected_worker: object = None,
        expected_thread: object = None,
    ) -> None:
        callback = self.cleanup_worker
        if expected_worker is not None or expected_thread is not None:
            callback = lambda worker=expected_worker, thread=expected_thread: self.cleanup_worker(
                expected_worker=worker,
                expected_thread=thread,
            )
        try:
            QTimer.singleShot(0, callback)
        except Exception:
            callback()

    def cleanup_worker(
        self: MainWindow,
        *,
        expected_worker: object = None,
        expected_thread: object = None,
    ) -> None:
        active_worker = getattr(self, 'worker', None)
        active_thread = getattr(self, 'worker_thread', None)
        worker_ref = expected_worker if expected_worker is not None else active_worker
        thread_ref = expected_thread if expected_thread is not None else active_thread

        if expected_worker is None or active_worker is expected_worker:
            self.worker = None
        if expected_thread is None or active_thread is expected_thread:
            self.worker_thread = None

        # worker.finished で worker.deleteLater が既に予約済みのことがあるため、
        # 二重 deleteLater や破棄済み wrapper 参照で完了直後に落ちないよう安全化する。
        _safe_delete_qobject_later(worker_ref, context='worker後始末')
        _safe_delete_qobject_later(thread_ref, context='thread後始末')

        if getattr(self, 'worker', None) is None and getattr(self, 'worker_thread', None) is None:
            try:
                self._set_worker_controls_running(False)
            except Exception:
                APP_LOGGER.exception('worker後始末後のUI解除に失敗しました')

    def _merge_results_summary_lines_with_warnings(
        self: MainWindow,
        summary_lines: object,
        warning_values: object,
    ) -> list[object]:
        return worker_logic.merge_postprocess_warnings_into_summary_lines(
            summary_lines,
            warning_values,
        )

    def _merge_results_summary_lines_and_collect_warnings(
        self: MainWindow,
        summary_lines: object,
        collected_warnings: object,
        warning_values: object,
    ) -> tuple[object, list[str]]:
        merged_warnings = studio_logic.merge_unique_message_values(
            worker_logic.coerce_postprocess_warning_messages(collected_warnings),
            worker_logic.coerce_postprocess_warning_messages(warning_values),
        )
        if not merged_warnings:
            return summary_lines, []
        return (
            self._merge_results_summary_lines_with_warnings(summary_lines, merged_warnings),
            merged_warnings,
        )

    def _build_results_summary_text(
        self: MainWindow,
        paths: object,
        summary_lines: object = None,
        *,
        fallback: object = None,
    ) -> str:
        try:
            context = results_controller.build_results_apply_context(paths, summary_lines)
            summary_text = _coerce_ui_message_text(context.get('summary_text')).strip()
            if summary_text:
                return summary_text
        except Exception:
            pass
        return _coerce_ui_message_text(fallback).strip()

    def _append_conversion_finish_error_log_with_fallback(
        self: MainWindow,
        log_message: object,
        *,
        status_timeout_ms: int = 5000,
    ) -> bool:
        helper_succeeded = False
        try:
            helper_succeeded = bool(
                self._append_log_without_status_with_optional_status_fallback(
                    log_message,
                    allow_status_fallback=False,
                    status_timeout_ms=status_timeout_ms,
                )
            )
        except Exception:
            helper_succeeded = False
        if helper_succeeded:
            return True
        try:
            return bool(
                self._append_log_without_status_with_optional_status_fallback(
                    log_message,
                    allow_status_fallback=True,
                    status_timeout_ms=status_timeout_ms,
                )
            )
        except Exception:
            return False

    def _handle_conversion_finish_ui_error(
        self: MainWindow,
        msg: str,
        exc: object,
        *,
        context: str,
        badge_text: str = '完了',
        clear_results: bool = False,
    ) -> bool:
        error_text = _coerce_ui_message_text(exc, str(exc)).strip() or '不明なエラー'
        APP_LOGGER.exception('変換完了後の %s でエラーが発生しました', context)
        log_message = f'{context}エラー: {error_text}'
        helper_succeeded = bool(
            self._append_conversion_finish_error_log_with_fallback(
                log_message,
                status_timeout_ms=5000,
            )
        )
        status_message = f'{msg} / {context}エラー: {error_text}'
        terminal_visible = False
        if clear_results:
            clear_summary_text = f'{msg}\n{context}エラー: {error_text}'
            clear_results_succeeded = False
            try:
                clear_results_succeeded = bool(self._clear_results_view(clear_summary_text))
            except Exception:
                clear_results_succeeded = False
            if not clear_results_succeeded:
                try:
                    self._set_results_summary_text_with_fallback(clear_summary_text)
                except Exception:
                    pass
            try:
                self._clear_loaded_xtc_state()
            except Exception:
                pass
            selection_cleared = False
            self._clear_results_selection_with_fallback({'clear_selection': True})
        terminal_visible = bool(
            self._apply_direct_conversion_terminal_fallback(
                msg,
                badge_text=badge_text,
                status_message=status_message,
                status_timeout=5000,
            )
        )
        if clear_results and hasattr(self, 'bottom_tabs'):
            try:
                self._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
            except Exception:
                pass
        return bool(helper_succeeded or terminal_visible)


    def _append_log_without_status(self: MainWindow, text: object) -> bool:
        message = _coerce_ui_message_text(text)
        if not message:
            return False
        try:
            self.append_log(message, reflect_in_status=False)
            return True
        except TypeError:
            pass
        except Exception:
            pass
        try:
            APP_LOGGER.info(message)
        except Exception:
            pass
        try:
            if hasattr(self, 'log_edit'):
                self.log_edit.append(message)
                return True
        except Exception:
            pass
        try:
            log_widget = getattr(self, 'log_edit', None)
            if log_widget is not None and hasattr(log_widget, 'append'):
                log_widget.append(message)
                return True
        except Exception:
            pass
        return False

    def _append_log_with_status_fallback(
        self: MainWindow,
        text: object,
        *,
        reflect_in_status: bool = False,
        status_timeout_ms: int = 5000,
    ) -> bool:
        message = _coerce_ui_message_text(text)
        if not message:
            return False
        try:
            self.append_log(message, reflect_in_status=reflect_in_status)
            return True
        except TypeError:
            pass
        except Exception:
            pass
        append_log_succeeded = False
        try:
            append_log_succeeded = bool(self._append_log_without_status(message))
        except Exception:
            append_log_succeeded = False
            try:
                self.append_log(message, reflect_in_status=False)
                append_log_succeeded = True
            except TypeError:
                pass
            except Exception:
                pass
            if not append_log_succeeded:
                try:
                    APP_LOGGER.info(message)
                except Exception:
                    pass
                try:
                    log_widget = getattr(self, 'log_edit', None)
                    if log_widget is not None and hasattr(log_widget, 'append'):
                        log_widget.append(message)
                        append_log_succeeded = True
                except Exception:
                    pass
        if reflect_in_status or not append_log_succeeded:
            try:
                if self._is_render_failure_status_text(message):
                    if self._show_ui_status_message_direct_with_reflection_best_effort(message, status_timeout_ms):
                        return True
            except Exception:
                pass
            try:
                if self._show_ui_status_message_with_reflection_or_direct_fallback(message, status_timeout_ms):
                    return True
            except Exception:
                pass
        return append_log_succeeded

    def _append_log_without_status_best_effort(self: MainWindow, text: object) -> bool:
        message = _coerce_ui_message_text(text)
        if not message:
            return False
        helper = getattr(self, '_append_log_with_status_fallback', None)
        if callable(helper):
            try:
                helper_result = helper(message, reflect_in_status=False)
                if helper_result is not False:
                    return True
            except TypeError:
                try:
                    helper_result = helper(message)
                    if helper_result is not False:
                        return True
                except Exception:
                    pass
            except Exception:
                pass
        fallback_helper = getattr(self, '_append_log_without_status', None)
        if callable(fallback_helper):
            try:
                if bool(fallback_helper(message)):
                    return True
            except Exception:
                pass
        try:
            self.append_log(message, reflect_in_status=False)
            return True
        except TypeError:
            pass
        except Exception:
            pass
        try:
            APP_LOGGER.info(message)
        except Exception:
            pass
        try:
            log_widget = getattr(self, 'log_edit', None)
            if log_widget is not None and hasattr(log_widget, 'append'):
                log_widget.append(message)
                return True
        except Exception:
            pass
        return False

    def _append_log_without_status_or_status_bar(
        self: MainWindow,
        text: object,
        *,
        status_timeout_ms: int = 5000,
    ) -> bool:
        message = _coerce_ui_message_text(text)
        if not message:
            return False
        try:
            if self._append_log_without_status_best_effort(message):
                return True
        except Exception:
            pass
        try:
            if self._show_ui_status_message_with_reflection_or_direct_fallback(message, status_timeout_ms):
                return True
        except Exception:
            pass
        return False

    def _append_log_without_status_with_optional_status_fallback(
        self: MainWindow,
        log_message: object,
        *,
        allow_status_fallback: bool = False,
        status_timeout_ms: int = 5000,
    ) -> bool:
        message_text = _coerce_ui_message_text(log_message)
        if not message_text:
            return False
        try:
            if allow_status_fallback:
                return bool(
                    self._append_log_without_status_or_status_bar(
                        message_text,
                        status_timeout_ms=status_timeout_ms,
                    )
                )
            return bool(self._append_log_without_status_best_effort(message_text))
        except Exception:
            return False

    def _emit_postprocess_warning(
        self: MainWindow,
        warning_message: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> bool:
        message = _coerce_ui_message_text(warning_message).strip()
        if not message:
            return False
        try:
            APP_LOGGER.warning('非致命後処理警告: %s', message)
        except Exception:
            pass
        helper_succeeded = False
        try:
            helper_succeeded = bool(self._append_log_without_status_best_effort(message))
        except Exception:
            helper_succeeded = False
        if show_status and not helper_succeeded:
            try:
                helper_succeeded = bool(
                    self._append_log_without_status_or_status_bar(
                        message,
                        status_timeout_ms=duration_ms,
                    )
                )
            except Exception:
                helper_succeeded = False
        if not show_status:
            return helper_succeeded
        status_succeeded = False
        try:
            status_succeeded = bool(
                self._show_ui_status_message_with_reflection_or_direct_fallback(
                    message,
                    duration_ms,
                )
            )
        except Exception:
            status_succeeded = False
        return bool(helper_succeeded or status_succeeded)

    def _emit_postprocess_warning_via_log_and_optional_status_fallback(
        self: MainWindow,
        warning_message: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> bool:
        message_text = _coerce_ui_message_text(warning_message).strip()
        if not message_text:
            return False
        try:
            APP_LOGGER.warning('非致命後処理警告: %s', message_text)
        except Exception:
            pass
        log_succeeded = False
        try:
            log_succeeded = bool(self._append_log_without_status_best_effort(message_text))
        except Exception:
            log_succeeded = False
        helper_succeeded = log_succeeded
        if show_status and not log_succeeded:
            try:
                helper_succeeded = bool(
                    self._append_log_without_status_or_status_bar(
                        message_text,
                        status_timeout_ms=duration_ms,
                    )
                )
            except Exception:
                helper_succeeded = False
        if not show_status:
            return log_succeeded
        status_succeeded = False
        try:
            status_succeeded = bool(
                self._show_ui_status_message_with_reflection_or_direct_fallback(
                    message_text,
                    duration_ms,
                )
            )
        except Exception:
            status_succeeded = False
        return bool(log_succeeded or helper_succeeded or status_succeeded)

    def _emit_postprocess_warnings_and_collect(
        self: MainWindow,
        warning_values: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> list[str]:
        emitted_messages: list[str] = []
        for message in worker_logic.coerce_postprocess_warning_messages(warning_values):
            emitted_here = False
            try:
                try:
                    emitted_result = self._emit_postprocess_warning(
                        message,
                        duration_ms=duration_ms,
                        show_status=show_status,
                    )
                except TypeError:
                    if show_status:
                        emitted_result = self._emit_postprocess_warning(message, duration_ms=duration_ms)
                    else:
                        raise
                emitted_here = emitted_result is not False
            except Exception:
                emitted_here = False
            if not emitted_here:
                emitted_here = bool(
                    self._emit_postprocess_warning_via_log_and_optional_status_fallback(
                        message,
                        duration_ms=duration_ms,
                        show_status=show_status,
                    )
                )
            if emitted_here:
                emitted_messages.append(message)
        return emitted_messages

    def _emit_postprocess_warnings(
        self: MainWindow,
        warning_values: object,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> bool:
        return bool(
            self._emit_postprocess_warnings_and_collect(
                warning_values,
                duration_ms=duration_ms,
                show_status=show_status,
            )
        )

    def _emit_unique_postprocess_warnings_with_fallback(
        self: MainWindow,
        warning_values: object,
        emitted_messages: set[str] | None = None,
        duration_ms: int = 5000,
        *,
        show_status: bool = True,
    ) -> list[str]:
        normalized_warnings = worker_logic.coerce_postprocess_warning_messages(warning_values)
        if emitted_messages is None:
            emitted_messages = set()
        unique_warnings = [
            warning_message for warning_message in normalized_warnings
            if warning_message not in emitted_messages
        ]
        if not unique_warnings:
            return []

        emitted_now = self._emit_postprocess_warnings_and_collect(
            unique_warnings,
            duration_ms=duration_ms,
            show_status=show_status,
        )
        emitted_messages.update(emitted_now)
        return emitted_now

    def _append_unique_postprocess_warnings_to_log_with_fallback(
        self: MainWindow,
        warning_values: object,
        emitted_messages: set[str] | None = None,
        *,
        allow_status_fallback: bool = False,
        status_timeout_ms: int = 5000,
    ) -> list[str]:
        normalized_warnings = worker_logic.coerce_postprocess_warning_messages(warning_values)
        if emitted_messages is None:
            emitted_messages = set()
        appended_now: list[str] = []
        for warning_message in normalized_warnings:
            if warning_message in emitted_messages:
                continue
            try:
                APP_LOGGER.warning('非致命後処理警告: %s', warning_message)
            except Exception:
                pass
            appended_here = False
            try:
                appended_here = bool(
                    self._append_log_without_status_with_optional_status_fallback(
                        warning_message,
                        allow_status_fallback=allow_status_fallback,
                        status_timeout_ms=status_timeout_ms,
                    )
                )
            except Exception:
                appended_here = False
            if appended_here:
                appended_now.append(warning_message)
                emitted_messages.add(warning_message)
        return appended_now

    def _emit_unique_postprocess_warnings_or_append_to_log(
        self: MainWindow,
        warning_values: object,
        emitted_messages: set[str] | None = None,
        *,
        duration_ms: int = 5000,
        show_status: bool = True,
    ) -> list[str]:
        effective_emitted_messages = emitted_messages if emitted_messages is not None else set()
        emitted_now: list[str] = []
        try:
            emitted_now = self._emit_unique_postprocess_warnings_with_fallback(
                warning_values,
                effective_emitted_messages,
                duration_ms=duration_ms,
                show_status=show_status,
            )
        except Exception:
            emitted_now = []
        appended_now: list[str] = []
        try:
            appended_now = self._append_unique_postprocess_warnings_to_log_with_fallback(
                warning_values,
                effective_emitted_messages,
                allow_status_fallback=show_status,
                status_timeout_ms=duration_ms,
            )
        except Exception:
            appended_now = []
        combined_messages: list[str] = []
        seen_messages: set[str] = set()
        for warning_message in list(emitted_now) + list(appended_now):
            if warning_message in seen_messages:
                continue
            seen_messages.add(warning_message)
            combined_messages.append(warning_message)
        return combined_messages

    def _open_finished_conversion_folder(self: MainWindow, result: ConversionResult) -> list[str]:
        if not worker_logic._bool_config_value(result, 'open_folder_requested', False):
            return []
        target = _coerce_ui_message_text(result.get('open_folder_target'), '').strip()
        if not target:
            return []
        try:
            if _open_path_in_file_manager(target):
                return []
            warning = f'完了後フォルダを開けませんでした: {target}'
            APP_LOGGER.warning(warning)
            return [warning]
        except Exception as exc:
            APP_LOGGER.exception('完了後フォルダを開けませんでした (target=%s): %s', target, exc)
            detail = _coerce_ui_message_text(exc).strip()
            message = f'完了後フォルダを開けませんでした。 / 対象: {target}'
            if detail:
                message = f'{message} / {detail}'
            return [message]

    def on_conversion_finished(self: MainWindow, result: ConversionResult) -> None:
        self._clear_active_conversion_run_token()
        msg = worker_logic._str_config_value(result, 'message', '変換完了しました。').strip() or '変換完了しました。'
        for helper_name in (
            '_open_finished_conversion_folder',
            '_merge_results_summary_lines_with_warnings',
            '_merge_results_summary_lines_and_collect_warnings',
            '_append_log_without_status_best_effort',
            '_append_log_without_status_or_status_bar',
            '_append_log_without_status_with_optional_status_fallback',
            '_emit_postprocess_warning_via_log_and_optional_status_fallback',
            '_emit_postprocess_warnings_and_collect',
            '_emit_unique_postprocess_warnings_with_fallback',
            '_append_unique_postprocess_warnings_to_log_with_fallback',
            '_emit_unique_postprocess_warnings_or_append_to_log',
            '_build_results_summary_text',
            '_coerce_mapping_payload',
            '_clear_results_selection_with_fallback',
            '_ui_widget_index',
            '_set_bottom_tab_index_with_fallback',
            '_set_results_summary_text_with_fallback',
            '_show_ui_status_message_with_reflection_or_direct_fallback',
        ):
            if hasattr(self, helper_name):
                continue
            helper = getattr(MainWindow, helper_name, None)
            if callable(helper):
                try:
                    setattr(self, helper_name, helper.__get__(self, type(self)))
                except Exception:
                    pass
        stopped = worker_logic._bool_config_value(result, 'stopped', False)
        converted_files = results_controller.coerce_result_path_list(result.get('converted_files'))
        postprocess_warnings = worker_logic.coerce_postprocess_warning_messages(
            result.get('postprocess_warnings')
        )
        postprocess_warnings = worker_logic.coerce_postprocess_warning_messages(
            list(postprocess_warnings) + self._open_finished_conversion_folder(result)
        )
        terminal_state_fallback_warnings: list[str] = []

        emitted_postprocess_warnings: set[str] = set()

        try:
            self._apply_conversion_terminal_state(msg, badge_text='停止' if stopped else '完了')
        except Exception as exc:
            finish_error_visible = bool(
                self._handle_conversion_finish_ui_error(
                    msg,
                    exc,
                    context='完了表示',
                    badge_text='停止' if stopped else '完了',
                    clear_results=False,
                )
            )
            if not finish_error_visible:
                finish_error_text = _coerce_ui_message_text(exc, str(exc)).strip() or '不明なエラー'
                terminal_state_fallback_warnings = worker_logic.coerce_postprocess_warning_messages(
                    f'完了表示エラー: {finish_error_text}'
                )
        summary_lines = result.get('summary_lines')
        show_postprocess_warning_status = not stopped
        summary_lines, final_postprocess_warnings = self._merge_results_summary_lines_and_collect_warnings(
            summary_lines,
            terminal_state_fallback_warnings,
            postprocess_warnings,
        )
        try:
            self._show_conversion_results(converted_files, summary_lines)
            if hasattr(self, 'bottom_tabs'):
                try:
                    if stopped and not converted_files:
                        self._set_bottom_tab_index_with_fallback(LOG_TAB_INDEX)
                    elif self._ui_widget_index(self.bottom_tabs) is None:
                        self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX)
                except Exception:
                    pass
        except Exception as exc:
            try:
                status_message = self._render_failure_status_message('変換結果表示エラー', exc)
            except Exception as render_exc:
                status_message = f'変換結果表示エラー: {_coerce_ui_message_text(render_exc, str(render_exc)).strip() or _coerce_ui_message_text(exc, str(exc)).strip() or "不明なエラー"}'
            fallback_warnings = worker_logic.coerce_postprocess_warning_messages(status_message)
            if fallback_warnings:
                summary_lines, final_postprocess_warnings = self._merge_results_summary_lines_and_collect_warnings(
                    summary_lines,
                    final_postprocess_warnings,
                    fallback_warnings,
                )
                self._emit_unique_postprocess_warnings_or_append_to_log(
                    fallback_warnings,
                    emitted_postprocess_warnings,
                    duration_ms=5000,
                    show_status=show_postprocess_warning_status,
                )
            else:
                try:
                    self._append_log_without_status_with_optional_status_fallback(status_message)
                except Exception:
                    pass
                if show_postprocess_warning_status:
                    try:
                        self._show_ui_status_message_with_reflection_or_direct_fallback(status_message, 5000)
                    except Exception:
                        pass
            fallback_summary_text = _coerce_ui_message_text(status_message).strip()
            fallback_results_visible = False
            try:
                self.populate_results(converted_files, summary_lines)
                fallback_results_visible = not hasattr(self, 'results_list')
            except Exception:
                try:
                    fallback_summary_text = self._build_results_summary_text(
                        converted_files,
                        summary_lines,
                        fallback=status_message,
                    )
                except Exception:
                    fallback_summary_text = _coerce_ui_message_text(status_message).strip()
                try:
                    clear_results_succeeded = bool(self._clear_results_view(fallback_summary_text))
                except Exception:
                    clear_results_succeeded = False
                if not clear_results_succeeded:
                    try:
                        self._set_results_summary_text_with_fallback(fallback_summary_text)
                    except Exception:
                        pass
            try:
                self._clear_loaded_xtc_state()
            except Exception:
                pass
            selection_cleared = False
            self._clear_results_selection_with_fallback({'clear_selection': True})
            if hasattr(self, 'bottom_tabs'):
                try:
                    self._set_bottom_tab_index_with_fallback(
                        RESULT_TAB_INDEX if fallback_results_visible else LOG_TAB_INDEX
                    )
                except Exception:
                    pass
        self._emit_unique_postprocess_warnings_or_append_to_log(
            final_postprocess_warnings,
            emitted_postprocess_warnings,
            duration_ms=5000,
            show_status=show_postprocess_warning_status,
        )

    def on_conversion_error(self: MainWindow, message: str) -> None:
        self._clear_active_conversion_run_token()
        message_text = _coerce_ui_message_text(message, '不明なエラー')
        APP_LOGGER.error('変換エラー: %s', message_text)
        try:
            self._show_critical_dialog_with_status_fallback(
                '変換エラー',
                message_text,
                fallback_status_message=message_text,
            )
        except Exception:
            APP_LOGGER.exception('変換エラーダイアログの表示に失敗しました')
        failure_summary_text = self._build_conversion_failure_summary_text('エラー', message_text)
        self._apply_conversion_failure_ui(
            failure_summary_text,
            status_message=message_text,
            log_error_context='変換エラー時のログ追記に失敗しました',
            terminal_state_error_context='変換エラー時の終端状態反映に失敗しました',
            clear_results_error_context='変換エラー時の結果表示クリアに失敗しました',
            clear_preview_error_context='変換エラー時の実機ビュー状態クリアに失敗しました',
            progress_error_context='変換エラー時の進捗バー更新に失敗しました',
            tab_error_context='変換エラー時のタブ切替に失敗しました',
        )

    def append_log(
        self: MainWindow,
        text: str,
        *,
        reflect_in_status: bool = True,
    ) -> None:
        message_text = _coerce_ui_message_text(text)
        if not message_text:
            return
        try:
            APP_LOGGER.info(message_text)
        except Exception:
            pass
        try:
            log_widget = getattr(self, 'log_edit', None)
            if log_widget is not None and hasattr(log_widget, 'append'):
                log_widget.append(message_text)
        except Exception:
            pass
        try:
            visible_render_failure = bool(self._visible_render_failure_status_text())
        except Exception:
            visible_render_failure = False
        try:
            message_is_render_failure = self._is_render_failure_status_text(message_text)
        except Exception:
            message_is_render_failure = False
        preserve_visible_render_failure = visible_render_failure and not message_is_render_failure
        if reflect_in_status and not self.worker and not preserve_visible_render_failure and hasattr(self, 'progress_label'):
            try:
                self.progress_label.setText(message_text)
            except Exception:
                pass
        if reflect_in_status and not preserve_visible_render_failure:
            if message_is_render_failure:
                self._show_ui_status_message_direct_with_reflection_best_effort(message_text, 5000)
            else:
                try:
                    self._show_ui_status_message_with_reflection_or_direct_fallback(message_text, 5000)
                except Exception:
                    pass

    def _progress_status_text(self: MainWindow, current: int, total: int, message: object) -> str:
        return studio_logic.build_progress_status_text(current, total, message)

    def update_conversion_progress(self: MainWindow, current: int, total: int, message: str) -> None:
        total_value = max(1, _coerce_progress_number(total, 1))
        current_value = max(0, min(_coerce_progress_number(current, 0), total_value))
        text = self._progress_status_text(current_value, total_value, message)
        if hasattr(self, 'progress_bar'):
            try:
                self.progress_bar.setRange(0, 0)
                self.progress_bar.setValue(0)
            except Exception:
                pass
        try:
            visible_render_failure = bool(self._visible_render_failure_status_text())
        except Exception:
            visible_render_failure = False
        if hasattr(self, 'progress_label') and not visible_render_failure:
            try:
                self.progress_label.setText(text)
            except Exception:
                pass
        if not visible_render_failure:
            try:
                self._show_ui_status_message_with_reflection_or_direct_fallback(text, None)
            except Exception:
                pass

    def open_log_folder(self: MainWindow) -> None:
        try:
            target_dir = _resolve_log_dir()
        except Exception:
            target_dir = LOG_DIR
        if _open_path_in_file_manager(target_dir):
            return
        try:
            self._show_information_dialog_with_status_fallback(
                'ログフォルダ',
                str(target_dir),
                fallback_status_message=f'ログフォルダ: {target_dir}',
            )
        except Exception:
            try:
                self._show_ui_status_message_with_reflection_or_direct_fallback(f'ログフォルダ: {target_dir}', 5000)
            except Exception:
                pass

    def _set_results_summary_text_fallback(
        self: MainWindow,
        summary_text: object = None,
        *,
        default_text: str = '保存されたファイルはありません。',
    ) -> bool:
        if not hasattr(self, 'results_summary_label'):
            return False
        text = _coerce_ui_message_text(summary_text)
        try:
            self.results_summary_label.setText(text or default_text)
            return True
        except Exception:
            return False

    def _set_results_summary_text_with_fallback(
        self: MainWindow,
        summary_text: object = None,
        *,
        default_text: str = '保存されたファイルはありません。',
    ) -> bool:
        expected_text = _coerce_ui_message_text(summary_text).strip() or default_text
        try:
            if bool(self._set_results_summary_text_fallback(summary_text, default_text=default_text)):
                if self._ui_widget_text(getattr(self, 'results_summary_label', None)) == expected_text:
                    return True
                # sweep353: the primary helper may be monkey-patched or may report
                # success without mutating the visible label.  Fall through to the
                # direct label update path so tests and stubbed UI objects still see
                # the requested summary text.
        except Exception:
            pass
        if not hasattr(self, 'results_summary_label'):
            return False
        if self._ui_widget_text(getattr(self, 'results_summary_label', None)) == expected_text:
            return True
        try:
            self.results_summary_label.setText(expected_text)
        except Exception:
            return False
        return self._ui_widget_text(getattr(self, 'results_summary_label', None)) == expected_text

    def _set_bottom_tab_index_with_fallback(self: MainWindow, index: object) -> bool:
        if not hasattr(self, 'bottom_tabs'):
            return False
        try:
            normalized_index = int(index)
        except Exception:
            return False
        tab_count = getattr(self.bottom_tabs, 'count', None)
        if callable(tab_count):
            try:
                if normalized_index < 0 or normalized_index >= max(0, int(tab_count())):
                    return False
            except Exception:
                return False
        try:
            self.bottom_tabs.setCurrentIndex(normalized_index)
        except Exception:
            pass
        if self._ui_widget_index(getattr(self, 'bottom_tabs', None)) == normalized_index:
            return True
        tab_bar_getter = getattr(self.bottom_tabs, 'tabBar', None)
        if callable(tab_bar_getter):
            try:
                tab_bar = tab_bar_getter()
            except Exception:
                tab_bar = None
            set_tab_bar_index = getattr(tab_bar, 'setCurrentIndex', None)
            if callable(set_tab_bar_index):
                try:
                    set_tab_bar_index(normalized_index)
                except Exception:
                    pass
            if self._ui_widget_index(getattr(self, 'bottom_tabs', None)) == normalized_index:
                return True
            if self._ui_widget_index(tab_bar) == normalized_index:
                return True
        widget_getter = getattr(self.bottom_tabs, 'widget', None)
        set_current_widget = getattr(self.bottom_tabs, 'setCurrentWidget', None)
        if callable(widget_getter) and callable(set_current_widget):
            try:
                target_widget = widget_getter(normalized_index)
            except Exception:
                target_widget = None
            if target_widget is not None:
                try:
                    set_current_widget(target_widget)
                except Exception:
                    pass
            if self._ui_widget_index(getattr(self, 'bottom_tabs', None)) == normalized_index:
                return True
        return False

    def _clear_results_view(self: MainWindow, summary_text: object = None) -> bool:
        has_results_list = hasattr(self, 'results_list')
        list_cleared = False
        if has_results_list:
            try:
                self.results_list.clear()
                list_cleared = True
            except Exception:
                APP_LOGGER.exception('結果一覧クリアに失敗しました')
        selection_cleared = False
        if has_results_list:
            try:
                selection_cleared = bool(self._clear_results_selection_state())
            except Exception:
                APP_LOGGER.exception('結果一覧選択状態クリアに失敗しました')
        summary_updated = False
        normalized_summary_text = _coerce_ui_message_text(summary_text)
        summary_requested = bool(normalized_summary_text) or hasattr(self, 'results_summary_label')
        try:
            summary_updated = bool(self._set_results_summary_text_with_fallback(summary_text))
        except Exception:
            APP_LOGGER.exception('結果一覧サマリ更新に失敗しました')
        if summary_requested and not summary_updated:
            return False
        return bool(list_cleared or selection_cleared or summary_updated)

    def _result_display_name(self: MainWindow, path_text: str) -> str:
        return studio_logic.build_result_display_name(path_text)

    def _normalized_result_entries(self: MainWindow, paths: list[object]) -> list[tuple[str, str]]:
        return results_controller.build_results_entries(paths)

    def _apply_results_entries_to_ui(
        self: MainWindow,
        entries: list[tuple[str, str]],
        summary_text: object = None,
        initial_index: object = None,
    ) -> None:
        self._clear_results_view()
        if hasattr(self, 'results_summary_label'):
            normalized_summary = _coerce_ui_message_text(summary_text)
            if normalized_summary:
                self._set_results_summary_text_with_fallback(normalized_summary)
        if not hasattr(self, 'results_list'):
            return
        for display_name, raw in entries:
            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, raw)
            self.results_list.addItem(item)
        try:
            normalized_index = int(initial_index)
        except Exception:
            normalized_index = None
        if normalized_index is not None:
            self._set_results_current_index_with_fallback(normalized_index)

    def populate_results(self: MainWindow, paths: list[object], summary_lines: list[str] | None = None) -> None:
        context = results_controller.build_results_apply_context(paths, summary_lines)
        self._apply_results_entries_to_ui(
            context.get('entries', []),
            context.get('summary_text', ''),
            context.get('initial_index'),
        )
        remembered_path = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_path_text')).strip()
        if not remembered_path or self._result_item_count() <= 0:
            return
        selection_context = results_controller.build_results_selection_context(
            remembered_path,
            self._result_item_paths(),
        )
        if studio_logic.payload_optional_int_value(selection_context, 'matched_index') is None:
            return
        self._apply_results_selection_context_with_fallback(selection_context)

    def on_result_item_clicked(self: MainWindow, item: QListWidgetItem) -> None:
        def _load_result_path_with_tab_fallback(path_value: object) -> None:
            load_succeeded = self._load_xtc_from_path_with_result(path_value)
            if hasattr(self, 'bottom_tabs'):
                try:
                    self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX if load_succeeded else LOG_TAB_INDEX)
                except Exception:
                    APP_LOGGER.exception('結果項目クリック時のタブ切替に失敗しました')

        path = worker_logic._normalized_path_text(self._results_item_path(item)).strip()
        if path:
            matched_index = results_controller.find_matching_loaded_path_index(path, self._result_item_paths())
            if matched_index is not None:
                self._apply_results_selection_context_with_fallback({'matched_index': matched_index, 'clear_selection': False})
                _load_result_path_with_tab_fallback(path)
                return
            if self._result_item_count() <= 0:
                _load_result_path_with_tab_fallback(path)
                return
        resolved_context = self._resolved_result_load_context()
        resolved_path = worker_logic._normalized_path_text(resolved_context.get('resolved_path')).strip()
        preferred_index = studio_logic.payload_optional_int_value(resolved_context, 'preferred_index')
        if resolved_path and self._payload_bool_value(resolved_context, 'has_path', False) and preferred_index is not None:
            self._apply_results_selection_context_with_fallback({'matched_index': preferred_index, 'clear_selection': False})
            _load_result_path_with_tab_fallback(resolved_path)
            return
        remembered_path = worker_logic._normalized_path_text(self.__dict__.get('_loaded_xtc_path_text')).strip()
        try:
            if remembered_path:
                self._sync_results_selection_for_loaded_path_with_fallback(remembered_path)
            else:
                self._clear_results_selection_with_fallback(
                    results_controller.build_results_clear_selection_context()
                )
        except Exception:
            pass
        try:
            self._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        self._show_result_load_dialog_with_status_fallback(
            'warning',
            '実機ビュー',
            '選択した項目のファイルパスを取得できませんでした。',
        )

    def _normalize_results_path_key(self: MainWindow, path: object) -> str:
        return results_controller.normalize_results_path_key(path)


    def _clear_results_selection_state(self: MainWindow) -> bool:
        if not hasattr(self, 'results_list'):
            return False
        selection_cleared = False
        clear_selection = getattr(self.results_list, 'clearSelection', None)
        if callable(clear_selection):
            try:
                clear_selection()
                selection_cleared = True
            except Exception:
                pass
        set_current_item = getattr(self.results_list, 'setCurrentItem', None)
        if callable(set_current_item):
            try:
                set_current_item(None)
                return True
            except Exception:
                pass
        set_current_row = getattr(self.results_list, 'setCurrentRow', None)
        if callable(set_current_row):
            try:
                set_current_row(-1)
                return True
            except Exception:
                pass
        return selection_cleared

    def _clear_results_selection_with_fallback(
        self: MainWindow,
        context: Mapping[str, object] | object = None,
    ) -> bool:
        selection_context = self._coerce_mapping_payload(context)
        if not selection_context:
            selection_context = results_controller.build_results_clear_selection_context()
        try:
            self._apply_results_selection_context(selection_context)
        except Exception:
            pass
        try:
            return bool(self._clear_results_selection_state())
        except Exception:
            return False

    def _apply_results_selection_context_with_fallback(
        self: MainWindow,
        context: Mapping[str, object] | object,
    ) -> bool:
        selection_context = self._coerce_mapping_payload(context)
        if not selection_context:
            return self._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
        if self._payload_bool_value(selection_context, 'clear_selection', False):
            return self._clear_results_selection_with_fallback(selection_context)
        matched_index = studio_logic.payload_optional_int_value(selection_context, 'matched_index')
        if matched_index is None:
            return self._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
        try:
            self._apply_results_selection_context(selection_context)
            current_index = self._current_results_index()
            if current_index == matched_index:
                return True
            if matched_index in self._selected_result_indexes():
                return True
        except Exception:
            pass
        return self._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )

    def _sync_results_selection_for_loaded_path_with_fallback(
        self: MainWindow,
        path: object,
    ) -> bool:
        normalized_path = worker_logic._normalized_path_text(path).strip()
        if not normalized_path:
            return self._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
        selection_context = results_controller.build_results_selection_context(
            normalized_path,
            self._result_item_paths(),
        )
        matched_index = studio_logic.payload_optional_int_value(selection_context, 'matched_index')
        try:
            self._sync_results_selection_for_loaded_path(normalized_path)
            if matched_index is None:
                return self._clear_results_selection_with_fallback(
                    results_controller.build_results_clear_selection_context()
                )
            current_index = self._current_results_index()
            if current_index == matched_index:
                return True
            if matched_index in self._selected_result_indexes():
                return True
        except Exception:
            pass
        return self._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )


    def _result_item_count(self: MainWindow) -> int:
        if not hasattr(self, 'results_list'):
            return 0
        count = getattr(self.results_list, 'count', None)
        if not callable(count):
            return 0
        try:
            return max(0, int(count()))
        except Exception:
            return 0

    def _result_item_at(self: MainWindow, index: object) -> QListWidgetItem | None:
        if not hasattr(self, 'results_list'):
            return None
        item_at = getattr(self.results_list, 'item', None)
        if not callable(item_at):
            return None
        try:
            normalized_index = int(index)
        except Exception:
            return None
        if normalized_index < 0 or normalized_index >= self._result_item_count():
            return None
        try:
            return item_at(normalized_index)
        except Exception:
            return None

    def _result_item_paths(self: MainWindow) -> list[object]:
        paths: list[object] = []
        for idx in range(self._result_item_count()):
            item = self._result_item_at(idx)
            paths.append(self._results_item_path(item) if item is not None else None)
        return paths

    def _result_item_path_keys(self: MainWindow) -> list[str]:
        return [self._normalize_results_path_key(path) for path in self._result_item_paths()]

    def _set_results_current_index_with_fallback(self: MainWindow, index: object) -> bool:
        if not hasattr(self, 'results_list'):
            return False
        try:
            normalized_index = int(index)
        except Exception:
            return False
        if normalized_index < 0 or normalized_index >= self._result_item_count():
            return False
        matched_item = self._result_item_at(normalized_index)
        if matched_item is None:
            return False
        current_item_getter = getattr(self.results_list, 'currentItem', None)
        selected_items_getter = getattr(self.results_list, 'selectedItems', None)
        can_verify_current_index = callable(current_item_getter) or callable(selected_items_getter)
        set_current_row = getattr(self.results_list, 'setCurrentRow', None)
        if callable(set_current_row):
            try:
                set_current_row(normalized_index)
            except Exception:
                pass
        if self._current_results_index() == normalized_index:
            return True
        if normalized_index in self._selected_result_indexes():
            return True
        set_current_item = getattr(self.results_list, 'setCurrentItem', None)
        if callable(set_current_item):
            try:
                set_current_item(matched_item)
            except Exception:
                pass
        if self._current_results_index() == normalized_index:
            return True
        if normalized_index in self._selected_result_indexes():
            return True
        if callable(set_current_item) and not can_verify_current_index:
            return True
        if callable(set_current_row) and not can_verify_current_index:
            return True
        return False

    def _apply_results_selection_context(self: MainWindow, context: Mapping[str, object] | object) -> QListWidgetItem | None:
        context = self._coerce_mapping_payload(context)
        if not hasattr(self, 'results_list'):
            return None
        if self._payload_bool_value(context, 'clear_selection', False):
            self._clear_results_selection_state()
            return None
        matched_index = studio_logic.payload_optional_int_value(context, 'matched_index')
        if matched_index is None:
            self._clear_results_selection_state()
            return None
        matched_item = self._result_item_at(matched_index)
        if matched_item is None:
            self._clear_results_selection_state()
            return None
        if self._set_results_current_index_with_fallback(matched_index):
            return matched_item
        self._clear_results_selection_state()
        return None

    def _sync_results_selection_for_loaded_path(self: MainWindow, path: object) -> None:
        if not hasattr(self, 'results_list'):
            return
        context = results_controller.build_results_selection_context(path, self._result_item_paths())
        self._apply_results_selection_context(context)

    def _selected_result_indexes(self: MainWindow) -> list[int]:
        if not hasattr(self, 'results_list'):
            return []
        selected_items = getattr(self.results_list, 'selectedItems', None)
        row = getattr(self.results_list, 'row', None)
        if not callable(selected_items) or not callable(row):
            return []
        try:
            selected = selected_items()
        except Exception:
            return []
        indexes: list[int] = []
        for item in selected or []:
            try:
                indexes.append(int(row(item)))
            except Exception:
                continue
        return indexes

    def _current_results_index(self: MainWindow) -> int | None:
        if not hasattr(self, 'results_list'):
            return None
        current_item = getattr(self.results_list, 'currentItem', None)
        if not callable(current_item):
            return None
        try:
            item = current_item()
        except Exception:
            item = None
        if item is None:
            return None
        row = getattr(self.results_list, 'row', None)
        if not callable(row):
            return None
        try:
            return int(row(item))
        except Exception:
            return None

    def _resolved_result_load_context(self: MainWindow) -> dict[str, object]:
        return results_controller.build_results_load_context(
            selected_indexes=self._selected_result_indexes(),
            current_index=self._current_results_index(),
            item_paths=self._result_item_paths(),
            loaded_path=self.__dict__.get('_loaded_xtc_path_text'),
        )

    def _resolved_results_item_for_loading(self: MainWindow) -> QListWidgetItem | None:
        context = self._resolved_result_load_context()
        preferred_index = studio_logic.payload_optional_int_value(context, 'preferred_index')
        if preferred_index is None:
            return None
        return self._result_item_at(preferred_index)

    def _fallback_loaded_result_load_context(self: MainWindow) -> dict[str, object]:
        return results_controller.build_fallback_loaded_result_load_context(
            self.__dict__.get('_loaded_xtc_path_text'),
            self._result_item_paths(),
        )

    def _results_item_path(self: MainWindow, item: object) -> object:
        data = getattr(item, 'data', None)
        if callable(data):
            try:
                return data(Qt.UserRole)
            except Exception:
                return None
        return None

    def _show_result_load_dialog_with_status_fallback(
        self: MainWindow,
        level: str,
        title: str,
        message: str,
    ) -> None:
        dialog = getattr(QMessageBox, str(level), None)
        if callable(dialog):
            try:
                dialog(self, title, message)
                return
            except Exception:
                pass
        try:
            self._show_ui_status_message_with_reflection_or_direct_fallback(
                message,
                5000,
                reuse_existing_message=False,
            )
        except Exception:
            pass

    def load_selected_result(self: MainWindow) -> None:
        context = self._resolved_result_load_context()
        preferred_index = studio_logic.payload_optional_int_value(context, 'preferred_index')
        if self._payload_bool_value(context, 'should_warn_no_selection', False) or preferred_index is None:
            try:
                self._sync_active_display_context_for_visible_page()
            except Exception:
                pass
            self._show_result_load_dialog_with_status_fallback('information', '実機ビュー', '表示する変換結果を選択してください。')
            return
        effective_context = dict(context)
        effective_index = preferred_index
        if self._payload_bool_value(context, 'should_warn_missing_path', False) or not self._payload_bool_value(context, 'has_path', False):
            fallback_context = self._fallback_loaded_result_load_context()
            fallback_index = studio_logic.payload_optional_int_value(fallback_context, 'preferred_index')
            if fallback_index is not None and self._payload_bool_value(fallback_context, 'has_path', False):
                effective_context = fallback_context
                effective_index = fallback_index
            else:
                try:
                    self._sync_active_display_context_for_visible_page()
                except Exception:
                    pass
                self._show_result_load_dialog_with_status_fallback('warning', '実機ビュー', '選択した項目のファイルパスを取得できませんでした。')
                return
        path = effective_context.get('resolved_path')
        if not self._payload_bool_value(effective_context, 'has_path', False):
            try:
                self._sync_active_display_context_for_visible_page()
            except Exception:
                pass
            self._show_result_load_dialog_with_status_fallback('warning', '実機ビュー', '選択した項目のファイルパスを取得できませんでした。')
            return
        self._apply_results_selection_context_with_fallback({'matched_index': effective_index, 'clear_selection': False})
        load_succeeded = self._load_xtc_from_path_with_result(path)
        if hasattr(self, 'bottom_tabs'):
            try:
                self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX if load_succeeded else LOG_TAB_INDEX)
            except Exception:
                APP_LOGGER.exception('結果選択読込時のタブ切替に失敗しました')

    # ── XTCビューア ───────────────────────────────────────

    def _xtc_source_payload(self: MainWindow, path: object) -> dict[str, str]:
        path_text = worker_logic._normalized_path_text(path).strip()
        return studio_logic.build_xtc_source_payload(
            path_text,
            self._xtc_display_name(path_text),
        )

    def _normalized_xtc_bytes(self: MainWindow, data: object) -> bytes:
        return studio_logic.normalize_xtc_bytes(data)

    def _xtc_document_payload(self: MainWindow, data: object) -> dict[str, object]:
        xtc_data = self._normalized_xtc_bytes(data)
        pages = parse_xtc_pages(xtc_data)
        return studio_logic.build_xtc_document_payload_from_pages(xtc_data, pages)

    def _xtc_source_document_payload(self: MainWindow, path: object) -> dict[str, object]:
        source_payload = self._xtc_source_payload(path)
        raw = Path(source_payload['path_text']).read_bytes()
        document_payload = self._xtc_document_payload(raw)
        return studio_logic.build_xtc_source_document_payload(source_payload, document_payload)

    def _xtc_display_name(self: MainWindow, path: object) -> str:
        path_text = worker_logic._normalized_path_text(path).strip()
        return studio_logic.build_xtc_display_name(path_text)

    def _reset_xtc_page_input(self: MainWindow, total_pages: object, current_page: object = 0) -> None:
        if not hasattr(self, 'page_input'):
            return
        nav_bar_plan = gui_layouts.build_nav_bar_plan()
        page_input_state = studio_logic.build_page_input_apply_state(
            total_pages=total_pages,
            current_page=current_page,
            empty_minimum=self._plan_int_value(nav_bar_plan, 'page_input_empty_minimum', 0),
            empty_maximum=self._plan_int_value(nav_bar_plan, 'page_input_empty_maximum', 0),
            active_minimum=self._plan_int_value(nav_bar_plan, 'page_input_active_minimum', 1),
        )
        minimum = self._payload_int_value(page_input_state, 'minimum', 0)
        maximum = self._payload_int_value(page_input_state, 'maximum', 0)
        value = self._payload_int_value(page_input_state, 'value', 0)
        with _bulk_block_signals(self.page_input):
            self.page_input.setRange(minimum, maximum)
            self.page_input.setValue(value)

    def _apply_xtc_document_payload(self: MainWindow, payload: Mapping[str, object]) -> None:
        xtc_data = self._normalized_xtc_bytes(payload.get('data', b''))
        pages = self._normalized_xtc_pages_for_runtime(payload.get('pages'))
        total = max(0, worker_logic._int_config_value(payload, 'total', len(pages)))
        total = len(pages) if pages else total
        current_index = self._normalized_xtc_page_index(payload.get('current_index', 0), total=total) if pages else 0
        current_page = current_index + 1 if total > 0 else 0
        self.xtc_bytes = xtc_data
        self.xtc_pages = pages
        self._clear_xtc_page_qimage_cache()
        self.loaded_xtc_profile_ui_override = False
        self.device_view_source = 'xtc'
        self.current_device_preview_page_index = 0
        self.current_page_index = current_index
        self._refresh_loaded_xtc_viewer_profile_cache()
        self._reset_xtc_page_input(total, current_page if self.xtc_pages else 0)
        self.render_current_page(refresh_navigation=True)

    def _apply_loaded_xtc_document(self: MainWindow, data: bytes, pages: list[PageInfo]) -> None:
        self._apply_xtc_document_payload(
            {
                'data': data,
                'pages': pages,
                'total': len(pages),
                'current_index': 0,
                'current_page': 1 if pages else 0,
            }
        )

    def _current_xtc_page_blob(self: MainWindow) -> bytes | None:
        if not getattr(self, 'xtc_bytes', b''):
            return None
        payload = self._xtc_page_state_payload()
        total = worker_logic._int_config_value(payload, 'total', 0)
        if total <= 0:
            return None
        current_index = worker_logic._int_config_value(payload, 'current_index', 0)
        if current_index != getattr(self, 'current_page_index', 0):
            self.current_page_index = current_index
            self._refresh_loaded_xtc_viewer_profile_cache()
        page = payload.get('page')
        if page is None:
            return None
        offset = max(0, worker_logic._int_config_value({'value': getattr(page, 'offset', 0)}, 'value', 0))
        length = max(0, worker_logic._int_config_value({'value': getattr(page, 'length', 0)}, 'value', 0))
        return self.xtc_bytes[offset: offset + length]

    def _clear_xtc_viewer_page(self: MainWindow, *, refresh_navigation: bool = True) -> None:
        if hasattr(self, 'viewer_widget'):
            try:
                self.viewer_widget.set_profile(self._active_device_viewer_profile())
            except Exception:
                pass
            self.viewer_widget.clear_page()
        if refresh_navigation:
            self.update_navigation_ui()

    def _page_image_dimensions(self: MainWindow, image: object) -> tuple[int, int]:
        return studio_logic.read_image_dimensions(image)

    def _viewer_profile_for_dimensions(self: MainWindow, width: object, height: object) -> DeviceProfile:
        current_profile = self._current_viewer_profile()
        resolution = studio_logic.build_viewer_profile_resolution_state(
            width,
            height,
            current_width=getattr(current_profile, 'width_px', 0),
            current_height=getattr(current_profile, 'height_px', 0),
            profile_dimensions={
                key: (getattr(profile, 'width_px', 0), getattr(profile, 'height_px', 0))
                for key, profile in DEVICE_PROFILES.items()
            },
            preferred_profile_keys=('x4', 'x3'),
        )
        resolution_kind = str(resolution.get('kind') or '').strip()
        if resolution_kind == 'current':
            return current_profile
        if resolution_kind == 'profile':
            profile = DEVICE_PROFILES.get(str(resolution.get('profile_key') or '').strip())
            if profile is not None:
                return profile
            return current_profile
        width_px = max(0, worker_logic._int_config_value({'value': resolution.get('width_px')}, 'value', 0))
        height_px = max(0, worker_logic._int_config_value({'value': resolution.get('height_px')}, 'value', 0))
        return self._custom_viewer_profile_for_dimensions(width_px, height_px)

    def _custom_viewer_profile_for_dimensions(self: MainWindow, width: int, height: int) -> DeviceProfile:
        base_profile = DEVICE_PROFILES.get('custom', DEVICE_PROFILES['x4'])
        metrics = studio_logic.build_custom_viewer_profile_metrics(
            width_px=width,
            height_px=height,
            ppi=getattr(base_profile, 'ppi', 300.0),
            screen_w_mm=getattr(base_profile, 'screen_w_mm', 1.0),
            screen_h_mm=getattr(base_profile, 'screen_h_mm', 1.0),
            body_w_mm=getattr(base_profile, 'body_w_mm', 1.0),
            body_h_mm=getattr(base_profile, 'body_h_mm', 1.0),
        )
        return replace(
            base_profile,
            width_px=int(metrics['width_px']),
            height_px=int(metrics['height_px']),
            screen_w_mm=float(metrics['screen_w_mm']),
            screen_h_mm=float(metrics['screen_h_mm']),
            body_w_mm=float(metrics['body_w_mm']),
            body_h_mm=float(metrics['body_h_mm']),
        )

    def _viewer_profile_for_xtc_pages(self: MainWindow, pages: object) -> DeviceProfile | None:
        page_list = self._normalized_xtc_pages_for_runtime(pages)
        if not page_list:
            return None
        total = len(page_list)
        current_index = self._normalized_xtc_page_index(getattr(self, 'current_page_index', 0), total=total)
        candidates: list[object] = []
        if 0 <= current_index < total:
            candidates.append(page_list[current_index])
        first_page = page_list[0]
        if not candidates or candidates[0] is not first_page:
            candidates.append(first_page)
        for candidate in candidates:
            width = max(0, worker_logic._int_config_value({'value': getattr(candidate, 'width', 0)}, 'value', 0))
            height = max(0, worker_logic._int_config_value({'value': getattr(candidate, 'height', 0)}, 'value', 0))
            if width > 0 and height > 0:
                return self._viewer_profile_for_dimensions(width, height)
        return None

    def _viewer_profile_for_page_image(self: MainWindow, image: object) -> DeviceProfile:
        current_key = getattr(self, 'current_profile_key', '')
        if current_key and current_key != 'custom':
            return self._current_viewer_profile()

        width, height = self._page_image_dimensions(image)
        return self._viewer_profile_for_dimensions(width, height)

    def _viewer_profile_for_preview_payload(self: MainWindow, payload: object = None) -> DeviceProfile:
        preview_payload_obj = payload if isinstance(payload, Mapping) else getattr(self, 'last_applied_preview_payload', None)
        preview_payload = dict(preview_payload_obj) if isinstance(preview_payload_obj, Mapping) else {}
        if not preview_payload:
            return self._current_viewer_profile()

        profile_key = self._normalize_choice_value(preview_payload.get('profile'), '', DEVICE_PROFILES)
        width = worker_logic._int_config_value({'width': preview_payload.get('width')}, 'width', 0)
        height = worker_logic._int_config_value({'height': preview_payload.get('height')}, 'height', 0)

        if profile_key and profile_key != 'custom':
            profile = DEVICE_PROFILES.get(profile_key)
            if profile is not None:
                return profile

        if width > 0 and height > 0:
            for key in ('x4', 'x3'):
                profile = DEVICE_PROFILES.get(key)
                if profile and int(profile.width_px) == width and int(profile.height_px) == height:
                    return profile
            return self._custom_viewer_profile_for_dimensions(width, height)

        return self._current_viewer_profile()

    def _refresh_successful_device_render_status(self: MainWindow) -> None:
        view_mode = self._normalized_main_view_mode(
            getattr(self, 'main_view_mode', 'font')
        )
        has_font_preview_pages = bool(self._runtime_preview_pages()) if view_mode == 'font' else False
        preview_replacement = self._current_preview_render_status_message() if has_font_preview_pages else ''
        progress_status_text = ''
        if hasattr(self, 'progress_label'):
            progress_status_text = self._ui_widget_text(self.progress_label)
        status_state = studio_logic.build_successful_device_render_status_refresh_state(
            view_mode=view_mode,
            current_label_text=self._ui_widget_text(getattr(self, 'current_xtc_label', None)),
            preview_replacement=preview_replacement,
            has_font_preview_pages=has_font_preview_pages,
            progress_status_text=progress_status_text,
            status_bar_text=self._status_bar_message_text(),
        )
        replacement = str(status_state.get('replacement', ''))
        if not replacement:
            return
        stale_progress_status = bool(status_state.get('stale_progress_status'))
        if stale_progress_status and hasattr(self, 'progress_label'):
            try:
                self.progress_label.setText(replacement)
            except Exception:
                pass
        if status_state.get('should_notify_status_bar'):
            self._show_ui_status_message_direct_with_reflection_best_effort(replacement, 5000)

    def _apply_rendered_xtc_page(
        self: MainWindow,
        image: QImage,
        *,
        refresh_navigation: bool = True,
        profile: DeviceProfile | None = None,
    ) -> None:
        if hasattr(self, 'viewer_widget'):
            resolved_profile = profile or self._viewer_profile_for_page_image(image)
            self.viewer_widget.set_profile(resolved_profile)
            self.viewer_widget.set_page_image(image)
        try:
            self._refresh_successful_device_render_status()
        except Exception:
            pass
        if refresh_navigation:
            self.update_navigation_ui()

    def _render_failure_status_message(self: MainWindow, title: object, exc: Exception) -> str:
        title_text = worker_logic._normalized_path_text(title).strip() or '表示エラー'
        detail = worker_logic._normalized_path_text(exc).strip()
        preserved = self._xtc_load_failure_preserved_display_name()
        return studio_logic.build_render_failure_status_message(
            title_text,
            detail,
            preserved,
        )

    def _handle_xtc_render_failure(self: MainWindow, exc: Exception, *, refresh_navigation: bool = True) -> None:
        try:
            self._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        self._clear_xtc_viewer_page(refresh_navigation=refresh_navigation)
        status_message = self._render_failure_status_message('ページ表示エラー', exc)
        device_view_visible = self._normalized_main_view_mode(
            getattr(self, 'main_view_mode', 'font')
        ) == 'device'
        reflect_failure_in_status = device_view_visible or not self._visible_render_failure_status_text()
        self._append_log_with_status_fallback(
            status_message,
            reflect_in_status=reflect_failure_in_status,
        )
        if not device_view_visible:
            return
        try:
            self._show_critical_dialog_with_status_fallback(
                'ページ表示エラー',
                str(exc),
                fallback_status_message=status_message,
            )
        except Exception:
            pass

    def _set_current_device_preview_page_index(self: MainWindow, index: object, *, refresh_navigation: bool = False) -> bool:
        nav_state = studio_logic.build_navigation_target_state(
            total=len(self._runtime_device_preview_pages()),
            current_index=getattr(self, 'current_device_preview_page_index', 0),
            target_index=index,
        )
        if not self._payload_bool_value(nav_state, 'active', False):
            if refresh_navigation:
                self.update_navigation_ui()
            return False
        new_idx = self._payload_int_value(
            nav_state,
            'target_index',
            int(getattr(self, 'current_device_preview_page_index', 0)),
        )
        if new_idx == getattr(self, 'current_device_preview_page_index', 0):
            try:
                self._sync_active_display_context_for_visible_page()
            except Exception:
                pass
            if refresh_navigation:
                self.update_navigation_ui()
            return False
        self.current_device_preview_page_index = new_idx
        self.render_current_page(refresh_navigation=refresh_navigation)
        return True

    def _set_current_page_index(self: MainWindow, index: object, *, refresh_navigation: bool = False) -> bool:
        nav_state = studio_logic.build_navigation_target_state(
            total=self._xtc_page_count(),
            current_index=getattr(self, 'current_page_index', 0),
            target_index=index,
        )
        if not self._payload_bool_value(nav_state, 'active', False):
            if refresh_navigation:
                self.update_navigation_ui()
            return False
        new_idx = self._payload_int_value(
            nav_state,
            'target_index',
            int(getattr(self, 'current_page_index', 0)),
        )
        if new_idx == getattr(self, 'current_page_index', 0):
            try:
                self._sync_active_display_context_for_visible_page()
            except Exception:
                pass
            if refresh_navigation:
                self.update_navigation_ui()
            return False
        self.current_page_index = new_idx
        self._refresh_loaded_xtc_viewer_profile_cache()
        self.render_current_page(refresh_navigation=refresh_navigation)
        return True

    def _apply_loaded_xtc_view_mode(self: MainWindow, mode: object, *, safe: bool = False) -> None:
        can_apply_full_view_mode = all(hasattr(self, name) for name in ('preview_stack', 'font_view_btn', 'device_view_btn'))
        can_apply_full_view_mode = can_apply_full_view_mode and hasattr(QTimer, 'singleShot')
        view_mode_state = studio_logic.build_loaded_xtc_view_mode_state(
            mode,
            safe=safe,
            can_apply_full_view_mode=can_apply_full_view_mode,
        )
        if not view_mode_state.get('has_mode'):
            return
        mode_text = str(view_mode_state.get('mode', '')).strip()
        if view_mode_state.get('apply_full_view_mode'):
            self.set_main_view_mode(mode_text)
            return
        self.main_view_mode = mode_text

    def _apply_loaded_xtc_ui_context(self: MainWindow, context: Mapping[str, object] | object) -> None:
        context = self._coerce_mapping_payload(context)
        if self._payload_bool_value(context, 'clear_loaded_state', False):
            self._clear_loaded_xtc_state()
        device_view_source = self._normalized_device_view_source_value(
            context.get('device_view_source'),
            default='',
        )
        if device_view_source:
            self.device_view_source = device_view_source
        selection_context = context.get('selection_context')
        if isinstance(selection_context, Mapping):
            self._apply_results_selection_context_with_fallback(selection_context)
        log_message = worker_logic._normalized_path_text(context.get('log_message')).strip()
        if log_message:
            try:
                self._append_log_without_status_or_status_bar(log_message)
            except Exception:
                pass
        if 'path_text' in context:
            normalized_path_text = worker_logic._normalized_path_text(context.get('path_text')).strip()
            self._loaded_xtc_path_text = normalized_path_text or None
        if 'display_name' in context:
            display_name = context.get('display_name')
            normalized_display_name = worker_logic._normalized_path_text(display_name).strip()
            self._loaded_xtc_display_name = normalized_display_name or None
            self._set_current_xtc_display_name(display_name)
        self._apply_loaded_xtc_view_mode(
            context.get('view_mode'),
            safe=self._payload_bool_value(context, 'safe_view_mode', False),
        )

    def _apply_loaded_xtc_path_success(self: MainWindow, path_text: str, display_name: str) -> None:
        context = results_controller.build_loaded_xtc_path_success_context(
            path_text,
            display_name,
            self._result_item_paths(),
        )
        self._apply_loaded_xtc_ui_context(context)

    def _apply_loaded_xtc_path_failure(self: MainWindow) -> None:
        self._apply_loaded_xtc_ui_context(results_controller.build_loaded_xtc_failure_context())

    def _restore_results_selection_after_xtc_load_failure(self: MainWindow) -> None:
        try:
            preview_active = self._is_preview_display_active()
        except Exception:
            preview_active = False
        if preview_active:
            self._clear_results_selection_with_fallback(
                results_controller.build_results_clear_selection_context()
            )
            return
        restored_path = worker_logic._normalized_path_text(getattr(self, '_loaded_xtc_path_text', None)).strip()
        if restored_path:
            if self._sync_results_selection_for_loaded_path_with_fallback(restored_path):
                return
        self._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )

    def _xtc_load_failure_preserved_display_name(self: MainWindow) -> str:
        try:
            preview_active = self._is_preview_display_active()
        except Exception:
            preview_active = False
        remembered_display_name = worker_logic._normalized_path_text(
            getattr(self, '_loaded_xtc_display_name', None)
        ).strip()
        remembered_path = worker_logic._normalized_path_text(
            getattr(self, '_loaded_xtc_path_text', None)
        ).strip()
        remembered_path_display_name = ''
        if remembered_path:
            remembered_path_display_name = worker_logic._normalized_path_text(
                self._xtc_display_name(remembered_path)
            ).strip()
        label_text = ''
        if hasattr(self, 'current_xtc_label'):
            text_getter = getattr(self.current_xtc_label, 'text', None)
            try:
                label_text = text_getter() if callable(text_getter) else text_getter
            except Exception:
                label_text = ''
        return studio_logic.build_xtc_load_failure_preserved_display_name(
            preview_active=preview_active,
            remembered_display_name=remembered_display_name,
            remembered_path_display_name=remembered_path_display_name,
            current_label_text=label_text,
        )

    def _xtc_load_failure_status_message(self: MainWindow, path: object, exc: Exception) -> str:
        target = worker_logic._normalized_path_text(path).strip() or '指定ファイル'
        detail = worker_logic._normalized_path_text(exc).strip()
        preserved = self._xtc_load_failure_preserved_display_name()
        return studio_logic.build_xtc_load_failure_status_message(
            target,
            detail,
            preserved,
        )

    def _apply_loaded_xtc_bytes_success(self: MainWindow) -> None:
        self._apply_loaded_xtc_ui_context(results_controller.build_loaded_xtc_bytes_success_context())

    def open_xtc_file(self: MainWindow) -> None:
        path, _ = self._get_open_file_name_with_status_fallback(
            'XTC/XTCHを開く',
            str(Path.home()),
            'XTC / XTCH Files (*.xtc *.xtch)',
            warning_title='XTC読込エラー',
            fallback_status_message='XTC/XTCH選択ダイアログを開けませんでした。',
        )
        if path:
            load_succeeded = self._load_xtc_from_path_with_result(path)
            if hasattr(self, 'bottom_tabs'):
                try:
                    self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX if load_succeeded else LOG_TAB_INDEX)
                except Exception:
                    APP_LOGGER.exception('XTC手動読込時のタブ切替に失敗しました')

    def load_xtc_from_path(self: MainWindow, path: object) -> bool:
        try:
            payload = self._xtc_source_document_payload(path)
            self._apply_xtc_document_payload(payload)
            self._apply_loaded_xtc_path_success(
                str(payload.get('path_text', '')),
                str(payload.get('display_name', '')),
            )
            return True
        except Exception as exc:
            self._restore_results_selection_after_xtc_load_failure()
            status_message = self._xtc_load_failure_status_message(path, exc)
            reflect_failure_in_status = not self._visible_render_failure_status_text()
            self._append_log_with_status_fallback(
                status_message,
                reflect_in_status=reflect_failure_in_status,
            )
            try:
                self._show_critical_dialog_with_status_fallback(
                    'XTC読込エラー',
                    str(exc),
                    fallback_status_message=status_message,
                )
            except Exception:
                try:
                    APP_LOGGER.exception('XTC読込エラーダイアログの表示に失敗しました')
                except Exception:
                    pass
            return False

    def load_xtc_from_bytes(self: MainWindow, data: bytes) -> None:
        self._apply_xtc_document_payload(self._xtc_document_payload(data))
        self._apply_loaded_xtc_bytes_success()

    def render_current_page(self: MainWindow, *, refresh_navigation: bool = True) -> None:
        device_view_visible = self._normalized_main_view_mode(
            getattr(self, 'main_view_mode', 'font')
        ) == 'device'
        effective_source = self._effective_device_view_source()
        if effective_source == 'preview':
            try:
                self._sync_preview_display_context_for_device_view()
            except Exception:
                pass
            preview_profile = self._active_device_viewer_profile()
            if hasattr(self, 'viewer_widget'):
                try:
                    self.viewer_widget.set_profile(preview_profile)
                except Exception:
                    pass
            pages = self._runtime_device_preview_pages()
            current_index = self._normalized_device_preview_page_index(getattr(self, 'current_device_preview_page_index', 0), total=len(pages))
            self.current_device_preview_page_index = current_index
            cache_key = self._device_preview_page_qimage_cache_key(current_index)
            cached_qimage = self._cached_device_preview_page_qimage(cache_key)
            if cached_qimage is not None:
                qimg = cached_qimage
            else:
                try:
                    raw = base64.b64decode(self._coerce_preview_base64_text(pages[current_index]), validate=True)
                    qimg = QImage.fromData(raw, 'PNG')
                    qimg_is_null = getattr(qimg, 'isNull', None)
                    if callable(qimg_is_null) and qimg_is_null():
                        raise RuntimeError('プレビュー画像の読み込みに失敗しました。')
                except Exception as exc:
                    self._handle_xtc_render_failure(exc, refresh_navigation=refresh_navigation)
                    return
                self._store_device_preview_page_qimage(cache_key, qimg)
            preview_profile = self._active_device_viewer_profile(qimg)
            self._apply_rendered_xtc_page(
                qimg,
                refresh_navigation=refresh_navigation,
                profile=preview_profile,
            )
            return

        if self._normalized_device_view_source_value(getattr(self, 'device_view_source', 'xtc')) != 'xtc':
            self.device_view_source = 'xtc'
        should_sync_loaded_display_context = device_view_visible or not self._runtime_preview_pages()
        if should_sync_loaded_display_context:
            try:
                self._sync_loaded_xtc_display_context_for_device_view()
            except Exception:
                pass
        blob = self._current_xtc_page_blob()
        if blob is None:
            try:
                self._sync_blank_device_display_context()
            except Exception:
                pass
            self._clear_xtc_viewer_page(refresh_navigation=refresh_navigation)
            return
        cache_key = self._xtc_page_qimage_cache_key()
        cached_qimage = self._cached_xtc_page_qimage(cache_key)
        if cached_qimage is not None:
            qi = cached_qimage
        else:
            try:
                qi = xt_page_blob_to_qimage(blob)
            except Exception as exc:
                self._handle_xtc_render_failure(exc, refresh_navigation=refresh_navigation)
                return
            self._store_xtc_page_qimage(cache_key, qi)
        self._apply_rendered_xtc_page(
            qi,
            refresh_navigation=refresh_navigation,
            profile=self._active_device_viewer_profile(qi),
        )

    # ── 設定の保存 / 読み込み ──────────────────────────────

    def _restore_settings(self: MainWindow) -> None:
        previous_shutdown_clean = bool(self.__dict__.get('_previous_shutdown_clean', True))
        window_payload = self._window_state_restore_payload()
        if not previous_shutdown_clean:
            window_payload = dict(window_payload)
            window_payload['geometry'] = None
            window_payload['is_maximized'] = False
            window_payload['left_splitter_state'] = None
            APP_LOGGER.warning('前回終了が正常に完了していないため、ウィンドウ配置の復元をスキップしました')
        default_size = self._default_window_size()
        window_width = max(1100, self._payload_int_value(window_payload, 'window_width', int(default_size.width())))
        window_height = max(760, self._payload_int_value(window_payload, 'window_height', int(default_size.height())))
        is_maximized = self._payload_bool_value(window_payload, 'is_maximized', False)
        left_w = max(0, self._payload_int_value(window_payload, 'left_panel_width', DEFAULT_LEFT_PANEL_WIDTH))
        left_splitter_sizes = self._payload_splitter_sizes_value(
            window_payload,
            'left_splitter_sizes',
            self._default_left_splitter_sizes(),
        )
        stored_left_vis = self._payload_bool_value(window_payload, 'left_panel_visible', True)
        left_vis = True

        geometry_restored = False
        geometry_state = window_payload.get('geometry')
        if geometry_state is not None:
            try:
                geometry_restored = bool(self.restoreGeometry(geometry_state))
            except Exception:
                geometry_restored = False
        if not geometry_restored:
            self.resize(window_width, window_height)
        if is_maximized:
            self.showMaximized()

        splitter_restored = False
        splitter_state = window_payload.get('left_splitter_state')
        if splitter_state is not None:
            try:
                splitter_restored = bool(self.left_splitter.restoreState(splitter_state))
            except Exception:
                splitter_restored = False
        if not splitter_restored:
            self.left_splitter.setSizes(left_splitter_sizes)

        restore_payload = self._settings_restore_payload()
        if not previous_shutdown_clean:
            restore_payload = dict(restore_payload)
            restore_payload['target'] = ''
            restore_payload['main_view_mode'] = 'font'
            APP_LOGGER.warning('前回終了が正常に完了していないため、変換対象と表示モードの自動復元をスキップしました')
        restore_payload = self._startup_preview_defaults_payload(restore_payload)

        with _bulk_block_signals(*self._restore_settings_widgets()):
            self._apply_settings_payload_to_ui(restore_payload)
            self._restore_preset_selection()

        self._apply_viewer_display_runtime_state()
        self._apply_render_option_ui_state()
        self.on_profile_changed()
        self.set_ui_theme(self._settings_str_value('ui_theme', 'light'), persist=False)
        panel_button_visible = self._settings_bool_value('panel_button_visible', True)
        self.set_panel_button_visible(bool(panel_button_visible), persist=False)
        self.current_preview_mode = 'text'

        self.left_panel.setVisible(left_vis)
        self._pending_left_panel_width = left_w if left_w > 0 else None
        if not stored_left_vis and self._pending_left_panel_width is None:
            self._pending_left_panel_width = left_w if left_w > 0 else DEFAULT_LEFT_PANEL_WIDTH

        # 起動復元では、保存済み target に対するプレビュー生成・EPUB 解析・
        # 実機ページ再描画を開始しない。表示だけ dirty にして、
        # ユーザーが「プレビュー更新」を押すまで待つ。
        self.mark_preview_dirty_for_target_change()

        self._refresh_preset_ui()
        self._update_top_status()
        self._initialized = True

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
        help_message = '使い方ダイアログを開けませんでした。'
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle('使い方')
            dlg.resize(640, 500)
            lay = QVBoxLayout(dlg)
            tv = QTextEdit(dlg)
            tv.setReadOnly(True)
            tv.setPlainText("""\
【基本的な流れ】
1. 上部の「ファイル」または「フォルダ」で変換対象を選びます。
2. 左側の設定を調整します。
3. 必要に応じて上部の「プレビュー更新」で手動再描画します。
4. 右側のフォントビューで文字の見え方を確認します。
5. 「▶ 変換実行」を押すと .xtc / .xtch を保存します。
6. 変換後は実機ビューで XTC を確認できます。

【プレビュー】
・フォントビュー: 設定中の文字の見え方を確認します。
・実機ビュー: 変換後の XTC を X3/X4 の外形で確認します。
・ページ送りは右ペインの「前/次」ボタン、またはページ番号入力で行います。
・「ボタン反転」を ON にすると、前/次 ボタンの左右配置と動作感を入れ替えられます。

【右ペイン表示ツールバー】
・「実寸近似」は PC 画面上の実機サイズに近い表示へ切り替えます。
・実寸近似 ON 中は、右ペイン倍率のラベルが「実寸補正」に変わります。
・実寸補正は、定規で実物と比較しながら右ペイン側で調整してください。
・「ガイド」は余白・非描画域の補助線を表示します。

【左ペインの出力・機種設定】
・機種選択は「出力・フォント・組版」内の出力形式付近にあります。
・機種を選ぶと解像度が自動設定されます（Custom では手動指定）。

【ファイルビューワー】
・「XTC/XTCHを開く」から既存の .xtc / .xtch ファイルを右ペインの実機ビューへ読み込めます。

【プリセット】
・コンボボックスで選択し「プリセット適用」で呼び出します。
・「組版保存」で現在の設定を上書きします。
・プリセットには禁則処理モードも保存されます。

【下部パネル】
・「変換結果」タブでファイルをクリックすると実機ビューへ読み込みます。
・「ログ」タブで変換の詳細を確認できます。

【表示設定】
・右上の歯車から、白基調 / ダーク の切替ができます。
・同じ画面で、三本線ボタンの表示 / 非表示も切り替えられます。

【補足】
・停止ボタンは変換中のみ有効です。
・同名ファイルがある場合の動作は、右上の歯車メニュー内「その他オプション > 同名出力」で選べます。
・変換後は「変換結果」タブの先頭に保存件数やエラー件数の概要を表示します。
""")
            lay.addWidget(tv)
            close_btn = QPushButton('閉じる')
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
