from __future__ import annotations

import importlib
import sys
from types import ModuleType
from typing import Any


class _BoundSignal:
    def __init__(self) -> None:
        self._callbacks: list[Any] = []
        self.emissions: list[tuple[Any, ...]] = []

    def connect(self, callback: Any) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: Any) -> None:
        self.emissions.append(args)
        for callback in list(self._callbacks):
            callback(*args)


class _SignalDescriptor:
    def __set_name__(self, owner: type, name: str) -> None:
        self._storage_name = f'__signal_{name}'

    def __get__(self, instance: Any, owner: type | None = None) -> Any:
        if instance is None:
            return self
        bound = instance.__dict__.get(self._storage_name)
        if bound is None:
            bound = _BoundSignal()
            instance.__dict__[self._storage_name] = bound
        return bound


class _QtDummy:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def __call__(self, *args: Any, **kwargs: Any) -> '_QtDummy':
        return self

    def __getattr__(self, name: str) -> Any:
        return _QtDummy()

    def __bool__(self) -> bool:
        return False

    def __iter__(self):
        return iter(())

    def __int__(self) -> int:
        return 0

    def __lt__(self, _other: Any) -> bool:
        return False

    def __le__(self, _other: Any) -> bool:
        return False

    def __gt__(self, _other: Any) -> bool:
        return False

    def __ge__(self, _other: Any) -> bool:
        return False


class _QObject:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


class _QSettings:
    IniFormat = 1

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def value(self, _key: str, default: Any = None, type: Any = None) -> Any:
        return default

    def setValue(self, _key: str, _value: Any) -> None:
        return None

    def sync(self) -> None:
        return None


class _QSize:
    def __init__(self, width: int = 0, height: int = 0) -> None:
        self._width = width
        self._height = height

    def width(self) -> int:
        return self._width

    def height(self) -> int:
        return self._height


class _QRectF(_QtDummy):
    pass


class _QPoint(_QtDummy):
    pass


class _QtNamespace:
    AlignBottom = 1
    AlignCenter = 2
    AlignHCenter = 4
    AlignTop = 8
    DashLine = 16
    Horizontal = 32
    KeepAspectRatio = 64
    Key_Left = 65
    Key_Right = 66
    NoFocus = 128
    OtherFocusReason = 256
    ScrollBarAlwaysOff = 512
    ShortcutFocusReason = 1024
    SmoothTransformation = 2048
    StrongFocus = 4096
    TextWordWrap = 8192
    UserRole = 16384
    Vertical = 32768


class _QImage(_QtDummy):
    pass


class _QPixmap(_QtDummy):
    @classmethod
    def fromImage(cls, _image: Any) -> '_QPixmap':
        return cls()


class _QApplication(_QtDummy):
    _instance: '_QApplication | None' = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _QApplication._instance = self

    @staticmethod
    def instance() -> '_QApplication | None':
        return _QApplication._instance

    @staticmethod
    def primaryScreen() -> None:
        return None


class _QMainWindow(_QtDummy):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._window_title = ''

    def setWindowTitle(self, title: str) -> None:
        self._window_title = title

    def windowTitle(self) -> str:
        return self._window_title

    def close(self) -> None:
        return None


class _QMessageBox(_QtDummy):
    @staticmethod
    def warning(*args: Any, **kwargs: Any) -> None:
        return None


_PYSIDE6_STUB_MODULE_NAMES = (
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
)


def _pyside6_modules_are_test_stubs() -> bool:
    module = sys.modules.get('PySide6')
    return bool(getattr(module, '__tategaki_test_stub__', False))


def _remove_pyside6_modules() -> None:
    for name in _PYSIDE6_STUB_MODULE_NAMES:
        sys.modules.pop(name, None)


def _remove_pyside6_test_stubs() -> None:
    if _pyside6_modules_are_test_stubs():
        _remove_pyside6_modules()


