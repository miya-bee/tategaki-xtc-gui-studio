from __future__ import annotations

"""Settings and small plan-value helpers for ``tategakiXTC_gui_studio``.

The entry module keeps thin ``MainWindow`` wrappers for backward compatibility,
while the implementation lives here so it can be tested and released as an
independent split module.
"""

from collections.abc import Mapping, Sequence

import tategakiXTC_worker_logic as worker_logic


def _settings_raw_value(settings_store: object, key: str, default: object = None) -> object:
    value_getter = getattr(settings_store, 'value', None)
    if callable(value_getter):
        return value_getter(key, default)
    return default


def _settings_contains_key(settings_store: object, key: str) -> bool:
    contains = getattr(settings_store, 'contains', None)
    if callable(contains):
        try:
            return bool(contains(key))
        except Exception:
            pass
    sentinel = object()
    try:
        return _settings_raw_value(settings_store, key, sentinel) is not sentinel
    except Exception:
        return False


def _settings_int_value(settings_store: object, key: str, default: int) -> int:
    raw = _settings_raw_value(settings_store, key, default)
    return worker_logic._int_config_value({key: raw}, key, default)


def _settings_bool_value(settings_store: object, key: str, default: bool) -> bool:
    raw = _settings_raw_value(settings_store, key, default)
    return worker_logic._bool_config_value({key: raw}, key, default)


def _settings_str_value(settings_store: object, key: str, default: str = '') -> str:
    raw = _settings_raw_value(settings_store, key, default)
    return worker_logic._str_config_value({key: raw}, key, default)


def _coerce_mapping_payload(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, Mapping) else {}


def _plan_int_value(payload_obj: object, key: str, default: int) -> int:
    payload = _coerce_mapping_payload(payload_obj)
    return worker_logic._int_config_value(payload, key, default)


def _plan_bool_value(payload_obj: object, key: str, default: bool) -> bool:
    payload = _coerce_mapping_payload(payload_obj)
    return worker_logic._bool_config_value(payload, key, default)


def _plan_int_tuple_value(
    payload_obj: object,
    key: str,
    default: Sequence[int],
    *,
    expected_length: int | None = None,
) -> tuple[int, ...]:
    payload = _coerce_mapping_payload(payload_obj)
    value = payload.get(key, default)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return tuple(int(item) for item in default)
    items = list(value)
    if expected_length is not None and len(items) != expected_length:
        return tuple(int(item) for item in default)
    normalized: list[int] = []
    try:
        for item in items:
            normalized.append(int(item))
    except (TypeError, ValueError):
        return tuple(int(item) for item in default)
    return tuple(normalized)


def _plan_token_value(payload_obj: object, key: str, default: str) -> str:
    payload = _coerce_mapping_payload(payload_obj)
    value = payload.get(key, default)
    text = str(value).strip().lower().replace('-', '_')
    return text or default


def _combo_find_data_index(combo: object, value: object) -> int:
    find_data = getattr(combo, 'findData', None)
    if not callable(find_data):
        return -1
    try:
        idx = find_data(value)
    except Exception:
        return -1
    return idx if isinstance(idx, int) else -1
