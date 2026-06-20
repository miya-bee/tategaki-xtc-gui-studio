from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel, QWidget

import tategakiXTC_gui_layouts as gui_layouts
from tategakiXTC_gui_studio_constants import (
    CLOSING_BRACKET_POSITION_MODE_OPTIONS,
    GLYPH_POSITION_MODE_OPTIONS,
    KINSOKU_MODE_OPTIONS,
    LATIN_ORIENTATION_MODE_OPTIONS,
    OPENING_BRACKET_INDENT_MODE_OPTIONS,
    DEFAULT_UI_LANGUAGE,
    DEVICE_PROFILES,
    OUTPUT_CONFLICT_OPTIONS,
    OUTPUT_FORMAT_LABELS,
    PROGRESS_BAR_POSITION_OPTIONS,
    TATECHUYOKO_DIGIT_MODE_OPTIONS,
    UI_LANGUAGE_OPTIONS,
    WAVE_DASH_DRAWING_MODE_OPTIONS,
    WAVE_DASH_POSITION_MODE_OPTIONS,
)
from tategakiXTC_gui_studio_widgets import FontPopupTopComboBox


def _section_output(self: Any):
    font_plan = self._localized_plan(gui_layouts.build_font_section_plan())
    display_plan = self._localized_plan(gui_layouts.build_display_section_plan())
    box, lay, _section_plan = self._build_section_box_layout(
        'output',
        '出力先',
        default_margins=(8, 12, 8, 7),
        default_spacing=6,
    )

    output_row = self._make_hbox_layout_from_plan(
        gui_layouts.build_row_layout_plan(spacing=font_plan.get('output_profile_row_spacing', 6))
    )
    output_row.addWidget(self._dim_label(self._ui_text('機種')))
    self.profile_combo = QComboBox()
    for label, key in tuple(display_plan.get('profile_items', ())):
        self.profile_combo.addItem(str(label), key)
    self.profile_combo.setMinimumWidth(self._plan_int_value(display_plan, 'profile_combo_min_width', 130))
    self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
    output_row.addWidget(self.profile_combo)
    output_row.addWidget(self._help_icon_button(self._ui_text('機種: 選ぶと解像度が自動設定されます。\nCustom: 手動で幅・高さを指定します。')))
    output_row.addSpacing(12)

    output_row.addWidget(self._dim_label(self._ui_text('出力形式')))
    self.output_format_combo = QComboBox()
    for key, label in OUTPUT_FORMAT_LABELS.items():
        self.output_format_combo.addItem(self._ui_text(label), key)
    self.output_format_combo.currentIndexChanged.connect(self._schedule_live_preview_refresh_from_signal)
    self.output_format_combo.currentIndexChanged.connect(lambda _i, self=self: self.save_ui_state())
    output_row.addWidget(self.output_format_combo)
    output_row.addWidget(self._help_icon_button(self._ui_text('XTC: 2 階調（白黒）で保存します。\nXTCH: 4 階調（白黒 4 段階）で保存します。\n使い分け: 通常の白黒表示なら XTC、階調を残したい画像寄りの用途では XTCH を選びます。')))
    output_row.addStretch(1)
    lay.addLayout(output_row)

    row_custom = self._make_hbox_layout_from_plan()
    self.width_spin = self._spin(240, 2000, 480)
    self.height_spin = self._spin(240, 2000, 800)
    self.custom_size_row = QWidget()
    self.custom_size_row.setVisible(False)
    cs_lay = QHBoxLayout(self.custom_size_row)
    cs_lay.setContentsMargins(*tuple(display_plan.get('custom_size_row_margins', (0, 0, 0, 0))))
    cs_lay.setSpacing(self._plan_int_value(display_plan, 'custom_size_row_spacing', 8))
    cs_lay.addWidget(self._dim_label(str(display_plan.get('custom_width_label', '幅'))))
    cs_lay.addWidget(self.width_spin)
    cs_lay.addSpacing(self._plan_int_value(display_plan, 'custom_size_pair_spacing', 8))
    cs_lay.addWidget(self._dim_label(str(display_plan.get('custom_height_label', '高さ'))))
    cs_lay.addWidget(self.height_spin)
    row_custom.addWidget(self.custom_size_row)
    row_custom.addStretch(1)
    lay.addLayout(row_custom)

    self.width_spin.valueChanged.connect(self._on_custom_size_changed)
    self.height_spin.valueChanged.connect(self._on_custom_size_changed)
    return box


