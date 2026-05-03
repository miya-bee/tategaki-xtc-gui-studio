from __future__ import annotations

import unittest
from unittest import mock

import tategakiXTC_gui_preview_controller as preview_controller


class GuiPreviewControllerRegressionTests(unittest.TestCase):
    def test_build_preview_payload_uses_render_settings_and_clamps_limit(self):
        payload = preview_controller.build_preview_payload(
            render_settings_base={
                'target': '',
                'font_file': 'font.ttf',
                'font_size': 28,
                'ruby_size': 12,
                'line_spacing': 44,
                'margin_t': 10,
                'margin_b': 12,
                'margin_r': 14,
                'margin_l': 16,
                'dither': False,
                'threshold': 128,
                'night_mode': True,
                'kinsoku_mode': 'standard',
                'punctuation_position_mode': 'down_weak',
                'ichi_position_mode': 'up_weak',
                'lower_closing_bracket_position_mode': 'up_strong',
                'output_format': 'xtc',
                'width': 528,
                'height': 792,
            },
            current_preview_mode='image',
            selected_profile_key='x3',
            preview_image_data_url=b'data:image/png;base64,AAAA',
            preview_page_limit=0,
            default_preview_page_limit=10,
        )

        self.assertEqual(payload['mode'], 'image')
        self.assertEqual(payload['profile'], 'x3')
        self.assertEqual(payload['file_b64'], 'data:image/png;base64,AAAA')
        self.assertEqual(payload['max_pages'], 1)
        self.assertEqual(payload['night_mode'], 'true')
        self.assertEqual(payload['dither'], 'false')
        self.assertEqual(payload['punctuation_position_mode'], 'down_weak')
        self.assertEqual(payload['ichi_position_mode'], 'up_weak')
        self.assertEqual(payload['lower_closing_bracket_position_mode'], 'up_strong')

    def test_build_preview_payload_forces_text_mode_for_text_target_after_stale_image_mode(self):
        payload = preview_controller.build_preview_payload(
            render_settings_base={
                'target': 'sample.txt',
                'font_file': 'font.ttf',
                'font_size': 28,
                'ruby_size': 12,
                'line_spacing': 44,
                'margin_t': 10,
                'margin_b': 12,
                'margin_r': 14,
                'margin_l': 16,
                'dither': False,
                'threshold': 128,
                'night_mode': False,
                'kinsoku_mode': 'standard',
                'output_format': 'xtc',
                'width': 528,
                'height': 792,
            },
            current_preview_mode='image',
            selected_profile_key='x3',
            preview_image_data_url='data:image/png;base64,STALE',
            preview_page_limit=5,
            default_preview_page_limit=10,
        )

        self.assertEqual(payload['mode'], 'text')
        self.assertEqual(payload['file_b64'], '')
        self.assertEqual(payload['target_path'], 'sample.txt')

    def test_build_preview_payload_uses_target_path_for_image_file_targets_too(self):
        payload = preview_controller.build_preview_payload(
            render_settings_base={
                'target': 'cover.png',
                'font_file': 'font.ttf',
                'font_size': 28,
                'ruby_size': 12,
                'line_spacing': 44,
                'margin_t': 10,
                'margin_b': 12,
                'margin_r': 14,
                'margin_l': 16,
                'dither': False,
                'threshold': 128,
                'night_mode': False,
                'kinsoku_mode': 'standard',
                'output_format': 'xtc',
                'width': 528,
                'height': 792,
            },
            current_preview_mode='image',
            selected_profile_key='x3',
            preview_image_data_url='data:image/png;base64,STALE',
            preview_page_limit=5,
            default_preview_page_limit=10,
        )

        self.assertEqual(payload['mode'], 'text')
        self.assertEqual(payload['file_b64'], '')
        self.assertEqual(payload['target_path'], 'cover.png')


    def test_build_preview_payload_normalizes_string_bool_values(self):
        payload = preview_controller.build_preview_payload(
            render_settings_base={
                'target': 'book.epub',
                'font_file': 'font.ttf',
                'font_size': 28,
                'ruby_size': 12,
                'line_spacing': 44,
                'margin_t': 10,
                'margin_b': 12,
                'margin_r': 14,
                'margin_l': 16,
                'dither': 'false',
                'threshold': 128,
                'night_mode': '0',
                'kinsoku_mode': 'standard',
                'output_format': 'xtc',
                'width': 528,
                'height': 792,
            },
            current_preview_mode='text',
            selected_profile_key='x3',
            preview_image_data_url=None,
            preview_page_limit=5,
            default_preview_page_limit=10,
        )

        self.assertEqual(payload['dither'], 'false')
        self.assertEqual(payload['night_mode'], 'false')

    def test_build_preview_request_plan_overrides_output_format_and_normalizes_limit(self):
        plan = preview_controller.build_preview_request_plan(
            {'mode': 'text', 'output_format': 'xtc', 'max_pages': '0'},
            current_output_format='xtch',
            default_preview_page_limit=10,
        )

        self.assertEqual(plan['payload']['output_format'], 'xtch')
        self.assertEqual(plan['payload']['max_pages'], 1)
        self.assertEqual(plan['preview_limit'], 1)


    def test_build_preview_request_plan_tolerates_non_mapping_payload(self):
        plan = preview_controller.build_preview_request_plan(
            'bad-payload',
            current_output_format='xtch',
            default_preview_page_limit=10,
        )

        self.assertEqual(plan['payload']['output_format'], 'xtch')
        self.assertEqual(plan['payload']['max_pages'], 10)
        self.assertEqual(plan['preview_limit'], 10)

    def test_build_preview_start_context_sets_running_button_and_status(self):
        context = preview_controller.build_preview_start_context(preview_limit=8)

        self.assertFalse(context['button_enabled'])
        self.assertEqual(context['button_text'], '生成中…')
        self.assertEqual(context['status_message'], '先頭 8 ページまでプレビューを更新しています…')

    def test_build_preview_progress_context_formats_status_message(self):
        context = preview_controller.build_preview_progress_context(
            2,
            5,
            '画像を生成中',
            preview_limit=10,
        )

        self.assertEqual(context['status_message'], '画像を生成中 (2/5)')

    def test_build_preview_finish_context_restores_button_state(self):
        context = preview_controller.build_preview_finish_context()

        self.assertTrue(context['button_enabled'])
        self.assertEqual(context['button_text'], 'プレビュー更新')

    def test_preview_page_cache_tokens_reuse_single_page_token_helper_for_duplicates(self):
        preview_controller._preview_page_cache_token_text.cache_clear()
        pages = ['ZmFrZQ==', 'ZmFrZQ==', 'bW9jaw==']

        with mock.patch.object(
            preview_controller,
            '_preview_page_cache_token_text',
            wraps=preview_controller._preview_page_cache_token_text,
        ) as mocked_token:
            tokens = preview_controller._preview_page_cache_tokens(pages)

        self.assertEqual(tokens[0], tokens[1])
        self.assertEqual(mocked_token.call_count, 3)
        info = preview_controller._preview_page_cache_token_text.cache_info()
        self.assertGreaterEqual(info.hits, 1)

    def test_preview_page_cache_tokens_reuse_cached_page_sequence_for_identical_inputs(self):
        preview_controller._preview_page_cache_token_text.cache_clear()
        preview_controller._preview_page_cache_tokens_tuple.cache_clear()
        pages = ['ZmFrZQ==', 'bW9jaw==']

        first = preview_controller._preview_page_cache_tokens(pages)
        info_after_first = preview_controller._preview_page_cache_tokens_tuple.cache_info()
        second = preview_controller._preview_page_cache_tokens(list(pages))
        info_after_second = preview_controller._preview_page_cache_tokens_tuple.cache_info()

        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_build_manual_preview_refresh_context_builds_request_kwargs(self):
        context = preview_controller.build_manual_preview_refresh_context(
            {'mode': 'text', 'output_format': 'xtc', 'max_pages': '0'},
            current_output_format='xtch',
            default_preview_page_limit=10,
            reset_page=True,
        )

        self.assertTrue(context['reset_page'])
        self.assertEqual(context['preview_payload']['output_format'], 'xtch')
        self.assertEqual(context['preview_payload']['max_pages'], 1)
        self.assertTrue(context['should_update_top_status'])
        self.assertTrue(context['should_save_ui_state'])

    def test_build_manual_preview_refresh_context_normalizes_string_reset_flag(self):
        context = preview_controller.build_manual_preview_refresh_context(
            {'mode': 'text', 'output_format': 'xtc', 'max_pages': '2'},
            current_output_format='xtch',
            default_preview_page_limit=10,
            reset_page='false',
        )

        self.assertFalse(context['reset_page'])

    def test_build_manual_preview_refresh_context_tolerates_non_mapping_request_payload(self):
        original = preview_controller.build_preview_request_plan
        try:
            preview_controller.build_preview_request_plan = lambda *args, **kwargs: {
                'payload': 'not-a-mapping',
                'preview_limit': 3,
            }
            context = preview_controller.build_manual_preview_refresh_context(
                {'mode': 'text'},
                current_output_format='xtc',
                default_preview_page_limit=10,
                reset_page=False,
            )
        finally:
            preview_controller.build_preview_request_plan = original

        self.assertEqual(context['preview_payload'], {})

    def test_build_preview_bundle_state_filters_invalid_pages_and_preserves_payload(self):
        payload = {'mode': 'text', 'output_format': 'xtch', 'max_pages': 10}
        state = preview_controller.build_preview_bundle_state(
            {'pages': ['ZmFrZQ==', None, 123, 'bW9jaw=='], 'truncated': True},
            reset_page=False,
            current_preview_index=8,
            current_device_index='-1',
            preview_limit=10,
            payload=payload,
        )

        self.assertEqual(state['pages'], ['ZmFrZQ==', 'bW9jaw=='])
        self.assertTrue(state['truncated'])
        self.assertEqual(state['device_view_source'], 'preview')
        self.assertEqual(state['last_applied_preview_payload'], payload)
        refresh_state = state['refresh_state']
        self.assertTrue(refresh_state['has_pages'])
        self.assertEqual((refresh_state['preview_index'], refresh_state['device_index']), (1, 0))
        self.assertEqual(refresh_state['status_message'], '先頭 2 / 上限 10 ページを生成しました。')


    def test_build_preview_bundle_state_flattens_nested_page_structures(self):
        state = preview_controller.build_preview_bundle_state(
            {'pages': {'first': bytearray(b'ZmFrZQ=='), 'nested': [None, ['  bW9jaw==  '], {'last': 'Y2FjaGU='}]}, 'truncated': True},
            reset_page=False,
            current_preview_index=7,
            current_device_index='1',
            preview_limit=10,
            payload={'mode': 'text', 'output_format': 'xtch'},
        )

        self.assertEqual(state['pages'], ['ZmFrZQ==', 'bW9jaw==', 'Y2FjaGU='])
        self.assertTrue(state['truncated'])
        refresh_state = state['refresh_state']
        self.assertEqual((refresh_state['preview_index'], refresh_state['device_index']), (2, 1))

    def test_build_preview_bundle_state_accepts_single_string_page(self):
        payload = {'mode': 'text', 'output_format': 'xtc', 'max_pages': 10}
        state = preview_controller.build_preview_bundle_state(
            {'pages': 'ZmFrZQ==', 'truncated': False},
            reset_page=True,
            current_preview_index=3,
            current_device_index=0,
            preview_limit=10,
            payload=payload,
        )

        self.assertEqual(state['pages'], ['ZmFrZQ=='])
        refresh_state = state['refresh_state']
        self.assertTrue(refresh_state['has_pages'])
        self.assertEqual((refresh_state['preview_index'], refresh_state['device_index']), (0, 0))

    def test_build_preview_bundle_state_normalizes_string_truncated_flag(self):
        state = preview_controller.build_preview_bundle_state(
            {'pages': 'ZmFrZQ==', 'truncated': 'false'},
            reset_page=False,
            current_preview_index=0,
            current_device_index=0,
            preview_limit=10,
            payload={'mode': 'text'},
        )

        self.assertFalse(state['truncated'])

    def test_build_preview_apply_context_expands_bundle_state_for_runtime_use(self):
        payload = {'mode': 'text', 'output_format': 'xtch', 'max_pages': 10}
        context = preview_controller.build_preview_apply_context(
            {'pages': ['ZmFrZQ==', None, 'bW9jaw=='], 'truncated': True},
            reset_page=False,
            current_preview_index=5,
            current_device_index=1,
            preview_limit=10,
            payload=payload,
        )

        self.assertEqual(context['preview_pages_b64'], ['ZmFrZQ==', 'bW9jaw=='])
        self.assertEqual(context['device_preview_pages_b64'], ['ZmFrZQ==', 'bW9jaw=='])
        self.assertEqual(len(context['preview_page_cache_tokens']), 2)
        self.assertEqual(context['preview_page_cache_tokens'], context['device_preview_page_cache_tokens'])
        self.assertTrue(context['preview_pages_truncated'])
        self.assertTrue(context['device_preview_pages_truncated'])
        self.assertEqual(context['device_view_source'], 'preview')
        self.assertEqual(context['last_preview_requested_limit'], 10)
        self.assertEqual(context['last_applied_preview_payload'], payload)
        self.assertEqual(context['current_preview_page_index'], 1)
        self.assertEqual(context['current_device_preview_page_index'], 1)
        self.assertTrue(context['has_pages'])
        self.assertEqual(context['status_message'], '先頭 2 / 上限 10 ページを生成しました。')
        self.assertEqual(context['display_name'], 'プレビュー')
        self.assertFalse(context['clear_device_page'])


    def test_build_preview_apply_context_flattens_nested_page_structures(self):
        context = preview_controller.build_preview_apply_context(
            {'pages': {'first': 'ZmFrZQ==', 'nested': [bytearray(b'bW9jaw=='), {'last': 'Y2FjaGU='}]}, 'truncated': False},
            reset_page=True,
            current_preview_index=5,
            current_device_index=4,
            preview_limit=10,
            payload={'mode': 'text'},
        )

        self.assertEqual(context['preview_pages_b64'], ['ZmFrZQ==', 'bW9jaw==', 'Y2FjaGU='])
        self.assertEqual(context['device_preview_pages_b64'], ['ZmFrZQ==', 'bW9jaw==', 'Y2FjaGU='])
        self.assertEqual(len(context['preview_page_cache_tokens']), 3)
        self.assertEqual(context['preview_page_cache_tokens'], context['device_preview_page_cache_tokens'])
        self.assertEqual((context['current_preview_page_index'], context['current_device_preview_page_index']), (0, 0))

    def test_build_preview_apply_context_builds_tokens_for_single_string_page(self):
        context = preview_controller.build_preview_apply_context(
            {'pages': 'bW9jaw==', 'truncated': False},
            reset_page=False,
            current_preview_index=0,
            current_device_index=0,
            preview_limit=10,
            payload={'mode': 'text'},
        )

        self.assertEqual(context['preview_pages_b64'], ['bW9jaw=='])
        self.assertEqual(context['device_preview_pages_b64'], ['bW9jaw=='])
        self.assertEqual(len(context['preview_page_cache_tokens']), 1)
        self.assertEqual(context['preview_page_cache_tokens'], context['device_preview_page_cache_tokens'])

    def test_build_preview_apply_context_marks_empty_preview_for_clear(self):
        context = preview_controller.build_preview_apply_context(
            {'pages': [], 'truncated': False},
            reset_page=True,
            current_preview_index=3,
            current_device_index=4,
            preview_limit=10,
            payload={'mode': 'text'},
        )

        self.assertFalse(context['has_pages'])
        self.assertEqual(context['status_message'], 'プレビューを生成できませんでした')
        self.assertTrue(context['clear_device_page'])
        self.assertEqual(context['current_preview_page_index'], 0)
        self.assertEqual(context['current_device_preview_page_index'], 0)

    def test_build_preview_apply_context_normalizes_bundle_state_scalars(self):
        original = preview_controller.build_preview_bundle_state
        try:
            preview_controller.build_preview_bundle_state = lambda *args, **kwargs: {
                'pages': 'AAA=',
                'truncated': 'false',
                'device_view_source': 'unexpected',
                'last_preview_requested_limit': 'bad-limit',
                'last_applied_preview_payload': 'not-a-mapping',
                'refresh_state': {
                    'preview_index': '8',
                    'device_index': 'bad-index',
                    'has_pages': 'true',
                    'status_message': 123,
                },
            }
            context = preview_controller.build_preview_apply_context(
                {'pages': ['ignored']},
                reset_page=False,
                current_preview_index=0,
                current_device_index=0,
                preview_limit=10,
                payload={'mode': 'text'},
            )
        finally:
            preview_controller.build_preview_bundle_state = original

        self.assertEqual(context['preview_pages_b64'], ['AAA='])
        self.assertFalse(context['preview_pages_truncated'])
        self.assertEqual(context['device_view_source'], 'preview')
        self.assertEqual(context['last_preview_requested_limit'], 10)
        self.assertEqual(context['last_applied_preview_payload'], {'mode': 'text'})
        self.assertEqual(context['current_preview_page_index'], 0)
        self.assertEqual(context['current_device_preview_page_index'], 0)
        self.assertTrue(context['has_pages'])
        self.assertEqual(context['status_message'], '123')
        self.assertFalse(context['clear_device_page'])

    def test_build_preview_failure_context_resets_preview_runtime_state(self):
        context = preview_controller.build_preview_failure_context(
            previous_device_source='preview',
            error=RuntimeError('bad preview'),
        )

        self.assertEqual(context['preview_pages_b64'], [])
        self.assertEqual(context['device_preview_pages_b64'], [])
        self.assertEqual(context['preview_page_cache_tokens'], [])
        self.assertEqual(context['device_preview_page_cache_tokens'], [])
        self.assertFalse(context['preview_pages_truncated'])
        self.assertFalse(context['device_preview_pages_truncated'])
        self.assertEqual(context['device_view_source'], 'xtc')
        self.assertEqual(context['current_preview_page_index'], 0)
        self.assertEqual(context['current_device_preview_page_index'], 0)
        self.assertTrue(context['clear_device_page'])
        self.assertEqual(context['status_message'], 'プレビュー生成エラー: bad preview')
        self.assertEqual(context['error_message'], 'プレビュー生成エラー\nbad preview')


    def test_build_preview_failure_context_preserves_previous_preview_runtime_state(self):
        context = preview_controller.build_preview_failure_context(
            previous_device_source='preview',
            error=RuntimeError('bad preview'),
            previous_preview_pages={'first': 'AAA=', 'nested': [None, {'last': bytearray(b'BBB=')}]},
            previous_device_preview_pages='CCC=',
            previous_preview_page_cache_tokens=(101, 202),
            previous_device_preview_page_cache_tokens=['303'],
            previous_preview_pages_truncated=True,
            previous_device_preview_pages_truncated=True,
            current_preview_index='99',
            current_device_index='5',
        )

        self.assertEqual(context['preview_pages_b64'], ['AAA=', 'BBB='])
        self.assertEqual(context['device_preview_pages_b64'], ['CCC='])
        self.assertEqual(context['preview_page_cache_tokens'], [101, 202])
        self.assertEqual(context['device_preview_page_cache_tokens'], [303])
        self.assertTrue(context['preview_pages_truncated'])
        self.assertTrue(context['device_preview_pages_truncated'])
        self.assertEqual(context['current_preview_page_index'], 1)
        self.assertEqual(context['current_device_preview_page_index'], 0)
        self.assertEqual(context['device_view_source'], 'xtc')
        self.assertTrue(context['clear_device_page'])
        self.assertEqual(context['status_message'], 'プレビュー生成エラー: bad preview')

    def test_build_preview_failure_context_normalizes_string_truncated_flags(self):
        context = preview_controller.build_preview_failure_context(
            previous_device_source='xtc',
            error='bad preview',
            previous_preview_pages='AAA=',
            previous_device_preview_pages='BBB=',
            previous_preview_pages_truncated='false',
            previous_device_preview_pages_truncated='1',
            current_preview_index=0,
            current_device_index=0,
        )

        self.assertFalse(context['preview_pages_truncated'])
        self.assertTrue(context['device_preview_pages_truncated'])
        self.assertFalse(context['clear_device_page'])


if __name__ == '__main__':
    unittest.main()
