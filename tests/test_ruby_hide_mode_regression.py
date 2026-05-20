import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
import tategakiXTC_gui_core_renderer as renderer
import tategakiXTC_worker_logic as worker_logic
from tests.font_test_helper import resolve_test_font_spec


class RubyHideModeRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font_value = resolve_test_font_spec()

    def _args(self, *, ruby_hide=False):
        return core.ConversionArgs(
            width=160,
            height=220,
            font_size=26,
            ruby_size=12,
            ruby_hide=ruby_hide,
            line_spacing=44,
            margin_t=12,
            margin_b=14,
            margin_r=12,
            margin_l=12,
            output_format='xtc',
        )

    def test_worker_build_conversion_args_carries_ruby_hide_flag(self):
        args = worker_logic.build_conversion_args({'ruby_hide': 'on'})
        self.assertTrue(args.ruby_hide)
        args = worker_logic.build_conversion_args({'ruby_hide': 'off'})
        self.assertFalse(args.ruby_hide)

    def test_preview_cache_key_includes_halfwidth_digit_position_mode(self):
        base = {
            'mode': 'text',
            'target_path': '',
            'font_file': self.font_value,
            'font_size': 26,
            'ruby_size': 12,
            'width': 160,
            'height': 220,
        }
        standard_key = core._preview_bundle_cache_key({**base, 'halfwidth_digit_position_mode': 'standard'}, preview_sources=[])
        down_key = core._preview_bundle_cache_key({**base, 'halfwidth_digit_position_mode': 'down_strong'}, preview_sources=[])
        self.assertNotEqual(standard_key, down_key)


    def test_preview_cache_key_includes_tatechuyoko_digit_mode(self):
        base = {
            'mode': 'text',
            'target_path': '',
            'font_file': self.font_value,
            'font_size': 26,
            'ruby_size': 12,
            'width': 160,
            'height': 220,
        }
        two_key = core._preview_bundle_cache_key({**base, 'tatechuyoko_digit_mode': '2'}, preview_sources=[])
        four_key = core._preview_bundle_cache_key({**base, 'tatechuyoko_digit_mode': '4'}, preview_sources=[])
        self.assertNotEqual(two_key, four_key)

    def test_preview_cache_key_includes_ruby_hide_flag(self):
        base = {
            'mode': 'text',
            'target_path': '',
            'font_file': self.font_value,
            'font_size': 26,
            'ruby_size': 12,
            'width': 160,
            'height': 220,
        }
        key_with_ruby = core._preview_bundle_cache_key({**base, 'ruby_hide': False}, preview_sources=[])
        key_without_ruby = core._preview_bundle_cache_key({**base, 'ruby_hide': True}, preview_sources=[])
        self.assertNotEqual(key_with_ruby, key_without_ruby)


    def test_ruby_hide_initial_column_uses_ruby_lane_space(self):
        args_with_ruby = self._args(ruby_hide=False)
        args_without_ruby = self._args(ruby_hide=True)

        x_with_ruby = renderer._initial_text_column_x(args_with_ruby)
        x_without_ruby = renderer._initial_text_column_x(args_without_ruby)

        self.assertEqual(x_without_ruby, args_without_ruby.width - args_without_ruby.font_size - args_without_ruby.margin_r)
        self.assertEqual(x_without_ruby - x_with_ruby, args_with_ruby.ruby_size + 4)

    def test_text_render_clears_ruby_metadata_only_when_enabled(self):
        blocks = [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '吾輩', 'ruby': 'わがはい', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
                ],
            }
        ]
        captured = []

        def fake_draw_runs(_renderer, runs, **_kwargs):
            captured.append([dict(run) for run in runs])

        with mock.patch.object(core._VerticalPageRenderer, 'draw_runs', new=fake_draw_runs):
            core._render_text_blocks_to_page_entries(blocks, self.font_value, self._args(ruby_hide=False))
            core._render_text_blocks_to_page_entries(blocks, self.font_value, self._args(ruby_hide=True))

        self.assertEqual(captured[0][0]['ruby'], 'わがはい')
        self.assertEqual(captured[0][0]['text'], '吾輩')
        self.assertEqual(captured[1][0]['ruby'], '')
        self.assertEqual(captured[1][0]['text'], '吾輩')

    def test_epub_ruby_node_keeps_base_text_when_ruby_hide_enabled(self):
        try:
            core._require_bs4_beautifulsoup()
        except Exception:
            self.skipTest('bs4 unavailable')

        html = '<html><body><p><ruby>吾輩<rt>わがはい</rt></ruby></p></body></html>'
        font = core.load_truetype_font(self.font_value, 26)
        ruby_font = core.load_truetype_font(self.font_value, 12)
        captured = []

        def fake_draw_runs(_renderer, runs, **_kwargs):
            captured.append([dict(run) for run in runs])

        with mock.patch.object(core._VerticalPageRenderer, 'draw_runs', new=fake_draw_runs):
            core._render_epub_chapter_pages_from_html(
                html,
                'chapter.xhtml',
                self._args(ruby_hide=False),
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {},
                {},
                [],
            )
            core._render_epub_chapter_pages_from_html(
                html,
                'chapter.xhtml',
                self._args(ruby_hide=True),
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {},
                {},
                [],
            )

        ruby_runs = [run for call in captured for run in call if run.get('text') == '吾輩']
        self.assertGreaterEqual(len(ruby_runs), 2)
        self.assertEqual(ruby_runs[0]['ruby'], 'わがはい')
        self.assertEqual(ruby_runs[-1]['ruby'], '')
        self.assertEqual(ruby_runs[-1]['text'], '吾輩')

    def test_runs_without_ruby_preserves_base_and_does_not_mutate_original(self):
        runs = [
            {'text': '吾輩', 'ruby': 'わがはい', 'bold': True, 'italic': False, 'emphasis': 'dot', 'side_line': '', 'code': False},
            {'text': 'は猫である', 'ruby': '', 'bold': False, 'italic': True, 'emphasis': '', 'side_line': 'left', 'code': False},
        ]

        cleaned = renderer._runs_without_ruby(runs)

        self.assertEqual([run['text'] for run in cleaned], ['吾輩', 'は猫である'])
        self.assertEqual([run['ruby'] for run in cleaned], ['', ''])
        self.assertTrue(cleaned[0]['bold'])
        self.assertEqual(cleaned[0]['emphasis'], 'dot')
        self.assertTrue(cleaned[1]['italic'])
        self.assertEqual(cleaned[1]['side_line'], 'left')
        self.assertEqual(runs[0]['ruby'], 'わがはい')
        self.assertIsNot(cleaned[0], runs[0])

    def test_xtc_and_xtch_save_pipeline_receives_ruby_hide_args(self):
        blocks = [
            {
                'kind': 'paragraph',
                'runs': [
                    {'text': '吾輩', 'ruby': 'わがはい', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
                ],
            }
        ]
        seen = []

        def fake_render_entries(_blocks, _font_path, args, **_kwargs):
            seen.append((bool(args.ruby_hide), args.output_format))
            return [core._make_page_entry(Image.new('L', (args.width, args.height), 255), page_args=args, label='本文ページ')]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with mock.patch.object(core, '_render_text_blocks_to_page_entries', side_effect=fake_render_entries):
                xtc_out = core._render_text_blocks_to_xtc(
                    blocks,
                    tmp / 'sample.txt',
                    self.font_value,
                    self._args(ruby_hide=True),
                    output_path=tmp / 'sample.xtc',
                )
                xtch_args = self._args(ruby_hide=True)
                xtch_args.output_format = 'xtch'
                xtch_out = core._render_text_blocks_to_xtc(
                    blocks,
                    tmp / 'sample.txt',
                    self.font_value,
                    xtch_args,
                    output_path=tmp / 'sample.xtch',
                )

            self.assertEqual(xtc_out.read_bytes()[:4], b'XTC\x00')
            self.assertEqual(xtch_out.read_bytes()[:4], b'XTCH')

        self.assertEqual(seen, [(True, 'xtc'), (True, 'xtch')])


if __name__ == '__main__':
    unittest.main()
