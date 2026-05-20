# Publish Checklist v1.3.5

## Version / docs

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.3.5` になっている
- [ ] README の現在公開版が `v1.3.5` になっている
- [ ] `RELEASE_NOTES_v1_3_5.md` が存在し、v1.3.4 から v1.3.5 までの差分を1本にまとめている
- [ ] `CHANGELOG.md` の先頭に `v1.3.5` がある
- [ ] ライセンス欄で Source Available / not Open Source が明示されている

## Release zip

- [ ] `Font/` フォルダを含める場合、フォント本体と `LICENSE_OFL.txt` が同梱されている
- [ ] `build_release_zip.py` で release zip を作成できる
- [ ] `build_release_zip.py --verify` が通る
- [ ] handoff md / logs / cache / .github / .git が release zip に混入していない

## GitHub source

- [ ] source-only zip には `.github/workflows/python-tests.yml` が含まれている
- [ ] source-only zip に handoff md / logs / cache が混入していない
- [ ] GitHub repository 上の `Font/` フォルダを維持する場合、フォントライセンス文書も維持する

## Smoke test

- [ ] `run_gui.bat` で起動する
- [ ] EPUBをプレビューできる
- [ ] テスト文字列 `第４４章第88節　全角！？と半角!?でどう？？変わるだろう??` を確認する
- [ ] 全角 `！？` / `？？` の右張り出しが抑えられている
- [ ] 半角 `!?` / `??` が記号ペアとして表示される
- [ ] 「縦中横記号」補正の `標準` / `下補正 弱` / `下補正 強` を確認する
- [ ] `88` / `123` / `2026` の縦中横に劣化がない
- [ ] XTC / XTCH 保存ができる
