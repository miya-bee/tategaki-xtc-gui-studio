from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QLabel,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import tategakiXTC_gui_layouts as gui_layouts
from tategakiXTC_gui_studio_constants import DEFAULT_PREVIEW_PAGE_LIMIT


def build_margin_rows(self):
    font_plan = self._localized_plan(gui_layouts.build_font_section_plan())
    margin_rows_plan = self._localized_plan(gui_layouts.build_margin_rows_plan(
        row_spacing=font_plan.get('margin_rows_spacing', 2),
        pair_spacing=font_plan.get('margin_pair_spacing', 16),
    ))
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*self._plan_int_tuple_value(margin_rows_plan, 'container_margins', (0, 0, 0, 0), expected_length=4))
    lay.setSpacing(self._plan_int_value(margin_rows_plan, 'row_spacing', 2))

    row_plan = gui_layouts.build_row_layout_plan(
        contents_margins=margin_rows_plan.get('row_contents_margins', (0, 0, 0, 0))
    )
    row = self._make_hbox_layout_from_plan(row_plan)
    row.addWidget(self._dim_label(str(margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[0])))
    row.addWidget(self.margin_t_spin)
    row.addSpacing(self._plan_int_value(margin_rows_plan, 'pair_spacing', 16))
    row.addWidget(self._dim_label(str(margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[1])))
    row.addWidget(self.margin_b_spin)
    row.addSpacing(self._plan_int_value(margin_rows_plan, 'pair_spacing', 16))
    row.addWidget(self._dim_label(str(margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[2])))
    row.addWidget(self.margin_l_spin)
    row.addSpacing(self._plan_int_value(margin_rows_plan, 'pair_spacing', 16))
    row.addWidget(self._dim_label(str(margin_rows_plan.get('labels', ('上余白', '下余白', '左余白', '右余白'))[3])))
    row.addWidget(self.margin_r_spin)
    if self._plan_bool_value(margin_rows_plan, 'trailing_stretch', True):
        row.addStretch(1)

    lay.addLayout(row)
    return w

# ── プレビュー更新コントロール（セクション外） ────────────────


