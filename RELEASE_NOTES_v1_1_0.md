# v1.1.0

v1.1.0 は、GitHub で公開済みの **v1.0.2 の次の正式版**です。

このリリースは **Python GUI版のみ**を公開対象とします。  
旧ローカル Web 試作版関連ファイルは、v1.1.0 の release payload には含めません。

## 公開情報

- Release tag: `v1.1.0`
- Release title: `v1.1.0`
- Previous tag: `v1.0.2`
- Release asset: `tategaki-xtc-gui-studio_v1.1.0.zip`

GitHub Release では、`v1.1.0` を正式版として公開します。  
`rc1` や `sweep` 番号は、公開版名には含めません。

## 主な更新内容

### Python GUI版のみを公開対象として整理

v1.1.0 では、公開対象を Python GUI版のみに整理しました。

作業用 payload に残っていた旧ローカル Web 試作版関連ファイルは、公開用 payload / release 検査の対象から除外しています。

### GUI と説明文の整理

GUI の表示や説明文を整理しました。

主な整理内容は以下です。

- 左ペインの表記整理
- フォントビュー / 実機ビューの説明整理
- 実寸近似やガイド表示まわりの説明整理
- 右ペインの倍率表示まわりの調整
- README の初回セットアップ手順整理
- Font フォルダーとライセンス説明の追加

### 描画・変換処理の安定化

縦書き描画、句読点、括弧、ルビ、下端処理まわりの安定性を改善しました。

主な改善対象は以下です。

- 閉じ括弧の描画位置
- ぶら下がり句読点の配置
- 下端 guard と余白処理
- ルビ描画まわりの回帰防止
- preview / device view 周辺の安定性
- EPUB / テキスト変換まわりの回帰確認

### release payload の整理

v1.1.0 では、release zip 作成・検査を Python GUI版前提に整理しました。

以下の旧ローカル Web 試作版関連ファイルは、公開用 payload には含めません。

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

### 同梱フォントについて

v1.1.0 では、縦書き表示とテスト再現性のため、`Font/` フォルダーに Noto Sans JP / Noto Serif JP 系フォントを同梱しています。

同梱フォントは **SIL Open Font License 1.1** に基づいて配布されています。  
詳細は `LICENSE_OFL.txt` を参照してください。

アプリ本体の利用条件と、同梱フォントのライセンスは別です。

## インストール / 起動

zip を展開したあと、Windows のコマンドプロンプトで展開先フォルダーに移動してください。

初回セットアップ:

    py -3.10 -m venv .venv

    .venv\Scripts\activate

    .venv\Scripts\python.exe ^
      -m pip install ^
      --upgrade pip

    .venv\Scripts\python.exe ^
      -m pip install ^
      -r requirements.txt

起動:

    run_gui.bat

または:

    .venv\Scripts\python.exe -B ^
      tategakiXTC_gui_studio.py

## 動作確認の目安

公開前確認では、以下を確認しています。

- Python GUI版として起動できること
- 主要 Python ファイルが compile できること
- release docs / release hygiene 系の回帰テストが通ること
- release bundle hygiene 系の検査が通ること
- conversion worker 周辺のテストが通ること
- release zip の verify が通ること
- 旧ローカル Web 試作版関連ファイルが release payload に混入していないこと
- `Font/` と `LICENSE_OFL.txt` が同梱フォントの扱いとして整合していること

## 注意事項

- v1.1.0 は Python GUI版のみの公開です
- 旧ローカル Web 試作版は公開対象外です
- 同梱フォントは SIL Open Font License 1.1 に従います
- フォントを差し替えて再配布する場合は、差し替え先フォントのライセンスを確認してください
- GitHub Release の添付ファイルには `tategaki-xtc-gui-studio_v1.1.0.zip` を使用してください

## 更新対象ファイルの例

v1.1.0 では、主に以下を更新・整理しています。

- `README.md`
- `CHANGELOG.md`
- `RELEASE_NOTES_v1_1_0.md`
- `LICENSE_OFL.txt`
- `build_release_zip.py`
- `run_tests.bat`
- `.github/workflows/python-tests.yml`
- `tests/test_release_docs_regression.py`
- `tests/test_release_hygiene_regression.py`
- `tests/test_release_bundle_hygiene.py`
- `tests/test_type_annotations_regression.py`
- `tategakiXTC_worker_logic.py`
- `tategakiXTC_gui_studio.py`

## まとめ

v1.1.0 は、v1.0.2 の次の正式版として、Python GUI版を公開向けに整理したリリースです。

描画・変換処理の安定化、GUI 表示の整理、release payload の整理、同梱フォントのライセンス明記を行っています。
