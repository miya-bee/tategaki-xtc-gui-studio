import unittest
from unittest import mock

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class TextCodeFontLazyRegressionTests(unittest.TestCase):
    def test_render_text_blocks_to_images_does_not_resolve_code_font_without_code_runs(self):
        args = core.ConversionArgs(width=180, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        blocks = [{'kind': 'paragraph', 'runs': [{'text': '本文だけ'}], 'blank_before': 1}]
        with mock.patch.object(core, 'get_code_font_value', side_effect=AssertionError('should stay lazy')):
            pages = core._render_text_blocks_to_images(blocks, str(FONT_PATH), args)
        self.assertTrue(pages)

    def test_render_text_blocks_to_images_resolves_code_font_when_code_run_exists(self):
        args = core.ConversionArgs(width=180, height=180, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
        blocks = [{'kind': 'paragraph', 'runs': [{'text': 'code', 'code': True}], 'blank_before': 1}]
        with mock.patch.object(core, 'get_code_font_value', wraps=core.get_code_font_value) as mocked:
            pages = core._render_text_blocks_to_images(blocks, str(FONT_PATH), args)
        self.assertTrue(pages)
        self.assertTrue(mocked.called)


if __name__ == '__main__':
    unittest.main()
