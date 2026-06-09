from __future__ import annotations

"""Pure helpers for the GUI layer.

This module keeps presentation and small orchestration decisions out of
MainWindow so they can be tested without a live Qt runtime.
"""

import html
import ntpath
import os
import re
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path
import math
from typing import Any


LOWER_CLOSING_BRACKET_POSITION_MODES: dict[str, str] = {
    'down_strong': '下補正強',
    'down_weak': '下補正弱',
    'standard': '標準',
    'up_weak': '上補正弱',
    'up_strong': '上補正強',
}
WAVE_DASH_DRAWING_MODES: dict[str, str] = {
    'rotate': '回転グリフ',
    'separate': '別描画',
}
WAVE_DASH_POSITION_MODES: dict[str, str] = {
    'standard': '標準',
    'down_weak': '下補正弱',
    'down_strong': '下補正強',
}
TATECHUYOKO_DIGIT_MODES: dict[str, str] = {
    '4': '4文字',
    '3': '3文字',
    '2': '2文字',
    'none': '無し',
}
PROGRESS_BAR_POSITIONS: dict[str, str] = {
    'center': '下中央',
    'left': '下左',
}


UI_LANGUAGES: dict[str, str] = {
    'ja': '日本語',
    'en': 'English',
}


def normalize_ui_language(value: object, default: str = 'ja') -> str:
    normalized = str(value if value is not None else default).strip().lower()
    compact = normalized.replace('_', '-').split('-', 1)[0]
    aliases = {
        'ja': {'ja', 'jp', 'japanese', '日本語'},
        'en': {'en', 'english', '英語'},
    }
    for key, values in aliases.items():
        if normalized in values or compact in values:
            return key
    return normalized if normalized in UI_LANGUAGES else str(default if default in UI_LANGUAGES else 'ja')


def build_language_restart_notice(language: object = 'ja') -> dict[str, str]:
    """Return restart guidance in the language the user just selected.

    Language switching is applied on the next launch, so the one-time notice
    must be understandable even when the current UI was still built in another
    language.  This helper intentionally formats the notice in the target
    language, not in the language that was active before the combo change.
    """
    normalized = normalize_ui_language(language, 'ja')
    if normalized == 'en':
        note = 'Please restart the app to apply the language change.'
        return {
            'title': 'Restart required',
            'message': note,
            'status': f'Language saved as {UI_LANGUAGES[normalized]}. {note}',
            'note': note,
        }
    note = '表示言語の変更は次回起動時に反映されます。'
    return {
        'title': '再起動が必要です',
        'message': note,
        'status': f'表示言語を {UI_LANGUAGES[normalized]} に保存しました。{note}',
        'note': note,
    }



