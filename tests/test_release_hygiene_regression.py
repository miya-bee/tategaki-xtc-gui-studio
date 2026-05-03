from pathlib import Path
import unittest



class ReleaseHygieneRegressionTests(unittest.TestCase):
    def test_dummy_placeholder_files_are_not_packaged(self):
        self.assertFalse(Path('dummy.xtc').exists())
        self.assertFalse(Path('dummy_preview.epub').exists())

    def test_run_tests_bat_checks_golden_images_and_coverage(self):
        content = Path('run_tests.bat').read_text(encoding='utf-8')
        self.assertIn('tests\\generate_golden_images.py --check', content)
        self.assertIn('-m mypy --config-file mypy.ini', content)
        self.assertIn('-m coverage run -m unittest discover -s tests -v', content)
        self.assertIn('-m coverage report -m --fail-under=60 > coverage-report.txt', content)
        self.assertIn('type coverage-report.txt', content)
        self.assertIn('-m coverage xml -o coverage.xml', content)
        self.assertIn('-m coverage html -d htmlcov', content)
        self.assertIn('build_release_zip.py', content)
        self.assertIn('tategakiXTC_release_metadata.py', content)
        self.assertIn('build_release_zip.py --verify', content)
        self.assertIn(r'dist\*-release.zip', content)
        self.assertIn('tategakiXTC_gui_widget_factory.py', content)
        self.assertIn('tategakiXTC_worker_logic.py', content)
        self.assertNotIn('localweb_launcher.py', content)
        self.assertNotIn('tategakiXTC_localweb.py', content)
        self.assertNotIn('tategakiXTC_localweb_service.py', content)
        self.assertIn('py_compile.compile', content)
        self.assertNotIn(r'tests\*.py', content)

    def test_github_actions_tests_multiple_python_versions_and_coverage(self):
        content = Path('.github/workflows/python-tests.yml').read_text(encoding='utf-8')
        self.assertIn("['3.10', '3.11', '3.12']", content)
        self.assertIn('matrix.python-version', content)
        self.assertIn('python -m pip install -r requirements.txt', content)
        self.assertNotIn('python -m pip install -r requirements-web.txt', content)
        self.assertIn('python -m mypy --config-file mypy.ini', content)
        self.assertIn('python -m coverage run -m unittest discover -s tests -v', content)
        self.assertIn('python -m coverage report -m --fail-under=60 > coverage-report.txt', content)
        self.assertIn('Get-Content coverage-report.txt', content)
        self.assertIn('python -m coverage xml -o coverage.xml', content)
        self.assertIn('python -m coverage html -d htmlcov', content)
        self.assertIn('build_release_zip.py', content)
        self.assertIn('python build_release_zip.py --verify dist/${{ github.event.repository.name }}-release.zip', content)
        self.assertIn('tategakiXTC_gui_widget_factory.py', content)
        self.assertIn('tategakiXTC_worker_logic.py', content)
        self.assertNotIn('localweb_launcher.py', content)
        self.assertNotIn('tategakiXTC_localweb.py', content)
        self.assertNotIn('tategakiXTC_localweb_service.py', content)
        self.assertIn('py_compile.compile', content)
        self.assertNotIn(r'tests\*.py', content)
        self.assertIn('Upload coverage artifacts', content)
        self.assertIn('coverage-report.txt', content)
        self.assertIn('build_release_zip.py --verify', content)


    def test_changelog_exists_and_mentions_current_release(self):
        content = Path('CHANGELOG.md').read_text(encoding='utf-8')
        self.assertIn('## v1.2.1', content)
        self.assertIn('v1.2.1 は、v1.2.0 を基準にした TXT / Markdown プレビューの小修正版です。', content)
        self.assertIn('## v1.1.0', content)
        self.assertIn('v1.0.2 の次の正式版 v1.1.0', content)
        self.assertIn('tategakiXTC_gui_studio_logic.py', content)
        self.assertIn('py_compile.compile', Path('run_tests.bat').read_text(encoding='utf-8'))


    def test_release_notes_file_matches_public_version(self):
        self.assertTrue(Path('RELEASE_NOTES_v1_2_1.md').exists())
        self.assertFalse(Path('RELEASE_NOTES_v1_1_69.md').exists())
        notes = Path('RELEASE_NOTES_v1_2_1.md').read_text(encoding='utf-8')
        self.assertIn('v1.2.1', notes)
        self.assertNotIn('1.1.69', notes)
        self.assertNotIn('bugfix', notes.casefold())

    def test_readme_describes_coverage_policy(self):
        content = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('## テストと coverage の運用', content)
        self.assertIn('fail-under は **60%**', content)
        self.assertIn('coverage-report.txt', content)


    def test_readme_describes_gui_smoke_offscreen_platform_default(self):
        content = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('QT_QPA_PLATFORM=offscreen', content)
        self.assertIn('ヘッドレス CI / WSL', content)


    def test_mypy_ini_targets_split_modules_too(self):
        content = Path('mypy.ini').read_text(encoding='utf-8')
        self.assertIn('build_release_zip.py', content)
        self.assertIn('tategakiXTC_release_metadata.py', content)
        self.assertIn('tategakiXTC_gui_core_renderer.py', content)
        self.assertIn('tategakiXTC_numpy_helper.py', content)
        self.assertIn('tategakiXTC_gui_core_epub.py', content)
        self.assertIn('tategakiXTC_gui_core_pages.py', content)
        self.assertIn('tategakiXTC_gui_layouts.py', content)
        self.assertIn('tategakiXTC_gui_widget_factory.py', content)
        self.assertIn('tategakiXTC_gui_preview_controller.py', content)
        self.assertIn('tategakiXTC_gui_results_controller.py', content)
        self.assertIn('tategakiXTC_gui_settings_controller.py', content)
        self.assertIn('tategakiXTC_gui_studio.py', content)
        self.assertIn('tategakiXTC_gui_studio_logic.py', content)
        self.assertIn('tategakiXTC_gui_studio_startup.py', content)
        self.assertIn('tategakiXTC_gui_studio_constants.py', content)
        self.assertIn('tategakiXTC_gui_studio_xtc_io.py', content)
        self.assertIn('tategakiXTC_gui_studio_widgets.py', content)
        self.assertIn('tategakiXTC_gui_studio_worker.py', content)
        self.assertIn('tategakiXTC_gui_studio_runtime.py', content)
        self.assertIn('tategakiXTC_gui_studio_desktop.py', content)
        self.assertIn('tategakiXTC_gui_studio_ui_helpers.py', content)
        self.assertIn('tategakiXTC_gui_studio_dialog_helpers.py', content)
        self.assertIn('tategakiXTC_gui_studio_preview_helpers.py', content)
        self.assertIn('tategakiXTC_gui_studio_path_helpers.py', content)
        self.assertIn('tategakiXTC_gui_studio_view_helpers.py', content)
        self.assertIn('tategakiXTC_gui_studio_settings_helpers.py', content)
        self.assertIn('py_compile.compile', Path('run_tests.bat').read_text(encoding='utf-8'))
        self.assertIn('follow_imports = silent', content)
        self.assertIn('warn_unused_ignores = True', content)

    def test_readme_matches_current_ui_paths(self):
        content = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('Preset → Font → Image → Display', content)
        self.assertNotIn('「その他オプション」を左ペインへ戻し', content)
        self.assertNotIn('同梱 ini も合わせて更新しました', content)

    def test_public_docs_do_not_expose_internal_work_numbers(self):
        readme = Path('README.md').read_text(encoding='utf-8')
        changelog = Path('CHANGELOG.md').read_text(encoding='utf-8')
        notes = Path('RELEASE_NOTES_v1_2_1.md').read_text(encoding='utf-8')
        for content in (readme, changelog, notes):
            self.assertNotIn('bugfix171', content)
            self.assertNotIn('1.1.69', content)
        self.assertNotRegex(changelog, r'^## 1\.1\.0\.\d+', msg='公開向け CHANGELOG に内部作業番号見出しを残さないこと')


    def test_readme_documents_required_public_docs_release_verify(self):
        readme = Path('README.md').read_text(encoding='utf-8')
        build_release_source = Path('build_release_zip.py').read_text(encoding='utf-8')
        self.assertIn('Python GUI版のみ', readme)
        self.assertIn('作業用 payload に Web 試作ファイル候補', readme)
        self.assertIn('README.md', build_release_source)
        self.assertIn('LICENSE.txt', build_release_source)
        self.assertIn('CHANGELOG.md', build_release_source)
        self.assertIn('RELEASE_NOTES_FILE', build_release_source)
        self.assertIn('from tategakiXTC_release_metadata import RELEASE_NOTES_FILE, RELEASE_ZIP_FILE_NAME', build_release_source)
        self.assertIn('verify_release_zip_required_file_contents', build_release_source)
        self.assertIn('REQUIRED_ASCII_BATCH_FILES', build_release_source)
        self.assertIn('REQUIRED_UTF8_TEXT_FILES', build_release_source)
        self.assertIn('REQUIRED_BATCH_CONTENT_MARKERS', build_release_source)
        self.assertIn('REQUIRED_REQUIREMENTS_CONTENT_MARKERS', build_release_source)
        self.assertIn('REQUIRED_DOCUMENT_CONTENT_MARKERS', build_release_source)
        self.assertIn('PROHIBITED_WEB_RELEASE_FILES', build_release_source)
        self.assertIn('REQUIRED_PROJECT_APP_ENTRY_FILES', build_release_source)
        self.assertIn('REQUIRED_PROJECT_APP_MODULE_FILES', build_release_source)
        self.assertIn('REQUIRED_APP_CONTENT_MARKERS', build_release_source)
        self.assertIn('REQUIRED_PROJECT_GUI_ASSET_FILES', build_release_source)
        self.assertIn('REQUIRED_GUI_ASSET_CONTENT_MARKERS', build_release_source)
        self.assertIn('tategakiXTC_worker_logic.py', build_release_source)
        self.assertNotIn('REQUIRED_LOCALWEB_SUPPORT_CONTENT_MARKERS', build_release_source)
        self.assertNotIn('localweb_launcher.py\': (', build_release_source)
        self.assertNotIn('tategakiXTC_localweb_service.py\': (', build_release_source)
        self.assertIn('ui_assets/spin_up.svg', build_release_source)
        self.assertIn('REQUIRED_PROJECT_TEST_SUPPORT_FILES', build_release_source)
        self.assertIn('REQUIRED_TEST_SUPPORT_CONTENT_MARKERS', build_release_source)
        self.assertIn('tests/__init__.py', build_release_source)
        self.assertIn('tests/generate_golden_images.py', build_release_source)
        self.assertIn('REQUIRED_PROJECT_TEST_DATA_FILES', build_release_source)
        self.assertIn('REQUIRED_TEST_FIXTURE_CONTENT_MARKERS', build_release_source)
        self.assertIn('REQUIRED_PROJECT_TEST_FIXTURE_IMAGE_FILES', build_release_source)
        self.assertIn('REQUIRED_PROJECT_PNG_IMAGE_FILES', build_release_source)
        self.assertIn('tests/fixtures/epub/images/scene.png', build_release_source)
        self.assertIn('tests/fixtures/epub/styles/main.css', build_release_source)
        self.assertIn('REQUIRED_PROJECT_GOLDEN_IMAGE_FILES', build_release_source)
        self.assertIn('tests/golden_images/page_compound_layout.png', build_release_source)
        self.assertIn('REQUIRED_PROJECT_TOOLING_FILES', build_release_source)
        self.assertIn('REQUIRED_TOOLING_CONTENT_MARKERS', build_release_source)
        self.assertIn('mypy.ini', build_release_source)
        self.assertIn('.coveragerc', build_release_source)
        self.assertIn('.github/workflows/python-tests.yml', build_release_source)
        self.assertIn('REQUIRED_PROJECT_REGRESSION_TEST_FILES', build_release_source)
        self.assertIn('verify_release_zip_untracked_regression_test_files', build_release_source)
        self.assertIn('verify_release_zip_untracked_golden_case_files', build_release_source)
        self.assertIn('verify_release_zip_required_file_list_issues', build_release_source)
        self.assertIn('_required_file_content_issues_from_bytes', build_release_source)
        self.assertIn('_zip_required_member_info_by_key', build_release_source)
        self.assertIn('_zip_missing_required_member_names', build_release_source)
        self.assertIn('verify_release_zip_required_member_spellings', build_release_source)
        self.assertIn('_release_zip_verification_checks', build_release_source)
        self.assertIn('_run_release_zip_verification_checks', build_release_source)
        self.assertIn('_release_zip_verify_issue_messages', build_release_source)
        self.assertIn('_format_release_zip_issue_entries', build_release_source)
        self.assertIn('_display_release_zip_diagnostic_text', build_release_source)
        self.assertIn('_format_release_zip_issue_messages', build_release_source)


    def test_help_text_points_same_name_output_to_gear_menu(self):
        content = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        self.assertIn('右上の歯車メニュー内「その他オプション > 同名出力」', content)

    def test_studio_import_does_not_create_logs_until_configured(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        import_block = source[:source.index('def _resolve_log_dir')]

        self.assertIn("LOG_DIR = Path(__file__).resolve().parent / 'logs'", import_block)
        self.assertIn("FALLBACK_LOG_DIR = Path(tempfile.gettempdir()) / 'tategaki_xtc_logs'", import_block)
        self.assertIn('ACTIVE_LOG_DIR: Path | None = None', import_block)
        self.assertIn('SESSION_LOG_PATH: Path | None = None', import_block)
        self.assertNotIn('logging.FileHandler(', import_block)
        self.assertNotIn('LOG_DIR.mkdir(', import_block)
        self.assertNotIn('_resolve_session_log_path()', import_block)


    def test_resolve_session_log_path_falls_back_to_temp_dir_when_app_logs_unwritable(self):
        source = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        resolve_log_dir = source[source.index('def _resolve_log_dir'): source.index('def _resolve_session_log_path')]
        resolve_session_log_path = source[source.index('def _resolve_session_log_path'): source.index('def _configure_app_logging')]

        self.assertIn('for candidate in (LOG_DIR, FALLBACK_LOG_DIR):', resolve_log_dir)
        self.assertIn('candidate.mkdir(parents=True, exist_ok=True)', resolve_log_dir)
        self.assertIn('ACTIVE_LOG_DIR = candidate', resolve_log_dir)
        self.assertIn('raise last_error', resolve_log_dir)
        self.assertIn('log_dir = _resolve_log_dir()', resolve_session_log_path)
        self.assertIn('SESSION_LOG_PATH = log_dir /', resolve_session_log_path)

    def test_python_3_10_typing_compat_is_documented_and_packaged(self):
        requirements = Path('requirements.txt').read_text(encoding='utf-8')
        core = Path('tategakiXTC_gui_core.py').read_text(encoding='utf-8')
        self.assertIn('typing_extensions', requirements)
        self.assertIn('numpy', requirements)
        self.assertIn('from typing_extensions import NotRequired, Required, TypeAlias', core)
        self.assertIn("'impact': 'performance'", core)

    def test_run_gui_bat_guides_dependency_install_on_startup_failure(self):
        content = Path('run_gui.bat').read_text(encoding='utf-8')
        self.assertIn('-m pip install -r requirements.txt', content)
        self.assertIn('install_requirements.bat', content)
        self.assertIn('Python 3.10 / 3.11 / 3.12', content)
        self.assertIn('where py', content)
        self.assertIn('where python', content)
        self.assertIn('PY_VERSION_CHECK', content)


    def test_install_requirements_bat_installs_requirements(self):
        content = Path('install_requirements.bat').read_text(encoding='utf-8')
        self.assertIn('-m pip install --upgrade pip', content)
        self.assertIn('-m pip install -r requirements.txt', content)
        self.assertIn('Python 3.10 / 3.11 / 3.12', content)
        self.assertIn('where py', content)
        self.assertIn('where python', content)
        self.assertIn('PY_VERSION_CHECK', content)


    def test_batch_files_use_ascii_messages_to_avoid_cmd_mojibake(self):
        for relative in (
            'run_gui.bat',
            'install_requirements.bat',
            'run_tests.bat',
        ):
            content = Path(relative).read_text(encoding='utf-8')
            self.assertTrue(content.isascii(), relative)

    def test_batch_files_switch_to_their_own_folder_before_running(self):
        for relative in (
            'run_gui.bat',
            'install_requirements.bat',
            'run_tests.bat',
        ):
            content = Path(relative).read_text(encoding='utf-8')
            self.assertIn('set "SCRIPT_DIR=%~dp0"', content)
            self.assertIn('pushd "%SCRIPT_DIR%" >nul 2>nul', content)
            self.assertIn('Could not switch to the script folder.', content)
            self.assertIn('popd', content)


    def test_windows_batch_version_check_avoids_cmd_block_parentheses(self):
        for relative in (
            'run_gui.bat',
            'install_requirements.bat',
            'run_tests.bat',
        ):
            content = Path(relative).read_text(encoding='utf-8')
            version_line = next(
                line for line in content.splitlines()
                if line.startswith('set "PY_VERSION_CHECK=')
            )
            self.assertIn('sys.version_info.major == 3', version_line, relative)
            self.assertIn('sys.version_info.minor in [10, 11, 12]', version_line, relative)
            self.assertNotIn('sys.version_info[:2]', version_line, relative)
            self.assertNotIn('raise SystemExit(0 if (3, 10)', version_line, relative)
            self.assertNotIn('<=', version_line, relative)
            self.assertNotIn('(', version_line, relative)
            self.assertNotIn(')', version_line, relative)

    def test_windows_batch_files_quote_python_executable_paths_and_fallbacks(self):
        for relative in (
            'run_gui.bat',
            'install_requirements.bat',
            'run_tests.bat',
        ):
            content = Path(relative).read_text(encoding='utf-8')
            self.assertIn('set "PY_EXE="', content)
            self.assertIn('set "PY_ARGS="', content)
            self.assertIn('"%PY_EXE%" %PY_ARGS%', content)
            self.assertIn(r'%LocalAppData%\Programs\Python\Python%%V\python.exe', content)
            self.assertIn('for %%V in (3.12 3.11 3.10)', content)
            self.assertIn('for %%V in (312 311 310)', content)
            self.assertIn(r'"%LocalAppData%\Programs\Python\Python%%V\python.exe" -c "%PY_VERSION_CHECK%" >nul 2>nul', content)
            fallback_check_index = content.index(r'"%LocalAppData%\Programs\Python\Python%%V\python.exe" -c "%PY_VERSION_CHECK%"')
            fallback_set_index = content.index(r'set "PY_EXE=%LocalAppData%\Programs\Python\Python%%V\python.exe"')
            self.assertLess(fallback_check_index, fallback_set_index, relative)
            self.assertIn('PY_VERSION_CHECK', content)
            self.assertIn('Python 3.10 / 3.11 / 3.12', content)
            self.assertNotIn('Python313', content)
            self.assertNotIn('for %%V in (313', content)
            self.assertNotIn('set \"PY_ARGS=-3\"', content)
            self.assertNotIn('cd /d "%~dp0"', content)

    def test_windows_batch_files_disable_bytecode_cache_writes(self):
        for relative in (
            'run_gui.bat',
            'install_requirements.bat',
            'run_tests.bat',
        ):
            content = Path(relative).read_text(encoding='utf-8')
            self.assertIn('set \"PYTHONDONTWRITEBYTECODE=1\"', content, relative)
            self.assertLess(content.index('set \"PYTHONDONTWRITEBYTECODE=1\"'), content.index('set \"PY_EXE=\"'), relative)

    def test_readme_describes_release_zip_integrity_verify(self):
        content = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('build_release_zip.py --verify <zipパス>', content)
        self.assertIn('zip の読み取り破損', content)
        self.assertIn('symlink 等の特殊ファイル属性', content)
        self.assertIn('ローカル生成物混入', content)
        self.assertIn('必須 release ファイルリストの同期漏れ', content)
        self.assertIn('作業用 payload に Web 試作ファイル候補', content)
        self.assertIn('release 対象外', content)
        self.assertIn('フォントを同梱する場合は `LICENSE_OFL.txt`', content)


    def test_readme_verify_command_examples_include_zip_path_argument(self):
        content = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('build_release_zip.py ^\n      --verify ^\n      dist\\tategaki-xtc-gui-studio_v1.2.1-release.zip', content)
        self.assertIn('python build_release_zip.py --verify dist\\tategaki-xtc-gui-studio_v1.2.1-release.zip', content)
        self.assertNotIn('dist\\sweep471_smoke-release.zip', content)


    def test_build_release_zip_verify_arg_help_names_zip_path(self):
        content = Path('build_release_zip.py').read_text(encoding='utf-8')
        self.assertIn("parser.add_argument('--verify'", content)
        self.assertIn("metavar='ZIP_PATH'", content)
        self.assertIn('既存 zip を検査する場合の zip パス', content)


    def test_build_release_zip_default_output_uses_public_versioned_filename(self):
        content = Path('build_release_zip.py').read_text(encoding='utf-8')
        metadata = Path('tategakiXTC_release_metadata.py').read_text(encoding='utf-8')
        self.assertIn('RELEASE_ZIP_FILE_NAME', content)
        self.assertIn('def default_release_output_path(root: Path) -> Path:', content)
        self.assertIn("return root / 'dist' / RELEASE_ZIP_FILE_NAME", content)
        self.assertIn('default_output = default_release_output_path(root)', content)
        self.assertIn("help=f'出力 zip パス。未指定時は dist/{RELEASE_ZIP_FILE_NAME}'", content)
        self.assertIn("RELEASE_ZIP_FILE_NAME = f'tategaki-xtc-gui-studio_v{PUBLIC_VERSION}-release.zip'", metadata)


    def test_release_docs_and_batches_are_registered_for_public_payload(self):
        builder = Path('build_release_zip.py').read_text(encoding='utf-8')
        readme = Path('README.md').read_text(encoding='utf-8')
        for expected in (
            "'install_requirements.bat'",
            "'run_gui.bat'",
            "'run_tests.bat'",
            'RELEASE_NOTES_FILE',
            'RELEASE_ZIP_FILE_NAME',
        ):
            self.assertIn(expected, builder)
        self.assertIn('install_requirements.bat', readme)
        self.assertIn('tategaki-xtc-gui-studio_v1.2.1-release.zip', readme)
        self.assertIn('RELEASE_NOTES_v1_2_1.md', readme)


    def test_run_tests_verifies_created_release_zip_with_explicit_path(self):
        content = Path('run_tests.bat').read_text(encoding='utf-8')
        self.assertIn('for %%F in (dist\\*-release.zip) do (', content)
        self.assertIn('build_release_zip.py --verify "%%~fF"', content)
        self.assertLess(
            content.index('build_release_zip.py'),
            content.index('build_release_zip.py --verify "%%~fF"'),
        )


    def test_readme_includes_initial_setup_steps(self):
        content = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('## 初回セットアップ', content)
        self.assertIn('py -3.12 -m pip install -r requirements.txt', content)
        self.assertIn('python -m pip install -r requirements.txt', content)
        self.assertIn('python --version', content)
        self.assertIn('3.10〜3.12 系であることを確認後', content)
        self.assertIn('py -3.11', content)
        self.assertIn('py -3.10', content)
        self.assertIn('py -3.12 build_release_zip.py', content)
        self.assertIn('python build_release_zip.py', content)
        self.assertIn('python build_release_zip.py --verify <zipパス>', content)
        self.assertIn('PySide6', content)
        self.assertIn('numpy', content)
        self.assertIn('高速化', content)
        self.assertIn('.venv/', content)
        self.assertIn('node_modules/', content)


    def test_gitignore_and_release_rules_exclude_rootcopy_and_work_clean_memos(self):
        gitignore = Path('.gitignore').read_text(encoding='utf-8')
        self.assertIn('*.rootcopy', gitignore)
        self.assertIn('work_clean*_md.md', gitignore)
        builder = Path('build_release_zip.py').read_text(encoding='utf-8')
        self.assertIn("'.rootcopy'", builder)
        self.assertIn("'work_clean*_md.md'", builder)

    def test_gitignore_and_release_rules_exclude_local_archives(self):
        gitignore = Path('.gitignore').read_text(encoding='utf-8')
        builder = Path('build_release_zip.py').read_text(encoding='utf-8')
        for pattern in ('*.zip', '*.7z', '*.tar', '*.tgz', '*.gz', '*.bz2', '*.xz', '*.whl'):
            self.assertIn(pattern, gitignore)
        for suffix in ("'.zip'", "'.7z'", "'.tar'", "'.tgz'", "'.gz'", "'.bz2'", "'.xz'", "'.whl'"):
            self.assertIn(suffix, builder)

    def test_gitignore_and_release_rules_exclude_test_logs(self):
        gitignore = Path('.gitignore').read_text(encoding='utf-8')
        builder = Path('build_release_zip.py').read_text(encoding='utf-8')
        for pattern in ('*.log', '*.out', '*.err', '*.trace', '*.prof', '*.pid', '*.lock', '.coverage.*', 'test_full_log*.txt', 'test_fail_index*.txt', 'test_errors*.txt', 'test_failures*.txt', 'bundle_*.txt'):
            self.assertIn(pattern, gitignore)
        for suffix in ("'.log'", "'.out'", "'.err'", "'.trace'", "'.prof'", "'.pid'", "'.lock'"):
            self.assertIn(suffix, builder)
        for pattern in ("'.coverage.*'", "'test_full_log*.txt'", "'test_fail_index*.txt'", "'test_errors*.txt'", "'test_failures*.txt'", "'bundle_*.txt'"):
            self.assertIn(pattern, builder)

    def test_gitignore_keeps_mypy_ini_trackable(self):
        content = Path('.gitignore').read_text(encoding='utf-8')
        self.assertIn('tategakiXTC_gui_studio.ini', content)
        self.assertNotIn('\n*.ini\n', f'\n{content}\n')

    def test_coverage_report_is_not_packaged(self):
        self.assertFalse(Path('coverage-report.txt').exists())

    def test_gitignore_covers_coverage_artifacts(self):
        content = Path('.gitignore').read_text(encoding='utf-8')
        self.assertIn('.coverage', content)
        self.assertIn('coverage.xml', content)
        self.assertIn('htmlcov/', content)
        self.assertIn('coverage-report.txt', content)
        self.assertIn('.coverage.*', content)

    def test_gitignore_covers_parallel_test_helper_outputs(self):
        content = Path('.gitignore').read_text(encoding='utf-8')
        builder = Path('build_release_zip.py').read_text(encoding='utf-8')
        self.assertIn('pt_*.log', content)
        self.assertIn('pt_*.exit', content)
        self.assertIn('pt*.log', content)
        self.assertIn('pt*.exit', content)
        self.assertIn("'pt_*.log'", builder)
        self.assertIn("'pt_*.exit'", builder)
        self.assertIn("'pt*.log'", builder)
        self.assertIn("'pt*.exit'", builder)

    def test_gitignore_covers_local_env_and_editor_noise(self):
        content = Path('.gitignore').read_text(encoding='utf-8')
        self.assertIn('.venv/', content)
        self.assertIn('venv/', content)
        self.assertIn('.tox/', content)
        self.assertIn('.nox/', content)
        self.assertIn('.idea/', content)
        self.assertIn('.vscode/', content)


    def test_coveragerc_targets_split_modules_too(self):
        content = Path('.coveragerc').read_text(encoding='utf-8')
        self.assertIn('build_release_zip', content)
        self.assertIn('tategakiXTC_release_metadata', content)
        self.assertIn('tategakiXTC_gui_core', content)
        self.assertIn('tategakiXTC_numpy_helper', content)
        self.assertIn('tategakiXTC_gui_layouts', content)
        self.assertIn('tategakiXTC_gui_preview_controller', content)
        self.assertIn('tategakiXTC_gui_results_controller', content)
        self.assertIn('tategakiXTC_gui_settings_controller', content)
        self.assertIn('tategakiXTC_gui_studio', content)
        self.assertIn('tategakiXTC_gui_studio_logic', content)
        self.assertIn('tategakiXTC_gui_studio_startup', content)
        self.assertIn('tategakiXTC_gui_studio_constants', content)
        self.assertIn('tategakiXTC_gui_studio_xtc_io', content)
        self.assertIn('tategakiXTC_gui_studio_widgets', content)
        self.assertIn('tategakiXTC_gui_studio_worker', content)
        self.assertIn('tategakiXTC_gui_studio_runtime', content)
        self.assertIn('tategakiXTC_gui_studio_desktop', content)
        self.assertIn('tategakiXTC_gui_studio_ui_helpers', content)
        self.assertIn('tategakiXTC_gui_studio_dialog_helpers', content)
        self.assertIn('tategakiXTC_gui_studio_preview_helpers', content)
        self.assertIn('tategakiXTC_gui_studio_path_helpers', content)
        self.assertIn('tategakiXTC_gui_studio_view_helpers', content)
        self.assertIn('tategakiXTC_gui_studio_settings_helpers', content)
        self.assertIn('tategakiXTC_gui_widget_factory', content)
        self.assertIn('tategakiXTC_worker_logic', content)
        self.assertIn('branch = True', content)

    def test_epub_runs_is_module_level_pure_helper(self):
        epub = Path('tategakiXTC_gui_core_epub.py').read_text(encoding='utf-8')
        self.assertIn('def _epub_runs(', epub)
        self.assertIn('_append_text_run(', epub)
        self.assertIn('bold=bool(bold)', epub)
        self.assertIn('code=bool(code)', epub)
        self.assertIn('ruby=ruby', epub)


    def test_epub_preview_uses_page_created_callback_for_early_limit(self):
        content = Path('tategakiXTC_gui_core_renderer.py').read_text(encoding='utf-8')
        self.assertIn('page_created_cb=_collect_page', content)
        self.assertIn('store_page_entries=False', content)
        self.assertIn('raise _PreviewPageLimitReached()', content)
        self.assertIn('def _collect_page(entry: PageEntry)', content)

    def test_vertical_dot_leader_is_drawn_without_font_vertical_glyph_dependency(self):
        content = (Path('tategakiXTC_gui_core.py').read_text(encoding='utf-8') + '\n' + Path('tategakiXTC_gui_core_renderer.py').read_text(encoding='utf-8'))
        self.assertIn('VERTICAL_DOT_LEADER_THREE_CHARS', content)
        for dot_char in ('…', '⋯', '︙'):
            self.assertIn(dot_char, content)
        self.assertIn('def draw_vertical_dot_leader', content)
        self.assertIn('draw.ellipse', content)
        self.assertIn('if char in VERTICAL_DOT_LEADER_CHARS:', content)

    def test_widgets_import_qrect_for_device_preview_paint_info_rect(self):
        content = Path('tategakiXTC_gui_studio_widgets.py').read_text(encoding='utf-8')
        self.assertIn('QRect, QRectF', content)
        self.assertIn('info_rect = QRect(', content)


    def test_release_required_app_code_files_cover_root_tategaki_modules(self):
        import build_release_zip as builder

        root_modules = {
            candidate.name
            for candidate in Path('.').glob('tategakiXTC*.py')
            if candidate.is_file()
        }
        tracked_modules = set(builder.REQUIRED_PROJECT_APP_CODE_FILES)

        self.assertEqual(set(), root_modules - tracked_modules)
        self.assertEqual(set(), tracked_modules - root_modules)
        self.assertEqual(
            len(builder.REQUIRED_PROJECT_APP_CODE_FILES),
            len(tracked_modules),
        )

    def test_tooling_targets_all_release_app_code_files(self):
        import build_release_zip as builder

        mypy_ini = Path('mypy.ini').read_text(encoding='utf-8')
        coveragerc = Path('.coveragerc').read_text(encoding='utf-8')

        for relative in builder.REQUIRED_PROJECT_APP_CODE_FILES:
            with self.subTest(relative=relative):
                self.assertIn(relative, mypy_ini)
                self.assertIn(Path(relative).stem, coveragerc)


    def test_settings_save_payload_records_schema_metadata(self):
        content = Path('tategakiXTC_gui_settings_controller.py').read_text(encoding='utf-8')
        constants = Path('tategakiXTC_gui_studio_constants.py').read_text(encoding='utf-8')
        studio = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        self.assertIn('SETTINGS_SCHEMA_VERSION = 2', constants)
        self.assertIn("payload['settings_schema_version'] = studio_constants.SETTINGS_SCHEMA_VERSION", content)
        self.assertIn("payload['last_app_version'] = studio_constants.APP_VERSION", content)
        self.assertIn("self.settings_store.setValue('settings_schema_version', SETTINGS_SCHEMA_VERSION)", studio)
        self.assertIn("self.settings_store.setValue('last_app_version', APP_VERSION)", studio)

    def test_default_render_settings_are_shared_by_settings_helpers(self):
        constants = Path('tategakiXTC_gui_studio_constants.py').read_text(encoding='utf-8')
        controller = Path('tategakiXTC_gui_settings_controller.py').read_text(encoding='utf-8')
        studio = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        self.assertIn('DEFAULT_RENDER_SETTINGS', constants)
        self.assertIn('_DEFAULT_RENDER_SETTINGS = studio_constants.DEFAULT_RENDER_SETTINGS', controller)
        self.assertIn('defaults = DEFAULT_RENDER_SETTINGS', studio)

    def test_help_text_does_not_expose_internal_sweep_numbers(self):
        studio = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        layouts = Path('tategakiXTC_gui_layouts.py').read_text(encoding='utf-8')
        self.assertNotIn('実寸補正: sweep361', studio)
        self.assertNotIn('実寸補正: sweep361', layouts)
        self.assertNotIn('試作版では、機種選択', studio)

    def test_gui_logging_has_session_log_retention_policy(self):
        studio = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        helper = Path('tategakiXTC_gui_studio_logging.py').read_text(encoding='utf-8')
        self.assertIn('DEFAULT_LOG_RETENTION_DAYS = 30', helper)
        self.assertIn('DEFAULT_LOG_RETENTION_MAX_FILES = 50', helper)
        self.assertIn('def cleanup_old_session_logs(', helper)
        self.assertIn('active_log_path', helper)
        self.assertIn('cleanup_old_session_logs as _cleanup_old_session_logs', studio)
        self.assertIn('_cleanup_old_session_logs(active_log_dir, active_log_path=session_log_path)', studio)

if __name__ == '__main__':
    unittest.main()

