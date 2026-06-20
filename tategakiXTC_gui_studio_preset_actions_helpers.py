from __future__ import annotations

"""Preset save/apply/rename action helpers for ``tategakiXTC_gui_studio``.

The entry module keeps thin ``MainWindow`` wrapper methods so existing call
sites, monkey patches, and unbound test calls keep working.  The
implementations here accept the window object and call its existing methods, so
no widget ownership or signal wiring changes are introduced.  The Qt-heavy rename dialog is exposed through a thin entry-module wrapper
that injects the Qt widget classes.  That keeps existing monkey patches and
unbound ``MainWindow`` calls working while moving the implementation out of
the large entry module.
"""

import logging
from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from PySide6.QtWidgets import QMessageBox

import tategakiXTC_gui_core as core
import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_settings_controller as settings_controller

from tategakiXTC_gui_studio_constants import (
    CLOSING_BRACKET_POSITION_MODE_LABELS,
    DEFAULT_PRESET_DEFINITIONS,
    DEFAULT_RENDER_SETTINGS,
    GLYPH_POSITION_MODE_LABELS,
    KINSOKU_MODE_LABELS,
    LATIN_ORIENTATION_MODE_LABELS,
    OPENING_BRACKET_INDENT_MODE_LABELS,
    OUTPUT_FORMAT_LABELS,
    PRESET_FIELDS,
    TATECHUYOKO_DIGIT_MODE_LABELS,
    WAVE_DASH_DRAWING_MODE_LABELS,
    WAVE_DASH_POSITION_MODE_LABELS,
)
from tategakiXTC_gui_studio_ui_helpers import _bulk_block_signals, _coerce_ui_message_text

APP_LOGGER = logging.getLogger('tategaki_xtc')


def verify_preset_save_readback(
    self: Any,
    key: str,
    payload: Mapping[str, object],
) -> tuple[bool, str]:
    if not self._settings_status_is_ok(self.settings_store):
        return False, f'設定ファイルへの書き込みに失敗しました。状態: {self._settings_status_text(self.settings_store)}'

    readback_store = self._settings_store_for_disk_readback()
    if not self._settings_status_is_ok(readback_store):
        return False, f'設定ファイルの再読込に失敗しました。状態: {self._settings_status_text(readback_store)}'

    prefix = self._preset_settings_prefix(key)
    expected_fields = tuple(str(field) for field in payload.keys())
    missing_fields: list[str] = []
    readback_payload: dict[str, object] = {}
    sentinel = object()
    for field in expected_fields:
        settings_key = f'{prefix}/{field}'
        if not self._settings_store_contains_key(readback_store, settings_key):
            missing_fields.append(field)
            continue
        value = self._settings_store_raw_value(readback_store, settings_key, sentinel)
        if value is sentinel:
            missing_fields.append(field)
            continue
        readback_payload[field] = value
    if missing_fields:
        sample = ', '.join(missing_fields[:4])
        if len(missing_fields) > 4:
            sample += f' ほか {len(missing_fields) - 4} 件'
        return False, f'保存後に設定値を再読込できませんでした: {sample}'

    fallback = DEFAULT_PRESET_DEFINITIONS.get(key)
    fallback_font = self._default_font_name()
    expected_norm = self._normalize_preset_payload(
        payload,
        fallback=fallback,
        fallback_font=fallback_font,
        fallback_wave_dash_drawing_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_drawing_mode', 'rotate')),
        fallback_wave_dash_position_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_position_mode', 'standard')),
    )
    actual_norm = self._normalize_preset_payload(
        readback_payload,
        fallback=fallback,
        fallback_font=fallback_font,
        fallback_wave_dash_drawing_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_drawing_mode', 'rotate')),
        fallback_wave_dash_position_mode=str(DEFAULT_RENDER_SETTINGS.get('wave_dash_position_mode', 'standard')),
    )
    mismatched: list[str] = []
    for field in expected_fields:
        if field in PRESET_FIELDS and expected_norm.get(field) != actual_norm.get(field):
            mismatched.append(field)
    if mismatched:
        sample = ', '.join(mismatched[:4])
        if len(mismatched) > 4:
            sample += f' ほか {len(mismatched) - 4} 件'
        return False, f'保存後に再読込した設定値が一致しません: {sample}'
    return True, ''


def show_preset_save_failed(self: Any, reason: str) -> None:
    message = 'プリセットを保存できませんでした。\n\n'
    message += str(reason or '設定ファイルへの書き込みを確認できませんでした。')
    message += '\n\nアプリをzip内や書き込み不可フォルダから起動していないか確認してください。'
    try:
        APP_LOGGER.error('プリセット保存失敗: %s', reason)
    except Exception:
        pass
    self._show_warning_dialog_with_status_fallback(
        'プリセット保存',
        message,
        duration_ms=7000,
    )


