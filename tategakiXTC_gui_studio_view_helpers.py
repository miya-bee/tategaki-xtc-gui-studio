from __future__ import annotations

"""View-mode helper functions for tategakiXTC GUI Studio.

This module keeps small, mostly pure view-mode text/normalization helpers out of
``tategakiXTC_gui_studio.py`` while preserving the entry module re-export API.
"""

import tategakiXTC_gui_layouts as gui_layouts
import tategakiXTC_gui_studio_logic as studio_logic


def _normalized_main_view_mode(mode: object) -> str:
    """Normalize a main-view mode value to ``font`` or ``device``."""
    return studio_logic.normalize_choice_value(mode, 'font', {'font', 'device'})


def _preview_view_help_text() -> str:
    """Return the help text shown for the preview/device view toggle."""
    toggle_plan = gui_layouts.build_view_toggle_bar_plan()
    return str(toggle_plan.get(
        'help_text',
        'フォントビュー: 文字サイズ・余白・ルビの見え方を調整するときに使います。\n'
        '実機ビュー: 変換後のXTCをページ送りしながら実機に近い形で確認します。',
    ))


def _main_view_mode_help_text(mode: object) -> str:
    """Return the help text for a main-view mode.

    ``mode`` is accepted for API symmetry with the MainWindow wrapper.
    """
    return _preview_view_help_text()


def _main_view_mode_status_text(mode: object) -> str:
    """Return the status-bar text for switching to a main-view mode."""
    normalized = _normalized_main_view_mode(mode)
    if normalized == 'font':
        return 'フォントビューに切り替えました。'
    return '実機ビューに切り替えました。'
