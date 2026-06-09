from __future__ import annotations

"""Small preset-related helpers split out from the GUI entry module."""

import re
from typing import Any

import tategakiXTC_gui_studio_logic as studio_logic


def selected_preset_key_from_combo(combo: object) -> str | None:
    """Return the selected preset key from a QComboBox-like object."""
    if combo is None:
        return None
    current_data = getattr(combo, 'currentData', None)
    if callable(current_data):
        try:
            key = current_data()
        except Exception:
            key = None
        if key:
            return str(key)

    current_index = getattr(combo, 'currentIndex', None)
    item_data = getattr(combo, 'itemData', None)
    item_text = getattr(combo, 'itemText', None)
    if not callable(current_index):
        return None
    try:
        index = int(current_index())
    except Exception:
        return None
    if index < 0:
        return None

    if callable(item_data):
        try:
            data = item_data(index)
        except Exception:
            data = None
        if data:
            return str(data)

    if callable(item_text):
        try:
            text = str(item_text(index) or '').strip()
        except Exception:
            text = ''
        if text.startswith('プリセット'):
            suffix = text.replace('プリセット', '').strip()
            if suffix.isdigit():
                return f'preset_{suffix}'
    return None


def preset_combo_entries(combo: object) -> tuple[tuple[str, object], ...]:
    """Return (text, data) entries from a QComboBox-like object."""
    if combo is None or not hasattr(combo, 'count'):
        return ()
    count_getter = getattr(combo, 'count', None)
    if not callable(count_getter):
        return ()
    try:
        count = int(count_getter())
    except Exception:
        return ()
    entries: list[tuple[str, object]] = []
    item_text = getattr(combo, 'itemText', None)
    item_data = getattr(combo, 'itemData', None)
    for index in range(max(0, count)):
        try:
            text = item_text(index) if callable(item_text) else ''
        except Exception:
            text = ''
        try:
            data = item_data(index) if callable(item_data) else None
        except Exception:
            data = None
        entries.append((str(text or ''), data))
    return tuple(entries)


def preset_settings_prefix(key: str) -> str:
    return f'presets/{key}'


def preset_display_name_settings_key(key: str) -> str:
    return f'{preset_settings_prefix(key)}/display_name'


def normalize_preset_display_name(value: object, *, fallback: str) -> str:
    text = str(value or '').strip()
    return text or str(fallback or 'プリセット').strip() or 'プリセット'


_MARGIN_PATTERN = re.compile(
    r'^余白:\s*上\s*(?P<top>\S+)\s*下\s*(?P<bottom>\S+)\s*左\s*(?P<left>\S+)\s*右\s*(?P<right>\S+)\s*$'
)


def preset_side_summary_text(summary: object) -> str:
    """Return a taller, left-pane friendly preset specification summary."""
    lines: list[str] = []

    def _append_summary_part(part: str) -> None:
        margin_match = _MARGIN_PATTERN.match(part)
        if margin_match:
            lines.append(f'余白の上下: 上 {margin_match.group("top")} 下 {margin_match.group("bottom")}')
            lines.append(f'余白の左右: 左 {margin_match.group("left")} 右 {margin_match.group("right")}')
            return
        lines.append(part)

    for raw_line in str(summary or '').splitlines():
        text = raw_line.strip()
        if not text:
            continue
        parts = [part.strip() for part in text.split(' / ') if part.strip()]
        if len(parts) > 1:
            for part in parts:
                _append_summary_part(part)
        else:
            _append_summary_part(text)
    return studio_logic.compact_multiline_label_text('\n'.join(lines))


__all__ = [
    'normalize_preset_display_name',
    'preset_combo_entries',
    'preset_display_name_settings_key',
    'preset_settings_prefix',
    'preset_side_summary_text',
    'selected_preset_key_from_combo',
]
