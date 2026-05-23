# Release checklist v1.3.6

## 公開前確認

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.3.6` になっている。
- [ ] `RELEASE_NOTES_v1_3_6.md` が、v1.3.5 から v1.3.6 までの差分まとめになっている。
- [ ] `PUBLISH_CHECKLIST_v1_3_6.md` が公開版 v1.3.6 用の確認項目になっている。
- [ ] `CHANGELOG.md` の先頭が `v1.3.6 - Public release` になっている。
- [ ] `build_release_zip.py --verify` が通る。
- [ ] release zip に `Font/` と `sample_texts/` が含まれている。
- [ ] release zip に logs / ini / `__pycache__` / `.pytest_cache` / `.pyc` が混入していない。

## 実機確認

- [ ] `run_gui.bat` または `python tategakiXTC_gui_studio.py` で起動する。
- [ ] 起動直後に「生成中…」表示が残らない。
- [ ] TXT / Markdown / EPUB のプレビューと XTC / XTCH 保存ができる。
- [ ] 別保存先指定、保存先リセット、「保存先を開く」が期待どおり動く。
- [ ] ファイルビューワーモードから通常入力へ戻れる。
- [ ] sample_texts の位置補正確認用ファイルで、半角数字/記号、縦中横記号、半角英字の補正を確認する。

## GitHub Release

- [ ] Release tag: `v1.3.6`
- [ ] Release title: `v1.3.6`
- [ ] Previous tag: `v1.3.5`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.3.6-release.zip`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.3.6-release.zip.sha256.txt`
- [ ] Release 本文には `RELEASE_NOTES_v1_3_6.md` の内容を使用する。
