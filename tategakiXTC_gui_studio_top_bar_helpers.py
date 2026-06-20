from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout

try:
    from PySide6.QtWidgets import QSizePolicy
except Exception:  # pragma: no cover - test stubs may omit QSizePolicy
    QSizePolicy = None  # type: ignore[assignment]

import tategakiXTC_gui_layouts as gui_layouts
from tategakiXTC_gui_studio_constants import DEFAULT_TOP_PATH_BUTTON_WIDTH
from tategakiXTC_gui_studio_widgets import SourceDropLineEdit


def build_top_bar(self):
    top_bar_plan = self._localized_plan(gui_layouts.build_top_bar_plan(path_button_width=DEFAULT_TOP_PATH_BUTTON_WIDTH))
    bar = QFrame()
    bar.setObjectName('topBar')
    bar.setFixedHeight(self._plan_int_value(top_bar_plan, 'bar_height', 56))
    lay = QHBoxLayout(bar)
    lay.setContentsMargins(*self._plan_int_tuple_value(top_bar_plan, 'contents_margins', (16, 0, 12, 0), expected_length=4))
    lay.setSpacing(self._plan_int_value(top_bar_plan, 'spacing', 10))

    # v1.3.8.5: remove the subtle version label from the top bar.
    # Keep version information in dialogs/docs, but reserve this row for
    # file controls now that the 3-pane UI needs more horizontal room.

    btn_file = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('file_button_text', 'ファイルを開く'),
            object_name='topBtn',
            tooltip=top_bar_plan.get('file_button_tooltip', '1つのファイルを読み込みます'),
            minimum_width=top_bar_plan.get('top_path_button_min_width', 0),
        ),
        lambda: self.select_target_path(True),
    )


    btn_folder = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('folder_button_text', '保存先を選ぶ'),
            object_name='topBtn',
            tooltip=top_bar_plan.get('folder_button_tooltip', '変換後のXTC保存先を選びます'),
            minimum_width=top_bar_plan.get('top_path_button_min_width', 0),
        ),
        self.select_output_folder,
    )

    btn_output_reset = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('output_reset_button_text', '保存先リセット'),
            object_name='topBtn',
            tooltip=top_bar_plan.get('output_reset_button_tooltip', '保存先指定を解除し、ソースファイルと同じフォルダへ戻します'),
            minimum_width=top_bar_plan.get('top_path_button_min_width', 0),
        ),
        self.reset_output_folder,
    )

    self.folder_batch_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('folder_batch_button_text', 'フォルダ一括変換'),
            object_name='topBtn',
            tooltip=top_bar_plan.get('folder_batch_button_tooltip', 'フォルダ内のファイルをまとめて変換します'),
            minimum_width=top_bar_plan.get('folder_batch_button_min_width', 0),
        ),
        self._open_folder_batch_dialog,
    )

    lay.addWidget(btn_file)
    lay.addWidget(self.folder_batch_btn)
    lay.addWidget(self._v_sep())
    lay.addWidget(btn_folder)
    lay.addWidget(btn_output_reset)
    lay.addWidget(self._help_icon_button(
        str(top_bar_plan.get('top_buttons_help_text', '上部ボタンの違いを説明します。')),
        tooltip=str(top_bar_plan.get('top_buttons_help_tooltip', '上部ボタンの違い')),
        title=str(top_bar_plan.get('top_buttons_help_title', '上部ボタンの使い分け')),
    ))

    self.target_edit = SourceDropLineEdit()
    self.target_edit.setObjectName('targetEdit')
    self.target_edit.setPlaceholderText(str(top_bar_plan.get('target_placeholder', 'EPUB / ZIP / CBZ / CBR / RAR / TXT / Markdown / 画像 / フォルダ')))
    target_base_tooltip = str(top_bar_plan.get('target_tooltip', '変換対象のファイルまたはフォルダを入力します。ソースファイルはここへドラッグ＆ドロップできます。'))
    self.target_edit.setToolTip(target_base_tooltip)
    self.target_edit.setMinimumWidth(self._plan_int_value(top_bar_plan, 'target_minimum_width', 240))
    if QSizePolicy is not None:
        try:
            self.target_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        except Exception:
            pass

    def _refresh_target_tooltip(text: str) -> None:
        normalized = str(text or '').strip()
        if normalized:
            self.target_edit.setToolTip(f'{normalized}\n\n{target_base_tooltip}')
        else:
            self.target_edit.setToolTip(target_base_tooltip)

    self.target_edit.textChanged.connect(_refresh_target_tooltip)
    self.target_edit.textChanged.connect(self.on_target_text_changed)
    self.target_edit.editingFinished.connect(self._update_top_status)
    self.target_edit.editingFinished.connect(self.save_ui_state)
    self.target_edit.editingFinished.connect(self.on_target_editing_finished)
    self.target_edit.sourcePathDropped.connect(self._apply_dropped_target_path)
    lay.addWidget(self.target_edit, 1)

    lay.addWidget(self._v_sep())

    self.run_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('run_button_text', '▶  変換実行'),
            object_name='runBtn',
            fixed_width=top_bar_plan.get('run_button_width', 130),
        ),
        self.start_conversion,
    )
    lay.addWidget(self.run_btn)

    self.stop_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('stop_button_text', '■  停止'),
            object_name='stopBtn',
            fixed_width=top_bar_plan.get('stop_button_width', 90),
            enabled=False,
        ),
        self.stop_conversion,
    )
    lay.addWidget(self.stop_btn)
    lay.addWidget(self._v_sep())

    self.panel_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('panel_button_text', '≡'),
            object_name='iconBtn',
            tooltip=top_bar_plan.get('panel_button_tooltip', '左パネルの表示/非表示'),
            fixed_size=top_bar_plan.get('panel_button_size', (36, 36)),
            focus_policy='no_focus',
        ),
        self.toggle_left_panel,
    )
    lay.addWidget(self.panel_btn)

    help_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('help_button_text', '?'),
            object_name='iconBtn',
            tooltip=top_bar_plan.get('help_button_tooltip', '使い方の流れ'),
            fixed_size=top_bar_plan.get('help_button_size', (36, 36)),
            focus_policy='no_focus',
        ),
        self.show_help_dialog,
    )
    lay.addWidget(help_btn)

    self.settings_btn = self._make_button_from_plan(
        gui_layouts.build_button_widget_plan(
            top_bar_plan.get('settings_button_text', '⚙'),
            object_name='iconBtn',
            tooltip=top_bar_plan.get('settings_button_tooltip', '表示設定'),
            fixed_size=top_bar_plan.get('settings_button_size', (36, 36)),
            focus_policy='no_focus',
        ),
        self.show_display_settings_popup,
    )
    lay.addWidget(self.settings_btn)

    return bar



