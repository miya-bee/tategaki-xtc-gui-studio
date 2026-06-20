# CHANGELOG

## v1.5.0

- GitHub公開用のPublic版として、v1.4.2 以降の開発内容を v1.5.0 に統合しました。配布ファイル名は `tategaki-xtc-gui-studio_v1.5.0-public.zip` です。
- Public版では青空文庫検索・ダウンロード機能とクリップボード変換機能を削除しました。これらは有償配布中のFull版（`tategaki-xtc-gui-studio_v1.5.0-full.zip`）で扱います。
- 上部バーから「青空文庫」「クリップボード」ボタンを削除し、上部ボタンのヘルプも通常ファイル入力・フォルダ一括変換・保存先操作中心に整理しました。
- 青空文庫の記法パーサ、ルビ・外字・傍点・傍線・改ページ・字下げ注記のローカルTXT変換対応は維持しています。
- 欧文横組み、URL横組み、行頭鍵括弧設定を追加しました。
- `https://` / `http://` / `www.` 単体のようにホスト部分がない不完全URL風文字列を、横組みURLとして扱わないよう修正しました。
- 複数空行、連続会話行、ぶら下がり句読点直後の空行、短いルビ＋読点など、草枕テキストで確認した組版上の不自然さを修正しました。
- v1.5.0.1〜v1.5.0.26 の細かな作業版変更は、この公開版エントリへ集約しています。

## v1.4.4

v1.4.4 は、v1.4.3.43 を基準に、Web小説・メモ本文を試しやすくする「クリップボードから読み込み」と、変換結果を共有しやすくする「SNS用PNG保存」を追加した機能更新版です。

- 上部バーに「クリップボード」ボタンを追加しました。
- クリップボード内のテキストを UTF-8 の一時TXTファイルとして保存し、既存のTXT入力と同じプレビュー・変換経路へ流せるようにしました。
- 右ペイン上部に「SNS用PNG保存」ボタンを追加しました。
- 現在表示中のプレビュー1ページ、またはファイルビューワーで開いた XTC/XTCH の現在ページを、枠付きPNGとして保存できるようにしました。
- ファイルビューワー表示中は、古い生成プレビューが残っていても、表示中の XTC/XTCH ページを優先してPNG保存します。
- 追加機能の回帰テストとして、クリップボード一時TXT化、空クリップボード拒否、ツールバー plan、ファイルビューワー優先のPNG保存元選択を確認するテストを追加しました。
- 既存の変換コア、描画仕様、XTC/XTCH出力仕様、設定保存形式、プリセット形式は変更していません。

## v1.4.3.43

v1.4.3.43 は、v1.4.3.42 を基準に、非ZIPアーカイブ（RAR/CBR/7z 系を patool 経由で扱う経路）の展開安全性を少し強化した保守版です。

- ZIP/CBZ 以外の patool 展開を、直接 `tmpdir` へ出すのではなく専用 staging ディレクトリへ出すようにしました。
- 展開後に staging 外へ新規生成物が見つかった場合は、安全のためアーカイブ展開を中止します。
- RAR/CBR などで外部展開ツールに依存する経路に、`../` 系パス・トラバーサルへの防御的な検知を追加しました。
- ZIP/CBZ の既存の安全抽出経路、変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式に意図的な変更はありません。

## v1.4.3.42

v1.4.3.42 は、v1.4.3.41 を基準に、過大マージンで本文領域が消える設定を `ConversionArgs` の入口で拒否する保守版です。

- `ConversionArgs.__post_init__` に本文配置可能領域の検証を追加しました。
- `width - margin_l - margin_r` または `height - margin_t - margin_b` が `font_size` 未満になる場合、`ValueError` で明確に停止します。
- ページ番号 / 進捗バーの bottom reserve 反映後の `margin_b` を使って検証するため、下部オーバーレイ込みで本文領域不足を検出します。
- 退化したページ形状でプレビューが空白に見え、実変換ではページ数とファイルサイズが膨らむ経路を防ぎました。
- 既存テストの極小ページ用ダミー設定を、新しい `ConversionArgs` 契約に合う最小有効設定へ更新しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式に意図的な変更はありません。

## v1.4.3.41

v1.4.3.41 は、v1.4.3.39 を基準に、sweep368 レイアウト契約テストの PySide6 / shiboken hard-crash リスクを避けるための保守版です。

- `tests/test_sweep368_layout_contract_regression.py` を、PySide6 導入済み環境でも常に lightweight recording stand-ins で実行するようにしました。
- 実 Qt object と local fake widget tree が混在し、`section_preview_controls` 周辺で shiboken abort を起こし得る経路を避けました。
- `test_preview_toolbar_help_texts_are_substantive` は、引き続き plan 由来の tooltip / help text / objectName / range などの受け渡しを検証します。
- 行数削減目的の追加リファクタリングは行っていません。
- アプリ本体の変換仕様、描画仕様、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.39

v1.4.3.39 は、v1.4.3.38 を基準に、プリセット名称変更ダイアログと pending UI flush 処理を helper module へ分離した保守版です。

- `_preset_rename_dialog_result` の実装を `tategakiXTC_gui_studio_preset_actions_helpers.py` へ移動しました。
- `QDialog` / layout / widget class は entry wrapper から注入し、既存テストの monkeypatch 互換を維持しました。
- `_flush_pending_ui_changes` の実装を `tategakiXTC_gui_studio_ui_helpers.py` へ移動しました。
- `MainWindow` 側の既存メソッド名は thin wrapper として維持しました。
- split module compatibility test を追従更新しました。
- `tategakiXTC_gui_studio.py` は 5,228 行から 5,172 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.38

v1.4.3.38 は、v1.4.3.37 を基準に、XTC/XTCH ファイルビューワー状態の clear / target-change exit 処理を XTC load helper module へ分離した保守版です。

- `_clear_loaded_xtc_state` と `_leave_file_viewer_mode_for_target_change` の実装を `tategakiXTC_gui_studio_xtc_load_helpers.py` へ移動しました。
- `MainWindow` 側の既存メソッド名は thin wrapper として維持しました。
- split module compatibility test を追従更新しました。
- `tategakiXTC_gui_studio.py` は 5,269 行から 5,228 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.37

v1.4.3.37 は、v1.4.3.36 を基準に、実機風ビューの表示 runtime state と profile runtime state の反映処理を viewer profile helper module へ分離した保守版です。

- `_apply_viewer_display_runtime_state` / `_apply_profile_runtime_state` の実装を `tategakiXTC_gui_studio_viewer_profile_helpers.py` へ移動しました。
- `MainWindow` 側の既存メソッド名は thin wrapper として維持しました。
- split module compatibility test を追従更新しました。
- `tategakiXTC_gui_studio.py` は 5,306 行から 5,269 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.36

v1.4.3.36 は、v1.4.3.35 を基準に、optional dependency の起動時ログ表示と変換前依存チェックを helper module へ分離した保守版です。

- 新規 `tategakiXTC_gui_studio_dependency_helpers.py` を追加しました。
- `_log_optional_dependency_status` / `_missing_dependencies_for_targets` / `_check_conversion_dependencies` の実装を helper module へ移動しました。
- `core.list_optional_dependency_status` / `core.get_missing_dependencies_for_suffixes` / `_format_missing_dependency_message` は entry wrapper から注入し、既存テストの monkeypatch 互換を維持しました。
- split module compatibility test を追従更新しました。
- `tategakiXTC_gui_studio.py` は 5,335 行から 5,306 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.35

v1.4.3.35 は、v1.4.3.34 を基準に、プリセット summary 表示同期の残部を helper module へ分離した保守版です。

- `_sync_summary_payload` / `_sync_current_settings_summary` / `_sync_selected_preset_summary` / `_refresh_preset_ui` を `tategakiXTC_gui_studio_preset_summary_layout_helpers.py` へ移動しました。
- `MainWindow` 側の既存メソッド名は thin wrapper として維持しました。
- `_refresh_preset_ui` の signal block 処理は entry wrapper から注入し、既存テストの monkeypatch 互換を維持しました。
- split module compatibility test を追従更新しました。
- `tategakiXTC_gui_studio.py` は 5,373 行から 5,335 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.34

v1.4.3.34 は、v1.4.3.33 を基準に、単体変換前の出力名確認フローと、変換完了後の結果ガイダンス反映を helper module へ分離した保守版です。

- `_prepare_conversion_settings` を `tategakiXTC_gui_studio_settings_save_helpers.py` へ移動しました。
- `_build_conversion_completion_summary_lines` と `_apply_conversion_completion_guidance_to_results_view` を `tategakiXTC_gui_studio_conversion_finish_helpers.py` へ移動しました。
- `QInputDialog` / `Path` / `ConversionWorker._sanitize_output_stem` は entry wrapper から注入し、既存テストの monkeypatch 互換を維持しました。
- split module compatibility test を追従更新しました。
- `tategakiXTC_gui_studio.py` は 5,425 行から 5,373 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.33

v1.4.3.33 は、v1.4.3.32 を基準に、ログフォルダ表示、手動 XTC/XTCH 読込入口、XTC 読込後の view mode 反映、結果アイテム path 取得を helper module へ分離した保守版です。

- `open_log_folder` を `tategakiXTC_gui_studio_log_helpers.py` へ移動し、platform opener と dialog/status fallback の挙動を維持しました。
- `open_xtc_file` と `_apply_loaded_xtc_view_mode` を `tategakiXTC_gui_studio_xtc_load_helpers.py` へ移動しました。
- `_results_item_path` を `tategakiXTC_gui_studio_results_actions_helpers.py` へ移動しました。
- `_resolve_log_dir` / `_open_path_in_file_manager` / `Path.home()` / tab index は entry wrapper から注入し、既存テストの monkeypatch 互換を維持しました。
- `tategakiXTC_gui_studio.py` は 5,462 行から 5,425 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.32

v1.4.3.32 は、v1.4.3.31 を基準に、conversion runtime に残っていた run token 管理、worker signal dispatch、変換エラー終端処理を helper module へ分離した保守版です。

- `_next_conversion_run_token` / `_clear_active_conversion_run_token` / `_is_active_conversion_run_token` を `tategakiXTC_gui_studio_conversion_runtime_helpers.py` へ移動しました。
- `_connect_worker_dispatch_signals`、`_emit_worker_*`、`_dispatch_*` 系を同 helper へ移動しました。
- `on_conversion_error` の本体を `handle_conversion_error` として同 helper へ移動しました。
- `_connect_signal_best_effort` は entry wrapper から callable 注入し、既存の monkeypatch 互換を維持しました。
- `tategakiXTC_gui_studio.py` は 5,545 行から 5,462 行へ縮小しました。
- 変換仕様、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.31

v1.4.3.31 は、v1.4.3.30 を基準に、変換開始フロー、worker cleanup、ログ追記本体を helper module へ分離した保守版です。

- `start_conversion` を `tategakiXTC_gui_studio_conversion_runtime_helpers.py` へ移動し、QThread / ConversionWorker の接続フローを thin wrapper 経由にしました。
- `_schedule_cleanup_worker` / `cleanup_worker` を同 helper へ移動し、QTimer と safe delete は entry wrapper から注入する形を維持しました。
- `append_log` を `tategakiXTC_gui_studio_log_helpers.py` へ移動し、ログ欄・進捗ラベル・status fallback・render-failure 表示保持の挙動を維持しました。
- split module compatibility テストに、今回移動した wrapper / helper の同一性と entry module からの実装退避を確認する検査を追加しました。
- `tategakiXTC_gui_studio.py` は 5,627 行から 5,545 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.30

v1.4.3.30 は、v1.4.3.29 を基準に、XTC/XTCH document runtime と実機風ビュー描画フローの残部を helper module へ分離した保守版です。

- `_apply_xtc_document_payload` / `_apply_loaded_xtc_document` / `_current_xtc_page_blob` / `_clear_xtc_viewer_page` を `tategakiXTC_gui_studio_xtc_load_helpers.py` へ移動しました。
- `_apply_rendered_xtc_page` / `_set_current_device_preview_page_index` / `_set_current_page_index` / `load_xtc_from_path` / `load_xtc_from_bytes` / `render_current_page` を thin wrapper 化しました。
- `render_current_page` は `QImage.fromData` / `base64.b64decode` / `xt_page_blob_to_qimage` を entry wrapper から callable 注入し、既存の monkeypatch 互換と PySide6-free helper source 契約を維持しました。
- split module compatibility テストに、今回移動した wrapper / helper の同一性と entry module からの実装退避を確認する検査を追加しました。
- `tategakiXTC_gui_studio.py` は 5,829 行から 5,627 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.29

v1.4.3.29 は、v1.4.3.28 を基準に、リファクタリング計画書 第2版のイテレーション5として、プレビュー表示残部を helper module へ分離した保守版です。

