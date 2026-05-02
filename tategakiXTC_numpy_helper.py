"""
tategakiXTC_numpy_helper.py — optional numpy lazy import helper

XTC / XTCH の高速化でだけ利用する numpy を、必要になるまで読み込まない
ための小さな共有 helper。呼び出し側は従来互換の ``np`` / import-attempted
state を持ったまま、この helper に読み込み処理だけ委譲する。
"""
from __future__ import annotations

from typing import Any


def get_cached_numpy_module(cached_module: Any, import_attempted: bool) -> tuple[Any, bool]:
    """Return the cached optional numpy module and updated attempted flag."""
    if import_attempted:
        return cached_module, import_attempted
    if cached_module is not None:
        return cached_module, True
    try:
        import numpy as numpy_module  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        return None, True
    return numpy_module, True


__all__ = [
    'get_cached_numpy_module',
]