UI_TRANSLATIONS_EN: dict[str, str] = {
    '準備完了': 'Ready',
    'ファイルを開く': 'Open File',
    '1つのファイルを開いて変換します': 'Open one file for conversion.',
    'XTC/XTCHを開く': 'Open XTC/XTCH',
    '既存の .xtc / .xtch ファイルを右ペインで確認します': 'Open an existing .xtc / .xtch file in the right pane.',
    '既存の .xtc / .xtch ファイルを右ペインへ読み込んで確認します。': 'Load an existing .xtc / .xtch file into the right pane for preview.',
    '保存先を選ぶ': 'Save To...',
    '変換後のXTC / XTCH の保存先を選びます': 'Choose the destination folder for converted XTC / XTCH files.',
    '保存先指定を解除し、ソースファイルと同じフォルダへ戻します': 'Clear the custom destination and return to the source folder.',
    '保存先リセット': 'Reset Folder',
    'フォルダ一括変換': 'Batch Convert',
    'フォルダ内の複数ファイルをまとめて変換します': 'Convert multiple files in a folder.',
    '変換対象のファイル / フォルダ（ここへドロップ可）': 'Source file / folder (drop here)',
    '変換対象のファイルまたはフォルダを入力します。ソースファイルはここへドラッグ＆ドロップできます。': 'Enter or drop the source file/folder to convert.',
    '▶  変換実行': '▶  Convert',
    '■  停止': '■  Stop',
    '左パネルの表示/非表示': 'Show/hide the left panel',
    '使い方の流れ': 'How to use',
    '表示設定': 'Display settings',
    '外観': 'Appearance',
    '上部ボタンの使い分け': 'Top button guide',
    '出力先': 'Output',
    '組版': 'Typesetting',
    '位置補正': 'Position',
    '表示言語 / Language': 'Language',
    'プリセット': 'Presets',
    'その他オプション': 'Other Options',
    'ファイルビューワー': 'File Viewer',
    '表示言語': 'Language',
    'Japanese': 'Japanese',
    'UI表示言語を選びます。変更は次回起動時に反映されます。': 'Choose the UI language. Changes apply after restart.',
    '変更は次回起動時に反映されます。': 'Changes apply after restart.',
    '参照': 'Browse',
    '参照...': 'Browse...',
    '機種': 'Device',
    '出力形式': 'Output Format',
    '幅': 'Width',
    '高さ': 'Height',
    '本文': 'Body',
    'ルビ': 'Ruby',
    '行間': 'Line Spacing',
    '上余白': 'Top Margin',
    '下余白': 'Bottom Margin',
    '左余白': 'Left Margin',
    '右余白': 'Right Margin',
    '縦中横': 'Tate-chu-yoko',
    '禁則処理': 'Line Rules',
    'ページ番号': 'Page No.',
    'サイズ': 'Size',
    '進捗バー': 'Progress Bar',
    '位置': 'Position',
    'ルビ消し': 'Hide Ruby',
    '白黒反転': 'Invert B/W',
    'ディザリング': 'Dithering',
    'しきい値': 'Threshold',
    '実寸近似': 'Actual Size',
    'ガイド': 'Guides',
    '実寸補正': 'Actual Size Adj.',
    '更新対象': 'Preview Pages',
    'ページ': 'Page',
    'プレビュー更新': 'Refresh Preview',
    '完了後フォルダを開く': 'Open folder after convert',
    '同名出力': 'Existing File',
    '前': 'Prev',
    '次': 'Next',
    'ページ送りキー反転': 'Reverse page keys',
    '表示中: なし': 'Viewing: none',
    '待機中': 'Idle',
    '変換結果': 'Results',
    'ログ': 'Log',
    '変換結果の概要をここに表示します。': 'Conversion summary will appear here.',
    '保存先:': 'Folder:',
    'ログフォルダを開く': 'Open Log Folder',
    '保存先を開く': 'Open Save Folder',
    '右ペインで確認': 'Preview on Right',
    '選択中、または先頭の変換結果が保存されたフォルダを開きます。': 'Open the folder for the selected or first conversion result.',
    '選択中、または先頭の変換結果を右ペインへ読み込みます。': 'Load the selected or first conversion result into the right pane.',
    '変換完了': 'Conversion Complete',
    '閉じる': 'Close',
    '句読点': 'Punctuation',
    '漢数字 一': 'Kanji numeral 一',
    '半角数字/記号': 'Numbers/Symbols',
    '半角英字': 'Letters',
    '縦中横記号': 'TCY Symbols',
    '下鍵括弧': 'Closing Quote',
    '波線描画': 'Wave Dash',
    '波線位置': 'Wave Position',
    '縦書きXTC Studio': 'TategakiXTC GUI Studio',
    'プリセット\n読み込み': 'Load\nPreset',
    'プリセット\n保存': 'Save\nPreset',
    '名称変更': 'Rename',
    '選択中のプリセットを現在の組版へ読み込みます': 'Load the selected preset into the current settings.',
    '現在の組版設定をこのプリセットへ保存します': 'Save current settings to this preset.',
    '選択中のプリセットの表示名を変更します': 'Rename the selected preset.',
    '右ペイン': 'Right Pane',
    'フォントビュー': 'Font View',
    '表示倍率': 'Zoom',
    '表示倍率を下げます。': 'Zoom out.',
    '表示倍率を上げます。': 'Zoom in.',
    '右ペイン表示の表示倍率です。': 'Zoom level for the right pane.',
    '右ペイン表示の表示倍率です。実寸近似ONでは実寸補正として使います。': 'Zoom level for the right pane. With Actual Size enabled, it works as actual-size adjustment.',
    '右ペイン: プレビュー生成後の見え方を確認します。\nXTC/XTCHを開くと、同じ右ペインでページ送りしながら確認できます。': 'Right Pane: check how the preview looks after generation.\nWhen you open an XTC/XTCH file, you can page through it in the same right pane.',
    '実寸近似: PC画面上の表示サイズを、選択中の機種の実物サイズに近づける表示モードです。\n端末に表示したときのおおよその大きさを確認したい場合に使います。\nONにすると右ペインの倍率欄は「実寸補正」に切り替わります。\n表示が実物より大きい/小さい場合は、この実寸補正を調整してください。\nOFFでは右ペイン倍率は通常の表示ズームとして働きます。': 'Actual Size: approximates the selected device\'s physical display size on your PC screen.\nUse this when you want to roughly check how large the page will look on the device.\nWhen enabled, the right-pane zoom control becomes Actual Size Adjustment.\nIf the preview looks larger or smaller than the real device, adjust that value.\nWhen disabled, the right-pane zoom works as normal display zoom.',
    'ガイド: 右ペインのプレビューに、余白や非描画域の目安線を重ねて表示します。\n本文が端に寄りすぎていないか、余白設定が意図通りかを確認するときに使います。\nONにすると補助線を表示し、OFFにすると実際の見た目に近い状態で確認できます。\n変換結果そのものを書き換える機能ではなく、確認用の表示補助です。': 'Guides: overlays margin and non-drawing-area guide lines on the right-pane preview.\nUse this to check whether the text is too close to the edges and whether margins look as intended.\nTurn it on to show guide lines, or off to see a view closer to the actual output.\nThis is only a preview aid; it does not change the converted file.',
    '実寸補正は右ペインの倍率UIで調整します。': 'Adjust actual-size scaling with the zoom control in the right pane.',

    # v1.4.2.3: combo-box choices and frequently used help/tooltips.
    'オフ': 'Off',
    '簡易': 'Simple',
    '標準': 'Standard',
    '4文字': '4 chars',
    '3文字': '3 chars',
    '2文字': '2 chars',
    '無し': 'None',
    '下中央': 'Bottom center',
    '下左': 'Bottom left',
    '上補正強': 'Up strong',
    '上補正弱': 'Up weak',
    '下補正弱': 'Down weak',
    '下補正強': 'Down strong',
    '回転グリフ': 'Rotated',
    '別描画': 'Separate',
    '自動連番で保存': 'Auto-number',
    '同名なら上書き': 'Overwrite',
    '同名ならエラー': 'Error',
    '白基調': 'Light',
    'ダーク': 'Dark',
    'その他オプション': 'Other Options',
    '三本線ボタンを表示': 'Show menu button',
    '機種: 選ぶと解像度が自動設定されます。\nCustom: 手動で幅・高さを指定します。': 'Device: selecting a device sets the resolution automatically.\nCustom: set width and height manually.',
    'XTC: 2 階調（白黒）で保存します。\nXTCH: 4 階調（白黒 4 段階）で保存します。\n使い分け: 通常の白黒表示なら XTC、階調を残したい画像寄りの用途では XTCH を選びます。': 'XTC: save in 2 levels (black and white).\nXTCH: save in 4 grayscale levels.\nUse XTC for normal black-and-white text, and XTCH when you want to preserve more tone for image-like content.',
    '半角数字を1文字分に横組みする上限です。\n4文字: 4桁までを縦中横にします。\n3文字: 3桁までを縦中横にします。\n2文字: 2桁までを縦中横にします。\n無し: 半角数字を縦中横にしません。': 'Sets the maximum number of half-width digits grouped into one vertical-text cell.\n4 chars: group up to 4 digits.\n3 chars: group up to 3 digits.\n2 chars: group up to 2 digits.\nNone: do not group half-width digits.',
    'オフ: 禁則処理を行わず機械的に流し込みます。\n簡易: 行頭禁則・行末禁則・句読点のぶら下げのみ行います。\n標準: 連続約物や閉じ括弧＋句読点のまとまりも含めて、現在の禁則処理を有効にします。': 'Off: lay out text mechanically without line-breaking rules.\nSimple: apply basic start/end-of-line rules and hanging punctuation.\nStandard: also keeps grouped punctuation and closing quote + punctuation clusters together.',
    'ページ番号: チェックすると各ページ右下に「現在ページ/総ページ」を表示します。\nサイズ: 1〜29 の数値を指定します。30以上はエラーです。\nページ番号ON時は、下余白を「サイズ+1」以上に自動確保します。': 'Page Number: show current/total page numbers at the lower right.\nSize: choose a value from 1 to 29. 30 or higher is rejected.\nWhen enabled, the bottom margin is automatically kept at least size + 1.',
    '進捗バー: チェックすると下部に読書位置を示す黒い横棒を表示します。\n位置: 下中央または下左を選べます。\n進捗バーON時は、下余白を最低10px程度に自動確保します。': 'Progress Bar: show a black reading-progress bar at the bottom.\nPosition: choose bottom center or bottom left.\nWhen enabled, the bottom margin is automatically kept around at least 10 px.',
    'ルビ消し: チェックした場合だけ、親文字は残したままルビを表示しない変換モードにします。\n白黒反転: 白と黒を入れ替えて出力します。プレビューにも反映されます。\nディザリング: 粒状感と引き換えに濃淡感を残します。\nしきい値: 白と黒の分かれ目を調整します。': 'Hide Ruby: hide ruby text while keeping the base text.\nInvert B/W: swap black and white in output and preview.\nDithering: preserves tonal detail with a grainy look.\nThreshold: adjust the black/white cutoff.',
    '対象: ぶら下がり句読点のみです。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。': 'Target: hanging punctuation only.\nMove down strong/weak: shift below the standard position.\nStandard: use the existing position.\nMove up weak/strong: shift above the standard position.',
    '対象: 文中すべての漢数字「一」です。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。': 'Target: all kanji numeral 一 in the text.\nMove down strong/weak: shift below the standard position.\nStandard: use the existing position.\nMove up weak/strong: shift above the standard position.',
    '対象: 半角数字と半角記号ペアの縦中横です。\nルビ内数字や全角数字には適用しません。\n下補正強/弱: 標準より下へ寄せます。\n上補正弱/強: 標準より上へ寄せます。': 'Target: tate-chu-yoko for half-width numbers and half-width punctuation pairs.\nDoes not apply to digits inside ruby or full-width digits.\nMove down/up modes shift from the standard position.',
    '対象: 半角英字です。\n下補正強/弱: 標準より下へ寄せます。\n上補正弱/強: 標準より上へ寄せます。': 'Target: half-width letters.\nMove down strong/weak: shift below the standard position.\nMove up weak/strong: shift above the standard position.',
    '対象: 全角/半角の！？、？？、！！、？！など、記号ペアの縦中横です。\n数字の縦中横には適用しません。\n下補正強/弱: 標準より下へ寄せます。\n上補正弱/強: 標準より上へ寄せます。': 'Target: tate-chu-yoko punctuation pairs such as !?, ??, !!, and ?!, including full-width and half-width variants.\nDoes not apply to numeric tate-chu-yoko.\nMove down/up modes shift from the standard position.',
    '対象: 下鍵括弧（﹂ / ﹄）です。\n標準: これまでの位置です。\n下補正弱/強: 標準より下へ寄せます。': 'Target: lower closing quotes (﹂ / ﹄).\nStandard: use the existing position.\nMove down weak/strong: shift below the standard position.',
    '対象: 波線系記号の描画方式です。\n回転グリフ: フォントのグリフを回転します。\n別描画: 線として描画します。': 'Target: drawing method for wave-dash-like marks.\nRotated glyph: rotate the font glyph.\nDraw separately: draw it as a line.',
    '対象: 波線系記号の縦位置だけを補正します。\n標準: これまでの位置です。\n下補正弱/強: 標準より下へ寄せます。': 'Target: vertical position of wave-dash-like marks.\nStandard: use the existing position.\nMove down weak/strong: shift below the standard position.',
    '保存先に同名の .xtc / .xtch があるときの動作を選びます。\n自動連番: foo(1).xtc 形式で保存します。\n上書き: 既存ファイルを置き換えます。\nエラー: そのファイルを保存せずエラーとして記録します。': 'Choose what to do when the destination already has the same .xtc / .xtch filename.\nAuto-number: save as foo(1).xtc.\nOverwrite: replace the existing file.\nError: skip that file and record it as an error.',
    'ファイル読込時: プレビューを自動生成します。\n設定変更後: 更新対象が20ページ以下なら自動更新します。21ページ以上では自動更新せず、「プレビュー更新が必要です」と表示し、［プレビュー更新］を押した時点で再生成します。\n更新対象: プレビュー上限を増やすほど確認範囲は広がりますが、読込と再描画は重くなります。': 'When loading a file: preview is generated automatically.\nAfter changing settings: if the preview target is 20 pages or fewer, it updates automatically. For 21 pages or more, it waits and shows that a preview refresh is needed.\nPreview Pages: increasing the limit widens the preview range, but loading and redrawing become heavier.',

    '対象: 文中の半角数字、数値記号（/ . , : ; + - = % など）、縦中横の半角数字です。\n全角数字とルビ内数字は対象外です。\n!! / !? / ?? などの記号ペアは「縦中横記号」で補正します。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。': 'Target: half-width numbers, numeric symbols (/ . , : ; + - = %, etc.), and half-width numeric tate-chu-yoko in the text.\nFull-width digits and digits inside ruby are not affected.\nPunctuation pairs such as !! / !? / ?? are adjusted by Tate-chu-yoko Symbols.\nMove down strong/weak: shift below the standard position.\nStandard: use the existing position.\nMove up weak/strong: shift above the standard position.',
    '対象: 文中の半角英字（A-Z / a-z）です。\n半角数字、数値記号、全角英字、ルビ内英字は対象外です。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。': 'Target: half-width letters (A-Z / a-z) in the text.\nHalf-width digits, numeric symbols, full-width letters, and letters inside ruby are not affected.\nMove down strong/weak: shift below the standard position.\nStandard: use the existing position.\nMove up weak/strong: shift above the standard position.',
    '対象: 縦中横で描画される記号ペア（！？/？？/！！/？！/!?/??/!!/?!）のみです。\n数字の縦中横には影響しません。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。': 'Target: punctuation pairs drawn as tate-chu-yoko only (！？ / ？？ / ！！ / ？！ / !? / ?? / !! / ?!).\nNumeric tate-chu-yoko is not affected.\nMove down strong/weak: shift below the standard position.\nStandard: use the existing position.\nMove up weak/strong: shift above the standard position.',
    '対象: 閉じ鍵括弧（」/﹂）と二重閉じ鍵括弧（』/﹄）のみです。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。': 'Target: closing quotes (」 / ﹂) and double closing quotes (』 / ﹄) only.\nMove down strong/weak: shift below the standard position.\nStandard: use the existing position.\nMove up weak/strong: shift above the standard position.',
    '対象: 波線系記号（～/〜/〰/~ など）の描画方式です。\n回転グリフ: フォントの質感を保って90度回転します。\n別描画: アプリ側で縦波線を描きます。\n自動フォールバック: 回転グリフに失敗した場合は別描画へ切り替えます。': 'Target: drawing method for wave-dash-like marks (～ / 〜 / 〰 / ~, etc.).\nRotated glyph: rotate the font glyph 90 degrees while preserving the font texture.\nDraw separately: draw a vertical wave line in the app.\nAutomatic fallback: if rotated glyph drawing fails, it switches to separate drawing.',
    'ファイル読込時: プレビューを自動生成します。\n設定変更後: 更新対象が20ページ以下なら自動更新します。21ページ以上では自動更新せず、「プレビュー更新が必要です」と表示し、［プレビュー更新］を押した時点で再生成します。\n更新対象: プレビュー上限を増やすほど確認範囲は広がりますが、読込・再描画・メモリ使用量は重くなります。最大9999ページまで指定できます。': 'When loading a file: preview is generated automatically.\nAfter changing settings: if the preview target is 20 pages or fewer, it updates automatically. For 21 pages or more, it waits and shows that a preview refresh is needed.\nPreview Pages: increasing the limit widens the preview range, but loading, redrawing, and memory use become heavier. You can specify up to 9999 pages.',

    # v1.4.2.4: dialog/status/help coverage.
    '説明': 'Help',
    '使い方': 'How to use',
    '使い方ダイアログを開けませんでした。': 'Could not open the help dialog.',
    '前回の作業ファイル': 'Previous work file',
    'ファイル選択エラー': 'File Selection Error',
    'フォルダ選択エラー': 'Folder Selection Error',
    'ライブラリ不足': 'Missing Libraries',
    'フォルダ一括変換はすでに実行中です。': 'Folder batch conversion is already running.',
    'フォルダ一括変換': 'Batch Convert',
    '通常変換の実行中は、フォルダ一括変換を開始できません。現在の変換が終わってからもう一度実行してください。': 'Folder batch conversion cannot start while a normal conversion is running. Try again after the current conversion finishes.',
    '保存先フォルダを選択': 'Choose Save Folder',
    '保存先フォルダの選択ダイアログを開けませんでした。': 'Could not open the save-folder selection dialog.',
    '変換対象を選択': 'Choose Source File',
    '変換対象のファイル選択ダイアログを開けませんでした。': 'Could not open the source-file selection dialog.',
    '変換対象フォルダを選択': 'Choose Source Folder',
    '変換対象フォルダの選択ダイアログを開けませんでした。': 'Could not open the source-folder selection dialog.',
    'フォントファイルを選択': 'Choose Font File',
    'フォントファイル選択ダイアログを開けませんでした。': 'Could not open the font-file selection dialog.',
    '保存先指定を解除しました。\n次回の単体変換は、ソースファイルと同じフォルダへ保存します。': 'The custom save folder was cleared.\nThe next single-file conversion will save next to the source file.',
    '保存先指定を解除しました。次回の単体変換はソースファイルと同じフォルダへ保存します。': 'The custom save folder was cleared. The next single-file conversion will save next to the source file.',
    'ソースファイルと同じフォルダ': 'Same folder as source file',
    '表示設定メニューを開けませんでした。': 'Could not open the display settings menu.',
    'プリセット名称変更': 'Rename Preset',
    '現在選択中のプリセット表示名を変更します。': 'Rename the display name of the selected preset.',
    '既定名:': 'Default name:',
    '既定名に戻す': 'Restore Default Name',
    'キャンセル': 'Cancel',
    '変換停止中': 'Stopping Conversion',
    '変換の停止を待っています。停止完了後にもう一度閉じてください。': 'Waiting for conversion to stop. Please close again after it has stopped.',
    '変換停止中のため終了を保留しました。停止完了後にもう一度閉じてください。': 'Exit was postponed while conversion is stopping. Please close again after it has stopped.',
    '変換エラー': 'Conversion Error',
    '不明なエラー': 'Unknown error',
    'エラー': 'Error',
    'XTC読込エラー': 'XTC Load Error',
    'XTC/XTCH選択ダイアログを開けませんでした。': 'Could not open the XTC/XTCH selection dialog.',
    'ドロップしたファイルを変換対象に設定しました。': 'Dropped file was set as the source.',
    '変換をキャンセルしました。': 'Conversion canceled.',
    '変換中…': 'Converting…',
    '停止要求を受け付けました。現在の変換単位が終わりしだい停止します。': 'Stop request accepted. Conversion will stop after the current item finishes.',
    '停止中': 'Stopping',
    'ログフォルダを開く': 'Open Log Folder',
    'ログフォルダ:': 'Log folder:',
    '出力ファイル名': 'Output Filename',
    '空の名前は使えません。': 'An empty name cannot be used.',
    'プリセット保存': 'Save Preset',
    'プリセット保存の確認ダイアログを表示できませんでした。': 'Could not show the preset-save confirmation dialog.',
    '適用するプリセットが見つかりませんでした。': 'Could not find the preset to apply.',
    'プレビューを生成してください': 'Generate a preview',
    'プレビュー更新を準備しています…': 'Preparing preview update…',
    'プレビューを生成できませんでした': 'Could not generate preview',
    'プレビュー生成エラー': 'Preview generation error',
    'プレビュー表示エラー': 'Preview display error',
    'ページ表示エラー': 'Page display error',
    'ファイルビューワーモード: XTC/XTCHを直接表示中です': 'File viewer mode: directly showing XTC/XTCH',
    'ファイルビューワー表示エラー': 'File viewer display error',
    '出力フォルダを開けませんでした': 'Could not open the output folder',
    '出力フォルダが見つかりません': 'Output folder not found',
    '出力フォルダを開きました': 'Opened output folder',
    'Qt 経由で出力フォルダを開けませんでした': 'Could not open the output folder via Qt',
    '出力フォルダボタン付き完了通知に失敗しました': 'Could not show the completion dialog with an output-folder button',
    'フォルダ一括変換結果一覧の反映に失敗しました': 'Could not reflect folder-batch results in the result list',
    'フォルダ一括変換カードの表示に失敗しました': 'Could not show the folder-batch completion card',
    'フォルダ一括変換を開始しました。': 'Folder batch conversion started.',
    'フォルダ一括変換メニューを追加しました。': 'Added the folder batch conversion menu.',
'出力先': 'Output folder',
'フォルダ一括変換を中止しました。': 'Folder batch stopped.',
'変換を中止しました。': 'Conversion stopped.',
'保存済みファイルはありません。': 'No saved files.',
'停止要求により、以降の未処理ファイルは変換していません。': 'Remaining pending files were not converted because a stop was requested.',
'停止要求により、変換結果は保存されませんでした。': 'No conversion result was saved because a stop was requested.',
'詳細は左下の「変換結果」タブにも記録しています。': 'Details are also recorded in the Results tab at the lower left.',
'詳細は左下の「ログ」タブにも記録しています。': 'Details are also recorded in the Log tab at the lower left.',
'保存先を開く場合は、下の［保存先を開く］を押してください。': 'Use [Open Save Folder] below to open the output folder.',
'出力ファイル:': 'Output files:',
'サブフォルダ構造を保持して保存しました。': 'Saved while preserving the subfolder structure.',
'保存先': 'Save folder',
'基準フォルダ': 'Base folder',
'開ける変換結果がありません。': 'There is no conversion result to open.',
'保存先を開けませんでした。': 'Could not open the save folder.',
'保存先フォルダを特定できませんでした。': 'Could not identify the save folder.',
'確認できる変換結果がありません。': 'There is no conversion result to preview.',
'プリセット名を': 'Preset name changed',
    'フォルダ一括変換メニューの追加をスキップしました': 'Skipped adding the folder batch conversion menu',
    # v1.4.2.11: remaining English UI polish.
    'ファイル表示中': 'File Viewer',
    '生成中…': 'Generating…',
    '更新中…': 'Updating…',
    'ファイルビューワーモードではXTC/XTCHを直接表示しているため、プレビュー更新は不要です。': 'Preview refresh is not needed in file-viewer mode because XTC/XTCH is shown directly.',
    '変換完了カードを閉じます。': 'Close the conversion-complete card.',
    '変換結果が保存されたフォルダを開きます。': 'Open the folder where conversion results were saved.',
    '入力元フォルダを選択': 'Choose Input Folder',
    '出力先フォルダを選択': 'Choose Output Folder',
    '入力元フォルダと出力先フォルダを指定してください。': 'Choose the input folder and output folder.',
    'フォルダ': 'Folders',
    '入力元フォルダ:': 'Input folder:',
    '出力先フォルダ:': 'Output folder:',
    '一括変換オプション': 'Batch Conversion Options',
    'サブフォルダ内も対象にする': 'Include subfolders',
    'フォルダ構造を保持して出力する': 'Preserve folder structure',
    '既存ファイルがある場合:': 'If output file exists:',
    '現在のメイン画面設定で変換します。': 'Use the current main-window settings for conversion.',
    '確認': 'Review',
    '変換開始': 'Start Conversion',
    '変換予定のファイルがないため開始できません。': 'Cannot start because there are no files to convert.',
    'この内容で変換を開始しますか？': 'Start conversion with these settings?',
    '上書き確認': 'Overwrite Confirmation',
    'フォルダ一括変換の確認': 'Confirm Batch Conversion',
    '既存ファイルを上書きする設定です。': 'Existing files will be overwritten.',
    'スキップ': 'Skip',
    '上書き': 'Overwrite',
    '別名で保存': 'Rename',
    '対象形式: なし': 'Target formats: none',
}



def translate_ui_text(text: object, language: object = 'ja') -> str:
    value = str(text if text is not None else '')
    if normalize_ui_language(language, 'ja') != 'en':
        return value
    exact = UI_TRANSLATIONS_EN.get(value)
    if exact is not None:
        return exact
    return _translate_dynamic_ui_text_en(value)