- `render_current_preview_page` を `tategakiXTC_gui_studio_preview_pixmap_helpers.py` へ移動し、生成済みプレビューのページ表示・キャッシュ利用・失敗時ステータス反映を thin wrapper 経由にしました。
- `_refresh_active_view_after_mode_change` と `_refresh_font_preview_display_if_needed` を `tategakiXTC_gui_studio_preview_refresh_helpers.py` へ移動し、フォントビュー/実機風ビュー切替後の再描画フローを helper 側へ整理しました。
- split module compatibility テストに、今回移動した wrapper / helper の同一性と entry module からの実装退避を確認する検査を追加しました。
- `tategakiXTC_gui_studio.py` は 5,904 行から 5,829 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.28

v1.4.3.28 は、v1.4.3.27 を基準に、リファクタリング計画書 第2版のイテレーション4として、sweep368 レイアウト契約テスト後半を source inspection から挙動ベースへ置き換えた保守版です。

- `tests/test_sweep368_layout_contract_regression.py` の navigation / right preview stack / preview toolbar help 系の残り source pin を、split helper を軽量スタブ window 上で実行して確認する挙動テストへ整理しました。
- ナビゲーション行、ページ入力範囲、総ページラベル形式、右プレビュー stack chrome、前後ボタン文言反転の plan 反映を挙動で確認するようにしました。
- source-only 環境でも該当テストを実行できるよう、既存の PySide6 代替スタブを必要最小限だけ拡張しました。
- アプリ本体の変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.27

v1.4.3.27 は、v1.4.3.26 を基準に、リファクタリング計画書 第2版のイテレーション3として、結果アクション / XTC 読込フローを helper module へ分離した保守版です。

- `tategakiXTC_gui_studio_results_actions_helpers.py` を追加し、結果一覧反映、選択結果の読込、保存先を開く、XTC/XTCH 読込後の UI context 反映を分離しました。
- `on_result_item_clicked` / `load_selected_result` / `_show_conversion_results` / `populate_results` / `_apply_loaded_xtc_ui_context` などを thin wrapper 化しました。
- 既存テストの monkeypatch 互換を維持するため、`QListWidgetItem` / `QMessageBox` / file-manager opener は helper 内で entry module 側を runtime lookup する形にしました。
- `tategakiXTC_gui_studio.py` は 6,159 行から 5,904 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.26

v1.4.3.26 は、v1.4.3.25 を基準に、リファクタリング計画書 第2版のイテレーション2として、sweep368 レイアウト契約テスト前半を source inspection から挙動ベースへ置き換えた保守版です。

- `tests/test_sweep368_layout_contract_regression.py` の前半を、helper source 文字列検査ではなく、split helper を軽量スタブ window 上で実行して widget/layout へ反映された値を確認する形へ整理しました。
- ファイルビューワーセクション、右ペイン表示トグル、表示倍率コントロール、表示倍率ラベル/tooltip、右ペイン help text の plan 反映を挙動テスト化しました。
- source-only 環境でも該当テストを実行できるよう、テスト内に最小限の PySide6 代替スタブを追加しました。実 PySide6 がある環境では従来どおり実 Qt を使用します。
- sweep368 の実装ブロック source pin は前半分を削減し、後半の navigation / right preview stack 系を v1.4.3.28 以降の対象として残しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.25

v1.4.3.25 は、v1.4.3.24 を基準に、リファクタリング計画書 第2版のイテレーション1として、受領時のテスト追従漏れ修正と C-2 の低リスク分割を行った保守版です。

- v1.4.3.24 受領時に残っていた help 文言・glyph position 表示ラベル系の source inspection 追従漏れを、移動後 helper module も参照する形へ修正しました。
- フォルダ一括変換の menu/dialog entry point を `tategakiXTC_gui_studio_top_bar_helpers.py` へ分離しました。
- 表示言語セクションを `tategakiXTC_gui_studio_settings_sections_helpers.py` へ分離しました。
- `MainWindow` 側の既存 method 名は thin wrapper として維持しました。
- `REFACTORING_PLAN*.md` を release/source-only zip の除外対象に追加し、内部計画書が配布物へ混入しないようにしました。
- `tategakiXTC_gui_studio.py` は 6,233 行から 6,159 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.24

v1.4.3.24 は、v1.4.3.23 を基準に、リファクタリング計画書の A-9 としてホイールガード・起動時フォーカス退避処理を helper module へ分離した保守版です。

- `tategakiXTC_gui_studio_wheel_guard_helpers.py` を追加し、center settings wheel guard、combo popup 判定、wheel scroll 変換、起動時 input focus 退避を分離しました。
- `eventFilter` 本体は Qt event override として entry module に残し、判定・補助処理のみ helper 化しました。
- `MainWindow` 側の既存 method 名は thin wrapper として維持しました。
- wheel/focus guard 系の source inspection test を、移動後の helper module を参照する形へ付け替えました。
- `tategakiXTC_gui_studio.py` は 6,440 行から 6,233 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.23

v1.4.3.23 は、v1.4.3.22 を基準に、リファクタリング計画書の A-8 として右ペイン構築処理を helper module へ分離した保守版です。

- `tategakiXTC_gui_studio_right_pane_build_helpers.py` を追加し、右プレビューパネル、表示ツールバー、ナビゲーション行、倍率コントロール、変換完了カード周りを分離しました。
- `MainWindow` 側の既存 method 名は thin wrapper として維持しました。
- sweep368 / worker regression の plan 参照テストを、移動後の helper module を参照する形へ付け替えました。
- `tategakiXTC_gui_studio.py` は 6,862 行から 6,440 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.22

v1.4.3.22 は、v1.4.3.21 を基準に、リファクタリング計画書の A-7 前半として中央設定セクション構築処理を helper module へ分離した保守版です。

- `tategakiXTC_gui_studio_settings_sections_helpers.py` を追加し、出力先・組版・位置補正・プリセット・その他オプション・ファイルビューワーの section builder を分離しました。
- `MainWindow` 側の既存 method 名は thin wrapper として維持しました。
- section chrome / plan 参照の静的テストを、移動後の helper module を参照する形へ付け替えました。
- `tategakiXTC_gui_studio.py` は 7,305 行から 6,862 行へ縮小しました。
- 変換処理、描画結果、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.16

v1.4.3.16 は、v1.4.3.15 を基準に、リファクタリング計画書の A-2 と B-2 前半として、変換対象/保存先/外部フォント選択 helper 分割と、ステータス反映・render-failure 保持系のソースピン依存テスト 5 件の挙動テスト化を行った保守版です。

- `tategakiXTC_gui_studio_target_select_helpers.py` を追加し、変換対象ファイル選択、保存先フォルダ選択、保存先リセット、ドラッグ&ドロップ対象反映、外部フォントファイル選択処理を分離しました。
- `MainWindow` 側の既存 method 名は thin wrapper として維持しました。
- `test_gui_studio_worker_regression.py` の `test_source_declares_*` 系テストを 21 件から 16 件へ削減しました。
- 停止要求後の status fallback、変換 terminal fallback、append_log の render-failure 反映、preview status label の best-effort 更新、render-failure 表示中の通常 status 抑制を、実ロジック + 忠実スタブで検証する挙動テストへ置き換えました。
- 変換処理、描画処理、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.15

v1.4.3.15 は、v1.4.3.14 を基準に、リファクタリング計画書の A-1 と B-1 後半として、フォント選択 helper 分割と結果一覧・下部タブ系のソースピン依存テスト 4 件の挙動テスト化を行った保守版です。

- `tategakiXTC_gui_studio_font_combo_helpers.py` を追加し、フォント一覧取得、未検出フォントラベル、現在フォント値の正規化、既定フォント選択、フォント combo への値追加/選択処理を分離しました。
- `MainWindow` 側の既存 method 名は thin wrapper として維持しました。
- `test_gui_studio_worker_regression.py` の `test_source_declares_*` 系テストを 25 件から 21 件へ削減しました。
- `load_selected_result` / `on_result_item_clicked` / 結果一覧適用 / 変換開始・結果表示・失敗時タブ fallback を、実ロジック + 忠実スタブで検証する挙動テストへ置き換えました。
- 変換処理、描画処理、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.14

v1.4.3.14 は、v1.4.3.13 を基準に、リファクタリング計画書の Part B-1 前半として、結果一覧・下部タブ系のソースピン依存テスト 5 件を挙動テストへ置き換えた保守版です。

- `test_gui_studio_worker_regression.py` の `test_source_declares_*` 系テストを 30 件から 25 件へ削減しました。
- 結果サマリ、下部タブ切替、結果一覧の current/selected index fallback、結果エントリ適用時の初期選択、結果選択クリアを、実ロジック + 忠実スタブで検証する挙動テストへ置き換えました。
- 実装文字列に依存した検査を減らし、今後の helper 分割時にテストを機械的に付け替える負担を下げました。
- 変換処理、描画処理、UI 構成、設定保存形式、プリセット形式は変更していません。

## v1.4.3.13

v1.4.3.13 は、v1.4.3.12 を基準に、一番大きい GUI entry module の分割をさらに進めたリファクタリング保守版です。

- `tategakiXTC_gui_studio.py` のプリセット保存/適用/名称変更の確認・検証・自動プレビュー更新ロジックを `tategakiXTC_gui_studio_preset_actions_helpers.py` へ分離しました。`MainWindow` 側は既存 method 名を維持した薄い wrapper です（Qt ダイアログ構築の `_preset_rename_dialog_result` は entry module に残しています）。
- v1.4.3.12 公開版に残っていた、過去のリファクタで helper module へ移動済みの実装を旧 entry module 位置で検査していた静的回帰テスト 3 件（nav button text / preview toolbar help / margin row layout）を、現在の helper module を参照するよう修正しました。
- `tategakiXTC_gui_studio.py` は 8,158 行から 7,889 行へ縮小しました。
- 変換処理、描画処理、設定保存形式、プリセット形式は変更していません。

## v1.4.3.12

v1.4.3.12 は、v1.4.3.11 を基準に、GUI entry module の下部パネル構築と外部スクロールバー同期処理を helper module へ分離したリファクタリング保守版です。変換仕様・出力仕様・見える UI 構成は変更していません。

- `tategakiXTC_gui_studio_bottom_panel_helpers.py` を追加しました。
- `MainWindow._build_bottom_panel` / `_build_results_tab` / `_build_log_tab` は既存名を維持した thin wrapper にしました。
- 下部パネルの外部スクロールバー同期処理も同 helper module へ移動しました。
- `tategakiXTC_gui_studio.py` は 8,391 行から 8,158 行へ縮小しました。
- `build_release_zip.py` / `run_tests.bat` / `mypy.ini` / `.coveragerc` の管理対象に新 helper module を追加しました。
- 変換処理、描画処理、設定保存形式、プリセット形式は変更していません。

## v1.4.3.11

v1.4.3.11 は、v1.4.3.10 を基準に、GUI entry module の UI 構築処理をさらに helper module へ分離したリファクタリング保守版です。変換仕様・出力仕様・見える UI 構成は変更していません。

- `tategakiXTC_gui_studio.py` のトップバー構築処理を `tategakiXTC_gui_studio_top_bar_helpers.py` へ分離しました。
- プレビュー更新行と旧実寸補正互換 UI の生成、余白行生成を `tategakiXTC_gui_studio_preview_controls_helpers.py` へ分離しました。
- `MainWindow` 側の既存 method 名は維持し、呼び出し元との互換性を保っています。
- release tooling / mypy / coverage / run_tests の管理対象に新 helper module を追加しました。

## v1.4.3.10

v1.4.3.10 は、v1.4.3.9 を基準に、変換 runtime UI 周りを helper module へ分離したリファクタリング保守版です。

- `tategakiXTC_gui_studio.py` の変換開始時 UI 初期化、停止要求、進捗表示反映、変換失敗時 UI summary を `tategakiXTC_gui_studio_conversion_runtime_helpers.py` へ分離しました。
- `MainWindow` 側の既存 method 名は維持しています。
- 変換仕様・出力仕様・見える UI 構成は変更していません。

## v1.4.3.7

v1.4.3.7 は、v1.4.3.6 を基準に、公開前の配布整合性を整えた Python GUI 版のリリース準備版です。変換仕様や UI 構成は変更していません。

- `APP_VERSION` / `PUBLIC_VERSION` / `PREVIOUS_PUBLIC_VERSION` と release metadata を v1.4.3.7 / v1.4.3.6 に更新しました。
- README、RELEASE_CHECKLIST、release notes、publish checklist の現在版・前回版・添付ファイル名を v1.4.3.7 向けに揃えました。
- 添付元に残っていた過去の `dist/`、`logs/`、`.mypy_cache/` などの生成物は、release/source-only zip へ混入しないことを再確認しました。
- v1.4.3.6 までの GUI entry module 分割、render status helper、release gate 補完の内容は維持しています。
- XTC / XTCH の基本書き出し形式、EPUB / TXT / Markdown / 画像入力の基本変換処理は変更していません。

