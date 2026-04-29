from __future__ import annotations

"""Pure helpers for the GUI layer.

This module keeps presentation and small orchestration decisions out of
MainWindow so they can be tested without a live Qt runtime.
"""

import html
import ntpath
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
import math
from typing import Any


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
    allowed = {str(item).strip().lower() for item in allowed_values}
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
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
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
    payload['target'] = str(raw_payload.get('target') or '').strip()
    payload['font_file'] = str(raw_payload.get('font_file') or '').strip()
    payload['main_view_mode'] = normalize_choice_value(
        raw_payload.get('main_view_mode'),
        'font',
        allowed_view_modes,
    )
    return payload


def build_settings_ui_apply_payload(
    raw_payload: Mapping[str, object],
    *,
    defaults: Mapping[str, object],
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    bottom_tab_count: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
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
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
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


def build_preset_display_name(preset: Mapping[str, object]) -> str:
    button_text = str(preset.get('button_text') or '').strip()
    name = str(preset.get('name') or '').strip()
    if button_text and name:
        return button_text if button_text == name else f'{button_text} / {name}'
    return button_text or name or 'プリセット'


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
) -> str:
    name_line, line1, line2, line3 = _build_preset_summary_lines(
        preset,
        font_text=font_text,
        device_profile_keys=device_profile_keys,
        kinsoku_mode_labels=kinsoku_mode_labels,
        output_format_labels=output_format_labels,
    )
    tag_text = str(summary_tag or '').strip()
    if tag_text:
        name_line = f'{name_line} {tag_text}'
    return '\n'.join((name_line, line1, line2, line3))



def build_preset_summary_html(
    preset: Mapping[str, object],
    *,
    font_text: str,
    device_profile_keys: Collection[str],
    kinsoku_mode_labels: Mapping[str, str],
    output_format_labels: Mapping[str, str],
    summary_tag: str = '',
) -> str:
    name_line, line1, line2, line3 = _build_preset_summary_lines(
        preset,
        font_text=font_text,
        device_profile_keys=device_profile_keys,
        kinsoku_mode_labels=kinsoku_mode_labels,
        output_format_labels=output_format_labels,
    )
    tag_text = str(summary_tag or '').strip()
    escaped_preset_name = html.escape(name_line)
    escaped_font_line = html.escape(line3)
    escaped_tag_text = html.escape(tag_text)
    rendered_name_line = (
        escaped_preset_name
        if not escaped_tag_text
        else f'{escaped_preset_name} <span style="color:#6B7C90;">{escaped_tag_text}</span>'
    )
    return (
        '<div style="line-height:1.12; text-align:left; margin:0; padding:0;">'
        f'<div style="margin:0; padding:0;">{rendered_name_line}</div>'
        f'<div style="margin:0; padding:0;">{html.escape(line1)}</div>'
        f'<div style="margin:0; padding:0;">{html.escape(line2)}</div>'
        f'<div style="margin:0; padding:0;">{escaped_font_line}</div>'
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


def build_results_summary_message(summary_lines: Sequence[str], entry_count: int, fallback: str = '') -> str:
    normalized_lines = [str(line).strip() for line in summary_lines if str(line).strip()]
    if normalized_lines:
        return ' / '.join(normalized_lines)
    if entry_count > 0:
        return f'保存ファイル: {entry_count} 件'
    return str(fallback or '').strip()
