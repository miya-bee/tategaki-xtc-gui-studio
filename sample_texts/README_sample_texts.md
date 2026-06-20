# sample_texts

縦書きXTC GUI Studio の表示設定確認用サンプルです。

- `tategaki_position_kinsoku_test_text_v3.txt`
  - TXT / 青空文庫風ルビ / 禁則処理 / 位置補正確認用。
  - TXT入力では青空文庫風の太字注記は未対応のため、太字確認には使いません。
- `tategaki_position_kinsoku_bold_markdown_v1.md`
  - Markdown の `**太字**` を使った太字確認用。
  - 太字、禁則、句読点、半角数字/記号、縦中横記号、下鍵括弧、ルビをまとめて確認できます。

- `tategaki_tatechuyoko_punctuation_test_text_v1.txt`
  - 以前の縦中横記号調整で使った「第４４章第88節　全角！？と半角!?でどう？？変わるだろう??」確認用。
  - 半角 `!?` / `??` と全角 `！？` / `？？` の位置・サイズ差を短時間で確認できます。

ファイル名は配布zip内で扱いやすいよう ASCII のみにしています。

- `tategaki_halfwidth_alpha_position_test_text_v1.txt`
  - 半角英字（A-Z / a-z）の上下位置補正を確認するためのテスト文です。
  - `XTC`、`EPUB`、`PDF`、`GitHub`、`Windows`、`Python` などを含みます。
  - 半角数字/記号補正との切り分け確認にも使えます。

- `tategaki_halfwidth_fullwidth_alpha_compare_test_text_v1.txt`
  - 半角英字と全角英字の見え方を比較するためのテスト文です。
  - 「半角英字」位置補正が半角 A-Z / a-z だけに効き、全角 Ａ-Ｚ / ａ-ｚ には影響しないことを確認できます。

- `tategaki_middle_dot_position_test_text_v1.txt`
  - 中黒「・」/ 半角中黒「･」/ 欧文中点「·」の上下位置補正確認用。
  - 語中・連続・句読点混在・XTC/XTCH などの並びで見え方を比較できます。
