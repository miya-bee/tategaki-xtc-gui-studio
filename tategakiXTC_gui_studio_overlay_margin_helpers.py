from __future__ import annotations

"""Bottom-overlay (page number / progress bar) margin helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and read/mutate Qt widget state and the
``_bottom_overlay_margin_auto_state`` attribute through ``window``, so
instance-level overrides installed by tests keep working.  This module
intentionally does not import PySide6 or ``tategakiXTC_gui_studio``.
"""

from collections.abc import Mapping
from typing import Any

import tategakiXTC_worker_logic as worker_logic


def _minimum_bottom_overlay_margin(
    window: Any,
    enabled_override: bool | None = None,
) -> int:
    if enabled_override is None:
        try:
            enabled = bool(
                getattr(window, 'page_number_check', None) is not None
                and window.page_number_check.isChecked()
            )
        except Exception:
            enabled = False
    else:
        enabled = bool(enabled_override)
    progress_enabled = False
    try:
        progress_enabled = bool(
            getattr(window, 'progress_bar_check', None) is not None
            and window.progress_bar_check.isChecked()
        )
    except Exception:
        progress_enabled = False
    required = 0
    if enabled:
        try:
            size = int(window.page_number_font_size_spin.value())
        except Exception:
            size = 12
        required = max(required, size + 1)
    if progress_enabled:
        required = max(required, 10)
    return max(0, required)


def _effective_bottom_overlay_margin(
    window: Any,
    margin_b: int | None = None,
    *,
    enabled_override: bool | None = None,
) -> int:
    if margin_b is None:
        widget = getattr(window, 'margin_b_spin', None)
        try:
            margin_b = int(widget.value()) if widget is not None and hasattr(widget, 'value') else 0
        except Exception:
            margin_b = 0
    return max(0, int(margin_b), window._minimum_bottom_overlay_margin(enabled_override))


def _current_bottom_overlay_margin_auto_state(window: Any) -> dict[str, int | bool] | None:
    state = getattr(window, '_bottom_overlay_margin_auto_state', None)
    if not isinstance(state, dict) or not bool(state.get('active')):
        return None
    try:
        base_value = max(0, int(state.get('base_value', 0)))
        auto_value = max(0, int(state.get('auto_value', 0)))
    except Exception:
        return None
    widget = getattr(window, 'margin_b_spin', None)
    try:
        current = max(0, int(widget.value())) if widget is not None and hasattr(widget, 'value') else auto_value
    except Exception:
        current = auto_value
    if current != auto_value:
        return None
    return {'active': True, 'base_value': base_value, 'auto_value': auto_value}


def _restore_bottom_overlay_margin_auto_state_from_payload(window: Any, payload: Mapping[str, object]) -> None:
    if not isinstance(payload, Mapping):
        return
    try:
        primary_active = worker_logic._bool_config_value(payload, 'bottom_overlay_margin_auto_active', False)
        legacy_active = worker_logic._bool_config_value(payload, 'page_number_margin_auto_active', False)
        use_legacy = bool(not primary_active and legacy_active)
        active = bool(primary_active or legacy_active)
    except Exception:
        active = False
        use_legacy = False
    if not active:
        try:
            delattr(window, '_bottom_overlay_margin_auto_state')
        except Exception:
            pass
        return
    widget = getattr(window, 'margin_b_spin', None)
    try:
        current = max(0, int(widget.value())) if widget is not None and hasattr(widget, 'value') else 0
        base_key = (
            'page_number_margin_auto_base_value'
            if use_legacy
            else 'bottom_overlay_margin_auto_base_value'
        )
        auto_key = (
            'page_number_margin_auto_value'
            if use_legacy
            else 'bottom_overlay_margin_auto_value'
        )
        base_value = max(0, worker_logic._int_config_value(payload, base_key, current))
        auto_value = max(0, worker_logic._int_config_value(payload, auto_key, current))
    except Exception:
        return
    try:
        enabled = bool(
            (getattr(window, 'page_number_check', None) is not None and window.page_number_check.isChecked())
            or (getattr(window, 'progress_bar_check', None) is not None and window.progress_bar_check.isChecked())
        )
    except Exception:
        enabled = False
    if enabled and current == auto_value and auto_value >= base_value:
        setattr(window, '_bottom_overlay_margin_auto_state', {
            'active': True,
            'base_value': int(base_value),
            'auto_value': int(auto_value),
        })
    else:
        try:
            delattr(window, '_bottom_overlay_margin_auto_state')
        except Exception:
            pass


