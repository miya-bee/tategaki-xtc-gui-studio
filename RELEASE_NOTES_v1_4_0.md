# TategakiXTC GUI Studio v1.4.0

v1.4.0 は、前回公開版 v1.3.6 以降の開発版で行った UI 整理、変換安定化、不具合修正をまとめた公開版です。v1.3.7 は公開版として配布せず、v1.3.8.x は v1.4.0 に向けた開発・安定化ラインとして扱います。

## 主な変更

### 3ペインUI

- 画面構成を `Left Preset/Spec → Center Settings/Results → Right Preview` に整理しました。
- 左ペインはプリセット選択と仕様表示、中央ペインは出力・組版・位置補正・プレビュー更新、右ペインはプレビュー表示を担当します。
- `XTC/XTCHを開く` を上部ボタン列へ移動し、ファイルビューワー導線を見つけやすくしました。
- 中央設定ペインはスクロール可能にし、コンボボックスやスピンボックス上のホイール誤操作を抑制しました。
- 起動直後に入力欄へ文字カーソルが残りにくいよう、初期フォーカスを調整しました。

### 出力・保存先まわり

- 新規設定時の既定出力形式を XTCH にしました。既存 ini の設定は尊重します。
- `保存先を開く` がアプリフォルダーや作業フォルダーを誤って開くケースを抑制しました。
- 同名出力、明示保存先、保存先リセット、ファイルビューワーモード復帰まわりの互換性を維持しました。
- 旧 `device` view-mode 値は互換レイヤーとして受け入れますが、旧 device-view UI を復活させず、現行の右ペイン表示へ丸めます。
- 画像入力 `.png` / `.jpg` / `.jpeg` / `.webp` が変換対象として検出されても保存先生成で `None` になりスキップされる問題を修正しました。

### TXT / Markdown / 禁則処理

- TXT 行頭の全角スペースが既定1字下げと重なって2字下げになる問題を修正しました。
- TXT 行頭が `「` / `『` / `【` などの開き括弧で始まる場合、明示字下げがない限り不要な既定1字下げを入れないようにしました。
- 標準禁則で、`終わりです」` が過剰に `です」` ごと次列へ送られるケースを緩和しつつ、`か？」` のような約物付きの短い文末は保護するよう調整しました。
- 2-token 約物ペアの hint cache を修正し、`、。` / `。、` / `、、` / `。。` が列末で不要に改列されないようにしました。
- 大きな折り返し字下げで実スロットが0になる場合、禁則判定が advance を繰り返してハングする問題を修正しました。
- 過大な字下げ注記で本文がページ外へ押し出され、プレビューが白紙に見える問題を防ぐため、描画時に安全範囲を超える字下げは無効化し、本文が列頭付近から始まるようにしました。

### 起動・設定復元

- `last_shutdown_clean=false` / `settings_schema_version` / `last_app_version` だけが残った metadata-only ini から起動する場合に、異常終了復元経路へ入って一瞬で終了することがある問題を修正しました。
- 実際の保存済み設定がある ini では従来どおり復元を試み、復元対象がない ini だけ通常初回起動として扱います。

### プレビュー・キャンセル処理

- ライブプレビューの更新判定が実際の payload キー名とずれていた問題を修正しました。
- 画像変換中のキャンセルが広い例外処理に吸収され、一般失敗扱いになる問題を修正しました。
- ページ番号フォントサイズに上限超過値が渡された場合は、変換全体を失敗させず上限値へクランプするようにしました。

### フォント・非Windows環境

- macOS / Linux の等幅フォント候補を増やし、Markdown コードブロックのフォント検出を改善しました。
- macOS のヒラギノ / Osaka 系フォント候補を追加しました。
- Unicode 正規化差や `Font` / `font` / `fonts` / `Fonts` のフォルダー名差を考慮するようにしました。

### 読み戻し・文字コード判定

- XTC/XTCH 読み戻しで、ページテーブル直後にパディングがある非標準コンテナでも標準16バイト entry を優先するようにしました。
- BOMなしUTF-16の日本語TXT/Markdownについて、NUL比率だけでは検出できない本文を慎重に推定する fallback を追加しました。

## 変更していない範囲

- XTC / XTCH の基本書き出し形式は変更していません。
- EPUB解析、ルビ描画、既存プリセット、既存 ini の主要キーは互換性を維持しています。
- 旧ローカル Web 試作版は、この Python GUI 版公開パッケージには含めません。

## ドキュメント整理

- v1.3.8.x の細かな `RELEASE_NOTES_v1_3_8_*.md` / `PUBLISH_CHECKLIST_v1_3_8_*.md` は公開版には残していません。
- v1.3.6 から v1.4.0 までの差分は、この `RELEASE_NOTES_v1_4_0.md` と `CHANGELOG.md` の v1.4.0 項目へ統合しています。
- Windows の `.bat` 起動ファイルは CRLF 改行に正規化済みです。配布zip作成時にも LF のみの `.bat` が混入しないよう検査します。
- `run_gui.bat` に加え、`install_requirements.bat` / `run_tests.bat` もダブルクリック利用時に無言終了しないよう、フォルダ切替失敗や各 `exit /b` の直前に `pause` を置く構成へ揃えました。

## 検証

- Python compile / focused regression tests
- release docs / bundle hygiene tests
- source-only / release zip build and verify
- zip integrity / forbidden cache-log-ini-pyc artifact check

## 成果物

- `tategaki-xtc-gui-studio_v1.4.0-source-only.zip`
- `tategaki-xtc-gui-studio_v1.4.0-source-only.zip.sha256.txt`
- `tategaki-xtc-gui-studio_v1.4.0-release.zip`
- `tategaki-xtc-gui-studio_v1.4.0-release.zip.sha256.txt`

詳細な履歴は `CHANGELOG.md` を参照してください。


### Windows launcher reliability

- run_gui.bat hardening: added pushd/cd fallback, app-file existence check, pause-on-failure messaging, and CRLF-only packaging guard for Windows batch launchers.
