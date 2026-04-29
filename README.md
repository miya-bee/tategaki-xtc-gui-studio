# 縦書きXTC GUI Studio

Xteink 向けの縦書き **XTC / XTCH** ファイルを、GUI で作成・確認するための Windows 向けツールです。  
EPUB、画像アーカイブ、プレーンテキスト、Markdown、単体画像を入力として扱えます。

> \*\*注意:\*\* テキストファイル（`.txt`）とマークダウンファイル（`.md` / `.markdown`）の変換は、十分な実地検証ができていない \*\*簡易実装\*\* です。ログタブと `logs` フォルダへ、対応範囲の概要と簡略扱いになった要素の注意を出すようにしています。

## バージョン

**1.1.0**

この版は、GitHub 上で既に公開済みの **v1.0.2 の次の公開版**として扱います。
公開時のタグ / Release 名は **v1.1.0** を想定しています。

## v1.0.2 から v1.1.0 への主な更新

* 左ペインの既定順を **Preset → Font → Image → Display** に整理し、公開版として説明しやすい UI に整えました。
* プリセット周辺の操作を見直し、ボタン名を **「プリセット適用」 / 「組版保存」** に統一しました。
* 実機ビューまわりを再監査し、X3 / X4 判定、X3 の **528 × 792** 解像度、実機枠の直角表示、表示ラベルの整合を改善しました。
* `XTCH` 指定時のプレビュー反映、プレビュー中の再入防止、成功 / 空結果 / 失敗時の UI 復帰を整理しました。
* 単体画像（`.png` / `.jpg` / `.jpeg` / `.webp`）を GUI から選択して変換できるよう改善しました。
* 同名出力の導線を **右上の歯車メニュー内「その他オプション > 同名出力」** に統一しました。
* `MainWindow` から preview / results / settings controller、layout helper、widget factory、`tategakiXTC\_gui\_studio\_logic.py` などへの切り出しを進め、今後の分割作業に入りやすい形へ整理しました。
* 字形キャッシュ、画像ページ処理、XTC / XTCH pack 処理、preview 再利用などを見直し、変換とプレビューの体感速度を改善しました。
* `coverage`、`mypy`、release zip 監査を整え、GitHub 公開前の検査漏れが起きにくい構成にしました。

## 公開方針 / 利用条件

本リポジトリでのソース公開は、**学習および透明性のため** に行っています。

* ソースの閲覧・学習・参考利用: 可
* ソースそのものの再配布: 不可
* 商用利用: 不可
* 改変したものの配布: 不可

必要に応じて個別に許諾する場合があります。詳細は `LICENSE.txt` を参照してください。

## 開発環境

* Windows 上で開発・動作確認を行っています。
* **Windows を公式対応の起点** とし、macOS / Linux での動作は未確認です。
* Python は **3.10 / 3.11 / 3.12 系**を想定しています。
* Python 3.10 では `typing\_extensions` があると、型付き辞書の互換動作がより安定します。

## 主な機能

* EPUB の縦書き XTC / XTCH 変換
* ZIP / CBZ / CBR / RAR 内画像の一括変換
* 単体画像（PNG / JPG / JPEG / WEBP）の変換
* `.txt` の簡易変換
* `.md` / `.markdown` の簡易変換
* フォントビュー / 実機ビューによる確認
* フォント、ルビ、行間、余白、しきい値、ディザリングの調整
* 白基調 / ダークの外観切替
* プリセット保存・呼び出し
* 白黒反転の出力反映
* 禁則処理の切替（オフ / 簡易 / 標準）

## 対応入力形式

|形式|備考|
|-|-|
|`.epub`|推奨入力|
|`.zip` / `.cbz` / `.cbr` / `.rar`|内部画像を一括変換|
|`.png` / `.jpg` / `.jpeg` / `.webp`|単体画像として変換|
|`.txt`|簡易対応|
|`.md` / `.markdown`|簡易対応|

## テキスト / マークダウン変換の簡易対応について

テキストおよびマークダウンの変換は **テストが十分ではない簡易実装** です。  
正確な縦書き組版が必要な場合は EPUB 形式の使用を推奨します。

### `.txt`

* UTF-8（BOM 付き含む）を優先し、必要に応じて CP932 でも読み込みます。
* 改行を段落区切りとして扱います。
* 青空文庫形式のルビ記法など、特殊な記法は解釈しません。

### `.md` / `.markdown`

* UTF-8（BOM 付き含む）を優先し、必要に応じて CP932 でも読み込みます。
* 見出し（`#`）の前後に空きを入れて表示します。
* 箇条書きを簡易整形します。
* `\*\*太字\*\*` / `\*斜体\*` / `\*\*\*太字斜体\*\*\*` に対応します。
* リンクは表示テキストを残し URL を省略します。
* コードブロックは本文として扱います。

