from __future__ import annotations

"""Settings orchestration helpers for the GUI layer.

This module prepares settings restore/save payloads without depending on Qt
widgets so MainWindow can stay thinner while behavior remains
regression-tested.
"""

from collections.abc import Callable, Collection, Mapping, Sequence
from typing import Any

import tategakiXTC_gui_studio_logic as studio_logic


SettingsValueReader = Callable[[str, object], object]


_RESTORE_DEFAULTS: tuple[tuple[str, object], ...] = (
    ('profile', 'x4'),
    ('actual_size', False),
    ('show_guides', True),
    ('calibration_pct', 100),
    ('nav_buttons_reversed', False),
    ('font_size', 26),
    ('ruby_size', 12),
    ('line_spacing', 44),
    ('margin_t', 12),
    ('margin_b', 14),
    ('margin_r', 12),
    ('margin_l', 12),
    ('threshold', 128),
    ('width', 480),
    ('height', 800),
    ('dither', False),
    ('night_mode', False),
    ('open_folder', True),
    ('output_conflict', 'rename'),
    ('output_format', 'xtc'),
    ('kinsoku_mode', 'standard'),
    ('target', ''),
    ('main_view_mode', 'font'),
    ('bottom_tab_index', 0),
)

def _coerce_mapping_payload(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}



_SAVE_UI_FIELDS: tuple[tuple[str, object], ...] = (
    ('bottom_tab_index', 0),
    ('main_view_mode', 'font'),
    ('ui_theme', 'light'),
    ('panel_button_visible', True),
    ('preset_index', -1),
    ('preset_key', ''),
    ('profile', 'x4'),
    ('actual_size', False),
    ('show_guides', True),
    ('calibration_pct', 100),
    ('nav_buttons_reversed', False),
)


def build_settings_restore_raw_payload(
    *,
    read_default_value: SettingsValueReader,
    default_font_name: str,
    default_preview_page_limit: int,
) -> dict[str, object]:
    payload = {
        key: read_default_value(key, default)
        for key, default in _RESTORE_DEFAULTS
    }
    payload['font_file'] = read_default_value('font_file', default_font_name)
    payload['preview_page_limit'] = read_default_value('preview_page_limit', default_preview_page_limit)
    return payload


def build_settings_restore_payload(
    *,
    read_default_value: SettingsValueReader,
    default_font_name: str,
    default_preview_page_limit: int,
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_profiles: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    normalize_font_setting_value: Callable[[object, str], str],
    normalize_target_path_text: Callable[[str], str],
    resolve_profile_dimensions: Callable[[object, object, object], tuple[str, object, int, int]],
) -> dict[str, object]:
    raw_payload = build_settings_restore_raw_payload(
        read_default_value=read_default_value,
        default_font_name=default_font_name,
        default_preview_page_limit=default_preview_page_limit,
    )
    payload = _coerce_mapping_payload(studio_logic.build_settings_restore_payload(
        raw_payload,
        allowed_view_modes=allowed_view_modes,
        allowed_profiles=allowed_profiles,
        allowed_kinsoku_modes=allowed_kinsoku_modes,
        allowed_output_formats=allowed_output_formats,
        allowed_output_conflicts=allowed_output_conflicts,
        default_preview_page_limit=default_preview_page_limit,
    ))
    saved_profile = str(payload.get('profile') or 'x4')
    _resolved_key, _profile, width, height = resolve_profile_dimensions(
        saved_profile,
        payload.get('width', 480),
        payload.get('height', 800),
    )
    payload['width'] = width
    payload['height'] = height
    payload['target'] = normalize_target_path_text(str(payload.get('target') or ''))
    payload['font_file'] = normalize_font_setting_value(payload.get('font_file'), default_font_name)
    return payload


