from __future__ import annotations

import unittest

from tests.studio_import_helper import load_studio_module


class GuiStartupSmokeRegressionTest(unittest.TestCase):
    def test_main_window_constructs_with_lightweight_qt_stubs(self) -> None:
        studio = load_studio_module(force_reload=True)
        app = studio.QApplication.instance() or studio.QApplication([])
        self.assertIsNotNone(app)

        window = studio.MainWindow()
        expected_titles = {
            f'縦書きXTC Studio Public {studio.APP_VERSION}',
            f'TategakiXTC GUI Studio Public {studio.APP_VERSION}',
        }
        self.assertEqual(window.windowTitle(), window._app_window_title())
        self.assertIn(window.windowTitle(), expected_titles)
        self.assertTrue(hasattr(window, 'profile_hint'))


if __name__ == '__main__':
    unittest.main()
