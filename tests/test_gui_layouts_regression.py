import unittest

import tategakiXTC_gui_layouts as gui_layouts


class GuiLayoutsRegressionTests(unittest.TestCase):
    def test_build_settings_section_plan_normalizes_title_and_object_name(self):
        plan = gui_layouts.build_settings_section_plan('  プリセット  ', object_name='  customSection  ')
        self.assertEqual(plan['title'], 'プリセット')
        self.assertEqual(plan['object_name'], 'customSection')

    def test_build_settings_section_plan_falls_back_to_default_object_name(self):
        plan = gui_layouts.build_settings_section_plan('', object_name='  ')
        self.assertEqual(plan['title'], '')
        self.assertEqual(plan['object_name'], 'settingsSection')

    def test_build_uniform_button_row_plan_uses_largest_width_and_minimum(self):
        plan = gui_layouts.build_uniform_button_row_plan(['96', 120.9, None, 'bad'], minimum_width='104')
        self.assertEqual(plan['button_min_width'], 120)

    def test_build_uniform_button_row_plan_never_drops_below_minimum(self):
        plan = gui_layouts.build_uniform_button_row_plan([0, -1, ''], minimum_width=104)
        self.assertEqual(plan['button_min_width'], 104)

    def test_build_bottom_status_strip_plan_clamps_and_normalizes_values(self):
        plan = gui_layouts.build_bottom_status_strip_plan(
            badge_text='  変換中  ',
            progress_text='  2 / 5件  ',
            progress_minimum='1',
            progress_maximum='4',
            progress_value='9',
            progress_max_width='240',
        )
        self.assertEqual(plan['badge_text'], '変換中')
        self.assertEqual(plan['progress_text'], '2 / 5件')
        self.assertEqual(plan['progress_minimum'], 1)
        self.assertEqual(plan['progress_maximum'], 4)
        self.assertEqual(plan['progress_value'], 4)
        self.assertEqual(plan['progress_max_width'], 240)
        self.assertEqual(plan['badge_object_name'], 'badge')
        self.assertFalse(plan['progress_text_visible'])
        self.assertEqual(plan['progress_fixed_height'], 6)
        self.assertEqual(plan['progress_label_object_name'], 'hintLabel')

    def test_build_results_tab_plan_uses_default_summary_text(self):
        plan = gui_layouts.build_results_tab_plan(summary_text='  ')
        self.assertEqual(plan['contents_margins'], (6, 6, 6, 6))
        self.assertEqual(plan['spacing'], 4)
        self.assertEqual(plan['summary_text'], '変換結果の概要をここに表示します。')
        self.assertEqual(plan['summary_label_object_name'], 'hintLabel')
        self.assertTrue(plan['summary_label_word_wrap'])
        self.assertEqual(plan['results_list_selection_mode'], 'single_selection')





    def test_build_top_bar_plan_exposes_button_labels_and_widths(self):
        plan = gui_layouts.build_top_bar_plan(path_button_width='96')
        self.assertEqual(plan['bar_height'], 56)
        self.assertEqual(plan['path_button_width'], 96)
        self.assertEqual(plan['file_button_text'], 'ファイル')
        self.assertEqual(plan['run_button_text'], '▶  変換実行')
        self.assertEqual(plan['settings_button_tooltip'], '表示設定')

    def test_build_view_toggle_and_nav_bar_plans_expose_defaults(self):
        toggle_plan = gui_layouts.build_view_toggle_bar_plan()
        nav_plan = gui_layouts.build_nav_bar_plan()
        self.assertEqual(toggle_plan['font_view_text'], 'フォントビュー')
        self.assertEqual(toggle_plan['device_view_text'], '実機ビュー')
        self.assertIn('フォントビュー:', toggle_plan['help_text'])
        self.assertIn('実機ビュー:', toggle_plan['help_text'])
        self.assertEqual(toggle_plan['bar_height'], 88)
        self.assertEqual(toggle_plan['row_spacing'], 2)
        self.assertEqual(toggle_plan['display_toggle_spacing'], 10)
        self.assertEqual(toggle_plan['preview_zoom_spacing'], 8)
        self.assertEqual(toggle_plan['top_row_contents_margins'], (0, 0, 0, 0))
        self.assertEqual(toggle_plan['bottom_row_contents_margins'], (0, 0, 0, 0))
        self.assertEqual(toggle_plan['view_button_object_name'], 'viewToggleBtn')
        self.assertEqual(toggle_plan['view_button_focus_policy'], 'no_focus')
        self.assertTrue(toggle_plan['view_button_checkable'])
        self.assertTrue(toggle_plan['font_view_checked_default'])
        self.assertFalse(toggle_plan['device_view_checked_default'])
        self.assertEqual(toggle_plan['preview_zoom_down_text'], '−')
        self.assertEqual(toggle_plan['preview_zoom_button_object_name'], 'stepBtn')
        self.assertEqual(toggle_plan['preview_zoom_up_text'], '+')
        self.assertTrue(toggle_plan['preview_zoom_spin_accelerated'])
        self.assertEqual(toggle_plan['preview_zoom_spin_button_symbols'], 'no_buttons')
        self.assertEqual(toggle_plan['preview_zoom_spin_suffix'], '%')
        self.assertEqual(toggle_plan['preview_zoom_label_text'], '表示倍率')
        self.assertEqual(toggle_plan['preview_zoom_actual_size_label_text'], '実寸補正')
        self.assertIn('実機ビューの表示倍率', toggle_plan['preview_zoom_normal_tooltip'])
        self.assertIn('補正倍率', toggle_plan['preview_zoom_actual_size_tooltip'])
        self.assertIn('実寸補正', toggle_plan['preview_zoom_tooltip'])
        self.assertEqual(nav_plan['current_xtc_label_text'], '表示中: なし')
        self.assertEqual(nav_plan['current_xtc_label_object_name'], 'hintLabel')
        self.assertEqual(nav_plan['current_xtc_label_min_width'], 0)
        self.assertEqual(nav_plan['current_xtc_label_max_width'], 220)
        self.assertEqual(nav_plan['nav_reverse_object_name'], 'navToggle')
        self.assertEqual(nav_plan['nav_reverse_focus_policy'], 'no_focus')
        self.assertEqual(nav_plan['page_input_minimum'], 0)
        self.assertEqual(nav_plan['page_input_maximum'], 0)
        self.assertEqual(nav_plan['page_input_empty_minimum'], 0)
        self.assertEqual(nav_plan['page_input_empty_maximum'], 0)
        self.assertEqual(nav_plan['page_input_active_minimum'], 1)
        self.assertEqual(nav_plan['page_input_button_symbols'], 'no_buttons')
        self.assertFalse(nav_plan['page_input_keyboard_tracking'])
        self.assertEqual(nav_plan['page_input_width'], 60)
        self.assertEqual(nav_plan['page_total_label_format'], '/ {total}')
        self.assertEqual(nav_plan['page_total_label_object_name'], 'hintLabel')
        self.assertEqual(nav_plan['nav_button_object_name'], 'navBtn')
        self.assertEqual(nav_plan['nav_button_focus_policy'], 'no_focus')
        self.assertEqual(nav_plan['prev_button_text'], '前')
        self.assertEqual(nav_plan['next_button_text'], '次')

    def test_build_preview_display_toggle_plan_owns_actual_size_and_guides_help(self):
        plan = gui_layouts.build_preview_display_toggle_plan()

        self.assertEqual(plan['actual_size_text'], '実寸近似')
        self.assertEqual(plan['actual_size_object_name'], 'viewToggleBtn')
        self.assertTrue(plan['actual_size_checkable'])
        self.assertEqual(plan['actual_size_focus_policy'], 'no_focus')
        self.assertIn('ONにすると右ペインの倍率欄は「実寸補正」に切り替わります。', plan['actual_size_help_text'])
        self.assertIn('表示が実物より大きい/小さい場合は、この実寸補正を調整してください。', plan['actual_size_help_text'])
        self.assertEqual(plan['guide_text'], 'ガイド')
        self.assertEqual(plan['guide_object_name'], 'previewToolbarToggle')
        self.assertEqual(plan['guide_focus_policy'], 'no_focus')
        self.assertTrue(plan['guide_checked_default'])
        self.assertIn('本文が端に寄りすぎていないか、余白設定が意図通りかを確認するときに使います。', plan['guide_help_text'])
        self.assertIn('変換結果そのものを書き換える機能ではなく、確認用の表示補助です。', plan['guide_help_text'])
        self.assertEqual(plan['toggle_spacing'], 18)

    def test_build_view_toggle_bar_plan_owns_toggle_button_chrome(self):
        plan = gui_layouts.build_view_toggle_bar_plan()
        self.assertEqual(plan['top_row_contents_margins'], (0, 0, 0, 0))
        self.assertEqual(plan['bottom_row_contents_margins'], (0, 0, 0, 0))
        self.assertEqual(plan['top_separator_object_name'], 'topSep')
        self.assertEqual(plan['view_button_object_name'], 'viewToggleBtn')
        self.assertEqual(plan['view_button_focus_policy'], 'no_focus')
        self.assertTrue(plan['view_button_checkable'])
        self.assertTrue(plan['font_view_checked_default'])
        self.assertFalse(plan['device_view_checked_default'])


    def test_build_right_preview_panel_plan_exposes_preview_sizes(self):
        plan = gui_layouts.build_right_preview_panel_plan()
        self.assertEqual(plan['panel_contents_margins'], (0, 0, 0, 0))
        self.assertEqual(plan['font_preview_min_size'], (360, 600))
        self.assertEqual(plan['device_preview_min_size'], (360, 600))
        self.assertEqual(plan['preview_stack_index'], 0)

    def test_build_right_preview_panel_plan_owns_stack_widget_chrome_contracts(self):
        plan = gui_layouts.build_right_preview_panel_plan()
        self.assertEqual(plan['top_separator_frame_shape'], 'hline')
        self.assertEqual(plan['top_separator_object_name'], 'topSep')
        self.assertEqual(plan['font_preview_alignment'], 'center')
        self.assertFalse(plan['font_scroll_widget_resizable'])
        self.assertEqual(plan['font_scroll_alignment'], 'center')
        self.assertEqual(plan['font_scroll_frame_shape'], 'no_frame')
        self.assertFalse(plan['device_scroll_widget_resizable'])
        self.assertEqual(plan['device_scroll_alignment'], 'center')
        self.assertEqual(plan['device_scroll_frame_shape'], 'no_frame')
        self.assertEqual(plan['device_scroll_focus_policy'], 'strong_focus')

    def test_nav_bar_plan_owns_navigation_widget_object_names(self):
        plan = gui_layouts.build_nav_bar_plan()
        self.assertEqual(plan['current_xtc_label_object_name'], 'hintLabel')
        self.assertEqual(plan['current_xtc_label_min_width'], 0)
        self.assertEqual(plan['nav_reverse_text'], 'ボタン反転')
        self.assertEqual(plan['nav_reverse_object_name'], 'navToggle')
        self.assertEqual(plan['nav_reverse_focus_policy'], 'no_focus')
        self.assertEqual(plan['nav_button_side_spacing'], 10)
        self.assertEqual(plan['nav_section_separator_object_name'], 'navSectionSep')
        self.assertEqual(plan['page_input_minimum'], 0)
        self.assertEqual(plan['page_input_maximum'], 0)
        self.assertEqual(plan['page_input_empty_minimum'], 0)
        self.assertEqual(plan['page_input_empty_maximum'], 0)
        self.assertEqual(plan['page_input_active_minimum'], 1)
        self.assertEqual(plan['page_input_button_symbols'], 'no_buttons')
        self.assertFalse(plan['page_input_keyboard_tracking'])
        self.assertEqual(plan['page_total_label_object_name'], 'hintLabel')
        self.assertEqual(plan['page_total_label_format'], '/ {total}')
        self.assertEqual(plan['nav_button_object_name'], 'navBtn')
        self.assertEqual(plan['nav_button_focus_policy'], 'no_focus')
        self.assertEqual(plan['prev_button_text'], '前')
        self.assertEqual(plan['next_button_text'], '次')

    def test_build_bottom_panel_layout_plan_exposes_tab_titles(self):
        plan = gui_layouts.build_bottom_panel_layout_plan()
        self.assertEqual(plan['panel_object_name'], 'bottomPanel')
        self.assertEqual(plan['content_object_name'], 'bottomPanelContent')
        self.assertEqual(plan['content_contents_margins'], (0, 0, 0, 0))
        self.assertEqual(plan['content_spacing'], 0)
        self.assertEqual(plan['external_scrollbar_object_name'], 'bottomPanelScrollBar')
        self.assertEqual(plan['external_scrollbar_single_step'], 20)
        self.assertEqual(plan['status_strip_height'], 34)
        self.assertEqual(plan['bottom_separator_frame_shape'], 'hline')
        self.assertEqual(plan['bottom_separator_object_name'], 'bottomPanelSep')
        self.assertEqual(plan['results_tab_title'], '変換結果')
        self.assertEqual(plan['log_tab_title'], 'ログ')

    def test_build_log_tab_plan_preserves_log_path_text(self):
        plan = gui_layouts.build_log_tab_plan(log_path=' /tmp/example.log ')
        self.assertEqual(plan['path_label_text'], '保存先:')
        self.assertEqual(plan['open_folder_button_text'], 'ログフォルダを開く')
        self.assertTrue(plan['log_path_edit_read_only'])
        self.assertTrue(plan['log_edit_read_only'])
        self.assertEqual(plan['log_path'], '/tmp/example.log')

    def test_build_left_settings_section_layout_plan_uses_section_defaults(self):
        plan = gui_layouts.build_left_settings_section_layout_plan(' display ')
        self.assertEqual(plan['section_key'], 'display')
        self.assertEqual(plan['title'], 'プレビュー')
        self.assertEqual(plan['contents_margins'], (8, 14, 8, 8))
        self.assertEqual(plan['spacing'], 8)
        self.assertEqual(plan['row_spacing'], 8)

    def test_build_left_settings_section_layout_plan_handles_unknown_section(self):
        plan = gui_layouts.build_left_settings_section_layout_plan('  custom pane  ')
        self.assertEqual(plan['title'], 'custom pane')
        self.assertEqual(plan['contents_margins'], (8, 12, 8, 7))
        self.assertEqual(plan['spacing'], 6)

    def test_build_display_section_plan_exposes_profile_items_and_widths(self):
        plan = gui_layouts.build_display_section_plan()
        self.assertEqual(plan['profile_items'][0], ('Xteink X4', 'x4'))
        self.assertEqual(plan['profile_combo_min_width'], 130)
        self.assertEqual(plan['preview_status_min_width'], 260)
        self.assertEqual(plan['calibration_label_text'], '実寸補正')
        self.assertEqual(plan['calibration_button_object_name'], 'stepBtn')
        self.assertEqual(plan['calibration_down_text'], '−')
        self.assertEqual(plan['calibration_up_text'], '+')
        self.assertEqual(plan['calibration_spin_button_symbols'], 'no_buttons')
        self.assertEqual(plan['calibration_spin_suffix'], '%')
        self.assertEqual(plan['custom_width_label'], '幅')
        self.assertEqual(plan['custom_height_label'], '高さ')
        self.assertEqual(plan['custom_size_pair_spacing'], 8)
        self.assertEqual(plan['preview_page_limit_label'], '更新対象')
        self.assertEqual(plan['preview_page_limit_unit_text'], 'ページ')
        self.assertEqual(plan['preview_update_button_object_name'], 'smallBtn')
        self.assertEqual(plan['preview_status_object_name'], 'hintLabel')
        self.assertEqual(plan['preview_status_help_spacing'], 4)
        self.assertIn('プレビュー上限を増やすほど', plan['preview_update_help_text'])

    def test_build_preset_section_plan_normalizes_button_minimum_width(self):
        plan = gui_layouts.build_preset_section_plan(minimum_button_width='bad')
        self.assertEqual(plan['row_spacing'], 8)
        self.assertEqual(plan['button_min_width'], 104)
        self.assertEqual(plan['apply_button_text'], 'プリセット適用')
        self.assertEqual(plan['save_button_text'], '組版保存')
        self.assertEqual(plan['button_object_name'], 'smallBtn')
        self.assertEqual(plan['summary_text'], '')
        self.assertEqual(plan['summary_label_object_name'], 'presetSummaryLabel')
        self.assertTrue(plan['summary_label_word_wrap'])
        self.assertEqual(plan['summary_label_alignment'], 'left_top')

    def test_build_image_section_plan_defaults_threshold_disabled(self):
        plan = gui_layouts.build_image_section_plan()
        self.assertEqual(plan['night_mode_text'], '白黒反転（出力）')
        self.assertEqual(plan['night_mode_spacing'], 16)
        self.assertEqual(plan['dither_text'], 'ディザリング')
        self.assertFalse(plan['dither_checked_default'])
        self.assertEqual(plan['dither_spacing'], 16)
        self.assertFalse(plan['threshold_enabled'])
        self.assertEqual(plan['threshold_help_spacing'], 6)
        self.assertEqual(plan['glyph_position_row_spacing'], 6)
        self.assertEqual(plan['wave_dash_row_spacing'], 6)
        self.assertIn('白と黒を入れ替えて出力', plan['help_text'])
        self.assertTrue(plan['trailing_stretch'])

    def test_build_font_section_plan_exposes_margin_spacing_defaults(self):
        plan = gui_layouts.build_font_section_plan()
        self.assertEqual(plan['browse_button_text'], '参照')
        self.assertEqual(plan['format_kinsoku_row_spacing'], 6)
        self.assertEqual(plan['margin_rows_spacing'], 2)
        self.assertEqual(plan['margin_pair_spacing'], 16)


    def test_build_left_settings_container_plan_exposes_left_pane_defaults(self):
        plan = gui_layouts.build_left_settings_container_plan()
        self.assertEqual(plan['container_object_name'], 'leftSettingsContainer')
        self.assertEqual(plan['contents_margins'], (10, 9, 10, 9))
        self.assertEqual(plan['spacing'], 5)
        self.assertFalse(plan['splitter_children_collapsible'])
        self.assertEqual(plan['splitter_handle_width'], 5)
        self.assertEqual(plan['splitter_top_stretch_factor'], 3)
        self.assertEqual(plan['splitter_bottom_stretch_factor'], 1)
        self.assertTrue(plan['scroll_widget_resizable'])
        self.assertEqual(plan['scroll_frame_shape'], 'no_frame')
        self.assertEqual(plan['scroll_horizontal_scroll_bar_policy'], 'always_off')
        self.assertEqual(plan['bottom_separator_frame_shape'], 'hline')
        self.assertEqual(plan['bottom_separator_object_name'], 'leftSettingsBottomSep')
        self.assertEqual(plan['bottom_separator_height'], 1)
        self.assertEqual(plan['bottom_panel_min_height'], 92)

    def test_build_left_settings_section_layout_plan_exposes_fileviewer_defaults(self):
        plan = gui_layouts.build_left_settings_section_layout_plan('fileviewer')
        self.assertEqual(plan['section_key'], 'fileviewer')
        self.assertEqual(plan['title'], 'ファイルビューワー')
        self.assertEqual(plan['contents_margins'], (8, 10, 8, 8))
        self.assertEqual(plan['spacing'], 6)

    def test_build_file_viewer_section_plan_owns_xtc_open_button_text(self):
        display_plan = gui_layouts.build_display_section_plan()
        file_viewer_plan = gui_layouts.build_file_viewer_section_plan()

        self.assertNotIn('open_xtc_button_text', display_plan)
        self.assertEqual(file_viewer_plan['open_xtc_button_text'], 'XTC/XTCHを開く')
        self.assertEqual(file_viewer_plan['open_xtc_button_object_name'], 'smallBtn')
        self.assertTrue(file_viewer_plan['open_xtc_trailing_stretch'])
        self.assertIn('.xtc / .xtch', file_viewer_plan['open_xtc_help_text'])
        self.assertIn('右ペインの実機ビュー', file_viewer_plan['open_xtc_help_text'])

    def test_build_left_settings_section_keys_preserves_default_order(self):
        section_keys = gui_layouts.build_left_settings_section_keys()
        self.assertEqual(section_keys, ('preset', 'font', 'image', 'display', 'fileviewer'))

    def test_build_left_settings_section_keys_optionally_appends_behavior(self):
        section_keys = gui_layouts.build_left_settings_section_keys(include_behavior=True)
        self.assertEqual(section_keys, ('preset', 'font', 'image', 'display', 'fileviewer', 'behavior'))


    def test_build_left_settings_section_keys_normalizes_boolean_like_flag(self):
        self.assertEqual(
            gui_layouts.build_left_settings_section_keys(include_behavior='false'),
            ('preset', 'font', 'image', 'display', 'fileviewer'),
        )
        self.assertEqual(
            gui_layouts.build_left_settings_section_keys(include_behavior='1'),
            ('preset', 'font', 'image', 'display', 'fileviewer', 'behavior'),
        )

    def test_build_row_layout_plan_normalizes_boolean_like_add_stretch(self):
        disabled_plan = gui_layouts.build_row_layout_plan(add_stretch='false')
        enabled_plan = gui_layouts.build_row_layout_plan(add_stretch='on')
        self.assertFalse(disabled_plan['add_stretch'])
        self.assertTrue(enabled_plan['add_stretch'])

    def test_build_labeled_widget_row_plan_normalizes_boolean_like_trailing_stretch(self):
        disabled_plan = gui_layouts.build_labeled_widget_row_plan(['A'], trailing_stretch='0')
        enabled_plan = gui_layouts.build_labeled_widget_row_plan(['A'], trailing_stretch='yes')
        self.assertFalse(disabled_plan['trailing_stretch'])
        self.assertTrue(enabled_plan['trailing_stretch'])

    def test_build_button_widget_plan_normalizes_boolean_like_flags(self):
        plan = gui_layouts.build_button_widget_plan(
            '  開く  ',
            checkable='true',
            checked='false',
            enabled='0',
        )
        self.assertTrue(plan['checkable'])
        self.assertFalse(plan['checked'])
        self.assertFalse(plan['enabled'])

    def test_build_behavior_section_plan_exposes_default_labels(self):
        plan = gui_layouts.build_behavior_section_plan()
        self.assertEqual(plan['open_folder_text'], '完了後フォルダを開く')
        self.assertTrue(plan['open_folder_checked_default'])
        self.assertTrue(plan['open_folder_row_stretch'])
        self.assertEqual(plan['output_conflict_label'], '同名出力')
        self.assertIn('同名の .xtc / .xtch', plan['output_conflict_help_text'])


    def test_build_row_layout_plan_normalizes_spacing_and_margins(self):
        plan = gui_layouts.build_row_layout_plan(
            spacing='8',
            contents_margins=('1', 2.9, 'bad', 4),
            add_stretch=1,
        )
        self.assertEqual(plan['spacing'], 8)
        self.assertEqual(plan['contents_margins'], (1, 2, 0, 4))
        self.assertTrue(plan['add_stretch'])

    def test_build_labeled_widget_row_plan_normalizes_labels_and_spacing(self):
        plan = gui_layouts.build_labeled_widget_row_plan(
            ['  本文  ', '', None],
            spacing='5',
            pair_spacing='12',
            label_object_name='  customLabel  ',
            trailing_stretch=False,
        )
        self.assertEqual(plan['labels'], ('本文', '', ''))
        self.assertEqual(plan['spacing'], 5)
        self.assertEqual(plan['pair_spacing'], 12)
        self.assertEqual(plan['label_object_name'], 'customLabel')
        self.assertFalse(plan['trailing_stretch'])

    def test_build_margin_rows_plan_exposes_expected_label_pairs(self):
        plan = gui_layouts.build_margin_rows_plan(row_spacing='3', pair_spacing='20')
        self.assertEqual(plan['container_margins'], (0, 0, 0, 0))
        self.assertEqual(plan['row_spacing'], 3)
        self.assertEqual(plan['pair_spacing'], 20)
        self.assertEqual(plan['top_labels'], ('上余白', '下余白'))
        self.assertEqual(plan['side_labels'], ('右余白', '左余白'))
        self.assertTrue(plan['trailing_stretch'])

    def test_build_button_widget_plan_normalizes_size_policy_and_flags(self):
        plan = gui_layouts.build_button_widget_plan(
            '  開く  ',
            object_name='  smallBtn  ',
            tooltip='  フォルダを開く  ',
            fixed_width='84',
            minimum_width='96',
            checkable=True,
            checked=True,
            enabled=False,
            focus_policy='  no_focus  ',
        )
        self.assertEqual(plan['text'], '開く')
        self.assertEqual(plan['object_name'], 'smallBtn')
        self.assertEqual(plan['tooltip'], 'フォルダを開く')
        self.assertEqual(plan['fixed_width'], 84)
        self.assertEqual(plan['minimum_width'], 96)
        self.assertIsNone(plan['fixed_size'])
        self.assertTrue(plan['checkable'])
        self.assertTrue(plan['checked'])
        self.assertFalse(plan['enabled'])
        self.assertEqual(plan['focus_policy'], 'no_focus')

    def test_build_button_widget_plan_ignores_invalid_fixed_size_and_unknown_focus_policy(self):
        plan = gui_layouts.build_button_widget_plan(
            '',
            fixed_size=('bad', 24),
            focus_policy='strong_focus',
            checked=True,
        )
        self.assertEqual(plan['text'], '')
        self.assertIsNone(plan['fixed_size'])
        self.assertEqual(plan['focus_policy'], 'default')
        self.assertFalse(plan['checked'])

if __name__ == '__main__':
    unittest.main()
