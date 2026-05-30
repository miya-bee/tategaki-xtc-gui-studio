from __future__ import annotations

from pathlib import Path
import inspect
import unittest

import tategakiXTC_gui_studio_view_helpers as view_helpers


class LegacyDeviceViewCompatibilityTests(unittest.TestCase):
    def test_legacy_device_value_is_accepted_as_compatibility_input(self) -> None:
        for raw in ('device', ' device ', 'DEVICE', '\tdevice\n'):
            with self.subTest(raw=raw):
                self.assertEqual(view_helpers._normalized_main_view_mode(raw), 'font')

    def test_legacy_device_value_uses_current_right_pane_status_text(self) -> None:
        self.assertEqual(
            view_helpers._main_view_mode_status_text('device'),
            '右ペイン表示に切り替えました。',
        )
        self.assertIn('右ペイン', view_helpers._main_view_mode_help_text('device'))

    def test_compatibility_policy_is_documented_in_helper_docstring(self) -> None:
        doc = inspect.getdoc(view_helpers._normalized_main_view_mode) or ''
        self.assertIn('Legacy INI/context', doc)
        self.assertIn('accepted for compatibility', doc)
        self.assertIn('mapped to the', doc)
        self.assertIn('normal preview/file-viewer surface', doc)

    def test_release_docs_record_device_mode_compatibility_boundary(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        notes = Path('RELEASE_NOTES_v1_4_0.md').read_text(encoding='utf-8')
        checklist = Path('PUBLISH_CHECKLIST_v1_4_0.md').read_text(encoding='utf-8')

        self.assertIn('旧 `device` view-mode 値は互換入力として受け入れ', readme)
        self.assertIn('旧 device-view UI は復活させません', readme)
        self.assertIn('旧 `device` view-mode 値は互換レイヤーとして受け入れ', notes)
        self.assertIn('旧 device-view UI を復活させず', notes)
        self.assertIn('旧 `device` view-mode 値が現行の右ペイン表示へ安全に丸められる', checklist)


if __name__ == '__main__':
    unittest.main()