def _translate_dynamic_ui_text_en(value: str) -> str:
    """Translate common dynamic GUI/result/log messages for the English UI.

    Keep this intentionally pattern-based and conservative.  Worker, folder-batch,
    and result helpers produce many count/path messages dynamically; exact
    dictionary lookup cannot cover those without threading language through every
    lower-level converter path.
    """

    text = str(value or '')
    if not text:
        return text
    replacements: tuple[tuple[str, str], ...] = (
        (r'^プレビュー更新が必要です（更新対象 (\d+) ページのため自動更新しません）$', r'Preview refresh needed (auto-refresh skipped because the target is \1 pages)'),
        (r'^プリセット(\d+)$', r'Preset \1'),
        (r'^保存しました:\s*(.+)$', r'Saved: \1'),
        (r'^保存済み:\s*(.+)$', r'Saved: \1'),
        (r'^保存済み:\s*(\d+)件$', r'Saved files: \1'),
        (r'^保存先:\s*複数フォルダ（(\d+)か所）$', r'Save folders: multiple folders (\1)'),
        (r'^保存先:\s*(.+)$', r'Save folder: \1'),
        (r'^出力先:\s*(.+)$', r'Output folder: \1'),
        (r'^基準フォルダ:\s*(.+)$', r'Base folder: \1'),
        (r'^処理済み:\s*(\d+)\s*/\s*(\d+)\s*件$', r'Processed: \1 / \2'),
        (r'^未処理:\s*(\d+)\s*件$', r'Pending: \1'),
        (r'^…ほか(\d+)件$', r'…and \1 more'),
        (r'^保存\s+(\d+)\s+件$', r'Saved files: \1'),
        (r'^自動連番\s+(\d+)\s+件$', r'Auto-numbered: \1'),
        (r'^上書き\s+(\d+)\s+件$', r'Overwritten: \1'),
        (r'^スキップ\s+(\d+)\s+件$', r'Skipped: \1'),
        (r'^エラー\s+(\d+)\s+件$', r'Errors: \1'),
        (r'^警告:\s*(.+)$', r'Warning: \1'),
        (r'^保存:\s*(.+)$', r'Saved: \1'),
        (r'^スキップ:\s*(.+)$', r'Skipped: \1'),
        (r'^\[(\d+)/(\d+)\]\s*変換中:\s*(.+)$', r'[\1/\2] Converting: \3'),
        (r'^同名あり\s*→\s*自動連番で保存:\s*(.+?)\s*->\s*(.+)$', r'Same name exists -> auto-numbered: \1 -> \2'),
        (r'^同名あり\s*→\s*上書き保存:\s*(.+)$', r'Same name exists -> overwritten: \1'),
        (r'^完了後フォルダの対象を特定できませんでした:\s*(.+)$', r'Could not identify the folder to open after conversion: \1'),
        (r'^完了後フォルダを開けませんでした。\s*/\s*対象:\s*(.+)$', r'Could not open the folder after conversion. / Target: \1'),
        (r'^変換結果表示エラー:\s*(.+)$', r'Conversion result display error: \1'),
        (r'^完了表示エラー:\s*(.+)$', r'Completion display error: \1'),
        (r'^XTC/XTCH読込:\s*(.+)$', r'XTC/XTCH loaded: \1'),
        (r'^XTC/XTCH読込失敗:\s*(.+)$', r'XTC/XTCH load failed: \1'),
        (r'^フォルダ一括変換中…\s*0/(\d+)\s*件｜準備中$', r'Batch converting… 0/\1 | Preparing'),
        (r'^フォルダ一括変換中…\s*(\d+)/(\d+)\s*件目｜(.+)$', r'Batch converting… \1/\2 | \3'),
        (r'^フォルダ一括変換中…\s*(\d+)/(\d+)\s*件目$', r'Batch converting… \1/\2'),
        (r'^内部\s*(\d+)/(\d+)$', r'Inner \1/\2'),
        (r'^フォルダ一括変換を停止しました。成功\s*(\d+)\s*/\s*スキップ\s*(\d+)\s*/\s*失敗\s*(\d+)\s*/\s*処理済み\s*(\d+)/(\d+)\s*/\s*未処理\s*(\d+)$', r'Folder batch stopped. Success \1 / Skipped \2 / Failed \3 / Processed \4/\5 / Pending \6'),
        (r'^フォルダ一括変換が完了しました。成功\s*(\d+)\s*/\s*スキップ\s*(\d+)\s*/\s*失敗\s*(\d+)\s*/\s*処理済み\s*(\d+)/(\d+)$', r'Folder batch complete. Success \1 / Skipped \2 / Failed \3 / Processed \4/\5'),
        (r'^対象形式:\s*(.+)$', r'Target formats: \1'),
        (r'^変換対象:\s*(\d+)\s*件$', r'Files to convert: \1'),
        (r'^変換予定:\s*(\d+)\s*件$', r'Will convert: \1'),
        (r'^スキップ予定:\s*(\d+)\s*件$', r'Will skip: \1'),
        (r'^出力先:\s*(.+)$', r'Output folder: \1'),
        (r'^既存ファイルの扱い:\s*スキップ$', r'Existing files: Skip'),
        (r'^既存ファイルの扱い:\s*上書き$', r'Existing files: Overwrite'),
        (r'^既存ファイルの扱い:\s*別名で保存$', r'Existing files: Rename'),
        (r'^既存ファイルによるスキップ:\s*(\d+)\s*件$', r'Skipped because file exists: \1'),
        (r'^同名衝突によるスキップ:\s*(\d+)\s*件$', r'Skipped due to same-name conflict: \1'),
        (r'^別名保存予定:\s*(\d+)\s*件$', r'Will rename: \1'),
        (r'^上書き予定:\s*(\d+)\s*件$', r'Will overwrite: \1'),
        (r'^入力元フォルダが見つかりません:\s*(.+)$', r'Input folder not found: \1'),
        (r'^入力元はフォルダを指定してください:\s*(.+)$', r'Input must be a folder: \1'),
        (r'^対象ファイルはありますが、(.+)によりすべてスキップされます。$', r'Target files exist, but all will be skipped due to \1.'),
        (r'^前回設定の保存に失敗しました。変換は続行します:\s*(.+)$', r'Could not save the previous settings. Conversion will continue: \1'),
        (r'^フォルダ一括変換を実行できませんでした:\s*(.+)$', r'Could not run folder batch conversion: \1'),
    )
    for pattern, replacement in replacements:
        if re.search(pattern, text):
            return re.sub(pattern, replacement, text)
    conversion_patterns: tuple[tuple[str, str], ...] = (
        (r'^変換を停止しました。\((\d+)\s*件を保存\s*/\s*(\d+)\s*件エラー\)$', r'Conversion stopped. (\1 saved / \2 errors)'),
        (r'^変換完了しました。\((\d+)\s*件を保存\s*/\s*(\d+)\s*件エラー\)$', r'Conversion complete. (\1 saved / \2 errors)'),
        (r'^変換できませんでした。\((\d+)\s*件エラー\)$', r'Conversion failed. (\1 errors)'),
        (r'^変換対象はありませんでした。\((\d+)\s*件スキップ\)$', r'No conversion targets. (\1 skipped)'),
        (r'^変換完了しました。\((\d+)\s*件\)$', r'Conversion complete. (\1 files)'),
    )
    for pattern, replacement in conversion_patterns:
        if re.search(pattern, text):
            return re.sub(pattern, replacement, text)
    simple = {
        '途中停止': 'Stopped',
        'プレビュー更新が必要です': 'Preview refresh needed',
        'ダイアログを開けませんでした': 'Could not open the dialog',
        '変換条件を取得できませんでした。': 'Could not get conversion settings.',
        '変換計画を取得できませんでした。': 'Could not get the conversion plan.',
        '変換を開始します。': 'Starting conversion.',
        '保存が完了しました。': 'Save complete.',
        '停止要求を受け付けました。': 'Stop request accepted.',
        '停止しました。': 'Stopped.',
        '変換中': 'Converting',
        '完了': 'Complete',
        '停止': 'Stopped',
        '中止中': 'Stopping',
        '一括変換中…': 'Batch converting…',
        '一括変換中': 'Batch converting',
        'フォルダ一括変換中…': 'Batch converting…',
        'フォルダ一括変換が終了しました。': 'Folder batch finished.',
        'フォルダ一括変換を完了できませんでした。': 'Folder batch conversion could not be completed.',
        'フォルダ一括変換を中止しました': 'Folder batch stopped',
        'フォルダ一括変換が完了しました': 'Folder batch complete',
        'フォルダ一括変換が完了しました（失敗あり）': 'Folder batch complete (with failures)',
        '出力フォルダを開く': 'Open Output Folder',
        'スキップ': 'Skip',
        '上書き': 'Overwrite',
        '別名で保存': 'Rename',
        '変換対象ファイルが見つかりません。': 'No files to convert were found.',
        '入力元フォルダ、サブフォルダ設定、対象ファイル形式を確認してください。': 'Check the input folder, subfolder setting, and target file formats.',
        '対象ファイルはありますが、すべて既存ファイル扱いによりスキップされます。': 'Target files exist, but all will be skipped because output files already exist.',
        '変換したい場合は「既存ファイルがある場合」を「上書き」または「別名で保存」に変更してください。': 'To convert them, change existing-file handling to Overwrite or Rename.',
        '対象ファイルはありますが、出力先の同名衝突によりすべてスキップされます。': 'Target files exist, but all will be skipped because of same-name conflicts in the output folder.',
        '「フォルダ構造を保持して出力する」をオンにするか、「既存ファイルがある場合」を「別名で保存」に変更してください。': 'Turn on Preserve folder structure, or change existing-file handling to Rename.',
        '既存ファイル': 'existing files',
        '同名衝突': 'same-name conflicts',
        '既存ファイルまたは同名衝突により': 'because of existing files or same-name conflicts',
        '既存ファイルがあるため': 'because output files already exist',
        '出力先の同名衝突により': 'because of same-name conflicts in the output folder',
        '入力元フォルダが未指定です。': 'Input folder is not specified.',
        '出力先フォルダが未指定です。': 'Output folder is not specified.',
        '入力元フォルダと出力先フォルダが同じです。変換後ファイルが入力元側に混在します。': 'The input folder and output folder are the same. Converted files will be mixed into the input folder.',
        '出力先フォルダが入力元フォルダの配下です。再実行時の混在に注意してください。': 'The output folder is inside the input folder. Be careful about mixed files when running again.',
        '入力元フォルダが出力先フォルダの配下です。出力先の管理単位に注意してください。': 'The input folder is inside the output folder. Check how the output folder is organized.',
        '変換条件を確認してください。': 'Check the conversion settings.',
    }
    return simple.get(text, text)


def translate_ui_structure(value: object, language: object = 'ja') -> object:
    if normalize_ui_language(language, 'ja') != 'en':
        return value
    if isinstance(value, str):
        return translate_ui_text(value, language)
    if isinstance(value, tuple):
        return tuple(translate_ui_structure(item, language) for item in value)
    if isinstance(value, list):
        return [translate_ui_structure(item, language) for item in value]
    if isinstance(value, dict):
        return {key: translate_ui_structure(item, language) for key, item in value.items()}
    return value

def _is_english_ui(language: object) -> bool:
    return normalize_ui_language(language, 'ja') == 'en'


def _yes_no_text(value: object, language: object = 'ja') -> str:
    if _is_english_ui(language):
        return 'On' if _config_bool_value(value, False) else 'Off'
    return 'あり' if _config_bool_value(value, False) else 'なし'


def _localized_mode_label(label: object, language: object = 'ja') -> str:
    return translate_ui_text(str(label or ''), language)

def normalize_progress_bar_position(value: object, default: str = 'center') -> str:
    normalized = str(value if value is not None else default).strip().lower()
    aliases = {
        'center': {'center', 'centre', 'middle', 'bottom_center', 'bottom-centre', '下中央', '中央'},
        'left': {'left', 'bottom_left', 'bottom-left', '下左', '左'},
    }
    for key, values in aliases.items():
        if normalized in values:
            return key
    return normalized if normalized in PROGRESS_BAR_POSITIONS else str(default if default in PROGRESS_BAR_POSITIONS else 'center')


def normalize_tatechuyoko_digit_mode(value: object, default: str = '2') -> str:
    normalized = str(value if value is not None else default).strip().lower()
    compact = normalized.replace(' ', '').replace('　', '').replace('-', '_')
    aliases = {
        '4': {'4', '4文字', '4桁', 'four', 'max4'},
        '3': {'3', '3文字', '3桁', 'three', 'max3'},
        '2': {'2', '2文字', '2桁', 'two', 'max2'},
        'none': {'none', 'no', 'off', '0', '無し', 'なし', '無効'},
    }
    for key, values in aliases.items():
        if compact in values:
            return key
    return compact if compact in TATECHUYOKO_DIGIT_MODES else str(default)


def build_top_status_message(
    target_raw: str,
    profile_name: str,
    font_size: int,
    line_spacing: int,
    language: object = 'ja',
) -> str:
    target = str(target_raw).strip()
    english = _is_english_ui(language)
    if not target:
        return 'Choose a source file or folder.' if english else '変換対象を選択してください。'
    # ステータス表示はファイル指定直後にも呼ばれるため、Path.is_dir()
    # などの実ファイルシステム確認を行わない。EPUB/ネットワークパスや
    # 大容量フォルダ指定時に、表示更新だけで UI が詰まることを避ける。
    path = Path(target)
    suffix = path.suffix.lower()
    file_like_suffixes = {
        '.epub', '.zip', '.rar', '.cbz', '.cbr',
        '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
        '.xtc', '.xtch',
    }
    if english:
        kind = 'File' if suffix in file_like_suffixes else 'Folder'
        return f'{kind}: {path.name}  |  {profile_name} / Body {font_size} / Line Spacing {line_spacing}'
    kind = 'ファイル' if suffix in file_like_suffixes else 'フォルダ'
    return f'{kind}: {path.name}  |  {profile_name} / 本文{font_size} / 行間{line_spacing}'


def should_prompt_for_output_name(supported_target_count: int, is_file_target: bool) -> bool:
    return is_file_target and supported_target_count == 1


def suggest_output_name(last_output_name: str, default_output_name: str) -> str:
    current = str(last_output_name).strip()
    if current:
        return current
    fallback = str(default_output_name).strip()
    return fallback or 'output'


def suggest_output_name_for_target(
    last_output_name: str,
    default_output_name: str,
    *,
    target_path: object = '',
    last_output_source: object = '',
) -> str:
    """Return the prompt default for a single-file conversion target.

    Older builds reused ``last_output_name`` unconditionally.  That made a
    previous EPUB conversion name appear again when the user converted a
    different TXT file.  Reuse the saved name only when it belongs to the
    same source target; otherwise prefer the current file-derived default.
    """
    fallback = str(default_output_name).strip() or 'output'
    current = str(last_output_name).strip()
    if not current:
        return fallback
    target_key = _normalize_path_identity(target_path)
    source_key = _normalize_path_identity(last_output_source)
    if target_key and source_key and target_key == source_key:
        return current
    return fallback


def _normalize_path_identity(value: object) -> str:
    text = str(value or '').strip().strip("\"'")
    if not text:
        return ''
    try:
        return str(Path(text).expanduser().resolve(strict=False)).casefold()
    except Exception:
        return text.replace('\\', '/').casefold()


def build_running_results_summary(language: object = 'ja') -> str:
    if _is_english_ui(language):
        return 'Converting. Saved and error counts will appear after completion.'
    return '変換中です。完了後に保存件数とエラー件数を表示します。'


def build_start_log_message(output_format: str, target_count: int, language: object = 'ja') -> str:
    fmt = str(output_format).strip().lower() or 'xtch'
    if _is_english_ui(language):
        if target_count <= 1:
            return f'Conversion started. ({fmt})'
        return f'Conversion started. ({fmt}, {target_count} files)'
    if target_count <= 1:
        return f'変換を開始しました。({fmt})'
    return f'変換を開始しました。({fmt}, {target_count}件)'



