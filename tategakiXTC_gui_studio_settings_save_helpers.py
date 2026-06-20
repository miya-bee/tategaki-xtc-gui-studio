from __future__ import annotations

"""Settings/window-state save payload helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._safe_widget_value`` etc.) and read Qt widget state via ``window``,
so instance-level overrides installed by tests keep working.  This module
intentionally does not import PySide6 or ``tategakiXTC_gui_studio``.
"""

from pathlib import Path
from typing import Any
import logging

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_settings_controller as settings_controller

from tategakiXTC_gui_studio_constants import (
    DEFAULT_RENDER_SETTINGS,
    DEFAULT_PREVIEW_PAGE_LIMIT,
    DEVICE_PROFILES,
    KINSOKU_MODE_LABELS,
    GLYPH_POSITION_MODE_LABELS,
    OUTPUT_FORMAT_LABELS,
    OUTPUT_CONFLICT_LABELS,
    CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY,
    CENTER_SETTINGS_LEGACY_SPLITTER_TOP_KEY,
    CENTER_SETTINGS_LEGACY_SPLITTER_BOTTOM_KEY,
    PRESET_PANEL_WIDTH_KEY,
    CENTER_SETTINGS_PANEL_WIDTH_KEY,
    PREVIEW_PANEL_WIDTH_KEY,
    MAIN_THREE_PANE_SPLITTER_STATE_KEY,
    THREE_PANE_PANEL_WIDTH_KEYS,
)

WorkerConversionSettings = worker_logic.WorkerConversionSettings
APP_LOGGER = logging.getLogger('tategaki_xtc')


def _current_render_settings_base(window: Any) -> WorkerConversionSettings:
    width, height = window._effective_output_dimensions()
    defaults = DEFAULT_RENDER_SETTINGS
    return {
        'target': worker_logic.normalize_target_path_text(window._safe_line_edit_text('target_edit')),
        'output_dir': worker_logic.normalize_target_path_text(window.__dict__.get('selected_output_dir', '')),
        'font_file': window.current_font_value() if hasattr(window, 'current_font_value') else str(defaults['font_file']),
        'font_size': window._safe_widget_value('font_size_spin', defaults['font_size']),
        'ruby_size': window._safe_widget_value('ruby_size_spin', defaults['ruby_size']),
        'ruby_hide': window._safe_widget_checked('ruby_hide_check', bool(defaults['ruby_hide'])),
        'page_number_enabled': window._safe_widget_checked('page_number_check', bool(defaults.get('page_number_enabled', False))),
        'page_number_font_size': window._safe_widget_value('page_number_font_size_spin', int(defaults.get('page_number_font_size', 12))),
        'progress_bar_enabled': window._safe_widget_checked('progress_bar_check', bool(defaults.get('progress_bar_enabled', False))),
        'progress_bar_position': window._safe_combo_data('progress_bar_position_combo', str(defaults.get('progress_bar_position', 'center'))),
        'line_spacing': window._safe_widget_value('line_spacing_spin', defaults['line_spacing']),
        'margin_t': window._safe_widget_value('margin_t_spin', defaults['margin_t']),
        'margin_b': window._safe_widget_value('margin_b_spin', defaults['margin_b']),
        'margin_r': window._safe_widget_value('margin_r_spin', defaults['margin_r']),
        'margin_l': window._safe_widget_value('margin_l_spin', defaults['margin_l']),
        'dither': window._safe_widget_checked('dither_check', bool(defaults['dither'])),
        'threshold': window._safe_widget_value('threshold_spin', defaults['threshold']),
        'night_mode': window._safe_widget_checked('night_check', bool(defaults['night_mode'])),
        'kinsoku_mode': window.current_kinsoku_mode() if hasattr(window, 'current_kinsoku_mode') else str(defaults['kinsoku_mode']),
        'tatechuyoko_digit_mode': window.current_tatechuyoko_digit_mode() if hasattr(window, 'current_tatechuyoko_digit_mode') else str(defaults['tatechuyoko_digit_mode']),
        'punctuation_position_mode': window.current_punctuation_position_mode() if hasattr(window, 'current_punctuation_position_mode') else str(defaults['punctuation_position_mode']),
        'ichi_position_mode': window.current_ichi_position_mode() if hasattr(window, 'current_ichi_position_mode') else str(defaults['ichi_position_mode']),
        'halfwidth_digit_position_mode': window.current_halfwidth_digit_position_mode() if hasattr(window, 'current_halfwidth_digit_position_mode') else str(defaults['halfwidth_digit_position_mode']),
        'halfwidth_alpha_position_mode': window.current_halfwidth_alpha_position_mode() if hasattr(window, 'current_halfwidth_alpha_position_mode') else str(defaults['halfwidth_alpha_position_mode']),
        'latin_orientation_mode': window.current_latin_orientation_mode() if hasattr(window, 'current_latin_orientation_mode') else str(defaults['latin_orientation_mode']),
        'opening_bracket_indent_mode': window.current_opening_bracket_indent_mode() if hasattr(window, 'current_opening_bracket_indent_mode') else str(defaults.get('opening_bracket_indent_mode', 'none')),
        'middle_dot_position_mode': window.current_middle_dot_position_mode() if hasattr(window, 'current_middle_dot_position_mode') else str(defaults['middle_dot_position_mode']),
        'tatechuyoko_symbol_position_mode': window.current_tatechuyoko_symbol_position_mode() if hasattr(window, 'current_tatechuyoko_symbol_position_mode') else str(defaults['tatechuyoko_symbol_position_mode']),
        'lower_closing_bracket_position_mode': window.current_lower_closing_bracket_position_mode() if hasattr(window, 'current_lower_closing_bracket_position_mode') else str(defaults['lower_closing_bracket_position_mode']),
        'wave_dash_drawing_mode': window.current_wave_dash_drawing_mode() if hasattr(window, 'current_wave_dash_drawing_mode') else str(defaults['wave_dash_drawing_mode']),
        'wave_dash_position_mode': window.current_wave_dash_position_mode() if hasattr(window, 'current_wave_dash_position_mode') else str(defaults['wave_dash_position_mode']),
        'output_format': window.current_output_format() if hasattr(window, 'current_output_format') else str(defaults['output_format']),
        'width': width,
        'height': height,
    }