## v1.4.3.6

v1.4.3.6 は、v1.4.3.5 を基準に、一番大きい GUI entry module の分割をさらに進めたリファクタリング保守版です。

- `tategakiXTC_gui_studio.py` のプレビュー/実機風表示のレンダリングステータス更新と XTC ページ表示エラー処理を `tategakiXTC_gui_studio_render_status_helpers.py` へ分離しました。`MainWindow` 側は既存 method 名を維持した薄い wrapper です。
- `tategakiXTC_gui_studio_settings_restore_helpers.py` に重複していた `_bulk_block_signals` 実装を削除し、`tategakiXTC_gui_studio_ui_helpers.py` の共有実装を import する形に統一しました。
- v1.4.3.2〜v1.4.3.4 で追加された helper module 群と `tategakiXTC_gui_studio_logging.py` を `run_tests.bat` の compile チェック対象に追加しました。
- helper module へ移動済みのレンダリングステータス処理を、静的な回帰テストが正しいファイルで確認するように更新しました。
- XTC / XTCH の基本書き出し形式、EPUB / TXT / Markdown / 画像入力の基本変換処理は変更していません。

## v1.4.3.5

v1.4.3.5 is a Python GUI maintenance build based on v1.4.3.4. It fixes issues found while checking the v1.4.3.1 and later refactoring changes.
- Hardened the conversion-finish helper so refactoring-compatible window objects can resolve the original `MainWindow` finish helpers after the implementation was split out of `tategakiXTC_gui_studio.py`.
- Updated refactoring regression tests to inspect the helper modules that now own the moved logic instead of only inspecting the thin `MainWindow` wrappers.
- Restored the mandatory mypy release gate under current unpinned mypy/PySide stub versions by documenting and suppressing known dynamic GUI compatibility noise in `mypy.ini`.
- Conversion formats, EPUB/TXT/Markdown/image conversion behavior, and the visible GUI layout are unchanged.

## v1.4.3.4

v1.4.3.4 は、v1.4.3.3 を基準に、一番大きい GUI entry module の起動時プレビュー復元・サンプルプレビュー初期化処理を helper module へ分離したリファクタリング版です。

- `tategakiXTC_gui_studio.py` の起動時 target 復元、前回作業ファイル確認、サンプルプレビュー生成、起動後のプレビュー idle 状態 reconciliation を `tategakiXTC_gui_studio_startup_preview_helpers.py` へ分離しました。
- `MainWindow` 側の既存 method 名は維持し、既存呼び出し元との互換性を保っています。
- target field 変更時に XTC/XTCH file viewer mode を解除する既存の安全経路は維持しています。
- XTC / XTCH の基本書き出し形式、EPUB / TXT / Markdown / 画像入力の基本変換処理は変更していません。

## v1.4.3.3

v1.4.3.3 は、v1.4.3.2 を基準に、一番大きい GUI entry module の変換完了後の結果表示・ログ・ステータス反映処理を helper module へ分離したリファクタリング版です。

- `tategakiXTC_gui_studio.py` の `on_conversion_finished` 本体を `tategakiXTC_gui_studio_conversion_finish_helpers.py` へ分離しました。
- `MainWindow.on_conversion_finished` の既存 method 名は維持し、既存呼び出し元との互換性を保っています。
- 変換完了時の結果一覧、完了カード、警告ログ、停止時表示の呼び出し順は変更していません。
- XTC / XTCH の基本書き出し形式、EPUB / TXT / Markdown / 画像入力の基本変換処理は変更していません。

## v1.4.3.2

v1.4.3.2 は、v1.4.3.1 を基準に、一番大きい GUI entry module の設定復元・設定適用処理を helper module へ分離したリファクタリング版です。

- `tategakiXTC_gui_studio.py` の `_apply_settings_payload_to_ui` と `_restore_settings` の本体を `tategakiXTC_gui_studio_settings_restore_helpers.py` へ分離しました。
- `MainWindow` 側の既存 method 名は維持し、既存呼び出し元との互換性を保っています。
- 設定復元、UI 設定適用、プリセット復元の呼び出し順は変更していません。
- XTC / XTCH の基本書き出し形式、EPUB / TXT / Markdown / 画像入力の基本変換処理は変更していません。

## v1.4.3.1

v1.4.3.1 は、v1.4.2 のリファクタリング後に見つかった release gate / split module import まわりの保守修正版です。

- `run_tests.bat` の必須 mypy ステップが、split module の動的 globals 同期で失敗する問題を修正しました。
- `tategakiXTC_gui_core_*` split module を単独 import した場合に、`tategakiXTC_gui_core` との循環 import で失敗する問題を修正しました。
- PySide6 6.11 系で `QMenu.exec` の bound method patch が効かず、English UI widget scan test が offscreen で固まる問題を修正しました。
- XTC / XTCH の基本書き出し形式、EPUB / TXT / Markdown / 画像入力の基本変換処理、3ペインUI構成は変更していません。

## v1.4.2

v1.4.2 は、v1.4.1 公開後の保守・安定化をまとめた公開版です。内部作業版 v1.4.1.6〜v1.4.1.17 の細かな変更は、この v1.4.2 項目へ統合しています。

- 縦書き書籍のページ進行に合わせ、progress bar の既読部分が右端から左へ伸びる表示に変更しました。
- ギアメニューの「外観」見出しが English UI で日本語のまま残る問題を修正しました。
- English UI の offscreen 実ウィジェット走査テストを、オンデマンド生成されるポップアップメニューにも広げました。
- 閉じ括弧 `」` / `』` / `）` などが列頭に出る問題について、閉じ括弧をぶら下げ対象にせず、既存の protected group による「前の本文字ごと追い出し」へ整理しました。
- `」』` / `）」` / `。」』` のような閉じ括弧連続でも、2個目以降が列頭に残らないよう、閉じ括弧群をまとめて扱う既存方針を維持しました。
- v1.4.1.9 で試した広い先読みガードは、列末に大きな空白を作るため撤回しました。
- アプリ直下 `logs/` が存在しても書き込み不可の場合に、GUI が起動時に `PermissionError` で落ちる問題を修正しました。
- フォルダ一括変換の停止時に、「未処理件数」が1件多く表示される場合がある問題を修正しました。
- `logs/`、`*.log`、`__pycache__/`、`*.pyc`、`tategakiXTC_gui_studio.ini` などのローカル状態・生成物が source-only / public zip に混入しないよう、release/source-only zip hygiene を再確認しました。
- v1.4.1 の3ペインUI、English UI、XTC/XTCH出力形式、EPUB解析、ルビ描画の基本処理は維持しています。

## v1.4.1

v1.4.1 は、v1.4.0 公開後の安定化・仕上げをまとめた公開版です。内部作業版 v1.4.1.x / v1.4.2.x の細かな変更は、この v1.4.1 項目へ統合しています。

- ページ下部 progress bar と、ページ番号 / progress bar の下部オーバーレイ余白管理を追加・整理しました。
- 旧ページ番号 margin 設定との互換復元を維持しつつ、下部オーバーレイ用の共通 margin 管理へ移行しました。
- UI language support を追加し、初回起動時は OS ロケールに応じて日本語UI / English UI を自動選択するようにしました。
- Language 欄で選択した表示言語を ini に保存し、次回以降は保存済み言語を優先するようにしました。
- English UI の主要ラベル、ヘルプ、ツールチップ、ダイアログ、ログ、変換結果、フォルダ一括変換メッセージを英語化しました。
- English UI のウィンドウタイトルを `TategakiXTC GUI Studio <version>` にしました。日本語UIは `縦書きXTC Studio <version>` を維持します。
- 右ペイン表示モード切替後に、ヘルプツールチップが日本語へ戻る経路を修正しました。
- English UI の実ウィジェットを offscreen で走査するテストを追加し、ラベル、ツールチップ、コンボ、タブ、ウィンドウタイトルの未翻訳日本語を検出できるようにしました。
- 実 PySide6 走査はサブプロセスで実行し、通常の stub Qt 系テストと衝突しないようにしました。
- フォルダ一括変換 launcher の Python 3.10 / 3.11 互換性を修正しました。
- i18n 対応に合わせ、ソース文字列固定テスト、sweep 系テスト、TypedDict 期待値を現行実装へ同期しました。
- v1.4.0 からの描画・変換・EPUB・XTC/XTCH 出力ロジックは維持しています。

## v1.4.0

- run_gui.bat hardening: added pushd/cd fallback, app-file existence check, pause-on-failure messaging, and CRLF-only packaging guard for Windows batch launchers. - Public release

v1.4.0 は、前回公開版 v1.3.6 以降の v1.3.8.x 開発・安定化ラインを統合した公開版です。v1.3.7 は非公開のUI検討版として扱い、公開版の更新履歴には細かな v1.3.8.x ファイルを残していません。

- 3ペインUIへ整理し、画面構成を `Left Preset/Spec → Center Settings/Results → Right Preview` にしました。
- `XTC/XTCHを開く` を上部ボタン列へ移動し、中央設定ペインのスクロールとホイール誤操作防止を調整しました。
- 新規設定時の既定出力形式を XTCH にし、保存先指定・保存先リセット・保存先を開く周りの安全性を高めました。
- TXT行頭全角スペースの二重字下げ、行頭開き括弧の不要字下げ、標準禁則の短い文末処理、2-token約物ペアの hint cache を修正しました。
- 大きな折り返し字下げで縦組み描画が無限ループする問題、および過大な字下げ注記で本文がページ外に出る問題を修正しました。安全範囲を超える字下げは無効化し、本文が列頭付近から始まるようにしています。
- 画像入力の保存先生成、ライブプレビュー更新判定、画像変換中キャンセル伝播を修正しました。
- `last_shutdown_clean=false` などの起動状態メタデータだけが残った ini でも、復元対象なしの初回起動相当として安全に起動するようにしました。
- macOS / Linux のフォント検出候補を増やし、ヒラギノ / Osaka 系や等幅フォントの fallback を改善しました。
- XTC/XTCH読み戻しの page table stride 推定、BOMなしUTF-16日本語本文推定、ページ番号フォントサイズ上限処理を堅牢化しました。
- v1.3.8.x の細かな release notes / publish checklist は `docs/release_notes/RELEASE_NOTES_v1_4_0.md` と本項目へ統合しました。
- Windows 起動用 `run_gui.bat` / `install_requirements.bat` / `run_tests.bat` を CRLF 改行に正規化し、配布zip作成時にも `.bat` 改行を検査・補正するようにしました。
- `install_requirements.bat` / `run_tests.bat` も `run_gui.bat` と同じく、フォルダ切替失敗や終了時に `pause` を挟むよう統一し、Explorer からのダブルクリック実行でメッセージが読めずに閉じる経路を塞ぎました。

## v1.3.6 - Public release

- v1.3.5 以降の v1.3.6.x 作業版を、公開版 v1.3.6 として統合しました。
- ページ番号表示を追加し、ON/OFF、フォントサイズ指定、下余白の自動保護に対応しました。
- EPUB 入力の堅牢性を改善し、`linear="no"` spine、複雑な ruby / rtc、CSS selector、画像検出、大きな EPUB のメモリ負荷に関する処理を強化しました。
- プレビュー更新制御、起動直後の「生成中…」表示残り、ファイルビューワーモード解除、XTC / XTCH 表示中のキー操作を改善しました。
- 単体変換の別保存先指定、保存先リセット、「保存先を開く」の挙動を整理しました。
- 半角数字/記号、縦中横記号、半角英字の位置補正を追加・改善し、確認用の `sample_texts/` を同梱しました。
- TXT / Markdown / EPUB などの主経路 XTC / XTCH 書き出しに `fsync` と自己検証を追加し、書き出し信頼性を強化しました。
- フォルダ一括変換のキャンセル判定、log callback 防御、連番保存先探索上限、保存先 helper の防御的入力を改善しました。
- 公開版として `APP_VERSION` / `PUBLIC_VERSION` は `1.3.6` です。内部作業版としては v1.3.6.45 相当を基準にしています。

## v1.3.5

v1.3.5 は、公開版 v1.3.4 の縦中横記号表示を改善した小修正版です。内部作業版 v1.3.4.3〜v1.3.4.6 の表示調整をまとめ、安定版として扱います。

