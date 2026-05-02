from unittest import TestCase
from unittest.mock import patch

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class VerticalRendererUnificationTests(TestCase):
    def test_text_blocks_render_through_shared_vertical_renderer(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        blocks = [
            {
                'kind': 'paragraph',
                'indent': False,
                'runs': [{'text': '共有描画テスト'}],
                'blank_before': 1,
            }
        ]
        created = []
        original = core._VerticalPageRenderer

        class TrackingRenderer(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.draw_runs_called = False
                self.text_run_called = False
                self.direct_plain_called = False
                created.append(self)

            def draw_text_run(self, *args, **kwargs):
                self.text_run_called = True
                return super().draw_text_run(*args, **kwargs)

            def _draw_text_run_plain(self, *args, **kwargs):
                self.direct_plain_called = True
                return super()._draw_text_run_plain(*args, **kwargs)

            def draw_runs(self, *args, **kwargs):
                self.draw_runs_called = True
                return super().draw_runs(*args, **kwargs)

        with patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            pages = core._render_text_blocks_to_images(blocks, FONT_PATH, args)

        self.assertEqual(len(pages), 1)
        self.assertTrue(created)
        self.assertTrue(created[0].draw_runs_called)
        self.assertTrue(created[0].text_run_called or created[0].direct_plain_called)

    def test_epub_chapter_render_uses_shared_vertical_renderer(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        html = '<html><body><pre><code>共有章描画テスト</code></pre></body></html>'
        created = []
        original = core._VerticalPageRenderer

        class TrackingRenderer(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.draw_runs_called = False
                self.text_run_called = False
                self.direct_plain_called = False
                self.epub_code_flag_seen = False
                created.append(self)

            def draw_text_run(self, *args, **kwargs):
                self.text_run_called = True
                return super().draw_text_run(*args, **kwargs)

            def _draw_text_run_plain(self, *args, **kwargs):
                self.direct_plain_called = True
                return super()._draw_text_run_plain(*args, **kwargs)

            def draw_runs(self, runs, *args, **kwargs):
                self.draw_runs_called = True
                self.epub_code_flag_seen = self.epub_code_flag_seen or any(bool((run or {}).get('code')) for run in (runs or []))
                return super().draw_runs(runs, *args, **kwargs)

        with patch.object(core, '_VerticalPageRenderer', TrackingRenderer):
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter.xhtml',
                args,
                font,
                ruby_font,
                bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
                image_map={},
                image_basename_map={},
                css_rules=[],
            )

        self.assertEqual(len(pages), 1)
        self.assertTrue(created)
        self.assertTrue(created[0].draw_runs_called)
        self.assertTrue(created[0].text_run_called or created[0].direct_plain_called)
        self.assertTrue(created[0].epub_code_flag_seen)
