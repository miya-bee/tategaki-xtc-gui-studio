from __future__ import annotations

"""Wheel/focus guard helpers for tategakiXTC GUI Studio.

These functions are split out from ``MainWindow`` while keeping the public
``MainWindow`` method names as compatibility wrappers in the entry module.
"""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit, QScrollBar, QSpinBox, QWidget


def _combo_popup_is_visible(self: Any, combo: object) -> bool:
    if not isinstance(combo, QComboBox):
        return False
    view_getter = getattr(combo, 'view', None)
    if not callable(view_getter):
        return False
    try:
        view = view_getter()
    except Exception:
        return False
    is_visible = getattr(view, 'isVisible', None)
    if callable(is_visible):
        try:
            return bool(is_visible())
        except Exception:
            return False
    return False


def _is_open_combo_popup_wheel_target(self: Any, obj: object) -> bool:
    """Allow wheel scrolling inside an opened combo-box popup list."""
    if obj is None:
        return False
    widget = obj
    visited_widget_ids: set[int] = set()
    while widget is not None and id(widget) not in visited_widget_ids:
        visited_widget_ids.add(id(widget))
        if isinstance(widget, QComboBox) and self._combo_popup_is_visible(widget):
            return True
        class_names = {cls.__name__ for cls in type(widget).__mro__}
        if class_names & {'QAbstractItemView', 'QListView', 'QTreeView', 'QTableView'}:
            try:
                container = self._center_settings_container_widget()
                combos = container.findChildren(QComboBox) if container is not None else []
                for combo in combos:
                    if self._combo_popup_is_visible(combo):
                        view = combo.view()
                        if widget is view or self._is_widget_descendant_of(widget, view):
                            return True
            except Exception:
                pass
        parent_getter = getattr(widget, 'parentWidget', None)
        if callable(parent_getter):
            try:
                widget = parent_getter()
                continue
            except Exception:
                return False
        parent_getter = getattr(widget, 'parent', None)
        widget = parent_getter() if callable(parent_getter) else None
    return False


def _wheel_value_change_control_for_event_object(self: Any, obj: object) -> object | None:
    widget = obj
    visited_widget_ids: set[int] = set()
    while widget is not None and id(widget) not in visited_widget_ids:
        visited_widget_ids.add(id(widget))
        if isinstance(widget, (QComboBox, QSpinBox)):
            return widget
        class_names = {cls.__name__ for cls in type(widget).__mro__}
        if 'QAbstractSpinBox' in class_names:
            return widget
        parent_getter = getattr(widget, 'parentWidget', None)
        if callable(parent_getter):
            try:
                widget = parent_getter()
                continue
            except Exception:
                return None
        parent_getter = getattr(widget, 'parent', None)
        widget = parent_getter() if callable(parent_getter) else None
    return None


def _should_suppress_center_settings_wheel_value_change(self: Any, obj: object) -> bool:
    """Return True when a center-pane wheel event must not edit a value.

    ``left_settings_container`` is still supported by
    _center_settings_container_widget() as a legacy alias, but the active
    v1.3.8 three-pane code should go through this center-named helper.
    """
    control = self._wheel_value_change_control_for_event_object(obj)
    if control is None:
        return False
    container = self._center_settings_container_widget()
    if container is None:
        return False
    return self._is_widget_descendant_of(control, container)


def _should_suppress_left_settings_wheel_value_change(self: Any, obj: object) -> bool:
    """Compatibility wrapper for pre-v1.3.8 left-settings tests/helpers."""
    return self._should_suppress_center_settings_wheel_value_change(obj)


def _should_scroll_center_settings_from_wheel_event(self: Any, obj: object) -> bool:
    """Return True when a wheel event should scroll the center settings pane.

    Qt does not always bubble wheel events from child widgets back to the
    QScrollArea on every Windows/PySide6 combination.  Installing this
    narrow filter on the upper settings container keeps labels, whitespace,
    checkboxes and buttons scrollable while value-changing controls are
    still protected by _should_suppress_center_settings_wheel_value_change().
    """
    container = self._center_settings_container_widget()
    scroll = self._center_settings_scroll_area()
    if container is None or scroll is None or obj is None:
        return False
    if obj is scroll:
        return True
    try:
        if obj is scroll.viewport():
            return True
    except Exception:
        pass
    if isinstance(obj, QScrollBar):
        return False
    return self._is_widget_descendant_of(obj, container)


def _should_scroll_left_settings_from_wheel_event(self: Any, obj: object) -> bool:
    """Compatibility wrapper for pre-v1.3.8 left-settings tests/helpers."""
    return self._should_scroll_center_settings_from_wheel_event(obj)


