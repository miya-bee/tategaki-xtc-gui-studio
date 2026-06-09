"""
tategakiXTC_gui_core_xtc.py — 画像フィルタ / XTC・XTCH コンテナ出力

`tategakiXTC_gui_core.py` から分離した XTC-family バイト列生成と
コンテナ書き出し実装。互換性維持のため、gui_core 側の re-export /
monkey patch を各入口で同期する。
"""
from __future__ import annotations

import hashlib
import os
import struct
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, BinaryIO, Callable, Literal, Sequence

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals'}
_CORE_SYNC_VERSION = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch を XTC 実装へ反映する。"""
    global _CORE_SYNC_VERSION
    version = core_sync_version(_core)
    if not force and _CORE_SYNC_VERSION == version:
        return
    for _name, _value in vars(_core).items():
        if _name.startswith('__') or _name in _CORE_SYNC_EXCLUDED_NAMES:
            continue
        globals()[_name] = _value
    _CORE_SYNC_VERSION = version


_refresh_core_globals()


# ==========================================
# --- 画像フィルタ & XTG/XTC 変換 ---
# ==========================================



# ==========================================
# --- Page number overlay helper ---
# ==========================================

def _page_number_overlay_enabled(args: ConversionArgs | None) -> bool:
    return bool(args is not None and getattr(args, 'page_number_enabled', False))


def _progress_bar_overlay_enabled(args: ConversionArgs | None) -> bool:
    return bool(args is not None and getattr(args, 'progress_bar_enabled', False))


def _progress_bar_overlay_position(args: ConversionArgs | None) -> str:
    raw_value = getattr(args, 'progress_bar_position', 'center') if args is not None else 'center'
    value = str(raw_value or 'center').strip().lower()
    return value if value in {'center', 'left'} else 'center'


def _progress_bar_overlay_reserve_margin(args: ConversionArgs | None) -> int:
    return 10 if _progress_bar_overlay_enabled(args) else 0


def _page_number_overlay_font_size(args: ConversionArgs | None) -> int:
    try:
        value = int(getattr(args, 'page_number_font_size', 12) if args is not None else 12)
    except Exception:
        value = 12
    if value < 1:
        raise ValueError('ページ番号フォントサイズは 1 以上である必要があります。')
    if value >= 30:
        raise ValueError('ページ番号フォントサイズは 30 未満である必要があります。')
    return value


def _load_page_number_overlay_font(args: ConversionArgs | None) -> Any:
    size = _page_number_overlay_font_size(args)
    font_value = ''
    if args is not None:
        font_value = str(getattr(args, 'page_number_font_file', '') or getattr(args, 'font_file', '') or '').strip()
    if font_value:
        loader = globals().get('load_truetype_font')
        if callable(loader):
            try:
                return loader(font_value, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _measure_page_number_text(draw: Any, text: str, font: Any) -> tuple[int, int, int, int]:
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
    except Exception:
        try:
            width, height = draw.textsize(text, font=font)
            return 0, 0, int(width), int(height)
        except Exception:
            size = max(1, len(text)) * 8
            return 0, 0, size, 10


def _page_number_overlay_layout(
    canvas: Image.Image,
    args: ConversionArgs | None,
    page_index: int,
    total_pages: int,
) -> tuple[str, Any, int, int, tuple[int, int, int, int]] | None:
    """Return the page-number draw payload and occupied rectangle.

    The rectangle is used by the shared bottom-overlay layout guard so progress
    bars do not overwrite the right-aligned page number when both overlays are
    enabled.  Coordinates are inclusive and include a small safety padding.
    """
    if not _page_number_overlay_enabled(args):
        return None
    try:
        current = int(page_index)
        total = int(total_pages)
    except Exception:
        return None
    if current <= 0 or total <= 0:
        return None
    text = f'{current}/{total}'
    width, height = canvas.size
    draw = ImageDraw.Draw(canvas)
    font = _load_page_number_overlay_font(args)
    left, top, right, bottom = _measure_page_number_text(draw, text, font)
    text_w = max(1, right - left)
    text_h = max(1, bottom - top)
    font_size = _page_number_overlay_font_size(args)
    try:
        margin_b = max(0, int(getattr(args, 'margin_b', font_size + 1) if args is not None else font_size + 1))
    except Exception:
        margin_b = font_size + 1
    try:
        margin_r = max(0, int(getattr(args, 'margin_r', 0) if args is not None else 0))
    except Exception:
        margin_r = 0
    bottom_band_top = max(0, height - max(margin_b, font_size + 1))
    x = max(0, width - margin_r - text_w - max(1, font_size // 6))
    y = bottom_band_top + max(0, (height - bottom_band_top - text_h) // 2) - top
    y = max(0, min(height - text_h, y))
    pad = max(2, font_size // 6)
    rect = (
        max(0, x + left - pad),
        max(0, y + top - pad),
        min(width - 1, x + right + pad),
        min(height - 1, y + bottom + pad),
    )
    return text, font, x, y, rect


def _bottom_overlay_rects_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return not (a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1])


def _fit_progress_bar_to_bottom_overlay_safe_area(
    *,
    x: int,
    bar_width: int,
    center_y: int,
    canvas_width: int,
    marker_height: int,
    avoid_rect: tuple[int, int, int, int] | None,
) -> tuple[int, int]:
    """Fit the progress bar so it does not occupy the page-number rectangle."""
    min_width = 8
    bar_width = max(1, min(int(bar_width), max(1, int(canvas_width))))
    x = max(0, min(int(x), max(0, canvas_width - bar_width)))
    if avoid_rect is None or canvas_width <= 0:
        return x, bar_width
    marker_top = max(0, center_y - marker_height // 2)
    marker_bottom = marker_top + marker_height - 1
    bar_rect = (x, marker_top, x + bar_width - 1, marker_bottom)
    if not _bottom_overlay_rects_overlap(bar_rect, avoid_rect):
        return x, bar_width

    gap = 3
    left_max_end = max(-1, avoid_rect[0] - gap - 1)
    available_width = left_max_end + 1
    if available_width >= min_width:
        fitted_width = min(bar_width, available_width)
        fitted_x = min(x, max(0, left_max_end - fitted_width + 1))
        fitted_x = max(0, fitted_x)
        return fitted_x, max(min_width, min(fitted_width, canvas_width - fitted_x))

    right_start = min(canvas_width, avoid_rect[2] + gap + 1)
    right_width = canvas_width - right_start
    if right_width >= min_width:
        fitted_width = min(bar_width, right_width)
        return right_start, fitted_width

    return x, max(1, min(bar_width, canvas_width - x))


def apply_page_number_overlay_to_canvas(canvas: Image.Image, args: ConversionArgs | None, page_index: int, total_pages: int) -> Image.Image:
    """Draw ``current/total`` at the bottom-right of a prepared page canvas."""
    if not _page_number_overlay_enabled(args):
        return canvas
    work = canvas if canvas.mode == 'L' else canvas.convert('L')
    if work is canvas:
        work = canvas.copy()
    layout = _page_number_overlay_layout(work, args, page_index, total_pages)
    if layout is None:
        return work
    text, font, x, y, _rect = layout
    draw = ImageDraw.Draw(work)
    draw.text((x, y), text, fill=0, font=font)
    return work

def apply_progress_bar_overlay_to_canvas(
    canvas: Image.Image,
    args: ConversionArgs | None,
    page_index: int,
    total_pages: int,
    *,
    avoid_rect: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Draw a compact reading progress bar at the bottom of a prepared page canvas."""
    if not _progress_bar_overlay_enabled(args):
        return canvas
    try:
        current = int(page_index)
        total = int(total_pages)
    except Exception:
        return canvas
    if current <= 0 or total <= 0:
        return canvas
    ratio = max(0.0, min(1.0, float(current) / float(total)))
    work = canvas if canvas.mode == 'L' else canvas.convert('L')
    if work is canvas:
        work = canvas.copy()
    width, height = work.size
    draw = ImageDraw.Draw(work)
    try:
        margin_b = max(0, int(getattr(args, 'margin_b', 10) if args is not None else 10))
    except Exception:
        margin_b = 10
    try:
        margin_l = max(0, int(getattr(args, 'margin_l', 0) if args is not None else 0))
    except Exception:
        margin_l = 0
    bar_width = max(8, int(round(width * 0.40)))
    track_height = 1
    progress_height = 3
    marker_height = 5
    reserve = max(1, min(height, max(margin_b, _progress_bar_overlay_reserve_margin(args))))
    bottom_band_top = max(0, height - reserve)
    center_y = bottom_band_top + max(0, (height - bottom_band_top) // 2)
    center_y = max(0, min(height - 1, center_y))
    position = _progress_bar_overlay_position(args)
    if position == 'left':
        x = max(0, margin_l)
    else:
        x = max(0, (width - bar_width) // 2)
    x, bar_width = _fit_progress_bar_to_bottom_overlay_safe_area(
        x=x,
        bar_width=bar_width,
        center_y=center_y,
        canvas_width=width,
        marker_height=marker_height,
        avoid_rect=avoid_rect,
    )
    x_end = x + bar_width - 1
    # Tategaki books progress from right to left.  Keep the thin full track
    # visible across the whole bar, but draw the thick read portion from the
    # right edge toward the left so it matches vertical Japanese page flow.
    marker_x = x_end - int(round((bar_width - 1) * ratio))
    marker_x = max(x, min(x_end, marker_x))
    progress_top = max(0, center_y - progress_height // 2)
    progress_bottom = min(height - 1, progress_top + progress_height - 1)
    marker_top = max(0, center_y - marker_height // 2)
    marker_bottom = min(height - 1, marker_top + marker_height - 1)
    draw.line([(x, center_y), (x_end, center_y)], fill=0, width=track_height)
    draw.rectangle([marker_x, progress_top, x_end, progress_bottom], fill=0)
    draw.line([(marker_x, marker_top), (marker_x, marker_bottom)], fill=0, width=1)
    return work


def apply_bottom_overlays_to_canvas(canvas: Image.Image, args: ConversionArgs | None, page_index: int, total_pages: int) -> Image.Image:
    """Apply bottom overlays in a collision-safe order.

    The progress bar is laid out first while reserving the page-number rectangle;
    the page number is then drawn last so it remains the priority overlay.
    """
    if not (_page_number_overlay_enabled(args) or _progress_bar_overlay_enabled(args)):
        return canvas
    work = canvas if canvas.mode == 'L' else canvas.convert('L')
    if work is canvas:
        work = canvas.copy()
    page_layout = _page_number_overlay_layout(work, args, page_index, total_pages)
    avoid_rect = page_layout[4] if page_layout is not None else None
    work = apply_progress_bar_overlay_to_canvas(work, args, page_index, total_pages, avoid_rect=avoid_rect)
    if page_layout is not None:
        draw = ImageDraw.Draw(work)
        text, font, x, y, _rect = page_layout
        draw.text((x, y), text, fill=0, font=font)
    return work


def _prepare_canvas_image(img: Image.Image, w: int, h: int) -> Image.Image:
    if img.mode == 'L' and img.size == (w, h):
        return img
    work = img if img.mode == 'L' else img.convert('L')
    if work.size != (w, h):
        work = work.copy()
        work.thumbnail((w, h), Image.Resampling.LANCZOS)
    background = Image.new('L', (w, h), 255)
    offset = ((w - work.width) // 2, (h - work.height) // 2)
    background.paste(work, offset)
    return background


def _clamp_u8(value: int) -> int:
    if value < 0:
        return 0
    if value > 255:
        return 255
    return value


@lru_cache(maxsize=64)
def _compute_xtch_thresholds(threshold: int) -> tuple[int, int, int]:
    bias = max(-48, min(48, int(threshold) - 128))
    t1 = max(16, min(96, 64 + bias // 2))
    t2 = max(t1 + 16, min(176, 128 + bias))
    t3 = max(t2 + 16, min(240, 192 + bias // 2))
    return t1, t2, t3


@lru_cache(maxsize=256)
def _xtc_threshold_lut(threshold: int) -> tuple[int, ...]:
    thr = int(threshold)
    return tuple(255 if value > thr else 0 for value in range(256))


@lru_cache(maxsize=64)
def _xtch_quantization_lut(threshold: int) -> tuple[int, ...]:
    t1, t2, t3 = _compute_xtch_thresholds(int(threshold))
    return tuple(_quantize_xtch_value(value, t1, t2, t3) for value in range(256))


@lru_cache(maxsize=1)
def _xtch_plane_value_lut() -> tuple[int, ...]:
    return tuple(0 if value >= 213 else 2 if value >= 128 else 1 if value >= 43 else 3 for value in range(256))


@lru_cache(maxsize=1)
def _invert_u8_lut() -> tuple[int, ...]:
    return tuple(255 - value for value in range(256))


def _invert_grayscale_image(image: Image.Image) -> Image.Image:
    if image.mode == 'L':
        return image.point(_invert_u8_lut(), mode='L')
    return ImageOps.invert(image.convert('L'))


def _quantize_xtch_value(v: int, t1: int, t2: int, t3: int) -> int:
    if v <= t1:
        return 0
    if v <= t2:
        return 85
    if v <= t3:
        return 170
    return 255


def _dither_xtch_grayscale(background: Image.Image, w: int, h: int, t1: int, t2: int, t3: int) -> Image.Image:
    buf = bytearray(background.tobytes())
    row_base = 0
    for _y in range(h):
        next_row_base = row_base + w
        row_end = row_base + w
        for idx in range(row_base, row_end):
            old = buf[idx]
            newv = _quantize_xtch_value(old, t1, t2, t3)
            err = old - newv
            buf[idx] = newv
            x = idx - row_base
            if x + 1 < w:
                right = idx + 1
                buf[right] = _clamp_u8(int(buf[right] + err * 7 / 16))
            if next_row_base < len(buf):
                below = next_row_base + x
                if x > 0:
                    below_left = below - 1
                    buf[below_left] = _clamp_u8(int(buf[below_left] + err * 3 / 16))
                buf[below] = _clamp_u8(int(buf[below] + err * 5 / 16))
                if x + 1 < w:
                    below_right = below + 1
                    buf[below_right] = _clamp_u8(int(buf[below_right] + err * 1 / 16))
        row_base = next_row_base
    return Image.frombytes('L', (w, h), bytes(buf))


def _prepared_canvas_to_xtg_bytes(background: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    row_bytes = (w + 7) // 8
    threshold = int(args.threshold)
    night_mode = bool(getattr(args, 'night_mode', False))
    np_module = _get_numpy_module()
    if not args.dither and np_module is not None and (w * h) >= 256:
        arr = np_module.asarray(background, dtype=np_module.uint8)
        packed = np_module.packbits((arr > threshold).astype(np_module.uint8), axis=1, bitorder='big')
        if night_mode:
            np_module.bitwise_xor(packed, 0xFF, out=packed)
            rem = w & 7
            if rem:
                valid_mask = (0xFF << (8 - rem)) & 0xFF
                packed[:, -1] &= valid_mask
        data = bytearray(packed.tobytes())
    else:
        bw_img = background.convert('1', dither=Image.FLOYDSTEINBERG) if args.dither else background.point(_xtc_threshold_lut(threshold), mode='1')
        data = bytearray(bw_img.tobytes())
        if night_mode:
            for idx in range(len(data)):
                data[idx] ^= 0xFF
            rem = w & 7
            if rem:
                valid_mask = (0xFF << (8 - rem)) & 0xFF
                for row in range(h):
                    data[row * row_bytes + (row_bytes - 1)] &= valid_mask
    md5 = hashlib.md5(data).digest()[:8]
    return struct.pack('<4sHHBBI8s', b'XTG\x00', w, h, 0, 0, len(data), md5) + data


def _prepared_canvas_to_xth_bytes(background: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    threshold = int(args.threshold)
    t1, t2, t3 = _compute_xtch_thresholds(threshold)
    if args.dither:
        gray_img = _dither_xtch_grayscale(background, w, h, t1, t2, t3)
    else:
        gray_img = background.point(_xtch_quantization_lut(threshold), mode='L')
    if getattr(args, 'night_mode', False):
        gray_img = _invert_grayscale_image(gray_img)
    plane_size = ((w * h) + 7) // 8
    plane_value_lut = _xtch_plane_value_lut()

    np_module = _get_numpy_module()
    if np_module is not None and (w * h) >= 256:
        arr = np_module.asarray(gray_img, dtype=np_module.uint8)
        vals = np_module.asarray(plane_value_lut, dtype=np_module.uint8)[arr]
        seq = vals[:, ::-1].T.reshape(-1)
        plane1 = np_module.packbits((seq >> 1) & 1, bitorder='big')
        plane2 = np_module.packbits(seq & 1, bitorder='big')
        data = plane1.tobytes() + plane2.tobytes()
        if len(plane1) != plane_size or len(plane2) != plane_size:
            data = data[:plane_size] + data[plane_size:plane_size * 2]
    else:
        pixels = gray_img.load()
        assert pixels is not None
        plane1 = bytearray(plane_size)
        plane2 = bytearray(plane_size)
        bit_index = 0
        for x in range(w - 1, -1, -1):
            for y in range(h):
                val = plane_value_lut[int(pixels[x, y])]
                byte_index = bit_index >> 3
                shift = 7 - (bit_index & 7)
                if (val >> 1) & 1:
                    plane1[byte_index] |= 1 << shift
                if val & 1:
                    plane2[byte_index] |= 1 << shift
                bit_index += 1
        data = bytes(plane1 + plane2)
    md5 = hashlib.md5(data).digest()[:8]
    return struct.pack('<4sHHBBI8s', b'XTH\x00', w, h, 0, 0, len(data), md5) + data


def canvas_image_to_xt_bytes(background: Image.Image, w: int, h: int, args: ConversionArgs, *, prepared: bool = False) -> bytes:
    _refresh_core_globals()
    canvas = background if prepared else _prepare_canvas_image(background, w, h)
    page_current = getattr(args, '_page_number_current', None)
    page_total = getattr(args, '_page_number_total', None)
    if page_current is not None and page_total is not None:
        canvas = apply_bottom_overlays_to_canvas(canvas, args, page_current, page_total)
    return _prepared_canvas_to_xth_bytes(canvas, w, h, args) if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else _prepared_canvas_to_xtg_bytes(canvas, w, h, args)


def _apply_xtc_filter_prepared(background: Image.Image, dither: bool, threshold: int) -> Image.Image:
    if dither:
        return background.convert("1", dither=Image.FLOYDSTEINBERG)  # type: ignore[attr-defined]
    return background.point(_xtc_threshold_lut(int(threshold)), mode="1")


def _apply_xtch_filter_prepared(background: Image.Image, dither: bool, threshold: int, w: int, h: int) -> Image.Image:
    t1, t2, t3 = _compute_xtch_thresholds(int(threshold))
    if dither:
        return _dither_xtch_grayscale(background, w, h, t1, t2, t3)
    return background.point(_xtch_quantization_lut(int(threshold)), mode='L')


def apply_xtc_filter(img: Image.Image, dither: bool, threshold: int, w: int, h: int) -> Image.Image:
    _refresh_core_globals()
    return _apply_xtc_filter_prepared(_prepare_canvas_image(img, w, h), dither, threshold)


def apply_xtch_filter(img: Image.Image, dither: bool, threshold: int, w: int, h: int) -> Image.Image:
    _refresh_core_globals()
    return _apply_xtch_filter_prepared(_prepare_canvas_image(img, w, h), dither, threshold, w, h)


def png_to_xtg_bytes(img: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    _refresh_core_globals()
    return _prepared_canvas_to_xtg_bytes(_prepare_canvas_image(img, w, h), w, h, args)


def png_to_xth_bytes(img: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    _refresh_core_globals()
    return _prepared_canvas_to_xth_bytes(_prepare_canvas_image(img, w, h), w, h, args)


def _verify_xt_page_blob_header(blob_header: bytes, page_length: int, expected_w: int, expected_h: int, normalized_format: str, page_index: int) -> None:
    if len(blob_header) < 22:
        raise RuntimeError(f'自己検証に失敗しました: ページ {page_index} のページデータヘッダが不足しています。')
    expected_magic = b'XTH\x00' if normalized_format == 'xtch' else b'XTG\x00'
    magic = blob_header[:4]
    if magic != expected_magic:
        raise RuntimeError(
            f'自己検証に失敗しました: ページ {page_index} のデータ種別が不正です。 expected={expected_magic!r} actual={magic!r}'
        )
    blob_w = struct.unpack_from('<H', blob_header, 4)[0]
    blob_h = struct.unpack_from('<H', blob_header, 6)[0]
    payload_len = struct.unpack_from('<I', blob_header, 10)[0]
    if blob_w != expected_w or blob_h != expected_h:
        raise RuntimeError(
            f'自己検証に失敗しました: ページ {page_index} のサイズ情報が不正です。 expected={expected_w}x{expected_h} actual={blob_w}x{blob_h}'
        )
    if payload_len <= 0 or (22 + payload_len) != page_length:
        raise RuntimeError(
            f'自己検証に失敗しました: ページ {page_index} のペイロード長が不正です。 page_length={page_length} payload={payload_len}'
        )



def _verify_xt_container_file(
    path: Path,
    expected_w: int,
    expected_h: int,
    output_format: str,
    expected_count: int | None = None,
    expected_page_specs: Sequence[tuple[int, int, int]] | None = None,
) -> int:
    normalized_format = _normalize_output_format(output_format)
    expected_mark = b'XTCH' if normalized_format == 'xtch' else b'XTC\x00'
    if expected_page_specs is not None:
        expected_count = len(expected_page_specs)
    with open(path, 'rb') as fh:
        fh.seek(0, os.SEEK_END)
        file_size = fh.tell()
        fh.seek(0)
        header = fh.read(48)
        if len(header) < 48:
            raise RuntimeError('自己検証に失敗しました: XTC/XTCHヘッダが途中で切れています。')
        mark = header[:4]
        if mark != expected_mark:
            raise RuntimeError(
                f'自己検証に失敗しました: コンテナ種別が不正です。 expected={expected_mark!r} actual={mark!r}'
            )
        count = struct.unpack_from('<H', header, 6)[0]
        idx_off = struct.unpack_from('<Q', header, 24)[0] or 48
        data_off = struct.unpack_from('<Q', header, 32)[0] or (48 + count * 16)
        if expected_count is not None and count != int(expected_count):
            raise RuntimeError(
                f'自己検証に失敗しました: ページ数が一致しません。 expected={expected_count} actual={count}'
            )
        if expected_page_specs is not None and len(expected_page_specs) != count:
            raise RuntimeError(
                f'自己検証に失敗しました: ページ仕様数が一致しません。 expected={len(expected_page_specs)} actual={count}'
            )
        if count <= 0:
            raise RuntimeError('自己検証に失敗しました: ページ数が 0 です。')
        if idx_off < 48 or idx_off > file_size:
            raise RuntimeError(f'自己検証に失敗しました: ページテーブル開始位置が不正です。 idx_off={idx_off}')
        if data_off < idx_off + count * 16 or data_off > file_size:
            raise RuntimeError(f'自己検証に失敗しました: ページデータ開始位置が不正です。 data_off={data_off}')
        prev_end = data_off
        for page_index in range(1, count + 1):
            fh.seek(idx_off + (page_index - 1) * 16)
            entry = fh.read(16)
            if len(entry) != 16:
                raise RuntimeError(f'自己検証に失敗しました: ページ {page_index} の索引が途中で切れています。')
            offset, length, width, height = struct.unpack('<Q I H H', entry)
            if expected_page_specs is not None:
                expected_length, expected_page_w, expected_page_h = expected_page_specs[page_index - 1]
            else:
                expected_length, expected_page_w, expected_page_h = length, expected_w, expected_h
            end = offset + length
            if (
                length <= 0
                or length != expected_length
                or width != expected_page_w
                or height != expected_page_h
                or offset < data_off
                or offset < prev_end
                or end > file_size
            ):
                raise RuntimeError(
                    f'自己検証に失敗しました: ページ {page_index} の索引が不正です。 '
                    f'offset={offset} length={length} width={width} height={height} file_size={file_size}'
                )
            fh.seek(offset)
            blob_header = fh.read(22)
            _verify_xt_page_blob_header(blob_header, length, expected_page_w, expected_page_h, normalized_format, page_index)
            prev_end = end
        if prev_end != file_size:
            raise RuntimeError(
                '自己検証に失敗しました: 最終ページ終端とファイルサイズが一致しません。 '
                f'page_end={prev_end} file_size={file_size}'
            )
    return count



def _atomic_replace_xt_container(out_path: Path, writer: Callable[[BinaryIO], None], verifier: Callable[[Path], None] | None = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_handle = tempfile.NamedTemporaryFile(prefix=f'{out_path.stem}_', suffix='.partial', dir=str(out_path.parent), delete=False)
    tmp_path = Path(tmp_handle.name)
    try:
        with tmp_handle:
            writer(tmp_handle)
            tmp_handle.flush()
            os.fsync(tmp_handle.fileno())
        if verifier is not None:
            verifier(tmp_path)
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise


def build_xtc(page_blobs: Sequence[bytes], out_path: PathLike, w: int, h: int, output_format: str = 'xtc', should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None) -> None:
    _refresh_core_globals()
    _raise_if_cancelled(should_cancel)
    cnt = len(page_blobs)
    if cnt == 0:
        raise ValueError("変換データがありません。")
    _emit_progress(progress_cb, 0, cnt * 2 + 1, f'XTCを書き出す準備をしています… (0/{cnt} ページ)')
    idx_off = 48
    data_off = 48 + cnt * 16
    idx_table = bytearray()
    curr_off = data_off
    total_steps = cnt * 2 + 1
    for idx, b in enumerate(page_blobs, 1):
        _raise_if_cancelled(should_cancel)
        idx_table += struct.pack("<Q I H H", curr_off, len(b), w, h)
        curr_off += len(b)
        _emit_progress(progress_cb, idx, total_steps, f'XTC索引を作成中… ({idx}/{cnt} ページ)')
    mark = b"XTCH" if _normalize_output_format(output_format) == 'xtch' else b"XTC\x00"
    header = struct.pack("<4sHHBBBBIQQQQ", mark, 1, cnt, 1, 0, 0, 0, 0, 0, idx_off, data_off, 0)

    out_path = Path(out_path)

    def _writer(dst: BinaryIO) -> None:
        dst.write(header)
        dst.write(idx_table)
        for idx, blob in enumerate(page_blobs, 1):
            _raise_if_cancelled(should_cancel)
            dst.write(blob)
            _emit_progress(progress_cb, cnt + idx, total_steps, f'XTCページデータを書き込み中… ({idx}/{cnt} ページ)')

    normalized_output_format = _normalize_output_format(output_format)
    _atomic_replace_xt_container(
        out_path,
        _writer,
        verifier=lambda tmp_path: _verify_xt_container_file(tmp_path, w, h, normalized_output_format, expected_count=cnt),
    )
    _emit_progress(progress_cb, total_steps, total_steps, f'XTCを書き出しました。({cnt} ページ)')


def page_image_to_xt_bytes(img: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    _refresh_core_globals()
    return canvas_image_to_xt_bytes(img, w, h, args)


def _copy_fileobj_with_cancel(
    src: BinaryIO,
    dst: BinaryIO,
    *,
    should_cancel: CancelCallback | None = None,
    chunk_size: int = 1024 * 1024,
) -> int:
    """copyfileobj 相当の逐次コピーに中止判定を挟む。"""
    copied = 0
    while True:
        _raise_if_cancelled(should_cancel)
        chunk = src.read(max(1, int(chunk_size)))
        if not chunk:
            break
        dst.write(chunk)
        copied += len(chunk)
    _raise_if_cancelled(should_cancel)
    return copied


def _looks_like_expected_xt_page_blob(blob: object, expected_w: int, expected_h: int, args: ConversionArgs) -> bool:
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        return False
    blob_bytes = bytes(blob)
    if len(blob_bytes) < 22:
        return False
    expected_magic = b'XTH\x00' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else b'XTG\x00'
    if blob_bytes[:4] != expected_magic:
        return False
    try:
        blob_w = struct.unpack_from('<H', blob_bytes, 4)[0]
        blob_h = struct.unpack_from('<H', blob_bytes, 6)[0]
        payload_len = struct.unpack_from('<I', blob_bytes, 10)[0]
    except struct.error:
        return False
    if blob_w != int(expected_w) or blob_h != int(expected_h):
        return False
    return payload_len > 0 and (22 + payload_len) == len(blob_bytes)


def ensure_valid_xt_page_blob(blob: object, page_image: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    _refresh_core_globals()
    if _looks_like_expected_xt_page_blob(blob, w, h, args):
        return bytes(blob)
    return canvas_image_to_xt_bytes(page_image, w, h, args)


class XTCSpooledPages:
    """ページデータを一時ファイルへ退避しながら XTC / XTCH を組み立てる。"""

    def __init__(self: XTCSpooledPages) -> None:
        self._tmp = tempfile.NamedTemporaryFile(prefix='tategaki_xtc_pages_', suffix='.bin', delete=False)
        self._tmp_path = Path(self._tmp.name)
        self.page_sizes: list[int] = []
        self.page_count = 0
        self.total_blob_bytes = 0
        self._closed = False

    def add_blob(self: XTCSpooledPages, blob: bytes | bytearray | memoryview | None) -> None:
        if not blob or self._closed:
            return
        self._tmp.write(blob)
        self.page_sizes.append(len(blob))
        self.page_count += 1
        self.total_blob_bytes += len(blob)

    def close(self: XTCSpooledPages) -> None:
        if not self._closed:
            self._tmp.flush()
            self._tmp.close()
            self._closed = True

    def __enter__(self: XTCSpooledPages) -> XTCSpooledPages:
        return self

    def __exit__(self: XTCSpooledPages, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> Literal[False]:
        self.cleanup()
        return False

    def __del__(self: XTCSpooledPages) -> None:
        try:
            self.cleanup()
        except Exception:
            pass

    def cleanup(self: XTCSpooledPages) -> None:
        try:
            self.close()
        finally:
            try:
                if self._tmp_path.exists():
                    self._tmp_path.unlink()
            except OSError:
                pass

    def finalize(self: XTCSpooledPages, out_path: PathLike, w: int, h: int, output_format: str = 'xtc', should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None) -> None:
        _refresh_core_globals()
        _raise_if_cancelled(should_cancel)
        self.close()
        cnt = self.page_count
        if cnt == 0:
            raise ValueError('変換データがありません。')

        _emit_progress(progress_cb, 0, cnt * 2 + 1, f'XTCを書き出す準備をしています… (0/{cnt} ページ)')
        idx_off = 48
        data_off = 48 + cnt * 16
        idx_table = bytearray()
        curr_off = data_off
        total_steps = cnt * 2 + 1
        for idx, size in enumerate(self.page_sizes, 1):
            _raise_if_cancelled(should_cancel)
            idx_table += struct.pack('<Q I H H', curr_off, size, w, h)
            curr_off += size
            _emit_progress(progress_cb, idx, total_steps, f'XTC索引を作成中… ({idx}/{cnt} ページ)')

        mark = b'XTCH' if _normalize_output_format(output_format) == 'xtch' else b'XTC\x00'
        header = struct.pack('<4sHHBBBBIQQQQ', mark, 1, cnt, 1, 0, 0, 0, 0, 0, idx_off, data_off, 0)
        out_path = Path(out_path)

        def _writer(dst: BinaryIO) -> None:
            dst.write(header)
            dst.write(idx_table)
            with open(self._tmp_path, 'rb') as src:
                if callable(progress_cb):
                    for idx, size in enumerate(self.page_sizes, 1):
                        _raise_if_cancelled(should_cancel)
                        blob = src.read(size)
                        if len(blob) != size:
                            raise RuntimeError('一時ページデータの読み込みに失敗しました。')
                        dst.write(blob)
                        _emit_progress(progress_cb, cnt + idx, total_steps, f'XTCページデータを書き込み中… ({idx}/{cnt} ページ)')
                else:
                    _copy_fileobj_with_cancel(src, dst, should_cancel=should_cancel, chunk_size=1024 * 1024)

        normalized_output_format = _normalize_output_format(output_format)
        try:
            _atomic_replace_xt_container(
                out_path,
                _writer,
                verifier=lambda tmp_path: _verify_xt_container_file(tmp_path, w, h, normalized_output_format, expected_count=cnt),
            )
        finally:
            self.cleanup()

        _emit_progress(progress_cb, total_steps, total_steps, f'XTCを書き出しました。({cnt} ページ)')



# ==========================================
# --- アーカイブ / EPUB 変換 ---
# ==========================================
