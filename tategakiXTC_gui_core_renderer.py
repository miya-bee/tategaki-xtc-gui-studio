"""
tategakiXTC_gui_core_renderer.py — 縦書きレンダリング / プレビュー生成

`tategakiXTC_gui_core.py` から分離した描画系実装。互換性維持のため、
必要な共通型・定数・フォント / 入出力ヘルパーは gui_core 側から参照する。
"""
from __future__ import annotations

from typing import Any

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals'}
_CORE_SYNC_VERSION = -1
_CORE_SYNC_ATTR_COUNT = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch を描画実装へ反映する。"""
    global _CORE_SYNC_VERSION, _CORE_SYNC_ATTR_COUNT
    version = core_sync_version(_core)
    attr_count = len(vars(_core))
    if not force and _CORE_SYNC_VERSION == version and _CORE_SYNC_ATTR_COUNT == attr_count:
        return
    for _name, _value in vars(_core).items():
        if _name.startswith('__') or _name in _CORE_SYNC_EXCLUDED_NAMES:
            continue
        globals()[_name] = _value
    _CORE_SYNC_VERSION = version
    _CORE_SYNC_ATTR_COUNT = attr_count


_refresh_core_globals()


# --- moved from tategakiXTC_gui_core.py lines 1335-3738 ---
# ==========================================
# --- グリフ描画ヘルパー ---
# ==========================================

@lru_cache(maxsize=64)
def _scaled_kutoten_offset(f_size: int) -> tuple[int, int]:
    off_x = max(1, int(round(f_size * 0.06)))
    off_y = -max(1, int(round(f_size * 0.10)))
    return off_x, off_y




@lru_cache(maxsize=64)
def _glyph_position_mode(value: object) -> str:
    normalized = str(value or 'standard').strip().lower()
    compact = normalized.replace(' ', '').replace('　', '').replace('-', '_')
    if compact in {
        'down_strong', 'strong_down', 'plus', 'positive', 'adjusted', 'mode2', '+',
        'プラス', 'プラス補正', '下', '下補正', '下補正強', '下強', '強下', '補正',
    }:
        return 'down_strong'
    if compact in {
        'down_weak', 'weak_down', '下補正弱', '下弱', '弱下',
    }:
        return 'down_weak'
    if compact in {
        'up_weak', 'weak_up', '上補正弱', '上弱', '弱上',
    }:
        return 'up_weak'
    if compact in {
        'up_strong', 'strong_up', 'minus', 'negative', '-',
        'マイナス', 'マイナス補正', '上', '上補正', '上補正強', '上強', '強上',
    }:
        return 'up_strong'
    return 'standard'


def _draw_glyph_position_mode(draw: Any, attr_name: str) -> str:
    return _glyph_position_mode(getattr(draw, attr_name, 'standard'))


def _apply_draw_glyph_position_modes(draw: Any, args: Any) -> Any:
    try:
        setattr(draw, '_tategaki_punctuation_position_mode', _glyph_position_mode(getattr(args, 'punctuation_position_mode', 'standard')))
        setattr(draw, '_tategaki_ichi_position_mode', _glyph_position_mode(getattr(args, 'ichi_position_mode', 'standard')))
        setattr(draw, '_tategaki_lower_closing_bracket_position_mode', _glyph_position_mode(getattr(args, 'lower_closing_bracket_position_mode', 'standard')))
    except Exception:
        pass
    return draw


def _punctuation_adjusted_drop(f_size: int, *, weak: bool = False) -> int:
    factor = 0.15 if weak else 0.30
    return max(2 if weak else 3, int(round(f_size * factor)))


def _ichi_adjusted_raise(f_size: int, *, weak: bool = False) -> int:
    factor = 0.11 if weak else 0.22
    return max(2 if weak else 3, int(round(f_size * factor)))


LOWER_CLOSING_KAGIKAKKO_POSITION_CHARS = frozenset({'」', '』', '﹂', '﹄'})


def _lower_closing_bracket_adjusted_raise(f_size: int, *, weak: bool = False) -> int:
    factor = 0.18 if weak else 0.35
    return max(3 if weak else 5, int(round(f_size * factor)))


@lru_cache(maxsize=64)
def _lower_closing_bracket_extra_y_for_mode(original_char: str, f_size: int, position_mode: str) -> int:
    if original_char not in LOWER_CLOSING_KAGIKAKKO_POSITION_CHARS:
        return 0
    mode = _glyph_position_mode(position_mode)
    if mode == 'up_weak':
        return -_lower_closing_bracket_adjusted_raise(f_size, weak=True)
    if mode == 'up_strong':
        return -_lower_closing_bracket_adjusted_raise(f_size)
    return 0


@lru_cache(maxsize=64)
def _punctuation_extra_y_for_mode(f_size: int, position_mode: str) -> int:
    mode = _glyph_position_mode(position_mode)
    if mode == 'down_strong':
        # PIL / image coordinates use positive Y for downward movement.
        return _punctuation_adjusted_drop(f_size)
    if mode == 'down_weak':
        return _punctuation_adjusted_drop(f_size, weak=True)
    if mode == 'up_weak':
        return -_punctuation_adjusted_drop(f_size, weak=True)
    if mode == 'up_strong':
        return -_punctuation_adjusted_drop(f_size)
    return 0


@lru_cache(maxsize=64)
def _scaled_kutoten_offset_for_mode(f_size: int, position_mode: str) -> tuple[int, int]:
    # split113: 句読点位置補正はぶら下がり句読点だけに限定する。
    # 文中句読点は、補正モードが指定されていても標準オフセットを返す。
    return _scaled_kutoten_offset(f_size)


@lru_cache(maxsize=64)
def _ichi_extra_y_for_mode(f_size: int, position_mode: str) -> int:
    mode = _glyph_position_mode(position_mode)
    if mode == 'down_strong':
        # PIL / image coordinates use positive Y for downward movement.
        return _ichi_adjusted_raise(f_size)
    if mode == 'down_weak':
        return _ichi_adjusted_raise(f_size, weak=True)
    if mode == 'up_weak':
        return -_ichi_adjusted_raise(f_size, weak=True)
    if mode == 'up_strong':
        return -_ichi_adjusted_raise(f_size)
    return 0

@lru_cache(maxsize=64)
def _small_kana_offset(f_size: int) -> tuple[int, int]:
    off_x = max(1, int(round(f_size * 0.08)))
    off_y = -max(2, int(round(f_size * 0.12)))
    return off_x, off_y


@lru_cache(maxsize=64)
def _kagikakko_extra_y(original_char: str, f_size: int) -> int:
    if original_char in {'「', '『'}:
        # sweep317: sweep316 ではフォントによって開き鉤括弧が下寄りに
        # 見えるケースがあったため、下げ量を少し弱める。
        return max(1, int(round(f_size * 0.18)))
    if original_char in {'」', '』'}:
        # sweep341: 閉じ鉤括弧は一部フォントで水平画が下に沈むため、
        # 通常描画側も少し強めに上げる。ぶら下げ時の bbox 補正とは
        # 独立させ、通常位置の見え方だけを微調整する。
        return -max(1, int(round(f_size * 0.18)))
    return 0


@lru_cache(maxsize=512)
def _should_draw_emphasis_for_cell_cached(cell_text: str) -> bool:
    if not cell_text:
        return False
    return any((ch not in AOZORA_EMPHASIS_SKIP_CHARS) and (not ch.isspace()) for ch in cell_text)


@lru_cache(maxsize=512)
def _should_draw_side_line_for_cell_cached(cell_text: str) -> bool:
    if not cell_text:
        return False
    return any((ch not in AOZORA_SIDE_LINE_SKIP_CHARS) and (not ch.isspace()) for ch in cell_text)


@lru_cache(maxsize=64)
def _get_side_line_pattern(font_size: int, line_kind: str) -> tuple[int, int, int]:
    normalized = str(line_kind or 'solid')
    if normalized == 'wavy':
        amplitude = max(1, int(round(font_size * 0.06)))
        wavelength = max(4, int(round(font_size * 0.22)))
        return amplitude, wavelength, 0
    if normalized == 'dashed':
        segment = max(3, int(round(font_size * 0.18)))
        gap = max(2, int(round(font_size * 0.12)))
        return segment, gap, 0
    if normalized == 'chain':
        segment = max(5, int(round(font_size * 0.28)))
        gap = max(2, int(round(font_size * 0.10)))
        return segment, gap, 0
    return 0, 0, 0


@lru_cache(maxsize=128)
def _get_side_line_style(font_size: int, ruby_size: int, side_line_kind: str, has_ruby_text: bool, prefer_left: bool, has_emphasis_kind: bool) -> tuple[int, int, int, int, int]:
    right_padding = max(0, ruby_size + 2) if has_ruby_text and not prefer_left else 0
    left_padding = max(2, int(round(font_size * 0.20))) if prefer_left and has_emphasis_kind else 0
    base_gap = max(1, int(round(font_size * 0.08)))
    width = 2 if side_line_kind == 'thick' else 1
    offset = 2 if side_line_kind == 'double' else 0
    return right_padding, left_padding, base_gap, width, offset


def _clamp_int(value: int, lower: int, upper: int) -> int:
    if upper < lower:
        return lower
    return min(max(int(value), int(lower)), int(upper))


def _side_line_horizontal_extent(font_size: int, line_kind: str, width: int) -> int:
    half_width = max(0, int(width) // 2)
    if str(line_kind or '') == 'wavy':
        amplitude, _wavelength, _unused = _get_side_line_pattern(font_size, 'wavy')
        return max(0, int(amplitude) + half_width)
    return half_width


@lru_cache(maxsize=512)
def _classify_tate_draw_char(char: str) -> str:
    if not char:
        return 'default'
    if len(char) == 2:
        return 'double_punct'
    if char == '一':
        return 'ichi'
    if char in {'ー', '－'}:
        return 'long_vowel'
    if char in HORIZONTAL_BRACKET_ORIGINAL_CHARS:
        return 'horizontal_bracket'
    if char in {'、', '。', '，', '．', '､', '｡'}:
        return 'punctuation'
    if char in SMALL_KANA_CHARS:
        return 'small_kana'
    if len(char) == 1 and char.isascii() and (not char.isspace()) and char.isalnum():
        return 'ascii_center'
    return 'default'


def create_image_draw(image: Image.Image) -> Any:
    draw = ImageDraw.Draw(image)
    setattr(draw, '_tategaki_image', image)
    setattr(draw, '_tategaki_target_image', image)
    return draw


def _get_draw_target_image(draw: Any) -> Image.Image:
    image = getattr(draw, '_tategaki_target_image', None)
    if image is not None:
        return image
    image = getattr(draw, '_tategaki_image', None)
    if image is not None:
        try:
            setattr(draw, '_tategaki_target_image', image)
        except Exception:
            pass
        return image
    image = getattr(draw, '_image', None)
    if image is not None:
        try:
            setattr(draw, '_tategaki_target_image', image)
        except Exception:
            pass
        return image
    raise AttributeError('描画先の Image オブジェクトを取得できませんでした。')


def _get_or_create_hanging_punctuation_overlay_image(draw: Any, target_image: Image.Image | None = None) -> Image.Image | None:
    """Return a white overlay image used to replay hanging punctuation after clipping.

    The normal text page margin clip intentionally clears pixels inside the page
    margins.  Hanging punctuation is different: it is allowed to protrude into
    the bottom margin by design.  To avoid keeping every stray glyph pixel in
    that band, only hanging punctuation pastes are mirrored to this overlay and
    later restored inside the bottom margin.
    """
    try:
        target = target_image if target_image is not None else _get_draw_target_image(draw)
    except Exception:
        return None
    overlay = getattr(target, '_tategaki_hanging_punctuation_overlay_image', None)
    if isinstance(overlay, Image.Image) and overlay.size == target.size:
        return overlay
    try:
        overlay = Image.new('L', target.size, 255)
        setattr(target, '_tategaki_hanging_punctuation_overlay_image', overlay)
        return overlay
    except Exception:
        return None


def _paste_glyph_image(draw: Any, glyph_img: Image.Image, xy: tuple[int, int], mask: Image.Image | None = None) -> None:
    target_image = _get_draw_target_image(draw)
    paste_xy = (int(xy[0]), int(xy[1]))
    target_image.paste(glyph_img, paste_xy, mask)
    if getattr(draw, '_tategaki_capture_hanging_punctuation_overlay', False):
        overlay = _get_or_create_hanging_punctuation_overlay_image(draw, target_image)
        if overlay is not None:
            overlay.paste(glyph_img, paste_xy, mask)


def _restore_hanging_punctuation_bottom_margin(image: Image.Image, args: ConversionArgs | None) -> None:
    """Replay mirrored hanging punctuation pixels inside the bottom margin only."""
    if args is None:
        return
    if _normalize_kinsoku_mode(getattr(args, 'kinsoku_mode', 'standard')) == 'off':
        return
    width, height = image.size
    margin_b = _clamp_margin_value(getattr(args, 'margin_b', 0), height)
    if margin_b <= 0:
        return
    overlay = getattr(image, '_tategaki_hanging_punctuation_overlay_image', None)
    if not isinstance(overlay, Image.Image) or overlay.size != image.size:
        return
    y0 = max(0, height - margin_b)
    if y0 >= height:
        return
    overlay_band = overlay.crop((0, y0, width, height))
    mask = ImageOps.invert(overlay_band)
    if mask.getbbox() is None:
        return
    image.paste(overlay_band, (0, y0), mask)


_FONT_OBJECT_CACHE_UNSET = object()


def _get_font_object_cache(font: Any, cache_attr: str) -> dict[Any, Any] | None:
    cache = getattr(font, cache_attr, None)
    return cache if isinstance(cache, dict) else None


def _get_or_create_font_object_cache(font: Any, cache_attr: str) -> dict[Any, Any] | None:
    cache = _get_font_object_cache(font, cache_attr)
    if cache is not None:
        return cache
    try:
        cache = {}
        setattr(font, cache_attr, cache)
        return cache
    except Exception:
        return None


@lru_cache(maxsize=512)
def _cached_resolve_cacheable_font_spec(font_path_text: str, font_index: int, font_size: int) -> tuple[str, int, int] | None:
    _refresh_core_globals()
    if not font_path_text or font_size <= 0:
        return None
    font_spec = _cached_build_font_spec(font_path_text, font_index)
    resolved_path = _cached_resolve_font_path(font_spec)
    if not resolved_path:
        return None
    return resolved_path, int(font_index), int(font_size)


def _resolve_cacheable_font_spec(font: Any) -> tuple[str, int, int] | None:
    _refresh_core_globals()
    cached_value = getattr(font, '_tategaki_cacheable_spec', _FONT_OBJECT_CACHE_UNSET)
    if cached_value is not _FONT_OBJECT_CACHE_UNSET:
        return None if cached_value is False else cached_value

    font_path = getattr(font, 'path', None)
    font_index = int(getattr(font, 'index', 0) or 0)
    font_size = int(getattr(font, 'size', 0) or 0)
    resolved_spec: tuple[str, int, int] | None = None
    if font_path and font_size > 0 and isinstance(font_path, (str, os.PathLike)):
        resolved_spec = _cached_resolve_cacheable_font_spec(str(font_path), font_index, font_size)
    try:
        setattr(font, '_tategaki_cacheable_spec', resolved_spec if resolved_spec is not None else False)
    except Exception:
        pass
    return resolved_spec


@lru_cache(maxsize=4096)
def _cached_render_text_glyph_bundle(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool, rotate_degrees: int, canvas_size: int | None, is_italic: bool) -> tuple[Image.Image, Image.Image]:
    _refresh_core_globals()
    glyph_img = _cached_render_text_glyph_image(font_path, font_index, font_size, text, is_bold, rotate_degrees, canvas_size, is_italic)
    return glyph_img, ImageOps.invert(glyph_img)


def _glyph_render_cache_key(text: str, is_bold: bool, rotate_degrees: int, canvas_size: int | None, is_italic: bool) -> tuple[str, bool, int, int | None, bool]:
    return str(text), bool(is_bold), int(rotate_degrees), (None if canvas_size is None else int(canvas_size)), bool(is_italic)


def _render_text_glyph_and_mask_shared(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> tuple[Image.Image, Image.Image]:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_render_text_glyph_bundle(
            font_path,
            font_index,
            font_size,
            text,
            is_bold,
            int(rotate_degrees),
            canvas_size,
            is_italic,
        )
    cache_key = _glyph_render_cache_key(text, is_bold, int(rotate_degrees), canvas_size, is_italic)
    bundle_cache = _get_font_object_cache(font, '_tategaki_glyph_bundle_cache')
    if bundle_cache is not None and cache_key in bundle_cache:
        return bundle_cache[cache_key]
    glyph_cache = _get_font_object_cache(font, '_tategaki_glyph_image_cache')
    glyph_img = glyph_cache.get(cache_key) if glyph_cache is not None else None
    if glyph_img is None:
        glyph_img = _build_text_glyph_image(text, font, is_bold=is_bold, rotate_degrees=rotate_degrees, canvas_size=canvas_size, is_italic=is_italic)
        glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_glyph_image_cache')
        if glyph_cache is not None:
            glyph_cache[cache_key] = glyph_img
    bundle = (glyph_img, ImageOps.invert(glyph_img))
    bundle_cache = _get_or_create_font_object_cache(font, '_tategaki_glyph_bundle_cache')
    if bundle_cache is not None:
        bundle_cache[cache_key] = bundle
    return bundle


def _render_text_glyph_and_mask(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> tuple[Image.Image, Image.Image]:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        glyph_img, mask = _cached_render_text_glyph_bundle(
            font_path,
            font_index,
            font_size,
            text,
            is_bold,
            int(rotate_degrees),
            canvas_size,
            is_italic,
        )
        return glyph_img.copy(), mask.copy()
    glyph_img = _build_text_glyph_image(
        text,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=canvas_size,
        is_italic=is_italic,
    )
    return glyph_img, ImageOps.invert(glyph_img)


def draw_weighted_text(draw: Any, pos_tuple: tuple[int, int], text: str, font: Any, is_bold: bool = False, is_italic: bool = False) -> None:
    _refresh_core_globals()
    draw_kwargs = {"font": font, "fill": 0}
    x, y = pos_tuple
    if is_italic:
        glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(text, font, is_bold=is_bold, is_italic=True)
        _paste_glyph_image(draw, glyph_img, (int(x), int(y)), glyph_mask)
        return
    draw.text((x, y), text, **draw_kwargs)
    if is_bold:
        # 疑似ボールド: 横方向 +1px、縦方向 +1px を重ねて太りを自然に増やす。
        draw.text((x + 1, y), text, **draw_kwargs)
        draw.text((x, y + 1), text, **draw_kwargs)


@lru_cache(maxsize=1024)
def _glyph_canvas_layout(glyph_w: int, glyph_h: int, bbox_left: int, bbox_top: int,
                         stroke_width: int, canvas_size: int | None) -> tuple[int, int, int]:
    pad = max(4, int(stroke_width) + 2)
    side = int(canvas_size) if canvas_size else max(int(glyph_w), int(glyph_h)) + pad * 4
    draw_x = (side - int(glyph_w)) // 2 - int(bbox_left)
    draw_y = (side - int(glyph_h)) // 2 - int(bbox_top)
    return int(side), int(draw_x), int(draw_y)


_GLYPH_ITALIC_SHEAR_PERMILLE = -220


def _trim_glyph_image_to_ink(glyph_img: Image.Image) -> Image.Image:
    ink_bbox = ImageOps.invert(glyph_img).getbbox()
    return glyph_img.crop(ink_bbox) if ink_bbox else glyph_img


@lru_cache(maxsize=256)
def _italic_extra_width(glyph_h: int, shear_permille: int = _GLYPH_ITALIC_SHEAR_PERMILLE) -> int:
    shear = abs(float(shear_permille) / 1000.0)
    return int(shear * int(glyph_h)) + 4


@lru_cache(maxsize=256)
def _italic_transform_layout(glyph_w: int, glyph_h: int,
                             shear_permille: int = _GLYPH_ITALIC_SHEAR_PERMILLE) -> tuple[tuple[int, int], tuple[float, float, float, float, float, float]]:
    shear = float(shear_permille) / 1000.0
    extra_w = _italic_extra_width(glyph_h, shear_permille)
    offset_x = extra_w if shear < 0 else 0
    return (
        (int(glyph_w) + int(extra_w), int(glyph_h)),
        (1.0, float(shear), float(offset_x), 0.0, 1.0, 0.0),
    )


def _build_text_glyph_image(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> Image.Image:
    _refresh_core_globals()
    stroke_width = 1 if is_bold else 0
    bbox = _get_text_bbox(font, text, is_bold=is_bold)
    glyph_w, glyph_h = _get_text_bbox_dims(font, text, is_bold=is_bold)
    side, draw_x, draw_y = _glyph_canvas_layout(
        glyph_w, glyph_h, int(bbox[0]), int(bbox[1]), stroke_width, canvas_size
    )
    glyph_img = Image.new("L", (side, side), 255)
    glyph_draw = create_image_draw(glyph_img)
    draw_weighted_text(glyph_draw, (draw_x, draw_y), text, font, is_bold=is_bold)
    glyph_img = _trim_glyph_image_to_ink(glyph_img)
    if rotate_degrees:
        glyph_img = glyph_img.rotate(rotate_degrees, expand=True, fillcolor=255)
        glyph_img = _trim_glyph_image_to_ink(glyph_img)
    if is_italic:
        transform_size, affine_coeffs = _italic_transform_layout(glyph_img.width, glyph_img.height)
        transformed = glyph_img.transform(
            transform_size,
            Image.AFFINE,  # type: ignore[attr-defined]
            affine_coeffs,
            resample=Image.Resampling.BICUBIC,
            fillcolor=255,
        )
        glyph_img = _trim_glyph_image_to_ink(transformed)
    return glyph_img


@lru_cache(maxsize=4096)
def _cached_render_text_glyph_image(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool, rotate_degrees: int, canvas_size: int | None, is_italic: bool) -> Image.Image:
    _refresh_core_globals()
    font = load_truetype_font(build_font_spec(font_path, font_index), font_size)
    return _build_text_glyph_image(
        text,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=canvas_size,
        is_italic=is_italic,
    )


def _render_text_glyph_image_shared(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> Image.Image:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_render_text_glyph_image(
            font_path,
            font_index,
            font_size,
            text,
            is_bold,
            int(rotate_degrees),
            canvas_size,
            is_italic,
        )
    cache_key = _glyph_render_cache_key(text, is_bold, int(rotate_degrees), canvas_size, is_italic)
    glyph_cache = _get_font_object_cache(font, '_tategaki_glyph_image_cache')
    if glyph_cache is not None and cache_key in glyph_cache:
        return glyph_cache[cache_key]
    glyph_img = _build_text_glyph_image(text, font, is_bold=is_bold, rotate_degrees=rotate_degrees, canvas_size=canvas_size, is_italic=is_italic)
    glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_glyph_image_cache')
    if glyph_cache is not None:
        glyph_cache[cache_key] = glyph_img
    return glyph_img


def _render_text_glyph_image(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> Image.Image:
    _refresh_core_globals()
    return _render_text_glyph_image_shared(
        text,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=canvas_size,
        is_italic=is_italic,
    ).copy()


_VERTICAL_GLYPH_FALLBACK_SENTINELS = ('͸', '΀', '﷐', '󰀀')


def _glyph_image_signature(image: Image.Image) -> tuple[int, int, bytes]:
    normalized = image if image.mode == 'L' else image.convert('L')
    return normalized.width, normalized.height, normalized.tobytes()


@lru_cache(maxsize=2048)
def _cached_glyph_signature(font_path: str, font_index: int, font_size: int, text: str,
                            is_bold: bool, is_italic: bool) -> tuple[int, int, bytes]:
    _refresh_core_globals()
    glyph_img = _cached_render_text_glyph_image(
        font_path,
        font_index,
        font_size,
        text,
        bool(is_bold),
        0,
        None,
        bool(is_italic),
    )
    return _glyph_image_signature(glyph_img)


@lru_cache(maxsize=128)
def _missing_glyph_signatures(font_path: str, font_index: int, size: int, is_bold: bool, is_italic: bool) -> tuple[tuple[int, int, bytes], ...]:
    _refresh_core_globals()
    signatures: list[tuple[int, int, bytes]] = []
    for sentinel in _VERTICAL_GLYPH_FALLBACK_SENTINELS:
        try:
            signatures.append(_cached_glyph_signature(font_path, font_index, size, sentinel, is_bold, is_italic))
        except Exception:
            continue
    return tuple(signatures)


def _missing_glyph_signatures_for_font(font: Any, *, is_bold: bool = False, is_italic: bool = False) -> tuple[tuple[int, int, bytes], ...]:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _missing_glyph_signatures(font_path, font_index, font_size, bool(is_bold), bool(is_italic))
    cache_key = (bool(is_bold), bool(is_italic))
    missing_cache = _get_font_object_cache(font, '_tategaki_missing_glyph_signatures_cache')
    if missing_cache is not None and cache_key in missing_cache:
        return missing_cache[cache_key]
    signatures: list[tuple[int, int, bytes]] = []
    for sentinel in _VERTICAL_GLYPH_FALLBACK_SENTINELS:
        try:
            signatures.append(
                _glyph_image_signature(
                    _render_text_glyph_image_shared(sentinel, font, is_bold=is_bold, is_italic=is_italic)
                )
            )
        except Exception:
            continue
    resolved = tuple(signatures)
    missing_cache = _get_or_create_font_object_cache(font, '_tategaki_missing_glyph_signatures_cache')
    if missing_cache is not None:
        missing_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=1024)
def _cached_font_has_distinct_glyph(font_path: str, font_index: int, font_size: int, char: str, is_bold: bool, is_italic: bool) -> bool:
    _refresh_core_globals()
    if not char:
        return False
    try:
        glyph_signature = _cached_glyph_signature(font_path, font_index, font_size, char, is_bold, is_italic)
    except Exception:
        return False
    missing_signatures = _missing_glyph_signatures(font_path, font_index, font_size, is_bold, is_italic)
    if not missing_signatures:
        return False
    return glyph_signature not in missing_signatures


def _font_has_distinct_glyph(font: Any, char: str, *, is_bold: bool = False, is_italic: bool = False) -> bool:
    _refresh_core_globals()
    if not char:
        return False
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_font_has_distinct_glyph(font_path, font_index, font_size, char, is_bold, is_italic)
    cache_key = (str(char), bool(is_bold), bool(is_italic))
    glyph_cache = _get_font_object_cache(font, '_tategaki_distinct_glyph_cache')
    if glyph_cache is not None and cache_key in glyph_cache:
        return bool(glyph_cache[cache_key])
    try:
        glyph_signature = _glyph_image_signature(
            _render_text_glyph_image_shared(char, font, is_bold=is_bold, is_italic=is_italic)
        )
        missing_signatures = _missing_glyph_signatures_for_font(font, is_bold=is_bold, is_italic=is_italic)
        result = bool(missing_signatures) and glyph_signature not in missing_signatures
    except Exception:
        result = False
    glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_distinct_glyph_cache')
    if glyph_cache is not None:
        glyph_cache[cache_key] = result
    return result


def _should_rotate_to_horizontal_from_glyph_image(glyph_img: Image.Image) -> bool:
    width, height = glyph_img.size
    if width <= 0 or height <= 0:
        return False
    return height > max(width + 1, int(round(width * 1.08)))


@lru_cache(maxsize=128)
def _cached_horizontal_rotation_decision(font_path: str, font_index: int, font_size: int, char: str, is_bold: bool, is_italic: bool) -> bool:
    _refresh_core_globals()
    try:
        glyph_img = _cached_render_text_glyph_image(
            font_path,
            font_index,
            font_size,
            char,
            bool(is_bold),
            0,
            None,
            bool(is_italic),
        )
    except Exception:
        return False
    return _should_rotate_to_horizontal_from_glyph_image(glyph_img)


def _should_rotate_to_horizontal(font: Any, char: str, *, is_bold: bool = False, is_italic: bool = False) -> bool:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_horizontal_rotation_decision(font_path, font_index, font_size, char, is_bold, is_italic)
    cache_key = (str(char), bool(is_bold), bool(is_italic))
    rotation_cache = _get_font_object_cache(font, '_tategaki_horizontal_rotation_cache')
    if rotation_cache is not None and cache_key in rotation_cache:
        return bool(rotation_cache[cache_key])
    try:
        glyph_img = _render_text_glyph_image_shared(char, font, is_bold=is_bold, is_italic=is_italic)
        result = _should_rotate_to_horizontal_from_glyph_image(glyph_img)
    except Exception:
        result = False
    rotation_cache = _get_or_create_font_object_cache(font, '_tategaki_horizontal_rotation_cache')
    if rotation_cache is not None:
        rotation_cache[cache_key] = result
    return result


HORIZONTAL_BRACKET_ORIGINAL_CHARS = frozenset({
    '「', '」', '『', '』', '【', '】', '〈', '〉', '［', '］', '[', ']',
    '≪', '≫', '《', '》', '〔', '〕', '（', '）', '(', ')', '｛', '｝', '{', '}',
    '＜', '＞', '<', '>',
})
HORIZONTAL_BRACKET_VERTICAL_FORMS = frozenset({
    '﹁', '﹂', '﹃', '﹄', '︻', '︼', '︹', '︺', '︵', '︶', '﹇', '﹈',
    '︷', '︸', '︿', '﹀', '︽', '︾',
})
HORIZONTAL_BRACKET_CHARS = HORIZONTAL_BRACKET_ORIGINAL_CHARS | HORIZONTAL_BRACKET_VERTICAL_FORMS


def _should_rotate_horizontal_bracket(font: Any, char: str, *, is_bold: bool = False, is_italic: bool = False) -> bool:
    _refresh_core_globals()
    if char not in HORIZONTAL_BRACKET_CHARS:
        return False
    if char in HORIZONTAL_BRACKET_VERTICAL_FORMS:
        return False
    # 括弧類はどのフォントでも横長に見える向きへ統一する。
    # 縦書き用の横長字形が使える場合は未回転、元字形しかない場合は縦長判定で右回転する。
    return _should_rotate_to_horizontal(font, char, is_bold=is_bold, is_italic=is_italic)


_VERTICAL_PUNCTUATION_CHARS = {'、', '。', '，', '．', '､', '｡'}


@lru_cache(maxsize=2048)
def _is_render_spacing_char(char: str) -> bool:
    if not char:
        return False
    char_text = str(char)
    if len(char_text) == 1:
        return char_text.isspace()
    return all(ch.isspace() for ch in char_text)


@lru_cache(maxsize=1024)
def _cached_resolve_vertical_glyph_char(font_path: str, font_index: int, font_size: int, original_char: str, is_bold: bool, is_italic: bool) -> str:
    _refresh_core_globals()
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    if mapped_char == original_char:
        return original_char
    if _cached_font_has_distinct_glyph(font_path, font_index, font_size, mapped_char, is_bold, is_italic):
        return mapped_char
    if _cached_font_has_distinct_glyph(font_path, font_index, font_size, original_char, is_bold, is_italic):
        return original_char
    return mapped_char


def _resolve_vertical_glyph_char(original_char: str, font: Any, *, is_bold: bool = False, is_italic: bool = False) -> str:
    _refresh_core_globals()
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    if mapped_char == original_char:
        return original_char
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
    cache_key = (str(original_char), bool(is_bold), bool(is_italic))
    glyph_cache = _get_font_object_cache(font, '_tategaki_vertical_glyph_char_cache')
    if glyph_cache is not None and cache_key in glyph_cache:
        return str(glyph_cache[cache_key])
    mapped_supported = _font_has_distinct_glyph(font, mapped_char, is_bold=is_bold, is_italic=is_italic)
    if mapped_supported:
        resolved_char = mapped_char
    else:
        original_supported = _font_has_distinct_glyph(font, original_char, is_bold=is_bold, is_italic=is_italic)
        resolved_char = original_char if original_supported else mapped_char
    glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_vertical_glyph_char_cache')
    if glyph_cache is not None:
        glyph_cache[cache_key] = resolved_char
    return resolved_char


@lru_cache(maxsize=1024)
def _cached_tate_punctuation_draw(font_path: str, font_index: int, font_size: int, original_char: str, is_bold: bool, is_italic: bool) -> tuple[str, bool]:
    _refresh_core_globals()
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
    fallback_layout = resolved_char == original_char and mapped_char != original_char
    return resolved_char, fallback_layout


def _resolve_tate_punctuation_draw(original_char: str, font: Any, *, is_bold: bool = False, is_italic: bool = False) -> tuple[str, bool]:
    _refresh_core_globals()
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    if mapped_char == original_char:
        return original_char, False
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_tate_punctuation_draw(font_path, font_index, font_size, original_char, is_bold, is_italic)
    cache_key = (str(original_char), bool(is_bold), bool(is_italic))
    draw_cache = _get_font_object_cache(font, '_tategaki_punctuation_draw_cache')
    if draw_cache is not None and cache_key in draw_cache:
        return draw_cache[cache_key]
    resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    fallback_layout = resolved_char == original_char and mapped_char != original_char
    resolved = (resolved_char, fallback_layout)
    draw_cache = _get_or_create_font_object_cache(font, '_tategaki_punctuation_draw_cache')
    if draw_cache is not None:
        draw_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=1024)
def _cached_horizontal_bracket_draw(font_path: str, font_index: int, font_size: int, original_char: str, f_size: int, is_bold: bool, is_italic: bool) -> tuple[str, int, int, int]:
    _refresh_core_globals()
    resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
    rotate_degrees = 0
    if resolved_char in HORIZONTAL_BRACKET_ORIGINAL_CHARS:
        rotate_degrees = 270 if _cached_horizontal_rotation_decision(
            font_path,
            font_index,
            font_size,
            resolved_char,
            is_bold,
            is_italic,
        ) else 0
    extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
    extra_y = _kagikakko_extra_y(original_char, f_size)
    return resolved_char, rotate_degrees, extra_x, extra_y


def _resolve_horizontal_bracket_draw(original_char: str, font: Any, f_size: int, *, is_bold: bool = False, is_italic: bool = False) -> tuple[str, int, int, int]:
    _refresh_core_globals()
    # 括弧は、縦書き互換字形が使えないフォールバック時に元字形を回転描画する。
    # 通常運用では cacheable font 用の lru_cache を使って高速化する。
    # ただし、回帰テストや診断コードが _resolve_vertical_glyph_char /
    # _should_rotate_horizontal_bracket を差し替えている場合は、その差し替え結果を
    # 確実に反映するため、font object 側の浅いキャッシュ経路へフォールバックする。
    cacheable_spec = _resolve_cacheable_font_spec(font)
    helper_overridden = (
        getattr(_resolve_vertical_glyph_char, 'mock_calls', None) is not None
        or getattr(_should_rotate_horizontal_bracket, 'mock_calls', None) is not None
    )
    if cacheable_spec and not helper_overridden:
        font_path, font_index, font_size = cacheable_spec
        return _cached_horizontal_bracket_draw(
            font_path,
            font_index,
            font_size,
            original_char,
            f_size,
            bool(is_bold),
            bool(is_italic),
        )

    cache_key = (str(original_char), int(f_size), bool(is_bold), bool(is_italic))
    draw_cache = _get_font_object_cache(font, '_tategaki_horizontal_bracket_draw_cache')
    if draw_cache is not None and cache_key in draw_cache:
        return draw_cache[cache_key]
    resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    rotate_degrees = 270 if _should_rotate_horizontal_bracket(font, resolved_char, is_bold=is_bold, is_italic=is_italic) else 0
    extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
    extra_y = _kagikakko_extra_y(original_char, f_size)
    resolved = (resolved_char, rotate_degrees, extra_x, extra_y)
    draw_cache = _get_or_create_font_object_cache(font, '_tategaki_horizontal_bracket_draw_cache')
    if draw_cache is not None:
        draw_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=1024)
def _cached_default_tate_draw(font_path: str, font_index: int, font_size: int, original_char: str, is_bold: bool, is_italic: bool) -> str:
    _refresh_core_globals()
    return _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)


def _resolve_default_tate_draw(original_char: str, font: Any, *, is_bold: bool = False, is_italic: bool = False) -> str:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_default_tate_draw(font_path, font_index, font_size, original_char, is_bold, is_italic)
    cache_key = (str(original_char), bool(is_bold), bool(is_italic))
    draw_cache = _get_font_object_cache(font, '_tategaki_default_tate_draw_cache')
    if draw_cache is not None and cache_key in draw_cache:
        return str(draw_cache[cache_key])
    resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    draw_cache = _get_or_create_font_object_cache(font, '_tategaki_default_tate_draw_cache')
    if draw_cache is not None:
        draw_cache[cache_key] = resolved_char
    return resolved_char


@lru_cache(maxsize=4096)
def _cached_tate_draw_spec(
    font_path: str,
    font_index: int,
    font_size: int,
    original_char: str,
    f_size: int,
    draw_kind: str,
    is_bold: bool,
    is_italic: bool,
) -> tuple[str, str, int, int, int, int, int, bool]:
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    resolved_char = original_char
    rotate_degrees = 0
    extra_x = 0
    extra_y = 0
    off_x = 0
    off_y = 0
    fallback_layout = False

    if draw_kind == 'horizontal_bracket':
        resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
        if resolved_char in HORIZONTAL_BRACKET_ORIGINAL_CHARS:
            rotate_degrees = 270 if _cached_horizontal_rotation_decision(
                font_path,
                font_index,
                font_size,
                resolved_char,
                is_bold,
                is_italic,
            ) else 0
        extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
        extra_y = _kagikakko_extra_y(original_char, f_size)
    elif draw_kind == 'punctuation':
        resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
        fallback_layout = resolved_char == original_char and mapped_char != original_char
        if not fallback_layout:
            off_x, off_y = _scaled_kutoten_offset(f_size)
    elif draw_kind == 'small_kana':
        resolved_char = (
            _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
            if mapped_char != original_char
            else original_char
        )
        off_x, off_y = _small_kana_offset(f_size)
    elif draw_kind == 'default':
        resolved_char = (
            _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
            if mapped_char != original_char
            else original_char
        )
    return draw_kind, resolved_char, rotate_degrees, extra_x, extra_y, off_x, off_y, fallback_layout



def _compute_uncached_tate_draw_spec(
    original_char: str,
    font: Any,
    f_size: int,
    *,
    draw_kind: str | None = None,
    is_bold: bool = False,
    is_italic: bool = False,
) -> tuple[str, str, int, int, int, int, int, bool]:
    draw_kind = draw_kind or _classify_tate_draw_char(original_char)
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    resolved_char = original_char
    rotate_degrees = 0
    extra_x = 0
    extra_y = 0
    off_x = 0
    off_y = 0
    fallback_layout = False

    if draw_kind == 'horizontal_bracket':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
        rotate_degrees = 270 if _should_rotate_horizontal_bracket(font, resolved_char, is_bold=is_bold, is_italic=is_italic) else 0
        extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
        extra_y = _kagikakko_extra_y(original_char, f_size)
    elif draw_kind == 'punctuation':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
        fallback_layout = resolved_char == original_char and mapped_char != original_char
        if not fallback_layout:
            off_x, off_y = _scaled_kutoten_offset(f_size)
    elif draw_kind == 'small_kana':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic) if mapped_char != original_char else original_char
        off_x, off_y = _small_kana_offset(f_size)
    elif draw_kind == 'default':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic) if mapped_char != original_char else original_char
    return draw_kind, resolved_char, rotate_degrees, extra_x, extra_y, off_x, off_y, fallback_layout


def _compute_tate_draw_spec(
    original_char: str,
    font: Any,
    f_size: int,
    *,
    draw_kind: str | None = None,
    is_bold: bool = False,
    is_italic: bool = False,
) -> tuple[str, str, int, int, int, int, int, bool]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_tate_draw_spec(font_path, font_index, font_size, original_char, int(f_size), draw_kind or _classify_tate_draw_char(original_char), is_bold, is_italic)

    return _compute_uncached_tate_draw_spec(
        original_char,
        font,
        f_size,
        draw_kind=draw_kind,
        is_bold=is_bold,
        is_italic=is_italic,
    )


def _compute_reference_glyph_center(font: Any, *, is_bold: bool = False, f_size: int | None = None) -> float:
    _refresh_core_globals()
    refs = ("口", "田", "国", "漢", "あ", "ア", "亜")
    centers = []
    for ref in refs:
        bbox = _get_text_bbox(font, ref, is_bold=is_bold)
        if bbox and (bbox[2] - bbox[0]) > 1 and (bbox[3] - bbox[1]) > 1:
            centers.append((bbox[1] + bbox[3]) / 2.0)
    if centers:
        return sum(centers) / len(centers)
    return (f_size / 2.0) if f_size else 0.0


@lru_cache(maxsize=128)
def _cached_reference_glyph_center(font_path: str, font_index: int, font_size: int, is_bold: bool) -> float:
    _refresh_core_globals()
    font = load_truetype_font(build_font_spec(font_path, font_index), font_size)
    return _compute_reference_glyph_center(font, is_bold=is_bold, f_size=font_size)


@lru_cache(maxsize=64)
def _get_reference_glyph_center(font: Any, is_bold: bool = False, f_size: int | None = None) -> float:
    _refresh_core_globals()
    """通常の全角文字が流し込み時に占める"見た目の中心"を推定する。"""
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_reference_glyph_center(font_path, font_index, font_size, bool(is_bold))
    cache_key = (bool(is_bold), int(f_size or 0))
    center_cache = _get_font_object_cache(font, '_tategaki_reference_center_cache')
    if center_cache is not None and cache_key in center_cache:
        return float(center_cache[cache_key])
    center = _compute_reference_glyph_center(font, is_bold=is_bold, f_size=f_size)
    center_cache = _get_or_create_font_object_cache(font, '_tategaki_reference_center_cache')
    if center_cache is not None:
        center_cache[cache_key] = float(center)
    return center


def _make_font_variant(font: Any, size: int) -> Any:
    _refresh_core_globals()
    size = int(size)
    variant_cache = getattr(font, '_tategaki_variant_cache', None)
    if isinstance(variant_cache, dict) and size in variant_cache:
        return variant_cache[size]

    variant_font: Any = font
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, _font_size = cacheable_spec
        variant_font = load_truetype_font(build_font_spec(font_path, font_index), size)
    else:
        used_font_variant = False
        if hasattr(font, "font_variant"):
            try:
                variant_font = font.font_variant(size=size)
                used_font_variant = True
            except TypeError:
                variant_font = font
        if not used_font_variant:
            font_path = getattr(font, 'path', None)
            font_index = getattr(font, 'index', 0)
            if font_path and isinstance(font_path, (str, os.PathLike)):
                variant_font = load_truetype_font(build_font_spec(font_path, int(font_index or 0)), size)

    try:
        if not isinstance(variant_cache, dict):
            variant_cache = {}
            setattr(font, '_tategaki_variant_cache', variant_cache)
        variant_cache[size] = variant_font
    except Exception:
        pass
    return variant_font


@lru_cache(maxsize=512)
def _centered_glyph_direct_offsets(f_size: int, glyph_w: int, glyph_h: int, bbox_left: int, bbox_top: int,
                                   align_to_text_flow: bool, target_center_y_q16: int, extra_x: int, extra_y: int) -> tuple[int, int]:
    offset_x = max(0, (f_size - glyph_w) // 2) - bbox_left + int(extra_x)
    if align_to_text_flow:
        target_center_y = target_center_y_q16 / 16.0
        glyph_center_y = bbox_top + (glyph_h / 2.0)
        offset_y = int(round(target_center_y - glyph_center_y))
    else:
        offset_y = max(0, (f_size - glyph_h) // 2) - bbox_top
    offset_y += int(extra_y)
    return int(offset_x), int(offset_y)


@lru_cache(maxsize=512)
def _centered_glyph_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                  align_to_text_flow: bool, target_center_y_q16: int,
                                  extra_x: int, extra_y: int) -> tuple[int, int]:
    offset_x = max(0, (f_size - glyph_w) // 2) + int(extra_x)
    if align_to_text_flow:
        target_center_y = target_center_y_q16 / 16.0
        offset_y = int(round(target_center_y - (glyph_h / 2.0)))
    else:
        offset_y = max(0, (f_size - glyph_h) // 2)
    offset_y += int(extra_y)
    return int(offset_x), int(offset_y)


def draw_centered_glyph(
    draw: Any,
    char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    is_bold: bool = False,
    rotate_degrees: int = 0,
    align_to_text_flow: bool = False,
    is_italic: bool = False,
    extra_x: int = 0,
    extra_y: int = 0,
) -> None:
    """
    Draw a single glyph centred within a square cell of size ``f_size``.

    This helper attempts to fast‑path the common case (no rotation/italic) by
    computing glyph bounding boxes and offsets directly rather than
    rendering an image for the glyph. When rotation or italics are
    requested, it falls back to rendering the glyph onto an image and
    pasting it.

    Parameters are intentionally kept simple and all optional flags are
    annotated to encourage the Python interpreter to avoid implicit
    conversions. Additional keyword arguments default to sensible values.
    """
    curr_x, curr_y = pos_tuple
    # Compute the target centre for aligning to the text flow only once.
    if align_to_text_flow:
        # Convert the floating centre into a fixed‑point integer scaled by 16.
        target_center_y_q16 = int(round(_get_reference_glyph_center(font, is_bold=is_bold, f_size=f_size) * 16.0))
    else:
        target_center_y_q16 = 0

    # Fast path: no rotation and no italic styling.
    if not rotate_degrees and not is_italic:
        # Resolve the glyph bounding box.  Using the cached helper avoids
        # allocating a new tuple on every call.
        bbox_left, bbox_top, bbox_right, bbox_bottom = _get_text_bbox(font, char, is_bold=is_bold)
        # Compute glyph width/height from the bbox.  Ensure they are at least 1px
        # tall/wide to avoid divide by zero in offset calculations.
        glyph_w = max(1, bbox_right - bbox_left)
        glyph_h = max(1, bbox_bottom - bbox_top)
        # Compute the centred offsets using the direct offset helper.  Pass
        # integers directly; the helper handles any further conversion.
        off_x, off_y = _centered_glyph_direct_offsets(
            f_size,
            glyph_w,
            glyph_h,
            bbox_left,
            bbox_top,
            align_to_text_flow,
            target_center_y_q16,
            extra_x,
            extra_y,
        )
        # Draw the glyph directly using the weighted text helper.  The italic
        # flag is always False in the fast path.
        draw_weighted_text(
            draw,
            (curr_x + off_x, curr_y + off_y),
            char,
            font,
            is_bold=is_bold,
            is_italic=False,
        )
        return

    # Slow path: either rotated or italic.  Render an image for the glyph.
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(
        char,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=f_size * 4,
        is_italic=is_italic,
    )
    gw, gh = glyph_img.size
    # Compute offsets for the rendered glyph.  Use the image‑based offset
    # helper since we cannot rely on the bounding box being relative to the
    # origin in the rotated/italic case.
    off_x, off_y = _centered_glyph_image_offsets(
        f_size,
        gw,
        gh,
        align_to_text_flow,
        target_center_y_q16,
        extra_x,
        extra_y,
    )
    # Paste the rendered glyph onto the draw target.
    _paste_glyph_image(
        draw,
        glyph_img,
        (curr_x + off_x, curr_y + off_y),
        glyph_mask,
    )


@lru_cache(maxsize=512)
def _ink_centered_glyph_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                      extra_x: int, extra_y: int) -> tuple[int, int]:
    """実インク画像をセルの幾何中央へ置くためのオフセット。"""
    offset_x = int(round((int(f_size) - int(glyph_w)) / 2.0)) + int(extra_x)
    offset_y = int(round((int(f_size) - int(glyph_h)) / 2.0)) + int(extra_y)
    return int(offset_x), int(offset_y)


@lru_cache(maxsize=512)
def _ink_flow_centered_glyph_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                           target_center_y_q16: int,
                                           extra_x: int, extra_y: int) -> tuple[int, int]:
    """実インク画像の中心を本文の見た目中心へ合わせるためのオフセット。"""
    offset_x = int(round((int(f_size) - int(glyph_w)) / 2.0)) + int(extra_x)
    target_center_y = float(target_center_y_q16) / 16.0
    offset_y = int(round(target_center_y - (int(glyph_h) / 2.0))) + int(extra_y)
    return int(offset_x), int(offset_y)


def _get_ichi_visual_target_center_y(font: Any, is_bold: bool = False, f_size: int | None = None) -> float:
    _refresh_core_globals()
    """漢数字「一」の実インクを合わせる縦方向の見た目中心を返す。

    通常漢字の bbox 中心を基準にする。ただし、フォントや Pillow 版によって
    参照中心がセル幾何中央付近へ倒れすぎる場合は、縦書き本文の見え方に
    合うようセル下寄りの安全下限を使う。
    """
    size = max(1, int(f_size or getattr(font, 'size', 0) or 1))
    try:
        target = float(_get_reference_glyph_center(font, is_bold=is_bold, f_size=size))
    except Exception:
        target = 0.0
    lower = size * 0.62
    upper = size * 0.82
    if target <= 0:
        target = lower
    return max(lower, min(target, upper))


def draw_ink_centered_glyph(
    draw: Any,
    char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    is_bold: bool = False,
    rotate_degrees: int = 0,
    align_to_text_flow: bool = False,
    is_italic: bool = False,
    extra_x: int = 0,
    extra_y: int = 0,
) -> None:
    _refresh_core_globals()
    """実インクbbox基準でグリフを描画する。

    align_to_text_flow=True の場合は、実インク中心を通常漢字の見た目中心へ
    合わせる。これにより、縦書き本文中の漢数字「一」がセル上側に
    残って見えるフォント差を抑える。
    """
    curr_x, curr_y = pos_tuple
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(
        char,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=f_size * 4,
        is_italic=is_italic,
    )
    gw, gh = glyph_img.size
    if align_to_text_flow:
        target_center_y_q16 = int(round(_get_ichi_visual_target_center_y(font, is_bold=is_bold, f_size=f_size) * 16.0))
        off_x, off_y = _ink_flow_centered_glyph_image_offsets(
            f_size, gw, gh, target_center_y_q16, extra_x, extra_y
        )
    else:
        off_x, off_y = _ink_centered_glyph_image_offsets(f_size, gw, gh, extra_x, extra_y)
    _paste_glyph_image(draw, glyph_img, (curr_x + off_x, curr_y + off_y), glyph_mask)


@lru_cache(maxsize=4096)
def _is_tatechuyoko_token(token: str) -> bool:
    if not token or len(token) < 2 or len(token) > 4:
        return False
    if not token.isascii() or not token.isalnum():
        return False
    if len(token) == 2:
        return True
    if len(token) == 3:
        return True
    return token.isdigit()


@lru_cache(maxsize=16)
def _tatechuyoko_layout_limits(f_size: int, text_len: int) -> tuple[int, int, int]:
    max_w = max(1, int(round(f_size * 0.92)))
    max_h = max(1, int(round(f_size * 0.58)))
    start_ratio = {2: 0.78, 3: 0.62, 4: 0.52}.get(int(text_len), 0.72)
    start_size = max(6, int(round(f_size * start_ratio)))
    return max_w, max_h, start_size


@lru_cache(maxsize=4096)
def _cached_text_bbox(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool) -> tuple[int, int, int, int]:
    _refresh_core_globals()
    font = load_truetype_font(build_font_spec(font_path, font_index), font_size)
    stroke_width = 1 if is_bold else 0
    return _normalize_text_bbox_result(_call_font_getbbox(font, text, stroke_width))


@lru_cache(maxsize=4096)
def _cached_text_bbox_dims(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool) -> tuple[int, int]:
    _refresh_core_globals()
    bbox = _cached_text_bbox(font_path, font_index, font_size, text, bool(is_bold))
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])


def _normalize_text_bbox_result(bbox: Any) -> tuple[int, int, int, int]:
    if not bbox:
        return 0, 0, 1, 1
    try:
        x0, y0, x1, y1 = bbox[:4]
    except Exception:
        return 0, 0, 1, 1
    try:
        x0_i, y0_i, x1_i, y1_i = int(x0), int(y0), int(x1), int(y1)
    except (TypeError, ValueError, OverflowError):
        return 0, 0, 1, 1
    if x1_i <= x0_i:
        x1_i = x0_i + 1
    if y1_i <= y0_i:
        y1_i = y0_i + 1
    return x0_i, y0_i, x1_i, y1_i


def _call_font_getbbox(font: Any, text: str, stroke_width: int) -> Any:
    getbbox = getattr(font, 'getbbox', None)
    if getbbox is None:
        return None
    try:
        return getbbox(text, stroke_width=stroke_width)
    except TypeError:
        try:
            return getbbox(text)
        except (AttributeError, OSError, TypeError, ValueError):
            return None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _get_text_bbox(font: Any, text: str, is_bold: bool = False) -> tuple[int, int, int, int]:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_text_bbox(font_path, font_index, font_size, text, bool(is_bold))
    cache_key = (str(text), bool(is_bold))
    bbox_cache = _get_font_object_cache(font, '_tategaki_text_bbox_cache')
    if bbox_cache is not None and cache_key in bbox_cache:
        return bbox_cache[cache_key]
    stroke_width = 1 if is_bold else 0
    normalized_bbox = _normalize_text_bbox_result(_call_font_getbbox(font, text, stroke_width))
    bbox_cache = _get_or_create_font_object_cache(font, '_tategaki_text_bbox_cache')
    if bbox_cache is not None:
        bbox_cache[cache_key] = normalized_bbox
    return normalized_bbox


def _get_text_bbox_dims(font: Any, text: str, is_bold: bool = False) -> tuple[int, int]:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_text_bbox_dims(font_path, font_index, font_size, text, bool(is_bold))
    cache_key = (str(text), bool(is_bold))
    dims_cache = _get_font_object_cache(font, '_tategaki_text_bbox_dims_cache')
    if dims_cache is not None and cache_key in dims_cache:
        cached = dims_cache[cache_key]
        return int(cached[0]), int(cached[1])
    bbox = _get_text_bbox(font, text, is_bold=is_bold)
    resolved = (max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1]))
    dims_cache = _get_or_create_font_object_cache(font, '_tategaki_text_bbox_dims_cache')
    if dims_cache is not None:
        dims_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=2048)
def _cached_tatechuyoko_candidate_dims(font_path: str, font_index: int, font_size: int, text: str,
                                       is_bold: bool, is_italic: bool) -> tuple[int, int]:
    _refresh_core_globals()
    glyph_w, glyph_h = _cached_text_bbox_dims(font_path, font_index, font_size, text, bool(is_bold))
    if is_italic:
        glyph_w += _italic_extra_width(glyph_h)
    return glyph_w, glyph_h


def _estimate_tatechuyoko_candidate_dims(font: Any, text: str, is_bold: bool = False, is_italic: bool = False) -> tuple[int, int]:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_tatechuyoko_candidate_dims(font_path, font_index, font_size, text, bool(is_bold), bool(is_italic))
    cache_key = (str(text), bool(is_bold), bool(is_italic))
    dims_cache = _get_font_object_cache(font, '_tategaki_tatechuyoko_candidate_dims_cache')
    if dims_cache is not None and cache_key in dims_cache:
        cached = dims_cache[cache_key]
        return int(cached[0]), int(cached[1])
    glyph_w, glyph_h = _get_text_bbox_dims(font, text, is_bold=is_bold)
    if is_italic:
        glyph_w += _italic_extra_width(glyph_h)
    resolved = (glyph_w, glyph_h)
    dims_cache = _get_or_create_font_object_cache(font, '_tategaki_tatechuyoko_candidate_dims_cache')
    if dims_cache is not None:
        dims_cache[cache_key] = resolved
    return resolved


def _finalize_tatechuyoko_fit_size(resolved_size: int | None, start_size: int) -> int:
    # When no candidate size fits, keep the logical base size and let the bundle
    # builder clamp the rendered glyph image to the target cell bounds.
    return int(start_size if resolved_size is None else resolved_size)


@lru_cache(maxsize=1024)
def _cached_tatechuyoko_fit_size(font_path: str, font_index: int, f_size: int, text: str, is_bold: bool, is_italic: bool) -> int:
    _refresh_core_globals()
    max_w, max_h, start_size = _tatechuyoko_layout_limits(f_size, len(text))
    resolved_size: int | None = None
    for size in range(start_size, 5, -1):
        cand_w, cand_h = _cached_tatechuyoko_candidate_dims(font_path, font_index, size, text, is_bold, is_italic)
        if cand_w <= max_w and cand_h <= max_h:
            resolved_size = size
            break
    return _finalize_tatechuyoko_fit_size(resolved_size, start_size)


def _resolve_tatechuyoko_fit_size(font: Any, f_size: int, text: str, *, is_bold: bool = False, is_italic: bool = False) -> int:
    _refresh_core_globals()
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, _font_size = cacheable_spec
        return _cached_tatechuyoko_fit_size(font_path, font_index, int(f_size), str(text), bool(is_bold), bool(is_italic))
    cache_key = (int(f_size), str(text), bool(is_bold), bool(is_italic))
    fit_cache = _get_font_object_cache(font, '_tategaki_tatechuyoko_fit_size_cache')
    if fit_cache is not None and cache_key in fit_cache:
        return int(fit_cache[cache_key])
    max_w, max_h, start_size = _tatechuyoko_layout_limits(f_size, len(text))
    resolved_size: int | None = None
    for size in range(start_size, 5, -1):
        sub_font = _make_font_variant(font, size)
        cand_w, cand_h = _estimate_tatechuyoko_candidate_dims(sub_font, text, is_bold=is_bold, is_italic=is_italic)
        if cand_w <= max_w and cand_h <= max_h:
            resolved_size = size
            break
        if sub_font is font:
            break
    finalized_size = _finalize_tatechuyoko_fit_size(resolved_size, start_size)
    fit_cache = _get_or_create_font_object_cache(font, '_tategaki_tatechuyoko_fit_size_cache')
    if fit_cache is not None:
        fit_cache[cache_key] = int(finalized_size)
    return int(finalized_size)


@lru_cache(maxsize=1024)
def _cached_tatechuyoko_bundle(font_path: str, font_index: int, f_size: int, text: str, is_bold: bool, is_italic: bool) -> tuple[Image.Image, Image.Image]:
    _refresh_core_globals()
    max_w, max_h, _start_size = _tatechuyoko_layout_limits(f_size, len(text))
    fit_size = _cached_tatechuyoko_fit_size(font_path, font_index, f_size, text, bool(is_bold), bool(is_italic))
    render_font = load_truetype_font(build_font_spec(font_path, font_index), fit_size)
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(text, render_font, is_bold=is_bold, is_italic=is_italic)
    if glyph_img.width > max_w or glyph_img.height > max_h:
        scale = min(max_w / glyph_img.width, max_h / glyph_img.height)
        resized = (
            max(1, int(round(glyph_img.width * scale))),
            max(1, int(round(glyph_img.height * scale))),
        )
        glyph_img = glyph_img.resize(resized, Image.Resampling.LANCZOS)
        glyph_mask = glyph_mask.resize(resized, Image.Resampling.LANCZOS)
    return glyph_img, glyph_mask


def _build_tatechuyoko_bundle(font: Any, text: str, f_size: int, *, is_bold: bool = False, is_italic: bool = False) -> tuple[Image.Image, Image.Image]:
    _refresh_core_globals()
    cache_key = (str(text), int(f_size), bool(is_bold), bool(is_italic))
    bundle_cache = _get_font_object_cache(font, '_tategaki_tatechuyoko_bundle_cache')
    if bundle_cache is not None and cache_key in bundle_cache:
        return bundle_cache[cache_key]
    max_w, max_h, _start_size = _tatechuyoko_layout_limits(f_size, len(text))
    fit_size = _resolve_tatechuyoko_fit_size(font, f_size, text, is_bold=is_bold, is_italic=is_italic)
    chosen_font = _make_font_variant(font, fit_size)
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(text, chosen_font, is_bold=is_bold, is_italic=is_italic)
    if glyph_img.width > max_w or glyph_img.height > max_h:
        scale = min(max_w / glyph_img.width, max_h / glyph_img.height)
        resized = (
            max(1, int(round(glyph_img.width * scale))),
            max(1, int(round(glyph_img.height * scale))),
        )
        glyph_img = glyph_img.resize(resized, Image.Resampling.LANCZOS)
        glyph_mask = glyph_mask.resize(resized, Image.Resampling.LANCZOS)
    bundle = (glyph_img, glyph_mask)
    bundle_cache = _get_or_create_font_object_cache(font, '_tategaki_tatechuyoko_bundle_cache')
    if bundle_cache is not None:
        bundle_cache[cache_key] = bundle
    return bundle


@lru_cache(maxsize=512)
def _tatechuyoko_paste_offsets(f_size: int, glyph_w: int, glyph_h: int) -> tuple[int, int]:
    return max(0, (int(f_size) - int(glyph_w)) // 2), max(0, (int(f_size) - int(glyph_h)) // 2)


def draw_tatechuyoko(draw: Any, text: str, pos_tuple: tuple[int, int], font: Any, f_size: int, is_bold: bool = False, is_italic: bool = False) -> None:
    _refresh_core_globals()
    curr_x, curr_y = pos_tuple
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, _font_size = cacheable_spec
        glyph_img, glyph_mask = _cached_tatechuyoko_bundle(font_path, font_index, f_size, text, bool(is_bold), bool(is_italic))
    else:
        glyph_img, glyph_mask = _build_tatechuyoko_bundle(font, text, f_size, is_bold=is_bold, is_italic=is_italic)
    gw, gh = glyph_img.size
    off_x, off_y = _tatechuyoko_paste_offsets(f_size, gw, gh)
    _paste_glyph_image(draw, glyph_img, (curr_x + off_x, curr_y + off_y), glyph_mask)


def _should_center_ascii_glyph(char: str) -> bool:
    return _classify_tate_draw_char(char) == 'ascii_center'


def _tokenize_vertical_text_impl(text: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] in '！？!?' and text[i + 1] in '！？!?':
            token = text[i:i + 2]
            if token in DOUBLE_PUNCT_TOKENS:
                tokens.append(token)
                i += 2
                continue
        if text[i].isascii() and text[i].isalnum():
            j = i + 1
            while j < len(text) and text[j].isascii() and text[j].isalnum():
                j += 1
            run = text[i:j]
            if _is_tatechuyoko_token(run):
                tokens.append(run)
            else:
                tokens.extend(list(run))
            i = j
            continue
        tokens.append(text[i])
        i += 1
    return tokens


@lru_cache(maxsize=512)
def _tokenize_vertical_text_cached(text: str) -> tuple[str, ...]:
    return tuple(_tokenize_vertical_text_impl(text))


def _tokenize_vertical_text(text: str) -> list[str]:
    return list(_tokenize_vertical_text_cached(str(text or '')))


def _is_line_head_forbidden(token: str) -> bool:
    if not token:
        return False
    if token in DOUBLE_PUNCT_TOKENS:
        return True
    return all(ch in LINE_HEAD_FORBIDDEN_CHARS for ch in token)


def _is_line_end_forbidden(token: str) -> bool:
    if not token:
        return False
    return all(ch in LINE_END_FORBIDDEN_CHARS for ch in token)


def _is_hanging_punctuation(token: str) -> bool:
    return bool(token) and len(token) == 1 and token in HANGING_PUNCTUATION_CHARS


def _is_continuous_punctuation_pair(current_token: str, next_token: str) -> bool:
    if not current_token or not next_token:
        return False
    if len(current_token) != 1 or len(next_token) != 1:
        return False
    return (current_token + next_token) in CONTINUOUS_PUNCTUATION_PAIRS


def _continuous_punctuation_run_length(tokens: Sequence[str], start_idx: int) -> int:
    if start_idx >= len(tokens):
        return 0
    token = tokens[start_idx]
    if not token or len(token) != 1 or token not in REPEATABLE_CONTINUOUS_PUNCT_CHARS:
        return 0
    idx = start_idx + 1
    while idx < len(tokens) and tokens[idx] == token:
        idx += 1
    run_len = idx - start_idx
    return run_len if run_len >= 2 else 0


def _closing_punctuation_group_length(tokens: Sequence[str], start_idx: int) -> int:
    if start_idx >= len(tokens):
        return 0
    idx = start_idx
    while idx < len(tokens):
        token = tokens[idx]
        if not token or len(token) != 1 or token not in CLOSE_BRACKET_CHARS:
            break
        idx += 1
    if idx == start_idx:
        return 0
    tail_idx = idx
    while tail_idx < len(tokens):
        token = tokens[tail_idx]
        if token in DOUBLE_PUNCT_TOKENS:
            tail_idx += 1
            continue
        if len(token) == 1 and token in TAIL_PUNCTUATION_CHARS:
            tail_idx += 1
            continue
        break
    if tail_idx == idx:
        return idx - start_idx
    return tail_idx - start_idx


def _minimum_safe_group_length(tokens: Sequence[str], start_idx: int) -> int:
    """start_idx から、行末/行頭禁則を破らず同一行へ残すための最小まとまり長を返す。"""
    if start_idx >= len(tokens):
        return 0
    for end_idx in range(start_idx, len(tokens)):
        tail_token = tokens[end_idx]
        if _is_line_end_forbidden(tail_token):
            continue
        if end_idx + 1 < len(tokens):
            next_token = tokens[end_idx + 1]
            if _is_line_head_forbidden(next_token):
                continue
            if _is_continuous_punctuation_pair(tail_token, next_token):
                continue
        return end_idx - start_idx + 1
    return len(tokens) - start_idx


def _protected_token_group_length(tokens: Sequence[str], start_idx: int) -> int:
    return max(
        _continuous_punctuation_run_length(tokens, start_idx),
        _closing_punctuation_group_length(tokens, start_idx),
        _minimum_safe_group_length(tokens, start_idx),
    )


@lru_cache(maxsize=512)
def _build_single_token_vertical_layout_hints(token: str) -> VerticalLayoutHints:
    line_head_forbidden = _is_line_head_forbidden(token)
    line_end_forbidden = _is_line_end_forbidden(token)
    hanging_punctuation = _is_hanging_punctuation(token)
    return {
        'line_head_forbidden': (line_head_forbidden,),
        'line_end_forbidden': (line_end_forbidden,),
        'hanging_punctuation': (hanging_punctuation,),
        'continuous_pair_with_next': (False,),
        'protected_group_len': (1,),
        'would_start_forbidden_after_hang_pair': (False,),
    }


@lru_cache(maxsize=512)
def _build_two_token_vertical_layout_hints(first_token: str, second_token: str) -> VerticalLayoutHints:
    token_pair = (first_token, second_token)
    first_line_head_forbidden = _is_line_head_forbidden(first_token)
    second_line_head_forbidden = _is_line_head_forbidden(second_token)
    first_line_end_forbidden = _is_line_end_forbidden(first_token)
    second_line_end_forbidden = _is_line_end_forbidden(second_token)
    first_hanging_punctuation = _is_hanging_punctuation(first_token)
    second_hanging_punctuation = _is_hanging_punctuation(second_token)
    continuous_pair = _is_continuous_punctuation_pair(first_token, second_token)
    first_would_start_forbidden_after_hang_pair = first_hanging_punctuation and second_line_head_forbidden
    return {
        'line_head_forbidden': (first_line_head_forbidden, second_line_head_forbidden),
        'line_end_forbidden': (first_line_end_forbidden, second_line_end_forbidden),
        'hanging_punctuation': (first_hanging_punctuation, second_hanging_punctuation),
        'continuous_pair_with_next': (continuous_pair, False),
        'protected_group_len': (
            _protected_token_group_length(token_pair, 0),
            _protected_token_group_length(token_pair, 1),
        ),
        'would_start_forbidden_after_hang_pair': (
            first_would_start_forbidden_after_hang_pair,
            False,
        ),
    }


@lru_cache(maxsize=512)
def _build_three_token_vertical_layout_hints(first_token: str, second_token: str, third_token: str) -> VerticalLayoutHints:
    token_triplet = (first_token, second_token, third_token)
    first_line_head_forbidden = _is_line_head_forbidden(first_token)
    second_line_head_forbidden = _is_line_head_forbidden(second_token)
    third_line_head_forbidden = _is_line_head_forbidden(third_token)
    first_line_end_forbidden = _is_line_end_forbidden(first_token)
    second_line_end_forbidden = _is_line_end_forbidden(second_token)
    third_line_end_forbidden = _is_line_end_forbidden(third_token)
    first_hanging_punctuation = _is_hanging_punctuation(first_token)
    second_hanging_punctuation = _is_hanging_punctuation(second_token)
    third_hanging_punctuation = _is_hanging_punctuation(third_token)
    first_continuous_pair = _is_continuous_punctuation_pair(first_token, second_token)
    second_continuous_pair = _is_continuous_punctuation_pair(second_token, third_token)
    return {
        'line_head_forbidden': (first_line_head_forbidden, second_line_head_forbidden, third_line_head_forbidden),
        'line_end_forbidden': (first_line_end_forbidden, second_line_end_forbidden, third_line_end_forbidden),
        'hanging_punctuation': (first_hanging_punctuation, second_hanging_punctuation, third_hanging_punctuation),
        'continuous_pair_with_next': (first_continuous_pair, second_continuous_pair, False),
        'protected_group_len': (
            _protected_token_group_length(token_triplet, 0),
            _protected_token_group_length(token_triplet, 1),
            _protected_token_group_length(token_triplet, 2),
        ),
        'would_start_forbidden_after_hang_pair': (
            third_line_head_forbidden,
            False,
            False,
        ),
    }


@lru_cache(maxsize=512)
def _build_four_token_vertical_layout_hints(first_token: str, second_token: str, third_token: str, fourth_token: str) -> VerticalLayoutHints:
    token_quad = (first_token, second_token, third_token, fourth_token)
    first_line_head_forbidden = _is_line_head_forbidden(first_token)
    second_line_head_forbidden = _is_line_head_forbidden(second_token)
    third_line_head_forbidden = _is_line_head_forbidden(third_token)
    fourth_line_head_forbidden = _is_line_head_forbidden(fourth_token)
    first_line_end_forbidden = _is_line_end_forbidden(first_token)
    second_line_end_forbidden = _is_line_end_forbidden(second_token)
    third_line_end_forbidden = _is_line_end_forbidden(third_token)
    fourth_line_end_forbidden = _is_line_end_forbidden(fourth_token)
    first_hanging_punctuation = _is_hanging_punctuation(first_token)
    second_hanging_punctuation = _is_hanging_punctuation(second_token)
    third_hanging_punctuation = _is_hanging_punctuation(third_token)
    fourth_hanging_punctuation = _is_hanging_punctuation(fourth_token)
    first_continuous_pair = _is_continuous_punctuation_pair(first_token, second_token)
    second_continuous_pair = _is_continuous_punctuation_pair(second_token, third_token)
    third_continuous_pair = _is_continuous_punctuation_pair(third_token, fourth_token)
    return {
        'line_head_forbidden': (
            first_line_head_forbidden,
            second_line_head_forbidden,
            third_line_head_forbidden,
            fourth_line_head_forbidden,
        ),
        'line_end_forbidden': (
            first_line_end_forbidden,
            second_line_end_forbidden,
            third_line_end_forbidden,
            fourth_line_end_forbidden,
        ),
        'hanging_punctuation': (
            first_hanging_punctuation,
            second_hanging_punctuation,
            third_hanging_punctuation,
            fourth_hanging_punctuation,
        ),
        'continuous_pair_with_next': (
            first_continuous_pair,
            second_continuous_pair,
            third_continuous_pair,
            False,
        ),
        'protected_group_len': (
            _protected_token_group_length(token_quad, 0),
            _protected_token_group_length(token_quad, 1),
            _protected_token_group_length(token_quad, 2),
            _protected_token_group_length(token_quad, 3),
        ),
        'would_start_forbidden_after_hang_pair': (
            third_line_head_forbidden,
            fourth_line_head_forbidden,
            False,
            False,
        ),
    }


@lru_cache(maxsize=512)
def _build_vertical_layout_hints_cached(tokens: tuple[str, ...]) -> VerticalLayoutHints:
    _refresh_core_globals()
    token_count = len(tokens)
    if token_count <= 0:
        empty_bools: tuple[bool, ...] = ()
        empty_ints: tuple[int, ...] = ()
        return {
            'line_head_forbidden': empty_bools,
            'line_end_forbidden': empty_bools,
            'hanging_punctuation': empty_bools,
            'continuous_pair_with_next': empty_bools,
            'protected_group_len': empty_ints,
            'would_start_forbidden_after_hang_pair': empty_bools,
        }
    if token_count == 1:
        return _build_single_token_vertical_layout_hints(tokens[0])
    if token_count == 2:
        return _build_two_token_vertical_layout_hints(tokens[0], tokens[1])
    if token_count == 3:
        return _build_three_token_vertical_layout_hints(tokens[0], tokens[1], tokens[2])
    if token_count == 4:
        return _build_four_token_vertical_layout_hints(tokens[0], tokens[1], tokens[2], tokens[3])

    line_head_forbidden = [False] * token_count
    line_end_forbidden = [False] * token_count
    hanging_punctuation = [False] * token_count
    continuous_pair_with_next = [False] * token_count
    would_start_forbidden_after_hang_pair = [False] * token_count

    for idx, token in enumerate(tokens):
        line_head_forbidden[idx] = _is_line_head_forbidden(token)
        line_end_forbidden[idx] = _is_line_end_forbidden(token)
        hanging_punctuation[idx] = _is_hanging_punctuation(token)

    for idx in range(token_count - 1):
        continuous_pair_with_next[idx] = _is_continuous_punctuation_pair(tokens[idx], tokens[idx + 1])

    for idx in range(token_count - 2):
        would_start_forbidden_after_hang_pair[idx] = line_head_forbidden[idx + 2]

    same_run_len = [0] * token_count
    continuous_run_len = [0] * token_count
    close_run_len = [0] * token_count
    tail_run_len = [0] * token_count

    for idx in range(token_count - 1, -1, -1):
        token = tokens[idx]
        if idx + 1 < token_count and tokens[idx + 1] == token:
            same_run_len[idx] = same_run_len[idx + 1] + 1
        else:
            same_run_len[idx] = 1
        if token and len(token) == 1 and token in REPEATABLE_CONTINUOUS_PUNCT_CHARS and same_run_len[idx] >= 2:
            continuous_run_len[idx] = same_run_len[idx]
        if token and len(token) == 1 and token in CLOSE_BRACKET_CHARS:
            close_run_len[idx] = 1 + (close_run_len[idx + 1] if idx + 1 < token_count else 0)
        if token in DOUBLE_PUNCT_TOKENS or (len(token) == 1 and token in TAIL_PUNCTUATION_CHARS):
            tail_run_len[idx] = 1 + (tail_run_len[idx + 1] if idx + 1 < token_count else 0)

    closing_group_len = [0] * token_count
    for idx in range(token_count):
        close_len = close_run_len[idx]
        if close_len <= 0:
            continue
        tail_idx = idx + close_len
        closing_group_len[idx] = close_len + (tail_run_len[tail_idx] if tail_idx < token_count else 0)

    safe_tail = [False] * token_count
    for idx in range(token_count):
        if line_end_forbidden[idx]:
            continue
        if idx + 1 < token_count and (line_head_forbidden[idx + 1] or continuous_pair_with_next[idx]):
            continue
        safe_tail[idx] = True

    minimum_safe_group_len = [0] * token_count
    next_safe_tail_idx = token_count
    for idx in range(token_count - 1, -1, -1):
        if safe_tail[idx]:
            next_safe_tail_idx = idx
        minimum_safe_group_len[idx] = max(0, next_safe_tail_idx - idx + 1) if next_safe_tail_idx < token_count else (token_count - idx)

    protected_group_len = [0] * token_count
    for idx in range(token_count):
        protected_group_len[idx] = max(continuous_run_len[idx], closing_group_len[idx], minimum_safe_group_len[idx])

    return {
        'line_head_forbidden': tuple(line_head_forbidden),
        'line_end_forbidden': tuple(line_end_forbidden),
        'hanging_punctuation': tuple(hanging_punctuation),
        'continuous_pair_with_next': tuple(continuous_pair_with_next),
        'protected_group_len': tuple(protected_group_len),
        'would_start_forbidden_after_hang_pair': tuple(would_start_forbidden_after_hang_pair),
    }


def _build_vertical_layout_hints(tokens: Sequence[str]) -> VerticalLayoutHints:
    _refresh_core_globals()
    return _build_vertical_layout_hints_cached(tokens if isinstance(tokens, tuple) else tuple(tokens))


def _choose_vertical_layout_action_with_hints(hints: VerticalLayoutHints, idx: int, slots_left: int, current_not_top: bool, kinsoku_mode: str = 'standard', action_cache: dict[tuple[int, int, bool], str] | None = None) -> str:
    mode = kinsoku_mode if kinsoku_mode in {'standard', 'simple', 'off'} else _normalize_kinsoku_mode(kinsoku_mode)
    cache_key: tuple[int, int, bool] | None = None
    if action_cache is not None:
        cache_key = (idx, slots_left, bool(current_not_top))
        cached = action_cache.get(cache_key)
        if cached is not None:
            return cached

    token_count = len(hints['line_head_forbidden'])
    if idx >= token_count:
        result = 'done'
    elif slots_left <= 0:
        result = 'advance'
    elif mode == 'off':
        result = 'draw'
    else:
        line_end_forbidden = hints['line_end_forbidden'][idx]
        if slots_left == 1 and current_not_top and line_end_forbidden:
            result = 'advance'
        elif slots_left == 1 and current_not_top and idx + 1 < token_count:
            if mode == 'standard' and hints['continuous_pair_with_next'][idx]:
                result = 'advance'
            elif hints['hanging_punctuation'][idx + 1] and not line_end_forbidden:
                if mode == 'standard' and hints['would_start_forbidden_after_hang_pair'][idx]:
                    result = 'advance'
                else:
                    result = 'hang_pair'
            elif hints['line_head_forbidden'][idx + 1]:
                result = 'advance'
            else:
                result = 'draw'
        elif mode == 'simple':
            result = 'draw'
        elif hints['protected_group_len'][idx] >= 2 and slots_left < hints['protected_group_len'][idx] and current_not_top:
            result = 'advance'
        elif line_end_forbidden and current_not_top and idx + 1 < token_count and slots_left >= 2:
            next_action = _choose_vertical_layout_action_with_hints(
                hints, idx + 1, slots_left - 1, True,
                kinsoku_mode=mode, action_cache=action_cache,
            )
            result = 'advance' if next_action == 'advance' else 'draw'
        else:
            result = 'draw'

    if action_cache is not None and cache_key is not None:
        action_cache[cache_key] = result
    return result


def _normalize_kinsoku_mode(mode: object) -> str:
    mode = str(mode or 'standard').strip().lower()
    return mode if mode in {'off', 'simple', 'standard'} else 'standard'


@lru_cache(maxsize=128)
def _effective_vertical_layout_bottom_margin(margin_b: int, font_size: int) -> int:
    """Return the bottom guard used by the vertical line grid.

    The bottom margin is specified in pixels, but the vertical text renderer advances
    in whole ``font_size + 2`` cells.  With combinations such as top margin 0 and
    bottom margin 12, the old slot calculation could keep the same last text cell as
    bottom margin 0, making the preview look as if the bottom margin had been ignored.
    Add a small font-scaled descender guard only when a positive bottom margin is
    requested so the bottom margin is visibly reserved without changing true zero
    margin layouts.
    """
    margin_b = max(0, int(margin_b or 0))
    font_size = max(1, int(font_size or 1))
    if margin_b <= 0:
        return 0
    descender_guard = max(2, int(round(font_size * 0.25)))
    return margin_b + descender_guard


def _remaining_vertical_slots(curr_y: int, height: int, margin_b: int, font_size: int) -> int:
    effective_margin_b = _effective_vertical_layout_bottom_margin(margin_b, font_size)
    limit = height - effective_margin_b - font_size
    if curr_y > limit:
        return 0
    return 1 + (limit - curr_y) // (font_size + 2)


def _remaining_vertical_slots_for_current_column(
    curr_y: int,
    margin_t: int,
    height: int,
    margin_b: int,
    font_size: int,
    wrap_indent_step: int = 0,
) -> int:
    """Return remaining body slots while preserving progress on tiny pages.

    Normal pages should respect the effective bottom guard from
    ``_remaining_vertical_slots``.  Extremely short pages can report no usable
    slots even at the top of a fresh column; in that case allow one progress
    slot so layout code does not keep advancing columns forever without
    consuming a token.
    """
    slots_left = _remaining_vertical_slots(curr_y, height, margin_b, font_size)
    top_y = int(margin_t or 0) + max(0, int(wrap_indent_step or 0))
    if slots_left <= 0 and int(curr_y or 0) <= top_y:
        return 1
    return slots_left


def _would_start_forbidden_after_hang_pair(tokens: Sequence[str], idx: int) -> bool:
    """idx, idx+1 を同一行へ置いた直後、次行頭が禁則になるなら True。"""
    next_idx = idx + 2
    if next_idx >= len(tokens):
        return False
    next_token = tokens[next_idx]
    return _is_line_head_forbidden(next_token)


def _choose_vertical_layout_action(tokens: Sequence[str], idx: int, curr_y: int, margin_t: int, height: int, margin_b: int, font_size: int, kinsoku_mode: str = 'standard') -> str:
    if idx >= len(tokens):
        return 'done'
    token = tokens[idx]
    slots_left = _remaining_vertical_slots(curr_y, height, margin_b, font_size)
    if slots_left == 0:
        return 'advance'

    mode = _normalize_kinsoku_mode(kinsoku_mode)
    if mode == 'off':
        return 'draw'

    if (
        slots_left == 1
        and curr_y > margin_t
        and _is_line_end_forbidden(token)
    ):
        return 'advance'
    if slots_left == 1 and curr_y > margin_t and idx + 1 < len(tokens):
        next_token = tokens[idx + 1]
        if mode == 'standard' and _is_continuous_punctuation_pair(token, next_token):
            return 'advance'
        if _is_hanging_punctuation(next_token) and not _is_line_end_forbidden(token):
            if mode == 'standard' and _would_start_forbidden_after_hang_pair(tokens, idx):
                return 'advance'
            return 'hang_pair'
        if _is_line_head_forbidden(next_token):
            return 'advance'

    if mode == 'simple':
        return 'draw'

    protected_group_len = _protected_token_group_length(tokens, idx)
    if (
        protected_group_len >= 2
        and slots_left < protected_group_len
        and curr_y > margin_t
    ):
        return 'advance'
    if (
        _is_line_end_forbidden(token)
        and curr_y > margin_t
        and idx + 1 < len(tokens)
        and slots_left >= 2
    ):
        next_curr_y = curr_y + font_size + 2
        next_action = _choose_vertical_layout_action(
            tokens, idx + 1, next_curr_y, margin_t, height, margin_b, font_size,
            kinsoku_mode=mode,
        )
        if next_action == 'advance':
            return 'advance'
    return 'draw'


@lru_cache(maxsize=128)
def _double_punctuation_layout(f_size: int) -> tuple[int, int, int]:
    sub_f_size = int(f_size * 0.75)
    half_w = f_size // 2
    char_offset = (half_w - sub_f_size) // 2
    return sub_f_size, half_w, char_offset


@lru_cache(maxsize=128)
def _double_punctuation_draw_offsets(f_size: int) -> tuple[int, int, int]:
    sub_f_size, half_w, char_offset = _double_punctuation_layout(f_size)
    first_x = char_offset + 10
    second_x = half_w + char_offset + 10
    return sub_f_size, first_x, second_x


@lru_cache(maxsize=128)
def _hanging_bottom_layout(f_size: int, is_kutoten: bool, extra_raise_ratio: float) -> tuple[int, int]:
    if is_kutoten:
        lower_ratio = max(0.22, 0.28 - float(extra_raise_ratio))
    else:
        lower_ratio = max(0.12, 0.20 - float(extra_raise_ratio))
    local_lower = max(1, int(round(f_size * lower_ratio)))
    return 0, local_lower


@lru_cache(maxsize=512)
def _hanging_bottom_draw_offsets(f_size: int, glyph_h: int, canvas_height: int, is_kutoten: bool,
                                 extra_raise_ratio: float) -> tuple[int, int]:
    draw_x_delta = _scaled_kutoten_offset(f_size)[0] if is_kutoten else 0
    base_raise, local_lower = _hanging_bottom_layout(f_size, bool(is_kutoten), float(extra_raise_ratio))
    desired_y = base_raise + local_lower
    cell_limit_y = max(0, int(f_size) - int(glyph_h) - 1)
    page_limit_y = int(canvas_height) - int(glyph_h) - 1 if canvas_height else cell_limit_y
    draw_y_delta = max(0, min(desired_y, cell_limit_y, page_limit_y))
    return int(draw_x_delta), int(draw_y_delta)


def _limit_draw_y_delta_to_page(draw_y_delta: int, curr_y: int, glyph_h: int, canvas_height: int) -> int:
    """Clamp a glyph-local Y delta so the final paste/draw stays inside the page.

    The hanging helpers compute offsets relative to the current text cell.  Their
    cached ``canvas_height`` guard only knows the page height, not the current
    cell's absolute Y position.  Near the bottom of a page, that can leave enough
    local offset to draw or paste the glyph below the image.  Keep upward
    adjustments intact while capping only the lower edge.
    """
    draw_y_delta = int(draw_y_delta)
    if not canvas_height:
        return draw_y_delta
    page_bottom_delta = int(canvas_height) - int(curr_y) - int(glyph_h) - 1
    return int(min(draw_y_delta, page_bottom_delta))


def _draw_hanging_text_near_bottom(
    draw: Any,
    original_char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    canvas_height: int,
    *,
    is_bold: bool = False,
    is_italic: bool = False,
    extra_raise_ratio: float = 0.0,
    anchor_visible_ink: bool = False,
    extra_y: int = 0,
) -> None:
    _refresh_core_globals()
    """
    Render a character near the bottom of the cell for hanging punctuation and
    closing brackets.  Characters that map to vertical variants via
    ``TATE_REPLACE`` are resolved accordingly; otherwise the original
    character is used.  For punctuation marks, an additional horizontal
    offset is applied via ``_scaled_kutoten_offset``.

    The implementation avoids unnecessary boolean/float coercions and
    trusts the helpers to perform any required normalisation internally.
    """
    curr_x, curr_y = pos_tuple
    # Resolve the character to be drawn.  Only call the expensive glyph
    # resolver when the mapping differs.
    mapped_char = TATE_REPLACE.get(original_char)
    if mapped_char and mapped_char != original_char:
        char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    else:
        char = original_char
    # Obtain the glyph height from the bounding box.  The helper returns a
    # minimal 1×1 bbox for missing glyphs, so no fallback is needed here.
    bbox_left, bbox_top, bbox_right, bbox_bottom = _get_text_bbox(font, char, is_bold=is_bold)
    glyph_h = max(1, bbox_bottom - bbox_top)
    # Determine if the original character is a punctuation mark that needs
    # additional horizontal shifting.
    is_kutoten = original_char in {"、", "。", "，", "．", "､", "｡"}
    # Compute draw deltas for positioning near the bottom of the cell.  Do
    # not wrap values into bool/float here; the callee handles that.
    draw_x_delta, draw_y_delta = _hanging_bottom_draw_offsets(
        f_size,
        glyph_h,
        canvas_height,
        is_kutoten,
        extra_raise_ratio,
    )
    if anchor_visible_ink:
        # sweep341: Some fonts expose closing-bracket glyphs with a large
        # positive bbox top.  Drawing them at the raw baseline makes the
        # visible horizontal stroke sink even though the logical offset is the
        # same.  For hanging closing brackets, anchor by the visible ink top
        # instead of the font baseline so low-bbox fonts are pulled back up.
        draw_y_delta -= int(bbox_top)
    draw_y_delta += int(extra_y)
    draw_y_delta = _limit_draw_y_delta_to_page(draw_y_delta, curr_y, glyph_h, canvas_height)
    # When hanging, we deliberately avoid applying the usual upward
    # correction used for normal punctuation.  Without this, the mark
    # would overlap with the preceding character.
    draw_weighted_text(
        draw,
        (curr_x + draw_x_delta, curr_y + draw_y_delta),
        char,
        font,
        is_bold=is_bold,
        is_italic=is_italic,
    )




def _is_lowerable_hanging_closing_bracket(token: str) -> bool:
    return bool(token) and len(token) == 1 and token in LOWERABLE_HANGING_CLOSING_BRACKET_CHARS


def draw_hanging_closing_bracket(draw: Any, char: str, pos_tuple: tuple[int, int], font: Any, f_size: int, canvas_height: int, is_bold: bool = False, ruby_mode: bool = False, is_italic: bool = False) -> None:
    _refresh_core_globals()
    lower_closing_bracket_position_mode = _draw_glyph_position_mode(
        draw,
        '_tategaki_lower_closing_bracket_position_mode',
    )
    _draw_hanging_text_near_bottom(
        draw, char, pos_tuple, font, f_size, canvas_height,
        is_bold=is_bold, is_italic=is_italic, extra_raise_ratio=0.18,
        anchor_visible_ink=True,
        extra_y=_lower_closing_bracket_extra_y_for_mode(char, f_size, lower_closing_bracket_position_mode),
    )


@lru_cache(maxsize=128)
def _tate_punctuation_layout_insets(f_size: int, next_cell: bool, fallback_layout: bool, position_mode: str = 'standard') -> tuple[int, int, int]:
    if fallback_layout:
        right_inset = max(1, int(round(f_size * 0.08)))
        top_inset = max(1, int(round(f_size * 0.06)))
    else:
        right_inset = max(0, int(round(f_size * 0.03)))
        top_inset = max(4, int(round(f_size * (0.25 if next_cell else 0.10))))
    # 位置モードによる上下補正は _punctuation_extra_y_for_mode() で
    # off_y に直接加える。top_inset を増やすと bottom anchor 計算では
    # かえって上方向へ動くため、ここでは標準レイアウトを維持する。
    extra_raise = max(2, int(round(f_size * 0.18))) if next_cell else 0
    return right_inset, top_inset, extra_raise


@lru_cache(maxsize=128)
def _tate_hanging_punctuation_raise(f_size: int, fallback_layout: bool) -> int:
    # clean203〜sweep312 で維持していた「ぶら下げ句読点を少し上へ戻す」仕様を、
    # right/bottom アンカー方式の上に重ねる。
    # sweep317: sweep316 の一律強め補正は大きいフォント/インク幅の広い
    # フォントで本文と重なる副作用があったため、基礎持ち上げ量を少し戻し、
    # 実際の安全域判定を _tate_hanging_punctuation_min_top_offset 側で行う。
    base_ratio = 0.30 if not fallback_layout else 0.24
    return max(3, int(round(f_size * base_ratio)))


@lru_cache(maxsize=128)
def _tate_hanging_punctuation_visual_targets(f_size: int, fallback_layout: bool) -> tuple[int, int, int]:
    cell_top = f_size + 2
    if fallback_layout:
        center_target = cell_top + int(round(f_size * 0.47))
        max_top = cell_top + int(round(f_size * 0.37))
        center_weight = 4
    else:
        center_target = cell_top + int(round(f_size * 0.43))
        max_top = cell_top + int(round(f_size * 0.34))
        center_weight = 5
    return center_target, max_top, center_weight


@lru_cache(maxsize=128)
def _tate_hanging_punctuation_min_top_offset(f_size: int, ink_top: int, ink_bottom: int, glyph_h: int) -> int:
    # sweep325: ごく一部のフォントで、ぶら下がり句読点のインクが前セルの本文へ
    # 重なるケースが残ったため、安全側の下限を少し下げる。単純に全体を下げすぎると
    # 「低すぎる」見え方へ戻るため、インク実高さとグリフキャンバス高さが大きい場合を
    # より強く保護する。
    ink_height = max(1, int(ink_bottom) - int(ink_top))
    f_size = max(1, int(f_size))
    glyph_h = max(1, int(glyph_h))
    if ink_height <= max(3, int(round(f_size * 0.24))):
        ratio = 0.62
    elif ink_height <= max(4, int(round(f_size * 0.42))):
        ratio = 0.68
    else:
        ratio = 0.76
    if f_size >= 48:
        ratio = max(ratio, 0.72)
    if glyph_h >= int(round(f_size * 0.85)):
        ratio = max(ratio, 0.78)
    if glyph_h >= int(round(f_size * 1.05)):
        ratio = max(ratio, 0.82)
    safety_top = int(round(f_size * ratio))
    return int(safety_top - int(ink_top))


@lru_cache(maxsize=1024)
def _tate_hanging_punctuation_offset_y(
    f_size: int,
    ink_top: int,
    ink_bottom: int,
    top_inset: int,
    extra_raise: int,
    canvas_height: int,
    glyph_h: int,
    fallback_layout: bool = False,
) -> int:
    cell_top = f_size + 2
    cell_bottom = cell_top + f_size - 1
    bottom_inset = max(2, top_inset - extra_raise)
    target_bottom = cell_bottom - bottom_inset
    offset_from_bottom = target_bottom - ink_bottom

    center_target, max_top, center_weight = _tate_hanging_punctuation_visual_targets(
        f_size,
        fallback_layout,
    )
    ink_center = (ink_top + ink_bottom) / 2.0
    offset_from_center = int(round(center_target - ink_center))

    weight_base = 10
    offset_y = int(round(
        ((offset_from_bottom * (weight_base - center_weight)) + (offset_from_center * center_weight)) / weight_base
    ))
    offset_y -= _tate_hanging_punctuation_raise(f_size, fallback_layout)

    max_top_offset = max_top - ink_top
    min_top_offset = _tate_hanging_punctuation_min_top_offset(f_size, ink_top, ink_bottom, glyph_h)
    offset_y = min(offset_y, max_top_offset)
    offset_y = max(offset_y, min_top_offset)

    if canvas_height:
        offset_y = min(offset_y, max(0, canvas_height - glyph_h - 1))
    return int(offset_y)


@lru_cache(maxsize=512)
def _tate_punctuation_direct_offsets(f_size: int, glyph_w: int, glyph_h: int, bbox_left: int, bbox_top: int,
                                     right_inset: int, top_inset: int, extra_raise: int,
                                     next_cell: bool, canvas_height: int, fallback_layout: bool = False) -> tuple[int, int]:
    offset_x = max(0, f_size - glyph_w - right_inset) - bbox_left
    if next_cell:
        bbox_bottom = bbox_top + glyph_h
        offset_y = _tate_hanging_punctuation_offset_y(
            f_size,
            bbox_top,
            bbox_bottom,
            top_inset,
            extra_raise,
            canvas_height,
            glyph_h + bbox_top,
            fallback_layout,
        )
    else:
        offset_y = top_inset - bbox_top
    if canvas_height:
        offset_y = min(offset_y, max(0, canvas_height - glyph_h - 1 - bbox_top))
    return int(offset_x), int(offset_y)


@lru_cache(maxsize=512)
def _tate_punctuation_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                    right_inset: int, top_inset: int, extra_raise: int,
                                    next_cell: bool, canvas_height: int, fallback_layout: bool = False) -> tuple[int, int]:
    offset_x = max(0, f_size - glyph_w - right_inset)
    if next_cell:
        offset_y = _tate_hanging_punctuation_offset_y(
            f_size,
            0,
            glyph_h,
            top_inset,
            extra_raise,
            canvas_height,
            glyph_h,
            fallback_layout,
        )
    else:
        offset_y = top_inset
    if canvas_height:
        offset_y = min(offset_y, max(0, canvas_height - glyph_h - 1))
    return int(offset_x), int(offset_y)


def _draw_tate_punctuation_glyph(
    draw: Any,
    glyph_char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    *,
    is_bold: bool = False,
    is_italic: bool = False,
    next_cell: bool = False,
    canvas_height: int = 0,
    fallback_layout: bool = False,
    position_mode: str = 'standard',
) -> None:
    _refresh_core_globals()
    """句読点は画像ベースで描画し、ぶら下がり時は実際の描画下端に合わせる。"""
    _refresh_core_globals()
    curr_x, curr_y = pos_tuple

    right_inset, top_inset, extra_raise = _tate_punctuation_layout_insets(
        f_size,
        next_cell,
        fallback_layout,
        position_mode,
    )

    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(
        glyph_char,
        font,
        is_bold=is_bold,
        is_italic=is_italic,
    )
    glyph_w, glyph_h = glyph_img.size

    off_x = max(0, f_size - glyph_w - right_inset)
    if next_cell:
        bbox = glyph_mask.getbbox() if glyph_mask else None
        if bbox:
            _ink_left, ink_top, _ink_right, ink_bottom = bbox
        else:
            ink_top, ink_bottom = 0, glyph_h
        off_y = _tate_hanging_punctuation_offset_y(
            f_size,
            ink_top,
            ink_bottom,
            top_inset,
            extra_raise,
            canvas_height,
            glyph_h,
            fallback_layout,
        )
        off_y += _punctuation_extra_y_for_mode(f_size, position_mode)
    else:
        off_y = top_inset

    off_y = _limit_draw_y_delta_to_page(off_y, curr_y, glyph_h, canvas_height)

    _paste_glyph_image(
        draw,
        glyph_img,
        (curr_x + int(off_x), curr_y + int(off_y)),
        glyph_mask,
    )


def _vertical_dot_leader_count(char: str) -> int:
    if char in VERTICAL_DOT_LEADER_THREE_CHARS:
        return 3
    if char in VERTICAL_DOT_LEADER_TWO_CHARS:
        return 2
    return 0


def draw_vertical_dot_leader(draw: Any, char: str, pos_tuple: tuple[int, int], f_size: int, *, is_bold: bool = False) -> None:
    """三点リーダ/二点リーダをフォント非依存の縦点列として描画する。"""
    dot_count = _vertical_dot_leader_count(char)
    if dot_count <= 0:
        return
    curr_x, curr_y = pos_tuple
    f_size = max(1, int(f_size or 1))
    dot_diameter = max(2, int(round(f_size * (0.145 if is_bold else 0.125))))
    # sweep316: フォント任せをやめた dot leader はセル基準で描くため、
    # 以前の 0.25/0.50/0.75 では実際の文字重心より上側に見えるフォントがあった。
    # 点列全体を少し下げ、下端に触れない範囲で視覚中央へ寄せる。
    # sweep317: 点列が上寄りに見える環境が残ったため、セル中央より
    # やや下側へ再配置する。下端には触れないよう max_center_y で制限する。
    centers = (0.48, 0.76) if dot_count == 2 else (0.39, 0.63, 0.86)
    center_x = curr_x + (f_size / 2.0)
    max_center_y = curr_y + f_size - (dot_diameter / 2.0) - 1
    for ratio in centers:
        center_y = min(curr_y + (f_size * ratio), max_center_y)
        left = int(round(center_x - dot_diameter / 2.0))
        top = int(round(center_y - dot_diameter / 2.0))
        right = left + dot_diameter
        bottom = top + dot_diameter
        draw.ellipse((left, top, right, bottom), fill=0)


def draw_hanging_punctuation(draw: Any, char: str, pos_tuple: tuple[int, int], font: Any, f_size: int, canvas_height: int, is_bold: bool = False, ruby_mode: bool = False, is_italic: bool = False) -> None:
    _refresh_core_globals()
    if _is_render_spacing_char(char):
        return
    previous_capture = getattr(draw, '_tategaki_capture_hanging_punctuation_overlay', False)
    try:
        setattr(draw, '_tategaki_capture_hanging_punctuation_overlay', True)
    except Exception:
        pass
    try:
        if char in {'，', '．', '､', '｡'}:
            _draw_tate_punctuation_glyph(
                draw,
                char,
                pos_tuple,
                font,
                f_size,
                is_bold=is_bold,
                is_italic=is_italic,
                next_cell=True,
                canvas_height=canvas_height,
                fallback_layout=False,
                position_mode=_draw_glyph_position_mode(draw, '_tategaki_punctuation_position_mode'),
            )
            return
        glyph_char, fallback_layout = _resolve_tate_punctuation_draw(
            char,
            font,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        _draw_tate_punctuation_glyph(
            draw,
            glyph_char,
            pos_tuple,
            font,
            f_size,
            is_bold=is_bold,
            is_italic=is_italic,
            next_cell=True,
            canvas_height=canvas_height,
            fallback_layout=fallback_layout,
            position_mode=_draw_glyph_position_mode(draw, '_tategaki_punctuation_position_mode'),
        )
    finally:
        try:
            setattr(draw, '_tategaki_capture_hanging_punctuation_overlay', previous_capture)
        except Exception:
            pass


def draw_char_tate(draw: Any, char: str, pos_tuple: tuple[int, int], font: Any, f_size: int, is_bold: bool = False, ruby_mode: bool = False, is_italic: bool = False) -> None:
    _refresh_core_globals()
    curr_x, curr_y = pos_tuple
    draw_centered = draw_centered_glyph
    draw_weighted = draw_weighted_text
    compute_spec = _compute_tate_draw_spec
    tate_replace = TATE_REPLACE

    if _is_render_spacing_char(char):
        return

    if char in VERTICAL_DOT_LEADER_CHARS:
        draw_vertical_dot_leader(draw, char, (curr_x, curr_y), f_size, is_bold=is_bold)
        return

    if _is_tatechuyoko_token(char):
        draw_tatechuyoko(draw, char, (curr_x, curr_y), font, f_size, is_bold=is_bold, is_italic=is_italic)
        return

    original_char = char
    draw_kind = _classify_tate_draw_char(original_char)

    # 2文字（！？や！！）を横並びにする
    if draw_kind == 'double_punct':
        sub_f_size, first_x, second_x = _double_punctuation_draw_offsets(f_size)
        sub_font = _make_font_variant(font, sub_f_size)
        draw_weighted(draw, (curr_x + first_x, curr_y), original_char[0], sub_font, is_bold=is_bold, is_italic=is_italic)
        draw_weighted(draw, (curr_x + second_x, curr_y), original_char[1], sub_font, is_bold=is_bold, is_italic=is_italic)
        return

    if draw_kind == 'ichi':
        # sweep348: 「一」は実インクが薄く、単純なセル幾何中央だと通常漢字
        # より上寄りに見えやすい。通常漢字の見た目中心へ合わせ直し、
        # 縦書き本文中で中央に見える位置へ戻す。
        ichi_position_mode = _draw_glyph_position_mode(draw, '_tategaki_ichi_position_mode')
        draw_ink_centered_glyph(
            draw, original_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, rotate_degrees=0, align_to_text_flow=True, is_italic=is_italic,
            extra_y=_ichi_extra_y_for_mode(f_size, ichi_position_mode),
        )
        return

    if draw_kind == 'long_vowel':
        draw_centered(
            draw, original_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, rotate_degrees=90, align_to_text_flow=True, is_italic=is_italic,
        )
        return

    if draw_kind == 'ascii_center':
        draw_centered(
            draw, original_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, align_to_text_flow=False, is_italic=is_italic,
        )
        return

    if draw_kind == 'punctuation':
        if original_char not in tate_replace:
            # 文中句読点は補正モードでも標準位置を維持する。
            # 句読点位置補正は draw_hanging_punctuation() 経由の
            # ぶら下がり句読点だけに限定する。
            off_x, off_y = _scaled_kutoten_offset(f_size)
            draw_weighted(draw, (curr_x + off_x, curr_y + off_y), original_char, font, is_bold=is_bold, is_italic=is_italic)
            return
        resolved_char, fallback_layout = _resolve_tate_punctuation_draw(
            original_char,
            font,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        if fallback_layout:
            _draw_tate_punctuation_glyph(
                draw,
                resolved_char,
                (curr_x, curr_y),
                font,
                f_size,
                is_bold=is_bold,
                is_italic=is_italic,
                next_cell=False,
                fallback_layout=True,
                position_mode='standard',
            )
        else:
            off_x, off_y = _scaled_kutoten_offset(f_size)
            draw_weighted(draw, (curr_x + off_x, curr_y + off_y), resolved_char, font, is_bold=is_bold, is_italic=is_italic)
        return

    if draw_kind == 'small_kana':
        off_x, off_y = _small_kana_offset(f_size)
        draw_weighted(draw, (curr_x + off_x, curr_y + off_y), original_char, font, is_bold=is_bold, is_italic=is_italic)
        return

    if draw_kind == 'horizontal_bracket':
        resolved_char, rotate_degrees, extra_x, extra_y = _resolve_horizontal_bracket_draw(
            original_char,
            font,
            f_size,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        lower_closing_bracket_position_mode = _draw_glyph_position_mode(
            draw,
            '_tategaki_lower_closing_bracket_position_mode',
        )
        extra_y += _lower_closing_bracket_extra_y_for_mode(
            original_char,
            f_size,
            lower_closing_bracket_position_mode,
        )
        draw_centered(
            draw, resolved_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, rotate_degrees=rotate_degrees, align_to_text_flow=True, is_italic=is_italic,
            extra_x=extra_x, extra_y=extra_y,
        )
        return

    if draw_kind == 'default':
        if original_char not in tate_replace:
            draw_weighted(draw, (curr_x, curr_y), original_char, font, is_bold=is_bold, is_italic=is_italic)
            return
        resolved_char = _resolve_default_tate_draw(
            original_char,
            font,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        draw_weighted(draw, (curr_x, curr_y), resolved_char, font, is_bold=is_bold, is_italic=is_italic)
        return

    _draw_kind, resolved_char, _rotate_degrees, _extra_x, _extra_y, _off_x, _off_y, _fallback_layout = compute_spec(
        original_char,
        font,
        f_size,
        draw_kind=draw_kind,
        is_bold=is_bold,
        is_italic=is_italic,
    )
    draw_weighted(draw, (curr_x, curr_y), resolved_char, font, is_bold=is_bold, is_italic=is_italic)



# --- moved from tategakiXTC_gui_core.py lines 5414-6035 ---
# ==========================================
# --- プレビュー生成 ---
# ==========================================

def _build_default_preview_blocks() -> TextBlocks:
    """プレビュー専用の代表サンプルを TextBlock 形式で返す。"""
    # 青空文庫『吾輩は猫である』公開 XHTML の冒頭段落構成に合わせて、
    # 文中の不必要な改行を入れず、段落単位でプレビュー用に構成する。
    return [
        {
            "indent": True,
            "blank_before": 0,
            "runs": [
                {"text": "吾輩", "ruby": "わがはい", "bold": False},
                {"text": "は猫である。名前はまだ無い。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "どこで生れたかとんと", "ruby": "", "bold": False},
                {"text": "見当", "ruby": "けんとう", "bold": False},
                {"text": "がつかぬ。何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは", "ruby": "", "bold": False},
                {"text": "記憶", "ruby": "きおく", "bold": False},
                {"text": "している。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "吾輩はここで始めて人間というものを見た。しかもあとで聞くとそれは書生という人間中で一番", "ruby": "", "bold": False},
                {"text": "獰悪", "ruby": "どうあく", "bold": False},
                {"text": "な種族であったそうだ。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "この書生というのは時々我々を", "ruby": "", "bold": False},
                {"text": "捕", "ruby": "つかま", "bold": False},
                {"text": "えて", "ruby": "", "bold": False},
                {"text": "煮", "ruby": "に", "bold": False},
                {"text": "て食うという話である。しかしその当時は何という考もなかったから別段恐しいとも思わなかった。ただ彼の", "ruby": "", "bold": False},
                {"text": "掌", "ruby": "てのひら", "bold": False},
                {"text": "に載せられてスーと持ち上げられた時何だかフワフワした感じがあったばかりである。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "掌", "ruby": "てのひら", "bold": False},
                {"text": "の上で少し落ちついて書生の顔を見たのがいわゆる人間というものの", "ruby": "", "bold": False},
                {"text": "見始", "ruby": "みはじめ", "bold": False},
                {"text": "であろう。この時妙なものだと思った感じが今でも残っている。第一毛をもって装飾されべきはずの顔がつるつるしてまるで", "ruby": "", "bold": False},
                {"text": "薬缶", "ruby": "やかん", "bold": False},
                {"text": "だ。その後猫にもだいぶ逢ったがこんな", "ruby": "", "bold": False},
                {"text": "片輪", "ruby": "かたわ", "bold": False},
                {"text": "には一度も出会わした事がない。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "のみならず顔の真中があまりに突起している。そうしてその穴の中から時々ぷうぷうと", "ruby": "", "bold": False},
                {"text": "煙", "ruby": "けむり", "bold": False},
                {"text": "を吹く。どうも", "ruby": "", "bold": False},
                {"text": "咽", "ruby": "む", "bold": False},
                {"text": "せぽくて実に弱った。これが人間の飲む", "ruby": "", "bold": False},
                {"text": "煙草", "ruby": "たばこ", "bold": False},
                {"text": "というものである事はようやくこの頃知った。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "この書生の掌の", "ruby": "", "bold": False},
                {"text": "裏", "ruby": "うち", "bold": False},
                {"text": "でしばらくはよい心持に坐っておったが、しばらくすると非常な速力で運転し始めた。", "ruby": "", "bold": False},
            ],
        },
    ]


def _resolve_preview_source_paths(target_path: PathLike | None) -> list[Path]:
    target_raw = str(target_path or '').strip()
    if not target_raw:
        return []
    path = Path(target_raw)
    if not path.exists():
        return []
    if path.is_file():
        suffix = path.suffix.lower()
        return [path] if suffix in SUPPORTED_INPUT_SUFFIXES or suffix in IMG_EXTS else []
    if not path.is_dir():
        return []

    conversion_sources = [
        p for p in iter_conversion_targets(path)
        if p.suffix.lower() in SUPPORTED_INPUT_SUFFIXES
    ]
    if conversion_sources:
        return conversion_sources

    image_sources = [
        p for p in path.rglob('*')
        if p.is_file() and p.suffix.lower() in IMG_EXTS and not should_skip_conversion_target(p)
    ]
    return sorted(image_sources, key=lambda p: _natural_sort_key(p.relative_to(path)))


def _resolve_preview_source_path(target_path: PathLike | None) -> Path | None:
    sources = _resolve_preview_source_paths(target_path)
    return sources[0] if sources else None


def _select_preview_blocks(blocks: Sequence[TextBlock] | None, *, max_blocks: int = 6) -> TextBlocks:
    selected: TextBlocks = []
    nonblank_count = 0
    for block in blocks or []:
        kind = str(block.get('kind', '') or '') if isinstance(block, dict) else ''
        if kind == 'blank':
            if selected:
                selected.append(block)
            continue
        runs = block.get('runs', []) if isinstance(block, dict) else []
        if not any(str(run.get('text', '') or '') for run in runs):
            continue
        selected.append(block)
        nonblank_count += 1
        if nonblank_count >= max_blocks:
            break
    return selected or _build_default_preview_blocks()


def _preview_fit_image(src_img: Image.Image, args: ConversionArgs) -> Image.Image:
    return _prepare_canvas_image(src_img, args.width, args.height)


def _preview_source_requires_font(preview_source: Path | None) -> bool:
    if preview_source is None:
        return True
    suffix = str(getattr(preview_source, 'suffix', '') or '').lower()
    if suffix in IMG_EXTS or suffix in {'.zip', '.cbz', '.cbr', '.rar'}:
        return False
    return True


def _preview_target_requires_font(target_path: PathLike | None, *, preview_sources: Sequence[Path] | None = None) -> bool:
    sources = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
    if not sources:
        return True
    return any(_preview_source_requires_font(source) for source in sources)


class _PreviewPageLimitReached(RuntimeError):
    """Raised internally to stop preview rendering once the requested page limit is reached."""


def _render_preview_pages_from_target(target_path: PathLike | None, font_value: str | Path, preview_args: ConversionArgs, *, max_pages: int = PREVIEW_PAGE_LIMIT, progress_cb: ProgressCallback | None = None, preview_sources: Sequence[Path] | None = None) -> tuple[list[Image.Image], bool]:
    _refresh_core_globals()
    resolved_preview_sources = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
    preview_source = resolved_preview_sources[0] if resolved_preview_sources else None
    blank_page = Image.new('L', (preview_args.width, preview_args.height), 255)
    max_pages = max(1, int(max_pages or PREVIEW_PAGE_LIMIT))
    truncated = False

    if len(resolved_preview_sources) > 1:
        page_images: list[Image.Image] = []
        total_sources = len(resolved_preview_sources)
        for source_index, source_path in enumerate(resolved_preview_sources, 1):
            if len(page_images) >= max_pages:
                truncated = True
                break
            remaining_pages = max_pages - len(page_images)
            _emit_progress(progress_cb, source_index - 1, total_sources, f'フォルダ内のプレビュー対象を処理中… ({source_index - 1}/{total_sources} 件)')
            source_pages, source_truncated = _render_preview_pages_from_target(
                source_path,
                font_value,
                preview_args,
                max_pages=remaining_pages,
                progress_cb=progress_cb,
            )
            for page_image in source_pages:
                if len(page_images) >= max_pages:
                    truncated = True
                    break
                page_images.append(page_image)
            if source_truncated:
                truncated = True
                break
        return (page_images if page_images else [blank_page.copy()]), truncated

    if preview_source is None:
        target_raw = str(target_path or '').strip()
        if target_raw:
            target_candidate = Path(target_raw)
            if not target_candidate.exists():
                raise RuntimeError('プレビュー対象が見つかりません。対応ファイルが含まれているか確認してください。')
        render_state = {}
        page_images = _render_text_blocks_to_images(
            _build_default_preview_blocks(),
            font_value,
            preview_args,
            progress_cb=progress_cb,
            max_output_pages=max_pages,
            render_state=render_state,
        )
        return (page_images[:max_pages] if page_images else [blank_page.copy()]), bool(render_state.get('page_limit_reached', False))

    suffix = preview_source.suffix.lower()
    if suffix in IMG_EXTS:
        with Image.open(preview_source) as src_img:
            return [_preview_fit_image(src_img, preview_args)], False

    if suffix in ('.txt',):
        document = load_text_input_document(preview_source, parser='plain')
        render_state = {}
        page_images = _render_text_blocks_to_images(
            document.blocks,
            font_value,
            preview_args,
            progress_cb=progress_cb,
            max_output_pages=max_pages,
            render_state=render_state,
        )
        return (page_images if page_images else [blank_page.copy()]), bool(render_state.get('page_limit_reached', False))

    if suffix in MARKDOWN_INPUT_SUFFIXES:
        document = load_text_input_document(preview_source, parser='markdown')
        render_state = {}
        page_images = _render_text_blocks_to_images(
            document.blocks,
            font_value,
            preview_args,
            progress_cb=progress_cb,
            max_output_pages=max_pages,
            render_state=render_state,
        )
        return (page_images if page_images else [blank_page.copy()]), bool(render_state.get('page_limit_reached', False))

    if suffix == '.epub':
        epub_doc = load_epub_input_document(preview_source)
        font = load_truetype_font(font_value, preview_args.font_size)
        ruby_font = load_truetype_font(font_value, preview_args.ruby_size)
        page_images = []
        total_docs = max(1, len(epub_doc.docs))

        def _collect_page(entry: PageEntry) -> None:
            nonlocal truncated
            page_image = entry.get('image') if isinstance(entry, dict) else None
            if page_image is None:
                return
            if len(page_images) >= max_pages:
                truncated = True
                raise _PreviewPageLimitReached()
            page_images.append(page_image)
            _emit_progress(progress_cb, len(page_images), max_pages, f'プレビューページを作成中… ({len(page_images)}/{max_pages} ページ)')
            if len(page_images) >= max_pages:
                truncated = True
                raise _PreviewPageLimitReached()

        try:
            for doc_index, item in enumerate(epub_doc.docs, 1):
                if len(page_images) >= max_pages:
                    truncated = True
                    break
                remaining_pages = max_pages - len(page_images)
                _emit_progress(progress_cb, doc_index - 1, total_docs, f'EPUB章を組版中… ({max(0, doc_index - 1)}/{total_docs} 章)')
                chapter_pages = _render_epub_chapter_pages_from_html(
                    item.get_content(),
                    getattr(item, 'file_name', ''),
                    preview_args,
                    font,
                    ruby_font,
                    epub_doc.bold_rules,
                    epub_doc.image_map,
                    epub_doc.image_basename_map,
                    epub_doc.css_rules,
                    primary_font_value=str(font_value),
                    page_created_cb=_collect_page,
                    store_page_entries=False,
                    max_output_pages=remaining_pages,
                )
                for entry in chapter_pages:
                    _collect_page(entry)
                if len(page_images) >= max_pages:
                    truncated = True
                    break
            if len(page_images) < max_pages:
                truncated = False
        except _PreviewPageLimitReached:
            truncated = True
        return (page_images if page_images else [blank_page.copy()]), truncated

    if suffix in ('.zip', '.cbz'):
        try:
            image_infos, _traversal_skipped = _safe_zip_archive_image_infos(preview_source)
            page_images = []
            with zipfile.ZipFile(preview_source) as zf:
                for _pure, info in image_infos[:max_pages]:
                    with zf.open(info) as member_fp:
                        with Image.open(member_fp) as src_img:
                            page_images.append(_preview_fit_image(src_img, preview_args))
            truncated = len(image_infos) > max_pages
            return (page_images if page_images else [blank_page.copy()]), truncated
        except (zipfile.BadZipFile, OSError):
            pass

    if suffix in ('.zip', '.cbz', '.cbr', '.rar'):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_document = _load_archive_input_document_compat(preview_source, tmpdir)
            page_images = []
            for image_path in archive_document.image_files[:max_pages]:
                with Image.open(image_path) as src_img:
                    page_images.append(_preview_fit_image(src_img, preview_args))
            truncated = len(archive_document.image_files) > max_pages
            return (page_images if page_images else [blank_page.copy()]), truncated

    page_images = _render_text_blocks_to_images(
        _build_default_preview_blocks(),
        font_value,
        preview_args,
        progress_cb=progress_cb,
        max_output_pages=max_pages,
    )
    return (page_images[:max_pages] if page_images else [blank_page.copy()]), len(page_images) > max_pages


def _render_preview_page_from_target(target_path: PathLike | None, font_value: str | Path, preview_args: ConversionArgs) -> Image.Image:
    _refresh_core_globals()
    page_images, _truncated = _render_preview_pages_from_target(target_path, font_value, preview_args, max_pages=1)
    return page_images[0] if page_images else Image.new('L', (preview_args.width, preview_args.height), 255)


def _apply_preview_postprocess(image: Image.Image, *, mode: object, output_format: str, dither: bool, threshold: int, width: int, height: int, night_mode: bool) -> Image.Image:
    if mode != 'image' and output_format == 'xtch':
        result = _apply_xtch_filter_prepared(image, dither, threshold, width, height)
    elif mode != 'image':
        result = _apply_xtc_filter_prepared(image, dither, threshold)
    else:
        result = image
    if night_mode:
        result = _invert_grayscale_image(result)
    return result


def _encode_preview_png_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    normalized = image if image.mode in {'1', 'L', 'LA', 'RGB', 'RGBA'} else image.convert('RGBA' if 'A' in image.mode else 'RGB')
    normalized.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def _mapping_get_int(mapping: Mapping[str, object], key: str, default: int) -> int:
    """Return an integer value from a loosely typed mapping."""
    value = mapping.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


def _mapping_get_bool(mapping: Mapping[str, object], key: str, default: bool) -> bool:
    """Return a boolean value from a loosely typed mapping."""
    value = mapping.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'off', ''}:
            return False
    return bool(default)


_PREVIEW_BUNDLE_CACHE: OrderedDict[tuple[object, ...], dict[str, object]] = OrderedDict()


def _preview_path_signature(path: Path) -> tuple[str, int, int]:
    try:
        stat = path.stat()
        mtime_ns = getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1_000_000_000))
        return (str(path.resolve()), int(stat.st_size), int(mtime_ns))
    except OSError:
        return (str(path), -1, -1)


def _preview_bundle_cache_key(args: Mapping[str, object], *, preview_sources: Sequence[Path] | None = None) -> tuple[object, ...]:
    mode = str(args.get('mode', 'text') or 'text')
    width = _mapping_get_int(args, 'width', DEF_WIDTH)
    height = _mapping_get_int(args, 'height', DEF_HEIGHT)
    dither = _mapping_get_bool(args, 'dither', False)
    threshold = _mapping_get_int(args, 'threshold', 128)
    night_mode = _mapping_get_bool(args, 'night_mode', False)
    output_format = _normalize_output_format(args.get('output_format', 'xtc'))
    max_pages = max(1, _mapping_get_int(args, 'max_pages', PREVIEW_PAGE_LIMIT))

    common = (mode, width, height, dither, threshold, night_mode, output_format, max_pages)
    if mode == 'image':
        file_b64 = args.get('file_b64')
        digest = hashlib.sha1(file_b64.encode('utf-8')).hexdigest() if isinstance(file_b64, str) and file_b64 else '<default-gradient>'
        return common + (digest,)

    target_path = str(args.get('target_path', '') or '').strip()
    font_part = (
        str(args.get('font_file', '') or ''),
        _mapping_get_int(args, 'font_size', 26),
        _mapping_get_int(args, 'ruby_size', 12),
        _mapping_get_int(args, 'line_spacing', 44),
        _mapping_get_int(args, 'margin_t', 12),
        _mapping_get_int(args, 'margin_b', 14),
        _mapping_get_int(args, 'margin_r', 12),
        _mapping_get_int(args, 'margin_l', 12),
        _normalize_kinsoku_mode(args.get('kinsoku_mode', 'standard')),
        _glyph_position_mode(args.get('punctuation_position_mode', 'standard')),
        _glyph_position_mode(args.get('ichi_position_mode', 'standard')),
        _glyph_position_mode(args.get('lower_closing_bracket_position_mode', 'standard')),
    )
    source_paths = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
    source_signature = tuple(_preview_path_signature(path) for path in source_paths[:max_pages])
    return common + font_part + (target_path, len(source_paths), source_signature)


def clear_preview_bundle_cache() -> None:
    _refresh_core_globals()
    _PREVIEW_BUNDLE_CACHE.clear()


def _iter_preview_bundle_pages(value: object) -> Iterator[object]:
    if value is None:
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, (bytes, bytearray)):
        try:
            yield bytes(value).decode('ascii')
        except Exception:
            yield bytes(value).decode('utf-8', errors='ignore')
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_preview_bundle_pages(nested)
        return
    try:
        iterator = iter(value)  # type: ignore[arg-type]
    except Exception:
        return
    for item in iterator:
        yield from _iter_preview_bundle_pages(item)



def _normalize_preview_bundle_pages(value: object) -> list[str]:
    pages: list[str] = []
    for item in _iter_preview_bundle_pages(value):
        if isinstance(item, str):
            text = item.strip()
            if text:
                pages.append(text)
    return pages



def _get_cached_preview_bundle(cache_key: tuple[object, ...]) -> dict[str, object] | None:
    _refresh_core_globals()
    cached = _PREVIEW_BUNDLE_CACHE.get(cache_key)
    if cached is None:
        return None
    _PREVIEW_BUNDLE_CACHE.move_to_end(cache_key)
    pages = _normalize_preview_bundle_pages(cached.get('pages'))
    page_count = _mapping_get_int(cached, 'page_count', len(pages))
    if page_count <= 0:
        page_count = len(pages)
    source_count = _mapping_get_int(cached, 'source_count', 0)
    if source_count < 0:
        source_count = 0
    return {
        'pages': pages,
        'page_count': page_count,
        'truncated': _mapping_get_bool(cached, 'truncated', False),
        'source_count': source_count,
    }



def _store_cached_preview_bundle(cache_key: tuple[object, ...], bundle: Mapping[str, object]) -> None:
    _refresh_core_globals()
    pages = _normalize_preview_bundle_pages(bundle.get('pages'))
    page_count = _mapping_get_int(bundle, 'page_count', len(pages))
    if page_count <= 0:
        page_count = len(pages)
    source_count = _mapping_get_int(bundle, 'source_count', 0)
    if source_count < 0:
        source_count = 0
    _PREVIEW_BUNDLE_CACHE[cache_key] = {
        'pages': pages,
        'page_count': page_count,
        'truncated': _mapping_get_bool(bundle, 'truncated', False),
        'source_count': source_count,
    }
    _PREVIEW_BUNDLE_CACHE.move_to_end(cache_key)
    while len(_PREVIEW_BUNDLE_CACHE) > PREVIEW_BUNDLE_CACHE_MAX:
        _PREVIEW_BUNDLE_CACHE.popitem(last=False)


def generate_preview_bundle(args: Mapping[str, object], progress_cb: ProgressCallback | None = None) -> dict[str, object]:
    """Render preview pages and return base64-encoded PNGs plus pagination info."""
    _refresh_core_globals()
    try:
        _args: dict[str, object] = dict(args)
        mode = _args.get('mode', 'text')
        preview_sources = None if mode == 'image' else _resolve_preview_source_paths(_args.get('target_path', ''))
        cache_key = _preview_bundle_cache_key(_args, preview_sources=preview_sources)
        cached_bundle = _get_cached_preview_bundle(cache_key)
        if cached_bundle is not None:
            cached_pages = max(1, _mapping_get_int(cached_bundle, 'page_count', len(cached_bundle.get('pages', []))))
            _emit_progress(progress_cb, cached_pages, cached_pages, f'キャッシュ済みのプレビューを再利用しています… ({cached_pages}/{cached_pages} ページ)')
            return cached_bundle

        w = _mapping_get_int(_args, 'width', DEF_WIDTH)
        h = _mapping_get_int(_args, 'height', DEF_HEIGHT)
        dither = _mapping_get_bool(_args, 'dither', False)
        threshold = _mapping_get_int(_args, 'threshold', 128)
        mode = _args.get('mode', 'text')
        night_mode = _mapping_get_bool(_args, 'night_mode', False)
        kinsoku_mode = _normalize_kinsoku_mode(_args.get('kinsoku_mode', 'standard'))
        output_format = _normalize_output_format(_args.get('output_format', 'xtc'))
        max_pages = max(1, _mapping_get_int(_args, 'max_pages', PREVIEW_PAGE_LIMIT))

        if mode == 'image':
            _emit_progress(progress_cb, 0, 3, 'プレビュー画像を準備しています…')
            file_b64 = _args.get('file_b64')
            src_img: Image.Image
            if file_b64:
                if not isinstance(file_b64, str):
                    raise ValueError('画像プレビュー用データURIが不正です。')
                if "," not in file_b64:
                    raise ValueError('画像プレビュー用データURIが不正です。')
                _header, encoded = file_b64.split(",", 1)
                src_img = Image.open(io.BytesIO(base64.b64decode(encoded)))
            else:
                src_img = Image.new('L', (w, h), 255)
                draw = create_image_draw(src_img)
                for i in range(16):
                    draw.rectangle([0, i * (h // 16), w, (i + 1) * (h // 16)], fill=int(255 * (i / 15)))
            _emit_progress(progress_cb, 1, 3, 'プレビュー画像を変換しています…')
            page_images = [apply_xtch_filter(src_img, dither, threshold, w, h) if output_format == 'xtch' else apply_xtc_filter(src_img, dither, threshold, w, h)]
            truncated = False
            preview_source_count = 1
        else:
            font_value = _args.get('font_file', "")
            target_path = _args.get('target_path', '')
            preview_sources = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
            preview_source_count = len(preview_sources)
            preview_args = ConversionArgs(
                width=w,
                height=h,
                font_size=_mapping_get_int(_args, 'font_size', 26),
                ruby_size=_mapping_get_int(_args, 'ruby_size', 12),
                line_spacing=_mapping_get_int(_args, 'line_spacing', 44),
                margin_t=_mapping_get_int(_args, 'margin_t', 12),
                margin_b=_mapping_get_int(_args, 'margin_b', 14),
                margin_r=_mapping_get_int(_args, 'margin_r', 12),
                margin_l=_mapping_get_int(_args, 'margin_l', 12),
                dither=dither,
                night_mode=night_mode,
                threshold=threshold,
                kinsoku_mode=kinsoku_mode,
                punctuation_position_mode=_glyph_position_mode(_args.get('punctuation_position_mode', 'standard')),
                ichi_position_mode=_glyph_position_mode(_args.get('ichi_position_mode', 'standard')),
                lower_closing_bracket_position_mode=_glyph_position_mode(_args.get('lower_closing_bracket_position_mode', 'standard')),
                output_format=output_format,
            )
            if _preview_target_requires_font(target_path, preview_sources=preview_sources):
                require_font_path(font_value)
            page_images, truncated = _render_preview_pages_from_target(target_path, font_value, preview_args, max_pages=max_pages, progress_cb=progress_cb, preview_sources=preview_sources)

        total_pages = max(1, len(page_images))
        encoded_pages = []
        for idx, image in enumerate(page_images, 1):
            _emit_progress(progress_cb, idx - 1, total_pages, f'プレビュー画像を整えています… ({idx - 1}/{total_pages} ページ)')
            processed = _apply_preview_postprocess(
                image,
                mode=mode,
                output_format=output_format,
                dither=dither,
                threshold=threshold,
                width=w,
                height=h,
                night_mode=night_mode,
            )
            _emit_progress(progress_cb, idx, total_pages, f'プレビューを出力しています… ({idx}/{total_pages} ページ)')
            encoded_pages.append(_encode_preview_png_base64(processed))
        bundle = {'pages': encoded_pages, 'page_count': len(encoded_pages), 'truncated': bool(truncated), 'source_count': int(preview_source_count) if mode != 'image' else 1}
        _store_cached_preview_bundle(cache_key, bundle)
        return bundle

    except Exception as e:
        LOGGER.exception('Preview Error: %s', e)
        raise RuntimeError(f"プレビュー生成に失敗しました: {e}") from e


def generate_preview_base64(args: Mapping[str, object]) -> str:
    """Render the first preview page and return it as a base64 PNG string.

    Args:
        args: Preview and rendering options supplied by the GUI layer.

    Returns:
        Base64-encoded PNG string for the first preview page.
    """
    _refresh_core_globals()
    bundle = generate_preview_bundle(args)
    pages = bundle.get('pages', []) if isinstance(bundle, dict) else []
    if not pages:
        blank = Image.new('L', (_mapping_get_int(dict(args), 'width', DEF_WIDTH), _mapping_get_int(dict(args), 'height', DEF_HEIGHT)), 255)
        return _encode_preview_png_base64(blank)
    first = pages[0]
    if not isinstance(first, str):
        raise RuntimeError('プレビュー生成に失敗しました: 先頭ページの形式が不正です。')
    return first


# --- moved from tategakiXTC_gui_core.py lines 7068-9473 ---
def _has_renderable_text_blocks(blocks: Sequence[Mapping[str, Any]], should_cancel: Callable[[], bool] | None = None) -> bool:
    for block in blocks:
        _raise_if_cancelled(should_cancel)
        if block.get('kind') == 'blank':
            continue
        runs = block.get('runs', [])
        if any(run.get('text', '') for run in runs):
            return True
    return False


@lru_cache(maxsize=2048)
def _split_ruby_text_segments_cached(
    rt_text: str,
    segment_lengths: tuple[int, ...],
    segment_capacities: tuple[int | None, ...] | None = None,
) -> tuple[str, ...]:
    """ルビ文字列を複数セグメントへ按分する。"""
    if not rt_text:
        return tuple('' for _ in segment_lengths)

    total_base = sum(segment_lengths) or 1
    total_ruby = len(rt_text)
    target_counts = []
    for seg_len in segment_lengths:
        target_counts.append(round(total_ruby * seg_len / total_base))

    if total_ruby >= len(segment_lengths):
        target_counts = [max(1, c) for c in target_counts]

    diff = total_ruby - sum(target_counts)
    if diff > 0:
        order = sorted(range(len(segment_lengths)), key=lambda i: (-segment_lengths[i], i))
        j = 0
        while diff > 0 and order:
            target_counts[order[j % len(order)]] += 1
            diff -= 1
            j += 1
    elif diff < 0:
        order = sorted(range(len(segment_lengths)), key=lambda i: (segment_lengths[i], -i))
        j = 0
        while diff < 0 and order:
            target_idx = order[j % len(order)]
            min_allowed = 1 if total_ruby >= len(segment_lengths) else 0
            if target_counts[target_idx] > min_allowed:
                target_counts[target_idx] -= 1
                diff += 1
            j += 1
            if j > len(order) * 4 and diff < 0:
                break

    if segment_capacities:
        target_counts = [max(0, int(c)) for c in target_counts]
        for j, cap in enumerate(segment_capacities):
            if cap is not None:
                target_counts[j] = min(target_counts[j], max(0, int(cap)))

        overflow = max(0, total_ruby - sum(target_counts))
        if overflow > 0:
            expandable = [
                j for j, cap in enumerate(segment_capacities)
                if cap is None or target_counts[j] < max(0, int(cap))
            ]
            order = sorted(expandable, key=lambda j: (-segment_lengths[j], j))
            j = 0
            while overflow > 0 and order:
                target_idx = order[j % len(order)]
                cap = segment_capacities[target_idx]
                if cap is None or target_counts[target_idx] < max(0, int(cap)):
                    target_counts[target_idx] += 1
                    overflow -= 1
                j += 1
                if j > len(order) * 4 and overflow > 0:
                    break

        if overflow > 0:
            order = sorted(range(len(segment_lengths)), key=lambda j: (-segment_lengths[j], j))
            j = 0
            while overflow > 0 and order:
                target_counts[order[j % len(order)]] += 1
                overflow -= 1
                j += 1
                if j > len(order) * 4 and overflow > 0:
                    break

    parts = []
    pos = 0
    for count in target_counts:
        parts.append(rt_text[pos:pos + count])
        pos += count
    if pos < total_ruby:
        if parts:
            parts[-1] += rt_text[pos:]
        else:
            parts = [rt_text[pos:]]
    while len(parts) < len(segment_lengths):
        parts.append('')
    return tuple(parts)


def _split_ruby_text_segments(rt_text: str, segment_lengths: Sequence[int], segment_capacities: Sequence[int | None] | None = None) -> list[str]:
    _refresh_core_globals()
    segment_lengths_tuple = tuple(int(v) for v in segment_lengths)
    segment_capacities_tuple = None if segment_capacities is None else tuple(None if cap is None else int(cap) for cap in segment_capacities)
    return list(_split_ruby_text_segments_cached(str(rt_text or ''), segment_lengths_tuple, segment_capacities_tuple))


def _append_ruby_overlay_group(groups: list[RubyOverlayGroup], page_index: int, x_pos: int, y_pos: int, base_len: int) -> None:
    base_len = max(1, int(base_len or 1))
    page_index = int(page_index)
    x_pos = int(x_pos)
    y_pos = int(y_pos)
    if groups:
        current = groups[-1]
        # Ruby groups may span page boundaries.  Normal continuation within the
        # same vertical column advances downward, while a page/column reset moves
        # Y back to the top margin.  Do not merge a backward Y jump into the
        # previous compact group; that would create an inverted start/end range
        # and split the ruby text against the wrong page-local capacity.
        if (
            current['page_index'] == page_index
            and current['x'] == x_pos
            and y_pos >= int(current['end_y'])
        ):
            current['end_y'] = y_pos
            current['base_len'] += base_len
            return
    groups.append({
        'page_index': page_index,
        'x': x_pos,
        'start_y': y_pos,
        'end_y': y_pos,
        'base_len': base_len,
    })


def _build_ruby_overlay_groups(segment_infos: Sequence[Mapping[str, Any]]) -> list[RubyOverlayGroup]:
    groups: list[RubyOverlayGroup] = []
    for info in segment_infos:
        _append_ruby_overlay_group(
            groups,
            int(info['page_index']),
            int(info['x']),
            int(info['y']),
            int(info.get('base_len', 1) or 1),
        )
    return groups


def _append_overlay_cell(cells: list[OverlayCell], page_index: int, x_pos: int, y_pos: int, cell_text: str) -> None:
    cells.append((int(page_index), int(x_pos), int(y_pos), str(cell_text or '')))


def _effective_ruby_overlay_bottom_margin(args: ConversionArgs) -> int:
    """Return the bottom guard shared by base text and ruby overlays.

    Ruby is drawn after the base glyph run has already reserved the vertical
    layout bottom guard.  If overlay placement uses only the raw bottom margin,
    long or bottom-adjacent ruby can drift below the last legal base-text slot
    and look clipped or too close to the page edge.
    """
    return _effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)


def _ruby_group_capacity_for_args(group: Mapping[str, Any], segment_index: int, total_segments: int, args: ConversionArgs) -> int:
    """セグメントごとのルビ配置可能数を算出する。"""
    slot_h = max(1, args.ruby_size + 2)
    page_top = args.margin_t
    page_bottom = args.height - _effective_ruby_overlay_bottom_margin(args)
    chars = group.get('chars')
    if chars:
        start_y = int(chars[0]['y'])
        end_y = int(chars[-1]['y']) + args.font_size
    else:
        start_y = int(group.get('start_y', page_top))
        end_y = int(group.get('end_y', start_y)) + args.font_size

    if total_segments == 1:
        usable_top = page_top
        usable_bottom = page_bottom
    elif segment_index == 0:
        usable_top = page_top
        usable_bottom = min(page_bottom, end_y)
    elif segment_index == total_segments - 1:
        usable_top = max(page_top, start_y)
        usable_bottom = page_bottom
    else:
        usable_top = page_top
        usable_bottom = page_bottom

    usable_height = max(0, usable_bottom - usable_top)
    if usable_height <= 0:
        return 0
    return ((usable_height - 1) // slot_h) + 1


def _clamp_margin_value(value: object, limit: int) -> int:
    try:
        margin = int(value or 0)
    except (TypeError, ValueError):
        margin = 0
    return max(0, min(max(0, int(limit or 0)), margin))


def _hanging_punctuation_bottom_clip_allowance(args: ConversionArgs | None) -> int:
    """Compatibility helper for older tests/imports.

    split118 no longer widens the global bottom clip band.  Hanging punctuation
    pixels are mirrored to a scoped overlay and restored only within the bottom
    margin, so ordinary text remains clipped at the guide boundary.
    """
    return 0


def _bottom_margin_clip_start_for_text_page(height: int, args: ConversionArgs | None) -> int:
    """Return the original Y coordinate where bottom margin clipping begins.

    Hanging punctuation is restored separately from a dedicated overlay, so this
    start position must keep clipping ordinary text pixels at the guide boundary.
    """
    if args is None:
        return int(height or 0)
    height = max(0, int(height or 0))
    margin_b = _clamp_margin_value(getattr(args, 'margin_b', 0), height)
    if margin_b <= 0:
        return height
    return max(0, height - margin_b)


def _apply_text_page_margin_clip(image: Image.Image, args: ConversionArgs | None) -> Image.Image:
    """本文ページの四辺余白に残った描画画素を白でクリップする。

    縦書き本文はフォントによって実インクがセル外へ出る場合があるため、
    レイアウト段階の余白計算に加え、ページ確定直前に外側余白を白で
    戻す。右辺は本文セルの外側にルビ用スペースを持つため、消すのは
    指定された右余白そのものだけに限定し、ルビ予約領域は残す。
    """
    if image is None or args is None:
        return image
    width, height = image.size
    if width <= 0 or height <= 0:
        return image
    margin_t = _clamp_margin_value(getattr(args, 'margin_t', 0), height)
    margin_b = _clamp_margin_value(getattr(args, 'margin_b', 0), height)
    margin_r = _clamp_margin_value(getattr(args, 'margin_r', 0), width)
    margin_l = _clamp_margin_value(getattr(args, 'margin_l', 0), width)
    if not (margin_t or margin_b or margin_r or margin_l):
        return image
    draw = ImageDraw.Draw(image)
    fill_value = 255
    if margin_t:
        draw.rectangle((0, 0, width - 1, margin_t - 1), fill=fill_value)
    if margin_b:
        y0 = _bottom_margin_clip_start_for_text_page(height, args)
        if y0 < height:
            draw.rectangle((0, y0, width - 1, height - 1), fill=fill_value)
            _restore_hanging_punctuation_bottom_margin(image, args)
    if margin_l:
        draw.rectangle((0, 0, margin_l - 1, height - 1), fill=fill_value)
    if margin_r:
        x0 = max(0, width - margin_r)
        draw.rectangle((x0, 0, width - 1, height - 1), fill=fill_value)
    return image


def _page_label_allows_text_margin_clip(label: object) -> bool:
    label_text = str(label or '')
    if '挿絵' in label_text or '画像' in label_text:
        return False
    return True


def _apply_page_entry_margin_clip(entry: PageEntry) -> PageEntry:
    if not isinstance(entry, dict):
        return entry
    if not _page_label_allows_text_margin_clip(entry.get('label', '')):
        return entry
    image = entry.get('image')
    args = entry.get('page_args')
    if image is not None and args is not None:
        _apply_text_page_margin_clip(cast(Image.Image, image), cast(ConversionArgs, args))
    return entry

class _VerticalPageRenderer:
    def __init__(self: _VerticalPageRenderer, args: ConversionArgs, font: Any, ruby_font: Any, *, should_cancel: CancelCallback | None = None, page_created_cb: PageCreatedCallback | None = None,
                 store_page_entries: bool = True, max_buffered_pages: int | None = None,
                 default_page_args: ConversionArgs | None = None, default_page_label: str = '本文ページ', emphasis_font_value: str | None = None,
                 code_font: Any | None = None, code_font_loader: Callable[[], Any] | None = None) -> None:
        self.args = args
        self.font = font
        self.ruby_font = ruby_font
        self.code_font = code_font
        self._code_font_loader = code_font_loader
        self.should_cancel = should_cancel
        self.page_created_cb = page_created_cb
        self.store_page_entries = bool(store_page_entries)
        self.max_buffered_pages = max(1, int(max_buffered_pages)) if max_buffered_pages else None
        self.default_page_args = default_page_args or args
        self.default_page_label = default_page_label
        self.emphasis_font_value = emphasis_font_value
        self.page_entries: PageEntries = []
        self._page_draw_cache: dict[int, ImageDraw.ImageDraw] = {}
        self._emphasis_font_cache_key: tuple[object, ...] | None = None
        self._emphasis_font_cache: Any | None = None
        self._emphasis_metrics_cache: dict[tuple[str, bool], tuple[int, int, int, int]] = {}
        self.has_started_document = False
        self._pending_paragraph_indent = False
        self._new_blank_page()

    def _new_blank_page(self: _VerticalPageRenderer) -> None:
        self.img = Image.new('L', (self.args.width, self.args.height), 255)
        self.draw = _apply_draw_glyph_position_modes(create_image_draw(self.img), self.args)
        self._page_draw_cache.clear()
        self.curr_x = self.args.width - self.args.font_size - (self.args.ruby_size + 4) - self.args.margin_r
        self.curr_y = self.args.margin_t
        self.has_drawn_on_page = False

    def add_page(self: _VerticalPageRenderer, image: Image.Image, *, label: str | None = None, page_args: ConversionArgs | None = None, copy_image: bool = True) -> PageEntry:
        stored_image = image.copy() if copy_image else image
        entry = _make_page_entry(
            stored_image,
            page_args=page_args or self.default_page_args,
            label=label or self.default_page_label,
        )
        # Ruby overlays are drawn after the base run has been laid out. When a
        # ruby run crosses a page boundary, earlier page images must remain
        # mutable until ``draw_split_ruby_groups`` has placed each ruby segment
        # on the correct page. Therefore page entries are retained here and
        # drained via ``pop_page_entries()`` after an overlay-safe boundary.
        self.page_entries.append(entry)
        if self.max_buffered_pages is not None and len(self.page_entries) >= self.max_buffered_pages:
            raise _PreviewPageLimitReached()
        return entry

    def flush_current_page(self: _VerticalPageRenderer, *, label: str | None = None, page_args: ConversionArgs | None = None) -> None:
        if self.has_drawn_on_page:
            self.add_page(self.img, label=label, page_args=page_args, copy_image=False)
        self._new_blank_page()

    @property
    def has_pending_output(self: _VerticalPageRenderer) -> bool:
        return bool(self.has_drawn_on_page or self.page_entries)

    def add_full_page_image(self: _VerticalPageRenderer, image: Image.Image, *, label: str | None = None, page_args: ConversionArgs | None = None, copy_image: bool = True) -> PageEntry:
        """Append a full-page image entry and reset the current working page.

        This is used for EPUB illustration pages and other content that should occupy
        an entire output page instead of being drawn into the current text column.
        Any in-progress text page is flushed first so the full-page image is emitted as
        its own page entry. Afterward a fresh blank page is prepared for subsequent
        text rendering.

        Args:
            image: Source image to store as a page entry.
            label: Optional human-readable page label for diagnostics and previews.
            page_args: Optional per-page conversion arguments. When omitted, the
                renderer's default page args are used.
            copy_image: Whether to store a copy of ``image`` in the page entry.

        Returns:
            The page entry dictionary that was appended to the renderer output.
        """
        if self.has_drawn_on_page:
            self.flush_current_page()
        entry = self.add_page(image, label=label, page_args=page_args, copy_image=copy_image)
        self._new_blank_page()
        return entry

    def set_pending_paragraph_indent(self: _VerticalPageRenderer, enabled: bool = True) -> None:
        self._pending_paragraph_indent = bool(enabled)

    def clear_pending_paragraph_indent(self: _VerticalPageRenderer) -> None:
        self._pending_paragraph_indent = False

    @property
    def has_pending_paragraph_indent(self: _VerticalPageRenderer) -> bool:
        return bool(self._pending_paragraph_indent)

    def apply_pending_paragraph_indent(self: _VerticalPageRenderer, indent_chars: int = 0) -> bool:
        """Apply a deferred paragraph indent if one is pending.

        EPUB rendering can defer indent insertion until the first actual text run is
        encountered after a ``<br>`` or paragraph boundary. This method resolves that
        deferred state, inserts the requested indent into the current column, and then
        clears the pending flag.

        Args:
            indent_chars: Preferred indent width in character units. When a pending
                paragraph indent exists, at least one character of indent is enforced.

        Returns:
            ``True`` when an indent was inserted, otherwise ``False``.
        """
        if self._pending_paragraph_indent:
            indent_chars = max(int(indent_chars or 0), 1)
        indent_chars = max(0, int(indent_chars or 0))
        if indent_chars <= 0:
            self._pending_paragraph_indent = False
            return False
        self.insert_paragraph_indent(indent_chars, continuation_indent_chars=indent_chars)
        self._pending_paragraph_indent = False
        return True

    def pop_page_entries(self: _VerticalPageRenderer) -> PageEntries:
        entries = self.page_entries
        self.page_entries = []
        self._page_draw_cache.clear()
        for entry in entries:
            _apply_page_entry_margin_clip(entry)
        if self.page_created_cb is not None:
            for entry in entries:
                self.page_created_cb(entry)
        if not self.store_page_entries:
            return []
        return entries

    def set_page_buffer_limit(self: _VerticalPageRenderer, value: int | None) -> None:
        self.max_buffered_pages = max(1, int(value)) if value else None

    def _indent_step_height(self: _VerticalPageRenderer, indent_chars: int) -> int:
        return max(0, int(indent_chars or 0)) * (self.args.font_size + 2)

    def _advance_column_with_indent_step(self: _VerticalPageRenderer, indent_step_height: int = 0) -> None:
        """Move to the next column using a precomputed continuation indent.

        Args:
            indent_step_height: Continuation indent already converted from character
                units into pixels.
        """
        _raise_if_cancelled(self.should_cancel)
        self.curr_y = self.args.margin_t + max(0, int(indent_step_height or 0))
        self.curr_x -= self.args.line_spacing
        if self.curr_x < self.args.margin_l:
            self.flush_current_page()
            self.curr_y = self.args.margin_t + max(0, int(indent_step_height or 0))

    def advance_column(self: _VerticalPageRenderer, count: int = 1, indent_chars: int = 0) -> None:
        """Move rendering to the next vertical column one or more times.

        The current Y position is reset to the top margin plus any continuation indent.
        When the next column would move past the left margin, the current page is
        flushed and a fresh blank page is started automatically.

        Args:
            count: Number of columns to advance.
            indent_chars: Continuation indent, expressed in character units, to apply
                when the new column starts.
        """
        _raise_if_cancelled(self.should_cancel)
        indent_step_height = self._indent_step_height(indent_chars)
        for _ in range(max(0, count)):
            self._advance_column_with_indent_step(indent_step_height)

    def ensure_room(self: _VerticalPageRenderer, char_height: int | None = None, continuation_indent_chars: int = 0) -> None:
        """Ensure the current column has space for the next glyph or block.

        When the current Y position would exceed the bottom margin after placing a
        glyph of ``char_height``, the renderer advances to a new column using the
        provided continuation indent.

        Args:
            char_height: Height of the next element in pixels. Defaults to the body
                font size when omitted.
            continuation_indent_chars: Indent to apply if a column advance becomes
                necessary.
        """
        char_height = char_height or self.args.font_size
        effective_margin_b = _effective_vertical_layout_bottom_margin(self.args.margin_b, self.args.font_size)
        if self.curr_y > self.args.height - effective_margin_b - char_height:
            self._advance_column_with_indent_step(self._indent_step_height(continuation_indent_chars))

    def insert_paragraph_indent(self: _VerticalPageRenderer, indent_chars: int = 0, continuation_indent_chars: int | None = None) -> None:
        """Insert vertical space that represents a paragraph indent.

        The indent is implemented as a Y offset measured in whole character steps. If
        the resulting position would overflow the current column, the renderer advances
        to a new column and reapplies the continuation indent there.

        Args:
            indent_chars: Indent width in character units.
            continuation_indent_chars: Indent to apply after an automatic column break.
                When omitted, the same value as ``indent_chars`` is reused.
        """
        indent_chars = max(0, int(indent_chars or 0))
        if indent_chars <= 0:
            return
        if continuation_indent_chars is None:
            continuation_indent_chars = indent_chars
        continuation_indent_chars = max(0, int(continuation_indent_chars or 0))
        self.curr_y += self._indent_step_height(indent_chars)
        self.ensure_room(self.args.font_size, continuation_indent_chars=continuation_indent_chars)

    def get_page_image_draw(self: _VerticalPageRenderer, page_index: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        if page_index == len(self.page_entries):
            return self.img, self.draw
        target_img = self.page_entries[page_index]['image']
        target_draw = self._page_draw_cache.get(page_index)
        if target_draw is None:
            target_draw = _apply_draw_glyph_position_modes(create_image_draw(target_img), self.args)
            self._page_draw_cache[page_index] = target_draw
        return target_img, target_draw

    def _draw_text_run_plain(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *, wrap_indent_step: int = 0,
                             is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                draw_hang_pair(
                    draw_obj, tokens[idx + 1], (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_ruby_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *,
                                  ruby_overlay_groups: list[RubyOverlayGroup], wrap_indent_step: int = 0,
                                  is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_ruby_group = _append_ruby_overlay_group
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token) + len(next_token))
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_overlay_cells_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *,
                                          overlay_cells: list[OverlayCell], wrap_indent_step: int = 0,
                                          is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_overlay_cell = _append_overlay_cell
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token + next_token)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_overlay_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *,
                                    ruby_overlay_groups: list[RubyOverlayGroup] | None = None,
                                    overlay_cells: list[OverlayCell] | None = None, wrap_indent_step: int = 0,
                                    is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_ruby_group = _append_ruby_overlay_group if ruby_overlay_groups is not None else None
        append_overlay_cell = _append_overlay_cell if overlay_cells is not None else None
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                if append_ruby_group is not None:
                    append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token) + len(next_token))
                if append_overlay_cell is not None:
                    append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token + next_token)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            if append_ruby_group is not None:
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            if append_overlay_cell is not None:
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_segment_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                    segment_infos: list[SegmentInfo], wrap_indent_step: int = 0, is_bold: bool = False,
                                    is_italic: bool = False, needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                append_segment_info(current_page_index, curr_x, curr_y, len(token) + len(next_token), token + next_token)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_segment_and_ruby_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                             segment_infos: list[SegmentInfo], ruby_overlay_groups: list[RubyOverlayGroup],
                                             wrap_indent_step: int = 0, is_bold: bool = False, is_italic: bool = False,
                                             needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        append_ruby_group = _append_ruby_overlay_group
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                base_len = len(token) + len(next_token)
                cell_text = token + next_token
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, base_len)
                append_segment_info(current_page_index, curr_x, curr_y, base_len, cell_text)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_segment_and_overlay_cells_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                                      segment_infos: list[SegmentInfo], overlay_cells: list[OverlayCell],
                                                      wrap_indent_step: int = 0, is_bold: bool = False, is_italic: bool = False,
                                                      needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        append_overlay_cell = _append_overlay_cell
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                base_len = len(token) + len(next_token)
                cell_text = token + next_token
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, cell_text)
                append_segment_info(current_page_index, curr_x, curr_y, base_len, cell_text)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()


    def _draw_text_run_segment_and_overlay_mixed(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                                 segment_infos: list[SegmentInfo], ruby_overlay_groups: list[RubyOverlayGroup], overlay_cells: list[OverlayCell],
                                                 wrap_indent_step: int = 0, is_bold: bool = False, is_italic: bool = False,
                                                 needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        append_ruby_group = _append_ruby_overlay_group
        append_overlay_cell = _append_overlay_cell
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                base_len = len(token) + len(next_token)
                cell_text = token + next_token
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, base_len)
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, cell_text)
                append_segment_info(current_page_index, curr_x, curr_y, base_len, cell_text)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def draw_text_run(self: _VerticalPageRenderer, text: str, run_font: Any, *, wrap_indent_chars: int = 0, segment_infos: list[SegmentInfo] | None = None,
                      ruby_overlay_groups: list[RubyOverlayGroup] | None = None, overlay_cells: list[OverlayCell] | None = None,
                      is_bold: bool = False, is_italic: bool = False, segment_info_needs_base_len: bool = True,
                      segment_info_needs_cell_text: bool = True) -> None:
        """Draw a single text run into the current page or subsequent columns.

        This method performs glyph-level wrapping, records per-segment placement into
        ``segment_infos`` for later ruby or emphasis overlay, and honors bold/italic
        styling hints supplied by the caller.

        Args:
            text: Text content to draw.
            run_font: Font object selected for this run.
            wrap_indent_chars: Continuation indent applied after automatic column
                breaks while this run is being drawn.
            segment_infos: Optional list that receives placement metadata for each
                contiguous segment rendered from this run.
            ruby_overlay_groups: Optional compact ruby overlay groups updated while
                rendering this run. When supplied, ruby metadata can be captured
                without allocating per-cell ``base_len`` entries.
            overlay_cells: Optional compact overlay cell tuples updated while
                rendering this run. When supplied, emphasis and side-line metadata
                can be captured without allocating per-cell dictionaries.
            is_bold: Whether bold styling should be simulated for this run.
            is_italic: Whether italic styling should be simulated for this run.
            segment_info_needs_base_len: Whether captured segment metadata should
                include ``base_len`` for ruby overlay grouping.
            segment_info_needs_cell_text: Whether captured segment metadata should
                include ``cell_text`` for emphasis or side-line filtering.
        """
        if not text:
            return
        _refresh_core_globals()
        _raise_if_cancelled(self.should_cancel)
        wrap_indent_chars = max(0, int(wrap_indent_chars or 0))
        wrap_indent_step = self._indent_step_height(wrap_indent_chars)
        build_single_hints = _build_single_token_vertical_layout_hints
        tokenize_vertical_text = _tokenize_vertical_text_cached
        build_layout_hints = _build_vertical_layout_hints
        if len(text) == 1:
            tokens = (text,)
            layout_hints = build_single_hints(text)
        else:
            tokens = tokenize_vertical_text(text)
            layout_hints = build_layout_hints(tokens)
        capture_mask = (
            (4 if segment_infos is not None else 0)
            | (2 if ruby_overlay_groups is not None else 0)
            | (1 if overlay_cells is not None else 0)
        )
        if capture_mask == 0:
            self._draw_text_run_plain(
                tokens,
                layout_hints,
                run_font,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        if capture_mask == 2:
            self._draw_text_run_ruby_only(
                tokens,
                layout_hints,
                run_font,
                ruby_overlay_groups=ruby_overlay_groups,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        if capture_mask == 1:
            self._draw_text_run_overlay_cells_only(
                tokens,
                layout_hints,
                run_font,
                overlay_cells=overlay_cells,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        if capture_mask == 3:
            self._draw_text_run_overlay_only(
                tokens,
                layout_hints,
                run_font,
                ruby_overlay_groups=ruby_overlay_groups,
                overlay_cells=overlay_cells,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        needs_base_len = bool(segment_info_needs_base_len)
        needs_cell_text = bool(segment_info_needs_cell_text) or bool(capture_mask & 1)
        if capture_mask == 4:
            self._draw_text_run_segment_only(
                tokens,
                layout_hints,
                run_font,
                segment_infos=segment_infos,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
                needs_base_len=needs_base_len,
                needs_cell_text=needs_cell_text,
            )
            return
        if capture_mask == 6:
            self._draw_text_run_segment_and_ruby_only(
                tokens,
                layout_hints,
                run_font,
                segment_infos=segment_infos,
                ruby_overlay_groups=ruby_overlay_groups,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
                needs_base_len=needs_base_len,
                needs_cell_text=needs_cell_text,
            )
            return
        if capture_mask == 5:
            self._draw_text_run_segment_and_overlay_cells_only(
                tokens,
                layout_hints,
                run_font,
                segment_infos=segment_infos,
                overlay_cells=overlay_cells,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
                needs_base_len=needs_base_len,
                needs_cell_text=needs_cell_text,
            )
            return
        self._draw_text_run_segment_and_overlay_mixed(
            tokens,
            layout_hints,
            run_font,
            segment_infos=segment_infos,
            ruby_overlay_groups=ruby_overlay_groups,
            overlay_cells=overlay_cells,
            wrap_indent_step=wrap_indent_step,
            is_bold=is_bold,
            is_italic=is_italic,
            needs_base_len=needs_base_len,
            needs_cell_text=needs_cell_text,
        )
        return

    def _ruby_group_capacity(self: _VerticalPageRenderer, group: Mapping[str, Any], segment_index: int, total_segments: int) -> int:
        return _ruby_group_capacity_for_args(group, segment_index, total_segments, self.args)

    def _get_code_font(self: _VerticalPageRenderer, default_font: Any | None = None) -> Any:
        if self.code_font is not None:
            return self.code_font
        loader = self._code_font_loader
        if callable(loader):
            try:
                self.code_font = loader()
            except Exception:
                self.code_font = default_font or self.font
        else:
            self.code_font = default_font or self.font
        return self.code_font

    def _select_run_font(self: _VerticalPageRenderer, run: Mapping[str, Any] | None, default_font: Any | None = None) -> Any:
        base_font = default_font or self.font
        return self._get_code_font(base_font) if bool((run or {}).get('code', False)) else base_font

    def _collect_repeated_run_texts(self: _VerticalPageRenderer, runs: Sequence[Mapping[str, Any]] | None, *, min_len: int = 7, max_len: int = 256) -> set[str]:
        if not runs:
            return set()
        min_len = max(1, int(min_len or 1))
        max_len = max(min_len, int(max_len or min_len))
        repeated_counts: dict[str, int] = {}
        repeated_texts: set[str] = set()
        for run in runs:
            if not run:
                continue
            seg_text = str(run.get('text', '') or '')
            text_len = len(seg_text)
            if text_len < min_len or text_len > max_len:
                continue
            next_count = repeated_counts.get(seg_text, 0) + 1
            if next_count >= 2:
                repeated_texts.add(seg_text)
            repeated_counts[seg_text] = next_count
        return repeated_texts

    def draw_runs(self: _VerticalPageRenderer, runs: Sequence[Mapping[str, Any]] | None, *, default_font: Any | None = None, wrap_indent_chars: int = 0) -> None:
        """Draw a sequence of rich text runs and their overlays.

        Each run may contain formatting flags such as ``bold``, ``italic``, ``code``,
        ``ruby``, ``emphasis``, or ``side_line``. The method renders the base text run
        first and then applies ruby, emphasis marks, and side lines using the segment
        metadata captured during drawing.

        Args:
            runs: Sequence of run dictionaries, typically produced by text/Markdown or
                EPUB preprocessing.
            default_font: Base font to use for runs that do not request a code font.
            wrap_indent_chars: Continuation indent applied after automatic column
                breaks while any of the supplied runs are being drawn.
        """
        _refresh_core_globals()
        _raise_if_cancelled(self.should_cancel)
        base_font = default_font or self.font
        wrap_indent_chars = max(0, int(wrap_indent_chars or 0))
        wrap_indent_step = self._indent_step_height(wrap_indent_chars)
        get_code_font = self._get_code_font
        draw_text_run = self.draw_text_run
        draw_text_run_plain = self._draw_text_run_plain
        draw_text_run_ruby_only = self._draw_text_run_ruby_only
        draw_text_run_overlay_cells_only = self._draw_text_run_overlay_cells_only
        draw_text_run_overlay_only = self._draw_text_run_overlay_only
        build_single_hints = _build_single_token_vertical_layout_hints
        tokenize_vertical_text = _tokenize_vertical_text_cached
        build_layout_hints_cached = _build_vertical_layout_hints_cached
        draw_split_ruby_groups = self.draw_split_ruby_groups
        draw_emphasis_marks_cells = self.draw_emphasis_marks_cells
        draw_side_lines_cells = self.draw_side_lines_cells
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        code_font = None
        repeated_medium_texts = self._collect_repeated_run_texts(runs, min_len=7, max_len=256)
        local_run_layout_cache: dict[str, tuple[tuple[str, ...], VerticalLayoutHints]] = {}
        local_run_layout_cache_get = local_run_layout_cache.get
        local_run_layout_cache_set = local_run_layout_cache.__setitem__
        ruby_overlay_groups: list[RubyOverlayGroup]
        overlay_cells: list[OverlayCell]
        if repeated_medium_texts:
            for repeated_text in repeated_medium_texts:
                repeated_tokens = tokenize_vertical_text(repeated_text)
                local_run_layout_cache_set(repeated_text, (repeated_tokens, build_layout_hints_cached(repeated_tokens)))
        for run in runs or ():
            raise_if_cancelled(should_cancel)
            if not run:
                continue
            get_value = run.get
            seg_text = get_value('text', '')
            if not seg_text:
                continue
            ruby = get_value('ruby', '')
            emphasis = get_value('emphasis', '')
            side_line = get_value('side_line', '')
            is_bold = bool(get_value('bold'))
            is_italic = bool(get_value('italic'))
            if get_value('code', False):
                if code_font is None:
                    code_font = get_code_font(base_font)
                run_font = code_font
            else:
                run_font = base_font
            run_mode = (
                (4 if ruby else 0)
                | (2 if emphasis else 0)
                | (1 if side_line else 0)
            )
            overlay_mode = run_mode & 3
            text_len = len(seg_text)
            use_cached_direct_path = (text_len <= 8) or (seg_text in repeated_medium_texts)
            if use_cached_direct_path:
                cached_run_layout = local_run_layout_cache_get(seg_text)
                if cached_run_layout is None:
                    if text_len == 1:
                        tokens = (seg_text,)
                        layout_hints = build_single_hints(seg_text)
                    else:
                        tokens = tokenize_vertical_text(seg_text)
                        layout_hints = build_layout_hints_cached(tokens)
                    local_run_layout_cache_set(seg_text, (tokens, layout_hints))
                else:
                    tokens, layout_hints = cached_run_layout
                if run_mode == 0:
                    draw_text_run_plain(
                        tokens,
                        layout_hints,
                        run_font,
                        wrap_indent_step=wrap_indent_step,
                        is_bold=is_bold,
                        is_italic=is_italic,
                    )
                    continue
                if run_mode == 4:
                    ruby_overlay_groups = []
                    draw_text_run_ruby_only(
                        tokens,
                        layout_hints,
                        run_font,
                        ruby_overlay_groups=ruby_overlay_groups,
                        wrap_indent_step=wrap_indent_step,
                        is_bold=is_bold,
                        is_italic=is_italic,
                    )
                    if ruby_overlay_groups:
                        draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
                    continue
                if run_mode < 4:
                    overlay_cells = []
                    draw_text_run_overlay_cells_only(
                        tokens,
                        layout_hints,
                        run_font,
                        overlay_cells=overlay_cells,
                        wrap_indent_step=wrap_indent_step,
                        is_bold=is_bold,
                        is_italic=is_italic,
                    )
                    if overlay_cells:
                        if overlay_mode & 2:
                            draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=False)
                        if overlay_mode & 1:
                            draw_side_lines_cells(overlay_cells, side_line, ruby_text='', emphasis_kind=emphasis)
                    continue
                ruby_overlay_groups = []
                overlay_cells = []
                draw_text_run_overlay_only(
                    tokens,
                    layout_hints,
                    run_font,
                    ruby_overlay_groups=ruby_overlay_groups,
                    overlay_cells=overlay_cells,
                    wrap_indent_step=wrap_indent_step,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                if ruby_overlay_groups:
                    draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
                if overlay_cells:
                    if overlay_mode & 2:
                        draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=True)
                    if overlay_mode & 1:
                        draw_side_lines_cells(overlay_cells, side_line, ruby_text=ruby, emphasis_kind=emphasis)
                continue
            if run_mode == 0:
                draw_text_run(
                    seg_text,
                    run_font,
                    wrap_indent_chars=wrap_indent_chars,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                continue
            if run_mode == 4:
                ruby_overlay_groups = []
                draw_text_run(
                    seg_text,
                    run_font,
                    wrap_indent_chars=wrap_indent_chars,
                    ruby_overlay_groups=ruby_overlay_groups,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                if ruby_overlay_groups:
                    draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
                continue
            if run_mode < 4:
                overlay_cells = []
                draw_text_run(
                    seg_text,
                    run_font,
                    wrap_indent_chars=wrap_indent_chars,
                    overlay_cells=overlay_cells,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                if overlay_cells:
                    if overlay_mode & 2:
                        draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=False)
                    if overlay_mode & 1:
                        draw_side_lines_cells(overlay_cells, side_line, ruby_text='', emphasis_kind=emphasis)
                continue
            ruby_overlay_groups = []
            overlay_cells = []
            draw_text_run(
                seg_text,
                run_font,
                wrap_indent_chars=wrap_indent_chars,
                ruby_overlay_groups=ruby_overlay_groups,
                overlay_cells=overlay_cells,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            if ruby_overlay_groups:
                draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
            if overlay_cells:
                if overlay_mode & 2:
                    draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=True)
                if overlay_mode & 1:
                    draw_side_lines_cells(overlay_cells, side_line, ruby_text=ruby, emphasis_kind=emphasis)

    def draw_split_ruby(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]], rt_text: str, *, is_bold: bool = False, is_italic: bool = False) -> None:
        _raise_if_cancelled(self.should_cancel)
        if not rt_text or not segment_infos:
            return
        self.draw_split_ruby_groups(
            _build_ruby_overlay_groups(segment_infos),
            rt_text,
            is_bold=is_bold,
            is_italic=is_italic,
        )

    def draw_split_ruby_groups(self: _VerticalPageRenderer, grouped: Sequence[Mapping[str, Any]], rt_text: str, *, is_bold: bool = False, is_italic: bool = False) -> None:
        _refresh_core_globals()
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        raise_if_cancelled(should_cancel)
        if not rt_text or not grouped:
            return
        total_segments = len(grouped)
        if total_segments == 1:
            ruby_parts = [str(rt_text or '')]
        else:
            segment_lengths = [group['base_len'] for group in grouped]
            ruby_group_capacity = self._ruby_group_capacity
            segment_capacities = [
                ruby_group_capacity(group, idx, total_segments)
                for idx, group in enumerate(grouped)
            ]
            ruby_parts = _split_ruby_text_segments(rt_text, segment_lengths, segment_capacities=segment_capacities)

        args = self.args
        ruby_size = args.ruby_size
        font_size = args.font_size
        min_ry = args.margin_t
        effective_bottom_margin = _effective_ruby_overlay_bottom_margin(args)
        max_ry = args.height - effective_bottom_margin - ruby_size
        max_visible_ry = args.height - effective_bottom_margin
        step_y = ruby_size + 2
        get_page_image_draw = self.get_page_image_draw
        draw_char_tate_fn = draw_char_tate
        ruby_font = self.ruby_font
        cached_page_index = None
        target_draw = None
        last_segment_index = total_segments - 1
        center_single_segment = total_segments == 1
        ruby_bbox_cache: dict[str, tuple[int, int, int, int]] = {}
        for idx, (group, ruby_part) in enumerate(zip(grouped, ruby_parts)):
            raise_if_cancelled(should_cancel)
            if not ruby_part:
                continue
            group_page_index = group['page_index']
            if cached_page_index != group_page_index or target_draw is None:
                _target_img, target_draw = get_page_image_draw(group_page_index)
                cached_page_index = group_page_index
            start_y = group['start_y']
            end_y = group['end_y']
            rb_h = max(font_size, end_y - start_y + font_size)
            rt_h = len(ruby_part) * step_y
            if center_single_segment:
                ry = start_y + (rb_h - rt_h) // 2
            elif idx == 0:
                ry = end_y + font_size - rt_h
            elif idx == last_segment_index:
                ry = start_y
            else:
                ry = start_y + (rb_h - rt_h) // 2
            if ry < min_ry:
                ry = min_ry
            elif ry > max_ry:
                ry = max_ry
            ruby_x = group['x'] + font_size + 1
            for r_char in ruby_part:
                raise_if_cancelled(should_cancel)
                bbox = ruby_bbox_cache.get(r_char)
                if bbox is None:
                    bbox = _get_text_bbox(ruby_font, r_char, is_bold=is_bold)
                    ruby_bbox_cache[r_char] = bbox
                bbox_x0, bbox_y0, bbox_x1, bbox_y1 = bbox
                min_draw_x = -int(bbox_x0)
                max_draw_x = args.width - int(bbox_x1)
                if max_draw_x < min_draw_x:
                    ry += step_y
                    continue
                draw_x = max(min_draw_x, min(int(ruby_x), max_draw_x))
                min_draw_y = min_ry - int(bbox_y0)
                max_draw_y = max_visible_ry - int(bbox_y1)
                if max_draw_y < min_draw_y:
                    ry += step_y
                    continue
                draw_y = max(min_draw_y, min(int(ry), max_draw_y))
                if min_ry <= draw_y + int(bbox_y0) and draw_y + int(bbox_y1) <= max_visible_ry:
                    draw_char_tate_fn(
                        target_draw, r_char, (draw_x, draw_y), ruby_font, ruby_size,
                        is_bold=is_bold, ruby_mode=True, is_italic=is_italic,
                    )
                ry += step_y

    def _should_draw_emphasis_for_cell(self: _VerticalPageRenderer, cell_text: str) -> bool:
        return _should_draw_emphasis_for_cell_cached(str(cell_text or ''))

    def _get_emphasis_font(self: _VerticalPageRenderer) -> Any:
        emphasis_size = max(8, int(round(self.args.font_size * 0.48)))
        cache_key = (self.emphasis_font_value or '', emphasis_size, id(self.font))
        if self._emphasis_font_cache_key == cache_key and self._emphasis_font_cache is not None:
            return self._emphasis_font_cache
        emphasis_font = self.font
        if self.emphasis_font_value:
            try:
                emphasis_font = load_truetype_font(self.emphasis_font_value, emphasis_size)
            except Exception:
                emphasis_font = self.font
        self._emphasis_font_cache_key = cache_key
        self._emphasis_font_cache = emphasis_font
        self._emphasis_metrics_cache.clear()
        return emphasis_font

    def _get_emphasis_marker_metrics(self: _VerticalPageRenderer, marker: str) -> tuple[int, int, int, int]:
        cache_key = str(marker or '')
        cached = self._emphasis_metrics_cache.get(cache_key)
        if cached is not None:
            return cached
        emphasis_font = self._get_emphasis_font()
        bbox = _get_text_bbox(emphasis_font, cache_key, is_bold=False)
        mark_w = max(1, bbox[2] - bbox[0])
        mark_h = max(1, bbox[3] - bbox[1])
        metrics = (mark_w, mark_h, int(bbox[0]), int(bbox[1]))
        self._emphasis_metrics_cache[cache_key] = metrics
        return metrics

    def draw_emphasis_marks(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]], emphasis_kind: str, *, prefer_left: bool = False) -> None:
        _refresh_core_globals()
        _raise_if_cancelled(self.should_cancel)
        if not emphasis_kind or not segment_infos:
            return
        overlay_cells = [
            (int(info['page_index']), int(info['x']), int(info['y']), str(info.get('cell_text', '') or ''))
            for info in segment_infos
        ]
        self.draw_emphasis_marks_cells(overlay_cells, emphasis_kind, prefer_left=prefer_left)

    def draw_emphasis_marks_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell], emphasis_kind: str, *, prefer_left: bool = False) -> None:
        _refresh_core_globals()
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        raise_if_cancelled(should_cancel)
        marker = AOZORA_EMPHASIS_MARKERS.get(emphasis_kind)
        if not marker or not overlay_cells:
            return
        emphasis_font = self._get_emphasis_font()
        emphasis_size = max(8, int(round(self.args.font_size * 0.48)))
        mark_w, mark_h, bbox_x0, bbox_y0 = self._get_emphasis_marker_metrics(marker)
        x_offset = max(1, emphasis_size // 6) if prefer_left else max(1, emphasis_size // 8)
        get_page_image_draw = self.get_page_image_draw
        should_draw_for_cell = self._should_draw_emphasis_for_cell
        args = self.args
        font_size = args.font_size
        mark_y_offset = max(0, (font_size - mark_h) // 2) - bbox_y0
        mark_x_delta = (-mark_w - x_offset - bbox_x0) if prefer_left else (font_size + x_offset - bbox_x0)
        min_mark_y = int(args.margin_t) - bbox_y0
        max_mark_y = int(args.height - _effective_vertical_layout_bottom_margin(args.margin_b, font_size) - mark_h - bbox_y0)
        min_mark_x = -bbox_x0
        max_mark_x = int(args.width - mark_w - bbox_x0)
        cached_page_index = None
        draw_text = None
        for page_index, x_pos, y_pos, cell_text in overlay_cells:
            raise_if_cancelled(should_cancel)
            if not should_draw_for_cell(cell_text):
                continue
            if cached_page_index != page_index or draw_text is None:
                _target_img, target_draw = get_page_image_draw(page_index)
                cached_page_index = page_index
                draw_text = target_draw.text
            mark_y = int(y_pos + mark_y_offset)
            if max_mark_y >= min_mark_y:
                mark_y = min(max(mark_y, min_mark_y), max_mark_y)
            else:
                mark_y = min_mark_y
            mark_x = int(x_pos + mark_x_delta)
            if max_mark_x >= min_mark_x:
                mark_x = min(max(mark_x, min_mark_x), max_mark_x)
            else:
                mark_x = min_mark_x
            draw_text((mark_x, mark_y), marker, font=emphasis_font, fill=0)

    def _should_draw_side_line_for_cell(self: _VerticalPageRenderer, cell_text: str) -> bool:
        return _should_draw_side_line_for_cell_cached(str(cell_text or ''))

    def _iter_side_line_groups(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]]) -> list[SideLineGroup]:
        overlay_cells = [
            (int(info['page_index']), int(info['x']), int(info['y']), str(info.get('cell_text', '') or ''))
            for info in segment_infos
        ]
        return self._iter_side_line_groups_cells(overlay_cells)

    def _iter_side_line_spans_cells_iter(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell]) -> Iterator[SideLineSpan]:
        current_page_index = None
        current_x = None
        start_y = None
        end_y = None
        prev_y = None
        max_step = self.args.font_size + 3
        should_draw = self._should_draw_side_line_for_cell

        for page_index, x_pos, y_pos, cell_text in overlay_cells:
            if not should_draw(cell_text):
                if current_page_index is not None:
                    yield (current_page_index, current_x, start_y, end_y)
                current_page_index = None
                current_x = None
                start_y = None
                end_y = None
                prev_y = None
                continue
            if (
                current_page_index == page_index
                and current_x == x_pos
                and prev_y is not None
                and 0 <= (y_pos - prev_y) <= max_step
            ):
                end_y = y_pos
            else:
                if current_page_index is not None:
                    yield (current_page_index, current_x, start_y, end_y)
                current_page_index = page_index
                current_x = x_pos
                start_y = y_pos
                end_y = y_pos
            prev_y = y_pos

        if current_page_index is not None:
            yield (current_page_index, current_x, start_y, end_y)

    def _iter_side_line_spans_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell]) -> list[SideLineSpan]:
        return list(self._iter_side_line_spans_cells_iter(overlay_cells))

    def _iter_side_line_groups_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell]) -> list[SideLineGroup]:
        groups: list[SideLineGroup] = []
        for page_index, x_pos, start_y, end_y in self._iter_side_line_spans_cells(overlay_cells):
            if start_y == end_y:
                infos = [(page_index, x_pos, start_y, '')]
            else:
                infos = [(page_index, x_pos, start_y, ''), (page_index, x_pos, end_y, '')]
            groups.append({'page_index': page_index, 'x': x_pos, 'infos': infos})
        return groups

    def _draw_single_side_line(self: _VerticalPageRenderer, target_draw: ImageDraw.ImageDraw, x: int, y1: int, y2: int, line_kind: str, width: int = 1) -> None:
        draw_line = target_draw.line
        x = int(x)
        y1 = int(y1)
        y2 = max(y1, int(y2))
        if y1 == y2:
            # Keep degenerate guard-clamped spans as a valid two-endpoint line.
            # Some ImageDraw backends reject a one-point polyline, notably for
            # wavy side-lines after lower-bound and bottom-guard clamping.
            draw_line((x, y1, x, y2), fill=0, width=width)
            return
        if line_kind not in {'wavy', 'dashed', 'chain'}:
            draw_line((x, y1, x, y2), fill=0, width=width)
            return
        pattern_a, pattern_b, _unused = _get_side_line_pattern(self.args.font_size, line_kind)
        if line_kind == 'wavy':
            points = []
            append_point = points.append
            amplitude = pattern_a
            wavelength = pattern_b
            y = y1
            idx = 0
            while y <= y2:
                offset = -amplitude if idx % 2 == 0 else amplitude
                append_point((x + offset, y))
                y += wavelength
                idx += 1
            if not points or points[-1][1] != y2:
                offset = -amplitude if idx % 2 == 0 else amplitude
                append_point((x + offset, y2))
            draw_line(points, fill=0, width=width)
            return
        seg = pattern_a
        gap = pattern_b
        y = y1
        while y <= y2:
            seg_end = min(y2, y + seg)
            draw_line((x, y, x, seg_end), fill=0, width=width)
            y = seg_end + gap

    def draw_side_lines(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]], side_line_kind: str, *, ruby_text: str = '', emphasis_kind: str = '') -> None:
        _refresh_core_globals()
        _raise_if_cancelled(self.should_cancel)
        if not side_line_kind or not segment_infos:
            return
        overlay_cells = [
            (int(info['page_index']), int(info['x']), int(info['y']), str(info.get('cell_text', '') or ''))
            for info in segment_infos
        ]
        self.draw_side_lines_cells(overlay_cells, side_line_kind, ruby_text=ruby_text, emphasis_kind=emphasis_kind)

    def draw_side_lines_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell], side_line_kind: str, *, ruby_text: str = '', emphasis_kind: str = '') -> None:
        _refresh_core_globals()
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        raise_if_cancelled(should_cancel)
        if not side_line_kind or not overlay_cells:
            return
        args = self.args
        font_size = args.font_size
        prefer_left = bool(emphasis_kind)
        is_double = side_line_kind == 'double'
        right_padding, left_padding, base_gap, width, offset = _get_side_line_style(
            font_size,
            args.ruby_size,
            str(side_line_kind or ''),
            bool(ruby_text),
            prefer_left,
            prefer_left,
        )
        y_inset = max(1, int(round(font_size * 0.08)))
        get_page_image_draw = self.get_page_image_draw
        draw_side_line = self._draw_single_side_line
        iter_spans = self._iter_side_line_spans_cells_iter
        cached_page_index = None
        target_draw = None
        double_offset = max(2, offset)
        if prefer_left:
            base_x_delta = -base_gap - left_padding
            secondary_x_delta = -double_offset if is_double else None
        else:
            base_x_delta = font_size + base_gap + right_padding
            secondary_x_delta = double_offset if is_double else None
        primary_kind = 'solid' if is_double else side_line_kind
        primary_width = 1 if is_double else width
        bottom_guard = int(args.height - _effective_vertical_layout_bottom_margin(args.margin_b, font_size))
        min_y = int(args.margin_t)
        max_primary_x_extent = _side_line_horizontal_extent(font_size, str(primary_kind or ''), primary_width)
        min_primary_x = max_primary_x_extent
        max_primary_x = int(args.width - 1 - max_primary_x_extent)

        def clamp_span_y(start: int, end: int) -> tuple[int, int]:
            y1 = _clamp_int(start + y_inset, min_y, bottom_guard)
            y2 = _clamp_int(end + font_size - y_inset, min_y, bottom_guard)
            if y2 < y1:
                y2 = y1
            return y1, y2

        def clamp_line_x(x: int, kind: str, line_width: int) -> int:
            extent = _side_line_horizontal_extent(font_size, str(kind or ''), line_width)
            return _clamp_int(x, extent, int(args.width - 1 - extent))

        def clamp_line_pair_x(primary_x: int, secondary_x: int) -> tuple[int, int]:
            primary_extent = _side_line_horizontal_extent(font_size, str(primary_kind or ''), primary_width)
            secondary_extent = _side_line_horizontal_extent(font_size, 'solid', 1)
            primary_x = int(primary_x)
            secondary_x = int(secondary_x)
            canvas_right = int(args.width - 1)
            min_shift = max(primary_extent - primary_x, secondary_extent - secondary_x)
            max_shift = min(
                canvas_right - primary_extent - primary_x,
                canvas_right - secondary_extent - secondary_x,
            )
            if min_shift <= max_shift:
                shift = _clamp_int(0, min_shift, max_shift)
                return primary_x + shift, secondary_x + shift
            return (
                clamp_line_x(primary_x, primary_kind, primary_width),
                clamp_line_x(secondary_x, 'solid', 1),
            )

        if secondary_x_delta is None:
            for page_index, x_pos, start_y, end_y in iter_spans(overlay_cells):
                raise_if_cancelled(should_cancel)
                if cached_page_index != page_index or target_draw is None:
                    _target_img, target_draw = get_page_image_draw(page_index)
                    cached_page_index = page_index
                y1, y2 = clamp_span_y(start_y, end_y)
                line_x = _clamp_int(x_pos + base_x_delta, min_primary_x, max_primary_x)
                draw_side_line(target_draw, line_x, y1, y2, primary_kind, width=primary_width)
            return
        for page_index, x_pos, start_y, end_y in iter_spans(overlay_cells):
            raise_if_cancelled(should_cancel)
            if cached_page_index != page_index or target_draw is None:
                _target_img, target_draw = get_page_image_draw(page_index)
                cached_page_index = page_index
            y1, y2 = clamp_span_y(start_y, end_y)
            base_x, secondary_x = clamp_line_pair_x(
                x_pos + base_x_delta,
                x_pos + base_x_delta + secondary_x_delta,
            )
            draw_side_line(target_draw, base_x, y1, y2, primary_kind, width=primary_width)
            draw_side_line(target_draw, secondary_x, y1, y2, 'solid', width=1)

    def draw_inline_image(self: _VerticalPageRenderer, char_img: Image.Image | None, *, wrap_indent_chars: int = 0) -> None:
        if char_img is None:
            return
        self.ensure_room(self.args.font_size, continuation_indent_chars=wrap_indent_chars)
        paste_x = self.curr_x + (self.args.font_size - char_img.width) // 2
        paste_y = self.curr_y + max(0, (self.args.font_size - char_img.height) // 2)
        self.img.paste(char_img, (paste_x, paste_y))
        self.curr_y += self.args.font_size + 2
        self.has_drawn_on_page = True
        self.has_started_document = True


def _render_text_blocks_to_page_entries(blocks: Sequence[TextBlock], font_value: str | Path, args: ConversionArgs, should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None, max_output_pages: int | None = None, render_state: dict[str, object] | None = None) -> PageEntries:
    _refresh_core_globals()
    _raise_if_cancelled(should_cancel)
    if not _has_renderable_text_blocks(blocks, should_cancel=should_cancel):
        raise RuntimeError("入力ファイルに変換できる本文がありません。")

    font = load_truetype_font(font_value, args.font_size)
    ruby_font = load_truetype_font(font_value, args.ruby_size)

    def _load_code_font() -> Any:
        code_font_value = get_code_font_value(str(font_value))
        try:
            return load_truetype_font(code_font_value, args.font_size)
        except Exception:
            return font

    page_entries: PageEntries = []
    render_progress_state = {'active_block_index': 0}
    page_limit = max(1, int(max_output_pages)) if max_output_pages else None
    page_limit_reached = False
    if render_state is not None:
        render_state.clear()
        render_state['page_limit_reached'] = False
    renderer = _VerticalPageRenderer(
        args,
        font,
        ruby_font,
        should_cancel=should_cancel,
        max_buffered_pages=page_limit,
        default_page_args=args,
        default_page_label='本文ページ',
        emphasis_font_value=font_value,
        code_font_loader=_load_code_font,
    )

    def _estimate_text_render_total() -> int:
        completed_pages = max(0, len(page_entries))
        active_block_index = int(render_progress_state.get('active_block_index', 0) or 0)
        remaining_blocks = max(0, len(blocks) - active_block_index)
        return max(1, completed_pages + remaining_blocks + 1)

    def add_page_entry(image: Image.Image, *, copy_image: bool = True, label: str = '本文ページ') -> None:
        nonlocal page_limit_reached
        if page_limit is not None and len(page_entries) >= page_limit:
            page_limit_reached = True
            return
        entry = _make_page_entry(image.copy() if copy_image else image, page_args=args, label=label)
        _apply_page_entry_margin_clip(entry)
        page_entries.append(entry)
        _emit_progress(progress_cb, len(page_entries), _estimate_text_render_total(), f'本文ページを作成中… ({len(page_entries)} ページ)')

    def spool_completed_block_pages() -> None:
        for entry in renderer.pop_page_entries():
            _raise_if_cancelled(should_cancel)
            add_page_entry(entry['image'], copy_image=False, label=entry.get('label') or '本文ページ')
        if page_limit is not None:
            remaining = page_limit - len(page_entries)
            renderer.set_page_buffer_limit(remaining if remaining > 0 else 1)

    def draw_runs(runs: Sequence[TextRun], wrap_indent_chars: int = 0) -> None:
        _raise_if_cancelled(should_cancel)
        renderer.draw_runs(runs, default_font=font, wrap_indent_chars=wrap_indent_chars)

    has_renderable_after_index = [False] * (len(blocks) + 1)
    seen_renderable = False
    for reverse_index in range(len(blocks) - 1, -1, -1):
        has_renderable_after_index[reverse_index] = seen_renderable
        if blocks[reverse_index].get('kind') not in {'blank', 'pagebreak'}:
            seen_renderable = True

    total_blocks = max(1, len(blocks))
    first_content = True
    previous_was_blank = False
    try:
        for block_index, block in enumerate(blocks, 1):
            render_progress_state['active_block_index'] = block_index
            _emit_progress(progress_cb, block_index - 1, total_blocks, f'テキストを描画中… ({max(0, block_index - 1)}/{total_blocks} ブロック)')
            block_kind = block.get('kind')
            if block_kind == 'blank':
                previous_was_blank = True
                continue
            if block_kind == 'pagebreak':
                previous_was_blank = False
                if renderer.has_pending_output:
                    renderer.flush_current_page()
                    spool_completed_block_pages()
                if page_limit is not None and len(page_entries) >= page_limit and has_renderable_after_index[block_index]:
                    page_limit_reached = True
                    break
                continue
            gap = block.get('blank_before', 1)
            if first_content:
                first_content = False
            elif renderer.has_drawn_on_page:
                renderer.advance_column(max(gap, 2 if previous_was_blank else gap))
            previous_was_blank = False
            block_indent_chars = block.get('indent_chars', 1 if block.get('indent', False) else 0)
            block_wrap_indent_chars = block.get('wrap_indent_chars', 0)
            if block.get('indent', False):
                renderer.insert_paragraph_indent(block_indent_chars)
            draw_runs(block.get('runs', []), wrap_indent_chars=block_wrap_indent_chars)
            spool_completed_block_pages()
            if page_limit is not None and len(page_entries) >= page_limit and has_renderable_after_index[block_index]:
                page_limit_reached = True
                break
    except _PreviewPageLimitReached:
        page_limit_reached = True
        spool_completed_block_pages()

    if not page_limit_reached:
        spool_completed_block_pages()
        if renderer.has_drawn_on_page:
            if page_limit is not None and len(page_entries) >= page_limit:
                page_limit_reached = True
            else:
                add_page_entry(renderer.img, copy_image=False)

    if page_limit_reached:
        _emit_progress(progress_cb, len(page_entries), max(1, page_limit or len(page_entries)), f'プレビュー生成を上限 {len(page_entries)} ページで打ち切りました。')
    if render_state is not None:
        render_state['page_limit_reached'] = bool(page_limit_reached)
    _emit_progress(progress_cb, total_blocks, total_blocks, f'テキスト描画が完了しました。({len(page_entries)} ページ)')
    return page_entries


def _render_text_blocks_to_images(blocks: Sequence[TextBlock], font_value: str | Path, args: ConversionArgs, should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None, max_output_pages: int | None = None, render_state: dict[str, object] | None = None) -> list[Image.Image]:
    _refresh_core_globals()
    return [entry['image'] for entry in _render_text_blocks_to_page_entries(
        blocks,
        font_value,
        args,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
        max_output_pages=max_output_pages,
        render_state=render_state,
    )]

