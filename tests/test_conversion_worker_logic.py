import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_worker_logic as worker_logic


class ConversionWorkerLogicTests(unittest.TestCase):
    def test_build_conversion_args_returns_conversion_args(self):
        args = worker_logic.build_conversion_args({
            'width': '600',
            'height': '900',
            'font_size': '30',
            'output_format': 'XTCH',
        })
        self.assertEqual(args.width, 600)
        self.assertEqual(args.height, 900)
        self.assertEqual(args.font_size, 30)
        self.assertEqual(args.output_format, 'xtch')
        self.assertEqual(args.punctuation_position_mode, 'standard')
        self.assertEqual(args.ichi_position_mode, 'standard')
        self.assertEqual(args.lower_closing_bracket_position_mode, 'standard')

    def test_build_conversion_args_preserves_glyph_position_modes(self):
        args = worker_logic.build_conversion_args({
            'output_format': 'xtc',
            'punctuation_position_mode': 'down_weak',
            'ichi_position_mode': 'up_strong',
            'lower_closing_bracket_position_mode': 'up_weak',
        })

        self.assertEqual(args.punctuation_position_mode, 'down_weak')
        self.assertEqual(args.ichi_position_mode, 'up_strong')
        self.assertEqual(args.lower_closing_bracket_position_mode, 'up_weak')

    def test_resolve_supported_conversion_targets_filters_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / 'book.epub').write_text('x', encoding='utf-8')
            (root / 'notes.md').write_text('# hi', encoding='utf-8')
            (root / 'cover.png').write_bytes(b'png')
            (root / 'done.xtc').write_bytes(b'x')
            (root / 'nested').mkdir()
            (root / 'nested' / 'page.cbz').write_text('x', encoding='utf-8')
            targets = worker_logic.resolve_supported_conversion_targets(root, {'.epub', '.md', '.cbz'})
            rels = [str(p.relative_to(root)).replace('\\', '/') for p in targets]
        self.assertEqual(rels, ['book.epub', 'cover.png', 'nested/page.cbz', 'notes.md'])

    def test_plan_output_path_for_target_warns_when_custom_name_ignored(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            args = worker_logic.build_conversion_args({'output_format': 'xtc'})
            calls = []

            def fake_apply(desired, strategy):
                calls.append((desired, strategy))
                return desired, {'final_path': str(desired), 'desired_path': str(desired)}

            out_path, plan, warning = worker_logic.plan_output_path_for_target(
                src,
                args,
                requested_name='custom_name',
                supported_count=2,
                conflict_strategy='rename',
                output_root=root,
                apply_conflict_strategy=fake_apply,
            )
        self.assertIn('単一ファイル変換時のみ', warning)
        self.assertEqual(out_path, root / 'book.xtc')
        self.assertEqual(calls[0][1], 'rename')
        self.assertEqual(Path(plan['final_path']).name, 'book.xtc')

    def test_plan_output_path_for_target_uses_custom_name_for_single_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            args = worker_logic.build_conversion_args({'output_format': 'xtch'})

            def fake_apply(desired, strategy):
                return desired, {'final_path': str(desired), 'desired_path': str(desired), 'strategy': strategy}

            out_path, plan, warning = worker_logic.plan_output_path_for_target(
                src,
                args,
                requested_name='  custom result  ',
                supported_count=1,
                conflict_strategy='overwrite',
                output_root=root,
                apply_conflict_strategy=fake_apply,
            )
        self.assertIsNone(warning)
        self.assertEqual(out_path.name, 'custom result.xtch')
        self.assertEqual(plan['strategy'], 'overwrite')

    def test_summarize_error_headlines_groups_duplicates_and_falls_back_to_message(self):
        lines = worker_logic.summarize_error_headlines([
            {'headline': 'EPUB読込エラー', 'error': ''},
            {'headline': 'EPUB読込エラー', 'error': ''},
            {'headline': '', 'error': '対象: foo.epub\n内容: Markdown 整形エラー\n詳細: x'},
        ])
        self.assertEqual(lines, ['主な原因 EPUB読込エラー 2件 / Markdown 整形エラー 1件'])


    def test_build_conversion_summary_accepts_error_generators(self):
        errors = ({'headline': '入出力エラー', 'error': ''} for _ in range(2))

        msg, lines = worker_logic.build_conversion_summary(
            converted_count=1,
            renamed_count=0,
            overwritten_count=0,
            errors=errors,
            stopped=False,
        )

        self.assertEqual(msg, '変換完了しました。(1 件を保存 / 2 件エラー)')
        self.assertIn('保存 1 件', lines)
        self.assertIn('エラー 2 件', lines)
        self.assertIn('主な原因 入出力エラー 2件', lines)

    def test_build_conversion_summary_accepts_single_mapping_error_item(self):
        msg, lines = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors={'headline': '入出力エラー', 'error': 'broken'},
            stopped=False,
        )

        self.assertEqual(msg, '変換できませんでした。(1 件エラー)')
        self.assertIn('エラー 1 件', lines)
        self.assertIn('主な原因 入出力エラー 1件', lines)

    def test_build_conversion_summary_normalizes_bytes_inside_single_mapping_error_item(self):
        msg, lines = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors={
                'headline': bytearray('画像処理エラー'.encode('utf-8')),
                'error': '対象: foo.epub\n内容: Markdown 整形エラー'.encode('utf-8'),
                'source': Path('foo.epub'),
            },
            stopped=False,
        )

        self.assertEqual(msg, '変換できませんでした。(1 件エラー)')
        self.assertIn('エラー 1 件', lines)
        self.assertIn('主な原因 画像処理エラー 1件', lines)

    def test_build_conversion_summary_treats_empty_mapping_errors_as_no_errors(self):
        msg, lines = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors={},
            stopped=False,
        )

        self.assertEqual(msg, '変換完了しました。(0 件)')
        self.assertNotIn('エラー 1 件', lines)
        self.assertFalse(any(line.startswith('主な原因') for line in lines))


    def test_build_conversion_summary_ignores_blank_error_items_inside_iterables(self):
        msg, lines = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors=['', '   ', b'', bytearray(), None, {}, ' \n\t '],
            stopped=False,
        )

        self.assertEqual(msg, '変換完了しました。(0 件)')
        self.assertNotIn('エラー 1 件', lines)
        self.assertFalse(any(line.startswith('主な原因') for line in lines))

    def test_build_conversion_summary_ignores_blank_scalar_error_inputs(self):
        for raw_error in ('   ', b'  ', bytearray(b' \n\t')):
            with self.subTest(raw_error=raw_error):
                msg, lines = worker_logic.build_conversion_summary(
                    converted_count=0,
                    renamed_count=0,
                    overwritten_count=0,
                    errors=raw_error,
                    stopped=False,
                )

                self.assertEqual(msg, '変換完了しました。(0 件)')
                self.assertNotIn('エラー 1 件', lines)
                self.assertFalse(any(line.startswith('主な原因') for line in lines))

    def test_build_conversion_summary_accepts_scalar_and_string_errors(self):
        msg1, lines1 = worker_logic.build_conversion_summary(
            converted_count=1,
            renamed_count=0,
            overwritten_count=0,
            errors=2,
            stopped=False,
        )
        self.assertEqual(msg1, '変換完了しました。(1 件を保存 / 2 件エラー)')
        self.assertIn('エラー 2 件', lines1)
        self.assertFalse(any(line.startswith('主な原因') for line in lines1))

        msg2, lines2 = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors='対象: foo.epub\n内容: Markdown 整形エラー',
            stopped=False,
        )
        self.assertEqual(msg2, '変換できませんでした。(1 件エラー)')
        self.assertIn('エラー 1 件', lines2)
        self.assertIn('主な原因 Markdown 整形エラー 1件', lines2)

    def test_build_conversion_summary_accepts_bytes_and_bytearray_errors(self):
        msg1, lines1 = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors='対象: foo.epub\n内容: Markdown 整形エラー'.encode('utf-8'),
            stopped=False,
        )
        self.assertEqual(msg1, '変換できませんでした。(1 件エラー)')
        self.assertIn('エラー 1 件', lines1)
        self.assertIn('主な原因 Markdown 整形エラー 1件', lines1)

        msg2, lines2 = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors=bytearray('対象: foo.epub\n内容: 画像処理エラー'.encode('utf-8')),
            stopped=False,
        )
        self.assertEqual(msg2, '変換できませんでした。(1 件エラー)')
        self.assertIn('エラー 1 件', lines2)
        self.assertIn('主な原因 画像処理エラー 1件', lines2)

    def test_collect_conversion_counts_accepts_iterables(self):
        counts = worker_logic.collect_conversion_counts(
            converted=['a.xtc', 'b.xtc'],
            renamed=[{'final_path': 'a_2.xtc'}],
            overwritten=[],
            errors=[{'headline': 'x'}],
            skipped=(item for item in ['skip-a', 'skip-b']),
        )
        self.assertEqual(
            counts,
            {
                'converted': 2,
                'renamed': 1,
                'overwritten': 0,
                'errors': 1,
                'skipped': 2,
            },
        )

    def test_collect_conversion_counts_accepts_single_path_objects(self):
        counts = worker_logic.collect_conversion_counts(
            converted=Path('exports/result.xtc'),
            renamed=Path('exports/result_2.xtc'),
            overwritten=None,
            errors=None,
            skipped=Path('exports/skipped.txt'),
        )
        self.assertEqual(
            counts,
            {
                'converted': 1,
                'renamed': 1,
                'overwritten': 0,
                'errors': 0,
                'skipped': 1,
            },
        )

    def test_collect_conversion_counts_accepts_single_mapping_items(self):
        counts = worker_logic.collect_conversion_counts(
            converted={'path': 'output/book.xtc'},
            renamed={'desired_path': 'output/book.xtc', 'final_path': 'output/book-1.xtc'},
            overwritten={'final_path': 'output/book.xtc'},
            errors={'error': 'failed'},
            skipped={},
        )
        self.assertEqual(
            counts,
            {
                'converted': 1,
                'renamed': 1,
                'overwritten': 1,
                'errors': 1,
                'skipped': 0,
            },
        )

    def test_collect_conversion_counts_accepts_scalar_counts_and_single_objects(self):
        counts = worker_logic.collect_conversion_counts(
            converted=2.0,
            renamed=1.0,
            overwritten=float('nan'),
            errors=object(),
            skipped=0.0,
        )
        self.assertEqual(
            counts,
            {
                'converted': 2,
                'renamed': 1,
                'overwritten': 0,
                'errors': 1,
                'skipped': 0,
            },
        )

    def test_resolve_open_folder_target_prefers_single_output_parent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            out_dir = root / 'exports'
            out_dir.mkdir()
            target = worker_logic.resolve_open_folder_target(src, [out_dir / 'book.xtc'])
        self.assertEqual(target, out_dir)

    def test_resolve_open_folder_target_falls_back_to_input_parent_for_multiple_output_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            a_dir = root / 'a'
            b_dir = root / 'b'
            a_dir.mkdir()
            b_dir.mkdir()
            target = worker_logic.resolve_open_folder_target(src, [a_dir / 'one.xtc', b_dir / 'two.xtc'])
        self.assertEqual(target, root)

    def test_build_conversion_summary_includes_error_headlines_and_stop(self):
        msg, summary_lines = worker_logic.build_conversion_summary(
            converted_count=2,
            renamed_count=1,
            overwritten_count=0,
            errors=[
                {'headline': 'EPUB読込エラー'},
                {'headline': 'EPUB読込エラー'},
                {'headline': '画像変換エラー'},
            ],
            stopped=True,
        )
        self.assertEqual(msg, '変換を停止しました。(2 件を保存 / 3 件エラー)')
        self.assertIn('保存 2 件', summary_lines)
        self.assertIn('自動連番 1 件', summary_lines)
        self.assertIn('エラー 3 件', summary_lines)
        self.assertIn('途中停止', summary_lines)
        self.assertTrue(any('EPUB読込エラー' in line for line in summary_lines))
        self.assertTrue(any('画像変換エラー' in line for line in summary_lines))



    def test_config_value_helpers_cover_bool_and_string_edges(self):
        self.assertEqual(worker_logic._int_config_value({'width': True}, 'width', 480), 1)
        self.assertEqual(worker_logic._int_config_value({'width': '32.0'}, 'width', 480), 32)
        self.assertEqual(worker_logic._int_config_value({'width': ' 14.0 '}, 'width', 480), 14)
        self.assertEqual(worker_logic._int_config_value({'width': '-3.0'}, 'width', 480), -3)
        self.assertEqual(worker_logic._int_config_value({'width': float('inf')}, 'width', 480), 480)
        self.assertEqual(worker_logic._int_config_value({'width': 'nan'}, 'width', 480), 480)
        self.assertEqual(worker_logic._int_config_value({'width': object()}, 'width', 480), 480)
        self.assertEqual(worker_logic._int_config_value({'width': 'broken'}, 'width', 480), 480)
        self.assertEqual(worker_logic._int_config_value({'width': ''}, 'width', 480), 480)
        self.assertTrue(worker_logic._bool_config_value({'open_folder': ' yes '}, 'open_folder', False))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': 'off'}, 'open_folder', True))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': '0'}, 'open_folder', True))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': 'false'}, 'open_folder', True))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': ''}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': ''}, 'open_folder', True))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': b''}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': b''}, 'open_folder', True))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': 2}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': '2'}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': '-1'}, 'open_folder', False))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': '0.0'}, 'open_folder', True))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': float('nan')}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': float('nan')}, 'open_folder', True))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': 'nan'}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': 'nan'}, 'open_folder', True))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': 'inf'}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': b'1'}, 'open_folder', False))
        self.assertFalse(worker_logic._bool_config_value({'open_folder': b'\xff'}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': b'\xff'}, 'open_folder', True))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': 'maybe'}, 'open_folder', True))
        self.assertEqual(worker_logic._str_config_value({'output_name': None}, 'output_name', 'default'), 'default')
        self.assertEqual(worker_logic._str_config_value({'output_name': 42}, 'output_name', 'default'), '42')
        self.assertEqual(worker_logic._str_config_value({'output_format': b'xtch'}, 'output_format', 'xtc'), 'xtch')
        self.assertEqual(worker_logic._str_config_value({'output_name': bytearray(b' custom ')}, 'output_name', 'default'), ' custom ')
        self.assertEqual(worker_logic._str_config_value({'output_format': b'\xff'}, 'output_format', 'xtc'), 'xtc')
        self.assertEqual(worker_logic._str_config_value({'ui_theme': bytearray(b'\xff')}, 'ui_theme', 'light'), 'light')
        self.assertEqual(worker_logic._int_config_value({'width': b'32\xff'}, 'width', 480), 480)
        self.assertFalse(worker_logic._bool_config_value({'open_folder': b'1\xff'}, 'open_folder', False))
        self.assertTrue(worker_logic._bool_config_value({'open_folder': b'1\xff'}, 'open_folder', True))
        self.assertEqual(worker_logic._str_config_value({'output_format': b'xtch\xff'}, 'output_format', 'xtc'), 'xtc')
        self.assertEqual(worker_logic.build_conversion_args({'output_format': b'xtch'}).output_format, 'xtch')
        self.assertEqual(worker_logic.build_conversion_args({'output_format': b'\xff'}).output_format, 'xtc')
        self.assertEqual(worker_logic.build_conversion_args({'output_format': b'xtch\xff'}).output_format, 'xtc')

    def test_sanitize_output_stem_drops_directory_parts_and_extension(self):
        self.assertEqual(worker_logic.sanitize_output_stem(' nested/custom.txt '), 'custom')
        self.assertEqual(worker_logic.sanitize_output_stem(r' nested\custom.txt '), 'custom')
        self.assertEqual(worker_logic.sanitize_output_stem(r'C:\output\book.xtch'), 'book')

    def test_sanitize_output_stem_rejects_windows_reserved_or_hidden_names(self):
        self.assertEqual(worker_logic.sanitize_output_stem('.xtc'), '')
        self.assertEqual(worker_logic.sanitize_output_stem('con.txt'), '')
        self.assertEqual(worker_logic.sanitize_output_stem('report?.txt'), '')

    def test_plan_output_path_for_target_invalid_custom_name_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            args = worker_logic.build_conversion_args({'output_format': 'xtc'})
            with self.assertRaises(RuntimeError):
                worker_logic.plan_output_path_for_target(
                    src,
                    args,
                    requested_name='   .   ',
                    supported_count=1,
                    conflict_strategy='rename',
                    output_root=root,
                    apply_conflict_strategy=lambda desired, strategy: (desired, {'final_path': str(desired)}),
                )

    def test_plan_output_path_for_target_returns_none_when_getter_returns_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            args = worker_logic.build_conversion_args({'output_format': 'xtc'})
            out_path, plan, warning = worker_logic.plan_output_path_for_target(
                src,
                args,
                requested_name='',
                supported_count=2,
                conflict_strategy='skip',
                output_path_getter=lambda *_args, **_kwargs: None,
            )
        self.assertIsNone(out_path)
        self.assertIsNone(plan)
        self.assertIsNone(warning)

    def test_plan_output_path_for_target_uses_core_defaults_when_callbacks_omitted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            args = worker_logic.build_conversion_args({'output_format': 'xtc'})
            with mock.patch.object(worker_logic.core, 'get_output_path_for_target', return_value=root / 'book.xtc') as getter, \
                 mock.patch.object(worker_logic.core, 'resolve_output_path_with_conflict', return_value=(root / 'book.xtc', {'final_path': str(root / 'book.xtc')})) as resolver:
                out_path, plan, warning = worker_logic.plan_output_path_for_target(
                    src,
                    args,
                    requested_name='',
                    supported_count=2,
                    conflict_strategy='rename',
                    output_root=root,
                )
        self.assertEqual(out_path, root / 'book.xtc')
        self.assertEqual(Path(plan['final_path']), root / 'book.xtc')
        self.assertIsNone(warning)
        getter.assert_called_once()
        resolver.assert_called_once()

    def test_extract_error_headline_truncates_compact_fallback(self):
        headline = worker_logic.extract_error_headline('  one\n\n' + ('x' * 100))
        self.assertTrue(headline.startswith('one'))
        self.assertTrue(headline.endswith('…'))

    def test_extract_error_headline_falls_back_when_content_line_is_blank(self):
        headline = worker_logic.extract_error_headline('対象: foo.epub\n内容:   \n詳細: Markdown 整形エラー')
        self.assertEqual(headline, '対象: foo.epub 内容: 詳細: Markdown 整形エラー')

    def test_summarize_error_headlines_keeps_items_when_content_line_is_blank(self):
        lines = worker_logic.summarize_error_headlines([
            {'headline': '', 'error': '対象: foo.epub\n内容:   \n詳細: Markdown 整形エラー'},
        ])
        self.assertEqual(lines, ['主な原因 対象: foo.epub 内容: 詳細: Markdown 整形エラー 1件'])

    def test_summarize_error_headlines_empty_and_max_items(self):
        self.assertEqual(worker_logic.summarize_error_headlines([]), [])
        lines = worker_logic.summarize_error_headlines([
            {'headline': 'A'},
            {'headline': 'B'},
            {'headline': 'A'},
            {'headline': 'C'},
        ], max_items=1)
        self.assertEqual(lines, ['主な原因 A 2件'])

    def test_resolve_open_folder_target_for_directory_and_unknown_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.assertEqual(worker_logic.resolve_open_folder_target(root, []), root)
            self.assertIsNone(worker_logic.resolve_open_folder_target(root / 'missing', []))

    def test_resolve_open_folder_target_accepts_bytes_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')

            single_target = worker_logic.resolve_open_folder_target(src, b'exports/book.xtc')
            listed_target = worker_logic.resolve_open_folder_target(src, [b'exports/book.xtc', bytearray(b'exports/other.xtc')])

        self.assertEqual(single_target, root / 'exports')
        self.assertEqual(listed_target, root / 'exports')

    def test_build_conversion_summary_covers_remaining_message_branches(self):
        msg1, lines1 = worker_logic.build_conversion_summary(
            converted_count=2, renamed_count=0, overwritten_count=1, errors=[{'headline': 'x'}], stopped=False
        )
        self.assertEqual(msg1, '変換完了しました。(2 件を保存 / 1 件エラー)')
        self.assertIn('上書き 1 件', lines1)

        msg2, _ = worker_logic.build_conversion_summary(
            converted_count=0, renamed_count=0, overwritten_count=0, errors=[{'headline': 'x'}], stopped=False
        )
        self.assertEqual(msg2, '変換できませんでした。(1 件エラー)')

        msg3, _ = worker_logic.build_conversion_summary(
            converted_count=3, renamed_count=0, overwritten_count=0, errors=[], stopped=False
        )
        self.assertEqual(msg3, '変換完了しました。(3 件)')



    def test_summarize_error_headlines_skips_blank_entries(self):
        self.assertEqual(worker_logic.summarize_error_headlines([{'headline': '', 'error': ''}]), [])

    def test_coerce_count_handles_none_and_int(self):
        self.assertEqual(worker_logic._coerce_count(None), 0)
        self.assertEqual(worker_logic._coerce_count(5), 5)

    def test_coerce_count_clamps_negative_numeric_values(self):
        self.assertEqual(worker_logic._coerce_count(-3), 0)
        self.assertEqual(worker_logic._coerce_count(-1.9), 0)
        self.assertEqual(worker_logic._coerce_count(float('-inf')), 0)

    def test_collect_conversion_counts_clamps_negative_scalar_counts(self):
        counts = worker_logic.collect_conversion_counts(
            converted=-2,
            renamed=-1.0,
            overwritten=0,
            errors=-5,
            skipped=-3,
        )
        self.assertEqual(
            counts,
            {
                'converted': 0,
                'renamed': 0,
                'overwritten': 0,
                'errors': 0,
                'skipped': 0,
            },
        )

    def test_coerce_count_treats_single_string_path_as_one_item(self):
        self.assertEqual(worker_logic._coerce_count('result.xtc'), 1)
        self.assertEqual(worker_logic._coerce_count('   '), 0)

    def test_coerce_count_treats_empty_bytes_as_zero_items(self):
        self.assertEqual(worker_logic._coerce_count(b''), 0)
        self.assertEqual(worker_logic._coerce_count(bytearray()), 0)
        self.assertEqual(worker_logic._coerce_count(b'result.xtc'), 1)

    def test_coerce_count_treats_single_mappings_as_one_item(self):
        self.assertEqual(worker_logic._coerce_count({'desired_path': 'a.xtc', 'final_path': 'b.xtc'}), 1)
        self.assertEqual(worker_logic._coerce_count({'error': 'failed'}), 1)
        self.assertEqual(worker_logic._coerce_count({}), 0)

    def test_coerce_count_ignores_blank_entries_inside_sequences(self):
        self.assertEqual(
            worker_logic._coerce_count(['result.xtc', '', '   ', None, b'', bytearray(), {}, {'error': 'failed'}]),
            2,
        )

    def test_collect_conversion_counts_ignores_blank_entries_inside_iterables(self):
        counts = worker_logic.collect_conversion_counts(
            converted=['result.xtc', '', '   ', None],
            renamed=[{}, {'final_path': 'result_2.xtc'}],
            overwritten=[None, '', b'', bytearray()],
            errors=[{}, {'error': 'failed'}, '   ', None],
            skipped=(item for item in ['', 'skip-a', None]),
        )
        self.assertEqual(
            counts,
            {
                'converted': 1,
                'renamed': 1,
                'overwritten': 0,
                'errors': 1,
                'skipped': 1,
            },
        )

    def test_normalize_target_path_text_strips_wrapping_quotes(self):
        self.assertEqual(worker_logic.normalize_target_path_text('  "C:/books/book.epub"  '), 'C:/books/book.epub')
        self.assertEqual(worker_logic.normalize_target_path_text("  'book.epub'  "), 'book.epub')

    def test_normalize_target_path_text_preserves_unbalanced_quotes(self):
        self.assertEqual(worker_logic.normalize_target_path_text('  "book.epub  '), '"book.epub')

    def test_resolve_open_folder_target_strips_wrapping_quotes_from_relative_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            target = worker_logic.resolve_open_folder_target(
                src,
                [' "exports/book.xtc" ', " 'exports/other.xtc' "],
            )
        self.assertEqual(target, root / 'exports')

    def test_resolve_open_folder_target_strips_wrapping_quotes_from_windows_like_paths(self):
        src = Path('C:/src/book.epub')
        with mock.patch.object(worker_logic.os.path, 'normcase', side_effect=lambda value: str(value).replace('\\', '/').lower()):
            target = worker_logic.resolve_open_folder_target(
                src,
                [' "C:/Exports/book.xtc" ', " 'c:\\exports\\other.xtc' "],
            )
        self.assertEqual(str(target), r'C:\Exports')

    def test_resolve_open_folder_target_accepts_single_string_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            out_dir = root / 'exports'
            out_dir.mkdir()
            target = worker_logic.resolve_open_folder_target(src, str(out_dir / 'book.xtc'))
        self.assertEqual(target, out_dir)

    def test_resolve_open_folder_target_accepts_single_pathlike_object(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            out_dir = root / 'exports'
            out_dir.mkdir()
            target = worker_logic.resolve_open_folder_target(src, PurePosixPath(str(out_dir / 'book.xtc')))
        self.assertEqual(target, out_dir)

    def test_resolve_open_folder_target_normalizes_parent_dot_segments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            out_dir = root / 'exports'
            nested = out_dir / 'nested'
            nested.mkdir(parents=True)
            target = worker_logic.resolve_open_folder_target(
                src,
                [out_dir / 'one.xtc', nested / '..' / 'two.xtc'],
            )
        self.assertEqual(target, out_dir)

    def test_resolve_open_folder_target_normalizes_windows_like_parent_keys(self):
        src = Path('C:/src/book.epub')
        with mock.patch.object(worker_logic.os.path, 'normcase', side_effect=lambda value: str(value).replace('\\', '/').lower()):
            target = worker_logic.resolve_open_folder_target(
                src,
                [r'C:\Exports\one.xtc', r'c:/exports/sub/../two.xtc'],
            )
        self.assertEqual(str(target), r'C:\Exports')

    def test_resolve_open_folder_target_uses_input_parent_for_relative_leaf_outputs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            target = worker_logic.resolve_open_folder_target(src, ['book.xtc'])
        self.assertEqual(target, root)

    def test_resolve_open_folder_target_uses_input_base_for_relative_subdirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'source'
            src.mkdir()
            out_dir = src / 'exports'
            target = worker_logic.resolve_open_folder_target(src, ['exports/one.xtc', 'exports/two.xtc'])
        self.assertEqual(target, out_dir)



    def test_resolve_open_folder_target_uses_input_base_for_relative_windows_subdirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            target = worker_logic.resolve_open_folder_target(src, [r'exports\one.xtc', r'exports\two.xtc'])
        self.assertEqual(target, root / 'exports')
    def test_normalize_path_match_key_casefolds_windows_like_paths_without_host_os_help(self):
        self.assertEqual(
            worker_logic._normalize_path_match_key(r'C:\Exports\Result.XTC'),
            worker_logic._normalize_path_match_key(r'c:/exports/result.xtc'),
        )


    def test_normalize_path_match_key_supports_mixed_separator_windows_style_paths(self):
        self.assertEqual(
            worker_logic._normalize_path_match_key(r'exports/sub\Result.XTC'),
            worker_logic._normalize_path_match_key(r'exports\sub/result.xtc'),
        )

    def test_resolve_open_folder_target_uses_input_base_for_mixed_separator_windows_subdirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            src = root / 'book.epub'
            src.write_text('x', encoding='utf-8')
            target = worker_logic.resolve_open_folder_target(
                src,
                [r'exports/sub\one.xtc', r'exports\sub/two.xtc'],
            )
        self.assertEqual(target, root / 'exports' / 'sub')

    def test_build_conversion_summary_decodes_bytes_inside_error_mappings(self):
        msg, summary_lines = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors=[
                {
                    'error': '対象: foo.epub\n内容: Markdown 整形エラー'.encode('utf-8'),
                    'headline': bytearray('画像処理エラー'.encode('utf-8')),
                    'source': Path('foo.epub'),
                }
            ],
            stopped=False,
        )
        self.assertEqual(msg, '変換できませんでした。(1 件エラー)')
        self.assertIn('エラー 1 件', summary_lines)
        self.assertIn('主な原因 画像処理エラー 1件', summary_lines)

    def test_build_conversion_summary_extracts_headline_from_bytes_error_mapping_when_headline_missing(self):
        msg, summary_lines = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors=[
                {
                    'error': bytearray('対象: foo.epub\n内容: Markdown 整形エラー'.encode('utf-8')),
                    'display': Path('foo.epub'),
                }
            ],
            stopped=False,
        )
        self.assertEqual(msg, '変換できませんでした。(1 件エラー)')
        self.assertIn('エラー 1 件', summary_lines)
        self.assertIn('主な原因 Markdown 整形エラー 1件', summary_lines)

    def test_build_conversion_summary_includes_skip_count(self):
        msg, summary_lines = worker_logic.build_conversion_summary(
            converted_count=0,
            renamed_count=0,
            overwritten_count=0,
            errors=[],
            stopped=False,
            skipped_count=2,
        )
        self.assertEqual(msg, '変換対象はありませんでした。(2 件スキップ)')
        self.assertIn('スキップ 2 件', summary_lines)

    def test_build_conversion_summary_clamps_negative_counts(self):
        msg, summary_lines = worker_logic.build_conversion_summary(
            converted_count=-2,
            renamed_count=-1,
            overwritten_count=-3,
            errors=[],
            stopped=False,
            skipped_count=-4,
        )
        self.assertEqual(msg, '変換完了しました。(0 件)')
        self.assertIn('保存 0 件', summary_lines)
        self.assertIn('自動連番 0 件', summary_lines)
        self.assertIn('上書き 0 件', summary_lines)
        self.assertFalse(any('スキップ' in line for line in summary_lines))


    def test_build_conversion_summary_accepts_numeric_like_scalar_counts(self):
        msg, summary_lines = worker_logic.build_conversion_summary(
            converted_count='2',
            renamed_count=b'3',
            overwritten_count=' 4.0 ',
            errors=[],
            stopped=False,
            skipped_count=bytearray(b'5'),
        )
        self.assertEqual(msg, '変換完了しました。(2 件)')
        self.assertIn('保存 2 件', summary_lines)
        self.assertIn('自動連番 3 件', summary_lines)
        self.assertIn('上書き 4 件', summary_lines)
        self.assertIn('スキップ 5 件', summary_lines)

    def test_build_conversion_summary_treats_invalid_scalar_count_text_as_zero(self):
        msg, summary_lines = worker_logic.build_conversion_summary(
            converted_count='done',
            renamed_count=b'bad',
            overwritten_count='nan',
            errors=[],
            stopped=False,
            skipped_count=bytearray(b'\xff'),
        )
        self.assertEqual(msg, '変換完了しました。(0 件)')
        self.assertIn('保存 0 件', summary_lines)
        self.assertIn('自動連番 0 件', summary_lines)
        self.assertIn('上書き 0 件', summary_lines)
        self.assertFalse(any('スキップ' in line for line in summary_lines))


if __name__ == '__main__':
    unittest.main()
