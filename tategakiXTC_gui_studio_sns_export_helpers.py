from __future__ import annotations

"""SNS/share PNG export helpers for ``tategakiXTC_gui_studio``."""

import base64
from pathlib import Path
from typing import Any

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QFileDialog

from tategakiXTC_gui_studio_xtc_io import xt_page_blob_to_qimage
import tategakiXTC_worker_logic as worker_logic


def _coerce_page_index(value: object, *, total: int) -> int:
    try:
        index = int(value)
    except Exception:
        index = 0
    if total <= 0:
        return 0
    return max(0, min(total - 1, index))


def _qimage_from_preview_base64(page_b64: object) -> QImage:
    text = str(page_b64 if page_b64 is not None else '').strip()
    if not text:
        raise RuntimeError('保存できるプレビュー画像がありません。')
    try:
        raw = base64.b64decode(text, validate=True)
    except Exception as exc:
        raise RuntimeError(f'プレビュー画像の読み込みに失敗しました: {exc}') from exc
    image = QImage.fromData(raw, 'PNG')
    if image.isNull():
        raise RuntimeError('プレビュー画像の読み込みに失敗しました。')
    return image


def current_share_page_image(self: Any) -> tuple[QImage, int, int]:
    """Return the current share source image and 1-based page/total counts."""
    prefer_loaded_xtc = False
    try:
        prefer_loaded_xtc = bool(self._is_file_viewer_mode_active())
    except Exception:
        prefer_loaded_xtc = False

    preview_pages = []
    try:
        preview_pages = list(self._runtime_preview_pages())
    except Exception:
        preview_pages = []
    if preview_pages and not prefer_loaded_xtc:
        index = _coerce_page_index(getattr(self, 'current_preview_page_index', 0), total=len(preview_pages))
        return _qimage_from_preview_base64(preview_pages[index]), index + 1, len(preview_pages)

    blob = None
    try:
        blob = self._current_xtc_page_blob(force_loaded_xtc=True)
    except TypeError:
        try:
            blob = self._current_xtc_page_blob()
        except Exception:
            blob = None
    except Exception:
        blob = None
    if blob is not None:
        image = xt_page_blob_to_qimage(blob)
        if image.isNull():
            raise RuntimeError('XTC/XTCHページ画像の読み込みに失敗しました。')
        total = 0
        try:
            total = int(self._xtc_page_count())
        except Exception:
            total = len(getattr(self, 'xtc_pages', []) or [])
        index = _coerce_page_index(getattr(self, 'current_page_index', 0), total=max(1, total))
        return image, index + 1, max(1, total)

    raise RuntimeError('保存できるプレビュー画像がありません。先にプレビューを生成するか、XTC/XTCHを開いてください。')


def _source_stem_for_share_export(self: Any) -> str:
    for candidate in (
        getattr(self, 'current_xtc_display_name', ''),
        getattr(self, '_last_loaded_xtc_path', ''),
        worker_logic.normalize_target_path_text(getattr(getattr(self, 'target_edit', None), 'text', lambda: '')()),
    ):
        text = str(candidate or '').strip()
        if not text:
            continue
        try:
            stem = Path(text).stem
        except Exception:
            stem = text
        stem = ''.join(ch if ch not in '<>:"/\\|?*' else '_' for ch in stem).strip(' ._')
        if stem:
            return stem[:80]
    return 'tategaki_sample'


def default_share_png_path(self: Any, *, page_number: int = 1) -> Path:
    stem = _source_stem_for_share_export(self)
    default_dir = ''
    try:
        default_dir = worker_logic.normalize_target_path_text(getattr(self, 'selected_output_dir', ''))
    except Exception:
        default_dir = ''
    if not default_dir:
        try:
            default_dir = str(Path(worker_logic.normalize_target_path_text(self.target_edit.text())).parent)
        except Exception:
            default_dir = ''
    base_dir = Path(default_dir) if default_dir and default_dir not in ('.', '') else Path.home()
    return base_dir / f'{stem}_page{max(1, int(page_number)):03d}_share.png'


def build_framed_share_image(page_image: QImage, *, page_number: int = 1, total_pages: int = 1) -> QImage:
    if page_image.isNull():
        raise RuntimeError('保存できるプレビュー画像がありません。')
    source = page_image.convertToFormat(QImage.Format_ARGB32)
    page_w = max(1, int(source.width()))
    page_h = max(1, int(source.height()))
    pad_x = max(40, page_w // 18)
    header_h = max(72, page_h // 18)
    footer_h = max(46, page_h // 32)
    out_w = page_w + pad_x * 2
    out_h = page_h + header_h + footer_h
    out = QImage(out_w, out_h, QImage.Format_ARGB32)
    out.fill(QColor('#F4F1E8'))

    painter = QPainter(out)
    try:
        painter.setRenderHint(QPainter.Antialiasing, True)
        title_font = QFont()
        title_font.setPointSize(max(12, min(24, page_w // 36)))
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor('#333333'))
        title_rect = QRect(pad_x, 12, page_w, max(28, header_h - 18))
        painter.drawText(title_rect, Qt.AlignLeft | Qt.AlignVCenter, 'TategakiXTC GUI Studio')

        page_x = pad_x
        page_y = header_h
        shadow_offset = max(4, min(12, page_w // 80))
        painter.fillRect(page_x + shadow_offset, page_y + shadow_offset, page_w, page_h, QColor(0, 0, 0, 36))
        painter.drawImage(page_x, page_y, source)
        painter.setPen(QPen(QColor('#333333'), 2))
        painter.drawRect(page_x, page_y, page_w - 1, page_h - 1)

        footer_font = QFont()
        footer_font.setPointSize(max(10, min(16, page_w // 54)))
        painter.setFont(footer_font)
        painter.setPen(QColor('#555555'))
        footer_text = f'Page {max(1, int(page_number))} / {max(1, int(total_pages))}'
        painter.drawText(QRect(pad_x, page_y + page_h + 6, page_w, max(20, footer_h - 10)), Qt.AlignRight | Qt.AlignTop, footer_text)
    finally:
        painter.end()
    return out


def export_current_preview_share_png(self: Any) -> bool:
    try:
        page_image, page_number, total_pages = current_share_page_image(self)
        share_image = build_framed_share_image(page_image, page_number=page_number, total_pages=total_pages)
    except Exception as exc:
        show_warning = getattr(self, '_show_warning_dialog_with_status_fallback', None)
        if callable(show_warning):
            show_warning(
                'PNG保存エラー',
                str(exc),
                fallback_status_message=str(exc),
            )
        return False

    default_path = default_share_png_path(self, page_number=page_number)
    path, _ = QFileDialog.getSaveFileName(
        self,
        self._ui_text('PNGを保存'),
        str(default_path),
        'PNG Image (*.png);;All Files (*.*)',
    )
    if not path:
        return False
    output_path = Path(path)
    if output_path.suffix.lower() != '.png':
        output_path = output_path.with_suffix('.png')
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not share_image.save(str(output_path), 'PNG'):
            raise RuntimeError('PNGファイルを保存できませんでした。')
    except Exception as exc:
        show_warning = getattr(self, '_show_warning_dialog_with_status_fallback', None)
        if callable(show_warning):
            show_warning(
                'PNG保存エラー',
                str(exc),
                fallback_status_message=str(exc),
            )
        return False
    self._show_ui_status_message_unless_render_failure_visible(
        f'PNGを保存しました: {output_path}',
        5000,
    )
    return True