def remove_pyside6_test_stubs_for_real_qt() -> None:
    """Remove test stubs before optional smoke tests import real PySide6.

    Unit tests loaded through :func:`load_studio_module` intentionally prefer
    lightweight stubs even on developer machines that have PySide6 installed.
    Optional smoke tests that construct a real ``QApplication`` must opt out
    explicitly and start from a clean module cache.
    """
    restore_qt_test_state()
    _remove_tategaki_qt_bound_modules()
    _remove_pyside6_test_stubs()


def _install_pyside6_stubs(force_reset: bool = False, prefer_test_stubs: bool = True) -> None:
    if force_reset or (prefer_test_stubs and not _pyside6_modules_are_test_stubs()):
        _remove_pyside6_modules()
    if 'PySide6' in sys.modules:
        return

    pyside6 = ModuleType('PySide6')
    qtcore = ModuleType('PySide6.QtCore')
    qtgui = ModuleType('PySide6.QtGui')
    qtwidgets = ModuleType('PySide6.QtWidgets')

    qtcore.Qt = _QtNamespace
    qtcore.QObject = _QObject
    qtcore.QThread = type('QThread', (_QtDummy,), {})
    qtcore.Signal = lambda *args, **kwargs: _SignalDescriptor()
    qtcore.QSize = _QSize
    qtcore.QSettings = _QSettings
    qtcore.QRect = _QRectF
    qtcore.QRectF = _QRectF
    qtcore.QTimer = type('QTimer', (_QtDummy,), {})
    qtcore.QEvent = type('QEvent', (_QtDummy,), {})
    qtcore.QPoint = _QPoint

    qtgui.QActionGroup = type('QActionGroup', (_QtDummy,), {})
    qtgui.QColor = type('QColor', (_QtDummy,), {})
    qtgui.QFont = type('QFont', (_QtDummy,), {})
    qtgui.QImage = _QImage
    qtgui.QPainter = type('QPainter', (_QtDummy,), {'Antialiasing': 1})
    qtgui.QPainterPath = type('QPainterPath', (_QtDummy,), {})
    qtgui.QPen = type('QPen', (_QtDummy,), {})
    qtgui.QPixmap = _QPixmap
    qtgui.QPolygon = type('QPolygon', (_QtDummy,), {})

    qtwidgets.QApplication = _QApplication
    for name in [
        'QCheckBox', 'QComboBox', 'QDialog', 'QFileDialog', 'QFrame', 'QGridLayout',
        'QGroupBox', 'QHBoxLayout', 'QInputDialog', 'QLabel', 'QLineEdit',
        'QListWidgetItem', 'QMenu', 'QPushButton',
        'QProgressBar', 'QScrollArea', 'QScrollBar', 'QSplitter', 'QStackedWidget',
        'QStyle', 'QStyleOptionSpinBox', 'QTabWidget', 'QTextEdit', 'QVBoxLayout',
        'QWidget'
    ]:
        setattr(qtwidgets, name, type(name, (_QtDummy,), {}))
    qtwidgets.QMainWindow = _QMainWindow
    qtwidgets.QListWidget = type('QListWidget', (_QtDummy,), {
        'SingleSelection': 1,
        'MultiSelection': 2,
        'ExtendedSelection': 3,
        'NoSelection': 4,
    })
    qtwidgets.QSpinBox = type('QSpinBox', (_QtDummy,), {
        'UpDownArrows': 1,
        'NoButtons': 2,
    })
    qtwidgets.QMessageBox = _QMessageBox

    pyside6.QtCore = qtcore
    pyside6.QtGui = qtgui
    pyside6.QtWidgets = qtwidgets

    for module in (pyside6, qtcore, qtgui, qtwidgets):
        module.__tategaki_test_stub__ = True

    sys.modules['PySide6'] = pyside6
    sys.modules['PySide6.QtCore'] = qtcore
    sys.modules['PySide6.QtGui'] = qtgui
    sys.modules['PySide6.QtWidgets'] = qtwidgets



