from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tategakiXTC_folder_batch_converter_adapter import (
    FolderBatchConversionContext,
    build_mainwindow_converter_from_known_hook,
    make_folder_batch_converter_from_callable,
    make_output_override_kwargs,
)
from tategakiXTC_folder_batch_plan import build_folder_batch_plan


class FolderBatchConverterAdapterTests(unittest.TestCase):
    def _item(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'in'
            out = Path(tmp) / 'out'
            root.mkdir()
            source = root / 'book.txt'
            source.write_text('hello', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, output_format='xtc')
            return plan.items[0]

    def test_wraps_three_argument_callback(self) -> None:
        item = self._item()
        calls = []

        def callback(src, dst, plan_item):
            calls.append((src, dst, plan_item))

        converter = make_folder_batch_converter_from_callable(callback)
        converter(item.source_path, item.output_path, item)
        self.assertEqual(calls[0][0], item.source_path)
        self.assertEqual(calls[0][1], item.output_path)
        self.assertIs(calls[0][2], item)

    def test_wraps_two_argument_callback(self) -> None:
        item = self._item()
        calls = []

        def callback(src, dst):
            calls.append((src, dst))

        converter = make_folder_batch_converter_from_callable(callback)
        converter(item.source_path, item.output_path, item)
        self.assertEqual(calls, [(item.source_path, item.output_path)])

    def test_wraps_keyword_callback(self) -> None:
        item = self._item()
        calls = []

        def callback(input_path=None, output_path=None, plan_item=None):
            calls.append((input_path, output_path, plan_item))

        converter = make_folder_batch_converter_from_callable(callback)
        converter(item.source_path, item.output_path, item)
        self.assertEqual(calls, [(item.source_path, item.output_path, item)])

    def test_wraps_context_callback(self) -> None:
        item = self._item()
        calls: list[FolderBatchConversionContext] = []

        def callback(context=None):
            calls.append(context)

        converter = make_folder_batch_converter_from_callable(callback)
        converter(item.source_path, item.output_path, item)
        self.assertEqual(calls[0].source_path, item.source_path)
        self.assertEqual(calls[0].output_path, item.output_path)

    def test_path_as_string_option(self) -> None:
        item = self._item()
        calls = []

        def callback(src, dst):
            calls.append((src, dst))

        converter = make_folder_batch_converter_from_callable(callback, path_as_string=True)
        converter(item.source_path, item.output_path, item)
        self.assertIsInstance(calls[0][0], str)
        self.assertIsInstance(calls[0][1], str)

    def test_before_after_callbacks_are_called(self) -> None:
        item = self._item()
        events: list[str] = []

        def callback(src, dst):
            events.append('convert')

        converter = make_folder_batch_converter_from_callable(
            callback,
            before_each=lambda context: events.append(f'before:{context.relative_source_path}'),
            after_each=lambda context: events.append(f'after:{context.relative_source_path}'),
        )
        converter(item.source_path, item.output_path, item)
        self.assertEqual(events, ['before:book.txt', 'convert', 'after:book.txt'])

    def test_extra_kwargs_getter_can_add_options(self) -> None:
        item = self._item()
        calls = []

        def callback(input_path=None, output_path=None, mode=None):
            calls.append((input_path, output_path, mode))

        converter = make_folder_batch_converter_from_callable(
            callback,
            extra_kwargs_getter=lambda context: {'mode': 'folder-batch'},
        )
        converter(item.source_path, item.output_path, item)
        self.assertEqual(calls[0][2], 'folder-batch')

    def test_real_typeerror_from_callback_is_not_swallowed(self) -> None:
        item = self._item()

        def callback(src, dst):
            raise TypeError('real internal failure')

        converter = make_folder_batch_converter_from_callable(callback)
        with self.assertRaisesRegex(TypeError, 'real internal failure'):
            converter(item.source_path, item.output_path, item)

    def test_output_override_kwargs(self) -> None:
        path = Path('out/book.xtc')
        self.assertEqual(make_output_override_kwargs(path), {'output_path': path})
        self.assertEqual(make_output_override_kwargs(path, key='dest', path_as_string=True), {'dest': str(path)})

    def test_build_mainwindow_converter_from_known_hook(self) -> None:
        item = self._item()
        calls = []

        class MainWindow:
            def _convert_single_file_for_folder_batch(self, src, dst, plan_item):
                calls.append((src, dst, plan_item))

        converter = build_mainwindow_converter_from_known_hook(MainWindow())
        converter(item.source_path, item.output_path, item)
        self.assertEqual(calls[0][0], item.source_path)

    def test_build_mainwindow_converter_requires_explicit_hook(self) -> None:
        with self.assertRaises(AttributeError):
            build_mainwindow_converter_from_known_hook(object())


if __name__ == '__main__':
    unittest.main()
