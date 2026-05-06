from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tategakiXTC_folder_batch_plan import build_folder_batch_plan
from tategakiXTC_folder_batch_worker_bridge import (
    _call_with_supported_arity,
    build_worker_settings_for_folder_batch_item,
    can_collect_worker_settings_from_mainwindow,
    collect_worker_settings_from_mainwindow,
    make_mainwindow_worker_bridge_converter,
    make_worker_bridge_converter,
)


class DummyWorker:
    calls = []

    def __init__(self, settings):
        self.settings = dict(settings)

    @staticmethod
    def _build_args(settings):
        return {'format': settings.get('output_format')}

    def _process_target(self, source_path, font_value, args, output_path, progress_cb=None):
        self.__class__.calls.append((Path(source_path), font_value, args, Path(output_path), dict(self.settings)))
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(f'converted: {Path(source_path).name}\n', encoding='utf-8')
        if progress_cb is not None:
            progress_cb(1, 1, 'done')
        return Path(output_path)


class MainWindowWithSettings:
    def __init__(self):
        self.calls = 0

    def _folder_batch_worker_settings(self):
        self.calls += 1
        return {
            'font_file': 'font.ttf',
            'output_format': 'xtc',
            'font_size': 26,
        }


class MainWindowWithSourceAwareSettings:
    def _build_worker_settings(self, source_path, output_path, item):
        return {
            'font_file': 'font.ttf',
            'output_format': output_path.suffix.lstrip('.'),
            'source_name': Path(source_path).name,
        }


class MainWindowWithItemAwareSettings:
    def _build_worker_settings(self, source_path, output_path, item):
        return {
            'font_file': 'font.ttf',
            'output_format': output_path.suffix.lstrip('.'),
            'relative_source': str(item.relative_source_path),
            'will_convert': item.will_convert,
        }


