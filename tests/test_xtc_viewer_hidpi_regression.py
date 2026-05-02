from __future__ import annotations

import unittest
from pathlib import Path


class XtcViewerHiDpiRegressionTests(unittest.TestCase):
    def test_paint_event_uses_hidpi_scaling_and_smooth_pixmap_transform(self) -> None:
        source = Path('tategakiXTC_gui_studio_widgets.py').read_text(encoding='utf-8')
        self.assertIn('painter.setRenderHint(QPainter.SmoothPixmapTransform)', source)
        self.assertIn('devicePixelRatioF', source)
        self.assertIn('setDevicePixelRatio', source)
        self.assertIn('target_phys = QSize(', source)


if __name__ == '__main__':
    unittest.main()
