"""
tategakiXTC_gui_studio_startup.py — GUI startup dependency helpers

PySide6 の読み込み前に行う起動依存チェックだけを、GUI 本体から
切り出した小さな helper。Qt / Pillow / numpy は import しない。
"""
from __future__ import annotations

import ctypes
import sys
from collections.abc import Sequence

StartupDependency = tuple[str, str]


def collect_missing_startup_dependencies(dependencies: Sequence[StartupDependency]) -> list[str]:
    """Return package names whose import targets are unavailable at startup."""
    missing = []
    for package_name, module_name in dependencies:
        try:
            __import__(module_name)
        except Exception:
            missing.append(package_name)
    return missing


def show_startup_dependency_alert(missing_packages: Sequence[str]) -> None:
    """Show or print a startup dependency error message."""
    install_line = 'pip install ' + ' '.join(missing_packages)
    message = (
        'アプリ起動に必要なライブラリが不足しているか、読み込みに失敗しました。\n\n'
        + '\n'.join(f'- {name}' for name in missing_packages)
        + '\n\nインストール例:\n'
        + install_line
        + '\nまたは\n'
        + 'pip install -r requirements.txt'
    )
    title = '起動に必要なライブラリ不足'
    if sys.platform.startswith('win'):
        try:
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
            return
        except Exception:
            pass
    print(f'{title}\n{message}', file=sys.stderr)


__all__ = [
    'StartupDependency',
    'collect_missing_startup_dependencies',
    'show_startup_dependency_alert',
]