def _install_center_settings_wheel_value_guards(self: Any) -> None:
    """Install wheel guards through the current three-pane naming."""
    container = self._center_settings_container_widget()
    if container is None:
        return
    candidates: list[object] = [container]
    try:
        candidates.extend(list(container.findChildren(QWidget)))
    except Exception:
        pass
    scroll = self._center_settings_scroll_area()
    if scroll is not None:
        candidates.append(scroll)
        try:
            candidates.append(scroll.viewport())
        except Exception:
            pass
    seen: set[int] = set()
    for target in candidates:
        if target is None or id(target) in seen:
            continue
        seen.add(id(target))
        install = getattr(target, 'installEventFilter', None)
        if callable(install):
            try:
                install(self)
            except Exception:
                pass


def _install_left_settings_wheel_value_guards(self: Any) -> None:
    """Compatibility wrapper for pre-v1.3.8 left-settings tests/helpers."""
    self._install_center_settings_wheel_value_guards()


def _scroll_center_settings_from_wheel_event(self: Any, event: object) -> None:
    """Scroll the center settings pane from a wheel event."""
    scroll = self._center_settings_scroll_area()
    if scroll is None:
        return
    try:
        delta = event.angleDelta()
    except Exception:
        delta = None
    dy = 0
    dx = 0
    if delta is not None:
        try:
            dy = int(delta.y())
            dx = int(delta.x())
        except Exception:
            dy = 0
            dx = 0
    horizontal_requested = False
    try:
        modifiers = event.modifiers()
        horizontal_requested = bool(modifiers & Qt.ShiftModifier)
    except Exception:
        horizontal_requested = False
    use_horizontal = horizontal_requested or abs(dx) > abs(dy)
    units = dy if horizontal_requested and dy else (dx if use_horizontal else dy)
    try:
        target_bar = scroll.horizontalScrollBar() if use_horizontal else scroll.verticalScrollBar()
    except Exception:
        return
    if target_bar is None or units == 0:
        return
    try:
        step = int(target_bar.singleStep() or 20)
        # Qt wheel deltas are normally 120 units per notch. Keep fractional
        # devices responsive by falling back to one step for small deltas.
        notches = units / 120.0
        amount = int(round(notches * step * 3))
        if amount == 0:
            amount = step if units > 0 else -step
        target_bar.setValue(int(target_bar.value()) - amount)
    except Exception:
        return


def _scroll_left_settings_from_wheel_event(self: Any, event: object) -> None:
    """Compatibility wrapper for pre-v1.3.8 left-settings tests/helpers."""
    self._scroll_center_settings_from_wheel_event(event)


def _is_widget_descendant_of(widget: object, ancestor: object) -> bool:
    if widget is ancestor:
        return True
    parent_getter = getattr(widget, 'parentWidget', None)
    while callable(parent_getter):
        try:
            widget = parent_getter()
        except Exception:
            return False
        if widget is None:
            return False
        if widget is ancestor:
            return True
        parent_getter = getattr(widget, 'parentWidget', None)
    return False


def _clear_startup_input_focus(self: Any) -> None:
    """Move startup focus away from editable fields without changing normal editing."""
    active_modal_getter = getattr(QApplication, 'activeModalWidget', None)
    try:
        active_modal = active_modal_getter() if callable(active_modal_getter) else None
    except Exception:
        active_modal = None
    if active_modal is not None and active_modal is not self:
        return

    focus_widget_getter = getattr(QApplication, 'focusWidget', None)
    try:
        current_focus = focus_widget_getter() if callable(focus_widget_getter) else None
    except Exception:
        current_focus = None
    if current_focus is None:
        return
    try:
        if not self._is_widget_descendant_of(current_focus, self):
            return
    except Exception:
        return

    widget = current_focus
    should_clear = False
    visited_widget_ids: set[int] = set()
    while widget is not None and id(widget) not in visited_widget_ids:
        visited_widget_ids.add(id(widget))
        if isinstance(widget, (QLineEdit, QSpinBox, QComboBox)):
            should_clear = True
            break
        class_names = {cls.__name__ for cls in type(widget).__mro__}
        if 'QAbstractSpinBox' in class_names:
            should_clear = True
            break
        parent_getter = getattr(widget, 'parentWidget', None)
        widget = parent_getter() if callable(parent_getter) else None
    if not should_clear:
        return

    clear_focus = getattr(current_focus, 'clearFocus', None)
    if callable(clear_focus):
        try:
            clear_focus()
        except Exception:
            pass

    for candidate in (
        getattr(self, 'preview_scroll', None),
        getattr(self, 'viewer_scroll', None),
        self,
    ):
        set_focus = getattr(candidate, 'setFocus', None)
        if callable(set_focus):
            try:
                set_focus(Qt.OtherFocusReason)
                break
            except Exception:
                continue
