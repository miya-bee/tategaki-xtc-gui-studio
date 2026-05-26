# 縦書きXTC GUI Studio

[English README](README_EN.md)

**縦書きXTC GUI Studio** は、Xteink X3 / X4 向けに、青空文庫テキスト、EPUB、Markdown、画像などを、日本語縦書きの **XTC / XTCH** ファイルへ変換する Windows 向け Python GUI アプリです。

ルビ、ページ番号、余白、行間、禁則処理、記号位置補正などを調整し、xteink の純正ファームウェアや XTC / XTCH 対応環境で読みやすい固定レイアウトの電子書籍データを作成できます。

**TategakiXTC GUI Studio** is a Windows GUI tool for converting Aozora Bunko text, EPUB, Markdown, images, and plain text into Japanese vertical-writing **XTC / XTCH** files for **Xteink X3 / X4**.

## 主な用途

このアプリは、次のような用途を想定しています。

- Xteink X3 / X4 で青空文庫を日本語縦書きで読みたい
- EPUB を xteink 向けの XTC / XTCH 形式に変換したい
- ルビ付き小説を固定レイアウトで読みやすくしたい
- 日本語縦書きの余白、行間、文字サイズ、ページ番号を調整したい
- Python コマンド操作ではなく、Windows GUI で変換したい
- xteink の小さな E Ink 画面に合わせて、本文中心の文書を読みやすく整えたい

## 対応入力

主な入力形式は以下です。

- 青空文庫風テキスト
- プレーンテキスト
- Markdown
- EPUB
- 画像ファイル
- 画像アーカイブ系入力

本文中心の小説、随筆、古典作品、青空文庫系テキストなどに向いています。

## 出力形式

主な出力形式は以下です。

- XTC
- XTCH

XTC / XTCH は、xteink X3 / X4 などで扱われる、端末解像度に合わせた固定レイアウト系の表示用ファイルです。

このアプリでは、変換元の本文をあらかじめページ画像として整形し、xteink で読みやすい形に変換します。

## 現在の公開版

現在の GitHub 公開版は **v1.3.6** です。

v1.3.6 は、v1.3.5 以降の追加開発をまとめた公開版です。

主な更新内容は以下です。

- ページ番号表示
- EPUB 入力の堅牢化
- プレビュー更新制御の改善
- ファイルビューワーモード改善
- 保存先処理改善
- 半角数字、半角英字、記号類の位置補正
- ルビ消しモード
- XTC / XTCH 書き出し信頼性強化
- サンプルテキスト同梱

詳細は `RELEASE_NOTES_v1_3_6.md` と `CHANGELOG.md` を参照してください。

## 公開版の履歴メモ

v1.1.0 は、v1.0.2 の次の公開版です。

現在の公開版は v1.3.6 です。

## v1.3.6 の主な機能

### ページ番号表示

出力ページ右下に、`1/100` のようなページ番号を表示できます。

- 初期状態は OFF
- ページ番号フォントサイズを指定可能
- ページ番号 ON 時は、下余白が不足しないように自動補正

電子書籍端末では現在位置が分かりにくいことがあるため、長編小説などで便利です。

### ルビ消しモード

ルビ付きテキストや EPUB から、ルビだけを非表示にして本文を出力できます。

- ルビ付き表示
- ルビ消し表示

を切り替えられます。

小さな E Ink 画面で本文を広く使いたい場合や、ルビが多すぎて読みにくい文書で便利です。

### 日本語縦書き向けの位置補正

フォントや文字種によって、縦書き時の記号位置がずれることがあります。

このアプリでは、以下のような項目を GUI から調整できます。

- 句読点
- 漢数字の「一」
- 半角数字
- 半角数字の縦中横
- 半角記号ペア
- 半角英字
- 下鍵括弧
- 波線描画

### EPUB 入力の堅牢化

v1.3.6 では、EPUB 入力まわりの処理を強化しています。

- EPUB spine の `linear="no"` をスキップ
- 複雑な ruby / rtc 構造で、ルビ文字が本文に漏れにくいよう改善
- CSS の子孫セレクタ / 子セレクタ処理を改善
- `display:none` などの過剰適用を抑制
- EPUB 内画像の検出対象を拡張
- 大きな EPUB の一部経路でメモリ負荷を軽減

ただし、すべての EPUB を完全に再現するものではありません。  
本文中心の EPUB を、xteink 向けの縦書き固定レイアウトへ変換する用途を主な対象にしています。

### XTC / XTCH ファイルビューワー

XTC / XTCH ファイルを読み込み、アプリ上で内容を確認できます。

既に変換したファイルの確認や、xteinkへ転送する前のチェックに使えます。

### フォルダ一括変換

複数ファイルをまとめて XTC / XTCH へ変換できます。

- サブフォルダ対象
- フォルダ構造保持
- 既存ファイルの扱い
- 中止処理

などに対応しています。

## 同梱サンプルテキスト