## 同梱フォントについて

* この配布物には、縦書き表示とゴールデン画像確認の再現性を高めるため、`Font/` フォルダーに Noto Sans JP / Noto Serif JP 系フォントを同梱しています。
* 同梱フォントは SIL Open Font License 1.1 に基づいて配布されています。詳細は `LICENSE_OFL.txt` を参照してください。
* フォントを削除した環境でも、利用可能な system font へ自動フォールバックします。ただし、ゴールデン画像系テストの実差分確認では、基準フォントの有無により結果が変わる場合があります。

## source-only 配布物について

* ゴールデン画像系テストのうち、基準フォント前提のものは、条件を満たさない環境では **skip されます**。
* v1.1.0 公開版は、既存の **v1.0.2 の次の版**として公開する Python GUI版です。

## 初回セットアップ

### 1\. Python を確認する

Windows のコマンドプロンプトで、Python 3.10〜3.12 系が使えることを確認します。

```bat
py -3.12 --version
```

3.12 が無い場合は、次のどちらかを確認してください。

```bat
py -3.11 --version

py -3.10 --version
```

`py` ランチャーを使わない環境では、`python --version` で 3.10〜3.12 系であることを確認後、以降の `py -3.12` を `python` に読み替えてください。

### 2\. 仮想環境を作る

```bat
cd /d <このリポジトリを展開したフォルダ>

py -3.12 -m venv .venv

.venv\\Scripts\\activate
```

3.12 が無い場合は、`py -3.11` または `py -3.10` を使ってください。

### 3\. 依存ライブラリを入れる

GUI 版の依存ライブラリは `requirements.txt` から導入します。仮想環境を使わずに入れる場合は、`py -3.12 -m pip install -r requirements.txt`（3.12 が無い場合は `py -3.11` / `py -3.10`）または `python -m pip install -r requirements.txt`（`python --version` で 3.10〜3.12 系であることを確認後）でも導入できます。

```bat
.venv\\Scripts\\python.exe ^
  -m pip install ^
  --upgrade pip

.venv\\Scripts\\python.exe ^
  -m pip install ^
  -r requirements.txt
```

* `PySide6` が未導入だと GUI は起動しません。
* `numpy` は未導入でも動作しますが、XTC / XTCH pack や preview 再利用まわりの **高速化** を活かすには導入を推奨します。
* Python 3.10 では `typing\_extensions` があると、型付き辞書の互換動作がより安定します。

### 4\. 起動する

通常は `run\_gui.bat` から起動します。

```bat
run\_gui.bat
```

直接起動する場合は、次のどちらかを使います。

```bat
py -3.12 tategakiXTC\_gui\_studio.py

python tategakiXTC\_gui\_studio.py
```

`run\_gui.bat` / `run\_tests.bat` は、どの作業フォルダから実行しても **同梱スクリプトのあるフォルダへ自動移動** してから処理します。
アプリ配置先に `logs/` を作れない環境では、ログは一時フォルダへ自動退避します。

## Font フォルダーの配置

`Font/` は同梱フォント用フォルダーです。v1.1.0 では Noto Sans JP / Noto Serif JP 系フォントを同梱しています。

別のフォントを使いたい場合は、`Font/` または `fonts/` に `.ttf` / `.ttc` / `.otf` / `.otc` を配置できます。

フォントを release zip に含める場合は、フォントのライセンスを確認し、`LICENSE_OFL.txt` をプロジェクト直下または `Font/` / `fonts/` 直下に置いてください。

## 使い方

1. `run\_gui.bat` から起動します。
2. 変換したい EPUB / アーカイブ / TXT / Markdown / 画像を選択します。
3. フォント、本文サイズ、ルビサイズ、行間、余白、出力形式（XTC / XTCH）などを調整します。
4. 必要に応じてプレビューで確認し、変換を実行します。

### 補足

* 同名ファイルがある場合の動作は、**右上の歯車メニュー内「その他オプション > 同名出力」** で選べます。
* 画像処理系の設定では、白黒反転（出力）とディザリングを切り替えられます。
* 実機ビューとフォントビューの切り替え状態は保存されます。



## テストと coverage の運用

* ローカルでは `run\_tests.bat` を使うと、ユニットテスト / ゴールデン画像確認 / coverage / `mypy` / release zip 検査をまとめて実行できます。
* coverage の fail-under は **60%** です。
* `coverage-report.txt` / `coverage.xml` / `htmlcov/` を生成し、確認後は GitHub へ含めない運用です。
* PySide6 実環境向けのスモークテストは任意で、ライブラリが無い環境では自動で skip されます。GUI smoke はヘッドレス CI / WSL でも落ちにくいよう、未指定時は `QT\_QPA\_PLATFORM=offscreen` で実行します。

