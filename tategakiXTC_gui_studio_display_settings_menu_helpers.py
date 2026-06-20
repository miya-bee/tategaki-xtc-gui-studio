from __future__ import annotations

"""Display-settings menu construction helpers for TategakiXTC GUI Studio."""

from typing import Any


def show_display_settings_popup(
    self: Any,
    *,
    menu_class: Any,
    action_group_class: Any,
    point_class: Any,
    application_class: Any,
    output_conflict_options: tuple[tuple[str, str], ...] | list[tuple[str, str]],
) -> None:
    menu = menu_class(self)
    menu.setObjectName('gearPopupMenu')
    menu.setToolTipsVisible(True)
    menu.addSection(self._ui_text('外観'))

    theme_group = action_group_class(menu)
    theme_group.setExclusive(True)

    light_action = menu.addAction(self._ui_text('白基調'))
    light_action.setCheckable(True)
    light_action.setChecked(self.current_ui_theme != 'dark')
    light_action.triggered.connect(lambda checked: checked and self.set_ui_theme('light'))
    theme_group.addAction(light_action)

    dark_action = menu.addAction(self._ui_text('ダーク'))
    dark_action.setCheckable(True)
    dark_action.setChecked(self.current_ui_theme == 'dark')
    dark_action.triggered.connect(lambda checked: checked and self.set_ui_theme('dark'))
    theme_group.addAction(dark_action)

    menu.addSeparator()
    menu.addSection(self._ui_text('その他オプション'))

    # フォルダ自動オープンは v1.3.3.48 で廃止。
    # 保存先を開きたい場合は、変換完了カードまたは変換結果タブのボタンを使う。

    panel_button_action = menu.addAction(self._ui_text('三本線ボタンを表示'))
    panel_button_action.setCheckable(True)
    panel_button_action.setChecked(bool(getattr(self, 'panel_button_visible', True)))
    panel_button_action.toggled.connect(lambda checked: self.set_panel_button_visible(bool(checked)))

    nav_reverse_control = self._ensure_nav_reverse_control()
    nav_reverse_action = menu.addAction(self._ui_text('ページ送りキー反転'))
    nav_reverse_action.setCheckable(True)
    nav_reverse_action.setChecked(bool(nav_reverse_control.isChecked()))
    nav_reverse_action.toggled.connect(lambda checked: nav_reverse_control.setChecked(bool(checked)))

    conflict_menu = menu.addMenu(self._ui_text('同名出力'))
    conflict_group = action_group_class(conflict_menu)
    conflict_group.setExclusive(True)
    for key, label in output_conflict_options:
        action = conflict_menu.addAction(self._ui_text(label))
        action.setCheckable(True)
        action.setChecked(self.current_output_conflict_mode() == key)
        action.triggered.connect(lambda checked, key=key: checked and self.output_conflict_combo.setCurrentIndex(self.output_conflict_combo.findData(key)))
        conflict_group.addAction(action)

    menu_size = menu.sizeHint()
    button_global = self.settings_btn.mapToGlobal(point_class(0, 0))
    x = button_global.x() + self.settings_btn.width() - menu_size.width()
    y = button_global.y() + self.settings_btn.height()

    screen = self.screen() or application_class.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        x = max(available.left(), min(x, available.right() - menu_size.width() + 1))
        y = max(available.top(), min(y, available.bottom() - menu_size.height() + 1))

    try:
        # Call through the class so Python-level test patches on QMenu.exec
        # are honored even on PySide versions whose bound instance method is
        # not replaced by mock.patch.object(QMenu, 'exec', ...).
        menu_class.exec(menu, point_class(x, y))
        return
    except Exception:
        pass
    self._show_information_dialog_with_status_fallback(
        '表示設定',
        '表示設定メニューを開けませんでした。',
        fallback_status_message='表示設定メニューを開けませんでした。',
    )
