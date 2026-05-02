from __future__ import annotations

"""Preview orchestration helpers for the GUI layer.

This module prepares preview payloads and refresh state without depending on Qt
widgets so MainWindow can stay thinner while behavior remains regression-tested.
"""

from functools import lru_cache
from typing import Any, Iterable, Mapping

import zlib

import tategakiXTC_gui_studio_logic as studio_logic


DEFAULT_OUTPUT_FORMAT = 'xtc'
ALLOWED_OUTPUT_FORMATS = {'xtc', 'xtch'}
ALLOWED_DEVICE_VIEW_SOURCES = {'preview', 'xtc'}


def _iter_preview_page_items(value: object) -> Iterable[object]:
    if value is None:
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, (bytes, bytearray)):
        try:
            yield bytes(value).decode('ascii')
        except Exception:
            yield bytes(value).decode('utf-8', errors='ignore')
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_preview_page_items(nested)
        return
    try:
        iterator = iter(value)  # type: ignore[arg-type]
    except Exception:
        return
    for item in iterator:
        yield from _iter_preview_page_items(item)



def _normalize_preview_pages(value: object) -> list[str]:
    """Normalize preview bundle pages into a flat list of base64 strings.

    The preview worker is expected to return a list of base64-encoded PNG
    strings, but we defensively accept:
    - a single base64 string
    - bytes / bytearray containing an ASCII/UTF-8 string
    - nested iterables or mappings yielding page-like objects

    This avoids accidental "string is iterable" bugs where a single page is
    treated as a list of characters, and also keeps the GUI resilient if the
    worker payload shape becomes slightly more nested in the future.
    """
    pages: list[str] = []
    for item in _iter_preview_page_items(value):
        if isinstance(item, str):
            text = item.strip()
            if text:
                pages.append(text)
    return pages


def _coerce_preview_page_list(value: object) -> list[str]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item.strip() for item in value if item and item.strip()]
    return _normalize_preview_pages(value)


def _coerce_preview_payload_mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _coerce_preview_data_url(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value).decode('utf-8')
        except Exception:
            value = bytes(value).decode('ascii', errors='ignore')
    text = str(value).strip()
    return text or None


@lru_cache(maxsize=8192)
def _preview_page_cache_token_text(text: str) -> int:
    normalized = str(text or '').strip()
    if not normalized:
        return 0
    try:
        data = normalized.encode('ascii')
    except Exception:
        data = normalized.encode('utf-8', 'ignore')
    checksum = zlib.crc32(data) & 0xFFFFFFFF
    return int((checksum << 1) ^ len(normalized))


@lru_cache(maxsize=512)
def _preview_page_cache_tokens_tuple(normalized_pages: tuple[str, ...]) -> tuple[int, ...]:
    if not normalized_pages:
        return tuple()
    token_for_text = _preview_page_cache_token_text
    return tuple(token_for_text(text) for text in normalized_pages)


def _preview_page_cache_token(value: object) -> int:
    return _preview_page_cache_token_text(_coerce_preview_data_url(value) or '')


def _preview_page_cache_tokens(pages: object) -> list[int]:
    normalized_pages = _coerce_preview_page_list(pages)
    if not normalized_pages:
        return []
    return list(_preview_page_cache_tokens_tuple(tuple(normalized_pages)))


