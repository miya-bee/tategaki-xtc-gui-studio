from __future__ import annotations

import unittest
from pathlib import Path

from tategakiXTC_folder_batch_settings import (
    FOLDER_BATCH_EXISTING_POLICY_KEY,
    FOLDER_BATCH_INCLUDE_SUBFOLDERS_KEY,
    FOLDER_BATCH_INPUT_ROOT_KEY,
    FOLDER_BATCH_OUTPUT_ROOT_KEY,
    FOLDER_BATCH_PRESERVE_STRUCTURE_KEY,
    load_folder_batch_dialog_defaults,
    save_folder_batch_dialog_defaults,
)


class FakeSettings:
    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.synced = False

    def value(self, key: str, default: object = None) -> object:
        return self.values.get(key, default)

    def setValue(self, key: str, value: object) -> None:
        self.values[key] = value

    def sync(self) -> None:
        self.synced = True


class FolderBatchSettingsTests(unittest.TestCase):
    def test_load_defaults_uses_project_decision_initial_values(self) -> None:
        defaults = load_folder_batch_dialog_defaults({})
        self.assertEqual(defaults.input_root, '')
        self.assertEqual(defaults.output_root, '')
        self.assertTrue(defaults.include_subfolders)
        self.assertTrue(defaults.preserve_structure)
        self.assertEqual(defaults.existing_policy, 'skip')

    def test_load_defaults_coerces_mapping_values(self) -> None:
        values = {
            FOLDER_BATCH_INPUT_ROOT_KEY: r'C:\Books',
            FOLDER_BATCH_OUTPUT_ROOT_KEY: r'D:\Out',
            FOLDER_BATCH_INCLUDE_SUBFOLDERS_KEY: 'false',
            FOLDER_BATCH_PRESERVE_STRUCTURE_KEY: '1',
            FOLDER_BATCH_EXISTING_POLICY_KEY: '上書き',
        }
        defaults = load_folder_batch_dialog_defaults(values)
        self.assertEqual(defaults.input_root, r'C:\Books')
        self.assertEqual(defaults.output_root, r'D:\Out')
        self.assertFalse(defaults.include_subfolders)
        self.assertTrue(defaults.preserve_structure)
        self.assertEqual(defaults.existing_policy, 'overwrite')

    def test_save_defaults_supports_qsettings_like_object(self) -> None:
        settings = FakeSettings()
        save_folder_batch_dialog_defaults(
            settings,
            input_root=Path('input'),
            output_root=Path('output'),
            include_subfolders=False,
            preserve_structure=True,
            existing_policy='別名で保存',
        )
        self.assertEqual(settings.values[FOLDER_BATCH_INPUT_ROOT_KEY], 'input')
        self.assertEqual(settings.values[FOLDER_BATCH_OUTPUT_ROOT_KEY], 'output')
        self.assertFalse(settings.values[FOLDER_BATCH_INCLUDE_SUBFOLDERS_KEY])
        self.assertTrue(settings.values[FOLDER_BATCH_PRESERVE_STRUCTURE_KEY])
        self.assertEqual(settings.values[FOLDER_BATCH_EXISTING_POLICY_KEY], 'rename')
        self.assertTrue(settings.synced)


if __name__ == '__main__':
    unittest.main()
