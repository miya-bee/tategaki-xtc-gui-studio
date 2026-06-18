# TategakiXTC GUI Studio v1.4.2

v1.4.2 は、v1.4.1 公開後の保守・安定化をまとめた公開版です。内部作業版 v1.4.1.6〜v1.4.1.17 で行った progress bar 表示方向、ギアメニュー英語化、禁則処理、起動時ログ処理、フォルダ一括変換停止表示、release/source-only zip hygiene の改善を、公開版 v1.4.2 として統合しています。

## 主な変更

### Progress bar

- 縦書き書籍のページ進行に合わせ、progress bar の既読部分が右端から左へ伸びる表示に変更しました。
- 既存のページ番号、下部オーバーレイ余白管理、progress bar 位置設定は維持しています。

### English UI / menu i18n

- ギアメニューの「外観」見出しが English UI で日本語のまま残る問題を修正しました。
- English UI の offscreen 実ウィジェット走査テストを、オンデマンド生成されるポップアップメニューにも広げました。

### 禁則処理

- 閉じ括弧 `」` / `』` / `）` などが列頭に出る問題について、閉じ括弧をぶら下げ対象にせず、既存の protected group による「前の本文字ごと追い出し」へ整理しました。
- `」』` / `）」` / `。」』` のように閉じ括弧が連続する場合でも、2個目以降が列頭に残らないよう、閉じ括弧群をまとめて扱う既存方針を維持しました。
- v1.4.1.9 で試した広い先読みガードは、列末に大きな空白を作るため採用せず、撤回済みです。
- 句読点 `、` / `。` の通常のぶら下げ処理は維持しています。

### 起動時ログ処理

- アプリ直下 `logs/` が存在しても書き込み不可の場合に、GUI が起動時に `PermissionError` で落ちる問題を修正しました。
- ログファイルを安全に作成できない場合は、一時フォルダへの fallback または stderr のみで継続し、GUI 起動を止めないようにしました。

### フォルダ一括変換

- フォルダ一括変換の停止時に、「未処理件数」が1件多く表示される場合がある問題を修正しました。
- キャンセル中のファイルを attempted count に含め、完了カード、STOPログ、表示上の未処理件数が実態に合うようにしました。

### Release / source-only zip hygiene

- `logs/`、`*.log`、`__pycache__/`、`*.pyc`、`tategakiXTC_gui_studio.ini` などのローカル状態・生成物が source-only / release zip に混入しないよう再確認しました。
- `build_release_zip.py --source-only` と `build_release_zip.py --verify` を通る GitHub 公開向け source-only zip を基準にしています。

## 変更していない範囲

- XTC / XTCH の基本書き出し形式は変更していません。
- EPUB解析、ルビ描画、基本的なページ生成、3ペインUI構造は維持しています。
- Windows portable/exe 版は GitHub Release には含めず、従来どおり note 購入者向け配布として扱います。
- 旧ローカル Web 試作版は、この Python GUI 版公開パッケージには含めません。

## English summary

v1.4.2 is a maintenance release after v1.4.1.

- Reversed the progress-bar fill direction so the read portion grows from right to left for vertical Japanese books.
- Fixed an untranslated `Appearance` section in the display/settings gear menu.
- Extended the English UI scan guard to popup menu actions and section headers.
- Stabilized kinsoku handling for closing-bracket runs such as `」』` and `）」` by using the existing push-out/protected-group behavior instead of hanging closing brackets.
- Made startup logging robust when the app-local `logs/` folder is not writable.
- Fixed a folder-batch stop summary case where the pending count could be one item too high.
- Rebuilt clean source-only/release archives without logs, ini files, pycache, or local test artifacts.

## 検証

- Python compile / focused regression tests
- renderer / kinsoku / golden image regression tests
- release docs / bundle hygiene tests
- English UI offscreen widget/menu scan guard
- source-only zip build and verify
- zip integrity / forbidden cache-log-ini-pyc artifact check

## 成果物

- `tategaki-xtc-gui-studio_v1.4.2-source-only.zip`
- `tategaki-xtc-gui-studio_v1.4.2-source-only.zip.sha256.txt`
- `tategaki-xtc-gui-studio_v1.4.2-release.zip`
- `tategaki-xtc-gui-studio_v1.4.2-release.zip.sha256.txt`

詳細な履歴は `CHANGELOG.md` を参照してください。
