# TategakiXTC GUI Studio v1.4.2.1 Publish Checklist

## 公開前確認

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.4.2.1` になっている。
- [ ] `PREVIOUS_PUBLIC_VERSION` が `1.4.2` になっている。
- [ ] `RELEASE_NOTES_v1_4_2_1.md` が、v1.4.2 から v1.4.2.1 までの差分まとめになっている。
- [ ] `PUBLISH_CHECKLIST_v1_4_2_1.md` が存在する。
- [ ] `CHANGELOG.md` の先頭に `v1.4.2.1` の項目がある。
- [ ] `README.md` の現在バージョン、Release tag、添付ファイル名、Release notes 参照が v1.4.2.1 に揃っている。
- [ ] release zip を作成し、SHA256を記録する。
- [ ] zip integrity と forbidden artifact 混入なしを確認する。

## 実機確認

- [ ] 日本語UIでウィンドウタイトルが `縦書きXTC Studio 1.4.2.1` と表示される。
- [ ] English UI でウィンドウタイトルが `TategakiXTC GUI Studio 1.4.2.1` と表示される。
- [ ] 先頭に空行を含むTXT / Markdownで、本文開始前に空白列が反映される。
- [ ] 先頭空行の空白列数が、本文中の空行と過剰に食い違わない。
- [ ] 空行なしの本文、本文中空行あり、先頭空行ありの3ケースで基本描画が崩れない。
- [ ] TXT / Markdown / EPUB のプレビューと XTC / XTCH 保存ができる。
- [ ] 保存先指定、保存先リセット、`保存先を開く` が期待どおり動く。

## 推奨テスト

```bat
py -3.10 -m compileall -q .
py -3.10 -m pytest ^
  tests\test_text_render_sync_regression.py ^
  tests\test_layout_regression.py ^
  tests\test_release_docs_regression.py ^
  tests\test_release_bundle_hygiene.py ^
  -q
```

## GitHub Release

- [ ] Release tag: `v1.4.2.1`
- [ ] Release title: `v1.4.2.1`
- [ ] Previous tag: `v1.4.2`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.2.1-release.zip`
- [ ] 添付ファイル: `tategaki-xtc-gui-studio_v1.4.2.1-release.zip.sha256.txt`
- [ ] Release 本文には `RELEASE_NOTES_v1_4_2_1.md` の内容を使用する。

## Known note

- Windows portable/exe 版は GitHub Release には置かず、note 購入者向け配布として別途作成する。
- v1.4.2.1 は差分zipではなく、利用者がそのまま展開できる全部入り release zip を正式アセットとして扱う。
