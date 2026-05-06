from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
else:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget
    except Exception:  # pragma: no cover - runtime fallback for test environments without PySide6
        class _QtFallback:
            NoFocus = 'no_focus'
            FocusPolicy = object

        class _MissingQtWidget:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                raise ModuleNotFoundError('PySide6 is required to create Qt widgets')

        Qt = _QtFallback()
        QGroupBox = _MissingQtWidget
        QHBoxLayout = _MissingQtWidget
        QVBoxLayout = _MissingQtWidget
        QLabel = _MissingQtWidget
        QPushButton = _MissingQtWidget
        QWidget = _MissingQtWidget

import tategakiXTC_gui_layouts as gui_layouts


def _coerce_mapping_payload(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, Mapping) else {}


def _mapping_bool_value(mapping: Mapping[str, Any], key: str, default: bool) -> bool:
    value = mapping.get(key, default)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'off', ''}:
            return False
    return bool(value)


def _mapping_int_value(mapping: Mapping[str, Any], key: str, default: int) -> int:
    value = mapping.get(key, default)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _mapping_int_tuple_value(
    mapping: Mapping[str, Any],
    key: str,
    default: tuple[int, ...],
    *,
    expected_length: int | None = None,
) -> tuple[int, ...]:
    value = mapping.get(key, default)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return tuple(default)
    items = list(value)
    if expected_length is not None and len(items) != expected_length:
        return tuple(default)
    normalized: list[int] = []
    for item in items:
        try:
            normalized.append(int(item))
        except (TypeError, ValueError):
            return tuple(default)
    return tuple(normalized)


def apply_button_widget_plan(
    button: QPushButton,
    plan: Mapping[str, Any],
    *,
    no_focus_policy: Qt.FocusPolicy = Qt.NoFocus,
) -> QPushButton:
    plan = _coerce_mapping_payload(plan)
    if 'text' in plan:
        button.setText(str(plan.get('text', '') or '').strip())
    if 'object_name' in plan:
        button.setObjectName(str(plan.get('object_name', '') or '').strip())
    if 'tooltip' in plan:
        button.setToolTip(str(plan.get('tooltip', '') or '').strip())
    fixed_size = plan.get('fixed_size')
    has_fixed_size = isinstance(fixed_size, (tuple, list)) and len(fixed_size) == 2
    if has_fixed_size:
        normalized_size = _mapping_int_tuple_value({'fixed_size': fixed_size}, 'fixed_size', (0, 0), expected_length=2)
        if normalized_size[0] > 0 and normalized_size[1] > 0:
            button.setFixedSize(normalized_size[0], normalized_size[1])
    else:
        fixed_width = _mapping_int_value(plan, 'fixed_width', 0)
        if fixed_width > 0:
            button.setFixedWidth(fixed_width)
        minimum_width = _mapping_int_value(plan, 'minimum_width', 0)
        if minimum_width > 0:
            button.setMinimumWidth(minimum_width)
    if 'checkable' in plan:
        is_checkable = _mapping_bool_value(plan, 'checkable', False)
        button.setCheckable(is_checkable)
        button.setChecked(_mapping_bool_value(plan, 'checked', False) if is_checkable else False)
    if 'enabled' in plan:
        button.setEnabled(_mapping_bool_value(plan, 'enabled', True))
    if str(plan.get('focus_policy', 'default')).strip().lower() == 'no_focus':
        button.setFocusPolicy(no_focus_policy)
    return button


def make_button_from_plan(
    plan: Mapping[str, Any],
    clicked: Callable[..., Any] | None = None,
    *,
    button_factory: type[QPushButton] = QPushButton,
    no_focus_policy: Qt.FocusPolicy = Qt.NoFocus,
) -> QPushButton:
    plan = _coerce_mapping_payload(plan)
    button = button_factory(str(plan.get('text', '') or ''))
    apply_button_widget_plan(button, plan, no_focus_policy=no_focus_policy)
    if clicked is not None:
        button.clicked.connect(clicked)
    return button


def make_hbox_layout_from_plan(
    plan: Mapping[str, Any] | None = None,
    *,
    default_spacing: int = 0,
    default_margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    layout_factory: type[QHBoxLayout] = QHBoxLayout,
) -> QHBoxLayout:
    layout = layout_factory()
    resolved_plan = _coerce_mapping_payload(plan)
    layout.setSpacing(_mapping_int_value(resolved_plan, 'spacing', default_spacing))
    layout.setContentsMargins(*_mapping_int_tuple_value(resolved_plan, 'contents_margins', default_margins, expected_length=4))
    if _mapping_bool_value(resolved_plan, 'add_stretch', False):
        layout.addStretch(1)
    return layout


def make_vbox_layout_from_plan(
    plan: Mapping[str, Any] | None = None,
    *,
    default_spacing: int = 0,
    default_margins: tuple[int, int, int, int] = (0, 0, 0, 0),
    layout_factory: type[QVBoxLayout] = QVBoxLayout,
) -> QVBoxLayout:
    layout = layout_factory()
    resolved_plan = _coerce_mapping_payload(plan)
    layout.setSpacing(_mapping_int_value(resolved_plan, 'spacing', default_spacing))
    layout.setContentsMargins(*_mapping_int_tuple_value(resolved_plan, 'contents_margins', default_margins, expected_length=4))
    if _mapping_bool_value(resolved_plan, 'add_stretch', False):
        layout.addStretch(1)
    return layout


