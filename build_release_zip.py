from __future__ import annotations

import argparse
import ast
import os
import re
import stat
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Iterable, Iterator

from tategakiXTC_release_metadata import RELEASE_NOTES_FILE, RELEASE_ZIP_FILE_NAME

DEFAULT_EXCLUDED_DIR_NAMES = {
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    '.git',
    '__MACOSX',
    '.venv',
    'venv',
    '.tox',
    '.nox',
    'node_modules',
    '.idea',
    '.vscode',
    'logs',
    'htmlcov',
    'dist',
    'release_build',
}

DEFAULT_EXCLUDED_FILE_NAMES = {
    '.coverage',
    'coverage.xml',
    'coverage-report.txt',
    '.DS_Store',
    'Thumbs.db',
    'desktop.ini',
    'tategakiXTC_gui_studio.ini',
    'dummy.xtc',
    'dummy_preview.epub',
    'pytest.out',
    'test.out',
    'fullpytest.log',
    'part.log',
}

DEFAULT_EXCLUDED_PREFIXES = (
    'pytest',
    'test',
)

DEFAULT_EXCLUDED_SUFFIXES = {
    '.pyc',
    '.pyo',
    '.rootcopy',
    '.log',
    '.out',
    '.err',
    '.trace',
    '.prof',
    '.pid',
    '.lock',
    '.tmp',
    '.partial',
    '.overwritebak',
    '.bak',
    '.orig',
    '.rej',
    '.zip',
    '.7z',
    '.tar',
    '.tgz',
    '.gz',
    '.bz2',
    '.xz',
    '.whl',
}

DEFAULT_EXCLUDED_GLOBS = (
    'regression_audit_bugfix*.md',
    'work_instructions_from_changelog_*.md',
    'code_split_preparation_roadmap_bugfix*.md',
    'split_refactor_progress_bugfix*.md',
    'CONTINUATION_PROGRESS*.md',
    '*handoff*.md',
    '*Handoff*.md',
    '*HANDOFF*.md',
    'handoff*.md',
    '引継ぎ*.md',
    '引き継ぎ書*.md',
    '引き継ぎ追記*.md',
    'work_clean*_md.md',
    'test_full_log*.txt',
    'test_fail_index*.txt',
    'test_failure_index*.txt',
    'test_errors*.txt',
    'test_failures*.txt',
    'bundle_*.txt',
    '.coverage.*',
    'pt_*.log',
    'pt_*.exit',
    'pt*.log',
    'pt*.exit',
)

BUNDLED_FONT_DIR_NAMES = ('Font', 'fonts')
BUNDLED_FONT_SUFFIXES = {'.ttf', '.ttc', '.otf', '.otc'}
REQUIRED_BUNDLED_FONT_LICENSE = 'LICENSE_OFL.txt'
PROJECT_APP_MARKER_FILES = (
    'tategakiXTC_gui_studio.py',
)
REQUIRED_PROJECT_APP_ENTRY_FILES = PROJECT_APP_MARKER_FILES
REQUIRED_PUBLIC_DOC_FILES = (
    'README.md',
    'LICENSE.txt',
    'CHANGELOG.md',
    'RELEASE_CHECKLIST.md',
    RELEASE_NOTES_FILE,
)
REQUIRED_PROJECT_APP_MODULE_FILES = (
    'tategakiXTC_release_metadata.py',
    'tategakiXTC_gui_core.py',
    'tategakiXTC_numpy_helper.py',
    'tategakiXTC_gui_core_sync.py',
    'tategakiXTC_gui_core_deps.py',
    'tategakiXTC_gui_core_fonts.py',
    'tategakiXTC_gui_core_paths.py',
    'tategakiXTC_gui_core_cache.py',
    'tategakiXTC_gui_core_archive.py',
    'tategakiXTC_gui_core_text.py',
    'tategakiXTC_gui_core_pages.py',
    'tategakiXTC_gui_core_renderer.py',
    'tategakiXTC_gui_core_epub.py',
    'tategakiXTC_gui_core_xtc.py',
    'tategakiXTC_gui_layouts.py',
    'tategakiXTC_gui_preview_controller.py',
    'tategakiXTC_gui_results_controller.py',
    'tategakiXTC_gui_settings_controller.py',
    'tategakiXTC_gui_studio_logic.py',
    'tategakiXTC_gui_studio_logging.py',
    'tategakiXTC_gui_studio_startup.py',
    'tategakiXTC_gui_studio_constants.py',
    'tategakiXTC_gui_studio_xtc_io.py',
    'tategakiXTC_gui_studio_widgets.py',
    'tategakiXTC_gui_studio_worker.py',
    'tategakiXTC_gui_studio_runtime.py',
    'tategakiXTC_gui_studio_desktop.py',
    'tategakiXTC_gui_studio_ui_helpers.py',
    'tategakiXTC_gui_studio_dialog_helpers.py',
    'tategakiXTC_gui_studio_preview_helpers.py',
    'tategakiXTC_gui_studio_path_helpers.py',
    'tategakiXTC_gui_studio_view_helpers.py',
    'tategakiXTC_gui_studio_settings_helpers.py',
    'tategakiXTC_gui_widget_factory.py',
    'tategakiXTC_worker_logic.py',
)
REQUIRED_PROJECT_APP_CODE_FILES = (
    *REQUIRED_PROJECT_APP_ENTRY_FILES,
    *REQUIRED_PROJECT_APP_MODULE_FILES,
)
REQUIRED_PROJECT_DOCUMENT_FILES = REQUIRED_PUBLIC_DOC_FILES
REQUIRED_PROJECT_REQUIREMENTS_FILES = (
    'requirements.txt',
)
PROHIBITED_WEB_RELEASE_FILES = (
    'README_localweb_quickstart.txt',
    'build_localweb_windows_dist.bat',
    'install_local_web_requirements.bat',
    'localweb_launcher.py',
    'pyinstaller_localweb.spec',
    'requirements-web.txt',
    'run_local_web.bat',
    'tategakiXTC_localweb.py',
    'tategakiXTC_localweb_service.py',
    'templates/localweb_index.html',
    'tests/test_localweb_service.py',
    'tests/test_localweb_smoke.py',
    'tests/test_localweb_template_regression.py',
)

PROHIBITED_WEB_RELEASE_FILE_KEYS = {
    unicodedata.normalize('NFC', name).casefold()
    for name in PROHIBITED_WEB_RELEASE_FILES
}


def _is_prohibited_web_release_path(path_name: str) -> bool:
    normalized = unicodedata.normalize('NFC', path_name.replace('\\', '/').strip('/')).casefold()
    return normalized in PROHIBITED_WEB_RELEASE_FILE_KEYS

