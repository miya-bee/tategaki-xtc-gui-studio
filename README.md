# 縦書きXTC GUI Studio

**縦書きXTC GUI Studio** は、EPUB やテキストを、xteink X4 / X3 などで扱いやすい縦書き XTC / XTCH 形式へ変換するための Python GUI アプリです。

このリポジトリの公開版は **Python GUI版のみ**です。  
旧ローカル Web 試作版関連ファイルは、v1.1.0 の公開対象から除外しています。

## バージョン

現在の公開版は **v1.1.0** です。

v1.1.0 は、GitHub で公開済みの **v1.0.2 の次の正式版**として扱います。

- 前回公開版: `v1.0.2`
- 今回公開版: `v1.1.0`
- GitHub Release tag: `v1.1.0`
- GitHub Release title: `v1.1.0`

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
- `RELEASE_NOTES_v1_1_0.md`

## 必要環境

推奨環境:

- Windows 10 / 11
- Python 3.10 系
- pip
- 仮想環境 venv

依存パッケージは `requirements.txt` からインストールします。

## 初回セットアップ

Windows のコマンドプロンプトで、展開先フォルダーに移動してから実行してください。

    py -3.10 -m venv .venv

    .venv\Scripts\activate

    .venv\Scripts\python.exe ^
      -m pip install ^
      --upgrade pip

    .venv\Scripts\python.exe ^
      -m pip install ^
      -r requirements.txt

## 起動方法

通常は、付属のバッチファイルから起動できます。

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
      dist\sweep471_smoke-release.zip

v1.1.0 では `Font/` を同梱する方針のため、release zip には `LICENSE_OFL.txt` も含めます。

## GitHub Release での公開方針

v1.1.0 は、GitHub 上では以下の扱いで公開します。

- Release tag: `v1.1.0`
- Release title: `v1.1.0`
- Previous tag: `v1.0.2`
- 添付ファイル: `tategaki-xtc-gui-studio_v1.1.0.zip`

Release 本文には `RELEASE_NOTES_v1_1_0.md` の内容を使用します。

## 公開対象について

v1.1.0 の公開対象は **Python GUI版のみ**です。

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

## ライセンス

アプリ本体のライセンス / 利用条件は、リポジトリ内のライセンス文書および README の記載に従います。

`Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントは、アプリ本体とは別に **SIL Open Font License 1.1** に基づきます。  
詳細は `LICENSE_OFL.txt` を参照してください。