def build_settings_ui_apply_defaults(
    *,
    actual_size: object,
    show_guides: object,
    calibration_pct: object,
    nav_buttons_reversed: object,
    font_size: object,
    ruby_size: object,
    line_spacing: object,
    margin_t: object,
    margin_b: object,
    margin_r: object,
    margin_l: object,
    threshold: object,
    preview_page_limit: object,
    dither: object,
    night_mode: object,
    open_folder: object,
    output_conflict: object,
    output_format: object,
    kinsoku_mode: object,
    main_view_mode: object,
) -> dict[str, object]:
    return {
        'actual_size': studio_logic._config_bool_value(actual_size, False),
        'show_guides': studio_logic._config_bool_value(show_guides, False),
        'calibration_pct': studio_logic._config_int_value(calibration_pct, 0),
        'nav_buttons_reversed': studio_logic._config_bool_value(nav_buttons_reversed, False),
        'font_size': studio_logic._config_int_value(font_size, 0),
        'ruby_size': studio_logic._config_int_value(ruby_size, 0),
        'line_spacing': studio_logic._config_int_value(line_spacing, 0),
        'margin_t': studio_logic._config_int_value(margin_t, 0),
        'margin_b': studio_logic._config_int_value(margin_b, 0),
        'margin_r': studio_logic._config_int_value(margin_r, 0),
        'margin_l': studio_logic._config_int_value(margin_l, 0),
        'threshold': studio_logic._config_int_value(threshold, 0),
        'preview_page_limit': studio_logic._config_int_value(preview_page_limit, 1),
        'dither': studio_logic._config_bool_value(dither, False),
        'night_mode': studio_logic._config_bool_value(night_mode, False),
        'open_folder': studio_logic._config_bool_value(open_folder, False),
        'output_conflict': output_conflict,
        'output_format': output_format,
        'kinsoku_mode': kinsoku_mode,
        'main_view_mode': str(main_view_mode or 'font'),
    }


def build_settings_ui_apply_plan(
    *,
    raw_payload: Mapping[str, object],
    defaults: Mapping[str, object],
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    bottom_tab_count: int,
) -> dict[str, object]:
    return studio_logic.build_settings_ui_apply_payload(
        raw_payload,
        defaults=defaults,
        allowed_view_modes=allowed_view_modes,
        allowed_kinsoku_modes=allowed_kinsoku_modes,
        allowed_output_formats=allowed_output_formats,
        allowed_output_conflicts=allowed_output_conflicts,
        bottom_tab_count=bottom_tab_count,
    )


def build_settings_save_ui_state(
    *,
    bottom_tab_index: object,
    main_view_mode: object,
    ui_theme: object,
    panel_button_visible: object,
    preset_index: object,
    preset_key: object,
    profile: object,
    actual_size: object,
    show_guides: object,
    calibration_pct: object,
    nav_buttons_reversed: object,
    preview_page_limit: object,
) -> dict[str, object]:
    return {
        'bottom_tab_index': studio_logic._config_int_value(bottom_tab_index, 0),
        'main_view_mode': str(main_view_mode or 'font'),
        'ui_theme': str(ui_theme or 'light'),
        'panel_button_visible': studio_logic._config_bool_value(panel_button_visible, True),
        'preset_index': studio_logic._config_int_value(preset_index, -1),
        'preset_key': str(preset_key or ''),
        'profile': str(profile or 'x4'),
        'actual_size': studio_logic._config_bool_value(actual_size, False),
        'show_guides': studio_logic._config_bool_value(show_guides, False),
        'calibration_pct': studio_logic._config_int_value(calibration_pct, 100),
        'nav_buttons_reversed': studio_logic._config_bool_value(nav_buttons_reversed, False),
        'preview_page_limit': studio_logic._config_int_value(preview_page_limit, 1),
    }


def build_settings_save_payload(
    *,
    current_settings: Mapping[str, object],
    ui_state: Mapping[str, object],
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_profiles: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, object]:
    raw_payload = build_settings_save_raw_payload(
        current_settings=current_settings,
        ui_state=ui_state,
        default_preview_page_limit=default_preview_page_limit,
    )
    return studio_logic.build_settings_save_payload(
        raw_payload,
        allowed_view_modes=allowed_view_modes,
        allowed_profiles=allowed_profiles,
        allowed_kinsoku_modes=allowed_kinsoku_modes,
        allowed_output_formats=allowed_output_formats,
        allowed_output_conflicts=allowed_output_conflicts,
        default_preview_page_limit=default_preview_page_limit,
    )

