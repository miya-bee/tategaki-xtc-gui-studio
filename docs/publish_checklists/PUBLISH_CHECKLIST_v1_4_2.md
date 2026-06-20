# TategakiXTC GUI Studio v1.4.2 Publish Checklist

## 公開前確認

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.4.2` になっている。
- [ ] `PREVIOUS_PUBLIC_VERSION` が `1.4.1` になっている。
- [ ] `docs/release_notes/RELEASE_NOTES_v1_4_2.md` が、v1.4.1 から v1.4.2 までの差分まとめになっている。
- [ ] `docs/publish_checklists/PUBLISH_CHECKLIST_v1_4_2.md` が存在する。
- [ ] `CHANGELOG.md` の先頭に `v1.4.2` の統合項目がある。
- [ ] v1.4.1.6〜v1.4.1.17 の細かな作業版メモや handoff が公開zipに残っていない。
- [ ] `README.md` の現在バージョン、Release tag、添付ファイル名、Release notes 参照が v1.4.2 に揃っている。
- [ ] source-only / release zip を作成し、SHA256を記録する。
- [ ] zip integrity と forbidden artifact 混入なしを確認する。

## 実機確認

- [ ] 日本語UIでウィンドウタイトルが `縦書きXTC Studio 1.4.2` と表示される。
- [ ] English UI でウィンドウタイトルが `TategakiXTC GUI Studio 1.4.2` と表示される。
- [ ] ギアメニューの「外観」が English UI で `Appearance` と表示される。
- [ ] English UI 走査テストが、起動時ウィジェットだけでなくギアメニューの section/action も検査する。
- [ ] progress bar の既読部分が右端から左へ伸びる。
- [ ] ページ番号と progress bar の下部表示が重ならない。
- [ ] `」』` / `）」` / `。」』` などの閉じ括弧連続箇所で、2個目以降の閉じ括弧が列頭に残らない。
- [ ] 通常の句読点 `、` / `。` のぶら下げ処理が壊れていない。
- [ ] 書き込み不可の app-local `logs/` 相当でも GUI 起動が落ちない。
- [ ] フォルダ一括変換の停止時、未処理件数が実態より1件多くならない。
- [ ] TXT / Markdown / EPUB のプレビューと XTC / XTCH 保存ができる。
- [ ] 画像単体入力と複数画像フォルダー変換で、スキップされず XTC / XTCH が生成される。
- [ ] 保存先指定、保存先リセット、`保存先を開く` が期待どおり動く。

## 推奨テスト

```bat
py -3.10 -m compileall -q .
py -3.10 -m pytest ^
  tests	est_font_draw_helper_regression.py ^
  tests	est_golden_workflow_regression.py ^
  tests	est_progress_bar_regression.py ^
  tests	est_english_ui_widget_scan.py ^
  tests	est_release_docs_regression.py ^
  tests	est_release_bundle_hygiene.py ^
  -q
```

## GitHub Release

- [ ] Release tag: `v1.4.2`
- [ ] Release title: `v1.4.2`
- [ ] Previous tag: `v1.4.1`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.2-source-only.zip`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.2-source-only.zip.sha256.txt`
- [ ] 必要に応じて release zip: `tategaki-xtc-gui-studio_v1.4.2-release.zip`
- [ ] 必要に応じて release zip SHA256: `tategaki-xtc-gui-studio_v1.4.2-release.zip.sha256.txt`
- [ ] Release 本文には `docs/release_notes/RELEASE_NOTES_v1_4_2.md` の内容を使用する。

## Known note

- Windows portable/exe 版は GitHub Release には置かず、note 購入者向け配布として別途作成する。
- source-only zip は GitHub リポジトリ更新向け、release zip はエンドユーザー向け配布候補として扱う。
