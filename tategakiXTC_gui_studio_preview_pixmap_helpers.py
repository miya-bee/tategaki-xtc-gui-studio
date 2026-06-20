from __future__ import annotations

import base64
from typing import Any, Callable

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap

from tategakiXTC_gui_studio_xtc_io import xt_page_blob_to_qimage
import tategakiXTC_worker_logic as worker_logic


def _decorate_font_view_pixmap(
    self: Any,
    pix: object,
    *,
    page_width: int = 0,
    page_height: int = 0,
) -> object:
    """Fontビューのプレビューを実機に近い見た目へ寄せるための装飾。

    - ガイドOFF: 青い帯は出さない（枠線だけ）
    - ガイドON : 実機ビューと同様に非描画域の帯 + 点線ガイドを重ねる

    Qt が無い環境（回帰テスト用スタブ）では、そのまま返す。
    """
    dark = bool(getattr(self, 'current_ui_theme', 'light') == 'dark')
    show_guides = False
    try:
        if hasattr(self, 'guides_check') and hasattr(self.guides_check, 'isChecked'):
            show_guides = bool(self.guides_check.isChecked())
    except Exception:
        show_guides = False

    try:
        out = pix.copy()
    except Exception:
        out = pix

    try:
        painter = QPainter(out)
        painter.setRenderHint(QPainter.Antialiasing, True)
        screen_border = QColor('#6D8295') if dark else QColor('#94A3B3')
        painter.setPen(QPen(screen_border, 1.0))
        rect = out.rect().adjusted(0, 0, -1, -1)
        painter.drawRect(rect)

        if show_guides:
            ref_w = max(1, int(page_width or out.width() or 1))
            ref_h = max(1, int(page_height or out.height() or 1))
            guide_rect = self._guide_rect_for_preview_rect(rect, ref_w, ref_h)
            if guide_rect != rect:
                guide_band = QPainterPath()
                guide_band.addRect(rect)
                guide_band.addRect(guide_rect)
                painter.fillPath(
                    guide_band,
                    QColor(75, 152, 255, 48) if not dark else QColor(114, 173, 255, 40),
                )
                guide_color = QColor(114, 173, 255, 120) if dark else QColor(75, 152, 255, 110)
                painter.setPen(QPen(guide_color, 1, Qt.DashLine))
                painter.drawRect(guide_rect)
        try:
            painter.end()
        except Exception:
            pass
    except Exception:
        return out
    return out

def _preview_pixmap_from_png_bytes(
    self: Any,
    raw: bytes,
    *,
    qimage_cls: Any = QImage,
    qpixmap_cls: Any = QPixmap,
) -> object:
    qimg = qimage_cls.fromData(raw, 'PNG')
    qimg_is_null = getattr(qimg, 'isNull', None)
    if callable(qimg_is_null) and qimg_is_null():
        raise RuntimeError('プレビュー画像の読み込みに失敗しました。')
    pix = qpixmap_cls.fromImage(qimg)
    pix_is_null = getattr(pix, 'isNull', None)
    if callable(pix_is_null) and pix_is_null():
        raise RuntimeError('プレビュー画像の描画準備に失敗しました。')
    return pix

