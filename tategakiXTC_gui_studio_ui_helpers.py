from __future__ import annotations

"""Small UI helper functions shared by the GUI Studio entry module.

This module intentionally does not import ``tategakiXTC_gui_studio``.  The
entry module re-exports the helpers so existing tests and monkey patches that
refer to ``import tategakiXTC_gui_studio as studio`` keep working.
"""

from contextlib import contextmanager
import logging
import os

from PySide6.QtCore import Qt

_APP_LOGGER_NAME = 'tategaki_xtc'


@contextmanager
def _bulk_block_signals(*widgets: object):
    active: list[tuple[object, bool]] = []
    for widget in widgets:
        if widget is None:
            continue
        blocker = getattr(widget, 'blockSignals', None)
        if not callable(blocker):
            continue
        previous_state = False
        getter = getattr(widget, 'signalsBlocked', None)
        if callable(getter):
            try:
                previous_state = bool(getter())
            except Exception:
                previous_state = False
        try:
            returned = blocker(True)
            if not callable(getter) and isinstance(returned, bool):
                previous_state = returned
            active.append((widget, previous_state))
        except Exception:
            continue
    try:
        yield
    finally:
        for widget, previous_state in reversed(active):
            try:
                widget.blockSignals(previous_state)
            except Exception:
                pass


def _coerce_ui_message_text(value: object, default: str = '') -> str:
    if value is None:
        text = ''
    elif isinstance(value, os.PathLike):
        text = os.fspath(value)
    elif isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        text = os.fsdecode(raw) if raw else ''
    else:
        text = str(value)
    return text if text.strip() else default


def _connect_signal_best_effort(signal: object, callback: object, *, queued: bool = False) -> bool:
    """Connect a Qt signal while tolerating lightweight test stubs.

    Worker signals can be emitted from a background thread.  For real Qt
    objects we request a queued connection so UI updates always run on the
    main-window thread.  The small unit-test stubs only accept
    ``connect(callback)``, so this helper falls back gracefully.
    """
    connect = getattr(signal, 'connect', None)
    if not callable(connect):
        return False
    if queued:
        queued_connection = getattr(Qt, 'QueuedConnection', None)
        if queued_connection is not None:
            try:
                connect(callback, queued_connection)
                return True
            except TypeError:
                pass
            except Exception:
                pass
    try:
        connect(callback)
        return True
    except Exception:
        return False


def _safe_delete_qobject_later(obj: object, *, context: str = '') -> bool:
    """Qt wrapper が既に破棄済みでも終了処理を落とさず deleteLater する。"""
    if obj is None:
        return False
    try:
        delete_later = getattr(obj, 'deleteLater', None)
    except RuntimeError:
        # PySide6: C++ 側で既に破棄された QObject wrapper に触ると RuntimeError になる。
        return False
    except Exception:
        return False
    if not callable(delete_later):
        return False
    try:
        delete_later()
        return True
    except RuntimeError:
        return False
    except Exception:
        if context:
            try:
                logging.getLogger(_APP_LOGGER_NAME).exception('%s の deleteLater に失敗しました', context)
            except Exception:
                pass
        return False
