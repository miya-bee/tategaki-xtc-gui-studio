# TategakiXTC GUI Studio v1.4.4 Release Notes

このリリースは v1.4.3.43 からの機能更新です。CHANGELOG もあわせて参照してください。Web小説やメモ本文をすぐ試せる入力導線と、変換結果を画像で共有しやすくする出力導線を追加しました。

## 変更点

- 上部バーに「クリップボード」ボタンを追加しました。
- クリップボード内のテキストを UTF-8 の一時TXTファイルとして保存し、既存のTXT入力と同じ流れでプレビュー・変換できるようにしました。
- 右ペイン上部に「SNS用PNG保存」ボタンを追加しました。
- 現在表示中のプレビュー1ページを、背景・枠・ページ番号付きのPNGとして保存できるようにしました。
- XTC/XTCH ファイルビューワーで表示中の場合は、表示中のXTC/XTCHページをPNG保存元として優先します。
- UI文言と英語UI翻訳を追加しました。

## 変更していないこと

- 変換コア、描画仕様、XTC/XTCH 出力仕様は変更していません。
- 設定保存形式、プリセット形式は変更していません。
- クリップボード入力は一時TXT化して既存のTXT処理へ渡すため、変換本体に別経路は追加していません。

## 検証

- `python3 -m compileall -q .`
- `python3 -m pytest tests/test_clipboard_and_share_export_regression.py tests/test_gui_layouts_regression.py tests/test_gui_studio_logic_regression.py tests/test_split_module_compatibility_regression.py tests/test_gui_studio_worker_regression.py -q`
- release / source-only zip build and verify