`sample_texts/` に、設定確認用のテキストを同梱しています。

- `tategaki_position_kinsoku_test_text_v3.txt`
  - TXT / 青空文庫風ルビ / 禁則処理 / 位置補正確認用
- `tategaki_position_kinsoku_bold_markdown_v1.md`
  - Markdown の `**太字**` を使った太字確認用
- `tategaki_tatechuyoko_punctuation_test_text_v1.txt`
  - 縦中横・記号ペア確認用
- `tategaki_halfwidth_alpha_position_test_text_v1.txt`
  - 半角英字位置補正確認用
- `tategaki_halfwidth_fullwidth_alpha_compare_test_text_v1.txt`
  - 半角英字と全角英字の比較確認用

TXT入力では、青空文庫風の `［＃ここから太字］...［＃ここで太字終わり］` は現在太字として解釈しません。  
太字確認は Markdown サンプルを使用してください。

## 得意な文書

このアプリは、次のような文書を主な対象にしています。

- 青空文庫系の小説本文
- 古い小説
- 随筆
- 読み物系テキスト
- ルビ付き本文
- プレーンテキスト
- 本文中心の EPUB

特に、xteink X3 / X4 のような小型 E Ink 端末で、縦書きの読み物を落ち着いて読む用途に向いています。

## 苦手な文書・注意が必要な文書

次のような文書は、縦書き化したときに見た目が不自然になる場合があります。

- Markdown記法が多い文書
- README のような横書き前提の技術文書
- URLが多い文書
- ファイル名やバージョン番号が多い文書
- 英数字や半角記号が多い文書
- 表
- コードブロック
- 箇条書き中心の文書
- 複雑なレイアウトの EPUB

半角コンマ `,` や半角ピリオド `.` は、フォントによって縦書き上で左下寄りに見えることがあります。  
青空文庫系の小説本文では大きな問題になりにくいため、仕様として扱っています。

## 必要環境

推奨環境は以下です。

- Windows 10 / 11
- Python 3.10 / 3.11 / 3.12
- pip
- venv
- PySide6
- Pillow
- numpy

依存パッケージは `requirements.txt` からインストールします。

`numpy` は XTC / XTCH pack の高速化に使います。

## 初回セットアップ

Windows のコマンドプロンプトで、展開先フォルダーに移動してから実行してください。

Python は 3.10 / 3.11 / 3.12 系を想定しています。  
迷った場合は 3.12 を優先してください。

### 1. Python を確認する

```cmd
python --version

py -3.12 --version
```

うまく動かない場合は、環境に合わせて以下も確認してください。

```cmd
py -3.11 --version

py -3.10 --version

python --version
```

### 2. 依存ライブラリを入れる

通常は付属のバッチファイルを使えます。

```cmd
install_requirements.bat
```

手動で入れる場合は以下です。

```cmd
py -3.12 -m pip install ^
  --upgrade pip

py -3.12 -m pip install ^
  -r requirements.txt
```

仮想環境を使う場合は以下です。

```cmd
py -3.12 -m venv .venv

.venv\Scripts\activate

.venv\Scripts\python.exe ^
  -m pip install ^
  --upgrade pip

.venv\Scripts\python.exe ^
  -m pip install ^
  -r requirements.txt
```

### 3. 起動する

```cmd
run_gui.bat
```

または、仮想環境を有効にしたうえで以下を実行します。

```cmd
.venv\Scripts\python.exe -B ^
  tategakiXTC_gui_studio.py
```

## Windows exe版について

GitHub 公開版は Python 環境が必要な source 配布版です。

Python環境なしで使いたい方向けに、Windows exe / portable 版も note で配布しています。

- GitHub版
  - Python環境がある方向け
  - source 配布
  - 無料で利用可能
- Windows exe / portable版
  - Python環境なしで使いたい方向け
  - note 有料配布
  - ZIPを展開して実行

Windows exe版 / ローカルWeb-GUI版の配布記事はこちらです。

https://note.com/miya_bee_note/n/n8e8424e96e4e

起動手順やトラブル対処は、無料サポート記事にもまとめています。

https://note.com/miya_bee_note/n/n0e172d7d2acb

xteink 関連記事のまとめはこちらです。

https://note.com/miya_bee_note/n/n1b5ef2af20d3

## 関連ドキュメント

- `WINDOWS_SETUP.md` — Windowsでの導入・起動手順
- `FAQ.md` — よくある質問
- `KNOWN_LIMITATIONS.md` — 既知の注意点・仕様
- `RELEASE_NOTES_v1_3_6.md` — v1.3.5 から v1.3.6 までの差分まとめ
- `RELEASE_NOTES_v1_3_5.md` — v1.3.4 から v1.3.5 までの差分まとめ
- `RELEASE_NOTES_v1_3_4.md` — v1.3.3 から v1.3.4 までの差分まとめ
- `CHANGELOG.md` — 公開版単位の更新履歴

## release zip の作成

