from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import tategakiXTC_gui_core as core
from tests.image_golden_cases import FONT_PATH


class TextRenderSyncRegressionTests(unittest.TestCase):
    def test_process_text_file_resolves_page_renderer_after_split_imports(self) -> None:
        """Regression guard for split-module startup order in real TXT conversion."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'smoke_input.txt'
            output = root / 'smoke_output.xtc'
            source.write_text('これはテキスト変換の同期テストです。\n', encoding='utf-8')
            args = core.ConversionArgs(width=600, height=800, output_format='xtc')
            result = core.process_text_file(source, FONT_PATH, args, output_path=output)
            self.assertEqual(Path(result), output)
            self.assertTrue(output.exists())
            self.assertGreater(output.stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
