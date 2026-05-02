from __future__ import annotations

"""XTC/XTCH container parsing and page image conversion helpers for GUI Studio.

This module is split out from ``tategakiXTC_gui_studio.py`` while the
entry-point module re-exports the same public names for compatibility.
"""

import logging
import struct
from dataclasses import dataclass
from io import BytesIO
from typing import Any, TYPE_CHECKING

from PySide6.QtGui import QImage

from tategakiXTC_numpy_helper import get_cached_numpy_module

APP_LOGGER = logging.getLogger('tategaki_xtc')

np = None  # type: ignore[assignment]
_NUMPY_IMPORT_ATTEMPTED = False
_XTCH_SHADE_LUT = None


def _get_numpy_module() -> Any:
    global np, _NUMPY_IMPORT_ATTEMPTED
    np, _NUMPY_IMPORT_ATTEMPTED = get_cached_numpy_module(np, _NUMPY_IMPORT_ATTEMPTED)
    return np


class _LazyPillowModule:
    def __init__(self, module_name: str) -> None:
        self._module_name = module_name
        self._module: Any | None = None

    def _load(self) -> Any:
        if self._module is None:
            self._module = __import__(f'PIL.{self._module_name}', fromlist=[self._module_name])
        return self._module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)


if TYPE_CHECKING:
    from PIL import Image as Image  # pragma: no cover
else:
    Image = _LazyPillowModule('Image')


@dataclass
class XtcPage:
    offset: int
    length: int
    width: int
    height: int


# ─────────────────────────────────────────────────────────
# XTC パーサ
# ─────────────────────────────────────────────────────────

def parse_xtc_pages(data: bytes) -> list[XtcPage]:
    if len(data) < 48 or data[:4] not in {b'XTC\x00', b'XTCH'}:
        raise RuntimeError('XTC/XTCHファイルのヘッダが不正です。')

    container_mark = data[:4]
    expected_blob_magic = b'XTH\x00' if container_mark == b'XTCH' else b'XTG\x00'
    count = struct.unpack_from('<H', data, 6)[0]
    idx_off = struct.unpack_from('<Q', data, 24)[0] or 48
    data_off = struct.unpack_from('<Q', data, 32)[0]

    if idx_off < 48 or idx_off > len(data):
        raise RuntimeError('XTCページテーブルの開始位置が不正です。')

    entry_size = 16
    if count > 0 and data_off > idx_off:
        span = data_off - idx_off
        if span >= count * 16 and span % count == 0:
            candidate = span // count
            if candidate >= 16:
                entry_size = candidate

    table_end = idx_off + count * entry_size
    if table_end > len(data):
        raise RuntimeError('XTCページテーブルが途中で切れています。')

    min_data_offset = max(idx_off + count * entry_size, data_off or 0)
    pages: list[XtcPage] = []
    prev_end = min_data_offset
    for i in range(count):
        off = idx_off + i * entry_size
        page = XtcPage(
            offset=struct.unpack_from('<Q', data, off)[0],
            length=struct.unpack_from('<I', data, off + 8)[0],
            width=struct.unpack_from('<H', data, off + 12)[0],
            height=struct.unpack_from('<H', data, off + 14)[0],
        )
        end = page.offset + page.length
        invalid = (
            page.length <= 0
            or page.width <= 0
            or page.height <= 0
            or page.offset < min_data_offset
            or page.offset < prev_end
            or end > len(data)
        )
        if not invalid:
            blob_header = data[page.offset: page.offset + min(22, page.length)]
            if len(blob_header) < 22:
                invalid = True
            else:
                magic = blob_header[:4]
                blob_w = struct.unpack_from('<H', blob_header, 4)[0]
                blob_h = struct.unpack_from('<H', blob_header, 6)[0]
                payload_len = struct.unpack_from('<I', blob_header, 10)[0]
                invalid = (
                    magic != expected_blob_magic
                    or blob_w != page.width
                    or blob_h != page.height
                    or payload_len <= 0
                    or (22 + payload_len) != page.length
                )
        if invalid:
            if pages:
                APP_LOGGER.warning(
                    'XTC/XTCHページ索引またはページデータの不整合を検出したため、有効な先頭 %s / %s ページのみを読み込みます。停止ページ: %s offset=%s length=%s file_size=%s',
                    len(pages), count, i + 1, page.offset, page.length, len(data)
                )
                break
            raise RuntimeError(f'XTCページ {i + 1} のオフセット、長さ、またはページデータが不正です。')
        pages.append(page)
        prev_end = end

    if not pages:
        raise RuntimeError('XTC/XTCH内に有効なページが見つかりませんでした。')
    return pages


