from __future__ import annotations

import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def _install_fake_pyside6(*, force: bool = False) -> None:
    """Install a tiny PySide6 stand-in for source-only CI environments.

    The project has many static regression tests that run without PySide6.  The
    behaviorized sweep368 tests only need lightweight widget state, so this fake
    keeps the tests executable in the source-only container while still running
    the real split helper functions.
    """

    class _Signal:
        def __init__(self, *args, **kwargs) -> None:
            self.callbacks: list[object] = []

        def connect(self, callback) -> None:
            self.callbacks.append(callback)

        def emit(self, *args, **kwargs) -> None:
            for callback in tuple(self.callbacks):
                callback(*args, **kwargs)

    class _Qt:
        AlignCenter = 0x0004
        AlignLeft = 0x0001
        AlignTop = 0x0020
        LeftToRight = 0
        NoFocus = 0
        StrongFocus = 11
        ScrollBarAlwaysOff = 1
        ScrollBarAlwaysOn = 2
        ScrollBarAsNeeded = 3
        class ScrollBarPolicy:
            ScrollBarAlwaysOff = 1
            ScrollBarAlwaysOn = 2
            ScrollBarAsNeeded = 3
        class AlignmentFlag:
            AlignCenter = 0x0004
            AlignLeft = 0x0001
            AlignTop = 0x0020
        class FocusPolicy:
            NoFocus = 0
            StrongFocus = 11

    class _Margins:
        def __init__(self, left=0, top=0, right=0, bottom=0) -> None:
            self._values = (left, top, right, bottom)
        def left(self): return self._values[0]
        def top(self): return self._values[1]
        def right(self): return self._values[2]
        def bottom(self): return self._values[3]

    class _Size:
        def __init__(self, width=0, height=0) -> None:
            self._width = int(width)
            self._height = int(height)
        def width(self): return self._width
        def height(self): return self._height

    class _Spacer:
        def __init__(self, width=0, height=0) -> None:
            self._size = _Size(width, height)
        def sizeHint(self): return self._size

    class _LayoutItem:
        def __init__(self, *, widget=None, layout=None, spacer=None) -> None:
            self._widget = widget
            self._layout = layout
            self._spacer = spacer
        def widget(self): return self._widget
        def layout(self): return self._layout
        def spacerItem(self): return self._spacer

    class _FakeWidget:
        HLine = 1
        NoFrame = 0
        UpDownArrows = 1
        NoButtons = 2
        def __init__(self, text='', *args, **kwargs) -> None:
            self._text = str(text) if text is not None else ''
            self._title = self._text
            self._object_name = ''
            self._tooltip = ''
            self._visible = True
            self._enabled = True
            self._layout = None
            self._width = 0
            self._height = 0
            self._minimum_height = 0
            self._maximum_height = 16777215
            self._frame_shape = self.NoFrame
            self.clicked = _Signal()
            self.toggled = _Signal()
            self.valueChanged = _Signal()
            self.currentIndexChanged = _Signal()
        def setObjectName(self, value): self._object_name = str(value)
        def objectName(self): return self._object_name
        def setToolTip(self, value): self._tooltip = str(value)
        def toolTip(self): return self._tooltip
        def setText(self, value): self._text = str(value)
        def text(self): return self._text
        def setVisible(self, value): self._visible = bool(value)
        def isVisible(self): return self._visible
        def setEnabled(self, value): self._enabled = bool(value)
        def isEnabled(self): return self._enabled
        def setChecked(self, value): self._checked = bool(value); self.toggled.emit(self._checked)
        def isChecked(self): return bool(getattr(self, '_checked', False))
        def setCheckable(self, value): self._checkable = bool(value)
        def isCheckable(self): return bool(getattr(self, '_checkable', False))
        def setTextVisible(self, value): self._text_visible = bool(value)
        def setFormat(self, value): self._format = str(value)
        def format(self): return getattr(self, '_format', '')
        def setRange(self, minimum, maximum): self._minimum = int(minimum); self._maximum = int(maximum)
        def minimum(self): return getattr(self, '_minimum', 0)
        def maximum(self): return getattr(self, '_maximum', 0)
        def setValue(self, value): self._value = int(value)
        def value(self): return getattr(self, '_value', 0)
        def setParent(self, parent): self._parent = parent
        def setAlignment(self, value): self._alignment = value
        def alignment(self): return getattr(self, '_alignment', None)
        def setWordWrap(self, value): self._word_wrap = bool(value)
        def setMinimumSize(self, width, height): self._minimum_size = _Size(width, height)
        def minimumSize(self): return getattr(self, '_minimum_size', _Size(0, 0))
        def setMinimumWidth(self, width): self._minimum_width = int(width)
        def setMaximumWidth(self, width): self._maximum_width = int(width)
        def setFixedWidth(self, width): self._width = int(width)
        def width(self): return self._width
        def setFixedHeight(self, height):
            self._height = int(height)
            self._minimum_height = int(height)
            self._maximum_height = int(height)
        def minimumHeight(self): return self._minimum_height
        def maximumHeight(self): return self._maximum_height
        def setFixedSize(self, width, height):
            self._width = int(width); self._height = int(height)
        def size(self): return _Size(self._width, self._height)
        def setFrameShape(self, shape): self._frame_shape = shape
        def frameShape(self): return self._frame_shape
        def setWidgetResizable(self, value): self._widget_resizable = bool(value)
        def setHorizontalScrollBarPolicy(self, value): self._horizontal_scroll_bar_policy = value
        def setVerticalScrollBarPolicy(self, value): self._vertical_scroll_bar_policy = value
        def setFocusPolicy(self, value): self._focus_policy = value
        def focusPolicy(self): return getattr(self, '_focus_policy', None)
        def setLayoutDirection(self, value): self._layout_direction = value
        def setWidget(self, widget): self._widget = widget
        def setLayout(self, layout): self._layout = layout
        def layout(self): return self._layout
        def title(self): return self._title
        def setTitle(self, value): self._title = str(value)
        def setProperty(self, name, value): setattr(self, f'_property_{name}', value)
        def addItem(self, *args, **kwargs): pass
        def addWidget(self, widget):
            widgets = getattr(self, '_stack_widgets', [])
            widgets.append(widget)
            self._stack_widgets = widgets
            return len(widgets) - 1
        def setCurrentIndex(self, index, *args, **kwargs): self._current_index = int(index)
        def currentIndex(self): return getattr(self, '_current_index', 0)
        def setCurrentText(self, *args, **kwargs): pass

    class _FakeLayout:
        def __init__(self, parent=None, *args, **kwargs) -> None:
            self._items: list[_LayoutItem] = []
            self._margins = _Margins()
            self._spacing = 0
            if parent is not None and hasattr(parent, 'setLayout'):
                parent.setLayout(self)
        def setContentsMargins(self, left, top, right, bottom): self._margins = _Margins(left, top, right, bottom)
        def contentsMargins(self): return self._margins
        def setSpacing(self, value): self._spacing = int(value)
        def spacing(self): return self._spacing
        def addWidget(self, widget, *args, **kwargs): self._items.append(_LayoutItem(widget=widget))
        def addLayout(self, layout, *args, **kwargs): self._items.append(_LayoutItem(layout=layout))
        def addSpacing(self, width): self._items.append(_LayoutItem(spacer=_Spacer(width, 0)))
        def addStretch(self, *args, **kwargs): self._items.append(_LayoutItem(spacer=_Spacer(0, 0)))
        def itemAt(self, index): return self._items[index]
        def count(self): return len(self._items)

    class _FakeSpinBox(_FakeWidget):
        UpDownArrows = 1
        NoButtons = 2
        def __init__(self, *args, **kwargs) -> None:
            super().__init__('', *args, **kwargs)
            self._minimum = 0; self._maximum = 99; self._value = 0
            self._single_step = 1; self._accelerated = False
            self._button_symbols = self.UpDownArrows
            self._suffix = ''
        def setRange(self, minimum, maximum): self._minimum = int(minimum); self._maximum = int(maximum)
        def minimum(self): return self._minimum
        def maximum(self): return self._maximum
        def setSingleStep(self, value): self._single_step = int(value)
        def singleStep(self): return self._single_step
        def setAccelerated(self, value): self._accelerated = bool(value)
        def isAccelerated(self): return self._accelerated
        def setButtonSymbols(self, value): self._button_symbols = value
        def buttonSymbols(self): return self._button_symbols
        def setKeyboardTracking(self, value): self._keyboard_tracking = bool(value)
        def keyboardTracking(self): return getattr(self, '_keyboard_tracking', True)
        def setValue(self, value): self._value = int(value); self.valueChanged.emit(self._value)
        def value(self): return self._value
        def setSuffix(self, value): self._suffix = str(value)
        def suffix(self): return self._suffix
        def stepBy(self, step): self.setValue(self._value + int(step))

    class _FakeApplication:
        _instance = None
        def __init__(self, *args, **kwargs) -> None:
            type(self)._instance = self
        @classmethod
        def instance(cls): return cls._instance

    class _FakeGeneric:
        def __init__(self, *args, **kwargs) -> None: pass
        def __call__(self, *args, **kwargs): return self

    if force:
        for module_name in ('PySide6', 'PySide6.QtCore', 'PySide6.QtWidgets', 'PySide6.QtGui'):
            sys.modules.pop(module_name, None)

    pyside = types.ModuleType('PySide6')
    qtcore = types.ModuleType('PySide6.QtCore')
    qtwidgets = types.ModuleType('PySide6.QtWidgets')
    qtgui = types.ModuleType('PySide6.QtGui')
    qtcore.Qt = _Qt
    qtcore.Signal = _Signal
    qtcore.__getattr__ = lambda name: _FakeGeneric
    widget_types = {
        'QApplication': _FakeApplication,
        'QFrame': _FakeWidget,
        'QGroupBox': _FakeWidget,
        'QHBoxLayout': _FakeLayout,
        'QLabel': _FakeWidget,
        'QPushButton': _FakeWidget,
        'QSpinBox': _FakeSpinBox,
        'QVBoxLayout': _FakeLayout,
        'QWidget': _FakeWidget,
    }
    qtwidgets.__getattr__ = lambda name: widget_types.get(name, _FakeWidget)
    qtgui.__getattr__ = lambda name: _FakeGeneric
    for module in (pyside, qtcore, qtwidgets, qtgui):
        module.__tategaki_test_stub__ = True
    sys.modules.setdefault('PySide6', pyside)
    sys.modules.setdefault('PySide6.QtCore', qtcore)
    sys.modules.setdefault('PySide6.QtWidgets', qtwidgets)
    sys.modules.setdefault('PySide6.QtGui', qtgui)

