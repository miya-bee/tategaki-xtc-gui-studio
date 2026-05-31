# TategakiXTC GUI Studio v1.4.1 Publish Checklist

## 公開前確認

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.4.1` になっている。
- [ ] `PREVIOUS_PUBLIC_VERSION` が `1.4.0` になっている。
- [ ] `RELEASE_NOTES_v1_4_1.md` が、v1.4.0 から v1.4.1 までの差分まとめになっている。
- [ ] `PUBLISH_CHECKLIST_v1_4_1.md` が存在する。
- [ ] `CHANGELOG.md` の先頭に `v1.4.1` の統合項目がある。
- [ ] v1.4.1.x / v1.4.2.x の細かな `RELEASE_NOTES_*.md` / `PUBLISH_CHECKLIST_*.md` が公開版に残っていない。
- [ ] `README.md` の現在バージョン、Release tag、添付ファイル名、Release notes 参照が v1.4.1 に揃っている。
- [ ] source-only / release zip を作成し、SHA256を記録する。
- [ ] zip integrity と forbidden artifact 混入なしを確認する。

## 実機確認

- [ ] 日本語環境の初回起動で、日本語UIとして起動する。
- [ ] English UI でウィンドウタイトルが `TategakiXTC GUI Studio 1.4.1` と表示される。
- [ ] 日本語UIでウィンドウタイトルが `縦書きXTC Studio 1.4.1` と表示される。
- [ ] Language 欄で表示言語を変更し、再起動後に保存済み言語が反映される。
- [ ] English UI で主要ラベル、ヘルプ、ツールチップ、ダイアログ、ログ、変換結果、フォルダ一括変換メッセージが英語表示される。
- [ ] `py -3.10 -m pytest tests/test_english_ui_widget_scan.py -q` が、PySide6/Pillow ありのWindows実機で PASS する。
- [ ] `py -3.10 -m pytest tests -q` のフルスイートで、real Qt 走査テストが stub Qt 系テストと衝突してプロセス異常終了しない。
- [ ] 既知の golden image 環境差以外に新規失敗がない。
- [ ] TXT / Markdown / EPUB のプレビューと XTC / XTCH 保存ができる。
- [ ] 画像単体入力と複数画像フォルダー変換で、スキップされず XTC / XTCH が生成される。
- [ ] 保存先指定、保存先リセット、`保存先を開く` が期待どおり動く。
- [ ] ページ番号と progress bar の下部表示が重ならない。
- [ ] sample_texts の位置補正確認用ファイルで、半角数字/記号、縦中横記号、半角英字の補正を確認する。

## GitHub Release

- [ ] Release tag: `v1.4.1`
- [ ] Release title: `v1.4.1`
- [ ] Previous tag: `v1.4.0`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.1-release.zip`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.1-release.zip.sha256.txt`
- [ ] Release 本文には `RELEASE_NOTES_v1_4_1.md` の内容を使用する。

## Known note

- golden image の `page_compound_layout` 差分は環境依存の既知差分として、Windows実機の既存golden運用で確認する。
