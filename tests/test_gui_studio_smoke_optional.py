import importlib.util
import os
import unittest


RUN_REAL_QT_SMOKE = os.environ.get('RUN_REAL_QT_SMOKE') == '1'
PYSIDE6_AVAILABLE = importlib.util.find_spec('PySide6') is not None
PILLOW_AVAILABLE = importlib.util.find_spec('PIL') is not None
QT_QPA_PLATFORM = os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
GUI_STUDIO_SMOKE_AVAILABLE = RUN_REAL_QT_SMOKE and PYSIDE6_AVAILABLE and PILLOW_AVAILABLE


@unittest.skipUnless(
    GUI_STUDIO_SMOKE_AVAILABLE,
    'real PySide6 smoke tests are opt-in only; set RUN_REAL_QT_SMOKE=1',
)
class GuiStudioSmokeOptionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.studio_import_helper import remove_pyside6_test_stubs_for_real_qt

        remove_pyside6_test_stubs_for_real_qt()
        from PySide6.QtWidgets import QApplication
        import tategakiXTC_gui_studio as studio

        cls.QApplication = QApplication
        cls.studio = studio
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_can_be_constructed_and_closed(self):
        window = self.studio.MainWindow()
        try:
            self.assertIsNotNone(window)
            self.assertEqual(window.windowTitle(), window._app_window_title())
        finally:
            window.close()

    def test_conversion_worker_has_expected_signals(self):
        worker = self.studio.ConversionWorker({'target': '', 'font_file': '', 'font_size': 32, 'ruby_size': 16, 'line_spacing': 12, 'margin_t': 12, 'margin_b': 12, 'margin_r': 12, 'margin_l': 12, 'dither': False, 'threshold': 160, 'night_mode': False, 'kinsoku_mode': 'basic', 'output_format': 'xtc', 'output_conflict': 'error', 'open_folder': False, 'width': 600, 'height': 800})
        self.assertTrue(hasattr(worker, 'finished'))
        self.assertTrue(hasattr(worker, 'error'))
        self.assertTrue(hasattr(worker, 'progress'))


if __name__ == '__main__':
    unittest.main()