REQUIRED_PROJECT_SUPPORT_FILES = (
    'requirements.txt',
    'run_gui.bat',
    'install_requirements.bat',
    'run_tests.bat',
)
REQUIRED_PROJECT_TOOLING_FILES = (
    'build_release_zip.py',
    'mypy.ini',
    '.coveragerc',
    '.github/workflows/python-tests.yml',
)
REQUIRED_PROJECT_GUI_ASSET_FILES = (
    'ui_assets/spin_up.svg',
    'ui_assets/spin_down.svg',
    'ui_assets/spin_up_dark.svg',
    'ui_assets/spin_down_dark.svg',
)
REQUIRED_PROJECT_TEST_SUPPORT_FILES = (
    'tests/__init__.py',
    'tests/font_test_helper.py',
    'tests/generate_golden_images.py',
    'tests/golden_regression_tools.py',
    'tests/golden_case_registry.py',
    'tests/image_golden_cases.py',
    'tests/sample_fixture_builders.py',
    'tests/studio_import_helper.py',
    'tests/fixtures/README.md',
    'tests/golden_images/README.md',
)
REQUIRED_PROJECT_TEST_FIXTURE_FILES = (
    'tests/fixtures/sample_aozora.txt',
    'tests/fixtures/sample_notes.md',
    'tests/fixtures/epub/chapter1.xhtml',
    'tests/fixtures/epub/styles/main.css',
)
REQUIRED_PROJECT_TEST_FIXTURE_IMAGE_FILES = (
    'tests/fixtures/epub/images/scene.png',
)
REQUIRED_PROJECT_GOLDEN_IMAGE_FILES = (
    'tests/golden_images/glyph_ichi.png',
    'tests/golden_images/glyph_small_kana_ya.png',
    'tests/golden_images/glyph_chouon.png',
    'tests/golden_images/tatechuyoko_2025.png',
    'tests/golden_images/page_compound_layout.png',
    'tests/golden_images/page_heading_spacing.png',
    'tests/golden_images/page_closing_bracket_period.png',
    'tests/golden_images/page_consecutive_punctuation.png',
    'tests/golden_images/page_x4_profile_layout.png',
    'tests/golden_images/page_x3_profile_layout.png',
    'tests/golden_images/ruby_across_columns_layout.png',
    'tests/golden_images/ruby_across_pages_layout.png',
    'tests/golden_images/page_night_mode_layout.png',
    'tests/golden_images/page_xtch_filter_layout.png',
    'tests/golden_images/page_ruby_size_small_layout.png',
    'tests/golden_images/page_ruby_size_large_layout.png',
)
REQUIRED_PROJECT_PNG_IMAGE_FILES = (
    *REQUIRED_PROJECT_TEST_FIXTURE_IMAGE_FILES,
    *REQUIRED_PROJECT_GOLDEN_IMAGE_FILES,
)
REQUIRED_PROJECT_TEST_DATA_FILES = (
    *REQUIRED_PROJECT_TEST_FIXTURE_FILES,
    *REQUIRED_PROJECT_TEST_FIXTURE_IMAGE_FILES,
    *REQUIRED_PROJECT_GOLDEN_IMAGE_FILES,
)
REQUIRED_PROJECT_REGRESSION_TEST_FILES = (
    'tests/test_aozora_archive_edge_regression.py',
    'tests/test_aozora_note_parser_regression.py',
    'tests/test_aozora_style_helpers_regression.py',
    'tests/test_api_safety_regression.py',
    'tests/test_archive_error_regression.py',
    'tests/test_archive_regression.py',
    'tests/test_conversion_diagnostics.py',
    'tests/test_conversion_worker_logic.py',
    'tests/test_core_optional_import_regression.py',
    'tests/test_docstrings_regression.py',
    'tests/test_epub_archive_dependency_regression.py',
    'tests/test_epub_chapter_renderer.py',
    'tests/test_epub_code_font_pathless.py',
    'tests/test_epub_code_font_preresolved.py',
    'tests/test_epub_css_pagebreak_skip_regression.py',
    'tests/test_epub_css_regression.py',
    'tests/test_epub_preview_helper_regression.py',
    'tests/test_epub_regression.py',
    'tests/test_epub_structure_progress_regression.py',
    'tests/test_extended_golden_cases.py',
    'tests/test_font_draw_helper_regression.py',
    'tests/test_font_popup_scroll_regression.py',
    'tests/test_golden_profile_registry.py',
    'tests/test_golden_threshold_profiles.py',
    'tests/test_golden_workflow_regression.py',
    'tests/test_gui_image_atomic_write_regression.py',
    'tests/test_gui_layouts_regression.py',
    'tests/test_gui_preview_controller_regression.py',
    'tests/test_gui_results_controller_regression.py',
    'tests/test_gui_settings_controller_regression.py',
    'tests/test_gui_studio_logic_regression.py',
    'tests/test_gui_studio_logging_regression.py',
    'tests/test_gui_studio_smoke_optional.py',
    'tests/test_gui_studio_worker_regression.py',
    'tests/test_gui_widget_factory_regression.py',
    'tests/test_ichi_centering_regression.py',
    'tests/test_image_golden_regression.py',
    'tests/test_input_pipeline_regression.py',
    'tests/test_layout_regression.py',
    'tests/test_margin_preview_regression.py',
    'tests/test_markdown_table_footnote_regression.py',
    'tests/test_misc_conversion_helper_regression.py',
    'tests/test_output_conflict_regression.py',
    'tests/test_pending_indent_regression.py',
    'tests/test_preview_shared_renderer.py',
    'tests/test_real_file_preview.py',
    'tests/test_release_bundle_hygiene.py',
    'tests/test_release_docs_regression.py',
    'tests/test_release_hygiene_regression.py',
    'tests/test_renderer_api_regression.py',
    'tests/test_ruby_renderer_helper_regression.py',
    'tests/test_sample_fixture_regression.py',
    'tests/test_sweep368_layout_contract_regression.py',
    'tests/test_shared_page_entry_pipeline.py',
    'tests/test_spooled_copy_cancel_regression.py',
    'tests/test_split_module_compatibility_regression.py',
    'tests/test_text_code_font_lazy_regression.py',
    'tests/test_text_input_helper_regression.py',
    'tests/test_text_markdown_scope.py',
    'tests/test_type_annotations_regression.py',
    'tests/test_vertical_renderer_unification.py',
    'tests/test_xtc_viewer_finish_regression.py',
    'tests/test_xtc_viewer_hidpi_regression.py',
    'tests/test_xtch_output_and_aozora_draw_regression.py',
)
REQUIRED_REGRESSION_TEST_CONTENT_MARKERS = ('def test_',)
REQUIRED_PROJECT_RELEASE_FILES = (
    *REQUIRED_PUBLIC_DOC_FILES,
    *REQUIRED_PROJECT_APP_ENTRY_FILES,
    *REQUIRED_PROJECT_APP_MODULE_FILES,
    *REQUIRED_PROJECT_SUPPORT_FILES,
    *REQUIRED_PROJECT_TOOLING_FILES,
    *REQUIRED_PROJECT_GUI_ASSET_FILES,
    *REQUIRED_PROJECT_TEST_SUPPORT_FILES,
    *REQUIRED_PROJECT_TEST_DATA_FILES,
    *REQUIRED_PROJECT_REGRESSION_TEST_FILES,
)
REQUIRED_ASCII_BATCH_FILES = tuple(
    name for name in REQUIRED_PROJECT_SUPPORT_FILES
    if name.casefold().endswith('.bat')
)
REQUIRED_UTF8_TEXT_FILES = tuple(
    name for name in REQUIRED_PROJECT_RELEASE_FILES
    if name not in REQUIRED_ASCII_BATCH_FILES
    and name not in REQUIRED_PROJECT_PNG_IMAGE_FILES
)
REQUIRED_APP_CONTENT_MARKERS = {
    'tategakiXTC_release_metadata.py': (
        "APP_VERSION = '1.2.1'",
        'RELEASE_NOTES_FILE',
        'RELEASE_ZIP_FILE_NAME',
    ),
    'tategakiXTC_gui_studio.py': (
        'class MainWindow',
        'QApplication',
        '_configure_app_logging',
    ),
    'tategakiXTC_gui_core.py': (
        'class ConversionArgs',
        'SUPPORTED_INPUT_SUFFIXES',
        'def process_text_file',
    ),
    'tategakiXTC_numpy_helper.py': (
        'def get_cached_numpy_module',
        'import numpy as numpy_module',
        '__all__',
    ),
    'tategakiXTC_gui_studio_logging.py': (
        'def cleanup_old_session_logs',
        'DEFAULT_LOG_RETENTION_DAYS',
        '__all__',
    ),
    'tategakiXTC_gui_studio_startup.py': (
        'def collect_missing_startup_dependencies',
        'def show_startup_dependency_alert',
        '__all__',
    ),
    'tategakiXTC_gui_studio_constants.py': (
        'class DeviceProfile',
        'DEVICE_PROFILES',
        'DEFAULT_PRESET_DEFINITIONS',
    ),
    'tategakiXTC_gui_studio_xtc_io.py': (
        'class XtcPage',
        'def parse_xtc_pages',
        'def xt_page_blob_to_qimage',
    ),
    'tategakiXTC_gui_studio_widgets.py': (
        'class XtcViewerWidget',
        'class VisibleArrowSpinBox',
        'class FontPopupTopComboBox',
    ),
    'tategakiXTC_gui_studio_worker.py': (
        'class ConversionWorker',
        'def build_conversion_args',
        'def plan_output_path_for_target',
        'def build_conversion_summary',
    ),
    'tategakiXTC_gui_studio_desktop.py': (
        'def _open_path_in_file_manager',
        'xdg-open',
        'os.startfile',
    ),
    'tategakiXTC_gui_studio_ui_helpers.py': (
        'def _bulk_block_signals',
        'def _connect_signal_best_effort',
        'def _safe_delete_qobject_later',
    ),
    'tategakiXTC_gui_studio_dialog_helpers.py': (
        'def show_warning_dialog_with_status_fallback',
        'def ask_question_dialog_with_status_fallback',
        'def get_open_file_name_with_status_fallback',
    ),
    'tategakiXTC_gui_studio_preview_helpers.py': (
        'def _coerce_preview_data_url',
        'def _coerce_preview_base64_text',
    ),
    'tategakiXTC_gui_studio_path_helpers.py': (
        'def _supported_targets_for_path',
        'def _default_output_name_for_target',
    ),
    'tategakiXTC_gui_studio_settings_helpers.py': (
        'def _settings_contains_key',
        'def _plan_int_tuple_value',
        'def _combo_find_data_index',
    ),
    'tategakiXTC_gui_studio_view_helpers.py': (
        'def _normalized_main_view_mode',
        'def _preview_view_help_text',
        'def _main_view_mode_status_text',
    ),
    'tategakiXTC_gui_core_sync.py': (
        'def install_core_sync_tracker',
        'def core_sync_version',
        'class _TrackedCoreModule',
    ),
    'tategakiXTC_gui_core_deps.py': (
        'def build_conversion_error_report',
        'def list_optional_dependency_status',
        'def get_missing_dependencies_for_suffixes',
    ),
    'tategakiXTC_gui_core_fonts.py': (
        'def get_font_entries',
        'def load_truetype_font',
        'def clear_font_entry_cache',
    ),
    'tategakiXTC_gui_core_paths.py': (
        'def iter_conversion_targets',
        'def get_output_path_for_target',
        'def resolve_output_path_with_conflict',
    ),
    'tategakiXTC_gui_core_cache.py': (
        'def _source_document_cache_key',
        'def _get_cached_input_document',
        'def _store_cached_input_document',
    ),
    'tategakiXTC_gui_core_archive.py': (
        'def load_archive_input_document',
        'def _extract_zip_archive_images_to_tempdir',
        'def _safe_zip_archive_image_infos',
    ),
    'tategakiXTC_gui_core_text.py': (
        'def load_text_input_document',
        'def process_text_file',
        'def process_markdown_file',
        'def _blocks_from_markdown',
        'def _aozora_inline_to_runs',
    ),
    'tategakiXTC_gui_core_pages.py': (
        'def _make_page_entry',
        'def _write_page_entries_to_xtc',
        'def _render_text_blocks_to_xtc',
    ),
    'tategakiXTC_gui_core_renderer.py': (
        'class _VerticalPageRenderer',
        'def generate_preview_base64',
        'def _render_text_blocks_to_page_entries',
    ),
    'tategakiXTC_gui_core_epub.py': (
        'class EpubInputDocument',
        'def load_epub_input_document',
        'def process_epub',
    ),
    'tategakiXTC_gui_core_xtc.py': (
        'class XTCSpooledPages',
        'def build_xtc',
        'def canvas_image_to_xt_bytes',
    ),
    'tategakiXTC_gui_layouts.py': (
        'build_left_settings_section_layout_plan',
        'build_bottom_panel_layout_plan',
    ),
    'tategakiXTC_gui_preview_controller.py': (
        'build_preview_payload',
        'build_preview_apply_context',
    ),
    'tategakiXTC_gui_results_controller.py': (
        'build_results_view_state',
        'resolve_preferred_results_index',
    ),
    'tategakiXTC_gui_settings_controller.py': (
        'build_settings_restore_payload',
        'build_current_settings_payload',
    ),
    'tategakiXTC_gui_studio_logic.py': (
        'build_settings_restore_payload',
        'build_preview_status_message',
    ),
    'tategakiXTC_gui_widget_factory.py': (
        'make_section',
        'make_help_icon_button',
    ),
    'tategakiXTC_worker_logic.py': (
        'build_conversion_args',
        'plan_output_path_for_target',
        'build_conversion_summary',
    ),
}

REQUIRED_BATCH_CONTENT_MARKERS = {
    'run_gui.bat': (
        'tategakiXTC_gui_studio.py',
        'requirements.txt',
        'install_requirements.bat',
    ),
    'install_requirements.bat': (
        'requirements.txt',
        '-m pip install',
    ),
    'run_tests.bat': (
        'unittest discover',
        'tests\\generate_golden_images.py',
        'build_release_zip.py',
        '--verify',
    ),
}
REQUIRED_REQUIREMENTS_CONTENT_MARKERS = {
    'requirements.txt': (
        'PySide6',
        'Pillow',
    ),
}
REQUIRED_DOCUMENT_CONTENT_MARKERS = {
    'README.md': (
        'run_gui.bat',
        'install_requirements.bat',
        'run_tests.bat',
        'requirements.txt',
        'build_release_zip.py',
        '--verify',
    ),
}

REQUIRED_TOOLING_CONTENT_MARKERS = {
    'build_release_zip.py': (
        'validate_release_tree',
        'verify_release_zip_required_file_contents',
        'verify_release_zip_untracked_golden_case_files',
        'verify_release_zip_required_file_list_issues',
        'verify_release_zip_required_member_spellings',
        '_zip_missing_required_member_names',
        'REQUIRED_PROJECT_RELEASE_FILES',
    ),
    'mypy.ini': (
        'files =',
        'warn_unused_ignores = True',
        'tategakiXTC_gui_core.py',
    ),
    '.coveragerc': (
        'branch = True',
        'source =',
        'tategakiXTC_worker_logic',
    ),
    '.github/workflows/python-tests.yml': (
        'actions/setup-python@v5',
        'build_release_zip.py --verify',
    ),
}

REQUIRED_GUI_ASSET_CONTENT_MARKERS = {
    'ui_assets/spin_up.svg': (
        '<svg',
        '<path',
        'viewBox',
    ),
    'ui_assets/spin_down.svg': (
        '<svg',
        '<path',
        'viewBox',
    ),
    'ui_assets/spin_up_dark.svg': (
        '<svg',
        '<path',
        'viewBox',
    ),
    'ui_assets/spin_down_dark.svg': (
        '<svg',
        '<path',
        'viewBox',
    ),
}

