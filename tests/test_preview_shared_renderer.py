import base64
import io
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec


class PreviewSharedRendererTests(unittest.TestCase):
    def test_preview_text_mode_matches_shared_renderer_first_page(self):
        font_value = resolve_test_font_spec()
        args = {
            'width': '160',
            'height': '220',
            'font_size': '26',
            'ruby_size': '12',
            'line_spacing': '44',
            'margin_t': '12',
            'margin_b': '14',
            'margin_r': '12',
            'margin_l': '12',
            'dither': 'false',
            'threshold': '128',
            'night_mode': 'false',
            'kinsoku_mode': 'standard',
            'output_format': 'xtc',
            'mode': 'text',
            'font_file': font_value,
        }

        preview_b64 = core.generate_preview_base64(args)
        preview_img = Image.open(io.BytesIO(base64.b64decode(preview_b64))).convert('L')

        conv_args = core.ConversionArgs(
            width=160,
            height=220,
            font_size=26,
            ruby_size=12,
            line_spacing=44,
            margin_t=12,
            margin_b=14,
            margin_r=12,
            margin_l=12,
            dither=False,
            night_mode=False,
            threshold=128,
            kinsoku_mode='standard',
            output_format='xtc',
        )
        page_images = core._render_text_blocks_to_images(core._build_default_preview_blocks(), font_value, conv_args)
        self.assertTrue(page_images)
        expected = core.apply_xtc_filter(page_images[0], False, 128, 160, 220).convert('L')

        self.assertEqual(preview_img.size, expected.size)
        self.assertEqual(preview_img.tobytes(), expected.tobytes())

    def test_shared_renderer_emits_progress_callback_updates(self):
        font_value = resolve_test_font_spec()
        conv_args = core.ConversionArgs(
            width=160,
            height=220,
            font_size=26,
            ruby_size=12,
            line_spacing=44,
            margin_t=12,
            margin_b=14,
            margin_r=12,
            margin_l=12,
            dither=False,
            night_mode=False,
            threshold=128,
            kinsoku_mode='standard',
            output_format='xtc',
        )
        events = []

        def progress_cb(done, total, message):
            events.append((done, total, message))

        page_images = core._render_text_blocks_to_images(
            core._build_default_preview_blocks(),
            font_value,
            conv_args,
            progress_cb=progress_cb,
        )
        self.assertTrue(page_images)
        self.assertTrue(events)
        self.assertTrue(any('本文ページを作成中' in msg for _, _, msg in events))
        self.assertIn('テキスト描画が完了しました', events[-1][2])

    def test_text_preview_stops_at_requested_page_limit_inside_long_run(self):
        font_value = resolve_test_font_spec()
        conv_args = core.ConversionArgs(
            width=160,
            height=220,
            font_size=26,
            ruby_size=12,
            line_spacing=44,
            margin_t=12,
            margin_b=14,
            margin_r=12,
            margin_l=12,
            dither=False,
            night_mode=False,
            threshold=128,
            kinsoku_mode='standard',
            output_format='xtc',
        )
        render_state = {}
        blocks = [{'kind': 'paragraph', 'runs': [{'text': 'abcdefg ' * 2000}]}]

        page_images = core._render_text_blocks_to_images(
            blocks,
            font_value,
            conv_args,
            max_output_pages=1,
            render_state=render_state,
        )

        self.assertEqual(len(page_images), 1)
        self.assertTrue(render_state.get('page_limit_reached'))

    def test_target_text_preview_uses_requested_page_limit(self):
        font_value = resolve_test_font_spec()
        with tempfile.TemporaryDirectory() as tmpdir:
            target_path = Path(tmpdir) / 'preview_long_target.txt'
            target_path.write_text('abcdefg ' * 2000, encoding='utf-8')
            core._PREVIEW_BUNDLE_CACHE.clear()
            args = {
                'width': '160',
                'height': '220',
                'font_size': '26',
                'ruby_size': '12',
                'line_spacing': '44',
                'margin_t': '12',
                'margin_b': '14',
                'margin_r': '12',
                'margin_l': '12',
                'dither': 'false',
                'threshold': '128',
                'night_mode': 'false',
                'kinsoku_mode': 'standard',
                'output_format': 'xtc',
                'mode': 'text',
                'font_file': font_value,
                'target_path': str(target_path),
                'max_pages': 1,
            }

            bundle = core.generate_preview_bundle(args)

        self.assertEqual(bundle['page_count'], 1)
        self.assertEqual(len(bundle['pages']), 1)
        self.assertTrue(bundle['truncated'])
        self.assertEqual(bundle['source_count'], 1)

    def test_preview_directory_stops_after_requested_source_pages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_dir = Path(tmpdir) / 'preview_image_dir_limit'
            image_dir.mkdir()
            for index in range(3):
                img = Image.new('L', (12, 12), 40 + index)
                img.save(image_dir / f'page_{index + 1}.png')
            args = core.ConversionArgs(
                width=24,
                height=24,
                font_size=10,
                ruby_size=5,
                line_spacing=14,
                margin_t=1,
                margin_b=1,
                margin_r=1,
                margin_l=1,
                dither=False,
                night_mode=False,
                threshold=128,
                kinsoku_mode='standard',
                output_format='xtc',
            )

            pages, truncated = core._render_preview_pages_from_target(image_dir, '', args, max_pages=1)

        self.assertEqual(len(pages), 1)
        self.assertTrue(truncated)
        self.assertEqual(pages[0].size, (24, 24))



if __name__ == '__main__':
    unittest.main()
