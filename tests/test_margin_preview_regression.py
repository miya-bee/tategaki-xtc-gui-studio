from __future__ import annotations

import unittest
from PIL import Image, ImageOps

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_spec


class MarginPreviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.font_value = resolve_test_font_spec('NotoSerifJP-Regular.ttf')

    def _bbox_for(self, *, margin_t: int = 0, margin_b: int = 0, margin_r: int = 0, margin_l: int = 0, text: str = 'あ'):
        args = core.ConversionArgs(
            width=600,
            height=800,
            font_size=20,
            ruby_size=11,
            line_spacing=35,
            margin_t=margin_t,
            margin_b=margin_b,
            margin_r=margin_r,
            margin_l=margin_l,
            threshold=180,
            night_mode=False,
            dither=False,
            output_format='xtc',
            kinsoku_mode='standard',
        )
        blocks = [{
            'kind': 'paragraph',
            'runs': [{'text': text, 'ruby': '', 'bold': False}],
            'indent': False,
        }]
        image = core._render_text_blocks_to_images(blocks, self.font_value, args, max_output_pages=1)[0]
        bbox = ImageOps.invert(image).getbbox()
        self.assertIsNotNone(bbox)
        return bbox

    def test_top_margin_zero_keeps_rendering_at_first_text_cell(self):
        bbox_zero = self._bbox_for(margin_t=0)
        bbox_twelve = self._bbox_for(margin_t=12)
        self.assertEqual(bbox_twelve[1] - bbox_zero[1], 12)

    def test_right_margin_zero_still_honors_ruby_reserve_but_not_extra_margin(self):
        bbox_zero = self._bbox_for(margin_r=0)
        bbox_twelve = self._bbox_for(margin_r=12)
        self.assertEqual(bbox_zero[0] - bbox_twelve[0], 12)

    def test_text_page_margin_clip_clears_all_four_outer_margins_but_keeps_ruby_lane(self):
        args = core.ConversionArgs(
            width=80,
            height=60,
            font_size=20,
            ruby_size=10,
            line_spacing=34,
            margin_t=6,
            margin_b=7,
            margin_r=9,
            margin_l=8,
            threshold=180,
            night_mode=False,
            dither=False,
            output_format='xtc',
            kinsoku_mode='standard',
        )
        img = Image.new('L', (args.width, args.height), 0)
        core._apply_text_page_margin_clip(img, args)

        self.assertEqual(img.getpixel((0, args.height // 2)), 255)
        self.assertEqual(img.getpixel((args.margin_l - 1, args.height // 2)), 255)
        self.assertEqual(img.getpixel((args.margin_l, args.height // 2)), 0)
        self.assertEqual(img.getpixel((args.width // 2, 0)), 255)
        self.assertEqual(img.getpixel((args.width // 2, args.margin_t - 1)), 255)
        self.assertEqual(img.getpixel((args.width // 2, args.margin_t)), 0)
        self.assertEqual(img.getpixel((args.width // 2, args.height - args.margin_b)), 255)
        self.assertEqual(img.getpixel((args.width - args.margin_r, args.height // 2)), 255)
        # 右余白のすぐ内側はルビ予約領域として残す。
        self.assertEqual(img.getpixel((args.width - args.margin_r - 1, args.height // 2)), 0)

    def test_page_entry_margin_clip_skips_full_page_illustration_label(self):
        args = core.ConversionArgs(width=40, height=40, margin_t=5, margin_b=5, margin_r=5, margin_l=5)
        img = Image.new('L', (args.width, args.height), 0)
        entry = {'image': img, 'page_args': args, 'label': '挿絵ページ'}

        core._apply_page_entry_margin_clip(entry)

        self.assertEqual(img.getpixel((0, 0)), 0)
        self.assertEqual(img.getpixel((args.width - 1, args.height - 1)), 0)


if __name__ == '__main__':
    unittest.main()