REQUIRED_TEST_SUPPORT_CONTENT_MARKERS = {
    'tests/__init__.py': (
        'Regression test package',
        'from tests',
        'local test helpers',
    ),
    'tests/font_test_helper.py': (
        'resolve_test_font_spec',
        'resolve_test_font_path',
        'has_bundled_reference_font',
    ),
    'tests/generate_golden_images.py': (
        'check_all_cases',
        'update_all_stale_cases',
        '--check',
    ),
    'tests/golden_regression_tools.py': (
        'compare_case',
        'should_update_goldens',
        'ImageChops',
    ),
    'tests/golden_case_registry.py': (
        'CASE_SPECS',
        'THRESHOLD_PROFILES',
        'resolve_case_thresholds',
    ),
    'tests/image_golden_cases.py': (
        'CASE_SPECS',
        'render_case',
        'THRESHOLD_PROFILES',
    ),
    'tests/sample_fixture_builders.py': (
        'build_sample_epub',
        'fixture_path',
        'chapter1.xhtml',
    ),
    'tests/studio_import_helper.py': (
        'load_studio_module',
        '_install_pyside6_stubs',
        'tategakiXTC_gui_studio',
    ),
    'tests/fixtures/README.md': (
        '回帰テスト',
        'sample_aozora.txt',
        'sample_notes.md',
    ),
    'tests/golden_images/README.md': (
        'ゴールデン',
        'generate_golden_images.py',
        '--check',
    ),
}

REQUIRED_TEST_FIXTURE_CONTENT_MARKERS = {
    'tests/fixtures/sample_aozora.txt': (
        '｜吾輩《わがはい》',
        '［＃改ページ］',
        '第二節',
    ),
    'tests/fixtures/sample_notes.md': (
        '# 旅のメモ',
        '- [x] 切符を確認する',
        '[^note]',
    ),
    'tests/fixtures/epub/chapter1.xhtml': (
        '<html xmlns=',
        '<ruby>吾輩<rt>わがはい</rt></ruby>',
        'pagebreak',
        'images/scene.png',
        'styles/main.css',
    ),
    'tests/fixtures/epub/styles/main.css': (
        '.hidden',
        'pagebreak',
        'strongish',
    ),
}

def _required_content_marker_category_specs() -> tuple[
    tuple[str, dict[str, tuple[str, ...]], tuple[str, ...], str],
    ...
]:
    """内容 marker map と、そのキーが属すべき必須ファイルカテゴリを返す。"""
    return (
        (
            'REQUIRED_APP_CONTENT_MARKERS',
            REQUIRED_APP_CONTENT_MARKERS,
            REQUIRED_PROJECT_APP_CODE_FILES,
            'REQUIRED_PROJECT_APP_CODE_FILES',
        ),
        (
            'REQUIRED_BATCH_CONTENT_MARKERS',
            REQUIRED_BATCH_CONTENT_MARKERS,
            REQUIRED_ASCII_BATCH_FILES,
            'REQUIRED_ASCII_BATCH_FILES',
        ),
        (
            'REQUIRED_REQUIREMENTS_CONTENT_MARKERS',
            REQUIRED_REQUIREMENTS_CONTENT_MARKERS,
            REQUIRED_PROJECT_REQUIREMENTS_FILES,
            'REQUIRED_PROJECT_REQUIREMENTS_FILES',
        ),
        (
            'REQUIRED_DOCUMENT_CONTENT_MARKERS',
            REQUIRED_DOCUMENT_CONTENT_MARKERS,
            REQUIRED_PROJECT_DOCUMENT_FILES,
            'REQUIRED_PROJECT_DOCUMENT_FILES',
        ),
        (
            'REQUIRED_TOOLING_CONTENT_MARKERS',
            REQUIRED_TOOLING_CONTENT_MARKERS,
            REQUIRED_PROJECT_TOOLING_FILES,
            'REQUIRED_PROJECT_TOOLING_FILES',
        ),
        (
            'REQUIRED_GUI_ASSET_CONTENT_MARKERS',
            REQUIRED_GUI_ASSET_CONTENT_MARKERS,
            REQUIRED_PROJECT_GUI_ASSET_FILES,
            'REQUIRED_PROJECT_GUI_ASSET_FILES',
        ),
        (
            'REQUIRED_TEST_SUPPORT_CONTENT_MARKERS',
            REQUIRED_TEST_SUPPORT_CONTENT_MARKERS,
            REQUIRED_PROJECT_TEST_SUPPORT_FILES,
            'REQUIRED_PROJECT_TEST_SUPPORT_FILES',
        ),
        (
            'REQUIRED_TEST_FIXTURE_CONTENT_MARKERS',
            REQUIRED_TEST_FIXTURE_CONTENT_MARKERS,
            REQUIRED_PROJECT_TEST_FIXTURE_FILES,
            'REQUIRED_PROJECT_TEST_FIXTURE_FILES',
        ),
    )


def _required_content_marker_maps() -> tuple[dict[str, tuple[str, ...]], ...]:
    """必須ファイルの内容 marker map 一覧を返す。"""
    return tuple(spec[1] for spec in _required_content_marker_category_specs())


PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

WINDOWS_RESERVED_FILE_STEMS = {
    'con',
    'prn',
    'aux',
    'nul',
    *(f'com{number}' for number in range(1, 10)),
    *(f'lpt{number}' for number in range(1, 10)),
}
WINDOWS_UNSAFE_NAME_CHARS = set('<>:\"|?*')
WINDOWS_PORTABLE_ARCHIVE_NAME_LIMIT = 240
WINDOWS_PORTABLE_ARCHIVE_PART_LIMIT = 200


def _casefold_set(values: Iterable[str]) -> set[str]:
    return {value.casefold() for value in values}


def _is_archive_member_unicode_noncharacter(char: str) -> bool:
    """Unicode noncharacter かを返す。"""
    codepoint = ord(char)
    return (
        0xFDD0 <= codepoint <= 0xFDEF
        or (codepoint & 0xFFFE) == 0xFFFE and codepoint <= 0x10FFFF
    )


def _is_archive_member_invisible_control_char(char: str) -> bool:
    """zip member 名として紛らわしい不可視制御文字かを返す。"""
    codepoint = ord(char)
    if codepoint < 32 or codepoint == 127:
        return True
    # Unicode format controls such as bidi override/isolate marks can make an
    # archive member appear with a different visual order in terminals or file
    # managers. They are not produced by this release builder, so reject them in
    # external zips and escape them in diagnostics.
    return unicodedata.category(char) == 'Cf'


def _is_archive_member_disallowed_unicode_char(char: str) -> bool:
    """release zip member 名として拒否する Unicode 文字かを返す。"""
    category = unicodedata.category(char)
    return (
        _is_archive_member_invisible_control_char(char)
        or category in {'Co', 'Cs'}
        or _is_archive_member_unicode_noncharacter(char)
    )


def _is_windows_unsafe_path_part(part: str) -> bool:
    """Windows で安全に展開しづらいパス構成要素かを返す。"""
    if not part or part in {'.', '..'}:
        return True
    if part[-1] in {' ', '.'}:
        return True
    if any(
        _is_archive_member_disallowed_unicode_char(char) or char in WINDOWS_UNSAFE_NAME_CHARS
        for char in part
    ):
        return True
    stem = part.split('.')[0].casefold()
    return stem in WINDOWS_RESERVED_FILE_STEMS



_NUMERIC_SPLIT_RE = re.compile(r'(\d+)')


def natural_sort_key(value: str) -> list[object]:
    """文字列中の数字を数値として扱う自然順キーを返す。"""
    key: list[object] = []
    for chunk in _NUMERIC_SPLIT_RE.split(value):
        if not chunk:
            continue
        if chunk.isdigit():
            key.append(int(chunk))
        else:
            key.append(chunk.casefold())
    return key



def _normalized_relative_path(path: Path, root: Path) -> Path:
    return path.resolve().relative_to(root.resolve())



def _relative_path_should_be_included(
    rel_path: Path,
    *,
    is_dir: bool,
    excluded_dir_names: set[str] | None = None,
    excluded_file_names: set[str] | None = None,
    excluded_suffixes: set[str] | None = None,
    excluded_globs: Iterable[str] | None = None,
    excluded_prefixes: Iterable[str] | None = None,
) -> bool:
    """正規化済みの相対パスが release zip に含まれるべきかを返す。"""
    excluded_dir_names = set(DEFAULT_EXCLUDED_DIR_NAMES if excluded_dir_names is None else excluded_dir_names)
    excluded_file_names = set(DEFAULT_EXCLUDED_FILE_NAMES if excluded_file_names is None else excluded_file_names)
    excluded_suffixes = set(DEFAULT_EXCLUDED_SUFFIXES if excluded_suffixes is None else excluded_suffixes)
    excluded_globs = tuple(DEFAULT_EXCLUDED_GLOBS if excluded_globs is None else excluded_globs)
    excluded_prefixes = tuple(DEFAULT_EXCLUDED_PREFIXES if excluded_prefixes is None else excluded_prefixes)

    text = str(rel_path)
    posix_text = rel_path.as_posix()
    if _is_prohibited_web_release_path(posix_text):
        return False
    if (
        rel_path.is_absolute()
        or text.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:", text)
    ):
        return False
    windows_path = PureWindowsPath(text)
    if windows_path.drive or windows_path.root or windows_path.anchor:
        return False

    parts = rel_path.parts
    if not parts:
        return False
    if any(_is_windows_unsafe_path_part(str(part)) for part in parts):
        return False

    excluded_dir_names_folded = _casefold_set(excluded_dir_names)
    excluded_file_names_folded = _casefold_set(excluded_file_names)

    dir_parts = parts if is_dir else parts[:-1]
    for part in dir_parts:
        if str(part).casefold() in excluded_dir_names_folded:
            return False

    name = rel_path.name
    name_folded = name.casefold()
    if name_folded in excluded_file_names_folded:
        return False
    if name.startswith('._'):
        return False
    if any(name_folded.startswith(prefix.casefold()) and name_folded.endswith(('.out', '.log')) for prefix in excluded_prefixes):
        return False
    if name.endswith('~'):
        return False
    if rel_path.suffix.lower() in excluded_suffixes:
        return False
    for pattern in excluded_globs:
        if rel_path.match(pattern) or Path(name).match(pattern):
            return False
    return True





def _archive_member_name_should_be_included(member_name: str, *, is_dir: bool = False) -> bool:
    """zip 内メンバー名が release へ含まれるべきかを内部判定する。"""
    if is_dir:
        return False
    if '\\' in member_name:
        return False
    normalized = member_name
    if normalized.startswith('/') or re.match(r'^[A-Za-z]:', normalized):
        return False
    normalized = normalized.strip('/')
    if not normalized:
        return False
    if _is_prohibited_web_release_path(normalized):
        return False
    parts = normalized.split('/')
    if any(_is_windows_unsafe_path_part(part) for part in parts):
        return False
    return _relative_path_should_be_included(Path(normalized), is_dir=is_dir)


