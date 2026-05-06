from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tategakiXTC_folder_batch_safety import analyze_folder_batch_roots


class FolderBatchSafetyTests(unittest.TestCase):
    def test_missing_roots_are_reported_without_resolving_current_directory(self) -> None:
        report = analyze_folder_batch_roots('', '')
        self.assertTrue(report.has_warnings)
        self.assertTrue(any('入力元フォルダ' in warning for warning in report.warnings))
        self.assertTrue(any('出力先フォルダ' in warning for warning in report.warnings))

    def test_same_input_and_output_root_is_warned(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'books'
            root.mkdir()
            report = analyze_folder_batch_roots(root, root)
        self.assertTrue(report.has_warnings)
        self.assertTrue(any('同じ' in warning for warning in report.warnings))

    def test_output_inside_input_root_is_warned(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'books'
            out = root / 'out'
            out.mkdir(parents=True)
            report = analyze_folder_batch_roots(root, out)
        self.assertTrue(report.has_warnings)
        self.assertTrue(any('配下' in warning for warning in report.warnings))

    def test_separate_roots_have_no_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / 'books'
            out = Path(tmpdir) / 'out'
            root.mkdir()
            out.mkdir()
            report = analyze_folder_batch_roots(root, out)
        self.assertFalse(report.has_warnings)


if __name__ == '__main__':
    unittest.main()
