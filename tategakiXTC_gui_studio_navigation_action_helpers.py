from __future__ import annotations

"""Navigation action helpers for ``tategakiXTC_gui_studio.MainWindow``.

These functions keep the user-triggered page navigation control flow out of the
large MainWindow module while preserving the existing public method names via
thin wrappers.
"""

from typing import Any

import tategakiXTC_gui_layouts as gui_layouts
import tategakiXTC_gui_studio_logic as studio_logic


def update_nav_button_texts(self: Any) -> None:
    if not hasattr(self, 'prev_btn') or not hasattr(self, 'next_btn'):
        return
    nav_bar_plan = self._localized_plan(gui_layouts.build_nav_bar_plan())
    prev_text = str(nav_bar_plan.get('prev_button_text', '前'))
    next_text = str(nav_bar_plan.get('next_button_text', '次'))
    if bool(getattr(self, 'nav_buttons_reversed', False)):
        self.prev_btn.setText(next_text)
        self.next_btn.setText(prev_text)
    else:
        self.prev_btn.setText(prev_text)
        self.next_btn.setText(next_text)


def on_nav_reverse_toggled(self: Any, checked: object) -> None:
    self.nav_buttons_reversed = bool(checked)
    self._update_nav_button_texts()
    self.update_navigation_ui()
    self.save_ui_state()


def on_nav_button_clicked(self: Any, logical_step: int) -> None:
    delta = -logical_step if bool(getattr(self, 'nav_buttons_reversed', False)) else logical_step
    self.change_page(delta)


def _font_view_mode_active(self: Any) -> bool:
    return (
        'main_view_mode' in self.__dict__
        and self._normalized_main_view_mode(getattr(self, 'main_view_mode', 'font')) == 'font'
    )


def on_page_input_changed(self: Any, value: int) -> None:
    if _font_view_mode_active(self):
        if self._is_file_viewer_mode_active():
            xtc_pages = self._runtime_xtc_pages()
            nav_state = studio_logic.build_navigation_input_state(
                total=len(xtc_pages),
                current_index=getattr(self, 'current_page_index', 0),
                input_page=value,
            )
            if self._payload_bool_value(nav_state, 'is_valid', False):
                new_idx = self._payload_int_value(nav_state, 'target_index', 0)
                if new_idx != getattr(self, 'current_page_index', 0):
                    self.current_page_index = new_idx
                    self._refresh_loaded_xtc_viewer_profile_cache()
                    try:
                        self._render_current_xtc_page_in_font_view(refresh_navigation=False)
                    except Exception as exc:
                        self._show_preview_message(f'ファイルビューワー表示エラー\n{exc}')
                else:
                    self._sync_active_display_context_for_visible_page()
                self.update_navigation_ui()
                return
        pages = self._runtime_preview_pages()
        if pages:
            nav_state = studio_logic.build_navigation_input_state(
                total=len(pages),
                current_index=getattr(self, 'current_preview_page_index', 0),
                input_page=value,
            )
            if self._payload_bool_value(nav_state, 'is_valid', False):
                new_idx = self._payload_int_value(nav_state, 'target_index', 0)
                if new_idx != getattr(self, 'current_preview_page_index', 0):
                    self.current_preview_page_index = new_idx
                    self.render_current_preview_page()
                else:
                    self._sync_active_display_context_for_visible_page()
                self.update_navigation_ui()
                return
            self._sync_active_display_context_for_visible_page()
            self.update_navigation_ui()
            return
        self._sync_active_display_context_for_visible_page()
        self.update_navigation_ui()
        return

    is_device_preview = self._effective_device_view_source() == 'preview'
    total = len(self._runtime_device_preview_pages()) if is_device_preview else self._xtc_page_count()
    current_device_index = (
        getattr(self, 'current_device_preview_page_index', 0)
        if is_device_preview
        else getattr(self, 'current_page_index', 0)
    )
    nav_state = studio_logic.build_navigation_input_state(
        total=total,
        current_index=current_device_index,
        input_page=value,
    )
    if self._payload_bool_value(nav_state, 'is_valid', False):
        if is_device_preview:
            self._set_current_device_preview_page_index(
                self._payload_int_value(nav_state, 'target_index', 0),
                refresh_navigation=True,
            )
        else:
            self._set_current_page_index(
                self._payload_int_value(nav_state, 'target_index', 0),
                refresh_navigation=True,
            )
        return
    self._sync_active_display_context_for_visible_page()
    self.update_navigation_ui()


def change_page(self: Any, delta: int) -> None:
    if _font_view_mode_active(self):
        if self._is_file_viewer_mode_active():
            xtc_pages = self._runtime_xtc_pages()
            nav_state = studio_logic.build_navigation_delta_state(
                total=len(xtc_pages),
                current_index=getattr(self, 'current_page_index', 0),
                delta=delta,
            )
            target_index = self._payload_int_value(nav_state, 'target_index', getattr(self, 'current_page_index', 0))
            if target_index != getattr(self, 'current_page_index', 0):
                self.current_page_index = target_index
                self._refresh_loaded_xtc_viewer_profile_cache()
                try:
                    self._render_current_xtc_page_in_font_view(refresh_navigation=False)
                except Exception as exc:
                    self._show_preview_message(f'ファイルビューワー表示エラー\n{exc}')
            else:
                self._sync_active_display_context_for_visible_page()
            self.update_navigation_ui()
            return
        pages = self._runtime_preview_pages()
        if pages:
            nav_state = studio_logic.build_navigation_delta_state(
                total=len(pages),
                current_index=getattr(self, 'current_preview_page_index', 0),
                delta=delta,
            )
            new_idx = self._payload_int_value(nav_state, 'target_index', 0)
            if new_idx != getattr(self, 'current_preview_page_index', 0):
                self.current_preview_page_index = new_idx
                self.render_current_preview_page()
            else:
                self._sync_active_display_context_for_visible_page()
            self.update_navigation_ui()
            return
        self._sync_active_display_context_for_visible_page()
        self.update_navigation_ui()
        return

    is_device_preview = self._effective_device_view_source() == 'preview'
    total = len(self._runtime_device_preview_pages()) if is_device_preview else self._xtc_page_count()
    if total <= 0:
        self._sync_active_display_context_for_visible_page()
        self.update_navigation_ui()
        return
    current_device_index = (
        getattr(self, 'current_device_preview_page_index', 0)
        if is_device_preview
        else getattr(self, 'current_page_index', 0)
    )
    nav_state = studio_logic.build_navigation_delta_state(
        total=total,
        current_index=current_device_index,
        delta=delta,
    )
    target_index = self._payload_int_value(nav_state, 'target_index', current_device_index)
    if is_device_preview:
        self._set_current_device_preview_page_index(target_index, refresh_navigation=True)
    else:
        self._set_current_page_index(target_index, refresh_navigation=True)