def request_preview_refresh_after_preset_apply(self: Any) -> bool:
    """Run the same lightweight preview refresh as the Preview Update button once.

    Preset application touches many UI widgets at once.  The individual
    value-change signals are blocked during the bulk update, so this method
    intentionally performs a single manual preview refresh after the preset
    has fully settled.  Guarding on an instance-created preview button keeps headless unit
    stubs from accidentally invoking the heavy renderer before the UI has
    been built.
    """
    instance_attrs = getattr(self, '__dict__', {})
    has_preview_button = False
    if isinstance(instance_attrs, Mapping):
        has_preview_button = any(
            instance_attrs.get(name) is not None
            for name in ('preview_update_btn', 'preview_refresh_btn')
        )
    if not has_preview_button:
        return False
    refresh = getattr(self, 'manual_refresh_preview', None)
    if not callable(refresh):
        return False
    try:
        refresh()
        return True
    except Exception:
        try:
            APP_LOGGER.exception('プリセット読込後のプレビュー自動更新に失敗しました')
        except Exception:
            pass
        try:
            self.mark_preview_dirty()
        except Exception:
            pass
        return False


def preset_save_confirmation_text(self: Any, preset: Mapping[str, object], preset_name: str) -> str:
    profile_key = str(preset.get('profile', 'x4')).strip().lower() or 'x4'
    profile_text = profile_key.upper()
    out_key = str(preset.get('output_format', 'xtch')).strip().lower() or 'xtch'
    out_text = OUTPUT_FORMAT_LABELS.get(out_key, out_key.upper())
    font_text = core.describe_font_value(str(preset.get('font_file') or '')) or str(preset.get('font_file') or '未指定')
    kinsoku_key = str(preset.get('kinsoku_mode', 'standard')).strip().lower() or 'standard'
    tate_key = studio_logic.normalize_tatechuyoko_digit_mode(preset.get('tatechuyoko_digit_mode', '2'), '2')
    glyph_default = 'standard'
    def _int(name: str, default: int) -> int:
        return worker_logic._int_config_value(preset, name, default)
    def _bool_text(name: str, default: bool = False) -> str:
        return 'ON' if worker_logic._bool_config_value(preset, name, default) else 'OFF'
    def _label(mapping: Mapping[str, str], value: object, default: str = glyph_default) -> str:
        key = str(value if value is not None else default).strip().lower() or default
        return mapping.get(key, key)
    page_number_text = 'ON' if worker_logic._bool_config_value(preset, 'page_number_enabled', False) else 'OFF'
    page_number_size = _int('page_number_font_size', 12)
    return '\n'.join([
        f'保存先プリセット: {preset_name}',
        '',
        '[基本]',
        f'  機種: {profile_text}  /  サイズ: {_int("width", 480)} x {_int("height", 800)}  /  出力形式: {out_text}',
        f'  フォント: {font_text}',
        '',
        '[文字・組版]',
        f'  本文: {_int("font_size", 26)}  /  ルビ: {_int("ruby_size", 12)}  /  行間: {_int("line_spacing", 44)}  /  ルビ消し: {_bool_text("ruby_hide")}',
        f'  余白: 上 {_int("margin_t", 12)}  /  下 {_int("margin_b", 14)}  /  左 {_int("margin_l", 12)}  /  右 {_int("margin_r", 12)}',
        f'  ページ番号: {page_number_text}  /  サイズ: {page_number_size}',
        '',
        '[画像処理]',
        f'  白黒反転: {_bool_text("night_mode")}  /  ディザ: {_bool_text("dither")}  /  しきい値: {_int("threshold", 128)}',
        '',
        '[禁則・補正]',
        f'  禁則: {KINSOKU_MODE_LABELS.get(kinsoku_key, kinsoku_key)}  /  縦中横: {TATECHUYOKO_DIGIT_MODE_LABELS.get(tate_key, tate_key)}  /  欧文表示: {_label(LATIN_ORIENTATION_MODE_LABELS, preset.get("latin_orientation_mode"), "vertical")}  /  行頭鍵括弧: {_label(OPENING_BRACKET_INDENT_MODE_LABELS, preset.get("opening_bracket_indent_mode"), "none")}',
        f'  句読点: {_label(GLYPH_POSITION_MODE_LABELS, preset.get("punctuation_position_mode"))}  /  漢数字 一: {_label(GLYPH_POSITION_MODE_LABELS, preset.get("ichi_position_mode"))}  /  半角数字/記号: {_label(GLYPH_POSITION_MODE_LABELS, preset.get("halfwidth_digit_position_mode"))}  /  半角英字: {_label(GLYPH_POSITION_MODE_LABELS, preset.get("halfwidth_alpha_position_mode"))}',
        f'  中黒: {_label(GLYPH_POSITION_MODE_LABELS, preset.get("middle_dot_position_mode"))}  /  縦中横記号: {_label(GLYPH_POSITION_MODE_LABELS, preset.get("tatechuyoko_symbol_position_mode"))}  /  下鍵括弧: {_label(CLOSING_BRACKET_POSITION_MODE_LABELS, preset.get("lower_closing_bracket_position_mode"))}',
        f'  波線描画: {_label(WAVE_DASH_DRAWING_MODE_LABELS, preset.get("wave_dash_drawing_mode"), "rotate")}  /  波線位置: {_label(WAVE_DASH_POSITION_MODE_LABELS, preset.get("wave_dash_position_mode"))}',
    ])