- 半角 `??` を、`!!` / `!?` / `?!` と同じく縦中横記号ペアとして扱うようにしました。
- 半角 `!?` / `??` / `!!` / `?!` を2文字ペアとしてトークン化し、半角数字とは別に扱います。
- 全角 `！？` / `？？` / `！！` / `？！` の右方向への張り出しを抑えるため、縦中横描画の貼り付けを ink bbox 中心基準へ寄せました。
- v1.3.4.3 で試した半角記号ペアの強い縮小は撤回し、半角 `!?` などが小さくなりすぎないようにしました。
- 画像処理セクションに「縦中横記号」の5段階位置補正を追加しました。対象は全角/半角の記号ペアのみで、数字の縦中横には適用しません。
- Noto 系フォントなどで記号ペアが上寄りに見える場合に備え、「下補正弱 / 強」の補正量を調整しました。
- 手動の「プレビュー更新」開始時に、未処理の設定変更由来 live preview 予約をキャンセルし、プレビュー更新が連鎖する場合がある問題を修正しました。
- XTC / XTCH 保存形式、ルビ描画ルーチン本体、フォルダ一括変換の基本処理は変更していません。

## v1.3.4

v1.3.4 は、GitHub 公開済みの v1.3.3 / v1.3.3.0 から、内部作業版 v1.3.3.x の改良をまとめた公開版です。

- ルビ消しモードを追加しました。
- 半角数字補正、半角数字の縦中横上限、半角英字・ASCII記号の縦書き表示を整理しました。
- 右ペイン高倍率プレビュー、ドラッグ＆ドロップ、変換完了カード、フォルダ一括変換の中止処理を改善しました。
- 中止時のエラー誤表示、プログレスバー継続、空表示を修正しました。
- 初回 ini 無し状態からのプリセット保存に sync / status / readback 確認を追加しました。
- GitHub 公開向け source-only zip と public zip の hygiene を整理しました。

## v1.3.3

v1.3.3 は、ルビ消しモード追加の基準として扱った公開版です。以後の v1.3.3.x は内部作業版として扱い、v1.3.4 にまとめました。

## v1.3.3.54

v1.3.3.54 は、v1.3.3.53 を基準に、GitHub 公開前の source-only zip hygiene と Source Available 表記を整理した作業版です。

- source-only zip から内部 handoff md と `logs/` が除外されるよう、source-only 用の生成経路を `build_release_zip.py --source-only` として追加しました。
- source-only zip には `.github/workflows/python-tests.yml` を含め、リポジトリへ展開した場合も CI 設定が残るようにしました。public zip では従来どおり `.github/` を除外します。
- `tests/test_cancel_stop_ui_regression_v13351.py` を release manifest に登録し、release bundle hygiene テストの期待一覧と同期しました。
- README に Source Available / not Open Source の明示を追加しました。
- 変換・描画ロジック、XTC / XTCH 保存処理本体、中止処理本体、プリセット保存処理本体は変更していません。

## v1.3.3.53

v1.3.3.53 は、v1.3.3.52 を基準に、初回起動時など ini ファイルが無い状態からのプリセット保存をより安全にした作業版です。

- プリセット保存後に `QSettings.sync()` を実行したうえで、`QSettings.status()` を確認するようにしました。
- 保存したプリセット値を再読込し、書き込んだ値と一致するか確認してから「保存しました」と表示するようにしました。
- 書き込み不可フォルダ、読み取り専用 ini、zip 内直接起動などで保存確認に失敗した場合は、保存成功表示ではなく警告を出すようにしました。
- プリセット関連の大きな UI 変更、プリセット値の自動反映、プリセット名編集はまだ入れていません。
- 変換・描画ロジック、XTC / XTCH 保存処理本体、中止処理本体は変更していません。

## v1.3.3.52

v1.3.3.52 は、v1.3.3.51 を基準に、中止後に右ペイン上部の中止カードが出ない問題を修正した作業版です。

- 単独変換を中止して保存済みファイルが0件の場合でも、「変換を中止しました」カードを表示するようにしました。
- フォルダ一括変換を中止して保存済みファイルが0件の場合も、「フォルダ一括変換を中止しました」と明示するようにしました。
- 中止カードの「保存先を開く」は、開ける保存先がある場合だけ有効にしました。

## v1.3.3.51

v1.3.3.51 は、v1.3.3.50 を基準に、中止要求時の表示を再修正した作業版です。

- EPUB の章描画中に停止要求が入った場合、`ConversionCancelled` を EPUB 本文描画エラーへ包まず、そのまま中止として扱うようにしました。
- 停止要求後に通常変換の進捗シグナルが残って届いても、プログレスバーを不定進捗へ戻さず、静止表示を維持するようにしました。
- 念のため、変換失敗レポート側でも停止系メッセージを EPUB / HTML / CSS エラーではなくユーザー停止として整形する fallback を追加しました。


## v1.3.3.50

v1.3.3.50 は、v1.3.3.49 を基準に、フォルダ一括変換の中止要求後もプログレスバーが動き続けて見える問題を修正した作業版です。

- 中止ボタン押下時に、進捗バーを現在位置の静止表示へ固定するよう修正しました。
- 中止要求後の内部進捗で「フォルダ一括変換中…」へ戻らないようガードしました。
- 中止待機中の表示を「中止中」に統一しました。

## v1.3.3.49

v1.3.3.49 は、v1.3.3.48 を基準に、フォルダ一括変換の中止ボタン挙動と報告欄の文言を整理した修正版です。

- フォルダ一括変換の中止ボタンで、現在処理中の個別変換 worker にも停止要求を伝えるようにしました。
- コア側が停止チェックできる箇所では、現在ファイルの完了待ちではなく途中停止しやすくしました。
- 変換中止を通常の失敗扱いにせず、`cancelled` 状態として集計するようにしました。
- 中止時の報告欄から「完了確認」など完了向けの文言が混ざらないように整理しました。
- フォルダ一括変換の完了/中止状態も右ペイン上部の完了カードへ反映しやすくしました。
- 通常変換の保存処理、XTC / XTCH 保存処理、縦書き描画ロジックは変更していません。

## v1.3.3.48

v1.3.3.48 は、v1.3.3.47 を基準に、変換完了後の右ペイン完了カードを見直した GUI 小改良版です。

- 変換完了後に Windows エクスプローラーを自動起動しないようにしました。
- 右ペイン上部の変換完了カードから「実機ビューで確認」「変換結果を見る」ボタンを削除しました。
- 完了カード内に、保存結果のミニ一覧を直接表示するようにしました。
- 単独ファイル、複数ファイル、サブフォルダ込み一括変換で表示文言と出力例を出し分けます。
- 完了カードの操作は「保存先を開く」と「閉じる」に整理しました。
- 左下の「変換結果」タブの詳細表示は従来どおり維持しています。
- 変換・描画ロジック、ドラッグ＆ドロップ指定、中央セパレーター 600px、ルビ消しページ維持、ディザリング更新制御は変更していません。

## v1.3.3.47

v1.3.3.47 は、v1.3.3.46 を基準に、変換完了後の確認導線を右ペイン上部へ見える形で追加した GUI 小改良版です。

- 変換完了後、右ペイン上部に「変換完了カード」を表示するようにしました。
- カード内に保存件数、保存先、サブフォルダ構造保持の要約を表示します。
- `保存先を開く` / `実機ビューで確認` / `変換結果を見る` / `閉じる` の操作ボタンを追加しました。
- 単独ファイル、複数ファイル、サブフォルダ込み一括変換で文言を出し分けます。
- 左下の「変換結果」タブの詳細表示は従来どおり維持しています。
- 変換・描画ロジック、中央セパレーター 600px、ルビ消しページ維持、ディザリング更新制御、XTC / XTCH 保存処理には変更ありません。

## v1.3.3.46

v1.3.3.46 は、v1.3.3.45 を基準に、中央セパレーターの既定位置を 600px に固定した GUI 小改良版です。

- 左右ペインの中央セパレーター既定位置を `600px` に変更しました。
- 旧既定値 `760px` / `800px` / `820px` が UI 状態として保存されている環境では、起動時に新既定幅 `600px` へ穏やかに移行します。
- 手動で別の幅へ調整済みのケースでは、その保存幅を維持します。
- 変換・描画ロジック、ドラッグ＆ドロップ指定、ルビ消しページ維持、ディザリング更新制御、XTC / XTCH 保存処理には変更ありません。

## v1.3.3.45

v1.3.3.45 は、v1.3.3.44 を基準に、ルビ消し時のページ維持とディザリング時のプレビュー更新制御を修正した小修正版です。

- ルビ消し ON/OFF 時に、プレビューページが1ページ目へ戻らないようにしました。
- ディザリング ON/OFF 時のプレビュー更新を debounced live refresh 経路に寄せました。
- プレビュー生成中に設定変更が入った場合、50ms 間隔の完了待ちポーリングを積み続けず、現在の生成完了後に1回だけ後続更新を予約するようにしました。
- 変換・描画ロジック本体、XTC / XTCH 保存処理は変更していません。

## v1.3.3.44

v1.3.3.44 は、v1.3.3.43 を基準に、変換完了後の確認導線を強化した GUI 改良版です。

- 通常変換の完了後、変換結果タブに保存結果の確認案内を追加しました。
- 単独ファイル変換では、出力ファイル名・保存先・実機ビューでの確認方法を表示します。
- 複数ファイル変換では、保存件数・保存先・下の一覧から確認できることを表示します。
- サブフォルダを含む一括変換では、複数フォルダ保存やフォルダ構造保持が分かる案内を追加しました。
- フォルダ一括変換の完了後も、成功した出力ファイルを変換結果一覧へ反映します。
- 変換・描画ロジック、ドラッグ＆ドロップ指定、左右ペイン既定幅、半角数字補正、ルビ消し、XTC / XTCH 保存処理には変更ありません。

## v1.3.3.43

v1.3.3.43 は、v1.3.3.42 を基準に、変換完了後の確認導線を強化した GUI 小改良版です。

- 通常変換の完了後、変換結果タブに保存結果の確認案内を追加しました。
- 単独ファイル変換では、出力ファイル名・保存先・実機ビューでの確認方法を表示します。
- 複数ファイル変換では、保存件数・保存先・下の一覧から確認できることを表示します。
- サブフォルダを含む一括変換では、複数フォルダ保存やフォルダ構造保持が分かる案内を追加しました。
- フォルダ一括変換の完了後も、成功した出力ファイルを変換結果一覧へ反映します。
- 変換・描画ロジック、ドラッグ＆ドロップ指定、左右ペイン既定幅、半角数字補正、ルビ消し、XTC / XTCH 保存処理には変更ありません。

## v1.3.3.42

v1.3.3.42 は、v1.3.3.41 を基準に、左右ペインの既定の仕切り位置をさらに左寄りへ再調整した GUI 小改良版です。

- 左右ペインの既定仕切り位置をさらに左寄りへ調整しました。
- 左ペイン既定幅を `760px` に変更しました。
- 旧既定値 `800px` と、v1.3.3.41 の既定値 `820px` が UI 状態として保存されている環境では、起動時に新既定幅 `760px` へ穏やかに移行します。
- 手動で別の幅へ調整済みのケースでは、その保存幅を維持します。
- 変換・描画ロジック、ドラッグ＆ドロップ指定、半角数字補正、ルビ消し、XTC / XTCH 保存処理には変更ありません。

## v1.3.3.41

v1.3.3.41 は、v1.3.3.40 を基準に、左右ペインの既定の仕切り位置を添付見本に近いバランスへ微調整した GUI 小改良版です。

- 左右ペインの既定仕切り位置を少し右寄りへ調整しました。
- 左ペイン既定幅を `800px` から `820px` に変更しました。
- 旧既定値 `800px` が UI 状態として保存されている環境では、起動時に新既定幅 `820px` へ穏やかに移行します。
- 手動で別の幅へ調整済みのケースでは、その保存幅を維持します。
- 変換・描画ロジック、ドラッグ＆ドロップ指定、半角数字補正、ルビ消し、XTC / XTCH 保存処理には変更ありません。

## v1.3.3.39

v1.3.3.39 は、v1.3.3.38 を基準に、実 PySide6 smoke test と public zip 内テストの衝突を修正したテスト基盤修正版です。

- optional な実 PySide6 smoke test を通常フルスイートから外し、`RUN_REAL_QT_SMOKE=1` を指定したときだけ実行する opt-in テストに変更しました。
- 通常の `run_tests.bat` / GitHub Actions / public zip 内テストでは、実 Qt と PySide6 テストスタブを同一 Python プロセス内で切り替えないようにしました。
- `.github/workflows/python-tests.yml` の存在確認は、workflow が存在する repo 環境だけで行い、public zip では skip するようにしました。
- `.github/` はリポジトリ用ファイルとして tracked にしつつ、public zip からは引き続き除外します。
- 縦中横モード、半角英字・ASCII記号、半角数字補正、ルビ消し、XTC / XTCH 保存処理などの描画・変換ロジックは変更していません。