def _section_composition(self: Any):
    font_plan = self._localized_plan(gui_layouts.build_font_section_plan())
    image_plan = self._localized_plan(gui_layouts.build_image_section_plan())
    box, lay, _section_plan = self._build_section_box_layout(
        'composition',
        '組版',
        default_margins=(8, 12, 8, 7),
        default_spacing=6,
    )

    font_row = self._make_hbox_layout_from_plan()
    self.font_combo = FontPopupTopComboBox()
    self._populate_font_combo()
    self._apply_default_font_selection()
    self.font_combo.currentIndexChanged.connect(self.on_font_changed)
    font_row.addWidget(self.font_combo, 2)
    browse_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            font_plan.get('browse_button_text', '参照'),
            object_name='smallBtn',
        ),
        self.select_font_file,
    )
    font_row.addWidget(browse_btn)
    font_row.addStretch(1)
    lay.addLayout(font_row)

    self.font_size_spin = self._spin(18, 72, 26, compact=True, buttons=True)
    self.ruby_size_spin = self._spin(8, 32, 12, compact=True, buttons=True)
    self.line_spacing_spin = self._spin(24, 80, 44, compact=True, buttons=True)
    lay.addLayout(self._spin_row([
        (self._ui_text('本文'), self.font_size_spin),
        (self._ui_text('ルビ'), self.ruby_size_spin),
        (self._ui_text('行間'), self.line_spacing_spin),
    ]))

    self.margin_t_spin = self._spin(0, 80, 12, compact=True, buttons=True)
    self.margin_b_spin = self._spin(0, 80, 14, compact=True, buttons=True)
    self.margin_r_spin = self._spin(0, 80, 12, compact=True, buttons=True)
    self.margin_l_spin = self._spin(0, 80, 12, compact=True, buttons=True)
    lay.addWidget(self._build_margin_rows())

    self._ensure_behavior_controls()
    composition_group_spacing = self._plan_int_value(font_plan, 'composition_group_spacing', 8)
    page_option_group_spacing = self._plan_int_value(font_plan, 'page_option_group_spacing', 12)
    page_option_inner_spacing = self._plan_int_value(font_plan, 'page_option_inner_spacing', 6)
    composition_row = self._make_hbox_layout_from_plan(
        gui_layouts.build_row_layout_plan(spacing=font_plan.get('format_kinsoku_row_spacing', 6))
    )
    composition_row.addWidget(self._dim_label(self._ui_text('縦中横')))
    self.tatechuyoko_digit_mode_combo.setMaximumWidth(self._plan_int_value(font_plan, 'tatechuyoko_digit_mode_combo_width', 78))
    composition_row.addWidget(self.tatechuyoko_digit_mode_combo)
    composition_row.addWidget(self._help_icon_button(self._ui_text('半角数字を1文字分に横組みする上限です。\n4文字: 4桁までを縦中横にします。\n3文字: 3桁までを縦中横にします。\n2文字: 2桁までを縦中横にします。\n無し: 半角数字を縦中横にしません。')))
    composition_row.addSpacing(composition_group_spacing)
    composition_row.addWidget(self._dim_label(self._ui_text('欧文表示')))
    self.latin_orientation_combo.setMaximumWidth(self._plan_int_value(font_plan, 'latin_orientation_combo_width', 78))
    composition_row.addWidget(self.latin_orientation_combo)
    composition_row.addWidget(self._help_icon_button(self._ui_text('欧文表示: 縦組みは従来どおり半角英字を縦方向に組みます。\n横組みは短い半角英字・英文句を横書き run として扱い、縦書き本文内へ配置します。')))
    composition_row.addSpacing(composition_group_spacing)
    composition_row.addWidget(self._dim_label(self._ui_text('行頭鍵括弧')))
    self.opening_bracket_indent_combo.setMaximumWidth(self._plan_int_value(font_plan, 'opening_bracket_indent_combo_width', 96))
    composition_row.addWidget(self.opening_bracket_indent_combo)
    composition_row.addWidget(self._help_icon_button(self._ui_text('行頭鍵括弧: 空白なしは従来どおり行頭に「/『を置きます。\n1文字下げは岩波文庫のように行頭鍵括弧の前へ1文字分の空きを入れます。')))
    composition_row.addStretch(1)
    lay.addLayout(composition_row)

    page_row = self._make_hbox_layout_from_plan()
    page_row.addWidget(self._dim_label(self._ui_text('禁則処理')))
    self.kinsoku_mode_combo.setMaximumWidth(self._plan_int_value(font_plan, 'kinsoku_mode_combo_width', 74))
    page_row.addWidget(self.kinsoku_mode_combo)
    page_row.addWidget(self._help_icon_button(self._ui_text('オフ: 禁則処理を行わず機械的に流し込みます。\n簡易: 行頭禁則・行末禁則・句読点のぶら下げのみ行います。\n標準: 連続約物や閉じ括弧＋句読点のまとまりも含めて、現在の禁則処理を有効にします。')))
    page_row.addSpacing(page_option_group_spacing)
    self.page_number_check = QCheckBox(self._ui_text('ページ番号'))
    self.page_number_check.setChecked(False)
    page_row.addWidget(self.page_number_check)
    page_row.addSpacing(page_option_inner_spacing)
    page_row.addWidget(self._dim_label(self._ui_text('サイズ')))
    self.page_number_font_size_spin = self._spin(1, 29, 12, compact=True, buttons=True)
    self.page_number_font_size_spin.setEnabled(False)
    page_row.addWidget(self.page_number_font_size_spin)
    page_row.addWidget(self._help_icon_button(self._ui_text('ページ番号: チェックすると各ページ右下に「現在ページ/総ページ」を表示します。\nサイズ: 1〜29 の数値を指定します。30以上はエラーです。\nページ番号ON時は、下余白を「サイズ+1」以上に自動確保します。')))
    page_row.addSpacing(page_option_group_spacing)
    self.progress_bar_check = QCheckBox(self._ui_text('進捗バー'))
    self.progress_bar_check.setChecked(False)
    page_row.addWidget(self.progress_bar_check)
    page_row.addSpacing(page_option_inner_spacing)
    page_row.addWidget(self._dim_label(self._ui_text('位置')))
    self.progress_bar_position_combo = QComboBox()
    for key, label in PROGRESS_BAR_POSITION_OPTIONS:
        self.progress_bar_position_combo.addItem(self._ui_text(label), key)
    self._set_combo_to_data(self.progress_bar_position_combo, 'center')
    self.progress_bar_position_combo.setMaximumWidth(self._plan_int_value(font_plan, 'progress_bar_position_combo_width', 88))
    self.progress_bar_position_combo.setEnabled(False)
    page_row.addWidget(self.progress_bar_position_combo)
    page_row.addWidget(self._help_icon_button(self._ui_text('進捗バー: チェックすると下部に読書位置を示す黒い横棒を表示します。\n位置: 下中央または下左を選べます。\n進捗バーON時は、下余白を最低10px程度に自動確保します。')))
    page_row.addStretch(1)
    self.page_number_check.toggled.connect(self.page_number_font_size_spin.setEnabled)
    self.page_number_check.toggled.connect(self.on_page_number_setting_changed)
    self.page_number_font_size_spin.valueChanged.connect(self.on_page_number_setting_changed)
    self.progress_bar_check.toggled.connect(self.progress_bar_position_combo.setEnabled)
    self.progress_bar_check.toggled.connect(self.on_progress_bar_setting_changed)
    self.progress_bar_position_combo.currentIndexChanged.connect(self.on_progress_bar_setting_changed)
    lay.addLayout(page_row)

    image_row = self._make_hbox_layout_from_plan()
    self.ruby_hide_check = QCheckBox(str(image_plan.get('ruby_hide_label', 'ルビ消し')))
    self.ruby_hide_check.setChecked(self._plan_bool_value(image_plan, 'ruby_hide_checked_default', False))
    self.ruby_hide_check.toggled.connect(self.on_ruby_hide_toggled)
    image_row.addWidget(self.ruby_hide_check)
    image_row.addSpacing(self._plan_int_value(image_plan, 'night_mode_spacing', 16))
    self.night_check = QCheckBox(str(image_plan.get('night_mode_text', '白黒反転')))
    self.night_check.toggled.connect(self.on_night_toggled)
    image_row.addWidget(self.night_check)
    image_row.addSpacing(self._plan_int_value(image_plan, 'night_mode_spacing', 16))
    self.dither_check = QCheckBox(str(image_plan.get('dither_text', 'ディザリング')))
    self.dither_check.setChecked(self._plan_bool_value(image_plan, 'dither_checked_default', False))
    self.dither_check.toggled.connect(self.on_dither_toggled)
    image_row.addWidget(self.dither_check)
    image_row.addSpacing(self._plan_int_value(image_plan, 'dither_spacing', 16))
    image_row.addWidget(self._dim_label(str(image_plan.get('threshold_label', 'しきい値'))))
    self.threshold_spin = self._spin(0, 255, 128, compact=True)
    self.threshold_spin.setEnabled(self._plan_bool_value(image_plan, 'threshold_enabled', False))
    self.threshold_spin.valueChanged.connect(self.on_threshold_changed)
    image_row.addWidget(self.threshold_spin)
    image_row.addSpacing(self._plan_int_value(image_plan, 'threshold_help_spacing', 6))
    image_row.addWidget(self._help_icon_button(str(image_plan.get('help_text', self._ui_text('ルビ消し: チェックした場合だけ、親文字は残したままルビを表示しない変換モードにします。\n白黒反転: 白と黒を入れ替えて出力します。プレビューにも反映されます。\nディザリング: 粒状感と引き換えに濃淡感を残します。\nしきい値: 白と黒の分かれ目を調整します。')))))
    if self._plan_bool_value(image_plan, 'trailing_stretch', True):
        image_row.addStretch(1)
    lay.addLayout(image_row)

    self.profile_hint = QLabel(DEVICE_PROFILES['x4'].tagline)
    self.profile_hint.setObjectName('hintLabel')
    self.profile_hint.setVisible(bool(DEVICE_PROFILES['x4'].tagline))
    lay.addWidget(self.profile_hint)

    for w in [
        self.font_size_spin, self.ruby_size_spin, self.line_spacing_spin,
    ]:
        w.valueChanged.connect(self._schedule_live_preview_refresh_from_signal)
        w.valueChanged.connect(lambda _v, self=self: self.save_ui_state())
    for w in [
        self.margin_t_spin, self.margin_b_spin, self.margin_r_spin, self.margin_l_spin,
    ]:
        w.valueChanged.connect(self.on_margin_changed)
    return box