def _install_folder_batch_menu_action(self: Any) -> None:
    """Add the first low-risk UI entry point for folder batch conversion."""
    try:
        from tategakiXTC_folder_batch_mainwindow_launcher import (
            install_folder_batch_menu_action_best_effort,
        )

        install_folder_batch_menu_action_best_effort(self)
    except Exception:
        logging.getLogger('tategaki_xtc').exception('フォルダ一括変換メニューの追加に失敗しました')


def _open_folder_batch_dialog(self: Any) -> None:
    """Open the folder batch dialog and run it through the worker bridge."""
    if bool(self.__dict__.get('_folder_batch_running', False)):
        try:
            self._show_ui_status_message_with_reflection_or_direct_fallback(
                'フォルダ一括変換はすでに実行中です。',
                5000,
            )
        except Exception:
            pass
        return
    if self.__dict__.get('worker') is not None:
        try:
            self._show_warning_dialog_with_status_fallback(
                'フォルダ一括変換',
                '通常変換の実行中は、フォルダ一括変換を開始できません。現在の変換が終わってからもう一度実行してください。',
            )
        except Exception:
            pass
        return
    try:
        from tategakiXTC_folder_batch_mainwindow_launcher import (
            open_folder_batch_dialog_for_mainwindow_real_or_warn,
        )

        open_folder_batch_dialog_for_mainwindow_real_or_warn(self)
    except Exception as exc:
        try:
            self.__dict__['_folder_batch_running'] = False
            self.__dict__['_folder_batch_cancel_requested'] = False
        except Exception:
            pass
        logging.getLogger('tategaki_xtc').exception('フォルダ一括変換ダイアログの起動に失敗しました')
        self._show_warning_dialog_with_status_fallback(
            'フォルダ一括変換',
            f'フォルダ一括変換を開始できませんでした: {exc}',
        )
