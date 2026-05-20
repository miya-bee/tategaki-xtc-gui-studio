from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase, mock

import tategakiXTC_gui_core as core
import tategakiXTC_gui_core_epub as epub_core


class _DummyEpubItem:
    file_name = '0001.xhtml'

    def get_content(self) -> bytes:
        return b'<html><body>dummy</body></html>'


class CancellationPropagationRegressionTests(TestCase):
    def test_epub_chapter_render_cancellation_is_not_wrapped_as_render_error(self) -> None:
        doc = SimpleNamespace(
            docs=[_DummyEpubItem()],
            bold_rules=[],
            image_map={},
            image_basename_map={},
            css_rules=[],
        )
        with mock.patch.object(core, 'load_epub_input_document', return_value=doc), \
             mock.patch.object(core, 'load_truetype_font', return_value=object()), \
             mock.patch.object(core, '_render_epub_chapter_pages_from_html', side_effect=core.ConversionCancelled('変換を停止しました。')):
            with self.assertRaises(core.ConversionCancelled):
                epub_core.process_epub('sample.epub', 'dummy.ttf', core.ConversionArgs())
