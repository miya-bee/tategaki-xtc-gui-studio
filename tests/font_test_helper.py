from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


DEFAULT_TEST_FONT_CANDIDATES = (
    'NotoSansJP-Regular.ttf',
    'NotoSansJP-SemiBold.ttf',
    'NotoSansJP-Bold.ttf',
    'NotoSerifJP-Regular.ttf',
)


def resolve_test_font_spec(preferred: str = 'NotoSansJP-Regular.ttf') -> str:
    candidates = [preferred, *DEFAULT_TEST_FONT_CANDIDATES]
    seen: set[str] = set()
    for candidate in candidates:
        spec = core.build_font_spec(*core.parse_font_spec(candidate))
        if not spec or spec in seen:
            continue
        seen.add(spec)
        path = core.resolve_font_path(spec)
        if path and path.exists() and path.is_file():
            return spec
    for entry in core.get_font_entries():
        value = str(entry.get('value', '')).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        path = core.resolve_font_path(value)
        if path and path.exists() and path.is_file():
            return value
    raise RuntimeError('テストで利用可能なフォントが見つかりません。')


def resolve_test_font_path(preferred: str = 'NotoSansJP-Regular.ttf') -> Path:
    return core.require_font_path(resolve_test_font_spec(preferred))


def has_bundled_reference_font() -> bool:
    return (ROOT / 'Font' / 'NotoSansJP-Regular.ttf').exists()
