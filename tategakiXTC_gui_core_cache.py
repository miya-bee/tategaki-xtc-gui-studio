"""
tategakiXTC_gui_core_cache.py — 入力ドキュメント cache helper

`tategakiXTC_gui_core.py` から分離した、TXT / Markdown / EPUB / archive の
入力解析キャッシュで共有する小さな helper 群。変換仕様には関与せず、
path + size + mtime による cache key と LRU 風の格納だけを担当する。
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any


INPUT_DOCUMENT_CACHE_MAX = 8


def _source_document_cache_key(path_like: str | Path) -> tuple[str, int, int]:
    """Return a stable cache key for an input document path."""
    path = Path(path_like)
    try:
        stat = path.stat()
        mtime_ns = getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1_000_000_000))
        return (str(path.resolve()), int(stat.st_size), int(mtime_ns))
    except OSError:
        return (str(path), -1, -1)


def _get_cached_input_document(cache: OrderedDict[tuple[object, ...], Any], cache_key: tuple[object, ...]) -> Any | None:
    """Return a cached parsed input document and refresh its LRU position."""
    cached = cache.get(cache_key)
    if cached is None:
        return None
    cache.move_to_end(cache_key)
    return cached


def _store_cached_input_document(cache: OrderedDict[tuple[object, ...], Any], cache_key: tuple[object, ...], document: Any) -> Any:
    """Store a parsed input document while keeping the cache bounded."""
    cache[cache_key] = document
    cache.move_to_end(cache_key)
    while len(cache) > INPUT_DOCUMENT_CACHE_MAX:
        cache.popitem(last=False)
    return document