def archive_member_should_be_included(member_name: str, *, is_dir: bool = False) -> bool:
    """zip 内メンバー名が release へ含まれるべきかを返す。

    Generated release archives contain regular file entries only. Treat
    explicit directory entries, backslashes, and other non-canonical names as
    invalid so that externally supplied zips are not accepted more loosely than
    archives produced by this script.
    """
    return _archive_member_name_should_be_included(member_name, is_dir=is_dir)

def should_include_path(path: Path, root: Path, *,
                        excluded_dir_names: set[str] | None = None,
                        excluded_file_names: set[str] | None = None,
                        excluded_suffixes: set[str] | None = None,
                        excluded_globs: Iterable[str] | None = None) -> bool:
    """release zip に含めるべきパスかを返す。"""
    if path.is_symlink():
        return False
    try:
        rel_path = _normalized_relative_path(path, root)
    except Exception:
        return False
    return _relative_path_should_be_included(
        rel_path,
        is_dir=path.is_dir(),
        excluded_dir_names=excluded_dir_names,
        excluded_file_names=excluded_file_names,
        excluded_suffixes=excluded_suffixes,
        excluded_globs=excluded_globs,
    )



def iter_release_files(root: Path, *, excluded_paths: Iterable[Path] | None = None) -> Iterator[Path]:
    """release zip に含めるファイル一覧を自然順で返す。"""
    root = root.resolve()
    excluded_resolved = {path.resolve() for path in (excluded_paths or ())}
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            dirname for dirname in dirnames
            if should_include_path(Path(dirpath) / dirname, root)
        ]
        for filename in filenames:
            candidate = Path(dirpath) / filename
            try:
                candidate_resolved = candidate.resolve()
            except Exception:
                continue
            if candidate_resolved in excluded_resolved:
                continue
            if candidate.is_symlink():
                continue
            if should_include_path(candidate, root):
                files.append(candidate)
    for path in sorted(files, key=lambda p: natural_sort_key(str(_normalized_relative_path(p, root)).replace('\\', '/'))):
        yield path



def _display_archive_member_name(member_name: str) -> str:
    """診断表示用の zip メンバー名を返す。空名と不可視制御文字を明示する。"""
    if not member_name:
        return '<empty member name>'
    if any(_is_archive_member_disallowed_unicode_char(char) for char in member_name):
        return member_name.encode('unicode_escape').decode('ascii')
    return member_name


def _display_release_zip_diagnostic_text(text: str) -> str:
    """release zip 診断の最終表示で制御文字などを raw のまま出さない。"""
    if not text:
        return '<empty diagnostic text>'
    return ''.join(
        char.encode('unicode_escape').decode('ascii')
        if _is_archive_member_disallowed_unicode_char(char)
        else char
        for char in text
    )

def _display_archive_member_with_normalized_context(
    raw_member_name: str,
    normalized_member_name: str | None = None,
) -> str:
    """raw member 名と正規化後 member 名が異なる場合に両方を表示する。"""
    normalized = (
        _normalized_archive_member_name(raw_member_name)
        if normalized_member_name is None
        else normalized_member_name
    )
    raw_display = _display_archive_member_name(raw_member_name)
    if raw_member_name == normalized:
        return raw_display
    return f'{raw_display} (normalized: {_display_archive_member_name(normalized)})'


def verify_release_zip(zip_path: Path) -> list[str]:
    """既存 release zip を検査し、除外対象メンバー名一覧を返す。"""
    zip_path = zip_path.resolve()
    bad_entries: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            member_name = info.filename
            if not archive_member_should_be_included(member_name, is_dir=info.is_dir()):
                bad_entries.append(_display_archive_member_name(member_name))
    return bad_entries

def verify_release_zip_integrity(zip_path: Path) -> list[str]:
    """既存 release zip の読み取り破損・CRC 不一致を返す。"""
    zip_path = zip_path.resolve()
    try:
        with zipfile.ZipFile(zip_path) as zf:
            corrupt_member = zf.testzip()
    except zipfile.BadZipFile as exc:
        return [f'<bad zip>: {exc}']
    except Exception as exc:
        return [f'<zip read error>: {exc}']
    if corrupt_member:
        return [_display_archive_member_name(corrupt_member)]
    return []


def _zip_info_unix_mode(info: zipfile.ZipInfo) -> int:
    """Unix 系属性を持つ zip メンバーの mode を返す。未設定なら 0。"""
    if info.create_system != 3:
        return 0
    return (info.external_attr >> 16) & 0xFFFF


def _zip_info_external_attr_summary(info: zipfile.ZipInfo, mode: int) -> str:
    """unsafe mode 診断用に raw 属性値を安定表示する。"""
    return (
        f'mode {oct(mode)}; '
        f'external_attr 0x{info.external_attr:08x}; '
        f'create_system {info.create_system}'
    )


def _zip_info_unsafe_mode_reason(info: zipfile.ZipInfo) -> str:
    """release zip として安全でない特殊ファイル属性の理由を返す。"""
    mode = _zip_info_unix_mode(info)
    if not mode:
        return ''
    file_type = stat.S_IFMT(mode)
    attr_summary = _zip_info_external_attr_summary(info, mode)
    if file_type == stat.S_IFLNK:
        return f'symlink; {attr_summary}'
    if file_type and file_type not in {stat.S_IFREG, stat.S_IFDIR}:
        return f'unsupported file type {oct(file_type)}; {attr_summary}'
    return ''


def verify_release_zip_unsafe_member_modes(zip_path: Path) -> list[str]:
    """既存 release zip に symlink 等の特殊ファイル属性がないか返す。"""
    zip_path = zip_path.resolve()
    unsafe_entries: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if not info.filename:
                continue
            reason = _zip_info_unsafe_mode_reason(info)
            if reason:
                unsafe_entries.append(f'{_display_archive_member_name(info.filename)} ({reason})')
    return unsafe_entries


def _normalized_archive_member_name(member_name: str) -> str:
    """zip メンバー名を重複検査用に正規化する。"""
    return member_name.replace('\\', '/').strip('/')


def _archive_member_collision_key(member_name: str) -> str:
    """Windows/macOS 展開時の名前衝突検査用キーを返す。"""
    normalized_name = _normalized_archive_member_name(member_name)
    return unicodedata.normalize('NFC', normalized_name).casefold()


def _utf16_code_unit_count(value: str) -> int:
    """Windows パス長の概算に使う UTF-16 code unit 数を返す。"""
    return len(value.encode('utf-16-le')) // 2


def _archive_member_windows_length_reason(member_name: str) -> str:
    """Windows 展開時に長すぎる可能性が高い zip メンバー名の理由を返す。"""
    normalized_name = _normalized_archive_member_name(member_name)
    if not normalized_name:
        return ''
    name_units = _utf16_code_unit_count(normalized_name)
    if name_units > WINDOWS_PORTABLE_ARCHIVE_NAME_LIMIT:
        return f'path too long ({name_units} UTF-16 units > {WINDOWS_PORTABLE_ARCHIVE_NAME_LIMIT})'
    for part in normalized_name.split('/'):
        part_units = _utf16_code_unit_count(part)
        if part_units > WINDOWS_PORTABLE_ARCHIVE_PART_LIMIT:
            return f'path part too long ({part_units} UTF-16 units > {WINDOWS_PORTABLE_ARCHIVE_PART_LIMIT})'
    return ''


def verify_release_zip_windows_path_lengths(zip_path: Path) -> list[str]:
    """既存 release zip に Windows 展開で扱いづらい長すぎるメンバー名がないか返す。"""
    zip_path = zip_path.resolve()
    long_entries: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            raw_name = info.filename
            normalized_name = _normalized_archive_member_name(raw_name)
            reason = _archive_member_windows_length_reason(raw_name)
            if reason:
                display_name = _display_archive_member_with_normalized_context(raw_name, normalized_name)
                long_entries.append(f'{display_name} ({reason})')
    return long_entries


def _duplicate_archive_member_group_reason(member_names: Iterable[str]) -> str:
    """重複・衝突した zip member 名グループを診断表示用に整形する。"""
    displayed_names = [
        _display_archive_member_name(name)
        for name in member_names
    ]
    if not displayed_names:
        return '<empty duplicate member group>'
    return f"{displayed_names[-1]} (duplicate/collision group: {', '.join(displayed_names)})"


def verify_release_zip_duplicate_members(zip_path: Path) -> list[str]:
    """既存 release zip に同一名・Windows 上で衝突するメンバー名がないか返す。"""
    zip_path = zip_path.resolve()
    member_names_by_key: dict[str, list[str]] = {}
    key_order: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            normalized_name = _normalized_archive_member_name(info.filename)
            if not normalized_name:
                continue
            collision_key = _archive_member_collision_key(normalized_name)
            if collision_key not in member_names_by_key:
                member_names_by_key[collision_key] = []
                key_order.append(collision_key)
            member_names_by_key[collision_key].append(info.filename)
    return [
        _duplicate_archive_member_group_reason(member_names_by_key[key])
        for key in key_order
        if len(member_names_by_key[key]) > 1
    ]


def _is_bundled_font_dir_name(name: str) -> bool:
    return name.casefold() in _casefold_set(BUNDLED_FONT_DIR_NAMES)


def _is_bundled_font_path_parts(parts: tuple[str, ...], suffix: str) -> bool:
    return bool(parts) and _is_bundled_font_dir_name(parts[0]) and suffix.lower() in BUNDLED_FONT_SUFFIXES


def _is_required_bundled_font_license_parts(parts: tuple[str, ...]) -> bool:
    required_name = REQUIRED_BUNDLED_FONT_LICENSE.casefold()
    folded = tuple(part.casefold() for part in parts)
    if len(folded) == 1:
        return folded[0] == required_name
    if len(folded) == 2:
        return _is_bundled_font_dir_name(folded[0]) and folded[1] == required_name
    return False


def _required_bundled_font_license_missing_reason() -> str:
    return f'{REQUIRED_BUNDLED_FONT_LICENSE} (required when bundled fonts are included)'


def _required_bundled_font_license_empty_reason() -> str:
    return f'{REQUIRED_BUNDLED_FONT_LICENSE} (bundled font license must not be empty)'


def _required_bundled_font_license_decode_reason() -> str:
    return f'{REQUIRED_BUNDLED_FONT_LICENSE} (bundled font license could not be decoded as UTF-8/BOM-declared text)'


def _is_release_regular_file(path: Path) -> bool:
    """release 作成時に通常ファイルとして取り込めるパスかを返す。"""
    return path.is_file() and not path.is_symlink()


def _is_release_directory(path: Path) -> bool:
    """release 作成時に走査対象にできる実ディレクトリかを返す。"""
    return path.is_dir() and not path.is_symlink()


def iter_bundled_font_files(root: Path) -> Iterator[Path]:
    """release に同梱予定のローカルフォント一覧を返す。"""
    root = root.resolve()
    font_dirs = [
        path for path in root.iterdir()
        if _is_release_directory(path) and _is_bundled_font_dir_name(path.name)
    ]
    for font_dir in sorted(font_dirs, key=lambda p: natural_sort_key(p.name)):
        for path in sorted(font_dir.rglob('*'), key=lambda p: natural_sort_key(str(p.relative_to(root)).replace('\\', '/'))):
            if _is_release_regular_file(path) and path.suffix.lower() in BUNDLED_FONT_SUFFIXES:
                yield path


