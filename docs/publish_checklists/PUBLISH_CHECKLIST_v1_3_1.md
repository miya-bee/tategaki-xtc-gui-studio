# PUBLISH_CHECKLIST v1.3.1

## 公開前確認

- [ ] `py -3.10 -m compileall -q .` が通る
- [ ] フォルダ一括変換関連 unittest が通る
- [ ] release hygiene / release docs regression が通る
- [ ] `build_release_zip.py` で公開 zip を作成できる
- [ ] 作成した zip を `build_release_zip.py --verify <zipパス>` で検証できる
- [ ] `unzip -t` または同等の zip 整合性確認が通る
- [ ] 公開 zip に Web 版関連ファイルが混入していない
- [ ] 公開 zip に `.github`、ログ、キャッシュ、一時ファイル、handoff md が混入していない
- [ ] Font フォルダと `LICENSE_OFL.txt` が含まれている
- [ ] Windows 実機で `py -3.10` 起動できる
- [ ] TXT 単体変換ができる
- [ ] TXT フォルダ一括変換ができる
- [ ] 失敗ファイルがある場合に `[ERROR-SUMMARY]` が表示される
- [ ] 完了後に「出力フォルダを開く」導線が動作する
- [ ] 停止ボタン押下後、停止要求文言と未処理件数が分かりやすく表示される
- [ ] PNG 由来 `.xtc` を軽く開けることを確認する

## 公開文面

- [ ] README の v1.3.1 更新内容を確認
- [ ] CHANGELOG の v1.3.1 項目を確認
- [ ] FAQ のフォルダ一括変換・停止・EPUB optional dependency 案内を確認
- [ ] 既知の注意点を確認
- [ ] GitHub Release 本文を作成
- [ ] note 等の告知文を作成