def _section_position(self: Any):
    image_plan = self._localized_plan(gui_layouts.build_image_section_plan())
    box, lay, _section_plan = self._build_section_box_layout(
        'position',
        '位置補正',
        default_margins=(8, 12, 8, 7),
        default_spacing=5,
    )

    self._ensure_behavior_controls()
    image_glyph_position_row = self._make_hbox_layout_from_plan(
        gui_layouts.build_row_layout_plan(spacing=image_plan.get('glyph_position_row_spacing', 6))
    )
    glyph_combo_width = self._plan_int_value(image_plan, 'glyph_position_combo_width', 92)
    closing_bracket_combo_width = self._plan_int_value(image_plan, 'closing_bracket_position_combo_width', glyph_combo_width)
    glyph_group_spacing = self._plan_int_value(image_plan, 'glyph_position_group_spacing', 8)
    for combo in (self.punctuation_position_combo, self.ichi_position_combo, self.halfwidth_digit_position_combo, self.halfwidth_alpha_position_combo, self.middle_dot_position_combo, self.tatechuyoko_symbol_position_combo):
        combo.setMaximumWidth(glyph_combo_width)
    self.lower_closing_bracket_position_combo.setMaximumWidth(closing_bracket_combo_width)
    self._add_glyph_position_control(
        image_glyph_position_row,
        '句読点',
        self.punctuation_position_combo,
        '対象: ぶら下がり句読点のみです。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。',
    )
    image_glyph_position_row.addSpacing(glyph_group_spacing)
    self._add_glyph_position_control(
        image_glyph_position_row,
        '漢数字 一',
        self.ichi_position_combo,
        '対象: 文中すべての漢数字「一」です。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。',
    )
    image_glyph_position_row.addSpacing(glyph_group_spacing)
    self._add_glyph_position_control(
        image_glyph_position_row,
        '半角数字/記号',
        self.halfwidth_digit_position_combo,
        '対象: 文中の半角数字、数値記号（/ . , : ; + - = % など）、縦中横の半角数字です。\n全角数字とルビ内数字は対象外です。\n!! / !? / ?? などの記号ペアは「縦中横記号」で補正します。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。',
    )
    image_glyph_position_row.addStretch(1)
    lay.addLayout(image_glyph_position_row)

    image_tatechuyoko_symbol_row = self._make_hbox_layout_from_plan(
        gui_layouts.build_row_layout_plan(spacing=image_plan.get('glyph_position_row_spacing', 6))
    )
    self.halfwidth_alpha_position_combo.setMaximumWidth(glyph_combo_width)
    self.tatechuyoko_symbol_position_combo.setMaximumWidth(glyph_combo_width)
    self._add_glyph_position_control(
        image_tatechuyoko_symbol_row,
        '半角英字',
        self.halfwidth_alpha_position_combo,
        '対象: 文中の半角英字（A-Z / a-z）です。\n半角数字、数値記号、全角英字、ルビ内英字は対象外です。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。',
    )
    image_tatechuyoko_symbol_row.addSpacing(glyph_group_spacing)
    self._add_glyph_position_control(
        image_tatechuyoko_symbol_row,
        '中黒',
        self.middle_dot_position_combo,
        '対象: 文中の中黒（・/･/·）です。\nフォントごとの差を抑えるため、実インク中心を本文の見た目中心へ合わせます。\n下補正強/弱: 標準より下へ寄せます。\n標準: 本文中心へ正規化して描画します。\n上補正弱/強: 標準より上へ寄せます。',
    )
    image_tatechuyoko_symbol_row.addSpacing(glyph_group_spacing)
    self._add_glyph_position_control(
        image_tatechuyoko_symbol_row,
        '縦中横記号',
        self.tatechuyoko_symbol_position_combo,
        '対象: 縦中横で描画される記号ペア（！？/？？/！！/？！/!?/??/!!/?!）のみです。\n数字の縦中横には影響しません。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。',
    )
    image_tatechuyoko_symbol_row.addSpacing(glyph_group_spacing)
    self._add_glyph_position_control(
        image_tatechuyoko_symbol_row,
        '下鍵括弧',
        self.lower_closing_bracket_position_combo,
        '対象: 閉じ鍵括弧（」/﹂）と二重閉じ鍵括弧（』/﹄）のみです。\n下補正強/弱: 標準より下へ寄せます。\n標準: これまでと同じ位置で描画します。\n上補正弱/強: 標準より上へ寄せます。',
    )
    image_tatechuyoko_symbol_row.addStretch(1)
    lay.addLayout(image_tatechuyoko_symbol_row)

    image_wave_dash_row = self._make_hbox_layout_from_plan(
        gui_layouts.build_row_layout_plan(spacing=image_plan.get('wave_dash_row_spacing', 6))
    )
    self.wave_dash_drawing_combo.setMaximumWidth(self._plan_int_value(image_plan, 'wave_dash_drawing_combo_width', 108))
    self.wave_dash_position_combo.setMaximumWidth(self._plan_int_value(image_plan, 'wave_dash_position_combo_width', 92))
    wave_dash_group_spacing = self._plan_int_value(image_plan, 'wave_dash_group_spacing', 8)
    image_wave_dash_row.addWidget(self._dim_label(self._ui_text('波線描画')))
    image_wave_dash_row.addWidget(self.wave_dash_drawing_combo)
    image_wave_dash_row.addWidget(self._help_icon_button(self._ui_text('対象: 波線系記号（～/〜/〰/~ など）の描画方式です。\n回転グリフ: フォントの質感を保って90度回転します。\n別描画: アプリ側で縦波線を描きます。\n自動フォールバック: 回転グリフに失敗した場合は別描画へ切り替えます。')))
    image_wave_dash_row.addSpacing(wave_dash_group_spacing)
    image_wave_dash_row.addWidget(self._dim_label(self._ui_text('波線位置')))
    image_wave_dash_row.addWidget(self.wave_dash_position_combo)
    image_wave_dash_row.addWidget(self._help_icon_button(self._ui_text('対象: 波線系記号の縦位置だけを補正します。\n標準: これまでの位置です。\n下補正弱/強: 標準より下へ寄せます。')))
    image_wave_dash_row.addStretch(1)
    lay.addLayout(image_wave_dash_row)

    return box


