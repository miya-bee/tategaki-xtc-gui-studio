# Publish checklist v1.3.6

- [ ] `APP_VERSION` / `PUBLIC_VERSION` が `1.3.6` になっている。
- [ ] 起動直後に「生成中…」表示が残らない。
- [ ] 通常 TXT / Markdown / EPUB プレビューが動く。
- [ ] TXT / Markdown / EPUB を XTC / XTCH 保存できる。
- [ ] 主経路の XTC / XTCH 書き出し後、出力ファイルをファイルビューワーで開ける。
- [ ] 「保存先を選ぶ...」でソースとは別フォルダを指定し、変換結果が指定先へ保存される。
- [ ] 「保存先を開く」で指定保存先が開く。
- [ ] 「保存先リセット」後、再変換と「保存先を開く」がソースファイル側フォルダへ戻る。
- [ ] ファイルビューワーで XTC / XTCH を開いた後、フォントビューのカーソルキー操作で通常サンプルへ戻らない。
- [ ] `sample_texts/tategaki_halfwidth_alpha_position_test_text_v1.txt` が同梱されている。
- [ ] `sample_texts/tategaki_halfwidth_fullwidth_alpha_compare_test_text_v1.txt` が同梱されている。
- [ ] 半角英字位置補正、半角数字/記号位置補正、縦中横記号位置補正に副作用がない。
- [ ] フォルダ一括変換の停止ボタンが従来通り機能する。
- [ ] release zip に Font/ と sample_texts/ が含まれている。
- [ ] logs / ini / __pycache__ / .pytest_cache / .pyc が混入していない。
