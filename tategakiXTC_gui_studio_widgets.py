from __future__ import annotations

"""Custom Qt widgets for tategakiXTC GUI Studio.

This module keeps PySide6 widget subclasses outside the main entry module while
`tategakiXTC_gui_studio.py` re-exports the public names for compatibility.
"""

import logging
import math
import sys
from typing import Any, Callable

from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygon
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QSpinBox,
    QStyle,
    QStyleOptionSpinBox,
    QWidget,
)

from tategakiXTC_gui_studio_constants import DeviceProfile, DEVICE_PROFILES
from tategakiXTC_gui_studio_xtc_io import XtcPage

APP_LOGGER = logging.getLogger('tategaki_xtc')


def _qrectf_class() -> Any:
    entry_module = sys.modules.get('tategakiXTC_gui_studio')
    candidate = getattr(entry_module, 'QRectF', None) if entry_module is not None else None
    if candidate is not None and candidate is not QRectF:
        return candidate
    return QRectF


def _scroll_combo_popup_to_top_helper() -> Callable[[object], None]:
    entry_module = sys.modules.get('tategakiXTC_gui_studio')
    candidate = getattr(entry_module, '_scroll_combo_popup_to_top_now', None) if entry_module is not None else None
    if callable(candidate) and candidate is not _scroll_combo_popup_to_top_now:
        return candidate
    return _scroll_combo_popup_to_top_now


def _scroll_combo_popup_to_top_now(combo: object) -> None:
    view_getter = getattr(combo, 'view', None)
    if not callable(view_getter):
        return
    try:
        view = view_getter()
    except Exception:
        return
    if view is None:
        return
    scroll_to_top = getattr(view, 'scrollToTop', None)
    if callable(scroll_to_top):
        try:
            scroll_to_top()
        except Exception:
            pass
    bar_getter = getattr(view, 'verticalScrollBar', None)
    if not callable(bar_getter):
        return
    try:
        bar = bar_getter()
    except Exception:
        return
    if bar is None:
        return
    minimum_value = 0
    minimum_getter = getattr(bar, 'minimum', None)
    if callable(minimum_getter):
        try:
            minimum_value = int(minimum_getter())
        except Exception:
            minimum_value = 0
    set_value = getattr(bar, 'setValue', None)
    if callable(set_value):
        try:
            set_value(minimum_value)
        except Exception:
            pass


class FontPopupTopComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._first_popup_shown = True

    def _reset_popup_scroll_to_top(self) -> None:
        scroll_to_top = _scroll_combo_popup_to_top_helper()
        scroll_to_top(self)
        try:
            QTimer.singleShot(0, lambda: _scroll_combo_popup_to_top_helper()(self))
            QTimer.singleShot(25, lambda: _scroll_combo_popup_to_top_helper()(self))
            if bool(getattr(self, '_first_popup_shown', False)):
                QTimer.singleShot(80, lambda: _scroll_combo_popup_to_top_helper()(self))
        except Exception:
            pass

    def showPopup(self) -> None:
        super().showPopup()
        self._reset_popup_scroll_to_top()
        self._first_popup_shown = False