def _section_language(self: Any):
    language_plan = self._localized_plan(gui_layouts.build_language_section_plan())
    box, lay, section_plan = self._build_section_box_layout(
        'language',
        '表示言語 / Language',
        default_margins=(8, 12, 8, 8),
        default_spacing=5,
    )
    row = self._make_hbox_layout_from_plan(
        gui_layouts.build_row_layout_plan(
            spacing=self._plan_int_value(language_plan, 'row_spacing', self._plan_int_value(section_plan, 'row_spacing', 8))
        )
    )
    row.addWidget(self._dim_label(str(language_plan.get('label_text', '表示言語'))))
    self.language_combo = QComboBox()
    self.language_combo.setObjectName('languageCombo')
    for key, label in UI_LANGUAGE_OPTIONS:
        self.language_combo.addItem(self._ui_text(label), key)
    combo_width = self._plan_int_value(language_plan, 'combo_width', 170)
    if combo_width > 0:
        self.language_combo.setMinimumWidth(combo_width)
        self.language_combo.setMaximumWidth(combo_width)
    self.language_combo.setToolTip(str(language_plan.get('combo_tooltip', 'UI表示言語を選びます。変更は次回起動時に反映されます。')))
    self._set_language_combo_value(getattr(self, 'current_ui_language', self._initial_ui_language()))
    self.language_combo.currentIndexChanged.connect(self.on_language_combo_changed)
    row.addWidget(self.language_combo)
    row.addStretch(1)
    lay.addLayout(row)

    note = QLabel(str(language_plan.get('restart_note_text', '変更は次回起動時に反映されます。')))
    note.setObjectName(str(language_plan.get('restart_note_object_name', 'hintLabel')))
    note.setWordWrap(True)
    self.language_restart_note_label = note
    self._update_language_restart_note_label(getattr(self, 'current_ui_language', DEFAULT_UI_LANGUAGE))
    lay.addWidget(note)
    return box


