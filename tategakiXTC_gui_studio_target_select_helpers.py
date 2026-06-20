from __future__ import annotations

"""Target, output-folder, and external-font selection helpers for MainWindow.

These functions keep the public ``MainWindow`` method names in the entry module
as thin wrappers while moving dialog/result state updates out of the large
entry file.  They intentionally call back through ``self`` methods so tests and
instance-level monkey patches remain compatible.
"""

from pathlib import Path
from typing import Any

import tategakiXTC_worker_logic as worker_logic

_TARGET_FILE_SUFFIXES = (
    '.epub', '.zip', '.rar', '.cbz', '.cbr',
    '.txt', '.md', '.markdown', '.png', '.jpg', '.jpeg', '.webp',
    '.xtc', '.xtch',
)


def _parent_dir_text_for_file_like_path(path_text: str) -> str:
    lower_text = path_text.lower()
    if lower_text.endswith(_TARGET_FILE_SUFFIXES):
        slash_pos = max(path_text.rfind('/'), path_text.rfind('\\'))
        if slash_pos > 0:
            return path_text[:slash_pos] or path_text
    return path_text


def _apply_dropped_target_path(self: Any, path: object) -> None:
    normalized_path = worker_logic.normalize_target_path_text(path)
    if not normalized_path:
        return
    self._set_target_path_for_normal_preview(normalized_path)
    self._update_top_status()
    self.save_ui_state()
    self._show_ui_status_message_unless_render_failure_visible('ドロップしたファイルを変換対象に設定しました。', 3000)
    self._schedule_target_preview_refresh(reset_page=True)


def _default_output_folder_start_dir(self: Any) -> str:
    selected = worker_logic.normalize_target_path_text(self.__dict__.get('selected_output_dir', ''))
    if selected:
        return selected
    current = worker_logic.normalize_target_path_text(self.target_edit.text()) or str(Path.home())
    return _parent_dir_text_for_file_like_path(current)


def _selected_output_dir_label_text(self: Any) -> str:
    selected = worker_logic.normalize_target_path_text(self.__dict__.get('selected_output_dir', ''))
    return selected or self._ui_text('ソースファイルと同じフォルダ')


def _announce_selected_output_dir(self: Any, timeout: int = 5000) -> None:
    self._show_ui_status_message_unless_render_failure_visible(
        f'{self._ui_text("保存先:")} {self._selected_output_dir_label_text()}',
        timeout,
    )


def reset_output_folder(self: Any) -> None:
    self.selected_output_dir = ''
    # Clear any previously selected output-folder target held by the
    # completion card.  Without this, pressing [保存先リセット] could leave
    # the next [保存先を開く] action biased toward an older folder if the next
    # conversion result did not provide a fresh explicit target.
    self._completion_card_open_folder_target = ''
    self._last_conversion_open_folder_target = ''
    self._active_conversion_open_folder_target = ''
    self.save_ui_state()
    self._show_information_dialog_with_status_fallback(
        '保存先リセット',
        '保存先指定を解除しました。\n次回の単体変換は、ソースファイルと同じフォルダへ保存します。',
        fallback_status_message='保存先指定を解除しました。次回の単体変換はソースファイルと同じフォルダへ保存します。',
    )
    self._announce_selected_output_dir()
    try:
        self._update_top_status()
    except Exception:
        pass


def select_output_folder(self: Any) -> None:
    start_dir = self._default_output_folder_start_dir()
    path = self._get_existing_directory_with_status_fallback(
        '保存先フォルダを選択',
        start_dir,
        fallback_status_message='保存先フォルダの選択ダイアログを開けませんでした。',
    )
    if not path:
        return
    normalized_path = worker_logic.normalize_target_path_text(path)
    self.selected_output_dir = normalized_path
    self._last_conversion_open_folder_target = normalized_path
    self._completion_card_open_folder_target = normalized_path
    self.save_ui_state()
    self._announce_selected_output_dir()


def select_target_path(self: Any, as_file: bool) -> None:
    if not as_file:
        self.select_output_folder()
        return
    current = worker_logic.normalize_target_path_text(self.target_edit.text()) or str(Path.home())
    path, _ = self._get_open_file_name_with_status_fallback(
        '変換対象を選択',
        current,
        'Supported (*.epub *.zip *.rar *.cbz *.cbr *.txt *.md *.markdown *.png *.jpg *.jpeg *.webp);;All Files (*.*)',
        fallback_status_message='変換対象のファイル選択ダイアログを開けませんでした。',
    )
    if path:
        normalized_path = worker_logic.normalize_target_path_text(path)
        self._set_target_path_for_normal_preview(normalized_path)
        self._update_top_status()
        self.save_ui_state()
        # ファイル指定直後はプレビューを更新する。
        # ただし handler 内では重い生成を直接走らせず、UI イベントループへ
        # 一度戻してから preview_page_limit_spin の指定ページ数だけを生成する。
        # 全文変換・本変換ルートへは入らない。
        self._schedule_target_preview_refresh(reset_page=True)


def select_font_file(self: Any) -> None:
    path, _ = self._get_open_file_name_with_status_fallback(
        'フォントファイルを選択',
        str(Path.home()),
        'Fonts (*.ttf *.ttc *.otf);;All Files (*.*)',
        fallback_status_message='フォントファイル選択ダイアログを開けませんでした。',
    )
    if path:
        preserved_night_mode = None
        if hasattr(self, 'night_check') and hasattr(self.night_check, 'isChecked'):
            try:
                preserved_night_mode = bool(self.night_check.isChecked())
            except Exception:
                preserved_night_mode = None
        normalized = self._normalize_font_setting_value(
            path,
            self.current_font_value() or self._default_font_name(),
        )
        if not normalized:
            return
        self._ensure_font_combo_value(normalized)
        self._set_current_font_value(normalized)
        if preserved_night_mode is not None and bool(self.night_check.isChecked()) != preserved_night_mode:
            self.night_check.setChecked(preserved_night_mode)
        self._finalize_setting_change()
