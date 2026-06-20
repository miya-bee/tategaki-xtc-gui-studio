from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt, QSize, QTimer

import tategakiXTC_gui_studio_logic as studio_logic


APP_LOGGER = logging.getLogger('tategaki_xtc')


def _set_horizontal_scrollbar_to_zoom_bias_later(
    self: Any,
    scroll_area: object,
) -> None:
    def _position() -> None:
        try:
            hbar_getter = getattr(scroll_area, 'horizontalScrollBar', None)
            hbar = hbar_getter() if callable(hbar_getter) else None
            if hbar is None:
                return
            minimum_getter = getattr(hbar, 'minimum', None)
            maximum_getter = getattr(hbar, 'maximum', None)
            minimum_value = int(minimum_getter() if callable(minimum_getter) else 0)
            maximum_value = int(maximum_getter() if callable(maximum_getter) else minimum_value)
            span = max(0, maximum_value - minimum_value)
            bias = self._preview_zoom_left_bias()
            target = minimum_value + int(round(span * 0.5 * (1.0 - bias)))
            set_value = getattr(hbar, 'setValue', None)
            if callable(set_value):
                set_value(max(minimum_value, min(maximum_value, target)))
        except Exception:
            pass

    _position()
    try:
        QTimer.singleShot(0, _position)
    except Exception:
        pass


def _set_horizontal_scrollbar_to_center_later(
    self: Any,
    scroll_area: object,
) -> None:
    def _position() -> None:
        try:
            hbar_getter = getattr(scroll_area, 'horizontalScrollBar', None)
            hbar = hbar_getter() if callable(hbar_getter) else None
            if hbar is None:
                return
            minimum_getter = getattr(hbar, 'minimum', None)
            maximum_getter = getattr(hbar, 'maximum', None)
            minimum_value = int(minimum_getter() if callable(minimum_getter) else 0)
            maximum_value = int(maximum_getter() if callable(maximum_getter) else minimum_value)
            target = minimum_value + max(0, maximum_value - minimum_value) // 2
            set_value = getattr(hbar, 'setValue', None)
            if callable(set_value):
                set_value(max(minimum_value, min(maximum_value, target)))
        except Exception:
            pass

    _position()
    try:
        QTimer.singleShot(0, _position)
    except Exception:
        pass


def _set_horizontal_scrollbar_to_minimum_later(
    self: Any,
    scroll_area: object,
) -> None:
    def _reset() -> None:
        try:
            hbar_getter = getattr(scroll_area, 'horizontalScrollBar', None)
            hbar = hbar_getter() if callable(hbar_getter) else None
            if hbar is None:
                return
            minimum_getter = getattr(hbar, 'minimum', None)
            minimum_value = minimum_getter() if callable(minimum_getter) else 0
            set_value = getattr(hbar, 'setValue', None)
            if callable(set_value):
                set_value(minimum_value)
        except Exception:
            pass

    _reset()
    try:
        QTimer.singleShot(0, _reset)
    except Exception:
        pass


def _sync_font_preview_scroll_placement(
    self: Any,
    *,
    reset_horizontal: bool = False,
) -> None:
    try:
        preview_scroll = getattr(self, 'preview_scroll', None)
        if preview_scroll is None:
            return
        preview_label = getattr(self, 'preview_label', None)
        scaled_size = getattr(self, '_last_font_preview_scaled_size', None)
        scaled_width = 0
        scaled_height = 0
        if scaled_size:
            try:
                scaled_width, scaled_height = int(scaled_size[0]), int(scaled_size[1])
            except Exception:
                scaled_width = scaled_height = 0
        leading_gap = self._font_preview_leading_gap(scaled_width) if scaled_width > 0 else 0
        # v1.3.3.19: keep the fixed-blank-rail fix from v1.3.3.18, but
        # replace the abrupt 100% -> 110% left snap with a viewport-aware
        # leading gap and a scrollbar position eased by the zoom percentage.
        preview_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        if preview_label is not None:
            try:
                preview_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            except Exception:
                pass
            try:
                preview_label.setContentsMargins(leading_gap, 0, 0, 0)
            except Exception:
                pass
            if scaled_width > 0 and scaled_height > 0:
                layout_width = max(1, scaled_width + leading_gap)
                layout_height = max(1, scaled_height)
                layout_size = QSize(layout_width, layout_height)
                try:
                    preview_label.setMinimumSize(layout_size)
                    preview_label.setMaximumSize(layout_size)
                    preview_label.resize(layout_size)
                except Exception:
                    pass
        if reset_horizontal:
            self._set_horizontal_scrollbar_to_zoom_bias_later(preview_scroll)
    except Exception:
        APP_LOGGER.exception('フォントビューのスクロール配置更新に失敗しました')