def _apply_preview_pixmap(self: Any, pix: object) -> None:
    try:
        orig_w = max(1, int(pix.width()))
        orig_h = max(1, int(pix.height()))
    except Exception:
        orig_w = orig_h = 0
    target = self._font_preview_target_size()
    if target.width() < 10 or target.height() < 10:
        target = QSize(480, 720)
    scaled = pix.scaled(target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    scaled = self._decorate_font_view_pixmap(scaled, page_width=orig_w, page_height=orig_h)
    scaled_size = scaled.size()
    self._last_font_preview_scaled_size = (int(scaled_size.width()), int(scaled_size.height()))
    try:
        self.preview_label.setMinimumSize(scaled_size)
        self.preview_label.setMaximumSize(scaled_size)
    except Exception:
        pass
    self.preview_label.resize(scaled_size)
    self.preview_label.setPixmap(scaled)
    self.preview_label.setText('')
    self._sync_font_preview_scroll_placement(reset_horizontal=True)

def _apply_preview_png_bytes(self: Any, raw: bytes) -> None:
    self._apply_preview_pixmap(self._preview_pixmap_from_png_bytes(raw))

def _apply_preview_page_base64_to_label(self: Any, page_b64: object, *, cache_key: object = None) -> None:
    img_b64 = self._coerce_preview_base64_text(page_b64)
    if not img_b64:
        self._show_preview_message('プレビューを生成できませんでした')
        return
    pix = self._cached_font_preview_page_pixmap(cache_key)
    if pix is None:
        raw = base64.b64decode(img_b64, validate=True)
        pix = self._preview_pixmap_from_png_bytes(raw)
        self._store_font_preview_page_pixmap(cache_key, pix)
    self._apply_preview_pixmap(pix)

def _render_current_xtc_page_in_font_view(
    self: Any,
    *,
    refresh_navigation: bool = True,
    qpixmap_cls: Any = QPixmap,
    xt_page_blob_to_qimage_func: Callable[[Any], Any] = xt_page_blob_to_qimage,
) -> bool:
    """Render the loaded XTC/XTCH page into the font-view preview area.

    File-viewer mode owns both the device view and font view.  When old
    conversion preview pages remain cached, switching back to font view must
    still show the opened XTC/XTCH page instead of a stale generated preview.
    """
    blob = self._current_xtc_page_blob(force_loaded_xtc=True)
    if blob is None:
        return False
    cache_key = self._xtc_page_qimage_cache_key()
    qimg = self._cached_xtc_page_qimage(cache_key)
    if qimg is None:
        qimg = xt_page_blob_to_qimage_func(blob)
        self._store_xtc_page_qimage(cache_key, qimg)
    pix = qpixmap_cls.fromImage(qimg)
    pix_is_null = getattr(pix, 'isNull', None)
    if callable(pix_is_null) and pix_is_null():
        raise RuntimeError('ファイルビューワー画像の描画準備に失敗しました。')
    self._apply_preview_pixmap(pix)
    try:
        self._sync_loaded_xtc_display_context_for_device_view()
    except Exception:
        pass
    try:
        self._update_preview_status_label(self._ui_text('ファイルビューワーモード: XTC/XTCHを直接表示中です'))
    except Exception:
        pass
    if refresh_navigation:
        try:
            self.update_navigation_ui()
        except Exception:
            pass
    return True


def render_current_preview_page(self: Any) -> None:
    pages = self._runtime_preview_pages()
    if not pages:
        self._show_preview_message('プレビューを生成できませんでした')
        return
    should_sync_display_context = self._normalized_main_view_mode(
        getattr(self, 'main_view_mode', 'font')
    ) == 'font'
    if should_sync_display_context:
        try:
            self._sync_preview_display_context_for_font_view()
        except Exception:
            pass
    current_index = worker_logic._int_config_value(
        {'value': getattr(self, 'current_preview_page_index', 0)},
        'value',
        0,
    )
    current_index = max(0, min(len(pages) - 1, current_index))
    self.current_preview_page_index = current_index
    try:
        self._apply_preview_page_base64_to_label(
            pages[current_index],
            cache_key=self._font_preview_page_pixmap_cache_key(current_index),
        )
        self._refresh_successful_preview_render_status()
    except Exception as exc:
        self._show_preview_message(f'プレビュー表示エラー\n{exc}')
        status_message = self._render_failure_status_message('プレビュー表示エラー', exc)
        font_view_visible = self._normalized_main_view_mode(
            getattr(self, 'main_view_mode', 'font')
        ) == 'font'
        reflect_failure_in_status = font_view_visible or not self._visible_render_failure_status_text()
        try:
            self._update_preview_status_label(status_message)
        except Exception:
            pass
        self._append_log_with_status_fallback(
            status_message,
            reflect_in_status=reflect_failure_in_status,
        )