def _tree_required_bundled_font_license_issue(root: Path) -> str:
    """同梱フォント用ライセンスが許容位置にあり、空でないかを返す。"""
    root = root.resolve()
    candidates: list[Path] = []
    candidates.extend(path for path in root.iterdir() if _is_release_regular_file(path))
    candidates.extend(
        child
        for font_dir in root.iterdir()
        if _is_release_directory(font_dir) and _is_bundled_font_dir_name(font_dir.name)
        for child in font_dir.iterdir()
        if _is_release_regular_file(child)
    )
    matched = [
        path
        for path in candidates
        if _is_required_bundled_font_license_parts(path.relative_to(root).parts)
    ]
    if not matched:
        return _required_bundled_font_license_missing_reason()

    first_read_error = ''
    first_decode_error = ''
    for path in matched:
        try:
            content_state = _text_bytes_have_non_whitespace_content(
                path.read_bytes(),
                require_utf8_without_bom=True,
            )
            if content_state is True:
                return ''
            if content_state is None and not first_decode_error:
                first_decode_error = _required_bundled_font_license_decode_reason()
        except OSError as exc:
            if not first_read_error:
                first_read_error = f'{REQUIRED_BUNDLED_FONT_LICENSE} (bundled font license could not be read: {exc})'

    if first_read_error:
        return first_read_error
    if first_decode_error:
        return first_decode_error
    return _required_bundled_font_license_empty_reason()


def _tree_has_required_bundled_font_license(root: Path) -> bool:
    """同梱フォント用ライセンスが許容位置にあり、空でないかを返す。"""
    return not _tree_required_bundled_font_license_issue(root)


def _tree_has_project_app_markers(root: Path) -> bool:
    """公開配布対象のアプリ本体を含むツリーかを返す。"""
    root = root.resolve()
    return any(_is_release_regular_file(root / name) for name in PROJECT_APP_MARKER_FILES)


def _tree_missing_required_public_docs(root: Path) -> list[str]:
    """公開配布対象ツリーで不足している必須公開文書を返す。"""
    root = root.resolve()
    if not _tree_has_project_app_markers(root):
        return []
    return [name for name in REQUIRED_PUBLIC_DOC_FILES if not _is_release_regular_file(root / name)]


def _required_project_support_member_names() -> tuple[str, ...]:
    return (
        *REQUIRED_PROJECT_APP_ENTRY_FILES,
        *REQUIRED_PROJECT_APP_MODULE_FILES,
        *REQUIRED_PROJECT_SUPPORT_FILES,
        *REQUIRED_PROJECT_TOOLING_FILES,
        *REQUIRED_PROJECT_GUI_ASSET_FILES,
        *REQUIRED_PROJECT_TEST_SUPPORT_FILES,
        *REQUIRED_PROJECT_TEST_DATA_FILES,
        *REQUIRED_PROJECT_REGRESSION_TEST_FILES,
    )


def _duplicate_sequence_items(items: Iterable[str]) -> list[str]:
    """同じ必須ファイル名が複数回登録されていれば、2回目以降の名前を返す。"""
    seen: set[str] = set()
    duplicates: list[str] = []
    duplicate_keys: set[str] = set()
    for item in items:
        key = unicodedata.normalize('NFC', item).casefold()
        if key in seen and key not in duplicate_keys:
            duplicates.append(item)
            duplicate_keys.add(key)
            continue
        seen.add(key)
    return duplicates


def _required_release_file_duplicate_reason(name: str) -> str:
    return f'{name} (duplicate entry in REQUIRED_PROJECT_RELEASE_FILES)'


def _required_release_file_path_issue_reason(name: str) -> str:
    return f'{name} (required file path must be a normalized POSIX relative path in REQUIRED_PROJECT_RELEASE_FILES)'


def _required_release_member_spelling_issue_reason(required_name: str, actual_name: str) -> str:
    actual_display = _display_archive_member_name(actual_name)
    return f'{required_name} (required file is present only as {actual_display}; use canonical archive member spelling)'


def _required_content_marker_key_issue_reason(name: str) -> str:
    return f'{name} (content marker key is not listed in REQUIRED_PROJECT_RELEASE_FILES)'


def _required_content_marker_category_key_issue_reason(
    name: str,
    marker_map_name: str,
    required_list_name: str,
) -> str:
    return f'{name} (content marker key in {marker_map_name} is not listed in {required_list_name})'


def _required_content_marker_category_spec_duplicate_marker_map_reason(marker_map_name: str) -> str:
    return f'{marker_map_name} (duplicate content marker category spec marker map name)'


def _required_content_marker_category_spec_duplicate_required_list_reason(required_list_name: str) -> str:
    return f'{required_list_name} (duplicate content marker category spec required list name)'


def _required_content_marker_category_spec_empty_marker_map_reason(marker_map_name: str) -> str:
    return f'{marker_map_name} (empty content marker category spec marker map)'


def _required_content_marker_category_spec_empty_required_list_reason(
    marker_map_name: str,
    required_list_name: str,
) -> str:
    return f'{required_list_name} (empty content marker category spec required list for {marker_map_name})'


def _required_content_marker_category_spec_duplicate_required_entry_reason(
    name: str,
    required_list_name: str,
) -> str:
    return f'{name} (duplicate entry in content marker category spec required list {required_list_name})'


def _required_release_file_path_issues() -> list[str]:
    """必須 release ファイル一覧に、環境依存しやすいパス表記がないか返す。"""
    issues: list[str] = []
    for name in REQUIRED_PROJECT_RELEASE_FILES:
        normalized = _normalized_archive_member_name(name)
        if (
            not name
            or name != normalized
            or '\\' in name
            or not _relative_path_should_be_included(Path(name), is_dir=False)
        ):
            issues.append(_required_release_file_path_issue_reason(name))
    return issues


def _required_content_marker_key_issues() -> list[str]:
    """内容 marker map のキーが必須 release ファイル一覧と同期しているか返す。"""
    required = {
        unicodedata.normalize('NFC', name).casefold()
        for name in REQUIRED_PROJECT_RELEASE_FILES
    }
    issues: list[str] = []
    seen: set[str] = set()
    for marker_map in _required_content_marker_maps():
        for name in marker_map:
            key = unicodedata.normalize('NFC', name).casefold()
            if key in seen:
                continue
            seen.add(key)
            if key not in required:
                issues.append(_required_content_marker_key_issue_reason(name))
    return sorted(issues, key=natural_sort_key)


def _required_content_marker_category_spec_issues() -> list[str]:
    """内容 marker map とカテゴリ必須リストの対応表自体の静的問題を返す。"""
    issues: list[str] = []
    seen_marker_map_names: set[str] = set()
    seen_required_list_names: set[str] = set()
    for marker_map_name, marker_map, category_files, category_list_name in _required_content_marker_category_specs():
        marker_map_key = unicodedata.normalize('NFC', marker_map_name).casefold()
        required_list_key = unicodedata.normalize('NFC', category_list_name).casefold()

        if marker_map_key in seen_marker_map_names:
            issues.append(
                _required_content_marker_category_spec_duplicate_marker_map_reason(marker_map_name)
            )
        else:
            seen_marker_map_names.add(marker_map_key)

        if required_list_key in seen_required_list_names:
            issues.append(
                _required_content_marker_category_spec_duplicate_required_list_reason(category_list_name)
            )
        else:
            seen_required_list_names.add(required_list_key)

        if not marker_map:
            issues.append(_required_content_marker_category_spec_empty_marker_map_reason(marker_map_name))
        if not category_files:
            issues.append(
                _required_content_marker_category_spec_empty_required_list_reason(
                    marker_map_name,
                    category_list_name,
                )
            )

        for name in _duplicate_sequence_items(category_files):
            issues.append(
                _required_content_marker_category_spec_duplicate_required_entry_reason(
                    name,
                    category_list_name,
                )
            )

    return sorted(set(issues), key=natural_sort_key)


def _required_content_marker_category_key_issues() -> list[str]:
    """内容 marker map のキーが該当カテゴリの必須リストと同期しているか返す。"""
    required_release = {
        unicodedata.normalize('NFC', name).casefold()
        for name in REQUIRED_PROJECT_RELEASE_FILES
    }
    issues: list[str] = []
    for (
        marker_map_name,
        marker_map,
        category_files,
        category_list_name,
    ) in _required_content_marker_category_specs():
        category_keys = {
            unicodedata.normalize('NFC', name).casefold()
            for name in category_files
        }
        for name in marker_map:
            key = unicodedata.normalize('NFC', name).casefold()
            if key not in required_release:
                continue
            if key not in category_keys:
                issues.append(
                    _required_content_marker_category_key_issue_reason(
                        name,
                        marker_map_name,
                        category_list_name,
                    )
                )
    return sorted(set(issues), key=natural_sort_key)


def _required_release_file_list_issues() -> list[str]:
    """必須 release ファイル一覧の静的な重複・パス表記・marker 同期問題を返す。"""
    return (
        [
            _required_release_file_duplicate_reason(name)
            for name in _duplicate_sequence_items(REQUIRED_PROJECT_RELEASE_FILES)
        ]
        + _required_release_file_path_issues()
        + _required_content_marker_category_spec_issues()
        + _required_content_marker_key_issues()
        + _required_content_marker_category_key_issues()
    )

def _tree_missing_required_project_support_files(root: Path) -> list[str]:
    """公開配布対象ツリーで不足している起動・依存関係ファイルや分割モジュール・GUI資産を返す。"""
    root = root.resolve()
    if not _tree_has_project_app_markers(root):
        return []
    return [name for name in _required_project_support_member_names() if not _is_release_regular_file(root / name)]


def _is_regression_test_member_name(member_name: str) -> bool:
    """release 必須リストと同期すべき tests/test_*.py かを返す。"""
    normalized = _normalized_archive_member_name(member_name)
    if not normalized:
        return False
    path = PureWindowsPath(normalized)
    return (
        len(path.parts) == 2
        and path.parts[0].casefold() == 'tests'
        and path.name.casefold().startswith('test_')
        and path.suffix.casefold() == '.py'
    )


def _required_regression_test_list_untracked_reason(name: str) -> str:
    return f'{name} (regression test file is not listed in REQUIRED_PROJECT_REGRESSION_TEST_FILES)'


def _tree_untracked_regression_test_files(root: Path) -> list[str]:
    """実ツリーにある tests/test_*.py のうち、必須リストから漏れているものを返す。"""
    root = root.resolve()
    if not _tree_has_project_app_markers(root):
        return []
    required = _required_release_member_keys(REQUIRED_PROJECT_REGRESSION_TEST_FILES)
    tests_dir = root / 'tests'
    if not _is_release_directory(tests_dir):
        return []
    untracked: list[str] = []
    for path in sorted(tests_dir.glob('test_*.py'), key=lambda p: natural_sort_key(p.name)):
        if not _is_release_regular_file(path):
            continue
        rel_name = path.relative_to(root).as_posix()
        if not should_include_path(path, root):
            continue
        if _required_release_member_key(rel_name) not in required:
            untracked.append(_required_regression_test_list_untracked_reason(rel_name))
    return untracked


