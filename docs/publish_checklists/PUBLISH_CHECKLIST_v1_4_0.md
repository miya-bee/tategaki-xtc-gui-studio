# Publish checklist v1.4.0

## 公開前確認

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.4.0` になっている。
- [ ] `PREVIOUS_PUBLIC_VERSION` が `1.3.6` になっている。
- [ ] `docs/release_notes/RELEASE_NOTES_v1_4_0.md` が、v1.3.6 から v1.4.0 までの差分まとめになっている。
- [ ] `CHANGELOG.md` の先頭が `v1.4.0 - Public release` になっている。
- [ ] v1.3.8.x の細かな `docs/release_notes/RELEASE_NOTES_v1_3_8_*.md` / `docs/publish_checklists/PUBLISH_CHECKLIST_v1_3_8_*.md` が残っていない。
- [ ] `README.md` の現在バージョン、Release tag、添付ファイル名が v1.4.0 に揃っている。
- [ ] source-only / release zip を作成し、SHA256を記録する。
- [ ] zip integrity と forbidden artifact 混入なしを確認する。

## 実機確認

- [ ] `run_gui.bat` または `python tategakiXTC_gui_studio.py` で起動する。
- [ ] 3ペインUIで、左プリセット、中央設定、右プレビューが期待どおり表示される。
- [ ] TXT / Markdown / EPUB のプレビューと XTC / XTCH 保存ができる。
- [ ] 画像単体入力と複数画像フォルダー変換で、スキップされず XTC / XTCH が生成される。
- [ ] 保存先指定、保存先リセット、`保存先を開く` が期待どおり動く。
- [ ] 設定変更時のライブプレビュー再生成が働く。
- [ ] 変換中キャンセルが一般失敗ではなく中止として扱われる。
- [ ] 大きな折り返し字下げを含むTXT/Markdownでハングせず、過大字下げ時も本文が列頭付近から始まる。
- [ ] ファイルビューワーモードから通常入力へ戻れる。
- [ ] sample_texts の位置補正確認用ファイルで、半角数字/記号、縦中横記号、半角英字の補正を確認する。

## GitHub Release

- [ ] Release tag: `v1.4.0`
- [ ] Release title: `v1.4.0`
- [ ] Previous tag: `v1.3.6`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.0-release.zip`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.0-release.zip.sha256.txt`
- [ ] Release 本文には `docs/release_notes/RELEASE_NOTES_v1_4_0.md` の内容を使用する。

- [ ] run_gui.bat hardening: confirm double-click launch from a normal extracted local folder and confirm batch files are CRLF-only.

- [ ] `run_gui.bat` / `install_requirements.bat` / `run_tests.bat` が CRLF で、各 `exit /b` の直前に `pause` があることを release hygiene で確認する。

## 互換性確認

- [ ] 旧 `device` view-mode 値が現行の右ペイン表示へ安全に丸められること。
