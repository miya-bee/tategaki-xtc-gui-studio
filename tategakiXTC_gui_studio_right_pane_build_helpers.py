from __future__ import annotations

"""Right preview pane construction helpers for TategakiXTC GUI Studio.

These helpers keep the entry ``MainWindow`` module focused on wiring while
preserving the existing method names as thin wrappers.
"""

import os
import ntpath
from pathlib import Path
from typing import Any, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import tategakiXTC_gui_layouts as gui_layouts
import tategakiXTC_gui_results_controller as results_controller
import tategakiXTC_worker_logic as worker_logic
from tategakiXTC_gui_completion_helpers import (
    build_conversion_completion_card_message,
    completion_card_parent_texts,
    completion_card_result_item_texts,
)
from tategakiXTC_gui_studio_constants import RESULT_TAB_INDEX
from tategakiXTC_gui_studio_widgets import XtcViewerWidget


# ── 右プレビューパネル ────────────────────────────────

def _build_right_preview(self):
    preview_panel_plan = self._localized_plan(gui_layouts.build_right_preview_panel_plan())
    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(*tuple(preview_panel_plan.get('panel_contents_margins', (0, 0, 0, 0))))
    lay.setSpacing(self._plan_int_value(preview_panel_plan, 'panel_spacing', 0))

    lay.addWidget(self._build_view_toggle_bar())
    lay.addWidget(self._build_conversion_completion_card())

    self.preview_stack = QStackedWidget()

    font_page = QWidget()
    fl = QVBoxLayout(font_page)
    fl.setContentsMargins(*tuple(preview_panel_plan.get('font_page_margins', (8, 8, 8, 8))))
    self.preview_scroll = QScrollArea()
    self.preview_scroll.setWidgetResizable(
        self._plan_bool_value(preview_panel_plan, 'font_scroll_widget_resizable', False)
    )
    self.preview_scroll.setAlignment(
        self._plan_alignment_value(preview_panel_plan, 'font_scroll_alignment', 'center')
    )
    self.preview_scroll.setFrameShape(
        self._plan_frame_shape_value(preview_panel_plan, 'font_scroll_frame_shape', 'no_frame')
    )
    self.preview_scroll.setHorizontalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(
            preview_panel_plan,
            'font_scroll_horizontal_scroll_bar_policy',
            'as_needed',
        )
    )
    self.preview_scroll.setVerticalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(
            preview_panel_plan,
            'font_scroll_vertical_scroll_bar_policy',
            'as_needed',
        )
    )
    try:
        self.preview_scroll.setLayoutDirection(Qt.LeftToRight)
    except Exception:
        pass
    self.preview_label = QLabel()
    self.preview_label.setAlignment(
        self._plan_alignment_value(preview_panel_plan, 'font_preview_alignment', 'center')
    )
    self.preview_label.setMinimumSize(*self._plan_int_tuple_value(preview_panel_plan, 'font_preview_min_size', (360, 600), expected_length=2))
    self.preview_label.setWordWrap(self._plan_bool_value(preview_panel_plan, 'font_preview_word_wrap', True))
    try:
        self.preview_label.setLayoutDirection(Qt.LeftToRight)
    except Exception:
        pass
    self.preview_scroll.setWidget(self.preview_label)
    fl.addWidget(self.preview_scroll, 1)
    self.preview_stack.addWidget(font_page)

    device_page = QWidget()
    dl = QVBoxLayout(device_page)
    dl.setContentsMargins(*self._plan_int_tuple_value(preview_panel_plan, 'device_page_margins', (8, 8, 8, 8), expected_length=4))
    self.viewer_scroll = QScrollArea()
    self.viewer_scroll.setWidgetResizable(
        self._plan_bool_value(preview_panel_plan, 'device_scroll_widget_resizable', False)
    )
    self.viewer_scroll.setAlignment(
        self._plan_alignment_value(preview_panel_plan, 'device_scroll_alignment', 'center')
    )
    self.viewer_scroll.setFrameShape(
        self._plan_frame_shape_value(preview_panel_plan, 'device_scroll_frame_shape', 'no_frame')
    )
    self.viewer_scroll.setHorizontalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(
            preview_panel_plan,
            'device_scroll_horizontal_scroll_bar_policy',
            'as_needed',
        )
    )
    self.viewer_scroll.setVerticalScrollBarPolicy(
        self._plan_scroll_bar_policy_value(
            preview_panel_plan,
            'device_scroll_vertical_scroll_bar_policy',
            'as_needed',
        )
    )
    try:
        self.viewer_scroll.setLayoutDirection(Qt.LeftToRight)
    except Exception:
        pass
    self.viewer_scroll.setFocusPolicy(
        self._plan_focus_policy_value(preview_panel_plan, 'device_scroll_focus_policy', 'strong_focus')
    )
    self.viewer_widget = XtcViewerWidget()
    self.viewer_widget.setMinimumSize(*self._plan_int_tuple_value(preview_panel_plan, 'device_preview_min_size', (360, 600), expected_length=2))
    self.viewer_scroll.setWidget(self.viewer_widget)
    dl.addWidget(self.viewer_scroll, 1)
    self.preview_stack.addWidget(device_page)

    lay.addWidget(self.preview_stack, 1)

    self.preview_stack.setCurrentIndex(self._plan_int_value(preview_panel_plan, 'preview_stack_index', 0))
    self._sync_preview_size()
    return panel

