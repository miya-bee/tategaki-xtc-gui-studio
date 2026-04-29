# CHANGELOG

このファイルは、GitHub で公開済みの **v1.0.2 の次の正式版 v1.1.0** の変更点をまとめたものです。  
内部の作業番号や段階的な bugfix 履歴は、公開物では扱わない方針としています。

## v1.1.0

### v1.0.2 からの主な整理

- 左ペインの既定順を **Preset → Font → Image → Display** に再整理しました。
- プリセット周辺のボタン名を **「プリセット適用」 / 「組版保存」** に統一しました。
- 同名出力の導線を **右上の歯車メニュー内「その他オプション > 同名出力」** に統一しました。
- 実機ビューまわりを再監査し、X3 / X4 判定、X3 の **528 × 792** 解像度、実機枠の直角表示、表示ラベルの整合を改善しました。
- `XTCH` 指定時のプレビュー反映、プレビュー中の再入防止、成功 / 空結果 / 失敗時の UI 復帰を整理しました。
- 単体画像（`.png` / `.jpg` / `.jpeg` / `.webp`）を GUI から選択して変換できるよう改善しました。
- `Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントについて、`LICENSE_OFL.txt` と README 説明を追加。

### 内部整理

- `MainWindow` から preview / results / settings controller を前段切り出ししました。
- layout helper、widget factory、`tategakiXTC_gui_studio_logic.py`、`tategakiXTC_worker_logic.py` を追加し、今後の分割作業へ入りやすい構成に寄せました。
- source-only 配布物で同梱フォントが無い環境でも、利用可能な system font へフォールバックして起動・テスト継続できるよう整理しました。
- README に初回セットアップ、起動手順、Font フォルダー配置、`LICENSE_OFL.txt` が必要になる条件を追記しました。

### 性能・品質

- 字形再描画、縦書き置換字形判定、画像ページ処理、preview bundle 再利用を見直し、体感速度を改善しました。
- XTC（2値）/ XTCH（4階調）出力では、numpy が利用できる環境で pack 処理を高速化しました。
- `coverage`、`mypy`、release zip 監査、`py_compile.compile` による公開前検査を整理しました。