def build_current_settings_payload(
    *,
    render_settings_base: Mapping[str, object],
    output_conflict: object,
    open_folder: object,
) -> dict[str, object]:
    payload: dict[str, object] = _coerce_mapping_payload(render_settings_base)
    payload['output_conflict'] = output_conflict
    payload['open_folder'] = open_folder
    return payload


def build_current_preset_payload(
    *,
    render_settings_base: Mapping[str, object],
    profile: object,
    fallback_font: str,
    fallback_night_mode: bool,
    fallback_dither: bool,
    fallback_kinsoku_mode: str,
    fallback_output_format: str,
    normalize_preset_payload: Callable[..., dict[str, object]],
) -> dict[str, object]:
    render_settings = _coerce_mapping_payload(render_settings_base)
    payload = {
        'profile': str(profile or 'x4'),
        'width': studio_logic._config_int_value(render_settings.get('width'), 480),
        'height': studio_logic._config_int_value(render_settings.get('height'), 800),
        'font_size': studio_logic._config_int_value(render_settings.get('font_size'), 26),
        'ruby_size': studio_logic._config_int_value(render_settings.get('ruby_size'), 12),
        'line_spacing': studio_logic._config_int_value(render_settings.get('line_spacing'), 44),
        'margin_t': studio_logic._config_int_value(render_settings.get('margin_t'), 12),
        'margin_b': studio_logic._config_int_value(render_settings.get('margin_b'), 14),
        'margin_r': studio_logic._config_int_value(render_settings.get('margin_r'), 12),
        'margin_l': studio_logic._config_int_value(render_settings.get('margin_l'), 12),
        'threshold': studio_logic._config_int_value(render_settings.get('threshold'), 128),
    }
    return normalize_preset_payload(
        payload,
        fallback_font=fallback_font,
        fallback_night_mode=fallback_night_mode,
        fallback_dither=fallback_dither,
        fallback_kinsoku_mode=fallback_kinsoku_mode,
        fallback_output_format=fallback_output_format,
    )



def build_live_preset_widget_payload(
    *,
    profile: object,
    width: object,
    height: object,
    font_size: object,
    ruby_size: object,
    line_spacing: object,
    margin_t: object,
    margin_b: object,
    margin_r: object,
    margin_l: object,
    threshold: object,
    night_mode: object,
    dither: object,
    kinsoku_mode: object,
    output_format: object,
    font_file: object,
    default_font_name: str,
    allowed_profiles: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_output_formats: Collection[str] | Mapping[str, object],
    normalize_choice_value: Callable[[object, str, Collection[str] | Mapping[str, object]], str],
    normalize_font_setting_value: Callable[[object, str], str],
) -> dict[str, object]:
    payload: dict[str, object] = {}
    if profile is not None:
        payload['profile'] = normalize_choice_value(profile, 'x4', allowed_profiles)
    if width is not None:
        payload['width'] = studio_logic._config_int_value(width, 480)
    if height is not None:
        payload['height'] = studio_logic._config_int_value(height, 800)
    if font_size is not None:
        payload['font_size'] = studio_logic._config_int_value(font_size, 26)
    if ruby_size is not None:
        payload['ruby_size'] = studio_logic._config_int_value(ruby_size, 12)
    if line_spacing is not None:
        payload['line_spacing'] = studio_logic._config_int_value(line_spacing, 44)
    if margin_t is not None:
        payload['margin_t'] = studio_logic._config_int_value(margin_t, 12)
    if margin_b is not None:
        payload['margin_b'] = studio_logic._config_int_value(margin_b, 14)
    if margin_r is not None:
        payload['margin_r'] = studio_logic._config_int_value(margin_r, 12)
    if margin_l is not None:
        payload['margin_l'] = studio_logic._config_int_value(margin_l, 12)
    if threshold is not None:
        payload['threshold'] = studio_logic._config_int_value(threshold, 128)
    if night_mode is not None:
        payload['night_mode'] = studio_logic._config_bool_value(night_mode, False)
    if dither is not None:
        payload['dither'] = studio_logic._config_bool_value(dither, False)
    if kinsoku_mode is not None:
        payload['kinsoku_mode'] = normalize_choice_value(kinsoku_mode, 'standard', allowed_kinsoku_modes)
    if output_format is not None:
        payload['output_format'] = normalize_choice_value(output_format, 'xtc', allowed_output_formats)
    if font_file is not None:
        payload['font_file'] = normalize_font_setting_value(font_file, default_font_name) or default_font_name
    return payload