def _section_preset(self: Any):
    preset_plan = self._localized_plan(gui_layouts.build_preset_section_plan(minimum_button_width=104))
    box, lay, section_plan = self._build_section_box_layout(
        'preset',
        'プリセット',
        default_margins=(8, 14, 8, 2),
        default_spacing=4,
    )
    self.preset_section_box = box

    self.preset_combo = QComboBox()
    for key, p in self.preset_definitions.items():
        self.preset_combo.addItem(p['button_text'], key)
    self.preset_combo.currentIndexChanged.connect(self.on_preset_selection_changed)
    preset_combo_width = self._plan_int_value(
        preset_plan,
        'combo_width',
        self._plan_int_value(preset_plan, 'combo_max_width', 260),
    )
    self.preset_combo.setMinimumWidth(preset_combo_width)
    self.preset_combo.setMaximumWidth(self._plan_int_value(preset_plan, 'combo_max_width', preset_combo_width))
    lay.addWidget(self.preset_combo)

    self.preset_apply_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            preset_plan.get('apply_button_text', 'プリセット\n読み込み'),
            object_name=preset_plan.get('button_object_name', 'smallBtn'),
            tooltip=preset_plan.get('apply_tooltip', '選択中のプリセットを現在の組版へ読み込みます'),
        ),
        self.apply_selected_preset,
    )

    self.preset_save_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            preset_plan.get('save_button_text', 'プリセット\n保存'),
            object_name=preset_plan.get('button_object_name', 'smallBtn'),
            tooltip=preset_plan.get('save_tooltip', '現在の組版設定をこのプリセットへ保存します'),
        ),
        self.save_selected_preset,
    )

    self.preset_rename_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            preset_plan.get('rename_button_text', '名称変更'),
            object_name=preset_plan.get('button_object_name', 'smallBtn'),
            tooltip=preset_plan.get('rename_tooltip', '選択中のプリセットの表示名を変更します'),
        ),
        self.rename_selected_preset,
    )

    preset_button_plan = gui_layouts.build_uniform_button_row_plan(
        [
            self.preset_apply_btn.sizeHint().width(),
            self.preset_save_btn.sizeHint().width(),
        ],
        minimum_width=self._plan_int_value(preset_plan, 'button_min_width', 104),
    )
    preset_button_width = self._plan_int_value(preset_button_plan, 'button_min_width', 104)
    button_row = self._make_hbox_layout_from_plan()
    button_row.setSpacing(self._plan_int_value(preset_plan, 'row_spacing', self._plan_int_value(section_plan, 'row_spacing', 8)))
    preset_button_height = self._plan_int_value(preset_plan, 'button_min_height', 44)
    for button in (self.preset_apply_btn, self.preset_save_btn):
        button.setMinimumWidth(preset_button_width)
        if preset_button_height > 0:
            button.setMinimumHeight(preset_button_height)
        button_row.addWidget(button)
    button_row.addStretch(1)
    lay.addLayout(button_row)

    rename_row = self._make_hbox_layout_from_plan()
    rename_row.setSpacing(self._plan_int_value(preset_plan, 'row_spacing', self._plan_int_value(section_plan, 'row_spacing', 8)))
    self.preset_rename_btn.setMinimumWidth(min(preset_combo_width, max(120, preset_button_width)))
    if preset_button_height > 0:
        self.preset_rename_btn.setMinimumHeight(max(32, preset_button_height - 8))
    rename_row.addWidget(self.preset_rename_btn)
    rename_row.addStretch(1)
    lay.addLayout(rename_row)

    self.preset_summary_label = QLabel(str(preset_plan.get('summary_text', '')))
    self.preset_summary_label.setObjectName(str(preset_plan.get('summary_label_object_name', 'presetSummaryLabel')))
    self.preset_summary_label.setWordWrap(
        self._plan_bool_value(preset_plan, 'summary_label_word_wrap', True)
    )
    self.preset_summary_label.setAlignment(
        self._plan_alignment_value(preset_plan, 'summary_label_alignment', 'left_top')
    )
    self.preset_summary_label.setContentsMargins(0, 0, 0, 0)
    self.preset_summary_label.setMargin(0)
    set_indent = getattr(self.preset_summary_label, 'setIndent', None)
    if callable(set_indent):
        set_indent(0)
    set_text_format = getattr(self.preset_summary_label, 'setTextFormat', None)
    if callable(set_text_format):
        set_text_format(Qt.PlainText)
    lay.addWidget(self.preset_summary_label)
    return box


