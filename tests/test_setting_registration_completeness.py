from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import tategakiXTC_gui_core as core


SETTING_FILES = {
    'worker': Path('tategakiXTC_worker_logic.py'),
    'settings_save': Path('tategakiXTC_gui_studio_settings_save_helpers.py'),
    'settings_restore': Path('tategakiXTC_gui_studio_settings_restore_helpers.py'),
    'preset_payload': Path('tategakiXTC_gui_studio_preset_payload_helpers.py'),
    'preview_payload': Path('tategakiXTC_gui_preview_controller.py'),
    'preview_renderer': Path('tategakiXTC_gui_core_renderer.py'),
}

# These are persisted settings that intentionally do not appear in the renderer's
# font/layout cache tuple because they are handled by image post-processing or are
# not preview-renderer layout inputs.
PREVIEW_RENDERER_CACHE_EXEMPTIONS = {
    'night_mode',
}


def _mode_setting_names() -> list[str]:
    names: list[str] = []
    for field in fields(core.ConversionArgs):
        name = field.name
        if name.endswith('_position_mode') or name.endswith('_mode'):
            names.append(name)
    return names


def test_mode_settings_are_registered_across_save_restore_preset_worker_and_preview_paths() -> None:
    sources = {name: path.read_text(encoding='utf-8') for name, path in SETTING_FILES.items()}
    settings = _mode_setting_names()

    assert 'middle_dot_position_mode' in settings
    assert 'wave_dash_drawing_mode' in settings

    for setting in settings:
        for label in ('worker', 'settings_save', 'settings_restore', 'preset_payload', 'preview_payload'):
            assert setting in sources[label], f'{setting} is missing from {label}'
        assert f"'{setting}'" in sources['preview_payload'], f'{setting} is not emitted in build_preview_payload'
        assert f"'{setting}'" in sources['preview_renderer'], f'{setting} is not consumed by preview renderer'


def test_layout_mode_settings_are_included_in_preview_cache_key_and_args_construction() -> None:
    source = SETTING_FILES['preview_renderer'].read_text(encoding='utf-8')
    cache_start = source.index('def _preview_bundle_cache_key(')
    cache_end = source.index('\n\ndef clear_preview_bundle_cache', cache_start)
    cache_body = source[cache_start:cache_end]
    args_start = source.index('preview_args = ConversionArgs(')
    args_end = source.index('\n        )', args_start)
    args_body = source[args_start:args_end]

    for setting in _mode_setting_names():
        if setting in PREVIEW_RENDERER_CACHE_EXEMPTIONS:
            continue
        assert setting in cache_body, f'{setting} is missing from preview cache key'
        assert setting in args_body, f'{setting} is missing from preview ConversionArgs construction'
