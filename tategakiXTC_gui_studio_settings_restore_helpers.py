from __future__ import annotations

"""Settings restore/apply helpers for :mod:`tategakiXTC_gui_studio`.

These helpers keep MainWindow-compatible settings orchestration out of the
large GUI entry module while intentionally preserving the existing runtime
behavior.  They accept the window object and call its existing small methods so
no widget ownership or signal wiring changes are introduced.
"""

import logging
from typing import Any, Mapping

import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_settings_controller as settings_controller
import tategakiXTC_worker_logic as worker_logic

from tategakiXTC_gui_studio_constants import (
    CENTER_SETTINGS_LEGACY_SPLITTER_SIZES_KEY,
    CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY,
    DEFAULT_LEFT_PANEL_WIDTH,
    DEFAULT_PREVIEW_PAGE_LIMIT,
    GLYPH_POSITION_MODE_LABELS,
    LATIN_ORIENTATION_MODE_LABELS,
    OPENING_BRACKET_INDENT_MODE_LABELS,
    KINSOKU_MODE_LABELS,
    MAIN_THREE_PANE_SPLITTER_SIZES_KEY,
    MAIN_THREE_PANE_SPLITTER_STATE_KEY,
    OUTPUT_CONFLICT_LABELS,
    OUTPUT_FORMAT_LABELS,
    PREVIEW_PANEL_WIDTH_KEY,
    THREE_PANE_SPLITTER_KEYS,
    DEVICE_PROFILES,
)
from tategakiXTC_gui_studio_ui_helpers import _bulk_block_signals

APP_LOGGER = logging.getLogger('tategaki_xtc')


