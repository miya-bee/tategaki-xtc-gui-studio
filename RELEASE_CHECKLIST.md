# RELEASE CHECKLIST / v1.3.4

## 必須確認

- [ ] `APP_VERSION` が `1.3.4` になっている
- [ ] README の現在公開版が `v1.3.4` になっている
- [ ] CHANGELOG に `v1.3.4` が追記されている
- [ ] `RELEASE_NOTES_v1_3_4.md` が存在する
- [ ] `PUBLISH_CHECKLIST_v1_3_4.md` が存在する
- [ ] Source Available / not Open Source の表記が README と LICENSE にある

## release zip

- [ ] `Font/` を含める公開zipを作成する
- [ ] `LICENSE_OFL.txt` を同梱する
- [ ] `build_release_zip.py --verify` が通る
- [ ] handoff md、logs、cache、`.github/`、`.git/` が混入していない

## GitHub Release

- [ ] Release tag: `v1.3.4`
- [ ] Release title: `v1.3.4`
- [ ] Previous tag: `v1.3.3`
- [ ] 添付ファイル名: `tategaki-xtc-gui-studio_v1.3.4-release.zip`
- [ ] Release 本文に `RELEASE_NOTES_v1_3_4.md` の内容を使用する

## 実機確認

- [ ] `run_gui.bat` で起動する
- [ ] EPUBプレビューができる
- [ ] XTC / XTCH 保存ができる
- [ ] 変換完了カードが表示される
- [ ] フォルダ一括変換の中止後、プログレスバーが止まる
- [ ] 中止がエラーではなく中止として表示される
- [ ] ini 無し初回起動からプリセット保存できる