def preset_rename_dialog_result(
    self: Any,
    *,
    current_name: str,
    default_name: str,
    dialog_cls: Any,
    vbox_layout_cls: Any,
    label_cls: Any,
    line_edit_cls: Any,
    hbox_layout_cls: Any,
    push_button_cls: Any,
) -> tuple[str, str | None]:
    dialog = dialog_cls(self)
    dialog.setWindowTitle(self._ui_text('プリセット名称変更'))
    layout = vbox_layout_cls(dialog)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)

    label = label_cls(self._ui_text('現在選択中のプリセット表示名を変更します。'))
    layout.addWidget(label)

    edit = line_edit_cls(current_name)
    edit.selectAll()
    layout.addWidget(edit)

    hint = label_cls(f'{self._ui_text("既定名:")} {default_name}')
    hint.setObjectName('dimLabel')
    layout.addWidget(hint)

    row = hbox_layout_cls()
    reset_btn = push_button_cls(self._ui_text('既定名に戻す'))
    ok_btn = push_button_cls('OK')
    cancel_btn = push_button_cls(self._ui_text('キャンセル'))
    row.addWidget(reset_btn)
    row.addStretch(1)
    row.addWidget(ok_btn)
    row.addWidget(cancel_btn)
    layout.addLayout(row)

    result: dict[str, str | None] = {'action': 'cancel', 'name': None}

    def accept_name() -> None:
        name = edit.text().strip()
        if not name:
            self._show_warning_dialog_with_status_fallback(
                'プリセット名称変更',
                'プリセット名を空欄にはできません。',
            )
            return
        result['action'] = 'rename'
        result['name'] = name
        dialog.accept()

    def reset_default() -> None:
        result['action'] = 'reset'
        result['name'] = None
        dialog.accept()

    ok_btn.clicked.connect(accept_name)
    cancel_btn.clicked.connect(dialog.reject)
    reset_btn.clicked.connect(reset_default)
    edit.returnPressed.connect(accept_name)

    exec_method = getattr(dialog, 'exec', None) or getattr(dialog, 'exec_', None)
    accepted_value = getattr(dialog_cls, 'Accepted', 1)
    accepted = exec_method() == accepted_value if callable(exec_method) else False
    if not accepted:
        return 'cancel', None
    return str(result.get('action') or 'cancel'), result.get('name')

def rename_preset_display_name(self: Any, key: str) -> None:
    preset = self.preset_definitions.get(key)
    if not preset:
        self._show_warning_dialog_with_status_fallback(
            'プリセット名称変更',
            '名称を変更するプリセットが見つかりませんでした。',
        )
        return
    default_name = self._default_preset_display_name(key)
    current_name = self._normalize_preset_display_name(
        preset.get('button_text') or preset.get('name'),
        fallback=default_name,
    )
    action, new_name = self._preset_rename_dialog_result(
        current_name=current_name,
        default_name=default_name,
    )
    if action == 'cancel':
        return

    display_key = self._preset_display_name_settings_key(key)
    if action == 'reset':
        display_name = default_name
        self.settings_store.remove(display_key)
    else:
        display_name = self._normalize_preset_display_name(new_name, fallback=default_name)
        self.settings_store.setValue(display_key, display_name)

    self.settings_store.sync()
    updated = dict(preset)
    updated['button_text'] = display_name
    updated['name'] = display_name
    self.preset_definitions[key] = updated
    self._refresh_preset_ui()
    self._set_combo_to_data(self.preset_combo, key)
    self._sync_selected_preset_summary(key)
    self.save_ui_state()
    self._show_ui_status_message_unless_render_failure_visible(
        f'プリセット名を「{display_name}」に変更しました。',
        3500,
    )