def _build_view_toggle_bar(self):
    toggle_plan = self._localized_plan(gui_layouts.build_view_toggle_bar_plan())
    bar = QFrame()
    bar.setObjectName(str(toggle_plan.get('object_name', 'viewToggleBar')))
    bar.setFixedHeight(self._plan_int_value(toggle_plan, 'bar_height', 96))
    outer_lay = QVBoxLayout(bar)
    outer_lay.setContentsMargins(*self._plan_int_tuple_value(toggle_plan, 'contents_margins', (12, 4, 12, 4), expected_length=4))
    outer_lay.setSpacing(self._plan_int_value(toggle_plan, 'row_spacing', 2))

    top_lay = QHBoxLayout()
    top_lay.setContentsMargins(*self._plan_int_tuple_value(toggle_plan, 'top_row_contents_margins', (0, 0, 0, 0), expected_length=4))
    top_lay.setSpacing(self._plan_int_value(toggle_plan, 'spacing', 6))

    # v1.3.8.10: remove the user-facing font/device mode switch.
    # The right pane now has one normal preview surface; XTC/XTCH files opened
    # via the top button are shown there as file-viewer content.  Keep these
    # attributes absent rather than hidden buttons so legacy mode-switch code
    # naturally becomes a no-op through getattr(..., None).
    self._add_preview_display_toggles_to_layout(top_lay)
    top_lay.addStretch(1)
    self.open_xtc_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            str(toggle_plan.get('open_xtc_button_text', 'XTCファイルを開く')),
            object_name=str(toggle_plan.get('open_xtc_button_object_name', 'previewToolbarButton')),
            tooltip=str(toggle_plan.get('open_xtc_button_tooltip', '既存の .xtc / .xtch ファイルを右ペインで確認します')),
            focus_policy=str(toggle_plan.get('open_xtc_button_focus_policy', 'no_focus')),
        ),
        self.open_xtc_file,
    )
    top_lay.addWidget(self.open_xtc_btn)
    self.share_png_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            str(toggle_plan.get('share_png_button_text', 'PNG保存')),
            object_name=str(toggle_plan.get('share_png_button_object_name', 'previewToolbarButton')),
            tooltip=str(toggle_plan.get('share_png_button_tooltip', '現在のプレビュー1ページを枠付きPNGとして保存します。')),
            focus_policy=str(toggle_plan.get('share_png_button_focus_policy', 'no_focus')),
        ),
        getattr(self, 'export_current_preview_share_png', lambda: None),
    )
    top_lay.addWidget(self.share_png_btn)
    self.view_help_btn = self._help_icon_button(self._ui_text(self._preview_view_help_text()))
    top_lay.addWidget(self.view_help_btn)
    outer_lay.addLayout(top_lay)

    sep = QFrame()
    sep.setFrameShape(self._qframe_shape_constant('HLine', self._qframe_shape_constant('NoFrame', 0)))
    sep.setObjectName(str(toggle_plan.get('top_separator_object_name', 'topSep')))
    outer_lay.addWidget(sep)

    bottom_lay = QHBoxLayout()
    bottom_lay.setContentsMargins(*self._plan_int_tuple_value(toggle_plan, 'bottom_row_contents_margins', (0, 0, 0, 0), expected_length=4))
    bottom_lay.setSpacing(self._plan_int_value(toggle_plan, 'bottom_row_spacing', self._plan_int_value(toggle_plan, 'spacing', 6)))
    self._add_nav_controls_to_layout(bottom_lay, current_label_stretch=0)
    self._add_preview_zoom_controls_to_layout(bottom_lay, toggle_plan=toggle_plan)
    bottom_lay.addStretch(1)
    outer_lay.addLayout(bottom_lay)
    return bar