def _make_position_mode_combo(self: Any, options, changed_slot) -> QComboBox:
    combo = QComboBox()
    for key, label in options:
        combo.addItem(self._ui_text(label), key)
    combo.currentIndexChanged.connect(changed_slot)
    return combo


def _make_glyph_position_combo(self: Any) -> QComboBox:
    return self._make_position_mode_combo(GLYPH_POSITION_MODE_OPTIONS, self._on_glyph_position_mode_changed)


def _add_glyph_position_control(self: Any, row, label: str, combo: QComboBox, help_text: str) -> None:
    row.addWidget(self._dim_label(self._ui_text(label)))
    row.addWidget(combo)
    row.addWidget(self._help_icon_button(self._ui_text(help_text)))


def _ensure_behavior_controls(self: Any):
    if hasattr(self, 'open_folder_check'):
        return
    behavior_plan = self._localized_plan(gui_layouts.build_behavior_section_plan())
    self.open_folder_check = QCheckBox(str(behavior_plan.get('open_folder_text', '完了後フォルダを開く')))
    self.open_folder_check.setChecked(self._plan_bool_value(behavior_plan, 'open_folder_checked_default', False))
    self.open_folder_check.toggled.connect(self.save_ui_state)

    self.kinsoku_mode_combo = QComboBox()
    for key, label in KINSOKU_MODE_OPTIONS:
        self.kinsoku_mode_combo.addItem(self._ui_text(label), key)
    self.kinsoku_mode_combo.currentIndexChanged.connect(self._on_kinsoku_mode_changed)

    self.tatechuyoko_digit_mode_combo = QComboBox()
    for key, label in TATECHUYOKO_DIGIT_MODE_OPTIONS:
        self.tatechuyoko_digit_mode_combo.addItem(self._ui_text(label), key)
    self._set_combo_to_data(self.tatechuyoko_digit_mode_combo, '2')
    self.tatechuyoko_digit_mode_combo.currentIndexChanged.connect(self._on_tatechuyoko_digit_mode_changed)

    self.latin_orientation_combo = QComboBox()
    for key, label in LATIN_ORIENTATION_MODE_OPTIONS:
        self.latin_orientation_combo.addItem(self._ui_text(label), key)
    self._set_combo_to_data(self.latin_orientation_combo, 'vertical')
    self.latin_orientation_combo.currentIndexChanged.connect(self._on_latin_orientation_mode_changed)

    self.opening_bracket_indent_combo = QComboBox()
    for key, label in OPENING_BRACKET_INDENT_MODE_OPTIONS:
        self.opening_bracket_indent_combo.addItem(self._ui_text(label), key)
    self._set_combo_to_data(self.opening_bracket_indent_combo, 'none')
    self.opening_bracket_indent_combo.currentIndexChanged.connect(self._on_opening_bracket_indent_mode_changed)

    self.punctuation_position_combo = self._make_glyph_position_combo()
    self.ichi_position_combo = self._make_glyph_position_combo()
    self.halfwidth_digit_position_combo = self._make_glyph_position_combo()
    self.halfwidth_alpha_position_combo = self._make_glyph_position_combo()
    self.middle_dot_position_combo = self._make_glyph_position_combo()
    self.tatechuyoko_symbol_position_combo = self._make_glyph_position_combo()
    self.lower_closing_bracket_position_combo = self._make_position_mode_combo(
        CLOSING_BRACKET_POSITION_MODE_OPTIONS,
        self._on_glyph_position_mode_changed,
    )

    self.wave_dash_drawing_combo = QComboBox()
    for key, label in WAVE_DASH_DRAWING_MODE_OPTIONS:
        self.wave_dash_drawing_combo.addItem(self._ui_text(label), key)
    self.wave_dash_drawing_combo.currentIndexChanged.connect(self._on_wave_dash_mode_changed)

    self.wave_dash_position_combo = QComboBox()
    for key, label in WAVE_DASH_POSITION_MODE_OPTIONS:
        self.wave_dash_position_combo.addItem(self._ui_text(label), key)
    self.wave_dash_position_combo.currentIndexChanged.connect(self._on_wave_dash_mode_changed)

    self.output_conflict_combo = QComboBox()
    for key, label in OUTPUT_CONFLICT_OPTIONS:
        self.output_conflict_combo.addItem(self._ui_text(label), key)
    self.output_conflict_combo.currentIndexChanged.connect(lambda _i, self=self: self.save_ui_state())


