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


def _install_pyside6_stubs() -> None:
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

    sys.modules['PySide6'] = pyside6
    sys.modules['PySide6.QtCore'] = qtcore
    sys.modules['PySide6.QtGui'] = qtgui
    sys.modules['PySide6.QtWidgets'] = qtwidgets


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


def load_studio_module(force_reload: bool = False):
    _install_pyside6_stubs()
    _install_pillow_stub()
    if force_reload:
        sys.modules.pop('tategakiXTC_gui_studio', None)
    return importlib.import_module('tategakiXTC_gui_studio')