def _pil_image_to_qimage(img: Image.Image) -> QImage:
    bio = BytesIO()
    img.save(bio, format='PNG')
    qimg = QImage.fromData(bio.getvalue(), 'PNG')
    if qimg.isNull():
        raise RuntimeError('画像データのQImage変換に失敗しました。')
    return qimg.copy()


_XTCH_SHADE_MAP = (255, 85, 170, 0)


def _get_xtch_shade_lut(np_module: Any) -> Any:
    global _XTCH_SHADE_LUT
    if _XTCH_SHADE_LUT is None:
        _XTCH_SHADE_LUT = np_module.array(_XTCH_SHADE_MAP, dtype=np_module.uint8)
    return _XTCH_SHADE_LUT


def xtg_blob_to_qimage(blob: bytes) -> QImage:
    if len(blob) < 22 or blob[:4] != b'XTG\x00':
        raise RuntimeError('XTC/XTCH内ページデータが不正です。')
    width = struct.unpack_from('<H', blob, 4)[0]
    height = struct.unpack_from('<H', blob, 6)[0]
    if width <= 0 or height <= 0:
        raise RuntimeError('XTC内ページのサイズ情報が不正です。')
    row_bytes = (width + 7) // 8
    expected_payload_len = row_bytes * height
    payload = blob[22:22 + expected_payload_len]
    if len(payload) != expected_payload_len:
        raise RuntimeError('XTC内ページデータが途中で切れています。')

    img = Image.frombytes('1', (width, height), payload).convert('L')
    return _pil_image_to_qimage(img)


def xth_blob_to_qimage(blob: bytes) -> QImage:
    if len(blob) < 22 or blob[:4] != b'XTH\x00':
        raise RuntimeError('XTCH内ページデータが不正です。')
    width = struct.unpack_from('<H', blob, 4)[0]
    height = struct.unpack_from('<H', blob, 6)[0]
    if width <= 0 or height <= 0:
        raise RuntimeError('XTCH内ページのサイズ情報が不正です。')
    plane_size = ((width * height) + 7) // 8
    expected_payload_len = plane_size * 2
    payload = blob[22:22 + expected_payload_len]
    if len(payload) != expected_payload_len:
        raise RuntimeError('XTCH内ページデータが途中で切れています。')
    plane1 = payload[:plane_size]
    plane2 = payload[plane_size:]
    pixel_count = width * height

    np_module = _get_numpy_module()
    if np_module is not None and pixel_count >= 256:
        plane1_bits = np_module.unpackbits(np_module.frombuffer(plane1, dtype=np_module.uint8), bitorder='big')[:pixel_count]
        plane2_bits = np_module.unpackbits(np_module.frombuffer(plane2, dtype=np_module.uint8), bitorder='big')[:pixel_count]
        seq = ((plane1_bits << 1) | plane2_bits).astype(np_module.uint8, copy=False)
        values = seq.reshape(width, height).T[:, ::-1]
        shades = _get_xtch_shade_lut(np_module)[values]
        img = Image.frombytes('L', (width, height), shades.tobytes())
        return _pil_image_to_qimage(img)

    seq = bytearray(pixel_count)
    bit_index = 0
    for byte_index in range(plane_size):
        byte1 = plane1[byte_index]
        byte2 = plane2[byte_index]
        for shift in range(7, -1, -1):
            if bit_index >= pixel_count:
                break
            seq[bit_index] = _XTCH_SHADE_MAP[((byte1 >> shift) & 1) << 1 | ((byte2 >> shift) & 1)]
            bit_index += 1

    pixels = bytearray(pixel_count)
    seq_offset = 0
    for rev_x in range(width):
        x = width - 1 - rev_x
        row_offset = x
        column = seq[seq_offset:seq_offset + height]
        for shade in column:
            pixels[row_offset] = shade
            row_offset += width
        seq_offset += height

    img = Image.frombytes('L', (width, height), bytes(pixels))
    return _pil_image_to_qimage(img)


def xt_page_blob_to_qimage(blob: bytes) -> QImage:
    mark = blob[:4] if len(blob) >= 4 else b''
    if mark == b'XTG\x00':
        return xtg_blob_to_qimage(blob)
    if mark == b'XTH\x00':
        return xth_blob_to_qimage(blob)
    raise RuntimeError('未対応のページ形式です。')


__all__ = [
    'XtcPage',
    'parse_xtc_pages',
    'xtg_blob_to_qimage',
    'xth_blob_to_qimage',
    'xt_page_blob_to_qimage',
]