def _coerce_mapping(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _normalize_device_view_source(value: object, *, default: str = 'preview') -> str:
    normalized = str(value or default).strip().lower()
    if normalized not in ALLOWED_DEVICE_VIEW_SOURCES:
        return default
    return normalized


def build_preview_payload(
    *,
    render_settings_base: Mapping[str, object],
    current_preview_mode: object,
    selected_profile_key: object,
    preview_image_data_url: object,
    preview_page_limit: object,
    default_preview_page_limit: int,
) -> dict[str, object]:
    """Build the current preview payload from GUI state."""
    preview_limit = max(1, studio_logic._config_int_value(preview_page_limit, default_preview_page_limit))
    return {
        'mode': str(current_preview_mode or 'text'),
        'profile': str(selected_profile_key or ''),
        'file_b64': _coerce_preview_data_url(preview_image_data_url),
        'target_path': render_settings_base['target'],
        'font_file': render_settings_base['font_file'],
        'font_size': render_settings_base['font_size'],
        'ruby_size': render_settings_base['ruby_size'],
        'line_spacing': render_settings_base['line_spacing'],
        'margin_t': render_settings_base['margin_t'],
        'margin_b': render_settings_base['margin_b'],
        'margin_r': render_settings_base['margin_r'],
        'margin_l': render_settings_base['margin_l'],
        'dither': 'true' if studio_logic._config_bool_value(render_settings_base.get('dither'), False) else 'false',
        'threshold': render_settings_base['threshold'],
        'night_mode': 'true' if studio_logic._config_bool_value(render_settings_base.get('night_mode'), False) else 'false',
        'kinsoku_mode': render_settings_base['kinsoku_mode'],
        'punctuation_position_mode': render_settings_base.get('punctuation_position_mode', 'standard'),
        'ichi_position_mode': render_settings_base.get('ichi_position_mode', 'standard'),
        'lower_closing_bracket_position_mode': render_settings_base.get('lower_closing_bracket_position_mode', 'standard'),
        'output_format': render_settings_base['output_format'],
        'width': render_settings_base['width'],
        'height': render_settings_base['height'],
        'max_pages': preview_limit,
    }


def build_preview_request_plan(
    preview_payload: Mapping[str, object] | None,
    *,
    current_output_format: object,
    default_preview_page_limit: int,
) -> dict[str, Any]:
    """Normalize payload values before preview generation runs."""
    payload = _coerce_preview_payload_mapping(preview_payload)
    payload['output_format'] = studio_logic.normalize_choice_value(
        current_output_format,
        DEFAULT_OUTPUT_FORMAT,
        ALLOWED_OUTPUT_FORMATS,
    )
    preview_limit = max(
        1,
        studio_logic._config_int_value(
            payload.get('max_pages', default_preview_page_limit),
            default_preview_page_limit,
        ),
    )
    payload['max_pages'] = preview_limit
    return {
        'payload': payload,
        'preview_limit': preview_limit,
    }


def build_preview_start_context(*, preview_limit: int) -> dict[str, Any]:
    """Build button/status state to apply when preview generation starts."""
    return {
        'button_enabled': False,
        'button_text': '生成中…',
        'status_message': studio_logic.build_preview_status_message('running', preview_limit=preview_limit),
    }


def build_preview_progress_context(
    current: object,
    total: object,
    message: object,
    *,
    preview_limit: int,
) -> dict[str, Any]:
    """Build preview progress label state without touching Qt widgets."""
    return {
        'status_message': studio_logic.build_preview_progress_message(
            current,
            total,
            message,
            preview_limit=preview_limit,
        ),
    }


def build_preview_finish_context() -> dict[str, Any]:
    """Build button state to apply after preview generation ends."""
    return {
        'button_enabled': True,
        'button_text': 'プレビュー更新',
    }


def build_manual_preview_refresh_context(
    preview_payload: Mapping[str, object] | None,
    *,
    current_output_format: object,
    default_preview_page_limit: int,
    reset_page: bool = False,
) -> dict[str, Any]:
    """Build the normalized request used by the manual refresh action."""
    request_plan = build_preview_request_plan(
        preview_payload,
        current_output_format=current_output_format,
        default_preview_page_limit=default_preview_page_limit,
    )
    return {
        'reset_page': studio_logic._config_bool_value(reset_page, False),
        'preview_payload': _coerce_mapping(request_plan.get('payload')),
        'should_update_top_status': True,
        'should_save_ui_state': True,
    }


def build_preview_bundle_state(
    bundle: Mapping[str, object] | None,
    *,
    reset_page: bool,
    current_preview_index: object,
    current_device_index: object,
    preview_limit: int,
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Build a normalized state payload from a preview bundle."""
    raw_bundle = _coerce_mapping(bundle)
    pages = _normalize_preview_pages(raw_bundle.get('pages'))
    truncated = studio_logic._config_bool_value(raw_bundle.get('truncated'), False)
    refresh_state = studio_logic.build_preview_refresh_state(
        page_count=len(pages),
        reset_page=reset_page,
        current_preview_index=current_preview_index,
        current_device_index=current_device_index,
        preview_limit=preview_limit,
        truncated=truncated,
    )
    return {
        'pages': list(pages),
        'truncated': truncated,
        'device_view_source': 'preview',
        'last_preview_requested_limit': preview_limit,
        'last_applied_preview_payload': _coerce_mapping(payload),
        'refresh_state': refresh_state,
    }



def build_preview_apply_context(
    bundle: Mapping[str, object] | None,
    *,
    reset_page: bool,
    current_preview_index: object,
    current_device_index: object,
    preview_limit: int,
    payload: Mapping[str, object],
) -> dict[str, Any]:
    """Build the preview runtime state to apply after generation succeeds."""
    bundle_state = build_preview_bundle_state(
        bundle,
        reset_page=reset_page,
        current_preview_index=current_preview_index,
        current_device_index=current_device_index,
        preview_limit=preview_limit,
        payload=payload,
    )
    refresh_state = _coerce_mapping(bundle_state.get('refresh_state'))
    pages = _coerce_preview_page_list(bundle_state.get('pages'))
    truncated = studio_logic._config_bool_value(bundle_state.get('truncated'), False)
    has_pages = studio_logic._config_bool_value(refresh_state.get('has_pages'), bool(pages))
    return {
        'preview_pages_b64': list(pages),
        'device_preview_pages_b64': list(pages),
        'preview_page_cache_tokens': list(page_tokens := _preview_page_cache_tokens(pages)),
        'device_preview_page_cache_tokens': list(page_tokens),
        'preview_pages_truncated': truncated,
        'device_preview_pages_truncated': truncated,
        'device_view_source': _normalize_device_view_source(bundle_state.get('device_view_source'), default='preview'),
        'last_preview_requested_limit': max(
            0,
            studio_logic._config_int_value(bundle_state.get('last_preview_requested_limit'), preview_limit),
        ),
        'last_applied_preview_payload': _coerce_mapping(bundle_state.get('last_applied_preview_payload')) or _coerce_mapping(payload),
        'current_preview_page_index': _clamp_preview_index(refresh_state.get('preview_index', 0), total=len(pages)),
        'current_device_preview_page_index': _clamp_preview_index(refresh_state.get('device_index', 0), total=len(pages)),
        'has_pages': has_pages,
        'status_message': str(refresh_state.get('status_message', '')),
        'display_name': 'プレビュー',
        'clear_device_page': not has_pages,
    }



def _normalized_preview_cache_tokens(tokens: object, *, expected_len: int) -> list[int] | None:
    if not isinstance(tokens, (list, tuple)) or len(tokens) != expected_len:
        return None
    normalized: list[int] = []
    for value in tokens:
        try:
            normalized.append(int(value))
        except Exception:
            return None
    return normalized



def _clamp_preview_index(index: object, *, total: int) -> int:
    total_pages = max(0, int(total))
    try:
        current_index = int(index)
    except Exception:
        current_index = 0
    if total_pages > 0:
        return max(0, min(total_pages - 1, current_index))
    return 0



def build_preview_failure_context(
    *,
    previous_device_source: object,
    error: object,
    previous_preview_pages: object = None,
    previous_device_preview_pages: object = None,
    previous_preview_page_cache_tokens: object = None,
    previous_device_preview_page_cache_tokens: object = None,
    previous_preview_pages_truncated: object = False,
    previous_device_preview_pages_truncated: object = False,
    current_preview_index: object = 0,
    current_device_index: object = 0,
) -> dict[str, Any]:
    """Build the preview runtime state to apply when generation fails."""
    error_state = studio_logic.build_preview_error_state(
        device_view_source=previous_device_source,
        error=error,
    )
    preview_pages = _coerce_preview_page_list(previous_preview_pages)
    device_pages = _coerce_preview_page_list(previous_device_preview_pages)
    preview_tokens = _normalized_preview_cache_tokens(
        previous_preview_page_cache_tokens,
        expected_len=len(preview_pages),
    )
    if preview_tokens is None:
        preview_tokens = _preview_page_cache_tokens(preview_pages)
    device_tokens = _normalized_preview_cache_tokens(
        previous_device_preview_page_cache_tokens,
        expected_len=len(device_pages),
    )
    if device_tokens is None:
        device_tokens = _preview_page_cache_tokens(device_pages)
    return {
        'preview_pages_b64': list(preview_pages),
        'device_preview_pages_b64': list(device_pages),
        'preview_page_cache_tokens': list(preview_tokens),
        'device_preview_page_cache_tokens': list(device_tokens),
        'preview_pages_truncated': studio_logic._config_bool_value(previous_preview_pages_truncated, False),
        'device_preview_pages_truncated': studio_logic._config_bool_value(previous_device_preview_pages_truncated, False),
        'device_view_source': 'xtc',
        'current_preview_page_index': _clamp_preview_index(
            current_preview_index,
            total=len(preview_pages),
        ),
        'current_device_preview_page_index': _clamp_preview_index(
            current_device_index,
            total=len(device_pages),
        ),
        'clear_device_page': studio_logic._config_bool_value(error_state.get('clear_device_page'), False),
        'status_message': str(error_state.get('status_message', '')),
        'error_message': f'プレビュー生成エラー\n{error}',
    }
