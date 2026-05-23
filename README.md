# 縦書きXTC GUI Studio

**縦書きXTC GUI Studio** は、EPUB やテキストを、xteink X4 / X3 などで扱いやすい縦書き XTC / XTCH 形式へ変換するための Python GUI アプリです。

このリポジトリの公開版は **Python GUI版のみ**です。  
旧ローカル Web 試作版関連ファイルは、v1.1.0 以降の公開対象から除外しています。

> **License note:** This project is **Source Available**, not Open Source.  
> You may view and study the source for personal use only. Redistribution, commercial use, and modified distribution are not permitted. See `LICENSE.txt` for details.

## バージョン

現在の公開版は **v1.3.6** です。

v1.3.6 は、v1.3.5 以降の追加開発をまとめた公開版です。ページ番号表示、EPUB 堅牢化、プレビュー/ファイルビューワーモード改善、保存先処理改善、位置補正機能追加、XTC / XTCH 書き出し信頼性強化を含みます。内部作業版としては v1.3.6.45 を基準にしています。

- 前回公開版: `v1.3.5`
- 今回公開版: `v1.3.6`
- GitHub Release tag: `v1.3.6`
- GitHub Release title: `v1.3.6`

## v1.3.6 の主な更新

- TXT / Markdown / EPUB などの主経路 XTC / XTCH 書き出しで、`os.replace()` 前の temp file fsync と自己検証を行うようにしました。
- page-entry pipeline の自己検証を、ページごとに width / height が異なる既存ケースにも対応させました。
- フォルダ一括変換のキャンセル判定を文字列推測ではなく `ConversionCancelled` の型判定へ変更しました。
- `ConversionWorker._convert()` の `None` 戻り値防御、folder batch log callback 防御、連番保存先候補探索の上限を追加しました。
- v1.3.6.44 の保存先 helper 防御、v1.3.6.42 の保存先 helper 化、v1.3.6.41 の位置補正整理と sample_texts 配布ガードは維持しています。
- v1.3.6.x 系のページ番号表示、EPUB 堅牢化、プレビュー進捗表示、半角数字/記号位置補正、半角英字位置補正、ファイルビューワーモード改善を維持しています。

詳細は `RELEASE_NOTES_v1_3_6.md` と `CHANGELOG.md` を参照してください。

### 同梱サンプルテキスト

`sample_texts/` に、設定確認用のテキストを同梱しています。

- `tategaki_position_kinsoku_test_text_v3.txt` — TXT / 青空文庫風ルビ / 禁則処理 / 位置補正確認用
- `tategaki_position_kinsoku_bold_markdown_v1.md` — Markdown の `**太字**` を使った太字確認用
- `tategaki_tatechuyoko_punctuation_test_text_v1.txt` — 以前の縦中横・記号ペア確認用
- `tategaki_halfwidth_alpha_position_test_text_v1.txt` — 半角英字位置補正確認用
- `tategaki_halfwidth_fullwidth_alpha_compare_test_text_v1.txt` — 半角英字と全角英字の比較確認用

TXT入力では、青空文庫風の `［＃ここから太字］...［＃ここで太字終わり］` は現在太字として解釈しません。太字確認は Markdown サンプルを使用してください。

## 過去の主な公開版

### v1.3.4

ルビ消しモード、半角数字補正、半角英字補正、半角数字の縦中横上限、右ペイン高倍率プレビュー、ドラッグ＆ドロップ、変換完了カード、フォルダ一括変換の中止処理などをまとめた公開版です。

### v1.3.3

ルビ消しモード追加の基準版として扱った公開版です。v1.3.4 では、その後の v1.3.3.x 内部改良をまとめて公開しました。

### v1.3.0

v1.2.2 を基準に、フォルダ一括変換を中心として、複数ファイルをまとめて XTC / XTCH へ変換する導線を追加した安定版です。

### v1.2.2