release zip は以下で作成できます。

```cmd
.venv\Scripts\python.exe -B ^
  build_release_zip.py
```

作成済み release zip の検証は以下です。

```cmd
.venv\Scripts\python.exe -B ^
  build_release_zip.py ^
  --verify ^
  dist\tategaki-xtc-gui-studio_v1.3.6-release.zip
```

環境に応じて、以下でも実行できます。

```cmd
py -3.12 build_release_zip.py

python build_release_zip.py
```

検証は任意の zip パスを指定できます。

```cmd
python build_release_zip.py --verify <zipパス>

python build_release_zip.py --verify dist\tategaki-xtc-gui-studio_v1.3.6-release.zip
```

## テスト

代表的なテストは以下です。

```cmd
.venv\Scripts\python.exe -B ^
  -m py_compile ^
  build_release_zip.py ^
  tategakiXTC_gui_core.py ^
  tategakiXTC_gui_studio.py ^
  tategakiXTC_worker_logic.py
```

```cmd
.venv\Scripts\python.exe -B ^
  -m unittest ^
  tests.test_type_annotations_regression ^
  tests.test_release_docs_regression ^
  tests.test_release_hygiene_regression ^
  -v
```

```cmd
.venv\Scripts\python.exe -B ^
  -m unittest ^
  tests.test_release_bundle_hygiene ^
  -v
```

```cmd
.venv\Scripts\python.exe -B ^
  -m unittest ^
  tests.test_conversion_worker_logic ^
  -v
```

pytest を導入している環境では、collection だけを先に確認すると SyntaxError の早期検出に便利です。

```cmd
.venv\Scripts\python.exe -B ^
  -m pytest ^
  tests ^
  --co ^
  -q
```

## 同梱フォントについて

縦書き表示とテスト再現性を高めるため、`Font/` フォルダーに Noto Sans JP / Noto Serif JP 系フォントを同梱できます。

同梱フォントは SIL Open Font License 1.1 に基づいて配布されています。  
詳細は `LICENSE_OFL.txt` を参照してください。

アプリ本体の利用条件と、同梱フォントのライセンスは別です。

- アプリ本体
  - このリポジトリのライセンス / 利用条件に従います
- 同梱フォント
  - `LICENSE_OFL.txt` に記載の SIL Open Font License 1.1 に従います

フォントを削除した環境でも、利用可能な system font へ自動フォールバックします。  
ただし、golden 画像系テストや描画差分確認では、基準フォントの有無により結果が変わる場合があります。

## Font フォルダーの配置

`Font/` は同梱フォント用フォルダーです。

主な用途は以下です。

- GUI プレビューの表示安定化
- 縦書き描画の再現性向上
- golden 画像系テストの差分確認

別のフォントを使いたい場合は、`Font/` または `fonts/` に `.ttf` / `.ttc` / `.otf` / `.otc` ファイルを配置できます。

フォントを追加・差し替えして再配布する場合は、必ず対象フォントのライセンスを確認してください。  
フォントを release zip に含める場合は、対応するライセンス文書も含める必要があります。

ライセンス文書とフォント本体の整合が取れない場合、`build_release_zip.py` は release zip 作成を停止します。

source-only 配布物では、環境や配布形態によって `Font/` フォルダーを含まない場合があります。

`Font/` が見つからない場合でも、アプリは利用可能な system font へ自動フォールバックします。  
ただし、golden 画像系テストや描画差分確認では、基準フォントの有無により結果が変わる場合があります。

## GitHub Release での公開方針

v1.3.6 は、GitHub 上では以下の扱いで公開しています。

- Release tag: `v1.3.6`
- Release title: `v1.3.6`
- Previous tag: `v1.3.5`
- 添付ファイル: `tategaki-xtc-gui-studio_v1.3.6-release.zip`

GitHub Release では Python GUI 版の source 配布 zip を公開します。

Windows exe / portable 版は GitHub には置かず、note 有料配布向けに別途配布します。

## 公開対象について

v1.3.6 の GitHub 公開対象は Python GUI版のみです。

旧ローカル Web 試作版関連ファイルは、公開用 payload / release 検査の対象外です。

## ライセンス

This project is **Source Available**, not Open Source.

You may view and study the source code for personal use only.  
Redistribution, commercial use, and distribution of modified versions are not permitted.

See `LICENSE.txt` for details.

GitHub のライセンス表示では、OSI 認定ライセンスではないため **Other** として扱ってください。

`Font/` に同梱している Noto Sans JP / Noto Serif JP 系フォントは、アプリ本体とは別に **SIL Open Font License 1.1** に基づきます。  
詳細は `LICENSE_OFL.txt` を参照してください。

## Keywords

Xteink X3, Xteink X4, xteink, XTC, XTCH, Aozora Bunko, 青空文庫, EPUB, Japanese vertical writing, 日本語縦書き, ruby text, ルビ, E Ink, ebook converter, Windows GUI, Python GUI.
