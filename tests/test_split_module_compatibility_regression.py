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
        self.assertIs(studio._safe_delete_qobject_later, studio_ui_helpers._safe_delete_qobject_later)


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
        self.assertEqual(studio.MainWindow._normalized_main_view_mode(window, 'device'), 'device')
        self.assertEqual(studio.MainWindow._normalized_main_view_mode(window, 'bad'), 'font')
        self.assertIn('フォントビュー', studio.MainWindow._preview_view_help_text(window))
        self.assertEqual(studio.MainWindow._main_view_mode_status_text(window, 'font'), 'フォントビューに切り替えました。')
        self.assertEqual(studio.MainWindow._main_view_mode_status_text(window, 'device'), '実機ビューに切り替えました。')


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
        self.assertNotIn('def _coerce_preview_data_url(', source)
        self.assertNotIn('def _coerce_preview_base64_text(', source)
        self.assertIn('def _coerce_preview_data_url(', helper_source)
        self.assertIn('def _coerce_preview_base64_text(', helper_source)

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
