from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock
import tempfile

from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
import tategakiXTC_gui_preview_controller as preview_controller

FONT_DIR = ROOT / "Font"
_FONT_CANDIDATES = list(FONT_DIR.glob("*.ttf")) if FONT_DIR.exists() else []


def _make_font(size: int = 40):
    if _FONT_CANDIDATES:
        return ImageFont.truetype(str(_FONT_CANDIDATES[0]), size)
    return ImageFont.load_default()


def _make_draw(size: int = 160):
    img = Image.new("L", (size, size), 255)
    return core.create_image_draw(img), img


class MiddleDotPositionTests(unittest.TestCase):
    def test_middle_dot_is_classified_separately_from_default(self):
        self.assertEqual(core._classify_tate_draw_char("・"), "middle_dot")
        self.assertEqual(core._classify_tate_draw_char("･"), "middle_dot")
        self.assertEqual(core._classify_tate_draw_char("·"), "middle_dot")
        self.assertEqual(core._classify_tate_draw_char("あ"), "default")

    def test_middle_dot_uses_ink_centered_text_flow_route(self):
        draw, _img = _make_draw()
        font = _make_font(40)

        with mock.patch.object(core, "draw_ink_centered_glyph", wraps=core.draw_ink_centered_glyph) as centered:
            core.draw_char_tate(draw, "・", (10, 10), font, 40, ruby_mode=False)

        centered.assert_called_once()
        self.assertEqual(centered.call_args.args[1], "・")
        self.assertIs(centered.call_args.kwargs.get("align_to_text_flow"), True)
        self.assertEqual(centered.call_args.kwargs.get("rotate_degrees", 0), 0)

    def test_middle_dot_position_mode_changes_extra_y(self):
        font = _make_font(40)
        glyph = Image.new("L", (8, 8), 0)
        mask = Image.new("L", (8, 8), 255)
        standard_calls: list[tuple[int, int]] = []
        down_calls: list[tuple[int, int]] = []

        draw, _img = _make_draw()
        with mock.patch.object(core, "_render_text_glyph_and_mask_shared", return_value=(glyph, mask)), \
             mock.patch.object(core, "_get_ichi_visual_target_center_y", return_value=24.0), \
             mock.patch.object(core, "_paste_glyph_image", side_effect=lambda _draw, _glyph, xy, _mask=None: standard_calls.append(xy)):
            setattr(draw, "_tategaki_middle_dot_position_mode", "standard")
            core.draw_char_tate(draw, "・", (10, 10), font, 40, ruby_mode=False)

        draw, _img = _make_draw()
        with mock.patch.object(core, "_render_text_glyph_and_mask_shared", return_value=(glyph, mask)), \
             mock.patch.object(core, "_get_ichi_visual_target_center_y", return_value=24.0), \
             mock.patch.object(core, "_paste_glyph_image", side_effect=lambda _draw, _glyph, xy, _mask=None: down_calls.append(xy)):
            setattr(draw, "_tategaki_middle_dot_position_mode", "down_strong")
            core.draw_char_tate(draw, "・", (10, 10), font, 40, ruby_mode=False)

        self.assertEqual(len(standard_calls), 1)
        self.assertEqual(len(down_calls), 1)
        self.assertGreater(down_calls[0][1], standard_calls[0][1])

    def test_apply_draw_glyph_position_modes_carries_middle_dot_mode(self):
        draw, _img = _make_draw()
        args = core.ConversionArgs(middle_dot_position_mode="up_weak")
        core._apply_draw_glyph_position_modes(draw, args)
        self.assertEqual(getattr(draw, "_tategaki_middle_dot_position_mode"), "up_weak")


    def test_conversion_args_normalizes_empty_middle_dot_position_mode(self):
        args = core.ConversionArgs(middle_dot_position_mode="")
        self.assertEqual(args.middle_dot_position_mode, "standard")

        args_none = core.ConversionArgs(middle_dot_position_mode=None)  # type: ignore[arg-type]
        self.assertEqual(args_none.middle_dot_position_mode, "standard")

    def test_preview_payload_carries_middle_dot_position_mode(self):
        payload = preview_controller.build_preview_payload(
            render_settings_base={
                "target": "sample.txt",
                "font_file": "font.ttf",
                "font_size": 28,
                "ruby_size": 12,
                "line_spacing": 44,
                "margin_t": 10,
                "margin_b": 12,
                "margin_r": 14,
                "margin_l": 16,
                "dither": False,
                "threshold": 128,
                "night_mode": False,
                "kinsoku_mode": "standard",
                "middle_dot_position_mode": "up_strong",
                "output_format": "xtc",
                "width": 528,
                "height": 792,
            },
            current_preview_mode="text",
            selected_profile_key="x3",
            preview_image_data_url="",
            preview_page_limit=1,
            default_preview_page_limit=10,
        )

        self.assertEqual(payload["middle_dot_position_mode"], "up_strong")

    def test_preview_bundle_cache_key_includes_middle_dot_position_mode(self):
        base = {
            "mode": "text",
            "target_path": "",
            "font_file": "font.ttf",
            "width": 96,
            "height": 144,
            "font_size": 20,
            "ruby_size": 10,
            "line_spacing": 28,
            "margin_t": 8,
            "margin_b": 8,
            "margin_l": 8,
            "margin_r": 8,
            "threshold": 128,
            "output_format": "xtc",
            "night_mode": False,
            "dither": False,
            "max_pages": 1,
        }

        standard_key = core._preview_bundle_cache_key(
            {**base, "middle_dot_position_mode": "standard"},
            preview_sources=[],
        )
        up_key = core._preview_bundle_cache_key(
            {**base, "middle_dot_position_mode": "up_strong"},
            preview_sources=[],
        )

        self.assertNotEqual(standard_key, up_key)

    def test_generate_preview_bundle_passes_middle_dot_mode_to_preview_args(self):
        core.clear_preview_bundle_cache()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.txt"
            path.write_text("中黒・確認", encoding="utf-8")
            payload = {
                "mode": "text",
                "target_path": str(path),
                "font_file": str(_FONT_CANDIDATES[0]) if _FONT_CANDIDATES else "",
                "width": 96,
                "height": 144,
                "font_size": 20,
                "ruby_size": 10,
                "line_spacing": 28,
                "margin_t": 8,
                "margin_b": 8,
                "margin_l": 8,
                "margin_r": 8,
                "threshold": 128,
                "output_format": "xtc",
                "night_mode": False,
                "dither": False,
                "max_pages": 1,
                "middle_dot_position_mode": "down_strong",
            }
            page = Image.new("L", (96, 144), 255)
            captured: list[core.ConversionArgs] = []

            def _fake_render(_target_path, _font_value, preview_args, **_kwargs):
                captured.append(preview_args)
                return [page.copy()], False

            with mock.patch.object(core, "_preview_target_requires_font", return_value=False), \
                 mock.patch.object(core, "_render_preview_pages_from_target", side_effect=_fake_render):
                core.generate_preview_bundle(payload)

        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].middle_dot_position_mode, "down_strong")


if __name__ == "__main__":
    unittest.main()
