from __future__ import annotations

from pathlib import Path
from typing import Any

import tategakiXTC_gui_core as core


def current_font_value(self: Any) -> str:
    if not hasattr(self, 'font_combo'):
        return ''
    value = self.font_combo.currentData()
    if value in (None, ''):
        value = self.font_combo.currentText()
    fallback = self._default_font_name() if hasattr(self, '_default_font_name') else ''
    normalized = self._normalize_font_setting_value(value, fallback)
    return normalized or fallback or str(value or '').strip()


def _available_font_entries(self: Any) -> list[dict[str, str]]:
    fonts = []
    for entry in core.get_font_entries():
        path_value, _font_index = core.parse_font_spec(entry.get('value', ''))
        lower = str(path_value).lower()
        if any(t in lower for t in ('msgothic', 'msmincho', 'ms gothic', 'ms mincho')):
            continue
        fonts.append({'label': str(entry.get('label', '')), 'value': str(entry.get('value', ''))})

    def sort_key(entry: dict):
        path_value, font_index = core.parse_font_spec(entry.get('value', ''))
        base = Path(path_value).name.lower()
        label = str(entry.get('label', '')).lower()

        def weight_priority(text: str) -> int:
            if 'thin' in text or 'hairline' in text:
                return 0
            if 'extralight' in text or 'ultralight' in text or 'extra-light' in text or 'ultra-light' in text:
                return 1
            if 'light' in text:
                return 2
            if 'regular' in text or 'normal' in text or 'book' in text:
                return 3
            if 'medium' in text:
                return 4
            if 'demibold' in text or 'demi-bold' in text:
                return 5
            if 'semibold' in text or 'semi-bold' in text:
                return 6
            if 'bold' in text:
                return 7
            if 'extrabold' in text or 'ultrabold' in text or 'extra-bold' in text or 'ultra-bold' in text:
                return 8
            if 'black' in text or 'heavy' in text:
                return 9
            return 50

        family_key = base
        for token in (
            'hairline', 'thin', 'ultralight', 'ultra-light', 'extralight', 'extra-light',
            'light', 'regular', 'normal', 'book', 'medium', 'demibold', 'demi-bold',
            'semibold', 'semi-bold', 'bold', 'extrabold', 'extra-bold', 'ultrabold',
            'ultra-bold', 'black', 'heavy'
        ):
            family_key = family_key.replace(token, '')
        family_key = family_key.replace('--', '-').replace('__', '_').replace('  ', ' ').strip(' -_')
        combined = f'{base} {label}'
        return (family_key or base, weight_priority(combined), base, label, int(font_index or 0))

    return sorted(fonts, key=sort_key)


def _populate_font_combo(self: Any) -> None:
    core.clear_font_entry_cache()
    self.font_combo.clear()
    for entry in self._available_font_entries():
        self.font_combo.addItem(entry['label'], entry['value'])


def _missing_font_combo_label(self: Any, font_value: str) -> str:
    path_value, _font_index = core.parse_font_spec(font_value)
    base_label = core.describe_font_value(font_value) or Path(path_value or font_value).name
    suffix = '（プリセット値 / 未検出）'
    if suffix in base_label:
        return base_label
    return f'{base_label}{suffix}'


def _ensure_font_combo_value(self: Any, font_value: str) -> None:
    font_value = core.build_font_spec(*core.parse_font_spec(font_value))
    if not font_value or not hasattr(self, 'font_combo'):
        return
    if self._combo_find_data_index(self.font_combo, font_value) >= 0:
        return
    added = False
    path_value, _font_index = core.parse_font_spec(font_value)
    candidate_entries = core.get_font_entries_for_value(path_value or font_value)
    exact_detected = False
    for entry in candidate_entries:
        value = str(entry.get('value', '')).strip()
        if not value:
            continue
        if value == font_value:
            exact_detected = True
        if self._combo_find_data_index(self.font_combo, value) >= 0:
            continue
        self.font_combo.addItem(str(entry.get('label', value)), value)
        added = True
    if self._combo_find_data_index(self.font_combo, font_value) < 0:
        label = self._missing_font_combo_label(font_value) if not exact_detected else (core.describe_font_value(font_value) or Path(path_value or font_value).name)
        self.font_combo.addItem(label, font_value)
    elif added:
        ordered_entries = self._available_font_entries()
        ordered_values = {entry['value'] for entry in ordered_entries}
        existing_values = {self.font_combo.itemData(i): self.font_combo.itemText(i) for i in range(self.font_combo.count())}
        self.font_combo.clear()
        for entry in ordered_entries:
            self.font_combo.addItem(entry['label'], entry['value'])
        for value, label in existing_values.items():
            if value not in ordered_values:
                self.font_combo.addItem(label, value)


def _set_current_font_value(self: Any, font_value: str) -> None:
    font_value = core.build_font_spec(*core.parse_font_spec(font_value))
    if not font_value or not hasattr(self, 'font_combo'):
        return
    preserved_night_mode = None
    if hasattr(self, 'night_check') and hasattr(self.night_check, 'isChecked'):
        try:
            preserved_night_mode = bool(self.night_check.isChecked())
        except Exception:
            preserved_night_mode = None
    self._ensure_font_combo_value(font_value)
    idx = self._combo_find_data_index(self.font_combo, font_value)
    if idx >= 0:
        self.font_combo.setCurrentIndex(idx)
        reset_popup_scroll = getattr(self.font_combo, '_reset_popup_scroll_to_top', None)
        if callable(reset_popup_scroll):
            reset_popup_scroll()
    if preserved_night_mode is not None and bool(self.night_check.isChecked()) != preserved_night_mode:
        self.night_check.setChecked(preserved_night_mode)


def _default_font_name(self: Any) -> str:
    preferred = ['NotoSansJP-SemiBold.ttf', 'NotoSansJP-SemiBold.otf', 'NotoSansJP-SemiBold.ttc']
    available = self._available_font_entries()
    for preferred_name in preferred:
        for entry in available:
            path_value, _font_index = core.parse_font_spec(entry['value'])
            base = Path(path_value).name
            label = entry['label'].lower()
            if base == preferred_name and (not preferred_name.lower().endswith('.ttc') or 'semibold' in label or 'semi-bold' in label):
                return entry['value']
    for entry in available:
        if 'semibold' in entry['label'].lower():
            return entry['value']
    return available[0]['value'] if available else ''


def _apply_default_font_selection(self: Any) -> None:
    name = self._default_font_name()
    if name:
        self._set_current_font_value(name)