def _section_behavior(self: Any):
    behavior_plan = self._localized_plan(gui_layouts.build_behavior_section_plan())
    box, lay, _section_plan = self._build_section_box_layout(
        'behavior',
        'その他オプション',
        default_margins=(8, 14, 8, 8),
        default_spacing=6,
    )

    self._ensure_behavior_controls()

    # v1.3.3.48: 変換完了後のフォルダ自動オープンは廃止し、
    # 右ペイン完了カードの［保存先を開く］ボタンから手動で開く導線に一本化する。
    try:
        self.open_folder_check.setChecked(False)
        self.open_folder_check.setVisible(False)
    except Exception:
        pass

    row2 = self._make_hbox_layout_from_plan()
    row2.addWidget(self._dim_label(str(behavior_plan.get('output_conflict_label', '同名出力'))))
    row2.addWidget(self.output_conflict_combo, 1)
    row2.addWidget(self._help_icon_button(str(behavior_plan.get('output_conflict_help_text', '保存先に同名の .xtc / .xtch があるときの動作を選びます。\n自動連番: foo(1).xtc 形式で保存します。\n上書き: 既存ファイルを置き換えます。\nエラー: そのファイルを保存せずエラーとして記録します。'))))
    lay.addLayout(row2)
    return box


def _section_file_viewer(self: Any):
    file_viewer_plan = self._localized_plan(gui_layouts.build_file_viewer_section_plan())
    box, lay, _section_plan = self._build_section_box_layout(
        'fileviewer',
        'ファイルビューワー',
        default_margins=(8, 10, 8, 8),
        default_spacing=6,
    )

    row = self._make_hbox_layout_from_plan()
    self.open_xtc_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            file_viewer_plan.get('open_xtc_button_text', 'XTCファイルを開く'),
            object_name=file_viewer_plan.get('open_xtc_button_object_name', 'smallBtn'),
        ),
        self.open_xtc_file,
    )
    row.addWidget(self.open_xtc_btn)
    row.addSpacing(self._plan_int_value(file_viewer_plan, 'open_xtc_help_leading_spacing', 8))
    row.addWidget(self._help_icon_button(
        file_viewer_plan.get(
            'open_xtc_help_text',
            '既存の .xtc / .xtch ファイルを右ペインへ読み込んで確認します。',
        )
    ))
    if self._plan_bool_value(file_viewer_plan, 'open_xtc_help_trailing_stretch', True):
        row.addStretch(1)
    lay.addLayout(row)
    return box

