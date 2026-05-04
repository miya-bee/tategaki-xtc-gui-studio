from __future__ import annotations

from pathlib import Path

import unittest

import tategakiXTC_gui_settings_controller as controller


class SettingsControllerRegressionTests(unittest.TestCase):
    def test_build_settings_restore_raw_payload_reads_expected_defaults(self):
        seen: list[tuple[str, object]] = []

        def reader(key: str, default: object) -> object:
            seen.append((key, default))
            values = {
                'profile': 'x3',
                'output_format': 'xtch',
                'preview_page_limit': '7',
            }
            return values.get(key, default)

        payload = controller.build_settings_restore_raw_payload(
            read_default_value=reader,
            default_font_name='safe.ttf',
            default_preview_page_limit=5,
        )

        self.assertEqual(payload['profile'], 'x3')
        self.assertEqual(payload['output_format'], 'xtch')
        self.assertEqual(payload['font_file'], 'safe.ttf')
        self.assertEqual(payload['preview_page_limit'], '7')
        self.assertIn(('font_file', 'safe.ttf'), seen)
        self.assertIn(('preview_page_limit', 5), seen)

    def test_build_current_settings_payload_merges_runtime_fields(self):
        payload = controller.build_current_settings_payload(
            render_settings_base={'target': 'sample.epub', 'output_format': 'xtch'},
            output_conflict='rename',
            open_folder=True,
        )
        self.assertEqual(payload['target'], 'sample.epub')
        self.assertEqual(payload['output_format'], 'xtch')
        self.assertEqual(payload['output_conflict'], 'rename')
        self.assertTrue(payload['open_folder'])

    def test_build_current_settings_payload_normalizes_wave_dash_label_variants(self):
        payload = controller.build_current_settings_payload(
            render_settings_base={
                'target': 'sample.epub',
                'wave_dash_drawing_mode': '別描画方式',
                'wave_dash_position_mode': '下補正 強',
            },
            output_conflict='rename',
            open_folder=False,
        )

        self.assertEqual(payload['target'], 'sample.epub')
        self.assertEqual(payload['wave_dash_drawing_mode'], 'separate')
        self.assertEqual(payload['wave_dash_position_mode'], 'down_strong')
        self.assertEqual(payload['output_conflict'], 'rename')
        self.assertFalse(payload['open_folder'])

    def test_build_settings_save_raw_payload_combines_ui_and_render_state(self):
        payload = controller.build_settings_save_raw_payload(
            current_settings={
                'target': 'sample.epub',
                'output_format': 'xtch',
                'output_conflict': 'overwrite',
                'open_folder': True,
                'punctuation_position_mode': 'down_strong',
                'ichi_position_mode': 'down_strong',
                'lower_closing_bracket_position_mode': 'up_weak',
                'wave_dash_drawing_mode': 'separate',
                'wave_dash_position_mode': 'down_weak',
            },
            ui_state={
                'bottom_tab_index': 2,
                'main_view_mode': 'device',
                'ui_theme': 'dark',
                'panel_button_visible': False,
                'preset_index': 3,
                'preset_key': 'preset_4',
                'profile': 'x3',
                'actual_size': True,
                'show_guides': False,
                'calibration_pct': 110,
                'nav_buttons_reversed': True,
            },
            default_preview_page_limit=6,
        )
        self.assertEqual(payload['target'], 'sample.epub')
        self.assertEqual(payload['output_format'], 'xtch')
        self.assertEqual(payload['output_conflict'], 'overwrite')
        self.assertTrue(payload['open_folder'])
        self.assertEqual(payload['bottom_tab_index'], 2)
        self.assertEqual(payload['main_view_mode'], 'device')
        self.assertEqual(payload['ui_theme'], 'dark')
        self.assertFalse(payload['panel_button_visible'])
        self.assertEqual(payload['preset_index'], 3)
        self.assertEqual(payload['preset_key'], 'preset_4')
        self.assertEqual(payload['profile'], 'x3')
        self.assertTrue(payload['actual_size'])
        self.assertFalse(payload['show_guides'])
        self.assertEqual(payload['calibration_pct'], 110)
        self.assertTrue(payload['nav_buttons_reversed'])
        self.assertEqual(payload['preview_page_limit'], 6)
        self.assertEqual(payload['wave_dash_drawing_mode'], 'separate')
        self.assertEqual(payload['wave_dash_position_mode'], 'down_weak')


    def test_build_settings_restore_payload_normalizes_profile_target_and_font(self):
        values = {
            'profile': 'x3',
            'width': '123',
            'height': '456',
            'target': ' sample.epub ',
            'font_file': '',
            'output_format': 'xtch',
            'punctuation_position_mode': 'down_strong',
            'ichi_position_mode': 'unknown',
            'lower_closing_bracket_position_mode': '上補正弱',
            'wave_dash_drawing_mode': '別描画',
            'wave_dash_position_mode': '下補正弱',
        }

        def reader(key: str, default: object) -> object:
            return values.get(key, default)

        payload = controller.build_settings_restore_payload(
            read_default_value=reader,
            default_font_name='fallback.ttf',
            default_preview_page_limit=5,
            allowed_view_modes={'font', 'device'},
            allowed_profiles={'x3': object(), 'x4': object()},
            allowed_kinsoku_modes={'standard': '標準'},
            allowed_glyph_position_modes={'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'},
            allowed_output_formats={'xtc': 'XTC', 'xtch': 'XTCH'},
            allowed_output_conflicts={'rename': 'rename'},
            normalize_font_setting_value=lambda value, default: str(value or '').strip() or default,
            normalize_target_path_text=lambda text: text.strip().upper(),
            resolve_profile_dimensions=lambda profile, width, height: ('x3', object(), 528, 792),
        )

        self.assertEqual(payload['profile'], 'x3')
        self.assertEqual(payload['width'], 528)
        self.assertEqual(payload['height'], 792)
        self.assertEqual(payload['target'], 'SAMPLE.EPUB')
        self.assertEqual(payload['font_file'], 'fallback.ttf')
        self.assertEqual(payload['output_format'], 'xtch')
        self.assertEqual(payload['punctuation_position_mode'], 'down_strong')
        self.assertEqual(payload['ichi_position_mode'], 'standard')
        self.assertEqual(payload['lower_closing_bracket_position_mode'], 'up_weak')
        self.assertEqual(payload['wave_dash_drawing_mode'], 'separate')
        self.assertEqual(payload['wave_dash_position_mode'], 'down_weak')

    def test_build_settings_restore_payload_maps_legacy_adjusted_to_down_strong(self):
        values = {
            'punctuation_position_mode': 'adjusted',
            'ichi_position_mode': '補正',
            'lower_closing_bracket_position_mode': '上補正強',
        }

        payload = controller.build_settings_restore_payload(
            read_default_value=lambda key, default: values.get(key, default),
            default_font_name='fallback.ttf',
            default_preview_page_limit=5,
            allowed_view_modes={'font', 'device'},
            allowed_profiles={'x4': object()},
            allowed_kinsoku_modes={'standard': '標準'},
            allowed_glyph_position_modes={'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'},
            allowed_output_formats={'xtc': 'XTC'},
            allowed_output_conflicts={'rename': 'rename'},
            normalize_font_setting_value=lambda value, default: str(value or '').strip() or default,
            normalize_target_path_text=lambda text: text.strip(),
            resolve_profile_dimensions=lambda profile, width, height: ('x4', object(), 480, 800),
        )

        self.assertEqual(payload['punctuation_position_mode'], 'down_strong')
        self.assertEqual(payload['ichi_position_mode'], 'down_strong')
        self.assertEqual(payload['lower_closing_bracket_position_mode'], 'up_strong')
        self.assertEqual(payload['wave_dash_drawing_mode'], 'rotate')
        self.assertEqual(payload['wave_dash_position_mode'], 'standard')

    def test_build_settings_ui_apply_defaults_and_plan_keep_latest_modes(self):
        defaults = controller.build_settings_ui_apply_defaults(
            actual_size=True,
            show_guides=False,
            calibration_pct=111,
            nav_buttons_reversed=True,
            font_size=31,
            ruby_size=14,
            line_spacing=52,
            margin_t=9,
            margin_b=10,
            margin_r=11,
            margin_l=12,
            threshold=130,
            preview_page_limit=8,
            dither=True,
            night_mode=False,
            open_folder=True,
            output_conflict='overwrite',
            output_format='xtch',
            kinsoku_mode='strict',
            punctuation_position_mode='down_strong',
            ichi_position_mode='down_strong',
            lower_closing_bracket_position_mode='up_weak',
            wave_dash_drawing_mode='separate',
            wave_dash_position_mode='down_weak',
            main_view_mode='device',
        )
        plan = controller.build_settings_ui_apply_plan(
            raw_payload={'output_format': 'xtch', 'main_view_mode': 'device', 'preview_page_limit': '7', 'punctuation_position_mode': 'down_strong', 'ichi_position_mode': 'standard', 'lower_closing_bracket_position_mode': 'up_strong', 'wave_dash_drawing_mode': 'separate', 'wave_dash_position_mode': 'down_strong'},
            defaults=defaults,
            allowed_view_modes={'font', 'device'},
            allowed_kinsoku_modes={'standard': '標準', 'strict': '強め'},
            allowed_glyph_position_modes={'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'},
            allowed_output_formats={'xtc': 'XTC', 'xtch': 'XTCH'},
            allowed_output_conflicts={'rename': 'rename', 'overwrite': 'overwrite'},
            bottom_tab_count=3,
        )

        self.assertEqual(plan['output_format'], 'xtch')
        self.assertEqual(plan['main_view_mode'], 'device')
        self.assertEqual(plan['preview_page_limit'], 7)
        self.assertEqual(plan['punctuation_position_mode'], 'down_strong')
        self.assertEqual(plan['ichi_position_mode'], 'standard')
        self.assertEqual(plan['lower_closing_bracket_position_mode'], 'up_strong')
        self.assertEqual(plan['wave_dash_drawing_mode'], 'separate')
        self.assertEqual(plan['wave_dash_position_mode'], 'down_strong')

        alias_defaults = controller.build_settings_ui_apply_defaults(
            actual_size=False,
            show_guides=True,
            calibration_pct=100,
            nav_buttons_reversed=False,
            font_size=26,
            ruby_size=12,
            line_spacing=44,
            margin_t=12,
            margin_b=14,
            margin_r=12,
            margin_l=12,
            threshold=128,
            preview_page_limit=5,
            dither=False,
            night_mode=False,
            open_folder=True,
            output_conflict='rename',
            output_format='xtc',
            kinsoku_mode='standard',
            punctuation_position_mode='standard',
            ichi_position_mode='standard',
            lower_closing_bracket_position_mode='standard',
            wave_dash_drawing_mode='別描画方式',
            wave_dash_position_mode='下補正 強',
            main_view_mode='font',
        )
        self.assertEqual(alias_defaults['wave_dash_drawing_mode'], 'separate')
        self.assertEqual(alias_defaults['wave_dash_position_mode'], 'down_strong')

    def test_build_settings_save_payload_normalizes_and_preserves_xtch(self):
        ui_state = controller.build_settings_save_ui_state(
            bottom_tab_index=2,
            main_view_mode='device',
            ui_theme='dark',
            panel_button_visible=False,
            preset_index=4,
            preset_key='preset_5',
            profile='x3',
            actual_size=True,
            show_guides=False,
            calibration_pct=115,
            nav_buttons_reversed=True,
            preview_page_limit=9,
        )
        payload = controller.build_settings_save_payload(
            current_settings={
                'target': 'sample.epub',
                'font_file': 'font.ttf',
                'output_format': 'xtch',
                'output_conflict': 'overwrite',
                'open_folder': True,
                'punctuation_position_mode': 'down_strong',
                'ichi_position_mode': 'down_strong',
                'lower_closing_bracket_position_mode': 'up_strong',
                'wave_dash_drawing_mode': 'separate',
                'wave_dash_position_mode': 'down_strong',
            },
            ui_state=ui_state,
            allowed_view_modes={'font', 'device'},
            allowed_profiles={'x3': object(), 'x4': object()},
            allowed_kinsoku_modes={'standard': '標準'},
            allowed_glyph_position_modes={'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'},
            allowed_output_formats={'xtc': 'XTC', 'xtch': 'XTCH'},
            allowed_output_conflicts={'rename': 'rename', 'overwrite': 'overwrite'},
            default_preview_page_limit=6,
        )

        self.assertEqual(payload['output_format'], 'xtch')
        self.assertEqual(payload['profile'], 'x3')
        self.assertEqual(payload['preview_page_limit'], 9)
        self.assertEqual(payload['main_view_mode'], 'device')
        self.assertEqual(payload['preset_key'], 'preset_5')
        self.assertFalse(payload['panel_button_visible'])
        self.assertEqual(payload['punctuation_position_mode'], 'down_strong')
        self.assertEqual(payload['ichi_position_mode'], 'down_strong')
        self.assertEqual(payload['lower_closing_bracket_position_mode'], 'up_strong')

    def test_build_settings_save_payload_records_schema_version_and_app_version_values(self):
        ui_state = controller.build_settings_save_ui_state(
            bottom_tab_index=0,
            main_view_mode='font',
            ui_theme='light',
            panel_button_visible=True,
            preset_index=-1,
            preset_key='',
            profile='x4',
            actual_size=False,
            show_guides=True,
            calibration_pct=100,
            nav_buttons_reversed=False,
            preview_page_limit=6,
        )

        payload = controller.build_settings_save_payload(
            current_settings={},
            ui_state=ui_state,
            allowed_view_modes={'font', 'device'},
            allowed_profiles={'x3': object(), 'x4': object()},
            allowed_kinsoku_modes={'standard': '標準'},
            allowed_output_formats={'xtc': 'XTC', 'xtch': 'XTCH'},
            allowed_output_conflicts={'rename': 'rename'},
            default_preview_page_limit=6,
        )

        self.assertEqual(
            payload['settings_schema_version'],
            controller.studio_constants.SETTINGS_SCHEMA_VERSION,
        )
        self.assertEqual(
            payload['last_app_version'],
            controller.studio_constants.APP_VERSION,
        )


    def test_build_current_preset_payload_normalizes_render_settings(self):
        seen: dict[str, object] = {}

        def normalize(payload: object, **kwargs: object) -> dict[str, object]:
            seen['payload'] = payload
            seen.update(kwargs)
            return {'normalized': True, 'font_size': 31}

        payload = controller.build_current_preset_payload(
            render_settings_base={
                'width': '528',
                'height': '792',
                'font_size': '31',
                'ruby_size': '13',
                'line_spacing': '46',
                'margin_t': '9',
                'margin_b': '10',
                'margin_r': '11',
                'margin_l': '12',
                'threshold': '144',
            },
            profile='x3',
            fallback_font='font.ttf',
            fallback_night_mode=True,
            fallback_dither=False,
            fallback_kinsoku_mode='standard',
            fallback_output_format='xtch',
            normalize_preset_payload=normalize,
        )

        self.assertEqual(payload, {'normalized': True, 'font_size': 31})
        self.assertEqual(seen['payload']['profile'], 'x3')
        self.assertEqual(seen['payload']['width'], 528)
        self.assertEqual(seen['payload']['height'], 792)
        self.assertEqual(seen['payload']['font_size'], 31)
        self.assertEqual(seen['payload']['threshold'], 144)
        self.assertEqual(seen['fallback_font'], 'font.ttf')
        self.assertTrue(seen['fallback_night_mode'])
        self.assertEqual(seen['fallback_output_format'], 'xtch')

    def test_build_live_preset_widget_payload_prefers_normalized_choices(self):
        payload = controller.build_live_preset_widget_payload(
            profile=' X3 ',
            width='528',
            height='792',
            font_size='31',
            ruby_size='13',
            line_spacing='46',
            margin_t='9',
            margin_b='10',
            margin_r='11',
            margin_l='12',
            threshold='144',
            night_mode='yes',
            dither='1',
            kinsoku_mode=' SIMPLE ',
            output_format=' XTCH ',
            punctuation_position_mode=' down_weak ',
            ichi_position_mode='invalid',
            lower_closing_bracket_position_mode=' up_strong ',
            wave_dash_drawing_mode='別描画方式',
            wave_dash_position_mode='下補正 強',
            font_file='',
            default_font_name='fallback.ttf',
            allowed_profiles={'x3': object(), 'x4': object()},
            allowed_kinsoku_modes={'standard': '標準', 'simple': '簡易'},
            allowed_output_formats={'xtc': 'XTC', 'xtch': 'XTCH'},
            allowed_glyph_position_modes={'down_strong': '下補正 強', 'down_weak': '下補正 弱', 'standard': '標準', 'up_weak': '上補正 弱', 'up_strong': '上補正 強'},
            normalize_choice_value=lambda value, default, allowed: str(value or default).strip().lower() if str(value or default).strip().lower() in {str(k).lower() for k in allowed} else default,
            normalize_font_setting_value=lambda value, default: str(value or '').strip() or default,
        )

        self.assertEqual(payload['profile'], 'x3')
        self.assertEqual(payload['width'], 528)
        self.assertEqual(payload['height'], 792)
        self.assertEqual(payload['font_size'], 31)
        self.assertEqual(payload['threshold'], 144)
        self.assertTrue(payload['night_mode'])
        self.assertTrue(payload['dither'])
        self.assertEqual(payload['kinsoku_mode'], 'simple')
        self.assertEqual(payload['output_format'], 'xtch')
        self.assertEqual(payload['punctuation_position_mode'], 'down_weak')
        self.assertEqual(payload['ichi_position_mode'], 'standard')
        self.assertEqual(payload['lower_closing_bracket_position_mode'], 'up_strong')
        self.assertEqual(payload['wave_dash_drawing_mode'], 'separate')
        self.assertEqual(payload['wave_dash_position_mode'], 'down_strong')
        self.assertEqual(payload['font_file'], 'fallback.ttf')

    def test_build_preset_save_and_summary_payload_merge_latest_values(self):
        payload = controller.build_preset_save_payload(
            current_preset={'profile': 'x4', 'font_size': 26, 'output_format': 'xtc'},
            live_widget_payload={'font_size': 31, 'output_format': 'xtch'},
        )
        summary_payload = controller.build_preset_summary_payload(
            stored_preset={'button_text': 'プリセット1', 'font_file': 'old.ttf'},
            pending_payload=payload,
        )

        self.assertEqual(payload['font_size'], 31)
        self.assertEqual(payload['output_format'], 'xtch')
        self.assertEqual(summary_payload['button_text'], 'プリセット1')
        self.assertEqual(summary_payload['font_size'], 31)
        self.assertEqual(summary_payload['font_file'], 'old.ttf')


    def test_resolve_preset_combo_index_matches_data_then_fallback_text(self):
        self.assertEqual(
            controller.resolve_preset_combo_index(
                preset_key='preset_4',
                combo_entries=(('プリセット1', 'preset_1'), ('プリセット4', None)),
            ),
            1,
        )
        self.assertEqual(
            controller.resolve_preset_combo_index(
                preset_key='preset_2',
                combo_entries=(('プリセット1', 'preset_1'), ('プリセット4', None)),
            ),
            -1,
        )

    def test_build_preset_selection_status_message_uses_button_label(self):
        self.assertEqual(
            controller.build_preset_selection_status_message('プリセット4'),
            'プリセット4 の詳細表示を更新しました。適用する場合は［プリセット適用］を押してください。',
        )

    def test_build_preset_apply_context_combines_selection_payload_and_status(self):
        seen: dict[str, object] = {}

        def normalize(payload: object, **kwargs: object) -> dict[str, object]:
            seen['payload'] = dict(payload)
            seen.update(kwargs)
            return {'profile': 'x3', 'font_size': 31}

        context = controller.build_preset_apply_context(
            preset_key='preset_4',
            stored_preset={'button_text': 'プリセット4', 'name': '標準', 'profile': 'broken'},
            fallback_preset={'profile': 'x4'},
            fallback_font='font.ttf',
            combo_entries=(('プリセット1', 'preset_1'), ('プリセット4', None)),
            normalize_preset_payload=normalize,
            preset_display_name=lambda preset: f"{preset.get('button_text')} / {preset.get('name')}",
        )

        self.assertEqual(context['combo_index'], 1)
        self.assertEqual(context['payload']['font_size'], 31)
        self.assertEqual(context['preset_display_name'], 'プリセット4 / 標準')
        self.assertIn('仕様表示はプリセット保存時に更新されます。', context['status_message'])
        self.assertEqual(seen['payload']['profile'], 'broken')
        self.assertEqual(seen['fallback']['profile'], 'x4')
        self.assertEqual(seen['fallback_font'], 'font.ttf')

    def test_build_preset_status_message_matches_save_and_apply_wording(self):
        self.assertEqual(controller.build_preset_status_message('save', 'プリセット4 / 標準'), 'プリセット4 / 標準 を保存しました')
        self.assertIn('仕様表示はプリセット保存時に更新されます。', controller.build_preset_status_message('apply', 'プリセット4 / 標準'))


    def test_build_current_settings_payload_ignores_non_mapping_render_settings(self):
        payload = controller.build_current_settings_payload(
            render_settings_base='bad-settings',
            output_conflict='rename',
            open_folder=False,
        )

        self.assertEqual(payload, {'output_conflict': 'rename', 'open_folder': False})

    def test_build_current_preset_payload_ignores_non_mapping_render_settings(self):
        seen: dict[str, object] = {}

        def normalize(payload: object, **kwargs: object) -> dict[str, object]:
            seen['payload'] = dict(payload)
            seen.update(kwargs)
            return {'normalized': True}

        payload = controller.build_current_preset_payload(
            render_settings_base='bad-settings',
            profile='x3',
            fallback_font='font.ttf',
            fallback_night_mode=False,
            fallback_dither=True,
            fallback_kinsoku_mode='standard',
            fallback_output_format='xtch',
            normalize_preset_payload=normalize,
        )

        self.assertEqual(payload, {'normalized': True})
        self.assertEqual(seen['payload']['profile'], 'x3')
        self.assertEqual(seen['payload']['width'], 480)
        self.assertEqual(seen['payload']['height'], 800)

    def test_build_preset_apply_context_ignores_non_mapping_presets(self):
        seen: dict[str, object] = {}

        def normalize(payload: object, **kwargs: object) -> dict[str, object]:
            seen['payload'] = dict(payload)
            seen.update(kwargs)
            return {'font_size': 26}

        context = controller.build_preset_apply_context(
            preset_key='preset_2',
            stored_preset='bad-preset',
            fallback_preset='bad-fallback',
            fallback_font='font.ttf',
            combo_entries=(('プリセット2', 'preset_2'),),
            normalize_preset_payload=normalize,
            preset_display_name=lambda preset: str(preset.get('button_text') or 'プリセット'),
        )

        self.assertEqual(context['combo_index'], 0)
        self.assertEqual(context['payload']['font_size'], 26)
        self.assertEqual(context['preset_display_name'], 'プリセット')
        self.assertEqual(seen['payload'], {})
        self.assertEqual(seen['fallback'], {})

    def test_build_preset_save_and_summary_payload_ignore_non_mapping_inputs(self):
        payload = controller.build_preset_save_payload(
            current_preset='bad-current',
            live_widget_payload='bad-live',
        )
        summary_payload = controller.build_preset_summary_payload(
            stored_preset='bad-stored',
            pending_payload='bad-pending',
        )

        self.assertEqual(payload, {})
        self.assertEqual(summary_payload, {})

    def test_build_settings_save_raw_payload_ignores_non_mapping_inputs(self):
        payload = controller.build_settings_save_raw_payload(
            current_settings='bad-current',
            ui_state='bad-ui',
            default_preview_page_limit=6,
        )

        self.assertEqual(payload['preview_page_limit'], 6)
        self.assertEqual(payload['profile'], 'x4')
        self.assertEqual(payload['main_view_mode'], 'font')
        self.assertEqual(payload['preset_index'], -1)

    def test_glyph_position_display_labels_use_directional_terms(self) -> None:
        import tategakiXTC_gui_studio_constants as constants

        self.assertEqual(constants.GLYPH_POSITION_MODE_OPTIONS, [
            ('down_strong', '下補正 強'),
            ('down_weak', '下補正 弱'),
            ('standard', '標準'),
            ('up_weak', '上補正 弱'),
            ('up_strong', '上補正 強'),
        ])
        self.assertEqual(constants.CLOSING_BRACKET_POSITION_MODE_OPTIONS, [
            ('up_strong', '上補正 強'),
            ('up_weak', '上補正 弱'),
            ('standard', '標準'),
        ])
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        self.assertIn("_dim_label('句読点')", source)
        self.assertIn("_dim_label('下鍵括弧')", source)
        self.assertNotIn('image_lower_bracket_position_row', source)
        self.assertLess(source.index("_dim_label('句読点')"), source.index("_dim_label('漢数字「一」')"))
        self.assertLess(source.index("_dim_label('漢数字「一」')"), source.index("_dim_label('下鍵括弧')"))
        self.assertNotIn("_dim_label('ぶら下がり句読点')", source)
        self.assertNotIn("_dim_label('句読点位置')", source)


if __name__ == '__main__':
    unittest.main()
