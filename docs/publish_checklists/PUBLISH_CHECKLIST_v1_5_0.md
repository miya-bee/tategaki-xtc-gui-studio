# Publish checklist v1.5.0

## Version / docs

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.5.0` になっている。
- [ ] `PREVIOUS_PUBLIC_VERSION` が `1.4.2` になっている。
- [ ] `CHANGELOG.md` が v1.5.0 から始まっている。
- [ ] `README.md` / `docs/release_notes/RELEASE_NOTES_v1_5_0.md` / `RELEASE_CHECKLIST.md` が v1.5.0 に揃っている。
- [ ] 公開用 zip 名が `tategaki-xtc-gui-studio_v1.5.0-public.zip` 系になっている。

## Required checks

```bat
py -3.10 -m compileall -q .
py -3.10 tests\generate_golden_images.py --check
py -3.10 -m pytest tests -q -x --ignore=tests/test_english_ui_widget_scan.py
```

## Focused checks

```bat
py -3.10 -m pytest -q tests\test_layout_regression.py
py -3.10 -m pytest -q tests\test_renderer_api_regression.py
py -3.10 -m pytest -q tests\test_aozora_note_parser_regression.py tests\test_aozora_style_helpers_regression.py tests\test_aozora_image_sidecar_regression.py
py -3.10 -m pytest -q tests\test_share_export_regression.py tests\test_gui_layouts_regression.py
```

## Manual checks

- [ ] 上部バーに「青空文庫」ボタンが無い。
- [ ] 上部バーに「クリップボード」ボタンが無い。
- [ ] 上部ボタンのヘルプに青空文庫検索・クリップボード入力の説明が残っていない。
- [ ] 通常ファイル入力、TXT / Markdown / EPUB / 画像 / フォルダ一括変換が動く。
- [ ] ローカル青空文庫形式TXTのルビ・外字・傍点・傍線が従来どおり動く。
- [ ] `https://example.com` が横組みになる。
- [ ] `https://` / `http://` / `www.` 単体が横組みにならない。
- [ ] 欧文横組み、URL横組み、行頭鍵括弧設定が残っている。

## Release build

```bat
py -3.10 build_release_zip.py --source-only
py -3.10 build_release_zip.py
py -3.10 build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.5.0-public-source-only.zip
py -3.10 build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.5.0-public.zip
```