波ダッシュ・チルダ類の縦書き表示調整を追加した安定版です。

### v1.2.1

TXT / Markdown などのテキスト入力プレビューを修正した小修正版です。

### v1.2.0

v1.1.1 系で行った GUI 整理、プレビュー更新、描画補正、release hygiene の改修をまとめた安定版です。

### v1.1.0

GitHub で公開済みの v1.0.2 の次の公開版です。

## 関連ドキュメント

- `WINDOWS_SETUP.md` — Windowsでの導入・起動手順
- `FAQ.md` — よくある質問
- `KNOWN_LIMITATIONS.md` — 既知の注意点・仕様
- `RELEASE_NOTES_v1_3_6.md` — v1.3.5 から v1.3.6 までの差分まとめ
- `RELEASE_NOTES_v1_3_5.md` — v1.3.4 から v1.3.5 までの差分まとめ
- `RELEASE_NOTES_v1_3_4.md` — v1.3.3 から v1.3.4 までの差分まとめ
- `RELEASE_NOTES_v1_3_0.md` — v1.3.0 の更新内容
- `RELEASE_NOTES_v1_2_2.md` — v1.2.2 の更新内容
- `RELEASE_NOTES_v1_2_1.md` — v1.2.1 の更新内容
- `RELEASE_NOTES_v1_2_0.md` — v1.2.0 の更新内容
- `RELEASE_NOTES_v1_1_0.md` — v1.1.0 の更新内容
- `CHANGELOG.md` — 公開版単位の更新履歴

## 得意な文書

このアプリは、青空文庫系の小説本文、古い小説、随筆、読み物系テキスト、プレーンテキストなど、本文中心の文書を主な対象にしています。

## 苦手な文書・注意が必要な文書

Markdown記法が多い文書、README のような横書き前提の技術文書、URL、ファイル名、バージョン番号、英数字や半角記号が多い文書、表、コードブロック、箇条書き中心の文書は、縦書き化したときに見た目が不自然になる場合があります。

半角コンマ `,` や半角ピリオド `.` は、フォントによって縦書き上で左下寄りに見えることがあります。青空文庫系の小説本文では大きな問題になりにくいため、v1.3.3.29 でも仕様として扱っています。

## 必要環境

推奨環境:

Python は **3.10 / 3.11 / 3.12 系**を想定しています。型互換のため `typing_extensions` も依存関係に含めています。

- Windows 10 / 11
- Python 3.10 系
- pip
- 仮想環境 venv

依存パッケージは `requirements.txt` からインストールします。
依存関係は PySide6 / Pillow / numpy などです。numpy は XTC / XTCH pack の高速化に使います。

## 初回セットアップ

Windows のコマンドプロンプトで、展開先フォルダーに移動してから実行してください。
Python は **3.10 / 3.11 / 3.12 系**を想定しています。迷った場合は 3.12 を優先してください。`python --version` で 3.10〜3.12 系であることを確認後、環境に合わせて `py -3.12` / `py -3.11` / `py -3.10` のいずれかを使ってください。

### 1. Python を確認する

    python --version

    py -3.12 --version

うまく動かない場合は、環境に合わせて `py -3.11 --version` / `py -3.10 --version` / `python --version` も確認してください。

### 2. 依存ライブラリを入れる

通常は付属のバッチファイルを使えます。

    install_requirements.bat

手動で入れる場合は以下です。

    py -3.12 -m pip install ^
      --upgrade pip

    py -3.12 -m pip install ^
      -r requirements.txt

    py -3.12 -m pip install -r requirements.txt

    python -m pip install -r requirements.txt

仮想環境を使う場合は以下です。

    py -3.12 -m venv .venv

    .venv\Scripts\activate

    .venv\Scripts\python.exe ^
      -m pip install ^
      --upgrade pip

    .venv\Scripts\python.exe ^
      -m pip install ^
      -r requirements.txt

### 3. 起動する

    run_gui.bat