class VisibleArrowSpinBox(QSpinBox):
    """Windows環境でも上下三角が確実に見えるよう、スピンボタン上に矢印を自前描画する。"""

    def paintEvent(self, event: object) -> None:
        super().paintEvent(event)
        if not bool(self.property('showSpinButtons')):
            return

        opt = QStyleOptionSpinBox()
        self.initStyleOption(opt)
        style = self.style()
        up_rect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxUp, self)
        down_rect = style.subControlRect(QStyle.CC_SpinBox, opt, QStyle.SC_SpinBoxDown, self)
        if not up_rect.isValid() or not down_rect.isValid():
            return

        theme = self.property('uiTheme') or 'light'
        fill = QColor('#0B3E78') if theme != 'dark' else QColor('#F5FAFF')
        outline = QColor('#06294D') if theme != 'dark' else QColor('#BFD8EE')

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(outline, 1.2))
        painter.setBrush(fill)

        def triangle(rect: Any, up: bool = True) -> QPolygon:
            cx = rect.center().x()
            cy = rect.center().y()
            half_w = max(5, min(7, rect.width() // 3))
            half_h = max(3, min(5, rect.height() // 4))
            if up:
                return QPolygon([
                    QPoint(cx, cy - half_h),
                    QPoint(cx - half_w, cy + half_h),
                    QPoint(cx + half_w, cy + half_h),
                ])
            return QPolygon([
                QPoint(cx - half_w, cy - half_h),
                QPoint(cx + half_w, cy - half_h),
                QPoint(cx, cy + half_h),
            ])

        painter.drawPolygon(triangle(up_rect, up=True))
        painter.drawPolygon(triangle(down_rect, up=False))




# ─────────────────────────────────────────────────────────
# 実機プレビューウィジェット
# ─────────────────────────────────────────────────────────

class XtcViewerWidget(QWidget):
    def __init__(self: XtcViewerWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(420, 560)
        self.profile = DEVICE_PROFILES['x4']
        self.actual_size = False
        self.show_guides = True
        self.guide_margins = (0, 0, 0, 0)
        self.calibration = 1.0
        self.preview_zoom_factor = 1.0
        self.page_image: QImage | None = None
        self.ui_theme = 'light'
        self.setFocusPolicy(Qt.StrongFocus)

    def set_ui_theme(self: XtcViewerWidget, theme: str) -> None:
        self.ui_theme = 'dark' if theme == 'dark' else 'light'
        self.update()

    def set_profile(self: XtcViewerWidget, profile: DeviceProfile) -> None:
        self.profile = profile
        self.updateGeometry()
        self.update()

    def set_actual_size(self: XtcViewerWidget, enabled: bool) -> None:
        self.actual_size = enabled
        self.updateGeometry()
        self.update()

    def set_show_guides(self: XtcViewerWidget, enabled: bool) -> None:
        self.show_guides = enabled
        self.update()

    def set_guide_margins(self: XtcViewerWidget, margin_t: int, margin_b: int, margin_r: int, margin_l: int) -> None:
        self.guide_margins = (
            max(0, int(margin_t)),
            max(0, int(margin_b)),
            max(0, int(margin_r)),
            max(0, int(margin_l)),
        )
        self.update()

    def _has_visible_guide_overlay(self: XtcViewerWidget) -> bool:
        if not self.show_guides:
            return False
        return any(int(value) > 0 for value in tuple(getattr(self, 'guide_margins', (0, 0, 0, 0))))

    def _guide_rect_for_screen_rect(self: XtcViewerWidget, screen_rect: QRectF) -> QRectF:
        if not self._has_visible_guide_overlay():
            return screen_rect
        margin_t, margin_b, margin_r, margin_l = tuple(getattr(self, 'guide_margins', (0, 0, 0, 0)))
        page_width = max(1, int(getattr(self.profile, 'width_px', 0) or 0))
        page_height = max(1, int(getattr(self.profile, 'height_px', 0) or 0))
        width = max(1.0, float(screen_rect.width()))
        height = max(1.0, float(screen_rect.height()))
        left_inset = int(round(width * max(0, margin_l) / page_width))
        right_inset = int(round(width * max(0, margin_r) / page_width))
        top_inset = int(round(height * max(0, margin_t) / page_height))
        bottom_inset = int(round(height * max(0, margin_b) / page_height))
        left_inset = max(0, min(left_inset, max(0, int(round(width)) - 1)))
        right_inset = max(0, min(right_inset, max(0, int(round(width)) - left_inset - 1)))
        top_inset = max(0, min(top_inset, max(0, int(round(height)) - 1)))
        bottom_inset = max(0, min(bottom_inset, max(0, int(round(height)) - top_inset - 1)))
        return screen_rect.adjusted(left_inset, top_inset, -right_inset, -bottom_inset)

    def _screen_fill_hex(self: XtcViewerWidget, dark: bool) -> str:
        if self._has_visible_guide_overlay():
            return '#DDE4E8' if dark else '#E8EEF0'
        return '#DCDCDC' if dark else '#F0F0F0'

    def set_calibration(self: XtcViewerWidget, value: float) -> None:
        self.calibration = value
        self.updateGeometry()
        self.update()

    def set_preview_zoom_factor(self: XtcViewerWidget, value: object) -> None:
        try:
            zoom = float(value)
        except Exception:
            zoom = 1.0
        if not math.isfinite(zoom):
            zoom = 1.0
        zoom = max(0.5, min(zoom, 3.0))
        if abs(float(getattr(self, 'preview_zoom_factor', 1.0)) - zoom) < 0.0001:
            return
        self.preview_zoom_factor = zoom
        self.updateGeometry()
        self.update()

    def _preview_zoom_factor(self: XtcViewerWidget) -> float:
        try:
            zoom = float(getattr(self, 'preview_zoom_factor', 1.0))
        except Exception:
            zoom = 1.0
        if not math.isfinite(zoom):
            zoom = 1.0
        return max(0.5, min(zoom, 3.0))

    def set_page_image(self: XtcViewerWidget, image: QImage | None) -> None:
        self.page_image = image
        self.update()

    def clear_page(self: XtcViewerWidget) -> None:
        self.page_image = None
        self.update()

    def _px_per_mm(self: XtcViewerWidget) -> float:
        screen = self.screen() or QApplication.primaryScreen()
        dpi = screen.logicalDotsPerInch() if screen else 96
        return max(1.0, dpi / 25.4) * self.calibration

    def sizeHint(self: XtcViewerWidget) -> QSize:
        margin = 48
        zoom = self._preview_zoom_factor()
        if self.actual_size:
            px = self._px_per_mm()
            body_w = int(round(float(self.profile.body_w_mm) * px * zoom))
            body_h = int(round(float(self.profile.body_h_mm) * px * zoom))
            return QSize(
                max(1, body_w) + margin * 2,
                max(1, body_h) + margin * 2,
            )
        base_w, base_h = 660, 860
        content_w = max(1, base_w - margin * 2)
        content_h = max(1, base_h - margin * 2)
        return QSize(
            margin * 2 + max(1, int(round(content_w * zoom))),
            margin * 2 + max(1, int(round(content_h * zoom))),
        )

    def paintEvent(self: XtcViewerWidget, event: object) -> None:
        rect = self.rect()
        if rect.width() < 24 or rect.height() < 24:
            return

        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)

            dark = self.ui_theme == 'dark'
            outer_bg = QColor('#0D1520') if dark else QColor('#F3F6FA')
            body_fill = QColor('#132131') if dark else QColor('#FCFEFF')
            title_color = QColor('#DDEAF7') if dark else QColor('#1E3650')
            sub_color = QColor('#8EA8BF') if dark else QColor('#6E8193')
            screen_fill = QColor(self._screen_fill_hex(dark))
            screen_border = QColor('#6D8295') if dark else QColor('#94A3B3')
            empty_color = QColor('#93A7B9') if dark else QColor('#7E8B98')
            guide_color = QColor(114, 173, 255, 120) if dark else QColor(75, 152, 255, 110)
            guide_text = QColor('#8CA6BC') if dark else QColor('#73879A')

            painter.fillRect(rect, outer_bg)
            body_rect, screen_rect = self._calculate_rects()
            if body_rect.width() <= 1 or body_rect.height() <= 1 or screen_rect.width() <= 1 or screen_rect.height() <= 1:
                return

            shadow_rect = body_rect.adjusted(-8, -8, 8, 8).toRect()
            painter.fillRect(shadow_rect, QColor(0, 0, 0, 28))

            body_rect_i = body_rect.toRect()
            painter.fillRect(body_rect_i, body_fill)
            painter.setPen(QPen(QColor(self.profile.accent), 2.2))
            painter.drawRect(body_rect_i)

            band = body_rect.adjusted(18, 16, -18, -(body_rect.height() - 52))
            if band.width() > 1 and band.height() > 1:
                painter.fillRect(band.toRect(), QColor(0, 0, 0, 6))

            painter.setFont(QFont('Meiryo', 10))
            painter.setPen(sub_color)
            painter.drawText(
                body_rect.adjusted(12, 18, -12, 0),
                Qt.AlignTop | Qt.AlignHCenter | Qt.TextWordWrap,
                self.profile.tagline,
            )

            sp = QPainterPath()
            sp.addRect(screen_rect)
            painter.fillPath(sp, screen_fill)
            painter.setPen(QPen(screen_border, 1.0))
            painter.drawPath(sp)

            guide_rect = self._guide_rect_for_screen_rect(screen_rect)
            if self.page_image and not self.page_image.isNull():
                dpr_getter = getattr(self, 'devicePixelRatioF', None)
                try:
                    dpr = float(dpr_getter()) if callable(dpr_getter) else 1.0
                except Exception:
                    dpr = 1.0
                if dpr <= 0:
                    dpr = 1.0
                pix = QPixmap.fromImage(self.page_image)
                target_logical = screen_rect.size().toSize()
                logical_w = max(1, min(int(round(target_logical.width())), 4096))
                logical_h = max(1, min(int(round(target_logical.height())), 4096))
                target_phys = QSize(
                    max(1, min(int(round(logical_w * dpr)), 8192)),
                    max(1, min(int(round(logical_h * dpr)), 8192)),
                )
                scaled = pix.scaled(target_phys, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                if hasattr(scaled, 'setDevicePixelRatio'):
                    try:
                        scaled.setDevicePixelRatio(dpr)
                    except Exception:
                        pass
                logical_w = scaled.width() / dpr
                logical_h = scaled.height() / dpr
                scaled_logical_w = logical_w
                scaled_logical_h = logical_h
                ix = int(round(screen_rect.x() + (screen_rect.width() - scaled_logical_w) / 2.0))
                iy = int(round(screen_rect.y() + (screen_rect.height() - logical_h) / 2.0))
                painter.drawPixmap(ix, iy, scaled)
            else:
                painter.setPen(empty_color)
                painter.setFont(QFont('Meiryo', 14))
                painter.drawText(
                    guide_rect.toRect(), Qt.AlignCenter,
                    'XTCを読み込むと\nここに実機風プレビューを表示します',
                )

            if self._has_visible_guide_overlay():
                guide_band = QPainterPath()
                guide_band.addRect(screen_rect)
                guide_band.addRect(guide_rect)
                painter.fillPath(guide_band, QColor(75, 152, 255, 48) if not dark else QColor(114, 173, 255, 40))
                painter.setPen(QPen(guide_color, 1, Qt.DashLine))
                painter.drawRect(guide_rect.toRect())
            if self.show_guides:
                painter.setFont(QFont('Meiryo', 10))
                painter.setPen(guide_text)
                info = (
                    f'{self.profile.width_px}×{self.profile.height_px}px'
                    f' / {self.profile.screen_w_mm:.1f}×{self.profile.screen_h_mm:.1f}mm'
                )
                info_top = int(round(screen_rect.bottom())) + 6
                info_rect = QRect(int(round(screen_rect.left())), info_top, int(round(screen_rect.width())), 18)
                painter.drawText(
                    info_rect,
                    Qt.AlignTop | Qt.AlignHCenter,
                    info,
                )
        except Exception:
            APP_LOGGER.exception('実機風プレビュー描画に失敗しました')
        finally:
            try:
                painter.end()
            except Exception:
                pass

    def _calculate_rects(self: XtcViewerWidget) -> tuple[QRectF, QRectF]:
        margin = 34
        rect = self.rect()
        qrectf_cls = _qrectf_class()
        if rect.width() <= margin * 2 + 2 or rect.height() <= margin * 2 + 2:
            return qrectf_cls(0, 0, 0, 0), qrectf_cls(0, 0, 0, 0)

        c = rect.adjusted(margin, margin, -margin, -margin)
        available_w = max(1.0, float(c.width()))
        available_h = max(1.0, float(c.height()))
        zoom = self._preview_zoom_factor()
        body_w_mm = max(1.0, float(getattr(self.profile, 'body_w_mm', 1.0) or 1.0))
        body_h_mm = max(1.0, float(getattr(self.profile, 'body_h_mm', 1.0) or 1.0))
        screen_w_mm = max(1.0, float(getattr(self.profile, 'screen_w_mm', body_w_mm) or body_w_mm))
        screen_h_mm = max(1.0, float(getattr(self.profile, 'screen_h_mm', body_h_mm) or body_h_mm))

        if self.actual_size:
            px = max(0.01, self._px_per_mm())
            base_body_w = max(1, min(int(round(body_w_mm * px)), 8192))
            base_body_h = max(1, min(int(round(body_h_mm * px)), 8192))
        else:
            scale = min(available_w / body_w_mm, available_h / body_h_mm)
            px = max(0.01, min(float(scale), 128.0))
            base_body_w = max(1, min(int(round(body_w_mm * px)), int(max(1.0, available_w))))
            base_body_h = max(1, min(int(round(body_h_mm * px)), int(max(1.0, available_h))))

        body_w = max(1, min(int(round(base_body_w * zoom)), 8192))
        body_h = max(1, min(int(round(base_body_h * zoom)), 8192))
        scaled_px = px * zoom

        x = float(c.x()) + max(0.0, (available_w - float(body_w)) / 2.0)
        y = float(c.y()) + max(0.0, (available_h - float(body_h)) / 2.0)
        body_rect = qrectf_cls(x, y, float(body_w), float(body_h))

        sw = max(1, min(int(round(screen_w_mm * scaled_px)), body_w))
        sh = max(1, min(int(round(screen_h_mm * scaled_px)), body_h))
        # Use the local numeric values instead of asking QRectF back for them.
        # The lightweight PySide6 stubs used by smoke tests may return sentinel
        # objects from QRectF.x()/width()/height(), even when QRectF was
        # constructed with numeric arguments. Keeping the arithmetic on plain
        # floats preserves real Qt behavior while avoiding stub-only TypeError.
        sx = x + max(0.0, (float(body_w) - float(sw)) / 2.0)
        vertical_bezel = max(0.0, float(body_h) - float(sh))
        top_bezel_ratio = max(0.0, min(1.0, float(getattr(self.profile, 'top_bezel_ratio', 0.34))))
        sy = y + vertical_bezel * top_bezel_ratio
        return body_rect, qrectf_cls(sx, sy, float(sw), float(sh))