# Keep sweep368 behavior tests on lightweight recording stand-ins even when
# PySide6 is installed.  Mixing real shiboken objects with the local fake widget
# tree can abort the Python process before pytest can report a normal failure.
_install_fake_pyside6(force=True)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget




def _load_sweep_behavior_modules():
    """Load split helpers with the local rich Qt fake, without polluting other tests."""
    for module_name in (
        'tategakiXTC_gui_studio',
        'tategakiXTC_gui_studio_widgets',
        'tategakiXTC_gui_studio_settings_sections_helpers',
        'tategakiXTC_gui_studio_right_pane_build_helpers',
        'tategakiXTC_gui_studio_preview_zoom_helpers',
        'tategakiXTC_gui_studio_preview_controls_helpers',
        'tategakiXTC_gui_studio_navigation_helpers',
        'tategakiXTC_gui_studio_navigation_action_helpers',
    ):
        sys.modules.pop(module_name, None)
    _install_fake_pyside6(force=True)
    import importlib
    gui_layouts = importlib.import_module('tategakiXTC_gui_layouts')
    studio = importlib.import_module('tategakiXTC_gui_studio')
    preview_zoom_helpers = importlib.import_module('tategakiXTC_gui_studio_preview_zoom_helpers')
    right_pane_helpers = importlib.import_module('tategakiXTC_gui_studio_right_pane_build_helpers')
    settings_sections_helpers = importlib.import_module('tategakiXTC_gui_studio_settings_sections_helpers')
    return gui_layouts, studio, preview_zoom_helpers, right_pane_helpers, settings_sections_helpers



