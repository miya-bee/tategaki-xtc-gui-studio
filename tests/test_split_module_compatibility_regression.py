from pathlib import Path
import importlib
import inspect
import unittest

import tategakiXTC_gui_core as core
import tategakiXTC_gui_core_archive as core_archive
import tategakiXTC_gui_core_text as core_text
import tategakiXTC_gui_core_sync as core_sync
import tategakiXTC_gui_core_renderer as core_renderer
import tategakiXTC_gui_studio_constants as studio_constants
import tategakiXTC_gui_studio_runtime as studio_runtime
import tategakiXTC_gui_studio_logging as studio_logging
import tategakiXTC_gui_studio_startup as studio_startup
import tategakiXTC_numpy_helper as numpy_helper

from tests.studio_import_helper import load_studio_module


class SplitModuleCompatibilityRegressionTests(unittest.TestCase):
    def test_split_helper_modules_expose_expected_public_entry_points(self):
        self.assertTrue(callable(numpy_helper.get_cached_numpy_module))
        self.assertTrue(callable(studio_startup.collect_missing_startup_dependencies))
        self.assertTrue(callable(studio_startup.show_startup_dependency_alert))
        self.assertTrue(callable(studio_logging.cleanup_old_session_logs))

    def test_gui_studio_reexports_constants_module_public_names(self):
        studio = load_studio_module(force_reload=True)
        self.assertIs(studio.DeviceProfile, studio_constants.DeviceProfile)
        self.assertIs(studio.DEVICE_PROFILES, studio_constants.DEVICE_PROFILES)
        self.assertEqual(studio.APP_VERSION, studio_constants.APP_VERSION)
        self.assertEqual(studio.APP_NAME, studio_constants.APP_NAME)
        self.assertIs(studio.DEFAULT_PRESET_DEFINITIONS, studio_constants.DEFAULT_PRESET_DEFINITIONS)
        self.assertIs(studio.SUPPORTED_INPUT_SUFFIXES, studio_constants.SUPPORTED_INPUT_SUFFIXES)

    def test_gui_studio_reexports_xtc_io_public_names(self):
        studio = load_studio_module(force_reload=True)
        studio_xtc_io = importlib.import_module('tategakiXTC_gui_studio_xtc_io')
        self.assertIs(studio.XtcPage, studio_xtc_io.XtcPage)
        self.assertIs(studio.parse_xtc_pages, studio_xtc_io.parse_xtc_pages)
        self.assertIs(studio.xtg_blob_to_qimage, studio_xtc_io.xtg_blob_to_qimage)
        self.assertIs(studio.xth_blob_to_qimage, studio_xtc_io.xth_blob_to_qimage)
        self.assertIs(studio.xt_page_blob_to_qimage, studio_xtc_io.xt_page_blob_to_qimage)

    def test_gui_studio_reexports_widgets_public_names(self):
        studio = load_studio_module(force_reload=True)
        studio_widgets = importlib.import_module('tategakiXTC_gui_studio_widgets')
        self.assertIs(studio._scroll_combo_popup_to_top_now, studio_widgets._scroll_combo_popup_to_top_now)
        self.assertIs(studio.FontPopupTopComboBox, studio_widgets.FontPopupTopComboBox)
        self.assertIs(studio.VisibleArrowSpinBox, studio_widgets.VisibleArrowSpinBox)
        self.assertIs(studio.XtcViewerWidget, studio_widgets.XtcViewerWidget)




    def test_gui_studio_reexports_ui_helper_public_names(self):
        studio = load_studio_module(force_reload=True)
        studio_ui_helpers = importlib.import_module('tategakiXTC_gui_studio_ui_helpers')
        self.assertIs(studio._bulk_block_signals, studio_ui_helpers._bulk_block_signals)
        self.assertIs(studio._coerce_ui_message_text, studio_ui_helpers._coerce_ui_message_text)
        self.assertIs(studio._connect_signal_best_effort, studio_ui_helpers._connect_signal_best_effort)
        self.assertIs(studio._flush_pending_ui_changes_impl, studio_ui_helpers.flush_pending_ui_changes)
        self.assertIs(studio._safe_delete_qobject_later, studio_ui_helpers._safe_delete_qobject_later)


    def test_gui_studio_dependency_helper_wrappers_delegate_to_split_module(self):
        studio = importlib.import_module('tategakiXTC_gui_studio')
        helpers = importlib.import_module('tategakiXTC_gui_studio_dependency_helpers')
        self.assertIs(studio._log_optional_dependency_status_impl, helpers.log_optional_dependency_status)
        self.assertIs(studio._missing_dependencies_for_targets_impl, helpers.missing_dependencies_for_targets)
        self.assertIs(studio._check_conversion_dependencies_impl, helpers.check_conversion_dependencies)

        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_dependency_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_dependency_helpers import', source)
        for symbol in (
            'log_optional_dependency_status',
            'missing_dependencies_for_targets',
            'check_conversion_dependencies',
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(f'def {symbol}(', helper_source)
        self.assertNotIn('def log_optional_dependency_status(', source)
        self.assertNotIn('def missing_dependencies_for_targets(', source)
        self.assertNotIn('def check_conversion_dependencies(', source)


    def test_gui_studio_dialog_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_dialog_helpers = importlib.import_module('tategakiXTC_gui_studio_dialog_helpers')

        self.assertIs(
            studio._show_warning_dialog_with_status_fallback_impl,
            studio_dialog_helpers.show_warning_dialog_with_status_fallback,
        )
        self.assertIs(
            studio._ask_question_dialog_with_status_fallback_impl,
            studio_dialog_helpers.ask_question_dialog_with_status_fallback,
        )
        self.assertIs(
            studio._get_open_file_name_with_status_fallback_impl,
            studio_dialog_helpers.get_open_file_name_with_status_fallback,
        )

        class WindowLike:
            def __init__(self):
                self.messages = []

            def _show_ui_status_message_with_reflection_or_direct_fallback(self, message, duration_ms, **kwargs):
                self.messages.append((message, duration_ms, kwargs))

        window = WindowLike()

        def fail_dialog(*_args):
            raise RuntimeError('dialog failed')

        original_warning = studio.QMessageBox.warning
        try:
            studio.QMessageBox.warning = fail_dialog
            studio.MainWindow._show_warning_dialog_with_status_fallback(window, '警告', 'fallback', duration_ms=123)
        finally:
            studio.QMessageBox.warning = original_warning

        self.assertEqual(window.messages, [('fallback', 123, {})])


    def test_gui_studio_reexports_preview_helper_public_names(self):
        studio = load_studio_module(force_reload=True)
        studio_preview_helpers = importlib.import_module('tategakiXTC_gui_studio_preview_helpers')
        self.assertIs(studio._coerce_preview_data_url, studio_preview_helpers._coerce_preview_data_url)
        self.assertIs(studio._coerce_preview_base64_text, studio_preview_helpers._coerce_preview_base64_text)
        self.assertIs(studio.MainWindow._coerce_preview_data_url, studio_preview_helpers._coerce_preview_data_url)
        self.assertIs(studio.MainWindow._coerce_preview_base64_text, studio_preview_helpers._coerce_preview_base64_text)
        self.assertIs(studio._preview_page_limit_value, studio_preview_helpers._preview_page_limit_value)
        self.assertIs(studio._preview_widget_limit_value, studio_preview_helpers._preview_widget_limit_value)

    def test_gui_studio_reexports_desktop_public_names(self):
        studio = load_studio_module(force_reload=True)
        studio_desktop = importlib.import_module('tategakiXTC_gui_studio_desktop')
        self.assertIs(studio._open_path_in_file_manager, studio_desktop._open_path_in_file_manager)

    def test_gui_studio_view_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_view_helpers = importlib.import_module('tategakiXTC_gui_studio_view_helpers')
        self.assertIs(studio._normalized_main_view_mode, studio_view_helpers._normalized_main_view_mode)
        self.assertIs(studio._preview_view_help_text, studio_view_helpers._preview_view_help_text)
        self.assertIs(studio._main_view_mode_help_text, studio_view_helpers._main_view_mode_help_text)
        self.assertIs(studio._main_view_mode_status_text, studio_view_helpers._main_view_mode_status_text)

        class WindowLike:
            pass

        window = WindowLike()
        self.assertEqual(studio.MainWindow._normalized_main_view_mode(window, 'device'), 'font')
        self.assertEqual(studio.MainWindow._normalized_main_view_mode(window, 'bad'), 'font')
        self.assertIn('右ペイン', studio.MainWindow._preview_view_help_text(window))
        self.assertEqual(studio.MainWindow._main_view_mode_status_text(window, 'font'), '右ペイン表示に切り替えました。')
        self.assertEqual(studio.MainWindow._main_view_mode_status_text(window, 'device'), '右ペイン表示に切り替えました。')




    def test_gui_studio_settings_sections_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        section_helpers = importlib.import_module('tategakiXTC_gui_studio_settings_sections_helpers')

        self.assertIs(studio._section_output_impl, section_helpers._section_output)
        self.assertIs(studio._section_composition_impl, section_helpers._section_composition)
        self.assertIs(studio._section_position_impl, section_helpers._section_position)
        self.assertIs(studio._section_language_impl, section_helpers._section_language)
        self.assertIs(studio._section_file_viewer_impl, section_helpers._section_file_viewer)

        output_source = inspect.getsource(studio.MainWindow._section_output)
        composition_source = inspect.getsource(studio.MainWindow._section_composition)
        position_source = inspect.getsource(studio.MainWindow._section_position)
        language_source = inspect.getsource(studio.MainWindow._section_language)
        file_viewer_source = inspect.getsource(studio.MainWindow._section_file_viewer)
        self.assertIn('return _section_output_impl(self)', output_source)
        self.assertIn('return _section_composition_impl(self)', composition_source)
        self.assertIn('return _section_position_impl(self)', position_source)
        self.assertIn('return _section_language_impl(self)', language_source)
        self.assertIn('return _section_file_viewer_impl(self)', file_viewer_source)
        self.assertNotIn('self.font_combo = FontPopupTopComboBox()', composition_source)
        self.assertNotIn('self.open_xtc_btn = self._make_button_from_plan', file_viewer_source)

    def test_gui_studio_top_bar_folder_batch_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        top_bar_helpers = importlib.import_module('tategakiXTC_gui_studio_top_bar_helpers')

        self.assertIs(studio._install_folder_batch_menu_action_impl, top_bar_helpers._install_folder_batch_menu_action)
        self.assertIs(studio._open_folder_batch_dialog_impl, top_bar_helpers._open_folder_batch_dialog)

        install_source = inspect.getsource(studio.MainWindow._install_folder_batch_menu_action)
        open_source = inspect.getsource(studio.MainWindow._open_folder_batch_dialog)
        self.assertIn('return _install_folder_batch_menu_action_impl(self)', install_source)
        self.assertIn('return _open_folder_batch_dialog_impl(self)', open_source)
        self.assertNotIn('open_folder_batch_dialog_for_mainwindow_real_or_warn(self)', open_source)

    def test_gui_studio_font_combo_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_font_combo_helpers = importlib.import_module('tategakiXTC_gui_studio_font_combo_helpers')

        self.assertIs(studio.current_font_value_impl, studio_font_combo_helpers.current_font_value)
        self.assertIs(studio._available_font_entries_impl, studio_font_combo_helpers._available_font_entries)
        self.assertIs(studio._set_current_font_value_impl, studio_font_combo_helpers._set_current_font_value)

        available_source = inspect.getsource(studio.MainWindow._available_font_entries)
        set_current_source = inspect.getsource(studio.MainWindow._set_current_font_value)
        self.assertIn('return _available_font_entries_impl(self)', available_source)
        self.assertIn('return _set_current_font_value_impl(self, font_value)', set_current_source)
        self.assertNotIn('core.get_font_entries()', available_source)
        self.assertNotIn('self.font_combo.setCurrentIndex(idx)', set_current_source)

    def test_gui_studio_target_select_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_target_select_helpers = importlib.import_module('tategakiXTC_gui_studio_target_select_helpers')

        self.assertIs(studio._apply_dropped_target_path_impl, studio_target_select_helpers._apply_dropped_target_path)
        self.assertIs(studio.select_target_path_impl, studio_target_select_helpers.select_target_path)
        self.assertIs(studio.select_output_folder_impl, studio_target_select_helpers.select_output_folder)
        self.assertIs(studio.select_font_file_impl, studio_target_select_helpers.select_font_file)

        select_source = inspect.getsource(studio.MainWindow.select_target_path)
        output_source = inspect.getsource(studio.MainWindow.select_output_folder)
        self.assertIn('return select_target_path_impl(self, as_file)', select_source)
        self.assertIn('return select_output_folder_impl(self)', output_source)
        self.assertNotIn('変換対象を選択', select_source)
        self.assertNotIn('保存先フォルダを選択', output_source)

    def test_gui_studio_preview_pixmap_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        pixmap_helpers = importlib.import_module('tategakiXTC_gui_studio_preview_pixmap_helpers')

        self.assertIs(studio._decorate_font_view_pixmap_impl, pixmap_helpers._decorate_font_view_pixmap)
        self.assertIs(studio._apply_preview_pixmap_impl, pixmap_helpers._apply_preview_pixmap)
        self.assertIs(studio._render_current_xtc_page_in_font_view_impl, pixmap_helpers._render_current_xtc_page_in_font_view)
        self.assertIs(studio.render_current_preview_page_impl, pixmap_helpers.render_current_preview_page)

        apply_source = inspect.getsource(studio.MainWindow._apply_preview_pixmap)
        render_source = inspect.getsource(studio.MainWindow._render_current_xtc_page_in_font_view)
        preview_source = inspect.getsource(studio.MainWindow.render_current_preview_page)
        helper_source = Path('tategakiXTC_gui_studio_preview_pixmap_helpers.py').read_text(encoding='utf-8')
        self.assertIn('return _apply_preview_pixmap_impl(self, pix)', apply_source)
        self.assertIn('return _render_current_xtc_page_in_font_view_impl(', render_source)
        self.assertIn('refresh_navigation=refresh_navigation', render_source)
        self.assertIn('qpixmap_cls=QPixmap', render_source)
        self.assertIn('xt_page_blob_to_qimage_func=xt_page_blob_to_qimage', render_source)
        self.assertIn('return render_current_preview_page_impl(self)', preview_source)
        self.assertIn('def render_current_preview_page(', helper_source)
        self.assertNotIn('QPixmap.fromImage(qimg)', render_source)
        self.assertNotIn('scaled = pix.scaled(', apply_source)
        self.assertNotIn('current_index = worker_logic._int_config_value', preview_source)

    def test_gui_studio_preview_refresh_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        refresh_helpers = importlib.import_module('tategakiXTC_gui_studio_preview_refresh_helpers')

        self.assertIs(studio._mark_preview_dirty_for_target_change_impl, refresh_helpers.mark_preview_dirty_for_target_change)
        self.assertIs(studio._request_preview_refresh_impl, refresh_helpers.request_preview_refresh)
        self.assertIs(studio._refresh_active_view_after_mode_change_impl, refresh_helpers.refresh_active_view_after_mode_change)
        self.assertIs(studio._refresh_font_preview_display_if_needed_impl, refresh_helpers.refresh_font_preview_display_if_needed)

        active_source = inspect.getsource(studio.MainWindow._refresh_active_view_after_mode_change)
        font_source = inspect.getsource(studio.MainWindow._refresh_font_preview_display_if_needed)
        helper_source = Path('tategakiXTC_gui_studio_preview_refresh_helpers.py').read_text(encoding='utf-8')
        self.assertIn('return _refresh_active_view_after_mode_change_impl(self, mode)', active_source)
        self.assertIn('return _refresh_font_preview_display_if_needed_impl(', font_source)
        self.assertIn('refresh_navigation=refresh_navigation', font_source)
        self.assertIn('def refresh_active_view_after_mode_change(', helper_source)
        self.assertIn('def refresh_font_preview_display_if_needed(', helper_source)
        self.assertNotIn("if self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) != 'font':", font_source)


    def test_gui_studio_right_pane_build_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        right_pane_helpers = importlib.import_module('tategakiXTC_gui_studio_right_pane_build_helpers')

        self.assertIs(studio._build_right_preview_impl, right_pane_helpers._build_right_preview)
        self.assertIs(studio._build_view_toggle_bar_impl, right_pane_helpers._build_view_toggle_bar)
        self.assertIs(
            studio._add_nav_controls_to_layout_impl,
            right_pane_helpers._add_nav_controls_to_layout,
        )
        self.assertIs(
            studio._add_preview_zoom_controls_to_layout_impl,
            right_pane_helpers._add_preview_zoom_controls_to_layout,
        )

        right_source = inspect.getsource(studio.MainWindow._build_right_preview)
        toggle_source = inspect.getsource(studio.MainWindow._build_view_toggle_bar)
        nav_source = inspect.getsource(studio.MainWindow._add_nav_controls_to_layout)
        self.assertIn('return _build_right_preview_impl(self)', right_source)
        self.assertIn('return _build_view_toggle_bar_impl(self)', toggle_source)
        self.assertIn('_add_nav_controls_to_layout_impl(', nav_source)
        self.assertNotIn('self.preview_stack = QStackedWidget()', right_source)
        self.assertNotIn('QVBoxLayout(bar)', toggle_source)
        self.assertNotIn('self.page_input = QSpinBox()', nav_source)

    def test_gui_studio_preview_layout_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        preview_layout_helpers = importlib.import_module('tategakiXTC_gui_studio_preview_layout_helpers')

        self.assertIs(studio._sync_viewer_size_impl, preview_layout_helpers._sync_viewer_size)
        self.assertIs(studio._sync_preview_size_impl, preview_layout_helpers._sync_preview_size)
        self.assertIs(
            studio._sync_font_preview_scroll_placement_impl,
            preview_layout_helpers._sync_font_preview_scroll_placement,
        )

        viewer_source = inspect.getsource(studio.MainWindow._sync_viewer_size)
        preview_source = inspect.getsource(studio.MainWindow._sync_preview_size)
        scroll_source = inspect.getsource(studio.MainWindow._sync_font_preview_scroll_placement)
        self.assertIn('_sync_viewer_size_impl(self)', viewer_source)
        self.assertIn('_sync_preview_size_impl(self)', preview_source)
        self.assertIn('_sync_font_preview_scroll_placement_impl(self, reset_horizontal=reset_horizontal)', scroll_source)
        self.assertNotIn('viewer_widget.setMinimumSize', viewer_source)
        self.assertNotIn('setContentsMargins(leading_gap, 0, 0, 0)', scroll_source)

    def test_gui_studio_wheel_guard_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        wheel_guard_helpers = importlib.import_module('tategakiXTC_gui_studio_wheel_guard_helpers')

        self.assertIs(
            studio._should_suppress_center_settings_wheel_value_change_impl,
            wheel_guard_helpers._should_suppress_center_settings_wheel_value_change,
        )
        self.assertIs(
            studio._scroll_center_settings_from_wheel_event_impl,
            wheel_guard_helpers._scroll_center_settings_from_wheel_event,
        )
        self.assertIs(studio._clear_startup_input_focus_impl, wheel_guard_helpers._clear_startup_input_focus)

        guard_source = inspect.getsource(studio.MainWindow._should_suppress_center_settings_wheel_value_change)
        scroll_source = inspect.getsource(studio.MainWindow._scroll_center_settings_from_wheel_event)
        focus_source = inspect.getsource(studio.MainWindow._clear_startup_input_focus)
        self.assertIn('_should_suppress_center_settings_wheel_value_change_impl(self, obj)', guard_source)
        self.assertIn('_scroll_center_settings_from_wheel_event_impl(self, event)', scroll_source)
        self.assertIn('_clear_startup_input_focus_impl(self)', focus_source)
        self.assertNotIn('angleDelta', scroll_source)
        self.assertNotIn('QApplication.focusWidget', focus_source)

    def test_gui_studio_settings_restore_residual_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        restore_helpers = importlib.import_module('tategakiXTC_gui_studio_settings_restore_helpers')

        self.assertIs(studio._has_restorable_user_settings_impl, restore_helpers._has_restorable_user_settings)
        self.assertIs(studio._window_state_restore_payload_impl, restore_helpers._window_state_restore_payload)
        self.assertIs(studio._settings_restore_payload_impl, restore_helpers._settings_restore_payload)
        self.assertIs(studio._startup_preview_defaults_payload_impl, restore_helpers._startup_preview_defaults_payload)

        window_state_source = inspect.getsource(studio.MainWindow._window_state_restore_payload)
        settings_payload_source = inspect.getsource(studio.MainWindow._settings_restore_payload)
        startup_defaults_source = inspect.getsource(studio.MainWindow._startup_preview_defaults_payload)
        self.assertIn('return _window_state_restore_payload_impl(self)', window_state_source)
        self.assertIn('return _settings_restore_payload_impl(self)', settings_payload_source)
        self.assertIn('return _startup_preview_defaults_payload_impl(self, payload)', startup_defaults_source)
        self.assertNotIn('build_window_state_restore_payload(', window_state_source)
        self.assertNotIn('build_settings_restore_payload(', settings_payload_source)

    def test_gui_studio_results_actions_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        result_actions_helpers = importlib.import_module('tategakiXTC_gui_studio_results_actions_helpers')

        self.assertIs(studio._show_conversion_results_impl, result_actions_helpers._show_conversion_results)
        self.assertIs(studio.on_result_item_clicked_impl, result_actions_helpers.on_result_item_clicked)
        self.assertIs(studio.load_selected_result_impl, result_actions_helpers.load_selected_result)
        self.assertIs(studio._apply_loaded_xtc_ui_context_impl, result_actions_helpers._apply_loaded_xtc_ui_context)
        self.assertIs(studio._results_item_path_impl, result_actions_helpers._results_item_path)

        show_source = inspect.getsource(studio.MainWindow._show_conversion_results)
        click_source = inspect.getsource(studio.MainWindow.on_result_item_clicked)
        load_source = inspect.getsource(studio.MainWindow.load_selected_result)
        apply_source = inspect.getsource(studio.MainWindow._apply_loaded_xtc_ui_context)
        result_item_path_source = inspect.getsource(studio.MainWindow._results_item_path)
        self.assertIn('return _show_conversion_results_impl(self, converted_files, summary_lines)', show_source)
        self.assertIn('return on_result_item_clicked_impl(self, item)', click_source)
        self.assertIn('return load_selected_result_impl(self)', load_source)
        self.assertIn('return _apply_loaded_xtc_ui_context_impl(self, context)', apply_source)
        self.assertIn('return _results_item_path_impl(self, item)', result_item_path_source)
        self.assertNotIn('build_results_apply_context(', show_source)
        self.assertNotIn('self._load_xtc_from_path_with_result(path_value)', click_source)


    def test_gui_studio_path_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_path_helpers = importlib.import_module('tategakiXTC_gui_studio_path_helpers')
        self.assertIs(studio._supported_targets_for_path, studio_path_helpers._supported_targets_for_path)
        self.assertIs(studio._default_output_name_for_target, studio_path_helpers._default_output_name_for_target)

        class WindowLike:
            def current_output_format(self):
                return 'xtc'

        calls = []
        def resolver(path):
            calls.append(path)
            return [path]

        target = Path('tests')
        original_resolver = studio.ConversionWorker._resolve_supported_targets
        original_get_output = studio.core.get_output_path_for_target
        original_sanitize = studio.ConversionWorker._sanitize_output_stem
        try:
            studio.ConversionWorker._resolve_supported_targets = staticmethod(resolver)
            self.assertEqual(studio.MainWindow._supported_targets_for_path(WindowLike(), str(target)), [target])
            self.assertEqual(calls, [target])
            studio.core.get_output_path_for_target = lambda path, output_format: path.with_name('Hello Unsafe!!.xtc')
            studio.ConversionWorker._sanitize_output_stem = staticmethod(lambda value: 'safe-name')
            self.assertEqual(
                studio.MainWindow._default_output_name_for_target(WindowLike(), Path('source.txt')),
                'safe-name',
            )
        finally:
            studio.ConversionWorker._resolve_supported_targets = original_resolver
            studio.core.get_output_path_for_target = original_get_output
            studio.ConversionWorker._sanitize_output_stem = original_sanitize

    def test_gui_studio_settings_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_settings_helpers = importlib.import_module('tategakiXTC_gui_studio_settings_helpers')

        class SettingsWithStoredValue:
            def value(self, key, default=None):
                values = {
                    'existing': 'stored',
                    'number': '12',
                    'flag': 'true',
                }
                return values.get(key, default)

        class WindowLike:
            pass

        window = WindowLike()
        window.settings_store = SettingsWithStoredValue()
        self.assertTrue(studio.MainWindow._settings_contains_key(window, 'existing'))
        self.assertEqual(studio.MainWindow._settings_int_value(window, 'number', 0), 12)
        self.assertTrue(studio.MainWindow._settings_bool_value(window, 'flag', False))
        self.assertEqual(studio.MainWindow._settings_str_value(window, 'missing', 'fallback'), 'fallback')
        self.assertEqual(
            studio.MainWindow._plan_int_tuple_value(
                window,
                {'sizes': ['1', 2, 3]},
                'sizes',
                (9, 9, 9),
                expected_length=3,
            ),
            (1, 2, 3),
        )
        self.assertEqual(
            studio.MainWindow._combo_find_data_index(window, object(), 'x'),
            studio_settings_helpers._combo_find_data_index(object(), 'x'),
        )

    def test_gui_studio_reexports_runtime_public_names(self):
        studio = load_studio_module(force_reload=True)
        self.assertIs(studio._iter_runtime_xtc_page_items, studio_runtime._iter_runtime_xtc_page_items)
        self.assertIs(studio._normalize_runtime_xtc_pages, studio_runtime._normalize_runtime_xtc_pages)

    def test_gui_studio_reexports_worker_public_names(self):
        studio = load_studio_module(force_reload=True)
        studio_worker = importlib.import_module('tategakiXTC_gui_studio_worker')
        self.assertIs(studio.ConversionWorker, studio_worker.ConversionWorker)
        self.assertIs(studio.build_conversion_args, studio_worker.build_conversion_args)
        self.assertIs(studio.resolve_supported_conversion_targets, studio_worker.resolve_supported_conversion_targets)
        self.assertIs(studio.sanitize_output_stem, studio_worker.sanitize_output_stem)
        self.assertIs(studio.plan_output_path_for_target, studio_worker.plan_output_path_for_target)
        self.assertIs(studio.build_conversion_summary, studio_worker.build_conversion_summary)
        self.assertIs(studio._process_single_image_file, studio_worker._process_single_image_file)
        self.assertIs(studio.PROCESSOR_BY_SUFFIX, studio_worker.PROCESSOR_BY_SUFFIX)

    def test_gui_studio_settings_contains_helper_tolerates_qsettings_stubs(self):
        studio = load_studio_module(force_reload=True)

        class SettingsWithoutContains:
            def value(self, key, default=None):
                return default

        class SettingsWithStoredValue:
            def value(self, key, default=None):
                if key == 'existing':
                    return 'stored'
                return default

        class WindowLike:
            pass

        window = WindowLike()
        window.settings_store = SettingsWithoutContains()
        self.assertFalse(studio.MainWindow._settings_contains_key(window, 'missing'))

        window.settings_store = SettingsWithStoredValue()
        self.assertTrue(studio.MainWindow._settings_contains_key(window, 'existing'))
        self.assertFalse(studio.MainWindow._settings_contains_key(window, 'missing'))

    def test_gui_studio_main_window_avoids_direct_qframe_shape_constants_for_stub_compatibility(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        build_ui_source = source[source.index('    def _build_ui(self):'):source.index('    def _build_top_bar(self):')]
        self.assertNotIn('QFrame.HLine', build_ui_source)
        self.assertIn("_qframe_shape_constant('HLine'", build_ui_source)

    def test_gui_studio_plan_scroll_bar_policy_tolerates_qt_stubs(self):
        studio = load_studio_module(force_reload=True)

        class WindowLike:
            def _plan_token_value(self, payload_obj, key, default):
                payload = dict(payload_obj) if isinstance(payload_obj, dict) else {}
                value = payload.get(key, default)
                return str(value).strip().lower().replace('-', '_') or default

            def _qt_constant(self, name, fallback=0):
                return studio.MainWindow._qt_constant(self, name, fallback)

        window = WindowLike()
        always_off = studio.MainWindow._qt_constant(window, 'ScrollBarAlwaysOff', 0)
        self.assertEqual(
            studio.MainWindow._plan_scroll_bar_policy_value(window, {'policy': 'always_on'}, 'policy', 'always_off'),
            studio.MainWindow._qt_constant(window, 'ScrollBarAlwaysOn', always_off),
        )
        self.assertEqual(
            studio.MainWindow._plan_scroll_bar_policy_value(window, {'policy': 'as_needed'}, 'policy', 'always_off'),
            studio.MainWindow._qt_constant(window, 'ScrollBarAsNeeded', always_off),
        )

    def test_gui_studio_combo_find_data_index_tolerates_qt_stubs(self):
        studio = load_studio_module(force_reload=True)

        class DummyCombo:
            def findData(self, _value):
                class NonComparableIndex:
                    pass
                return NonComparableIndex()

        class MissingFindData:
            pass

        class GoodCombo:
            def findData(self, _value):
                return 2

        class WindowLike:
            pass

        window = WindowLike()
        self.assertEqual(studio.MainWindow._combo_find_data_index(window, DummyCombo(), 'x'), -1)
        self.assertEqual(studio.MainWindow._combo_find_data_index(window, MissingFindData(), 'x'), -1)
        self.assertEqual(studio.MainWindow._combo_find_data_index(window, GoodCombo(), 'x'), 2)



    def test_gui_studio_keeps_ui_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_ui_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_ui_helpers import', source)
        for symbol in (
            '_bulk_block_signals',
            '_coerce_ui_message_text',
            '_connect_signal_best_effort',
            '_safe_delete_qobject_later',
            'flush_pending_ui_changes',
        ):
            with self.subTest(symbol=symbol):
                self.assertNotIn(f'def {symbol}(', source)
                self.assertIn(f'def {symbol}(', helper_source)


    def test_gui_studio_keeps_dialog_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_dialog_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_dialog_helpers import', source)
        self.assertIn('_show_warning_dialog_with_status_fallback_impl(', source)
        self.assertIn('_get_existing_directory_with_status_fallback_impl(', source)
        self.assertIn('def show_warning_dialog_with_status_fallback(', helper_source)
        self.assertIn('def ask_question_dialog_with_status_fallback(', helper_source)
        self.assertIn('def get_existing_directory_with_status_fallback(', helper_source)
        self.assertNotIn('QMessageBox.warning(self, title, message)', source)
        self.assertNotIn('QFileDialog.getOpenFileName(self, title, start_dir, filter_text)', source)
        self.assertNotIn('from PySide6', helper_source)


    def test_gui_studio_keeps_preview_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preview_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preview_helpers import', source)
        for symbol in (
            '_coerce_preview_data_url',
            '_coerce_preview_base64_text',
            '_preview_page_limit_value',
            '_preview_widget_limit_value',
        ):
            with self.subTest(symbol=symbol):
                self.assertNotIn(f'def {symbol}(', source)
                self.assertIn(f'def {symbol}(', helper_source)

    def test_gui_studio_keeps_desktop_helper_implementation_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        desktop_source = Path('tategakiXTC_gui_studio_desktop.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_desktop import', source)
        self.assertNotIn('def _open_path_in_file_manager(', source)
        self.assertIn('def _open_path_in_file_manager(', desktop_source)


    def test_gui_studio_path_helper_implementation_is_split_from_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_path_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_path_helpers import', source)
        self.assertIn('return _supported_targets_for_path(', source)
        self.assertIn('return _default_output_name_for_target(', source)
        self.assertIn('def _supported_targets_for_path(', helper_source)
        self.assertIn('def _default_output_name_for_target(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_view_helper_implementation_is_split_from_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_view_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_view_helpers import', source)
        self.assertIn('return _normalized_main_view_mode(', source)
        self.assertIn('return _preview_view_help_text(', source)
        self.assertIn('def _normalized_main_view_mode(', helper_source)
        self.assertIn('def _preview_view_help_text(', helper_source)
        self.assertIn('def _main_view_mode_status_text(', helper_source)
        self.assertNotIn('def _normalized_main_view_mode(mode: object)', source)
        self.assertNotIn('def _preview_view_help_text() -> str', source)


    def test_gui_studio_preset_helper_implementation_is_split_from_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_preset_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_preset_helpers import', source)
        self.assertIn('return selected_preset_key_from_combo(', source)
        self.assertIn('return preset_combo_entries(', source)
        self.assertIn('return preset_side_summary_text(', source)
        self.assertIn('def selected_preset_key_from_combo(', helper_source)
        self.assertIn('def preset_combo_entries(', helper_source)
        self.assertIn('def preset_side_summary_text(', helper_source)
        self.assertNotIn('def selected_preset_key_from_combo(', source)
        self.assertNotIn('def preset_side_summary_text(summary: object)', source)
        self.assertNotIn('from PySide6', helper_source)


    def test_gui_studio_settings_helper_implementation_is_split_from_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_settings_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_settings_helpers import', source)
        self.assertIn('return _settings_contains_key_in_store(', source)
        self.assertIn('return _plan_int_tuple_value_from_payload(', source)
        self.assertIn('return _combo_find_data_index_for_widget(', source)
        self.assertIn('def _settings_contains_key(', helper_source)
        self.assertIn('def _plan_int_tuple_value(', helper_source)
        self.assertIn('def _combo_find_data_index(', helper_source)

    def test_gui_studio_preset_actions_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_preset_actions_helpers')
        self.assertIs(studio.save_preset_impl, helpers.save_preset)
        self.assertIs(studio.apply_preset_impl, helpers.apply_preset)
        self.assertIs(studio._verify_preset_save_readback_impl, helpers.verify_preset_save_readback)
        self.assertIs(studio._preset_rename_dialog_result_impl, helpers.preset_rename_dialog_result)
        self.assertIs(studio.rename_preset_display_name_impl, helpers.rename_preset_display_name)

        class WindowLike:
            def __init__(self):
                self.preset_definitions = {}
                self.shown = []

            def _show_ui_status_message_unless_render_failure_visible(self, message, timeout):
                self.shown.append((message, timeout))

        # apply_preset with an unknown key reports a not-found status and returns early.
        window = WindowLike()
        studio.MainWindow.apply_preset(window, 'missing')
        self.assertEqual(len(window.shown), 1)
        self.assertIn('見つかりません', window.shown[0][0])

    def test_gui_studio_keeps_preset_actions_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preset_actions_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preset_actions_helpers import', source)
        self.assertIn('save_preset_impl(self, key)', source)
        self.assertIn('apply_preset_impl(self, key)', source)
        self.assertIn('def save_preset(', helper_source)
        self.assertIn('def apply_preset(', helper_source)
        self.assertIn('def verify_preset_save_readback(', helper_source)
        self.assertIn('def preset_rename_dialog_result(', helper_source)
        self.assertIn('_preset_rename_dialog_result_impl(', source)
        self.assertIn('dialog_cls=QDialog', source)

    def test_gui_studio_preset_summary_layout_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_preset_summary_layout_helpers')
        self.assertIs(studio._preset_summary_label_measurement_width_impl, helpers.preset_summary_label_measurement_width)
        self.assertIs(studio._queue_preset_summary_label_layout_retry_impl, helpers.queue_preset_summary_label_layout_retry)
        self.assertIs(studio._update_preset_summary_label_layout_impl, helpers.update_preset_summary_label_layout)
        self.assertIs(studio._sync_summary_payload_impl, helpers.sync_summary_payload)
        self.assertIs(studio._sync_current_settings_summary_impl, helpers.sync_current_settings_summary)
        self.assertIs(studio._sync_selected_preset_summary_impl, helpers.sync_selected_preset_summary)
        self.assertIs(studio._refresh_preset_ui_impl, helpers.refresh_preset_ui)

        class LabelStub:
            def __init__(self):
                self.text_value = ''
                self.tooltip_value = ''
                self.adjusted = False
                self.updated = False

            def setText(self, value):
                self.text_value = value

            def adjustSize(self):
                self.adjusted = True

            def update(self):
                self.updated = True

        class ComboStub:
            def __init__(self):
                self.tooltip_value = ''

            def setToolTip(self, value):
                self.tooltip_value = value

        class WindowLike:
            def __init__(self):
                self.preset_summary_label = LabelStub()
                self.preset_combo = ComboStub()
                self.preset_definitions = {'p1': {'name': 'Preset 1'}}
                self.layout_updates = 0

            def selected_preset_key(self):
                return 'p1'

            def _preset_side_summary_text(self, summary):
                return f'side:{summary}'

            def _preset_summary_plain_text(self, preset, *, summary_tag='', include_name_line=True):
                return f'{preset["name"]}:{summary_tag}:{include_name_line}'

            def _update_preset_summary_label_layout(self):
                self.layout_updates += 1

        window = WindowLike()
        studio.MainWindow._sync_selected_preset_summary(window)
        self.assertEqual(window.preset_summary_label.text_value, 'side:Preset 1::False')
        self.assertEqual(window.preset_combo.tooltip_value, 'side:Preset 1::False')
        self.assertTrue(window.preset_summary_label.adjusted)
        self.assertTrue(window.preset_summary_label.updated)
        self.assertEqual(window.layout_updates, 1)

    def test_gui_studio_keeps_preset_summary_ui_helpers_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preset_summary_layout_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preset_summary_layout_helpers import', source)
        for symbol in (
            'sync_summary_payload',
            'sync_current_settings_summary',
            'sync_selected_preset_summary',
            'refresh_preset_ui',
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(f'def {symbol}(', helper_source)
        self.assertIn('_sync_summary_payload_impl(self, payload, summary_tag=summary_tag)', source)
        self.assertIn('_refresh_preset_ui_impl(self, bulk_block_signals=_bulk_block_signals)', source)
        self.assertNotIn('def sync_summary_payload(', source)
        self.assertNotIn('def sync_selected_preset_summary(', source)
        self.assertNotIn('def refresh_preset_ui(', source)

    def test_gui_studio_render_status_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_render_status_helpers')
        self.assertIs(studio._refresh_successful_preview_render_status_impl, helpers._refresh_successful_preview_render_status)
        self.assertIs(studio._refresh_successful_device_render_status_impl, helpers._refresh_successful_device_render_status)
        self.assertIs(studio._handle_xtc_render_failure_impl, helpers._handle_xtc_render_failure)

        class WindowLike:
            def __init__(self):
                self.last_preview_requested_limit = 3
                self.preview_pages_truncated = False

            def _runtime_preview_pages(self):
                return ['p1', 'p2', 'p3']

            def current_ui_language_value(self):
                return 'ja'

        message = studio.MainWindow._current_preview_success_status_message(WindowLike())
        self.assertTrue(message)
        self.assertIn('3', message)

    def test_gui_studio_keeps_render_status_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_render_status_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_render_status_helpers import', source)
        self.assertIn('_refresh_successful_preview_render_status_impl(self)', source)
        self.assertIn('_handle_xtc_render_failure_impl(self, exc, refresh_navigation=refresh_navigation)', source)
        self.assertIn('def _refresh_successful_preview_render_status(', helper_source)
        self.assertIn('def _refresh_successful_device_render_status(', helper_source)
        self.assertIn('def _handle_xtc_render_failure(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_display_context_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_display_context_helpers')
        self.assertIs(studio._set_current_xtc_display_name_impl, helpers._set_current_xtc_display_name)
        self.assertIs(studio._restore_shared_status_for_visible_display_context_impl, helpers._restore_shared_status_for_visible_display_context)
        self.assertIs(studio._sync_active_display_context_for_visible_page_impl, helpers._sync_active_display_context_for_visible_page)

        class LabelStub:
            def __init__(self):
                self.text_value = ''

            def setText(self, value):
                self.text_value = value

            def text(self):
                return self.text_value

        class WindowLike:
            def __init__(self):
                self.current_xtc_label = LabelStub()

            def current_ui_language_value(self):
                return 'ja'

        window = WindowLike()
        studio.MainWindow._set_current_xtc_display_name(window, ' book.xtc ')
        self.assertEqual(window.current_xtc_label.text(), '表示中: book.xtc')

    def test_gui_studio_keeps_display_context_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_display_context_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_display_context_helpers import', source)
        self.assertIn('_restore_shared_status_for_visible_display_context_impl(self)', source)
        self.assertIn('_sync_active_display_context_for_visible_page_impl(self)', source)
        self.assertIn('def _restore_shared_status_for_visible_display_context(', helper_source)
        self.assertIn('def _sync_active_display_context_for_visible_page(', helper_source)
        self.assertIn('def _set_current_xtc_display_name(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_preview_context_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_preview_context_helpers')
        self.assertIs(studio._apply_preview_success_context_impl, helpers._apply_preview_success_context)
        self.assertIs(studio._apply_preview_failure_context_impl, helpers._apply_preview_failure_context)
        self.assertIs(studio._effective_right_pane_source_impl, helpers._effective_right_pane_source)

        class WindowLike:
            def __init__(self, source, device_pages):
                self.device_view_source = source
                self._device_pages = device_pages

            def _normalized_right_pane_source_value(self, value, *, default='xtc'):
                return studio.MainWindow._normalized_right_pane_source_value(self, value, default=default)

            def _runtime_device_preview_pages(self):
                return self._device_pages

            def _effective_right_pane_source(self, value=None):
                return studio.MainWindow._effective_right_pane_source(self, value)

        # 'preview' source with device preview pages stays 'preview'.
        self.assertEqual(studio.MainWindow._effective_right_pane_source(WindowLike('preview', ['p'])), 'preview')
        # 'preview' source without pages falls back to 'xtc'.
        self.assertEqual(studio.MainWindow._effective_right_pane_source(WindowLike('preview', [])), 'xtc')

    def test_gui_studio_keeps_preview_context_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preview_context_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preview_context_helpers import', source)
        self.assertIn('return _apply_preview_success_context_impl(', source)
        self.assertIn('return _apply_preview_failure_context_impl(', source)
        self.assertIn('def _apply_preview_success_context(', helper_source)
        self.assertIn('def _apply_preview_failure_context(', helper_source)
        self.assertIn('def _apply_preview_progress_bar_context(', helper_source)
        self.assertNotIn('from PySide6', helper_source)
        # QApplication.processEvents is threaded in from the entry wrapper.
        self.assertIn('process_events=getattr(QApplication', source)

    def test_gui_studio_preview_button_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_preview_button_helpers')
        self.assertIs(studio._is_file_viewer_mode_active_impl, helpers._is_file_viewer_mode_active)
        self.assertIs(studio._has_loaded_xtc_viewer_document_impl, helpers._has_loaded_xtc_viewer_document)
        self.assertIs(studio._refresh_preview_update_button_for_current_state_impl, helpers._refresh_preview_update_button_for_current_state)

        class WindowLike:
            def __init__(self, xtc_pages, path_text):
                self._xtc_pages = xtc_pages
                self._loaded_xtc_path_text = path_text

            def _runtime_xtc_pages(self):
                return self._xtc_pages

            def _has_loaded_xtc_viewer_document(self):
                return studio.MainWindow._has_loaded_xtc_viewer_document(self)

        # Loaded XTC pages with a loaded-file identity is file-viewer mode.
        loaded = WindowLike(['p1'], 'exports/book.xtc')
        self.assertTrue(studio.MainWindow._is_file_viewer_mode_active(loaded))
        # Bare XTC pages without a loaded-file identity is not.
        generated = WindowLike(['p1'], '')
        self.assertFalse(studio.MainWindow._is_file_viewer_mode_active(generated))

    def test_gui_studio_keeps_preview_button_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preview_button_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preview_button_helpers import', source)
        self.assertIn('return _is_file_viewer_mode_active_impl(', source)
        self.assertIn('_refresh_preview_update_button_for_current_state_impl(self, context)', source)
        self.assertIn('def _is_file_viewer_mode_active(', helper_source)
        self.assertIn('def _refresh_preview_update_button_for_current_state(', helper_source)
        self.assertIn('def _mark_preview_update_button_pending(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_overlay_margin_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_overlay_margin_helpers')
        self.assertIs(studio._minimum_bottom_overlay_margin_impl, helpers._minimum_bottom_overlay_margin)
        self.assertIs(studio._sync_bottom_overlay_margin_to_ui_impl, helpers._sync_bottom_overlay_margin_to_ui)
        self.assertIs(studio._effective_bottom_overlay_margin_impl, helpers._effective_bottom_overlay_margin)

        class CheckStub:
            def __init__(self, checked):
                self._checked = checked

            def isChecked(self):
                return self._checked

        class SpinStub:
            def __init__(self, value):
                self._value = value

            def value(self):
                return self._value

        class WindowLike:
            def __init__(self):
                self.page_number_check = CheckStub(True)
                self.progress_bar_check = CheckStub(False)
                self.page_number_font_size_spin = SpinStub(20)

            def _minimum_bottom_overlay_margin(self, enabled_override=None):
                return studio.MainWindow._minimum_bottom_overlay_margin(self, enabled_override)

        window = WindowLike()
        # page number font size 20 reserves font_size + 1 == 21
        self.assertEqual(studio.MainWindow._minimum_bottom_overlay_margin(window), 21)
        # effective margin lifts a smaller user margin up to the reserved minimum
        window.margin_b_spin = SpinStub(10)
        self.assertEqual(studio.MainWindow._effective_bottom_overlay_margin(window), 21)

    def test_gui_studio_keeps_overlay_margin_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_overlay_margin_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_overlay_margin_helpers import', source)
        self.assertIn('return _minimum_bottom_overlay_margin_impl(', source)
        self.assertIn('return _sync_bottom_overlay_margin_to_ui_impl(', source)
        self.assertIn('def _minimum_bottom_overlay_margin(', helper_source)
        self.assertIn('def _sync_bottom_overlay_margin_to_ui(', helper_source)
        self.assertIn('def _bottom_overlay_margin_auto_save_payload(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_live_preview_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_live_preview_helpers')
        self.assertIs(studio._schedule_live_preview_refresh_impl, helpers._schedule_live_preview_refresh)
        self.assertIs(studio._has_active_preview_for_live_refresh_impl, helpers._has_active_preview_for_live_refresh)
        self.assertIs(studio._mark_preview_dirty_without_auto_refresh_impl, helpers._mark_preview_dirty_without_auto_refresh)

        # The entry wrapper threads the entry-module tuning constant through to
        # the helper, so a page limit above the auto-refresh cap disables it.
        class WindowLike:
            def __init__(self, limit):
                self._limit = limit

            def _current_preview_page_limit_value(self):
                return self._limit

        cap = studio._AUTO_LIVE_PREVIEW_PAGE_LIMIT_MAX
        self.assertTrue(studio.MainWindow._should_auto_live_preview_refresh(WindowLike(cap)))
        self.assertFalse(studio.MainWindow._should_auto_live_preview_refresh(WindowLike(cap + 1)))

    def test_gui_studio_keeps_live_preview_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_live_preview_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_live_preview_helpers import', source)
        self.assertIn('return _schedule_live_preview_refresh_impl(', source)
        self.assertIn('_has_active_preview_for_live_refresh_impl(self)', source)
        self.assertIn('def _schedule_live_preview_refresh(', helper_source)
        self.assertIn('def _has_active_preview_for_live_refresh(', helper_source)
        self.assertIn('def _cancel_pending_settings_live_preview_refresh(', helper_source)
        # QTimer-bound scheduler and the delay constant stay in the entry module.
        self.assertNotIn('from PySide6', helper_source)
        self.assertNotIn('def _queue_live_preview_refresh_timer(', helper_source)

    def test_gui_studio_settings_save_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_settings_save_helpers')
        self.assertIs(studio._current_render_settings_base_impl, helpers._current_render_settings_base)
        self.assertIs(studio.current_settings_dict_impl, helpers.current_settings_dict)
        self.assertIs(studio._settings_save_payload_impl, helpers._settings_save_payload)
        self.assertIs(studio._prepare_conversion_settings_impl, helpers.prepare_conversion_settings)

        class WindowLike:
            def __init__(self):
                self.base_calls = 0

            def _current_render_settings_base(self):
                self.base_calls += 1
                return {'target': 'in.txt', 'width': 480, 'height': 800}

            def current_output_conflict_mode(self):
                return 'rename'

        window = WindowLike()
        result = studio.MainWindow.current_settings_dict(window)
        self.assertEqual(window.base_calls, 1)
        self.assertEqual(result.get('target'), 'in.txt')

    def test_gui_studio_keeps_settings_save_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_settings_save_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_settings_save_helpers import', source)
        self.assertIn('return _window_state_save_payload_impl(', source)
        self.assertIn('return current_settings_dict_impl(', source)
        self.assertIn('return _prepare_conversion_settings_impl(', source)
        self.assertIn('def _window_state_save_payload(', helper_source)
        self.assertIn('def current_settings_dict(', helper_source)
        self.assertIn('def _settings_save_payload(', helper_source)
        self.assertIn('def prepare_conversion_settings(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_navigation_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_navigation_helpers')
        self.assertIs(studio._xtc_navigation_payload_impl, helpers._xtc_navigation_payload)
        self.assertIs(studio._xtc_page_count_impl, helpers._xtc_page_count)
        self.assertIs(studio.update_navigation_ui_impl, helpers.update_navigation_ui)

        class WindowLike:
            def __init__(self, source, xtc_pages, device_pages):
                self._source = source
                self._xtc_pages = xtc_pages
                self._device_pages = device_pages

            def _effective_device_view_source(self):
                return self._source

            def _runtime_xtc_pages(self):
                return self._xtc_pages

            def _runtime_device_preview_pages(self):
                return self._device_pages

        xtc_window = WindowLike('xtc', ['a', 'b', 'c'], [])
        self.assertEqual(studio.MainWindow._xtc_page_count(xtc_window), 3)
        preview_window = WindowLike('preview', ['a', 'b', 'c'], ['p', 'q'])
        self.assertEqual(studio.MainWindow._xtc_page_count(preview_window), 2)

    def test_gui_studio_keeps_navigation_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_navigation_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_navigation_helpers import', source)
        self.assertIn('return _xtc_navigation_payload_impl(', source)
        self.assertIn('_apply_xtc_navigation_ui_impl(self, payload)', source)
        self.assertIn('def _xtc_navigation_payload(', helper_source)
        self.assertIn('def _apply_xtc_navigation_ui(', helper_source)
        self.assertIn('def update_navigation_ui(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_preview_zoom_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_preview_zoom_helpers')
        self.assertIs(studio._preview_zoom_left_bias_impl, helpers._preview_zoom_left_bias)
        self.assertIs(studio._preview_zoom_factor_impl, helpers._preview_zoom_factor)
        self.assertIs(studio._viewport_width_for_scroll_area_impl, helpers._viewport_width_for_scroll_area)

        class WindowLike:
            def __init__(self, zoom_factor):
                self._zoom_factor = zoom_factor

            def _preview_zoom_factor(self):
                return self._zoom_factor

        # 100% keeps the preview centered (no left bias); 300% reaches full bias.
        self.assertEqual(studio.MainWindow._preview_zoom_left_bias(WindowLike(1.0)), 0.0)
        self.assertEqual(studio.MainWindow._preview_zoom_left_bias(WindowLike(3.0)), 1.0)
        mid = studio.MainWindow._preview_zoom_left_bias(WindowLike(2.0))
        self.assertTrue(0.0 < mid < 1.0)

    def test_gui_studio_keeps_preview_zoom_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preview_zoom_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preview_zoom_helpers import', source)
        self.assertIn('return _preview_zoom_left_bias_impl(', source)
        self.assertIn('return _normalize_preview_zoom_pct_impl(', source)
        self.assertIn('def _preview_zoom_left_bias(', helper_source)
        self.assertIn('def _sync_preview_zoom_control_state(', helper_source)
        self.assertIn('def _font_preview_leading_gap(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_viewer_profile_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_viewer_profile_helpers')
        self.assertIs(studio._current_viewer_profile_impl, helpers._current_viewer_profile)
        self.assertIs(studio._viewer_profile_for_dimensions_impl, helpers._viewer_profile_for_dimensions)
        self.assertIs(studio._active_device_viewer_profile_impl, helpers._active_device_viewer_profile)
        self.assertIs(studio._apply_viewer_display_runtime_state_impl, helpers._apply_viewer_display_runtime_state)
        self.assertIs(studio._apply_profile_runtime_state_impl, helpers._apply_profile_runtime_state)

        x4 = studio.DEVICE_PROFILES['x4']

        class WindowLike:
            def _resolved_profile_and_dimensions(self, *args):
                return ('x4', x4, int(x4.width_px), int(x4.height_px))

        window = WindowLike()
        # named profile resolves directly without custom synthesis
        self.assertIs(studio.MainWindow._current_viewer_profile(window), x4)

    def test_gui_studio_keeps_viewer_profile_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_viewer_profile_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_viewer_profile_helpers import', source)
        self.assertIn('return _current_viewer_profile_impl(', source)
        self.assertIn('return _viewer_profile_for_dimensions_impl(', source)
        self.assertIn('_apply_viewer_display_runtime_state_impl(self)', source)
        self.assertIn('_apply_profile_runtime_state_impl(self)', source)
        self.assertIn('def _current_viewer_profile(', helper_source)
        self.assertIn('def _active_device_viewer_profile(', helper_source)
        self.assertIn('def _custom_viewer_profile_for_dimensions(', helper_source)
        self.assertIn('def _apply_viewer_display_runtime_state(', helper_source)
        self.assertIn('def _apply_profile_runtime_state(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_xtc_load_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_xtc_load_helpers')
        self.assertIs(studio._xtc_display_name_impl, helpers._xtc_display_name)
        self.assertIs(studio._xtc_source_payload_impl, helpers._xtc_source_payload)
        self.assertIs(studio._xtc_load_failure_status_message_impl, helpers._xtc_load_failure_status_message)
        self.assertIs(studio._apply_xtc_document_payload_impl, helpers._apply_xtc_document_payload)
        self.assertIs(studio._set_current_page_index_impl, helpers._set_current_page_index)
        self.assertIs(studio.render_current_page_impl, helpers.render_current_page)
        self.assertIs(studio.clear_loaded_xtc_state_impl, helpers.clear_loaded_xtc_state)
        self.assertIs(studio.leave_file_viewer_mode_for_target_change_impl, helpers.leave_file_viewer_mode_for_target_change)
        self.assertIs(studio._apply_loaded_xtc_view_mode_impl, helpers._apply_loaded_xtc_view_mode)
        self.assertIs(studio.open_xtc_file_impl, helpers.open_xtc_file)

        class WindowLike:
            def _xtc_display_name(self, path):
                return studio.MainWindow._xtc_display_name(self, path)

        window = WindowLike()
        payload = studio.MainWindow._xtc_source_payload(window, '  exports/book.xtc  ')
        self.assertEqual(payload['path_text'], 'exports/book.xtc')
        self.assertIn('display_name', payload)

    def test_gui_studio_keeps_xtc_load_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_xtc_load_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_xtc_load_helpers import', source)
        self.assertIn('return _xtc_source_document_payload_impl(', source)
        self.assertIn('return _xtc_load_failure_status_message_impl(', source)
        self.assertIn('return _current_xtc_page_blob_impl(', source)
        self.assertIn('return load_xtc_from_path_impl(', source)
        self.assertIn('render_current_page_impl(', source)
        self.assertIn('clear_loaded_xtc_state_impl(self)', source)
        self.assertIn('leave_file_viewer_mode_for_target_change_impl(self)', source)
        self.assertIn('return _apply_loaded_xtc_view_mode_impl(', source)
        self.assertIn('return open_xtc_file_impl(', source)
        self.assertIn('def _xtc_source_document_payload(', helper_source)
        self.assertIn('def _xtc_load_failure_status_message(', helper_source)
        self.assertIn('def _apply_loaded_xtc_path_success(', helper_source)
        self.assertIn('def _apply_xtc_document_payload(', helper_source)
        self.assertIn('def render_current_page(', helper_source)
        self.assertIn('def clear_loaded_xtc_state(', helper_source)
        self.assertIn('def leave_file_viewer_mode_for_target_change(', helper_source)
        self.assertIn('def _apply_loaded_xtc_view_mode(', helper_source)
        self.assertIn('def open_xtc_file(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_preview_cache_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_preview_cache_helpers')
        self.assertIs(studio._store_xtc_page_qimage_impl, helpers._store_xtc_page_qimage)
        self.assertIs(studio._cached_xtc_page_qimage_impl, helpers._cached_xtc_page_qimage)
        self.assertIs(studio._clear_font_preview_page_pixmap_cache_impl, helpers._clear_font_preview_page_pixmap_cache)

        class WindowLike:
            pass

        window = WindowLike()
        # store then read back, and confirm the wrapper applies the entry-module cache limit
        for idx in range(studio._XTC_PAGE_QIMAGE_CACHE_LIMIT + 3):
            studio.MainWindow._store_xtc_page_qimage(window, (idx, 0, 0), f'img{idx}')
        cache = window.__dict__['_xtc_page_qimage_cache']
        self.assertEqual(len(cache), studio._XTC_PAGE_QIMAGE_CACHE_LIMIT)
        last_key = (studio._XTC_PAGE_QIMAGE_CACHE_LIMIT + 2, 0, 0)
        self.assertEqual(studio.MainWindow._cached_xtc_page_qimage(window, last_key), f'img{studio._XTC_PAGE_QIMAGE_CACHE_LIMIT + 2}')
        self.assertIsNone(studio.MainWindow._cached_xtc_page_qimage(window, (0, 0, 0)))

    def test_gui_studio_keeps_preview_cache_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preview_cache_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preview_cache_helpers import', source)
        self.assertIn('return _xtc_page_qimage_cache_key_impl(', source)
        self.assertIn('_store_xtc_page_qimage_impl(self, key, image, cache_limit=_XTC_PAGE_QIMAGE_CACHE_LIMIT)', source)
        self.assertIn('def _xtc_page_qimage_cache_key(', helper_source)
        self.assertIn('def _store_xtc_page_qimage(', helper_source)
        self.assertIn('def _rebuild_preview_page_cache_tokens(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_preset_payload_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        helpers = importlib.import_module('tategakiXTC_gui_studio_preset_payload_helpers')
        self.assertIs(studio._normalize_preset_payload_impl, helpers._normalize_preset_payload)
        self.assertIs(studio._load_preset_definitions_impl, helpers._load_preset_definitions)
        self.assertIs(studio._live_preset_widget_payload_impl, helpers._live_preset_widget_payload)
        self.assertIs(studio._current_settings_summary_payload_impl, helpers._current_settings_summary_payload)

        class WindowLike:
            def _default_font_name(self):
                return 'Noto'

            def _normalize_font_setting_value(self, value, fallback):
                return value or fallback

            def _normalize_choice_value(self, value, default, allowed):
                return value if value in allowed else default

            def _resolved_profile_and_dimensions(self, profile, width=None, height=None):
                return (profile, {}, int(width or 480), int(height or 800))

        window = WindowLike()
        normalized = studio.MainWindow._normalize_preset_payload(window, {'font_size': 30})
        self.assertEqual(normalized['font_size'], 30)
        self.assertEqual(normalized['width'], 480)
        self.assertEqual(normalized['height'], 800)
        self.assertIn('kinsoku_mode', normalized)

    def test_gui_studio_keeps_preset_payload_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_preset_payload_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_preset_payload_helpers import', source)
        self.assertIn('return _normalize_preset_payload_impl(', source)
        self.assertIn('return _load_preset_definitions_impl(', source)
        self.assertIn('def _normalize_preset_payload(', helper_source)
        self.assertIn('def _load_preset_definitions(', helper_source)
        self.assertIn('def _live_preset_widget_payload(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_results_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_results_helpers = importlib.import_module('tategakiXTC_gui_studio_results_helpers')
        self.assertIs(studio._clear_results_view_impl, studio_results_helpers._clear_results_view)
        self.assertIs(studio._result_item_count_impl, studio_results_helpers._result_item_count)
        self.assertIs(
            studio._apply_results_selection_context_with_fallback_impl,
            studio_results_helpers._apply_results_selection_context_with_fallback,
        )

        class ResultsList:
            def __init__(self, item_count):
                self._item_count = item_count

            def count(self):
                return self._item_count

        class WindowLike:
            def _result_item_count(self):
                return studio.MainWindow._result_item_count(self)

        window = WindowLike()
        self.assertEqual(studio.MainWindow._result_item_count(window), 0)
        window.results_list = ResultsList(3)
        self.assertEqual(studio.MainWindow._result_item_count(window), 3)

    def test_gui_studio_keeps_results_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_results_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_results_helpers import', source)
        self.assertIn('return _clear_results_view_impl(', source)
        self.assertIn('return _set_results_current_index_with_fallback_impl(', source)
        self.assertIn('def _clear_results_view(', helper_source)
        self.assertIn('def _set_results_current_index_with_fallback(', helper_source)
        self.assertIn('def _sync_results_selection_for_loaded_path_with_fallback(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_status_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_status_helpers = importlib.import_module('tategakiXTC_gui_studio_status_helpers')
        self.assertIs(studio._status_bar_message_text_impl, studio_status_helpers._status_bar_message_text)
        self.assertIs(studio._visible_render_failure_status_text_impl, studio_status_helpers._visible_render_failure_status_text)
        self.assertIs(
            studio._show_ui_status_message_with_reflection_or_direct_fallback_impl,
            studio_status_helpers._show_ui_status_message_with_reflection_or_direct_fallback,
        )

        class StatusBar:
            def __init__(self):
                self.messages = []

            def showMessage(self, text, timeout=None):
                self.messages.append((text, timeout))

            def currentMessage(self):
                return self.messages[-1][0] if self.messages else ''

        class WindowLike:
            def __init__(self):
                self._status_bar = StatusBar()

            def statusBar(self):
                return self._status_bar

            def _ui_text(self, text):
                return text

            def _status_bar_message_text(self):
                return studio.MainWindow._status_bar_message_text(self)

        window = WindowLike()
        self.assertTrue(studio.MainWindow._show_ui_status_message_direct_with_reflection(window, '準備完了', None))
        self.assertEqual(window._status_bar.messages, [('準備完了', None)])
        self.assertEqual(studio.MainWindow._status_bar_message_text(window), '準備完了')

    def test_gui_studio_keeps_status_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_status_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_status_helpers import', source)
        self.assertIn('return _status_bar_message_text_impl(', source)
        self.assertIn('return _visible_render_failure_status_text_impl(', source)
        self.assertIn('def _status_bar_message_text(', helper_source)
        self.assertIn('def _visible_render_failure_status_text(', helper_source)
        self.assertIn('def _show_ui_status_message_direct_with_reflection(', helper_source)
        self.assertNotIn('from PySide6', helper_source)


    def test_gui_studio_conversion_finish_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        finish_helpers = importlib.import_module('tategakiXTC_gui_studio_conversion_finish_helpers')

        self.assertIs(studio._handle_conversion_finished_impl, finish_helpers.handle_conversion_finished)
        self.assertIs(
            studio._build_conversion_completion_summary_lines_impl,
            finish_helpers.build_conversion_completion_summary_lines,
        )
        self.assertIs(
            studio._apply_conversion_completion_guidance_to_results_view_impl,
            finish_helpers.apply_conversion_completion_guidance_to_results_view,
        )

        summary_source = inspect.getsource(studio.MainWindow._build_conversion_completion_summary_lines)
        guidance_source = inspect.getsource(studio.MainWindow._apply_conversion_completion_guidance_to_results_view)
        helper_source = Path('tategakiXTC_gui_studio_conversion_finish_helpers.py').read_text(encoding='utf-8')
        self.assertIn('return _build_conversion_completion_summary_lines_impl(', summary_source)
        self.assertIn('return _apply_conversion_completion_guidance_to_results_view_impl(', guidance_source)
        self.assertIn('def build_conversion_completion_summary_lines(', helper_source)
        self.assertIn('def apply_conversion_completion_guidance_to_results_view(', helper_source)


    def test_gui_studio_conversion_runtime_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        runtime_helpers = importlib.import_module('tategakiXTC_gui_studio_conversion_runtime_helpers')

        self.assertIs(studio._start_conversion_impl, runtime_helpers.start_conversion)
        self.assertIs(studio._schedule_cleanup_worker_impl, runtime_helpers.schedule_cleanup_worker)
        self.assertIs(studio._cleanup_worker_impl, runtime_helpers.cleanup_worker)
        self.assertIs(studio._handle_conversion_error_impl, runtime_helpers.handle_conversion_error)
        self.assertIs(studio._stop_conversion_impl, runtime_helpers.stop_conversion)
        self.assertIs(studio._next_conversion_run_token_impl, runtime_helpers.next_conversion_run_token)
        self.assertIs(studio._connect_worker_dispatch_signals_impl, runtime_helpers.connect_worker_dispatch_signals)
        self.assertIs(studio._emit_worker_finished_request_impl, runtime_helpers.emit_worker_finished_request)
        self.assertIs(studio._dispatch_conversion_finished_impl, runtime_helpers.dispatch_conversion_finished)
        self.assertIs(studio._dispatch_worker_log_impl, runtime_helpers.dispatch_worker_log)
        self.assertIs(studio._update_conversion_progress_impl, runtime_helpers.update_conversion_progress)

        token_source = inspect.getsource(studio.MainWindow._next_conversion_run_token)
        connect_source = inspect.getsource(studio.MainWindow._connect_worker_dispatch_signals)
        emit_source = inspect.getsource(studio.MainWindow._emit_worker_finished_request)
        dispatch_source = inspect.getsource(studio.MainWindow._dispatch_conversion_finished)
        error_source = inspect.getsource(studio.MainWindow.on_conversion_error)
        start_source = inspect.getsource(studio.MainWindow.start_conversion)
        schedule_source = inspect.getsource(studio.MainWindow._schedule_cleanup_worker)
        cleanup_source = inspect.getsource(studio.MainWindow.cleanup_worker)
        self.assertIn('return _next_conversion_run_token_impl(', token_source)
        self.assertIn('return _connect_worker_dispatch_signals_impl(', connect_source)
        self.assertIn('connect_signal_best_effort_func=_connect_signal_best_effort', connect_source)
        self.assertIn('return _emit_worker_finished_request_impl(', emit_source)
        self.assertIn('return _dispatch_conversion_finished_impl(', dispatch_source)
        self.assertIn('return _handle_conversion_error_impl(', error_source)
        self.assertIn('return _start_conversion_impl(', start_source)
        self.assertIn('qthread_cls=QThread', start_source)
        self.assertIn('conversion_worker_cls=ConversionWorker', start_source)
        self.assertIn('return _schedule_cleanup_worker_impl(', schedule_source)
        self.assertIn('qtimer_cls=QTimer', schedule_source)
        self.assertIn('return _cleanup_worker_impl(', cleanup_source)

    def test_gui_studio_keeps_conversion_runtime_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_conversion_runtime_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_conversion_runtime_helpers import', source)
        self.assertIn('return _start_conversion_impl(', source)
        self.assertIn('return _cleanup_worker_impl(', source)
        self.assertIn('def next_conversion_run_token(', helper_source)
        self.assertIn('def connect_worker_dispatch_signals(', helper_source)
        self.assertIn('def emit_worker_finished_request(', helper_source)
        self.assertIn('def dispatch_conversion_finished(', helper_source)
        self.assertIn('def dispatch_worker_log(', helper_source)
        self.assertIn('def start_conversion(', helper_source)
        self.assertIn('def schedule_cleanup_worker(', helper_source)
        self.assertIn('def cleanup_worker(', helper_source)
        self.assertIn('def handle_conversion_error(', helper_source)
        self.assertIn('def update_conversion_progress(', helper_source)
        self.assertNotIn('worker_thread.started.connect(worker.run)', source)
        self.assertNotIn('worker.finished.connect(worker_thread.quit)', source)
        self.assertNotIn("APP_LOGGER.exception('worker完了シグナルのUI反映に失敗しました')", source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_log_helper_wrappers_delegate_to_split_module(self):
        studio = load_studio_module(force_reload=True)
        studio_log_helpers = importlib.import_module('tategakiXTC_gui_studio_log_helpers')
        self.assertIs(studio.append_log_impl, studio_log_helpers.append_log)
        self.assertIs(studio.open_log_folder_impl, studio_log_helpers.open_log_folder)
        self.assertIs(studio._append_log_without_status_impl, studio_log_helpers._append_log_without_status)
        self.assertIs(studio._emit_postprocess_warning_impl, studio_log_helpers._emit_postprocess_warning)
        self.assertIs(
            studio._emit_unique_postprocess_warnings_or_append_to_log_impl,
            studio_log_helpers._emit_unique_postprocess_warnings_or_append_to_log,
        )

        class WindowLike:
            def __init__(self):
                self.lines = []

            def append_log(self, message, reflect_in_status=False):
                self.lines.append(message)

        window = WindowLike()
        self.assertTrue(studio.MainWindow._append_log_without_status(window, '行1'))
        self.assertEqual(window.lines, ['行1'])

    def test_gui_studio_keeps_log_helper_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper_source = Path('tategakiXTC_gui_studio_log_helpers.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_log_helpers import', source)
        self.assertIn('return append_log_impl(', source)
        self.assertIn('return open_log_folder_impl(', source)
        self.assertIn('return _append_log_without_status_impl(', source)
        self.assertIn('return _emit_postprocess_warning_impl(', source)
        self.assertIn('def append_log(', helper_source)
        self.assertIn('def open_log_folder(', helper_source)
        self.assertIn('def _append_log_without_status(', helper_source)
        self.assertNotIn('APP_LOGGER.info(message_text)', source)
        self.assertIn('def _emit_postprocess_warning(', helper_source)
        self.assertIn('def _emit_unique_postprocess_warnings_or_append_to_log(', helper_source)
        self.assertNotIn('from PySide6', helper_source)

    def test_gui_studio_keeps_runtime_page_normalizers_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        runtime_source = Path('tategakiXTC_gui_studio_runtime.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_runtime import', source)
        self.assertNotIn('def _iter_runtime_xtc_page_items(', source)
        self.assertNotIn('def _normalize_runtime_xtc_pages(', source)
        self.assertIn('def _iter_runtime_xtc_page_items(', runtime_source)
        self.assertIn('def _normalize_runtime_xtc_pages(', runtime_source)

    def test_gui_studio_keeps_worker_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        worker_source = Path('tategakiXTC_gui_studio_worker.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_worker import', source)
        self.assertNotIn('class ConversionWorker(', source)
        self.assertNotIn('def build_conversion_args(', source)
        self.assertNotIn('def plan_output_path_for_target(', source)
        self.assertNotIn('def build_conversion_summary(', source)
        self.assertIn('class ConversionWorker(', worker_source)
        self.assertIn('def build_conversion_args(', worker_source)
        self.assertIn('def plan_output_path_for_target(', worker_source)
        self.assertIn('def build_conversion_summary(', worker_source)

    def test_gui_studio_keeps_xtc_io_implementation_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        xtc_io_source = Path('tategakiXTC_gui_studio_xtc_io.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_xtc_io import', source)
        self.assertNotIn('def parse_xtc_pages(', source)
        self.assertNotIn('def xtg_blob_to_qimage(', source)
        self.assertIn('def parse_xtc_pages(', xtc_io_source)
        self.assertIn('def xt_page_blob_to_qimage(', xtc_io_source)

    def test_gui_studio_keeps_widget_implementations_out_of_entry_module(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        widgets_source = Path('tategakiXTC_gui_studio_widgets.py').read_text(encoding='utf-8')
        self.assertIn('from tategakiXTC_gui_studio_widgets import', source)
        self.assertNotIn('class XtcViewerWidget(', source)
        self.assertNotIn('class VisibleArrowSpinBox(', source)
        self.assertNotIn('class FontPopupTopComboBox(', source)
        self.assertNotIn('def _scroll_combo_popup_to_top_now(', source)
        self.assertIn('class XtcViewerWidget(', widgets_source)
        self.assertIn('class VisibleArrowSpinBox(', widgets_source)
        self.assertIn('class FontPopupTopComboBox(', widgets_source)
        self.assertIn('def _scroll_combo_popup_to_top_now(', widgets_source)

    def test_core_public_wrappers_keep_docstrings_and_delegate_to_split_aliases(self):
        specs = (
            ('process_text_file', '_text_process_text_file', 'tategakiXTC_gui_core_text.py'),
            ('process_markdown_file', '_text_process_markdown_file', 'tategakiXTC_gui_core_text.py'),
            ('process_archive', '_archive_process_archive', 'tategakiXTC_gui_core_archive.py'),
        )
        for public_name, delegate_name, implementation_file in specs:
            with self.subTest(public_name=public_name):
                wrapper = getattr(core, public_name)
                source = inspect.getsource(wrapper)
                doc = inspect.getdoc(wrapper) or ''

                self.assertIn('Args:', doc)
                self.assertIn('Returns:', doc)
                self.assertIn(implementation_file, doc)
                self.assertIn(f'return {delegate_name}(', source)

    def test_split_public_implementations_are_not_shadowed_by_core_wrappers(self):
        self.assertIsNot(core.process_text_file, core_text.process_text_file)
        self.assertIsNot(core.process_markdown_file, core_text.process_markdown_file)
        self.assertIsNot(core.process_archive, core_archive.process_archive)
        self.assertIs(core._text_process_text_file, core_text.process_text_file)
        self.assertIs(core._text_process_markdown_file, core_text.process_markdown_file)
        self.assertIs(core._archive_process_archive, core_archive.process_archive)


    def test_renderer_refresh_imports_epub_helpers_added_after_circular_import(self):
        original = getattr(core_renderer, 'load_epub_input_document', None)
        had_original = hasattr(core_renderer, 'load_epub_input_document')
        try:
            if had_original:
                delattr(core_renderer, 'load_epub_input_document')
            core_renderer._refresh_core_globals()
            self.assertIs(core_renderer.load_epub_input_document, core.load_epub_input_document)
        finally:
            if had_original:
                core_renderer.load_epub_input_document = original
            else:
                try:
                    delattr(core_renderer, 'load_epub_input_document')
                except AttributeError:
                    pass
            core_renderer._refresh_core_globals(force=True)

    def test_refresh_core_globals_excludes_relocated_public_entry_points(self):
        self.assertIn('process_text_file', core_text._CORE_SYNC_EXCLUDED_NAMES)
        self.assertIn('process_markdown_file', core_text._CORE_SYNC_EXCLUDED_NAMES)
        self.assertIn('process_archive', core_archive._CORE_SYNC_EXCLUDED_NAMES)

    def test_refresh_core_globals_tracks_core_assignment_versions(self):
        before = core_sync.core_sync_version(core)
        sentinel = object()
        try:
            core._split_module_sync_test_sentinel = sentinel
            after_set = core_sync.core_sync_version(core)
            self.assertGreater(after_set, before)
        finally:
            try:
                delattr(core, '_split_module_sync_test_sentinel')
            except AttributeError:
                pass
        self.assertGreater(core_sync.core_sync_version(core), before)

    def test_refresh_core_globals_short_circuits_when_core_is_unchanged(self):
        core_text._refresh_core_globals(force=True)

        def fail_if_full_scan(_module):
            raise AssertionError('refresh should skip vars(_core) when version is unchanged')

        original_vars = getattr(core_text, 'vars', None)
        had_vars = hasattr(core_text, 'vars')
        try:
            core_text.vars = fail_if_full_scan
            core_text._refresh_core_globals()
        finally:
            if had_vars:
                core_text.vars = original_vars
            else:
                try:
                    delattr(core_text, 'vars')
                except AttributeError:
                    pass

    def test_refresh_core_globals_still_imports_core_monkey_patches(self):
        original_core_render = core._render_text_blocks_to_xtc
        missing = object()
        original_text_render = getattr(core_text, '_render_text_blocks_to_xtc', missing)
        original_text_process = core_text.process_text_file
        original_core_process_image = core.process_image_data
        original_archive_process_image = core_archive.process_image_data
        original_archive_process = core_archive.process_archive
        render_sentinel = object()
        image_sentinel = object()

        try:
            core._render_text_blocks_to_xtc = render_sentinel
            core_text._refresh_core_globals()
            self.assertIs(core_text._render_text_blocks_to_xtc, render_sentinel)
            self.assertIs(core_text.process_text_file, original_text_process)

            core.process_image_data = image_sentinel
            core_archive._refresh_core_globals()
            self.assertIs(core_archive.process_image_data, image_sentinel)
            self.assertIs(core_archive.process_archive, original_archive_process)
        finally:
            core._render_text_blocks_to_xtc = original_core_render
            if original_text_render is missing:
                try:
                    delattr(core_text, '_render_text_blocks_to_xtc')
                except AttributeError:
                    pass
            else:
                core_text._render_text_blocks_to_xtc = original_text_render
            core_text._refresh_core_globals()
            core.process_image_data = original_core_process_image
            core_archive.process_image_data = original_archive_process_image
            core_archive._refresh_core_globals()


if __name__ == '__main__':
    unittest.main()