def save_preset(self: Any, key: str) -> None:
    p = self.preset_definitions.get(key)
    if not p:
        return
    payload = settings_controller.build_preset_save_payload(
        current_preset=self.current_preset_payload(),
        live_widget_payload=self._live_preset_widget_payload(),
    )
    summary_payload = settings_controller.build_preset_summary_payload(
        stored_preset=p,
        pending_payload=payload,
    )
    preset_name = self._preset_display_name(p)
    summary = self._preset_save_confirmation_text(summary_payload, preset_name)
    yes_button = getattr(QMessageBox, 'Yes', 1)
    no_button = getattr(QMessageBox, 'No', 0)
    ans = self._ask_question_dialog_with_status_fallback(
        'プリセット保存',
        f"現在の設定を{preset_name}へ保存しますか？\n\n{summary}",
        yes_button | no_button,
        yes_button,
        fallback_status_message='プリセット保存の確認ダイアログを表示できませんでした。',
        fallback_answer=no_button,
    )
    if ans != yes_button:
        return
    updated = deepcopy(p)
    updated.update(payload)
    prefix = self._preset_settings_prefix(key)
    try:
        for field, value in payload.items():
            self.settings_store.setValue(f'{prefix}/{field}', value)
        self.settings_store.sync()
        verified, reason = self._verify_preset_save_readback(key, payload)
    except Exception as exc:
        APP_LOGGER.exception('プリセット保存中に例外が発生しました')
        self._show_preset_save_failed(str(exc))
        return
    if not verified:
        self._show_preset_save_failed(reason)
        return

    self.preset_definitions[key] = updated
    self._refresh_preset_ui()
    self._sync_selected_preset_summary(key)
    self._show_ui_status_message_unless_render_failure_visible(
        settings_controller.build_preset_status_message('save', preset_name),
        4000,
    )


def apply_preset(self: Any, key: str) -> None:
    p = self.preset_definitions.get(key)
    if not p:
        self._show_ui_status_message_unless_render_failure_visible(
            '適用するプリセットが見つかりませんでした。',
            3000,
        )
        return

    apply_context_obj = settings_controller.build_preset_apply_context(
        preset_key=key,
        stored_preset=p,
        fallback_preset=DEFAULT_PRESET_DEFINITIONS.get(key),
        fallback_font=self._default_font_name(),
        combo_entries=self._preset_combo_entries(),
        normalize_preset_payload=self._normalize_preset_payload,
        preset_display_name=self._preset_display_name,
    )
    apply_context = apply_context_obj if isinstance(apply_context_obj, Mapping) else {}
    idx = self._payload_optional_int_value(apply_context, 'combo_index')
    if idx is None:
        idx = -1
    preset_combo = getattr(self, 'preset_combo', None)
    if idx >= 0 and preset_combo is not None and preset_combo.currentIndex() != idx:
        with _bulk_block_signals(preset_combo):
            preset_combo.setCurrentIndex(idx)

    payload_obj = apply_context.get('payload', {})
    payload = dict(payload_obj) if isinstance(payload_obj, Mapping) else {}
    with _bulk_block_signals(*self._preset_apply_widgets()):
        self._apply_settings_payload_to_ui(payload)

    self._sync_loaded_xtc_profile_ui_override()
    self._apply_profile_runtime_state()
    self._apply_viewer_display_runtime_state()
    mode = getattr(self, 'main_view_mode', 'font')
    normalized_mode = self._normalized_main_view_mode(mode)
    self._refresh_preset_ui()
    self._finalize_setting_change(update_status=True)
    self._sync_selected_preset_summary(key)

    # sweep350: プリセット読込後の自動プレビュー更新は、手動の
    # 「プレビュー更新」と同じ経路を優先し、1回だけ走らせる。
    # これが使える実GUIでは、ここで古い runtime preview を先に再描画
    # しない。ヘッドレス/旧スタブで手動更新経路が無い場合だけ、従来の
    # 表示中ページ再描画へフォールバックする。
    auto_refresh_requested = self._request_preview_refresh_after_preset_apply()
    if not auto_refresh_requested:
        try:
            if normalized_mode == 'device':
                self._refresh_active_view_after_mode_change(mode)
            elif self._runtime_preview_pages():
                self._refresh_font_preview_display_if_needed()
            else:
                self._refresh_font_preview_display_if_needed()
                self._refresh_active_view_after_mode_change(mode)
        except Exception:
            pass

    status_message = _coerce_ui_message_text(apply_context.get('status_message'))
    self._show_ui_status_message_unless_render_failure_visible(status_message, 3000)
