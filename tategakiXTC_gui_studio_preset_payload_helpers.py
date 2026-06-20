from __future__ import annotations

"""Preset payload normalization and summary helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._normalize_choice_value`` etc.), so instance-level overrides installed
by tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``.
"""

from copy import deepcopy
from typing import Any

import tategakiXTC_gui_core as core
import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_settings_controller as settings_controller

from tategakiXTC_gui_studio_constants import (
    DEVICE_PROFILES,
    DEFAULT_PRESET_DEFINITIONS,
    DEFAULT_RENDER_SETTINGS,
    PRESET_FIELDS,
    KINSOKU_MODE_LABELS,
    GLYPH_POSITION_MODE_LABELS,
    LATIN_ORIENTATION_MODE_LABELS,
    OPENING_BRACKET_INDENT_MODE_LABELS,
    CLOSING_BRACKET_POSITION_MODE_LABELS,
    OUTPUT_FORMAT_LABELS,
)

PresetDefinition = dict[str, object]
PresetDefinitions = dict[str, PresetDefinition]


def _live_preset_widget_payload(window: Any) -> PresetDefinition:
    profile_widget_present = window.__dict__.get('profile_combo') is not None or 'current_profile_key' in window.__dict__
    dimension_widget_present = window.__dict__.get('width_spin') is not None or window.__dict__.get('height_spin') is not None

    selected_profile = None
    resolved_width = None
    resolved_height = None
    if profile_widget_present or dimension_widget_present:
        selected_profile = window._selected_profile_key()
        _profile_key, _profile, resolved_width, resolved_height = window._resolved_profile_and_dimensions(selected_profile)

    def _widget_value(name: str) -> object:
        widget = window.__dict__.get(name)
        if widget is None or not hasattr(widget, 'value'):
            return None
        try:
            return widget.value()
        except Exception:
            return None

    night_mode = None
    if window.__dict__.get('night_check') is not None:
        try:
            night_mode = bool(window.night_check.isChecked())
        except Exception:
            night_mode = None

    dither = None
    if window.__dict__.get('dither_check') is not None:
        try:
            dither = bool(window.dither_check.isChecked())
        except Exception:
            dither = None

    ruby_hide = None
    if window.__dict__.get('ruby_hide_check') is not None:
        try:
            ruby_hide = bool(window.ruby_hide_check.isChecked())
        except Exception:
            ruby_hide = None

    page_number_enabled = None
    if window.__dict__.get('page_number_check') is not None:
        try:
            page_number_enabled = bool(window.page_number_check.isChecked())
        except Exception:
            page_number_enabled = None

    font_value = window.current_font_value() if window.__dict__.get('font_combo') is not None else None
    return settings_controller.build_live_preset_widget_payload(
        profile=selected_profile,
        width=resolved_width,
        height=resolved_height,
        font_size=_widget_value('font_size_spin'),
        ruby_size=_widget_value('ruby_size_spin'),
        ruby_hide=ruby_hide,
        page_number_enabled=page_number_enabled,
        page_number_font_size=_widget_value('page_number_font_size_spin'),
        progress_bar_enabled=window._safe_widget_checked('progress_bar_check') if window.__dict__.get('progress_bar_check') is not None else None,
        progress_bar_position=window._safe_combo_data('progress_bar_position_combo', 'center') if window.__dict__.get('progress_bar_position_combo') is not None else None,
        line_spacing=_widget_value('line_spacing_spin'),
        margin_t=_widget_value('margin_t_spin'),
        margin_b=_widget_value('margin_b_spin'),
        margin_r=_widget_value('margin_r_spin'),
        margin_l=_widget_value('margin_l_spin'),
        threshold=_widget_value('threshold_spin'),
        night_mode=night_mode,
        dither=dither,
        kinsoku_mode=window.current_kinsoku_mode() if window.__dict__.get('kinsoku_mode_combo') is not None else None,
        tatechuyoko_digit_mode=window.current_tatechuyoko_digit_mode() if window.__dict__.get('tatechuyoko_digit_mode_combo') is not None else None,
        output_format=window.current_output_format() if window.__dict__.get('output_format_combo') is not None else None,
        punctuation_position_mode=window.current_punctuation_position_mode() if window.__dict__.get('punctuation_position_combo') is not None else None,
        ichi_position_mode=window.current_ichi_position_mode() if window.__dict__.get('ichi_position_combo') is not None else None,
        halfwidth_digit_position_mode=window.current_halfwidth_digit_position_mode() if window.__dict__.get('halfwidth_digit_position_combo') is not None else None,
        halfwidth_alpha_position_mode=window.current_halfwidth_alpha_position_mode() if window.__dict__.get('halfwidth_alpha_position_combo') is not None else None,
        latin_orientation_mode=window.current_latin_orientation_mode() if window.__dict__.get('latin_orientation_combo') is not None else None,
        opening_bracket_indent_mode=window.current_opening_bracket_indent_mode() if window.__dict__.get('opening_bracket_indent_combo') is not None else None,
        middle_dot_position_mode=window.current_middle_dot_position_mode() if window.__dict__.get('middle_dot_position_combo') is not None else None,
        tatechuyoko_symbol_position_mode=window.current_tatechuyoko_symbol_position_mode() if window.__dict__.get('tatechuyoko_symbol_position_combo') is not None else None,
        lower_closing_bracket_position_mode=window.current_lower_closing_bracket_position_mode() if window.__dict__.get('lower_closing_bracket_position_combo') is not None else None,
        wave_dash_drawing_mode=window.current_wave_dash_drawing_mode() if window.__dict__.get('wave_dash_drawing_combo') is not None else None,
        wave_dash_position_mode=window.current_wave_dash_position_mode() if window.__dict__.get('wave_dash_position_combo') is not None else None,
        font_file=font_value,
        default_font_name=window._default_font_name(),
        allowed_profiles=DEVICE_PROFILES,
        allowed_kinsoku_modes=KINSOKU_MODE_LABELS,
        allowed_glyph_position_modes=GLYPH_POSITION_MODE_LABELS,
        allowed_output_formats=OUTPUT_FORMAT_LABELS,
        normalize_choice_value=window._normalize_choice_value,
        normalize_font_setting_value=window._normalize_font_setting_value,
    )