def _add_preview_display_toggles_to_layout(self, lay: QHBoxLayout) -> None:
    """右ペイン表示ツールバーへ表示系トグルを配置する。"""
    self._add_optional_widget_to_layout(lay, 'actual_size_check')
    self._add_optional_widget_to_layout(lay, 'actual_size_help_btn')
    preview_toggle_plan = self._localized_plan(gui_layouts.build_preview_display_toggle_plan())
    lay.addSpacing(self._plan_int_value(preview_toggle_plan, 'toggle_spacing', 18))
    self._add_optional_widget_to_layout(lay, 'guides_check')
    self._add_optional_widget_to_layout(lay, 'guides_help_btn')

def _build_conversion_completion_card(self):
    """右ペイン上部へ表示する変換完了カードを構築する。"""
    card = QFrame()
    card.setObjectName('conversionCompletionCard')
    card.setVisible(False)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(12, 8, 12, 8)
    lay.setSpacing(6)

    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(8)
    self.conversion_completion_title_label = QLabel(self._ui_text('変換完了'))
    self.conversion_completion_title_label.setObjectName('conversionCompletionTitle')
    top.addWidget(self.conversion_completion_title_label, 0)
    top.addStretch(1)
    self.close_conversion_completion_card_btn = QPushButton(self._ui_text('閉じる'))
    self.close_conversion_completion_card_btn.setObjectName('conversionCompletionCloseButton')
    self.close_conversion_completion_card_btn.setToolTip(self._ui_text('変換完了カードを閉じます。'))
    self.close_conversion_completion_card_btn.clicked.connect(self._hide_conversion_completion_card)
    top.addWidget(self.close_conversion_completion_card_btn, 0)
    lay.addLayout(top)

    self.conversion_completion_message_label = QLabel('')
    self.conversion_completion_message_label.setObjectName('conversionCompletionMessage')
    self.conversion_completion_message_label.setWordWrap(True)
    self.conversion_completion_message_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
    lay.addWidget(self.conversion_completion_message_label, 0)

    actions = QHBoxLayout()
    actions.setContentsMargins(0, 0, 0, 0)
    actions.setSpacing(8)
    self.card_open_results_folder_btn = QPushButton(self._ui_text('保存先を開く'))
    self.card_open_results_folder_btn.setObjectName('conversionCompletionActionButton')
    self.card_open_results_folder_btn.setToolTip(self._ui_text('変換結果が保存されたフォルダを開きます。'))
    self.card_open_results_folder_btn.clicked.connect(self.open_results_folder_from_results)
    actions.addWidget(self.card_open_results_folder_btn, 0)
    actions.addStretch(1)
    lay.addLayout(actions)
    self.conversion_completion_card = card
    return card

