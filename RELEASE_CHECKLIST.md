# RELEASE CHECKLIST

公開前に以下を確認します。

## Windows 実機確認

- targeted test が通る
- 必要に応じてフル回帰テストが通る
- GUI が起動する
- ぶら下がり句読点 `下補正 / 標準 / 上補正` が切り替わる
- 漢数字「一」位置 `標準 / 補正` が切り替わる
- ini に `punctuation_position_mode` / `ichi_position_mode` が保存され、再起動後に復元される

## release zip 確認

- `tategakiXTC_gui_studio.ini` を含めない
- `Font/` を同梱する場合は `LICENSE_OFL.txt` も含める
- README / CHANGELOG / release notes / release metadata の版番号が一致する
- `build_release_zip.py --verify <zipパス>` が通る

## GitHub Release 確認

- Release tag / title が公開版番号と一致する
- Previous tag が前回公開版と一致する
- 添付ファイル名が release metadata と一致する
- Release 本文は該当 `RELEASE_NOTES_*.md` を使用する
