# 縦書きXTC GUI Studio

**縦書きXTC GUI Studio** は、EPUB やテキストを、xteink X4 / X3 などで扱いやすい縦書き XTC / XTCH 形式へ変換するための Python GUI アプリです。

このリポジトリの公開版は **Python GUI版のみ**です。  
旧ローカル Web 試作版関連ファイルは、v1.1.0 以降の公開対象から除外しています。

## バージョン

現在の公開版は **v1.2.1** です。

v1.2.1 は、v1.2.0 を基準に TXT / Markdown などのテキスト入力プレビューを修正した小修正版です。
v1.2.0 は、v1.1.0 公開後に積み重ねた v1.1.1 系の改修をまとめた **安定版**として扱います。
v1.1.0 は、GitHub で公開済みの **v1.0.2 の次の公開版**です。

- 前回公開版: `v1.2.0`
- 今回公開版: `v1.2.1`
- GitHub Release tag: `v1.2.1`
- GitHub Release title: `v1.2.1`

## v1.2.1 の主な更新

- TXT / Markdown などのテキストファイルを読み込んだとき、プレビュー生成でテキスト入力キャッシュ helper を参照できずエラーになる問題を修正しました。
- 対象パスが選択されているプレビューでは、古い画像プレビュー用 `file_b64` を引きずらず、`target_path` から安全にプレビューするようにしました。

## v1.2.0 の主な更新

- v1.1.1 系で行った GUI 整理、プレビュー更新、描画補正、release hygiene の改修を、公開向け安定版としてまとめました。
- 句読点・漢数字「一」・下鍵括弧の描画位置補正を整理し、プレビューと実変換で設定が反映されるようにしました。
- ぶら下がり句読点、下余白クリップ、ページ移動維持、白黒反転プレビューなど、縦書きプレビュー周辺の退行を補正しました。
- 左ペイン「プリセット」仕様表示の余白・高さ計算を調整し、`setMaximumHeight(0)` による非表示化を防止しました。
- 左ペイン下部「変換結果 / ログ」外側スクロールバーの同期を安定化しました。
- 公開対象を Python GUI版に整理し、release zip 作成・検証・CI / 回帰テスト関連の整合性を更新しました。

## v1.0.2 から v1.1.0 への主な更新

v1.1.0 では、GUI の整理、プレビュー周辺、描画・変換処理、release payload の整理を中心に更新しました。

主な変更点は以下です。

- Python GUI版のみを公開対象として整理
- 旧ローカル Web 試作版関連ファイルを release 対象から除外
- 左ペイン / 右ペインの表示や説明文を整理
- フォントビュー / 実機ビュー周辺の説明を整理
- 実機ビューの倍率表示やガイド表示周辺を調整
- 縦書き描画、句読点、括弧、ルビ、下端処理まわりの安定性を改善
- EPUB / テキスト変換まわりの回帰テストを追加・整理
- release zip 作成時の必須ファイル検査を Python GUI版前提へ整理
- `Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントについて、OFL ライセンス文書を追加

詳細は以下も参照してください。

- `CHANGELOG.md`
- `RELEASE_NOTES_v1_2_1.md`
- `RELEASE_NOTES_v1_2_0.md`
- `RELEASE_NOTES_v1_1_0.md`（v1.1.0 の基準版メモ）

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

## 出力ファイル名の衝突設定

同名出力の扱いは、右上の歯車メニュー内「その他オプション > 同名出力」から変更できます。


## Font フォルダーの配置

release zip にフォントを同梱する場合は、`Font/NotoSansJP-Regular.ttf` などのフォント本体と `LICENSE_OFL.txt` を一緒に含めます。

source-only 配布物や source-only リポジトリ構成では `Font/` を含めない構成も可能です。その場合、実行時は利用可能な system font へ自動フォールバックし、基準フォントが必要な golden 画像系テストは skip されます。

ライセンス文書とフォント本体の整合が取れない場合、`build_release_zip.py` は release zip 作成を停止します。フォントを同梱しない検証を行う場合は、`build_release_zip.py` 実行前に `Font/` / `fonts/` を置かないか、一時的に退避してください。

## テスト

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

## release zip の作成

release zip は以下で作成できます。

    .venv\Scripts\python.exe -B ^
      build_release_zip.py

作成済み release zip の検証は以下です。

    .venv\Scripts\python.exe -B ^
      build_release_zip.py ^
      --verify ^
      dist\tategaki-xtc-gui-studio_v1.2.1-release.zip

release zip の作成は、環境に応じて以下でも実行できます。

    py -3.12 build_release_zip.py

    python build_release_zip.py

検証は任意の zip パスを指定できます。

    python build_release_zip.py --verify <zipパス>

    python build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.2.1-release.zip

v1.2.1 のこちらで作成する release zip は source-only 構成です。`Font/` を同梱して再配布する場合は、対応するフォント本体と `LICENSE_OFL.txt` を同じ release zip に含めてください。

## GitHub Release での公開方針

v1.2.1 は、GitHub 上では以下の扱いで公開します。

- Release tag: `v1.2.1`
- Release title: `v1.2.1`
- Previous tag: `v1.2.0`
- 添付ファイル: `tategaki-xtc-gui-studio_v1.2.1-release.zip`

Release 本文には `RELEASE_NOTES_v1_2_1.md` の内容を使用します。

開発用の `.venv/` や `node_modules/` は release 対象外です。

## 公開対象について

v1.2.1 の公開対象は **Python GUI版のみ**です。

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

アプリ本体のライセンス / 利用条件は、リポジトリ内のライセンス文書および README の記載に従います。

`Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントは、アプリ本体とは別に **SIL Open Font License 1.1** に基づきます。  
詳細は `LICENSE_OFL.txt` を参照してください。