def _expected_golden_image_names_from_case_specs_source(source: str) -> list[str]:
    """CASE_SPECS の静的 dict literal から期待される golden PNG 名を返す。"""
    try:
        module = ast.parse(source)
    except SyntaxError:
        return []
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == 'CASE_SPECS' for target in node.targets):
            continue
        try:
            case_specs = ast.literal_eval(node.value)
        except (TypeError, ValueError):
            return []
        if not isinstance(case_specs, dict):
            return []
        names = [
            f'tests/golden_images/{case_name}.png'
            for case_name in case_specs
            if isinstance(case_name, str)
        ]
        return sorted(names, key=natural_sort_key)
    return []


def _preferred_golden_case_specs_source_text(source_candidates: list[str]) -> str:
    """CASE_SPECS を静的展開できる source を優先順で返す。"""
    for source in source_candidates:
        if _expected_golden_image_names_from_case_specs_source(source):
            return source
    return source_candidates[0] if source_candidates else ''


def _required_golden_case_list_untracked_reason(name: str) -> str:
    return f'{name} (golden image derived from CASE_SPECS is not listed in REQUIRED_PROJECT_GOLDEN_IMAGE_FILES)'


def _untracked_golden_case_files_from_source(source: str) -> list[str]:
    required = _required_release_member_keys(REQUIRED_PROJECT_GOLDEN_IMAGE_FILES)
    return [
        _required_golden_case_list_untracked_reason(name)
        for name in _expected_golden_image_names_from_case_specs_source(source)
        if _required_release_member_key(name) not in required
    ]


def _tree_untracked_golden_case_files(root: Path) -> list[str]:
    """CASE_SPECS 由来の golden PNG が必須リストから漏れていないか返す。"""
    root = root.resolve()
    if not _tree_has_project_app_markers(root):
        return []
    sources: list[str] = []
    for rel_name in ('tests/golden_case_registry.py', 'tests/image_golden_cases.py'):
        source_path = root / rel_name
        if not _is_release_regular_file(source_path):
            continue
        try:
            sources.append(source_path.read_text(encoding='utf-8'))
        except OSError:
            continue
    if not sources:
        return []
    return _untracked_golden_case_files_from_source(_preferred_golden_case_specs_source_text(sources))


_TEXT_BOM_ENCODINGS = (
    (b'\xef\xbb\xbf', 'utf-8-sig'),
    (b'\xff\xfe\x00\x00', 'utf-32'),
    (b'\x00\x00\xfe\xff', 'utf-32'),
    (b'\xff\xfe', 'utf-16'),
    (b'\xfe\xff', 'utf-16'),
)


def _text_has_non_whitespace_content(text: str) -> bool:
    """可読テキストとして意味のある非空文字が含まれるか返す。"""
    return any(
        not char.isspace() and not unicodedata.category(char).startswith('C')
        for char in text
    )


def _looks_like_undeclared_utf16_or_utf32_text(data: bytes) -> bool:
    """BOM なし UTF-16/UTF-32 風のテキストを検出する。

    同梱フォントライセンスは UTF-8 または BOM 宣言付き UTF-16/UTF-32 のみを
    受け入れるため、NUL が規則的に混ざる BOM なし UTF-16/UTF-32 風 byte 列は
    UTF-8 として decode できても decode 不能扱いにする。
    """
    if len(data) < 4 or b'\x00' not in data:
        return False

    def ascii_ratio(values: bytes) -> float:
        if not values:
            return 0.0
        printable = sum(1 for value in values if value in (9, 10, 13) or 32 <= value <= 126)
        return printable / len(values)

    even = data[0::2]
    odd = data[1::2]
    if len(even) >= 2 and len(odd) >= 2:
        if even.count(0) / len(even) >= 0.75 and ascii_ratio(odd) >= 0.75:
            return True
        if odd.count(0) / len(odd) >= 0.75 and ascii_ratio(even) >= 0.75:
            return True

    groups = [data[index::4] for index in range(4)]
    for offset, text_group in enumerate(groups):
        zero_groups = [group for index, group in enumerate(groups) if index != offset]
        if len(text_group) < 1 or not all(zero_groups):
            continue
        if ascii_ratio(text_group) < 0.75:
            continue
        zero_values = sum(value == 0 for group in zero_groups for value in group)
        total_values = sum(len(group) for group in zero_groups)
        if total_values and zero_values / total_values >= 0.75:
            return True
    return False


def _text_bytes_have_non_whitespace_content(
    data: bytes,
    *,
    require_utf8_without_bom: bool = False,
) -> bool | None:
    """テキスト byte 列の非空判定を返す。decode 不能なら None を返す。"""
    if not data.strip():
        return False
    for bom, encoding in _TEXT_BOM_ENCODINGS:
        if not data.startswith(bom):
            continue
        try:
            return _text_has_non_whitespace_content(data.decode(encoding))
        except UnicodeDecodeError:
            return None
    if require_utf8_without_bom:
        if _looks_like_undeclared_utf16_or_utf32_text(data):
            return None
        try:
            return _text_has_non_whitespace_content(data.decode('utf-8'))
        except UnicodeDecodeError:
            return None
    return True


def _bytes_have_non_whitespace_content(data: bytes) -> bool:
    """必須テキスト系ファイルが BOM や空白のみでないかを返す。"""
    content_state = _text_bytes_have_non_whitespace_content(data)
    return True if content_state is None else content_state


def _required_file_empty_reason(name: str) -> str:
    return f'{name} (required file is empty)'


def _required_batch_ascii_reason(name: str) -> str:
    return f'{name} (Windows batch files must be ASCII)'


def _required_file_utf8_reason(name: str) -> str:
    return f'{name} (required text file must be UTF-8)'


def _required_batch_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (Windows batch file is missing required launch/dependency markers: {missing})'


def _required_requirements_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (requirements file is missing required dependency markers: {missing})'


def _required_document_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (release guide is missing required setup/launch markers: {missing})'


def _required_tooling_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (release tooling file is missing required test/build markers: {missing})'


def _required_gui_asset_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (GUI asset file is missing required SVG markers: {missing})'


def _required_app_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (project app file is missing required implementation markers: {missing})'


def _required_test_support_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (test support file is missing required regression-test markers: {missing})'


def _required_regression_test_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (regression test file is missing required test-case markers: {missing})'


def _required_test_fixture_missing_marker_reason(name: str, missing_markers: Iterable[str]) -> str:
    missing = ', '.join(missing_markers)
    return f'{name} (test fixture file is missing required fixture markers: {missing})'


def _required_golden_image_invalid_reason(name: str) -> str:
    return f'{name} (golden image file must be a PNG image)'


def _required_fixture_image_invalid_reason(name: str) -> str:
    return f'{name} (test fixture image file must be a PNG image)'


def _required_png_image_invalid_reason(name: str) -> str:
    if name in REQUIRED_PROJECT_GOLDEN_IMAGE_FILES:
        return _required_golden_image_invalid_reason(name)
    return _required_fixture_image_invalid_reason(name)


def _missing_text_content_markers(
    name: str,
    data: bytes,
    marker_map: dict[str, tuple[str, ...]],
    *,
    encoding: str,
) -> list[str]:
    markers = marker_map.get(name)
    if not markers:
        return []
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        return []
    folded = text.casefold()
    return [marker for marker in markers if marker.casefold() not in folded]


def _missing_app_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_APP_CONTENT_MARKERS,
        encoding='utf-8',
    )


def _missing_batch_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_BATCH_CONTENT_MARKERS,
        encoding='ascii',
    )


def _missing_requirements_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_REQUIREMENTS_CONTENT_MARKERS,
        encoding='utf-8',
    )


def _missing_document_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_DOCUMENT_CONTENT_MARKERS,
        encoding='utf-8',
    )


def _missing_tooling_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_TOOLING_CONTENT_MARKERS,
        encoding='utf-8',
    )


def _missing_gui_asset_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_GUI_ASSET_CONTENT_MARKERS,
        encoding='utf-8',
    )


def _missing_test_support_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_TEST_SUPPORT_CONTENT_MARKERS,
        encoding='utf-8',
    )


def _missing_regression_test_content_markers(name: str, data: bytes) -> list[str]:
    if name not in REQUIRED_PROJECT_REGRESSION_TEST_FILES:
        return []
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        return []
    folded = text.casefold()
    return [
        marker
        for marker in REQUIRED_REGRESSION_TEST_CONTENT_MARKERS
        if marker.casefold() not in folded
    ]


def _missing_test_fixture_content_markers(name: str, data: bytes) -> list[str]:
    return _missing_text_content_markers(
        name,
        data,
        REQUIRED_TEST_FIXTURE_CONTENT_MARKERS,
        encoding='utf-8',
    )


def _is_valid_required_png_image(name: str, data: bytes) -> bool:
    if name not in REQUIRED_PROJECT_PNG_IMAGE_FILES:
        return True
    return data.startswith(PNG_SIGNATURE)


def _required_file_content_issues_from_bytes(name: str, data: bytes) -> list[str]:
    """必須ファイル1件の空内容・文字コード・内容 marker・PNG 形式問題を返す。"""
    if not _bytes_have_non_whitespace_content(data):
        return [_required_file_empty_reason(name)]

    if name in REQUIRED_UTF8_TEXT_FILES:
        try:
            data.decode('utf-8')
        except UnicodeDecodeError:
            return [_required_file_utf8_reason(name)]

    issues: list[str] = []
    missing_app_markers = _missing_app_content_markers(name, data)
    if missing_app_markers:
        issues.append(_required_app_missing_marker_reason(name, missing_app_markers))

    if name in REQUIRED_ASCII_BATCH_FILES:
        if not data.isascii():
            return [_required_batch_ascii_reason(name)]
        missing_markers = _missing_batch_content_markers(name, data)
        if missing_markers:
            issues.append(_required_batch_missing_marker_reason(name, missing_markers))

    missing_requirement_markers = _missing_requirements_content_markers(name, data)
    if missing_requirement_markers:
        issues.append(_required_requirements_missing_marker_reason(name, missing_requirement_markers))

    missing_document_markers = _missing_document_content_markers(name, data)
    if missing_document_markers:
        issues.append(_required_document_missing_marker_reason(name, missing_document_markers))

    missing_tooling_markers = _missing_tooling_content_markers(name, data)
    if missing_tooling_markers:
        issues.append(_required_tooling_missing_marker_reason(name, missing_tooling_markers))

    missing_gui_asset_markers = _missing_gui_asset_content_markers(name, data)
    if missing_gui_asset_markers:
        issues.append(_required_gui_asset_missing_marker_reason(name, missing_gui_asset_markers))

    missing_test_support_markers = _missing_test_support_content_markers(name, data)
    if missing_test_support_markers:
        issues.append(_required_test_support_missing_marker_reason(name, missing_test_support_markers))

    missing_regression_test_markers = _missing_regression_test_content_markers(name, data)
    if missing_regression_test_markers:
        issues.append(_required_regression_test_missing_marker_reason(name, missing_regression_test_markers))

    missing_test_fixture_markers = _missing_test_fixture_content_markers(name, data)
    if missing_test_fixture_markers:
        issues.append(_required_test_fixture_missing_marker_reason(name, missing_test_fixture_markers))

    if not _is_valid_required_png_image(name, data):
        issues.append(_required_png_image_invalid_reason(name))

    return issues


