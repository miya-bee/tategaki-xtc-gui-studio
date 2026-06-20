# tategakiXTC GUI Studio v1.3.2 Publish Checklist

- [ ] `py -3.10 -m compileall -q .` が通る
- [ ] `py -3.10 -m unittest discover -s tests -v` が通る
- [ ] release zip の `--verify` が通る
- [ ] Windows 実機で `run_gui.bat` から起動できる
- [ ] 画面上のバージョン表示が `1.3.2` になっている
- [ ] プレビュー枚数の初期値が `20` になっている
- [ ] 下鍵括弧の選択肢が5モードになっている
- [ ] 下鍵括弧の `下補正 弱` / `下補正 強` がプレビューに反映される
- [ ] 通常変換・フォルダ一括変換の既存動作に目立つ後退がない
