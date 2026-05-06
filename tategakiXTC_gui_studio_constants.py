from __future__ import annotations

"""Constants and preset definitions for tategakiXTC_gui_studio.

This module is intentionally Qt-free so it can be imported by tests and helper
tools without pulling in the GUI stack. Public names are re-exported from
``tategakiXTC_gui_studio`` for backward compatibility.
"""

from dataclasses import dataclass
from pathlib import Path

from tategakiXTC_release_metadata import (
    APP_VERSION,
    PREVIOUS_PUBLIC_VERSION,
    PUBLIC_VERSION,
    PUBLIC_VERSION_TAG,
    RELEASE_NOTES_FILE,
    RELEASE_VERIFY_ZIP_FILE_NAME,
    RELEASE_ZIP_FILE_NAME,
)

import tategakiXTC_gui_core as core

APP_BASE_NAME = '縦書きXTC Studio'
APP_NAME = f'{APP_BASE_NAME} {APP_VERSION}'
SETTINGS_SCHEMA_VERSION = 2
SETTINGS_FILE = Path(__file__).with_name('tategakiXTC_gui_studio.ini')
DEFAULT_WINDOW_WIDTH = 1600
DEFAULT_WINDOW_HEIGHT = 1000
DEFAULT_LEFT_PANEL_WIDTH = 620
DEFAULT_STARTUP_PRESET_KEY = 'preset_4'
DEFAULT_TOP_PATH_BUTTON_WIDTH = 128
DEFAULT_LEFT_SPLITTER_TOP = 760
DEFAULT_LEFT_SPLITTER_BOTTOM = 140
DEFAULT_PREVIEW_PAGE_LIMIT = 10
RESULT_TAB_INDEX = 0
LOG_TAB_INDEX = 1
SUPPORTED_INPUT_SUFFIXES = core.SUPPORTED_INPUT_SUFFIXES
UI_ASSETS_DIR = Path(__file__).resolve().parent / 'ui_assets'
SPIN_UP_ICON = (UI_ASSETS_DIR / 'spin_up.svg').as_posix()
SPIN_DOWN_ICON = (UI_ASSETS_DIR / 'spin_down.svg').as_posix()
SPIN_UP_ICON_DARK = (UI_ASSETS_DIR / 'spin_up_dark.svg').as_posix()
SPIN_DOWN_ICON_DARK = (UI_ASSETS_DIR / 'spin_down_dark.svg').as_posix()

TEXT_OR_MARKDOWN_LABEL = 'TXT / Markdown（簡易対応）'
FONT_REQUIRED_SUFFIXES = {'.epub', '.txt', '.md', '.markdown'}

DEFAULT_RENDER_SETTINGS: dict[str, object] = {
    'profile': 'x4',
    'width': 480,
    'height': 800,
    'font_file': 'NotoSansJP-SemiBold.ttf',
    'font_size': 26,
    'ruby_size': 12,
    'line_spacing': 44,
    'margin_t': 12,
    'margin_b': 14,
    'margin_r': 12,
    'margin_l': 12,
    'night_mode': False,
    'dither': False,
    'threshold': 128,
    'kinsoku_mode': 'standard',
    'punctuation_position_mode': 'standard',
    'ichi_position_mode': 'standard',
    'lower_closing_bracket_position_mode': 'standard',
    'wave_dash_drawing_mode': 'rotate',
    'wave_dash_position_mode': 'standard',
    'output_format': 'xtc',
}

DEFAULT_UI_SETTINGS: dict[str, object] = {
    'actual_size': False,
    'show_guides': True,
    'calibration_pct': 100,
    'nav_buttons_reversed': False,
    'open_folder': True,
    'output_conflict': 'rename',
    'target': '',
    'main_view_mode': 'font',
    'bottom_tab_index': 0,
}

DEFAULT_SETTINGS_VALUES: dict[str, object] = {
    **DEFAULT_RENDER_SETTINGS,
    **DEFAULT_UI_SETTINGS,
}


@dataclass
class DeviceProfile:
    key: str
    name: str
    width_px: int
    height_px: int
    ppi: float
    body_w_mm: float
    body_h_mm: float
    screen_w_mm: float
    screen_h_mm: float
    accent: str
    tagline: str
    top_bezel_ratio: float = 0.34


