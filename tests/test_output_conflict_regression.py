import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
import tategakiXTC_worker_logic as worker_logic


class OutputConflictRegressionTests(unittest.TestCase):
    def test_rename_strategy_adds_number_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desired = Path(tmpdir) / 'sample.xtc'
            desired.write_bytes(b'existing')
            final_path, plan = core.resolve_output_path_with_conflict(desired, 'rename')
        self.assertTrue(plan['conflict'])
        self.assertTrue(plan['renamed'])
        self.assertFalse(plan['overwritten'])
        self.assertEqual(final_path.name, 'sample(1).xtc')

    def test_overwrite_strategy_keeps_original_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desired = Path(tmpdir) / 'sample.xtch'
            desired.write_bytes(b'existing')
            final_path, plan = core.resolve_output_path_with_conflict(desired, 'overwrite')
        self.assertEqual(final_path, desired)
        self.assertTrue(plan['conflict'])
        self.assertFalse(plan['renamed'])
        self.assertTrue(plan['overwritten'])

    def test_error_strategy_raises_on_existing_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desired = Path(tmpdir) / 'sample.xtc'
            desired.write_bytes(b'existing')
            with self.assertRaises(RuntimeError):
                core.resolve_output_path_with_conflict(desired, 'error')
    def test_find_output_conflicts_returns_source_and_output_pairs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'sample.txt'
            src.write_text('x', encoding='utf-8')
            out = src.with_suffix('.xtc')
            out.write_bytes(b'existing')
            conflicts = core.find_output_conflicts([str(src)], 'xtc')
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0][0], str(src))
        self.assertEqual(conflicts[0][1].name, 'sample.xtc')

    def test_batch_collision_reserves_second_output_even_when_overwrite_is_selected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            desired = base / 'sample.xtc'
            reserved = {worker_logic._normalize_path_match_key(desired)}
            out_path, plan = core.resolve_output_path_with_conflict(desired, 'overwrite')
            reserved_path, reserved_plan = worker_logic.reserve_unique_output_path_for_batch(out_path, plan, reserved)
        self.assertEqual(reserved_path.name, 'sample(1).xtc')
        self.assertTrue(bool(reserved_plan and reserved_plan.get('batch_collision')))
        self.assertTrue(bool(reserved_plan and reserved_plan.get('renamed')))
        self.assertFalse(bool(reserved_plan and reserved_plan.get('overwritten')))

    def test_batch_collision_skips_existing_and_reserved_candidates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            desired = base / 'sample.xtc'
            (base / 'sample(1).xtc').write_bytes(b'exists')
            reserved = {worker_logic._normalize_path_match_key(desired), worker_logic._normalize_path_match_key(base / 'sample(2).xtc')}
            reserved_path, _reserved_plan = worker_logic.reserve_unique_output_path_for_batch(desired, None, reserved)
        self.assertEqual(reserved_path.name, 'sample(3).xtc')



    def test_path_split_helpers_follow_core_monkey_patch_for_unique_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            desired = Path(tmpdir) / 'sample.xtc'
            patched = Path(tmpdir) / 'patched.xtc'
            with mock.patch.object(core, 'make_unique_output_path', return_value=patched) as make_unique:
                final_path, plan = core.resolve_output_path_with_conflict(desired, 'rename')
        make_unique.assert_called_once_with(desired)
        self.assertEqual(final_path, patched)
        self.assertTrue(plan['renamed'])
        self.assertEqual(plan['final_path'], str(patched))

    def test_should_skip_conversion_target_accepts_string_path(self):
        self.assertTrue(core.should_skip_conversion_target('sample.xtch'))
        self.assertFalse(core.should_skip_conversion_target('sample.txt'))



if __name__ == '__main__':
    unittest.main()