class FolderBatchWorkerBridgeTests(unittest.TestCase):
    def setUp(self):
        DummyWorker.calls = []

    @staticmethod
    def _minimal_real_worker_settings() -> dict[str, object]:
        from tests.font_test_helper import resolve_test_font_spec

        return {
            'font_file': resolve_test_font_spec(),
            'output_format': 'xtc',
            'width': 160,
            'height': 220,
            'font_size': 26,
            'ruby_size': 12,
            'line_spacing': 44,
            'margin_t': 12,
            'margin_b': 14,
            'margin_r': 12,
            'margin_l': 12,
            'dither': False,
            'threshold': 128,
            'night_mode': False,
            'kinsoku_mode': 'standard',
            'punctuation_position_mode': 'standard',
            'ichi_position_mode': 'standard',
            'lower_closing_bracket_position_mode': 'standard',
            'wave_dash_drawing_mode': 'rotate',
            'wave_dash_position_mode': 'standard',
        }

    def test_build_worker_settings_for_folder_batch_item_overrides_per_item_fields(self):
        settings = build_worker_settings_for_folder_batch_item(
            {'target': 'old.txt', 'output_format': 'xtc', 'open_folder': True},
            Path('src/sample.txt'),
            Path('out/sample.xtch'),
        )
        self.assertEqual(settings['target'], str(Path('src/sample.txt')))
        self.assertEqual(settings['output_name'], 'sample')
        self.assertEqual(settings['output_format'], 'xtch')
        self.assertEqual(settings['output_conflict'], 'overwrite')
        self.assertFalse(settings['open_folder'])

    def test_collect_worker_settings_from_mapping(self):
        settings = collect_worker_settings_from_mainwindow(
            {'font_file': 'font.ttf'},
            Path('a.txt'),
            Path('a.xtc'),
            object(),
        )
        self.assertEqual(settings, {'font_file': 'font.ttf'})

    def test_collect_worker_settings_from_mainwindow_getter(self):
        window = MainWindowWithSettings()
        settings = collect_worker_settings_from_mainwindow(
            window,
            Path('a.txt'),
            Path('a.xtc'),
            object(),
        )
        self.assertEqual(settings['font_file'], 'font.ttf')
        self.assertEqual(window.calls, 1)
        self.assertTrue(can_collect_worker_settings_from_mainwindow(window))

    def test_call_with_supported_arity_does_not_swallow_internal_type_error(self):
        calls: list[tuple[object, object, object]] = []

        def callback(source_path: object, output_path: object, item: object) -> object:
            calls.append((source_path, output_path, item))
            raise TypeError('internal callback type error')

        with self.assertRaisesRegex(TypeError, 'internal callback type error'):
            _call_with_supported_arity(callback, Path('a.txt'), Path('a.xtc'), object())

        self.assertEqual(len(calls), 1)

    def test_call_with_supported_arity_falls_back_by_signature_without_calling_mismatches(self):
        calls: list[tuple[object, object]] = []

        def callback(source_path: object, output_path: object) -> dict[str, object]:
            calls.append((source_path, output_path))
            return {'font_file': 'font.ttf'}

        result = _call_with_supported_arity(callback, Path('a.txt'), Path('a.xtc'), object())

        self.assertEqual(result, {'font_file': 'font.ttf'})
        self.assertEqual(calls, [(Path('a.txt'), Path('a.xtc'))])

    def test_make_worker_bridge_converter_runs_fake_worker_with_exact_output_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / '入力' / 'sample.txt'
            source.parent.mkdir()
            source.write_text('hello', encoding='utf-8')
            output = root / '出力' / 'nested' / 'sample.xtc'
            plan = build_folder_batch_plan(
                input_root=source.parent,
                output_root=output.parent,
                output_format='xtc',
                include_subfolders=False,
                preserve_structure=True,
                existing_policy='overwrite',
                supported_suffixes=['.txt'],
            )
            item = next(item for item in plan.items if item.will_convert)
            converter = make_worker_bridge_converter(
                lambda src, out, plan_item: {'font_file': 'font.ttf', 'output_format': 'xtc'},
                worker_cls=DummyWorker,
            )
            saved = converter(source, output, item)
            self.assertEqual(Path(saved), output)
            self.assertEqual(output.read_text(encoding='utf-8'), 'converted: sample.txt\n')
            self.assertEqual(DummyWorker.calls[0][3], output)
            self.assertEqual(DummyWorker.calls[0][4]['target'], str(source))

    def test_make_mainwindow_worker_bridge_converter_uses_mainwindow_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'book.md'
            source.write_text('# title', encoding='utf-8')
            output = root / 'out' / 'book.xtch'
            plan = build_folder_batch_plan(
                input_root=root,
                output_root=output.parent,
                output_format='xtch',
                supported_suffixes=['.md'],
                existing_policy='overwrite',
            )
            converter = make_mainwindow_worker_bridge_converter(
                MainWindowWithSourceAwareSettings(),
                worker_cls=DummyWorker,
            )
            converter(source, output, next(item for item in plan.items if item.will_convert))
            self.assertEqual(DummyWorker.calls[0][4]['output_format'], 'xtch')
            self.assertEqual(DummyWorker.calls[0][4]['source_name'], 'book.md')

    def test_make_mainwindow_worker_bridge_converter_eager_validation_uses_plan_item_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'nested' / 'book.txt'
            source.parent.mkdir()
            source.write_text('hello', encoding='utf-8')
            output = root / 'out' / 'book.xtc'
            plan = build_folder_batch_plan(
                input_root=root,
                output_root=output.parent,
                output_format='xtc',
                existing_policy='overwrite',
            )
            item = next(item for item in plan.items if item.will_convert)
            converter = make_mainwindow_worker_bridge_converter(
                MainWindowWithItemAwareSettings(),
                worker_cls=DummyWorker,
            )

            converter(source, output, item)

            self.assertEqual(DummyWorker.calls[0][4]['relative_source'], str(item.relative_source_path))
            self.assertTrue(DummyWorker.calls[0][4]['will_convert'])

    def test_worker_bridge_accepts_epub_and_common_image_folder_batch_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            for name in ('book.epub', 'cover.png', 'photo.jpg', 'scan.jpeg', 'panel.webp'):
                (root / name).write_bytes(b'x')
            plan = build_folder_batch_plan(root, out, existing_policy='overwrite')
            converter = make_worker_bridge_converter(
                lambda src, dst, plan_item: {'font_file': 'font.ttf', 'output_format': 'xtc'},
                worker_cls=DummyWorker,
            )
            for item in plan.items:
                self.assertTrue(item.will_convert)
                assert item.output_path is not None
                converter(item.source_path, item.output_path, item)

            self.assertEqual(len(DummyWorker.calls), 5)
            self.assertEqual(
                {call[0].suffix.lower() for call in DummyWorker.calls},
                {'.epub', '.png', '.jpg', '.jpeg', '.webp'},
            )
            for item in plan.items:
                assert item.output_path is not None
                self.assertTrue(item.output_path.exists())
                self.assertEqual(item.output_path.suffix, '.xtc')

    def test_worker_bridge_real_worker_converts_png_to_planned_output_path(self):
        from PIL import Image
        from tests import studio_import_helper

        studio_import_helper.load_studio_module(force_reload=True)
        from tategakiXTC_gui_studio_worker import ConversionWorker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            source = root / 'images' / 'cover.png'
            source.parent.mkdir(parents=True)
            Image.new('RGB', (32, 40), (120, 180, 220)).save(source)
            plan = build_folder_batch_plan(root, out, existing_policy='overwrite')
            item = next(item for item in plan.items if item.will_convert)
            converter = make_worker_bridge_converter(
                lambda src, dst, plan_item: self._minimal_real_worker_settings(),
                worker_cls=ConversionWorker,
            )

            assert item.output_path is not None
            saved = Path(converter(item.source_path, item.output_path, item))

            self.assertEqual(saved, item.output_path)
            self.assertEqual(saved, out / 'images' / 'cover.xtc')
            self.assertTrue(saved.exists())
            self.assertEqual(saved.read_bytes()[:4], b'XTC\x00')

    def test_worker_bridge_real_worker_converts_epub_when_optional_deps_available(self):
        from tests import studio_import_helper

        studio = studio_import_helper.load_studio_module(force_reload=True)
        try:
            studio.core._require_ebooklib_epub()
            studio.core._require_bs4_beautifulsoup()
        except Exception as exc:
            self.skipTest(f'EPUB optional dependencies unavailable: {exc}')

        from tests.sample_fixture_builders import build_sample_epub
        from tategakiXTC_gui_studio_worker import ConversionWorker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            source = build_sample_epub(root / 'books' / 'sample.epub')
            plan = build_folder_batch_plan(root, out, existing_policy='overwrite')
            item = next(item for item in plan.items if item.will_convert)
            converter = make_worker_bridge_converter(
                lambda src, dst, plan_item: self._minimal_real_worker_settings(),
                worker_cls=ConversionWorker,
            )

            assert item.output_path is not None
            saved = Path(converter(item.source_path, item.output_path, item))

            self.assertEqual(saved, item.output_path)
            self.assertEqual(saved, out / 'books' / 'sample.xtc')
            self.assertTrue(saved.exists())
            self.assertEqual(saved.read_bytes()[:4], b'XTC\x00')

    def test_missing_settings_hook_raises_clear_error(self):
        with self.assertRaisesRegex(AttributeError, '変換設定を取得できません'):
            collect_worker_settings_from_mainwindow(object(), Path('a.txt'), Path('a.xtc'), object())


if __name__ == '__main__':
    unittest.main()