## v1.3.3.38

v1.3.3.38 は、v1.3.3.37 を基準に、GUI 回帰テストの isolation を根本対処し、GitHub Actions の最小 CI を追加したテスト基盤修正版です。

- `load_studio_module()` 経由の GUI 単体テストは、実 PySide6 がインストールされた環境でも常にテストスタブを使うようにしました。
- `QTimer.singleShot` などの Qt class-level monkey patch がテスト間に残らないよう、`tests/conftest.py` の setup / fixture / teardown 復元を強化しました。
- optional な実 PySide6 smoke test は、テストスタブを明示的に外してから実 Qt を読み込むように分離しました。
- `.github/workflows/python-tests.yml` を追加し、Python 3.10 / 3.11 で pytest、golden check、public zip build/verify を行う最小 GitHub Actions CI を用意しました。
- `.github/` はリポジトリ用ファイルとして tracked にしつつ、public zip からは引き続き除外します。
- 縦中横モード、半角英字・ASCII記号、半角数字補正、ルビ消し、XTC / XTCH 保存処理などの描画・変換ロジックは変更していません。

## v1.3.3.37

v1.3.3.37 は、v1.3.3.36 を基準に、半角英字・ASCII記号の縦書き本文中の扱いを整理した組版調整版です。

- 半角英字を含む連続半角文字列を、縦中横ではなく1文字ずつ中央揃えで描画するようにしました。
- ASCII記号を縦中横扱いにせず、1文字ずつ中央揃えで描画するようにしました。
- ASCII括弧類 `() [] {} <>` は、右90度回転して中央揃えで描画します。
- 半角数字だけの連続文字列は、引き続き `縦中横` 設定（4文字 / 3文字 / 2文字 / 無し）に従います。
- 縦中横モード、半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの既存機能は維持しています。

## v1.3.3.36

v1.3.3.36 は、v1.3.3.35 を基準に、実 PySide6 環境での GUI 回帰テスト isolation を強化したテスト基盤修正版です。

- `QTimer.singleShot` などの Qt class-level monkey patch がテスト間に残る可能性を抑えるため、テスト helper に明示的な復元処理を追加しました。
- GUI 回帰テスト実行前後に Qt の可変テスト状態を復元する `tests/conftest.py` の autouse fixture を追加しました。
- `test_studio_import_helper_isolation.py` を、実 PySide6 環境でも成立する復元確認テストへ修正しました。
- 縦中横モード、半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.35

v1.3.3.35 は、v1.3.3.34 を基準に、半角数字の縦中横上限を選べるようにした組版機能追加版です。

- 「出力・フォント・組版」セクションに `縦中横` 設定を追加しました。
- 選択肢は `4文字 / 3文字 / 2文字 / 無し` です。
- デフォルトは `2文字` です。
- プレビュー、XTC / XTCH 保存、プリセット（ini）保存・読み込みへ反映します。
- プリセット仕様表示にも縦中横設定を表示します。
- 半角数字の縦位置補正、ルビ消し、右ペイン表示倍率補間、ページ送りキー反転など既存機能は維持しています。

## v1.3.3.34

v1.3.3.34 は、v1.3.3.33 を基準に、ファイルビューワー欄のヘルプボタン位置をさらに左寄せにした小改良版です。

- ファイルビューワー欄の `?` ヘルプボタンを、`XTC/XTCHを開く` ボタンの近くへ寄せました。
- `open_xtc_help_leading_spacing` を 8 に変更し、右端寄りの余白をなくしました。
- プレビュー欄、画像処理欄、左上バージョン表示など v1.3.3.33 までの整理は維持しています。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.33

v1.3.3.33 は、v1.3.3.32 を基準に、左ペイン上部のヘルプボタン位置とバージョン表示を整理した小改良版です。

- プレビュー欄の `?` ヘルプボタンを、行の右端から左寄りへ移動しました。
- ファイルビューワー欄の `?` ヘルプボタンも左寄りへ移動しました。
- どちらも画像処理欄の「波線位置」ヘルプボタンに近い位置へ揃え、ヘルプボタン列のばらつきを減らしました。
- 上部バー左端のバージョン表示を、目立つバッジから控えめなテキスト表示へ変更しました。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.32

v1.3.3.32 は、v1.3.3.31 を基準に、右ペインのページ送り反転設定の配置と名称を整理した小改良版です。

- 右ペイン下部にあった「ボタン反転」を、歯車メニュー内へ移動しました。
- 設定名を「ページ送りキー反転」に変更しました。
- ページ送りキー反転の設定保存・読み込みキー `nav_buttons_reversed` は維持しています。
- 右ペイン下部のページ送り行から反転チェックボックスを外し、表示中ラベル / 前・次ボタン / ページ入力 / 表示倍率の並びを整理しました。
- ヘルプ本文も、歯車メニューの「ページ送りキー反転」から設定する説明へ更新しました。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.31

v1.3.3.31 は、v1.3.3.30 を基準に、左ペインと下部パネルの表示文言・空状態表示を整理した小改良版です。

- プリセット操作ボタンの文言を「プリセット読込」「プリセット保存」に変更しました。
- クライアント領域左上のアプリ名重複表示を避け、上部バー側は `v1.3.3.31` のバージョンバッジだけを表示します。
- 画像処理の「白黒反転（出力）」を「白黒反転」に短縮しました。
- 設定変更後の未反映状態では、プレビュー更新ボタン自体を橙色の注意表示にして見落としにくくしました。
- 変換結果の空プレースホルダーを灰色・中央寄せ表示にしました。
- 下部ステータスの初期表示で「待機中」が重複しないようにしました。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.30

v1.3.3.30 は、v1.3.3.29 を基準に、フォント選択行の「参照」ボタン位置を調整した小改良版です。

- フォント選択行の「参照」ボタンを、従来より左寄りへ配置しました。
- フォントコンボを行の約 2/3 幅に抑え、右側に伸縮余白を残すことで、参照ボタンが右端へ離れすぎないようにしました。
- 左ペイン上部の横・縦スクロール、画像処理セクション2行構成、プリセット（ini）保存・読み込み経路は v1.3.3.29 の状態を維持しています。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.29

v1.3.3.29 は、v1.3.3.28 を基準に、左ペインと画像処理セクションの表示密度を調整した小改良版です。

- 左右ペインの初期仕切り位置を中央寄りにしました。
- 左ペイン上部の設定エリアに横・縦スクロールを明示し、小さいウィンドウでも設定項目が切れて見えにくくなるリスクを減らしました。
- 画像処理セクションの位置補正項目を2行に整理しました。
  - 1行目: 句読点 / 漢数字 一 / 半角数字
  - 2行目: 下鍵括弧 / 波線描画 / 波線位置
- 句読点、漢数字 一、半角数字、下鍵括弧、波線描画、波線位置のプリセット（ini）保存・読み込み経路は維持しています。
- 半角数字補正は、左ペイン上部のプリセット仕様表示には追加していません。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.28

v1.3.3.28 は、v1.3.3.27 を基準に、テスト用 PySide6 スタブと split module の isolation を強化した小修正版です。

- `load_studio_module(force_reload=True)` 実行時に、テスト用 PySide6 スタブと `tategakiXTC_` split module 群も再構築するようにしました。
- `QTimer.singleShot` など、前のテストが変更したスタブ状態が後続テストへ残る可能性を減らしました。
- force reload 時のスタブ再構築と split module 再読込を確認する回帰テストを追加しました。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.27

v1.3.3.27 は、v1.3.3.26 を基準に、公開ドキュメントと release 回帰テストの整合性を修正した小修正版です。

- README の公開版表記、public zip 名、GitHub Release 情報、release notes 参照先を現行 metadata と一致させました。
- CHANGELOG の先頭に v1.3.3.26 セクションが CHANGELOG タイトルより前へ出ていた構造破損を修正しました。
- release docs 回帰テストの APP_VERSION 固定文字列を、release metadata 参照へ変更しました。
- release notes 回帰テストから、任意のリリースに特定本文キーワードを要求する設計を外しました。
- 半角数字補正、ルビ消し、右ペイン表示倍率補間、XTC / XTCH 保存処理などの変換・描画ロジックは変更していません。

## v1.3.3.26

v1.3.3.26 は、v1.3.3.25 の半角数字位置補正を少し強めた小修正版です。

- 半角数字専用の縦位置補正量を少し強めました。
- 単独半角数字と、半角数字だけの縦中横の両方に反映されます。
- 句読点、漢数字 一、下鍵括弧、波線の補正量・描画ルーチンは変更していません。

## v1.3.3.25

v1.3.3.25 は、v1.3.3.24 で追加した半角数字位置補正がプレビューで効かない問題を修正した小修正版です。

- プレビュー生成用 `ConversionArgs` に `halfwidth_digit_position_mode` を渡すよう修正しました。
- プレビューキャッシュキーにも `halfwidth_digit_position_mode` を含め、半角数字補正を変更した直後に古いプレビューが再利用されないようにしました。
- プリセット正規化でも `halfwidth_digit_position_mode` を保持するようにしました。
- 単独半角数字と半角数字だけの縦中横に補正が効き、ルビ内数字には効かないことを回帰テストで確認しました。
- v1.3.3.24 の半角数字補正UI、XTC / XTCH 保存経路、右ペイン表示倍率補間、ルビ消し、余白UI、ヘルプ改行表示は維持しています。

## v1.3.3.24

v1.3.3.24 は、v1.3.3.23 を基準に、フォントによって半角数字の縦方向位置がずれて見える場合に調整できる「半角数字」位置補正を追加した小改良版です。

- 画像処理セクションの位置補正行に「半角数字」を追加し、句読点 / 漢数字 一 / 半角数字 / 下鍵括弧 の順に並べました。
- 半角数字補正は、句読点・漢数字一・下鍵括弧と同じ5モード（下補正強 / 下補正弱 / 標準 / 上補正弱 / 上補正強）です。
- 補正対象は半角数字のみです。全角数字とルビ内数字は対象外です。
- 通常の単独半角数字に加え、半角数字だけで構成される縦中横トークンにも補正を反映します。
- プレビューだけでなく XTC / XTCH 保存にも `halfwidth_digit_position_mode` を通すようにしました。
- v1.3.3.23 までの右ペイン表示倍率補間、実機ビュー初期同期、ルビ消し、余白UI、単体変換後フォルダ表示、ヘルプ改行表示は維持しています。

## v1.3.3.23

v1.3.3.23 は、v1.3.3.22 を基準に、起動直後に実機ビューボタンを押したとき、実機表示部だけが左へ寄る初期同期問題を修正した小修正版です。

- 実機ビュー切替直後に、実機ビューのサイズ・左寄せ補間余白・横スクロール位置を即時同期する処理を追加しました。
- Qt の stacked widget / scroll area の表示領域が確定した後にも同じ同期を再実行し、起動直後だけ `preview_leading_gap` が 0 に近くなる状態を避けるようにしました。
- XTC / XTCH ページ画像の適用後、空表示への切替後にも同じ同期を行い、実機ビューと実寸近似の初期表示を安定化しました。
- v1.3.3.22 の3モード共通補間カーブ、横スクロールバー、ルビ消し、余白UI、単体変換後フォルダ表示、ヘルプ改行表示は維持しています。

## v1.3.3.22

v1.3.3.22 は、v1.3.3.21 を基準に、右ペインのフォントビュー・実機ビュー・実寸近似で、表示倍率を連続して上げたときの表示位置移動をより自然にした小修正版です。

- 3モード共通の左寄せ補間カーブを、100%→200%で完了する動きから、100%→300%にかけてゆっくり進む動きへ変更しました。
- 100%〜150%付近では中央寄せ感を強めに残し、200%以降で段階的に左寄せへ近づくようにしました。
- フォントビュー・実機ビュー・実寸近似は引き続き同じ補間ロジックを使用します。
- 変換処理、保存処理、ルビ消し、余白UI、単体変換後フォルダ表示、ヘルプ改行表示は維持しています。

## v1.3.3.21

v1.3.3.21 は、v1.3.3.20 を基準に、右ペインのフォントビュー・実機ビュー・実寸近似の高倍率表示で、100%付近からの左寄せ補間挙動を揃えた小修正版です。

- 実機ビュー／実寸近似で、100%から110%へ上げたときに `QScrollArea` の中央寄せから左寄せへ切り替わる処理を廃止しました。
- 3モードとも、左上寄せのスクロール領域に対して、倍率に応じた `leading_gap` と横スクロール位置補間で表示位置を調整する方針へ揃えました。
- 実寸近似時の `sizeHint()` と描画側で異なっていた外側余白計算を共通化し、未描画背景による見かけのズレを減らしました。
- v1.3.3.20 までの横スクロールバー、フォントビュー補間、ルビ消し、余白UI、単体変換後フォルダ表示、ヘルプ改行表示は維持しています。

