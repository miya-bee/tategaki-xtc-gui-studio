from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def _coerce_nonnegative_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, int(value))
    if isinstance(value, float):
        if value != value:
            return max(0, int(default))
        return max(0, int(value))
    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            value = bytes(value).decode('utf-8', errors='ignore')
        except Exception:
            return max(0, int(default))
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return max(0, int(default))
        try:
            return max(0, int(normalized, 10))
        except (TypeError, ValueError, OverflowError):
            try:
                return max(0, int(float(normalized)))
            except (TypeError, ValueError, OverflowError):
                return max(0, int(default))
    return max(0, int(default))




def _coerce_bool_value(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        if value != value:
            return bool(default)
        return value != 0.0
    if isinstance(value, (bytes, bytearray, memoryview)):
        try:
            value = bytes(value).decode('utf-8', errors='ignore')
        except Exception:
            return bool(default)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return bool(default)
        if normalized in {'1', 'true', 'yes', 'on', 'enabled'}:
            return True
        if normalized in {'0', 'false', 'no', 'off', 'disabled'}:
            return False
        return bool(default)
    return bool(default)

def build_settings_section_plan(title: object, *, object_name: str = 'settingsSection') -> dict[str, str]:
    return {
        'title': str(title or '').strip(),
        'object_name': str(object_name or 'settingsSection').strip() or 'settingsSection',
    }


def build_left_settings_container_plan() -> dict[str, Any]:
    return {
        'container_object_name': 'leftSettingsContainer',
        'contents_margins': (10, 9, 10, 9),
        'spacing': 5,
        'splitter_children_collapsible': False,
        'splitter_handle_width': 5,
        'splitter_top_stretch_factor': 3,
        'splitter_bottom_stretch_factor': 1,
        'scroll_widget_resizable': True,
        'scroll_frame_shape': 'no_frame',
        'scroll_horizontal_scroll_bar_policy': 'always_off',
        'bottom_separator_frame_shape': 'hline',
        'bottom_separator_object_name': 'leftSettingsBottomSep',
        'bottom_separator_height': 1,
        'bottom_panel_min_height': 92,
    }


def build_left_settings_section_keys(*, include_behavior: object = False) -> tuple[str, ...]:
    section_keys = ('preset', 'font', 'image', 'display', 'fileviewer')
    if _coerce_bool_value(include_behavior):
        return section_keys + ('behavior',)
    return section_keys


def _normalize_margins(margins: object, default: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if isinstance(margins, (list, tuple)) and len(margins) == 4:
        return (
            _coerce_nonnegative_int(margins[0], default=default[0]),
            _coerce_nonnegative_int(margins[1], default=default[1]),
            _coerce_nonnegative_int(margins[2], default=default[2]),
            _coerce_nonnegative_int(margins[3], default=default[3]),
        )
    return default


def _normalize_optional_size_pair(value: object) -> tuple[int, int] | None:
    if isinstance(value, (list, tuple)) and len(value) == 2:
        width = _coerce_nonnegative_int(value[0])
        height = _coerce_nonnegative_int(value[1])
        if width > 0 and height > 0:
            return (width, height)
    return None


def build_left_settings_section_layout_plan(section_key: object) -> dict[str, Any]:
    key = str(section_key or '').strip().lower()
    defaults: dict[str, dict[str, Any]] = {
        'font': {
            'title': '出力・フォント・組版',
            'contents_margins': (8, 12, 8, 7),
            'spacing': 6,
        },
        'display': {
            'title': 'プレビュー',
            'contents_margins': (8, 14, 8, 8),
            'spacing': 8,
        },
        'fileviewer': {
            'title': 'ファイルビューワー',
            'contents_margins': (8, 10, 8, 8),
            'spacing': 6,
        },
        'image': {
            'title': '画像処理',
            'contents_margins': (8, 12, 8, 7),
            'spacing': 5,
        },
        'preset': {
            'title': 'プリセット',
            'contents_margins': (8, 14, 8, 0),
            'spacing': 3,
            'row_spacing': 8,
        },
        'behavior': {
            'title': 'その他オプション',
            'contents_margins': (8, 14, 8, 8),
            'spacing': 6,
        },
    }
    section = defaults.get(key, {'title': str(section_key or '').strip(), 'contents_margins': (8, 12, 8, 7), 'spacing': 6})
    return {
        'section_key': key,
        'title': str(section.get('title', '') or '').strip(),
        'contents_margins': _normalize_margins(section.get('contents_margins'), (8, 12, 8, 7)),
        'spacing': _coerce_nonnegative_int(section.get('spacing'), default=6),
        'row_spacing': _coerce_nonnegative_int(section.get('row_spacing'), default=_coerce_nonnegative_int(section.get('spacing'), default=6)),
    }


def build_font_section_plan() -> dict[str, Any]:
    return {
        'browse_button_text': '参照',
        'format_kinsoku_row_spacing': 6,
        'output_profile_row_spacing': 6,
        'kinsoku_row_spacing': 6,
        'margin_rows_spacing': 2,
        'margin_pair_spacing': 16,
    }


def build_display_section_plan() -> dict[str, Any]:
    return {
        'profile_items': (
            ('Xteink X4', 'x4'),
            ('Xteink X3', 'x3'),
            ('Custom', 'custom'),
        ),
        'profile_combo_min_width': 130,
        'calibration_label_text': '実寸補正',
        'calibration_button_size': (24, 24),
        'calibration_button_object_name': 'stepBtn',
        'calibration_down_text': '−',
        'calibration_up_text': '+',
        'calibration_spin_minimum': 50,
        'calibration_spin_maximum': 300,
        'calibration_spin_step': 5,
        'calibration_spin_accelerated': True,
        'calibration_spin_button_symbols': 'no_buttons',
        'calibration_spin_default': 100,
        'calibration_spin_suffix': '%',
        'calibration_spin_width': 62,
        'calibration_help_text': '実寸補正は右ペインの倍率UIで調整します。',
        'custom_size_row_margins': (0, 0, 0, 0),
        'custom_size_row_spacing': 8,
        'custom_size_pair_spacing': 8,
        'custom_width_label': '幅',
        'custom_height_label': '高さ',
        'preview_page_limit_label': '更新対象',
        'preview_page_limit_width': 68,
        'preview_page_limit_unit_text': 'ページ',
        'preview_page_limit_unit_object_name': 'dimLabel',
        'preview_update_button_text': 'プレビュー更新',
        'preview_update_button_object_name': 'smallBtn',
        'preview_status_text': '',
        'preview_status_object_name': 'hintLabel',
        'preview_status_min_width': 260,
        'preview_status_help_spacing': 4,
        'preview_update_help_text': 'ファイル読込時にプレビューを自動生成します。設定変更後は自動再生成せず、［プレビュー更新］を押した時点で再生成します。プレビュー上限を増やすほど確認範囲は広がりますが、読込と再描画は重くなります。',
    }


def build_file_viewer_section_plan() -> dict[str, Any]:
    return {
        'open_xtc_button_text': 'XTC/XTCHを開く',
        'open_xtc_button_object_name': 'smallBtn',
        'open_xtc_trailing_stretch': True,
        'open_xtc_help_text': '既存の .xtc / .xtch ファイルを右ペインの実機ビューへ読み込んで確認します。',
    }


def build_image_section_plan() -> dict[str, Any]:
    return {
        'night_mode_text': '白黒反転（出力）',
        'night_mode_spacing': 16,
        'dither_text': 'ディザリング',
        'dither_checked_default': False,
        'dither_spacing': 16,
        'threshold_label': 'しきい値',
        'threshold_enabled': False,
        'threshold_help_spacing': 6,
        'glyph_position_row_spacing': 6,
        'glyph_position_group_spacing': 8,
        'glyph_position_combo_width': 92,
        'closing_bracket_position_combo_width': 92,
        'wave_dash_row_spacing': 6,
        'wave_dash_group_spacing': 8,
        'wave_dash_drawing_combo_width': 108,
        'wave_dash_position_combo_width': 92,
        'help_text': '白黒反転（出力）: 白と黒を入れ替えて出力します。プレビューにも反映されます。しきい値: 白と黒の分かれ目を調整します。ディザリング: 粒状感と引き換えに濃淡感を残します。',
        'trailing_stretch': True,
    }


def build_behavior_section_plan() -> dict[str, Any]:
    return {
        'open_folder_text': '完了後フォルダを開く',
        'open_folder_checked_default': True,
        'open_folder_row_stretch': True,
        'output_conflict_label': '同名出力',
        'output_conflict_help_text': '保存先に同名の .xtc / .xtch があるときの動作を選びます。自動連番: foo(1).xtc 形式で保存 / 上書き: 既存ファイルを置き換え / エラー: そのファイルを保存せずエラーとして記録します。',
    }


def build_preset_section_plan(*, minimum_button_width: object = 104) -> dict[str, Any]:
    return {
        'row_spacing': 8,
        'apply_button_text': 'プリセット適用',
        'apply_tooltip': '選択中のプリセットを現在の組版へ反映',
        'save_button_text': '組版保存',
        'save_tooltip': '現在の組版設定をこのプリセットへ上書き保存',
        'button_object_name': 'smallBtn',
        'button_min_width': _coerce_nonnegative_int(minimum_button_width, default=104) or 104,
        'combo_width': 294,
        'combo_max_width': 294,
        'summary_text': '',
        'summary_label_object_name': 'presetSummaryLabel',
        'summary_label_word_wrap': True,
        'summary_label_alignment': 'left_top',
    }

def build_uniform_button_row_plan(width_candidates: Iterable[object], *, minimum_width: int = 0) -> dict[str, int]:
    resolved_minimum = _coerce_nonnegative_int(minimum_width)
    resolved_width = resolved_minimum
    for candidate in width_candidates:
        resolved_width = max(resolved_width, _coerce_nonnegative_int(candidate))
    return {
        'button_min_width': resolved_width,
    }




def build_top_bar_plan(*, path_button_width: object = 128) -> dict[str, Any]:
    return {
        'bar_height': 56,
        'contents_margins': (16, 0, 12, 0),
        'spacing': 10,
        'path_button_width': _coerce_nonnegative_int(path_button_width, default=136) or 136,
        'file_button_text': 'ファイルを開く...',
        'file_button_tooltip': '1つのファイルを開いて変換します',
        'folder_button_text': '保存先を選ぶ...',
        'folder_button_tooltip': '変換後のXTC / XTCH の保存先を選びます',
        'folder_batch_button_text': 'フォルダ一括変換...',
        'folder_batch_button_width': 152,
        'folder_batch_button_tooltip': 'フォルダ内の複数ファイルをまとめて変換します',
        'top_buttons_help_text': '上部ボタンの使い分け\n\n1) ファイルを開く...\n1つのファイルだけを開いて変換するときに使います。TXT / Markdown / EPUB / 画像などを個別に確認したい場合はこちらです。\n\n2) 保存先を選ぶ...\n変換後の XTC / XTCH を保存するフォルダを選びます。単体変換では、ここで選んだ場所に出力されます。\n\n3) フォルダ一括変換...\nフォルダ内の複数ファイルをまとめて変換するときに使います。サブフォルダも対象にしたい場合や、フォルダ構造を保って出力したい場合はこちらです。\n\n迷ったときの目安\n・1冊 / 1ファイルだけ試す → ファイルを開く...\n・保存場所を変えたい → 保存先を選ぶ...\n・複数ファイルをまとめて処理したい → フォルダ一括変換...',
        'top_buttons_help_title': '上部ボタンの使い分け',
        'top_buttons_help_tooltip': '上部3ボタンの使い分け',
        'target_placeholder': '変換対象のファイル / フォルダ',
        'run_button_text': '▶  変換実行',
        'run_button_width': 130,
        'stop_button_text': '■  停止',
        'stop_button_width': 90,
        'panel_button_text': '≡',
        'panel_button_size': (36, 36),
        'panel_button_tooltip': '左パネルの表示/非表示',
        'help_button_text': '?',
        'help_button_size': (36, 36),
        'help_button_tooltip': '使い方の流れ',
        'settings_button_text': '⚙',
        'settings_button_size': (36, 36),
        'settings_button_tooltip': '表示設定',
    }


def build_view_toggle_bar_plan() -> dict[str, Any]:
    return {
        'object_name': 'viewToggleBar',
        'bar_height': 88,
        'contents_margins': (12, 4, 12, 4),
        'spacing': 6,
        'row_spacing': 2,
        'bottom_row_spacing': 6,
        'display_toggle_spacing': 10,
        'top_separator_object_name': 'topSep',
        'preview_zoom_spacing': 8,
        'top_row_contents_margins': (0, 0, 0, 0),
        'bottom_row_contents_margins': (0, 0, 0, 0),
        'font_view_text': 'フォントビュー',
        'device_view_text': '実機ビュー',
        'view_button_object_name': 'viewToggleBtn',
        'view_button_focus_policy': 'no_focus',
        'view_button_checkable': True,
        'font_view_checked_default': True,
        'device_view_checked_default': False,
        'help_text': 'フォントビュー: 文字サイズ・余白・ルビの見え方を調整するときに使います。\n実機ビュー: 変換後のXTCをページ送りしながら実機に近い形で確認します。',
        'preview_zoom_label_text': '表示倍率',
        'preview_zoom_actual_size_label_text': '実寸補正',
        'preview_zoom_normal_tooltip': 'フォントビュー（実寸近似OFF）と実機ビューの表示倍率です。',
        'preview_zoom_actual_size_tooltip': '実寸近似ON: 実機サイズに合わせる補正倍率です。',
        'preview_zoom_min': 50,
        'preview_zoom_max': 300,
        'preview_zoom_step': 10,
        'preview_zoom_default': 100,
        'preview_zoom_button_size': (24, 24),
        'preview_zoom_button_object_name': 'stepBtn',
        'preview_zoom_down_text': '−',
        'preview_zoom_up_text': '+',
        'preview_zoom_spin_width': 78,
        'preview_zoom_spin_accelerated': True,
        'preview_zoom_spin_button_symbols': 'no_buttons',
        'preview_zoom_spin_suffix': '%',
        'preview_zoom_tooltip': 'フォントビュー（実寸近似OFF）と実機ビューの表示倍率です。実寸近似ONでは実寸補正として使います。',
    }


def build_preview_display_toggle_plan() -> dict[str, Any]:
    return {
        'actual_size_text': '実寸近似',
        'actual_size_object_name': 'viewToggleBtn',
        'actual_size_checkable': True,
        'actual_size_focus_policy': 'no_focus',
        'actual_size_help_text': (
            '実寸近似: PC画面上の表示サイズを、選択中の機種の実物サイズに近づける表示モードです。\n'
            '実機ビューで、端末に表示したときのおおよその大きさを確認したい場合に使います。\n'
            'ONにすると右ペインの倍率欄は「実寸補正」に切り替わります。\n'
            '表示が実物より大きい/小さい場合は、この実寸補正を調整してください。\n'
            'OFFでは右ペイン倍率は通常の表示ズームとして働きます。'
        ),
        'guide_text': 'ガイド',
        'guide_object_name': 'previewToolbarToggle',
        'guide_focus_policy': 'no_focus',
        'guide_checked_default': True,
        'guide_help_text': (
            'ガイド: 右ペインのプレビューに、余白や非描画域の目安線を重ねて表示します。\n'
            '本文が端に寄りすぎていないか、余白設定が意図通りかを確認するときに使います。\n'
            'ONにすると補助線を表示し、OFFにすると実際の見た目に近い状態で確認できます。\n'
            '変換結果そのものを書き換える機能ではなく、確認用の表示補助です。'
        ),
        'toggle_spacing': 18,
    }


def build_nav_bar_plan() -> dict[str, Any]:
    return {
        'object_name': 'navBar',
        'bar_height': 48,
        'contents_margins': (12, 0, 12, 0),
        'spacing': 8,
        'nav_button_side_spacing': 10,
        'nav_section_separator_object_name': 'navSectionSep',
        'current_xtc_label_text': '表示中: なし',
        'current_xtc_label_object_name': 'hintLabel',
        'current_xtc_label_min_width': 0,
        'current_xtc_label_max_width': 220,
        'nav_reverse_text': 'ボタン反転',
        'nav_reverse_object_name': 'navToggle',
        'nav_reverse_focus_policy': 'no_focus',
        'page_label_text': 'ページ',
        'page_input_minimum': 0,
        'page_input_maximum': 0,
        'page_input_empty_minimum': 0,
        'page_input_empty_maximum': 0,
        'page_input_active_minimum': 1,
        'page_input_button_symbols': 'no_buttons',
        'page_input_keyboard_tracking': False,
        'page_input_width': 60,
        'page_total_label_text': '/ 0',
        'page_total_label_format': '/ {total}',
        'page_total_label_object_name': 'hintLabel',
        'nav_button_object_name': 'navBtn',
        'nav_button_focus_policy': 'no_focus',
        'prev_button_text': '前',
        'next_button_text': '次',
    }


def build_right_preview_panel_plan() -> dict[str, Any]:
    return {
        'panel_contents_margins': (0, 0, 0, 0),
        'panel_spacing': 0,
        'top_separator_frame_shape': 'hline',
        'top_separator_object_name': 'topSep',
        'font_page_margins': (8, 8, 8, 8),
        'font_preview_min_size': (360, 600),
        'font_preview_alignment': 'center',
        'font_preview_word_wrap': True,
        'font_scroll_widget_resizable': False,
        'font_scroll_alignment': 'center',
        'font_scroll_frame_shape': 'no_frame',
        'device_page_margins': (8, 8, 8, 8),
        'device_preview_min_size': (360, 600),
        'device_scroll_widget_resizable': False,
        'device_scroll_alignment': 'center',
        'device_scroll_frame_shape': 'no_frame',
        'device_scroll_focus_policy': 'strong_focus',
        'preview_stack_index': 0,
    }


def build_bottom_panel_layout_plan() -> dict[str, Any]:
    return {
        'panel_object_name': 'bottomPanel',
        'panel_contents_margins': (0, 0, 0, 0),
        'panel_spacing': 0,
        'content_object_name': 'bottomPanelContent',
        'content_contents_margins': (0, 0, 0, 0),
        'content_spacing': 0,
        'external_scrollbar_object_name': 'bottomPanelScrollBar',
        'external_scrollbar_single_step': 20,
        'status_strip_object_name': 'statusStrip',
        'status_strip_height': 34,
        'status_strip_margins': (14, 0, 14, 0),
        'status_strip_spacing': 10,
        'bottom_separator_frame_shape': 'hline',
        'bottom_separator_object_name': 'bottomPanelSep',
        'results_tab_title': '変換結果',
        'log_tab_title': 'ログ',
    }


def build_log_tab_plan(*, log_path: object = '') -> dict[str, Any]:
    return {
        'contents_margins': (6, 6, 6, 6),
        'spacing': 6,
        'top_row_margins': (0, 0, 0, 0),
        'top_row_spacing': 8,
        'path_label_text': '保存先:',
        'path_label_object_name': 'logPathLabel',
        'open_folder_button_text': 'ログフォルダを開く',
        'log_path_edit_read_only': True,
        'log_edit_read_only': True,
        'log_path': str(log_path or '').strip(),
    }

def build_bottom_status_strip_plan(
    *,
    badge_text: object = '待機中',
    progress_text: object = '待機中です。',
    progress_minimum: object = 0,
    progress_maximum: object = 1,
    progress_value: object = 0,
    progress_max_width: object = 200,
) -> dict[str, Any]:
    minimum = _coerce_nonnegative_int(progress_minimum)
    maximum = max(minimum, _coerce_nonnegative_int(progress_maximum, default=minimum))
    value = _coerce_nonnegative_int(progress_value, default=minimum)
    value = max(minimum, min(value, maximum))
    return {
        'badge_text': str(badge_text or '').strip() or '待機中',
        'progress_text': str(progress_text or '').strip() or '待機中です。',
        'progress_minimum': minimum,
        'progress_maximum': maximum,
        'progress_value': value,
        'progress_max_width': max(1, _coerce_nonnegative_int(progress_max_width, default=200)),
        'badge_object_name': 'badge',
        'progress_text_visible': False,
        'progress_fixed_height': 6,
        'progress_label_object_name': 'hintLabel',
    }


def build_results_tab_plan(*, summary_text: object = '変換結果の概要をここに表示します。') -> dict[str, Any]:
    return {
        'contents_margins': (6, 6, 6, 6),
        'spacing': 4,
        'summary_text': str(summary_text or '').strip() or '変換結果の概要をここに表示します。',
        'summary_label_object_name': 'hintLabel',
        'summary_label_word_wrap': True,
        'results_list_selection_mode': 'single_selection',
    }




def build_row_layout_plan(
    *,
    spacing: object = 0,
    contents_margins: object = (0, 0, 0, 0),
    add_stretch: object = False,
) -> dict[str, Any]:
    return {
        'spacing': _coerce_nonnegative_int(spacing),
        'contents_margins': _normalize_margins(contents_margins, (0, 0, 0, 0)),
        'add_stretch': _coerce_bool_value(add_stretch),
    }


def build_labeled_widget_row_plan(
    labels: Iterable[object],
    *,
    spacing: object = 3,
    pair_spacing: object = 6,
    label_object_name: object = 'dimLabel',
    trailing_stretch: object = True,
) -> dict[str, Any]:
    normalized_labels = tuple(str(label or '').strip() for label in labels)
    return {
        'labels': normalized_labels,
        'spacing': _coerce_nonnegative_int(spacing, default=3),
        'pair_spacing': _coerce_nonnegative_int(pair_spacing, default=6),
        'label_object_name': str(label_object_name or 'dimLabel').strip() or 'dimLabel',
        'trailing_stretch': _coerce_bool_value(trailing_stretch, default=True),
    }


def build_margin_rows_plan(
    *,
    row_spacing: object = 2,
    pair_spacing: object = 16,
) -> dict[str, Any]:
    return {
        'container_margins': (0, 0, 0, 0),
        'row_spacing': _coerce_nonnegative_int(row_spacing, default=2),
        'pair_spacing': _coerce_nonnegative_int(pair_spacing, default=16),
        'row_contents_margins': (0, 0, 0, 0),
        'top_labels': ('上余白', '下余白'),
        'side_labels': ('右余白', '左余白'),
        'trailing_stretch': True,
    }


def build_button_widget_plan(
    text: object,
    *,
    object_name: object = '',
    tooltip: object = '',
    fixed_width: object | None = None,
    minimum_width: object | None = None,
    fixed_size: object | None = None,
    checkable: object = False,
    checked: object = False,
    enabled: object = True,
    focus_policy: object = 'default',
) -> dict[str, Any]:
    normalized_focus_policy = str(focus_policy or 'default').strip().lower() or 'default'
    if normalized_focus_policy not in {'default', 'no_focus'}:
        normalized_focus_policy = 'default'
    return {
        'text': str(text or '').strip(),
        'object_name': str(object_name or '').strip(),
        'tooltip': str(tooltip or '').strip(),
        'fixed_width': _coerce_nonnegative_int(fixed_width) or None,
        'minimum_width': _coerce_nonnegative_int(minimum_width) or None,
        'fixed_size': _normalize_optional_size_pair(fixed_size),
        'checkable': _coerce_bool_value(checkable),
        'checked': _coerce_bool_value(checked) if _coerce_bool_value(checkable) else False,
        'enabled': _coerce_bool_value(enabled, default=True),
        'focus_policy': normalized_focus_policy,
    }