def build_labeled_widget_row(
    pairs: Sequence[tuple[str, QWidget]],
    *,
    spacing: int = 3,
    pair_spacing: int = 6,
    label_object_name: str = 'dimLabel',
    trailing_stretch: bool = True,
    layout_factory: type[QHBoxLayout] = QHBoxLayout,
    label_factory: type[QLabel] = QLabel,
) -> QHBoxLayout:
    row_plan = gui_layouts.build_labeled_widget_row_plan(
        [label for label, _widget in pairs],
        spacing=spacing,
        pair_spacing=pair_spacing,
        label_object_name=label_object_name,
        trailing_stretch=trailing_stretch,
    )
    row = make_hbox_layout_from_plan(
        gui_layouts.build_row_layout_plan(spacing=row_plan.get('spacing', spacing)),
        layout_factory=layout_factory,
    )
    normalized_labels = tuple(row_plan.get('labels', ()))
    for index, (pair, normalized_label) in enumerate(zip(pairs, normalized_labels)):
        _source_label, widget = pair
        if index > 0:
            row.addSpacing(_mapping_int_value(row_plan, 'pair_spacing', pair_spacing))
        lbl = label_factory(str(normalized_label))
        lbl.setObjectName(str(row_plan.get('label_object_name', label_object_name)))
        row.addWidget(lbl)
        row.addWidget(widget)
    if _mapping_bool_value(row_plan, 'trailing_stretch', trailing_stretch):
        row.addStretch(1)
    return row


def make_section(
    title: str,
    *,
    group_box_factory: type[QGroupBox] = QGroupBox,
) -> QGroupBox:
    section_plan = gui_layouts.build_settings_section_plan(title)
    box = group_box_factory(str(section_plan.get('title', '')))
    box.setObjectName(str(section_plan.get('object_name', 'settingsSection')))
    return box


def make_section_box_layout(
    title: str,
    section_plan: Mapping[str, Any] | None = None,
    *,
    default_margins: tuple[int, int, int, int] = (8, 8, 8, 8),
    default_spacing: int = 6,
    group_box_factory: type[QGroupBox] = QGroupBox,
    layout_factory: type[QVBoxLayout] = QVBoxLayout,
) -> tuple[QGroupBox, QVBoxLayout, dict[str, Any]]:
    resolved_section_plan = _coerce_mapping_payload(section_plan) or _coerce_mapping_payload(gui_layouts.build_settings_section_plan(title))
    box = make_section(str(resolved_section_plan.get('title', title)), group_box_factory=group_box_factory)
    layout = make_vbox_layout_from_plan(
        {
            'spacing': resolved_section_plan.get('spacing', default_spacing),
            'contents_margins': resolved_section_plan.get('contents_margins', default_margins),
        },
        default_spacing=default_spacing,
        default_margins=default_margins,
        layout_factory=layout_factory,
    )
    set_layout = getattr(box, 'setLayout', None)
    if callable(set_layout):
        set_layout(layout)
    else:
        try:
            layout = layout_factory(box)
            layout.setSpacing(_mapping_int_value(resolved_section_plan, 'spacing', default_spacing))
            layout.setContentsMargins(*_mapping_int_tuple_value(resolved_section_plan, 'contents_margins', default_margins, expected_length=4))
        except TypeError:
            set_parent = getattr(layout, 'setParent', None)
            if callable(set_parent):
                try:
                    set_parent(box)
                except TypeError:
                    pass
            elif hasattr(box, 'layout'):
                try:
                    setattr(box, 'layout', layout)
                except Exception:
                    pass
    return box, layout, resolved_section_plan


def make_dim_label(text: str, *, label_factory: type[QLabel] = QLabel) -> QLabel:
    lbl = label_factory(text)
    lbl.setObjectName('dimLabel')
    return lbl


def make_note_label(text: str, *, label_factory: type[QLabel] = QLabel) -> QLabel:
    lbl = label_factory(text)
    lbl.setObjectName('subNoteLabel')
    word_wrap = getattr(lbl, 'setWordWrap', None)
    if callable(word_wrap):
        word_wrap(True)
    return lbl


def make_help_icon_button(
    text: str,
    *,
    tooltip: str | None = None,
    dialog_title: str | None = None,
    clicked: Callable[..., Any] | None = None,
    clicked_with_button: Callable[[QPushButton], Any] | None = None,
    property_name: str = 'helpText',
    button_factory: type[QPushButton] = QPushButton,
    no_focus_policy: Qt.FocusPolicy = Qt.NoFocus,
) -> QPushButton:
    help_text = str(text)
    tip = str(tooltip if tooltip is not None else help_text)
    resolved_dialog_title = str(dialog_title if dialog_title is not None else '説明')
    button = make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            '?',
            object_name='miniHelpBtn',
            fixed_size=(20, 20),
            tooltip=tip,
            focus_policy='no_focus',
        ),
        clicked=clicked,
        button_factory=button_factory,
        no_focus_policy=no_focus_policy,
    )
    set_property = getattr(button, 'setProperty', None)
    if callable(set_property):
        set_property(property_name, help_text)
        set_property('helpTitle', resolved_dialog_title)
    if clicked_with_button is not None:
        button.clicked.connect(lambda _checked=False, b=button: clicked_with_button(b))
    return button
