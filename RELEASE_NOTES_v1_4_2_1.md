# TategakiXTC GUI Studio v1.4.2.1

v1.4.2.1 は、v1.4.2 の小修正版です。TXT / Markdown などのテキスト入力で、本文冒頭の空行が描画上で無視される場合がある問題を修正しています。

## 主な変更

- 入力テキストの先頭に空行がある場合、その空行が本文開始前の空白列として反映されるようにしました。
- 本文冒頭の空行による列送りを、本文中の空行と同じ見え方になるよう調整しました。
- 先頭空行だけが本文中の空行より1列多く送られる問題を修正しました。
- アプリバージョンを `1.4.2.1` に更新しました。

## 変更していない範囲

- XTC / XTCH の基本書き出し形式は変更していません。
- EPUB解析、ルビ描画、禁則処理、3ペインUI構造は維持しています。
- Windows portable/exe 版は GitHub Release には含めず、従来どおり note 購入者向け配布として扱います。
- 旧ローカル Web 試作版は、この Python GUI 版公開パッケージには含めません。

## English summary

v1.4.2.1 is a small patch release after v1.4.2.

- Fixed a case where leading blank lines at the beginning of text input were not reflected in the rendered vertical layout.
- Adjusted the initial column advance so a leading blank line matches the visible spacing of a blank line inside the body text.
- Updated the application version to `1.4.2.1`.

## 検証

- Python compile
- focused text/rendering regression checks
- release zip build and verify
- zip integrity / forbidden cache-log-ini-pyc artifact check

## 成果物

- `tategaki-xtc-gui-studio_v1.4.2.1-release.zip`
- `tategaki-xtc-gui-studio_v1.4.2.1-release.zip.sha256.txt`

詳細な履歴は `CHANGELOG.md` を参照してください。
