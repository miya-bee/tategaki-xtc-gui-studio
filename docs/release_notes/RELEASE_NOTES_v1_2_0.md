# tategakiXTC GUI Studio v1.2.0 Release Notes

- 公開向けバージョン表記: `v1.2.0`
- 基準: `v1.1.1.37`
- 位置づけ: v1.1.1 系の累積改修をまとめた公開向け安定版

## 主な更新

- v1.1.0 公開後に積み重ねた v1.1.1 系の GUI 整理、プレビュー安定化、描画補正、release hygiene を、公開向け安定版としてまとめました。
- 句読点・漢数字「一」・下鍵括弧の描画位置補正を整理し、プレビューと実変換で設定が反映されるようにしました。
- ぶら下がり句読点、下余白クリップ、余白変更時のページ維持、白黒反転プレビューなど、縦書き表示周辺の退行を補正しました。
- 左ペイン「プリセット」仕様表示の余白・高さ計算を調整し、`setMaximumHeight(0)` によって QLabel が消えたままになる問題を防止しました。
- 左ペイン下部「変換結果 / ログ」エリアの外側スクロールバー同期を安定化しました。
- 公開対象を Python GUI版に整理し、release zip 作成・検証・CI / 回帰テスト関連の整合性を更新しました。

## 互換性

- ini の保存キーと読み込み互換は維持しています。
- v1.1.1 系で追加した設定項目は、従来設定がない環境でも既定値で起動します。
- 旧 Web 試作版関連ファイルは、v1.2.0 の公開対象には含めません。
- こちらで作成する release zip は source-only 構成です。`Font/` を同梱して再配布する場合は、対応するフォント本体と `LICENSE_OFL.txt` を同じ release zip に含めてください。

## GitHub Release 推奨設定

- Release tag: `v1.2.0`
- Release title: `v1.2.0`
- Previous tag: `v1.1.1.37`
- 添付ファイル: `tategaki-xtc-gui-studio_v1.2.0-release.zip`
- Pre-release: オフ
- Latest release: オン

## 確認事項

- README / CHANGELOG / release notes / APP_VERSION が v1.2.0 で一致していること。
- `build_release_zip.py` で `dist/tategaki-xtc-gui-studio_v1.2.0-release.zip` が作成できること。
- `build_release_zip.py --verify dist/tategaki-xtc-gui-studio_v1.2.0-release.zip` が成功すること。
- GitHub Release の本文にこのファイルの内容を使用すること。
