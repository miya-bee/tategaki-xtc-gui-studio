from __future__ import annotations

import base64
import io
import unittest

from PIL import Image

import tategakiXTC_gui_core as core
import tategakiXTC_gui_core_renderer as renderer
import tategakiXTC_worker_logic as worker_logic


class PageNumberRegressionTests(unittest.TestCase):
    def test_conversion_args_reserves_bottom_margin_when_page_number_enabled(self) -> None:
        args = core.ConversionArgs(
            width=120,
            height=80,
            margin_b=0,
            page_number_enabled=True,
            page_number_font_size=12,
        )
        self.assertEqual(args.margin_b, 13)

    def test_conversion_args_clamps_page_number_font_size_30_or_larger(self) -> None:
        self.assertEqual(core.ConversionArgs(page_number_font_size=30).page_number_font_size, 29)
        self.assertEqual(
            worker_logic.build_conversion_args({'page_number_enabled': True, 'page_number_font_size': 99}).page_number_font_size,
            29,
        )

    def test_page_number_overlay_draws_bottom_right_ink(self) -> None:
        args = core.ConversionArgs(
            width=140,
            height=90,
            margin_r=4,
            margin_b=0,
            page_number_enabled=True,
            page_number_font_size=12,
        )
        image = Image.new('L', (args.width, args.height), 255)
        rendered = core.apply_page_number_overlay_to_canvas(image, args, 1, 100)
        bottom_band = rendered.crop((0, args.height - args.margin_b, args.width, args.height))
        dark_pixels = sum(1 for value in bottom_band.getdata() if value < 128)
        self.assertGreater(dark_pixels, 0)


    def test_preview_bundle_draws_page_number_overlay_for_image_mode(self) -> None:
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
            'page_number_enabled': True,
            'page_number_font_size': 12,
            'margin_b': 0,
            'margin_r': 4,
        })
        encoded = bundle['pages'][0]
        rendered = Image.open(io.BytesIO(base64.b64decode(encoded))).convert('L')
        bottom_band = rendered.crop((0, 67, 120, 80))
        self.assertGreater(sum(1 for value in bottom_band.getdata() if value < 128), 0)

    def test_page_number_overlay_is_noop_when_disabled(self) -> None:
        args = core.ConversionArgs(width=140, height=90, page_number_enabled=False)
        image = Image.new('L', (args.width, args.height), 255)
        rendered = core.apply_page_number_overlay_to_canvas(image, args, 1, 100)
        self.assertEqual(list(rendered.getdata()), list(image.getdata()))


if __name__ == '__main__':
    unittest.main()
