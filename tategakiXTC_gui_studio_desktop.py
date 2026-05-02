from __future__ import annotations

"""Desktop/runtime helpers for the GUI Studio entry module.

This module intentionally does not import ``tategakiXTC_gui_studio`` so that
``MainWindow`` can re-export these helpers without introducing circular imports.
"""

import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

import tategakiXTC_worker_logic as worker_logic

_APP_LOGGER_NAME = 'tategaki_xtc'


def _coerce_desktop_message_text(value: object, default: str = '') -> str:
    text = worker_logic._coerce_path_text(value)
    return text if text.strip() else default


def _open_path_in_file_manager(path: Path | str) -> bool:
    logger = logging.getLogger(_APP_LOGGER_NAME)
    target = _coerce_desktop_message_text(path).strip()
    platform_name = _coerce_desktop_message_text(sys.platform).strip() or 'unknown'
    if not target:
        logger.warning('開く対象パスが空のため、ファイルマネージャを起動しませんでした (%s)。', platform_name)
        return False
    try:
        if sys.platform.startswith('win'):
            if not Path(target).exists():
                logger.warning('パスを開けませんでした (%s, %s): 対象が存在しません。', platform_name, target)
                return False
            startfile = getattr(os, 'startfile', None)
            if startfile is None:
                logger.warning('パスを開けませんでした (%s, %s): os.startfile が利用できません。', platform_name, target)
                return False
            startfile(target)
            return True
        if sys.platform == 'darwin':
            opener = 'open'
            if not shutil.which(opener):
                logger.warning('パスを開けませんでした (%s, %s): %s が見つかりません。', platform_name, target, opener)
                return False
            subprocess.Popen([opener, target])
            return True
        if sys.platform.startswith('linux'):
            opener = 'xdg-open'
            if not shutil.which(opener):
                logger.warning('パスを開けませんでした (%s, %s): %s が見つかりません。', platform_name, target, opener)
                return False
            subprocess.Popen([opener, target])
            return True
        logger.warning('パスを開けませんでした (%s, %s): 未対応のプラットフォームです。', platform_name, target)
    except Exception as exc:
        error_name = type(exc).__name__
        error_text = _coerce_desktop_message_text(exc).strip()
        if error_text:
            logger.exception('パスを開けませんでした (%s, %s): %s [%s]', platform_name, target, error_text, error_name)
        else:
            logger.exception('パスを開けませんでした (%s, %s): %s', platform_name, target, error_name)
    return False