def apply_settings_payload_to_ui(window: Any, payload: dict[str, object]) -> None:
    """Apply a normalized settings payload to an existing MainWindow object."""
    self = window
    apply_defaults = settings_controller.build_settings_ui_apply_defaults(
        actual_size=self._safe_widget_checked('actual_size_check'),
        show_guides=self._safe_widget_checked('guides_check'),
        calibration_pct=self._safe_widget_value('calib_spin', 100),
        nav_buttons_reversed=getattr(self, 'nav_buttons_reversed', False),
        font_size=self._safe_widget_value('font_size_spin', 26),
        ruby_size=self._safe_widget_value('ruby_size_spin', 12),
        ruby_hide=self._safe_widget_checked('ruby_hide_check'),
        page_number_enabled=self._safe_widget_checked('page_number_check'),
        page_number_font_size=self._safe_widget_value('page_number_font_size_spin', 12),
        progress_bar_enabled=self._safe_widget_checked('progress_bar_check'),
        progress_bar_position=self._safe_combo_data('progress_bar_position_combo', 'center'),
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
        output_format=self._safe_combo_data('output_format_combo', 'xtch'),
        kinsoku_mode=self._safe_combo_data('kinsoku_mode_combo', 'standard'),
        tatechuyoko_digit_mode=self._safe_combo_data('tatechuyoko_digit_mode_combo', '2'),
        punctuation_position_mode=self._safe_combo_data('punctuation_position_combo', 'standard'),
        ichi_position_mode=self._safe_combo_data('ichi_position_combo', 'standard'),
        halfwidth_digit_position_mode=self._safe_combo_data('halfwidth_digit_position_combo', 'standard'),
        halfwidth_alpha_position_mode=self._safe_combo_data('halfwidth_alpha_position_combo', 'standard'),
        latin_orientation_mode=self._safe_combo_data('latin_orientation_combo', 'vertical'),
        opening_bracket_indent_mode=self._safe_combo_data('opening_bracket_indent_combo', 'none'),
        middle_dot_position_mode=self._safe_combo_data('middle_dot_position_combo', 'standard'),
        tatechuyoko_symbol_position_mode=self._safe_combo_data('tatechuyoko_symbol_position_combo', 'standard'),
        lower_closing_bracket_position_mode=self._safe_combo_data('lower_closing_bracket_position_combo', 'standard'),
        wave_dash_drawing_mode=self._safe_combo_data('wave_dash_drawing_combo', 'rotate'),
        wave_dash_position_mode=self._safe_combo_data('wave_dash_position_combo', 'standard'),
        main_view_mode=getattr(self, 'main_view_mode', 'font'),
    )
    apply_plan = settings_controller.build_settings_ui_apply_plan(
        raw_payload=payload,
        defaults=apply_defaults,
        allowed_view_modes={'font'},
        allowed_kinsoku_modes=KINSOKU_MODE_LABELS,
        allowed_glyph_position_modes=GLYPH_POSITION_MODE_LABELS,
        allowed_output_formats=OUTPUT_FORMAT_LABELS,
        allowed_output_conflicts=OUTPUT_CONFLICT_LABELS,
        bottom_tab_count=self.bottom_tabs.count() if hasattr(self, 'bottom_tabs') else 0,
    )

    if 'ui_language' in apply_plan:
        self._set_language_combo_value(apply_plan.get('ui_language'))

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
        ('page_number_font_size', getattr(self, 'page_number_font_size_spin', None)),
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

    if 'ruby_hide' in apply_plan:
        getattr(self, 'ruby_hide_check', None) is not None and self.ruby_hide_check.setChecked(bool(apply_plan['ruby_hide']))
    if 'page_number_enabled' in apply_plan:
        getattr(self, 'page_number_check', None) is not None and self.page_number_check.setChecked(bool(apply_plan['page_number_enabled']))
    if getattr(self, 'page_number_font_size_spin', None) is not None and getattr(self, 'page_number_check', None) is not None:
        self.page_number_font_size_spin.setEnabled(bool(self.page_number_check.isChecked()))
    if 'progress_bar_enabled' in apply_plan:
        getattr(self, 'progress_bar_check', None) is not None and self.progress_bar_check.setChecked(bool(apply_plan['progress_bar_enabled']))
    if 'progress_bar_position' in apply_plan:
        getattr(self, 'progress_bar_position_combo', None) is not None and self._set_combo_to_data(self.progress_bar_position_combo, str(apply_plan['progress_bar_position']))
    if getattr(self, 'progress_bar_position_combo', None) is not None and getattr(self, 'progress_bar_check', None) is not None:
        self.progress_bar_position_combo.setEnabled(bool(self.progress_bar_check.isChecked()))
    self._restore_bottom_overlay_margin_auto_state_from_payload(payload)
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
    if 'tatechuyoko_digit_mode' in apply_plan:
        getattr(self, 'tatechuyoko_digit_mode_combo', None) is not None and self._set_combo_to_data(self.tatechuyoko_digit_mode_combo, str(apply_plan['tatechuyoko_digit_mode']))
    if 'punctuation_position_mode' in apply_plan:
        getattr(self, 'punctuation_position_combo', None) is not None and self._set_combo_to_data(self.punctuation_position_combo, str(apply_plan['punctuation_position_mode']))
    if 'ichi_position_mode' in apply_plan:
        getattr(self, 'ichi_position_combo', None) is not None and self._set_combo_to_data(self.ichi_position_combo, str(apply_plan['ichi_position_mode']))
    if 'halfwidth_digit_position_mode' in apply_plan:
        getattr(self, 'halfwidth_digit_position_combo', None) is not None and self._set_combo_to_data(self.halfwidth_digit_position_combo, str(apply_plan['halfwidth_digit_position_mode']))
    if 'halfwidth_alpha_position_mode' in apply_plan:
        getattr(self, 'halfwidth_alpha_position_combo', None) is not None and self._set_combo_to_data(self.halfwidth_alpha_position_combo, str(apply_plan['halfwidth_alpha_position_mode']))
    if 'latin_orientation_mode' in apply_plan:
        getattr(self, 'latin_orientation_combo', None) is not None and self._set_combo_to_data(self.latin_orientation_combo, str(apply_plan['latin_orientation_mode']))
    if 'opening_bracket_indent_mode' in apply_plan:
        getattr(self, 'opening_bracket_indent_combo', None) is not None and self._set_combo_to_data(self.opening_bracket_indent_combo, str(apply_plan['opening_bracket_indent_mode']))
    if 'middle_dot_position_mode' in apply_plan:
        getattr(self, 'middle_dot_position_combo', None) is not None and self._set_combo_to_data(self.middle_dot_position_combo, str(apply_plan['middle_dot_position_mode']))
    if 'tatechuyoko_symbol_position_mode' in apply_plan:
        getattr(self, 'tatechuyoko_symbol_position_combo', None) is not None and self._set_combo_to_data(self.tatechuyoko_symbol_position_combo, str(apply_plan['tatechuyoko_symbol_position_mode']))
    if 'lower_closing_bracket_position_mode' in apply_plan:
        getattr(self, 'lower_closing_bracket_position_combo', None) is not None and self._set_combo_to_data(self.lower_closing_bracket_position_combo, str(apply_plan['lower_closing_bracket_position_mode']))
    if 'wave_dash_drawing_mode' in apply_plan:
        getattr(self, 'wave_dash_drawing_combo', None) is not None and self._set_combo_to_data(self.wave_dash_drawing_combo, str(apply_plan['wave_dash_drawing_mode']))
    if 'wave_dash_position_mode' in apply_plan:
        getattr(self, 'wave_dash_position_combo', None) is not None and self._set_combo_to_data(self.wave_dash_position_combo, str(apply_plan['wave_dash_position_mode']))

    if 'target' in apply_plan:
        # プリセット/設定復元で変換対象が変わる場合も、ファイル選択・
        # ドロップ・手入力と同じ target 変更 helper を通して通常
        # プレビューへ戻す。
        self._set_target_path_for_normal_preview(
            str(apply_plan.get('target') or '').strip(),
            block_signals=False,
        )
    if 'output_dir' in apply_plan:
        self.selected_output_dir = worker_logic.normalize_target_path_text(str(apply_plan.get('output_dir') or ''))

    if 'main_view_mode' in apply_plan:
        hasattr(self, 'set_main_view_mode') and self.set_main_view_mode(str(apply_plan['main_view_mode']), initial=True)

    if 'bottom_tab_index' in apply_plan:
        hasattr(self, '_set_bottom_tab_index_with_fallback') and self._set_bottom_tab_index_with_fallback(int(apply_plan['bottom_tab_index']))

    if 'nav_buttons_reversed' in apply_plan:
        hasattr(self, 'update_navigation_ui') and self.update_navigation_ui()


