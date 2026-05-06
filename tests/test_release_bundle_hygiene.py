import os
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path, PureWindowsPath
from unittest import mock

import build_release_zip as rel


class ReleaseBundleHygieneTests(unittest.TestCase):
    def _make_file_symlink_or_skip(self, target: Path, link: Path) -> None:
        try:
            os.symlink(target, link)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f'file symlink creation is not available: {exc}')

    def _required_release_file_payload(self, rel_path: str) -> str | bytes:
        if rel_path in rel.REQUIRED_PROJECT_PNG_IMAGE_FILES:
            return rel.PNG_SIGNATURE + b'release-test-placeholder'
        app_markers = rel.REQUIRED_APP_CONTENT_MARKERS.get(rel_path)
        if app_markers:
            return '\n'.join(app_markers) + '\n'
        batch_markers = rel.REQUIRED_BATCH_CONTENT_MARKERS.get(rel_path)
        if batch_markers:
            return '@echo off\n' + '\n'.join(f'echo {marker}' for marker in batch_markers) + '\n'
        requirements_markers = rel.REQUIRED_REQUIREMENTS_CONTENT_MARKERS.get(rel_path)
        if requirements_markers:
            return '\n'.join(requirements_markers) + '\n'
        document_markers = rel.REQUIRED_DOCUMENT_CONTENT_MARKERS.get(rel_path)
        if document_markers:
            return '\n'.join(document_markers) + '\n'
        tooling_markers = rel.REQUIRED_TOOLING_CONTENT_MARKERS.get(rel_path)
        if tooling_markers:
            return '\n'.join(tooling_markers) + '\n'
        gui_asset_markers = rel.REQUIRED_GUI_ASSET_CONTENT_MARKERS.get(rel_path)
        if gui_asset_markers:
            return '<svg viewBox="0 0 1 1"><path d="M0 0 L1 1"/></svg>\n'
        test_support_markers = rel.REQUIRED_TEST_SUPPORT_CONTENT_MARKERS.get(rel_path)
        if test_support_markers:
            return '\n'.join(test_support_markers) + '\n'
        fixture_markers = rel.REQUIRED_TEST_FIXTURE_CONTENT_MARKERS.get(rel_path)
        if fixture_markers:
            return '\n'.join(fixture_markers) + '\n'
        if rel_path in rel.REQUIRED_PROJECT_REGRESSION_TEST_FILES:
            return 'def test_required_release_placeholder():\n    pass\n'
        return rel_path

    def _write_required_project_release_files(self, root: Path, *, omit: set[str] | None = None) -> None:
        omit = set() if omit is None else set(omit)
        for rel_path in rel.REQUIRED_PROJECT_RELEASE_FILES:
            if rel_path in omit:
                continue
            path = root / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = self._required_release_file_payload(rel_path)
            if isinstance(payload, bytes):
                path.write_bytes(payload)
            else:
                path.write_text(payload, encoding='utf-8')

    def _write_required_project_release_zip_members(self, zf: zipfile.ZipFile, *, omit: set[str] | None = None) -> None:
        omit = set() if omit is None else set(omit)
        existing = set(zf.namelist())
        for rel_path in rel.REQUIRED_PROJECT_RELEASE_FILES:
            if rel_path not in omit and rel_path not in existing:
                zf.writestr(rel_path, self._required_release_file_payload(rel_path))
                existing.add(rel_path)

    def _zipinfo_raw_member(self, member_name: str) -> zipfile.ZipInfo:
        # zipfile.ZipInfo / ZipFile.writestr may normalize backslashes to POSIX
        # separators on Windows. These regression cases specifically require
        # a raw non-canonical member name inside the archive, so skip them when
        # the stdlib cannot preserve that fixture shape.
        if os.name == 'nt' and '\\' in member_name:
            self.skipTest('raw backslash zip member fixtures are normalized by zipfile on Windows')
        info = zipfile.ZipInfo('placeholder')
        info.filename = member_name
        return info

    def _writestr_raw_member(self, zf: zipfile.ZipFile, member_name: str, data: str | bytes) -> None:
        zf.writestr(self._zipinfo_raw_member(member_name), data)


    def test_python_gui_release_excludes_work_payload_web_trial_files(self):
        prohibited = set(rel.PROHIBITED_WEB_RELEASE_FILES)
        self.assertIn('requirements-web.txt', prohibited)
        self.assertIn('tategakiXTC_localweb.py', prohibited)
        self.assertIn('templates/localweb_index.html', prohibited)
        for rel_path in prohibited:
            self.assertNotIn(rel_path, rel.REQUIRED_PROJECT_RELEASE_FILES)

    def test_should_include_path_excludes_generated_and_work_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            keep = root / 'README.md'
            keep.write_text('ok', encoding='utf-8')
            ignore_cases = [
                root / 'logs' / 'app.log',
                root / '__pycache__' / 'app.cpython-313.pyc',
                root / '.pytest_cache' / 'v' / 'cache' / 'nodeids',
                root / '.git' / 'HEAD',
                root / '__MACOSX' / '._README.md',
                root / '.venv' / 'Lib' / 'site-packages' / 'demo.txt',
                root / 'venv' / 'Lib' / 'site-packages' / 'demo.txt',
                root / '.idea' / 'workspace.xml',
                root / '.vscode' / 'settings.json',
                root / 'node_modules' / 'pkg' / 'index.js',
                root / 'coverage-report.txt',
                root / '.DS_Store',
                root / '.DS_STORE',
                root / 'Thumbs.db',
                root / 'THUMBS.DB',
                root / 'docs' / '._page.txt',
                root / 'desktop.ini',
                root / 'tategakiXTC_gui_studio.ini',
                root / 'regression_audit_bugfix126.md',
                root / 'work_instructions_from_changelog_1_1_0_29_and_later.md',
                root / 'code_split_preparation_roadmap_bugfix171b.md',
                root / 'split_refactor_progress_bugfix151.md',
                root / 'CONTINUATION_PROGRESS_v1_1_0_20260417.md',
                root / 'handoff_clean302_hangrestore2.md',
                root / '引継ぎ_localweb_step1ar_2026-04-21.md',
                root / '引き継ぎ書_v1_1_0_clean97_20260418.md',
                root / '引き継ぎ追記_clean98_20260418.md',
                root / 'README.md.rootcopy',
                root / 'work_clean273_md.md',
                root / 'sample.xtc.partial',
                root / 'session.tmp',
                root / 'old_output.xtc.overwritebak',
                root / 'debug.log',
                root / 'pytest-session.out',
                root / 'stderr.err',
                root / 'PYTEST-SUMMARY.LOG',
                root / '.coverage.hostname.12345.random',
                root / 'session.trace',
                root / 'profile.prof',
                root / 'server.pid',
                root / 'writer.lock',
                root / 'test_full_log.txt',
                root / 'test_full_log_retry.txt',
                root / 'test_fail_index.txt',
                root / 'test_errors.txt',
                root / 'test_failures.txt',
                root / 'bundle_tests_0_66.txt',
                root / 'pt_logic.log',
                root / 'pt_worker.exit',
                root / 'pt150.log',
                root / 'pt150.exit',
                root / 'old-release.zip',
                root / 'old-release.7z',
                root / 'old-release.tar',
                root / 'old-release.tgz',
                root / 'old-release.tar.gz',
                root / 'old-release.whl',
            ]
            for path in ignore_cases:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('x', encoding='utf-8')

            self.assertTrue(rel.should_include_path(keep, root))
            for path in ignore_cases:
                self.assertFalse(rel.should_include_path(path, root), str(path))

    def test_should_include_path_rejects_symlinked_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            target = root / 'README.md'
            target.write_text('ok', encoding='utf-8')
            link = root / 'README_link.md'
            self._make_file_symlink_or_skip(target, link)

            self.assertFalse(rel.should_include_path(link, root))

    def test_build_release_zip_excludes_symlinked_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            target = root / 'README.md'
            target.write_text('ok', encoding='utf-8')
            link = root / 'README_link.md'
            self._make_file_symlink_or_skip(target, link)

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])


    def test_archive_member_should_be_included_excludes_cache_names(self):
        self.assertFalse(rel.archive_member_should_be_included('tests/__pycache__/case.pyc'))
        self.assertFalse(rel.archive_member_should_be_included('.pytest_cache/v/cache/nodeids'))
        self.assertFalse(rel.archive_member_should_be_included('__MACOSX/._README.md'))
        self.assertFalse(rel.archive_member_should_be_included('docs/._page.txt'))
        self.assertFalse(rel.archive_member_should_be_included('.DS_STORE'))
        self.assertFalse(rel.archive_member_should_be_included('THUMBS.DB'))
        self.assertFalse(rel.archive_member_should_be_included('old-release.zip'))
        self.assertFalse(rel.archive_member_should_be_included('packages/demo.whl'))
        self.assertFalse(rel.archive_member_should_be_included('debug.log'))
        self.assertFalse(rel.archive_member_should_be_included('pytest-session.out'))
        self.assertFalse(rel.archive_member_should_be_included('stderr.err'))
        self.assertFalse(rel.archive_member_should_be_included('PYTEST-SUMMARY.LOG'))
        self.assertFalse(rel.archive_member_should_be_included('.coverage.hostname.12345.random'))
        self.assertFalse(rel.archive_member_should_be_included('session.trace'))
        self.assertFalse(rel.archive_member_should_be_included('profile.prof'))
        self.assertFalse(rel.archive_member_should_be_included('server.pid'))
        self.assertFalse(rel.archive_member_should_be_included('writer.lock'))
        self.assertFalse(rel.archive_member_should_be_included('test_full_log.txt'))
        self.assertFalse(rel.archive_member_should_be_included('test_fail_index.txt'))
        self.assertFalse(rel.archive_member_should_be_included('bundle_tests_0_66.txt'))
        self.assertTrue(rel.archive_member_should_be_included('tests/test_release_bundle_hygiene.py'))

    def test_archive_member_should_be_included_rejects_unsafe_member_names(self):
        unsafe_names = [
            '',
            '/',
            '///',
            r'\\',
            '../evil.py',
            'safe/../../evil.py',
            '/absolute/path.py',
            '//server/share/path.py',
            r'\\server\share\path.py',
            'C:relative/path.py',
            'C:/absolute/path.py',
            r'C:\absolute\path.py',
            'safe//double_slash.py',
            './relative_dot.py',
            'safe/./relative_dot.py',
            r'safe\windows_separator.py',
        ]
        for name in unsafe_names:
            self.assertFalse(rel.archive_member_should_be_included(name), name)
        self.assertTrue(rel.archive_member_should_be_included('safe/relative_path.py'))


    def test_verify_release_zip_reports_backslash_member_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'backslash-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._writestr_raw_member(zf, r'docs\page.txt', 'windows separator')

            bad_entries = rel.verify_release_zip(zip_path)

            self.assertEqual(bad_entries, [r'docs\page.txt'])

    def test_verify_release_zip_escapes_control_member_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'control-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('docs/bad\nname.txt', 'control character in member name')

            bad_entries = rel.verify_release_zip(zip_path)

            self.assertEqual(bad_entries, [r'docs/bad\nname.txt'])
            self.assertNotIn('\n', bad_entries[0])

    def test_verify_release_zip_escapes_bidi_control_member_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'bidi-control-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('docs/bidi\u202eeman.txt', 'bidi control in member name')

            bad_entries = rel.verify_release_zip(zip_path)

            self.assertEqual(bad_entries, [r'docs/bidi\u202eeman.txt'])
            self.assertNotIn('\u202e', bad_entries[0])
            self.assertIn(r'\u202e', bad_entries[0])

    def test_verify_release_zip_escapes_private_use_member_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'private-use-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('docs/private\ue000name.txt', 'private use character in member name')

            bad_entries = rel.verify_release_zip(zip_path)

            self.assertEqual(bad_entries, ['docs/private\\ue000name.txt'])
            self.assertNotIn('\ue000', bad_entries[0])
            self.assertIn('\\ue000', bad_entries[0])

    def test_verify_release_zip_escapes_noncharacter_member_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'noncharacter-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('docs/nonchar\ufdd0name.txt', 'Unicode noncharacter in member name')

            bad_entries = rel.verify_release_zip(zip_path)

            self.assertEqual(bad_entries, ['docs/nonchar\\ufdd0name.txt'])
            self.assertNotIn('\ufdd0', bad_entries[0])
            self.assertIn('\\ufdd0', bad_entries[0])

    def test_disallowed_unicode_member_names_are_rejected_and_escaped_consistently(self):
        samples = [
            ('C0 control', '\n', r'\n'),
            ('DEL control', '\x7f', r'\x7f'),
            ('bidi format control', '\u202e', r'\u202e'),
            ('private use', '\ue000', r'\ue000'),
            ('noncharacter', '\ufdd0', r'\ufdd0'),
            ('surrogate', '\ud800', r'\ud800'),
        ]
        for label, char, escaped in samples:
            with self.subTest(label=label):
                member_name = f'docs/bad{char}name.txt'
                self.assertTrue(rel._is_archive_member_disallowed_unicode_char(char))
                self.assertFalse(rel.archive_member_should_be_included(member_name))
                displayed = rel._display_archive_member_name(member_name)
                self.assertNotIn(char, displayed)
                self.assertIn(escaped, displayed)

    def test_archive_member_should_be_included_rejects_directory_entries(self):
        self.assertFalse(rel.archive_member_should_be_included('templates/', is_dir=True))
        self.assertFalse(rel.archive_member_should_be_included('README.md/', is_dir=True))

    def test_verify_release_zip_reports_directory_member_entries(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'directory-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('templates/', '')

            bad_entries = rel.verify_release_zip(zip_path)

            self.assertEqual(bad_entries, ['templates/'])

    def test_archive_member_should_be_included_rejects_windows_unsafe_names(self):
        unsafe_names = [
            'CON.txt',
            'docs/aux',
            'docs/NUL.md',
            'docs/COM1.log',
            'docs/LPT9.txt',
            'docs/trailingdot.',
            'docs/trailingspace ',
            'docs/foo:bar.txt',
            'docs/star*.txt',
            'docs/question?.txt',
            'docs/pipe|name.txt',
            'docs/control\x01.txt',
            'docs/bidi\u202eeman.txt',
            'docs/private\ue000name.txt',
            'docs/nonchar\ufdd0name.txt',
        ]
        for name in unsafe_names:
            self.assertFalse(rel.archive_member_should_be_included(name), name)
        self.assertTrue(rel.archive_member_should_be_included('docs/safe-name_01.txt'))

    def test_build_release_zip_self_validates_written_archive_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            keep = root / 'README.md'
            keep.write_text('ok', encoding='utf-8')
            out = root / 'dist' / 'release.zip'

            def fake_iter_release_files(_root, *, excluded_paths=None):
                yield keep

            with mock.patch.object(rel, 'iter_release_files', fake_iter_release_files), \
                 mock.patch.object(rel, 'archive_member_should_be_included', side_effect=[True, False]):
                with self.assertRaises(RuntimeError):
                    rel.build_release_zip(root, out)
            self.assertFalse(out.exists())

    def test_relative_path_should_be_included_excludes_hidden_cache_entries(self):
        self.assertFalse(rel._relative_path_should_be_included(Path('.pytest_cache/v/cache/nodeids'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('tests/__pycache__/case.pyc'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('.ruff_cache/checks.db'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('__MACOSX/._README.md'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/._page.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('.DS_STORE'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('THUMBS.DB'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('README.md.rootcopy'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('work_clean273_md.md'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('sample.xtc.partial'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('session.tmp'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('old_output.xtc.overwritebak'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('debug.log'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('pytest-session.out'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('stderr.err'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('PYTEST-SUMMARY.LOG'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('.coverage.hostname.12345.random'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('session.trace'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('profile.prof'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('server.pid'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('writer.lock'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('test_full_log.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('test_fail_index.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('bundle_tests_0_66.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('../outside.py'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('/absolute/path.py'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('C:/absolute/path.py'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path(r'C:\\absolute\\path.py'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path(r'\\absolute\\path.py'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(PureWindowsPath('/absolute/path.py'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(PureWindowsPath('C:/absolute/path.py'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('pt_logic.log'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('pt_worker.exit'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('pt150.log'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('pt150.exit'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('old-release.zip'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('old-release.7z'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('old-release.tar'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('old-release.tgz'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('old-release.tar.gz'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('old-release.whl'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('CON.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/aux.md'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/trailingdot.'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/trailingspace '), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/foo:bar.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/star*.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/control\x01.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/private\ue000name.txt'), is_dir=False))
        self.assertFalse(rel._relative_path_should_be_included(Path('docs/nonchar\ufdd0name.txt'), is_dir=False))
        self.assertTrue(rel._relative_path_should_be_included(Path('tests/test_release_bundle_hygiene.py'), is_dir=False))

    def test_iter_release_files_uses_natural_sort_and_skips_dist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for rel_path in ['docs/page2.txt', 'docs/page10.txt', 'docs/page1.txt', 'dist/old.zip']:
                path = root / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(rel_path, encoding='utf-8')

            names = [p.relative_to(root).as_posix() for p in rel.iter_release_files(root)]
            self.assertEqual(names, ['docs/page1.txt', 'docs/page2.txt', 'docs/page10.txt'])


    def test_build_release_zip_excludes_continuation_progress_memo(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            (root / 'CONTINUATION_PROGRESS_v1_1_0_20260417.md').write_text('internal', encoding='utf-8')

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])

    def test_build_release_zip_excludes_handoff_memos_with_current_names(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            handoff_names = [
                'handoff_clean302_hangrestore2.md',
                'tategaki-xtc-parallel-bugsweep357_handoff.md',
                'tategaki-xtc-parallel-bugsweep462_code_trial_handoff.md',
                'tategaki-xtc-parallel-bugsweep999_code_trial_handoff.md',
                'BUGSWEEP351_HANDOFF.md',
                '引継ぎ_localweb_step1ar_2026-04-21.md',
            ]
            for name in handoff_names:
                (root / name).write_text('internal', encoding='utf-8')

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])

    def test_current_code_trial_handoff_names_are_release_excluded(self):
        current_names = [
            'tategaki-xtc-parallel-bugsweep462_code_trial_handoff.md',
            'tategaki-xtc-parallel-bugsweep999_code_trial_handoff.md',
            'docs/tategaki-xtc-parallel-bugsweep999_code_trial_handoff.md',
        ]
        for name in current_names:
            with self.subTest(name=name):
                self.assertFalse(rel._relative_path_should_be_included(Path(name), is_dir=False))

    def test_build_release_zip_excludes_handover_memos(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            (root / '引き継ぎ書_v1_1_0_clean97_20260418.md').write_text('internal', encoding='utf-8')
            (root / '引き継ぎ追記_clean98_20260418.md').write_text('internal', encoding='utf-8')

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])

    def test_build_release_zip_excludes_custom_output_inside_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            out = root / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])

    def test_build_release_zip_excludes_archive_artifacts_outside_dist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            for rel_path in [
                'old-release.zip',
                'backup.7z',
                'bundle.tar',
                'bundle.tgz',
                'bundle.tar.gz',
                'vendor/demo.whl',
            ]:
                path = root / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'archive')

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])

    def test_build_release_zip_writes_only_expected_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            for rel_path in ['README.md', 'tategakiXTC_gui_core.py', 'logs/run.log', 'debug.log', 'pytest-session.out', 'stderr.err', '.coverage.hostname.12345.random', 'session.trace', 'profile.prof', 'server.pid', 'writer.lock', 'test_full_log.txt', 'test_fail_index.txt', 'bundle_tests_0_66.txt', 'pt_logic.log', 'pt_worker.exit', 'pt150.log', 'pt150.exit', '__pycache__/x.pyc']:
                path = root / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix == '.pyc':
                    path.write_bytes(b'cached')
                else:
                    path.write_text(rel_path, encoding='utf-8')

            out = root / 'dist' / 'release.zip'
            created = rel.build_release_zip(root, out)
            self.assertEqual(created, out.resolve())
            with zipfile.ZipFile(created) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md', 'build_release_zip.py', 'tategakiXTC_gui_core.py'] if (root / 'build_release_zip.py').exists() else ['README.md', 'tategakiXTC_gui_core.py'])



    def test_build_release_zip_excludes_pycache_entries_at_any_depth(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            for rel_path in ['__pycache__/root.pyc', 'tests/__pycache__/case.pyc', 'pkg/__pycache__/mod.pyc']:
                path = root / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'cached')

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])

    def test_build_release_zip_rechecks_candidates_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            keep = root / 'README.md'
            keep.write_text('ok', encoding='utf-8')
            cached = root / '__pycache__' / 'case.pyc'
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(b'cached')

            out = root / 'dist' / 'release.zip'
            with mock.patch.object(rel, 'iter_release_files', return_value=[keep, cached]):
                rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])

    def test_build_release_zip_excludes_local_env_editor_and_os_noise(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            for rel_path in [
                '.git/HEAD',
                '.venv/Lib/site-packages/demo.txt',
                'venv/Lib/site-packages/demo.txt',
                '.idea/workspace.xml',
                '.vscode/settings.json',
                'node_modules/pkg/index.js',
                '.DS_Store',
                'Thumbs.db',
                'desktop.ini',
            ]:
                path = root / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    path.write_text('noise', encoding='utf-8')
                except OSError:
                    # Some intentionally unsafe names cannot be created on
                    # Windows. POSIX still creates them and exercises the
                    # release exclusion logic.
                    continue

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])


    def test_build_release_zip_excludes_editor_backup_and_merge_noise(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            noise_paths = [
                'notes.txt~',
                'README.md.bak',
                '__MACOSX/._README.md',
                'docs/._page.txt',
                '.DS_STORE',
                'THUMBS.DB',
                'merge.patch.rej',
                'module.py.orig',
                'old-release.zip',
                'old-release.7z',
                'old-release.tar',
                'old-release.tgz',
                'old-release.tar.gz',
                'old-release.whl',
            ]
            if os.name != 'nt':
                # These exercise Windows-unsafe path parts on POSIX. On Windows,
                # the Win32 layer may reject or normalize them before the
                # release filter sees the intended raw filename. Windows-specific
                # rejection is covered by helper and zip verification tests.
                noise_paths.extend([
                    'CON.txt',
                    'docs/aux.md',
                    'docs/trailingdot.',
                    'docs/trailingspace ',
                    'docs/foo:bar.txt',
                    'docs/star*.txt',
                ])
            for rel_path in noise_paths:
                path = root / rel_path
                path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    path.write_text('noise', encoding='utf-8')
                except OSError:
                    # Windows refuses several intentionally unsafe fixture names
                    # (for example CON.txt, trailing-dot names, and star*.txt).
                    # POSIX still creates them and exercises the release exclusion
                    # rules; Windows should continue with the creatable cases.
                    continue

            out = root / 'dist' / 'release.zip'
            rel.build_release_zip(root, out)
            with zipfile.ZipFile(out) as zf:
                names = sorted(zf.namelist())
            self.assertEqual(names, ['README.md'])


    def test_verify_release_zip_reports_empty_and_root_like_member_names(self):
        class FakeZipInfo:
            def __init__(self, filename):
                self.filename = filename

            def is_dir(self):
                return False

        class FakeZipFile:
            def __init__(self, *_args, **_kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def infolist(self):
                return [
                    FakeZipInfo(''),
                    FakeZipInfo('/'),
                    FakeZipInfo('///'),
                    FakeZipInfo(r'\\server\share\path.py'),
                    FakeZipInfo('README.md'),
                ]

        with tempfile.TemporaryDirectory() as td:
            with mock.patch.object(rel.zipfile, 'ZipFile', FakeZipFile):
                bad_entries = rel.verify_release_zip(Path(td) / 'fake.zip')

        self.assertEqual(
            bad_entries,
            ['<empty member name>', '/', '///', r'\\server\share\path.py'],
        )

    def test_verify_release_zip_reports_excluded_entries_in_existing_archive(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'bad-release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'ok')
                zf.writestr('__pycache__/module.cpython-313.pyc', b'cached')
                zf.writestr('dist/project-release.zip', b'nested')
                zf.writestr('__MACOSX/._README.md', b'metadata')
                zf.writestr('docs/._page.txt', b'metadata')
                zf.writestr('.DS_STORE', b'metadata')
                zf.writestr('THUMBS.DB', b'metadata')
                zf.writestr('../escape.py', b'unsafe')
                zf.writestr('/absolute/path.py', b'unsafe')
                zf.writestr('C:/absolute/path.py', b'unsafe')
                zf.writestr('docs/CON.txt', b'unsafe')
                zf.writestr('docs/trailingdot.', b'unsafe')
                zf.writestr('docs/trailingspace ', b'unsafe')
                zf.writestr('docs/foo:bar.txt', b'unsafe')
                zf.writestr('docs/star*.txt', b'unsafe')
                zf.writestr('old-release.zip', b'archive')
                zf.writestr('packages/demo.whl', b'archive')
                zf.writestr('debug.log', b'log')
                zf.writestr('pytest-session.out', b'log')
                zf.writestr('stderr.err', b'log')
                zf.writestr('PYTEST-SUMMARY.LOG', b'log')
                zf.writestr('.coverage.hostname.12345.random', b'coverage')
                zf.writestr('session.trace', b'trace')
                zf.writestr('profile.prof', b'prof')
                zf.writestr('server.pid', b'pid')
                zf.writestr('writer.lock', b'lock')
                zf.writestr('test_full_log.txt', b'log')
                zf.writestr('test_fail_index.txt', b'log')
                zf.writestr('bundle_tests_0_66.txt', b'test list')

            bad_entries = rel.verify_release_zip(zip_path)

            self.assertEqual(
                bad_entries,
                [
                    '__pycache__/module.cpython-313.pyc',
                    'dist/project-release.zip',
                    '__MACOSX/._README.md',
                    'docs/._page.txt',
                    '.DS_STORE',
                    'THUMBS.DB',
                    '../escape.py',
                    '/absolute/path.py',
                    'C:/absolute/path.py',
                    'docs/CON.txt',
                    'docs/trailingdot.',
                    'docs/trailingspace ',
                    'docs/foo:bar.txt',
                    'docs/star*.txt',
                    'old-release.zip',
                    'packages/demo.whl',
                    'debug.log',
                    'pytest-session.out',
                    'stderr.err',
                    'PYTEST-SUMMARY.LOG',
                    '.coverage.hostname.12345.random',
                    'session.trace',
                    'profile.prof',
                    'server.pid',
                    'writer.lock',
                    'test_full_log.txt',
                    'test_fail_index.txt',
                    'bundle_tests_0_66.txt',
                ],
            )

    def test_verify_release_zip_integrity_reports_bad_zip_files(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'bad-release.zip'
            zip_path.write_bytes(b'not a zip file')

            integrity_errors = rel.verify_release_zip_integrity(zip_path)

            self.assertTrue(integrity_errors)
            self.assertIn('<bad zip>:', integrity_errors[0])

    def test_release_zip_verification_checks_have_unique_keys_and_expected_order(self):
        keys = [key for key, _func, _build_prefix, _verify_prefix in rel._release_zip_verification_checks()]

        self.assertEqual(
            keys,
            [
                'integrity',
                'duplicate_entries',
                'unsafe_mode_entries',
                'long_path_entries',
                'required_member_spelling_issues',
                'bad_entries',
                'missing_public_docs',
                'missing_support_files',
                'untracked_regression_tests',
                'untracked_golden_cases',
                'required_file_list_issues',
                'required_file_content_issues',
                'missing_assets',
            ],
        )
        self.assertEqual(len(keys), len(set(keys)))

    def test_run_release_zip_verification_checks_stops_after_integrity_failure(self):
        with mock.patch.object(
            rel,
            'verify_release_zip_integrity',
            return_value=['<bad zip>: broken'],
        ) as integrity_check, mock.patch.object(
            rel,
            'verify_release_zip_duplicate_members',
            side_effect=AssertionError('secondary checks must not run after integrity failure'),
        ) as duplicate_check:
            issues = rel._run_release_zip_verification_checks(Path('broken.zip'))

        integrity_check.assert_called_once_with(Path('broken.zip'))
        duplicate_check.assert_not_called()
        self.assertEqual(
            issues,
            [
                (
                    'integrity',
                    'release zip failed integrity check',
                    'Integrity check failed in release zip',
                    ['<bad zip>: broken'],
                ),
            ],
        )

    def test_release_zip_verify_issue_messages_share_common_prefixes(self):
        issues = [
            (
                'bad_entries',
                'release zip contained excluded entries',
                'Excluded entries found in release zip',
                ['debug.log'],
            ),
            (
                'missing_assets',
                'release zip missing required assets',
                'Missing required assets in release zip',
                ['LICENSE_OFL.txt'],
            ),
        ]

        self.assertEqual(
            rel._release_zip_verify_issue_messages(issues),
            [
                "Excluded entries found in release zip: debug.log",
                "Missing required assets in release zip: LICENSE_OFL.txt",
            ],
        )
        self.assertEqual(
            rel._first_release_zip_build_error_message(issues),
            "release zip contained excluded entries: debug.log",
        )


    def test_release_zip_issue_entries_are_formatted_without_repr_noise(self):
        entries = [r'docs/bad\nname.txt', r'docs/private\ue000name.txt']

        self.assertEqual(
            rel._format_release_zip_issue_entries(entries),
            r'2 items: [item 1] docs/bad\nname.txt [item 2] docs/private\ue000name.txt',
        )
        self.assertNotIn("['", rel._release_zip_verify_issue_messages([
            (
                'bad_entries',
                'release zip contained excluded entries',
                'Excluded entries found in release zip',
                entries,
            ),
        ])[0])



    def test_release_zip_issue_entries_escape_raw_disallowed_unicode_as_last_defense(self):
        entries = ['docs/raw\nname.txt', 'docs/private\ue000name.txt']

        formatted = rel._format_release_zip_issue_entries(entries)

        self.assertEqual(
            formatted,
            r'2 items: [item 1] docs/raw\nname.txt [item 2] docs/private\ue000name.txt',
        )
        self.assertNotIn('\n', formatted.replace(r'\n', ''))
        self.assertNotIn('\ue000', formatted)
        self.assertIn(r'\n', formatted)
        self.assertIn(r'\ue000', formatted)

    def test_release_zip_verify_issue_messages_escape_raw_disallowed_unicode_from_checks(self):
        issues = [
            (
                'custom_check',
                'release zip custom build prefix',
                'Custom check found in release zip',
                ['docs/raw\nname\ue000.txt'],
            ),
        ]

        messages = rel._release_zip_verify_issue_messages(issues)

        self.assertEqual(messages, [r'Custom check found in release zip: docs/raw\nname\ue000.txt'])
        self.assertNotIn('\n', messages[0].replace(r'\n', ''))
        self.assertNotIn('\ue000', messages[0])

    def test_release_zip_issue_messages_escape_raw_disallowed_unicode_as_last_defense(self):
        messages = [
            'Excluded entries found in release zip: docs/raw\nname.txt',
            'Missing required assets in release zip: docs/private\ue000name.txt',
        ]

        formatted = rel._format_release_zip_issue_messages(messages)

        self.assertEqual(
            formatted,
            r'2 issue groups: [group 1] Excluded entries found in release zip: docs/raw\nname.txt '
            r'[group 2] Missing required assets in release zip: docs/private\ue000name.txt',
        )
        self.assertNotIn('\n', formatted.replace(r'\n', ''))
        self.assertNotIn('\ue000', formatted)
        self.assertIn(r'\n', formatted)
        self.assertIn(r'\ue000', formatted)

    def test_release_zip_issue_entries_show_no_details_for_empty_iterable(self):
        formatted = rel._format_release_zip_issue_entries([])

        self.assertEqual(formatted, '<no details>')
        self.assertNotEqual(formatted, '')

    def test_release_zip_issue_messages_show_no_issue_groups_for_empty_iterable(self):
        formatted = rel._format_release_zip_issue_messages([])

        self.assertEqual(formatted, '<no issue groups>')
        self.assertNotEqual(formatted, '')

    def test_release_zip_issue_entries_show_empty_details_explicitly(self):
        formatted = rel._format_release_zip_issue_entries([''])

        self.assertEqual(formatted, '<empty diagnostic text>')
        self.assertNotEqual(formatted, '')

    def test_release_zip_issue_messages_show_empty_details_explicitly(self):
        formatted = rel._format_release_zip_issue_messages([''])

        self.assertEqual(formatted, '<empty diagnostic text>')
        self.assertNotEqual(formatted, '')

    def test_release_zip_issue_entries_are_indexed_when_entries_contain_separators(self):
        entries = ['docs/name;with:semicolon.txt', 'docs/second.txt (reason; with separator)']

        formatted = rel._format_release_zip_issue_entries(entries)

        self.assertEqual(
            formatted,
            '2 items: [item 1] docs/name;with:semicolon.txt [item 2] docs/second.txt (reason; with separator)',
        )
        self.assertNotEqual(formatted.count(';'), len(entries) - 1)
        self.assertIn('[item 1] docs/name;with:semicolon.txt', formatted)
        self.assertIn('[item 2] docs/second.txt (reason; with separator)', formatted)
        self.assertNotIn('[1] ', formatted)
        self.assertNotIn('[2] ', formatted)

    def test_release_zip_issue_messages_are_indexed_when_multiple_categories_fail(self):
        messages = [
            'Excluded entries found in release zip: 2 items: [item 1] debug.log [item 2] notes;draft.txt',
            'Missing required assets in release zip: fonts/LICENSE_OFL.txt',
        ]

        formatted = rel._format_release_zip_issue_messages(messages)

        self.assertEqual(
            formatted,
            '2 issue groups: [group 1] Excluded entries found in release zip: 2 items: [item 1] debug.log [item 2] notes;draft.txt '
            '[group 2] Missing required assets in release zip: fonts/LICENSE_OFL.txt',
        )
        self.assertNotIn(' | ', formatted)
        self.assertIn('[group 1] Excluded entries found in release zip', formatted)
        self.assertIn('[group 2] Missing required assets in release zip', formatted)
        self.assertNotIn('[1] ', formatted)
        self.assertNotIn('[2] ', formatted)

    def test_verify_mode_formats_multiple_issue_categories_without_pipe_separator(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('debug.log', 'temporary log')
                self._write_required_project_release_zip_members(zf, omit={'LICENSE.txt'})

            with self.assertRaises(SystemExit) as raised:
                with mock.patch.object(sys, 'argv', ['build_release_zip.py', '--verify', str(zip_path)]):
                    rel.main()

        message = str(raised.exception)
        self.assertIn('2 issue groups:', message)
        self.assertIn('[group 1] Excluded entries found in release zip: debug.log', message)
        self.assertIn('[group 2] Missing required public docs in release zip: LICENSE.txt', message)
        self.assertNotIn(' | ', message)

    def test_verify_release_zip_integrity_reports_crc_failures(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'ok')

            with mock.patch('build_release_zip.zipfile.ZipFile') as zip_file_mock:
                zip_file_mock.return_value.__enter__.return_value.testzip.return_value = 'README.md'
                integrity_errors = rel.verify_release_zip_integrity(zip_path)

            self.assertEqual(integrity_errors, ['README.md'])

    def test_verify_release_zip_integrity_escapes_corrupt_member_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'ok')

            with mock.patch('build_release_zip.zipfile.ZipFile') as zip_file_mock:
                zip_file_mock.return_value.__enter__.return_value.testzip.return_value = 'docs/bad\nname\ue000.txt'
                integrity_errors = rel.verify_release_zip_integrity(zip_path)

            self.assertEqual(integrity_errors, [r'docs/bad\nname\ue000.txt'])

    def test_verify_release_zip_unsafe_member_modes_reports_symlinks(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'symlink-release.zip'
            link_info = zipfile.ZipInfo('docs/link-to-outside')
            link_info.create_system = 3
            link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'ok')
                zf.writestr(link_info, '../outside.txt')

            unsafe_entries = rel.verify_release_zip_unsafe_member_modes(zip_path)

            self.assertEqual(
                unsafe_entries,
                ['docs/link-to-outside (symlink; mode 0o120777; external_attr 0xa1ff0000; create_system 3)'],
            )

    def test_verify_release_zip_unsafe_member_modes_reports_unsupported_special_files(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'fifo-release.zip'
            fifo_info = zipfile.ZipInfo('docs/special-fifo')
            fifo_info.create_system = 3
            fifo_info.external_attr = (stat.S_IFIFO | 0o644) << 16
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(fifo_info, b'')

            unsafe_entries = rel.verify_release_zip_unsafe_member_modes(zip_path)

            self.assertEqual(
                unsafe_entries,
                ['docs/special-fifo (unsupported file type 0o10000; mode 0o10644; external_attr 0x11a40000; create_system 3)'],
            )

    def test_verify_release_zip_unsafe_member_modes_reports_raw_noncanonical_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'backslash-symlink-release.zip'
            link_info = self._zipinfo_raw_member(r'docs\link-to-outside')
            link_info.create_system = 3
            link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(link_info, '../outside.txt')

            unsafe_entries = rel.verify_release_zip_unsafe_member_modes(zip_path)

            self.assertEqual(
                unsafe_entries,
                [r'docs\link-to-outside (symlink; mode 0o120777; external_attr 0xa1ff0000; create_system 3)'],
            )

    def test_verify_release_zip_unsafe_member_modes_ignores_non_unix_external_attrs(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'dos-attr-release.zip'
            odd_info = zipfile.ZipInfo('docs/not-a-unix-mode.txt')
            odd_info.create_system = 0
            odd_info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(odd_info, 'payload')

            self.assertEqual(rel.verify_release_zip_unsafe_member_modes(zip_path), [])

    def test_iter_bundled_font_files_detects_case_varied_font_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'FONTS' / 'NotoSansJP-Regular.TTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')

            bundled = [path.relative_to(root).as_posix() for path in rel.iter_bundled_font_files(root)]

            self.assertEqual(bundled, ['FONTS/NotoSansJP-Regular.TTF'])

    def test_validate_release_tree_accepts_case_varied_license_next_to_fonts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'Font' / 'NotoSansJP-Regular.ttf'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (font_path.parent / 'license_ofl.TXT').write_text('license', encoding='utf-8')

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_iter_bundled_font_files_detects_nested_uppercase_font_suffixes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            for relative_name in (
                'Font/subdir/NotoSansJP-Regular.TTC',
                'fonts/weights/NotoSansJP-Regular.OTC',
            ):
                font_path = root / relative_name
                font_path.parent.mkdir(parents=True, exist_ok=True)
                font_path.write_bytes(b'font')

            bundled = sorted(path.relative_to(root).as_posix() for path in rel.iter_bundled_font_files(root))

            self.assertEqual(
                bundled,
                [
                    'Font/subdir/NotoSansJP-Regular.TTC',
                    'fonts/weights/NotoSansJP-Regular.OTC',
                ],
            )

    def test_iter_bundled_font_files_ignores_font_suffix_lookalikes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_dir = root / 'fonts'
            font_dir.mkdir(parents=True, exist_ok=True)
            for name in (
                'NotoSansJP-Regular.ttf.bak',
                'NotoSansJP-Regular.otf.txt',
                'NotoSansJP-Regular',
            ):
                (font_dir / name).write_bytes(b'not a bundled font')

            bundled = [path.relative_to(root).as_posix() for path in rel.iter_bundled_font_files(root)]

            self.assertEqual(bundled, [])

    def test_validate_release_tree_accepts_root_license_for_nested_bundled_font(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'subdir' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_text('license', encoding='utf-8')

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_rejects_empty_bundled_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_text('   \n\t', encoding='utf-8')

            missing = rel.validate_release_tree(root)

            self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_validate_release_tree_rejects_bom_only_bundled_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_bytes(b'\xef\xbb\xbf   \n\t')

            missing = rel.validate_release_tree(root)

            self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_validate_release_tree_accepts_bom_prefixed_bundled_font_license_text(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_bytes(b'\xef\xbb\xbfOpen Font License')

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_rejects_utf16_utf32_whitespace_only_bundled_font_license(self):
        payloads = [
            '   \n\t'.encode('utf-16'),
            b'\xfe\xff' + '   \n\t'.encode('utf-16-be'),
            '   \n\t'.encode('utf-32'),
            b'\x00\x00\xfe\xff' + '   \n\t'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:4]):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td) / 'project'
                    root.mkdir(parents=True, exist_ok=True)
                    font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
                    font_path.parent.mkdir(parents=True, exist_ok=True)
                    font_path.write_bytes(b'font')
                    (root / 'LICENSE_OFL.TXT').write_bytes(payload)

                    missing = rel.validate_release_tree(root)

                self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_validate_release_tree_accepts_utf16_utf32_bom_prefixed_bundled_font_license_text(self):
        payloads = [
            'Open Font License'.encode('utf-16'),
            b'\xfe\xff' + 'Open Font License'.encode('utf-16-be'),
            'Open Font License'.encode('utf-32'),
            b'\x00\x00\xfe\xff' + 'Open Font License'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:4]):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td) / 'project'
                    root.mkdir(parents=True, exist_ok=True)
                    font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
                    font_path.parent.mkdir(parents=True, exist_ok=True)
                    font_path.write_bytes(b'font')
                    (root / 'LICENSE_OFL.TXT').write_bytes(payload)

                    self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_rejects_malformed_bom_bundled_font_license(self):
        payloads = [
            b'\xff\xfe ',
            b'\xfe\xff ',
            b'\xff\xfe\x00\x00 ',
            b'\x00\x00\xfe\xff ',
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:4]):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td) / 'project'
                    root.mkdir(parents=True, exist_ok=True)
                    font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
                    font_path.parent.mkdir(parents=True, exist_ok=True)
                    font_path.write_bytes(b'font')
                    (root / 'LICENSE_OFL.TXT').write_bytes(payload)

                    missing = rel.validate_release_tree(root)

                self.assertEqual(
                    missing,
                    ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
                )

    def test_validate_release_tree_rejects_non_utf8_bundled_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_bytes(b'Open Font License \xff')

            missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
            )

    def test_validate_release_tree_rejects_undeclared_utf16_utf32_bundled_font_license(self):
        payloads = [
            'Open Font License'.encode('utf-16-le'),
            'Open Font License'.encode('utf-16-be'),
            'Open Font License'.encode('utf-32-le'),
            'Open Font License'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:8]):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td) / 'project'
                    root.mkdir(parents=True, exist_ok=True)
                    font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
                    font_path.parent.mkdir(parents=True, exist_ok=True)
                    font_path.write_bytes(b'font')
                    (root / 'LICENSE_OFL.TXT').write_bytes(payload)

                    missing = rel.validate_release_tree(root)

                self.assertEqual(
                    missing,
                    ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
                )

    def test_validate_release_tree_rejects_short_undeclared_utf16_utf32_bundled_font_license(self):
        payloads = [
            'OF'.encode('utf-16-le'),
            'OF'.encode('utf-16-be'),
            'O'.encode('utf-32-le'),
            'O'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td) / 'project'
                    root.mkdir(parents=True, exist_ok=True)
                    font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
                    font_path.parent.mkdir(parents=True, exist_ok=True)
                    font_path.write_bytes(b'font')
                    (root / 'LICENSE_OFL.TXT').write_bytes(payload)

                    missing = rel.validate_release_tree(root)

                self.assertEqual(
                    missing,
                    ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
                )

    def test_validate_release_tree_rejects_control_only_bundled_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_bytes(b'\x00\x1f\x7f')

            missing = rel.validate_release_tree(root)

            self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_validate_release_tree_accepts_text_after_control_bundled_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_bytes(b'\x00Open Font License')

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_accepts_valid_license_after_non_utf8_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_bytes(b'Open Font License \xff')
            (root / 'fonts' / 'LICENSE_OFL.TXT').write_text('license', encoding='utf-8')

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_accepts_valid_license_after_malformed_bom_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_bytes(b'\xff\xfe ')
            (root / 'fonts' / 'LICENSE_OFL.TXT').write_text('license', encoding='utf-8')

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_accepts_non_empty_license_when_empty_candidate_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            (root / 'LICENSE_OFL.TXT').write_text('', encoding='utf-8')
            (root / 'fonts' / 'LICENSE_OFL.TXT').write_text('license', encoding='utf-8')

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_accepts_readable_license_after_unreadable_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            unreadable_license = root / 'LICENSE_OFL.TXT'
            unreadable_license.write_text('unreadable candidate', encoding='utf-8')
            (root / 'fonts' / 'LICENSE_OFL.TXT').write_text('license', encoding='utf-8')
            original_read_bytes = Path.read_bytes

            def fake_read_bytes(path):
                if path == unreadable_license:
                    raise OSError('mock license read failure')
                return original_read_bytes(path)

            with mock.patch.object(Path, 'read_bytes', autospec=True, side_effect=fake_read_bytes):
                self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_reports_read_error_when_no_readable_license_candidate_exists(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.OTF'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            unreadable_license = root / 'LICENSE_OFL.TXT'
            unreadable_license.write_text('unreadable candidate', encoding='utf-8')
            (root / 'fonts' / 'LICENSE_OFL.TXT').write_text('   ', encoding='utf-8')
            original_read_bytes = Path.read_bytes

            def fake_read_bytes(path):
                if path == unreadable_license:
                    raise OSError('mock license read failure')
                return original_read_bytes(path)

            with mock.patch.object(Path, 'read_bytes', autospec=True, side_effect=fake_read_bytes):
                missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                ['LICENSE_OFL.txt (bundled font license could not be read: mock license read failure)'],
            )

    def test_validate_release_tree_rejects_nested_license_for_direct_bundled_font(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'fonts' / 'NotoSansJP-Regular.ttf'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            nested_license = root / 'fonts' / 'subdir' / 'LICENSE_OFL.txt'
            nested_license.parent.mkdir(parents=True, exist_ok=True)
            nested_license.write_text('license', encoding='utf-8')

            missing = rel.validate_release_tree(root)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_validate_release_tree_requires_license_for_case_varied_font_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'FONTS' / 'NotoSansJP-Regular.otf'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')

            missing = rel.validate_release_tree(root)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_iter_bundled_font_files_ignores_symlinked_font_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_dir = root / 'Font'
            font_dir.mkdir(parents=True, exist_ok=True)
            target = root / 'outside-font.ttf'
            target.write_bytes(b'font')
            link = font_dir / 'NotoSansJP-Regular.ttf'
            self._make_file_symlink_or_skip(target, link)

            bundled = [path.relative_to(root).as_posix() for path in rel.iter_bundled_font_files(root)]

            self.assertEqual(bundled, [])

    def test_validate_release_tree_ignores_symlinked_font_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_dir = root / 'Font'
            font_dir.mkdir(parents=True, exist_ok=True)
            target = root / 'outside-font.ttf'
            target.write_bytes(b'font')
            link = font_dir / 'NotoSansJP-Regular.ttf'
            self._make_file_symlink_or_skip(target, link)

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_does_not_accept_symlinked_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            font_path = root / 'Font' / 'NotoSansJP-Regular.ttf'
            font_path.parent.mkdir(parents=True, exist_ok=True)
            font_path.write_bytes(b'font')
            target = root / 'outside-license.txt'
            target.write_text('license', encoding='utf-8')
            link = root / 'LICENSE_OFL.txt'
            self._make_file_symlink_or_skip(target, link)

            missing = rel.validate_release_tree(root)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_validate_release_tree_requires_public_docs_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'tategakiXTC_gui_studio.py').write_text('app', encoding='utf-8')
            self._write_required_project_release_files(
                root,
                omit={'LICENSE.txt', 'CHANGELOG.md', rel.RELEASE_NOTES_FILE},
            )

            missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                [
                    'LICENSE.txt (required for project release archives)',
                    'CHANGELOG.md (required for project release archives)',
                    f'{rel.RELEASE_NOTES_FILE} (required for project release archives)',
                ],
            )

    def test_validate_release_tree_accepts_required_public_docs_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'tategakiXTC_gui_studio.py').write_text('app', encoding='utf-8')
            self._write_required_project_release_files(root)

            self.assertEqual(rel.validate_release_tree(root), [])

    def test_validate_release_tree_requires_release_tooling_files_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(
                root,
                omit={'build_release_zip.py', 'mypy.ini', '.coveragerc'},
            )

            missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                [
                    'build_release_zip.py (required for project release archives)',
                    'mypy.ini (required for project release archives)',
                    '.coveragerc (required for project release archives)',
                ],
            )

    def test_validate_release_tree_requires_test_support_files_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(
                root,
                omit={'tests/generate_golden_images.py', 'tests/golden_regression_tools.py'},
            )

            missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                [
                    'tests/generate_golden_images.py (required for project release archives)',
                    'tests/golden_regression_tools.py (required for project release archives)',
                ],
            )

    def test_validate_release_tree_requires_tests_package_init_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root, omit={'tests/__init__.py'})

            missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                ['tests/__init__.py (required for project release archives)'],
            )

    def test_verify_release_zip_required_public_docs_requires_docs_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'missing-public-docs.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(
                    zf,
                    omit={'LICENSE.txt', 'CHANGELOG.md', rel.RELEASE_NOTES_FILE},
                )

            missing = rel.verify_release_zip_required_public_docs(zip_path)

            self.assertEqual(
                missing,
                [
                    'LICENSE.txt (required for project release archives)',
                    'CHANGELOG.md (required for project release archives)',
                    f'{rel.RELEASE_NOTES_FILE} (required for project release archives)',
                ],
            )

    def test_verify_release_zip_required_public_docs_ignores_non_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'generic.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'readme')

            self.assertEqual(rel.verify_release_zip_required_public_docs(zip_path), [])

    def test_verify_release_zip_required_public_docs_accepts_nfc_equivalent_member_name(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'nfc-public-doc.zip'
            required_name = 'Cafe\u0301Guide.txt'
            archive_name = 'Caf\xe9Guide.txt'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                zf.writestr(archive_name, 'guide')

            with mock.patch.object(rel, 'REQUIRED_PUBLIC_DOC_FILES', (required_name,)):
                missing = rel.verify_release_zip_required_public_docs(zip_path)

            self.assertEqual(missing, [])


    def test_verify_release_zip_required_project_support_files_requires_release_tooling_files(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'missing-release-tooling.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(
                    zf,
                    omit={'build_release_zip.py', 'mypy.ini', '.github/workflows/python-tests.yml'},
                )

            missing = rel.verify_release_zip_required_project_support_files(zip_path)

            self.assertEqual(
                missing,
                [
                    'build_release_zip.py (required for project release archives)',
                    'mypy.ini (required for project release archives)',
                ],
            )

    def test_verify_release_zip_required_project_support_files_requires_test_support_files(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'missing-test-support.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(
                    zf,
                    omit={'tests/image_golden_cases.py', 'tests/studio_import_helper.py'},
                )

            missing = rel.verify_release_zip_required_project_support_files(zip_path)

            self.assertEqual(
                missing,
                [
                    'tests/image_golden_cases.py (required for project release archives)',
                    'tests/studio_import_helper.py (required for project release archives)',
                ],
            )

    def test_verify_release_zip_required_project_support_files_requires_tests_package_init(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'missing-tests-package-init.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/__init__.py'})

            missing = rel.verify_release_zip_required_project_support_files(zip_path)

            self.assertEqual(
                missing,
                ['tests/__init__.py (required for project release archives)'],
            )

    def test_required_regression_test_file_list_matches_current_tests_tree(self):
        tests_dir = Path(__file__).resolve().parent
        actual = sorted(
            f'tests/{path.name}'
            for path in tests_dir.glob('test_*.py')
            if path.is_file()
        )

        self.assertEqual(actual, sorted(rel.REQUIRED_PROJECT_REGRESSION_TEST_FILES))

    def test_preview_renderer_targeted_test_module_name_matches_existing_file(self):
        tests_dir = Path(__file__).resolve().parent
        existing_modules = {
            f'tests.{path.stem}'
            for path in tests_dir.glob('test_*.py')
            if path.is_file()
        }

        self.assertIn('tests.test_preview_shared_renderer', existing_modules)
        self.assertIn(
            'tests/test_preview_shared_renderer.py',
            rel.REQUIRED_PROJECT_REGRESSION_TEST_FILES,
        )
        self.assertNotIn('tests.test_shared_preview_rendering', existing_modules)
        self.assertNotIn(
            'tests/test_shared_preview_rendering.py',
            rel.REQUIRED_PROJECT_REGRESSION_TEST_FILES,
        )

    def test_required_project_release_file_list_has_no_duplicate_entries(self):
        self.assertEqual(rel._duplicate_sequence_items(rel.REQUIRED_PROJECT_RELEASE_FILES), [])

    def test_required_project_release_file_list_has_normalized_posix_paths(self):
        self.assertEqual(rel._required_release_file_path_issues(), [])

    def test_required_project_release_file_list_reports_malformed_paths(self):
        patched = (
            *rel.REQUIRED_PROJECT_RELEASE_FILES,
            r'tests\test_windows_separator.py',
            '/absolute/path.py',
            'logs/debug.log',
        )

        with mock.patch.object(rel, 'REQUIRED_PROJECT_RELEASE_FILES', patched):
            issues = rel._required_release_file_list_issues()

        self.assertIn(
            r'tests\test_windows_separator.py (required file path must be a normalized POSIX relative path in REQUIRED_PROJECT_RELEASE_FILES)',
            issues,
        )
        self.assertIn(
            '/absolute/path.py (required file path must be a normalized POSIX relative path in REQUIRED_PROJECT_RELEASE_FILES)',
            issues,
        )
        self.assertIn(
            'logs/debug.log (required file path must be a normalized POSIX relative path in REQUIRED_PROJECT_RELEASE_FILES)',
            issues,
        )

    def test_required_project_release_file_list_reports_duplicate_entries(self):
        duplicated = (*rel.REQUIRED_PROJECT_RELEASE_FILES, 'README.md')

        with mock.patch.object(rel, 'REQUIRED_PROJECT_RELEASE_FILES', duplicated):
            issues = rel._required_release_file_list_issues()

        self.assertEqual(
            issues,
            ['README.md (duplicate entry in REQUIRED_PROJECT_RELEASE_FILES)'],
        )

    def test_verify_release_zip_required_file_list_issues_reports_duplicate_entries(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'duplicate-required-list.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)

            duplicated = (*rel.REQUIRED_PROJECT_RELEASE_FILES, 'README.md')
            with mock.patch.object(rel, 'REQUIRED_PROJECT_RELEASE_FILES', duplicated):
                issues = rel.verify_release_zip_required_file_list_issues(zip_path)

            self.assertEqual(
                issues,
                ['README.md (duplicate entry in REQUIRED_PROJECT_RELEASE_FILES)'],
            )

    def test_verify_release_zip_required_file_list_issues_reports_malformed_paths(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'malformed-required-list.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)

            patched = (*rel.REQUIRED_PROJECT_RELEASE_FILES, r'tests\test_windows_separator.py')
            with mock.patch.object(rel, 'REQUIRED_PROJECT_RELEASE_FILES', patched):
                issues = rel.verify_release_zip_required_file_list_issues(zip_path)

            self.assertEqual(
                issues,
                [
                    r'tests\test_windows_separator.py ' 
                    '(required file path must be a normalized POSIX relative path in REQUIRED_PROJECT_RELEASE_FILES)',
                ],
            )

    def test_required_project_release_file_list_has_registered_content_marker_keys(self):
        self.assertEqual(rel._required_content_marker_key_issues(), [])

    def test_required_project_release_file_list_has_registered_content_marker_category_keys(self):
        self.assertEqual(rel._required_content_marker_category_key_issues(), [])

    def test_required_project_release_file_list_has_valid_content_marker_category_specs(self):
        self.assertEqual(rel._required_content_marker_category_spec_issues(), [])

    def test_required_project_release_file_list_reports_duplicate_content_marker_category_spec(self):
        specs = rel._required_content_marker_category_specs()
        duplicated = (*specs, specs[0])

        with mock.patch.object(rel, '_required_content_marker_category_specs', return_value=duplicated):
            issues = rel._required_release_file_list_issues()

        self.assertIn(
            'REQUIRED_APP_CONTENT_MARKERS (duplicate content marker category spec marker map name)',
            issues,
        )
        self.assertIn(
            'REQUIRED_PROJECT_APP_CODE_FILES (duplicate content marker category spec required list name)',
            issues,
        )

    def test_required_project_release_file_list_reports_empty_content_marker_category_spec(self):
        specs = rel._required_content_marker_category_specs()
        empty_spec = ('REQUIRED_EMPTY_CONTENT_MARKERS', {}, (), 'REQUIRED_EMPTY_FILES')
        patched_specs = (empty_spec, *specs)

        with mock.patch.object(rel, '_required_content_marker_category_specs', return_value=patched_specs):
            issues = rel._required_release_file_list_issues()

        self.assertIn(
            'REQUIRED_EMPTY_CONTENT_MARKERS (empty content marker category spec marker map)',
            issues,
        )
        self.assertIn(
            'REQUIRED_EMPTY_FILES (empty content marker category spec required list for REQUIRED_EMPTY_CONTENT_MARKERS)',
            issues,
        )

    def test_required_project_release_file_list_reports_duplicate_content_marker_category_required_entry(self):
        specs = rel._required_content_marker_category_specs()
        marker_map_name, marker_map, category_files, category_list_name = specs[0]
        patched_spec = (
            marker_map_name,
            marker_map,
            (*category_files, category_files[0]),
            category_list_name,
        )
        patched_specs = (patched_spec, *specs[1:])

        with mock.patch.object(rel, '_required_content_marker_category_specs', return_value=patched_specs):
            issues = rel._required_release_file_list_issues()

        self.assertIn(
            'tategakiXTC_gui_studio.py '
            '(duplicate entry in content marker category spec required list REQUIRED_PROJECT_APP_CODE_FILES)',
            issues,
        )

    def test_validate_release_tree_reports_empty_content_marker_category_spec(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)

            specs = rel._required_content_marker_category_specs()
            empty_spec = ('REQUIRED_EMPTY_CONTENT_MARKERS', {}, (), 'REQUIRED_EMPTY_FILES')
            with mock.patch.object(rel, '_required_content_marker_category_specs', return_value=(empty_spec, *specs)):
                issues = rel.validate_release_tree(root)

            self.assertIn(
                'REQUIRED_EMPTY_CONTENT_MARKERS (empty content marker category spec marker map)',
                issues,
            )

    def test_verify_release_zip_required_file_list_issues_reports_empty_content_marker_category_spec(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'empty-marker-category-spec.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)

            specs = rel._required_content_marker_category_specs()
            empty_spec = ('REQUIRED_EMPTY_CONTENT_MARKERS', {}, (), 'REQUIRED_EMPTY_FILES')
            with mock.patch.object(rel, '_required_content_marker_category_specs', return_value=(empty_spec, *specs)):
                issues = rel.verify_release_zip_required_file_list_issues(zip_path)

            self.assertIn(
                'REQUIRED_EMPTY_CONTENT_MARKERS (empty content marker category spec marker map)',
                issues,
            )

    def test_required_project_release_file_list_reports_wrong_content_marker_category_key(self):
        patched_markers = {
            **rel.REQUIRED_DOCUMENT_CONTENT_MARKERS,
            'tategakiXTC_gui_studio.py': rel.REQUIRED_APP_CONTENT_MARKERS['tategakiXTC_gui_studio.py'],
        }

        with mock.patch.object(rel, 'REQUIRED_DOCUMENT_CONTENT_MARKERS', patched_markers):
            issues = rel._required_release_file_list_issues()

        self.assertIn(
            'tategakiXTC_gui_studio.py '
            '(content marker key in REQUIRED_DOCUMENT_CONTENT_MARKERS is not listed in REQUIRED_PROJECT_DOCUMENT_FILES)',
            issues,
        )

    def test_required_project_release_file_list_reports_unregistered_content_marker_key(self):
        patched_markers = {
            **rel.REQUIRED_DOCUMENT_CONTENT_MARKERS,
            'README_COPY.md': ('run_gui.bat',),
        }

        with mock.patch.object(rel, 'REQUIRED_DOCUMENT_CONTENT_MARKERS', patched_markers):
            issues = rel._required_release_file_list_issues()

        self.assertIn(
            'README_COPY.md (content marker key is not listed in REQUIRED_PROJECT_RELEASE_FILES)',
            issues,
        )

    def test_validate_release_tree_reports_unregistered_content_marker_key(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            patched_markers = {
                **rel.REQUIRED_DOCUMENT_CONTENT_MARKERS,
                'README_COPY.md': ('run_gui.bat',),
            }

            with mock.patch.object(rel, 'REQUIRED_DOCUMENT_CONTENT_MARKERS', patched_markers):
                issues = rel.validate_release_tree(root)

            self.assertIn(
                'README_COPY.md (content marker key is not listed in REQUIRED_PROJECT_RELEASE_FILES)',
                issues,
            )

    def test_validate_release_tree_reports_wrong_content_marker_category_key(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            patched_markers = {
                **rel.REQUIRED_DOCUMENT_CONTENT_MARKERS,
                'tategakiXTC_gui_studio.py': rel.REQUIRED_APP_CONTENT_MARKERS['tategakiXTC_gui_studio.py'],
            }

            with mock.patch.object(rel, 'REQUIRED_DOCUMENT_CONTENT_MARKERS', patched_markers):
                issues = rel.validate_release_tree(root)

            self.assertIn(
                'tategakiXTC_gui_studio.py '
                '(content marker key in REQUIRED_DOCUMENT_CONTENT_MARKERS is not listed in REQUIRED_PROJECT_DOCUMENT_FILES)',
                issues,
            )

    def test_verify_release_zip_required_file_list_issues_reports_unregistered_content_marker_key(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'unregistered-marker-key.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)

            patched_markers = {
                **rel.REQUIRED_DOCUMENT_CONTENT_MARKERS,
                'README_COPY.md': ('run_gui.bat',),
            }
            with mock.patch.object(rel, 'REQUIRED_DOCUMENT_CONTENT_MARKERS', patched_markers):
                issues = rel.verify_release_zip_required_file_list_issues(zip_path)

            self.assertEqual(
                issues,
                ['README_COPY.md (content marker key is not listed in REQUIRED_PROJECT_RELEASE_FILES)'],
            )

    def test_verify_release_zip_required_file_list_issues_reports_wrong_content_marker_category_key(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'wrong-marker-category-key.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)

            patched_markers = {
                **rel.REQUIRED_DOCUMENT_CONTENT_MARKERS,
                'tategakiXTC_gui_studio.py': rel.REQUIRED_APP_CONTENT_MARKERS['tategakiXTC_gui_studio.py'],
            }
            with mock.patch.object(rel, 'REQUIRED_DOCUMENT_CONTENT_MARKERS', patched_markers):
                issues = rel.verify_release_zip_required_file_list_issues(zip_path)

            self.assertEqual(
                issues,
                [
                    'tategakiXTC_gui_studio.py '
                    '(content marker key in REQUIRED_DOCUMENT_CONTENT_MARKERS is not listed in REQUIRED_PROJECT_DOCUMENT_FILES)',
                ],
            )

    def test_validate_release_tree_rejects_untracked_regression_test_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            extra_test = root / 'tests' / 'test_new_release_guard_regression.py'
            extra_test.write_text('def test_new_release_guard():\n    pass\n', encoding='utf-8')

            issues = rel.validate_release_tree(root)

            expected = (
                'tests/test_new_release_guard_regression.py '
                '(regression test file is not listed in REQUIRED_PROJECT_REGRESSION_TEST_FILES)'
            )
            self.assertIn(expected, issues)
            self.assertEqual(issues.count(expected), 1)

    def test_verify_release_zip_reports_untracked_regression_test_file(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'untracked-regression-test.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)
                zf.writestr('tests/test_new_release_guard_regression.py', 'def test_new_release_guard():\n    pass\n')

            issues = rel.verify_release_zip_untracked_regression_test_files(zip_path)

            self.assertEqual(
                issues,
                [
                    'tests/test_new_release_guard_regression.py '
                    '(regression test file is not listed in REQUIRED_PROJECT_REGRESSION_TEST_FILES)',
                ],
            )

    def test_required_golden_image_file_list_matches_case_specs(self):
        source = Path('tests/golden_case_registry.py').read_text(encoding='utf-8')
        expected = rel._expected_golden_image_names_from_case_specs_source(source)

        self.assertEqual(expected, sorted(rel.REQUIRED_PROJECT_GOLDEN_IMAGE_FILES))

    def test_tree_untracked_golden_case_files_prefers_registry_case_specs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            (root / 'tests' / 'golden_case_registry.py').write_text(
                "CASE_SPECS = {'glyph_ichi': {}, 'page_new_release_layout': {}}\n"
                "THRESHOLD_PROFILES = {}\n",
                encoding='utf-8',
            )
            (root / 'tests' / 'image_golden_cases.py').write_text(
                "from tests.golden_case_registry import CASE_SPECS, THRESHOLD_PROFILES\n"
                "def render_case():\n"
                "    pass\n",
                encoding='utf-8',
            )

            issues = rel.validate_release_tree(root)

            self.assertIn(
                'tests/golden_images/page_new_release_layout.png '
                '(golden image derived from CASE_SPECS is not listed in REQUIRED_PROJECT_GOLDEN_IMAGE_FILES)',
                issues,
            )

    def test_validate_release_tree_rejects_untracked_golden_case_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            (root / 'tests' / 'image_golden_cases.py').write_text(
                "CASE_SPECS = {'glyph_ichi': {}, 'page_new_release_layout': {}}\n"
                "def render_case():\n    pass\n"
                "THRESHOLD_PROFILES = {}\n",
                encoding='utf-8',
            )

            issues = rel.validate_release_tree(root)

            self.assertIn(
                'tests/golden_images/page_new_release_layout.png '
                '(golden image derived from CASE_SPECS is not listed in REQUIRED_PROJECT_GOLDEN_IMAGE_FILES)',
                issues,
            )

    def test_verify_release_zip_reports_untracked_golden_case_file(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'untracked-golden-case.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/image_golden_cases.py'})
                zf.writestr(
                    'tests/image_golden_cases.py',
                    "CASE_SPECS = {'glyph_ichi': {}, 'page_new_release_layout': {}}\n"
                    "def render_case():\n    pass\n"
                    "THRESHOLD_PROFILES = {}\n",
                )

            issues = rel.verify_release_zip_untracked_golden_case_files(zip_path)

            self.assertEqual(
                issues,
                [
                    'tests/golden_images/page_new_release_layout.png '
                    '(golden image derived from CASE_SPECS is not listed in REQUIRED_PROJECT_GOLDEN_IMAGE_FILES)',
                ],
            )

    def test_verify_release_zip_untracked_golden_case_files_prefers_exact_required_name(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'case-variant-golden-cases.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf, omit={'tests/image_golden_cases.py'})
                zf.writestr(
                    'tests/Image_Golden_Cases.py',
                    "CASE_SPECS = {'glyph_ichi': {}}\n"
                    "THRESHOLD_PROFILES = {}\n",
                )
                zf.writestr(
                    'tests/image_golden_cases.py',
                    "CASE_SPECS = {'glyph_ichi': {}, 'page_new_release_layout': {}}\n"
                    "THRESHOLD_PROFILES = {}\n",
                )

            issues = rel.verify_release_zip_untracked_golden_case_files(zip_path)

            self.assertEqual(
                issues,
                [
                    'tests/golden_images/page_new_release_layout.png '
                    '(golden image derived from CASE_SPECS is not listed in REQUIRED_PROJECT_GOLDEN_IMAGE_FILES)',
                ],
            )

    def test_verify_release_zip_required_project_support_files_ignores_non_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'generic.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('requirements.txt', 'requirements')

            self.assertEqual(rel.verify_release_zip_required_project_support_files(zip_path), [])

    def test_verify_release_zip_untracked_regression_test_files_accepts_nfc_equivalent_required_name(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'nfc-regression-test.zip'
            required_name = 'tests/test_Cafe\u0301.py'
            archive_name = 'tests/test_Caf\xe9.py'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                zf.writestr(archive_name, 'def test_cafe():\n    pass\n')

            with mock.patch.object(rel, 'REQUIRED_PROJECT_REGRESSION_TEST_FILES', (required_name,)):
                issues = rel.verify_release_zip_untracked_regression_test_files(zip_path)

            self.assertEqual(issues, [])

    def test_validate_release_tree_rejects_empty_required_project_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'tategakiXTC_gui_studio.py').write_text('app', encoding='utf-8')
            self._write_required_project_release_files(root)
            (root / 'README.md').write_text('  \n\t', encoding='utf-8')

            missing = rel.validate_release_tree(root)

            self.assertIn('README.md (required file is empty)', missing)

    def test_validate_release_tree_rejects_invalid_utf8_required_text_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'tategakiXTC_gui_studio.py').write_text('app', encoding='utf-8')
            self._write_required_project_release_files(root)
            (root / 'LICENSE.txt').write_bytes(b'\xff\xfe invalid license text')

            missing = rel.validate_release_tree(root)

            self.assertIn('LICENSE.txt (required text file must be UTF-8)', missing)

    def test_verify_release_zip_required_file_contents_reports_empty_and_non_ascii_batch(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'bad-required-contents.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(
                    zf,
                    omit={'README.md', 'run_gui.bat'},
                )
                zf.writestr('README.md', '  \n\t')
                zf.writestr('run_gui.bat', 'echo 起動\n')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                [
                    'README.md (required file is empty)',
                    'run_gui.bat (Windows batch files must be ASCII)',
                ],
            )

    def test_verify_release_zip_required_file_contents_ignores_non_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'generic.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', '')
                zf.writestr('run_gui.bat', 'echo 起動\n')

            self.assertEqual(rel.verify_release_zip_required_file_contents(zip_path), [])

    def test_verify_release_zip_required_file_contents_prefers_exact_required_name(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'case-variant-required-content.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf, omit={'README.md'})
                zf.writestr('readme.MD', 'case variant without guide markers')
                zf.writestr('README.md', self._required_release_file_payload('README.md'))

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(issues, [])

    def test_verify_release_zip_required_member_spellings_reports_single_case_variant(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'case-variant-required-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf, omit={'README.md'})
                zf.writestr('readme.MD', self._required_release_file_payload('README.md'))

            issues = rel.verify_release_zip_required_member_spellings(zip_path)

            self.assertEqual(
                issues,
                [
                    'README.md (required file is present only as readme.MD; '
                    'use canonical archive member spelling)',
                ],
            )

    def test_verify_release_zip_required_member_spellings_ignores_variant_when_exact_exists(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'case-variant-and-exact-required-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf, omit={'README.md'})
                zf.writestr('readme.MD', self._required_release_file_payload('README.md'))
                zf.writestr('README.md', self._required_release_file_payload('README.md'))

            issues = rel.verify_release_zip_required_member_spellings(zip_path)

            self.assertEqual(issues, [])


    def test_required_release_member_spelling_issue_reason_escapes_variant_name(self):
        issue = rel._required_release_member_spelling_issue_reason(
            'README.md',
            'README.md' + chr(10) + chr(0xE000),
        )

        self.assertEqual(
            issue,
            r'README.md (required file is present only as README.md\n\ue000; use canonical archive member spelling)',
        )

    def test_verify_release_zip_required_member_spellings_reports_leading_slash_required_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-required-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf, omit={'README.md'})
                zf.writestr('/README.md', self._required_release_file_payload('README.md'))

            issues = rel.verify_release_zip_required_member_spellings(zip_path)

            self.assertEqual(
                issues,
                [
                    'README.md (required file is present only as /README.md; '
                    'use canonical archive member spelling)',
                ],
            )

    def test_verify_release_zip_required_member_spellings_reports_app_marker_variant_without_exact_marker(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-app-marker.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    '/tategakiXTC_gui_studio.py',
                    self._required_release_file_payload('tategakiXTC_gui_studio.py'),
                )

            issues = rel.verify_release_zip_required_member_spellings(zip_path)

            self.assertEqual(
                issues,
                [
                    'tategakiXTC_gui_studio.py (required file is present only as '
                    '/tategakiXTC_gui_studio.py; use canonical archive member spelling)',
                ],
            )

    def test_verify_release_zip_required_public_docs_runs_for_app_marker_variant_without_exact_marker(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-app-marker-docs.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    '/tategakiXTC_gui_studio.py',
                    self._required_release_file_payload('tategakiXTC_gui_studio.py'),
                )

            missing = rel.verify_release_zip_required_public_docs(zip_path)

            self.assertEqual(
                missing,
                [
                    'README.md (required for project release archives)',
                    'LICENSE.txt (required for project release archives)',
                    'CHANGELOG.md (required for project release archives)',
                    'RELEASE_CHECKLIST.md (required for project release archives)',
                    'WINDOWS_SETUP.md (required for project release archives)',
                    'FAQ.md (required for project release archives)',
                    'KNOWN_LIMITATIONS.md (required for project release archives)',
                    'PUBLISH_CHECKLIST_v1_3_1.md (required for project release archives)',
                    f'{rel.RELEASE_NOTES_FILE} (required for project release archives)',
                ],
            )

    def test_verify_release_zip_required_project_support_files_runs_for_app_marker_variant_without_exact_marker(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-app-marker-support.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    '/tategakiXTC_gui_studio.py',
                    self._required_release_file_payload('tategakiXTC_gui_studio.py'),
                )

            missing = rel.verify_release_zip_required_project_support_files(zip_path)

            self.assertIn(
                'tategakiXTC_gui_studio.py (required for project release archives)',
                missing,
            )
            self.assertIn(
                'requirements.txt (required for project release archives)',
                missing,
            )

    def test_verify_release_zip_untracked_regression_test_files_runs_for_app_marker_variant_without_exact_marker(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-app-marker-untracked-regression.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    '/tategakiXTC_gui_studio.py',
                    self._required_release_file_payload('tategakiXTC_gui_studio.py'),
                )
                zf.writestr(
                    'tests/test_new_release_guard_regression.py',
                    'def test_new_release_guard():\n    pass\n',
                )

            issues = rel.verify_release_zip_untracked_regression_test_files(zip_path)

            self.assertEqual(
                issues,
                [
                    'tests/test_new_release_guard_regression.py '
                    '(regression test file is not listed in REQUIRED_PROJECT_REGRESSION_TEST_FILES)',
                ],
            )

    def test_verify_release_zip_required_file_list_issues_runs_for_app_marker_variant_without_exact_marker(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-app-marker-file-list.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    '/tategakiXTC_gui_studio.py',
                    self._required_release_file_payload('tategakiXTC_gui_studio.py'),
                )

            duplicated = (*rel.REQUIRED_PROJECT_RELEASE_FILES, 'README.md')
            with mock.patch.object(rel, 'REQUIRED_PROJECT_RELEASE_FILES', duplicated):
                issues = rel.verify_release_zip_required_file_list_issues(zip_path)

            self.assertEqual(
                issues,
                ['README.md (duplicate entry in REQUIRED_PROJECT_RELEASE_FILES)'],
            )

    def test_verify_release_zip_required_file_contents_runs_for_app_marker_variant_without_exact_marker(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-app-marker-required-contents.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    '/tategakiXTC_gui_studio.py',
                    self._required_release_file_payload('tategakiXTC_gui_studio.py'),
                )
                zf.writestr('README.md', '  \n\t')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(issues, ['README.md (required file is empty)'])

    def test_tree_and_zip_required_content_scans_share_bytes_helper(self):
        def sentinel_content_issues(name: str, data: bytes) -> list[str]:
            if name == 'README.md':
                return ['README.md (sentinel shared content check)']
            return []

        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)

            zip_path = Path(td) / 'project.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf)

            with mock.patch.object(
                rel,
                '_required_file_content_issues_from_bytes',
                side_effect=sentinel_content_issues,
            ):
                tree_issues = rel._tree_required_file_content_issues(root)
                zip_issues = rel.verify_release_zip_required_file_contents(zip_path)

        self.assertEqual(tree_issues, ['README.md (sentinel shared content check)'])
        self.assertEqual(zip_issues, ['README.md (sentinel shared content check)'])

    def test_validate_release_tree_rejects_broken_required_batch_targets(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'tategakiXTC_gui_studio.py').write_text('app', encoding='utf-8')
            self._write_required_project_release_files(root)
            (root / 'run_gui.bat').write_text('@echo off\necho placeholder\n', encoding='ascii')

            missing = rel.validate_release_tree(root)

            self.assertIn(
                'run_gui.bat (Windows batch file is missing required launch/dependency markers: '
                'tategakiXTC_gui_studio.py, requirements.txt, install_requirements.bat)',
                missing,
            )

    def test_verify_release_zip_required_file_contents_reports_missing_gui_asset_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-gui-asset.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'ui_assets/spin_up.svg'})
                zf.writestr('ui_assets/spin_up.svg', '<html>placeholder</html>\n')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                [
                    'ui_assets/spin_up.svg (GUI asset file is missing required SVG markers: '
                    '<svg, <path, viewBox)',
                ],
            )

    def test_validate_release_tree_rejects_broken_project_entry_point_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            (root / 'tategakiXTC_gui_studio.py').write_text('print(\"placeholder\")\n', encoding='utf-8')

            missing = rel.validate_release_tree(root)

            self.assertIn(
                'tategakiXTC_gui_studio.py (project app file is missing required implementation markers: '
                'class MainWindow, QApplication, _configure_app_logging)',
                missing,
            )

    def test_verify_release_zip_required_file_contents_reports_missing_app_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-app-module.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf, omit={'tategakiXTC_worker_logic.py'})
                zf.writestr('tategakiXTC_worker_logic.py', 'pass\n')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                [
                    'tategakiXTC_worker_logic.py (project app file is missing required implementation markers: '
                    'build_conversion_args, plan_output_path_for_target, build_conversion_summary)',
                ],
            )

    def test_validate_release_tree_rejects_broken_requirements_dependencies(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'tategakiXTC_gui_studio.py').write_text('app', encoding='utf-8')
            self._write_required_project_release_files(root)
            (root / 'requirements.txt').write_text('charset-normalizer\n', encoding='utf-8')

            missing = rel.validate_release_tree(root)

            self.assertIn(
                'requirements.txt (requirements file is missing required dependency markers: PySide6, Pillow)',
                missing,
            )

    def test_verify_mode_reports_missing_batch_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-batch.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'run_tests.bat'})
                zf.writestr('run_tests.bat', '@echo off\necho tests\n')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Invalid required file contents in release zip', str(raised.exception))
            self.assertIn('run_tests.bat', str(raised.exception))
            self.assertIn('unittest discover', str(raised.exception))
            self.assertIn('--verify', str(raised.exception))

    def test_verify_mode_reports_missing_requirements_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-requirements.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'requirements.txt'})
                zf.writestr('requirements.txt', 'Pillow\n')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Invalid required file contents in release zip', str(raised.exception))
            self.assertIn('requirements.txt', str(raised.exception))
            self.assertIn('PySide6', str(raised.exception))

    def test_validate_release_tree_rejects_broken_release_tooling_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            (root / 'mypy.ini').write_text('[mypy]\nfiles =\n', encoding='utf-8')

            issues = rel.validate_release_tree(root)

            self.assertEqual(
                issues,
                [
                    'mypy.ini (release tooling file is missing required test/build markers: '
                    'warn_unused_ignores = True, tategakiXTC_gui_core.py)',
                ],
            )

    def test_validate_release_tree_rejects_broken_test_support_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            (root / 'tests' / 'generate_golden_images.py').write_text('print("placeholder")\n', encoding='utf-8')

            issues = rel.validate_release_tree(root)

            self.assertEqual(
                issues,
                [
                    'tests/generate_golden_images.py (test support file is missing required regression-test markers: '
                    'check_all_cases, update_all_stale_cases, --check)',
                ],
            )

    def test_validate_release_tree_rejects_broken_tests_package_init_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            (root / 'tests' / '__init__.py').write_text('print("placeholder")\n', encoding='utf-8')

            issues = rel.validate_release_tree(root)

            self.assertEqual(
                issues,
                [
                    'tests/__init__.py (test support file is missing required regression-test markers: '
                    'Regression test package, from tests, local test helpers)',
                ],
            )

    def test_verify_release_zip_required_file_contents_reports_missing_release_tooling_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-release-tooling.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'.coveragerc'})
                zf.writestr('.coveragerc', 'source =\n')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                [
                    '.coveragerc (release tooling file is missing required test/build markers: '
                    'branch = True, tategakiXTC_worker_logic)',
                ],
            )

    def test_verify_release_zip_required_file_contents_reports_missing_test_support_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-test-support.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/studio_import_helper.py'})
                zf.writestr('tests/studio_import_helper.py', 'print("placeholder")\n')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                [
                    'tests/studio_import_helper.py (test support file is missing required regression-test markers: '
                    'load_studio_module, _install_pyside6_stubs, tategakiXTC_gui_studio)',
                ],
            )

    def test_verify_release_zip_required_file_contents_reports_missing_regression_test_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-regression-test.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/test_release_hygiene_regression.py'})
                zf.writestr('tests/test_release_hygiene_regression.py', 'print("placeholder")\n')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                [
                    'tests/test_release_hygiene_regression.py (regression test file is missing required test-case markers: def test_)',
                ],
            )

    def test_validate_release_tree_requires_golden_fixture_files_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(
                root,
                omit={'tests/fixtures/sample_notes.md', 'tests/golden_images/page_compound_layout.png'},
            )

            missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                [
                    'tests/fixtures/sample_notes.md (required for project release archives)',
                    'tests/golden_images/page_compound_layout.png (required for project release archives)',
                ],
            )

    def test_verify_release_zip_required_project_support_files_requires_golden_fixture_files(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'missing-golden-fixtures.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(
                    zf,
                    omit={'tests/fixtures/epub/chapter1.xhtml', 'tests/golden_images/glyph_ichi.png'},
                )

            missing = rel.verify_release_zip_required_project_support_files(zip_path)

            self.assertEqual(
                missing,
                [
                    'tests/fixtures/epub/chapter1.xhtml (required for project release archives)',
                    'tests/golden_images/glyph_ichi.png (required for project release archives)',
                ],
            )

    def test_validate_release_tree_requires_epub_fixture_assets_for_project_archives(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(
                root,
                omit={'tests/fixtures/epub/styles/main.css', 'tests/fixtures/epub/images/scene.png'},
            )

            missing = rel.validate_release_tree(root)

            self.assertEqual(
                missing,
                [
                    'tests/fixtures/epub/styles/main.css (required for project release archives)',
                    'tests/fixtures/epub/images/scene.png (required for project release archives)',
                ],
            )

    def test_verify_release_zip_required_project_support_files_requires_epub_fixture_assets(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'missing-epub-fixture-assets.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(
                    zf,
                    omit={'tests/fixtures/epub/styles/main.css', 'tests/fixtures/epub/images/scene.png'},
                )

            missing = rel.verify_release_zip_required_project_support_files(zip_path)

            self.assertEqual(
                missing,
                [
                    'tests/fixtures/epub/styles/main.css (required for project release archives)',
                    'tests/fixtures/epub/images/scene.png (required for project release archives)',
                ],
            )

    def test_validate_release_tree_rejects_broken_test_fixture_markers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            self._write_required_project_release_files(root)
            (root / 'tests' / 'fixtures' / 'sample_aozora.txt').write_text('placeholder\n', encoding='utf-8')

            issues = rel.validate_release_tree(root)

            self.assertEqual(
                issues,
                [
                    'tests/fixtures/sample_aozora.txt (test fixture file is missing required fixture markers: '
                    '｜吾輩《わがはい》, ［＃改ページ］, 第二節)',
                ],
            )

    def test_verify_release_zip_required_file_contents_reports_invalid_golden_png(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-golden-png.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/golden_images/tatechuyoko_2025.png'})
                zf.writestr('tests/golden_images/tatechuyoko_2025.png', b'not a png')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                ['tests/golden_images/tatechuyoko_2025.png (golden image file must be a PNG image)'],
            )

    def test_verify_release_zip_required_file_contents_reports_invalid_fixture_png(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-fixture-png.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/fixtures/epub/images/scene.png'})
                zf.writestr('tests/fixtures/epub/images/scene.png', b'not a png')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                ['tests/fixtures/epub/images/scene.png (test fixture image file must be a PNG image)'],
            )

    def test_verify_release_zip_required_file_contents_reports_missing_epub_css_markers(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'broken-epub-css.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/fixtures/epub/styles/main.css'})
                zf.writestr('tests/fixtures/epub/styles/main.css', 'placeholder\n')

            issues = rel.verify_release_zip_required_file_contents(zip_path)

            self.assertEqual(
                issues,
                [
                    'tests/fixtures/epub/styles/main.css (test fixture file is missing required fixture markers: '
                    '.hidden, pagebreak, strongish)'
                ],
            )

    def test_build_release_zip_rejects_project_archive_with_missing_public_docs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'tategakiXTC_gui_studio.py').write_text('app', encoding='utf-8')
            self._write_required_project_release_files(
                root,
                omit={'LICENSE.txt', 'CHANGELOG.md', rel.RELEASE_NOTES_FILE},
            )
            out = root / 'dist' / 'release.zip'

            with self.assertRaises(RuntimeError) as raised:
                rel.build_release_zip(root, out)

            self.assertIn('release zip missing required assets', str(raised.exception))
            self.assertIn('LICENSE.txt', str(raised.exception))
            self.assertFalse(out.exists())

    def test_verify_mode_reports_backslash_member_names_as_excluded_entries(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'backslash-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._writestr_raw_member(zf, r'docs\page.txt', 'windows separator')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Excluded entries found in release zip', str(raised.exception))
            self.assertIn(r'docs\page.txt', str(raised.exception))

    def test_verify_mode_reports_directory_member_entries_as_excluded_entries(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'directory-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('templates/', '')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Excluded entries found in release zip', str(raised.exception))
            self.assertIn('templates/', str(raised.exception))

    def test_verify_mode_reports_invalid_required_file_list(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'duplicate-required-list.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)

            duplicated = (*rel.REQUIRED_PROJECT_RELEASE_FILES, 'README.md')
            with mock.patch.object(rel, 'REQUIRED_PROJECT_RELEASE_FILES', duplicated):
                with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                    parse_args_mock.return_value = type('Args', (), {
                        'verify': str(zip_path),
                        'root': '.',
                        'output': '',
                    })()
                    with self.assertRaises(SystemExit) as raised:
                        rel.main()

            self.assertIn('Invalid required file list in release zip', str(raised.exception))
            self.assertIn('README.md', str(raised.exception))

    def test_verify_mode_reports_untracked_regression_test_files(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'untracked-regression-tests.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)
                zf.writestr('tests/test_new_release_guard_regression.py', 'def test_new_release_guard():\n    pass\n')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Untracked regression tests found in release zip', str(raised.exception))
            self.assertIn('tests/test_new_release_guard_regression.py', str(raised.exception))

    def test_verify_release_zip_untracked_regression_test_files_ignores_backslash_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'backslash-untracked-regression-test.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf)
                self._writestr_raw_member(zf, r'tests\test_new_release_guard_regression.py', 'def test_new_release_guard():\n    pass\n')

            self.assertEqual(rel.verify_release_zip_untracked_regression_test_files(zip_path), [])
            self.assertEqual(rel.verify_release_zip(zip_path), [r'tests\test_new_release_guard_regression.py'])

    def test_verify_mode_reports_untracked_golden_case_files(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'untracked-golden-cases.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('tategakiXTC_gui_studio.py', self._required_release_file_payload('tategakiXTC_gui_studio.py'))
                self._write_required_project_release_zip_members(zf, omit={'tests/image_golden_cases.py'})
                zf.writestr(
                    'tests/image_golden_cases.py',
                    "CASE_SPECS = {'glyph_ichi': {}, 'page_new_release_layout': {}}\n"
                    "def render_case():\n    pass\n"
                    "THRESHOLD_PROFILES = {}\n",
                )

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Untracked golden case files found in release zip', str(raised.exception))
            self.assertIn('tests/golden_images/page_new_release_layout.png', str(raised.exception))

    def test_verify_mode_reports_non_canonical_required_member_spelling(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'non-canonical-required-member.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_required_project_release_zip_members(zf, omit={'README.md'})
                zf.writestr('readme.MD', self._required_release_file_payload('README.md'))

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Non-canonical required member spellings found in release zip', str(raised.exception))
            self.assertIn('README.md', str(raised.exception))
            self.assertIn('readme.MD', str(raised.exception))

    def test_verify_release_zip_required_assets_accepts_case_varied_license_locations(self):
        with tempfile.TemporaryDirectory() as td:
            for license_name in (
                'license_ofl.TXT',
                'LICENSE_OFL.txt',
                'Font/LICENSE_OFL.txt',
                'fonts/license_ofl.txt',
                'FONTS/LICENSE_OFL.TXT',
            ):
                zip_path = Path(td) / f'{license_name.replace("/", "_")}.zip'
                with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr('FONTS/NotoSansJP-Regular.TTF', b'font')
                    zf.writestr(license_name, 'license')

                self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [], license_name)

    def test_verify_release_zip_required_assets_requires_license_for_case_varied_font_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-without-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('FONTS/NotoSansJP-Regular.TTF', b'font')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_verify_release_zip_required_assets_ignores_non_canonical_license_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-backslash-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('FONTS/NotoSansJP-Regular.TTF', b'font')
                self._writestr_raw_member(zf, r'FONTS\LICENSE_OFL.TXT', 'license')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_verify_release_zip_required_assets_ignores_non_canonical_font_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'backslash-font-without-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._writestr_raw_member(zf, r'FONTS\NotoSansJP-Regular.TTF', b'font')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_ignores_leading_slash_license_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-leading-slash-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('FONTS/NotoSansJP-Regular.TTF', b'font')
                zf.writestr('/FONTS/LICENSE_OFL.TXT', 'license')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_verify_release_zip_required_assets_ignores_leading_slash_root_license_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-leading-slash-root-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('FONTS/NotoSansJP-Regular.TTF', b'font')
                zf.writestr('/LICENSE_OFL.TXT', 'license')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_verify_release_zip_required_assets_ignores_nested_license_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-nested-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/subdir/NotoSansJP-Regular.TTF', b'font')
                zf.writestr('fonts/subdir/LICENSE_OFL.TXT', 'license')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_verify_release_zip_required_assets_accepts_root_license_for_nested_bundled_font(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'nested-font-with-root-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/subdir/NotoSansJP-Regular.OTC', b'font')
                zf.writestr('LICENSE_OFL.TXT', 'license')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_rejects_empty_bundled_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-empty-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', '  \n\t')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_verify_release_zip_required_assets_rejects_bom_only_bundled_font_license(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-bom-only-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', b'\xef\xbb\xbf  \n\t')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_verify_release_zip_required_assets_accepts_bom_prefixed_bundled_font_license_text(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-bom-prefixed-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', b'\xef\xbb\xbfOpen Font License')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_rejects_utf16_utf32_whitespace_only_license(self):
        payloads = [
            '   \n\t'.encode('utf-16'),
            b'\xfe\xff' + '   \n\t'.encode('utf-16-be'),
            '   \n\t'.encode('utf-32'),
            b'\x00\x00\xfe\xff' + '   \n\t'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:4]):
                with tempfile.TemporaryDirectory() as td:
                    zip_path = Path(td) / 'font-with-utf16-utf32-empty-license.zip'
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                        zf.writestr('LICENSE_OFL.TXT', payload)

                    missing = rel.verify_release_zip_required_assets(zip_path)

                self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_verify_release_zip_required_assets_accepts_utf16_utf32_bom_prefixed_license_text(self):
        payloads = [
            'Open Font License'.encode('utf-16'),
            b'\xfe\xff' + 'Open Font License'.encode('utf-16-be'),
            'Open Font License'.encode('utf-32'),
            b'\x00\x00\xfe\xff' + 'Open Font License'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:4]):
                with tempfile.TemporaryDirectory() as td:
                    zip_path = Path(td) / 'font-with-utf16-utf32-license.zip'
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                        zf.writestr('LICENSE_OFL.TXT', payload)

                    self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_rejects_malformed_bom_license(self):
        payloads = [
            b'\xff\xfe ',
            b'\xfe\xff ',
            b'\xff\xfe\x00\x00 ',
            b'\x00\x00\xfe\xff ',
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:4]):
                with tempfile.TemporaryDirectory() as td:
                    zip_path = Path(td) / 'font-with-malformed-bom-license.zip'
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                        zf.writestr('LICENSE_OFL.TXT', payload)

                    missing = rel.verify_release_zip_required_assets(zip_path)

                self.assertEqual(
                    missing,
                    ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
                )

    def test_verify_release_zip_required_assets_rejects_non_utf8_license(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-non-utf8-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', b'Open Font License \xff')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(
                missing,
                ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
            )

    def test_verify_release_zip_required_assets_rejects_undeclared_utf16_utf32_license(self):
        payloads = [
            'Open Font License'.encode('utf-16-le'),
            'Open Font License'.encode('utf-16-be'),
            'Open Font License'.encode('utf-32-le'),
            'Open Font License'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload[:8]):
                with tempfile.TemporaryDirectory() as td:
                    zip_path = Path(td) / 'font-with-undeclared-utf16-utf32-license.zip'
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                        zf.writestr('LICENSE_OFL.TXT', payload)

                    missing = rel.verify_release_zip_required_assets(zip_path)

                self.assertEqual(
                    missing,
                    ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
                )

    def test_verify_release_zip_required_assets_rejects_short_undeclared_utf16_utf32_license(self):
        payloads = [
            'OF'.encode('utf-16-le'),
            'OF'.encode('utf-16-be'),
            'O'.encode('utf-32-le'),
            'O'.encode('utf-32-be'),
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                with tempfile.TemporaryDirectory() as td:
                    zip_path = Path(td) / 'font-with-short-undeclared-utf16-license.zip'
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                        zf.writestr('LICENSE_OFL.TXT', payload)

                    missing = rel.verify_release_zip_required_assets(zip_path)

                self.assertEqual(
                    missing,
                    ['LICENSE_OFL.txt (bundled font license could not be decoded as UTF-8/BOM-declared text)'],
                )

    def test_verify_release_zip_required_assets_rejects_control_only_license(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-control-only-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', b'\x00\x1f\x7f')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (bundled font license must not be empty)'])

    def test_verify_release_zip_required_assets_accepts_text_after_control_license(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-control-then-text-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', b'\x00Open Font License')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_accepts_valid_license_after_non_utf8_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-non-utf8-and-valid-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', b'Open Font License \xff')
                zf.writestr('fonts/LICENSE_OFL.TXT', 'license')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_accepts_valid_license_after_malformed_bom_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-malformed-and-valid-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', b'\xff\xfe ')
                zf.writestr('fonts/LICENSE_OFL.TXT', 'license')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_accepts_non_empty_license_when_empty_candidate_exists(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-empty-and-non-empty-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', '')
                zf.writestr('fonts/LICENSE_OFL.TXT', 'license')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_accepts_readable_license_after_unreadable_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-unreadable-and-readable-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', 'unreadable candidate')
                zf.writestr('fonts/LICENSE_OFL.TXT', 'license')
            original_read = zipfile.ZipFile.read

            def fake_read(zf, name, pwd=None):
                filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
                if filename == 'LICENSE_OFL.TXT':
                    raise zipfile.BadZipFile('mock license read failure')
                return original_read(zf, name, pwd)

            with mock.patch.object(zipfile.ZipFile, 'read', autospec=True, side_effect=fake_read):
                self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_reports_read_error_when_no_readable_license_candidate_exists(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-with-unreadable-and-empty-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.OTF', b'font')
                zf.writestr('LICENSE_OFL.TXT', 'unreadable candidate')
                zf.writestr('fonts/LICENSE_OFL.TXT', '   ')
            original_read = zipfile.ZipFile.read

            def fake_read(zf, name, pwd=None):
                filename = name.filename if isinstance(name, zipfile.ZipInfo) else name
                if filename == 'LICENSE_OFL.TXT':
                    raise zipfile.BadZipFile('mock license read failure')
                return original_read(zf, name, pwd)

            with mock.patch.object(zipfile.ZipFile, 'read', autospec=True, side_effect=fake_read):
                missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(
                missing,
                ['LICENSE_OFL.txt (bundled font license could not be read: mock license read failure)'],
            )

    def test_verify_release_zip_required_assets_ignores_font_suffix_lookalike_members(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'font-lookalike-without-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('fonts/NotoSansJP-Regular.ttf.bak', b'not a font')
                zf.writestr('fonts/NotoSansJP-Regular.otf.txt', b'not a font')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_required_assets_requires_license_for_nested_bundled_font(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'nested-font-without-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('Font/subdir/NotoSansJP-Regular.TTC', b'font')

            missing = rel.verify_release_zip_required_assets(zip_path)

            self.assertEqual(missing, ['LICENSE_OFL.txt (required when bundled fonts are included)'])

    def test_verify_release_zip_required_assets_ignores_leading_slash_font_member(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'leading-slash-font-without-license.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('/FONTS/NotoSansJP-Regular.TTF', b'font')

            self.assertEqual(rel.verify_release_zip_required_assets(zip_path), [])

    def test_verify_release_zip_duplicate_members_reports_repeated_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'duplicate-release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    zf.writestr('README.md', 'first')
                    zf.writestr('docs/page.txt', 'ok')
                    zf.writestr('README.md', 'second')
                    zf.writestr(r'docs\page.txt', 'duplicate after normalization')

            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
            backslash_name = r'docs\page.txt'
            duplicate_page_name = backslash_name if backslash_name in names else 'docs/page.txt'
            duplicates = rel.verify_release_zip_duplicate_members(zip_path)

            self.assertEqual(
                duplicates,
                [
                    'README.md (duplicate/collision group: README.md, README.md)',
                    f'{duplicate_page_name} (duplicate/collision group: docs/page.txt, {duplicate_page_name})',
                ],
            )

    def test_verify_release_zip_duplicate_members_reports_unicode_normalization_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'unicode-collision-release.zip'
            nfc = 'docs/ガイド.txt'
            nfd = 'docs/ガイド.txt'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(nfc, 'first')
                zf.writestr(nfd, 'unicode normalization collision')

            duplicates = rel.verify_release_zip_duplicate_members(zip_path)

            self.assertEqual(
                duplicates,
                [f'{nfd} (duplicate/collision group: {nfc}, {nfd})'],
            )

    def test_verify_release_zip_duplicate_members_reports_windows_case_collisions(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'case-collision-release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'first')
                zf.writestr('readme.MD', 'case collision on Windows')
                zf.writestr('ReadMe.md', 'third spelling collision on Windows')
                zf.writestr('Font/LICENSE_OFL.txt', 'license')
                zf.writestr('font/license_ofl.TXT', 'case collision on Windows')

            duplicates = rel.verify_release_zip_duplicate_members(zip_path)

            self.assertEqual(
                duplicates,
                [
                    'ReadMe.md (duplicate/collision group: README.md, readme.MD, ReadMe.md)',
                    'font/license_ofl.TXT (duplicate/collision group: Font/LICENSE_OFL.txt, font/license_ofl.TXT)',
                ],
            )

    def test_verify_release_zip_windows_path_lengths_reports_long_member_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'long-path-release.zip'
            long_dir = 'a' * 120
            long_name = 'b' * 121 + '.txt'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'ok')
                zf.writestr(f'{long_dir}/{long_name}', 'too long for portable Windows extraction')

            long_entries = rel.verify_release_zip_windows_path_lengths(zip_path)

            self.assertEqual(
                long_entries,
                [f'{long_dir}/{long_name} (path too long (246 UTF-16 units > 240))'],
            )

    def test_verify_release_zip_windows_path_lengths_reports_long_path_parts(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'long-part-release.zip'
            long_part = 'a' * 201
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f'{long_part}/README.md', 'too long part')

            long_entries = rel.verify_release_zip_windows_path_lengths(zip_path)

            self.assertEqual(
                long_entries,
                [f'{long_part}/README.md (path part too long (201 UTF-16 units > 200))'],
            )

    def test_verify_release_zip_windows_path_lengths_reports_raw_noncanonical_names(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'long-raw-name-release.zip'
            long_part = 'a' * 201
            raw_name = rf'docs\{long_part}.txt'
            normalized_name = f'docs/{long_part}.txt'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._writestr_raw_member(zf, raw_name, 'too long noncanonical member')

            long_entries = rel.verify_release_zip_windows_path_lengths(zip_path)

            self.assertEqual(
                long_entries,
                [
                    f'{raw_name} (normalized: {normalized_name}) '
                    f'(path part too long (205 UTF-16 units > 200))'
                ],
            )

    def test_build_release_zip_removes_archive_when_windows_long_paths_exist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            long_path = root / ('a' * 201 + '.txt')
            try:
                long_path.write_text('too long', encoding='utf-8')
            except OSError as exc:
                self.skipTest(f'long path fixture is not writable on this filesystem: {exc}')
            out = root / 'dist' / 'release.zip'

            with self.assertRaises(RuntimeError) as raised:
                rel.build_release_zip(root, out)

            self.assertIn('Windows-long paths', str(raised.exception))
            self.assertFalse(out.exists())

    def test_build_release_zip_removes_archive_when_windows_case_collisions_exist(self):
        if os.name == 'nt':
            self.skipTest('case-collision source-tree fixture is filesystem-dependent on Windows')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            readme = root / 'README.md'
            variant = root / 'readme.MD'
            readme.write_text('ok', encoding='utf-8')
            variant.write_text('collision', encoding='utf-8')
            if readme.read_text(encoding='utf-8') == 'collision':
                self.skipTest('case-collision fixture cannot be represented on this filesystem')
            out = root / 'dist' / 'release.zip'

            with self.assertRaises(RuntimeError) as raised:
                rel.build_release_zip(root, out)

            self.assertIn('duplicate entries', str(raised.exception))
            self.assertIn('readme.MD', str(raised.exception))
            self.assertFalse(out.exists())

    def test_verify_mode_reports_duplicate_members(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'duplicate-release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', UserWarning)
                    zf.writestr('README.md', 'first')
                    zf.writestr('README.md', 'second')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Duplicate entries found in release zip', str(raised.exception))
            self.assertIn('README.md', str(raised.exception))

    def test_verify_mode_reports_windows_long_paths(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'long-path-release.zip'
            long_dir = 'a' * 120
            long_name = 'b' * 121 + '.txt'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f'{long_dir}/{long_name}', 'too long')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Windows-long paths found in release zip', str(raised.exception))
            self.assertIn('path too long', str(raised.exception))

    def test_verify_mode_reports_unsafe_member_modes(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'symlink-release.zip'
            link_info = zipfile.ZipInfo('docs/link-to-outside')
            link_info.create_system = 3
            link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(link_info, '../outside.txt')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock:
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()
                with self.assertRaises(SystemExit) as raised:
                    rel.main()

            self.assertIn('Unsafe member modes found in release zip', str(raised.exception))
            self.assertIn('docs/link-to-outside (symlink; mode 0o120777; external_attr 0xa1ff0000; create_system 3)', str(raised.exception))

    def test_verify_mode_runs_untracked_golden_case_scan_once(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'verify-once-release.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('README.md', 'ok')

            with mock.patch('build_release_zip.parse_args') as parse_args_mock, \
                 mock.patch.object(rel, 'verify_release_zip_integrity', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_duplicate_members', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_unsafe_member_modes', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_windows_path_lengths', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_required_member_spellings', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_required_public_docs', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_required_project_support_files', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_untracked_regression_test_files', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_untracked_golden_case_files', return_value=[]) as golden_mock, \
                 mock.patch.object(rel, 'verify_release_zip_required_file_list_issues', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_required_file_contents', return_value=[]), \
                 mock.patch.object(rel, 'verify_release_zip_required_assets', return_value=[]), \
                 mock.patch('builtins.print'):
                parse_args_mock.return_value = type('Args', (), {
                    'verify': str(zip_path),
                    'root': '.',
                    'output': '',
                })()

                self.assertEqual(rel.main(), 0)

            golden_mock.assert_called_once_with(zip_path.resolve())

    def test_verify_mode_reports_bad_zip_before_member_or_asset_scans(self):
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / 'bad-release.zip'
            zip_path.write_bytes(b'not a zip file')

            with mock.patch.object(rel, 'verify_release_zip_duplicate_members', side_effect=AssertionError('duplicate scan should be skipped')):
                with mock.patch.object(rel, 'verify_release_zip_unsafe_member_modes', side_effect=AssertionError('mode scan should be skipped')):
                    with mock.patch.object(rel, 'verify_release_zip_windows_path_lengths', side_effect=AssertionError('path length scan should be skipped')):
                        with mock.patch.object(rel, 'verify_release_zip', side_effect=AssertionError('member scan should be skipped')):
                            with mock.patch.object(rel, 'verify_release_zip_required_public_docs', side_effect=AssertionError('public doc scan should be skipped')):
                                with mock.patch.object(rel, 'verify_release_zip_required_project_support_files', side_effect=AssertionError('support file scan should be skipped')):
                                    with mock.patch.object(rel, 'verify_release_zip_required_file_list_issues', side_effect=AssertionError('required file list scan should be skipped')):
                                        with mock.patch.object(rel, 'verify_release_zip_required_file_contents', side_effect=AssertionError('required file content scan should be skipped')):
                                            with mock.patch.object(rel, 'verify_release_zip_required_assets', side_effect=AssertionError('asset scan should be skipped')):
                                                with mock.patch.object(rel, 'parse_args') as parse_args_mock:
                                                    parse_args_mock.return_value = type('Args', (), {
                                                        'verify': str(zip_path),
                                                        'root': '.',
                                                        'output': '',
                                                    })()
                                                    with self.assertRaises(SystemExit) as raised:
                                                        rel.main()

            self.assertIn('Integrity check failed in release zip', str(raised.exception))
            self.assertIn('<bad zip>:', str(raised.exception))

    def test_build_release_zip_checks_integrity_before_member_or_asset_scans(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            out = root / 'dist' / 'release.zip'

            with mock.patch.object(rel, 'verify_release_zip_integrity', return_value=['README.md']):
                with mock.patch.object(rel, 'verify_release_zip_duplicate_members', side_effect=AssertionError('duplicate scan should be skipped')):
                    with mock.patch.object(rel, 'verify_release_zip_unsafe_member_modes', side_effect=AssertionError('mode scan should be skipped')):
                        with mock.patch.object(rel, 'verify_release_zip_windows_path_lengths', side_effect=AssertionError('path length scan should be skipped')):
                            with mock.patch.object(rel, 'verify_release_zip', side_effect=AssertionError('member scan should be skipped')):
                                with mock.patch.object(rel, 'verify_release_zip_required_public_docs', side_effect=AssertionError('public doc scan should be skipped')):
                                    with mock.patch.object(rel, 'verify_release_zip_required_project_support_files', side_effect=AssertionError('support file scan should be skipped')):
                                        with mock.patch.object(rel, 'verify_release_zip_required_file_list_issues', side_effect=AssertionError('required file list scan should be skipped')):
                                            with mock.patch.object(rel, 'verify_release_zip_required_file_contents', side_effect=AssertionError('required file content scan should be skipped')):
                                                with mock.patch.object(rel, 'verify_release_zip_required_assets', side_effect=AssertionError('asset scan should be skipped')):
                                                    with self.assertRaises(RuntimeError) as raised:
                                                        rel.build_release_zip(root, out)

            self.assertIn('release zip failed integrity check', str(raised.exception))
            self.assertFalse(out.exists())

    def test_build_release_zip_removes_archive_when_duplicate_members_are_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            out = root / 'dist' / 'release.zip'

            with mock.patch.object(rel, 'verify_release_zip_duplicate_members', return_value=['README.md']):
                with self.assertRaises(RuntimeError) as raised:
                    rel.build_release_zip(root, out)

            self.assertIn('duplicate entries', str(raised.exception))
            self.assertFalse(out.exists())

    def test_build_release_zip_removes_archive_when_unsafe_member_modes_are_reported(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            out = root / 'dist' / 'release.zip'

            with mock.patch.object(rel, 'verify_release_zip_unsafe_member_modes', return_value=['docs/link (symlink; mode 0o120777; external_attr 0xa1ff0000; create_system 3)']):
                with self.assertRaises(RuntimeError) as raised:
                    rel.build_release_zip(root, out)

            self.assertIn('unsafe member modes', str(raised.exception))
            self.assertFalse(out.exists())

    def test_build_release_zip_verifies_written_archive_via_existing_zip_inspection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            out = root / 'dist' / 'release.zip'

            with mock.patch.object(rel, 'verify_release_zip', return_value=['__pycache__/bad.pyc']):
                with self.assertRaises(RuntimeError):
                    rel.build_release_zip(root, out)

            self.assertFalse(out.exists())

    def test_build_release_zip_removes_archive_when_integrity_check_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'project'
            root.mkdir(parents=True, exist_ok=True)
            (root / 'README.md').write_text('ok', encoding='utf-8')
            out = root / 'dist' / 'release.zip'

            with mock.patch.object(rel, 'verify_release_zip_integrity', return_value=['README.md']):
                with self.assertRaises(RuntimeError):
                    rel.build_release_zip(root, out)

            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
