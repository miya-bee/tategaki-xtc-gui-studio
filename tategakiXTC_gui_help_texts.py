from __future__ import annotations

"""Help text providers for TategakiXTC GUI Studio.

This module keeps long, mostly-static help prose outside the MainWindow
implementation.  The text remains intentionally plain-text because it is shown
in QTextEdit help dialogs and is also easy to inspect in regression tests.
"""

USAGE_HELP_TEXT_EN = """\
[Basic workflow]
1. Use "Open File" to choose a source file, and "Save To..." to choose an output folder when needed.
2. Use "Batch Convert Folder" when converting multiple files together.
3. Adjust the settings in the left and center panes.
4. Use "Refresh Preview" when you want to regenerate the preview manually.
5. Check the text appearance in the right preview pane.
6. Press "▶ Convert" to save .xtc / .xtch files.
7. After conversion, you can inspect XTC / XTCH output in the right pane.

[Preview]
- Right pane: check how the current settings will look. When you open an XTC/XTCH file, it is shown in the same pane with page navigation.
- Use Prev/Next or the page number field to move through pages.
- In the gear menu, "Reverse page keys" swaps the page-key direction and Prev/Next feel.

[Right-pane toolbar]
- "Actual Size" approximates the real device size on your PC display.
- When Actual Size is enabled, the right-pane zoom control works as actual-size adjustment.
- Adjust it while comparing the on-screen size with a ruler or the real device.
- "Guides" overlays margin and non-display-area guide lines.

[Output and device settings]
- Device selection is in the Output section.
- Selecting a device sets the resolution automatically. Use Custom for manual width/height.

[File Viewer]
- Use "Open XTC File" to load an existing .xtc / .xtch file into the right pane.

[Presets]
- Choose a preset from the combo box and press "Load Preset".
- Press "Save Preset" to overwrite the selected preset with current settings.
- Presets also store the line-rule mode.

[Bottom panel]
- Click an item in the Results tab to load it into the right pane.
- Use the Log tab to inspect conversion details.

[Display settings]
- Use the gear menu to switch between Light and Dark themes.
- The same menu can show or hide the hamburger button.

[Notes]
- The Stop button is enabled only during conversion.
- Existing-file behavior is available from Gear > Other Options > Existing File.
- After conversion, the Results tab shows a summary of saved files and errors.
"""

USAGE_HELP_TEXT_JA = """\
【基本的な流れ】
1. 上部の「ファイルを開く」で変換対象を選び、「保存先を選ぶ」で保存先を選びます。
2. 複数ファイルをまとめて変換するときは「フォルダ一括変換」を使います。
3. 左側の設定を調整します。
4. 必要に応じて上部の「プレビュー更新」で手動再描画します。
5. 右側のフォントビューで文字の見え方を確認します。
6. 「▶ 変換実行」を押すと .xtc / .xtch を保存します。
7. 変換後は右ペインで XTC / XTCH を確認できます。

【プレビュー】
・右ペイン: 設定中の文字の見え方を確認します。XTCファイルを開くと、同じ場所でページ送りしながら確認できます。
・ページ送りは右ペインの「前/次」ボタン、またはページ番号入力で行います。
・歯車メニューの「ページ送りキー反転」を ON にすると、前/次 ボタンの左右配置と動作感を入れ替えられます。

【右ペイン表示ツールバー】
・「実寸近似」は PC 画面上の実機サイズに近い表示へ切り替えます。
・実寸近似 ON 中は、右ペイン倍率のラベルが「実寸補正」に変わります。
・実寸補正は、定規で実物と比較しながら右ペイン側で調整してください。
・「ガイド」は余白・非描画域の補助線を表示します。

【左ペインの出力・機種設定】
・機種選択は「出力・フォント・組版」内の出力形式付近にあります。
・機種を選ぶと解像度が自動設定されます（Custom では手動指定）。

【ファイルビューワー】
・「XTCファイルを開く」から既存の .xtc / .xtch ファイルを右ペインへ読み込めます。

【プリセット】
・コンボボックスで選択し「プリセット読込」で呼び出します。
・「プリセット保存」で現在の設定を上書きします。
・プリセットには禁則処理モードも保存されます。

【下部パネル】
・「変換結果」タブでファイルをクリックすると右ペインへ読み込みます。
・「ログ」タブで変換の詳細を確認できます。

【表示設定】
・右上の歯車から、白基調 / ダーク の切替ができます。
・同じ画面で、三本線ボタンの表示 / 非表示も切り替えられます。

【補足】
・停止ボタンは変換中のみ有効です。
・同名ファイルがある場合の動作は、右上の歯車メニュー内「その他オプション > 同名出力」で選べます。
・変換後は「変換結果」タブの先頭に保存件数やエラー件数の概要を表示します。
"""


def usage_help_text(language: object) -> str:
    """Return the main help dialog body for the requested UI language."""
    if str(language).strip().lower() == 'en':
        return USAGE_HELP_TEXT_EN
    return USAGE_HELP_TEXT_JA