DEVICE_PROFILES = {
    'x4': DeviceProfile(
        key='x4', name='Xteink X4', width_px=480, height_px=800, ppi=220.0,
        body_w_mm=69.0, body_h_mm=114.0, screen_w_mm=55.42, screen_h_mm=92.36,
        accent='#5DA9FF', tagline='', top_bezel_ratio=0.34,
    ),
    'x3': DeviceProfile(
        # X3 の解像度は横 528px × 縦 792px（ユーザー指定）
        # 画面寸法は解像度と 252ppi に整合する値を使う。
        key='x3', name='Xteink X3', width_px=528, height_px=792, ppi=252.0,
        body_w_mm=64.0, body_h_mm=98.0, screen_w_mm=53.21904761904762, screen_h_mm=79.82857142857142,
        accent='#9B80FF', tagline='', top_bezel_ratio=0.28,
    ),
    'custom': DeviceProfile(
        key='custom', name='Custom', width_px=480, height_px=800, ppi=220.0,
        body_w_mm=69.0, body_h_mm=114.0, screen_w_mm=55.42, screen_h_mm=92.36,
        accent='#38C172', tagline='任意サイズで確認', top_bezel_ratio=0.34,
    ),
}


# ─────────────────────────────────────────────────────────
# プリセット定義
# ─────────────────────────────────────────────────────────

def _make_preset(n: int, font_size: int = 20, ruby_size: int = 11, line_spacing: int = 35) -> dict:
    """プリセット辞書を生成するファクトリ関数。"""
    return {
        'button_text': f'プリセット{n}',
        'name': f'プリセット{n}',
        **DEFAULT_RENDER_SETTINGS,
        'font_size': font_size,
        'ruby_size': ruby_size,
        'line_spacing': line_spacing,
    }


DEFAULT_PRESET_DEFINITIONS = {
    'preset_1':  _make_preset(1,  font_size=20, ruby_size=11, line_spacing=35),
    'preset_2':  _make_preset(2,  font_size=22, ruby_size=11, line_spacing=37),
    'preset_3':  _make_preset(3,  font_size=24, ruby_size=12, line_spacing=41),
    'preset_4':  _make_preset(4,  font_size=26, ruby_size=12, line_spacing=41),
    'preset_5':  _make_preset(5,  font_size=27, ruby_size=12, line_spacing=41),
    'preset_6':  _make_preset(6,  font_size=28, ruby_size=12, line_spacing=44),
    'preset_7':  _make_preset(7,  font_size=29, ruby_size=12, line_spacing=44),
    'preset_8':  _make_preset(8,  font_size=30, ruby_size=13, line_spacing=44),
    'preset_9':  _make_preset(9,  font_size=31, ruby_size=13, line_spacing=44),
    'preset_10': _make_preset(10, font_size=32, ruby_size=13, line_spacing=44),
}

PRESET_FIELDS = [
    'profile', 'width', 'height', 'font_file',
    'font_size', 'ruby_size', 'line_spacing',
    'margin_t', 'margin_b', 'margin_r', 'margin_l',
    'night_mode', 'dither', 'threshold', 'kinsoku_mode',
    'punctuation_position_mode', 'ichi_position_mode', 'lower_closing_bracket_position_mode',
    'wave_dash_drawing_mode', 'wave_dash_position_mode', 'output_format',
]