## 起動方法

通常は、付属のバッチファイルから起動できます。`run_gui.bat` / `install_requirements.bat` / `run_tests.bat` は同梱スクリプトのあるフォルダへ自動移動してから処理します。

    run_gui.bat

または、仮想環境を有効にしたうえで以下を実行します。

    .venv\Scripts\python.exe -B ^
      tategakiXTC_gui_studio.py

## 同梱フォントについて

v1.1.0 では、縦書き表示とテスト再現性を高めるため、`Font/` フォルダーに Noto Sans JP / Noto Serif JP 系フォントを同梱しています。

同梱フォントは **SIL Open Font License 1.1** に基づいて配布されています。  
詳細は `LICENSE_OFL.txt` を参照してください。

アプリ本体の利用条件と、同梱フォントのライセンスは別です。

- アプリ本体: このリポジトリのライセンス / 利用条件に従います
- 同梱フォント: `LICENSE_OFL.txt` に記載の SIL Open Font License 1.1 に従います

フォントを削除した環境でも、利用可能な system font へ自動フォールバックします。  
ただし、golden 画像系テストや描画差分確認では、基準フォントの有無により結果が変わる場合があります。

## Font フォルダーの扱い

`Font/` は同梱フォント用フォルダーです。

v1.1.0 では、以下のような用途で使用します。

- GUI プレビューの表示安定化
- 縦書き描画の再現性向上
- golden 画像系テストの差分確認

別のフォントを使いたい場合は、`Font/` または `fonts/` に `.ttf` / `.ttc` / `.otf` / `.otc` ファイルを配置できます。

フォントを追加・差し替えして再配布する場合は、必ず対象フォントのライセンスを確認してください。  
フォントを release zip に含める場合は、対応するライセンス文書も含める必要があります。

## 補正設定について

縦書き表示では、フォントによって記号の位置や形が大きく変わることがあります。v1.3.3.29 では、句読点、漢数字一、半角数字/記号、半角英字、下鍵括弧、波線描画、波線位置をGUIから調整できます。下鍵括弧も、句読点などと同じ5モードで上下補正できます。迷った場合は、まず標準設定のまま使い、気になる記号だけ補正してください。

## 出力ファイル名の衝突設定

同名出力の扱いは、右上の歯車メニュー内「その他オプション > 同名出力」から変更できます。


## Font フォルダーの配置

release zip にフォントを同梱する場合は、`Font/NotoSansJP-Regular.ttf` などのフォント本体と `LICENSE_OFL.txt` を一緒に含めます。

source-only 配布物や source-only リポジトリ構成では `Font/` を含めない構成も可能です。その場合、実行時は利用可能な system font へ自動フォールバックし、基準フォントが必要な golden 画像系テストは skip されます。

ライセンス文書とフォント本体の整合が取れない場合、`build_release_zip.py` は release zip 作成を停止します。フォントを同梱しない検証を行う場合は、`build_release_zip.py` 実行前に `Font/` / `fonts/` を置かないか、一時的に退避してください。

## テスト

テストを実行する場合は、release zip を展開したフォルダーをカレントディレクトリにして実行することを推奨します。
一部の統合ゲートテストはプロジェクトルート上のファイル構成を検証します。v1.3.3.29 でも主要な静的統合テストはテストファイル位置からプロジェクトルートを解決するため、別ディレクトリから個別実行しても参照先がずれにくくなっています。

代表的なテストは以下です。

    .venv\Scripts\python.exe -B ^
      -m py_compile ^
      build_release_zip.py ^
      tategakiXTC_gui_core.py ^
      tategakiXTC_gui_studio.py ^
      tategakiXTC_worker_logic.py

    .venv\Scripts\python.exe -B ^
      -m unittest ^
      tests.test_type_annotations_regression ^
      tests.test_release_docs_regression ^
      tests.test_release_hygiene_regression ^
      -v

    .venv\Scripts\python.exe -B ^
      -m unittest ^
      tests.test_release_bundle_hygiene ^
      -v

    .venv\Scripts\python.exe -B ^
      -m unittest ^
      tests.test_conversion_worker_logic ^
      -v

