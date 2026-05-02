import importlib.util
import os
import unittest


PYSIDE6_AVAILABLE = importlib.util.find_spec('PySide6') is not None
PILLOW_AVAILABLE = importlib.util.find_spec('PIL') is not None
QT_QPA_PLATFORM = os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
GUI_STUDIO_SMOKE_AVAILABLE = PYSIDE6_AVAILABLE and PILLOW_AVAILABLE


@unittest.skipUnless(GUI_STUDIO_SMOKE_AVAILABLE, 'PySide6 and Pillow are required for GUI studio smoke tests')
class GuiStudioSmokeOptionalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        import tategakiXTC_gui_studio as studio

        cls.QApplication = QApplication
        cls.studio = studio
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_can_be_constructed_and_closed(self):
        window = self.studio.MainWindow()
        try:
            self.assertIsNotNone(window)
            self.assertEqual(window.windowTitle(), self.studio.APP_NAME)
        finally:
            window.close()

    def test_conversion_worker_has_expected_signals(self):
        worker = self.studio.ConversionWorker({'target': '', 'font_file': '', 'font_size': 32, 'ruby_size': 16, 'line_spacing': 12, 'margin_t': 12, 'margin_b': 12, 'margin_r': 12, 'margin_l': 12, 'dither': False, 'threshold': 160, 'night_mode': False, 'kinsoku_mode': 'basic', 'output_format': 'xtc', 'output_conflict': 'error', 'open_folder': False, 'width': 600, 'height': 800})
        self.assertTrue(hasattr(worker, 'finished'))
        self.assertTrue(hasattr(worker, 'error'))
        self.assertTrue(hasattr(worker, 'progress'))


if __name__ == '__main__':
    unittest.main()
