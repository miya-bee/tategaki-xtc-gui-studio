import unittest
from unittest.mock import patch

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class _NoPathFont:
    def __init__(self, inner):
        self._inner = inner

    def __getattr__(self, name):
        if name == 'path':
            raise AssertionError('font.path should not be accessed')
        return getattr(self._inner, name)


class EpubCodeFontPathlessTests(unittest.TestCase):
    def _wrapped_fonts(self, args):
        font = _NoPathFont(core.load_truetype_font(FONT_PATH, args.font_size))
        ruby_font = _NoPathFont(core.load_truetype_font(FONT_PATH, args.ruby_size))
        return font, ruby_font

    def test_preresolved_code_font_renders_without_font_path_attribute(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._wrapped_fonts(args)
        html = '<html><body><pre><code>code block</code></pre></body></html>'

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

    def test_primary_font_value_resolution_does_not_require_font_path_attribute(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        font, ruby_font = self._wrapped_fonts(args)
        html = '<html><body><pre><code>code block</code></pre></body></html>'

        with patch.object(core, 'get_code_font_value', return_value=str(FONT_PATH)) as mocked_resolve:
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
        mocked_resolve.assert_called_once_with('C:/dummy/fonts/source.ttf')


if __name__ == '__main__':
    unittest.main()