## GitHub に置かないローカル生成物

以下は開発用・ローカル用として扱い、コミットしない想定です。

* `logs/`
* `dist/`
* `htmlcov/`
* `.venv/` / `venv/`
* `.mypy\_cache/` / `.ruff\_cache/`
* `node\_modules/`
* `\_\_pycache\_\_/`
* `\*.rootcopy`
* `work\_clean\*\_md.md`
* `\*.zip` / `\*.7z` / `\*.tar` / `\*.tgz` / `\*.gz` / `\*.bz2` / `\*.xz` / `\*.whl`

## 配布 zip の作成

* 開発用生成物を除外した zip は `py -3.12 build\_release\_zip.py`（3.12 が無い場合は `py -3.11` / `py -3.10`）または `python build\_release\_zip.py`（`python --version` で 3.10〜3.12 系であることを確認後）で作成できます。
* 既定では `dist/<フォルダ名>-release.zip` を生成します。
* 生成済み zip の再検査は `py -3.12 build\_release\_zip.py --verify <zipパス>`（3.12 が無い場合は `py -3.11` / `py -3.10`）または `python build\_release\_zip.py --verify <zipパス>`（`python --version` で 3.10〜3.12 系であることを確認後）で行えます。
* `--verify` は除外対象メンバー名に加えて、zip の読み取り破損、重複メンバー、symlink 等の特殊ファイル属性、Windows 展開時の名前衝突、危険な member 名、ローカル生成物混入、必須ファイル不足、必須ファイルの内容 marker、UTF-8 / ASCII 条件、回帰テスト一覧、golden 画像一覧、必須 release ファイルリストの同期漏れを検査します。
* v1.1.0 公開版は **Python GUI版のみ** を対象とします。GitHub 公開先は GUI版リポジトリとして扱い、作業用 payload に Web 試作ファイル候補（`requirements-web.txt`、`run\_local\_web.bat`、`tategakiXTC\_localweb.py` など）が混入した場合も release 対象外として検出します。
* フォントを同梱する場合は `LICENSE\_OFL.txt` をプロジェクト直下、または `Font/` / `fonts/` 直下に置いてください。検査では `Font` / `fonts` と `LICENSE\_OFL.txt` の大文字小文字ゆらぎを許容しますが、ライセンスは root 直下または `Font/` / `fonts/` 直下の直接配置だけを数え、`fonts/subdir/LICENSE\_OFL.txt` のような深い階層や、空・空白のみ・制御文字のみ・UTF-8 / UTF-16 / UTF-32 BOM と空白のみ、または BOM なしで UTF-8 として decode できない、短いものを含む BOM なし UTF-16/UTF-32 風、または BOM が示す文字コードで decode できない `LICENSE\_OFL.txt` は充足扱いにしません。複数候補がある場合は、読み取りに失敗した候補があっても、別候補が読み取り可能かつ非空なら充足扱いにします。フォント本体は `Font/` / `fonts/` 配下の `.ttf` / `.ttc` / `.otf` / `.otc` を同梱フォントとして扱い、深い階層のフォントも対象ですが、`.ttf.bak` などの suffix もどきは対象外です。zip 内の同梱フォント/ライセンス資産判定では POSIX `/` 区切りの正規 archive member 名だけを数え、leading slash や Windows 形式のバックスラッシュ区切りなどの非正規 member はフォント/ライセンス充足扱いにしません。symlink されたフォントやライセンスは、release 作成時に取り込まれないため同梱判定からも除外します。
* `logs/`、`\_\_pycache\_\_/`、`.pytest\_cache/`、coverage 生成物（`.coverage.\*` を含む）、ローカル ini、分割準備メモ、`.rootcopy`、テストログ（`\*.log` / `\*.out` / `\*.err` や `test\_full\_log\*.txt` など）・分割実行用の一時 `bundle\_\*.txt`、trace / prof / pid / lock などの一時実行ファイル、古い配布 zip / 7z / tar / wheel などのローカルアーカイブは自動で除外されます。

## 変更履歴

* 詳細な履歴は [CHANGELOG.md](CHANGELOG.md) を参照してください。
* GitHub Release 本文の下書きとしては [RELEASE\_NOTES\_v1\_1\_0.md](RELEASE_NOTES_v1_1_0.md) を用意しています。
* GitHub では、既存の v1.0.2 に続く正式版として **v1.1.0** タグ / Release で公開する想定です。

## ライセンス

* 本ツールは一般的なオープンソースライセンスでは公開していません。
* ソース公開は学習・透明性のためです。
* 再配布・商用利用・改変物配布は不可です。
* 詳細は `LICENSE.txt` を参照してください。