## v1.3.3.20

v1.3.3.20 は、v1.3.3.19 を基準に、右ペインの実機ビュー／実寸近似でも、表示倍率を100%から110%へ上げたときに急に左寄せへ切り替わらず、フォントビューと同様に倍率に応じて徐々に左へ動くよう調整した小修正版です。

- 実機ビュー用ウィジェットに、倍率補間に応じた左側余白を渡せるようにしました。
- 実機ビュー／実寸近似で、表示内容が表示領域より小さい間は左側余白を段階的に縮小し、表示領域より大きい場合は横スクロール位置を段階的に左へ寄せます。
- v1.3.3.19 のフォントビュー補間、横スクロールバー、ルビ消し、余白UI、単体変換後フォルダ表示、ヘルプ改行表示は維持しています。

## v1.3.3.19

v1.3.3.19 は、v1.3.3.18 を基準に、右ペインのフォントビュー高倍率表示で、100%から110%へ上げたときに急に左寄せへ切り替わる挙動を、倍率に応じて徐々に左へ動くよう調整した小修正版です。

- フォントビューのプレビュー配置に、100%では中央寄せ相当、200%以上では左寄せ相当になる smoothstep 型の補間を追加しました。
- プレビュー画像が表示領域より小さい場合は左側の余白を段階的に縮め、表示領域より大きい場合は横スクロール位置を中央寄りから左端へ段階的に移動します。
- 実機ビュー側も高倍率時の横スクロール位置を同じ補間で扱い、100%直後の急な左端移動を避けるようにしました。
- 変換処理、保存処理、ルビ消し、ルビ描画本体、余白UI、プリセット仕様表示、ヘルプ文面は変更していません。
## v1.3.3.18

v1.3.3.18 は、v1.3.3.17 を基準に、右ペインのフォントビュー高倍率表示で、プレビュー画像がラベル内部で中央寄せされたままになり、左側スペースが固定的に残る問題を追加修正した小修正版です。

- フォントビューのプレビュー画像を、実際の scaled pixmap サイズに合わせてラベルサイズ固定するよう修正。
- 高倍率時は `QScrollArea` だけでなく `QLabel` 側の pixmap 配置も左上寄せに変更。
- プレビュー非表示・メッセージ表示時にはラベルサイズ固定を解除し、通常表示へ戻すよう調整。
- v1.3.3.16 / v1.3.3.17 の実機ビュー・フォントビュー側スクロール補正は維持。
- 変換処理、保存処理、ルビ消し、余白UI、プリセット仕様表示、ヘルプ文面は変更なし。

## v1.3.3.17

v1.3.3.17 は、v1.3.3.16 を基準に、右ペインのフォントビュー高倍率表示で左側スペースが固定的に残り、ページ右側が見切れて見える問題を修正した小修正版です。

- フォントビュー用 `QScrollArea` に横スクロールバー / 縦スクロールバーを明示設定。
- 表示倍率が 100% を超える場合、フォントビューを左上寄せに切り替え、中央スプリッター側の空白を縮小。
- プレビュー画像の再描画後、横スクロール位置を左端へ戻す処理を追加。
- v1.3.3.16 の実機ビュー側スクロール補正は維持。
- 変換処理、保存処理、ruby_hide、ルビ描画本体、余白UI、プリセット仕様表示、ヘルプ文面は変更なし。

## v1.3.3.16

v1.3.3.16 は、v1.3.3.15 を基準に、右ペイン実機ビューの高倍率表示で、中央スプリッター側に余白が残って見える問題を追加修正した版です。

- v1.3.3.15 で追加した横スクロールバー表示方針は維持しています。
- 実機ビューの `sizeHint` と描画矩形を同じ device-body 基準に揃え、未描画背景がスプリッター側に大きく残らないようにしました。
- 表示倍率が 100% を超えると、実機ビューのスクロールエリアを左上寄せに切り替え、横スクロールの開始位置を左端へ戻すようにしました。
- 100% 以下では中央寄せ表示を維持し、通常時の見た目が極端に左へ寄らないようにしています。
- 変換処理、保存処理、ルビ消し、余白UI、プリセット仕様表示、ヘルプ文面の既存挙動は変更していません。

## v1.3.3.14

v1.3.3.14 は、v1.3.3.13 を基準に、`?` ヘルプウィンドウ内の複数項目説明を読みやすくした小修正版です。

- 出力形式 / 機種 / 禁則処理 / プレビュー更新 / 句読点 / 漢数字 一 / 下鍵括弧 / 波線描画 / 波線位置 / 同名出力 / 使い方の流れ の説明に、項目ごとの改行を追加しました。
- 既に改行済みだった画像処理右端ヘルプ、上部3ボタンヘルプ、フォントビュー / 実機ビュー系ヘルプは維持しています。
- 変換処理、保存処理、ルビ消し、余白UI、プリセット仕様表示の既存挙動は変更していません。

## v1.3.3.13

v1.3.3.13 は、v1.3.3.12 を基準に、プリセット仕様表示欄の余白表示順を修正した小修正版です。

- プリセット仕様表示欄の余白表示を、`上 / 下 / 右 / 左` から `上 / 下 / 左 / 右` へ変更しました。
- 余白UI本体、余白値の保存・読み込み、プレビュー反映ロジックは変更していません。
- 単体ファイル変換後に開くフォルダの v1.3.3.12 修正は維持しています。
- ルビ消し、余白1行レイアウト、ヘルプ改行表示、XTC / XTCH 保存の既存挙動は維持しています。

## v1.3.3.12

v1.3.3.12 は、v1.3.3.11 を基準に、単体ファイル変換後に開くエクスプローラーの対象フォルダを修正した版です。

- 単体ファイル変換では、完了後に開くフォルダをソースファイルの親フォルダへ固定しました。
- フォルダ一括変換やフォルダ入力時の出力フォルダ解決は従来のまま維持しています。
- ルビ消し、余白1行レイアウト、ヘルプ改行表示、XTC / XTCH 保存の既存挙動は維持しています。

## v1.3.3.11

v1.3.3.11 は、v1.3.3.10 を基準に、ルビ消しチェックの並び順とヘルプ表示の読みやすさを調整した版です。

- 画像処理セクション先頭のルビ消しを、他のチェック項目と同じく `□ ルビ消し` の並びへ統一しました。
- 画像処理セクション右端の `?` ヘルプで、複数項目の説明が項目ごとに改行されるようにしました。
- ヘルプダイアログは PlainText 表示にして、改行がそのまま反映されるようにしました。
- ルビ消し ON/OFF、プレビュー、XTC / XTCH 保存の既存挙動は維持しています。

## v1.3.3.9

v1.3.3.9 は、v1.3.3.8 を基準に、余白設定 UI の並びを整理した版です。

- 上余白 / 下余白 / 左余白 / 右余白 の設定を、2行構成から1行構成へまとめました。
- ユーザー指定の「右から、上余白・下余白・左余白・右余白」に合わせ、実際の左から右の並びは「右余白・左余白・下余白・上余白」としています。
- 余白値そのものの保存・読み込み・プレビュー反映ロジックは変更していません。

## v1.3.3.8

v1.3.3.8 は、v1.3.3.7 を基準に、画像処理セクション先頭行のヘルプ構成を整理した版です。

- 「ルビ消し」の右にあった個別の「？」を削除しました。
- 行の一番右にある共通ヘルプ「？」へ、ルビ消し / 白黒反転（出力） / ディザリング / しきい値 の説明を集約しました。
- ルビ消しの機能、保存経路、レイアウト色調整、右側空白調整は従来どおりです。

## v1.3.3.7

v1.3.3.7 は、v1.3.3.6 の実機確認で見つかったルビ消しUI色と、ルビ消し時の右側空白を調整した版です。

- 「ルビ消し」ラベルの色を、白黒反転（出力）などのチェックボックス文字色と揃えました。
- ルビ消し ON のときだけ、右端に残っていたルビ用の空きレーンを本文側へ詰めるようにしました。
- 通常のルビ付き表示では、従来どおり右側にルビ用スペースを確保します。
- 既存のルビ描画関数本体・ルビ配置ロジック本体は変更していません。

## v1.3.3.6

v1.3.3.6 は、v1.3.3.5 の実機確認で見つかったルビ消しUIとプレビュー反映の修正版です。

- 「ルビ消し」ラベルを dimLabel ではなく通常ラベルに変更し、周辺チェックボックスと比べて小さく見えないようにしました。
- プレビュー payload に `ruby_hide` が含まれていなかったため、チェック ON でもプレビュー側ではルビ消しが反映されない問題を修正しました。
- 変換・XTC / XTCH 保存経路の `ruby_hide` は維持し、既存ルビ描画 core 本体は変更していません。

## v1.3.3.5

v1.3.3.5 は、v1.3.3.4 を基準に、画像処理セクションの「ルビ消し」UI の横並びバランスを調整した版です。

- 「ルビ消し・□・？」の最小構成に変更し、チェックボックス内の「ルビを表示しない」文言を外しました。
- 「ルビ消し」一式を、白黒反転（出力）と同じ行の左側へ移動しました。
- ルビ消しの機能、設定保存、描画反映、XTC / XTCH 保存経路は変更していません。

## v1.3.3.4

v1.3.3.4 は、v1.3.3.3 を基準に、ルビ消しモードの完成候補として公開整合性を修正した版です。

- Python 3.10 / 3.11 で `build_release_zip.py` が SyntaxError にならないよう、f-string 内の quote を修正しました。
- `tests/test_release_bundle_hygiene.py` の同種 f-string を修正し、テスト collection が途中で止まらないようにしました。
- release metadata、README、release notes、publish checklist、public zip 検証対象を v1.3.3.4 に更新しました。
- `run_tests.bat` に、pytest が導入されている環境では `python -m pytest tests --co -q` を先に実行する collection ガードを追加しました。

## v1.3.3.3

v1.3.3.3 は、v1.3.3.2 のルビ消し実装を基準に、XTC / XTCH 保存経路と回帰確認を厚くした検証版です。

- `ruby_hide=True` が XTC / XTCH 書き出しパイプラインまで維持されることを回帰テストで確認しました。
- ルビ消し用の run コピーが、親文字・太字・斜体・傍点・サイドラインなど ruby 以外の情報を保持することを確認しました。
- 既存のルビ描画関数本体・ルビ配置ロジック本体は変更していません。

## v1.3.3.2

v1.3.3.2 は、v1.3.3.1 の UI / 設定保存を基準に、「ルビ消し」チェックを描画入力へ反映した版です。

- `ConversionArgs` に `ruby_hide` フラグを追加しました。
- 変換ワーカー設定から描画直前まで `ruby_hide` を渡すようにしました。
- プレビューキャッシュキーに `ruby_hide` を含め、ON/OFF 切替時に古いプレビューを再利用しないようにしました。
- TXT / Markdown / 青空文庫系では、`ruby_hide=True` の場合だけ描画直前の run コピーから `ruby` 情報を空にします。
- EPUB の `<ruby>` ノードでは、親文字を残し、`rt` だけを描画 run に渡さない分岐を追加しました。

## v1.3.3.1

v1.3.3.1 は、v1.3.2 を基準に、ルビ消しモードの UI と設定保存・読み込みを追加した第1段階です。

- 画像処理セクションの先頭に「ルビ消し」欄を追加しました。
- 「ルビを表示しない」チェックボックスを追加しました。
- 初期状態は OFF で、従来どおりルビ付きです。
- `ruby_hide` 設定値を保存・読み込みできるようにしました。
- プリセット保存・復元の通り道にも `ruby_hide` を追加しました。

## v1.3.3.0

v1.3.3.0 は、ルビ消しモード追加の計画段階として扱った番号です。配布用 public zip は作成していません。

- 画像処理セクション先頭に「ルビ消し」チェックを置く方針を決めました。
- デフォルトは従来どおりルビ付き、チェック時だけルビを非表示にする仕様を決めました。
- 既存のルビ描画関数本体には手を入れず、描画入力側で ruby 情報だけを空扱いにする方針を決めました。

## v1.3.2

v1.3.2 は、v1.3.1 を基準にした下鍵括弧補正とプレビュー初期値の小改良版です。

- 下鍵括弧の補正モードを、句読点・漢数字一と同じ `下補正強 / 下補正弱 / 標準 / 上補正弱 / 上補正強` の5モードに拡張しました。
- 下鍵括弧の `下補正` が、プレビューと実変換の描画処理で実際に反映されるようにしました。
- プレビュー枚数の初期値を 10 ページから 20 ページに変更しました。

## v1.3.1