KINSOKU_MODE_OPTIONS = [
    ('off', 'オフ'),
    ('simple', '簡易'),
    ('standard', '標準'),
]
KINSOKU_MODE_LABELS = {key: label for key, label in KINSOKU_MODE_OPTIONS}
GLYPH_POSITION_MODE_OPTIONS = [
    ('down_strong', '下補正 強'),
    ('down_weak', '下補正 弱'),
    ('standard', '標準'),
    ('up_weak', '上補正 弱'),
    ('up_strong', '上補正 強'),
]
GLYPH_POSITION_MODE_LABELS = {key: label for key, label in GLYPH_POSITION_MODE_OPTIONS}
CLOSING_BRACKET_POSITION_MODE_OPTIONS = [
    ('up_strong', '上補正 強'),
    ('up_weak', '上補正 弱'),
    ('standard', '標準'),
]
CLOSING_BRACKET_POSITION_MODE_LABELS = {key: label for key, label in CLOSING_BRACKET_POSITION_MODE_OPTIONS}
WAVE_DASH_DRAWING_MODE_OPTIONS = [
    ('rotate', '回転グリフ'),
    ('separate', '別描画'),
]
WAVE_DASH_DRAWING_MODE_LABELS = {key: label for key, label in WAVE_DASH_DRAWING_MODE_OPTIONS}
WAVE_DASH_POSITION_MODE_OPTIONS = [
    ('standard', '標準'),
    ('down_weak', '下補正弱'),
    ('down_strong', '下補正強'),
]
WAVE_DASH_POSITION_MODE_LABELS = {key: label for key, label in WAVE_DASH_POSITION_MODE_OPTIONS}

OUTPUT_FORMAT_OPTIONS = [
    ('xtc', 'XTC'),
    ('xtch', 'XTCH'),
]
OUTPUT_FORMAT_LABELS = {key: label for key, label in OUTPUT_FORMAT_OPTIONS}
OUTPUT_CONFLICT_OPTIONS = [
    ('rename', '自動連番で保存'),
    ('overwrite', '同名なら上書き'),
    ('error', '同名ならエラー'),
]
OUTPUT_CONFLICT_LABELS = {key: label for key, label in OUTPUT_CONFLICT_OPTIONS}


__all__ = [
    'APP_BASE_NAME',
    'APP_VERSION',
    'APP_NAME',
    'PUBLIC_VERSION',
    'PREVIOUS_PUBLIC_VERSION',
    'PUBLIC_VERSION_TAG',
    'RELEASE_NOTES_FILE',
    'RELEASE_ZIP_FILE_NAME',
    'RELEASE_VERIFY_ZIP_FILE_NAME',
    'SETTINGS_SCHEMA_VERSION',
    'SETTINGS_FILE',
    'DEFAULT_WINDOW_WIDTH',
    'DEFAULT_WINDOW_HEIGHT',
    'DEFAULT_LEFT_PANEL_WIDTH',
    'DEFAULT_STARTUP_PRESET_KEY',
    'DEFAULT_TOP_PATH_BUTTON_WIDTH',
    'DEFAULT_LEFT_SPLITTER_TOP',
    'DEFAULT_LEFT_SPLITTER_BOTTOM',
    'DEFAULT_PREVIEW_PAGE_LIMIT',
    'RESULT_TAB_INDEX',
    'LOG_TAB_INDEX',
    'SUPPORTED_INPUT_SUFFIXES',
    'UI_ASSETS_DIR',
    'SPIN_UP_ICON',
    'SPIN_DOWN_ICON',
    'SPIN_UP_ICON_DARK',
    'SPIN_DOWN_ICON_DARK',
    'TEXT_OR_MARKDOWN_LABEL',
    'FONT_REQUIRED_SUFFIXES',
    'DEFAULT_RENDER_SETTINGS',
    'DEFAULT_UI_SETTINGS',
    'DEFAULT_SETTINGS_VALUES',
    'DeviceProfile',
    'DEVICE_PROFILES',
    '_make_preset',
    'DEFAULT_PRESET_DEFINITIONS',
    'PRESET_FIELDS',
    'KINSOKU_MODE_OPTIONS',
    'KINSOKU_MODE_LABELS',
    'GLYPH_POSITION_MODE_OPTIONS',
    'GLYPH_POSITION_MODE_LABELS',
    'CLOSING_BRACKET_POSITION_MODE_OPTIONS',
    'CLOSING_BRACKET_POSITION_MODE_LABELS',
    'WAVE_DASH_DRAWING_MODE_OPTIONS',
    'WAVE_DASH_DRAWING_MODE_LABELS',
    'WAVE_DASH_POSITION_MODE_OPTIONS',
    'WAVE_DASH_POSITION_MODE_LABELS',
    'OUTPUT_FORMAT_OPTIONS',
    'OUTPUT_FORMAT_LABELS',
    'OUTPUT_CONFLICT_OPTIONS',
    'OUTPUT_CONFLICT_LABELS',
]