def _tree_required_file_content_issues(root: Path) -> list[str]:
    """公開配布対象ツリーで、必須ファイルの空内容や .bat / requirements 内容問題を返す。"""
    root = root.resolve()
    if not _tree_has_project_app_markers(root):
        return []

    issues: list[str] = []
    for name in REQUIRED_PROJECT_RELEASE_FILES:
        path = root / name
        if not _is_release_regular_file(path):
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            issues.append(f'{name} (required file could not be read: {exc})')
            continue
        issues.extend(_required_file_content_issues_from_bytes(name, data))
    return issues


def validate_release_tree(root: Path) -> list[str]:
    """release 作成前に、公開配布に必要な資産不足を返す。"""
    root = root.resolve()
    missing_assets: list[str] = []
    missing_assets.extend(
        f'{name} (required for project release archives)'
        for name in _tree_missing_required_public_docs(root)
    )
    missing_assets.extend(
        f'{name} (required for project release archives)'
        for name in _tree_missing_required_project_support_files(root)
    )
    missing_assets.extend(_tree_untracked_regression_test_files(root))
    missing_assets.extend(_tree_untracked_golden_case_files(root))
    missing_assets.extend(_required_release_file_list_issues())
    missing_assets.extend(_tree_required_file_content_issues(root))

    bundled_fonts = list(iter_bundled_font_files(root))
    if bundled_fonts:
        bundled_font_license_issue = _tree_required_bundled_font_license_issue(root)
        if bundled_font_license_issue:
            missing_assets.append(bundled_font_license_issue)
    return missing_assets


def _required_release_member_key(name: str) -> str:
    """必須 release ファイル名の照合キーを NFC + casefold で返す。"""
    return unicodedata.normalize('NFC', name).casefold()


def _zip_info_matches_required_member_spelling(info: zipfile.ZipInfo, required_name: str) -> bool:
    """zip メンバーが必須ファイル名と NFC 正規化後に同じ綴りかを返す。

    Backslashes or leading/trailing slashes are not canonical zip member
    spelling, even if they normalize to the same logical path.
    """
    raw_member_name = info.filename
    normalized_archive_name = _normalized_archive_member_name(raw_member_name)
    if raw_member_name != normalized_archive_name or '\\' in raw_member_name:
        return False
    normalized_member_name = unicodedata.normalize('NFC', raw_member_name)
    return normalized_member_name == unicodedata.normalize('NFC', required_name)

def _zip_required_member_lookup_name(info: zipfile.ZipInfo) -> str:
    """必須ファイル照合に使える zip member 名を返す。

    Case variant は spelling 検査で別途報告しつつ内容確認の対象にするが、
    Windows 形式のバックスラッシュや leading/trailing slash など、POSIX
    member 名として非正規のものは必須ファイルの充足・内容確認に数えない。
    """
    raw_member_name = info.filename
    normalized_name = _normalized_archive_member_name(raw_member_name)
    if info.is_dir() or not normalized_name:
        return ''
    if raw_member_name != normalized_name or '\\' in raw_member_name:
        return ''
    if not _archive_member_name_should_be_included(raw_member_name, is_dir=False):
        return ''
    return raw_member_name


def _zip_required_member_info_by_key(
    zf: zipfile.ZipFile,
    required_names: Iterable[str],
) -> dict[str, zipfile.ZipInfo]:
    """必須ファイルに対応する zip メンバーを、正規名を優先して返す。

    大文字小文字だけが異なる衝突は別検査で報告する。内容検査側では、
    正規の必須ファイル名が存在する場合に case variant を先に読んで余計な
    内容エラーを出さないよう、NFC 正規化後の綴りが一致するメンバーを優先する。
    ただし、バックスラッシュ区切りなど POSIX member 名として非正規のものは
    必須ファイルの内容確認対象に数えない。
    """
    required_name_by_key = {
        _required_release_member_key(name): name
        for name in required_names
    }
    info_by_key: dict[str, zipfile.ZipInfo] = {}
    for info in zf.infolist():
        lookup_name = _zip_required_member_lookup_name(info)
        if not lookup_name:
            continue
        key = _required_release_member_key(lookup_name)
        required_name = required_name_by_key.get(key)
        if required_name is None:
            continue
        existing = info_by_key.get(key)
        if existing is None:
            info_by_key[key] = info
            continue
        if (
            _zip_info_matches_required_member_spelling(info, required_name)
            and not _zip_info_matches_required_member_spelling(existing, required_name)
        ):
            info_by_key[key] = info
    return info_by_key


def _zip_preferred_required_member_info(
    zf: zipfile.ZipFile,
    required_name: str,
) -> zipfile.ZipInfo | None:
    """単一の必須ファイルに対応する zip メンバーを、正規名優先で返す。"""
    return _zip_required_member_info_by_key(zf, (required_name,)).get(
        _required_release_member_key(required_name)
    )


def _zip_project_member_names(zip_path: Path) -> set[str]:
    """既存 zip の正規通常ファイル名を NFC + casefold で返す。

    Case variant は存在判定に使うが、バックスラッシュ区切りなど非正規の
    archive member は必須ファイルの充足扱いにしない。
    """
    zip_path = zip_path.resolve()
    member_names: set[str] = set()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            lookup_name = _zip_required_member_lookup_name(info)
            if not lookup_name:
                continue
            member_names.add(_required_release_member_key(lookup_name))
    return member_names


def verify_release_zip_required_member_spellings(zip_path: Path) -> list[str]:
    """既存 release zip の必須ファイルが正規の archive member 綴りで入っているか返す。

    Project archive detection for this spelling check intentionally accepts
    non-canonical app marker variants. Otherwise an archive containing only
    `/tategakiXTC_gui_studio.py` would be skipped before the spelling checker can
    report that the app marker itself needs canonical member spelling.
    """
    zip_path = zip_path.resolve()
    required_name_by_key = {
        _required_release_member_key(name): name
        for name in REQUIRED_PROJECT_RELEASE_FILES
    }
    project_app_marker_keys = _required_release_member_keys(PROJECT_APP_MARKER_FILES)
    has_project_app_marker_or_variant = False
    seen_exact_keys: set[str] = set()
    first_variant_by_key: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            normalized_name = _normalized_archive_member_name(info.filename)
            if not normalized_name or info.is_dir():
                continue
            key = _required_release_member_key(normalized_name)
            if key in project_app_marker_keys:
                has_project_app_marker_or_variant = True
            required_name = required_name_by_key.get(key)
            if required_name is None:
                continue
            if _zip_info_matches_required_member_spelling(info, required_name):
                seen_exact_keys.add(key)
            else:
                first_variant_by_key.setdefault(key, info.filename)

    if not has_project_app_marker_or_variant:
        return []

    issues = [
        _required_release_member_spelling_issue_reason(required_name, first_variant_by_key[key])
        for key, required_name in required_name_by_key.items()
        if key not in seen_exact_keys and key in first_variant_by_key
    ]
    return sorted(issues, key=natural_sort_key)


def _required_release_member_keys(names: Iterable[str]) -> set[str]:
    """必須 release ファイル名群を NFC + casefold の zip 照合キーへ変換する。"""
    return {_required_release_member_key(name) for name in names}


def _zip_has_project_app_markers(member_names: set[str]) -> bool:
    return any(key in member_names for key in _required_release_member_keys(PROJECT_APP_MARKER_FILES))


def _zip_has_project_app_marker_or_variant(
    zip_path: Path,
    member_names: set[str] | None = None,
) -> bool:
    """project archive 判定用に、app marker の非正規 spelling も検出する。

    Missing/support/content 系の検査は、必須ファイルの充足そのものには
    leading slash や backslash などの非正規 member を数えない。ただし、
    app marker 自体が非正規 spelling で入っている外部 zip は project
    archive として扱い、spelling 検査だけでなく不足検査も走らせる。
    """
    if member_names is not None and _zip_has_project_app_markers(member_names):
        return True

    zip_path = zip_path.resolve()
    project_app_marker_keys = _required_release_member_keys(PROJECT_APP_MARKER_FILES)
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            normalized_name = _normalized_archive_member_name(info.filename)
            if not normalized_name or info.is_dir():
                continue
            if _required_release_member_key(normalized_name) in project_app_marker_keys:
                return True
    return False


def _zip_missing_required_member_names(
    member_names: set[str],
    required_names: Iterable[str],
) -> list[str]:
    """NFC + casefold 済み zip member 集合に存在しない必須名を正規名で返す。"""
    return [
        name
        for name in required_names
        if _required_release_member_key(name) not in member_names
    ]


def _required_project_archive_missing_reason(name: str) -> str:
    return f'{name} (required for project release archives)'


def verify_release_zip_required_public_docs(zip_path: Path) -> list[str]:
    """既存 release zip に公開配布用の必須文書が揃っているか返す。"""
    member_names = _zip_project_member_names(zip_path)
    if not _zip_has_project_app_marker_or_variant(zip_path, member_names):
        return []
    return [
        _required_project_archive_missing_reason(name)
        for name in _zip_missing_required_member_names(member_names, REQUIRED_PUBLIC_DOC_FILES)
    ]


def verify_release_zip_required_project_support_files(zip_path: Path) -> list[str]:
    """既存 release zip に公開配布用の起動・依存関係ファイルが揃っているか返す。"""
    member_names = _zip_project_member_names(zip_path)
    if not _zip_has_project_app_marker_or_variant(zip_path, member_names):
        return []
    return [
        _required_project_archive_missing_reason(name)
        for name in _zip_missing_required_member_names(
            member_names,
            _required_project_support_member_names(),
        )
    ]


def verify_release_zip_untracked_regression_test_files(zip_path: Path) -> list[str]:
    """既存 release zip 内に、必須リストへ未登録の tests/test_*.py がないか返す。"""
    zip_path = zip_path.resolve()
    member_names = _zip_project_member_names(zip_path)
    if not _zip_has_project_app_marker_or_variant(zip_path, member_names):
        return []
    required = _required_release_member_keys(REQUIRED_PROJECT_REGRESSION_TEST_FILES)
    untracked: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            lookup_name = _zip_required_member_lookup_name(info)
            if not lookup_name:
                continue
            lookup_key = _required_release_member_key(lookup_name)
            if _is_regression_test_member_name(lookup_name) and lookup_key not in required:
                untracked.append(_required_regression_test_list_untracked_reason(lookup_name))
    return sorted(set(untracked), key=natural_sort_key)


def verify_release_zip_untracked_golden_case_files(zip_path: Path) -> list[str]:
    """既存 release zip 内の CASE_SPECS 由来 golden PNG が必須リストから漏れていないか返す。"""
    zip_path = zip_path.resolve()
    member_names = _zip_project_member_names(zip_path)
    if not _zip_has_project_app_marker_or_variant(zip_path, member_names):
        return []
    source_names = ('tests/golden_case_registry.py', 'tests/image_golden_cases.py')
    sources: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        for source_name in source_names:
            key = _required_release_member_key(source_name)
            if key not in member_names:
                continue
            info = _zip_preferred_required_member_info(zf, source_name)
            if info is None:
                continue
            try:
                sources.append(zf.read(info).decode('utf-8'))
            except (UnicodeDecodeError, OSError, RuntimeError, zipfile.BadZipFile):
                continue
    if not sources:
        return []
    source = _preferred_golden_case_specs_source_text(sources)
    return sorted(set(_untracked_golden_case_files_from_source(source)), key=natural_sort_key)