v1.3.1 は、v1.3.0 を基準に、フォルダ一括変換まわりの表示・案内・停止動作と、上ペインのボタン説明を整理した安定版です。

- フォルダ一括変換完了後に「出力フォルダを開く」導線を追加しました。
- 失敗ファイルがある場合の完了ダイアログとログ表示を改善し、ログ末尾に `[ERROR-SUMMARY]` を追加しました。
- EPUB optional dependency 不足時の案内を改善し、`install_requirements.bat` / `requirements.txt` の利用を案内するようにしました。
- フォルダ一括変換中の進捗表示を `1/N 件目｜ファイル名` 形式に整理しました。
- 停止ボタン押下後の文言を自然化し、停止完了時の未処理件数を表示するようにしました。
- 停止時の `[STOP]` ログにも未処理件数を記録するようにしました。
- 上ペインのボタン名を「ファイルを開く...」「保存先を選ぶ...」「フォルダ一括変換...」に整理し、3つの違いを説明する `?` ヘルプを追加しました。
- v1.3.1 公開向けに README、FAQ、既知の注意点、release notes、公開チェックリスト、public zip 検証表記を更新しました。

## v1.3.0

v1.3.0 は、v1.2.2 を基準に、フォルダ一括変換を追加した安定版です。

- 「ファイル一括変換」からフォルダ一括変換ダイアログを開けるようにしました。
- サブフォルダ内の対象ファイル検索と、フォルダ構造を保持した出力に対応しました。
- 既存ファイルの扱いとして、スキップ、別名保存、上書きを選べるようにしました。
- 結果表示とログに、成功・スキップ・失敗・処理済み件数・出力先・スキップ内訳を表示するようにしました。
- EPUB optional dependency 不足時の案内を改善しました。
- 画像由来のフォルダ一括変換結果を正しい XTC / XTCH コンテナとして保存するよう修正しました。
- release hygiene と公開 zip 検証の対象リストを、フォルダ一括変換モジュール追加後の構成に合わせて整理しました。

## v1.2.2

v1.2.2 は、v1.2.1 を基準に、波ダッシュ・チルダ類の縦書き表示調整を追加した安定版です。

- 波線描画方式として `回転グリフ` / `別描画` を追加しました。
- 波線位置として `標準` / `下補正弱` / `下補正強` を追加しました。
- 対象文字 `～ 〜 〰 ~ ∼ ∽ ∿ ≀` の縦書き表示確認を行いやすくしました。
- 波線設定を GUI 変更時の即時プレビュー、ini 保存・読み込み、preview payload、conversion args に反映しました。
- 波線設定の表記ゆれ正規化と安全な fallback を追加しました。
- `WorkerConversionSettings` に波線設定キーを追加し、型定義上も正式な変換設定として扱うようにしました。
- 左ペイン上部のプリセット仕様表示は基本仕様に絞り、フォント依存のチューニング項目である波線描画・波線位置は表示対象から外しました。
- 横書き前提文書における半角コンマ・半角ピリオドなどの見え方について、既知の注意点として整理しました。

## v1.2.1

v1.2.1 は、v1.2.0 を基準にした TXT / Markdown プレビューの小修正版です。

- `tategakiXTC_gui_core_text.py` で、分割後のテキスト入力キャッシュ helper を直接参照できるようにし、TXT / Markdown 読み込み時のプレビュー生成エラーを修正しました。
- `tategakiXTC_gui_preview_controller.py` で、対象パスが選択されている場合は古い画像プレビュー状態を引きずらず、`target_path` からプレビュー生成するようにしました。
- テキスト対象選択後の preview payload を確認する回帰テストを追加しました。

## v1.2.0

v1.2.0 は、v1.1.0 公開後に積み重ねた v1.1.1 系の改修をまとめた公開向け安定版です。

- Python GUI版のみを公開対象とする方針を維持し、旧 Web 試作版関連ファイルを release 対象外に整理しました。
- GUI 配置、左ペイン「プリセット」仕様表示、右ペインのプレビュー更新導線、左ペイン下部「変換結果 / ログ」スクロール同期を安定化しました。
- 句読点、漢数字「一」、下鍵括弧の描画位置補正を整理し、プレビューと実変換の反映経路を修正しました。
- ぶら下がり句読点、下余白クリップ、余白変更時のページ維持、白黒反転プレビューなど、縦書き表示周辺の退行を補正しました。
- public zip 作成、verify、README / CHANGELOG / release notes、CI / 回帰テストの整合性を v1.2.0 に更新しました。

## v1.1.1.37

v1.1.1.37 は、v1.1.1.36 を基準にしたプリセット仕様表示・下鍵括弧補正・スクロール同期の小修正版です。

- プリセット仕様表示で、高さ測定が 0 のときに `setMaximumHeight(0)` を呼ばず、ラベルが消えたまま固定される問題を防ぎました。
- `setFixedHeight()` が成功した場合は、`setMinimumHeight()` / `setMaximumHeight()` の二重指定を行わないようにしました。
- 縦書き専用の閉じ鍵括弧 `﹂` / `﹄` を、下鍵括弧補正の対象判定に追加しました。
- 「下鍵括弧」の選択肢表記を `上補正強` / `上補正弱` に統一しました。
- 左ペイン下部の外側スクロールバー同期で、内部スクロールバーの `setValue()` が失敗した場合も再同期するようにしました。

## v1.1.1.36

v1.1.1.36 は、v1.1.1.35 を基準にしたプリセット仕様表示末尾余白の追加修正版です。

- 左ペイン「プリセット」セクションの仕様表示について、初回レイアウト前の狭い QLabel 幅で高さを多めに固定してしまうケースを抑制しました。
- プリセット仕様表示の高さ計算で、親ウィジェット幅を候補に含め、Qt のレイアウト確定後に再測定する導線を追加しました。
- プリセットセクションの下余白と行間を追加で詰めました。
- プリセット名、プリセット選択ボタン、プリセット保存・読み込み、ini 互換、内部データ構造、プリセット適用ロジックは変更していません。
- split135 の下鍵括弧補正（上補正弱 / 上補正強）と画像処理行の配置は維持しています。

## v1.1.1.34

v1.1.1.34 は、v1.1.1.33 を基準にした下鍵括弧描画位置補正の追加版です。

- 右ペイン「画像処理」セクションに、下鍵括弧の描画位置補正「下鍵括弧」を追加しました。
- 選択肢は「上補正強」「上補正弱」「標準」の3段階とし、標準では従来の描画位置を維持します。
- 閉じ鍵括弧 `」` と二重閉じ鍵括弧 `』` のみを対象に、描画時の y 方向位置だけを上へ補正できるようにしました。
- 句読点補正、漢数字一補正、通常文字、上鍵括弧、テキスト内容、出力ファイル名、内部文字列には影響しないようにしました。
- ini 保存・読み込み、preview payload、実変換 args、描画キャッシュキーに新設定を反映しました。

## v1.1.1.33

v1.1.1.33 は、v1.1.1.32 を基準にした左ペイン「プリセット」仕様表示の余白調整版です。

- 左ペイン「プリセット」セクションの仕様表示で、末尾に残っていた余分な空行ぶんの余白を削減しました。
- 表示文字列の末尾空行を取り除き、プリセット仕様ラベルの高さを本文に合わせて締めました。
- プリセット名、選択、適用、保存・読み込み、ini 互換、内部データ構造、プリセット適用ロジックは変更していません。
- プリセット仕様表示の末尾空行と高さ計算に関する回帰テストを追加・更新しました。

## v1.1.1.32

v1.1.1.32 は、v1.1.1.31 を基準にした右ペイン「白黒反転」プレビュー更新導線の小修正版です。

- 右ペイン「画像処理」セクションの「白黒反転（出力）」切り替え時に、live preview debounce 経由でプレビュー更新待ちへ入るようにしました。
- フォント変更・禁則・字形位置補正と同じ即時プレビュー導線に揃えました。
- 白黒反転の描画処理、変換結果への反映仕様、ini 保存・読み込み、内部設定キーは変更していません。
- 白黒反転トグルの即時プレビュー反映に関する回帰テストを更新しました。

## v1.1.1.31

v1.1.1.31 は、v1.1.1.30 を基準にした左ペイン「プリセット」仕様表示の小修正版です。

- 左ペイン「プリセット」セクションの仕様表示から、先頭行の「プリセット1」「プリセット2」などの見出し行を表示しないようにしました。
- プリセット選択コンボ、プリセット名、保存・読み込み、ini 互換、内部データ構造、プリセット適用ロジックは変更していません。
- 仕様本文は従来どおり維持し、不要な空行が残らないようにしました。
- プリセット仕様表示に関する回帰テストを追加・更新しました。

## v1.1.1.30

v1.1.1.30 は、v1.1.1.29 を基準にした右ペイン設定UIの配置調整版です。

- 「出力・フォント・組版」セクションにあった、ぶら下がり句読点補正と漢数字「一」補正を「画像処理」セクションへ移動しました。
- 表示ラベルのみ、「ぶら下がり句読点」を「句読点」に変更しました。
- 内部設定キー、ini 保存・読み込み、preview payload、変換処理で参照する値は変更していません。
- 補正選択肢と live preview / debounce の動作は従来どおり維持しました。
- 右ペインのセクション配置に関する回帰テストを追加・更新しました。

## v1.1.1.29

v1.1.1.29 は、v1.1.1.28 を基準にした preview / bottom panel / 型注釈の小修正版です。

- live preview の debounce 更新待ち中に、別のプレビュー生成完了処理が走っても［プレビュー更新］ボタンの `更新待ち…` / `pending` 状態を維持するようにしました。
- 左ペイン下部の外側スクロールバー同期で、内部スクロールバーの `valueChanged` 由来の同期を抑制し、最後に1回だけ範囲・値を同期するようにしました。
- 余白変更専用だった旧 `_has_active_preview_for_margin_refresh()` を削除し、live preview scheduler への委譲だけを残しました。
- 下部パネル区切り線の objectName を `topSep` から `bottomPanelSep` に変更し、上部区切り線とのスタイル共有を避けました。
- renderer 内の同一スコープ型アノテーション重複を整理しました。
- 上記の回帰テストを追加・更新しました。

## v1.1.1.28

v1.1.1.28 は、v1.1.1.27 を基準にした左ペイン下部スクロールバー調整版です。

- 左ペイン下部の変換結果 / ログエリアに、セパレーター直下から始まる外側スクロールバーを追加しました。
- 変換結果リスト / ログ本文の個別スクロールバーを非表示にし、外側スクロールバーへ同期するようにしました。
- タブ切り替え時に外側スクロールバーが現在のタブのスクロール位置へ追従するようにしました。
- GUI layout / MainWindow 回帰テストを更新しました。

## v1.1.1.27

v1.1.1.27 は、v1.1.1.26 を基準にした Windows 実機フル回帰テスト追従版です。

- release hygiene テストの release notes 必須ファイル期待値を、現在の公開版に追従するよう修正
- `WorkerConversionSettings` の TypedDict 回帰テストに `punctuation_position_mode` / `ichi_position_mode` を追加
- フル回帰で検出されたテスト期待値のずれを修正

## v1.1.1.26

v1.1.1.26 は、v1.1.1.25 を基準にした live preview 更新退行の補正版です。

- live preview の実行可否判定に、現在の対象ファイル / 画像プレビュー入力の存在確認を追加。
- キャッシュ済み preview pages が空の状態でも、対象ファイルが存在する場合は設定変更からプレビュー再生成を予約できるように変更。
- フォント変更・本文サイズ・ルビサイズ・行間・余白・禁則処理・保存形式変更後に、自動プレビュー更新が止まる退行を抑制。
- キャッシュなし状態からの live preview 再生成と対象パス判定の回帰テストを追加。
- split125 の左ペインセパレータ / スプリッター位置調整は維持。
- MainWindow の大規模構造変更なし。

## v1.1.1.25

v1.1.1.25 は、v1.1.1.24 を基準にした左ペイン上下スプリッター位置の再調整版です。

- 左ペイン上部設定エリアの末尾に `leftSettingsBottomSep` セパレータを追加。
- セパレータをファイルビューワー欄の直下へ配置し、下部の変換結果 / ログ欄との境界を明確化。
- 初期表示時は、保存済み状態がない場合に限り、ファイルビューワー直下のセパレータ付近から下部エリアが始まるよう左ペイン上下スプリッターの既定サイズを調整。
- 既存の保存済みスプリッター状態がある場合は従来どおりユーザー保存値を優先。
- 右ペインのプレビュー表示領域を削る変更なし。
- MainWindow の大規模構造変更なし。

## v1.1.1.24

v1.1.1.24 は、v1.1.1.23 を基準にした右ペインナビゲーションとログ欄の視認性改善版です。

