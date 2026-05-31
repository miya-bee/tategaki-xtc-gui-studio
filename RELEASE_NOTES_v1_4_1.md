# TategakiXTC GUI Studio v1.4.1

v1.4.1 は、v1.4.0 公開後の安定化・仕上げをまとめた公開版です。内部作業版 v1.4.1.x / v1.4.2.x で行った進捗バー、下部オーバーレイ保護、英語UI対応、テスト品質ゲート整備を、公開版 v1.4.1 として統合しています。

## 主な変更

### 進捗バーと下部表示

- ページ下部に読書進捗を示す progress bar を表示できるようにしました。
- ページ番号と progress bar の下部オーバーレイが重なる場合の余白管理を整理しました。
- 旧ページ番号 margin 設定からの復元を維持しつつ、下部オーバーレイ用の共通 margin 管理へ移行しました。
- フォントや設定の差で下部表示が過剰に崩れないよう、fallback と cleanup を追加しました。

### English UI

- UI language support を追加しました。
- 初回起動時は OS の言語設定に応じて、日本語環境では日本語UI、それ以外の環境では English UI で起動します。
- 表示言語を変更した場合は、その設定が保存され、次回以降は保存済みの言語で起動します。
- English UI では、主要ラベル、ツールチップ、ダイアログ、ヘルプ、ログ、変換結果、フォルダ一括変換メッセージを英語表示します。
- English UI のウィンドウタイトルを `TategakiXTC GUI Studio <version>` にしました。日本語UIでは従来どおり `縦書きXTC Studio <version>` を維持します。

### English UI quality gate

- English UI の実ウィジェットを offscreen で走査するテストを追加しました。
- ラベル、ボタン、ツールチップ、コンボボックス、タブ、ウィンドウタイトルに未翻訳の日本語が残っていないかを検査します。
- 実 PySide6 走査はサブプロセスで実行し、通常の stub Qt 系テストと衝突しないようにしました。
- PySide6 / Pillow がない軽量環境では clean skip します。
- 右ペイン表示モード切替など、起動後にツールチップを上書きする経路も検査対象にしました。

### Python 3.10 / 3.11 compatibility and tests

- フォルダ一括変換 launcher の Python 3.10 / 3.11 互換性を修正しました。
- i18n 対応に合わせ、ソース文字列固定テスト、sweep 系テスト、TypedDict 期待値を現行実装へ同期しました。
- v1.4.0 からの描画・変換・EPUB・XTC/XTCH 出力ロジックは維持しています。

## 変更していない範囲

- XTC / XTCH の基本書き出し形式は変更していません。
- EPUB解析、ルビ描画、禁則処理、既存プリセット、既存 ini の主要キーは互換性を維持しています。
- v1.4.0 の3ペインUI、保存先処理、ファイルビューワー導線は維持しています。
- 旧ローカル Web 試作版は、この Python GUI 版公開パッケージには含めません。

## English summary

v1.4.1 is the public stable release that consolidates the post-v1.4.0 stabilization work.

- Added optional progress-bar support and bottom-overlay layout guards.
- Added Japanese / English UI language support.
- On first launch, Japanese OS locales start in Japanese UI; other locales start in English UI.
- Saved language settings take priority on later launches.
- English UI uses the localized window title `TategakiXTC GUI Studio <version>`.
- Added an offscreen real-widget English UI scan test to catch untranslated Japanese UI strings mechanically when PySide6 is available.

## ドキュメント整理

- 内部作業版 v1.4.1.x / v1.4.2.x の細かな release notes / publish checklist は公開版には残していません。
- v1.4.0 から v1.4.1 までの差分は、この `RELEASE_NOTES_v1_4_1.md` と `CHANGELOG.md` の v1.4.1 項目へ統合しています。

## 検証

- Python compile / focused regression tests
- release docs / bundle hygiene tests
- English UI offscreen widget scan test on real PySide6 environments
- source-only / release zip build and verify
- zip integrity / forbidden cache-log-ini-pyc artifact check

## 成果物

- `tategaki-xtc-gui-studio_v1.4.1-source-only.zip`
- `tategaki-xtc-gui-studio_v1.4.1-source-only.sha256.txt`
- `tategaki-xtc-gui-studio_v1.4.1-release.zip`
- `tategaki-xtc-gui-studio_v1.4.1-release.zip.sha256.txt`

詳細な履歴は `CHANGELOG.md` を参照してください。
