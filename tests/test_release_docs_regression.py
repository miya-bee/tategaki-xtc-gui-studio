from __future__ import annotations

from pathlib import Path
import unittest


class ReleaseDocsRegressionTests(unittest.TestCase):
    def test_readme_matches_current_left_pane_order(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn('Preset → Font → Image → Display', readme)

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
        self.assertIn('release zip 作成を停止します', readme)
        self.assertIn('build_release_zip.py` 実行前に `Font/` / `fonts/` を置かないか、一時的に退避', readme)

    def test_changelog_is_clean_single_title(self) -> None:
        changelog = Path('CHANGELOG.md').read_text(encoding='utf-8')
        self.assertTrue(changelog.startswith('# CHANGELOG\n'))
        self.assertEqual(changelog.count('# CHANGELOG'), 1)
        self.assertIn('## v1.2.2', changelog)
        self.assertIn('v1.2.2 は、v1.2.1 を基準に、波ダッシュ・チルダ類の縦書き表示調整を追加した安定版です。', changelog)
        self.assertIn('## v1.1.0', changelog)
        self.assertIn('v1.0.2 の次の正式版 v1.1.0', changelog)

    def test_release_notes_exist_for_current_public_version(self) -> None:
        notes = Path('RELEASE_NOTES_v1_2_2.md').read_text(encoding='utf-8')
        self.assertIn('v1.2.2', notes)
        self.assertIn('安定版', notes)
        self.assertIn('波ダッシュ・チルダ類', notes)
        self.assertIn('回転グリフ', notes)
        self.assertIn('別描画', notes)


    def test_docs_treat_v1_1_0_as_next_after_v1_0_2(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        changelog = Path('CHANGELOG.md').read_text(encoding='utf-8')
        notes = Path('RELEASE_NOTES_v1_1_0.md').read_text(encoding='utf-8')
        self.assertIn('v1.0.2 の次の公開版', readme)
        self.assertIn('v1.0.2 の次の正式版 v1.1.0', changelog)
        self.assertIn('v1.0.2 の次の正式版', notes)
        self.assertIn('検証用の名前や sweep 番号は公開版名には含めません', notes)

    def test_public_app_version_matches_current_release_metadata(self) -> None:
        studio = Path('tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
        constants = Path('tategakiXTC_gui_studio_constants.py').read_text(encoding='utf-8')
        metadata = Path('tategakiXTC_release_metadata.py').read_text(encoding='utf-8')
        self.assertIn('APP_VERSION,', studio)
        self.assertIn('from tategakiXTC_release_metadata import', constants)
        self.assertIn("APP_VERSION = '1.2.2'", metadata)

    def test_v1_2_2_support_docs_exist(self) -> None:
        for relative in (
            'WINDOWS_SETUP.md',
            'FAQ.md',
            'KNOWN_LIMITATIONS.md',
            'RELEASE_NOTES_v1_2_2.md',
            'PUBLISH_CHECKLIST_v1_2_2.md',
        ):
            self.assertTrue(Path(relative).exists(), relative)

    def test_readme_github_release_block_matches_release_metadata(self) -> None:
        import tategakiXTC_release_metadata as release_metadata

        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertIn(f'- Release tag: `v{release_metadata.PUBLIC_VERSION_TAG}`', readme)
        self.assertIn(f'- Release title: `v{release_metadata.PUBLIC_VERSION}`', readme)
        self.assertIn(f'- Previous tag: `v{release_metadata.PREVIOUS_PUBLIC_VERSION}`', readme)
        self.assertIn(f'- 添付ファイル: `{release_metadata.RELEASE_ZIP_FILE_NAME}`', readme)
        self.assertIn(f'Release 本文には `{release_metadata.RELEASE_NOTES_FILE}` の内容を使用します。', readme)

    def test_readme_has_single_initial_setup_section(self) -> None:
        readme = Path('README.md').read_text(encoding='utf-8')
        self.assertEqual(readme.count('## 初回セットアップ'), 1)
        self.assertNotIn('## 初回セットアップ補足', readme)

if __name__ == '__main__':
    unittest.main()
