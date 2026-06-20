from __future__ import annotations

from pathlib import Path
import unittest


class ReleaseDocsRegressionTests(unittest.TestCase):
    def test_readme_matches_current_left_pane_order(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('Left Preset/Spec → Center Settings/Results → Right Preview', readme)

    def test_readme_mentions_current_conflict_menu_route(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('右上の歯車メニュー内「その他オプション > 同名出力」', readme)
        self.assertNotIn('同梱 ini', readme)

    def test_readme_explains_source_only_font_fallback(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('source-only 配布物', readme)
        self.assertIn('system font へ自動フォールバック', readme)
        self.assertIn('skip されます', readme)
        self.assertIn('source-only リポジトリ構成', readme)

    def test_readme_mentions_python_3_10_typing_compat(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('Python は **3.10 / 3.11 / 3.12 系**を想定', readme)
        self.assertIn('typing_extensions', readme)

    def test_readme_mentions_batch_scripts_switch_to_bundled_folder(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('run_gui.bat', readme)
        self.assertIn('run_tests.bat', readme)
        self.assertIn('同梱スクリプトのあるフォルダへ自動移動', readme)


    def test_readme_documents_gui_quick_start_steps(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('### 1. Python を確認する', readme)
        self.assertIn('py -3.12 --version', readme)
        self.assertIn('### 2. 依存ライブラリを入れる', readme)
        self.assertIn('install_requirements.bat', readme)
        self.assertIn('py -3.12 -m pip install', readme)
        self.assertIn('py -3.12 -m venv .venv', readme)
        self.assertIn('.venv\\Scripts\\activate', readme)
        self.assertIn('.venv\\Scripts\\python.exe', readme)
        self.assertIn('### 3. 起動する', readme)
        self.assertIn('run_gui.bat', readme)

    def test_readme_documents_font_folder_release_zip_boundary(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('## Font フォルダーの配置', readme)
        self.assertIn('Font/NotoSansJP-Regular.ttf', readme)
        self.assertIn('LICENSE_OFL.txt', readme)
        self.assertIn('public zip 作成を停止します', readme)
        self.assertIn('build_release_zip.py` 実行前に `Font/` / `fonts/` を置かないか、一時的に退避', readme)

    def test_changelog_is_clean_single_title(self) -> None:
        changelog = Path('CHANGELOG.md').read_text(encoding='utf-8')
        self.assertTrue(changelog.startswith('# CHANGELOG\n'))
        self.assertEqual(changelog.count('# CHANGELOG'), 1)
        import tategakiXTC_release_metadata as release_metadata

        self.assertIn(f'## v{release_metadata.PUBLIC_VERSION}', changelog)
        self.assertIn(f'## v{release_metadata.PREVIOUS_PUBLIC_VERSION}', changelog)
        self.assertIn('## v1.3.3.26', changelog)
        self.assertIn('## v1.3.3.25', changelog)
        self.assertIn('## v1.3.3.24', changelog)
        self.assertIn('## v1.3.3.23', changelog)
        self.assertIn('## v1.3.3.22', changelog)
        self.assertIn('## v1.3.3.21', changelog)
        self.assertIn('## v1.3.3.20', changelog)
        self.assertIn('## v1.3.3.3', changelog)
        self.assertIn('## v1.3.3.2', changelog)
        self.assertIn('## v1.3.3.1', changelog)
        self.assertIn('## v1.3.3.0', changelog)
        self.assertIn('## v1.2.2', changelog)
        self.assertIn('v1.2.2 は、v1.2.1 を基準に、波ダッシュ・チルダ類の縦書き表示調整を追加した安定版です。', changelog)
        self.assertIn('## v1.1.0', changelog)
        self.assertIn('v1.0.2 の次の正式版 v1.1.0', changelog)

    def test_release_notes_exist_for_current_public_version(self) -> None:
        import tategakiXTC_release_metadata as release_metadata

        notes_path = Path(release_metadata.RELEASE_NOTES_FILE)
        self.assertTrue(notes_path.exists(), release_metadata.RELEASE_NOTES_FILE)
        notes = notes_path.read_text(encoding='utf-8')
        self.assertIn(f'v{release_metadata.PUBLIC_VERSION}', notes)
        self.assertIn('CHANGELOG', notes)



    def test_current_public_release_docs_are_consolidated(self) -> None:
        self.assertTrue(Path('docs/release_notes/RELEASE_NOTES_v1_4_2.md').exists())
        self.assertTrue(Path('docs/publish_checklists/PUBLISH_CHECKLIST_v1_4_2.md').exists())
        self.assertTrue(Path('docs/release_notes/RELEASE_NOTES_v1_4_1.md').exists())
        self.assertTrue(Path('docs/publish_checklists/PUBLISH_CHECKLIST_v1_4_1.md').exists())
        self.assertTrue(Path('docs/release_notes/RELEASE_NOTES_v1_4_0.md').exists())
        self.assertTrue(Path('docs/publish_checklists/PUBLISH_CHECKLIST_v1_4_0.md').exists())
        self.assertTrue(Path('docs/release_notes/RELEASE_NOTES_v1_3_6.md').exists())
        self.assertTrue(Path('docs/publish_checklists/PUBLISH_CHECKLIST_v1_3_6.md').exists())
        self.assertFalse(list(Path('docs/release_notes').glob('RELEASE_NOTES_v1_3_8*.md')))
        self.assertFalse(list(Path('docs/publish_checklists').glob('PUBLISH_CHECKLIST_v1_3_8*.md')))
        self.assertFalse(list(Path('docs/release_notes').glob('RELEASE_NOTES_v1_4_1_*.md')))
        self.assertFalse(list(Path('docs/publish_checklists').glob('PUBLISH_CHECKLIST_v1_4_1_*.md')))
        self.assertFalse(list(Path('docs/release_notes').glob('RELEASE_NOTES_v1_4_2_*.md')))
        self.assertFalse(list(Path('docs/publish_checklists').glob('PUBLISH_CHECKLIST_v1_4_2_*.md')))
        self.assertFalse(list(Path('docs/release_notes').glob('RELEASE_NOTES_v1_4_3_*.md')))
        self.assertFalse(list(Path('docs/publish_checklists').glob('PUBLISH_CHECKLIST_v1_4_3_*.md')))
        self.assertFalse(list(Path('docs/release_notes').glob('RELEASE_NOTES_v1_5_0_*.md')))
        self.assertFalse(list(Path('docs/publish_checklists').glob('PUBLISH_CHECKLIST_v1_5_0_*.md')))
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('docs/release_notes/RELEASE_NOTES_v1_4_2.md` — v1.4.1 から v1.4.2 までの差分まとめ', readme)
        self.assertIn('docs/release_notes/RELEASE_NOTES_v1_4_1.md` — v1.4.0 から v1.4.1 までの差分まとめ', readme)
        self.assertIn('docs/release_notes/RELEASE_NOTES_v1_4_0.md` — v1.3.6 から v1.4.0 までの差分まとめ', readme)
        self.assertIn('docs/release_notes/RELEASE_NOTES_v1_3_6.md` — v1.3.5 から v1.3.6 までの差分まとめ', readme)
        self.assertNotIn('docs/release_notes/RELEASE_NOTES_v1_3_8_40.md', readme)
        release_checklist = Path('RELEASE_CHECKLIST.md').read_text(encoding='utf-8')
        self.assertNotIn('docs/publish_checklists/PUBLISH_CHECKLIST_v1_3_8_40.md', release_checklist)
        self.assertNotIn('docs/publish_checklists/PUBLISH_CHECKLIST_v1_4_2_17.md', release_checklist)

    def test_docs_treat_v1_1_0_as_next_after_v1_0_2(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        changelog = Path('CHANGELOG.md').read_text(encoding='utf-8')
        notes = Path('docs/release_notes/RELEASE_NOTES_v1_1_0.md').read_text(encoding='utf-8')
        self.assertIn('v1.0.2 の次の公開版', readme)
        self.assertIn('v1.0.2 の次の正式版 v1.1.0', changelog)
        self.assertIn('v1.0.2 の次の正式版', notes)
        self.assertIn('検証用の名前や sweep 番号は公開版名には含めません', notes)

    def test_public_app_version_matches_current_release_metadata(self) -> None:
        studio = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        constants = Path('tategakiXTC_gui_studio_constants.py').read_text(encoding='utf-8')
        metadata = Path('tategakiXTC_release_metadata.py').read_text(encoding='utf-8')
        import tategakiXTC_release_metadata as release_metadata

        self.assertIn('APP_VERSION,', studio)
        self.assertIn('from tategakiXTC_release_metadata import', constants)
        self.assertIn(f"APP_VERSION = '{release_metadata.APP_VERSION}'", metadata)


    def test_preview_high_zoom_eases_left_shift(self) -> None:
        studio = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        xtc_load_helpers = Path('tategakiXTC_gui_studio_xtc_load_helpers.py').read_text(encoding='utf-8')
        device_render_source = studio + xtc_load_helpers
        preview_zoom_helpers = Path('tategakiXTC_gui_studio_preview_zoom_helpers.py').read_text(encoding='utf-8')
        preview_layout_helpers = Path('tategakiXTC_gui_studio_preview_layout_helpers.py').read_text(encoding='utf-8')
        self.assertIn('_last_font_preview_scaled_size', preview_layout_helpers)
        self.assertIn('_preview_zoom_left_bias', studio)
        self.assertIn('_font_preview_leading_gap', studio)
        self.assertIn('setContentsMargins(leading_gap, 0, 0, 0)', preview_layout_helpers)
        self.assertIn('_set_horizontal_scrollbar_to_zoom_bias_later', studio)
        self.assertIn('v1.3.3.22: the previous 100%->200% smoothstep', preview_zoom_helpers)
        self.assertIn('end = 3.0', preview_zoom_helpers)
        self.assertIn('eased = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)', preview_zoom_helpers)
        self.assertIn('v1.3.8.5: in the 3-pane file-viewer flow, center the XTC', preview_layout_helpers)
        self.assertIn('_set_horizontal_scrollbar_to_center_later', studio)
        self.assertIn('set_preview_leading_gap', preview_layout_helpers)
        self.assertIn("self._qt_constant('AlignHCenter'", preview_layout_helpers)
        self.assertIn('set_alignment(align_hcenter | align_top)', preview_layout_helpers)
        self.assertNotIn('viewer_scroll.setAlignment(Qt.AlignCenter)', preview_layout_helpers)
        self.assertIn('_resync_device_preview_layout_now_and_later', device_render_source)
        self.assertIn('v1.3.3.23: when switching from font view to device view immediately', studio)
        self.assertIn('for delay_ms in (0, 50):', studio)
        self.assertIn('window._resync_device_preview_layout_now_and_later()', device_render_source)

    def test_v1_3_0_support_docs_exist(self) -> None:
        for relative in (
            'WINDOWS_SETUP.md',
            'FAQ.md',
            'KNOWN_LIMITATIONS.md',
            'docs/release_notes/RELEASE_NOTES_v1_3_2.md',
            'docs/publish_checklists/PUBLISH_CHECKLIST_v1_3_2.md',
        ):
            self.assertTrue(Path(relative).exists(), relative)

    def test_readme_github_release_block_matches_release_metadata(self) -> None:
        import tategakiXTC_release_metadata as release_metadata

        readme = Path('README.md').read_text(encoding='utf-8')
        source_only_zip = release_metadata.SOURCE_ONLY_ZIP_FILE_NAME
        self.assertIn(f'- Release tag: `v{release_metadata.PUBLIC_VERSION_TAG}`', readme)
        self.assertIn(f'- Release title: `v{release_metadata.PUBLIC_VERSION} Public`', readme)
        self.assertIn(f'- Previous tag: `v{release_metadata.PREVIOUS_PUBLIC_VERSION}`', readme)
        self.assertIn(f'- 添付ファイル: `{source_only_zip}`', readme)
        self.assertIn(f'- 添付ファイル: `{release_metadata.RELEASE_ZIP_FILE_NAME}`', readme)
        self.assertIn(
            f'v{release_metadata.PUBLIC_VERSION} Public の公開対象は **Python GUI版の public-source-only zip / public zip** です。',
            readme,
        )
        self.assertIn(f'Release 本文には `{release_metadata.RELEASE_NOTES_FILE}` の内容を使用します。', readme)

    def test_release_checklist_matches_release_metadata(self) -> None:
        import tategakiXTC_release_metadata as release_metadata

        checklist = Path('RELEASE_CHECKLIST.md').read_text(encoding='utf-8')
        current = release_metadata.PUBLIC_VERSION
        previous = release_metadata.PREVIOUS_PUBLIC_VERSION
        source_only_zip = release_metadata.SOURCE_ONLY_ZIP_FILE_NAME
        source_only_sha = f'{source_only_zip}.sha256.txt'
        release_zip = release_metadata.RELEASE_ZIP_FILE_NAME
        release_zip_sha = f'{release_zip}.sha256.txt'
        publish_checklist = f'docs/publish_checklists/PUBLISH_CHECKLIST_v{current.replace(".", "_")}.md'

        self.assertIn(f'# Release checklist v{current}', checklist)
        self.assertIn(f'`APP_VERSION` / `PUBLIC_VERSION` are `{current}`', checklist)
        self.assertIn(f'`PREVIOUS_PUBLIC_VERSION` is `{previous}`', checklist)
        self.assertIn(release_metadata.RELEASE_NOTES_FILE, checklist)
        self.assertIn(publish_checklist, checklist)
        self.assertIn(f'Japanese UI title shows `縦書きXTC Studio Public {current}`', checklist)
        self.assertIn(f'English UI title shows `TategakiXTC GUI Studio Public {current}`', checklist)
        self.assertIn(f'Release tag: `v{release_metadata.PUBLIC_VERSION_TAG}`', checklist)
        self.assertIn(f'Release title: `v{current} Public`', checklist)
        self.assertIn(f'Previous tag: `v{previous}`', checklist)
        self.assertIn(source_only_zip, checklist)
        self.assertIn(source_only_sha, checklist)
        self.assertIn(release_zip, checklist)
        self.assertIn(release_zip_sha, checklist)
        self.assertNotIn('v1.4.3.29', checklist)
        self.assertNotIn('v1.4.3.12', checklist)

    def test_readme_has_single_initial_setup_section(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertEqual(readme.count('## 初回セットアップ'), 1)
        self.assertNotIn('## 初回セットアップ補足', readme)

if __name__ == '__main__':
    unittest.main()