def _hide_conversion_completion_card(self: Any) -> None:
    card = getattr(self, 'conversion_completion_card', None)
    if card is not None and hasattr(card, 'setVisible'):
        try:
            card.setVisible(False)
        except Exception:
            pass

def _show_results_tab_from_completion_card(self: Any) -> None:
    if hasattr(self, 'bottom_tabs'):
        try:
            self._set_bottom_tab_index_with_fallback(RESULT_TAB_INDEX)
        except Exception:
            pass

def _completion_card_parent_texts(self: Any, paths: object) -> list[str]:
    return completion_card_parent_texts(paths)

def _completion_card_result_item_texts(
    self: Any,
    paths: object,
    *,
    base_path: object = '',
    max_items: int = 5,
) -> list[str]:
    """変換完了カードへ表示する出力ファイルの短い一覧を返す。"""
    return completion_card_result_item_texts(paths, base_path=base_path, max_items=max_items)

def _build_conversion_completion_card_message(
    self: Any,
    converted_files: object,
    result: Mapping[str, object] | None = None,
) -> str:
    return build_conversion_completion_card_message(
        converted_files,
        result,
        ui_language=self.current_ui_language_value(),
    )

def _meaningful_open_folder_target_text(self: Any, value: object) -> str:
    if not isinstance(value, (str, bytes, bytearray, os.PathLike)):
        return ''
    target = worker_logic._normalized_path_text(value).strip()
    if not target:
        return ''
    # ``'.'``, ``'./'``, ``'.\\'``, ``'./.'``, ``'foo/..'`` などは
    # 正規化すると ``'.'`` になり、``os.startfile`` ではアプリのある
    # 作業ディレクトリ（cwd）を開いてしまう。``'..'`` も親ディレクトリへ
    # 落ちて意図しないフォルダを開くため、同じく拒否する。
    try:
        if worker_logic._is_windows_like_path(target):
            normalized_for_check = ntpath.normpath(target)
        else:
            normalized_for_check = os.path.normpath(target)
    except Exception:
        normalized_for_check = target
    if normalized_for_check in ('', '.', '..'):
        return ''
    return target

def _source_target_parent_text(self: Any) -> str:
    target_text = worker_logic.normalize_target_path_text(self._safe_line_edit_text('target_edit'))
    if not target_text:
        return ''
    try:
        if worker_logic._is_windows_like_path(target_text):
            normalized = ntpath.normpath(target_text)
            lower = normalized.lower()
            if lower.endswith((
                '.epub', '.zip', '.rar', '.cbz', '.cbr',
                '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
                '.xtc', '.xtch',
            )):
                parent = ntpath.dirname(normalized)
                return '' if parent in ('', '.') else parent
            return '' if normalized in ('', '.') else normalized
        path = Path(target_text)
        if path.suffix.lower() in {
            '.epub', '.zip', '.rar', '.cbz', '.cbr',
            '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
            '.xtc', '.xtch',
        }:
            parent_text = str(path.parent)
            return '' if parent_text in ('', '.') else parent_text
        return target_text
    except Exception:
        return ''

def _planned_open_folder_target_from_settings(self: Any, cfg: Mapping[str, object] | None = None) -> str:
    payload = cfg or {}
    output_dir = self._meaningful_open_folder_target_text(payload.get('output_dir'))
    target_text = worker_logic.normalize_target_path_text(payload.get('target'))
    if output_dir and target_text:
        try:
            if worker_logic._is_windows_like_path(target_text):
                lower = ntpath.normpath(target_text).lower()
                if lower.endswith((
                    '.epub', '.zip', '.rar', '.cbz', '.cbr',
                    '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
                    '.xtc', '.xtch',
                )):
                    return output_dir
            else:
                if Path(target_text).suffix.lower() in {
                    '.epub', '.zip', '.rar', '.cbz', '.cbr',
                    '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
                    '.xtc', '.xtch',
                }:
                    return output_dir
        except Exception:
            return output_dir
    if output_dir:
        # Preserve current folder-batch behavior: explicit output_dir is not
        # used for folder input, but keeping it as a last-known manual target
        # is safer than ever falling back to the app working directory.
        return output_dir
    return self._source_target_parent_text()