def resolve_preset_combo_index(
    *,
    preset_key: object,
    combo_entries: Sequence[tuple[object, object]],
) -> int:
    normalized_key = str(preset_key or '').strip()
    if not normalized_key:
        return -1

    for index, (_text, item_data) in enumerate(combo_entries):
        if item_data is not None and str(item_data).strip() == normalized_key:
            return index

    if normalized_key.startswith('preset_'):
        suffix = normalized_key.split('_')[-1].strip()
        if suffix.isdigit():
            fallback_text = f'プリセット{int(suffix)}'
            for index, (item_text, _item_data) in enumerate(combo_entries):
                if str(item_text or '').strip() == fallback_text:
                    return index
    return -1


def build_preset_selection_status_message(preset_button_text: object) -> str:
    button_text = str(preset_button_text or '').strip() or 'プリセット'
    return f'{button_text} の詳細表示を更新しました。適用する場合は［プリセット適用］を押してください。'


def build_preset_apply_context(
    *,
    preset_key: object,
    stored_preset: Mapping[str, object],
    fallback_preset: Mapping[str, object] | None,
    fallback_font: str,
    combo_entries: Sequence[tuple[object, object]],
    normalize_preset_payload: Callable[..., dict[str, object]],
    preset_display_name: Callable[[Mapping[str, object]], str],
) -> dict[str, object]:
    normalized_stored_preset = _coerce_mapping_payload(stored_preset)
    normalized_fallback_preset = _coerce_mapping_payload(fallback_preset) if fallback_preset is not None else None
    payload = normalize_preset_payload(
        normalized_stored_preset,
        fallback=normalized_fallback_preset,
        fallback_font=fallback_font,
    )
    display_name = preset_display_name(normalized_stored_preset)
    return {
        'combo_index': resolve_preset_combo_index(
            preset_key=preset_key,
            combo_entries=combo_entries,
        ),
        'payload': payload,
        'preset_display_name': display_name,
        'status_message': build_preset_status_message('apply', display_name),
    }


def build_preset_save_payload(
    *,
    current_preset: Mapping[str, object],
    live_widget_payload: Mapping[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = _coerce_mapping_payload(current_preset)
    payload.update(_coerce_mapping_payload(live_widget_payload))
    return payload



def build_preset_summary_payload(
    *,
    stored_preset: Mapping[str, object],
    pending_payload: Mapping[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = _coerce_mapping_payload(stored_preset)
    payload.update(_coerce_mapping_payload(pending_payload))
    return payload



def build_preset_status_message(action: str, preset_display_name: str) -> str:
    normalized_action = str(action or '').strip().lower()
    display_name = str(preset_display_name or '').strip() or 'プリセット'
    if normalized_action == 'save':
        return f'{display_name} を保存しました'
    if normalized_action == 'apply':
        return f'{display_name} を適用しました。仕様表示はプリセット保存時に更新されます。'
    return display_name


def build_settings_save_raw_payload(
    *,
    current_settings: Mapping[str, object],
    ui_state: Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = _coerce_mapping_payload(current_settings)
    normalized_ui_state = _coerce_mapping_payload(ui_state)
    for key, default in _SAVE_UI_FIELDS:
        payload[key] = normalized_ui_state.get(key, default)
    payload['preview_page_limit'] = normalized_ui_state.get('preview_page_limit', default_preview_page_limit)
    return payload
