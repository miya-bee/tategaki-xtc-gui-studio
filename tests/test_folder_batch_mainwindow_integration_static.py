from __future__ import annotations

from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read_project_file(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding='utf-8')


class FolderBatchMainWindowIntegrationStaticTests(unittest.TestCase):
    def test_mainwindow_exposes_folder_batch_hooks_and_topbar_button(self) -> None:
        source = read_project_file('tategakiXTC_gui_studio.py')
        self.assertIn('def _open_folder_batch_dialog(', source)
        self.assertIn('def _folder_batch_worker_settings(', source)
        self.assertIn("'フォルダ一括変換...'", source)
        self.assertIn('self.folder_batch_btn = self._make_button_from_plan', source)
        self.assertIn('self._open_folder_batch_dialog,', source)
        self.assertIn("'_folder_batch_running'", source)
        self.assertIn("'フォルダ一括変換はすでに実行中です。'", source)
        self.assertIn("'通常変換の実行中は、フォルダ一括変換を開始できません。", source)
        self.assertIn('open_folder_batch_dialog_for_mainwindow_real_or_warn(self)', source)


    def test_worker_running_state_disables_folder_batch_entry_points(self) -> None:
        source = read_project_file('tategakiXTC_gui_studio.py')
        start = source.index('def _set_worker_controls_running(')
        end = source.index('def _prepare_conversion_ui_for_run(', start)
        body = source[start:end]
        self.assertIn("('folder_batch_btn', 'folder_batch_action')", body)
        self.assertIn('setter(not running)', body)

    def test_build_release_zip_includes_folder_batch_runtime_modules(self) -> None:
        source = read_project_file('build_release_zip.py')
        for name in (
            'tategakiXTC_folder_batch_plan.py',
            'tategakiXTC_folder_batch_executor.py',
            'tategakiXTC_folder_batch_settings.py',
            'tategakiXTC_folder_batch_safety.py',
            'tategakiXTC_folder_batch_dialog.py',
            'tategakiXTC_folder_batch_controller.py',
            'tategakiXTC_folder_batch_converter_adapter.py',
            'tategakiXTC_folder_batch_mainwindow_launcher.py',
            'tategakiXTC_folder_batch_worker_bridge.py',
        ):
            self.assertIn(name, source)

    def test_folder_batch_dialog_imports_partial_skip_notice_used_by_summary(self) -> None:
        source = read_project_file('tategakiXTC_folder_batch_dialog.py')
        self.assertIn('describe_folder_batch_partial_skip_notice,', source)
        self.assertIn('describe_folder_batch_partial_skip_notice(plan)', source)
        self.assertIn('normalize_suffixes,', source)
        self.assertIn('def _supported_suffixes_label', source)
        self.assertIn("QLabel(self._supported_suffixes_label())", source)


if __name__ == '__main__':
    unittest.main()