def _resolve_conversion_open_folder_target(
    self: Any,
    converted_files: object,
    result: Mapping[str, object] | None = None,
) -> str:
    paths = results_controller.coerce_result_path_list(converted_files)
    payload = result or {}
    for candidate in (
        self.__dict__.get('_active_conversion_open_folder_target', ''),
        payload.get('open_folder_target', ''),
        self.__dict__.get('_last_conversion_open_folder_target', ''),
        self.__dict__.get('selected_output_dir', ''),
    ):
        target = self._meaningful_open_folder_target_text(candidate)
        if target:
            return target
    target = results_controller.resolve_manual_open_folder_target(paths, '')
    if target:
        return target
    return self._source_target_parent_text()

def _show_conversion_completion_card(
    self: Any,
    converted_files: object,
    result: Mapping[str, object] | None = None,
) -> bool:
    card = getattr(self, 'conversion_completion_card', None)
    if card is None:
        return False
    paths = results_controller.coerce_result_path_list(converted_files)
    result_payload = result or {}
    if not paths and not bool(result_payload.get('show_without_paths')):
        self._hide_conversion_completion_card()
        return False
    message = self._build_conversion_completion_card_message(paths, result_payload)
    if not message:
        self._hide_conversion_completion_card()
        return False
    title_label = getattr(self, 'conversion_completion_title_label', None)
    if title_label is not None and hasattr(title_label, 'setText'):
        try:
            title_label.setText(str(result_payload.get('completion_title') or '変換完了'))
        except Exception:
            pass
    message_label = getattr(self, 'conversion_completion_message_label', None)
    if message_label is not None and hasattr(message_label, 'setText'):
        try:
            message_label.setText(message)
        except Exception:
            pass
    try:
        self._completion_card_open_folder_target = self._resolve_conversion_open_folder_target(
            paths,
            result_payload,
        )
        self._last_conversion_open_folder_target = self._completion_card_open_folder_target
    except Exception:
        self._completion_card_open_folder_target = ''
    open_target_available = bool(self._completion_card_open_folder_target or paths)
    for attr_name in (
        'card_open_results_folder_btn',
    ):
        button = getattr(self, attr_name, None)
        if button is None or not hasattr(button, 'setEnabled'):
            continue
        try:
            button.setEnabled(open_target_available)
        except Exception:
            pass
    try:
        card.setVisible(True)
    except Exception:
        return False
    return True

def _build_nav_bar(self):
    nav_bar_plan = self._localized_plan(gui_layouts.build_nav_bar_plan())
    bar = QFrame()
    bar.setObjectName(str(nav_bar_plan.get('object_name', 'navBar')))
    bar.setFixedHeight(self._plan_int_value(nav_bar_plan, 'bar_height', 48))
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(*self._plan_int_tuple_value(nav_bar_plan, 'contents_margins', (12, 0, 12, 0), expected_length=4))
    lay.setSpacing(self._plan_int_value(nav_bar_plan, 'spacing', 8))
    self._add_nav_controls_to_layout(lay, nav_bar_plan=nav_bar_plan, current_label_stretch=1)
    return bar

