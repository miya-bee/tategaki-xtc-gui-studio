# Changelog

このファイルでは、縦書きXTC GUI Studio の主な変更履歴をまとめます。

## v1.1.0

v1.1.0 は、GitHub で公開済みの **v1.0.2 の次の正式版**です。

このリリースでは、公開対象を **Python GUI版のみ**に整理し、GUI、描画・変換処理、release payload、ドキュメントを更新しました。

### Added

- `CHANGELOG.md` を追加
- `RELEASE_NOTES_v1_1_0.md` を追加
- 同梱フォント用に `LICENSE_OFL.txt` を追加
- `Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントについて、README に説明を追加
- type hygiene 用の回帰テストを追加
- release docs / release hygiene 用の回帰テストを追加
- release zip に旧 Web 試作版関連ファイルが混入しないための検査を追加・整理

### Changed

- README を v1.1.0 公開向けに整理
- v1.1.0 を v1.0.2 の次の正式版として明記
- GitHub Release tag / title を `v1.1.0` として扱う方針を明記
- 公開対象を Python GUI版のみとして整理
- 旧ローカル Web 試作版関連の導線を README / CI / release payload から除外
- 初回セットアップ手順を Python 確認、venv 作成、requirements 導入、起動の順に整理
- `run_gui.bat` を基本起動手順として明確化
- `Font/` と `LICENSE_OFL.txt` の関係を README に明記
- release zip 作成時の検査を Python GUI版前提へ整理
- `.github/workflows/python-tests.yml` の依存導入を Python GUI版前提へ整理
- `run_tests.bat` の compile 対象を Python GUI版前提へ整理

### Fixed

- `tategakiXTC_worker_logic.py` の `Collection` import 漏れを修正
- `VisibleArrowSpinBox.paintEvent` の self 型アノテーション誤りを修正
- `_apply_output_conflict_strategy` の戻り型アノテーションを実態に合わせて修正
- `apply_conflict_strategy` callable 型を worker logic 側と一致するよう修正
- `build_conversion_summary` の `summarize_error_headlines` パラメータ名を整理し、同名関数の遮蔽を避けるよう修正
- 縦書き描画、句読点、括弧、ルビ、下端処理まわりの安定性を改善
- 一部フォントで閉じ括弧の描画位置が不安定になる問題を改善
- ぶら下がり句読点が文字と重なりやすいケースを改善
- 実機ビュー周辺の倍率表示や説明表示を整理

### Removed

- v1.1.0 の release payload から旧ローカル Web 試作版関連ファイルを除外
- `requirements-web.txt` への公開導線を削除
- local web launcher / service / template / smoke test などの旧試作版導線を release 対象から除外

### Notes

- v1.1.0 は Python GUI版のみの公開です
- GitHub Release では `v1.1.0` tag を使用します
- Previous tag は `v1.0.2` を想定します
- Release 添付ファイル名は `tategaki-xtc-gui-studio_v1.1.0.zip` を想定します
- `Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントは SIL Open Font License 1.1 に基づきます
- 同梱フォントのライセンス本文は `LICENSE_OFL.txt` を参照してください

## v1.0.2

前回の公開版です。

v1.1.0 は、この v1.0.2 の次の正式版として公開します。
