# tategakiXTC GUI Studio v1.2.1 Release Notes

- 公開向けバージョン表記: `v1.2.1`
- 基準版: `v1.2.0`
- 公開対象: Python GUI版
- 種別: 小修正版

## 修正内容

### TXT / Markdown プレビューのエラー修正

TXT / Markdown などのテキストファイルを読み込んだとき、プレビュー生成で `tategakiXTC_gui_core_text.py` のテキスト入力キャッシュ helper 参照が解決できず、エラーになる問題を修正しました。

### preview payload の安全化

対象パスが選択されている状態では、前回の画像プレビュー用 `file_b64` や `image` mode を引きずらず、`target_path` からプレビュー生成するようにしました。これにより、テキストファイル選択後のプレビューが画像データ扱いになる退行を防ぎます。

## 検証

以下を確認済みです。

- `tests.test_gui_preview_controller_regression`
- `tests.test_input_pipeline_regression`
- `tests.test_real_file_preview`
- `tests.test_sample_fixture_regression`
- `tests.test_text_input_helper_regression`
- TXT fixture からの `generate_preview_bundle()` 実行

## Release 情報

- Release tag: `v1.2.1`
- Release title: `v1.2.1`
- Previous tag: `v1.2.0`
- 添付ファイル: `tategaki-xtc-gui-studio_v1.2.1-release.zip`