def _ensure_nav_reverse_control(self: Any, nav_bar_plan: dict | None = None):
    nav_bar_plan = nav_bar_plan or self._localized_plan(gui_layouts.build_nav_bar_plan())
    existing = getattr(self, 'nav_reverse_check', None)
    if existing is not None:
        return existing
    text = str(nav_bar_plan.get('nav_reverse_text', 'ページ送りキー反転'))
    try:
        self.nav_reverse_check = QCheckBox(text, self)
    except TypeError:
        self.nav_reverse_check = QCheckBox(text)
    self.nav_reverse_check.setObjectName(str(nav_bar_plan.get('nav_reverse_object_name', 'navToggle')))
    self.nav_reverse_check.setFocusPolicy(
        self._plan_focus_policy_value(nav_bar_plan, 'nav_reverse_focus_policy', 'no_focus')
    )
    self.nav_reverse_check.setVisible(False)
    self.nav_reverse_check.toggled.connect(self.on_nav_reverse_toggled)
    return self.nav_reverse_check

def _add_nav_controls_to_layout(self, lay: QHBoxLayout, *, nav_bar_plan: dict | None = None, current_label_stretch: int = 0) -> None:
    nav_bar_plan = nav_bar_plan or self._localized_plan(gui_layouts.build_nav_bar_plan())

    self.current_xtc_label = QLabel(str(nav_bar_plan.get('current_xtc_label_text', '表示中: なし')))
    self.current_xtc_label.setObjectName(str(nav_bar_plan.get('current_xtc_label_object_name', 'hintLabel')))
    self.current_xtc_label.setMinimumWidth(self._plan_int_value(nav_bar_plan, 'current_xtc_label_min_width', 0))
    self.current_xtc_label.setMaximumWidth(self._plan_int_value(nav_bar_plan, 'current_xtc_label_max_width', 120))
    show_current_label = self._plan_bool_value(nav_bar_plan, 'current_xtc_label_visible', False)
    self.current_xtc_label.setVisible(show_current_label)
    if show_current_label:
        lay.addWidget(self.current_xtc_label, current_label_stretch)
        lay.addWidget(self._nav_section_separator(nav_bar_plan))
        lay.addSpacing(self._plan_int_value(nav_bar_plan, 'nav_button_side_spacing', 10))

    self._ensure_nav_reverse_control(nav_bar_plan)

    self.prev_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            nav_bar_plan.get('prev_button_text', '前'),
            object_name=str(nav_bar_plan.get('nav_button_object_name', 'navBtn')),
            focus_policy=str(nav_bar_plan.get('nav_button_focus_policy', 'no_focus')),
        ),
        lambda: self.on_nav_button_clicked(-1),
    )
    lay.addWidget(self.prev_btn)

    lay.addWidget(self._dim_label(str(nav_bar_plan.get('page_label_text', 'ページ'))))
    self.page_input = QSpinBox()
    self.page_input.setRange(
        self._plan_int_value(nav_bar_plan, 'page_input_minimum', 0),
        self._plan_int_value(nav_bar_plan, 'page_input_maximum', 0),
    )
    self.page_input.setButtonSymbols(
        self._plan_spin_button_symbols_value(nav_bar_plan, 'page_input_button_symbols', 'no_buttons')
    )
    self.page_input.setKeyboardTracking(
        self._plan_bool_value(nav_bar_plan, 'page_input_keyboard_tracking', False)
    )
    self.page_input.setFixedWidth(self._plan_int_value(nav_bar_plan, 'page_input_width', 60))
    self.page_input.valueChanged.connect(self.on_page_input_changed)
    lay.addWidget(self.page_input)

    self.page_total_label = QLabel(str(nav_bar_plan.get('page_total_label_text', '/ 0')))
    self.page_total_label.setObjectName(str(nav_bar_plan.get('page_total_label_object_name', 'hintLabel')))
    lay.addWidget(self.page_total_label)

    self.next_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            nav_bar_plan.get('next_button_text', '次'),
            object_name=str(nav_bar_plan.get('nav_button_object_name', 'navBtn')),
            focus_policy=str(nav_bar_plan.get('nav_button_focus_policy', 'no_focus')),
        ),
        lambda: self.on_nav_button_clicked(1),
    )
    lay.addWidget(self.next_btn)
    lay.addSpacing(self._plan_int_value(nav_bar_plan, 'nav_button_side_spacing', 10))
    lay.addWidget(self._nav_section_separator(nav_bar_plan))

    self._update_nav_button_texts()

