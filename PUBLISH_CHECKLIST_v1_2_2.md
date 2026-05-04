# v1.2.2 公開前チェックリスト

## 1. バージョン表記

- [ ] `APP_VERSION` が `1.2.2` になっている
- [ ] README の現在公開版が `v1.2.2` になっている
- [ ] CHANGELOG に `v1.2.2` が追記されている
- [ ] `RELEASE_NOTES_v1_2_2.md` が存在する
- [ ] GitHub Release tag を `v1.2.2` にする
- [ ] GitHub Release title を `v1.2.2` にする

## 2. 公開対象

- [ ] Python GUI版のみを公開対象にしている
- [ ] 旧ローカルWeb試作版関連ファイルが release zip に混入していない
- [ ] 不要な作業用 md / handoff md / 一時ファイルが混入していない
- [ ] `.venv`、`__pycache__`、`.pytest_cache` が混入していない

## 3. フォント・ライセンス

- [ ] Font フォルダを同梱する場合、フォント本体が入っている
- [ ] Font フォルダを同梱する場合、`LICENSE_OFL.txt` が入っている
- [ ] フォントのライセンス説明が README にある
- [ ] アプリ本体とフォントのライセンスを分けて説明している

## 4. ドキュメント

- [ ] `README.md` を v1.2.2 向けに更新した
- [ ] `WINDOWS_SETUP.md` を追加または更新した
- [ ] `FAQ.md` を追加または更新した
- [ ] `KNOWN_LIMITATIONS.md` を追加または更新した
- [ ] `RELEASE_NOTES_v1_2_2.md` を追加した
- [ ] README から関連ドキュメントへリンクしている

## 5. 実機確認

- [ ] GUI が起動する
- [ ] 波線描画 `回転グリフ` が動作する
- [ ] 波線描画 `別描画` が動作する
- [ ] 波線位置 `標準` が動作する
- [ ] 波線位置 `下補正弱` が動作する
- [ ] 波線位置 `下補正強` が動作する
- [ ] `～ 〜 〰 ~ ∼ ∽ ∿ ≀` の表示を確認した
- [ ] ボールド系フォントで波線の太さ・質感を確認した
- [ ] GUI変更時にプレビューへ即時反映される
- [ ] 再起動後に ini 設定が復元される
- [ ] プリセット仕様表示に波線描画・波線位置が出ない
- [ ] GUI上の波線設定項目自体は残っている

## 6. テスト

- [ ] 関連回帰テストが通る
- [ ] フル回帰テストが通る
- [ ] `build_release_zip.py --verify` が通る
- [ ] zip 展開検査が通る

例:

```cmd
python -B -m pytest tests -q

python -B build_release_zip.py

python -B build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.2.2-release.zip

tar -tf dist\tategaki-xtc-gui-studio_v1.2.2-release.zip > nul
```

## 7. GitHub Release

- [ ] Release tag: `v1.2.2`
- [ ] Release title: `v1.2.2`
- [ ] Previous tag: `v1.2.1`
- [ ] 添付ファイル名: `tategaki-xtc-gui-studio_v1.2.2-release.zip`
- [ ] Release 本文に `RELEASE_NOTES_v1_2_2.md` の内容を使う
- [ ] 公開後、Release ページから zip がダウンロードできることを確認する