def _sync_preview_size(self: Any) -> None:
    self._sync_viewer_size()
    self._sync_font_preview_scroll_placement(reset_horizontal=False)
    preview_label = getattr(self, 'preview_label', None)
    if preview_label is None:
        return
    target = self._safe_preview_layout_size(self._font_preview_target_size())
    last_scaled = getattr(self, '_last_font_preview_scaled_size', None)
    try:
        current_pixmap = preview_label.pixmap() if hasattr(preview_label, 'pixmap') else None
    except Exception:
        current_pixmap = None
    if current_pixmap is not None and last_scaled:
        try:
            width, height = last_scaled
            target = QSize(max(1, int(width)), max(1, int(height)))
            preview_label.setMaximumSize(target)
        except Exception:
            pass
    else:
        try:
            preview_label.setMaximumSize(16777215, 16777215)
        except Exception:
            pass
    try:
        preview_label.setMinimumSize(target)
    except Exception:
        APP_LOGGER.exception('フォントプレビューの最小サイズ更新に失敗しました')
    try:
        preview_label.resize(target)
    except Exception:
        pass
    try:
        preview_label.updateGeometry()
    except Exception:
        APP_LOGGER.exception('フォントプレビューのレイアウト更新に失敗しました')
    self._sync_font_preview_scroll_placement(reset_horizontal=False)


def _sync_viewer_size(self: Any) -> None:
    try:
        if hasattr(self.viewer_widget, 'set_preview_zoom_factor'):
            self.viewer_widget.set_preview_zoom_factor(self._preview_zoom_factor())
    except Exception:
        APP_LOGGER.exception('実機ビューの表示倍率更新に失敗しました')
    try:
        # v1.3.8.5: keep XTC/XTCH file-viewer pages centered in the right
        # pane. The font preview still uses a zoom-dependent left-bias,
        # but the direct XTC viewer should not add a synthetic leading gap.
        set_gap = getattr(self.viewer_widget, 'set_preview_leading_gap', None)
        if callable(set_gap):
            set_gap(0)
    except Exception:
        APP_LOGGER.exception('実機ビューの中央寄せ余白更新に失敗しました')
    hint = self.viewer_widget.sizeHint()
    w, h = studio_logic.build_viewer_minimum_size(hint)
    try:
        self.viewer_widget.setMinimumSize(w, h)
    except Exception:
        APP_LOGGER.exception('実機ビューの最小サイズ更新に失敗しました')
    try:
        resize = getattr(self.viewer_widget, 'resize', None)
        if callable(resize):
            resize(w, h)
    except Exception:
        APP_LOGGER.exception('実機ビューの表示サイズ更新に失敗しました')
    try:
        viewer_scroll = getattr(self, 'viewer_scroll', None)
        if viewer_scroll is not None:
            # v1.3.8.5: in the 3-pane file-viewer flow, center the XTC
            # page horizontally in the right pane. When the page is wider
            # than the viewport, place the horizontal scrollbar at the
            # center instead of biasing it left.
            set_alignment = getattr(viewer_scroll, 'setAlignment', None)
            align_hcenter = self._qt_constant('AlignHCenter', self._qt_constant('AlignCenter', 0))
            align_top = self._qt_constant('AlignTop', 0)
            if callable(set_alignment):
                set_alignment(align_hcenter | align_top)
            self._set_horizontal_scrollbar_to_center_later(viewer_scroll)
    except Exception:
        APP_LOGGER.exception('実機ビューのスクロール配置更新に失敗しました')
    try:
        self.viewer_widget.updateGeometry()
    except Exception:
        APP_LOGGER.exception('実機ビューのレイアウト更新に失敗しました')
    try:
        self.viewer_widget.update()
    except Exception:
        APP_LOGGER.exception('実機ビューの再描画要求に失敗しました')