def _nav_section_separator(self, nav_bar_plan: Mapping[str, Any]) -> QFrame:
    sep = QFrame()
    sep.setFrameShape(self._qframe_shape_constant('VLine', self._qframe_shape_constant('NoFrame', 0)))
    sep.setObjectName(str(nav_bar_plan.get('nav_section_separator_object_name', 'navSectionSep')))
    return sep

def _add_preview_zoom_controls_to_layout(self, lay: QHBoxLayout, *, toggle_plan: dict | None = None) -> None:
    toggle_plan = toggle_plan or self._localized_plan(gui_layouts.build_view_toggle_bar_plan())
    lay.addSpacing(self._plan_int_value(toggle_plan, 'preview_zoom_spacing', 8))
    self.preview_zoom_label = self._dim_label(str(toggle_plan.get('preview_zoom_label_text', '表示倍率')))
    self.preview_zoom_label.setVisible(False)
    if self._plan_bool_value(toggle_plan, 'preview_zoom_label_visible', False):
        self.preview_zoom_label.setVisible(True)
        lay.addWidget(self.preview_zoom_label)
    preview_zoom_button_object_name = str(toggle_plan.get('preview_zoom_button_object_name', 'stepBtn'))
    self.preview_zoom_down_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            toggle_plan.get('preview_zoom_down_text', '−'),
            object_name=preview_zoom_button_object_name,
            tooltip=toggle_plan.get('preview_zoom_down_tooltip', '表示倍率を下げます。'),
            fixed_size=toggle_plan.get('preview_zoom_button_size', (24, 24)),
        ),
    )
    lay.addWidget(self.preview_zoom_down_btn)
    self.preview_zoom_spin = QSpinBox()
    self.preview_zoom_spin.setRange(
        self._plan_int_value(toggle_plan, 'preview_zoom_min', 50),
        self._plan_int_value(toggle_plan, 'preview_zoom_max', 300),
    )
    self.preview_zoom_spin.setSingleStep(self._plan_int_value(toggle_plan, 'preview_zoom_step', 10))
    self.preview_zoom_spin.setAccelerated(
        self._plan_bool_value(toggle_plan, 'preview_zoom_spin_accelerated', True)
    )
    self.preview_zoom_spin.setButtonSymbols(
        self._plan_spin_button_symbols_value(toggle_plan, 'preview_zoom_spin_button_symbols', 'no_buttons')
    )
    self.preview_zoom_spin.setValue(self._plan_int_value(toggle_plan, 'preview_zoom_default', 100))
    self.preview_zoom_spin.setSuffix(str(toggle_plan.get('preview_zoom_spin_suffix', '%')))
    self.preview_zoom_spin.setFixedWidth(self._plan_int_value(toggle_plan, 'preview_zoom_spin_width', 78))
    self.preview_zoom_spin.setToolTip(str(toggle_plan.get('preview_zoom_tooltip', '表示倍率です。')))
    self.preview_zoom_spin.valueChanged.connect(self.on_preview_zoom_changed)
    lay.addWidget(self.preview_zoom_spin)
    self.preview_zoom_up_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            toggle_plan.get('preview_zoom_up_text', '+'),
            object_name=preview_zoom_button_object_name,
            tooltip=toggle_plan.get('preview_zoom_up_tooltip', '表示倍率を上げます。'),
            fixed_size=toggle_plan.get('preview_zoom_button_size', (24, 24)),
        ),
    )
    lay.addWidget(self.preview_zoom_up_btn)
    self.preview_zoom_down_btn.clicked.connect(lambda: self.preview_zoom_spin.stepBy(-1))
    self.preview_zoom_up_btn.clicked.connect(lambda: self.preview_zoom_spin.stepBy(1))
    self._sync_preview_zoom_control_state()

