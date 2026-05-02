from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import tategakiXTC_gui_studio_logic as logic


class GuiStudioLogicRegressionTests(unittest.TestCase):
    def test_build_top_status_message_for_empty_target(self):
        self.assertEqual(logic.build_top_status_message('', 'X4', 32, 14), '変換対象を選択してください。')

    def test_build_top_status_message_for_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / 'book.epub'
            target.write_text('x', encoding='utf-8')
            message = logic.build_top_status_message(str(target), 'X4', 32, 14)
            self.assertIn('ファイル: book.epub', message)
            self.assertIn('X4 / 本文32 / 行間14', message)

    def test_build_top_status_message_for_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            message = logic.build_top_status_message(tmpdir, 'X3', 30, 12)
            self.assertIn('フォルダ:', message)
            self.assertIn('X3 / 本文30 / 行間12', message)

    def test_build_top_status_message_does_not_probe_filesystem(self):
        with mock.patch.object(Path, 'is_dir', side_effect=AssertionError('status must not stat path')):
            message = logic.build_top_status_message('C:/very/large/book.epub', 'X4', 26, 44)
        self.assertIn('ファイル: book.epub', message)

    def test_should_prompt_for_output_name(self):
        self.assertTrue(logic.should_prompt_for_output_name(1, True))
        self.assertFalse(logic.should_prompt_for_output_name(1, False))
        self.assertFalse(logic.should_prompt_for_output_name(0, True))
        self.assertFalse(logic.should_prompt_for_output_name(2, True))

    def test_suggest_output_name_prefers_saved_name(self):
        self.assertEqual(logic.suggest_output_name('saved', 'default'), 'saved')

    def test_suggest_output_name_falls_back_to_default_and_output(self):
        self.assertEqual(logic.suggest_output_name('', 'default'), 'default')
        self.assertEqual(logic.suggest_output_name('', ''), 'output')

    def test_suggest_output_name_for_target_reuses_only_same_source(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'memo.txt'
            other = Path(tmpdir) / 'book.epub'
            self.assertEqual(
                logic.suggest_output_name_for_target(
                    'saved-name',
                    'memo',
                    target_path=src,
                    last_output_source=src,
                ),
                'saved-name',
            )
            self.assertEqual(
                logic.suggest_output_name_for_target(
                    'book-name',
                    'memo',
                    target_path=src,
                    last_output_source=other,
                ),
                'memo',
            )
            self.assertEqual(
                logic.suggest_output_name_for_target(
                    'book-name',
                    'memo',
                    target_path=src,
                    last_output_source='',
                ),
                'memo',
            )

    def test_build_running_results_summary(self):
        self.assertIn('変換中です', logic.build_running_results_summary())

    def test_build_start_log_message(self):
        self.assertEqual(logic.build_start_log_message('xtc', 1), '変換を開始しました。(xtc)')
        self.assertEqual(logic.build_start_log_message('xtch', 3), '変換を開始しました。(xtch, 3件)')


    def test_build_progress_status_text_includes_counts_and_percent(self):
        self.assertEqual(logic.build_progress_status_text(3, 5, '更新中'), '更新中 (3/5, 60%)')
        self.assertEqual(logic.build_progress_status_text(0, 0, ''), '変換中… (0/1, 0%)')
        self.assertEqual(logic.build_progress_status_text('9', '5', b'bytes'), 'bytes (5/5, 100%)')


    def test_build_conversion_failure_summary_text_combines_prefix_and_message(self):
        self.assertEqual(
            logic.build_conversion_failure_summary_text('開始エラー', '入力がありません'),
            '開始エラー: 入力がありません',
        )

    def test_build_conversion_failure_summary_text_uses_message_without_prefix(self):
        self.assertEqual(logic.build_conversion_failure_summary_text('', '失敗しました'), '失敗しました')

    def test_build_conversion_failure_summary_text_falls_back_to_unknown_error(self):
        self.assertEqual(logic.build_conversion_failure_summary_text('エラー', ''), 'エラー: 不明なエラー')

    def test_render_failure_status_text_helpers(self):
        self.assertTrue(logic.is_preview_render_failure_status_text('プレビュー表示エラー: broken'))
        self.assertTrue(logic.is_preview_render_failure_status_text('プレビュー生成エラー'))
        self.assertFalse(logic.is_preview_render_failure_status_text('プレビュー更新完了'))
        self.assertTrue(logic.is_device_render_failure_status_text('ページ表示エラー: broken'))
        self.assertFalse(logic.is_device_render_failure_status_text('ページ 1 / 3'))
        self.assertTrue(logic.is_render_failure_status_text('ページ表示エラー: broken'))
        self.assertTrue(logic.is_render_failure_status_text('プレビュー生成エラー: broken'))
        self.assertFalse(logic.is_render_failure_status_text('変換中…'))

    def test_display_context_name_from_label_text(self):
        self.assertEqual(logic.display_context_name_from_label_text('表示中: book.xtc'), 'book.xtc')
        self.assertEqual(logic.display_context_name_from_label_text(' 表示中: なし '), 'なし')
        self.assertEqual(logic.display_context_name_from_label_text('book.xtc'), 'book.xtc')

    def test_render_failure_preserved_display_name_extracts_visible_name(self):
        self.assertEqual(
            logic.render_failure_preserved_display_name('ページ表示エラー: broken（表示は sample.xtc のまま）'),
            'sample.xtc',
        )
        self.assertEqual(
            logic.render_failure_preserved_display_name('プレビュー表示エラー（表示は プレビュー のまま）'),
            'プレビュー',
        )
        self.assertEqual(logic.render_failure_preserved_display_name('ページ表示エラー: broken'), '')
        self.assertEqual(logic.render_failure_preserved_display_name('ページ表示エラー（表示は 未完了'), '')


    def test_render_failure_matches_display_context_compares_only_when_both_names_exist(self):
        self.assertTrue(
            logic.render_failure_matches_display_context(
                'ページ表示エラー: broken（表示は sample.xtc のまま）',
                'sample.xtc',
            )
        )
        self.assertFalse(
            logic.render_failure_matches_display_context(
                'ページ表示エラー: broken（表示は sample.xtc のまま）',
                'other.xtc',
            )
        )
        self.assertTrue(logic.render_failure_matches_display_context('ページ表示エラー: broken', 'sample.xtc'))
        self.assertTrue(
            logic.render_failure_matches_display_context(
                'ページ表示エラー: broken（表示は sample.xtc のまま）',
                '',
            )
        )

    def test_normalize_choice_value_accepts_known_values_only(self):
        self.assertEqual(logic.normalize_choice_value(' XTCH ', 'xtc', {'xtc', 'xtch'}), 'xtch')
        self.assertEqual(logic.normalize_choice_value('broken', 'xtc', {'xtc', 'xtch'}), 'xtc')

    def test_payload_optional_int_value_handles_legacy_strings_and_invalid_values(self):
        self.assertEqual(logic.payload_optional_int_value({'value': ' 42 '}, 'value'), 42)
        self.assertEqual(logic.payload_optional_int_value({'value': '7.9'}, 'value'), 7)
        self.assertIsNone(logic.payload_optional_int_value({'value': 'broken'}, 'value'))

    def test_payload_splitter_sizes_value_falls_back_safely(self):
        self.assertEqual(
            logic.payload_splitter_sizes_value({'sizes': ['broken', None]}, 'sizes', [760, 140]),
            [760, 140],
        )
        self.assertEqual(
            logic.payload_splitter_sizes_value({'sizes': ['120', '80']}, 'sizes', [760, 140]),
            [280, 92],
        )

    def test_build_window_state_restore_payload_normalizes_legacy_values(self):
        payload = logic.build_window_state_restore_payload(
            {
                'geometry': b'geom',
                'window_width': 'broken',
                'window_height': '',
                'is_maximized': '1',
                'left_panel_width': 'bad',
                'left_splitter_state': b'split',
                'left_splitter_sizes': ['oops', None],
                'left_panel_visible': '0',
            },
            default_width=1600,
            default_height=1000,
            default_left_panel_width=620,
            default_left_splitter_sizes=[760, 140],
        )
        self.assertEqual(payload['geometry'], b'geom')
        self.assertEqual((payload['window_width'], payload['window_height']), (1600, 1000))
        self.assertTrue(payload['is_maximized'])
        self.assertEqual(payload['left_panel_width'], 620)
        self.assertEqual(payload['left_splitter_state'], b'split')
        self.assertEqual(payload['left_splitter_sizes'], [760, 140])
        self.assertFalse(payload['left_panel_visible'])

    def test_build_window_state_restore_payload_ignores_non_mapping_payload(self):
        payload = logic.build_window_state_restore_payload(
            'bad-payload',
            default_width=1600,
            default_height=1000,
            default_left_panel_width=620,
            default_left_splitter_sizes=[760, 140],
        )
        self.assertEqual((payload['window_width'], payload['window_height']), (1600, 1000))
        self.assertFalse(payload['is_maximized'])
        self.assertEqual(payload['left_panel_width'], 620)
        self.assertEqual(payload['left_splitter_sizes'], [760, 140])
        self.assertTrue(payload['left_panel_visible'])

    def test_build_window_state_save_payload_normalizes_sizes_and_optional_fields(self):
        payload = logic.build_window_state_save_payload(
            {
                'geometry': b'geom',
                'window_width': '900',
                'window_height': '700',
                'is_maximized': '0',
                'left_panel_width': '512',
                'left_splitter_state': b'split',
                'left_splitter_top': '310',
                'left_splitter_bottom': '210',
                'left_panel_visible': 'false',
            }
        )
        self.assertEqual(payload['geometry'], b'geom')
        self.assertEqual((payload['window_width'], payload['window_height']), (1100, 760))
        self.assertFalse(payload['is_maximized'])
        self.assertEqual(payload['left_panel_width'], 512)
        self.assertEqual(payload['left_splitter_state'], b'split')
        self.assertEqual((payload['left_splitter_top'], payload['left_splitter_bottom']), (310, 210))
        self.assertFalse(payload['left_panel_visible'])

    def test_build_settings_restore_payload_normalizes_choice_and_bool_values(self):
        payload = logic.build_settings_restore_payload(
            {
                'profile': 'weird',
                'actual_size': '1',
                'show_guides': 'off',
                'calibration_pct': 'bad',
                'nav_buttons_reversed': 'yes',
                'font_size': '31',
                'ruby_size': 'bad',
                'line_spacing': '41',
                'margin_t': '13',
                'margin_b': None,
                'margin_r': '17',
                'margin_l': 'oops',
                'threshold': '130',
                'width': '528',
                'height': '792',
                'preview_page_limit': '0',
                'dither': 'true',
                'night_mode': '0',
                'open_folder': 'off',
                'output_format': 'bad',
                'output_conflict': 'oops',
                'kinsoku_mode': 'broken',
                'target': '  "book.epub"  ',
                'font_file': ' font.ttf ',
                'main_view_mode': 'broken',
                'bottom_tab_index': 'bad',
            },
            allowed_view_modes={'font', 'device'},
            allowed_profiles={'x4', 'x3', 'custom'},
            allowed_kinsoku_modes={'standard', 'strict'},
            allowed_output_formats={'xtc', 'xtch'},
            allowed_output_conflicts={'rename', 'overwrite'},
            default_preview_page_limit=10,
        )
        self.assertEqual(payload['profile'], 'x4')
        self.assertTrue(payload['actual_size'])
        self.assertFalse(payload['show_guides'])
        self.assertEqual(payload['calibration_pct'], 100)
        self.assertTrue(payload['nav_buttons_reversed'])
        self.assertEqual(payload['font_size'], 31)
        self.assertEqual(payload['ruby_size'], 12)
        self.assertEqual(payload['line_spacing'], 41)
        self.assertEqual(payload['margin_t'], 13)
        self.assertEqual(payload['margin_b'], 14)
        self.assertEqual(payload['margin_r'], 17)
        self.assertEqual(payload['margin_l'], 12)
        self.assertEqual(payload['threshold'], 130)
        self.assertEqual((payload['width'], payload['height']), (528, 792))
        self.assertEqual(payload['preview_page_limit'], 1)
        self.assertTrue(payload['dither'])
        self.assertFalse(payload['night_mode'])
        self.assertFalse(payload['open_folder'])
        self.assertEqual(payload['output_format'], 'xtc')
        self.assertEqual(payload['output_conflict'], 'rename')
        self.assertEqual(payload['kinsoku_mode'], 'standard')
        self.assertEqual(payload['target'], '"book.epub"')
        self.assertEqual(payload['font_file'], 'font.ttf')
        self.assertEqual(payload['main_view_mode'], 'font')
        self.assertEqual(payload['bottom_tab_index'], 0)

    def test_build_settings_ui_apply_payload_normalizes_present_fields_only(self):
        payload = logic.build_settings_ui_apply_payload(
            {
                'actual_size': '0',
                'show_guides': 'on',
                'calibration_pct': 'bad',
                'font_size': '31',
                'preview_page_limit': '0',
                'output_format': 'bad',
                'output_conflict': 'overwrite',
                'kinsoku_mode': 'broken',
                'main_view_mode': 'broken',
                'target': '  input.epub  ',
                'font_file': ' font.ttf ',
                'bottom_tab_index': '5',
            },
            defaults={
                'actual_size': True,
                'show_guides': False,
                'calibration_pct': 100,
                'font_size': 26,
                'preview_page_limit': 10,
                'output_format': 'xtc',
                'output_conflict': 'rename',
                'kinsoku_mode': 'standard',
                'main_view_mode': 'font',
            },
            allowed_view_modes={'font', 'device'},
            allowed_kinsoku_modes={'standard', 'strict'},
            allowed_output_formats={'xtc', 'xtch'},
            allowed_output_conflicts={'rename', 'overwrite'},
            bottom_tab_count=2,
        )
        self.assertFalse(payload['actual_size'])
        self.assertTrue(payload['show_guides'])
        self.assertEqual(payload['calibration_pct'], 100)
        self.assertEqual(payload['font_size'], 31)
        self.assertEqual(payload['preview_page_limit'], 1)
        self.assertEqual(payload['output_format'], 'xtc')
        self.assertEqual(payload['output_conflict'], 'overwrite')
        self.assertEqual(payload['kinsoku_mode'], 'standard')
        self.assertEqual(payload['main_view_mode'], 'font')
        self.assertEqual(payload['target'], 'input.epub')
        self.assertEqual(payload['font_file'], 'font.ttf')
        self.assertNotIn('bottom_tab_index', payload)
        self.assertNotIn('night_mode', payload)

    def test_build_settings_ui_apply_payload_ignores_non_mapping_payloads(self):
        payload = logic.build_settings_ui_apply_payload(
            'bad-payload',
            defaults='bad-defaults',
            allowed_view_modes={'font', 'device'},
            allowed_kinsoku_modes={'standard', 'strict'},
            allowed_output_formats={'xtc', 'xtch'},
            allowed_output_conflicts={'rename', 'overwrite'},
            bottom_tab_count=2,
        )
        self.assertEqual(payload, {})

    def test_build_settings_save_payload_normalizes_choice_and_bool_values(self):
        payload = logic.build_settings_save_payload(
            {
                'bottom_tab_index': '-5',
                'main_view_mode': 'broken',
                'ui_theme': '',
                'panel_button_visible': '0',
                'preset_index': '-2',
                'preset_key': ' preset_1 ',
                'profile': 'weird',
                'actual_size': '1',
                'show_guides': 'false',
                'calibration_pct': '105',
                'nav_buttons_reversed': 'yes',
                'preview_page_limit': '0',
                'target': '  "book.epub"  ',
                'font_file': ' font.ttf ',
                'dither': '1',
                'night_mode': '0',
                'open_folder': 'true',
                'output_format': 'bad',
                'output_conflict': 'oops',
                'kinsoku_mode': 'broken',
                'width': '528',
                'height': '792',
            },
            allowed_view_modes={'font', 'device'},
            allowed_profiles={'x4', 'x3', 'custom'},
            allowed_kinsoku_modes={'standard', 'strict'},
            allowed_output_formats={'xtc', 'xtch'},
            allowed_output_conflicts={'rename', 'overwrite'},
            default_preview_page_limit=10,
        )
        self.assertEqual(payload['bottom_tab_index'], 0)
        self.assertEqual(payload['main_view_mode'], 'font')
        self.assertEqual(payload['ui_theme'], 'light')
        self.assertFalse(payload['panel_button_visible'])
        self.assertEqual(payload['preset_index'], -1)
        self.assertEqual(payload['preset_key'], 'preset_1')
        self.assertEqual(payload['profile'], 'x4')
        self.assertTrue(payload['actual_size'])
        self.assertFalse(payload['show_guides'])
        self.assertEqual(payload['calibration_pct'], 105)
        self.assertTrue(payload['nav_buttons_reversed'])
        self.assertEqual(payload['preview_page_limit'], 1)
        self.assertEqual(payload['target'], '"book.epub"')
        self.assertEqual(payload['font_file'], 'font.ttf')
        self.assertTrue(payload['dither'])
        self.assertFalse(payload['night_mode'])
        self.assertTrue(payload['open_folder'])
        self.assertEqual(payload['output_format'], 'xtc')
        self.assertEqual(payload['output_conflict'], 'rename')
        self.assertEqual(payload['kinsoku_mode'], 'standard')
        self.assertEqual((payload['width'], payload['height']), (528, 792))

    def test_build_displaying_document_label_uses_fallback(self):
        self.assertEqual(logic.build_displaying_document_label('book.xtc'), '表示中: book.xtc')
        self.assertEqual(logic.build_displaying_document_label(''), '表示中: なし')

    def test_build_preview_status_message_variants(self):
        self.assertEqual(logic.build_preview_status_message('dirty'), '設定変更あり（未反映）')
        self.assertEqual(
            logic.build_preview_status_message('running', preview_limit=10),
            '先頭 10 ページまでプレビューを更新しています…',
        )
        self.assertEqual(logic.build_preview_status_message('empty'), 'プレビューを生成できませんでした')
        self.assertEqual(
            logic.build_preview_status_message('complete', generated_pages=3, preview_limit=10, truncated=False),
            'プレビュー更新完了（3 / 上限 10 ページ）',
        )
        self.assertEqual(
            logic.build_preview_status_message('complete', generated_pages=10, preview_limit=10, truncated=True),
            '先頭 10 / 上限 10 ページを生成しました。',
        )
        self.assertEqual(
            logic.build_preview_status_message('error', error='boom'),
            'プレビュー生成エラー: boom',
        )

    def test_build_preview_status_message_normalizes_invalid_numeric_values(self):
        self.assertEqual(
            logic.build_preview_status_message('running', preview_limit='bad-limit'),
            '先頭 0 ページまでプレビューを更新しています…',
        )
        self.assertEqual(
            logic.build_preview_status_message('complete', generated_pages='bad-pages', preview_limit='bad-limit', truncated=True),
            '先頭 0 / 上限 0 ページを生成しました。',
        )

    def test_build_preview_progress_message_prefers_detail_and_has_fallback(self):
        self.assertEqual(
            logic.build_preview_progress_message(2, 10, 'プレビューページを作成中… (2/10 ページ)', preview_limit=10),
            'プレビューページを作成中… (2/10 ページ)',
        )
        self.assertEqual(
            logic.build_preview_progress_message(2, 10, 'プレビュー画像を準備しています…', preview_limit=10),
            'プレビュー画像を準備しています… (2/10)',
        )
        self.assertEqual(
            logic.build_preview_progress_message(2, 10, '', preview_limit=10),
            'プレビューを更新しています… (2/10)',
        )
        self.assertEqual(
            logic.build_preview_progress_message(None, None, None, preview_limit=8),
            '先頭 8 ページまでプレビューを更新しています…',
        )

    def test_build_preview_refresh_state_handles_empty_and_clamps_indices(self):
        empty = logic.build_preview_refresh_state(
            page_count=0,
            reset_page=False,
            current_preview_index=4,
            current_device_index=9,
            preview_limit=10,
            truncated=False,
        )
        self.assertFalse(empty['has_pages'])
        self.assertEqual((empty['preview_index'], empty['device_index']), (0, 0))
        self.assertEqual(empty['status_message'], 'プレビューを生成できませんでした')

        clamped = logic.build_preview_refresh_state(
            page_count=3,
            reset_page=False,
            current_preview_index=8,
            current_device_index='-2',
            preview_limit=10,
            truncated=True,
        )
        self.assertTrue(clamped['has_pages'])
        self.assertEqual((clamped['preview_index'], clamped['device_index']), (2, 0))
        self.assertEqual(clamped['generated_pages'], 3)
        self.assertEqual(clamped['status_message'], '先頭 3 / 上限 10 ページを生成しました。')

        reset = logic.build_preview_refresh_state(
            page_count=2,
            reset_page=True,
            current_preview_index=1,
            current_device_index=1,
            preview_limit=5,
            truncated=False,
        )
        self.assertEqual((reset['preview_index'], reset['device_index']), (0, 0))

    def test_build_preview_error_state_preserves_xtc_device_view(self):
        keep_xtc = logic.build_preview_error_state(device_view_source='xtc', error='boom')
        self.assertFalse(keep_xtc['clear_device_page'])
        self.assertEqual(keep_xtc['status_message'], 'プレビュー生成エラー: boom')

        clear_preview = logic.build_preview_error_state(device_view_source='preview', error='boom')
        self.assertTrue(clear_preview['clear_device_page'])
        self.assertEqual(clear_preview['device_index'], 0)

    def test_build_navigation_display_state_clamps_and_marks_truncation(self):
        state = logic.build_navigation_display_state(view_mode='font', total=3, current_index=9, truncated=True)
        self.assertTrue(state['active'])
        self.assertEqual(state['current_index'], 2)
        self.assertEqual(state['current_page'], 3)
        self.assertTrue(state['can_go_prev'])
        self.assertFalse(state['can_go_next'])
        self.assertEqual(state['total_label'], '/ 3+')
        self.assertEqual(state['view_mode'], 'font')



    def test_build_preset_helpers_keep_summary_labels_stable(self):
        preset = {
            'button_text': 'プリセット4',
            'name': '標準',
            'profile': 'broken',
            'font_size': '32',
            'ruby_size': '13',
            'line_spacing': '44',
            'margin_t': '12',
            'margin_b': '14',
            'margin_r': '12',
            'margin_l': '12',
            'night_mode': 'false',
            'dither': '1',
            'kinsoku_mode': 'weird',
            'output_format': 'xtch',
        }
        self.assertEqual(logic.build_preset_display_name(preset), 'プリセット4 / 標準')
        summary = logic.build_preset_summary_html(
            preset,
            font_text='Noto Serif',
            device_profile_keys=['x4', 'x3', 'custom'],
            kinsoku_mode_labels={'standard': '標準'},
            output_format_labels={'xtc': 'XTC', 'xtch': 'XTCH'},
            summary_tag='（現在の設定）',
        )
        self.assertIn('プリセット4 / 標準', summary)
        self.assertIn('（現在の設定）', summary)
        self.assertIn('機種: X4', summary)
        self.assertIn('フォント: Noto Serif', summary)
        self.assertIn('出力形式: XTCH', summary)
        self.assertIn('白黒反転: OFF', summary)
        self.assertIn('ディザ: ON', summary)
        self.assertIn('しきい値: 128', summary)
        self.assertIn('禁則: 標準', summary)
        self.assertNotIn('<table', summary)
        self.assertNotIn('align="right"', summary)
        self.assertIn('text-align:left', summary)
        self.assertGreaterEqual(summary.count('<div style="margin:0; padding:0;">'), 4)
        compact_summary = logic.build_preset_summary_html(
            preset,
            font_text='Noto Serif',
            device_profile_keys=['x4', 'x3', 'custom'],
            kinsoku_mode_labels={'standard': '標準'},
            output_format_labels={'xtc': 'XTC', 'xtch': 'XTCH'},
            summary_tag='（現在の設定）',
            include_name_line=False,
        )
        self.assertNotIn('プリセット4 / 標準', compact_summary)
        self.assertNotIn('（現在の設定）', compact_summary)
        self.assertIn('機種: X4', compact_summary)
        self.assertIn('フォント: Noto Serif', compact_summary)
        self.assertEqual(compact_summary.count('<div style="margin:0; padding:0;">'), 3)

    def test_build_preset_summary_text_for_dialog(self):
        preset = {
            'button_text': 'プリセット4',
            'name': '標準',
            'profile': 'x4',
            'font_size': 26,
            'ruby_size': 12,
            'line_spacing': 41,
            'margin_t': 12,
            'margin_b': 14,
            'margin_r': 12,
            'margin_l': 12,
            'night_mode': 'false',
            'dither': '0',
            'threshold': 128,
            'kinsoku_mode': 'standard',
            'output_format': 'xtch',
        }
        summary = logic.build_preset_summary_text(
            preset,
            font_text='NotoSerifJP-Medium.ttf',
            device_profile_keys=['x4', 'x3'],
            kinsoku_mode_labels={'standard': '標準'},
            output_format_labels={'xtc': 'XTC', 'xtch': 'XTCH'},
        )
        self.assertIn('プリセット4 / 標準', summary)
        self.assertIn('機種: X4 / 出力形式: XTCH / 本文: 26 / ルビ: 12 / 行間: 41', summary)
        self.assertIn('余白: 上 12 下 14 右 12 左 12 / 白黒反転: OFF / ディザ: OFF / しきい値: 128 / 禁則: 標準', summary)
        self.assertIn('フォント: NotoSerifJP-Medium.ttf', summary)
        self.assertNotIn('<div', summary)
        self.assertEqual(summary.count('\n'), 3)
        compact_summary = logic.build_preset_summary_text(
            preset,
            font_text='NotoSerifJP-Medium.ttf',
            device_profile_keys=['x4', 'x3'],
            kinsoku_mode_labels={'standard': '標準'},
            output_format_labels={'xtc': 'XTC', 'xtch': 'XTCH'},
            include_name_line=False,
        )
        self.assertNotIn('プリセット4 / 標準', compact_summary)
        self.assertTrue(compact_summary.startswith('機種: X4 / 出力形式: XTCH'))
        self.assertIn('フォント: NotoSerifJP-Medium.ttf', compact_summary)
        self.assertEqual(compact_summary.count('\n'), 2)
        self.assertNotIn('\n\n', compact_summary)
        self.assertFalse(compact_summary.endswith('\n'))
        self.assertEqual(
            logic.compact_multiline_label_text(f'{compact_summary}\n\n'),
            compact_summary,
        )

    def test_build_result_helpers_handle_windows_and_summary_lines(self):
        self.assertEqual(logic.build_result_display_name(r'C:\work\book.xtc'), 'book.xtc')
        self.assertEqual(logic.build_result_display_name('/tmp/result.xtch'), 'result.xtch')
        self.assertEqual(
            logic.build_results_summary_message(['保存 2 件', '', 'エラー 0 件'], 0),
            '保存 2 件 / エラー 0 件',
        )
        self.assertEqual(logic.build_results_summary_message([], 2), '保存ファイル: 2 件')




    def test_merge_unique_message_values_preserves_order_and_deduplicates(self):
        self.assertEqual(
            logic.merge_unique_message_values(['警告A', ' ', '警告B'], ['警告A', '警告C', None]),
            ['警告A', '警告B', '警告C'],
        )

    def test_build_render_failure_status_message_preserves_context_and_detail(self):
        self.assertEqual(
            logic.build_render_failure_status_message('ページ表示エラー', 'boom', 'book.xtc'),
            'ページ表示エラー（表示は book.xtc のまま）: boom',
        )
        self.assertEqual(
            logic.build_render_failure_status_message('', ''),
            '表示エラー',
        )

    def test_build_render_failure_status_message_normalizes_base64_detail(self):
        self.assertEqual(
            logic.build_render_failure_status_message('ページ表示エラー', 'Non-base64 digit found'),
            'ページ表示エラー: Only base64 data is allowed',
        )

    def test_build_xtc_load_failure_status_message_preserves_context_and_detail(self):
        self.assertEqual(
            logic.build_xtc_load_failure_status_message('broken.xtc', 'boom', 'preview.xtc'),
            'XTC/XTCH読込失敗: broken.xtc（表示は preview.xtc のまま） / boom',
        )
        self.assertEqual(
            logic.build_xtc_load_failure_status_message('', ''),
            'XTC/XTCH読込失敗: 指定ファイル',
        )

    def test_build_xtc_load_failure_status_message_normalizes_base64_detail(self):
        self.assertEqual(
            logic.build_xtc_load_failure_status_message('broken.xtch', 'Non-base64 digit found'),
            'XTC/XTCH読込失敗: broken.xtch / Only base64 data is allowed',
        )

    def test_normalize_xtc_bytes_accepts_bytes_like_values(self):
        raw = b'xtc-data'
        self.assertIs(logic.normalize_xtc_bytes(raw), raw)
        self.assertEqual(logic.normalize_xtc_bytes(bytearray(raw)), raw)
        self.assertEqual(logic.normalize_xtc_bytes(memoryview(raw)), raw)

    def test_normalize_xtc_bytes_rejects_non_bytes_values(self):
        with self.assertRaisesRegex(TypeError, 'XTCデータは bytes 系である必要があります'):
            logic.normalize_xtc_bytes('not-bytes')

    def test_build_xtc_document_payload_from_pages_sets_initial_navigation(self):
        page1 = object()
        page2 = object()

        payload = logic.build_xtc_document_payload_from_pages(b'xtc-data', (page1, page2))

        self.assertEqual(payload['data'], b'xtc-data')
        self.assertEqual(payload['pages'], [page1, page2])
        self.assertEqual(payload['total'], 2)
        self.assertEqual(payload['current_index'], 0)
        self.assertEqual(payload['current_page'], 1)

    def test_build_xtc_document_payload_from_pages_rejects_empty_pages(self):
        with self.assertRaisesRegex(RuntimeError, 'XTC内にページがありません'):
            logic.build_xtc_document_payload_from_pages(b'xtc-data', [])

    def test_build_xtc_display_name_reuses_result_display_rules(self):
        self.assertEqual(logic.build_xtc_display_name(r'exports\nested\result.xtc'), 'result.xtc')
        self.assertEqual(logic.build_xtc_display_name('/tmp/books/result.xtch'), 'result.xtch')
        self.assertEqual(logic.build_xtc_display_name(''), '')

    def test_build_xtc_source_payload_uses_normalized_path_and_display_name(self):
        self.assertEqual(
            logic.build_xtc_source_payload(r'exports\nested\result.xtc', '表示名.xtc'),
            {
                'path_text': r'exports\nested\result.xtc',
                'display_name': '表示名.xtc',
            },
        )
        self.assertEqual(
            logic.build_xtc_source_payload('/tmp/books/result.xtch'),
            {
                'path_text': '/tmp/books/result.xtch',
                'display_name': 'result.xtch',
            },
        )

    def test_build_xtc_source_document_payload_merges_source_and_document_parts(self):
        source = {'path_text': '/tmp/books/result.xtc', 'display_name': 'result.xtc'}
        document = {
            'data': b'xtc-data',
            'pages': [{'image': 'A'}],
            'total': 1,
            'current_index': 0,
            'current_page': 1,
        }

        payload = logic.build_xtc_source_document_payload(source, document)

        self.assertEqual(payload['path_text'], '/tmp/books/result.xtc')
        self.assertEqual(payload['display_name'], 'result.xtc')
        self.assertEqual(payload['data'], b'xtc-data')
        self.assertEqual(payload['pages'], [{'image': 'A'}])
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['current_index'], 0)
        self.assertEqual(payload['current_page'], 1)
        self.assertIsNot(payload, source)

    def test_build_xtc_load_failure_preserved_display_name_prefers_preview(self):
        self.assertEqual(
            logic.build_xtc_load_failure_preserved_display_name(
                preview_active=True,
                remembered_display_name='old.xtc',
                remembered_path_display_name='path.xtc',
                current_label_text='表示中: label.xtc',
            ),
            'プレビュー',
        )

    def test_build_xtc_load_failure_preserved_display_name_fallback_order(self):
        self.assertEqual(
            logic.build_xtc_load_failure_preserved_display_name(
                remembered_display_name='old.xtc',
                remembered_path_display_name='path.xtc',
                current_label_text='表示中: label.xtc',
            ),
            'old.xtc',
        )
        self.assertEqual(
            logic.build_xtc_load_failure_preserved_display_name(
                remembered_display_name='なし',
                remembered_path_display_name='path.xtc',
                current_label_text='表示中: label.xtc',
            ),
            'path.xtc',
        )
        self.assertEqual(
            logic.build_xtc_load_failure_preserved_display_name(
                remembered_display_name='',
                remembered_path_display_name='なし',
                current_label_text='表示中: label.xtc',
            ),
            'label.xtc',
        )
        self.assertEqual(
            logic.build_xtc_load_failure_preserved_display_name(
                remembered_display_name='',
                remembered_path_display_name='',
                current_label_text='表示中: なし',
            ),
            '',
        )

    def test_build_xtc_page_state_payload_clamps_and_exposes_page(self):
        pages = ['page-1', 'page-2', 'page-3']

        payload = logic.build_xtc_page_state_payload(pages, 99)

        self.assertEqual(payload['total'], 3)
        self.assertEqual(payload['current_index'], 2)
        self.assertEqual(payload['current_page'], 3)
        self.assertEqual(payload['page'], 'page-3')

    def test_build_xtc_page_state_payload_handles_empty_pages(self):
        payload = logic.build_xtc_page_state_payload([], 5)

        self.assertEqual(payload['total'], 0)
        self.assertEqual(payload['current_index'], 0)
        self.assertEqual(payload['current_page'], 0)
        self.assertIsNone(payload['page'])

    def test_find_matching_result_index_returns_first_exact_key_match(self):
        self.assertEqual(
            logic.find_matching_result_index('books/result.xtc', ['other', 'books/result.xtc', 'books/result.xtc']),
            1,
        )
        self.assertIsNone(logic.find_matching_result_index('', ['books/result.xtc']))
        self.assertIsNone(logic.find_matching_result_index('missing', ['books/result.xtc']))

    def test_resolve_preferred_result_index_prefers_current_then_single_selected_then_single_item(self):
        self.assertEqual(
            logic.resolve_preferred_result_index(selected_indexes=['2'], current_index=1, item_count=3),
            1,
        )
        self.assertEqual(
            logic.resolve_preferred_result_index(selected_indexes=['2'], current_index=None, item_count=3),
            2,
        )
        self.assertEqual(
            logic.resolve_preferred_result_index(selected_indexes=[], current_index='1', item_count=3),
            1,
        )
        self.assertEqual(
            logic.resolve_preferred_result_index(selected_indexes=[], current_index=None, item_count=1),
            0,
        )
        self.assertIsNone(
            logic.resolve_preferred_result_index(selected_indexes=[], current_index=None, item_count=2),
        )

    def test_normalize_navigation_index_clamps_and_handles_empty_totals(self):
        self.assertEqual(logic.normalize_navigation_index(total=4, current_index=' 99 '), 3)
        self.assertEqual(logic.normalize_navigation_index(total=4, current_index='-2'), 0)
        self.assertEqual(logic.normalize_navigation_index(total=0, current_index=5), 0)
        self.assertEqual(logic.normalize_navigation_index(total='bad', current_index='bad'), 0)

    def test_normalize_preview_page_cache_tokens_requires_matching_count(self):
        self.assertEqual(logic.normalize_preview_page_cache_tokens(['1', 2], expected_len=2), [1, 2])
        self.assertIsNone(logic.normalize_preview_page_cache_tokens(['1'], expected_len=2))
        self.assertIsNone(logic.normalize_preview_page_cache_tokens(['bad'], expected_len=1))
        self.assertIsNone(logic.normalize_preview_page_cache_tokens('12', expected_len=2))

    def test_normalize_device_view_source_value_accepts_known_sources_only(self):
        self.assertEqual(logic.normalize_device_view_source_value(' PREVIEW '), 'preview')
        self.assertEqual(logic.normalize_device_view_source_value(b'xtc'), 'xtc')
        self.assertEqual(logic.normalize_device_view_source_value('"preview"'), 'preview')
        self.assertEqual(logic.normalize_device_view_source_value('unknown', default='preview'), 'preview')

    def test_build_navigation_target_state_clamps_and_reports_changes(self):
        state = logic.build_navigation_target_state(total=3, current_index=1, target_index=' 9 ')
        self.assertTrue(state['active'])
        self.assertEqual(state['current_index'], 1)
        self.assertEqual(state['target_index'], 2)
        self.assertTrue(state['changed'])

        same = logic.build_navigation_target_state(total=3, current_index=2, target_index=2)
        self.assertTrue(same['active'])
        self.assertEqual(same['target_index'], 2)
        self.assertFalse(same['changed'])

        empty = logic.build_navigation_target_state(total=0, current_index=5, target_index=1)
        self.assertFalse(empty['active'])
        self.assertEqual(empty['target_index'], 0)
        self.assertFalse(empty['changed'])

    def test_build_navigation_target_state_handles_invalid_numeric_values(self):
        state = logic.build_navigation_target_state(total='bad-total', current_index='bad-index', target_index='9')
        self.assertFalse(state['active'])
        self.assertEqual(state['current_index'], 0)
        self.assertEqual(state['target_index'], 0)
        self.assertFalse(state['changed'])

    def test_build_navigation_delta_state_clamps_to_available_pages(self):
        state = logic.build_navigation_delta_state(total=3, current_index=0, delta=' 5 ')
        self.assertTrue(state['active'])
        self.assertEqual(state['target_index'], 2)
        self.assertTrue(state['changed'])

        same = logic.build_navigation_delta_state(total=3, current_index=2, delta=4)
        self.assertTrue(same['active'])
        self.assertEqual(same['target_index'], 2)
        self.assertFalse(same['changed'])

    def test_build_navigation_input_state_validates_page_number(self):
        valid = logic.build_navigation_input_state(total=4, current_index=1, input_page=' 4 ')
        self.assertTrue(valid['active'])
        self.assertTrue(valid['is_valid'])
        self.assertEqual(valid['target_index'], 3)
        self.assertTrue(valid['changed'])

        invalid = logic.build_navigation_input_state(total=4, current_index=1, input_page='0')
        self.assertTrue(invalid['active'])
        self.assertFalse(invalid['is_valid'])
        self.assertEqual(invalid['target_index'], 1)
        self.assertFalse(invalid['changed'])

        empty = logic.build_navigation_input_state(total=0, current_index=1, input_page='1')
        self.assertFalse(empty['active'])
        self.assertFalse(empty['is_valid'])
        self.assertEqual(empty['target_index'], 0)

    def test_build_navigation_display_state_handles_empty_pages(self):
        state = logic.build_navigation_display_state(view_mode='weird', total=0, current_index=5, truncated=True)
        self.assertFalse(state['active'])
        self.assertEqual(state['current_index'], 0)
        self.assertEqual(state['current_page'], 0)
        self.assertEqual(state['total_label'], '/ 0')
        self.assertEqual(state['view_mode'], 'device')

    def test_build_device_navigation_payload_preserves_current_page_and_view_activity(self):
        state = logic.build_device_navigation_payload(
            view_mode='font',
            total=5,
            current_index=2,
            current_page=3,
            is_preview=True,
            truncated=True,
        )

        self.assertFalse(state['active'])
        self.assertEqual(state['total'], 5)
        self.assertEqual(state['current_index'], 2)
        self.assertEqual(state['current_page'], 3)
        self.assertEqual(state['total_label'], '/ 5+')
        self.assertEqual(state['view_mode'], 'device')

    def test_build_device_navigation_payload_disables_truncation_for_loaded_xtc_source(self):
        state = logic.build_device_navigation_payload(
            view_mode='device',
            total='2',
            current_index='9',
            current_page=None,
            is_preview=False,
            truncated=True,
        )

        self.assertTrue(state['active'])
        self.assertEqual(state['current_index'], 1)
        self.assertEqual(state['current_page'], 2)
        self.assertEqual(state['total_label'], '/ 2')

    def test_build_navigation_apply_state_respects_activity_and_labels(self):
        state = logic.build_navigation_apply_state(
            {'active': True, 'total': 4, 'total_label': '/ 4+'},
            {'active': True, 'current_page': 2, 'can_go_prev': True, 'can_go_next': True},
            total_label_format='of {total}',
        )

        self.assertTrue(state['active'])
        self.assertEqual(state['current_page'], 2)
        self.assertTrue(state['prev_enabled'])
        self.assertTrue(state['next_enabled'])
        self.assertEqual(state['total_label'], '/ 4+')

    def test_build_navigation_apply_state_handles_empty_and_reversed_buttons(self):
        state = logic.build_navigation_apply_state(
            {'active': True, 'total': 3},
            {'active': True, 'current_page': 1, 'can_go_prev': False, 'can_go_next': True},
            total_label_format='of {total}',
            nav_buttons_reversed=True,
        )

        self.assertTrue(state['active'])
        self.assertTrue(state['prev_enabled'])
        self.assertFalse(state['next_enabled'])
        self.assertEqual(state['total_label'], 'of 3')

        empty = logic.build_navigation_apply_state(
            {'active': True, 'total': 0},
            {'active': True, 'current_page': 9, 'can_go_prev': True, 'can_go_next': True},
            total_label_format='{missing}',
        )
        self.assertFalse(empty['prev_enabled'])
        self.assertFalse(empty['next_enabled'])
        self.assertEqual(empty['current_page'], 0)
        self.assertEqual(empty['total_label'], '/ 0')


    def test_build_nav_button_text_state_applies_plan_and_reversal(self):
        normal = logic.build_nav_button_text_state(
            {'prev_button_text': '戻る', 'next_button_text': '進む'},
            nav_buttons_reversed=False,
        )
        self.assertEqual(normal, {'prev_button_text': '戻る', 'next_button_text': '進む'})

        reversed_state = logic.build_nav_button_text_state(
            {'prev_button_text': '戻る', 'next_button_text': '進む'},
            nav_buttons_reversed=True,
        )
        self.assertEqual(reversed_state, {'prev_button_text': '進む', 'next_button_text': '戻る'})

        fallback = logic.build_nav_button_text_state(None, nav_buttons_reversed='bad')
        self.assertEqual(fallback, {'prev_button_text': '前', 'next_button_text': '次'})


    def test_build_preview_zoom_control_state_uses_normal_and_actual_size_text(self):
        plan = {
            'preview_zoom_label_text': '倍率',
            'preview_zoom_actual_size_label_text': '補正',
            'preview_zoom_normal_tooltip': '通常説明',
            'preview_zoom_actual_size_tooltip': '補正説明',
        }

        normal = logic.build_preview_zoom_control_state(plan, actual_size=False)
        self.assertEqual(normal, {'label_text': '倍率', 'tooltip': '通常説明'})

        actual = logic.build_preview_zoom_control_state(plan, actual_size=True)
        self.assertEqual(actual, {'label_text': '補正', 'tooltip': '補正説明'})

        fallback = logic.build_preview_zoom_control_state(None, actual_size=True)
        self.assertEqual(fallback['label_text'], '実寸補正')
        self.assertIn('補正倍率', fallback['tooltip'])


    def test_build_page_input_apply_state_clamps_active_page(self):
        state = logic.build_page_input_apply_state(
            total_pages='5',
            current_page='99',
            empty_minimum=-1,
            empty_maximum=0,
            active_minimum=1,
        )

        self.assertTrue(state['active'])
        self.assertEqual(state['minimum'], 1)
        self.assertEqual(state['maximum'], 5)
        self.assertEqual(state['value'], 5)

    def test_build_page_input_apply_state_handles_empty_total(self):
        state = logic.build_page_input_apply_state(
            total_pages=0,
            current_page=3,
            empty_minimum=0,
            empty_maximum=0,
            active_minimum=1,
        )

        self.assertFalse(state['active'])
        self.assertEqual(state['minimum'], 0)
        self.assertEqual(state['maximum'], 0)
        self.assertEqual(state['value'], 0)


    def test_read_image_dimensions_accepts_methods_and_clamps(self):
        class DummyImage:
            def width(self):
                return '640'

            def height(self):
                return -20

        self.assertEqual(logic.read_image_dimensions(DummyImage()), (640, 0))

    def test_read_image_dimensions_handles_attributes_and_errors(self):
        class BrokenWidth:
            width = 'bad'

            def height(self):
                raise RuntimeError('boom')

        class AttributeImage:
            width = 300
            height = '400'

        self.assertEqual(logic.read_image_dimensions(BrokenWidth()), (0, 0))
        self.assertEqual(logic.read_image_dimensions(AttributeImage()), (300, 400))
        self.assertEqual(logic.read_image_dimensions(None), (0, 0))



    def test_build_preview_view_page_sync_state_syncs_between_preview_views(self):
        font_state = logic.build_preview_view_page_sync_state(
            mode='font',
            effective_device_view_source='preview',
            preview_page_count=3,
            device_preview_page_count=0,
            current_preview_index=0,
            current_device_preview_index=9,
        )
        self.assertEqual(font_state['target'], 'font')
        self.assertTrue(font_state['should_sync'])
        self.assertEqual(font_state['target_index'], 2)

        device_state = logic.build_preview_view_page_sync_state(
            mode='device',
            effective_device_view_source='preview',
            preview_page_count=0,
            device_preview_page_count=4,
            current_preview_index='2',
            current_device_preview_index=0,
        )
        self.assertEqual(device_state['target'], 'device')
        self.assertTrue(device_state['should_sync'])
        self.assertEqual(device_state['target_index'], 2)

    def test_build_preview_view_page_sync_state_skips_non_preview_sources_and_empty_targets(self):
        xtc_state = logic.build_preview_view_page_sync_state(
            mode='device',
            effective_device_view_source='xtc',
            preview_page_count=3,
            device_preview_page_count=3,
            current_preview_index=1,
            current_device_preview_index=2,
        )
        self.assertFalse(xtc_state['should_sync'])
        self.assertEqual(xtc_state['target'], '')

        empty_state = logic.build_preview_view_page_sync_state(
            mode='font',
            effective_device_view_source='preview',
            preview_page_count=0,
            device_preview_page_count=3,
            current_preview_index=0,
            current_device_preview_index=2,
        )
        self.assertFalse(empty_state['should_sync'])
        self.assertEqual(empty_state['target'], 'font')

    def test_resolve_effective_device_view_source_requires_preview_pages(self):
        self.assertEqual(
            logic.resolve_effective_device_view_source('preview', has_preview_pages=True),
            'preview',
        )
        self.assertEqual(
            logic.resolve_effective_device_view_source('preview', has_preview_pages=False),
            'xtc',
        )
        self.assertEqual(
            logic.resolve_effective_device_view_source('broken', has_preview_pages=True),
            'xtc',
        )

    def test_is_preview_display_active_matches_visible_view_source(self):
        self.assertTrue(
            logic.is_preview_display_active(
                'font',
                has_font_preview_pages=True,
                effective_device_view_source='xtc',
            )
        )
        self.assertFalse(
            logic.is_preview_display_active(
                'font',
                has_font_preview_pages=False,
                effective_device_view_source='preview',
            )
        )
        self.assertTrue(
            logic.is_preview_display_active(
                'device',
                has_font_preview_pages=False,
                effective_device_view_source='preview',
            )
        )
        self.assertFalse(
            logic.is_preview_display_active(
                'device',
                has_font_preview_pages=True,
                effective_device_view_source='xtc',
            )
        )

    def test_build_preview_success_status_state_clamps_limit_and_truncated_message(self):
        state = logic.build_preview_success_status_state(
            page_count='3',
            requested_limit='2',
            truncated=True,
        )
        self.assertEqual(state['generated_pages'], 3)
        self.assertEqual(state['preview_limit'], 3)
        self.assertTrue(state['truncated'])
        self.assertEqual(state['status_message'], '先頭 3 / 上限 3 ページを生成しました。')

    def test_build_preview_render_status_message_preserves_running_dirty_and_complete_policy(self):
        self.assertEqual(
            logic.build_preview_render_status_message(
                page_count=0,
                requested_limit=0,
                running=True,
                widget_limit=5,
            ),
            '先頭 5 ページまでプレビューを更新しています…',
        )
        self.assertEqual(
            logic.build_preview_render_status_message(
                page_count=4,
                requested_limit=10,
                dirty=True,
            ),
            '設定変更あり（未反映）',
        )
        self.assertEqual(
            logic.build_preview_render_status_message(
                page_count=0,
                requested_limit=0,
                widget_limit=5,
            ),
            'プレビュー更新完了（0 / 上限 0 ページ）',
        )


    def test_build_successful_preview_render_status_refresh_state_updates_stale_font_statuses(self):
        state = logic.build_successful_preview_render_status_refresh_state(
            preview_replacement='プレビュー更新完了（2 / 上限 2 ページ）',
            view_mode='font',
            visible_font_preview_active=True,
            preview_status_text='プレビュー表示エラー: broken',
            progress_status_text='ページ表示エラー: stale device',
            status_bar_text='ページ表示エラー: stale device',
        )

        self.assertTrue(state['font_view_visible'])
        self.assertTrue(state['stale_preview_status'])
        self.assertTrue(state['stale_progress_status'])
        self.assertTrue(state['stale_status_bar'])
        self.assertTrue(state['should_notify_status_bar'])
        self.assertEqual(state['progress_replacement'], 'プレビュー更新完了（2 / 上限 2 ページ）')

    def test_build_successful_preview_render_status_refresh_state_uses_current_label_for_device_view(self):
        state = logic.build_successful_preview_render_status_refresh_state(
            preview_replacement='プレビュー更新完了（1 / 上限 1 ページ）',
            view_mode='device',
            visible_font_preview_active=False,
            preview_status_text='プレビュー表示エラー: hidden',
            progress_status_text='プレビュー生成エラー: stale preview',
            status_bar_text='',
            current_label_text='表示中: プレビュー',
        )

        self.assertFalse(state['font_view_visible'])
        self.assertTrue(state['device_view_visible'])
        self.assertTrue(state['stale_preview_status'])
        self.assertTrue(state['stale_progress_status'])
        self.assertFalse(state['stale_status_bar'])
        self.assertTrue(state['should_notify_status_bar'])
        self.assertEqual(state['progress_replacement'], '表示中: プレビュー')

    def test_build_preview_page_cache_tokens_state_accepts_matching_lengths(self):
        state = logic.build_preview_page_cache_tokens_state(
            {
                'preview_page_cache_tokens': ['1', 2],
                'device_preview_page_cache_tokens': [3],
            },
            preview_page_count=2,
            device_preview_page_count='1',
        )

        self.assertFalse(state['should_rebuild'])
        self.assertEqual(state['preview_page_cache_tokens'], [1, 2])
        self.assertEqual(state['device_preview_page_cache_tokens'], [3])

    def test_build_preview_page_cache_tokens_state_requests_rebuild_for_bad_payload(self):
        missing_device = logic.build_preview_page_cache_tokens_state(
            {'preview_page_cache_tokens': [1, 2]},
            preview_page_count=2,
            device_preview_page_count=1,
        )
        self.assertTrue(missing_device['should_rebuild'])
        self.assertEqual(missing_device['preview_page_cache_tokens'], [1, 2])
        self.assertEqual(missing_device['device_preview_page_cache_tokens'], [])

        bad_preview = logic.build_preview_page_cache_tokens_state(
            {'preview_page_cache_tokens': ['bad'], 'device_preview_page_cache_tokens': []},
            preview_page_count=1,
            device_preview_page_count=0,
        )
        self.assertTrue(bad_preview['should_rebuild'])
        self.assertEqual(bad_preview['preview_page_cache_tokens'], [])
        self.assertEqual(bad_preview['device_preview_page_cache_tokens'], [])

    def test_build_preview_button_state_normalizes_worker_context(self):
        state = logic.build_preview_button_state({
            'button_enabled': 'false',
            'button_text': '生成中…',
        })

        self.assertFalse(state['button_enabled'])
        self.assertEqual(state['button_text'], '生成中…')

        fallback = logic.build_preview_button_state('bad-context')
        self.assertTrue(fallback['button_enabled'])
        self.assertEqual(fallback['button_text'], 'プレビュー更新')

    def test_build_preview_progress_context_state_uses_status_message_fallback(self):
        self.assertEqual(
            logic.build_preview_progress_context_state({'status_message': '進行中'})['status_message'],
            '進行中',
        )
        self.assertEqual(
            logic.build_preview_progress_context_state('bad-context')['status_message'],
            '',
        )


    def test_build_successful_device_render_status_refresh_state_uses_label_for_visible_device(self):
        state = logic.build_successful_device_render_status_refresh_state(
            view_mode='device',
            current_label_text='表示中: book.xtc',
            preview_replacement='プレビュー更新完了（1 / 上限 1 ページ）',
            has_font_preview_pages=True,
            progress_status_text='ページ表示エラー（表示は old.xtc のまま）: stale device',
            status_bar_text='プレビュー表示エラー: stale preview',
        )

        self.assertTrue(state['device_view_visible'])
        self.assertFalse(state['font_view_visible'])
        self.assertEqual(state['replacement'], '表示中: book.xtc')
        self.assertTrue(state['stale_progress_status'])
        self.assertTrue(state['stale_status_bar'])
        self.assertTrue(state['should_notify_status_bar'])

    def test_build_successful_device_render_status_refresh_state_restores_preview_status_for_font_preview(self):
        state = logic.build_successful_device_render_status_refresh_state(
            view_mode='font',
            current_label_text='表示中: book.xtc',
            preview_replacement='プレビュー更新完了（2 / 上限 2 ページ）',
            has_font_preview_pages=True,
            progress_status_text='ページ表示エラー: stale device',
            status_bar_text='ページ表示エラー: stale device',
        )

        self.assertTrue(state['font_view_visible'])
        self.assertFalse(state['device_view_visible'])
        self.assertTrue(state['font_preview_visible'])
        self.assertEqual(state['replacement'], 'プレビュー更新完了（2 / 上限 2 ページ）')
        self.assertTrue(state['stale_progress_status'])
        self.assertTrue(state['stale_status_bar'])
        self.assertTrue(state['should_notify_status_bar'])

    def test_build_successful_device_render_status_refresh_state_skips_hidden_font_without_preview(self):
        state = logic.build_successful_device_render_status_refresh_state(
            view_mode='font',
            current_label_text='表示中: book.xtc',
            preview_replacement='プレビュー更新完了（2 / 上限 2 ページ）',
            has_font_preview_pages=False,
            progress_status_text='ページ表示エラー: stale device',
            status_bar_text='ページ表示エラー: stale device',
        )

        self.assertEqual(state['replacement'], '')
        self.assertFalse(state['font_preview_visible'])
        self.assertTrue(state['stale_progress_status'])
        self.assertTrue(state['stale_status_bar'])
        self.assertTrue(state['should_notify_status_bar'])

    def test_normalize_preview_zoom_pct_clamps_and_parses_values(self):
        self.assertEqual(logic.normalize_preview_zoom_pct('175'), 175)
        self.assertEqual(logic.normalize_preview_zoom_pct('175.8'), 175)
        self.assertEqual(logic.normalize_preview_zoom_pct(20), 50)
        self.assertEqual(logic.normalize_preview_zoom_pct(999), 300)
        self.assertEqual(logic.normalize_preview_zoom_pct('bad'), 100)

    def test_build_actual_size_calibration_factor_uses_zoom_or_legacy_calibration(self):
        self.assertAlmostEqual(
            logic.build_actual_size_calibration_factor(
                uses_preview_zoom=True,
                preview_zoom_pct=175,
                calibration_pct=80,
            ),
            1.75,
        )
        self.assertAlmostEqual(
            logic.build_actual_size_calibration_factor(
                uses_preview_zoom=False,
                preview_zoom_pct=175,
                calibration_pct=80,
            ),
            0.8,
        )
        self.assertAlmostEqual(
            logic.build_actual_size_calibration_factor(
                uses_preview_zoom=False,
                preview_zoom_pct=175,
                calibration_pct=10,
            ),
            0.5,
        )
        self.assertAlmostEqual(
            logic.build_actual_size_calibration_factor(
                uses_preview_zoom=False,
                preview_zoom_pct=175,
                calibration_pct=float('inf'),
            ),
            1.0,
        )

    def test_build_font_preview_target_size_handles_actual_size_zoom_and_fallback(self):
        self.assertEqual(
            logic.build_font_preview_target_size(
                actual_size=True,
                screen_w_mm=100,
                screen_h_mm=200,
                px_per_mm=2.5,
            ),
            (250, 500),
        )
        self.assertEqual(
            logic.build_font_preview_target_size(
                actual_size=False,
                screen_w_mm=100,
                screen_h_mm=200,
                px_per_mm=2.5,
                viewport_width=600,
                viewport_height=900,
                zoom_factor=1.25,
            ),
            (750, 1125),
        )
        self.assertEqual(
            logic.build_font_preview_target_size(
                actual_size=False,
                screen_w_mm=100,
                screen_h_mm=200,
                px_per_mm=2.5,
                viewport_width=5,
                viewport_height=5,
            ),
            (480, 720),
        )

    def test_build_viewer_profile_resolution_state_selects_current_preset_or_custom(self):
        self.assertEqual(
            logic.build_viewer_profile_resolution_state(
                528,
                792,
                current_width=528,
                current_height=792,
                profile_dimensions={'x4': (1072, 1448), 'x3': (528, 792)},
            )['kind'],
            'current',
        )
        preset = logic.build_viewer_profile_resolution_state(
            1072,
            1448,
            current_width=528,
            current_height=792,
            profile_dimensions={'x4': (1072, 1448), 'x3': (528, 792)},
        )
        self.assertEqual(preset['kind'], 'profile')
        self.assertEqual(preset['profile_key'], 'x4')
        custom = logic.build_viewer_profile_resolution_state(
            '600',
            '900',
            current_width=528,
            current_height=792,
            profile_dimensions={'x4': (1072, 1448), 'x3': (528, 792)},
        )
        self.assertEqual(custom, {'kind': 'custom', 'profile_key': 'custom', 'width_px': 600, 'height_px': 900})
        self.assertEqual(
            logic.build_viewer_profile_resolution_state(0, 900)['kind'],
            'current',
        )

    def test_build_custom_viewer_profile_metrics_preserves_body_area_ratio(self):
        metrics = logic.build_custom_viewer_profile_metrics(
            width_px=600,
            height_px=800,
            ppi=300,
            screen_w_mm=100,
            screen_h_mm=200,
            body_w_mm=80,
            body_h_mm=150,
        )

        self.assertEqual(metrics['width_px'], 600)
        self.assertEqual(metrics['height_px'], 800)
        self.assertAlmostEqual(metrics['screen_w_mm'], 600 / (300 / 25.4))
        self.assertAlmostEqual(metrics['screen_h_mm'], 800 / (300 / 25.4))
        self.assertAlmostEqual(metrics['body_w_mm'], metrics['screen_w_mm'] * 0.8)
        self.assertAlmostEqual(metrics['body_h_mm'], metrics['screen_h_mm'] * 0.75)

    def test_build_safe_preview_layout_size_clamps_and_uses_fallback(self):
        class MethodSize:
            def width(self):
                return '9000'

            def height(self):
                return -5

        class BadSize:
            def width(self):
                raise RuntimeError('boom')

            def height(self):
                return 'bad'

        self.assertEqual(logic.build_safe_preview_layout_size(MethodSize()), (4096, 10))
        self.assertEqual(
            logic.build_safe_preview_layout_size(BadSize(), fallback=(321, 654)),
            (321, 654),
        )
        self.assertEqual(
            logic.build_safe_preview_layout_size(object(), fallback=(1, 99999)),
            (10, 4096),
        )


    def test_build_viewer_minimum_size_clamps_hint_and_uses_fallback(self):
        class MethodSize:
            def width(self):
                return 420

            def height(self):
                return 650

        class BadSize:
            def width(self):
                raise RuntimeError('bad width')

            def height(self):
                return 'bad height'

        self.assertEqual(logic.build_viewer_minimum_size(MethodSize()), (420, 650))
        self.assertEqual(
            logic.build_viewer_minimum_size(BadSize(), fallback=(222, 333)),
            (360, 600),
        )
        self.assertEqual(
            logic.build_viewer_minimum_size(types.SimpleNamespace(width=99999, height=10)),
            (4096, 600),
        )

    def test_build_loaded_xtc_view_mode_state_handles_safe_fallback(self):
        self.assertEqual(
            logic.build_loaded_xtc_view_mode_state('', safe=True, can_apply_full_view_mode=True),
            {
                'has_mode': False,
                'mode': '',
                'apply_full_view_mode': False,
                'assign_main_view_mode': False,
            },
        )
        self.assertEqual(
            logic.build_loaded_xtc_view_mode_state(' device ', safe=False, can_apply_full_view_mode=False),
            {
                'has_mode': True,
                'mode': 'device',
                'apply_full_view_mode': True,
                'assign_main_view_mode': False,
            },
        )
        self.assertEqual(
            logic.build_loaded_xtc_view_mode_state('font', safe=True, can_apply_full_view_mode=False),
            {
                'has_mode': True,
                'mode': 'font',
                'apply_full_view_mode': False,
                'assign_main_view_mode': True,
            },
        )



if __name__ == '__main__':
    unittest.main()
