import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class EpubCodeFontPreresolvedTests(unittest.TestCase):
    def _document_stub(self, html):
        doc = types.SimpleNamespace(get_content=lambda: html, file_name='text/chapter.xhtml')
        return types.SimpleNamespace(
            docs=[doc],
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
            image_map={},
            image_basename_map={},
            css_rules=[],
        )

    def test_render_preview_page_from_target_keeps_code_font_lazy(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        document = self._document_stub('<html><body><p>preview</p></body></html>')
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'dummy_preview.epub'
            epub_path.write_bytes(b'placeholder')
            with mock.patch.object(core, 'load_epub_input_document', return_value=document):
                with mock.patch.object(core, '_render_epub_chapter_pages_from_html', return_value=[{'image': core.Image.new('L', (args.width, args.height), 255)}]) as mocked_render:
                    core._render_preview_page_from_target(epub_path, str(FONT_PATH), args)
        kwargs = mocked_render.call_args.kwargs
        self.assertEqual(kwargs['primary_font_value'], str(FONT_PATH))
        self.assertNotIn('code_font_value', kwargs)

    def test_process_epub_keeps_code_font_lazy(self):
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        document = self._document_stub('<html><body><p>process</p></body></html>')
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / 'dummy.epub'
            out_path = Path(td) / 'dummy.xtc'
            with mock.patch.object(core, 'load_epub_input_document', return_value=document):
                with mock.patch.object(core, '_render_epub_chapter_pages_from_html', return_value=[{'image': core.Image.new('L', (args.width, args.height), 255), 'label': '本文ページ', 'page_args': args}]) as mocked_render:
                    with mock.patch.object(core, '_write_page_entries_to_xtc', return_value=out_path):
                        result = core.process_epub(epub_path, str(FONT_PATH), args, output_path=out_path)
        self.assertEqual(result, out_path)
        kwargs = mocked_render.call_args.kwargs
        self.assertEqual(kwargs['primary_font_value'], str(FONT_PATH))
        self.assertNotIn('code_font_value', kwargs)


if __name__ == '__main__':
    unittest.main()