def verify_release_zip_required_file_list_issues(zip_path: Path) -> list[str]:
    """既存 release zip 検査時に、必須 release ファイル一覧の静的な重複・パス表記・marker 同期問題を返す。"""
    member_names = _zip_project_member_names(zip_path)
    if not _zip_has_project_app_marker_or_variant(zip_path, member_names):
        return []
    return _required_release_file_list_issues()


def verify_release_zip_required_file_contents(zip_path: Path) -> list[str]:
    """既存 release zip の必須ファイルが空でなく、.bat や requirements の最低限内容が揃うかを返す。"""
    zip_path = zip_path.resolve()
    member_names = _zip_project_member_names(zip_path)
    if not _zip_has_project_app_marker_or_variant(zip_path, member_names):
        return []

    with zipfile.ZipFile(zip_path) as zf:
        info_by_key = _zip_required_member_info_by_key(zf, REQUIRED_PROJECT_RELEASE_FILES)

        issues: list[str] = []
        for name in REQUIRED_PROJECT_RELEASE_FILES:
            info = info_by_key.get(_required_release_member_key(name))
            if info is None:
                continue
            try:
                data = zf.read(info)
            except Exception as exc:
                issues.append(f'{name} (required file could not be read: {exc})')
                continue
            issues.extend(_required_file_content_issues_from_bytes(name, data))
        return issues


def _zip_canonical_regular_member_name(info: zipfile.ZipInfo) -> str:
    """通常ファイルとして正規の zip member 名ならそのまま返す。"""
    raw_member_name = info.filename
    normalized_name = _normalized_archive_member_name(raw_member_name)
    if info.is_dir() or not normalized_name:
        return ''
    if raw_member_name != normalized_name or '\\' in raw_member_name:
        return ''
    if not _archive_member_name_should_be_included(raw_member_name, is_dir=False):
        return ''
    return raw_member_name


def verify_release_zip_required_assets(zip_path: Path) -> list[str]:
    """既存 release zip に必要な同梱フォント関連資産が揃っているか返す。"""
    zip_path = zip_path.resolve()
    has_bundled_font = False
    has_license_candidate = False
    has_non_empty_license = False
    first_license_read_error = ''
    first_license_decode_error = ''
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            canonical_name = _zip_canonical_regular_member_name(info)
            if not canonical_name:
                continue
            member_path = PurePosixPath(canonical_name)
            parts = member_path.parts
            if _is_required_bundled_font_license_parts(parts):
                has_license_candidate = True
                try:
                    content_state = _text_bytes_have_non_whitespace_content(
                        zf.read(info),
                        require_utf8_without_bom=True,
                    )
                    if content_state is True:
                        has_non_empty_license = True
                    elif content_state is None and not first_license_decode_error:
                        first_license_decode_error = _required_bundled_font_license_decode_reason()
                except Exception as exc:
                    if not first_license_read_error:
                        first_license_read_error = f'{REQUIRED_BUNDLED_FONT_LICENSE} (bundled font license could not be read: {exc})'
            if _is_bundled_font_path_parts(parts, member_path.suffix):
                has_bundled_font = True
    if not has_bundled_font:
        return []
    if has_non_empty_license:
        return []
    if first_license_read_error:
        return [first_license_read_error]
    if first_license_decode_error:
        return [first_license_decode_error]
    if has_license_candidate:
        return [_required_bundled_font_license_empty_reason()]
    return [_required_bundled_font_license_missing_reason()]



ReleaseZipVerificationCheck = tuple[
    str,
    Callable[[Path], list[str]],
    str,
    str,
]
ReleaseZipVerificationIssue = tuple[str, str, str, list[str]]


def _release_zip_verification_checks() -> tuple[ReleaseZipVerificationCheck, ...]:
    """release zip 作成後 self-check / --verify で共有する検査一覧を返す。"""
    return (
        (
            'integrity',
            verify_release_zip_integrity,
            'release zip failed integrity check',
            'Integrity check failed in release zip',
        ),
        (
            'duplicate_entries',
            verify_release_zip_duplicate_members,
            'release zip contained duplicate entries',
            'Duplicate entries found in release zip',
        ),
        (
            'unsafe_mode_entries',
            verify_release_zip_unsafe_member_modes,
            'release zip contained unsafe member modes',
            'Unsafe member modes found in release zip',
        ),
        (
            'long_path_entries',
            verify_release_zip_windows_path_lengths,
            'release zip contained Windows-long paths',
            'Windows-long paths found in release zip',
        ),
        (
            'required_member_spelling_issues',
            verify_release_zip_required_member_spellings,
            'release zip contained non-canonical required member spellings',
            'Non-canonical required member spellings found in release zip',
        ),
        (
            'bad_entries',
            verify_release_zip,
            'release zip contained excluded entries',
            'Excluded entries found in release zip',
        ),
        (
            'missing_public_docs',
            verify_release_zip_required_public_docs,
            'release zip missing required public docs',
            'Missing required public docs in release zip',
        ),
        (
            'missing_support_files',
            verify_release_zip_required_project_support_files,
            'release zip missing required project support files',
            'Missing required project support files in release zip',
        ),
        (
            'untracked_regression_tests',
            verify_release_zip_untracked_regression_test_files,
            'release zip contained untracked regression tests',
            'Untracked regression tests found in release zip',
        ),
        (
            'untracked_golden_cases',
            verify_release_zip_untracked_golden_case_files,
            'release zip contained untracked golden case files',
            'Untracked golden case files found in release zip',
        ),
        (
            'required_file_list_issues',
            verify_release_zip_required_file_list_issues,
            'release zip invalid required file list',
            'Invalid required file list in release zip',
        ),
        (
            'required_file_content_issues',
            verify_release_zip_required_file_contents,
            'release zip invalid required file contents',
            'Invalid required file contents in release zip',
        ),
        (
            'missing_assets',
            verify_release_zip_required_assets,
            'release zip missing required assets',
            'Missing required assets in release zip',
        ),
    )


def _run_release_zip_verification_checks(zip_path: Path) -> list[ReleaseZipVerificationIssue]:
    """release zip 検査を共通順序で実行し、問題がある項目だけ返す。"""
    issues: list[ReleaseZipVerificationIssue] = []
    for key, check_func, build_prefix, verify_prefix in _release_zip_verification_checks():
        entries = check_func(zip_path)
        if entries:
            issues.append((key, build_prefix, verify_prefix, entries))
            if key == 'integrity':
                break
    return issues


def _format_release_zip_issue_entries(entries: Iterable[str]) -> str:
    """release zip 検査結果の項目一覧を安定した one-line 表示にする。

    Single-entry diagnostics stay compact. Multi-entry diagnostics are item-labeled
    instead of relying only on a separator, because archive member names and
    reason strings can themselves contain semicolons.
    """
    formatted_entries = [
        _display_release_zip_diagnostic_text(str(entry))
        for entry in entries
    ]
    if not formatted_entries:
        return '<no details>'
    if len(formatted_entries) == 1:
        return formatted_entries[0]
    indexed_entries = ' '.join(
        f'[item {index}] {entry}'
        for index, entry in enumerate(formatted_entries, start=1)
    )
    return f'{len(formatted_entries)} items: {indexed_entries}'


def _release_zip_verify_issue_messages(
    issues: Iterable[ReleaseZipVerificationIssue],
) -> list[str]:
    """--verify 用の診断メッセージを共通形式で返す。"""
    return [
        f'{verify_prefix}: {_format_release_zip_issue_entries(entries)}'
        for _key, _build_prefix, verify_prefix, entries in issues
    ]


def _format_release_zip_issue_messages(messages: Iterable[str]) -> str:
    """複数カテゴリの release zip 診断を安定した one-line 表示にする。

    Single-category diagnostics stay compact. Multi-category diagnostics are
    group-labeled instead of relying on a bare separator, because detail messages may
    contain punctuation that makes category boundaries hard to spot.
    """
    formatted_messages = [
        _display_release_zip_diagnostic_text(str(message))
        for message in messages
    ]
    if not formatted_messages:
        return '<no issue groups>'
    if len(formatted_messages) == 1:
        return formatted_messages[0]
    indexed_messages = ' '.join(
        f'[group {index}] {message}'
        for index, message in enumerate(formatted_messages, start=1)
    )
    return f'{len(formatted_messages)} issue groups: {indexed_messages}'


def _first_release_zip_build_error_message(
    issues: Iterable[ReleaseZipVerificationIssue],
) -> str:
    """release zip 作成後 self-check 用に最初の失敗を共通形式で返す。"""
    for _key, build_prefix, _verify_prefix, entries in issues:
        return f'{build_prefix}: {_format_release_zip_issue_entries(entries)}'
    return 'release zip verification failed'


def build_release_zip(root: Path, output_path: Path) -> Path:
    """開発用生成物を除外した release zip を作成する。"""
    root = root.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing_assets = validate_release_tree(root)
    if missing_assets:
        raise RuntimeError(f'release zip missing required assets: {missing_assets}')

    with zipfile.ZipFile(output_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in iter_release_files(root, excluded_paths=(output_path,)):
            if not file_path.is_file():
                continue
            try:
                rel_path = _normalized_relative_path(file_path, root)
            except Exception:
                continue
            archive_name = rel_path.as_posix()
            if not archive_member_should_be_included(archive_name, is_dir=False):
                continue
            zf.write(file_path, archive_name)

    verification_issues = _run_release_zip_verification_checks(output_path)
    if verification_issues:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError(_first_release_zip_build_error_message(verification_issues))
    return output_path



def default_release_output_path(root: Path) -> Path:
    """Return the versioned default release zip path for a project root."""
    return root / 'dist' / RELEASE_ZIP_FILE_NAME


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='開発用生成物を除外した release zip を作成または検査します。')
    parser.add_argument('--root', default='.', help='対象ルートフォルダ')
    parser.add_argument('--output', default='', help=f'出力 zip パス。未指定時は dist/{RELEASE_ZIP_FILE_NAME}')
    parser.add_argument('--verify', default='', metavar='ZIP_PATH', help='既存 zip を検査する場合の zip パス')
    return parser.parse_args()



def main() -> int:
    args = parse_args()
    verify_target = Path(args.verify).resolve() if args.verify else None
    if verify_target is not None:
        verification_issues = _run_release_zip_verification_checks(verify_target)
        if verification_issues:
            raise SystemExit(_format_release_zip_issue_messages(
                _release_zip_verify_issue_messages(verification_issues)
            ))
        print(verify_target)
        return 0

    root = Path(args.root).resolve()
    default_output = default_release_output_path(root)
    output_path = Path(args.output).resolve() if args.output else default_output
    created = build_release_zip(root, output_path)
    print(created)
    return 0



if __name__ == '__main__':
    raise SystemExit(main())
