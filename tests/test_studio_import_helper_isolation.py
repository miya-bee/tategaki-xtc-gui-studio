from __future__ import annotations

import sys
from types import ModuleType

from tests.studio_import_helper import load_studio_module, restore_qt_test_state


def test_load_studio_module_uses_pyside6_test_stubs_by_default() -> None:
    studio = load_studio_module(force_reload=True)
    assert getattr(sys.modules['PySide6'], '__tategaki_test_stub__', False)
    assert getattr(sys.modules['PySide6.QtCore'], '__tategaki_test_stub__', False)
    assert getattr(studio.QTimer, '__mro__', None) is not None


def test_load_studio_module_replaces_cached_real_like_pyside6_modules() -> None:
    fake_pyside6 = ModuleType('PySide6')
    fake_qtcore = ModuleType('PySide6.QtCore')
    fake_qtcore.QTimer = type('RealLikeQTimer', (), {'singleShot': staticmethod(lambda delay, callback: None)})
    fake_qtgui = ModuleType('PySide6.QtGui')
    fake_qtwidgets = ModuleType('PySide6.QtWidgets')
    sys.modules['PySide6'] = fake_pyside6
    sys.modules['PySide6.QtCore'] = fake_qtcore
    sys.modules['PySide6.QtGui'] = fake_qtgui
    sys.modules['PySide6.QtWidgets'] = fake_qtwidgets

    studio = load_studio_module(force_reload=True)

    assert getattr(sys.modules['PySide6'], '__tategaki_test_stub__', False)
    assert getattr(sys.modules['PySide6.QtCore'], '__tategaki_test_stub__', False)
    assert studio.QTimer.__name__ == 'QTimer'


def test_force_reload_restores_qtimer_single_shot_after_mutation() -> None:
    studio = load_studio_module(force_reload=True)
    widgets = sys.modules['tategakiXTC_gui_studio_widgets']
    original_single_shot = getattr(studio.QTimer, 'singleShot', None)

    def dirty_single_shot(_delay, _callback):
        raise AssertionError('stale QTimer.singleShot leaked between tests')

    studio.QTimer.singleShot = dirty_single_shot
    widgets.QTimer.singleShot = dirty_single_shot

    fresh = load_studio_module(force_reload=True)
    fresh_widgets = sys.modules['tategakiXTC_gui_studio_widgets']

    assert fresh is not studio
    assert fresh_widgets is not widgets
    assert getattr(fresh.QTimer, 'singleShot', None) is not dirty_single_shot
    assert getattr(fresh_widgets.QTimer, 'singleShot', None) is not dirty_single_shot
    assert getattr(fresh.QTimer, 'singleShot', None) is original_single_shot


def test_restore_qt_test_state_restores_qtimer_without_reloading_modules() -> None:
    studio = load_studio_module(force_reload=True)
    original_single_shot = getattr(studio.QTimer, 'singleShot', None)

    def dirty_single_shot(_delay, _callback):
        raise AssertionError('stale QTimer.singleShot leaked between tests')

    studio.QTimer.singleShot = dirty_single_shot
    assert getattr(studio.QTimer, 'singleShot', None) is dirty_single_shot

    restore_qt_test_state()

    assert getattr(studio.QTimer, 'singleShot', None) is original_single_shot
