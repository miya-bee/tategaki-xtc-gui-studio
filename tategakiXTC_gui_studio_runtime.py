from __future__ import annotations

"""Runtime normalization helpers for tategakiXTC GUI Studio.

The entry module re-exports these names so existing imports and monkey patches
that import from ``tategakiXTC_gui_studio`` keep working.
"""

import os
from collections.abc import Iterable, Mapping


def _coerce_path_text(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        if not raw:
            return ''
        return os.fsdecode(raw)
    return str(value)


def _iter_runtime_xtc_page_items(value: object) -> Iterable[object]:
    if value is None:
        return
    if isinstance(value, str):
        text = value.strip()
        if text:
            yield text
        return
    if isinstance(value, (bytes, bytearray, memoryview)):
        text = _coerce_path_text(value).strip()
        if text:
            yield text
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_runtime_xtc_page_items(nested)
        return
    try:
        iterator = iter(value)  # type: ignore[arg-type]
    except TypeError:
        yield value
        return
    for item in iterator:
        yield from _iter_runtime_xtc_page_items(item)


def _normalize_runtime_xtc_pages(value: object) -> list[object]:
    return [item for item in _iter_runtime_xtc_page_items(value)]