def _config_bool_value(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    normalized = str(value).strip().lower()
    if normalized in {'1', 'true', 'yes', 'on'}:
        return True
    if normalized in {'0', 'false', 'no', 'off', ''}:
        return False
    return default


def _config_int_value(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _coerce_mapping_payload(payload: object) -> dict[str, object]:
    return dict(payload) if isinstance(payload, Mapping) else {}



def normalize_choice_value(value: object, default: str, allowed_values: Collection[str] | Mapping[str, object]) -> str:
    normalized = str(value if value not in (None, '') else default).strip().lower()
    compact = _compact_choice_key(normalized)
    allowed = {str(item).strip().lower() for item in allowed_values}
    allowed_compact = {_compact_choice_key(item): item for item in allowed}
    if normalized in allowed:
        return normalized
    if compact in allowed_compact:
        return allowed_compact[compact]
    glyph_aliases = {
        'down_strong': {
            'down_strong', 'strong_down', 'plus', 'positive', 'adjusted', 'mode2', '+',
            'プラス', 'プラス補正', '下', '下補正', '下補正強', '下強', '強下', '補正',
        },
        'down_weak': {'down_weak', 'weak_down', '下補正弱', '下弱', '弱下'},
        'up_weak': {'up_weak', 'weak_up', '上補正弱', '上弱', '弱上'},
        'up_strong': {
            'up_strong', 'strong_up', 'minus', 'negative', '-',
            'マイナス', 'マイナス補正', '上', '上補正', '上補正強', '上強', '強上',
        },
    }
    for canonical, aliases in glyph_aliases.items():
        if compact in aliases:
            if canonical in allowed:
                return canonical
            if canonical == 'down_strong' and 'plus' in allowed:
                return 'plus'
            if canonical == 'up_strong' and 'minus' in allowed:
                return 'minus'
    choice_aliases = {
        'rotate': {
            'rotate', 'rotated', 'rotated_glyph', 'rotatedglyph', 'glyph_rotate', 'glyphrotate',
            'font', 'font_rotate', 'fontrotate', '回転', '回転グリフ', '回転グリフ方式',
            'グリフ回転', 'グリフ回転方式',
        },
        'separate': {
            'separate', 'draw', 'custom', 'app', 'line', 'font_independent', 'fontindependent',
            'separate_drawing', 'separatedrawing', '別描画', '別描画方式', '専用描画',
            'アプリ側描画', '独自描画',
        },
    }
    for canonical, aliases in choice_aliases.items():
        if compact in aliases and canonical in allowed:
            return canonical
    return normalized if normalized in allowed else str(default).strip().lower()


def _compact_choice_key(value: object) -> str:
    return str(value or '').strip().lower().replace(' ', '').replace('　', '').replace('-', '_')


def normalize_wave_dash_drawing_mode(value: object, default: str = 'rotate') -> str:
    normalized = normalize_choice_value(value, default, WAVE_DASH_DRAWING_MODES)
    return normalized if normalized in WAVE_DASH_DRAWING_MODES else 'rotate'


def normalize_wave_dash_position_mode(value: object, default: str = 'standard') -> str:
    normalized = normalize_choice_value(value, default, WAVE_DASH_POSITION_MODES)
    return normalized if normalized in WAVE_DASH_POSITION_MODES else 'standard'


def payload_optional_int_value(payload: Mapping[str, object], key: str) -> int | None:
    if key not in payload:
        return None
    raw = payload.get(key)
    if isinstance(raw, bool):
        return int(raw)
    if isinstance(raw, int):
        return int(raw)
    if isinstance(raw, float):
        return int(raw) if math.isfinite(raw) else None
    if isinstance(raw, (bytes, bytearray)):
        raw = bytes(raw)
        if not raw.strip():
            return None
        try:
            raw = raw.decode('utf-8')
        except Exception:
            return None
    if isinstance(raw, str):
        normalized = raw.strip()
        if not normalized:
            return None
        try:
            return int(normalized, 10)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = float(normalized)
            except (TypeError, ValueError, OverflowError):
                return None
            return int(parsed) if math.isfinite(parsed) else None
    return None


def payload_splitter_sizes_value(
    payload: Mapping[str, object],
    key: str,
    default: Sequence[int],
    *,
    min_top: int = 280,
    min_bottom: int = 92,
) -> list[int]:
    fallback = list(default[:2])
    if len(fallback) < 2:
        fallback = [min_top, min_bottom]
    raw = payload.get(key)
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return fallback
    raw_list = list(raw)
    if len(raw_list) < 2:
        return fallback
    top = payload_optional_int_value({'value': raw_list[0]}, 'value')
    bottom = payload_optional_int_value({'value': raw_list[1]}, 'value')
    return [
        max(min_top, fallback[0] if top is None else top),
        max(min_bottom, fallback[1] if bottom is None else bottom),
    ]


def build_window_state_restore_payload(
    raw_payload: Mapping[str, object],
    *,
    default_width: int,
    default_height: int,
    default_left_panel_width: int,
    default_left_splitter_sizes: Sequence[int],
) -> dict[str, object]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    window_width = payload_optional_int_value(raw_payload, 'window_width')
    window_height = payload_optional_int_value(raw_payload, 'window_height')
    left_panel_width = payload_optional_int_value(raw_payload, 'left_panel_width')
    return {
        'geometry': raw_payload.get('geometry'),
        'window_width': max(1100, default_width if window_width is None else window_width),
        'window_height': max(760, default_height if window_height is None else window_height),
        'is_maximized': _config_bool_value(raw_payload.get('is_maximized'), False),
        'left_panel_width': max(0, default_left_panel_width if left_panel_width is None else left_panel_width),
        'left_splitter_state': raw_payload.get('left_splitter_state'),
        'left_splitter_sizes': payload_splitter_sizes_value(raw_payload, 'left_splitter_sizes', default_left_splitter_sizes),
        'left_panel_visible': _config_bool_value(raw_payload.get('left_panel_visible'), True),
    }

def build_window_state_save_payload(
    raw_payload: Mapping[str, object],
    *,
    min_width: int = 1100,
    min_height: int = 760,
) -> dict[str, object]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    payload: dict[str, object] = {
        'window_width': max(min_width, _config_int_value(raw_payload.get('window_width'), min_width)),
        'window_height': max(min_height, _config_int_value(raw_payload.get('window_height'), min_height)),
        'is_maximized': _config_bool_value(raw_payload.get('is_maximized'), False),
        'left_splitter_state': raw_payload.get('left_splitter_state'),
        'left_panel_visible': _config_bool_value(raw_payload.get('left_panel_visible'), True),
    }
    geometry = raw_payload.get('geometry')
    if geometry is not None:
        payload['geometry'] = geometry
    left_panel_width = payload_optional_int_value(raw_payload, 'left_panel_width')
    if left_panel_width is not None and left_panel_width > 0:
        payload['left_panel_width'] = left_panel_width
    top = payload_optional_int_value(raw_payload, 'left_splitter_top')
    bottom = payload_optional_int_value(raw_payload, 'left_splitter_bottom')
    if top is not None and bottom is not None:
        payload['left_splitter_top'] = top
        payload['left_splitter_bottom'] = bottom
    return payload




def build_settings_restore_payload(
    raw_payload: Mapping[str, object],
    *,
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_profiles: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_glyph_position_modes: Collection[str] | Mapping[str, object] | None = None,
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    if allowed_glyph_position_modes is None:
        allowed_glyph_position_modes = {'down_strong': '下補正強', 'down_weak': '下補正弱', 'standard': '標準', 'up_weak': '上補正弱', 'up_strong': '上補正強'}
    allowed_lower_closing_bracket_position_modes = LOWER_CLOSING_BRACKET_POSITION_MODES
    allowed_wave_dash_drawing_modes = WAVE_DASH_DRAWING_MODES
    allowed_wave_dash_position_modes = WAVE_DASH_POSITION_MODES
    allowed_tatechuyoko_digit_modes = TATECHUYOKO_DIGIT_MODES
    payload: dict[str, Any] = {}
    payload['profile'] = normalize_choice_value(raw_payload.get('profile'), 'x4', allowed_profiles)
    for key, default in (
        ('actual_size', False),
        ('show_guides', True),
        ('nav_buttons_reversed', False),
        ('dither', False),
        ('night_mode', False),
        ('ruby_hide', False),
        ('page_number_enabled', False),
        ('progress_bar_enabled', False),
        ('bottom_overlay_margin_auto_active', False),
        ('page_number_margin_auto_active', False),
        ('open_folder', True),
    ):
        payload[key] = _config_bool_value(raw_payload.get(key), default)
    for key, default in (
        ('calibration_pct', 100),
        ('font_size', 26),
        ('ruby_size', 12),
        ('page_number_font_size', 12),
        ('bottom_overlay_margin_auto_base_value', 14),
        ('bottom_overlay_margin_auto_value', 14),
        ('page_number_margin_auto_base_value', 14),
        ('page_number_margin_auto_value', 14),
        ('line_spacing', 44),
        ('margin_t', 12),
        ('margin_b', 14),
        ('margin_r', 12),
        ('margin_l', 12),
        ('threshold', 128),
        ('width', 480),
        ('height', 800),
        ('bottom_tab_index', 0),
    ):
        payload[key] = _config_int_value(raw_payload.get(key), default)
    payload['preview_page_limit'] = max(1, _config_int_value(raw_payload.get('preview_page_limit'), default_preview_page_limit))
    payload['output_conflict'] = normalize_choice_value(
        raw_payload.get('output_conflict'),
        'rename',
        allowed_output_conflicts,
    )
    payload['output_format'] = normalize_choice_value(
        raw_payload.get('output_format'),
        'xtc',
        allowed_output_formats,
    )
    payload['kinsoku_mode'] = normalize_choice_value(
        raw_payload.get('kinsoku_mode'),
        'standard',
        allowed_kinsoku_modes,
    )
    payload['tatechuyoko_digit_mode'] = normalize_tatechuyoko_digit_mode(
        raw_payload.get('tatechuyoko_digit_mode'),
        '2',
    )
    payload['punctuation_position_mode'] = normalize_choice_value(
        raw_payload.get('punctuation_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['ichi_position_mode'] = normalize_choice_value(
        raw_payload.get('ichi_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['halfwidth_digit_position_mode'] = normalize_choice_value(
        raw_payload.get('halfwidth_digit_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['halfwidth_alpha_position_mode'] = normalize_choice_value(
        raw_payload.get('halfwidth_alpha_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['tatechuyoko_symbol_position_mode'] = normalize_choice_value(
        raw_payload.get('tatechuyoko_symbol_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['lower_closing_bracket_position_mode'] = normalize_choice_value(
        raw_payload.get('lower_closing_bracket_position_mode'),
        'standard',
        allowed_lower_closing_bracket_position_modes,
    )
    payload['wave_dash_drawing_mode'] = normalize_wave_dash_drawing_mode(
        raw_payload.get('wave_dash_drawing_mode'),
    )
    payload['wave_dash_position_mode'] = normalize_wave_dash_position_mode(
        raw_payload.get('wave_dash_position_mode'),
    )
    payload['target'] = str(raw_payload.get('target') or '').strip()
    payload['output_dir'] = str(raw_payload.get('output_dir') or '').strip()
    payload['font_file'] = str(raw_payload.get('font_file') or '').strip()
    payload['progress_bar_position'] = normalize_progress_bar_position(raw_payload.get('progress_bar_position'), 'center')
    payload['main_view_mode'] = normalize_choice_value(
        raw_payload.get('main_view_mode'),
        'font',
        allowed_view_modes,
    )
    payload['ui_language'] = normalize_ui_language(raw_payload.get('ui_language'), 'ja')
    return payload



def build_startup_preview_defaults_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Return startup-only preview defaults for restored UI state.

    Saved actual-size/device-view settings are still persisted, but startup uses
    the normal font preview so the zoom controls near the preview remain
    immediately usable and less confusing.
    """
    normalized = dict(payload or {})
    normalized['main_view_mode'] = 'font'
    normalized['actual_size'] = False
    return normalized


def build_settings_ui_apply_payload(
    raw_payload: Mapping[str, object],
    *,
    defaults: Mapping[str, object],
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_glyph_position_modes: Collection[str] | Mapping[str, object] | None = None,
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    bottom_tab_count: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    if allowed_glyph_position_modes is None:
        allowed_glyph_position_modes = {'down_strong': '下補正強', 'down_weak': '下補正弱', 'standard': '標準', 'up_weak': '上補正弱', 'up_strong': '上補正強'}
    allowed_lower_closing_bracket_position_modes = LOWER_CLOSING_BRACKET_POSITION_MODES
    allowed_wave_dash_drawing_modes = WAVE_DASH_DRAWING_MODES
    allowed_wave_dash_position_modes = WAVE_DASH_POSITION_MODES
    defaults = _coerce_mapping_payload(defaults)
    plan: dict[str, Any] = {}

    for key in ('profile', 'width', 'height'):
        if key in raw_payload:
            plan[key] = raw_payload.get(key)

    for key in ('target', 'output_dir', 'font_file'):
        if key in raw_payload:
            plan[key] = str(raw_payload.get(key) or '').strip()

    for key, fallback_key in (
        ('actual_size', 'actual_size'),
        ('show_guides', 'show_guides'),
        ('nav_buttons_reversed', 'nav_buttons_reversed'),
        ('dither', 'dither'),
        ('night_mode', 'night_mode'),
        ('ruby_hide', 'ruby_hide'),
        ('page_number_enabled', 'page_number_enabled'),
        ('progress_bar_enabled', 'progress_bar_enabled'),
        ('open_folder', 'open_folder'),
    ):
        if key in raw_payload:
            plan[key] = _config_bool_value(raw_payload.get(key), _config_bool_value(defaults.get(fallback_key), False))

    for key, fallback_key in (
        ('calibration_pct', 'calibration_pct'),
        ('font_size', 'font_size'),
        ('ruby_size', 'ruby_size'),
        ('page_number_font_size', 'page_number_font_size'),
        ('line_spacing', 'line_spacing'),
        ('margin_t', 'margin_t'),
        ('margin_b', 'margin_b'),
        ('margin_r', 'margin_r'),
        ('margin_l', 'margin_l'),
        ('threshold', 'threshold'),
        ('preview_page_limit', 'preview_page_limit'),
    ):
        if key in raw_payload:
            default_value = _config_int_value(defaults.get(fallback_key), 0)
            normalized = _config_int_value(raw_payload.get(key), default_value)
            if key == 'preview_page_limit':
                normalized = max(1, normalized)
            plan[key] = normalized

    if 'output_conflict' in raw_payload:
        plan['output_conflict'] = normalize_choice_value(
            raw_payload.get('output_conflict'),
            str(defaults.get('output_conflict') or 'rename'),
            allowed_output_conflicts,
        )
    if 'output_format' in raw_payload:
        plan['output_format'] = normalize_choice_value(
            raw_payload.get('output_format'),
            str(defaults.get('output_format') or 'xtch'),
            allowed_output_formats,
        )
    if 'kinsoku_mode' in raw_payload:
        plan['kinsoku_mode'] = normalize_choice_value(
            raw_payload.get('kinsoku_mode'),
            str(defaults.get('kinsoku_mode') or 'standard'),
            allowed_kinsoku_modes,
        )
    if 'tatechuyoko_digit_mode' in raw_payload:
        plan['tatechuyoko_digit_mode'] = normalize_tatechuyoko_digit_mode(
            raw_payload.get('tatechuyoko_digit_mode'),
            str(defaults.get('tatechuyoko_digit_mode') or '2'),
        )
    if 'progress_bar_position' in raw_payload:
        plan['progress_bar_position'] = normalize_progress_bar_position(
            raw_payload.get('progress_bar_position'),
            str(defaults.get('progress_bar_position') or 'center'),
        )
    for glyph_key in ('punctuation_position_mode', 'ichi_position_mode', 'halfwidth_digit_position_mode', 'halfwidth_alpha_position_mode', 'tatechuyoko_symbol_position_mode'):
        if glyph_key in raw_payload:
            plan[glyph_key] = normalize_choice_value(
                raw_payload.get(glyph_key),
                str(defaults.get(glyph_key) or 'standard'),
                allowed_glyph_position_modes,
            )
    if 'lower_closing_bracket_position_mode' in raw_payload:
        plan['lower_closing_bracket_position_mode'] = normalize_choice_value(
            raw_payload.get('lower_closing_bracket_position_mode'),
            str(defaults.get('lower_closing_bracket_position_mode') or 'standard'),
            allowed_lower_closing_bracket_position_modes,
        )
    if 'wave_dash_drawing_mode' in raw_payload:
        plan['wave_dash_drawing_mode'] = normalize_wave_dash_drawing_mode(
            raw_payload.get('wave_dash_drawing_mode'),
            str(defaults.get('wave_dash_drawing_mode') or 'rotate'),
        )
    if 'wave_dash_position_mode' in raw_payload:
        plan['wave_dash_position_mode'] = normalize_wave_dash_position_mode(
            raw_payload.get('wave_dash_position_mode'),
            str(defaults.get('wave_dash_position_mode') or 'standard'),
        )
    if 'main_view_mode' in raw_payload:
        plan['main_view_mode'] = normalize_choice_value(
            raw_payload.get('main_view_mode'),
            str(defaults.get('main_view_mode') or 'font'),
            allowed_view_modes,
        )
    if 'ui_language' in raw_payload:
        plan['ui_language'] = normalize_ui_language(
            raw_payload.get('ui_language'),
            str(defaults.get('ui_language') or 'ja'),
        )

    if 'bottom_tab_index' in raw_payload:
        bottom_tab_index = payload_optional_int_value(raw_payload, 'bottom_tab_index')
        if bottom_tab_index is not None and 0 <= bottom_tab_index < max(0, int(bottom_tab_count)):
            plan['bottom_tab_index'] = bottom_tab_index

    return plan


def build_settings_save_payload(
    raw_payload: Mapping[str, object],
    *,
    allowed_view_modes: Collection[str] | Mapping[str, object],
    allowed_profiles: Collection[str] | Mapping[str, object],
    allowed_kinsoku_modes: Collection[str] | Mapping[str, object],
    allowed_glyph_position_modes: Collection[str] | Mapping[str, object] | None = None,
    allowed_output_formats: Collection[str] | Mapping[str, object],
    allowed_output_conflicts: Collection[str] | Mapping[str, object],
    default_preview_page_limit: int,
) -> dict[str, Any]:
    raw_payload = _coerce_mapping_payload(raw_payload)
    if allowed_glyph_position_modes is None:
        allowed_glyph_position_modes = {'down_strong': '下補正強', 'down_weak': '下補正弱', 'standard': '標準', 'up_weak': '上補正弱', 'up_strong': '上補正強'}
    allowed_lower_closing_bracket_position_modes = LOWER_CLOSING_BRACKET_POSITION_MODES
    allowed_wave_dash_drawing_modes = WAVE_DASH_DRAWING_MODES
    allowed_wave_dash_position_modes = WAVE_DASH_POSITION_MODES
    payload: dict[str, Any] = dict(raw_payload)
    payload['bottom_tab_index'] = max(0, _config_int_value(raw_payload.get('bottom_tab_index'), 0))
    payload['main_view_mode'] = normalize_choice_value(
        raw_payload.get('main_view_mode'),
        'font',
        allowed_view_modes,
    )
    payload['ui_language'] = normalize_ui_language(raw_payload.get('ui_language'), 'ja')
    ui_theme = str(raw_payload.get('ui_theme') or '').strip()
    payload['ui_theme'] = ui_theme or 'light'
    payload['panel_button_visible'] = _config_bool_value(raw_payload.get('panel_button_visible'), True)
    payload['preset_index'] = max(-1, _config_int_value(raw_payload.get('preset_index'), -1))
    payload['preset_key'] = str(raw_payload.get('preset_key') or '').strip()
    payload['profile'] = normalize_choice_value(raw_payload.get('profile'), 'x4', allowed_profiles)
    payload['actual_size'] = _config_bool_value(raw_payload.get('actual_size'), False)
    payload['show_guides'] = _config_bool_value(raw_payload.get('show_guides'), True)
    payload['calibration_pct'] = _config_int_value(raw_payload.get('calibration_pct'), 100)
    payload['nav_buttons_reversed'] = _config_bool_value(raw_payload.get('nav_buttons_reversed'), False)
    payload['preview_page_limit'] = max(1, _config_int_value(raw_payload.get('preview_page_limit'), default_preview_page_limit))
    payload['target'] = str(raw_payload.get('target') or '').strip()
    payload['output_dir'] = str(raw_payload.get('output_dir') or '').strip()
    payload['font_file'] = str(raw_payload.get('font_file') or '').strip()
    payload['progress_bar_position'] = normalize_progress_bar_position(raw_payload.get('progress_bar_position'), 'center')
    for key, default in (
        ('font_size', 26),
        ('ruby_size', 12),
        ('page_number_font_size', 12),
        ('bottom_overlay_margin_auto_base_value', 14),
        ('bottom_overlay_margin_auto_value', 14),
        ('page_number_margin_auto_base_value', 14),
        ('page_number_margin_auto_value', 14),
        ('line_spacing', 44),
        ('margin_t', 12),
        ('margin_b', 14),
        ('margin_r', 12),
        ('margin_l', 12),
        ('threshold', 128),
        ('width', 480),
        ('height', 800),
    ):
        payload[key] = _config_int_value(raw_payload.get(key), default)
    for key, default in (
        ('dither', False),
        ('night_mode', False),
        ('ruby_hide', False),
        ('page_number_enabled', False),
        ('progress_bar_enabled', False),
        ('bottom_overlay_margin_auto_active', False),
        ('page_number_margin_auto_active', False),
        ('open_folder', False),
    ):
        payload[key] = _config_bool_value(raw_payload.get(key), default)
    payload['kinsoku_mode'] = normalize_choice_value(
        raw_payload.get('kinsoku_mode'),
        'standard',
        allowed_kinsoku_modes,
    )
    payload['tatechuyoko_digit_mode'] = normalize_tatechuyoko_digit_mode(
        raw_payload.get('tatechuyoko_digit_mode'),
        '2',
    )
    payload['output_format'] = normalize_choice_value(
        raw_payload.get('output_format'),
        'xtc',
        allowed_output_formats,
    )
    payload['punctuation_position_mode'] = normalize_choice_value(
        raw_payload.get('punctuation_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['ichi_position_mode'] = normalize_choice_value(
        raw_payload.get('ichi_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['halfwidth_digit_position_mode'] = normalize_choice_value(
        raw_payload.get('halfwidth_digit_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['halfwidth_alpha_position_mode'] = normalize_choice_value(
        raw_payload.get('halfwidth_alpha_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['tatechuyoko_symbol_position_mode'] = normalize_choice_value(
        raw_payload.get('tatechuyoko_symbol_position_mode'),
        'standard',
        allowed_glyph_position_modes,
    )
    payload['lower_closing_bracket_position_mode'] = normalize_choice_value(
        raw_payload.get('lower_closing_bracket_position_mode'),
        'standard',
        allowed_lower_closing_bracket_position_modes,
    )
    payload['wave_dash_drawing_mode'] = normalize_wave_dash_drawing_mode(
        raw_payload.get('wave_dash_drawing_mode'),
    )
    payload['wave_dash_position_mode'] = normalize_wave_dash_position_mode(
        raw_payload.get('wave_dash_position_mode'),
    )
    payload['output_conflict'] = normalize_choice_value(
        raw_payload.get('output_conflict'),
        'rename',
        allowed_output_conflicts,
    )
    return payload


def build_displaying_document_label(display_name: object = None, fallback: str = 'なし', language: object = 'ja') -> str:
    text = str(display_name if display_name is not None else fallback).strip()
    if not text:
        text = str(fallback).strip() or ('none' if _is_english_ui(language) else 'なし')
    if _is_english_ui(language):
        if text == 'なし':
            text = 'none'
        return f'Viewing: {text}'
    return f'表示中: {text}'



def display_context_name_from_label_text(text: object) -> str:
    normalized = _coerce_message_text(text).strip()
    for prefix in ('表示中:', 'Viewing:'):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
            break
    return normalized


def is_preview_render_failure_status_text(text: object) -> bool:
    normalized = _coerce_message_text(text).strip()
    return (
        normalized.startswith('プレビュー表示エラー')
        or normalized.startswith('プレビュー生成エラー')
        or normalized.startswith('Preview display error')
        or normalized.startswith('Preview generation error')
    )


def is_device_render_failure_status_text(text: object) -> bool:
    normalized = _coerce_message_text(text).strip()
    return normalized.startswith('ページ表示エラー') or normalized.startswith('Page display error')


def is_render_failure_status_text(text: object) -> bool:
    return (
        is_device_render_failure_status_text(text)
        or is_preview_render_failure_status_text(text)
    )


def render_failure_preserved_display_name(text: object) -> str:
    normalized = _coerce_message_text(text).strip()
    marker = '（表示は '
    suffix = ' のまま）'
    start = normalized.find(marker)
    if start >= 0:
        start += len(marker)
        end = normalized.find(suffix, start)
        if end >= 0:
            return normalized[start:end].strip()
    english_marker = '(still showing '
    english_suffix = ')'
    start = normalized.find(english_marker)
    if start < 0:
        return ''
    start += len(english_marker)
    end = normalized.find(english_suffix, start)
    if end < 0:
        return ''
    return normalized[start:end].strip()


def render_failure_matches_display_context(status_text: object, visible_display_name: object) -> bool:
    preserved_display_name = render_failure_preserved_display_name(status_text)
    visible_name = _coerce_message_text(visible_display_name).strip()
    if visible_name and preserved_display_name:
        return preserved_display_name == visible_name
    return True


def build_preview_status_message(
    state: str,
    *,
    preview_limit: int = 0,
    generated_pages: int = 0,
    truncated: bool = False,
    error: object = None,
    language: object = 'ja',
) -> str:
    normalized = str(state or '').strip().lower()
    english = _is_english_ui(language)
    if normalized == 'dirty':
        return 'Settings changed (not applied)' if english else '設定変更あり（未反映）'
    if normalized == 'running':
        limit = max(0, _config_int_value(preview_limit, 0))
        return f'Updating preview up to the first {limit} pages…' if english else f'先頭 {limit} ページまでプレビューを更新しています…'
    if normalized == 'empty':
        return 'Could not generate preview' if english else 'プレビューを生成できませんでした'
    if normalized == 'error':
        detail = str(error or '').strip()
        return (f'Preview generation error: {detail}' if detail else 'Preview generation error') if english else (f'プレビュー生成エラー: {detail}' if detail else 'プレビュー生成エラー')
    if normalized == 'complete':
        pages = max(0, _config_int_value(generated_pages, 0))
        limit = max(0, _config_int_value(preview_limit, 0))
        if english:
            if truncated:
                return f'Generated first {pages} / limit {limit} pages.'
            return f'Preview update complete ({pages} / limit {limit} pages)'
        if truncated:
            return f'先頭 {pages} / 上限 {limit} ページを生成しました。'
        return f'プレビュー更新完了（{pages} / 上限 {limit} ページ）'
    return str(state or '').strip()


def build_preview_progress_message(
    current: object,
    total: object,
    message: object,
    *,
    preview_limit: int = 0,
    language: object = 'ja',
) -> str:
    detail = translate_ui_text(str(message or '').strip(), language)
    current_value = max(0, _config_int_value(current, 0))
    total_value = max(0, _config_int_value(total, 0))
    if detail:
        if total_value > 0 and '/' not in detail:
            return f'{detail} ({current_value}/{total_value})'
        return detail
    if total_value > 0:
        if _is_english_ui(language):
            return f'Updating preview… ({current_value}/{total_value})'
        return f'プレビューを更新しています… ({current_value}/{total_value})'
    return build_preview_status_message('running', preview_limit=preview_limit, language=language)


def build_preview_success_status_state(
    *,
    page_count: object,
    requested_limit: object,
    truncated: object = False,
    language: object = 'ja',
) -> dict[str, Any]:
    """Return the normalized status payload for a completed preview render."""
    generated_pages = max(0, _config_int_value(page_count, 0))
    preview_limit = max(generated_pages, _config_int_value(requested_limit, 0))
    is_truncated = bool(truncated)
    return {
        'generated_pages': generated_pages,
        'preview_limit': preview_limit,
        'truncated': is_truncated,
        'status_message': build_preview_status_message(
            'complete',
            preview_limit=preview_limit,
            generated_pages=generated_pages,
            truncated=is_truncated,
            language=language,
        ),
    }


def build_preview_render_status_message(
    *,
    page_count: object,
    requested_limit: object,
    truncated: object = False,
    running: object = False,
    dirty: object = False,
    widget_limit: object = 0,
    language: object = 'ja',
) -> str:
    """Return the preview status message visible for the current render state."""
    success_state = build_preview_success_status_state(
        page_count=page_count,
        requested_limit=requested_limit,
        truncated=truncated,
        language=language,
    )
    preview_limit = _config_int_value(success_state.get('preview_limit'), 0)
    if preview_limit <= 0:
        fallback_limit = _config_int_value(widget_limit, 0)
        if fallback_limit > 0:
            preview_limit = max(1, fallback_limit)
    if bool(running):
        return build_preview_status_message('running', preview_limit=max(1, preview_limit or 1), language=language)
    if bool(dirty):
        return build_preview_status_message('dirty', language=language)
    return str(success_state.get('status_message', ''))


def build_successful_preview_render_status_refresh_state(
    *,
    preview_replacement: object,
    view_mode: object,
    visible_font_preview_active: object = False,
    preview_status_text: object = '',
    progress_status_text: object = '',
    status_bar_text: object = '',
    current_label_text: object = '',
) -> dict[str, Any]:
    """Return which shared status surfaces should be refreshed after success."""
    replacement = _coerce_message_text(preview_replacement).strip()
    normalized_mode = normalize_choice_value(view_mode, 'font', {'font', 'device'})
    font_view_visible = normalized_mode == 'font'
    device_view_visible = normalized_mode == 'device'
    preview_status = _coerce_message_text(preview_status_text).strip()
    progress_status = _coerce_message_text(progress_status_text).strip()
    status_bar_status = _coerce_message_text(status_bar_text).strip()
    visible_font_preview = bool(visible_font_preview_active)

    stale_preview_status = (
        is_render_failure_status_text(preview_status)
        or preview_status == 'プレビューを生成できませんでした'
    )

    progress_replacement = replacement
    if device_view_visible:
        label_text = _coerce_message_text(current_label_text).strip()
        progress_replacement = label_text or replacement

    stale_progress_status = is_preview_render_failure_status_text(progress_status)
    if not stale_progress_status and visible_font_preview:
        stale_progress_status = is_device_render_failure_status_text(progress_status)

    stale_status_bar = is_preview_render_failure_status_text(status_bar_status)
    if not stale_status_bar and visible_font_preview:
        stale_status_bar = is_device_render_failure_status_text(status_bar_status)

    should_notify_status_bar = (
        stale_progress_status
        or stale_status_bar
        or (stale_preview_status and font_view_visible)
    )

    return {
        'preview_replacement': replacement,
        'progress_replacement': progress_replacement,
        'font_view_visible': font_view_visible,
        'device_view_visible': device_view_visible,
        'stale_preview_status': stale_preview_status,
        'stale_progress_status': stale_progress_status,
        'stale_status_bar': stale_status_bar,
        'should_notify_status_bar': should_notify_status_bar,
    }

def build_successful_device_render_status_refresh_state(
    *,
    view_mode: object,
    current_label_text: object = '',
    preview_replacement: object = '',
    has_font_preview_pages: object = False,
    progress_status_text: object = '',
    status_bar_text: object = '',
) -> dict[str, Any]:
    """Return shared status refresh decisions after a device page render succeeds."""
    normalized_mode = normalize_choice_value(view_mode, 'font', {'font', 'device'})
    device_view_visible = normalized_mode == 'device'
    font_view_visible = normalized_mode == 'font'
    font_preview_visible = font_view_visible and bool(has_font_preview_pages)

    if device_view_visible:
        replacement = _coerce_message_text(current_label_text).strip()
    elif font_preview_visible:
        replacement = _coerce_message_text(preview_replacement).strip()
    else:
        replacement = ''

    progress_status = _coerce_message_text(progress_status_text).strip()
    status_bar_status = _coerce_message_text(status_bar_text).strip()
    if device_view_visible:
        stale_progress_status = is_render_failure_status_text(progress_status)
        stale_status_bar = is_render_failure_status_text(status_bar_status)
    else:
        stale_progress_status = is_device_render_failure_status_text(progress_status)
        stale_status_bar = is_device_render_failure_status_text(status_bar_status)

    should_notify_status_bar = stale_progress_status or stale_status_bar
    return {
        'replacement': replacement,
        'font_view_visible': font_view_visible,
        'device_view_visible': device_view_visible,
        'font_preview_visible': font_preview_visible,
        'stale_progress_status': stale_progress_status,
        'stale_status_bar': stale_status_bar,
        'should_notify_status_bar': should_notify_status_bar,
    }


def build_preview_button_state(
    context: Mapping[str, object] | None,
    *,
    default_text: str = 'プレビュー更新',
) -> dict[str, Any]:
    """Return normalized button state for preview refresh controls."""
    payload = _coerce_mapping_payload(context)
    return {
        'button_enabled': _config_bool_value(payload.get('button_enabled'), True),
        'button_text': str(payload.get('button_text', default_text)),
    }


def build_preview_progress_context_state(
    context: Mapping[str, object] | None,
) -> dict[str, Any]:
    """Return normalized preview-progress status/progress-bar state."""
    payload = _coerce_mapping_payload(context)
    total = max(0, _config_int_value(payload.get('progress_total'), 0))
    current = max(0, _config_int_value(payload.get('progress_current'), 0))
    if total > 0:
        current = min(current, total)
    return {
        'status_message': str(payload.get('status_message', '')),
        'progress_visible': _config_bool_value(payload.get('progress_visible'), False),
        'progress_busy': _config_bool_value(payload.get('progress_busy'), total <= 0),
        'progress_current': current,
        'progress_total': total,
    }


def _coerce_message_text(value: object, default: str = '') -> str:
    if value is None:
        text = ''
    else:
        if isinstance(value, os.PathLike):
            try:
                value = os.fspath(value)
            except Exception:
                pass
        if isinstance(value, (bytes, bytearray)):
            try:
                text = os.fsdecode(bytes(value))
            except Exception:
                text = str(value)
        else:
            text = str(value)
    return text if text.strip() else default


def _progress_number_value(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else int(default)
    if isinstance(value, os.PathLike):
        try:
            value = os.fspath(value)
        except Exception:
            return int(default)
    if isinstance(value, (bytes, bytearray)):
        try:
            value = os.fsdecode(bytes(value))
        except Exception:
            return int(default)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return int(default)
        try:
            return int(normalized, 10)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = float(normalized)
            except (TypeError, ValueError, OverflowError):
                return int(default)
            return int(parsed) if math.isfinite(parsed) else int(default)
    return int(default)



def merge_unique_message_values(existing_messages: Sequence[object], new_messages: Sequence[object]) -> list[str]:
    merged: list[str] = []
    for raw_message in [*existing_messages, *new_messages]:
        message = _coerce_message_text(raw_message).strip()
        if message and message not in merged:
            merged.append(message)
    return merged


def build_progress_status_text(current: object, total: object, message: object, language: object = 'ja') -> str:
    total_value = max(1, _progress_number_value(total, 1))
    current_value = max(0, min(_progress_number_value(current, 0), total_value))
    detail = translate_ui_text(_coerce_message_text(message).strip(), language)
    base = detail or ('Converting…' if _is_english_ui(language) else '変換中…')
    percent = int(round((current_value / total_value) * 100.0)) if total_value > 0 else 0
    return f'{base} ({current_value}/{total_value}, {percent}%)'


def build_conversion_failure_summary_text(prefix: object, message: object, language: object = 'ja') -> str:
    prefix_text = translate_ui_text(_coerce_message_text(prefix).strip(), language)
    fallback = 'Unknown error' if _is_english_ui(language) else '不明なエラー'
    message_text = translate_ui_text(_coerce_message_text(message, fallback).strip(), language) or fallback
    if not prefix_text:
        return message_text
    return f'{prefix_text}: {message_text}'





def build_render_failure_status_message(
    title: object,
    detail: object = '',
    preserved_display_name: object = '',
    language: object = 'ja',
) -> str:
    english = _is_english_ui(language)
    title_text = translate_ui_text(_coerce_message_text(title).strip(), language) or ('Display Error' if english else '表示エラー')
    detail_text = _coerce_message_text(detail).strip()
    if detail_text == 'Non-base64 digit found':
        detail_text = 'Only base64 data is allowed'
    preserved_text = _coerce_message_text(preserved_display_name).strip()
    message = title_text
    if preserved_text:
        if english:
            message += f' (still showing {preserved_text})'
        else:
            message += f'（表示は {preserved_text} のまま）'
    if detail_text:
        message += f': {detail_text}'
    return message

def build_xtc_load_failure_status_message(
    target: object,
    detail: object = '',
    preserved_display_name: object = '',
    language: object = 'ja',
) -> str:
    english = _is_english_ui(language)
    target_text = _coerce_message_text(target).strip() or ('specified file' if english else '指定ファイル')
    detail_text = _coerce_message_text(detail).strip()
    if detail_text == 'Non-base64 digit found':
        detail_text = 'Only base64 data is allowed'
    preserved_text = _coerce_message_text(preserved_display_name).strip()
    message = f'XTC/XTCH load failed: {target_text}' if english else f'XTC/XTCH読込失敗: {target_text}'
    if preserved_text:
        if english:
            message += f' (still showing {preserved_text})'
        else:
            message += f'（表示は {preserved_text} のまま）'
    if detail_text:
        message += f' / {detail_text}'
    return message


def build_xtc_load_failure_preserved_display_name(
    *,
    preview_active: object = False,
    remembered_display_name: object = '',
    remembered_path_display_name: object = '',
    current_label_text: object = '',
) -> str:
    if bool(preview_active):
        return 'プレビュー'

    remembered = _coerce_message_text(remembered_display_name).strip()
    if remembered and remembered != 'なし':
        return remembered

    remembered_path = _coerce_message_text(remembered_path_display_name).strip()
    if remembered_path and remembered_path != 'なし':
        return remembered_path

    normalized_label = display_context_name_from_label_text(current_label_text).strip()
    if normalized_label and normalized_label != 'なし':
        return normalized_label
    return ''


def normalize_xtc_bytes(data: object) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    raise TypeError('XTCデータは bytes 系である必要があります。')


def build_xtc_document_payload_from_pages(data: object, pages: Sequence[object]) -> dict[str, object]:
    page_list = list(pages)
    if not page_list:
        raise RuntimeError('XTC内にページがありません。')
    return {
        'data': data,
        'pages': page_list,
        'total': len(page_list),
        'current_index': 0,
        'current_page': 1,
    }


def build_xtc_page_state_payload(pages: Sequence[object], current_index: object = 0) -> dict[str, object]:
    page_list = list(pages)
    total = len(page_list)
    normalized_index = _config_int_value(current_index, 0)
    if total > 0:
        normalized_index = max(0, min(total - 1, normalized_index))
        page = page_list[normalized_index]
    else:
        normalized_index = 0
        page = None
    return {
        'total': total,
        'current_index': normalized_index,
        'current_page': normalized_index + 1 if total > 0 else 0,
        'page': page,
    }


def build_preview_refresh_state(
    *,
    page_count: object,
    reset_page: bool,
    current_preview_index: object,
    current_device_index: object,
    preview_limit: int,
    truncated: bool,
) -> dict[str, Any]:
    total_pages = max(0, _config_int_value(page_count, 0))
    if total_pages <= 0:
        return {
            'has_pages': False,
            'preview_index': 0,
            'device_index': 0,
            'generated_pages': 0,
            'status_message': build_preview_status_message('empty'),
        }
    if reset_page:
        preview_index = 0
        device_index = 0
    else:
        preview_index = max(0, min(total_pages - 1, _config_int_value(current_preview_index, 0)))
        device_index = max(0, min(total_pages - 1, _config_int_value(current_device_index, 0)))
    return {
        'has_pages': True,
        'preview_index': preview_index,
        'device_index': device_index,
        'generated_pages': total_pages,
        'status_message': build_preview_status_message(
            'complete',
            generated_pages=total_pages,
            preview_limit=preview_limit,
            truncated=truncated,
        ),
    }


def build_right_pane_preview_error_state(*, right_pane_source: object, error: object) -> dict[str, Any]:
    """Return preview-error cleanup state for the current right-pane surface."""
    normalized_source = normalize_right_pane_source_value(right_pane_source, default='preview')
    clear_right_pane_page = normalized_source != 'xtc'
    return {
        'preview_index': 0,
        'device_index': 0,
        'clear_device_page': clear_right_pane_page,
        'clear_right_pane_page': clear_right_pane_page,
        'status_message': build_preview_status_message('error', error=error),
    }


def build_preview_error_state(*, device_view_source: object, error: object) -> dict[str, Any]:
    """Legacy wrapper for older device-view source terminology."""
    return build_right_pane_preview_error_state(
        right_pane_source=device_view_source,
        error=error,
    )


def _clamp_navigation_index(total: int, current_index: int) -> tuple[int, int]:
    total_pages = max(0, _config_int_value(total, 0))
    index = _config_int_value(current_index, 0)
    if total_pages > 0:
        index = max(0, min(total_pages - 1, index))
    else:
        index = 0
    return total_pages, index


def normalize_navigation_index(total: object, current_index: object = 0) -> int:
    """Return a zero-based page index clamped to the available page count."""
    _, index = _clamp_navigation_index(
        _config_int_value(total, 0),
        _config_int_value(current_index, 0),
    )
    return index


def normalize_preview_page_cache_tokens(tokens: object, *, expected_len: int) -> list[int] | None:
    """Return integer cache tokens only when the payload matches the page count."""
    if not isinstance(tokens, (list, tuple)) or len(tokens) != expected_len:
        return None
    normalized: list[int] = []
    for value in tokens:
        try:
            normalized.append(int(value))
        except Exception:
            return None
    return normalized


def build_preview_page_cache_tokens_state(
    context: Mapping[str, object] | None,
    *,
    preview_page_count: object,
    device_preview_page_count: object,
) -> dict[str, Any]:
    """Return normalized preview-cache tokens or a rebuild request."""
    payload = _coerce_mapping_payload(context)
    preview_count = max(0, _config_int_value(preview_page_count, 0))
    device_count = max(0, _config_int_value(device_preview_page_count, 0))
    preview_tokens = normalize_preview_page_cache_tokens(
        payload.get('preview_page_cache_tokens'),
        expected_len=preview_count,
    )
    device_tokens = normalize_preview_page_cache_tokens(
        payload.get('device_preview_page_cache_tokens'),
        expected_len=device_count,
    )
    should_rebuild = preview_tokens is None or device_tokens is None
    return {
        'should_rebuild': should_rebuild,
        'preview_page_cache_tokens': [] if preview_tokens is None else list(preview_tokens),
        'device_preview_page_cache_tokens': [] if device_tokens is None else list(device_tokens),
    }


def normalize_right_pane_source_value(value: object, *, default: str = 'xtc') -> str:
    """Normalize the source selector used by the right-pane runtime.

    The old device-view UI was retired in v1.3.8.10, but older context/INI
    payloads can still carry the former selector values.  Keep this helper
    focused on the current right-pane surface while preserving those legacy
    inputs through the ``normalize_device_view_source_value`` wrapper below.
    """
    if value is None:
        text = ''
    elif isinstance(value, os.PathLike):
        text = os.fspath(value)
    elif isinstance(value, (bytes, bytearray)):
        try:
            text = os.fsdecode(bytes(value))
        except Exception:
            text = ''
    else:
        text = str(value)
    normalized = text.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {'\"', "'"}:
        quoted = normalized[1:-1].strip()
        if quoted:
            normalized = quoted
    normalized = normalized.lower()
    if normalized in {'preview', 'xtc'}:
        return normalized
    return default


def normalize_device_view_source_value(value: object, *, default: str = 'xtc') -> str:
    """Legacy wrapper for older device-view source terminology."""
    return normalize_right_pane_source_value(value, default=default)


def resolve_effective_right_pane_source(source: object, *, has_preview_pages: object) -> str:
    """Return the right-pane source that can actually be displayed now."""
    normalized = normalize_right_pane_source_value(source, default='xtc')
    if normalized == 'preview' and bool(has_preview_pages):
        return 'preview'
    return 'xtc'


def resolve_effective_device_view_source(source: object, *, has_preview_pages: object) -> str:
    """Legacy wrapper for older device-view source terminology."""
    return resolve_effective_right_pane_source(source, has_preview_pages=has_preview_pages)


def is_right_pane_preview_display_active(
    view_mode: object,
    *,
    has_font_preview_pages: object,
    effective_right_pane_source: object,
) -> bool:
    """Return whether the currently visible page source is a generated preview."""
    normalized_mode = normalize_choice_value(view_mode, 'font', {'font', 'device'})
    if normalized_mode == 'font':
        return bool(has_font_preview_pages)
    return normalize_right_pane_source_value(effective_right_pane_source, default='xtc') == 'preview'


def is_preview_display_active(
    view_mode: object,
    *,
    has_font_preview_pages: object,
    effective_device_view_source: object,
) -> bool:
    """Legacy wrapper for older device-view source terminology."""
    return is_right_pane_preview_display_active(
        view_mode,
        has_font_preview_pages=has_font_preview_pages,
        effective_right_pane_source=effective_device_view_source,
    )


def build_right_pane_preview_page_sync_state(
    *,
    mode: object,
    effective_right_pane_source: object,
    preview_page_count: object,
    device_preview_page_count: object,
    current_preview_index: object,
    current_device_preview_index: object,
) -> dict[str, Any]:
    """Return the page-index sync plan when switching between preview views."""
    normalized_mode = normalize_choice_value(mode, 'font', {'font', 'device'})
    source = normalize_right_pane_source_value(effective_right_pane_source, default='xtc')
    if source != 'preview':
        return {
            'should_sync': False,
            'target': '',
            'target_index': 0,
        }
    if normalized_mode == 'font':
        total = max(0, _config_int_value(preview_page_count, 0))
        if total <= 0:
            return {
                'should_sync': False,
                'target': 'font',
                'target_index': 0,
            }
        return {
            'should_sync': True,
            'target': 'font',
            'target_index': normalize_navigation_index(total, current_device_preview_index),
        }
    total = max(0, _config_int_value(device_preview_page_count, 0))
    if total <= 0:
        return {
            'should_sync': False,
            'target': 'device',
            'target_index': 0,
        }
    return {
        'should_sync': True,
        'target': 'device',
        'target_index': normalize_navigation_index(total, current_preview_index),
    }



def build_preview_view_page_sync_state(
    *,
    mode: object,
    effective_device_view_source: object,
    preview_page_count: object,
    device_preview_page_count: object,
    current_preview_index: object,
    current_device_preview_index: object,
) -> dict[str, Any]:
    """Legacy wrapper for older device-view source terminology."""
    return build_right_pane_preview_page_sync_state(
        mode=mode,
        effective_right_pane_source=effective_device_view_source,
        preview_page_count=preview_page_count,
        device_preview_page_count=device_preview_page_count,
        current_preview_index=current_preview_index,
        current_device_preview_index=current_device_preview_index,
    )


def build_navigation_target_state(
    *,
    total: object,
    current_index: object,
    target_index: object,
) -> dict[str, Any]:
    total_pages, current = _clamp_navigation_index(_config_int_value(total, 0), _config_int_value(current_index, 0))
    if total_pages <= 0:
        return {
            'active': False,
            'current_index': 0,
            'target_index': 0,
            'changed': False,
        }
    _, target = _clamp_navigation_index(total_pages, _config_int_value(target_index, current))
    return {
        'active': True,
        'current_index': current,
        'target_index': target,
        'changed': target != current,
    }


def build_navigation_delta_state(
    *,
    total: object,
    current_index: object,
    delta: object,
) -> dict[str, Any]:
    total_pages, current = _clamp_navigation_index(_config_int_value(total, 0), _config_int_value(current_index, 0))
    if total_pages <= 0:
        return {
            'active': False,
            'current_index': 0,
            'target_index': 0,
            'changed': False,
        }
    delta_value = _config_int_value(delta, 0)
    return build_navigation_target_state(
        total=total_pages,
        current_index=current,
        target_index=current + delta_value,
    )


def build_navigation_input_state(
    *,
    total: object,
    current_index: object,
    input_page: object,
) -> dict[str, Any]:
    total_pages, current = _clamp_navigation_index(_config_int_value(total, 0), _config_int_value(current_index, 0))
    if total_pages <= 0:
        return {
            'active': False,
            'current_index': 0,
            'target_index': 0,
            'changed': False,
            'is_valid': False,
        }
    page_number = _config_int_value(input_page, 0)
    if page_number < 1 or page_number > total_pages:
        return {
            'active': True,
            'current_index': current,
            'target_index': current,
            'changed': False,
            'is_valid': False,
        }
    target = page_number - 1
    return {
        'active': True,
        'current_index': current,
        'target_index': target,
        'changed': target != current,
        'is_valid': True,
    }



def build_navigation_display_state(
    *,
    view_mode: str,
    total: int,
    current_index: int,
    truncated: bool = False,
) -> dict[str, Any]:
    normalized_view_mode = str(view_mode or 'device').strip().lower()
    if normalized_view_mode not in {'font', 'device'}:
        normalized_view_mode = 'device'
    total_pages = max(0, int(total))
    index = int(current_index)
    if total_pages > 0:
        index = max(0, min(total_pages - 1, index))
    else:
        index = 0
    active = total_pages > 0
    return {
        'active': active,
        'total': total_pages,
        'current_index': index,
        'current_page': index + 1 if active else 0,
        'can_go_prev': active and index > 0,
        'can_go_next': active and index < max(0, total_pages - 1),
        'total_label': f'/ {total_pages}{"+" if truncated and active else ""}',
        'view_mode': normalized_view_mode,
    }




def build_right_pane_navigation_payload(
    *,
    view_mode: object,
    total: object,
    current_index: object,
    current_page: object | None = None,
    is_preview: object = False,
    truncated: object = False,
) -> dict[str, Any]:
    """Build the navigation payload for the current right-pane page surface.

    ``view_mode='device'`` remains the compatibility value used by older
    call sites to mean that the right-pane XTC/XTCH/page surface is active.
    The public user-facing device-view switch itself is no longer restored.
    """
    total_pages = max(0, _config_int_value(total, 0))
    index = _config_int_value(current_index, 0)
    preview_source = bool(is_preview)
    payload = build_navigation_display_state(
        view_mode='device',
        total=total_pages,
        current_index=index,
        truncated=bool(preview_source and truncated),
    )
    normalized_view_mode = str(view_mode or 'font').strip().lower()
    payload['active'] = bool(normalized_view_mode == 'device' and payload.get('active'))
    if current_page is not None:
        payload['current_page'] = max(0, _config_int_value(current_page, payload.get('current_page', 0)))
    return payload


def build_device_navigation_payload(
    *,
    view_mode: object,
    total: object,
    current_index: object,
    current_page: object | None = None,
    is_preview: object = False,
    truncated: object = False,
) -> dict[str, Any]:
    """Legacy wrapper for older device-view navigation terminology."""
    return build_right_pane_navigation_payload(
        view_mode=view_mode,
        total=total,
        current_index=current_index,
        current_page=current_page,
        is_preview=is_preview,
        truncated=truncated,
    )

def build_navigation_apply_state(
    payload: Mapping[str, object],
    nav_state: Mapping[str, object],
    *,
    total_label_format: object = '/ {total}',
    nav_buttons_reversed: object = False,
) -> dict[str, Any]:
    total = max(0, _config_int_value(payload.get('total'), 0))
    nav_active = _config_bool_value(nav_state.get('active'), False)
    active = total > 0 and _config_bool_value(payload.get('active'), nav_active) and nav_active
    current_page = _config_int_value(nav_state.get('current_page'), 0) if total > 0 else 0
    can_go_prev = active and _config_bool_value(nav_state.get('can_go_prev'), False)
    can_go_next = active and _config_bool_value(nav_state.get('can_go_next'), False)

    format_text = str(total_label_format or '/ {total}')
    try:
        total_label_fallback = format_text.format(total=total)
    except Exception:
        total_label_fallback = f'/ {total}'
    total_label = str(payload.get('total_label', total_label_fallback))
    if bool(nav_buttons_reversed):
        prev_enabled = can_go_next
        next_enabled = can_go_prev
    else:
        prev_enabled = can_go_prev
        next_enabled = can_go_next

    return {
        'active': active,
        'current_page': current_page,
        'can_go_prev': can_go_prev,
        'can_go_next': can_go_next,
        'prev_enabled': prev_enabled,
        'next_enabled': next_enabled,
        'total_label': total_label,
    }


def build_nav_button_text_state(
    nav_bar_plan: Mapping[str, object] | None = None,
    *,
    nav_buttons_reversed: object = False,
) -> dict[str, str]:
    """Return display texts for the previous/next navigation buttons.

    ``MainWindow`` keeps ownership of the actual buttons and signal wiring;
    this helper only resolves the layout-plan labels and reversed-button
    presentation rule.
    """

    plan = dict(nav_bar_plan or {})
    prev_text = str(plan.get('prev_button_text', '前'))
    next_text = str(plan.get('next_button_text', '次'))
    if _config_bool_value(nav_buttons_reversed, False):
        return {'prev_button_text': next_text, 'next_button_text': prev_text}
    return {'prev_button_text': prev_text, 'next_button_text': next_text}


def build_preview_zoom_control_state(
    view_toggle_bar_plan: Mapping[str, object] | None = None,
    *,
    actual_size: object = False,
    label_key: object = None,
    tooltip_key: object = None,
) -> dict[str, str]:
    """Return label/tooltip text for the right-pane preview zoom controls.

    ``MainWindow`` owns the Qt widgets; this helper keeps the mode-dependent
    text resolution testable without constructing the GUI.
    """

    plan = dict(view_toggle_bar_plan or {})
    actual = _config_bool_value(actual_size, False)
    resolved_label_key = str(
        label_key
        or ('preview_zoom_actual_size_label_text' if actual else 'preview_zoom_label_text')
    )
    resolved_tooltip_key = str(
        tooltip_key
        or ('preview_zoom_actual_size_tooltip' if actual else 'preview_zoom_normal_tooltip')
    )
    label_fallback = '実寸補正' if actual else '表示倍率'
    tooltip_fallback = (
        '実寸近似ON: 実機サイズに合わせる補正倍率です。'
        if actual
        else 'フォントビュー（実寸近似OFF）と実機ビューの表示倍率です。'
    )
    return {
        'label_text': str(plan.get(resolved_label_key, label_fallback)),
        'tooltip': str(plan.get(resolved_tooltip_key, tooltip_fallback)),
    }



def build_loaded_xtc_view_mode_state(
    mode: object,
    *,
    safe: object = False,
    can_apply_full_view_mode: object = False,
) -> dict[str, Any]:
    """Return how a loaded XTC view-mode request should be applied.

    The GUI keeps ownership of Qt widgets and ``set_main_view_mode``.  This
    helper only normalizes the requested mode and decides whether safe mode
    should use the full UI path or direct state assignment.
    """
    mode_text = _coerce_message_text(mode).strip()
    if not mode_text:
        return {
            'has_mode': False,
            'mode': '',
            'apply_full_view_mode': False,
            'assign_main_view_mode': False,
        }
    safe_mode = _config_bool_value(safe, False)
    apply_full = (not safe_mode) or _config_bool_value(can_apply_full_view_mode, False)
    return {
        'has_mode': True,
        'mode': mode_text,
        'apply_full_view_mode': apply_full,
        'assign_main_view_mode': not apply_full,
    }

def build_page_input_apply_state(
    *,
    total_pages: object,
    current_page: object = 0,
    empty_minimum: object = 0,
    empty_maximum: object = 0,
    active_minimum: object = 1,
) -> dict[str, int | bool]:
    """Return the range/value state for the shared page input widget."""
    empty_min = _config_int_value(empty_minimum, 0)
    empty_max = _config_int_value(empty_maximum, 0)
    active_min = _config_int_value(active_minimum, 1)
    total = max(0, _config_int_value(total_pages, 0))
    value = max(0, _config_int_value(current_page, 0))
    if total <= 0:
        return {
            'active': False,
            'minimum': empty_min,
            'maximum': empty_max,
            'value': empty_min,
        }
    return {
        'active': True,
        'minimum': active_min,
        'maximum': total,
        'value': max(active_min, min(value or active_min, total)),
    }




def read_image_dimensions(image: object) -> tuple[int, int]:
    """Return safe ``(width, height)`` values from a Qt/Pillow-like image object."""
    if image is None:
        return 0, 0

    def _read_dimension(name: str) -> int:
        candidate = getattr(image, name, None)
        try:
            value = candidate() if callable(candidate) else candidate
        except Exception:
            value = 0
        try:
            return max(0, int(value))
        except Exception:
            return 0

    return _read_dimension('width'), _read_dimension('height')




def normalize_preview_zoom_pct(
    value: object,
    *,
    default: int = 100,
    minimum: int = 50,
    maximum: int = 300,
) -> int:
    """Return a safe preview zoom percentage for UI/runtime calculations."""
    parsed = payload_optional_int_value({'preview_zoom_pct': value}, 'preview_zoom_pct')
    normalized = int(default) if parsed is None else int(parsed)
    lower = min(int(minimum), int(maximum))
    upper = max(int(minimum), int(maximum))
    return max(lower, min(normalized, upper))


def build_actual_size_calibration_factor(
    *,
    uses_preview_zoom: object,
    preview_zoom_pct: object,
    calibration_pct: object,
    min_factor: float = 0.5,
    max_factor: float = 3.0,
) -> float:
    """Return the effective scale factor for actual-size preview rendering."""
    if _config_bool_value(uses_preview_zoom, False):
        return normalize_preview_zoom_pct(preview_zoom_pct) / 100.0
    try:
        value = float(calibration_pct) / 100.0
    except Exception:
        value = 1.0
    if not math.isfinite(value):
        value = 1.0
    lower = min(float(min_factor), float(max_factor))
    upper = max(float(min_factor), float(max_factor))
    return max(lower, min(value, upper))




def build_font_preview_target_size(
    *,
    actual_size: object,
    screen_w_mm: object,
    screen_h_mm: object,
    px_per_mm: object,
    viewport_width: object = 0,
    viewport_height: object = 0,
    zoom_factor: object = 1.0,
    fallback: tuple[int, int] = (480, 720),
) -> tuple[int, int]:
    """Return the target font-preview size as a plain ``(width, height)`` pair."""

    def _float_value(value: object, default: float = 0.0) -> float:
        try:
            parsed = float(value)
        except Exception:
            return float(default)
        return parsed if math.isfinite(parsed) else float(default)

    if _config_bool_value(actual_size, False):
        width_mm = max(0.0, _float_value(screen_w_mm, 0.0))
        height_mm = max(0.0, _float_value(screen_h_mm, 0.0))
        px = max(0.0, _float_value(px_per_mm, 0.0))
        return max(180, int(width_mm * px)), max(240, int(height_mm * px))

    viewport_w = _config_int_value(viewport_width, 0)
    viewport_h = _config_int_value(viewport_height, 0)
    if viewport_w >= 10 and viewport_h >= 10:
        zoom = _float_value(zoom_factor, 1.0)
        if abs(zoom - 1.0) < 0.001:
            return viewport_w, viewport_h
        return max(10, int(round(viewport_w * zoom))), max(10, int(round(viewport_h * zoom)))

    try:
        fallback_w, fallback_h = fallback
    except Exception:
        fallback_w, fallback_h = 480, 720
    return _config_int_value(fallback_w, 480), _config_int_value(fallback_h, 720)



def build_viewer_profile_resolution_state(
    width: object,
    height: object,
    *,
    current_width: object = 0,
    current_height: object = 0,
    profile_dimensions: Mapping[str, Sequence[object]] | None = None,
    preferred_profile_keys: Sequence[str] = ('x4', 'x3'),
) -> dict[str, object]:
    """Return how the GUI should resolve a viewer profile for page dimensions.

    The GUI layer still owns ``DeviceProfile`` instances. This helper only
    decides whether the requested pixel size maps to the current profile, a
    known preset profile, a custom profile, or an invalid fallback.
    """

    width_px = max(0, _config_int_value(width, 0))
    height_px = max(0, _config_int_value(height, 0))
    if width_px <= 0 or height_px <= 0:
        return {
            'kind': 'current',
            'profile_key': '',
            'width_px': width_px,
            'height_px': height_px,
        }

    current_w = max(0, _config_int_value(current_width, 0))
    current_h = max(0, _config_int_value(current_height, 0))
    if current_w == width_px and current_h == height_px:
        return {
            'kind': 'current',
            'profile_key': '',
            'width_px': width_px,
            'height_px': height_px,
        }

    dimensions = dict(profile_dimensions or {})
    for raw_key in preferred_profile_keys:
        key = str(raw_key).strip()
        if not key:
            continue
        raw_size = dimensions.get(key)
        if not isinstance(raw_size, Sequence) or isinstance(raw_size, (str, bytes, bytearray)):
            continue
        size_values = list(raw_size)
        if len(size_values) < 2:
            continue
        preset_w = max(0, _config_int_value(size_values[0], 0))
        preset_h = max(0, _config_int_value(size_values[1], 0))
        if preset_w == width_px and preset_h == height_px:
            return {
                'kind': 'profile',
                'profile_key': key,
                'width_px': width_px,
                'height_px': height_px,
            }

    return {
        'kind': 'custom',
        'profile_key': 'custom',
        'width_px': width_px,
        'height_px': height_px,
    }


def build_custom_viewer_profile_metrics(
    *,
    width_px: object,
    height_px: object,
    ppi: object,
    screen_w_mm: object,
    screen_h_mm: object,
    body_w_mm: object,
    body_h_mm: object,
) -> dict[str, float | int]:
    """Return dimensions for a custom viewer profile derived from pixels.

    The GUI layer owns the concrete ``DeviceProfile`` object; this helper only
    normalizes the arithmetic so the mm conversion and body-area ratios can be
    regression tested without Qt.
    """

    def _float_value(value: object, default: float) -> float:
        try:
            parsed = float(value)
        except Exception:
            return float(default)
        return parsed if math.isfinite(parsed) else float(default)

    def _int_value(value: object, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return int(default)

    width_value = max(1, _int_value(width_px, 1))
    height_value = max(1, _int_value(height_px, 1))
    ppi_value = max(1e-6, _float_value(ppi, 300.0))
    px_per_mm = max(1e-6, ppi_value / 25.4)
    source_screen_w_mm = max(1e-6, _float_value(screen_w_mm, 1.0))
    source_screen_h_mm = max(1e-6, _float_value(screen_h_mm, 1.0))
    source_body_w_mm = max(0.0, _float_value(body_w_mm, source_screen_w_mm))
    source_body_h_mm = max(0.0, _float_value(body_h_mm, source_screen_h_mm))
    body_w_ratio = source_body_w_mm / source_screen_w_mm
    body_h_ratio = source_body_h_mm / source_screen_h_mm
    resolved_screen_w_mm = float(width_value) / px_per_mm
    resolved_screen_h_mm = float(height_value) / px_per_mm
    return {
        'width_px': int(width_value),
        'height_px': int(height_value),
        'screen_w_mm': resolved_screen_w_mm,
        'screen_h_mm': resolved_screen_h_mm,
        'body_w_mm': resolved_screen_w_mm * body_w_ratio,
        'body_h_mm': resolved_screen_h_mm * body_h_ratio,
    }


def build_safe_preview_layout_size(
    size: object,
    *,
    fallback: tuple[int, int] = (480, 720),
    minimum: int = 10,
    maximum: int = 4096,
) -> tuple[int, int]:
    """Return a clamped ``(width, height)`` pair from a Qt-like size object."""
    try:
        fallback_w, fallback_h = fallback
    except Exception:
        fallback_w, fallback_h = 480, 720

    def _dimension_value(name: str, fallback_value: int) -> int:
        candidate = getattr(size, name, None)
        try:
            raw_value = candidate() if callable(candidate) else candidate
        except Exception:
            raw_value = fallback_value
        try:
            return int(raw_value)
        except Exception:
            return int(fallback_value)

    lower = min(int(minimum), int(maximum))
    upper = max(int(minimum), int(maximum))
    width = _dimension_value('width', int(fallback_w))
    height = _dimension_value('height', int(fallback_h))
    return max(lower, min(width, upper)), max(lower, min(height, upper))


def build_viewer_minimum_size(
    size_hint: object,
    *,
    fallback: tuple[int, int] = (660, 860),
    min_width: int = 360,
    min_height: int = 600,
    maximum: int = 4096,
) -> tuple[int, int]:
    """Return a clamped minimum size for the device preview widget."""
    try:
        fallback_w, fallback_h = fallback
    except Exception:
        fallback_w, fallback_h = 660, 860

    def _dimension_value(name: str, fallback_value: int) -> int:
        candidate = getattr(size_hint, name, None)
        try:
            raw_value = candidate() if callable(candidate) else candidate
        except Exception:
            raw_value = fallback_value
        try:
            return int(raw_value)
        except Exception:
            return int(fallback_value)

    upper = max(1, int(maximum))
    width = _dimension_value('width', int(fallback_w))
    height = _dimension_value('height', int(fallback_h))
    return (
        max(int(min_width), min(width, upper)),
        max(int(min_height), min(height, upper)),
    )

def localized_preset_display_name_text(text: object, language: object = 'ja') -> str:
    raw = str(text or '').strip()
    if not raw:
        return 'Preset' if _is_english_ui(language) else 'プリセット'
    if _is_english_ui(language):
        match = re.fullmatch(r'プリセット\s*(\d+)', raw)
        if match:
            return f'Preset {match.group(1)}'
        if raw == 'プリセット':
            return 'Preset'
    return raw


def build_preset_display_name(preset: Mapping[str, object], language: object = 'ja') -> str:
    button_text = localized_preset_display_name_text(preset.get('button_text'), language)
    name = localized_preset_display_name_text(preset.get('name'), language)
    if button_text and name:
        return button_text if button_text == name else f'{button_text} / {name}'
    return button_text or name or ('Preset' if _is_english_ui(language) else 'プリセット')


def compact_multiline_label_text(text: object) -> str:
    """Return text without trailing blank lines for compact QLabel display."""
    lines = [line.rstrip() for line in str(text or '').splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    return '\n'.join(lines)


def _build_preset_summary_lines(
    preset: Mapping[str, object],
    *,
    font_text: str,
    device_profile_keys: Collection[str],
    kinsoku_mode_labels: Mapping[str, str],
    output_format_labels: Mapping[str, str],
    language: object = 'ja',
) -> tuple[str, str, str, str]:
    normalized_profiles = {str(item).strip().lower() for item in device_profile_keys}
    night_text = 'ON' if _config_bool_value(preset.get('night_mode'), False) else 'OFF'
    dither_text = 'ON' if _config_bool_value(preset.get('dither'), False) else 'OFF'
    profile_key = str(preset.get('profile', 'x4')).strip().lower()
    if profile_key not in normalized_profiles:
        profile_key = 'x4'
    profile_text = profile_key.upper()
    kinsoku_mode = str(preset.get('kinsoku_mode', 'standard')).strip().lower()
    if kinsoku_mode not in kinsoku_mode_labels:
        kinsoku_mode = 'standard'
    kinsoku_text = _localized_mode_label(kinsoku_mode_labels.get(kinsoku_mode, '標準'), language)
    out_fmt = str(preset.get('output_format', 'xtch')).strip().lower()
    if out_fmt not in output_format_labels:
        out_fmt = 'xtch'
    preset_name = build_preset_display_name(preset, language)
    font_size = _config_int_value(preset.get('font_size'), 26)
    ruby_size = _config_int_value(preset.get('ruby_size'), 12)
    line_spacing = _config_int_value(preset.get('line_spacing'), 44)
    margin_t = _config_int_value(preset.get('margin_t'), 12)
    margin_b = _config_int_value(preset.get('margin_b'), 14)
    margin_r = _config_int_value(preset.get('margin_r'), 12)
    margin_l = _config_int_value(preset.get('margin_l'), 12)
    threshold = _config_int_value(preset.get('threshold'), 128)
    out_fmt_text = output_format_labels.get(out_fmt, 'XTCH')
    tatechuyoko_mode = normalize_tatechuyoko_digit_mode(preset.get('tatechuyoko_digit_mode', '2'), '2')
    tatechuyoko_text = _localized_mode_label(TATECHUYOKO_DIGIT_MODES.get(tatechuyoko_mode, '2文字'), language)
    name_line = preset_name
    page_number_text = _yes_no_text(preset.get('page_number_enabled'), language)
    page_number_size = _config_int_value(preset.get('page_number_font_size'), 12)
    progress_bar_text = _yes_no_text(preset.get('progress_bar_enabled'), language)
    progress_bar_position = normalize_progress_bar_position(preset.get('progress_bar_position'), 'center')
    progress_bar_position_text = _localized_mode_label({'center': '下中央', 'left': '下左'}.get(progress_bar_position, '下中央'), language)
    if _is_english_ui(language):
        line1 = f'Device: {profile_text} / Output Format: {out_fmt_text} / Body: {font_size} / Ruby: {ruby_size} / Line Spacing: {line_spacing} / Tate-chu-yoko: {tatechuyoko_text}'
        line2 = f'Margins: Top {margin_t} Bottom {margin_b} Left {margin_l} Right {margin_r} / Invert B/W: {night_text} / Dither: {dither_text} / Threshold: {threshold} / Line Rules: {kinsoku_text} / Page Number: {page_number_text}({page_number_size}) / Progress Bar: {progress_bar_text}({progress_bar_position_text})'
        line3 = f'Font: {font_text}'
    else:
        line1 = f'機種: {profile_text} / 出力形式: {out_fmt_text} / 本文: {font_size} / ルビ: {ruby_size} / 行間: {line_spacing} / 縦中横: {tatechuyoko_text}'
        line2 = f'余白: 上 {margin_t} 下 {margin_b} 左 {margin_l} 右 {margin_r} / 白黒反転: {night_text} / ディザ: {dither_text} / しきい値: {threshold} / 禁則: {kinsoku_text} / ページ番号: {page_number_text}({page_number_size}) / 進捗バー: {progress_bar_text}({progress_bar_position_text})'
        line3 = f'フォント: {font_text}'
    return name_line, line1, line2, line3


def build_preset_summary_text(
    preset: Mapping[str, object],
    *,
    font_text: str,
    device_profile_keys: Collection[str],
    kinsoku_mode_labels: Mapping[str, str],
    output_format_labels: Mapping[str, str],
    summary_tag: str = '',
    include_name_line: bool = True,
    language: object = 'ja',
) -> str:
    name_line, line1, line2, line3 = _build_preset_summary_lines(
        preset,
        font_text=font_text,
        device_profile_keys=device_profile_keys,
        kinsoku_mode_labels=kinsoku_mode_labels,
        output_format_labels=output_format_labels,
        language=language,
    )
    lines = [line1, line2, line3]
    if include_name_line:
        tag_text = str(summary_tag or '').strip()
        if tag_text:
            name_line = f'{name_line} {tag_text}'
        lines.insert(0, name_line)
    return compact_multiline_label_text('\n'.join(line for line in lines if str(line).strip()))



def build_preset_summary_html(
    preset: Mapping[str, object],
    *,
    font_text: str,
    device_profile_keys: Collection[str],
    kinsoku_mode_labels: Mapping[str, str],
    output_format_labels: Mapping[str, str],
    summary_tag: str = '',
    include_name_line: bool = True,
    language: object = 'ja',
) -> str:
    name_line, line1, line2, line3 = _build_preset_summary_lines(
        preset,
        font_text=font_text,
        device_profile_keys=device_profile_keys,
        kinsoku_mode_labels=kinsoku_mode_labels,
        output_format_labels=output_format_labels,
        language=language,
    )
    rendered_lines = [html.escape(line1), html.escape(line2), html.escape(line3)]
    if include_name_line:
        tag_text = str(summary_tag or '').strip()
        escaped_preset_name = html.escape(name_line)
        escaped_tag_text = html.escape(tag_text)
        rendered_name_line = (
            escaped_preset_name
            if not escaped_tag_text
            else f'{escaped_preset_name} <span style="color:#6B7C90;">{escaped_tag_text}</span>'
        )
        rendered_lines.insert(0, rendered_name_line)
    line_markup = ''.join(
        f'<div style="margin:0; padding:0;">{line}</div>'
        for line in rendered_lines
        if str(line).strip()
    )
    return (
        '<div style="line-height:1.12; text-align:left; margin:0; padding:0;">'
        f'{line_markup}'
        '</div>'
    )




def find_matching_result_index(target_key: object, candidate_keys: Sequence[object]) -> int | None:
    normalized_target = str(target_key or '').strip()
    if not normalized_target:
        return None
    for idx, raw_key in enumerate(candidate_keys):
        if str(raw_key or '').strip() == normalized_target:
            return idx
    return None


def resolve_preferred_result_index(
    *,
    selected_indexes: Sequence[object],
    current_index: object,
    item_count: object,
) -> int | None:
    normalized_count = max(0, _config_int_value(item_count, 0))

    def _is_valid_index(value: object) -> int | None:
        normalized = payload_optional_int_value({'value': value}, 'value')
        if normalized is None or normalized < 0:
            return None
        if normalized_count > 0 and normalized >= normalized_count:
            return None
        return normalized

    valid_selected_indexes: list[int] = []
    seen_indexes: set[int] = set()
    for raw_index in selected_indexes:
        valid_index = _is_valid_index(raw_index)
        if valid_index is None or valid_index in seen_indexes:
            continue
        seen_indexes.add(valid_index)
        valid_selected_indexes.append(valid_index)

    valid_current = _is_valid_index(current_index)

    if valid_current is not None:
        return valid_current

    if len(valid_selected_indexes) == 1:
        return valid_selected_indexes[0]
    if len(valid_selected_indexes) > 1:
        return None

    if normalized_count == 1:
        return 0
    return None

def build_result_display_name(path_text: object) -> str:
    raw = str(path_text or '').strip()
    if not raw:
        return ''
    if '\\' in raw or (len(raw) >= 2 and raw[1] == ':'):
        return ntpath.basename(raw) or raw
    return Path(raw).name or raw


def build_xtc_display_name(path_text: object) -> str:
    return build_result_display_name(path_text)


def build_xtc_source_payload(path_text: object, display_name: object = None) -> dict[str, str]:
    normalized_path = str(path_text or '').strip()
    resolved_display_name = (
        str(display_name).strip()
        if display_name is not None
        else build_xtc_display_name(normalized_path)
    )
    return {
        'path_text': normalized_path,
        'display_name': resolved_display_name,
    }


def build_xtc_source_document_payload(
    source_payload: Mapping[str, object],
    document_payload: Mapping[str, object],
) -> dict[str, object]:
    payload: dict[str, object] = dict(source_payload)
    payload.update(dict(document_payload))
    return payload


def build_results_summary_message(
    summary_lines: Sequence[str],
    entry_count: int,
    fallback: str = '',
    language: object = 'ja',
) -> str:
    normalized_lines = [translate_ui_text(str(line).strip(), language) for line in summary_lines if str(line).strip()]
    if normalized_lines:
        return ' / '.join(normalized_lines)
    if entry_count > 0:
        return f'Saved files: {entry_count}' if _is_english_ui(language) else f'保存ファイル: {entry_count} 件'
    return translate_ui_text(str(fallback or '').strip(), language)
