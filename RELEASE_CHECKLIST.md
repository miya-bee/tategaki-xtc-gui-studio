# RELEASE CHECKLIST / v1.3.5

## 必須確認

- [ ] `APP_VERSION` が `1.3.5` になっている
- [ ] README の現在公開版が `v1.3.5` になっている
- [ ] CHANGELOG に `v1.3.5` が追記されている
- [ ] `RELEASE_NOTES_v1_3_5.md` が存在する
- [ ] `PUBLISH_CHECKLIST_v1_3_5.md` が存在する
- [ ] Source Available / not Open Source の表記が README と LICENSE にある

## release zip

- [ ] `Font/` を含める公開zipを作成する場合は、フォント本体と `LICENSE_OFL.txt` を同梱する
- [ ] `build_release_zip.py --verify` が通る
- [ ] handoff md、logs、cache、`.github/`、`.git/` が混入していない

## GitHub Release

- [ ] Release tag: `v1.3.5`
- [ ] Release title: `v1.3.5`
- [ ] Previous tag: `v1.3.4`
- [ ] 添付ファイル名: `tategaki-xtc-gui-studio_v1.3.5-release.zip`
- [ ] Release 本文に `RELEASE_NOTES_v1_3_5.md` の内容を使用する

## 実機確認

- [ ] `run_gui.bat` で起動する
- [ ] EPUBプレビューができる
- [ ] XTC / XTCH 保存ができる
- [ ] テスト文字列 `第４４章第88節　全角！？と半角!?でどう？？変わるだろう??` を確認する
- [ ] 全角 `！？` / `？？` の右張り出しが抑えられている
- [ ] 半角 `!?` / `??` が記号ペアとして表示される
- [ ] 「縦中横記号」補正の `標準` / `下補正 弱` / `下補正 強` を確認する
- [ ] `88` / `123` / `2026` の縦中横に劣化がない
