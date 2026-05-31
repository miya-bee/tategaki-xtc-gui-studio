from __future__ import annotations

import base64
import inspect
import io
import unittest

from PIL import Image

import tategakiXTC_gui_core as core
import tategakiXTC_gui_core_renderer as renderer
import tategakiXTC_worker_logic as worker_logic


class ProgressBarRegressionTests(unittest.TestCase):
    def test_conversion_args_reserves_bottom_margin_when_progress_bar_enabled(self) -> None:
        args = core.ConversionArgs(
            width=120,
            height=80,
            margin_b=0,
            progress_bar_enabled=True,
            progress_bar_position='center',
        )
        self.assertEqual(args.margin_b, 10)

    def test_worker_args_normalizes_progress_bar_position(self) -> None:
        args = worker_logic.build_conversion_args({
            'progress_bar_enabled': True,
            'progress_bar_position': '下左',
        })
        self.assertTrue(args.progress_bar_enabled)
        self.assertEqual(args.progress_bar_position, 'left')

    def test_progress_bar_overlay_draws_center_bottom_ink(self) -> None:
        args = core.ConversionArgs(
            width=140,
            height=90,
            margin_b=0,
            progress_bar_enabled=True,
            progress_bar_position='center',
        )
        image = Image.new('L', (args.width, args.height), 255)
        rendered = core.apply_progress_bar_overlay_to_canvas(image, args, 2, 4)
        bottom_band = rendered.crop((0, args.height - args.margin_b, args.width, args.height))
        dark_pixels = [(x, y) for y in range(bottom_band.height) for x in range(bottom_band.width) if bottom_band.getpixel((x, y)) < 128]
        self.assertGreater(len(dark_pixels), 0)
        xs = [x for x, _y in dark_pixels]
        self.assertGreaterEqual(min(xs), 35)
        self.assertLessEqual(max(xs), 105)

    def test_progress_bar_overlay_draws_track_progress_and_marker_without_gray(self) -> None:
        args = core.ConversionArgs(
            width=140,
            height=90,
            margin_b=0,
            progress_bar_enabled=True,
            progress_bar_position='center',
        )
        image = Image.new('L', (args.width, args.height), 255)
        rendered = core.apply_progress_bar_overlay_to_canvas(image, args, 2, 4)

        # width 140 -> bar width 56, centered at x=42..97.
        # page 2/4 -> marker is near the middle at x=70.
        self.assertEqual(rendered.getpixel((42, 85)), 0)  # track start
        self.assertEqual(rendered.getpixel((97, 85)), 0)  # track end
        self.assertEqual(rendered.getpixel((50, 84)), 0)  # thick read progress upper row
        self.assertEqual(rendered.getpixel((50, 86)), 0)  # thick read progress lower row
        self.assertEqual(rendered.getpixel((90, 84)), 255)  # unread side is only the thin center track
        self.assertEqual(rendered.getpixel((90, 86)), 255)
        self.assertEqual(rendered.getpixel((70, 83)), 0)  # current-position marker top
        self.assertEqual(rendered.getpixel((70, 87)), 0)  # current-position marker bottom
        pixels = set(rendered.crop((42, 80, 98, 90)).getdata())
        self.assertLessEqual(pixels, {0, 255})

    def test_progress_bar_overlay_draws_left_bottom_ink(self) -> None:
        args = core.ConversionArgs(
            width=140,
            height=90,
            margin_l=12,
            margin_b=0,
            progress_bar_enabled=True,
            progress_bar_position='left',
        )
        image = Image.new('L', (args.width, args.height), 255)
        rendered = core.apply_progress_bar_overlay_to_canvas(image, args, 1, 4)
        bottom_band = rendered.crop((0, args.height - args.margin_b, args.width, args.height))
        xs = [x for y in range(bottom_band.height) for x in range(bottom_band.width) if bottom_band.getpixel((x, y)) < 128]
        self.assertGreater(len(xs), 0)
        self.assertGreaterEqual(min(xs), 12)
        self.assertLess(min(xs), 20)


    def test_bottom_overlay_layout_keeps_progress_bar_out_of_page_number_rect(self) -> None:
        args = core.ConversionArgs(
            width=90,
            height=60,
            margin_b=0,
            margin_r=0,
            page_number_enabled=True,
            page_number_font_size=12,
            progress_bar_enabled=True,
            progress_bar_position='center',
        )
        image = Image.new('L', (args.width, args.height), 255)
        page_only = core.apply_page_number_overlay_to_canvas(image, args, 88, 100)
        combined = core.apply_bottom_overlays_to_canvas(image, args, 88, 100)

        # The page-number area is the priority bottom overlay.  If the progress
        # bar entered this rectangle, it would add black pixels behind the text.
        x0, y0, x1, y1 = 45, args.height - args.margin_b, args.width, args.height
        self.assertEqual(
            list(page_only.crop((x0, y0, x1, y1)).getdata()),
            list(combined.crop((x0, y0, x1, y1)).getdata()),
        )

    def test_preview_bundle_uses_combined_bottom_overlay_without_individual_fallback(self) -> None:
        source = inspect.getsource(renderer.generate_preview_bundle)
        self.assertIn('apply_bottom_overlays_to_canvas', source)
        self.assertNotIn("globals().get('apply_progress_bar_overlay_to_canvas')", source)
        self.assertNotIn("globals().get('apply_page_number_overlay_to_canvas')", source)

    def test_preview_bundle_draws_progress_bar_overlay_for_image_mode(self) -> None:
        src = Image.new('L', (120, 80), 255)
        buf = io.BytesIO()
        src.save(buf, format='PNG')
        bundle = renderer.generate_preview_bundle({
            'mode': 'image',
            'file_b64': 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode('ascii'),
            'width': 120,
            'height': 80,
            'output_format': 'xtc',
            'dither': False,
            'threshold': 128,
            'night_mode': False,
            'progress_bar_enabled': True,
            'progress_bar_position': 'center',
            'margin_b': 0,
        })
        encoded = bundle['pages'][0]
        rendered = Image.open(io.BytesIO(base64.b64decode(encoded))).convert('L')
        bottom_band = rendered.crop((0, 70, 120, 80))
        self.assertGreater(sum(1 for value in bottom_band.getdata() if value < 128), 0)


if __name__ == '__main__':
    unittest.main()
