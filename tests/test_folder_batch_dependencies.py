from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tategakiXTC_folder_batch_dependencies import (
    describe_folder_batch_missing_dependencies,
    folder_batch_planned_source_suffixes,
    format_folder_batch_missing_dependency_lines,
    missing_dependencies_for_folder_batch_plan,
)
from tategakiXTC_folder_batch_plan import build_folder_batch_plan


class FolderBatchDependencyGuidanceTests(unittest.TestCase):
    def test_planned_suffixes_include_only_items_that_will_convert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            out.mkdir()
            (root / 'book.epub').write_bytes(b'epub')
            (root / 'done.epub').write_bytes(b'epub')
            (root / 'memo.txt').write_text('hello', encoding='utf-8')
            (out / 'done.xtc').write_text('old', encoding='utf-8')
            plan = build_folder_batch_plan(root, out, existing_policy='skip')

        self.assertEqual(folder_batch_planned_source_suffixes(plan), ('.epub', '.txt'))

    def test_missing_dependency_guidance_uses_injected_checker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.epub').write_bytes(b'epub')
            plan = build_folder_batch_plan(root, out)

        seen_suffixes: list[tuple[str, ...]] = []

        def fake_getter(suffixes):
            seen_suffixes.append(tuple(suffixes))
            return [
                {'label': 'ebooklib', 'package': 'ebooklib', 'purpose': 'EPUB変換'},
                {'label': 'beautifulsoup4', 'package': 'beautifulsoup4', 'purpose': 'EPUB変換'},
            ]

        missing = missing_dependencies_for_folder_batch_plan(plan, dependency_getter=fake_getter)
        message = describe_folder_batch_missing_dependencies(plan, dependency_getter=fake_getter)

        self.assertEqual(seen_suffixes[0], ('.epub',))
        self.assertEqual(len(missing), 2)
        self.assertIn('ebooklib', message)
        self.assertIn('beautifulsoup4', message)
        self.assertIn('install_requirements.bat', message)
        self.assertIn('requirements.txt', message)

    def test_format_missing_dependency_lines_is_empty_when_available(self) -> None:
        self.assertEqual(format_folder_batch_missing_dependency_lines([]), [])

    def test_dependency_checker_failure_is_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            out = Path(tmp) / 'out'
            root.mkdir()
            (root / 'book.epub').write_bytes(b'epub')
            plan = build_folder_batch_plan(root, out)

        def broken_getter(_suffixes):
            raise RuntimeError('dependency checker unavailable')

        self.assertEqual(missing_dependencies_for_folder_batch_plan(plan, dependency_getter=broken_getter), [])
        self.assertEqual(describe_folder_batch_missing_dependencies(plan, dependency_getter=broken_getter), '')


if __name__ == '__main__':
    unittest.main()
