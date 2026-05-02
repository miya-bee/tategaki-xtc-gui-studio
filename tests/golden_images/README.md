# ゴールデン画像テスト運用メモ

## ケース名のファミリ

- `glyph_*`
  - 単字・単体グリフ比較
  - 例: `glyph_ichi`, `glyph_small_kana_ya`
- `tatechuyoko_*`
  - 縦中横の単体比較
  - 例: `tatechuyoko_2025`
- `page_*`
  - ページ全体・複数段落・ルビまたぎ・端末別レイアウト比較
  - 出力フィルタ（ナイトモード / XTCH）や `ruby_size` 極値ケースも含みます
  - 例: `page_compound_layout`, `page_x4_profile_layout`, `page_night_mode_layout`

## しきい値プロファイルの考え方

ケース名と `threshold_profile` は、同じファミリ接頭辞で揃えます。

- `glyph_*` ケース → 原則 `glyph_*` 系プロファイル
- `tatechuyoko_*` ケース → 原則 `tatechuyoko_*` 系プロファイル
- `page_*` ケース → 原則 `page_*` 系プロファイル

新しいケースを追加するときは、まず既存の `THRESHOLD_PROFILES` から選びます。
既存で足りない場合のみ、新しいプロファイルを追加してください。

## 更新手順

基準フォント配置状態を確認するとき:

```bat
.venv\Scripts\python.exe -B ^
  tests\generate_golden_images.py ^
  --font-status
```

差分ケース名だけを確認するとき:

```bat
.venv\Scripts\python.exe -B ^
  tests\generate_golden_images.py ^
  --list-stale
```

差分確認だけを行うとき:

```bat
.venv\Scripts\python.exe -B ^
  tests\generate_golden_images.py ^
  --check
```

特定ケースだけを切り分けるとき:

```bat
.venv\Scripts\python.exe -B ^
  tests\generate_golden_images.py ^
  --check ^
  --case page_compound_layout
```

複数ケースをまとめて確認するとき:

```bat
.venv\Scripts\python.exe -B ^
  tests\generate_golden_images.py ^
  --check ^
  --case page_compound_layout ^
  --case page_heading_spacing
```

差分がある画像だけ更新するとき:

```bat
.venv\Scripts\python.exe -B ^
  tests\generate_golden_images.py ^
  --update
```

全ケースを再生成するとき:

```bat
.venv\Scripts\python.exe -B ^
  tests\generate_golden_images.py
```

## CI 上の確認

この README のローカル実行例は、Windows cmd とプロジェクト直下の `.venv` を前提にしています。
GitHub Actions では workflow 側で準備した Python を使うため、ローカル手順の `.venv\Scripts\python.exe -B` 形式とは別管理です。


## 基準フォントの配置

ゴールデン画像の実差分確認は、プロジェクト直下に次の基準フォントがある場合だけ実行されます。

```text
Font/NotoSansJP-Regular.ttf
```

`--font-status` の状態コードが `ready` なら比較可能、`missing` なら比較は省略されます。`missing` の場合は `Font` フォルダーをプロジェクト直下へコピーしてから、`--font-status` と `--list-stale` を再確認してください。

## 自動整合チェック

次のテストが、ケース定義としきい値プロファイル定義の整合を自動で確認します。

- `tests/test_golden_profile_registry.py`

このテストでは、次を検査します。

- すべての `threshold_profile` が定義済みであること
- 未使用のプロファイルが残っていないこと
- ケース名ファミリとプロファイル名ファミリが一致していること