def current_settings_dict(window: Any) -> WorkerConversionSettings:
    return settings_controller.build_current_settings_payload(
        render_settings_base=window._current_render_settings_base(),
        output_conflict=window.current_output_conflict_mode(),
        # v1.3.3.48: 変換完了後に Windows エクスプローラーを自動起動しない。
        # 保存先を開く操作は完了カード / 変換結果タブの手動ボタンに限定する。
        open_folder=False,
    )


def _folder_batch_worker_settings(
    window: Any,
    source_path: object = None,
    output_path: object = None,
    item: object = None,
) -> WorkerConversionSettings:
    """Return current worker settings for one folder-batch item.

    The folder-batch worker bridge overrides target/output fields per item,
    so this hook deliberately avoids the normal single-file output-name
    prompt used by ``_prepare_conversion_settings()``.
    """
    return dict(window.current_settings_dict())



def prepare_conversion_settings(
    window: Any,
    *,
    qinputdialog_cls: Any,
    path_cls: Any = Path,
    sanitize_output_stem_func: Any,
) -> WorkerConversionSettings | None:
    cfg = window.current_settings_dict()
    target_value = str(cfg.get('target', '')).strip()
    supported = window._supported_targets_for_path(target_value)
    is_file_target = path_cls(target_value).is_file() if target_value else False
    if not studio_logic.should_prompt_for_output_name(len(supported), is_file_target):
        return cfg

    current_name = sanitize_output_stem_func(window._settings_str_value('last_output_name', ''))
    default_name = window._default_output_name_for_target(supported[0])
    suggested = studio_logic.suggest_output_name_for_target(
        current_name,
        default_name,
        target_path=supported[0],
        last_output_source=window._settings_str_value('last_output_source', ''),
    )
    new_name, ok = qinputdialog_cls.getText(
        window, '出力ファイル名', '保存する .xtc / .xtch のファイル名を入力してください', text=suggested,
    )
    if not ok:
        try:
            window._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        try:
            window._show_ui_status_message_with_reflection_or_direct_fallback('変換をキャンセルしました。', 3000)
        except Exception:
            pass
        return None

    sanitized = sanitize_output_stem_func(new_name)
    if not sanitized:
        try:
            window._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        window._show_warning_dialog_with_status_fallback('出力ファイル名', '空の名前は使えません。')
        return None

    cfg['output_name'] = sanitized
    window.settings_store.setValue('last_output_name', sanitized)
    try:
        window.settings_store.setValue('last_output_source', str(supported[0]))
    except Exception:
        APP_LOGGER.exception('最終出力名の入力元保存に失敗しました')
    window.settings_store.sync()
    return cfg

