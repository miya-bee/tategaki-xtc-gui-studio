import unittest
from unittest.mock import patch

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class PendingIndentRegressionTests(unittest.TestCase):
    def _load_renderer(self, args):
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        return core._VerticalPageRenderer(args, font, ruby_font)

    def test_apply_pending_paragraph_indent_does_not_double_advance_column(self):
        args = core.ConversionArgs(width=120, height=120, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        renderer = self._load_renderer(args)
        renderer.curr_y = args.height - args.margin_b - args.font_size + 1
        renderer.set_pending_paragraph_indent(True)

        with patch.object(renderer, '_advance_column_with_indent_step', wraps=renderer._advance_column_with_indent_step) as mocked_advance:
            applied = renderer.apply_pending_paragraph_indent(1)

        self.assertTrue(applied)
        self.assertEqual(mocked_advance.call_count, 1)
        self.assertFalse(renderer.has_pending_paragraph_indent)

    def test_epub_render_uses_public_pending_indent_property(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        html = '<html><body><p>本文</p><br/>続き</body></html>'
        created = []
        original = core._VerticalPageRenderer

        class TrackingRenderer(original):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.property_reads = 0
                created.append(self)

            @property
            def has_pending_paragraph_indent(self):
                self.property_reads += 1
                return super().has_pending_paragraph_indent

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
                primary_font_value=str(FONT_PATH),
            )

        self.assertEqual(len(pages), 1)
        self.assertTrue(created)
        self.assertGreater(created[0].property_reads, 0)

    def test_epub_code_font_selection_uses_primary_font_value_when_not_preresolved(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        html = '<html><body><pre><code>code</code></pre></body></html>'

        with patch.object(core, 'get_code_font_value', wraps=core.get_code_font_value) as mocked_get_code_font_value:
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
                primary_font_value='C:/dummy/fonts/source.ttf',
            )

        self.assertEqual(len(pages), 1)
        self.assertTrue(mocked_get_code_font_value.called)
        self.assertEqual(mocked_get_code_font_value.call_args[0][0], 'C:/dummy/fonts/source.ttf')

    def test_epub_code_font_selection_skips_internal_resolution_when_preresolved(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font = core.load_truetype_font(FONT_PATH, args.font_size)
        ruby_font = core.load_truetype_font(FONT_PATH, args.ruby_size)
        html = '<html><body><pre><code>code</code></pre></body></html>'

        with patch.object(core, 'get_code_font_value', side_effect=AssertionError('should not resolve internally')):
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
                primary_font_value='C:/dummy/fonts/source.ttf',
                code_font_value=str(FONT_PATH),
            )

        self.assertEqual(len(pages), 1)


if __name__ == '__main__':
    unittest.main()