def section_preview_controls(self):
    display_plan = self._localized_plan(gui_layouts.build_display_section_plan())

    # sweep363/sweep365: 実寸近似/ガイドは右ペインの表示ツールバーへ集約する。
    # v1.3.8.6: 中央ペインでは「プレビュー」セクションを廃止するが、
    # 右ペインへ移す既存 widget と設定互換はここで生成する。
    preview_toggle_plan = self._localized_plan(gui_layouts.build_preview_display_toggle_plan())
    self.actual_size_check = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            preview_toggle_plan.get('actual_size_text', '実寸'),
            object_name=preview_toggle_plan.get('actual_size_object_name', 'viewToggleBtn'),
            checkable=self._plan_bool_value(preview_toggle_plan, 'actual_size_checkable', True),
            focus_policy=preview_toggle_plan.get('actual_size_focus_policy', 'no_focus'),
        ),
    )
    actual_size_help_text = str(preview_toggle_plan.get('actual_size_help_text', '実寸表示モードです。'))
    self.actual_size_check.setToolTip(actual_size_help_text)
    self.actual_size_help_btn = self._help_icon_button(actual_size_help_text)
    self.actual_size_check.toggled.connect(self.on_actual_size_toggled)

    guide_help_text = str(preview_toggle_plan.get('guide_help_text', 'ガイド表示の切り替えです。'))
    self.guides_check = QCheckBox(str(preview_toggle_plan.get('guide_text', 'ガイド')))
    self.guides_check.setObjectName(str(preview_toggle_plan.get('guide_object_name', 'previewToolbarToggle')))
    self.guides_check.setFocusPolicy(
        self._plan_focus_policy_value(preview_toggle_plan, 'guide_focus_policy', 'no_focus')
    )
    self.guides_check.setToolTip(guide_help_text)
    self.guides_check.setChecked(self._plan_bool_value(preview_toggle_plan, 'guide_checked_default', True))
    self.guides_help_btn = self._help_icon_button(guide_help_text)

    wrapper = QWidget()
    wrapper.setObjectName('previewUpdateRowContainer')

    # 旧左ペインの実寸補正UIは、設定互換用に保持するが表示しない。
    # v1.3.8.8: 親なしトップレベル widget にならないよう、返却する
    # wrapper を親にして作る。UIには追加せず、設定値の互換だけ維持する。
    self.calib_label = self._dim_label(str(display_plan.get('calibration_label_text', '実寸補正')))
    self.calib_label.setParent(wrapper)
    calibration_button_object_name = str(display_plan.get('calibration_button_object_name', 'stepBtn'))
    self.calib_down_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            display_plan.get('calibration_down_text', '−'),
            object_name=calibration_button_object_name,
            fixed_size=display_plan.get('calibration_button_size', (24, 24)),
        ),
    )
    self.calib_down_btn.setParent(wrapper)
    self.calib_spin = QSpinBox(wrapper)
    self.calib_spin.setRange(
        self._plan_int_value(display_plan, 'calibration_spin_minimum', 50),
        self._plan_int_value(display_plan, 'calibration_spin_maximum', 300),
    )
    self.calib_spin.setSingleStep(self._plan_int_value(display_plan, 'calibration_spin_step', 5))
    self.calib_spin.setAccelerated(
        self._plan_bool_value(display_plan, 'calibration_spin_accelerated', True)
    )
    self.calib_spin.setButtonSymbols(
        self._plan_spin_button_symbols_value(display_plan, 'calibration_spin_button_symbols', 'no_buttons')
    )
    self.calib_spin.setValue(self._plan_int_value(display_plan, 'calibration_spin_default', 100))
    self.calib_spin.setSuffix(str(display_plan.get('calibration_spin_suffix', '%')))
    self.calib_spin.setFixedWidth(self._plan_int_value(display_plan, 'calibration_spin_width', 62))
    self.calib_spin.valueChanged.connect(self.on_calibration_changed)
    self.calib_up_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            display_plan.get('calibration_up_text', '+'),
            object_name=calibration_button_object_name,
            fixed_size=display_plan.get('calibration_button_size', (24, 24)),
        ),
    )
    self.calib_up_btn.setParent(wrapper)
    self.calib_help_btn = self._help_icon_button(
        str(display_plan.get('calibration_help_text', '実寸補正は右ペインの倍率UIで調整します。'))
    )
    self.calib_help_btn.setParent(wrapper)
    self._sync_legacy_calibration_control_state()

    self.guides_check.toggled.connect(self.on_guides_toggled)
    self.calib_down_btn.clicked.connect(lambda: self.calib_spin.stepBy(-1))
    self.calib_up_btn.clicked.connect(lambda: self.calib_spin.stepBy(1))

    outer = QVBoxLayout(wrapper)
    outer.setContentsMargins(0, 3, 0, 3)
    outer.setSpacing(3)

    sep_top = QFrame()
    sep_top.setFrameShape(self._qframe_shape_constant('HLine', self._qframe_shape_constant('NoFrame', 0)))
    sep_top.setObjectName('leftSettingsBottomSep')
    sep_top.setFixedHeight(1)
    outer.addWidget(sep_top)

    row = self._make_hbox_layout_from_plan()
    row.addWidget(self._dim_label(str(display_plan.get('preview_page_limit_label', '更新対象'))))
    self.preview_page_limit_spin = self._spin(1, 9999, DEFAULT_PREVIEW_PAGE_LIMIT, compact=True, buttons=True)
    self.preview_page_limit_spin.setProperty('miniSpinButtons', True)
    self.preview_page_limit_spin.setFixedWidth(self._plan_int_value(display_plan, 'preview_page_limit_width', 68))
    self.preview_page_limit_spin.valueChanged.connect(self._mark_preview_dirty_from_signal)
    self.preview_page_limit_spin.valueChanged.connect(lambda _v, self=self: self.save_ui_state())
    row.addWidget(self.preview_page_limit_spin)
    page_limit_unit_label = QLabel(str(display_plan.get('preview_page_limit_unit_text', 'ページ')))
    page_limit_unit_label.setObjectName(str(display_plan.get('preview_page_limit_unit_object_name', 'dimLabel')))
    row.addWidget(page_limit_unit_label)
    self.preview_update_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            display_plan.get('preview_update_button_text', 'プレビュー更新'),
            object_name=display_plan.get('preview_update_button_object_name', 'smallBtn'),
        ),
        self.manual_refresh_preview,
    )
    row.addWidget(self.preview_update_btn)
    self.preview_refresh_btn = self.preview_update_btn
    self.preview_progress_bar = QProgressBar()
    self.preview_progress_bar.setObjectName(str(display_plan.get('preview_progress_object_name', 'previewProgressBar')))
    self.preview_progress_bar.setTextVisible(True)
    self.preview_progress_bar.setFixedWidth(self._plan_int_value(display_plan, 'preview_progress_width', 118))
    self.preview_progress_bar.setRange(0, 1)
    self.preview_progress_bar.setValue(0)
    self.preview_progress_bar.setFormat(str(display_plan.get('preview_progress_idle_format', '')))
    self.preview_progress_bar.setVisible(False)
    row.addWidget(self.preview_progress_bar)
    self.preview_status_label = QLabel(str(display_plan.get('preview_status_text', '')))
    self.preview_status_label.setObjectName(str(display_plan.get('preview_status_object_name', 'hintLabel')))
    self.preview_status_label.setMinimumWidth(self._plan_int_value(display_plan, 'preview_status_min_width', 220))
    self.preview_status_label.setMaximumWidth(self._plan_int_value(display_plan, 'preview_status_max_width', 260))
    row.addWidget(self.preview_status_label)
    row.addSpacing(self._plan_int_value(display_plan, 'preview_status_help_spacing', 4))
    row.addWidget(self._help_icon_button(str(display_plan.get('preview_update_help_text', 'ファイル読込時: プレビューを自動生成します。\n設定変更後: 更新対象が20ページ以下なら自動更新します。21ページ以上では自動更新せず、「プレビュー更新が必要です」と表示し、［プレビュー更新］を押した時点で再生成します。\n更新対象: プレビュー上限を増やすほど確認範囲は広がりますが、読込・再描画・メモリ使用量は重くなります。最大9999ページまで指定できます。'))))
    row.addStretch(1)
    outer.addLayout(row)

    sep_bottom = QFrame()
    sep_bottom.setFrameShape(self._qframe_shape_constant('HLine', self._qframe_shape_constant('NoFrame', 0)))
    sep_bottom.setObjectName('leftSettingsBottomSep')
    sep_bottom.setFixedHeight(1)
    outer.addWidget(sep_bottom)
    return wrapper

# Backward-compatible alias for tests and older layout probes.
