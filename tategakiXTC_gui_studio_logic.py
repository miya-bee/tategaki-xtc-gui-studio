from __future__ import annotations

"""Pure helpers for the GUI layer.

This module keeps presentation and small orchestration decisions out of
MainWindow so they can be tested without a live Qt runtime.
"""

import html
import ntpath
import os
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
import math
from typing import Any


LOWER_CLOSING_BRACKET_POSITION_MODES: dict[str, str] = {
    'standard': '標準',
    'up_weak': '上補正 弱',
    'up_strong': '上補正 強',
}


def build_top_status_message(target_raw: str, profile_name: str, font_size: int, line_spacing: int) -> str:
    target = str(target_raw).strip()
    if not target:
        return '変換対象を選択してください。'
    # ステータス表示はファイル指定直後にも呼ばれるため、Path.is_dir()
    # などの実ファイルシステム確認を行わない。EPUB/ネットワークパスや
    # 大容量フォルダ指定時に、表示更新だけで UI が詰まることを避ける。
    path = Path(target)
    suffix = path.suffix.lower()
    file_like_suffixes = {
        '.epub', '.zip', '.rar', '.cbz', '.cbr',
        '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
        '.xtc', '.xtch',
    }
    kind = 'ファイル' if suffix in file_like_suffixes else 'フォルダ'
    return f'{kind}: {path.name}  |  {profile_name} / 本文{font_size} / 行間{line_spacing}'


def should_prompt_for_output_name(supported_target_count: int, is_file_target: bool) -> bool:
    return is_file_target and supported_target_count == 1


def suggest_output_name(last_output_name: str, default_output_name: str) -> str:
    current = str(last_output_name).strip()
    if current:
        return current
    fallback = str(default_output_name).strip()
    return fallback or 'output'


def suggest_output_name_for_target(
    last_output_name: str,
    default_output_name: str,
    *,
    target_path: object = '',
    last_output_source: object = '',
) -> str:
    """Return the prompt default for a single-file conversion target.

    Older builds reused ``last_output_name`` unconditionally.  That made a
    previous EPUB conversion name appear again when the user converted a
    different TXT file.  Reuse the saved name only when it belongs to the
    same source target; otherwise prefer the current file-derived default.
    """
    fallback = str(default_output_name).strip() or 'output'
    current = str(last_output_name).strip()
    if not current:
        return fallback
    target_key = _normalize_path_identity(target_path)
    source_key = _normalize_path_identity(last_output_source)
    if target_key and source_key and target_key == source_key:
        return current
    return fallback


def _normalize_path_identity(value: object) -> str:
    text = str(value or '').strip().strip("\"'")
    if not text:
        return ''
    try:
        return str(Path(text).expanduser().resolve(strict=False)).casefold()
    except Exception:
        return text.replace('\\', '/').casefold()


def build_running_results_summary() -> str:
    return '変換中です。完了後に保存件数とエラー件数を表示します。'


def build_start_log_message(output_format: str, target_count: int) -> str:
    fmt = str(output_format).strip().lower() or 'xtc'
    if target_count <= 1:
        return f'変換を開始しました。({fmt})'
    return f'変換を開始しました。({fmt}, {target_count}件)'