def _bottom_overlay_margin_auto_save_payload(window: Any) -> dict[str, object]:
    state = window._current_bottom_overlay_margin_auto_state()
    if state is None:
        value = window._safe_widget_value('margin_b_spin', 14)
        return {
            'bottom_overlay_margin_auto_active': False,
            'bottom_overlay_margin_auto_base_value': value,
            'bottom_overlay_margin_auto_value': value,
            # Transitional aliases for v1.4.1.1/v1.4.1.2 ini compatibility.
            'page_number_margin_auto_active': False,
            'page_number_margin_auto_base_value': value,
            'page_number_margin_auto_value': value,
        }
    base_value = int(state['base_value'])
    auto_value = int(state['auto_value'])
    return {
        'bottom_overlay_margin_auto_active': True,
        'bottom_overlay_margin_auto_base_value': base_value,
        'bottom_overlay_margin_auto_value': auto_value,
        # Transitional aliases for v1.4.1.1/v1.4.1.2 ini compatibility.
        'page_number_margin_auto_active': True,
        'page_number_margin_auto_base_value': base_value,
        'page_number_margin_auto_value': auto_value,
    }


def _clear_bottom_overlay_margin_auto_state_if_bottom_margin_was_edited(window: Any) -> None:
    state = getattr(window, '_bottom_overlay_margin_auto_state', None)
    if not isinstance(state, dict) or not bool(state.get('active')):
        return
    widget = getattr(window, 'margin_b_spin', None)
    try:
        current = max(0, int(widget.value())) if widget is not None and hasattr(widget, 'value') else 0
        auto_value = max(0, int(state.get('auto_value', 0)))
    except Exception:
        return
    if current != auto_value:
        try:
            delattr(window, '_bottom_overlay_margin_auto_state')
        except Exception:
            pass


def _sync_bottom_overlay_margin_to_ui(
    window: Any,
    enabled_override: bool | None = None,
) -> bool:
    """Sync the visible bottom margin with lower overlay requirements.

    Page numbers reserve at least ``font_size + 1`` pixels and the
    progress bar reserves a small bottom lane.  The spinbox should show
    the effective bottom margin too.  When an overlay requirement grows,
    raise the bottom margin automatically.  When it shrinks, lower the
    spinbox again only if the current value still appears to be the value
    that this helper previously set automatically.  A larger user-set
    bottom margin is preserved.
    """
    required = window._minimum_bottom_overlay_margin(enabled_override)
    widget = getattr(window, 'margin_b_spin', None)
    if widget is None or not hasattr(widget, 'value') or not hasattr(widget, 'setValue'):
        return False
    try:
        current = max(0, int(widget.value()))
    except Exception:
        current = 0

    state = getattr(window, '_bottom_overlay_margin_auto_state', None)
    auto_active = isinstance(state, dict) and bool(state.get('active'))
    auto_value = None
    base_value = None
    if auto_active:
        try:
            auto_value = max(0, int(state.get('auto_value', 0)))
        except Exception:
            auto_value = None
        try:
            base_value = max(0, int(state.get('base_value', 0)))
        except Exception:
            base_value = None
        # If the user edited the margin after our previous automatic set,
        # stop treating it as auto-managed.
        if auto_value is None or current != auto_value:
            auto_active = False
            auto_value = None
            base_value = None
            try:
                delattr(window, '_bottom_overlay_margin_auto_state')
            except Exception:
                pass

    if required <= 0:
        # Lower overlays are OFF.  If the bottom margin still matches the
        # value that this helper set automatically, restore the user's
        # pre-auto margin.  If the user has edited the margin after auto
        # expansion, keep the user value and simply clear auto-management.
        if auto_active and auto_value is not None and base_value is not None:
            target = int(base_value)
            if target == current:
                try:
                    delattr(window, '_bottom_overlay_margin_auto_state')
                except Exception:
                    pass
                return False
            blocked_old = None
            block_signals = getattr(widget, 'blockSignals', None)
            if callable(block_signals):
                try:
                    blocked_old = block_signals(True)
                except Exception:
                    blocked_old = None
            try:
                widget.setValue(int(target))
            finally:
                if callable(block_signals):
                    try:
                        block_signals(bool(blocked_old))
                    except Exception:
                        pass
            try:
                delattr(window, '_bottom_overlay_margin_auto_state')
            except Exception:
                pass
            return True
        return False

    target = current
    if current < required:
        if not auto_active:
            base_value = current
        target = required
    elif auto_active and auto_value is not None and base_value is not None:
        # The overlay requirement shrank.  Follow it downward, but do
        # not go below the bottom margin the user had before auto-expansion.
        target = max(base_value, required)
    else:
        return False

    if target == current:
        if auto_active:
            setattr(window, '_bottom_overlay_margin_auto_state', {
                'active': True,
                'base_value': int(base_value if base_value is not None else current),
                'auto_value': int(current),
            })
        return False

    blocked_old = None
    block_signals = getattr(widget, 'blockSignals', None)
    if callable(block_signals):
        try:
            blocked_old = block_signals(True)
        except Exception:
            blocked_old = None
    try:
        widget.setValue(int(target))
    finally:
        if callable(block_signals):
            try:
                block_signals(bool(blocked_old))
            except Exception:
                pass
    setattr(window, '_bottom_overlay_margin_auto_state', {
        'active': True,
        'base_value': int(base_value if base_value is not None else current),
        'auto_value': int(target),
    })
    return True
