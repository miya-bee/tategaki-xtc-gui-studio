"""Bottom panel builders for TategakiXTC GUI Studio.

This module keeps the bottom status/results/log UI construction out of the
MainWindow entry module while preserving the existing MainWindow methods as
thin compatibility wrappers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import tategakiXTC_gui_layouts as gui_layouts


def build_bottom_panel(self: Any):
    bottom_panel_plan = self._localized_plan(gui_layouts.build_bottom_panel_layout_plan())
    panel = QFrame()
    panel.setObjectName(str(bottom_panel_plan.get('panel_object_name', 'bottomPanel')))
    outer_lay = QHBoxLayout(panel)
    outer_lay.setContentsMargins(*self._plan_int_tuple_value(bottom_panel_plan, 'panel_contents_margins', (0, 0, 0, 0), expected_length=4))
    outer_lay.setSpacing(self._plan_int_value(bottom_panel_plan, 'panel_spacing', 0))

    content = QFrame()
    content.setObjectName(str(bottom_panel_plan.get('content_object_name', 'bottomPanelContent')))
    lay = QVBoxLayout(content)
    lay.setContentsMargins(*self._plan_int_tuple_value(bottom_panel_plan, 'content_contents_margins', (0, 0, 0, 0), expected_length=4))
    lay.setSpacing(self._plan_int_value(bottom_panel_plan, 'content_spacing', 0))

    strip = QFrame()
    strip.setObjectName(str(bottom_panel_plan.get('status_strip_object_name', 'statusStrip')))
    strip.setFixedHeight(self._plan_int_value(bottom_panel_plan, 'status_strip_height', 34))
    sl = QHBoxLayout(strip)
    sl.setContentsMargins(*self._plan_int_tuple_value(bottom_panel_plan, 'status_strip_margins', (14, 0, 14, 0), expected_length=4))
    sl.setSpacing(self._plan_int_value(bottom_panel_plan, 'status_strip_spacing', 10))

    status_strip_plan = self._localized_plan(gui_layouts.build_bottom_status_strip_plan())

    self.busy_badge = QLabel(str(status_strip_plan.get('badge_text', '待機中')))
    self.busy_badge.setObjectName(str(status_strip_plan.get('badge_object_name', 'badge')))
    sl.addWidget(self.busy_badge)

    self.progress_bar = QProgressBar()
    self.progress_bar.setRange(
        self._plan_int_value(status_strip_plan, 'progress_minimum', 0),
        self._plan_int_value(status_strip_plan, 'progress_maximum', 1),
    )
    self.progress_bar.setValue(self._plan_int_value(status_strip_plan, 'progress_value', 0))
    self.progress_bar.setTextVisible(self._plan_bool_value(status_strip_plan, 'progress_text_visible', False))
    self.progress_bar.setFixedHeight(self._plan_int_value(status_strip_plan, 'progress_fixed_height', 6))
    self.progress_bar.setMaximumWidth(self._plan_int_value(status_strip_plan, 'progress_max_width', 200))
    sl.addWidget(self.progress_bar)

    self.progress_label = QLabel(str(status_strip_plan.get('progress_text', '')))
    self.progress_label.setObjectName(str(status_strip_plan.get('progress_label_object_name', 'hintLabel')))
    sl.addWidget(self.progress_label, 1)

    lay.addWidget(strip)

    sep = QFrame()
    sep.setFrameShape(self._plan_frame_shape_value(bottom_panel_plan, 'bottom_separator_frame_shape', 'hline'))
    sep.setObjectName(str(bottom_panel_plan.get('bottom_separator_object_name', 'bottomPanelSep')))
    lay.addWidget(sep)

    self.bottom_tabs = QTabWidget()
    self.bottom_tabs.addTab(self._build_results_tab(), str(bottom_panel_plan.get('results_tab_title', '変換結果')))
    self.bottom_tabs.addTab(self._build_log_tab(), str(bottom_panel_plan.get('log_tab_title', 'ログ')))
    self.bottom_tabs.currentChanged.connect(lambda _index: self._bind_bottom_panel_external_scrollbar())
    lay.addWidget(self.bottom_tabs, 1)

    outer_lay.addWidget(content, 1)
    if self._plan_bool_value(bottom_panel_plan, 'external_scrollbar_enabled', False):
        self.bottom_panel_scrollbar = QScrollBar(Qt.Vertical)
        self.bottom_panel_scrollbar.setObjectName(
            str(bottom_panel_plan.get('external_scrollbar_object_name', 'bottomPanelScrollBar'))
        )
        self.bottom_panel_scrollbar.setSingleStep(
            self._plan_int_value(bottom_panel_plan, 'external_scrollbar_single_step', 20)
        )
        self.bottom_panel_scrollbar.valueChanged.connect(self._apply_bottom_panel_external_scroll_value)
        outer_lay.addWidget(self.bottom_panel_scrollbar, 0)
    else:
        self.bottom_panel_scrollbar = None
    self._bind_bottom_panel_external_scrollbar()
    return panel

def build_results_tab(self: Any):
    results_tab_plan = self._localized_plan(gui_layouts.build_results_tab_plan())
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*self._plan_int_tuple_value(results_tab_plan, 'contents_margins', (6, 6, 6, 6), expected_length=4))
    lay.setSpacing(self._plan_int_value(results_tab_plan, 'spacing', 4))
    self.results_summary_label = QLabel(str(results_tab_plan.get('summary_text', '変換結果の概要をここに表示します。')))
    self.results_summary_label.setObjectName(str(results_tab_plan.get('summary_label_object_name', 'resultsPlaceholderLabel')))
    self.results_summary_label.setWordWrap(self._plan_bool_value(results_tab_plan, 'summary_label_word_wrap', True))
    self.results_summary_label.setAlignment(
        self._plan_alignment_value(results_tab_plan, 'summary_label_alignment', 'center')
    )
    self._set_results_summary_placeholder_state(True)
    self.results_summary_scroll = QScrollArea()
    self.results_summary_scroll.setWidgetResizable(
        self._plan_bool_value(results_tab_plan, 'summary_scroll_widget_resizable', True)
    )
    self.results_summary_scroll.setFrameShape(
        self._plan_frame_shape_value(results_tab_plan, 'summary_scroll_frame_shape', 'no_frame')
    )
    self.results_summary_scroll.setHorizontalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(results_tab_plan, 'summary_scroll_horizontal_scroll_bar_policy', 'as_needed')
    )
    self.results_summary_scroll.setVerticalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(results_tab_plan, 'summary_scroll_vertical_scroll_bar_policy', 'as_needed')
    )
    self.results_summary_scroll.setWidget(self.results_summary_label)
    lay.addWidget(self.results_summary_scroll, 0)

    self.results_action_row = QFrame()
    self.results_action_row.setObjectName('resultsActionRow')
    results_action_lay = QHBoxLayout(self.results_action_row)
    results_action_lay.setContentsMargins(8, 5, 8, 5)
    results_action_lay.setSpacing(8)
    self.open_results_folder_btn = QPushButton(self._ui_text('保存先を開く'))
    self.open_results_folder_btn.setObjectName('resultsActionButton')
    self.open_results_folder_btn.setToolTip(self._ui_text('選択中、または先頭の変換結果が保存されたフォルダを開きます。'))
    self.open_results_folder_btn.clicked.connect(self.open_results_folder_from_results)
    results_action_lay.addWidget(self.open_results_folder_btn, 0)
    self.open_selected_result_btn = QPushButton(self._ui_text('右ペインで確認'))
    self.open_selected_result_btn.setObjectName('resultsActionButton')
    self.open_selected_result_btn.setToolTip(self._ui_text('選択中、または先頭の変換結果を右ペインへ読み込みます。'))
    self.open_selected_result_btn.clicked.connect(self.open_selected_result_from_results)
    results_action_lay.addWidget(self.open_selected_result_btn, 0)
    results_action_lay.addStretch(1)
    lay.addWidget(self.results_action_row, 0)

    self.results_list = QListWidget()
    self.results_list.setVerticalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(results_tab_plan, 'results_list_vertical_scroll_bar_policy', 'always_on')
    )
    self.results_list.setHorizontalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(results_tab_plan, 'results_list_horizontal_scroll_bar_policy', 'as_needed')
    )
    self.results_list.setSelectionMode(
        self._plan_list_selection_mode_value(results_tab_plan, 'results_list_selection_mode', 'single_selection')
    )
    self.results_list.itemClicked.connect(self.on_result_item_clicked)
    self.results_list.itemActivated.connect(self.on_result_item_clicked)
    lay.addWidget(self.results_list, 1)
    self._sync_results_action_buttons_state()
    return w

def build_log_tab(self: Any, session_log_path_display: Path):
    log_tab_plan = self._localized_plan(gui_layouts.build_log_tab_plan(log_path=session_log_path_display))
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(*self._plan_int_tuple_value(log_tab_plan, 'contents_margins', (6, 6, 6, 6), expected_length=4))
    lay.setSpacing(self._plan_int_value(log_tab_plan, 'spacing', 6))

    top = QHBoxLayout()
    top.setContentsMargins(*self._plan_int_tuple_value(log_tab_plan, 'top_row_margins', (0, 0, 0, 0), expected_length=4))
    top.setSpacing(self._plan_int_value(log_tab_plan, 'top_row_spacing', 8))
    label = QLabel(str(log_tab_plan.get('path_label_text', '保存先:')))
    label.setObjectName(str(log_tab_plan.get('path_label_object_name', 'logPathLabel')))
    top.addWidget(label, 0)

    self.log_path_edit = QLineEdit(str(log_tab_plan.get('log_path', str(session_log_path_display))))
    log_path_read_only = self._plan_bool_value(log_tab_plan, 'log_path_edit_read_only', True)
    self.log_path_edit.setReadOnly(log_path_read_only)
    top.addWidget(self.log_path_edit, 1)

    open_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(log_tab_plan.get('open_folder_button_text', 'ログフォルダを開く')),
        self.open_log_folder,
    )
    top.addWidget(open_btn, 0)
    lay.addLayout(top)

    self.log_edit = QTextEdit()
    self.log_edit.setVerticalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(log_tab_plan, 'log_edit_vertical_scroll_bar_policy', 'always_on')
    )
    self.log_edit.setHorizontalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(log_tab_plan, 'log_edit_horizontal_scroll_bar_policy', 'as_needed')
    )
    log_edit_read_only = self._plan_bool_value(log_tab_plan, 'log_edit_read_only', True)
    self.log_edit.setReadOnly(log_edit_read_only)
    lay.addWidget(self.log_edit, 1)
    return w


def active_bottom_panel_scrollbar(self: Any) -> object | None:
    tabs = getattr(self, 'bottom_tabs', None)
    try:
        index = int(tabs.currentIndex()) if tabs is not None else 0
    except Exception:
        index = 0
    if index == 1:
        widget = getattr(self, 'log_edit', None)
    else:
        widget = getattr(self, 'results_list', None)
    if widget is None or not hasattr(widget, 'verticalScrollBar'):
        return None
    try:
        return widget.verticalScrollBar()
    except Exception:
        return None

def bind_bottom_panel_external_scrollbar(self: Any) -> None:
    external = getattr(self, 'bottom_panel_scrollbar', None)
    if external is None:
        return
    source = self._active_bottom_panel_scrollbar()
    previous = getattr(self, '_bottom_panel_bound_scrollbar', None)
    if previous is not None and previous is not source:
        for signal_name in ('rangeChanged', 'valueChanged'):
            signal = getattr(previous, signal_name, None)
            if signal is None:
                continue
            try:
                signal.disconnect(self._sync_bottom_panel_external_scrollbar)
            except Exception:
                pass
    if source is None:
        self._bottom_panel_bound_scrollbar = None
        self._set_bottom_panel_external_scrollbar_range(0, 0, 0, 0, 0)
        return
    if previous is not source:
        for signal_name in ('rangeChanged', 'valueChanged'):
            signal = getattr(source, signal_name, None)
            if signal is None:
                continue
            try:
                signal.connect(self._sync_bottom_panel_external_scrollbar)
            except Exception:
                pass
        self._bottom_panel_bound_scrollbar = source
    self._sync_bottom_panel_external_scrollbar()

def set_bottom_panel_external_scrollbar_range(
    self: Any,
    minimum: int,
    maximum: int,
    value: int,
    page_step: int,
    single_step: int,
) -> None:
    external = getattr(self, 'bottom_panel_scrollbar', None)
    if external is None:
        return
    self._bottom_panel_scrollbar_syncing = True
    try:
        external.blockSignals(True)
        external.setRange(max(0, int(minimum)), max(0, int(maximum)))
        external.setPageStep(max(1, int(page_step or 1)))
        external.setSingleStep(max(1, int(single_step or 1)))
        external.setValue(max(external.minimum(), min(external.maximum(), int(value))))
        external.setEnabled(external.maximum() > external.minimum())
    finally:
        try:
            external.blockSignals(False)
        except Exception:
            pass
        self._bottom_panel_scrollbar_syncing = False

def sync_bottom_panel_external_scrollbar(self: Any, *_args: object) -> None:
    if bool(getattr(self, '_bottom_panel_scrollbar_syncing', False)):
        return
    source = self._active_bottom_panel_scrollbar()
    if source is None:
        self._set_bottom_panel_external_scrollbar_range(0, 0, 0, 0, 0)
        return
    try:
        minimum = int(source.minimum())
        maximum = int(source.maximum())
        value = int(source.value())
        page_step = int(source.pageStep())
        single_step = int(source.singleStep())
    except Exception:
        self._set_bottom_panel_external_scrollbar_range(0, 0, 0, 0, 0)
        return
    self._set_bottom_panel_external_scrollbar_range(minimum, maximum, value, page_step, single_step)

def apply_bottom_panel_external_scroll_value(self: Any, value: int) -> None:
    if bool(getattr(self, '_bottom_panel_scrollbar_syncing', False)):
        return
    source = self._active_bottom_panel_scrollbar()
    if source is None:
        return
    self._bottom_panel_scrollbar_syncing = True
    try:
        try:
            source.setValue(int(value))
        except Exception:
            pass
    finally:
        self._bottom_panel_scrollbar_syncing = False
    self._sync_bottom_panel_external_scrollbar()