def _config_bool_value(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off', ''}:
        return False
    return default


def _config_int_value(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_mapping_payload(payload: object) -> dict[str, object]:
    return dict(payload) if isinstance(payload, Mapping) else {}



def normalize_choice_value(value: object, default: str, allowed_values: Collection[str] | Mapping[str, object]) -> str:
    normalized = str(value if value not in (None, '') else default).strip().lower()
    compact = normalized.replace(' ', '').replace('　', '').replace('-', '_')
    allowed = {str(item).strip().lower() for item in allowed_values}
    allowed_compact = {item.replace(' ', '').replace('　', '').replace('-', '_'): item for item in allowed}
    if normalized in allowed:
        return normalized
    if compact in allowed_compact:
        return allowed_compact[compact]
    glyph_aliases = {
        'down_strong': {
            'down_strong', 'strong_down', 'plus', 'positive', 'adjusted', 'mode2', '+',
            'プラス', 'プラス補正', '下', '下補正', '下補正強', '下強', '強下', '補正',
        },
        'down_weak': {'down_weak', 'weak_down', '下補正弱', '下弱', '弱下'},
        'up_weak': {'up_weak', 'weak_up', '上補正弱', '上弱', '弱上'},
        'up_strong': {
            'up_strong', 'strong_up', 'minus', 'negative', '-',
            'マイナス', 'マイナス補正', '上', '上補正', '上補正強', '上強', '強上',
        },
    }
    for canonical, aliases in glyph_aliases.items():
        if compact in aliases:
            if canonical in allowed:
                return canonical
            if canonical == 'down_strong' and 'plus' in allowed:
                return 'plus'
            if canonical == 'up_strong' and 'minus' in allowed:
                return 'minus'
    return normalized if normalized in allowed else str(default).strip().lower()


def payload_optional_int_value(payload: Mapping[str, object], key: str) -> int | None:
    if key not in payload:
        return None
    raw = payload.get(key)
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, float):
        return int(raw) if math.isfinite(raw) else None
    if isinstance(raw, (bytes, bytearray)):
        raw = bytes(raw)
        if not raw.strip():
            return None
        try:
            raw = raw.decode('utf-8')
        except Exception:
            return None
    if isinstance(raw, str):
        normalized = raw.strip()
        if not normalized:
            return None
        try:
            return int(normalized, 10)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = float(normalized)
            except (TypeError, ValueError, OverflowError):
                return None
            return int(parsed) if math.isfinite(parsed) else None
    return None


def payload_splitter_sizes_value(
    payload: Mapping[str, object],
    key: str,
    default: Sequence[int],
    *,
    min_top: int = 280,
    min_bottom: int = 92,
) -> list[int]:
    fallback = list(default[:2])
    if len(fallback) < 2:
        fallback = [min_top, min_bottom]
    raw = payload.get(key)
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return fallback
    raw_list = list(raw)
    if len(raw_list) < 2:
        return fallback
    top = payload_optional_int_value({'value': raw_list[0]}, 'value')
    bottom = payload_optional_int_value({'value': raw_list[1]}, 'value')
    return [
        max(min_top, fallback[0] if top is None else top),
        max(min_bottom, fallback[1] if bottom is None else bottom),
    ]


def build_window_state_restore_payload(
    raw_payload: Mapping[str, object],
    *,
    default_width: int,
    default_height: int,
    default_left_panel_width: int,
    default_left_splitter_sizes: Sequence[int],
) -> dict[str, object]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    window_width = payload_optional_int_value(raw_payload, 'window_width')
    window_height = payload_optional_int_value(raw_payload, 'window_height')
    left_panel_width = payload_optional_int_value(raw_payload, 'left_panel_width')
    return {
        'geometry': raw_payload.get('geometry'),
        'window_width': max(1100, default_width if window_width is None else window_width),
        'window_height': max(760, default_height if window_height is None else window_height),
        'is_maximized': _config_bool_value(raw_payload.get('is_maximized'), False),
        'left_panel_width': max(0, default_left_panel_width if left_panel_width is None else left_panel_width),
        'left_splitter_state': raw_payload.get('left_splitter_state'),
        'left_splitter_sizes': payload_splitter_sizes_value(raw_payload, 'left_splitter_sizes', default_left_splitter_sizes),
        'left_panel_visible': _config_bool_value(raw_payload.get('left_panel_visible'), True),
    }

def build_window_state_save_payload(
    raw_payload: Mapping[str, object],
    *,
    min_width: int = 1100,
    min_height: int = 760,
) -> dict[str, object]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    payload: dict[str, object] = {
        'window_width': max(min_width, _config_int_value(raw_payload.get('window_width'), min_width)),
        'window_height': max(min_height, _config_int_value(raw_payload.get('window_height'), min_height)),
        'is_maximized': _config_bool_value(raw_payload.get('is_maximized'), False),
        'left_splitter_state': raw_payload.get('left_splitter_state'),
        'left_panel_visible': _config_bool_value(raw_payload.get('left_panel_visible'), True),
    }
    geometry = raw_payload.get('geometry')
    if geometry is not None:
        payload['geometry'] = geometry
    left_panel_width = payload_optional_int_value(raw_payload, 'left_panel_width')
    if left_panel_width is not None and left_panel_width > 0:
        payload['left_panel_width'] = left_panel_width
    top = payload_optional_int_value(raw_payload, 'left_splitter_top')
    bottom = payload_optional_int_value(raw_payload, 'left_splitter_bottom')
    if top is not None and bottom is not None:
        payload['left_splitter_top'] = top
        payload['left_splitter_bottom'] = bottom
    return payload




def build_settings_restore_payload(
    raw_payload: Mapping[str, object],
    *,
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_profiles: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_glyph_position_modes: Collection[str] | Mapping[str, object] | None = None,
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    if allowed_glyph_position_modes is None:
        allowed_glyph_position_modes = {'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'}
    allowed_lower_closing_bracket_position_modes = LOWER_CLOSING_BRACKET_POSITION_MODES
    payload: dict[str, Any] = {}
    payload['profile'] = normalize_choice_value(raw_payload.get('profile'), 'x4', allowed_profiles)
    for key, default in (
        ('actual_size', False),
        ('show_guides', True),
        ('nav_buttons_reversed', False),
        ('dither', False),
        ('night_mode', False),
        ('open_folder', True),
    ):
        payload[key] = _config_bool_value(raw_payload.get(key), default)
    for key, default in (
        ('calibration_pct', 100),
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
        ('bottom_tab_index', 0),
    ):
        payload[key] = _config_int_value(raw_payload.get(key), default)
    payload['preview_page_limit'] = max(1, _config_int_value(raw_payload.get('preview_page_limit'), default_preview_page_limit))
    payload['output_conflict'] = normalize_choice_value(
        raw_payload.get('output_conflict'),
        'rename',
        allowed_output_conflicts,
    )
    payload['output_format'] = normalize_choice_value(
        raw_payload.get('output_format'),
        'xtc',
        allowed_output_formats,
    )
    payload['kinsoku_mode'] = normalize_choice_value(
        raw_payload.get('kinsoku_mode'),
        'standard',
        allowed_kinsoku_modes,
    )
    payload['punctuation_position_mode'] = normalize_choice_value(
        raw_payload.get('punctuation_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['ichi_position_mode'] = normalize_choice_value(
        raw_payload.get('ichi_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['lower_closing_bracket_position_mode'] = normalize_choice_value(
        raw_payload.get('lower_closing_bracket_position_mode'),
        'standard',
        allowed_lower_closing_bracket_position_modes,
    )
    payload['target'] = str(raw_payload.get('target') or '').strip()
    payload['font_file'] = str(raw_payload.get('font_file') or '').strip()
    payload['main_view_mode'] = normalize_choice_value(
        raw_payload.get('main_view_mode'),
        'font',
        allowed_view_modes,
    )
    return payload



def build_startup_preview_defaults_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Return startup-only preview defaults for restored UI state.

    Saved actual-size/device-view settings are still persisted, but startup uses
    the normal font preview so the zoom controls near the preview remain
    immediately usable and less confusing.
    """
    normalized = dict(payload or {})
    normalized['main_view_mode'] = 'font'
    normalized['actual_size'] = False
    return normalized


def build_settings_ui_apply_payload(
    raw_payload: Mapping[str, object],
    *,
    defaults: Mapping[str, object],
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_glyph_position_modes: Collection[str] | Mapping[str, object] | None = None,
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    bottom_tab_count: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    if allowed_glyph_position_modes is None:
        allowed_glyph_position_modes = {'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'}
    allowed_lower_closing_bracket_position_modes = LOWER_CLOSING_BRACKET_POSITION_MODES
    defaults = _coerce_mapping_payload(defaults)
    plan: dict[str, Any] = {}

    for key in ('profile', 'width', 'height'):
        if key in raw_payload:
            plan[key] = raw_payload.get(key)

    for key in ('target', 'font_file'):
        if key in raw_payload:
            plan[key] = str(raw_payload.get(key) or '').strip()

    for key, fallback_key in (
        ('actual_size', 'actual_size'),
        ('show_guides', 'show_guides'),
        ('nav_buttons_reversed', 'nav_buttons_reversed'),
        ('dither', 'dither'),
        ('night_mode', 'night_mode'),
        ('open_folder', 'open_folder'),
    ):
        if key in raw_payload:
            plan[key] = _config_bool_value(raw_payload.get(key), _config_bool_value(defaults.get(fallback_key), False))

    for key, fallback_key in (
        ('calibration_pct', 'calibration_pct'),
        ('font_size', 'font_size'),
        ('ruby_size', 'ruby_size'),
        ('line_spacing', 'line_spacing'),
        ('margin_t', 'margin_t'),
        ('margin_b', 'margin_b'),
        ('margin_r', 'margin_r'),
        ('margin_l', 'margin_l'),
        ('threshold', 'threshold'),
        ('preview_page_limit', 'preview_page_limit'),
    ):
        if key in raw_payload:
            default_value = _config_int_value(defaults.get(fallback_key), 0)
            normalized = _config_int_value(raw_payload.get(key), default_value)
            if key == 'preview_page_limit':
                normalized = max(1, normalized)
            plan[key] = normalized

    if 'output_conflict' in raw_payload:
        plan['output_conflict'] = normalize_choice_value(
            raw_payload.get('output_conflict'),
            str(defaults.get('output_conflict') or 'rename'),
            allowed_output_conflicts,
        )
    if 'output_format' in raw_payload:
        plan['output_format'] = normalize_choice_value(
            raw_payload.get('output_format'),
            str(defaults.get('output_format') or 'xtc'),
            allowed_output_formats,
        )
    if 'kinsoku_mode' in raw_payload:
        plan['kinsoku_mode'] = normalize_choice_value(
            raw_payload.get('kinsoku_mode'),
            str(defaults.get('kinsoku_mode') or 'standard'),
            allowed_kinsoku_modes,
        )
    for glyph_key in ('punctuation_position_mode', 'ichi_position_mode'):
        if glyph_key in raw_payload:
            plan[glyph_key] = normalize_choice_value(
                raw_payload.get(glyph_key),
                str(defaults.get(glyph_key) or 'standard'),
                allowed_glyph_position_modes,
            )
    if 'lower_closing_bracket_position_mode' in raw_payload:
        plan['lower_closing_bracket_position_mode'] = normalize_choice_value(
            raw_payload.get('lower_closing_bracket_position_mode'),
            str(defaults.get('lower_closing_bracket_position_mode') or 'standard'),
            allowed_lower_closing_bracket_position_modes,
        )
    if 'main_view_mode' in raw_payload:
        plan['main_view_mode'] = normalize_choice_value(
            raw_payload.get('main_view_mode'),
            str(defaults.get('main_view_mode') or 'font'),
            allowed_view_modes,
        )

    if 'bottom_tab_index' in raw_payload:
        bottom_tab_index = payload_optional_int_value(raw_payload, 'bottom_tab_index')
        if bottom_tab_index is not None and 0 <= bottom_tab_index < max(0, int(bottom_tab_count)):
            plan['bottom_tab_index'] = bottom_tab_index

    return plan


def build_settings_save_payload(
    raw_payload: Mapping[str, object],
    *,
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_profiles: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_glyph_position_modes: Collection[str] | Mapping[str, object] | None = None,
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    if allowed_glyph_position_modes is None:
        allowed_glyph_position_modes = {'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'}
    allowed_lower_closing_bracket_position_modes = LOWER_CLOSING_BRACKET_POSITION_MODES
    payload: dict[str, Any] = dict(raw_payload)
    payload['bottom_tab_index'] = max(0, _config_int_value(raw_payload.get('bottom_tab_index'), 0))
    payload['main_view_mode'] = normalize_choice_value(
        raw_payload.get('main_view_mode'),
        'font',
        allowed_view_modes,
    )
    ui_theme = str(raw_payload.get('ui_theme') or '').strip()
    payload['ui_theme'] = ui_theme or 'light'
    payload['panel_button_visible'] = _config_bool_value(raw_payload.get('panel_button_visible'), True)
    payload['preset_index'] = max(-1, _config_int_value(raw_payload.get('preset_index'), -1))
    payload['preset_key'] = str(raw_payload.get('preset_key') or '').strip()
    payload['profile'] = normalize_choice_value(raw_payload.get('profile'), 'x4', allowed_profiles)
    payload['actual_size'] = _config_bool_value(raw_payload.get('actual_size'), False)
    payload['show_guides'] = _config_bool_value(raw_payload.get('show_guides'), True)
    payload['calibration_pct'] = _config_int_value(raw_payload.get('calibration_pct'), 100)
    payload['nav_buttons_reversed'] = _config_bool_value(raw_payload.get('nav_buttons_reversed'), False)
    payload['preview_page_limit'] = max(1, _config_int_value(raw_payload.get('preview_page_limit'), default_preview_page_limit))
    payload['target'] = str(raw_payload.get('target') or '').strip()
    payload['font_file'] = str(raw_payload.get('font_file') or '').strip()
    for key, default in (
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
    ):
        payload[key] = _config_int_value(raw_payload.get(key), default)
    for key, default in (
        ('dither', False),
        ('night_mode', False),
        ('open_folder', False),
    ):
        payload[key] = _config_bool_value(raw_payload.get(key), default)
    payload['kinsoku_mode'] = normalize_choice_value(
        raw_payload.get('kinsoku_mode'),
        'standard',
        allowed_kinsoku_modes,
    )
    payload['output_format'] = normalize_choice_value(
        raw_payload.get('output_format'),
        'xtc',
        allowed_output_formats,
    )
    payload['punctuation_position_mode'] = normalize_choice_value(
        raw_payload.get('punctuation_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['ichi_position_mode'] = normalize_choice_value(
        raw_payload.get('ichi_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['lower_closing_bracket_position_mode'] = normalize_choice_value(
        raw_payload.get('lower_closing_bracket_position_mode'),
        'standard',
        allowed_lower_closing_bracket_position_modes,
    )
    payload['output_conflict'] = normalize_choice_value(
        raw_payload.get('output_conflict'),
        'rename',
        allowed_output_conflicts,
    )
    return payload


def build_displaying_document_label(display_name: object = None, fallback: str = 'なし') -> str:
    text = str(display_name if display_name is not None else fallback).strip()
    if not text:
        text = str(fallback).strip() or 'なし'
    return f'表示中: {text}'



def display_context_name_from_label_text(text: object) -> str:
    normalized = _coerce_message_text(text).strip()
    prefix = '表示中:'
    if normalized.startswith(prefix):
        normalized = normalized[len(prefix):].strip()
    return normalized


def is_preview_render_failure_status_text(text: object) -> bool:
    normalized = _coerce_message_text(text).strip()
    return (
        normalized.startswith('プレビュー表示エラー')
        or normalized.startswith('プレビュー生成エラー')
    )


def is_device_render_failure_status_text(text: object) -> bool:
    normalized = _coerce_message_text(text).strip()
    return normalized.startswith('ページ表示エラー')


def is_render_failure_status_text(text: object) -> bool:
    return (
        is_device_render_failure_status_text(text)
        or is_preview_render_failure_status_text(text)
    )


def render_failure_preserved_display_name(text: object) -> str:
    normalized = _coerce_message_text(text).strip()
    marker = '（表示は '
    suffix = ' のまま）'
    start = normalized.find(marker)
    if start < 0:
        return ''
    start += len(marker)
    end = normalized.find(suffix, start)
    if end < 0:
        return ''
    return normalized[start:end].strip()


def render_failure_matches_display_context(status_text: object, visible_display_name: object) -> bool:
    preserved_display_name = render_failure_preserved_display_name(status_text)
    visible_name = _coerce_message_text(visible_display_name).strip()
    if visible_name and preserved_display_name:
        return preserved_display_name == visible_name
    return True


def build_preview_status_message(
    state: str,
    *,
    preview_limit: int = 0,
    generated_pages: int = 0,
    truncated: bool = False,
    error: object = None,
) -> str:
    normalized = str(state or '').strip().lower()
    if normalized == 'dirty':
        return '設定変更あり（未反映）'
    if normalized == 'running':
        return f'先頭 {max(0, _config_int_value(preview_limit, 0))} ページまでプレビューを更新しています…'
    if normalized == 'empty':
        return 'プレビューを生成できませんでした'
    if normalized == 'error':
        detail = str(error or '').strip()
        return f'プレビュー生成エラー: {detail}' if detail else 'プレビュー生成エラー'
    if normalized == 'complete':
        pages = max(0, _config_int_value(generated_pages, 0))
        limit = max(0, _config_int_value(preview_limit, 0))
        if truncated:
            return f'先頭 {pages} / 上限 {limit} ページを生成しました。'
        return f'プレビュー更新完了（{pages} / 上限 {limit} ページ）'
    return str(state or '').strip()


def build_preview_progress_message(
    current: object,
    total: object,
    message: object,
    *,
    preview_limit: int = 0,
) -> str:
    detail = str(message or '').strip()
    current_value = max(0, _config_int_value(current, 0))
    total_value = max(0, _config_int_value(total, 0))
    if detail:
        if total_value > 0 and '/' not in detail:
            return f'{detail} ({current_value}/{total_value})'
        return detail
    if total_value > 0:
        return f'プレビューを更新しています… ({current_value}/{total_value})'
    return build_preview_status_message('running', preview_limit=preview_limit)


def build_preview_success_status_state(
    *,
    page_count: object,
    requested_limit: object,
    truncated: object = False,
) -> dict[str, Any]:
    """Return the normalized status payload for a completed preview render."""
    generated_pages = max(0, _config_int_value(page_count, 0))
    preview_limit = max(generated_pages, _config_int_value(requested_limit, 0))
    is_truncated = bool(truncated)
    return {
        'generated_pages': generated_pages,
        'preview_limit': preview_limit,
        'truncated': is_truncated,
        'status_message': build_preview_status_message(
            'complete',
            preview_limit=preview_limit,
            generated_pages=generated_pages,
            truncated=is_truncated,
        ),
    }


def build_preview_render_status_message(
    *,
    page_count: object,
    requested_limit: object,
    truncated: object = False,
    running: object = False,
    dirty: object = False,
    widget_limit: object = 0,
) -> str:
    """Return the preview status message visible for the current render state."""
    success_state = build_preview_success_status_state(
        page_count=page_count,
        requested_limit=requested_limit,
        truncated=truncated,
    )
    preview_limit = _config_int_value(success_state.get('preview_limit'), 0)
    if preview_limit <= 0:
        fallback_limit = _config_int_value(widget_limit, 0)
        if fallback_limit > 0:
            preview_limit = max(1, fallback_limit)
    if bool(running):
        return build_preview_status_message('running', preview_limit=max(1, preview_limit or 1))
    if bool(dirty):
        return build_preview_status_message('dirty')
    return str(success_state.get('status_message', ''))


def build_successful_preview_render_status_refresh_state(
    *,
    preview_replacement: object,
    view_mode: object,
    visible_font_preview_active: object = False,
    preview_status_text: object = '',
    progress_status_text: object = '',
    status_bar_text: object = '',
    current_label_text: object = '',
) -> dict[str, Any]:
    """Return which shared status surfaces should be refreshed after success."""
    replacement = _coerce_message_text(preview_replacement).strip()
    normalized_mode = normalize_choice_value(view_mode, 'font', {'font', 'device'})
    font_view_visible = normalized_mode == 'font'
    device_view_visible = normalized_mode == 'device'
    preview_status = _coerce_message_text(preview_status_text).strip()
    progress_status = _coerce_message_text(progress_status_text).strip()
    status_bar_status = _coerce_message_text(status_bar_text).strip()
    visible_font_preview = bool(visible_font_preview_active)

    stale_preview_status = (
        is_render_failure_status_text(preview_status)
        or preview_status == 'プレビューを生成できませんでした'
    )

    progress_replacement = replacement
    if device_view_visible:
        label_text = _coerce_message_text(current_label_text).strip()
        progress_replacement = label_text or replacement

    stale_progress_status = is_preview_render_failure_status_text(progress_status)
    if not stale_progress_status and visible_font_preview:
        stale_progress_status = is_device_render_failure_status_text(progress_status)

    stale_status_bar = is_preview_render_failure_status_text(status_bar_status)
    if not stale_status_bar and visible_font_preview:
        stale_status_bar = is_device_render_failure_status_text(status_bar_status)

    should_notify_status_bar = (
        stale_progress_status
        or stale_status_bar
        or (stale_preview_status and font_view_visible)
    )

    return {
        'preview_replacement': replacement,
        'progress_replacement': progress_replacement,
        'font_view_visible': font_view_visible,
        'device_view_visible': device_view_visible,
        'stale_preview_status': stale_preview_status,
        'stale_progress_status': stale_progress_status,
        'stale_status_bar': stale_status_bar,
        'should_notify_status_bar': should_notify_status_bar,
    }

def build_successful_device_render_status_refresh_state(
    *,
    view_mode: object,
    current_label_text: object = '',
    preview_replacement: object = '',
    has_font_preview_pages: object = False,
    progress_status_text: object = '',
    status_bar_text: object = '',
) -> dict[str, Any]:
    """Return shared status refresh decisions after a device page render succeeds."""
    normalized_mode = normalize_choice_value(view_mode, 'font', {'font', 'device'})
    device_view_visible = normalized_mode == 'device'
    font_view_visible = normalized_mode == 'font'
    font_preview_visible = font_view_visible and bool(has_font_preview_pages)

    if device_view_visible:
        replacement = _coerce_message_text(current_label_text).strip()
    elif font_preview_visible:
        replacement = _coerce_message_text(preview_replacement).strip()
    else:
        replacement = ''

    progress_status = _coerce_message_text(progress_status_text).strip()
    status_bar_status = _coerce_message_text(status_bar_text).strip()
    if device_view_visible:
        stale_progress_status = is_render_failure_status_text(progress_status)
        stale_status_bar = is_render_failure_status_text(status_bar_status)
    else:
        stale_progress_status = is_device_render_failure_status_text(progress_status)
        stale_status_bar = is_device_render_failure_status_text(status_bar_status)

    should_notify_status_bar = stale_progress_status or stale_status_bar
    return {
        'replacement': replacement,
        'font_view_visible': font_view_visible,
        'device_view_visible': device_view_visible,
        'font_preview_visible': font_preview_visible,
        'stale_progress_status': stale_progress_status,
        'stale_status_bar': stale_status_bar,
        'should_notify_status_bar': should_notify_status_bar,
    }


def build_preview_button_state(
    context: Mapping[str, object] | None,
    *,
    default_text: str = 'プレビュー更新',
) -> dict[str, Any]:
    """Return normalized button state for preview refresh controls."""
    payload = _coerce_mapping_payload(context)
    return {
        'button_enabled': _config_bool_value(payload.get('button_enabled'), True),
        'button_text': str(payload.get('button_text', default_text)),
    }


def build_preview_progress_context_state(
    context: Mapping[str, object] | None,
) -> dict[str, str]:
    """Return normalized preview-progress status text from a worker context."""
    payload = _coerce_mapping_payload(context)
    return {
        'status_message': str(payload.get('status_message', '')),
    }


def _coerce_message_text(value: object, default: str = '') -> str:
    if value is None:
        text = ''
    else:
        if isinstance(value, os.PathLike):
            try:
                value = os.fspath(value)
            except Exception:
                pass
        if isinstance(value, (bytes, bytearray)):
            try:
                text = os.fsdecode(bytes(value))
            except Exception:
                text = str(value)
        else:
            text = str(value)
    return text if text.strip() else default


def _progress_number_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else int(default)
    if isinstance(value, os.PathLike):
        try:
            value = os.fspath(value)
        except Exception:
            return int(default)
    if isinstance(value, (bytes, bytearray)):
        try:
            value = os.fsdecode(bytes(value))
        except Exception:
            return int(default)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return int(default)
        try:
            return int(normalized, 10)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = float(normalized)
            except (TypeError, ValueError, OverflowError):
                return int(default)
            return int(parsed) if math.isfinite(parsed) else int(default)
    return int(default)



def merge_unique_message_values(existing_messages: Sequence[object], new_messages: Sequence[object]) -> list[str]:
    merged: list[str] = []
    for raw_message in [*existing_messages, *new_messages]:
        message = _coerce_message_text(raw_message).strip()
        if message and message not in merged:
            merged.append(message)
    return merged


def build_progress_status_text(current: object, total: object, message: object) -> str:
    total_value = max(1, _progress_number_value(total, 1))
    current_value = max(0, min(_progress_number_value(current, 0), total_value))
    detail = _coerce_message_text(message).strip()
    base = detail or '変換中…'
    percent = int(round((current_value / total_value) * 100.0)) if total_value > 0 else 0
    return f'{base} ({current_value}/{total_value}, {percent}%)'


def build_conversion_failure_summary_text(prefix: object, message: object) -> str:
    prefix_text = _coerce_message_text(prefix).strip()
    message_text = _coerce_message_text(message, '不明なエラー').strip() or '不明なエラー'
    if not prefix_text:
        return message_text
    return f'{prefix_text}: {message_text}'





def build_render_failure_status_message(title: object, detail: object = '', preserved_display_name: object = '') -> str:
    title_text = _coerce_message_text(title).strip() or '表示エラー'
    detail_text = _coerce_message_text(detail).strip()
    if detail_text == 'Non-base64 digit found':
        detail_text = 'Only base64 data is allowed'
    preserved_text = _coerce_message_text(preserved_display_name).strip()
    message = title_text
    if preserved_text:
        message += f'（表示は {preserved_text} のまま）'
    if detail_text:
        message += f': {detail_text}'
    return message

def build_xtc_load_failure_status_message(target: object, detail: object = '', preserved_display_name: object = '') -> str:
    target_text = _coerce_message_text(target).strip() or '指定ファイル'
    detail_text = _coerce_message_text(detail).strip()
    if detail_text == 'Non-base64 digit found':
        detail_text = 'Only base64 data is allowed'
    preserved_text = _coerce_message_text(preserved_display_name).strip()
    message = f'XTC/XTCH読込失敗: {target_text}'
    if preserved_text:
        message += f'（表示は {preserved_text} のまま）'
    if detail_text:
        message += f' / {detail_text}'
    return message


def build_xtc_load_failure_preserved_display_name(
    *,
    preview_active: object = False,
    remembered_display_name: object = '',
    remembered_path_display_name: object = '',
    current_label_text: object = '',
) -> str:
    if bool(preview_active):
        return 'プレビュー'

    remembered = _coerce_message_text(remembered_display_name).strip()
    if remembered and remembered != 'なし':
        return remembered

    remembered_path = _coerce_message_text(remembered_path_display_name).strip()
    if remembered_path and remembered_path != 'なし':
        return remembered_path

    normalized_label = display_context_name_from_label_text(current_label_text).strip()
    if normalized_label and normalized_label != 'なし':
        return normalized_label
    return ''


def normalize_xtc_bytes(data: object) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    raise TypeError('XTCデータは bytes 系である必要があります。')


def build_xtc_document_payload_from_pages(data: object, pages: Sequence[object]) -> dict[str, object]:
    page_list = list(pages)
    if not page_list:
        raise RuntimeError('XTC内にページがありません。')
    return {
        'data': data,
        'pages': page_list,
        'total': len(page_list),
        'current_index': 0,
        'current_page': 1,
    }


def build_xtc_page_state_payload(pages: Sequence[object], current_index: object = 0) -> dict[str, object]:
    page_list = list(pages)
    total = len(page_list)
    normalized_index = _config_int_value(current_index, 0)
    if total > 0:
        normalized_index = max(0, min(total - 1, normalized_index))
        page = page_list[normalized_index]
    else:
        normalized_index = 0
        page = None
    return {
        'total': total,
        'current_index': normalized_index,
        'current_page': normalized_index + 1 if total > 0 else 0,
        'page': page,
    }


def build_preview_refresh_state(
    *,
    page_count: object,
    reset_page: bool,
    current_preview_index: object,
    current_device_index: object,
    preview_limit: int,
    truncated: bool,
) -> dict[str, Any]:
    total_pages = max(0, _config_int_value(page_count, 0))
    if total_pages <= 0:
        return {
            'has_pages': False,
            'preview_index': 0,
            'device_index': 0,
            'generated_pages': 0,
            'status_message': build_preview_status_message('empty'),
        }
    if reset_page:
        preview_index = 0
        device_index = 0
    else:
        preview_index = max(0, min(total_pages - 1, _config_int_value(current_preview_index, 0)))
        device_index = max(0, min(total_pages - 1, _config_int_value(current_device_index, 0)))
    return {
        'has_pages': True,
        'preview_index': preview_index,
        'device_index': device_index,
        'generated_pages': total_pages,
        'status_message': build_preview_status_message(
            'complete',
            generated_pages=total_pages,
            preview_limit=preview_limit,
            truncated=truncated,
        ),
    }


def build_preview_error_state(*, device_view_source: object, error: object) -> dict[str, Any]:
    normalized_source = str(device_view_source or 'preview').strip().lower()
    clear_device_page = normalized_source != 'xtc'
    return {
        'preview_index': 0,
        'device_index': 0,
        'clear_device_page': clear_device_page,
        'status_message': build_preview_status_message('error', error=error),
    }


def _clamp_navigation_index(total: int, current_index: int) -> tuple[int, int]:
    total_pages = max(0, _config_int_value(total, 0))
    index = _config_int_value(current_index, 0)
    if total_pages > 0:
        index = max(0, min(total_pages - 1, index))
    else:
        index = 0
    return total_pages, index


def normalize_navigation_index(total: object, current_index: object = 0) -> int:
    """Return a zero-based page index clamped to the available page count."""
    _, index = _clamp_navigation_index(
        _config_int_value(total, 0),
        _config_int_value(current_index, 0),
    )
    return index


def normalize_preview_page_cache_tokens(tokens: object, *, expected_len: int) -> list[int] | None:
    """Return integer cache tokens only when the payload matches the page count."""
    if not isinstance(tokens, (list, tuple)) or len(tokens) != expected_len:
        return None
    normalized: list[int] = []
    for value in tokens:
        try:
            normalized.append(int(value))
        except Exception:
            return None
    return normalized


def build_preview_page_cache_tokens_state(
    context: Mapping[str, object] | None,
    *,
    preview_page_count: object,
    device_preview_page_count: object,
) -> dict[str, Any]:
    """Return normalized preview-cache tokens or a rebuild request."""
    payload = _coerce_mapping_payload(context)
    preview_count = max(0, _config_int_value(preview_page_count, 0))
    device_count = max(0, _config_int_value(device_preview_page_count, 0))
    preview_tokens = normalize_preview_page_cache_tokens(
        payload.get('preview_page_cache_tokens'),
        expected_len=preview_count,
    )
    device_tokens = normalize_preview_page_cache_tokens(
        payload.get('device_preview_page_cache_tokens'),
        expected_len=device_count,
    )
    should_rebuild = preview_tokens is None or device_tokens is None
    return {
        'should_rebuild': should_rebuild,
        'preview_page_cache_tokens': [] if preview_tokens is None else list(preview_tokens),
        'device_preview_page_cache_tokens': [] if device_tokens is None else list(device_tokens),
    }


def normalize_device_view_source_value(value: object, *, default: str = 'xtc') -> str:
    """Normalize the source selector used by the device-view runtime."""
    if value is None:
        text = ''
    elif isinstance(value, os.PathLike):
        text = os.fspath(value)
    elif isinstance(value, (bytes, bytearray)):
        try:
            text = os.fsdecode(bytes(value))
        except Exception:
            text = ''
    else:
        text = str(value)
    normalized = text.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'\"', "'"}:
        quoted = normalized[1:-1].strip()
        if quoted:
            normalized = quoted
    normalized = normalized.lower()
    if normalized in {'preview', 'xtc'}:
        return normalized
    return default


def resolve_effective_device_view_source(source: object, *, has_preview_pages: object) -> str:
    """Return the device-view source that can actually be displayed now."""
    normalized = normalize_device_view_source_value(source, default='xtc')
    if normalized == 'preview' and bool(has_preview_pages):
        return 'preview'
    return 'xtc'


def is_preview_display_active(
    view_mode: object,
    *,
    has_font_preview_pages: object,
    effective_device_view_source: object,
) -> bool:
    """Return whether the currently visible page source is a generated preview."""
    normalized_mode = normalize_choice_value(view_mode, 'font', {'font', 'device'})
    if normalized_mode == 'font':
        return bool(has_font_preview_pages)
    return normalize_device_view_source_value(effective_device_view_source, default='xtc') == 'preview'


def build_preview_view_page_sync_state(
    *,
    mode: object,
    effective_device_view_source: object,
    preview_page_count: object,
    device_preview_page_count: object,
    current_preview_index: object,
    current_device_preview_index: object,
) -> dict[str, Any]:
    """Return the page-index sync plan when switching between preview views."""
    normalized_mode = normalize_choice_value(mode, 'font', {'font', 'device'})
    source = normalize_device_view_source_value(effective_device_view_source, default='xtc')
    if source != 'preview':
        return {
            'should_sync': False,
            'target': '',
            'target_index': 0,
        }
    if normalized_mode == 'font':
        total = max(0, _config_int_value(preview_page_count, 0))
        if total <= 0:
            return {
                'should_sync': False,
                'target': 'font',
                'target_index': 0,
            }
        return {
            'should_sync': True,
            'target': 'font',
            'target_index': normalize_navigation_index(total, current_device_preview_index),
        }
    total = max(0, _config_int_value(device_preview_page_count, 0))
    if total <= 0:
        return {
            'should_sync': False,
            'target': 'device',
            'target_index': 0,
        }
    return {
        'should_sync': True,
        'target': 'device',
        'target_index': normalize_navigation_index(total, current_preview_index),
    }


def build_navigation_target_state(
    *,
    total: object,
    current_index: object,
    target_index: object,
) -> dict[str, Any]:
    total_pages, current = _clamp_navigation_index(_config_int_value(total, 0), _config_int_value(current_index, 0))
    if total_pages <= 0:
        return {
            'active': False,
            'current_index': 0,
            'target_index': 0,
            'changed': False,
        }
    _, target = _clamp_navigation_index(total_pages, _config_int_value(target_index, current))
    return {
        'active': True,
        'current_index': current,
        'target_index': target,
        'changed': target != current,
    }


def build_navigation_delta_state(
    *,
    total: object,
    current_index: object,
    delta: object,
) -> dict[str, Any]:
    total_pages, current = _clamp_navigation_index(_config_int_value(total, 0), _config_int_value(current_index, 0))
    if total_pages <= 0:
        return {
            'active': False,
            'current_index': 0,
            'target_index': 0,
            'changed': False,
        }
    delta_value = _config_int_value(delta, 0)
    return build_navigation_target_state(
        total=total_pages,
        current_index=current,
        target_index=current + delta_value,
    )


def build_navigation_input_state(
    *,
    total: object,
    current_index: object,
    input_page: object,
) -> dict[str, Any]:
    total_pages, current = _clamp_navigation_index(_config_int_value(total, 0), _config_int_value(current_index, 0))
    if total_pages <= 0:
        return {
            'active': False,
            'current_index': 0,
            'target_index': 0,
            'changed': False,
            'is_valid': False,
        }
    page_number = _config_int_value(input_page, 0)
    if page_number < 1 or page_number > total_pages:
        return {
            'active': True,
            'current_index': current,
            'target_index': current,
            'changed': False,
            'is_valid': False,
        }
    target = page_number - 1
    return {
        'active': True,
        'current_index': current,
        'target_index': target,
        'changed': target != current,
        'is_valid': True,
    }


def build_navigation_display_state(
    *,
    view_mode: str,
    total: int,
    current_index: int,
    truncated: bool = False,
) -> dict[str, Any]:
    normalized_view_mode = str(view_mode or 'device').strip().lower()
    if normalized_view_mode not in {'font', 'device'}:
        normalized_view_mode = 'device'
    total_pages = max(0, int(total))
    index = int(current_index)
    if total_pages > 0:
        index = max(0, min(total_pages - 1, index))
    else:
        index = 0
    active = total_pages > 0
    return {
        'active': active,
        'total': total_pages,
        'current_index': index,
        'current_page': index + 1 if active else 0,
        'can_go_prev': active and index > 0,
        'can_go_next': active and index < max(0, total_pages - 1),
        'total_label': f'/ {total_pages}{"+" if truncated and active else ""}',
        'view_mode': normalized_view_mode,
    }




def build_device_navigation_payload(
    *,
    view_mode: object,
    total: object,
    current_index: object,
    current_page: object | None = None,
    is_preview: object = False,
    truncated: object = False,
) -> dict[str, Any]:
    total_pages = max(0, _config_int_value(total, 0))
    index = _config_int_value(current_index, 0)
    preview_source = bool(is_preview)
    payload = build_navigation_display_state(
        view_mode='device',
        total=total_pages,
        current_index=index,
        truncated=bool(preview_source and truncated),
    )
    normalized_view_mode = str(view_mode or 'font').strip().lower()
    payload['active'] = bool(normalized_view_mode == 'device' and payload.get('active'))
    if current_page is not None:
        payload['current_page'] = max(0, _config_int_value(current_page, payload.get('current_page', 0)))
    return payload

def build_navigation_apply_state(
    payload: Mapping[str, object],
    nav_state: Mapping[str, object],
    *,
    total_label_format: object = '/ {total}',
    nav_buttons_reversed: object = False,
) -> dict[str, Any]:
    total = max(0, _config_int_value(payload.get('total'), 0))
    nav_active = _config_bool_value(nav_state.get('active'), False)
    active = total > 0 and _config_bool_value(payload.get('active'), nav_active) and nav_active
    current_page = _config_int_value(nav_state.get('current_page'), 0) if total > 0 else 0
    can_go_prev = active and _config_bool_value(nav_state.get('can_go_prev'), False)
    can_go_next = active and _config_bool_value(nav_state.get('can_go_next'), False)

    format_text = str(total_label_format or '/ {total}')
    try:
        total_label_fallback = format_text.format(total=total)
    except Exception:
        total_label_fallback = f'/ {total}'
    total_label = str(payload.get('total_label', total_label_fallback))
    if bool(nav_buttons_reversed):
        prev_enabled = can_go_next
        next_enabled = can_go_prev
    else:
        prev_enabled = can_go_prev
        next_enabled = can_go_next

    return {
        'active': active,
        'current_page': current_page,
        'can_go_prev': can_go_prev,
        'can_go_next': can_go_next,
        'prev_enabled': prev_enabled,
        'next_enabled': next_enabled,
        'total_label': total_label,
    }


def build_nav_button_text_state(
    nav_bar_plan: Mapping[str, object] | None = None,
    *,
    nav_buttons_reversed: object = False,
) -> dict[str, str]:
    """Return display texts for the previous/next navigation buttons.

    ``MainWindow`` keeps ownership of the actual buttons and signal wiring;
    this helper only resolves the layout-plan labels and reversed-button
    presentation rule.
    """

    plan = dict(nav_bar_plan or {})
    prev_text = str(plan.get('prev_button_text', '前'))
    next_text = str(plan.get('next_button_text', '次'))
    if _config_bool_value(nav_buttons_reversed, False):
        return {'prev_button_text': next_text, 'next_button_text': prev_text}
    return {'prev_button_text': prev_text, 'next_button_text': next_text}


def build_preview_zoom_control_state(
    view_toggle_bar_plan: Mapping[str, object] | None = None,
    *,
    actual_size: object = False,
    label_key: object = None,
    tooltip_key: object = None,
) -> dict[str, str]:
    """Return label/tooltip text for the right-pane preview zoom controls.

    ``MainWindow`` owns the Qt widgets; this helper keeps the mode-dependent
    text resolution testable without constructing the GUI.
    """

    plan = dict(view_toggle_bar_plan or {})
    actual = _config_bool_value(actual_size, False)
    resolved_label_key = str(
        label_key
        or ('preview_zoom_actual_size_label_text' if actual else 'preview_zoom_label_text')
    )
    resolved_tooltip_key = str(
        tooltip_key
        or ('preview_zoom_actual_size_tooltip' if actual else 'preview_zoom_normal_tooltip')
    )
    label_fallback = '実寸補正' if actual else '表示倍率'
    tooltip_fallback = (
        '実寸近似ON: 実機サイズに合わせる補正倍率です。'
        if actual
        else 'フォントビュー（実寸近似OFF）と実機ビューの表示倍率です。'
    )
    return {
        'label_text': str(plan.get(resolved_label_key, label_fallback)),
        'tooltip': str(plan.get(resolved_tooltip_key, tooltip_fallback)),
    }



def build_loaded_xtc_view_mode_state(
    mode: object,
    *,
    safe: object = False,
    can_apply_full_view_mode: object = False,
) -> dict[str, Any]:
    """Return how a loaded XTC view-mode request should be applied.

    The GUI keeps ownership of Qt widgets and ``set_main_view_mode``.  This
    helper only normalizes the requested mode and decides whether safe mode
    should use the full UI path or direct state assignment.
    """
    mode_text = _coerce_message_text(mode).strip()
    if not mode_text:
        return {
            'has_mode': False,
            'mode': '',
            'apply_full_view_mode': False,
            'assign_main_view_mode': False,
        }
    safe_mode = _config_bool_value(safe, False)
    apply_full = (not safe_mode) or _config_bool_value(can_apply_full_view_mode, False)
    return {
        'has_mode': True,
        'mode': mode_text,
        'apply_full_view_mode': apply_full,
        'assign_main_view_mode': not apply_full,
    }

def build_page_input_apply_state(
    *,
    total_pages: object,
    current_page: object = 0,
    empty_minimum: object = 0,
    empty_maximum: object = 0,
    active_minimum: object = 1,
) -> dict[str, int | bool]:
    """Return the range/value state for the shared page input widget."""
    empty_min = _config_int_value(empty_minimum, 0)
    empty_max = _config_int_value(empty_maximum, 0)
    active_min = _config_int_value(active_minimum, 1)
    total = max(0, _config_int_value(total_pages, 0))
    value = max(0, _config_int_value(current_page, 0))
    if total <= 0:
        return {
            'active': False,
            'minimum': empty_min,
            'maximum': empty_max,
            'value': empty_min,
        }
    return {
        'active': True,
        'minimum': active_min,
        'maximum': total,
        'value': max(active_min, min(value or active_min, total)),
    }




def read_image_dimensions(image: object) -> tuple[int, int]:
    """Return safe ``(width, height)`` values from a Qt/Pillow-like image object."""
    if image is None:
        return 0, 0

    def _read_dimension(name: str) -> int:
        candidate = getattr(image, name, None)
        try:
            value = candidate() if callable(candidate) else candidate
        except Exception:
            value = 0
        try:
            return max(0, int(value))
        except Exception:
            return 0

    return _read_dimension('width'), _read_dimension('height')




def normalize_preview_zoom_pct(
    value: object,
    *,
    default: int = 100,
    minimum: int = 50,
    maximum: int = 300,
) -> int:
    """Return a safe preview zoom percentage for UI/runtime calculations."""
    parsed = payload_optional_int_value({'preview_zoom_pct': value}, 'preview_zoom_pct')
    normalized = int(default) if parsed is None else int(parsed)
    lower = min(int(minimum), int(maximum))
    upper = max(int(minimum), int(maximum))
    return max(lower, min(normalized, upper))


def build_actual_size_calibration_factor(
    *,
    uses_preview_zoom: object,
    preview_zoom_pct: object,
    calibration_pct: object,
    min_factor: float = 0.5,
    max_factor: float = 3.0,
) -> float:
    """Return the effective scale factor for actual-size preview rendering."""
    if _config_bool_value(uses_preview_zoom, False):
        return normalize_preview_zoom_pct(preview_zoom_pct) / 100.0
    try:
        value = float(calibration_pct) / 100.0
    except Exception:
        value = 1.0
    if not math.isfinite(value):
        value = 1.0
    lower = min(float(min_factor), float(max_factor))
    upper = max(float(min_factor), float(max_factor))
    return max(lower, min(value, upper))




def build_font_preview_target_size(
    *,
    actual_size: object,
    screen_w_mm: object,
    screen_h_mm: object,
    px_per_mm: object,
    viewport_width: object = 0,
    viewport_height: object = 0,
    zoom_factor: object = 1.0,
    fallback: tuple[int, int] = (480, 720),
) -> tuple[int, int]:
    """Return the target font-preview size as a plain ``(width, height)`` pair."""

    def _float_value(value: object, default: float = 0.0) -> float:
        try:
            parsed = float(value)
        except Exception:
            return float(default)
        return parsed if math.isfinite(parsed) else float(default)

    if _config_bool_value(actual_size, False):
        width_mm = max(0.0, _float_value(screen_w_mm, 0.0))
        height_mm = max(0.0, _float_value(screen_h_mm, 0.0))
        px = max(0.0, _float_value(px_per_mm, 0.0))
        return max(180, int(width_mm * px)), max(240, int(height_mm * px))

    viewport_w = _config_int_value(viewport_width, 0)
    viewport_h = _config_int_value(viewport_height, 0)
    if viewport_w >= 10 and viewport_h >= 10:
        zoom = _float_value(zoom_factor, 1.0)
        if abs(zoom - 1.0) < 0.001:
            return viewport_w, viewport_h
        return max(10, int(round(viewport_w * zoom))), max(10, int(round(viewport_h * zoom)))

    try:
        fallback_w, fallback_h = fallback
    except Exception:
        fallback_w, fallback_h = 480, 720
    return _config_int_value(fallback_w, 480), _config_int_value(fallback_h, 720)



def build_viewer_profile_resolution_state(
    width: object,
    height: object,
    *,
    current_width: object = 0,
    current_height: object = 0,
    profile_dimensions: Mapping[str, Sequence[object]] | None = None,
    preferred_profile_keys: Sequence[str] = ('x4', 'x3'),
) -> dict[str, object]:
    """Return how the GUI should resolve a viewer profile for page dimensions.

    The GUI layer still owns ``DeviceProfile`` instances. This helper only
    decides whether the requested pixel size maps to the current profile, a
    known preset profile, a custom profile, or an invalid fallback.
    """

    width_px = max(0, _config_int_value(width, 0))
    height_px = max(0, _config_int_value(height, 0))
    if width_px <= 0 or height_px <= 0:
        return {
            'kind': 'current',
            'profile_key': '',
            'width_px': width_px,
            'height_px': height_px,
        }

    current_w = max(0, _config_int_value(current_width, 0))
    current_h = max(0, _config_int_value(current_height, 0))
    if current_w == width_px and current_h == height_px:
        return {
            'kind': 'current',
            'profile_key': '',
            'width_px': width_px,
            'height_px': height_px,
        }

    dimensions = dict(profile_dimensions or {})
    for raw_key in preferred_profile_keys:
        key = str(raw_key).strip()
        if not key:
            continue
        raw_size = dimensions.get(key)
        if not isinstance(raw_size, Sequence) or isinstance(raw_size, (str, bytes, bytearray)):
            continue
        size_values = list(raw_size)
        if len(size_values) < 2:
            continue
        preset_w = max(0, _config_int_value(size_values[0], 0))
        preset_h = max(0, _config_int_value(size_values[1], 0))
        if preset_w == width_px and preset_h == height_px:
            return {
                'kind': 'profile',
                'profile_key': key,
                'width_px': width_px,
                'height_px': height_px,
            }

    return {
        'kind': 'custom',
        'profile_key': 'custom',
        'width_px': width_px,
        'height_px': height_px,
    }


def build_custom_viewer_profile_metrics(
    *,
    width_px: object,
    height_px: object,
    ppi: object,
    screen_w_mm: object,
    screen_h_mm: object,
    body_w_mm: object,
    body_h_mm: object,
) -> dict[str, float | int]:
    """Return dimensions for a custom viewer profile derived from pixels.

    The GUI layer owns the concrete ``DeviceProfile`` object; this helper only
    normalizes the arithmetic so the mm conversion and body-area ratios can be
    regression tested without Qt.
    """

    def _float_value(value: object, default: float) -> float:
        try:
            parsed = float(value)
        except Exception:
            return float(default)
        return parsed if math.isfinite(parsed) else float(default)

    def _int_value(value: object, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return int(default)

    width_value = max(1, _int_value(width_px, 1))
    height_value = max(1, _int_value(height_px, 1))
    ppi_value = max(1e-6, _float_value(ppi, 300.0))
    px_per_mm = max(1e-6, ppi_value / 25.4)
    source_screen_w_mm = max(1e-6, _float_value(screen_w_mm, 1.0))
    source_screen_h_mm = max(1e-6, _float_value(screen_h_mm, 1.0))
    source_body_w_mm = max(0.0, _float_value(body_w_mm, source_screen_w_mm))
    source_body_h_mm = max(0.0, _float_value(body_h_mm, source_screen_h_mm))
    body_w_ratio = source_body_w_mm / source_screen_w_mm
    body_h_ratio = source_body_h_mm / source_screen_h_mm
    resolved_screen_w_mm = float(width_value) / px_per_mm
    resolved_screen_h_mm = float(height_value) / px_per_mm
    return {
        'width_px': int(width_value),
        'height_px': int(height_value),
        'screen_w_mm': resolved_screen_w_mm,
        'screen_h_mm': resolved_screen_h_mm,
        'body_w_mm': resolved_screen_w_mm * body_w_ratio,
        'body_h_mm': resolved_screen_h_mm * body_h_ratio,
    }


def build_safe_preview_layout_size(
    size: object,
    *,
    fallback: tuple[int, int] = (480, 720),
    minimum: int = 10,
    maximum: int = 4096,
) -> tuple[int, int]:
    """Return a clamped ``(width, height)`` pair from a Qt-like size object."""
    try:
        fallback_w, fallback_h = fallback
    except Exception:
        fallback_w, fallback_h = 480, 720

    def _dimension_value(name: str, fallback_value: int) -> int:
        candidate = getattr(size, name, None)
        try:
            raw_value = candidate() if callable(candidate) else candidate
        except Exception:
            raw_value = fallback_value
        try:
            return int(raw_value)
        except Exception:
            return int(fallback_value)

    lower = min(int(minimum), int(maximum))
    upper = max(int(minimum), int(maximum))
    width = _dimension_value('width', int(fallback_w))
    height = _dimension_value('height', int(fallback_h))
    return max(lower, min(width, upper)), max(lower, min(height, upper))


def build_viewer_minimum_size(
    size_hint: object,
    *,
    fallback: tuple[int, int] = (660, 860),
    min_width: int = 360,
    min_height: int = 600,
    maximum: int = 4096,
) -> tuple[int, int]:
    """Return a clamped minimum size for the device preview widget."""
    try:
        fallback_w, fallback_h = fallback
    except Exception:
        fallback_w, fallback_h = 660, 860

    def _dimension_value(name: str, fallback_value: int) -> int:
        candidate = getattr(size_hint, name, None)
        try:
            raw_value = candidate() if callable(candidate) else candidate
        except Exception:
            raw_value = fallback_value
        try:
            return int(raw_value)
        except Exception:
            return int(fallback_value)

    upper = max(1, int(maximum))
    width = _dimension_value('width', int(fallback_w))
    height = _dimension_value('height', int(fallback_h))
    return (
        max(int(min_width), min(width, upper)),
        max(int(min_height), min(height, upper)),
    )

def build_preset_display_name(preset: Mapping[str, object]) -> str:
    button_text = str(preset.get('button_text') or '').strip()
    name = str(preset.get('name') or '').strip()
    if button_text and name:
        return button_text if button_text == name else f'{button_text} / {name}'
    return button_text or name or 'プリセット'


def compact_multiline_label_text(text: object) -> str:
    """Return text without trailing blank lines for compact QLabel display."""
    lines = [line.rstrip() for line in str(text or '').splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines)


def _build_preset_summary_lines(
    preset: Mapping[str, object],
    *,
    font_text: str,
    device_profile_keys: Collection[str],
    kinsoku_mode_labels: Mapping[str, str],
    output_format_labels: Mapping[str, str],
) -> tuple[str, str, str, str]:
    normalized_profiles = {str(item).strip().lower() for item in device_profile_keys}
    night_text = 'ON' if _config_bool_value(preset.get('night_mode'), False) else 'OFF'
    dither_text = 'ON' if _config_bool_value(preset.get('dither'), False) else 'OFF'
    profile_key = str(preset.get('profile', 'x4')).strip().lower()
    if profile_key not in normalized_profiles:
        profile_key = 'x4'
    profile_text = profile_key.upper()
    kinsoku_mode = str(preset.get('kinsoku_mode', 'standard')).strip().lower()
    if kinsoku_mode not in kinsoku_mode_labels:
        kinsoku_mode = 'standard'
    kinsoku_text = kinsoku_mode_labels.get(kinsoku_mode, '標準')
    out_fmt = str(preset.get('output_format', 'xtc')).strip().lower()
    if out_fmt not in output_format_labels:
        out_fmt = 'xtc'
    preset_name = build_preset_display_name(preset)
    font_size = _config_int_value(preset.get('font_size'), 26)
    ruby_size = _config_int_value(preset.get('ruby_size'), 12)
    line_spacing = _config_int_value(preset.get('line_spacing'), 44)
    margin_t = _config_int_value(preset.get('margin_t'), 12)
    margin_b = _config_int_value(preset.get('margin_b'), 14)
    margin_r = _config_int_value(preset.get('margin_r'), 12)
    margin_l = _config_int_value(preset.get('margin_l'), 12)
    threshold = _config_int_value(preset.get('threshold'), 128)
    out_fmt_text = output_format_labels.get(out_fmt, 'XTC')
    name_line = preset_name
    line1 = f'機種: {profile_text} / 出力形式: {out_fmt_text} / 本文: {font_size} / ルビ: {ruby_size} / 行間: {line_spacing}'
    line2 = f'余白: 上 {margin_t} 下 {margin_b} 右 {margin_r} 左 {margin_l} / 白黒反転: {night_text} / ディザ: {dither_text} / しきい値: {threshold} / 禁則: {kinsoku_text}'
    line3 = f'フォント: {font_text}'
    return name_line, line1, line2, line3



def build_preset_summary_text(
    preset: Mapping[str, object],
    *,
    font_text: str,
    device_profile_keys: Collection[str],
    kinsoku_mode_labels: Mapping[str, str],
    output_format_labels: Mapping[str, str],
    summary_tag: str = '',
    include_name_line: bool = True,
) -> str:
    name_line, line1, line2, line3 = _build_preset_summary_lines(
        preset,
        font_text=font_text,
        device_profile_keys=device_profile_keys,
        kinsoku_mode_labels=kinsoku_mode_labels,
        output_format_labels=output_format_labels,
    )
    lines = [line1, line2, line3]
    if include_name_line:
        tag_text = str(summary_tag or '').strip()
        if tag_text:
            name_line = f'{name_line} {tag_text}'
        lines.insert(0, name_line)
    return compact_multiline_label_text('\n'.join(line for line in lines if str(line).strip()))



def build_preset_summary_html(
    preset: Mapping[str, object],
    *,
    font_text: str,
    device_profile_keys: Collection[str],
    kinsoku_mode_labels: Mapping[str, str],
    output_format_labels: Mapping[str, str],
    summary_tag: str = '',
    include_name_line: bool = True,
) -> str:
    name_line, line1, line2, line3 = _build_preset_summary_lines(
        preset,
        font_text=font_text,
        device_profile_keys=device_profile_keys,
        kinsoku_mode_labels=kinsoku_mode_labels,
        output_format_labels=output_format_labels,
    )
    rendered_lines = [html.escape(line1), html.escape(line2), html.escape(line3)]
    if include_name_line:
        tag_text = str(summary_tag or '').strip()
        escaped_preset_name = html.escape(name_line)
        escaped_tag_text = html.escape(tag_text)
        rendered_name_line = (
            escaped_preset_name
            if not escaped_tag_text
            else f'{escaped_preset_name} <span style="color:#6B7C90;">{escaped_tag_text}</span>'
        )
        rendered_lines.insert(0, rendered_name_line)
    line_markup = ''.join(
        f'<div style="margin:0; padding:0;">{line}</div>'
        for line in rendered_lines
        if str(line).strip()
    )
    return (
        '<div style="line-height:1.12; text-align:left; margin:0; padding:0;">'
        f'{line_markup}'
        '</div>'
    )




def find_matching_result_index(target_key: object, candidate_keys: Sequence[object]) -> int | None:
    normalized_target = str(target_key or '').strip()
    if not normalized_target:
        return None
    for idx, raw_key in enumerate(candidate_keys):
        if str(raw_key or '').strip() == normalized_target:
            return idx
    return None


def resolve_preferred_result_index(
    *,
    selected_indexes: Sequence[object],
    current_index: object,
    item_count: object,
) -> int | None:
    normalized_count = max(0, _config_int_value(item_count, 0))

    def _is_valid_index(value: object) -> int | None:
        normalized = payload_optional_int_value({'value': value}, 'value')
        if normalized is None or normalized < 0:
            return None
        if normalized_count > 0 and normalized >= normalized_count:
            return None
        return normalized

    valid_selected_indexes: list[int] = []
    seen_indexes: set[int] = set()
    for raw_index in selected_indexes:
        valid_index = _is_valid_index(raw_index)
        if valid_index is None or valid_index in seen_indexes:
            continue
        seen_indexes.add(valid_index)
        valid_selected_indexes.append(valid_index)

    valid_current = _is_valid_index(current_index)

    if valid_current is not None:
        return valid_current

    if len(valid_selected_indexes) == 1:
        return valid_selected_indexes[0]
    if len(valid_selected_indexes) > 1:
        return None

    if normalized_count == 1:
        return 0
    return None

def build_result_display_name(path_text: object) -> str:
    raw = str(path_text or '').strip()
    if not raw:
        return ''
    if '\\' in raw or (len(raw) >= 2 and raw[1] == ':'):
        return ntpath.basename(raw) or raw
    return Path(raw).name or raw


def build_xtc_display_name(path_text: object) -> str:
    return build_result_display_name(path_text)


def build_xtc_source_payload(path_text: object, display_name: object = None) -> dict[str, str]:
    normalized_path = str(path_text or '').strip()
    resolved_display_name = (
        str(display_name).strip()
        if display_name is not None
        else build_xtc_display_name(normalized_path)
    )
    return {
        'path_text': normalized_path,
        'display_name': resolved_display_name,
    }


def build_xtc_source_document_payload(
    source_payload: Mapping[str, object],
    document_payload: Mapping[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = dict(source_payload)
    payload.update(dict(document_payload))
    return payload


def build_results_summary_message(summary_lines: Sequence[str], entry_count: int, fallback: str = '') -> str:
    normalized_lines = [str(line).strip() for line in summary_lines if str(line).strip()]
    if normalized_lines:
        return ' / '.join(normalized_lines)
    if entry_count > 0:
        return f'保存ファイル: {entry_count} 件'
    return str(fallback or '').strip()