- 右ペインの `反転` 表記を `ボタン反転` に変更。
- `前` / `次` ボタンの前後に余白と縦区切りを追加し、ボタン反転・ページ送り・表示倍率のセクションを視覚的に分離。
- 右ペイン上部の区切り線を既存バー内のプレビュー表示項目直下へ移動し、プレビュー表示領域を削らない構成に変更。
- 変換結果リストとログ欄に常時表示の右側スクロールバーを設定。
- MainWindow の大規模構造変更なし。

## v1.1.1.23

v1.1.1.23 は、v1.1.1.22 を基準にしたプレビュー更新ボタンの状態表示改善版です。

- 見た目・組版設定の live preview 更新予約中に、［プレビュー更新］ボタンを `更新待ち…` 表示へ切り替えるように変更
- プレビュー生成中は同ボタンをオレンジ系の `生成中…` 表示にし、更新処理中であることを視覚的に分かりやすくした
- ボタンの通常状態 / 更新待ち / 更新中を `previewState` 動的プロパティで管理し、ライトテーマ・ダークテーマ双方に対応
- 更新予約・生成開始・生成完了のボタン状態に関する回帰テストを追加

## v1.1.1.22

v1.1.1.22 は、v1.1.1.21 を基準にした見た目・組版設定の自動プレビュー更新版です。

- フォントサイズ、ルビサイズ、行間、フォント選択、上下左右余白、禁則処理、ぶら下がり句読点補正、漢数字「一」補正、保存形式を live preview 更新対象に追加。
- 設定変更ごとの即時フル再生成ではなく、短い遅延つきの `_schedule_live_preview_refresh()` に集約。
- 連続変更時は世代番号で古い予約を無視し、最後の設定値だけでプレビュー再生成。
- 余白変更専用だった再生成経路を共通 live preview scheduler に統合。
- ガイド overlay の runtime state は即時反映しつつ、プレビュー画像本体は debounce 後に再生成。
- プレビュー再生成は `reset_page=False` を維持し、現在ページを可能な範囲で保持。
- MainWindow の大規模構造変更なし。

## v1.1.1.21

v1.1.1.21 は、v1.1.1.20 を基準にしたフォントビューのガイド位置補正版です。

- フォントビューのガイド描画で、スケール済みプレビューサイズではなく、スケール前の元ページ寸法を基準に余白ガイド位置を計算。
- 下余白が大きい場合に、ガイド帯が実際の描画クリップ位置より内側へずれて文字と重なって見える問題を修正。
- `_apply_preview_pixmap()` で元 pixmap 寸法を記録し、`_decorate_font_view_pixmap()` へ `page_width` / `page_height` として渡すように変更。
- `_decorate_font_view_pixmap()` は元寸法が渡されない場合のみ表示後サイズへフォールバック。
- フォントビューのガイド計算が元ページ寸法を使うことを回帰テストで確認。
- 実機ビュー側のガイド計算は従来どおり維持。
- MainWindow の大規模構造変更なし。

## v1.1.1.20

v1.1.1.20 は、v1.1.1.19 を基準にした余白変更時のページ維持・最新余白再生成修正版です。

- 余白変更時のプレビュー再生成を `reset_page=False` に変更し、表示中ページを維持。
- 再生成後のページ数が減った場合は、既存の preview controller の clamp 処理で有効範囲内へ丸める。
- プレビュー生成中に余白が追加変更された場合、生成完了後に最新余白で再生成する follow-up refresh を予約。
- 古いプレビュー画像を新しいガイドで再装飾したまま残る状態を抑制。
- split118 の「ぶら下がり句読点だけを下余白クリップ後に復元する」方針は維持。
- MainWindow の大規模構造変更なし。

## v1.1.1.17

v1.1.1.17 は、v1.1.1.16 を基準にしたぶら下がり句読点の下余白クリップ調整版です。

- 本文ページ確定時の余白クリップ処理で、ぶら下がり句読点用の下方向許容量を確保
- 下余白の値を変更しても、ぶら下がり句読点が白塗りクリップで削られて圧縮表示のように見える問題を抑制
- 禁則処理が `オフ` の場合は従来どおり下余白クリップを維持
- ぶら下がり句読点の描画サイズ・位置補正ロジックは変更せず、最終クリップ開始位置のみ調整
- 回帰テストで、ぶら下がり句読点が下余白へ1文字セル分はみ出しても最終クリップで削られないことを確認
- MainWindow の大規模構造変更なし

## v1.1.1.16

v1.1.1.16 は、v1.1.1.15 を基準にした字形位置補正の5段階化版です。

- ぶら下がり句読点と漢数字「一」の位置補正を5段階へ拡張
- GUI 選択肢を `下補正強 / 下補正弱 / 標準 / 上補正弱 / 上補正強` に変更
- 現在の下補正・上補正をそれぞれ強補正として維持し、弱補正は強補正の半量として追加
- 句読点補正は引き続きぶら下がり句読点のみ対象、文中句読点は標準位置を維持
- 漢数字「一」は文中すべての「一」を5段階補正の対象として維持
- 旧 `plus` / `minus` / `adjusted` / `補正` / `プラス補正` / `マイナス補正` の強補正への後方互換読み替えを維持
- GUI ヘルプ文、正規化ロジック、回帰テスト、release docs を5段階モードに整合
- MainWindow の大規模構造変更なし

## v1.1.1.15

v1.1.1.15 は、v1.1.1.14 を基準にした GUI 文言整理版です。

- GUI ラベル「句読点位置」を「ぶら下がり句読点」に変更
- 句読点および漢数字「一」の選択肢を `下補正 / 標準 / 上補正` に変更
- 内部値 `plus` は下補正、`minus` は上補正として維持し、既存 ini との互換性を保持
- 旧 `プラス補正` / `マイナス補正` / `補正` / `adjusted` の読み替えを維持
- GUI ヘルプ文、正規化ロジック、回帰テスト、release docs を現行文言に整合
- 描画・変換ロジック本体の上下補正量は変更なし
- MainWindow の大規模構造変更なし

## v1.1.1.14

v1.1.1.14 は、v1.1.1.13 を基準にした公開前の字形位置モード拡張版です。

- 句読点位置モードを `プラス補正 / 標準 / マイナス補正` の3段階へ拡張
- 句読点のプラス補正が標準より下方向へ動くよう、ぶら下がり句読点の off_y 補正に修正
- 文中句読点は3段階モード選択時も標準位置を維持
- 漢数字「一」位置モードも `プラス補正 / 標準 / マイナス補正` の3段階へ拡張
- 漢数字「一」の補正は文中すべての「一」に適用
- 旧 `補正` / `adjusted` 設定を `プラス補正` として扱う後方互換を追加
- GUI 文言、ini 保存・復元、プレビュー payload、回帰テストを3段階モードに整合
- MainWindow の大規模構造変更なし

## v1.1.1.13

v1.1.1.13 は、v1.1.1.12 を基準にした公開前の句読点位置補正の適用範囲調整版です。

- 句読点位置補正の適用対象を「ぶら下がり句読点」に限定
- 文中句読点は `補正` 選択時も標準位置のまま描画
- ぶら下がり句読点の補正は `draw_hanging_punctuation()` 経由に集約
- 漢数字「一」の位置補正ロジックは維持
- 句読点補正の適用範囲を確認する回帰テストを追加・更新
- MainWindow の大規模構造変更なし

## v1.1.1.12

v1.1.1.12 は、v1.1.1.11 を基準にした公開前のプレビュー導線修正版です。

- GUI のプレビュー生成 payload に `punctuation_position_mode` を追加
- GUI のプレビュー生成 payload に `ichi_position_mode` を追加
- GUI 選択 → preview payload → preview renderer → preview cache key の導線を整合
- preview controller の回帰テストで、句読点位置 / 漢数字「一」位置モードが payload に入ることを確認
- 既定値は `標準` のまま維持

## v1.1.1.08

v1.1.1.08 は、v1.1.1.07 を基準にした公開前ドキュメント整合の保守更新です。

- README の初回セットアップ補足を本体手順へ統合し、重複説明を整理
- GitHub Release の Previous tag / 添付ファイル名を公開メタ情報と一致
- release docs hygiene test で README の公開情報と `tategakiXTC_release_metadata.py` の整合を確認
- `run_gui.bat` / `install_requirements.bat` / `run_tests.bat` の公開導線検査を維持
- 描画・変換ロジック本体には変更なし
- MainWindow の大規模構造変更なし

## v1.1.1.07

v1.1.1.07 は、v1.1.1.06 を基準にした回帰テスト強化の保守更新です。

- ini 保存 payload の `settings_schema_version` / `last_app_version` を実値で確認する回帰テストを追加
- GUI ログ整理処理を Qt 非依存 helper に切り出し、active log と unrelated file を保持する回帰テストを追加
- public zip 既定名、`install_requirements.bat`、release docs の整合検査を補強
- 描画・変換ロジック本体には変更なし
- MainWindow の大規模構造変更なし

## v1.1.1.06

v1.1.1.06 は、v1.1.1.05 を基準にした public zip 作成フローの保守更新です。

- `build_release_zip.py` の既定出力ファイル名を公開版番号つきに変更
- 既定の public zip 出力先を `dist/tategaki-xtc-gui-studio_v1.1.1.06-release.zip` に統一
- 既存の `--output` 指定は従来どおり利用可能
- README、CHANGELOG、release notes、release hygiene tests を v1.1.1.06 に整合
- 描画・変換ロジック本体には変更なし
- MainWindow の大規模構造変更なし

## v1.1.1.05

v1.1.1.05 は、v1.1.1.04 を基準にしたフル回帰テスト互換性の保守更新です。

- `show_help_dialog()` の公開向けヘルプ文言に合わせて、`test_help_dialog_describes_actual_size_and_guides_as_right_preview_toolbar` の期待値を更新
- v1.1.1.04 で追加した公開品質・設定安全性改善はそのまま維持

## v1.1.1.04

v1.1.1.04 は、v1.1.1.03 を基準にした公開品質・設定安全性の保守更新です。

- 公開版番号、release notes、public zip 検査で参照する公開メタ情報を整理
- ini 保存時に `settings_schema_version` / `last_app_version` を記録するように変更
- 設定初期値の参照元を整理し、既定値の散在を軽減
- ユーザー向けヘルプ文から内部作業番号由来の表現を除去
- GUI ログの古いセッションファイルを自動整理する保持ポリシーを追加
- 初回セットアップ説明を整理し、`install_requirements.bat` を追加

このファイルでは、縦書きXTC GUI Studio の主な変更履歴をまとめます。

## v1.1.1.03

v1.1.1.03 は、v1.1.0 を基準にした v1.1.1 系の安定化・保守更新です。

- 起動時プレビュー復元の fallback を整理
- EPUB プレビュー生成時の helper 同期漏れを修正
- APP_VERSION / README / release hygiene test のバージョン表記を v1.1.1.03 に更新
- 結果一覧選択 fallback の `matched_index` なし入力を事前に clear-selection として扱うよう修正
- `_normalize_summary_line_item` の `lines` 二重アノテーションを解消

## v1.1.0

v1.1.0 は、GitHub で公開済みの **v1.0.2 の次の正式版 v1.1.0**です。

このリリースでは、公開対象を **Python GUI版のみ**に整理し、GUI、描画・変換処理、release payload、ドキュメントを更新しました。

### Added

- `CHANGELOG.md` を追加
- `docs/release_notes/RELEASE_NOTES_v1_1_0.md` を追加
- 同梱フォント用に `LICENSE_OFL.txt` を追加
- `Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントについて、README に説明を追加
- type hygiene 用の回帰テストを追加
- release docs / release hygiene 用の回帰テストを追加
- public zip に旧 Web 試作版関連ファイルが混入しないための検査を追加・整理

### Changed

- `tategakiXTC_gui_core_renderer.py` / `tategakiXTC_gui_core_epub.py` を追加し、core から段階的に分割
- README を v1.1.0 公開向けに整理
- v1.1.0 を v1.0.2 の次の正式版として明記
- GitHub Release tag / title を `v1.1.0` として扱う方針を明記
- 公開対象を Python GUI版のみとして整理
- 旧ローカル Web 試作版関連の導線を README / CI / release payload から除外
- 初回セットアップ手順を Python 確認、venv 作成、requirements 導入、起動の順に整理
- `run_gui.bat` を基本起動手順として明確化
- `Font/` と `LICENSE_OFL.txt` の関係を README に明記
- public zip 作成時の検査を Python GUI版前提へ整理
- `.github/workflows/python-tests.yml` の依存導入を Python GUI版前提へ整理
- `run_tests.bat` の compile 対象を Python GUI版前提へ整理
- `tategakiXTC_gui_studio_logic.py` を含む GUI ロジック分離構成を release 検査対象として明記

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
