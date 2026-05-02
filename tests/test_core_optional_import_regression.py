from __future__ import annotations

import unittest
from pathlib import Path
from typing import Any


class CoreOptionalImportRegressionTest(unittest.TestCase):
    def test_gui_core_keeps_numpy_import_inside_lazy_helper(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = (root / 'tategakiXTC_gui_core.py').read_text(encoding='utf-8')
        helper_source = (root / 'tategakiXTC_numpy_helper.py').read_text(encoding='utf-8')
        helper_pos = source.index('def _get_numpy_module()')
        before_helper = source[:helper_pos]
        helper_body = source[helper_pos: source.index("LOGGER_NAME = 'tategaki_xtc'")]
        shared_helper_body = helper_source[
            helper_source.index('def get_cached_numpy_module('):
            helper_source.index('__all__ = [')
        ]

        self.assertNotIn('import numpy', before_helper)
        self.assertIn('from tategakiXTC_numpy_helper import get_cached_numpy_module', source)
        self.assertIn('get_cached_numpy_module(np, _NUMPY_IMPORT_ATTEMPTED)', helper_body)
        self.assertIn('import numpy as numpy_module', shared_helper_body)
        self.assertIn('_NUMPY_IMPORT_ATTEMPTED = False', source)

    def test_gui_core_keeps_pillow_modules_lazy(self) -> None:
        source = (Path(__file__).resolve().parents[1] / 'tategakiXTC_gui_core.py').read_text(encoding='utf-8')
        lazy_class_pos = source.index('class _LazyPillowModule:')
        before_lazy_class = source[:lazy_class_pos]
        lazy_block = source[lazy_class_pos: source.index('# numpy は XTC / XTCH pack')]

        self.assertNotIn('from PIL import Image\n', before_lazy_class)
        self.assertNotIn('from PIL import Image, ImageDraw, ImageFont, ImageOps', before_lazy_class)
        self.assertNotIn('from PIL import ImageDraw', before_lazy_class)
        self.assertNotIn('from PIL import ImageFont', before_lazy_class)
        self.assertNotIn('from PIL import ImageOps', before_lazy_class)
        self.assertIn("if TYPE_CHECKING:", lazy_block)
        self.assertIn("Image = _LazyPillowModule('Image')", lazy_block)
        self.assertIn("ImageDraw = _LazyPillowModule('ImageDraw')", lazy_block)
        self.assertIn("ImageFont = _LazyPillowModule('ImageFont')", lazy_block)
        self.assertIn("ImageOps = _LazyPillowModule('ImageOps')", lazy_block)
        self.assertIn("importlib.import_module(f'PIL.{self._module_name}')", lazy_block)


    def test_gui_core_lazy_pillow_allows_annotation_attrs_without_pillow(self) -> None:
        import tategakiXTC_gui_core as core

        missing_module = core._LazyPillowModule('__missing_for_type_hint_test__')

        self.assertIs(missing_module.Image, Any)
        self.assertIs(missing_module.ImageDraw, Any)
        self.assertIs(missing_module.FreeTypeFont, Any)
        with self.assertRaises(ModuleNotFoundError):
            missing_module.open



    def test_gui_studio_keeps_numpy_and_pillow_lazy_for_import_hygiene(self) -> None:
        studio_source = (Path(__file__).resolve().parents[1] / 'tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        root = Path(__file__).resolve().parents[1]
        xtc_io_source = (root / 'tategakiXTC_gui_studio_xtc_io.py').read_text(encoding='utf-8')
        numpy_helper_source = (root / 'tategakiXTC_numpy_helper.py').read_text(encoding='utf-8')
        studio_startup_block = studio_source[:studio_source.index('_STARTUP_DEPENDENCIES = [')]
        xtc_io_header = xtc_io_source[:xtc_io_source.index('class _LazyPillowModule:')]
        pillow_block = xtc_io_source[
            xtc_io_source.index('class _LazyPillowModule:'):
            xtc_io_source.index('@dataclass')
        ]
        xtch_block = xtc_io_source[
            xtc_io_source.index('_XTCH_SHADE_MAP ='):
            xtc_io_source.index('def xtg_blob_to_qimage')
        ]

        self.assertNotIn('import numpy as np', studio_startup_block)
        self.assertNotIn('import numpy as np', xtc_io_header)
        self.assertIn('def _get_numpy_module()', xtc_io_source)
        self.assertIn('from tategakiXTC_numpy_helper import get_cached_numpy_module', xtc_io_source)
        self.assertIn('get_cached_numpy_module(np, _NUMPY_IMPORT_ATTEMPTED)', xtc_io_source)
        self.assertIn('import numpy as numpy_module', numpy_helper_source)
        self.assertNotIn('from PIL import Image\n', xtc_io_header)
        self.assertIn("Image = _LazyPillowModule('Image')", pillow_block)
        self.assertIn('if TYPE_CHECKING:', pillow_block)
        self.assertIn('def _get_xtch_shade_lut(', xtch_block)
        self.assertIn('np_module.array(_XTCH_SHADE_MAP', xtch_block)


    def test_gui_studio_smoke_skips_cleanly_without_pillow(self) -> None:
        source = (Path(__file__).resolve().parents[1] / 'tests' / 'test_gui_studio_smoke_optional.py').read_text(encoding='utf-8')
        pre_class = source[:source.index('class GuiStudioSmokeOptionalTests')]

        self.assertIn("PYSIDE6_AVAILABLE = importlib.util.find_spec('PySide6') is not None", pre_class)
        self.assertIn("PILLOW_AVAILABLE = importlib.util.find_spec('PIL') is not None", pre_class)
        self.assertIn("QT_QPA_PLATFORM = os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')", pre_class)
        self.assertLess(pre_class.index("os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')"), pre_class.index('GUI_STUDIO_SMOKE_AVAILABLE'))
        self.assertIn('GUI_STUDIO_SMOKE_AVAILABLE = PYSIDE6_AVAILABLE and PILLOW_AVAILABLE', pre_class)
        self.assertIn("@unittest.skipUnless(GUI_STUDIO_SMOKE_AVAILABLE, 'PySide6 and Pillow are required for GUI studio smoke tests')", pre_class)
        self.assertNotIn("@unittest.skipUnless(PYSIDE6_AVAILABLE, 'PySide6 is not installed in this environment')", pre_class)


    def test_optional_tqdm_is_disabled_by_default_for_non_interactive_runs(self) -> None:
        source = (Path(__file__).resolve().parents[1] / 'tategakiXTC_gui_core.py').read_text(encoding='utf-8')
        helper_pos = source.index('def _iter_with_optional_tqdm(')
        helper_body = source[helper_pos: source.index('def _is_module_available', helper_pos)]

        self.assertIn('sys.stderr.isatty()', helper_body)
        self.assertIn('TATEGAKI_XTC_FORCE_TQDM', helper_body)
        self.assertLess(helper_body.index('sys.stderr.isatty()'), helper_body.index('from tqdm import tqdm as tqdm_func'))

