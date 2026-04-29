# Release Notes - v1.1.0

## 概要

v1.1.0 は、GitHub で公開済みの **v1.0.2 の次の正式版**として公開する版です。  
公開対象は **Python GUI版のみ** です。GitHub 公開先は GUI版リポジトリとして扱い、作業用 payload に Web 試作ファイル候補が混入した場合も release 対象外として検出するよう整理しました。  
UI の整理、実機ビューの安定化、変換まわりの軽量化、そして今後の分割作業に向けた下地整理をまとめています。

## 主な改善点

### UI とプリセット
- 左ペインの既定順を **Preset → Font → Image → Display** に統一
- ボタン名を **「プリセット適用」 / 「組版保存」** に整理
- 同名出力の導線を **右上の歯車メニュー内「その他オプション > 同名出力」** に統一
- フォントコンボの初回表示位置を見直し、開いたとき先頭から見やすい挙動へ改善

### プレビューと実機ビュー
- X3 / X4 判定と表示ラベルの整合を改善
- X3 の解像度を **528 × 792** に統一
- 実機ビュー枠を直角表示へ修正
- `XTCH` 指定時のプレビュー反映を修正
- プレビュー更新中の再入防止、成功 / 失敗 / 空結果時の UI 復帰を整理

### 変換と入力
- 単体画像（PNG / JPG / JPEG / WEBP）を GUI から変換可能に修正
- `load_xtc_from_path()` / `load_xtc_from_bytes()` 失敗時のクリア処理を改善
- 変換開始時に前回結果を先にクリアし、誤認しにくい挙動へ調整

### コード整理と公開準備
- preview / results / settings controller、layout helper、widget factory、`tategakiXTC_gui_studio_logic.py` を分離して責務を整理
- `coverage`、`mypy`、release zip 検査を含む公開前チェックを更新
- Python GUI版のみの公開構成に合わせ、作業用 payload 内の Web 試作ファイル候補を release 対象から除外
- source-only 構成では、同梱フォントが無くても **system font へフォールバック** して起動しやすいよう整理
- README の初回セットアップ、起動手順、Font フォルダー配置、`LICENSE_OFL.txt` の扱いを整理
- `.rootcopy`、`__pycache__`、`work_clean*_md.md` などのローカル作業物が release zip へ混ざらないよう監査対象を強化

### パフォーマンス
- 字形キャッシュ、縦書き置換字形判定キャッシュ、preview 再利用を見直し、変換とプレビューの体感速度を改善
- XTC（2値）/ XTCH（4階調）出力では、numpy 利用環境で pack 処理を高速化

## テスト

公開準備時点で、以下を基準に確認しています。

- `python -m unittest discover -s tests -v`
- `run_tests.bat`
- release zip の生成と `build_release_zip.py --verify` による検査

## 同梱フォント

v1.1.0 では、縦書き表示とテスト再現性のため、`Font/` フォルダーに Noto Sans JP / Noto Serif JP 系フォントを同梱しています。

同梱フォントは SIL Open Font License 1.1 に基づきます。詳細は `LICENSE_OFL.txt` を参照してください。

## GitHub 公開時の扱い

- Release 名 / tag は **v1.1.0** を想定しています。
- GitHub 上の既存 **v1.0.2** に続く次版として扱います。
- 検証用の名前や sweep 番号は公開版名には含めません。

## 補足

この版は、見た目の微修正だけでなく、巻き戻り防止と将来のファイル分割のしやすさも意識して整理しています。
