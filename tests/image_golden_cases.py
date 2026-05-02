import sys
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec
from tests.golden_case_registry import (
    CASE_PROFILE_PREFIX_RULES,
    CASE_SPECS,
    GOLDEN_DIR,
    THRESHOLD_PROFILES,
    expected_profile_prefix_for_case,
    resolve_case_thresholds,
    validate_threshold_profile_registry,
)

FONT_SPEC = resolve_test_font_spec()
FONT_PATH = resolve_test_font_path()

def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return core.load_truetype_font(FONT_SPEC, size)


def _build_args(args_kwargs: Dict) -> core.ConversionArgs:
    return core.ConversionArgs(**args_kwargs)


def _concat_pages(pages: List[Image.Image], gap: int = 6) -> Image.Image:
    if not pages:
        raise AssertionError('concat 대상 페이지가ありません')
    if len(pages) == 1:
        return pages[0]
    width = max(page.width for page in pages)
    height = sum(page.height for page in pages) + gap * (len(pages) - 1)
    canvas = Image.new('L', (width, height), 255)
    cursor_y = 0
    for page in pages:
        canvas.paste(page, (0, cursor_y))
        cursor_y += page.height + gap
    return canvas


def render_glyph_case(char: str, *, font_size: int = 48, canvas_size: int = 96, origin=(24, 24)) -> Image.Image:
    img = Image.new('L', (canvas_size, canvas_size), 255)
    draw = core.create_image_draw(img)
    font = _load_font(font_size)
    core.draw_char_tate(draw, char, origin, font, font_size)
    return img


def render_tatechuyoko_case(text: str, *, font_size: int = 48, canvas_size: int = 96, origin=(24, 24)) -> Image.Image:
    img = Image.new('L', (canvas_size, canvas_size), 255)
    draw = core.create_image_draw(img)
    font = _load_font(font_size)
    core.draw_tatechuyoko(draw, text, origin, font, font_size)
    return img


def render_page_blocks_case(args_kwargs: Dict, blocks: List[Dict], *, page_mode: str = 'first', gap: int = 6) -> Image.Image:
    args = _build_args(args_kwargs)
    pages = core._render_text_blocks_to_images(blocks, FONT_PATH, args)
    if not pages:
        raise AssertionError('ページ描画結果がありません')
    if page_mode == 'first':
        return pages[0]
    if page_mode == 'strip':
        return _concat_pages(pages, gap=gap)
    raise KeyError(f'Unknown page_mode: {page_mode}')


def render_filtered_page_case(args_kwargs: Dict, blocks: List[Dict], *, page_mode: str = 'first', gap: int = 6) -> Image.Image:
    args = _build_args(args_kwargs)
    base = render_page_blocks_case(args_kwargs, blocks, page_mode=page_mode, gap=gap)
    output_format = core._normalize_output_format(getattr(args, 'output_format', 'xtc'))
    if output_format == 'xtch':
        filtered = core.apply_xtch_filter(base, args.dither, args.threshold, args.width, args.height)
    else:
        filtered = core.apply_xtc_filter(base, args.dither, args.threshold, args.width, args.height).convert('L')
    if getattr(args, 'night_mode', False):
        filtered = ImageOps.invert(filtered.convert('L'))
    return filtered.convert('L')


def render_case(name: str) -> Image.Image:
    spec = CASE_SPECS[name]
    kind = spec['kind']
    if kind == 'glyph':
        return render_glyph_case(
            spec['char'],
            font_size=spec['font_size'],
            canvas_size=spec['canvas_size'],
            origin=spec['origin'],
        )
    if kind == 'tatechuyoko':
        return render_tatechuyoko_case(
            spec['text'],
            font_size=spec['font_size'],
            canvas_size=spec['canvas_size'],
            origin=spec['origin'],
        )
    if kind == 'page_blocks':
        return render_page_blocks_case(
            spec['args'],
            spec['blocks'],
            page_mode=spec.get('page_mode', 'first'),
            gap=spec.get('gap', 6),
        )
    if kind == 'filtered_page':
        return render_filtered_page_case(
            spec['args'],
            spec['blocks'],
            page_mode=spec.get('page_mode', 'first'),
            gap=spec.get('gap', 6),
        )
    raise KeyError(f'Unknown golden case: {name}')


__all__ = ['CASE_PROFILE_PREFIX_RULES', 'CASE_SPECS', 'FONT_PATH', 'GOLDEN_DIR', 'THRESHOLD_PROFILES', 'expected_profile_prefix_for_case', 'render_case', 'render_filtered_page_case', 'render_page_blocks_case', 'resolve_case_thresholds', 'validate_threshold_profile_registry']