def _window_state_save_payload(window: Any) -> dict[str, object]:
    normal_geom = window.normalGeometry() if window.isMaximized() else window.geometry()
    raw_payload: dict[str, object] = {
        'window_width': int(normal_geom.width()),
        'window_height': int(normal_geom.height()),
        'is_maximized': bool(window.isMaximized()),
        # Keep the historical payload / INI key names, but resolve the
        # v1.3.8 center-settings splitter through center-named helpers.
        CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY: window._center_settings_splitter_state_value(),
        'left_panel_visible': window.left_panel.isVisible(),
    }
    if not window.isMaximized():
        raw_payload['geometry'] = window.saveGeometry()
    sizes = window.main_splitter.sizes()
    left_panel_width = 0
    if len(sizes) >= 3:
        preset_width, center_width, _preview_width = sizes[:3]
        for key, width in zip(THREE_PANE_PANEL_WIDTH_KEYS, sizes[:3]):
            if width > 0:
                raw_payload[key] = width
        if preset_width > 0 or center_width > 0:
            left_panel_width = max(0, preset_width) + max(0, center_width)
        raw_payload[MAIN_THREE_PANE_SPLITTER_STATE_KEY] = window.main_splitter.saveState()
    elif sizes and sizes[0] > 0:
        left_panel_width = sizes[0]
    elif not window.left_panel.isVisible():
        pending_width = getattr(window, '_pending_left_panel_width', None)
        if pending_width and pending_width > 0:
            left_panel_width = pending_width
    if left_panel_width > 0:
        raw_payload['left_panel_width'] = left_panel_width
    center_settings_splitter_sizes = window._center_settings_splitter_sizes_value()
    if len(center_settings_splitter_sizes) >= 2:
        raw_payload[CENTER_SETTINGS_LEGACY_SPLITTER_TOP_KEY] = center_settings_splitter_sizes[0]
        raw_payload[CENTER_SETTINGS_LEGACY_SPLITTER_BOTTOM_KEY] = center_settings_splitter_sizes[1]
    payload = studio_logic.build_window_state_save_payload(raw_payload)
    if raw_payload.get(MAIN_THREE_PANE_SPLITTER_STATE_KEY) is not None:
        payload[MAIN_THREE_PANE_SPLITTER_STATE_KEY] = raw_payload.get(MAIN_THREE_PANE_SPLITTER_STATE_KEY)
    if raw_payload.get(PRESET_PANEL_WIDTH_KEY) is not None and raw_payload.get(CENTER_SETTINGS_PANEL_WIDTH_KEY) is not None:
        payload[PRESET_PANEL_WIDTH_KEY] = raw_payload[PRESET_PANEL_WIDTH_KEY]
        payload[CENTER_SETTINGS_PANEL_WIDTH_KEY] = raw_payload[CENTER_SETTINGS_PANEL_WIDTH_KEY]
    if raw_payload.get(PREVIEW_PANEL_WIDTH_KEY) is not None:
        payload[PREVIEW_PANEL_WIDTH_KEY] = raw_payload[PREVIEW_PANEL_WIDTH_KEY]
    return payload


def _settings_save_payload(window: Any) -> dict[str, object]:
    ui_state = settings_controller.build_settings_save_ui_state(
        bottom_tab_index=int(window.bottom_tabs.currentIndex()),
        main_view_mode=getattr(window, 'main_view_mode', 'font'),
        ui_theme=str(getattr(window, 'current_ui_theme', 'light') or 'light'),
        panel_button_visible=bool(getattr(window, 'panel_button_visible', True)),
        preset_index=int(window.preset_combo.currentIndex()),
        preset_key=window.selected_preset_key() or '',
        profile=window._selected_profile_key(),
        actual_size=window.actual_size_check.isChecked(),
        show_guides=window.guides_check.isChecked(),
        calibration_pct=int(window.calib_spin.value()),
        nav_buttons_reversed=window.nav_reverse_check.isChecked(),
        preview_page_limit=window.preview_page_limit_spin.value() if hasattr(window, 'preview_page_limit_spin') else DEFAULT_PREVIEW_PAGE_LIMIT,
        ui_language=window.current_ui_language_value(),
    )
    payload = settings_controller.build_settings_save_payload(
        current_settings=window.current_settings_dict(),
        ui_state=ui_state,
        allowed_view_modes={'font'},
        allowed_profiles=DEVICE_PROFILES,
        allowed_kinsoku_modes=KINSOKU_MODE_LABELS,
        allowed_glyph_position_modes=GLYPH_POSITION_MODE_LABELS,
        allowed_output_formats=OUTPUT_FORMAT_LABELS,
        allowed_output_conflicts=OUTPUT_CONFLICT_LABELS,
        default_preview_page_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
    )
    payload.update(window._bottom_overlay_margin_auto_save_payload())
    payload['preview_zoom_pct'] = window._normalize_preview_zoom_pct()
    return payload
