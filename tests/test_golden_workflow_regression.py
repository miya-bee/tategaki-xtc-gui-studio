import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.golden_regression_tools import describe_golden_case_scope, describe_reference_font_action_hint, describe_reference_font_next_check, describe_reference_font_ready_hint, describe_reference_font_skip_hint, describe_reference_font_status, describe_reference_font_status_line, reference_font_status_code, describe_skipped_case_names, describe_skipped_case_summary, describe_stale_case_names, describe_stale_case_summary, format_golden_check_command, format_golden_check_command_block, format_golden_list_stale_command, format_golden_list_stale_command_block, format_golden_update_command, format_golden_update_command_block, normalize_case_names, should_update_goldens, skipped_case_names, stale_case_names, stale_case_results, strip_update_flag


class GoldenWorkflowRegressionTests(unittest.TestCase):
    def test_should_update_goldens_accepts_env(self):
        self.assertTrue(should_update_goldens(argv=['prog'], environ={'TATEGAKI_UPDATE_GOLDEN': '1'}))
        self.assertFalse(should_update_goldens(argv=['prog'], environ={}))

    def test_strip_update_flag_removes_custom_arg(self):
        values = strip_update_flag(['python', '--update-golden', '-m', 'unittest'])
        self.assertNotIn('--update-golden', values)
        self.assertEqual(values, ['python', '-m', 'unittest'])


    def test_normalize_case_names_dedupes_and_preserves_order(self):
        values = normalize_case_names(['page_heading_spacing', 'glyph_ichi', 'page_heading_spacing'])
        self.assertEqual(values, ['page_heading_spacing', 'glyph_ichi'])

    def test_normalize_case_names_rejects_unknown_case(self):
        with self.assertRaisesRegex(KeyError, 'missing_case'):
            normalize_case_names(['glyph_ichi', 'missing_case'])


    def test_golden_regression_tools_reexports_case_specs_for_image_tests(self):
        from tests import golden_regression_tools as tools
        from tests.golden_case_registry import CASE_SPECS as registry_case_specs

        self.assertIs(tools.CASE_SPECS, registry_case_specs)
        self.assertIn('glyph_ichi', tools.CASE_SPECS)


    def test_format_golden_update_command_keeps_case_scope(self):
        command = format_golden_update_command(['page_heading_spacing', 'glyph_ichi', 'page_heading_spacing'])
        self.assertEqual(
            command,
            r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --update --case page_heading_spacing --case glyph_ichi',
        )

    def test_format_golden_update_command_without_case_updates_all(self):
        self.assertEqual(format_golden_update_command([]), r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --update')
        self.assertEqual(format_golden_update_command(None), r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --update')

    def test_format_golden_check_command_keeps_case_scope(self):
        command = format_golden_check_command(['page_heading_spacing', 'glyph_ichi', 'page_heading_spacing'])
        self.assertEqual(
            command,
            r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --check --case page_heading_spacing --case glyph_ichi',
        )

    def test_format_golden_check_command_without_case_checks_all(self):
        self.assertEqual(format_golden_check_command([]), r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --check')
        self.assertEqual(format_golden_check_command(None), r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --check')



    def test_format_golden_command_blocks_are_copyable_for_windows_cmd(self):
        self.assertEqual(
            format_golden_check_command_block(['glyph_ichi', 'glyph_chouon']),
            r'.venv\Scripts\python.exe -B ^' '\n'
            r'  tests\generate_golden_images.py ^' '\n'
            '  --check ^\n'
            '  --case glyph_ichi ^\n'
            '  --case glyph_chouon',
        )
        self.assertEqual(
            format_golden_update_command_block([]),
            r'.venv\Scripts\python.exe -B ^' '\n'
            r'  tests\generate_golden_images.py ^' '\n'
            '  --update',
        )

    def test_format_golden_command_blocks_use_project_venv_python_for_user_smoke(self):
        text = format_golden_check_command_block(['glyph_ichi'])
        self.assertTrue(text.startswith(r'.venv\Scripts\python.exe -B ^'))
        self.assertNotIn('python -B ^', text)

    def test_format_golden_inline_commands_use_project_venv_python_for_user_smoke(self):
        text = format_golden_check_command(['glyph_ichi'])
        self.assertTrue(text.startswith(r'.venv\Scripts\python.exe -B '))
        self.assertIn(r'tests\generate_golden_images.py', text)
        self.assertNotIn(r'python tests\generate_golden_images.py', text)
        self.assertNotIn(r'\\', text)
        self.assertNotIn('^', text)

    def test_format_golden_list_stale_command_keeps_case_scope(self):
        command = format_golden_list_stale_command(['glyph_ichi', 'glyph_chouon', 'glyph_ichi'])
        self.assertEqual(
            command,
            r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --list-stale --case glyph_ichi --case glyph_chouon',
        )

    def test_format_golden_list_stale_command_block_is_copyable_for_windows_cmd(self):
        self.assertEqual(
            format_golden_list_stale_command_block(['glyph_ichi', 'glyph_chouon']),
            r'.venv\Scripts\python.exe -B ^' '\n'
            r'  tests\generate_golden_images.py ^' '\n'
            '  --list-stale ^\n'
            '  --case glyph_ichi ^\n'
            '  --case glyph_chouon',
        )

    def test_golden_images_readme_marks_commands_as_windows_cmd_examples(self):
        text = (ROOT / "tests" / "golden_images" / "README.md").read_text(encoding="utf-8")
        self.assertIn("```bat\n.venv\\Scripts\\python.exe -B ^\n  tests\\generate_golden_images.py ^\n  --check\n```", text)
        self.assertNotIn("```bash\n.venv\\Scripts\\python.exe -B", text)

    def test_golden_images_readme_documents_font_status_and_list_stale_smoke_commands(self):
        text = (ROOT / "tests" / "golden_images" / "README.md").read_text(encoding="utf-8")
        self.assertIn("```bat\n.venv\\Scripts\\python.exe -B ^\n  tests\\generate_golden_images.py ^\n  --font-status\n```", text)
        self.assertIn("```bat\n.venv\\Scripts\\python.exe -B ^\n  tests\\generate_golden_images.py ^\n  --list-stale\n```", text)

    def test_golden_images_readme_keeps_long_case_examples_multiline_for_cmd(self):
        text = (ROOT / "tests" / "golden_images" / "README.md").read_text(encoding="utf-8")
        self.assertIn("  --check ^\n  --case page_compound_layout ^\n  --case page_heading_spacing", text)
        self.assertNotIn("--check --case page_compound_layout --case page_heading_spacing", text)

    def test_golden_images_readme_separates_local_cmd_examples_from_ci_workflow(self):
        text = (ROOT / "tests" / "golden_images" / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "python-tests.yml").read_text(encoding="utf-8")
        self.assertIn("## CI 上の確認", text)
        self.assertIn("GitHub Actions", text)
        self.assertIn(r"python tests/generate_golden_images.py --check", workflow)
        self.assertNotIn(r"python tests/generate_golden_images.py", text)

    def test_golden_images_readme_documents_reference_font_ready_and_missing_states(self):
        text = (ROOT / "tests" / "golden_images" / "README.md").read_text(encoding="utf-8")
        self.assertIn("## 基準フォントの配置", text)
        self.assertIn("Font/NotoSansJP-Regular.ttf", text)
        self.assertIn("状態コードが `ready`", text)
        self.assertIn("`missing`", text)
        self.assertIn("`--font-status` と `--list-stale`", text)


    def test_describe_reference_font_next_check_uses_case_scope(self):
        text = describe_reference_font_next_check(['glyph_ichi'])
        self.assertIn('実差分確認コマンド:', text)
        self.assertIn('--list-stale ^', text)
        self.assertIn('--case glyph_ichi', text)


    def test_describe_reference_font_next_check_labels_missing_font_as_after_setup(self):
        from tests import golden_regression_tools as tools

        original_has_font = tools.has_bundled_reference_font
        try:
            tools.has_bundled_reference_font = lambda: False
            missing_text = tools.describe_reference_font_next_check(['glyph_ichi'])
            tools.has_bundled_reference_font = lambda: True
            ready_text = tools.describe_reference_font_next_check(['glyph_ichi'])
        finally:
            tools.has_bundled_reference_font = original_has_font

        self.assertIn('フォント配置後の実差分確認コマンド:', missing_text)
        self.assertIn('--list-stale ^', missing_text)
        self.assertIn('--case glyph_ichi', missing_text)
        self.assertTrue(ready_text.startswith('実差分確認コマンド:'))

    def test_describe_golden_case_scope_shows_selected_cases(self):
        self.assertEqual(
            describe_golden_case_scope(['page_heading_spacing', 'glyph_ichi', 'page_heading_spacing']),
            '対象ケース: page_heading_spacing, glyph_ichi',
        )

    def test_describe_golden_case_scope_shows_all_case_count(self):
        label = describe_golden_case_scope([])
        self.assertRegex(label, r'^対象ケース: 全ケース \(\d+件\)$')


    def test_describe_stale_case_summary_reports_count(self):
        self.assertEqual(describe_stale_case_summary(['glyph_ichi', 'glyph_chouon']), '差分ケース数: 2件')
        self.assertEqual(describe_stale_case_summary([]), '差分ケース数: 0件')

    def test_describe_stale_case_names_lists_names_or_none(self):
        self.assertEqual(describe_stale_case_names(['glyph_ichi', 'glyph_chouon']), '差分ケース: glyph_ichi, glyph_chouon')
        self.assertEqual(describe_stale_case_names([]), '差分ケース: なし')

    def test_describe_skipped_case_summary_reports_count(self):
        self.assertEqual(describe_skipped_case_summary(['glyph_ichi', 'glyph_chouon']), '比較省略ケース数: 2件')
        self.assertEqual(describe_skipped_case_summary([]), '比較省略ケース数: 0件')

    def test_describe_skipped_case_names_lists_names_or_none(self):
        self.assertEqual(describe_skipped_case_names(['glyph_ichi', 'glyph_chouon']), '比較省略ケース: glyph_ichi, glyph_chouon')
        self.assertEqual(describe_skipped_case_names([]), '比較省略ケース: なし')

    def test_describe_reference_font_skip_hint_explains_next_action(self):
        self.assertIn('Font/NotoSansJP-Regular.ttf', describe_reference_font_skip_hint())

    def test_describe_reference_font_ready_hint_explains_ready_state(self):
        self.assertIn('実差分確認を実行できます', describe_reference_font_ready_hint())

    def test_describe_reference_font_action_hint_switches_by_font_state(self):
        from tests import golden_regression_tools as tools

        original_has_font = tools.has_bundled_reference_font
        try:
            tools.has_bundled_reference_font = lambda: True
            self.assertIn('配置済み', tools.describe_reference_font_action_hint())
            tools.has_bundled_reference_font = lambda: False
            self.assertIn('配置してから', tools.describe_reference_font_action_hint())
        finally:
            tools.has_bundled_reference_font = original_has_font

    def test_reference_font_status_code_is_grep_friendly(self):
        from tests import golden_regression_tools as tools

        original_has_font = tools.has_bundled_reference_font
        try:
            tools.has_bundled_reference_font = lambda: True
            self.assertEqual(tools.reference_font_status_code(), 'ready')
            tools.has_bundled_reference_font = lambda: False
            self.assertEqual(tools.reference_font_status_code(), 'missing')
        finally:
            tools.has_bundled_reference_font = original_has_font

    def test_describe_reference_font_status_line_is_grep_friendly(self):
        text = describe_reference_font_status_line()
        self.assertRegex(text, r'^基準フォント状態コード: (ready|missing)$')

    def test_describe_reference_font_status_reports_path_and_availability(self):
        text = describe_reference_font_status()
        self.assertIn('基準フォント: Font/NotoSansJP-Regular.ttf', text)
        self.assertRegex(text, r'状態: (あり|なし)')
        self.assertRegex(text, r'状態コード: (ready|missing)')
        self.assertRegex(text, r'実差分確認: (可能|不可)')

    def test_generate_golden_images_font_status_does_not_render_cases(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        original_describe_reference_font_status = script.describe_reference_font_status
        original_describe_reference_font_action_hint = script.describe_reference_font_action_hint
        original_describe_reference_font_next_check = script.describe_reference_font_next_check
        try:
            sys.argv = ['generate_golden_images.py', '--font-status']

            def fail_if_checked(case_names):
                raise AssertionError('font-status should not check or render golden cases')

            script.check_cases = fail_if_checked
            script.describe_reference_font_status = lambda: '基準フォント: Font/NotoSansJP-Regular.ttf\n状態: なし\n実差分確認: 不可'
            script.describe_reference_font_action_hint = lambda: '実差分確認には Font/NotoSansJP-Regular.ttf を配置してから再実行してください。'
            script.describe_reference_font_next_check = lambda case_names: 'フォント配置後の実差分確認コマンド:\n' + format_golden_list_stale_command_block(case_names)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases
            script.describe_reference_font_status = original_describe_reference_font_status
            script.describe_reference_font_action_hint = original_describe_reference_font_action_hint
            script.describe_reference_font_next_check = original_describe_reference_font_next_check

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('対象ケース: 全ケース', text)
        self.assertIn('基準フォント: Font/NotoSansJP-Regular.ttf', text)
        self.assertIn('状態: なし', text)
        self.assertIn('実差分確認: 不可', text)
        self.assertIn('実差分確認には Font/NotoSansJP-Regular.ttf', text)
        self.assertIn('実差分確認コマンド:', text)
        self.assertIn('--list-stale', text)


    def test_generate_golden_images_font_status_keeps_case_scope_in_next_command(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        original_describe_reference_font_status = script.describe_reference_font_status
        original_describe_reference_font_action_hint = script.describe_reference_font_action_hint
        original_describe_reference_font_next_check = script.describe_reference_font_next_check
        try:
            sys.argv = ['generate_golden_images.py', '--font-status', '--case', 'glyph_ichi']

            def fail_if_checked(case_names):
                raise AssertionError('font-status should not check or render golden cases')

            script.check_cases = fail_if_checked
            script.describe_reference_font_status = lambda: '基準フォント: Font/NotoSansJP-Regular.ttf\n状態: なし\n実差分確認: 不可'
            script.describe_reference_font_action_hint = lambda: '実差分確認には Font/NotoSansJP-Regular.ttf を配置してから再実行してください。'
            script.describe_reference_font_next_check = lambda case_names: 'フォント配置後の実差分確認コマンド:\n' + format_golden_list_stale_command_block(case_names)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases
            script.describe_reference_font_status = original_describe_reference_font_status
            script.describe_reference_font_action_hint = original_describe_reference_font_action_hint
            script.describe_reference_font_next_check = original_describe_reference_font_next_check

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('対象ケース: glyph_ichi', text)
        self.assertIn('実差分確認コマンド:', text)
        self.assertIn('--list-stale ^', text)
        self.assertIn('--case glyph_ichi', text)


    def test_skipped_case_names_reports_only_skipped_results(self):
        results = [
            {'name': 'glyph_ichi', 'stale': True, 'skipped': False},
            {'name': 'page_heading_spacing', 'stale': False, 'skipped': True},
            {'name': 'page_compound_layout', 'stale': True, 'skipped': True},
        ]
        self.assertEqual(skipped_case_names(results), ['page_heading_spacing', 'page_compound_layout'])

    def test_stale_case_names_omits_clean_and_skipped_results(self):
        results = [
            {'name': 'glyph_ichi', 'stale': True, 'skipped': False},
            {'name': 'page_heading_spacing', 'stale': False, 'skipped': False},
            {'name': 'page_compound_layout', 'stale': True, 'skipped': True},
        ]
        self.assertEqual(stale_case_names(results), ['glyph_ichi'])

    def test_stale_case_results_omits_skipped_results(self):
        results = [
            {'name': 'glyph_ichi', 'stale': True, 'skipped': False},
            {'name': 'page_heading_spacing', 'stale': False, 'skipped': False},
            {'name': 'page_compound_layout', 'stale': True, 'skipped': True},
        ]
        actionable = stale_case_results(results)
        self.assertEqual([result['name'] for result in actionable], ['glyph_ichi'])

    def test_compare_case_skips_before_render_without_bundled_reference_font(self):
        from tests import golden_regression_tools as tools

        original_has_font = tools._has_bundled_reference_font
        original_render = tools._render_case_png_bytes
        try:
            tools._has_bundled_reference_font = lambda: False

            def fail_if_rendered(name):
                raise AssertionError(f'render should not run for skipped golden case: {name}')

            tools._render_case_png_bytes = fail_if_rendered
            result = tools.compare_case('glyph_ichi')
        finally:
            tools._has_bundled_reference_font = original_has_font
            tools._render_case_png_bytes = original_render

        self.assertTrue(result['skipped'])
        self.assertFalse(result['stale'])
        self.assertIsNone(result['actual'])
        self.assertEqual(result['thresholds']['threshold_ratio'], 0.0015)

    def test_generate_golden_images_list_stale_reports_font_status_code_line(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        original_status_line = script.describe_reference_font_status_line
        try:
            sys.argv = ['generate_golden_images.py', '--list-stale', '--case', 'glyph_ichi']
            script.check_cases = lambda case_names: [
                {'name': 'glyph_ichi', 'stale': False, 'skipped': False},
            ]
            script.describe_reference_font_status_line = lambda: '基準フォント状態コード: ready'
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases
            script.describe_reference_font_status_line = original_status_line

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('対象ケース: glyph_ichi', text)
        self.assertIn('基準フォント状態コード: ready', text)
        self.assertIn('差分ケースはありません。', text)

    def test_generate_golden_images_list_stale_reports_only_matching_stale_cases(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--list-stale', '--case', 'glyph_ichi']
            script.check_cases = lambda case_names: [
                {'name': 'glyph_ichi', 'stale': True, 'skipped': False},
                {'name': 'page_heading_spacing', 'stale': False, 'skipped': False},
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        self.assertEqual(code, 1)
        self.assertIn('対象ケース: glyph_ichi', out.getvalue())
        self.assertIn('差分ケース数: 1件', out.getvalue())
        self.assertIn('差分ケース: glyph_ichi', out.getvalue())
        self.assertIn('glyph_ichi', out.getvalue())
        self.assertIn('確認するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --check --case glyph_ichi', out.getvalue())
        self.assertIn('確認コマンド:', out.getvalue())
        self.assertIn('  tests\\generate_golden_images.py ^', out.getvalue())
        self.assertIn('更新するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --update --case glyph_ichi', out.getvalue())
        self.assertIn('更新コマンド:', out.getvalue())
        self.assertNotIn('page_heading_spacing', out.getvalue())


    def test_generate_golden_images_list_stale_prints_recheck_before_update_hint(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--list-stale']
            script.check_cases = lambda case_names: [
                {'name': 'glyph_ichi', 'stale': True, 'skipped': False},
                {'name': 'glyph_chouon', 'stale': True, 'skipped': False},
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn('差分ケース数: 2件', text)
        self.assertIn('差分ケース: glyph_ichi, glyph_chouon', text)
        self.assertLess(text.index('確認するには:'), text.index('更新するには:'))
        self.assertIn(
            '確認するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --check --case glyph_ichi --case glyph_chouon',
            text,
        )
        self.assertIn(
            '更新するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --update --case glyph_ichi --case glyph_chouon',
            text,
        )

    def test_generate_golden_images_list_stale_reports_partial_skips_separately(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--list-stale']
            script.check_cases = lambda case_names: [
                {'name': 'glyph_ichi', 'stale': True, 'skipped': True, 'reason': 'skip'},
                {'name': 'glyph_chouon', 'stale': True, 'skipped': False},
                {'name': 'page_heading_spacing', 'stale': False, 'skipped': False},
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn('比較省略ケース数: 1件', text)
        self.assertIn('比較省略ケース: glyph_ichi', text)
        self.assertIn('差分ケース数: 1件', text)
        self.assertIn('差分ケース: glyph_chouon', text)
        self.assertIn('更新するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --update --case glyph_chouon', text)
        self.assertNotIn('--case glyph_ichi', text.split('更新するには:', 1)[1])

    def test_generate_golden_images_list_stale_reports_all_skipped_case_names_and_hint(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--list-stale']
            script.check_cases = lambda case_names: [
                {'name': 'glyph_ichi', 'stale': False, 'skipped': True, 'reason': 'skip'},
                {'name': 'glyph_chouon', 'stale': False, 'skipped': True, 'reason': 'skip'},
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('比較省略ケース数: 2件', text)
        self.assertIn('比較省略ケース: glyph_ichi, glyph_chouon', text)
        self.assertIn('同梱基準フォントが無いためゴールデン比較を省略しました。', text)
        self.assertIn('Font/NotoSansJP-Regular.ttf', text)
        self.assertNotIn('更新するには:', text)

    def test_generate_golden_images_check_mode_suggests_only_actual_stale_cases(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--check']
            script.check_cases = lambda case_names: [
                {
                    'name': 'glyph_ichi',
                    'stale': True,
                    'skipped': False,
                    'missing': True,
                    'size_matches': False,
                },
                {'name': 'page_heading_spacing', 'stale': False, 'skipped': False},
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn('対象ケース: 全ケース', text)
        self.assertIn('glyph_ichi: ゴールデン画像がありません', text)
        self.assertIn('更新するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --update --case glyph_ichi', text)
        self.assertNotIn('--case page_heading_spacing', text)


    def test_generate_golden_images_check_mode_prints_copyable_update_command_block(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--check']
            script.check_cases = lambda case_names: [
                {
                    'name': 'glyph_ichi',
                    'stale': True,
                    'skipped': True,
                    'reason': 'skip',
                    'missing': False,
                    'size_matches': True,
                },
                {
                    'name': 'glyph_chouon',
                    'stale': True,
                    'skipped': False,
                    'missing': True,
                    'size_matches': False,
                },
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn('更新コマンド:', text)
        self.assertIn('  --update ^', text)
        self.assertIn('  --case glyph_chouon', text)
        update_block = text.split('更新コマンド:', 1)[1]
        self.assertNotIn('--case glyph_ichi', update_block)

    def test_generate_golden_images_check_mode_omits_skipped_stale_from_update_hint(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--check']
            script.check_cases = lambda case_names: [
                {
                    'name': 'glyph_ichi',
                    'stale': True,
                    'skipped': True,
                    'reason': 'skip',
                    'missing': False,
                    'size_matches': True,
                },
                {
                    'name': 'glyph_chouon',
                    'stale': True,
                    'skipped': False,
                    'missing': True,
                    'size_matches': False,
                },
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn('更新するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --update --case glyph_chouon', text)
        self.assertNotIn('--case glyph_ichi', text)


    def test_generate_golden_images_check_mode_does_not_suggest_update_all_for_only_skipped_stale(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--check']
            script.check_cases = lambda case_names: [
                {
                    'name': 'glyph_ichi',
                    'stale': True,
                    'skipped': True,
                    'reason': 'skip',
                    'missing': False,
                    'size_matches': True,
                },
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('同梱基準フォントが無いためゴールデン比較を省略しました。', text)
        self.assertNotIn('更新するには:', text)
        self.assertNotIn(r'.venv\Scripts\python.exe -B tests\generate_golden_images.py --update', text)

    def test_generate_golden_images_check_mode_reports_partial_skips_when_remaining_clean(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--check']
            script.check_cases = lambda case_names: [
                {
                    'name': 'glyph_ichi',
                    'stale': True,
                    'skipped': True,
                    'reason': 'skip',
                    'missing': False,
                    'size_matches': True,
                },
                {'name': 'page_heading_spacing', 'stale': False, 'skipped': False},
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('比較省略ケース数: 1件', text)
        self.assertIn('比較省略ケース: glyph_ichi', text)
        self.assertIn('比較可能なゴールデン画像は最新です。', text)
        self.assertNotIn('更新するには:', text)

    def test_generate_golden_images_update_mode_reports_only_skipped_without_unneeded_hint(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        try:
            sys.argv = ['generate_golden_images.py', '--update', '--case', 'glyph_ichi']
            script.check_cases = lambda case_names: [
                {
                    'name': 'glyph_ichi',
                    'stale': True,
                    'skipped': True,
                    'reason': 'skip',
                    'actual': None,
                },
            ]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('対象ケース: glyph_ichi', text)
        self.assertIn('同梱基準フォントが無いためゴールデン比較を省略しました。', text)
        self.assertNotIn('更新の必要はありません。', text)
        self.assertNotIn('updated:', text)

    def test_generate_golden_images_update_mode_reports_partial_skips_and_updates_actionable_cases(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        original_update_stale_case_results = script.update_stale_case_results
        seen = []
        try:
            sys.argv = ['generate_golden_images.py', '--update']
            results = [
                {'name': 'glyph_ichi', 'stale': True, 'skipped': True, 'reason': 'skip', 'actual': None},
                {'name': 'glyph_chouon', 'stale': True, 'skipped': False, 'actual': object()},
            ]
            script.check_cases = lambda case_names: results

            def fake_update_stale_case_results(received):
                seen.extend(received)
                return [Path('/tmp/glyph_chouon.png')]

            script.update_stale_case_results = fake_update_stale_case_results
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases
            script.update_stale_case_results = original_update_stale_case_results

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertEqual(seen, results)
        self.assertIn('比較省略ケース数: 1件', text)
        self.assertIn('比較省略ケース: glyph_ichi', text)
        self.assertIn(f'updated: {Path("/tmp/glyph_chouon.png")}', text)
        self.assertIn('確認するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --check --case glyph_chouon', text)
        self.assertIn('確認コマンド:', text)
        self.assertIn('  --check ^', text)
        self.assertIn('  --case glyph_chouon', text)

    def test_generate_golden_images_update_mode_prints_copyable_check_command_block_after_update(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        original_update_stale_case_results = script.update_stale_case_results
        try:
            sys.argv = ['generate_golden_images.py', '--update', '--case', 'glyph_chouon']
            results = [
                {'name': 'glyph_chouon', 'stale': True, 'skipped': False, 'actual': object()},
            ]
            script.check_cases = lambda case_names: results
            script.update_stale_case_results = lambda received: [Path('/tmp/glyph_chouon.png')]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases
            script.update_stale_case_results = original_update_stale_case_results

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('確認するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --check --case glyph_chouon', text)
        self.assertIn('確認コマンド:', text)
        self.assertIn('  --check ^', text)
        self.assertIn('  --case glyph_chouon', text)


    def test_generate_golden_images_update_mode_check_hint_targets_only_updated_cases(self):
        from tests import generate_golden_images as script

        original_argv = sys.argv
        original_check_cases = script.check_cases
        original_update_stale_case_results = script.update_stale_case_results
        try:
            sys.argv = ['generate_golden_images.py', '--update']
            results = [
                {'name': 'glyph_ichi', 'stale': True, 'skipped': True, 'reason': 'skip', 'actual': None},
                {'name': 'glyph_chouon', 'stale': True, 'skipped': False, 'actual': object()},
                {'name': 'page_heading_spacing', 'stale': False, 'skipped': False, 'actual': object()},
            ]
            script.check_cases = lambda case_names: results
            script.update_stale_case_results = lambda received: [Path('/tmp/glyph_chouon.png')]
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = script.main()
        finally:
            sys.argv = original_argv
            script.check_cases = original_check_cases
            script.update_stale_case_results = original_update_stale_case_results

        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn('確認するには: .venv\\Scripts\\python.exe -B tests\\generate_golden_images.py --check --case glyph_chouon', text)
        self.assertIn('確認コマンド:', text)
        self.assertIn('  --case glyph_chouon', text)
        check_block = text.split('確認コマンド:', 1)[1]
        self.assertNotIn('--case glyph_ichi', check_block)
        self.assertNotIn('--case page_heading_spacing', check_block)


    def test_update_stale_case_results_ignores_skipped_results_without_actual_image(self):
        from tests import golden_regression_tools as tools

        original_save_golden = tools.save_golden
        saved = []
        try:
            def fake_save(name, actual):
                saved.append((name, actual))
                return Path(f'/tmp/{name}.png')

            tools.save_golden = fake_save
            updated = tools.update_stale_case_results([
                {'name': 'glyph_ichi', 'stale': True, 'skipped': True, 'actual': None},
                {'name': 'glyph_chouon', 'stale': True, 'skipped': False, 'actual': object()},
            ])
        finally:
            tools.save_golden = original_save_golden

        self.assertEqual([path.name for path in updated], ['glyph_chouon.png'])
        self.assertEqual([name for name, _actual in saved], ['glyph_chouon'])

    def test_update_stale_cases_ignores_skipped_results_without_actual_image(self):
        from tests import golden_regression_tools as tools

        original_check_cases = tools.check_cases
        original_save_golden = tools.save_golden
        saved = []
        try:
            tools.check_cases = lambda case_names=None: [
                {'name': 'glyph_ichi', 'stale': True, 'skipped': True, 'actual': None},
                {'name': 'glyph_chouon', 'stale': True, 'skipped': False, 'actual': object()},
            ]

            def fake_save(name, actual):
                saved.append((name, actual))
                return Path(f'/tmp/{name}.png')

            tools.save_golden = fake_save
            updated = tools.update_stale_cases(['glyph_ichi', 'glyph_chouon'])
        finally:
            tools.check_cases = original_check_cases
            tools.save_golden = original_save_golden

        self.assertEqual([path.name for path in updated], ['glyph_chouon.png'])
        self.assertEqual([name for name, _actual in saved], ['glyph_chouon'])

    def test_generate_golden_images_list_can_select_case(self):
        script = ROOT / 'tests' / 'generate_golden_images.py'
        proc = subprocess.run(
            [sys.executable, str(script), '--list', '--case', 'glyph_ichi'],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.strip().splitlines(), ['glyph_ichi'])

    def test_generate_golden_images_check_mode_reports_selected_scope(self):
        script = ROOT / 'tests' / 'generate_golden_images.py'
        proc = subprocess.run(
            [sys.executable, str(script), '--check', '--case', 'glyph_ichi'],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertIn(proc.returncode, {0, 1}, proc.stdout + proc.stderr)
        self.assertIn('対象ケース: glyph_ichi', proc.stdout)

    def test_generate_golden_images_check_mode_reports_clean_state(self):
        script = ROOT / 'tests' / 'generate_golden_images.py'
        proc = subprocess.run(
            [sys.executable, str(script), '--check'],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(
            'ゴールデン画像は最新です。' in proc.stdout
            or '同梱基準フォントが無いためゴールデン比較を省略しました。' in proc.stdout
        )

