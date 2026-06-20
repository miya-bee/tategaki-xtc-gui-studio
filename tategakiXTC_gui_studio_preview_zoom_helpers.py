from __future__ import annotations

"""Preview zoom/calibration and leading-gap helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._preview_zoom_factor`` etc.), so instance-level overrides installed by
tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``; the ``QSize``/``QApplication`` constructing helpers
(``_font_preview_target_size`` etc.) stay in the entry module.
"""

import math
from typing import Any

import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_layouts as gui_layouts


def _normalize_preview_zoom_pct(window: Any, value: object = None) -> int:
    if value is None:
        value = window._safe_widget_value('preview_zoom_spin', 100)
    return studio_logic.normalize_preview_zoom_pct(value)


def _preview_zoom_factor(window: Any) -> float:
    return window._normalize_preview_zoom_pct() / 100.0


def _actual_size_uses_preview_zoom_calibration(window: Any) -> bool:
    return window._safe_widget_checked('actual_size_check')


def _actual_size_calibration_factor(window: Any) -> float:
    return studio_logic.build_actual_size_calibration_factor(
        uses_preview_zoom=window._actual_size_uses_preview_zoom_calibration(),
        preview_zoom_pct=window._safe_widget_value('preview_zoom_spin', 100),
        calibration_pct=window._safe_widget_value('calib_spin', 100),
    )


def _sync_legacy_calibration_control_state(window: Any) -> None:
    # sweep361: 実寸近似ON時の補正は右ペインの倍率UIへ集約する。
    # 既存設定との互換のため左側の実寸補正ウィジェットは保持し、
    # UI上は非表示にして二重操作に見えないようにする。
    for widget_name in ('calib_label', 'calib_down_btn', 'calib_spin', 'calib_up_btn', 'calib_help_btn'):
        widget = getattr(window, widget_name, None)
        if widget is None:
            continue
        try:
            widget.setVisible(False)
        except Exception:
            pass
        try:
            widget.setEnabled(False)
        except Exception:
            pass


def _sync_preview_zoom_control_state(window: Any) -> None:
    actual_size = window._actual_size_uses_preview_zoom_calibration()
    toggle_plan = window._localized_plan(gui_layouts.build_view_toggle_bar_plan())
    zoom_control_state = studio_logic.build_preview_zoom_control_state(
        toggle_plan,
        actual_size=actual_size,
        label_key='preview_zoom_actual_size_label_text' if actual_size else 'preview_zoom_label_text',
        tooltip_key='preview_zoom_actual_size_tooltip' if actual_size else 'preview_zoom_normal_tooltip',
    )
    label_text = zoom_control_state['label_text']
    tooltip = zoom_control_state['tooltip']
    label = getattr(window, 'preview_zoom_label', None)
    if label is not None:
        try:
            label.setText(label_text)
        except Exception:
            pass
        try:
            label.setToolTip(tooltip)
        except Exception:
            pass
    for widget_name in ('preview_zoom_down_btn', 'preview_zoom_spin', 'preview_zoom_up_btn'):
        widget = getattr(window, widget_name, None)
        if widget is None:
            continue
        try:
            widget.setEnabled(True)
        except Exception:
            pass
        try:
            widget.setToolTip(tooltip)
        except Exception:
            pass
    window._sync_legacy_calibration_control_state()


def _preview_zoom_left_bias(window: Any) -> float:
    """Return a gentle 0.0..1.0 left-shift bias for preview zoom.

    v1.3.3.22: the previous 100%->200% smoothstep made the preview feel
    over-eager while repeatedly increasing the zoom.  Keep 100% centered,
    preserve most of the centered feeling through the mid zoom range, and
    finish the left shift only near the maximum 300% setting.  All three
    right-pane modes use this same curve.
    """
    try:
        zoom = float(window._preview_zoom_factor())
    except Exception:
        zoom = 1.0
    if not math.isfinite(zoom):
        zoom = 1.0
    start = 1.0
    end = 3.0
    if zoom <= start:
        return 0.0
    if zoom >= end:
        return 1.0
    t = (zoom - start) / (end - start)
    # smootherstep keeps the 100%-150% range calm, while still reaching
    # the left-biased high-zoom view at the 300% upper limit.
    eased = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
    return max(0.0, min(1.0, eased))


def _viewport_width_for_scroll_area(window: Any, scroll_area: object) -> int:
    try:
        viewport_getter = getattr(scroll_area, 'viewport', None)
        viewport = viewport_getter() if callable(viewport_getter) else None
        size_getter = getattr(viewport, 'size', None)
        size = size_getter() if callable(size_getter) else None
        width_getter = getattr(size, 'width', None)
        width = width_getter() if callable(width_getter) else 0
        return max(0, int(width))
    except Exception:
        return 0


def _font_preview_leading_gap(window: Any, content_width: int) -> int:
    preview_scroll = getattr(window, 'preview_scroll', None)
    viewport_width = window._viewport_width_for_scroll_area(preview_scroll)
    content_width = max(0, int(content_width))
    if viewport_width <= 0 or content_width <= 0 or content_width >= viewport_width:
        return 0
    centered_gap = max(0, int(round((viewport_width - content_width) / 2.0)))
    bias = window._preview_zoom_left_bias()
    return max(0, int(round(centered_gap * (1.0 - bias))))


def _viewer_preview_leading_gap(window: Any, content_width: int) -> int:
    viewer_scroll = getattr(window, 'viewer_scroll', None)
    viewport_width = window._viewport_width_for_scroll_area(viewer_scroll)
    content_width = max(0, int(content_width))
    if viewport_width <= 0 or content_width <= 0 or content_width >= viewport_width:
        return 0
    centered_gap = max(0, int(round((viewport_width - content_width) / 2.0)))
    bias = window._preview_zoom_left_bias()
    return max(0, int(round(centered_gap * (1.0 - bias))))
