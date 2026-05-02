from __future__ import annotations

import unittest
from unittest import mock

import tategakiXTC_gui_results_controller as results_controller


class GuiResultsControllerRegressionTests(unittest.TestCase):
    def test_build_results_view_state_normalizes_paths_and_summary(self):
        state = results_controller.build_results_view_state(
            [b'exports/book.xtc', '  "exports/other.xtch"  ', '', None],
            ['保存 2 件'.encode('utf-8'), {'error': 'エラー 0 件', 'count': 0}, '   '],
        )

        self.assertEqual(
            state['entries'],
            [('book.xtc', 'exports/book.xtc'), ('other.xtch', 'exports/other.xtch')],
        )
        self.assertEqual(state['summary_text'], '保存 2 件 / エラー 0 件')
        self.assertEqual(state['initial_index'], 0)


    def test_normalize_summary_line_item_declares_lines_annotation_once(self):
        from pathlib import Path

        source = Path('tategakiXTC_gui_results_controller.py').read_text(encoding='utf-8')
        marker = 'def _normalize_summary_line_item(item: object) -> list[str]:'
        start = source.find(marker)
        self.assertNotEqual(start, -1)
        end = source.find('def coerce_summary_line_list', start)
        self.assertNotEqual(end, -1)
        block = source[start:end]
        self.assertEqual(block.count('lines: list[str] = []'), 1)
        self.assertIn('if isinstance(item, (list, tuple, set, frozenset)):\n        lines = []', block)

    def test_build_results_view_state_flattens_nested_path_and_summary_structures(self):
        state = results_controller.build_results_view_state(
            {
                'primary': bytearray(b'exports/book.xtc'),
                'secondary': ['  "exports/other.xtch"  ', None],
            },
            {
                'saved': [bytearray('保存 2 件'.encode('utf-8')), None],
                'nested': {'error': ['  エラー 0 件  ']},
            },
        )

        self.assertEqual(
            state['entries'],
            [('book.xtc', 'exports/book.xtc'), ('other.xtch', 'exports/other.xtch')],
        )
        self.assertEqual(state['summary_text'], '保存 2 件 / エラー 0 件')
        self.assertEqual(state['initial_index'], 0)

    def test_coerce_result_path_list_deduplicates_repeated_paths_preserving_first_order(self):
        normalized = results_controller.coerce_result_path_list([
            'exports/book.xtc',
            {'dup': ['exports/book.xtc', b'exports/other.xtch']},
            '  "exports/book.xtc"  ',
            bytearray(b'exports/other.xtch'),
        ])

        self.assertEqual(normalized, ['exports/book.xtc', 'exports/other.xtch'])


    def test_coerce_result_path_list_deduplicates_same_file_referenced_with_different_spellings(self):
        from pathlib import Path
        import tempfile

        root = Path(tempfile.mkdtemp(prefix='results_paths_'))
        target = root / 'result.xtc'
        target.write_bytes(b'xtc')
        nested = root / 'nested'
        nested.mkdir()
        alias = nested / '..' / 'result.xtc'

        normalized = results_controller.coerce_result_path_list([
            str(target),
            str(alias),
        ])

        self.assertEqual(normalized, [str(target)])

    def test_build_results_entries_disambiguates_duplicate_display_names(self):
        entries = results_controller.build_results_entries([
            'exports/vol1/book.xtc',
            'exports/vol2/book.xtc',
        ])

        self.assertEqual(
            entries,
            [
                ('vol1/book.xtc', 'exports/vol1/book.xtc'),
                ('vol2/book.xtc', 'exports/vol2/book.xtc'),
            ],
        )


    def test_build_results_entries_expands_to_shortest_unique_suffix_when_parent_names_also_collide(self):
        entries = results_controller.build_results_entries([
            'exports/libA/shared/book.xtc',
            'exports/libB/shared/book.xtc',
            'exports/libC/other/book.xtc',
        ])

        self.assertEqual(
            entries,
            [
                ('libA/shared/book.xtc', 'exports/libA/shared/book.xtc'),
                ('libB/shared/book.xtc', 'exports/libB/shared/book.xtc'),
                ('other/book.xtc', 'exports/libC/other/book.xtc'),
            ],
        )

    def test_build_results_apply_context_keeps_entries_summary_and_initial_selection(self):
        context = results_controller.build_results_apply_context(
            [b'exports/book.xtc', 'exports/other.xtch'],
            {'saved': '保存 2 件'},
        )

        self.assertTrue(context['has_entries'])
        self.assertEqual(
            context['entries'],
            [('book.xtc', 'exports/book.xtc'), ('other.xtch', 'exports/other.xtch')],
        )
        self.assertEqual(context['summary_text'], '保存 2 件')
        self.assertEqual(context['initial_index'], 0)

    def test_build_results_selection_context_requests_clear_when_no_match_exists(self):
        context = results_controller.build_results_selection_context(
            'missing.xtc',
            ['exports/book.xtc', 'exports/other.xtc'],
        )

        self.assertTrue(context['clear_selection'])
        self.assertIsNone(context['matched_index'])

    def test_build_results_load_context_prefers_current_index_and_exposes_resolved_path(self):
        context = results_controller.build_results_load_context(
            selected_indexes=['1'],
            current_index=0,
            item_paths=['exports/book.xtc', bytearray(b'exports/other.xtch')],
        )

        self.assertTrue(context['has_selection'])
        self.assertTrue(context['has_path'])
        self.assertEqual(context['preferred_index'], 0)
        self.assertEqual(context['resolved_path'], 'exports/book.xtc')
        self.assertFalse(context['should_warn_no_selection'])
        self.assertFalse(context['should_warn_missing_path'])

    def test_build_loaded_xtc_path_success_context_includes_selection_log_and_label(self):
        context = results_controller.build_loaded_xtc_path_success_context(
            b'exports/book.xtc',
            '',
            ['exports/other.xtc', 'exports/book.xtc'],
        )

        self.assertEqual(context['device_view_source'], 'xtc')
        self.assertEqual(context['display_name'], 'book.xtc')
        self.assertEqual(context['log_message'], 'XTC/XTCH読込: exports/book.xtc')
        self.assertEqual(context['view_mode'], 'device')
        self.assertFalse(context['safe_view_mode'])
        self.assertEqual(context['selection_context'], {'matched_index': 1, 'clear_selection': False})

    def test_build_loaded_xtc_bytes_success_context_clears_selection_and_uses_safe_view_mode(self):
        context = results_controller.build_loaded_xtc_bytes_success_context(bytearray(' メモリ上のデータ '.encode('utf-8')))

        self.assertEqual(context['device_view_source'], 'xtc')
        self.assertEqual(context['display_name'], 'メモリ上のデータ')
        self.assertEqual(context['selection_context'], {'matched_index': None, 'clear_selection': True})
        self.assertEqual(context['view_mode'], 'device')
        self.assertTrue(context['safe_view_mode'])

    def test_build_loaded_xtc_failure_context_requests_state_and_selection_clear(self):
        context = results_controller.build_loaded_xtc_failure_context()

        self.assertTrue(context['clear_loaded_state'])
        self.assertEqual(context['selection_context'], {'matched_index': None, 'clear_selection': True})

    def test_build_results_load_context_flags_missing_selection_and_path(self):
        no_selection = results_controller.build_results_load_context(
            selected_indexes=[],
            current_index=None,
            item_paths=['exports/book.xtc', 'exports/other.xtc'],
        )
        missing_path = results_controller.build_results_load_context(
            selected_indexes=['0'],
            current_index=None,
            item_paths=[None],
        )

        self.assertTrue(no_selection['should_warn_no_selection'])
        self.assertFalse(no_selection['should_warn_missing_path'])
        self.assertTrue(missing_path['has_selection'])
        self.assertTrue(missing_path['should_warn_missing_path'])
        self.assertFalse(missing_path['has_path'])

    def test_build_results_load_context_falls_back_to_loaded_path_when_selection_is_stale(self):
        context = results_controller.build_results_load_context(
            selected_indexes=[],
            current_index=None,
            item_paths=['exports/book.xtc', 'exports/other.xtc'],
            loaded_path='  "exports/other.xtc"  ',
        )

        self.assertTrue(context['has_selection'])
        self.assertTrue(context['has_path'])
        self.assertEqual(context['preferred_index'], 1)
        self.assertEqual(context['resolved_path'], 'exports/other.xtc')
        self.assertFalse(context['should_warn_no_selection'])
        self.assertFalse(context['should_warn_missing_path'])

    def test_build_fallback_loaded_result_load_context_matches_loaded_path(self):
        context = results_controller.build_fallback_loaded_result_load_context(
            '  "exports/other.xtc"  ',
            ['exports/book.xtc', 'exports/other.xtc'],
        )

        self.assertEqual(context['preferred_index'], 1)
        self.assertEqual(context['resolved_path'], 'exports/other.xtc')
        self.assertTrue(context['has_path'])

    def test_build_fallback_loaded_result_load_context_returns_empty_without_match(self):
        self.assertEqual(
            results_controller.build_fallback_loaded_result_load_context(
                'exports/missing.xtc',
                ['exports/book.xtc'],
            ),
            {},
        )
        self.assertEqual(
            results_controller.build_fallback_loaded_result_load_context('', ['exports/book.xtc']),
            {},
        )

    def test_find_matching_loaded_path_index_matches_windows_like_variants(self):
        with mock.patch('os.path.normcase', side_effect=lambda value: str(value).replace('\\', '/').lower()):
            matched_index = results_controller.find_matching_loaded_path_index(
                r'C:\Books\Sub\..\Result.xtc',
                [r'C:/Books/Result.XTC', r'D:/Else/other.xtc'],
            )

        self.assertEqual(matched_index, 0)

    def test_find_matching_loaded_path_index_matches_bytes_and_quoted_paths(self):
        matched_index = results_controller.find_matching_loaded_path_index(
            bytearray(b'exports/book.xtc'),
            ['  "exports/book.xtc"  ', 'other.xtc'],
        )

        self.assertEqual(matched_index, 0)

    def test_resolve_preferred_results_index_prefers_current_then_single_selected_then_single_item(self):
        self.assertEqual(
            results_controller.resolve_preferred_results_index(
                selected_indexes=['2'],
                current_index=1,
                item_count=3,
            ),
            1,
        )
        self.assertEqual(
            results_controller.resolve_preferred_results_index(
                selected_indexes=['2'],
                current_index=None,
                item_count=3,
            ),
            2,
        )
        self.assertEqual(
            results_controller.resolve_preferred_results_index(
                selected_indexes=[],
                current_index='1',
                item_count=3,
            ),
            1,
        )
        self.assertEqual(
            results_controller.resolve_preferred_results_index(
                selected_indexes=[],
                current_index=None,
                item_count=1,
            ),
            0,
        )

    def test_resolve_preferred_results_index_prefers_current_when_multiple_valid_selected_indexes_exist(self):
        self.assertEqual(
            results_controller.resolve_preferred_results_index(
                selected_indexes=['0', '2', '0'],
                current_index='2',
                item_count=3,
            ),
            2,
        )

    def test_resolve_preferred_results_index_prefers_current_even_when_single_valid_selected_index_differs(self):
        self.assertEqual(
            results_controller.resolve_preferred_results_index(
                selected_indexes=['0'],
                current_index='2',
                item_count=3,
            ),
            2,
        )

    def test_resolve_preferred_results_index_returns_none_for_ambiguous_multiple_selection_without_current(self):
        self.assertIsNone(
            results_controller.resolve_preferred_results_index(
                selected_indexes=['0', '1'],
                current_index=None,
                item_count=3,
            )
        )


if __name__ == '__main__':
    unittest.main()