def restore_settings(window: Any) -> None:
    """Restore persisted settings/window state for an existing MainWindow object."""
    self = window
    previous_shutdown_clean = bool(self.__dict__.get('_previous_shutdown_clean', True))
    window_payload = self._window_state_restore_payload()
    if not previous_shutdown_clean:
        window_payload = dict(window_payload)
        window_payload['geometry'] = None
        window_payload['is_maximized'] = False
        window_payload[CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY] = None
        window_payload['preset_settings_splitter_state'] = None
        window_payload[MAIN_THREE_PANE_SPLITTER_STATE_KEY] = None
        APP_LOGGER.warning('前回終了が正常に完了していないため、ウィンドウ配置の復元をスキップしました')
    default_size = self._default_window_size()
    window_width = max(1100, self._payload_int_value(window_payload, 'window_width', int(default_size.width())))
    window_height = max(760, self._payload_int_value(window_payload, 'window_height', int(default_size.height())))
    is_maximized = self._payload_bool_value(window_payload, 'is_maximized', False)
    left_w = max(0, self._payload_int_value(window_payload, 'left_panel_width', DEFAULT_LEFT_PANEL_WIDTH))
    # v1.3.8.3: 3ペイン試作では左+中央の合計幅を使うため、
    # v1.3.6 以前の2ペイン保存幅が残っている環境では新既定値へ寄せる。
    if left_w < 940 or left_w in (760, 800, 820):
        left_w = DEFAULT_LEFT_PANEL_WIDTH
        window_payload = dict(window_payload)
        window_payload['left_panel_width'] = left_w
    center_settings_splitter_sizes = self._payload_splitter_sizes_value(
        window_payload,
        CENTER_SETTINGS_LEGACY_SPLITTER_SIZES_KEY,
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
        clamped_size = self._clamp_window_size_to_available(window_width, window_height)
        self.resize(clamped_size.width(), clamped_size.height())
    if is_maximized:
        self.showMaximized()

    self._restore_center_settings_splitter_from_payload(
        splitter_state=window_payload.get(CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY),
        splitter_sizes=center_settings_splitter_sizes,
    )

    three_pane_sizes = self._payload_three_pane_splitter_sizes_value(
        window_payload,
        MAIN_THREE_PANE_SPLITTER_SIZES_KEY,
        self._default_three_pane_splitter_sizes(),
    )
    if len(three_pane_sizes) < 3:
        legacy_preset_center = studio_logic.payload_splitter_sizes_value(
            window_payload,
            'preset_settings_splitter_sizes',
            self._default_preset_settings_splitter_sizes(),
            min_top=220,
            min_bottom=360,
        )
        legacy_preview = max(320, self._settings_int_value(PREVIEW_PANEL_WIDTH_KEY, 560))
        three_pane_sizes = [*legacy_preset_center[:2], legacy_preview]
    three_pane_restored = False
    three_pane_state = window_payload.get(MAIN_THREE_PANE_SPLITTER_STATE_KEY)
    if three_pane_state is not None and hasattr(self, 'main_splitter'):
        try:
            three_pane_restored = bool(self.main_splitter.restoreState(three_pane_state))
        except Exception:
            three_pane_restored = False
    if not three_pane_restored and hasattr(self, 'main_splitter'):
        try:
            self.main_splitter.setSizes(three_pane_sizes)
        except Exception:
            pass

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



def _has_restorable_user_settings(window: Any) -> bool:
    self = window
    """Return True when the ini contains user-facing state worth restoring.

    A crash or interrupted startup can leave only lifecycle metadata such as
    ``last_shutdown_clean=false`` in a freshly created ini.  Treating that
    bare marker as a full previous session forces the abnormal-shutdown
    restore path even though there is nothing to restore.  Keep that path for
    real saved settings, but allow a metadata-only ini to boot with normal
    defaults.
    """
    keys_getter = getattr(self.settings_store, 'allKeys', None)
    if not callable(keys_getter):
        return True
    try:
        raw_keys = list(keys_getter())
    except Exception:
        return True
    if not raw_keys:
        return False
    lifecycle_leaf_keys = {'last_shutdown_clean', 'settings_schema_version', 'last_app_version'}
    for raw_key in raw_keys:
        key = str(raw_key or '').strip().replace('\\', '/')
        if not key:
            continue
        leaf = key.rsplit('/', 1)[-1]
        if leaf not in lifecycle_leaf_keys:
            return True
    return False


def _window_state_restore_payload(window: Any) -> dict[str, object]:
    self = window
    default_size = self._default_window_size()
    default_width = int(default_size.width())
    default_height = int(default_size.height())
    raw_payload = {
        'geometry': self._settings_raw_value('geometry', None),
        'window_width': self._settings_raw_value('window_width', default_width),
        'window_height': self._settings_raw_value('window_height', default_height),
        'is_maximized': self._settings_raw_value('is_maximized', False),
        'left_panel_width': self._settings_raw_value('left_panel_width', DEFAULT_LEFT_PANEL_WIDTH),
        CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY: self._settings_raw_value(CENTER_SETTINGS_LEGACY_SPLITTER_STATE_KEY, None),
        CENTER_SETTINGS_LEGACY_SPLITTER_SIZES_KEY: self._default_left_splitter_sizes(),
        'left_panel_visible': self._settings_raw_value('left_panel_visible', True),
    }
    payload = studio_logic.build_window_state_restore_payload(
        raw_payload,
        default_width=default_width,
        default_height=default_height,
        default_left_panel_width=DEFAULT_LEFT_PANEL_WIDTH,
        default_left_splitter_sizes=self._default_left_splitter_sizes(),
    )
    raw_payload['preset_settings_splitter_state'] = self._settings_raw_value('preset_settings_splitter_state', None)
    raw_payload['preset_settings_splitter_sizes'] = self._default_preset_settings_splitter_sizes()
    payload['preset_settings_splitter_state'] = raw_payload.get('preset_settings_splitter_state')
    payload['preset_settings_splitter_sizes'] = studio_logic.payload_splitter_sizes_value(
        raw_payload,
        'preset_settings_splitter_sizes',
        self._default_preset_settings_splitter_sizes(),
        min_top=240,
        min_bottom=560,
    )
    three_pane_state_key, three_pane_sizes_key = THREE_PANE_SPLITTER_KEYS
    raw_payload[three_pane_state_key] = self._settings_raw_value(three_pane_state_key, None)
    raw_payload[three_pane_sizes_key] = self._default_three_pane_splitter_sizes()
    payload[three_pane_state_key] = raw_payload.get(three_pane_state_key)
    payload[three_pane_sizes_key] = self._payload_three_pane_splitter_sizes_value(
        raw_payload,
        three_pane_sizes_key,
        self._default_three_pane_splitter_sizes(),
    )
    return payload


def _settings_restore_payload(window: Any) -> dict[str, object]:
    self = window
    payload = settings_controller.build_settings_restore_payload(
        read_default_value=self._settings_default_value,
        default_font_name=self._default_font_name(),
        default_preview_page_limit=DEFAULT_PREVIEW_PAGE_LIMIT,
        allowed_view_modes={'font'},
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
    if not self._settings_contains_key('ui_language'):
        payload['ui_language'] = self._os_default_ui_language()
    else:
        payload['ui_language'] = self._normalize_ui_language(payload.get('ui_language'), self._os_default_ui_language())
    return payload


def _startup_preview_defaults_payload(window: Any, payload: Mapping[str, object]) -> dict[str, object]:
    self = window
    # sweep348: 通常倍率UIは実寸近似OFFのフォントビュー用。
    # 起動直後に保存済みの実寸近似/実機ビューを復元すると、倍率ボタンが
    # 近くにあるのに効かない状態に見えるため、起動時だけ右ペインを
    # 通常フォントビューへ戻す。通常倍率値そのものは別途復元する。
    return studio_logic.build_startup_preview_defaults_payload(payload)


__all__ = [
    'apply_settings_payload_to_ui',
    'restore_settings',
    '_has_restorable_user_settings',
    '_window_state_restore_payload',
    '_settings_restore_payload',
    '_startup_preview_defaults_payload',
]
