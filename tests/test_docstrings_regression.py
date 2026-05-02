import inspect
import unittest

import tategakiXTC_gui_core as core


class DocstringRegressionTests(unittest.TestCase):
    def test_key_renderer_methods_have_docstrings(self):
        targets = [
            core._VerticalPageRenderer.add_full_page_image,
            core._VerticalPageRenderer.apply_pending_paragraph_indent,
            core._VerticalPageRenderer.advance_column,
            core._VerticalPageRenderer.ensure_room,
            core._VerticalPageRenderer.insert_paragraph_indent,
            core._VerticalPageRenderer.draw_text_run,
            core._VerticalPageRenderer.draw_runs,
        ]
        for target in targets:
            with self.subTest(target=target.__name__):
                doc = inspect.getdoc(target)
                self.assertIsInstance(doc, str)
                self.assertGreaterEqual(len(doc.splitlines()), 2)

    def test_key_conversion_functions_have_docstrings(self):
        targets = [
            core.generate_preview_base64,
            core.process_archive,
            core.process_epub,
        ]
        for target in targets:
            with self.subTest(target=target.__name__):
                doc = inspect.getdoc(target)
                self.assertIsInstance(doc, str)
                self.assertIn('Args:', doc)
                self.assertIn('Returns:', doc)


if __name__ == '__main__':
    unittest.main()
