from __future__ import annotations

"""Preview page-cache helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._runtime_preview_pages`` etc.) and mutate cache attributes on the
window, so instance-level overrides installed by tests keep working.  This
module intentionally does not import PySide6 or ``tategakiXTC_gui_studio``.

Cache size limits are passed in by the wrappers so the entry module remains the
single source of truth for the tuning constants.
"""

from collections import OrderedDict
from typing import Any

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_preview_controller as preview_controller


def _rebuild_preview_page_cache_tokens(window: Any) -> None:
    window._preview_page_cache_tokens = preview_controller._preview_page_cache_tokens(
        window._runtime_preview_pages()
    )
    window._device_preview_page_cache_tokens = preview_controller._preview_page_cache_tokens(
        window._runtime_device_preview_pages()
    )


def _clear_font_preview_page_pixmap_cache(window: Any) -> None:
    cache = window.__dict__.get('_font_preview_page_pixmap_cache')
    if isinstance(cache, OrderedDict):
        cache.clear()
    else:
        window._font_preview_page_pixmap_cache = OrderedDict()


def _font_preview_page_pixmap_cache_key(window: Any, index: object = None) -> tuple[int, int] | None:
    pages = window._runtime_preview_pages()
    if not pages:
        return None
    current_index = worker_logic._int_config_value(
        {'value': window.__dict__.get('current_preview_page_index', 0) if index is None else index},
        'value',
        0,
    )
    current_index = max(0, min(len(pages) - 1, current_index))
    tokens = window.__dict__.get('_preview_page_cache_tokens')
    if not isinstance(tokens, list) or len(tokens) != len(pages):
        window._rebuild_preview_page_cache_tokens()
        tokens = window.__dict__.get('_preview_page_cache_tokens', [])
    token = int(tokens[current_index]) if current_index < len(tokens) else window._preview_page_cache_token(pages[current_index])
    return (current_index, token)


def _cached_font_preview_page_pixmap(window: Any, key: object) -> object | None:
    if key is None:
        return None
    cache = window.__dict__.get('_font_preview_page_pixmap_cache')
    if not isinstance(cache, OrderedDict):
        cache = OrderedDict()
        window._font_preview_page_pixmap_cache = cache
    pixmap = cache.get(key)
    if pixmap is not None:
        cache.move_to_end(key)
    return pixmap


def _store_font_preview_page_pixmap(window: Any, key: object, pixmap: object, *, cache_limit: int) -> None:
    if key is None or pixmap is None:
        return
    cache = window.__dict__.get('_font_preview_page_pixmap_cache')
    if not isinstance(cache, OrderedDict):
        cache = OrderedDict()
        window._font_preview_page_pixmap_cache = cache
    cache[key] = pixmap
    cache.move_to_end(key)
    while len(cache) > cache_limit:
        cache.popitem(last=False)


def _clear_xtc_page_qimage_cache(window: Any) -> None:
    cache = window.__dict__.get('_xtc_page_qimage_cache')
    if isinstance(cache, OrderedDict):
        cache.clear()
    else:
        window._xtc_page_qimage_cache = OrderedDict()


def _clear_device_preview_page_qimage_cache(window: Any) -> None:
    cache = window.__dict__.get('_device_preview_page_qimage_cache')
    if isinstance(cache, OrderedDict):
        cache.clear()
    else:
        window._device_preview_page_qimage_cache = OrderedDict()


def _device_preview_page_qimage_cache_key(window: Any, index: object = None) -> tuple[int, int] | None:
    if window._effective_device_view_source(window.__dict__.get('device_view_source', 'xtc')) != 'preview':
        return None
    pages = window._runtime_device_preview_pages()
    if not pages:
        return None
    current_index = window._normalized_device_preview_page_index(
        window.__dict__.get('current_device_preview_page_index', 0) if index is None else index,
        total=len(pages),
    )
    tokens = window.__dict__.get('_device_preview_page_cache_tokens')
    if not isinstance(tokens, list) or len(tokens) != len(pages):
        window._rebuild_preview_page_cache_tokens()
        tokens = window.__dict__.get('_device_preview_page_cache_tokens', [])
    token = int(tokens[current_index]) if current_index < len(tokens) else window._preview_page_cache_token(pages[current_index])
    if token == 0:
        return None
    return (int(current_index), token)


def _cached_device_preview_page_qimage(window: Any, key: object) -> object | None:
    if key is None:
        return None
    cache = window.__dict__.get('_device_preview_page_qimage_cache')
    if not isinstance(cache, OrderedDict):
        cache = OrderedDict()
        window._device_preview_page_qimage_cache = cache
    image = cache.get(key)
    if image is not None:
        cache.move_to_end(key)
    return image


def _store_device_preview_page_qimage(window: Any, key: object, image: object, *, cache_limit: int) -> None:
    if key is None or image is None:
        return
    cache = window.__dict__.get('_device_preview_page_qimage_cache')
    if not isinstance(cache, OrderedDict):
        cache = OrderedDict()
        window._device_preview_page_qimage_cache = cache
    cache[key] = image
    cache.move_to_end(key)
    while len(cache) > cache_limit:
        cache.popitem(last=False)


def _xtc_page_qimage_cache_key(window: Any, index: object = None) -> tuple[int, int, int] | None:
    if window._effective_device_view_source(window.__dict__.get('device_view_source', 'xtc')) != 'xtc':
        return None
    payload = window._xtc_page_state_payload(index)
    page = payload.get('page')
    if page is None:
        return None
    current_index = worker_logic._int_config_value(payload, 'current_index', 0)
    offset = max(0, worker_logic._int_config_value({'value': getattr(page, 'offset', 0)}, 'value', 0))
    length = max(0, worker_logic._int_config_value({'value': getattr(page, 'length', 0)}, 'value', 0))
    return (current_index, offset, length)


def _cached_xtc_page_qimage(window: Any, key: object) -> object | None:
    if not isinstance(key, tuple):
        return None
    cache = window.__dict__.get('_xtc_page_qimage_cache')
    if not isinstance(cache, OrderedDict):
        cache = OrderedDict()
        window._xtc_page_qimage_cache = cache
    image = cache.get(key)
    if image is not None:
        cache.move_to_end(key)
    return image


def _store_xtc_page_qimage(window: Any, key: object, image: object, *, cache_limit: int) -> None:
    if not isinstance(key, tuple) or image is None:
        return
    cache = window.__dict__.get('_xtc_page_qimage_cache')
    if not isinstance(cache, OrderedDict):
        cache = OrderedDict()
        window._xtc_page_qimage_cache = cache
    cache[key] = image
    cache.move_to_end(key)
    while len(cache) > cache_limit:
        cache.popitem(last=False)
