# Publish Checklist v1.3.4

## Version / docs

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.3.4` になっている
- [ ] README の現在公開版が `v1.3.4` になっている
- [ ] `docs/release_notes/RELEASE_NOTES_v1_3_4.md` が存在し、v1.3.3 から v1.3.4 までの差分を1本にまとめている
- [ ] `CHANGELOG.md` の先頭に `v1.3.4` がある
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
- [ ] ルビ消し ON/OFF がプレビューと保存に反映される
- [ ] 半角数字補正が効く
- [ ] 単独変換後、右ペイン上部に完了カードが出る
- [ ] 変換完了後に Explorer が自動起動しない
- [ ] フォルダ一括変換の中止後、プログレスバーが止まり、中止カードが出る
- [ ] ini 無し初回起動からプリセット保存し、再起動後に値が残る