def _normalize_preset_payload(
    window: Any,
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
    source = payload if isinstance(payload, dict) else {}
    fallback_payload = fallback if isinstance(fallback, dict) else {}
    normalized = dict(fallback_payload)
    normalized.update(source)

    default_font = window._default_font_name()
    font_fallback = window._normalize_font_setting_value(
        fallback_font or fallback_payload.get('font_file') or default_font,
        default_font,
    ) or default_font

    normalized['profile'] = window._normalize_choice_value(
        source.get('profile', fallback_payload.get('profile', 'x4')),
        'x4',
        DEVICE_PROFILES,
    )
    normalized['font_file'] = window._normalize_font_setting_value(
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
    normalized['ruby_hide'] = worker_logic._bool_config_value(
        source,
        'ruby_hide',
        worker_logic._bool_config_value(fallback_payload, 'ruby_hide', bool(fallback_ruby_hide)),
    )
    normalized['kinsoku_mode'] = window._normalize_choice_value(
        source.get('kinsoku_mode', fallback_payload.get('kinsoku_mode', fallback_kinsoku_mode)),
        'standard',
        KINSOKU_MODE_LABELS,
    )
    normalized['tatechuyoko_digit_mode'] = studio_logic.normalize_tatechuyoko_digit_mode(
        source.get('tatechuyoko_digit_mode', fallback_payload.get('tatechuyoko_digit_mode', fallback_tatechuyoko_digit_mode)),
        '2',
    )
    normalized['output_format'] = window._normalize_choice_value(
        source.get('output_format', fallback_payload.get('output_format', fallback_output_format)),
        'xtc',
        OUTPUT_FORMAT_LABELS,
    )
    normalized['punctuation_position_mode'] = window._normalize_choice_value(
        source.get('punctuation_position_mode', fallback_payload.get('punctuation_position_mode', fallback_punctuation_position_mode)),
        'standard',
        GLYPH_POSITION_MODE_LABELS,
    )
    normalized['ichi_position_mode'] = window._normalize_choice_value(
        source.get('ichi_position_mode', fallback_payload.get('ichi_position_mode', fallback_ichi_position_mode)),
        'standard',
        GLYPH_POSITION_MODE_LABELS,
    )
    normalized['halfwidth_digit_position_mode'] = window._normalize_choice_value(
        source.get('halfwidth_digit_position_mode', fallback_payload.get('halfwidth_digit_position_mode', fallback_halfwidth_digit_position_mode)),
        'standard',
        GLYPH_POSITION_MODE_LABELS,
    )
    normalized['halfwidth_alpha_position_mode'] = window._normalize_choice_value(
        source.get('halfwidth_alpha_position_mode', fallback_payload.get('halfwidth_alpha_position_mode', fallback_halfwidth_alpha_position_mode)),
        'standard',
        GLYPH_POSITION_MODE_LABELS,
    )
    normalized['latin_orientation_mode'] = window._normalize_choice_value(
        source.get('latin_orientation_mode', fallback_payload.get('latin_orientation_mode', fallback_latin_orientation_mode)),
        'vertical',
        LATIN_ORIENTATION_MODE_LABELS,
    )
    normalized['opening_bracket_indent_mode'] = studio_logic.normalize_opening_bracket_indent_mode(
        source.get('opening_bracket_indent_mode', fallback_payload.get('opening_bracket_indent_mode', fallback_opening_bracket_indent_mode)),
        fallback_opening_bracket_indent_mode,
    )
    normalized['middle_dot_position_mode'] = window._normalize_choice_value(
        source.get('middle_dot_position_mode', fallback_payload.get('middle_dot_position_mode', fallback_middle_dot_position_mode)),
        'standard',
        GLYPH_POSITION_MODE_LABELS,
    )
    normalized['tatechuyoko_symbol_position_mode'] = window._normalize_choice_value(
        source.get('tatechuyoko_symbol_position_mode', fallback_payload.get('tatechuyoko_symbol_position_mode', fallback_tatechuyoko_symbol_position_mode)),
        'standard',
        GLYPH_POSITION_MODE_LABELS,
    )
    normalized['lower_closing_bracket_position_mode'] = window._normalize_choice_value(
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
    profile_key, _profile, resolved_width, resolved_height = window._resolved_profile_and_dimensions(
        normalized.get('profile', 'x4'),
        candidate_width,
        candidate_height,
    )
    normalized['profile'] = profile_key
    normalized['width'] = resolved_width
    normalized['height'] = resolved_height

    return normalized


def _default_preset_display_name(window: Any, key: str) -> str:
    default_payload = DEFAULT_PRESET_DEFINITIONS.get(key, {})
    return studio_logic.localized_preset_display_name_text(
        default_payload.get('button_text') or default_payload.get('name') or key or 'プリセット',
        window.current_ui_language_value(),
    )


def _load_preset_definitions(window: Any) -> PresetDefinitions:
    presets = deepcopy(DEFAULT_PRESET_DEFINITIONS)
    stored_font = window._normalize_font_setting_value(
        window._settings_default_value('font_file', window._default_font_name()),
        window._default_font_name(),
    ) or window._default_font_name()
    stored_night = worker_logic._bool_config_value({'night_mode': window._settings_default_value('night_mode', False)}, 'night_mode', False)
    stored_dither = worker_logic._bool_config_value({'dither': window._settings_default_value('dither', False)}, 'dither', False)
    stored_ruby_hide = worker_logic._bool_config_value({'ruby_hide': window._settings_default_value('ruby_hide', False)}, 'ruby_hide', False)
    stored_kinsoku_mode = window._normalize_choice_value(
        worker_logic._str_config_value({'kinsoku_mode': window._settings_default_value('kinsoku_mode', 'standard')}, 'kinsoku_mode', 'standard'),
        'standard',
        KINSOKU_MODE_LABELS,
    )
    stored_output_format = window._normalize_choice_value(
        worker_logic._str_config_value({'output_format': window._settings_default_value('output_format', 'xtch')}, 'output_format', 'xtch'),
        'xtch',
        OUTPUT_FORMAT_LABELS,
    )
    for key in list(presets):
        preset = presets[key]
        prefix = window._preset_settings_prefix(key)
        for field in PRESET_FIELDS:
            sk = f'{prefix}/{field}'
            if window._settings_contains_key(sk):
                dv = preset.get(field)
                preset[field] = window._settings_raw_value(sk, dv)
        display_name_key = window._preset_display_name_settings_key(key)
        if window._settings_contains_key(display_name_key):
            default_display_name = window._default_preset_display_name(key)
            display_name = window._normalize_preset_display_name(
                window._settings_raw_value(display_name_key, default_display_name),
                fallback=default_display_name,
            )
            preset['button_text'] = display_name
            preset['name'] = display_name
        presets[key] = window._normalize_preset_payload(
            preset,
            fallback=DEFAULT_PRESET_DEFINITIONS.get(key),
            fallback_font=stored_font,
            fallback_night_mode=bool(stored_night),
            fallback_dither=bool(stored_dither),
            fallback_ruby_hide=bool(stored_ruby_hide),
            fallback_kinsoku_mode=stored_kinsoku_mode,
            fallback_wave_dash_drawing_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_drawing_mode', 'rotate')),
            fallback_wave_dash_position_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_position_mode', 'standard')),
            fallback_output_format=stored_output_format,
        )
    return presets


def _preset_display_name(window: Any, p: PresetDefinition) -> str:
    return studio_logic.build_preset_display_name(p, window.current_ui_language_value())


def _preset_summary_plain_text(
    window: Any,
    p: PresetDefinition,
    *,
    summary_tag: str = '',
    include_name_line: bool = True,
) -> str:
    font_text = core.describe_font_value(p.get('font_file') or window._default_font_name())
    return studio_logic.build_preset_summary_text(
        p,
        font_text=font_text,
        device_profile_keys=DEVICE_PROFILES.keys(),
        kinsoku_mode_labels=KINSOKU_MODE_LABELS,
        output_format_labels=OUTPUT_FORMAT_LABELS,
        summary_tag=summary_tag,
        include_name_line=include_name_line,
        language=window.current_ui_language_value(),
    )


def _preset_summary_text(
    window: Any,
    p: PresetDefinition,
    *,
    summary_tag: str = '',
    include_name_line: bool = True,
) -> str:
    font_text = core.describe_font_value(p.get('font_file') or window._default_font_name())
    return studio_logic.build_preset_summary_html(
        p,
        font_text=font_text,
        device_profile_keys=DEVICE_PROFILES.keys(),
        kinsoku_mode_labels=KINSOKU_MODE_LABELS,
        output_format_labels=OUTPUT_FORMAT_LABELS,
        summary_tag=summary_tag,
        include_name_line=include_name_line,
        language=window.current_ui_language_value(),
    )


def _current_settings_summary_payload(window: Any, key: str | None = None) -> PresetDefinition:
    selected_key = key or window.selected_preset_key()
    base_preset = dict(window.preset_definitions.get(selected_key) or {}) if selected_key else {}
    current_payload = dict(window.current_preset_payload())
    if base_preset:
        merged = dict(base_preset)
        merged.update(current_payload)
        return merged
    return current_payload