ROOT = Path(__file__).resolve().parents[1]
LAYOUTS_SOURCE = (ROOT / 'tategakiXTC_gui_layouts.py').read_text(encoding='utf-8')
SETTINGS_SECTIONS_HELPERS_SOURCE = (ROOT / 'tategakiXTC_gui_studio_settings_sections_helpers.py').read_text(encoding='utf-8')


def _ensure_qapplication() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _layout_margins_tuple(layout) -> tuple[int, int, int, int]:
    margins = layout.contentsMargins()
    return (margins.left(), margins.top(), margins.right(), margins.bottom())


class _SweepBehaviorWindow:
    """Minimal recording double that runs the real split helper functions.

    The sweep368 tests are regression contracts for layout-plan ownership.  They
    intentionally use local PySide6 stand-ins instead of real Qt widgets so a
    layout contract regression cannot become a shiboken hard-crash.
    """

    def __init__(self) -> None:
        _ensure_qapplication()
        self.help_texts: list[str] = []
        self.optional_widget_calls: list[str] = []
        self.legacy_calibration_syncs = 0
        self.actual_size = False
        self.preview_zoom_changed_values: list[int] = []

    def _localized_plan(self, payload_obj):
        return dict(payload_obj or {})

    def _ui_text(self, text: object) -> str:
        return str(text)

    def _plan_int_value(self, payload_obj: object, key: str, default: int) -> int:
        try:
            return int(dict(payload_obj or {}).get(key, default))
        except Exception:
            return int(default)

    def _plan_bool_value(self, payload_obj: object, key: str, default: bool) -> bool:
        value = dict(payload_obj or {}).get(key, default)
        if isinstance(value, str):
            return value.strip().lower() in {'1', 'true', 'yes', 'on'}
        return bool(value)

    def _plan_int_tuple_value(
        self,
        payload_obj: object,
        key: str,
        default: tuple[int, ...],
        *,
        expected_length: int | None = None,
    ) -> tuple[int, ...]:
        value = dict(payload_obj or {}).get(key, default)
        try:
            result = tuple(int(part) for part in value)
        except Exception:
            result = tuple(default)
        if expected_length is not None and len(result) != expected_length:
            return tuple(default)
        return result

    def _plan_token_value(self, payload_obj: object, key: str, default: str) -> str:
        value = dict(payload_obj or {}).get(key, default)
        return str(value or default).strip().lower().replace('-', '_')

    def _qframe_shape_constant(self, name: str, fallback: object = 0):
        return getattr(QFrame, name, fallback)

    def _plan_alignment_value(self, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {
            'center': Qt.AlignCenter,
            'align_center': Qt.AlignCenter,
            'left_top': Qt.AlignLeft | Qt.AlignTop,
            'align_left_top': Qt.AlignLeft | Qt.AlignTop,
        }.get(token, Qt.AlignCenter)

    def _plan_frame_shape_value(self, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {'hline': QFrame.HLine, 'no_frame': QFrame.NoFrame}.get(token, QFrame.NoFrame)

    def _plan_focus_policy_value(self, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {'no_focus': Qt.NoFocus, 'strong_focus': Qt.StrongFocus}.get(token, Qt.NoFocus)

    def _plan_scroll_bar_policy_value(self, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {
            'always_off': Qt.ScrollBarAlwaysOff,
            'always_on': Qt.ScrollBarAlwaysOn,
            'as_needed': Qt.ScrollBarAsNeeded,
        }.get(token, Qt.ScrollBarAsNeeded)

    def _nav_section_separator(self, nav_bar_plan: object) -> QFrame:
        sep = QFrame()
        sep.setObjectName(str(dict(nav_bar_plan or {}).get('nav_section_separator_object_name', 'navSectionSep')))
        return sep

    def _ensure_nav_reverse_control(self, nav_bar_plan: object | None = None):
        import tategakiXTC_gui_studio_right_pane_build_helpers as right_pane_helpers
        return right_pane_helpers._ensure_nav_reverse_control(self, nav_bar_plan)

    def _update_nav_button_texts(self) -> None:
        import tategakiXTC_gui_studio_navigation_action_helpers as navigation_action_helpers
        navigation_action_helpers.update_nav_button_texts(self)

    def _plan_spin_button_symbols_value(self, payload_obj: object, key: str, default: str):
        token = self._plan_token_value(payload_obj, key, default)
        return {
            'up_down_arrows': QSpinBox.UpDownArrows,
            'no_buttons': QSpinBox.NoButtons,
        }.get(token, QSpinBox.UpDownArrows if default == 'up_down_arrows' else QSpinBox.NoButtons)

    def _build_section_box_layout(
        self,
        section_key: object,
        fallback_title: str,
        *,
        default_margins: tuple[int, int, int, int],
        default_spacing: int,
    ):
        import tategakiXTC_gui_layouts as gui_layouts
        section_plan = self._localized_plan(gui_layouts.build_center_settings_section_layout_plan(section_key))
        box = QGroupBox(str(section_plan.get('title', fallback_title)))
        layout = QVBoxLayout(box)
        layout.setContentsMargins(*default_margins)
        layout.setSpacing(default_spacing)
        return box, layout, section_plan

    def _make_hbox_layout_from_plan(self, plan: object | None = None) -> QHBoxLayout:
        plan_dict = dict(plan or {})
        layout = QHBoxLayout()
        layout.setContentsMargins(*self._plan_int_tuple_value(plan_dict, 'contents_margins', (0, 0, 0, 0), expected_length=4))
        layout.setSpacing(self._plan_int_value(plan_dict, 'spacing', 6))
        return layout

    def _dim_label(self, text: object) -> QLabel:
        label = QLabel(str(text))
        label.setObjectName('dimLabel')
        return label

    def _help_icon_button(self, text: object) -> QPushButton:
        button = QPushButton('?')
        button.setObjectName('helpBtn')
        button.setToolTip(str(text))
        self.help_texts.append(str(text))
        return button

    def _make_button_from_plan(self, plan: object, callback=None) -> QPushButton:
        plan_dict = dict(plan or {})
        button = QPushButton(str(plan_dict.get('text', plan_dict.get('label', ''))))
        button.setObjectName(str(plan_dict.get('object_name', '')))
        if plan_dict.get('tooltip'):
            button.setToolTip(str(plan_dict.get('tooltip')))
        if plan_dict.get('checkable') is not None:
            button.setCheckable(self._plan_bool_value(plan_dict, 'checkable', False))
        if plan_dict.get('focus_policy') is not None:
            button.setFocusPolicy(self._plan_focus_policy_value(plan_dict, 'focus_policy', 'no_focus'))
        fixed_size = plan_dict.get('fixed_size')
        if fixed_size:
            try:
                width, height = fixed_size
                button.setFixedSize(int(width), int(height))
            except Exception:
                pass
        if callback is not None:
            button.clicked.connect(callback)
        return button

    def _add_optional_widget_to_layout(self, layout: QHBoxLayout, attr_name: str) -> None:
        self.optional_widget_calls.append(attr_name)
        widget = getattr(self, attr_name, None)
        if widget is not None:
            layout.addWidget(widget)

    def _sync_preview_zoom_control_state(self) -> None:
        preview_zoom_helpers._sync_preview_zoom_control_state(self)

    def _actual_size_uses_preview_zoom_calibration(self) -> bool:
        return bool(self.actual_size)

    def _sync_legacy_calibration_control_state(self) -> None:
        self.legacy_calibration_syncs += 1

    def _payload_int_value(self, payload_obj: object, key: str, default: int = 0) -> int:
        try:
            return int(dict(payload_obj or {}).get(key, default))
        except Exception:
            return int(default)

    def _payload_bool_value(self, payload_obj: object, key: str, default: bool = False) -> bool:
        try:
            return bool(dict(payload_obj or {}).get(key, default))
        except Exception:
            return bool(default)

    def _spin(self, minimum: int, maximum: int, value: int, **_kwargs) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def on_actual_size_toggled(self, *_args) -> None:
        pass

    def on_guides_toggled(self, *_args) -> None:
        pass

    def on_calibration_changed(self, *_args) -> None:
        pass

    def _mark_preview_dirty_from_signal(self, *_args) -> None:
        pass

    def save_ui_state(self, *_args) -> None:
        pass

    def manual_refresh_preview(self, *_args) -> None:
        pass

    def on_page_input_changed(self, *_args) -> None:
        pass

    def on_nav_reverse_toggled(self, *_args) -> None:
        pass

    def _sync_preview_size(self) -> None:
        pass

    def on_preview_zoom_changed(self, value: int) -> None:
        self.preview_zoom_changed_values.append(int(value))

    def open_xtc_file(self) -> None:
        pass

class Sweep368LayoutContractRegressionTests(unittest.TestCase):
    """sweep368でOKになったGUI整理の巻き戻りを静的に検出する。"""

    def test_left_pane_keeps_file_viewer_section_after_output_display_section(self):
        self.assertIn(
            "CENTER_SETTINGS_SECTION_KEYS: tuple[str, ...] = (\n"
            "    'output',\n"
            "    'composition',\n"
            "    'position',\n"
            "    'preview_controls',\n"
            ")",
            LAYOUTS_SOURCE,
        )
        self.assertLess(
            LAYOUTS_SOURCE.index("'preview_controls'"),
            LAYOUTS_SOURCE.index("'fileviewer'"),
        )
        self.assertIn("self.open_xtc_file", SETTINGS_SECTIONS_HELPERS_SOURCE)

    def test_file_viewer_section_keeps_xtc_xtch_open_button_and_help(self):
        gui_layouts, _studio, _preview_zoom_helpers, _right_pane_helpers, settings_sections_helpers = _load_sweep_behavior_modules()
        plan = {
            'open_xtc_button_text': 'OPEN-XTC',
            'open_xtc_button_object_name': 'customOpenBtn',
            'open_xtc_help_leading_spacing': 13,
            'open_xtc_help_text': 'CUSTOM HELP TEXT',
            'open_xtc_help_trailing_stretch': False,
        }
        window = _SweepBehaviorWindow()

        with mock.patch.object(settings_sections_helpers.gui_layouts, 'build_file_viewer_section_plan', return_value=plan):
            box = settings_sections_helpers._section_file_viewer(window)

        self.assertEqual(box.title(), 'ファイルビューワー')
        self.assertEqual(window.open_xtc_btn.text(), 'OPEN-XTC')
        self.assertEqual(window.open_xtc_btn.objectName(), 'customOpenBtn')
        self.assertEqual(window.help_texts[-1], 'CUSTOM HELP TEXT')
        self.assertIn("'open_xtc_help_text'", LAYOUTS_SOURCE)
        self.assertIn('既存の .xtc / .xtch ファイルを右ペインへ読み込んで確認します。', LAYOUTS_SOURCE)


    def test_right_pane_toolbar_owns_xtc_xtch_open_button(self):
        _gui_layouts, _studio, _preview_zoom_helpers, right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        import inspect

        source = inspect.getsource(right_pane_helpers._build_view_toggle_bar)
        self.assertIn('self.open_xtc_btn = self._make_button_from_plan', source)
        self.assertIn("toggle_plan.get('open_xtc_button_text', 'XTCファイルを開く')", source)
        self.assertIn('self.open_xtc_file', source)
        self.assertIn('top_lay.addWidget(self.open_xtc_btn)', source)
        self.assertIn("'open_xtc_button_text'", LAYOUTS_SOURCE)


    def test_preview_toolbar_keeps_actual_size_and_guides_help_layout(self):
        _gui_layouts, _studio, _preview_zoom_helpers, right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        window.actual_size_check = QLabel('actual')
        window.actual_size_help_btn = QLabel('actual-help')
        window.guides_check = QLabel('guides')
        window.guides_help_btn = QLabel('guides-help')
        plan = {'toggle_spacing': 23}
        container = QWidget()
        layout = QHBoxLayout(container)

        with mock.patch.object(right_pane_helpers.gui_layouts, 'build_preview_display_toggle_plan', return_value=plan):
            right_pane_helpers._add_preview_display_toggles_to_layout(window, layout)

        self.assertEqual(
            window.optional_widget_calls,
            ['actual_size_check', 'actual_size_help_btn', 'guides_check', 'guides_help_btn'],
        )
        self.assertIs(layout.itemAt(0).widget(), window.actual_size_check)
        self.assertIs(layout.itemAt(1).widget(), window.actual_size_help_btn)
        self.assertIsNotNone(layout.itemAt(2).spacerItem())
        self.assertEqual(layout.itemAt(2).spacerItem().sizeHint().width(), 23)
        self.assertIs(layout.itemAt(3).widget(), window.guides_check)
        self.assertIs(layout.itemAt(4).widget(), window.guides_help_btn)



    def test_preview_toolbar_help_texts_are_substantive(self):
        gui_layouts, _studio, _preview_zoom_helpers, _right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        import importlib
        preview_controls_helpers = importlib.import_module('tategakiXTC_gui_studio_preview_controls_helpers')
        window = _SweepBehaviorWindow()
        preview_toggle_plan = {
            'actual_size_text': 'ACTUAL',
            'actual_size_object_name': 'actualCustom',
            'actual_size_checkable': True,
            'actual_size_focus_policy': 'strong_focus',
            'actual_size_help_text': 'ACTUAL HELP TEXT',
            'guide_text': 'GUIDE',
            'guide_object_name': 'guideCustom',
            'guide_focus_policy': 'strong_focus',
            'guide_checked_default': False,
            'guide_help_text': 'GUIDE HELP TEXT',
        }
        display_plan = {
            'calibration_label_text': 'CALIB',
            'calibration_help_text': 'CALIB HELP TEXT',
        }

        with mock.patch.object(preview_controls_helpers.gui_layouts, 'build_preview_display_toggle_plan', return_value=preview_toggle_plan), \
             mock.patch.object(preview_controls_helpers.gui_layouts, 'build_display_section_plan', return_value=display_plan):
            wrapper = preview_controls_helpers.section_preview_controls(window)

        self.assertEqual(wrapper.objectName(), 'previewUpdateRowContainer')
        self.assertEqual(window.actual_size_check.text(), 'ACTUAL')
        self.assertEqual(window.actual_size_check.objectName(), 'actualCustom')
        self.assertTrue(window.actual_size_check.isCheckable())
        self.assertEqual(window.actual_size_check.focusPolicy(), Qt.NoFocus)
        self.assertEqual(window.actual_size_check.toolTip(), 'ACTUAL HELP TEXT')
        self.assertEqual(window.guides_check.text(), 'GUIDE')
        self.assertEqual(window.guides_check.objectName(), 'guideCustom')
        self.assertEqual(window.guides_check.focusPolicy(), Qt.StrongFocus)
        self.assertFalse(window.guides_check.isChecked())
        self.assertEqual(window.guides_check.toolTip(), 'GUIDE HELP TEXT')
        self.assertIn('ACTUAL HELP TEXT', window.help_texts)
        self.assertIn('GUIDE HELP TEXT', window.help_texts)
        self.assertIn('CALIB HELP TEXT', window.help_texts)
        self.assertIn('ONにすると右ペインの倍率欄は「実寸補正」に切り替わります。', LAYOUTS_SOURCE)
        self.assertIn('変換結果そのものを書き換える機能ではなく、確認用の表示補助です。', LAYOUTS_SOURCE)

    def test_view_toggle_button_chrome_is_owned_by_plan(self):
        _gui_layouts, _studio, _preview_zoom_helpers, right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        calls: list[str] = []
        window._add_preview_display_toggles_to_layout = lambda layout: calls.append('display')
        window._add_nav_controls_to_layout = lambda *args, **kwargs: calls.append('nav')
        window._add_preview_zoom_controls_to_layout = lambda *args, **kwargs: calls.append('zoom')
        window._preview_view_help_text = lambda: 'toggle help'
        plan = {
            'object_name': 'customViewToggleBar',
            'bar_height': 123,
            'contents_margins': (1, 2, 3, 4),
            'row_spacing': 9,
            'top_row_contents_margins': (5, 6, 7, 8),
            'spacing': 11,
            'top_separator_object_name': 'customTopSep',
            'bottom_row_contents_margins': (9, 10, 11, 12),
            'bottom_row_spacing': 13,
        }

        with mock.patch.object(right_pane_helpers.gui_layouts, 'build_view_toggle_bar_plan', return_value=plan):
            bar = right_pane_helpers._build_view_toggle_bar(window)

        outer = bar.layout()
        top_layout = outer.itemAt(0).layout()
        separator = outer.itemAt(1).widget()
        bottom_layout = outer.itemAt(2).layout()
        self.assertEqual(bar.objectName(), 'customViewToggleBar')
        self.assertEqual(bar.minimumHeight(), 123)
        self.assertEqual(bar.maximumHeight(), 123)
        self.assertEqual(_layout_margins_tuple(outer), (1, 2, 3, 4))
        self.assertEqual(outer.spacing(), 9)
        self.assertEqual(_layout_margins_tuple(top_layout), (5, 6, 7, 8))
        self.assertEqual(top_layout.spacing(), 11)
        self.assertEqual(separator.objectName(), 'customTopSep')
        self.assertEqual(_layout_margins_tuple(bottom_layout), (9, 10, 11, 12))
        self.assertEqual(bottom_layout.spacing(), 13)
        self.assertEqual(calls, ['display', 'nav', 'zoom'])


    def test_preview_zoom_width_and_spacing_contracts_are_owned_by_plan(self):
        _gui_layouts, _studio, _preview_zoom_helpers, right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        plan = {
            'preview_zoom_spacing': 17,
            'preview_zoom_label_visible': True,
            'preview_zoom_label_text': '倍率X',
            'preview_zoom_down_text': 'DOWN',
            'preview_zoom_up_text': 'UP',
            'preview_zoom_button_object_name': 'zoomStepCustom',
            'preview_zoom_button_size': (31, 29),
            'preview_zoom_min': 20,
            'preview_zoom_max': 220,
            'preview_zoom_step': 7,
            'preview_zoom_default': 83,
            'preview_zoom_spin_width': 91,
            'preview_zoom_spin_suffix': 'pt',
            'preview_zoom_spin_button_symbols': 'up_down_arrows',
            'preview_zoom_spin_accelerated': False,
            'preview_zoom_tooltip': '倍率ツールチップ',
        }
        container = QWidget()
        layout = QHBoxLayout(container)
        sync_calls: list[str] = []
        window._sync_preview_zoom_control_state = lambda: sync_calls.append('sync')

        right_pane_helpers._add_preview_zoom_controls_to_layout(window, layout, toggle_plan=plan)

        self.assertIsNotNone(layout.itemAt(0).spacerItem())
        self.assertEqual(layout.itemAt(0).spacerItem().sizeHint().width(), 17)
        self.assertTrue(window.preview_zoom_label.isVisible())
        self.assertEqual(window.preview_zoom_label.text(), '倍率X')
        self.assertEqual(window.preview_zoom_down_btn.text(), 'DOWN')
        self.assertEqual(window.preview_zoom_down_btn.objectName(), 'zoomStepCustom')
        self.assertEqual(window.preview_zoom_up_btn.text(), 'UP')
        self.assertEqual(window.preview_zoom_up_btn.objectName(), 'zoomStepCustom')
        self.assertEqual(window.preview_zoom_down_btn.size().width(), 31)
        self.assertEqual(window.preview_zoom_up_btn.size().height(), 29)
        self.assertEqual(window.preview_zoom_spin.minimum(), 20)
        self.assertEqual(window.preview_zoom_spin.maximum(), 220)
        self.assertEqual(window.preview_zoom_spin.singleStep(), 7)
        self.assertEqual(window.preview_zoom_spin.value(), 83)
        self.assertEqual(window.preview_zoom_spin.suffix(), 'pt')
        self.assertEqual(window.preview_zoom_spin.width(), 91)
        self.assertEqual(window.preview_zoom_spin.buttonSymbols(), QSpinBox.UpDownArrows)
        self.assertFalse(window.preview_zoom_spin.isAccelerated())
        self.assertEqual(window.preview_zoom_spin.toolTip(), '倍率ツールチップ')
        self.assertEqual(sync_calls, ['sync'])
        self.assertIn("'preview_zoom_spin_width': 78", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_spin_button_symbols': 'no_buttons'", LAYOUTS_SOURCE)


    def test_preview_zoom_dynamic_label_and_tooltips_are_owned_by_plan(self):
        _gui_layouts, _studio, preview_zoom_helpers, _right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        window.preview_zoom_label = QLabel('')
        window.preview_zoom_down_btn = QPushButton('down')
        window.preview_zoom_spin = QSpinBox()
        window.preview_zoom_up_btn = QPushButton('up')
        plan = {
            'preview_zoom_label_text': '通常倍率',
            'preview_zoom_actual_size_label_text': '実寸補正X',
            'preview_zoom_normal_tooltip': '通常ツールチップ',
            'preview_zoom_actual_size_tooltip': '実寸ツールチップ',
        }

        with mock.patch.object(preview_zoom_helpers.gui_layouts, 'build_view_toggle_bar_plan', return_value=plan):
            window.actual_size = False
            preview_zoom_helpers._sync_preview_zoom_control_state(window)
            self.assertEqual(window.preview_zoom_label.text(), '通常倍率')
            self.assertEqual(window.preview_zoom_label.toolTip(), '通常ツールチップ')
            self.assertEqual(window.preview_zoom_spin.toolTip(), '通常ツールチップ')

            window.actual_size = True
            preview_zoom_helpers._sync_preview_zoom_control_state(window)
            self.assertEqual(window.preview_zoom_label.text(), '実寸補正X')
            self.assertEqual(window.preview_zoom_label.toolTip(), '実寸ツールチップ')
            self.assertEqual(window.preview_zoom_down_btn.toolTip(), '実寸ツールチップ')
            self.assertEqual(window.preview_zoom_up_btn.toolTip(), '実寸ツールチップ')

        self.assertGreaterEqual(window.legacy_calibration_syncs, 2)


    def test_preview_view_help_text_is_owned_by_view_toggle_plan(self):
        _gui_layouts, studio, _preview_zoom_helpers, _right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        expected = 'CUSTOM RIGHT PANE HELP'

        with mock.patch.object(studio.gui_layouts, 'build_view_toggle_bar_plan', return_value={'help_text': expected}):
            self.assertEqual(studio.MainWindow._preview_view_help_text(window), expected)

        self.assertIn("'help_text': '右ペイン:", LAYOUTS_SOURCE)
        self.assertIn('「XTCファイルを開く」では、既存のXTC/XTCHファイルを同じ右ペインでページ送りしながら確認できます。', LAYOUTS_SOURCE)


    def test_navigation_widget_identity_is_owned_by_nav_bar_plan(self):
        _gui_layouts, _studio, _preview_zoom_helpers, right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        window._update_nav_button_texts = lambda: None
        plan = {
            'current_xtc_label_text': 'CURRENT',
            'current_xtc_label_visible': True,
            'current_xtc_label_object_name': 'customHint',
            'current_xtc_label_min_width': 17,
            'current_xtc_label_max_width': 222,
            'nav_reverse_text': 'REVERSE',
            'nav_reverse_object_name': 'customReverse',
            'nav_reverse_focus_policy': 'strong_focus',
            'prev_button_text': 'BACK',
            'next_button_text': 'FORWARD',
            'nav_button_object_name': 'customNavBtn',
            'nav_button_focus_policy': 'strong_focus',
            'page_label_text': 'PAGE',
            'page_input_minimum': 3,
            'page_input_maximum': 9,
            'page_input_button_symbols': 'up_down_arrows',
            'page_input_keyboard_tracking': True,
            'page_input_width': 77,
            'page_total_label_text': '/ TOTAL',
            'page_total_label_object_name': 'customTotal',
            'nav_button_side_spacing': 5,
            'nav_section_separator_object_name': 'customSep',
        }
        layout = QHBoxLayout(QWidget())

        right_pane_helpers._add_nav_controls_to_layout(window, layout, nav_bar_plan=plan, current_label_stretch=1)

        self.assertEqual(window.current_xtc_label.text(), 'CURRENT')
        self.assertEqual(window.current_xtc_label.objectName(), 'customHint')
        self.assertEqual(getattr(window.current_xtc_label, '_minimum_width', None), 17)
        self.assertEqual(getattr(window.current_xtc_label, '_maximum_width', None), 222)
        self.assertTrue(window.current_xtc_label.isVisible())
        self.assertEqual(window.nav_reverse_check.text(), 'REVERSE')
        self.assertEqual(window.nav_reverse_check.objectName(), 'customReverse')
        self.assertEqual(window.nav_reverse_check.focusPolicy(), Qt.StrongFocus)
        self.assertEqual(window.prev_btn.text(), 'BACK')
        self.assertEqual(window.prev_btn.objectName(), 'customNavBtn')
        self.assertEqual(window.prev_btn.focusPolicy(), Qt.NoFocus)
        self.assertEqual(window.page_input.minimum(), 3)
        self.assertEqual(window.page_input.maximum(), 9)
        self.assertEqual(window.page_input.buttonSymbols(), QSpinBox.UpDownArrows)
        self.assertTrue(window.page_input.keyboardTracking())
        self.assertEqual(window.page_input.width(), 77)
        self.assertEqual(window.page_total_label.text(), '/ TOTAL')
        self.assertEqual(window.page_total_label.objectName(), 'customTotal')
        self.assertEqual(window.next_btn.text(), 'FORWARD')
        self.assertIn("'page_input_button_symbols': 'no_buttons'", LAYOUTS_SOURCE)
        self.assertIn("'nav_reverse_focus_policy': 'no_focus'", LAYOUTS_SOURCE)

    def test_spin_button_symbols_tokens_are_resolved_by_shared_helper(self):
        _gui_layouts, studio, _preview_zoom_helpers, _right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()

        self.assertEqual(
            studio.MainWindow._plan_spin_button_symbols_value(
                window, {'symbols': 'up_down_arrows'}, 'symbols', 'no_buttons'
            ),
            QSpinBox.UpDownArrows,
        )
        self.assertEqual(
            studio.MainWindow._plan_spin_button_symbols_value(
                window, {'symbols': 'no_buttons'}, 'symbols', 'up_down_arrows'
            ),
            QSpinBox.NoButtons,
        )
        self.assertEqual(
            studio.MainWindow._plan_spin_button_symbols_value(
                window, {'symbols': 'unknown'}, 'symbols', 'up_down_arrows'
            ),
            QSpinBox.UpDownArrows,
        )

    def test_page_input_runtime_range_is_owned_by_nav_bar_plan(self):
        _gui_layouts, studio, _preview_zoom_helpers, _right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        window.page_input = QSpinBox()
        nav_plan = {
            'page_input_empty_minimum': 4,
            'page_input_empty_maximum': 6,
            'page_input_active_minimum': 2,
        }

        with mock.patch.object(studio.gui_layouts, 'build_nav_bar_plan', return_value=nav_plan):
            studio.MainWindow._reset_xtc_page_input(window, total_pages=0, current_page=99)
            self.assertEqual((window.page_input.minimum(), window.page_input.maximum(), window.page_input.value()), (4, 6, 4))
            studio.MainWindow._reset_xtc_page_input(window, total_pages=5, current_page=3)
            self.assertEqual((window.page_input.minimum(), window.page_input.maximum(), window.page_input.value()), (2, 5, 3))

        self.assertIn("'page_input_empty_minimum': 0", LAYOUTS_SOURCE)
        self.assertIn("'page_input_active_minimum': 1", LAYOUTS_SOURCE)

    def test_page_total_label_format_is_owned_by_nav_bar_plan(self):
        _gui_layouts, _studio, _preview_zoom_helpers, _right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        import importlib
        navigation_helpers = importlib.import_module('tategakiXTC_gui_studio_navigation_helpers')
        window = _SweepBehaviorWindow()
        window.prev_btn = QPushButton('prev')
        window.next_btn = QPushButton('next')
        window.page_input = QSpinBox()
        window.page_total_label = QLabel('')
        window.current_page_index = 0
        window.nav_buttons_reversed = False
        window._effective_device_view_source = lambda: 'xtc'
        window._normalized_xtc_page_index = lambda index=None, total=None: int(index or 0)
        window._normalized_device_preview_page_index = lambda index=None, total=None: int(index or 0)
        window._refresh_loaded_xtc_viewer_profile_cache = lambda: None
        window._reset_xtc_page_input = lambda total, current: setattr(window, 'reset_page_input_args', (total, current))
        window._apply_file_viewer_mode_preview_button_state = lambda: False
        window._restore_preview_update_button_from_file_viewer_state = lambda: None
        nav_plan = {'page_total_label_format': 'TOTAL={total}'}
        payload = {'view_mode': 'device', 'total': 7, 'current_index': 2, 'current_page': 3}

        with mock.patch.object(navigation_helpers.gui_layouts, 'build_nav_bar_plan', return_value=nav_plan):
            navigation_helpers._apply_xtc_navigation_ui(window, payload)

        self.assertEqual(window.page_total_label.text(), 'TOTAL=7')
        self.assertEqual(window.reset_page_input_args, (7, 3))
        self.assertIn("'page_total_label_format': '/ {total}'", LAYOUTS_SOURCE)

    def test_right_preview_stack_chrome_contracts_are_owned_by_panel_plan(self):
        _gui_layouts, _studio, _preview_zoom_helpers, right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        window = _SweepBehaviorWindow()
        window._build_view_toggle_bar = lambda: QFrame()
        window._build_conversion_completion_card = lambda: QFrame()
        plan = {
            'panel_contents_margins': (1, 2, 3, 4),
            'panel_spacing': 9,
            'font_page_margins': (5, 6, 7, 8),
            'font_preview_min_size': (111, 222),
            'font_preview_alignment': 'left_top',
            'font_preview_word_wrap': False,
            'font_scroll_widget_resizable': True,
            'font_scroll_alignment': 'left_top',
            'font_scroll_frame_shape': 'hline',
            'device_page_margins': (9, 10, 11, 12),
            'device_preview_min_size': (333, 444),
            'device_scroll_widget_resizable': True,
            'device_scroll_alignment': 'left_top',
            'device_scroll_frame_shape': 'hline',
            'device_scroll_focus_policy': 'no_focus',
            'preview_stack_index': 1,
        }

        with mock.patch.object(right_pane_helpers.gui_layouts, 'build_right_preview_panel_plan', return_value=plan), \
             mock.patch.object(right_pane_helpers, 'XtcViewerWidget', QWidget):
            panel = right_pane_helpers._build_right_preview(window)

        self.assertEqual(_layout_margins_tuple(panel.layout()), (1, 2, 3, 4))
        self.assertEqual(panel.layout().spacing(), 9)
        self.assertTrue(getattr(window.preview_scroll, '_widget_resizable', False))
        self.assertEqual(window.preview_scroll.alignment(), Qt.AlignLeft | Qt.AlignTop)
        self.assertEqual(window.preview_scroll.frameShape(), QFrame.HLine)
        self.assertEqual(window.preview_label.alignment(), Qt.AlignLeft | Qt.AlignTop)
        self.assertEqual(window.preview_label.minimumSize().width(), 111)
        self.assertFalse(getattr(window.preview_label, '_word_wrap', True))
        self.assertTrue(getattr(window.viewer_scroll, '_widget_resizable', False))
        self.assertEqual(window.viewer_scroll.alignment(), Qt.AlignLeft | Qt.AlignTop)
        self.assertEqual(window.viewer_scroll.frameShape(), QFrame.HLine)
        self.assertEqual(window.viewer_scroll.focusPolicy(), Qt.NoFocus)
        self.assertEqual(window.viewer_widget.minimumSize().height(), 444)
        self.assertEqual(window.preview_stack.currentIndex(), 1)
        self.assertIn("'font_scroll_frame_shape': 'no_frame'", LAYOUTS_SOURCE)
        self.assertIn("'device_scroll_focus_policy': 'strong_focus'", LAYOUTS_SOURCE)

    def test_navigation_button_texts_are_owned_by_nav_bar_plan(self):
        _gui_layouts, _studio, _preview_zoom_helpers, _right_pane_helpers, _settings_sections_helpers = _load_sweep_behavior_modules()
        import importlib
        navigation_action_helpers = importlib.import_module('tategakiXTC_gui_studio_navigation_action_helpers')
        window = _SweepBehaviorWindow()
        window.prev_btn = QPushButton('')
        window.next_btn = QPushButton('')
        nav_plan = {'prev_button_text': 'BACK', 'next_button_text': 'FORWARD'}

        with mock.patch.object(navigation_action_helpers.gui_layouts, 'build_nav_bar_plan', return_value=nav_plan):
            window.nav_buttons_reversed = False
            navigation_action_helpers.update_nav_button_texts(window)
            self.assertEqual((window.prev_btn.text(), window.next_btn.text()), ('BACK', 'FORWARD'))
            window.nav_buttons_reversed = True
            navigation_action_helpers.update_nav_button_texts(window)
            self.assertEqual((window.prev_btn.text(), window.next_btn.text()), ('FORWARD', 'BACK'))

        self.assertIn("'prev_button_text': '前'", LAYOUTS_SOURCE)
        self.assertIn("'next_button_text': '次'", LAYOUTS_SOURCE)


if __name__ == '__main__':
    unittest.main()