pytest を導入している環境では、collection だけを先に確認すると SyntaxError の早期検出に便利です。

    .venv\Scripts\python.exe -B ^
      -m pytest ^
      tests ^
      --co ^
      -q

## release zip の作成

release zip は以下で作成できます。

    .venv\Scripts\python.exe -B ^
      build_release_zip.py

作成済み release zip の検証は以下です。

    .venv\Scripts\python.exe -B ^
      build_release_zip.py ^
      --verify ^
      dist\tategaki-xtc-gui-studio_v1.3.6-release.zip

release zip の作成は、環境に応じて以下でも実行できます。

    py -3.12 build_release_zip.py

    python build_release_zip.py

検証は任意の zip パスを指定できます。

    python build_release_zip.py --verify <zipパス>

    python build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.3.6-release.zip

v1.3.6 の release zip は Python GUI版の source 構成に加えて `Font/` を同梱できます。Font フォルダが同梱されている release zip では、別コピー手順は不要です。source-only 配布に切り替える場合は、対応するフォント本体と `LICENSE_OFL.txt` の扱いを合わせてください。

## GitHub Release での公開方針

v1.3.6 は、GitHub 上では以下の扱いで公開します。

- Release tag: `v1.3.6`
- Release title: `v1.3.6`
- Previous tag: `v1.3.5`
- 添付ファイル: `tategaki-xtc-gui-studio_v1.3.6-release.zip`

Release 本文には `RELEASE_NOTES_v1_3_6.md` の内容を使用します。

開発用の `.venv/` や `node_modules/` は release 対象外です。

## 公開対象について

v1.3.6 の公開対象は **Python GUI版のみ**です。

以下の旧ローカル Web 試作版関連ファイルは、公開用 payload / release 検査の対象外です。

- `README_localweb_quickstart.txt`
- `build_localweb_windows_dist.bat`
- `install_local_web_requirements.bat`
- `localweb_launcher.py`
- `pyinstaller_localweb.spec`
- `requirements-web.txt`
- `run_local_web.bat`
- `tategakiXTC_localweb.py`
- `tategakiXTC_localweb_service.py`
- `templates/localweb_index.html`
- `tests/test_localweb_service.py`
- `tests/test_localweb_smoke.py`
- `tests/test_localweb_template_regression.py`
- `tests/test_xtc_parser_offsets_regression.py`

## 画面構成メモ

現在の左ペイン構成は `Preset → Font → Image → Display` を基準にしています。
GUI smoke をヘッドレス CI / WSL で動かす場合は `QT_QPA_PLATFORM=offscreen` を使います。

## テストと coverage の運用

coverage の fail-under は **60%** を基準にしています。CI では `coverage-report.txt` を成果物として確認できるようにしています。

## release zip 検証メモ

検証コマンドは `build_release_zip.py --verify <zipパス>` です。
この検査では、zip の読み取り破損、symlink 等の特殊ファイル属性、ローカル生成物混入、必須 release ファイルリストの同期漏れ、作業用 payload に Web 試作ファイル候補が混入していないことを確認します。
旧 Web 試作ファイルは release 対象外です。フォントを同梱する場合は `LICENSE_OFL.txt` も含めます。

## ライセンス

This project is **Source Available**, not Open Source.

You may view and study the source code for personal use only. Redistribution, commercial use, and distribution of modified versions are not permitted. See `LICENSE.txt` for details.

GitHub のライセンス表示では、OSI 認定ライセンスではないため **Other** として扱ってください。

`Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントは、アプリ本体とは別に **SIL Open Font License 1.1** に基づきます。  
詳細は `LICENSE_OFL.txt` を参照してください。