_TATEGAKI_QT_BOUND_MODULE_NAMES = (
    'tategakiXTC_gui_studio',
    'tategakiXTC_gui_studio_ui_helpers',
    'tategakiXTC_gui_studio_widgets',
    'tategakiXTC_gui_studio_worker',
    'tategakiXTC_gui_studio_xtc_io',
    'tategakiXTC_folder_batch_dialog',
)


def _remove_tategaki_qt_bound_modules() -> None:
    for name in _TATEGAKI_QT_BOUND_MODULE_NAMES:
        sys.modules.pop(name, None)


_QTIMER_SINGLESHOT_SENTINEL = object()
_QTIMER_BASELINE_SINGLESHOT_BY_CLASS: dict[type, Any] = {}


def _iter_loaded_qtimer_classes():
    """Yield currently loaded QTimer class objects without importing PySide6.

    Real PySide6 exposes QTimer as one process-global class object.  Tests that
    assign to ``QTimer.singleShot`` therefore mutate a shared class, and
    ``importlib.reload(tategakiXTC_gui_studio)`` cannot undo that mutation.  The
    helper keeps a per-class baseline so force_reload and an autouse fixture can
    restore the class explicitly in both real-PySide6 and stub environments.
    """
    seen: set[int] = set()
    module_names = ('PySide6.QtCore',) + _TATEGAKI_QT_BOUND_MODULE_NAMES
    for module_name in module_names:
        module = sys.modules.get(module_name)
        qtimer = getattr(module, 'QTimer', None) if module is not None else None
        if isinstance(qtimer, type) and id(qtimer) not in seen:
            seen.add(id(qtimer))
            yield qtimer


def _capture_qtimer_single_shot_baselines() -> None:
    for qtimer in _iter_loaded_qtimer_classes():
        if qtimer not in _QTIMER_BASELINE_SINGLESHOT_BY_CLASS:
            _QTIMER_BASELINE_SINGLESHOT_BY_CLASS[qtimer] = getattr(
                qtimer,
                'singleShot',
                _QTIMER_SINGLESHOT_SENTINEL,
            )


def restore_qt_test_state() -> None:
    """Restore mutable Qt class-level state touched by GUI tests.

    This is intentionally explicit rather than relying on module reloads.  In a
    real PySide6 environment the Qt modules remain cached and return the same
    C++ wrapper class objects, so class-level monkey patches can leak across
    tests unless we save and restore them ourselves.
    """
    _capture_qtimer_single_shot_baselines()
    for qtimer, original in list(_QTIMER_BASELINE_SINGLESHOT_BY_CLASS.items()):
        if original is _QTIMER_SINGLESHOT_SENTINEL:
            if hasattr(qtimer, 'singleShot'):
                try:
                    delattr(qtimer, 'singleShot')
                except (AttributeError, TypeError):
                    pass
        else:
            try:
                setattr(qtimer, 'singleShot', original)
            except (AttributeError, TypeError):
                pass

def _install_pillow_stub() -> None:
    if 'PIL' in sys.modules:
        return
    try:
        importlib.import_module('PIL')
        return
    except Exception:
        pass
    pillow = ModuleType('PIL')
    pillow.__path__ = []  # mark as package-like for submodule imports used by lazy paths
    sys.modules['PIL'] = pillow


def load_studio_module(force_reload: bool = False, *, use_test_stubs: bool = True):
    if force_reload or use_test_stubs:
        restore_qt_test_state()
        _remove_tategaki_qt_bound_modules()
    if use_test_stubs:
        _install_pyside6_stubs(force_reset=force_reload, prefer_test_stubs=True)
    else:
        _remove_pyside6_test_stubs()
    _install_pillow_stub()
    module = importlib.import_module('tategakiXTC_gui_studio')
    _capture_qtimer_single_shot_baselines()
    return module
