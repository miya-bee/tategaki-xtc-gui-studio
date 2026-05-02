from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STUDIO_SOURCE = (ROOT / 'tategakiXTC_gui_studio.py').read_text(encoding='utf-8')
LAYOUTS_SOURCE = (ROOT / 'tategakiXTC_gui_layouts.py').read_text(encoding='utf-8')


def _method_source(source: str, method_name: str) -> str:
    marker = f"    def {method_name}("
    start = source.index(marker)
    next_start = source.find("\n    def ", start + 1)
    if next_start == -1:
        return source[start:]
    return source[start:next_start]


class Sweep368LayoutContractRegressionTests(unittest.TestCase):
    """sweep368でOKになったGUI整理の巻き戻りを静的に検出する。"""

    def test_left_pane_keeps_file_viewer_section_after_output_display_section(self):
        self.assertIn(
            "section_keys = ('preset', 'font', 'image', 'display', 'fileviewer')",
            LAYOUTS_SOURCE,
        )
        self.assertLess(
            LAYOUTS_SOURCE.index("'display'"),
            LAYOUTS_SOURCE.index("'fileviewer'"),
        )
        self.assertIn("'fileviewer': self._section_file_viewer", STUDIO_SOURCE)

    def test_file_viewer_section_keeps_xtc_xtch_open_button_and_help(self):
        source = _method_source(STUDIO_SOURCE, '_section_file_viewer')

        self.assertIn("'ファイルビューワー'", source)
        self.assertIn("file_viewer_plan = gui_layouts.build_file_viewer_section_plan()", source)
        self.assertIn("self.open_xtc_btn", source)
        self.assertIn("file_viewer_plan.get('open_xtc_button_text', 'XTC/XTCHを開く')", source)
        self.assertIn("file_viewer_plan.get(", source)
        self.assertIn("'open_xtc_help_text'", source)
        self.assertIn("self.open_xtc_file", source)
        self.assertIn("既存の .xtc / .xtch ファイルを右ペインの実機ビューへ読み込んで確認します。", source)

    def test_preview_toolbar_keeps_actual_size_and_guides_help_layout(self):
        source = _method_source(STUDIO_SOURCE, '_add_preview_display_toggles_to_layout')

        actual_size_index = source.index("self._add_optional_widget_to_layout(lay, 'actual_size_check')")
        actual_help_index = source.index("self._add_optional_widget_to_layout(lay, 'actual_size_help_btn')")
        spacing_index = source.index("self._plan_int_value(preview_toggle_plan, 'toggle_spacing', 18)")
        guides_index = source.index("self._add_optional_widget_to_layout(lay, 'guides_check')")
        guides_help_index = source.index("self._add_optional_widget_to_layout(lay, 'guides_help_btn')")

        self.assertLess(actual_size_index, actual_help_index)
        self.assertLess(actual_help_index, spacing_index)
        self.assertLess(spacing_index, guides_index)
        self.assertLess(guides_index, guides_help_index)

    def test_preview_toolbar_optional_widget_insertions_use_shared_helper(self):
        helper_source = _method_source(STUDIO_SOURCE, '_add_optional_widget_to_layout')
        toolbar_source = _method_source(STUDIO_SOURCE, '_add_preview_display_toggles_to_layout')

        self.assertIn("widget = getattr(self, attr_name, None)", helper_source)
        self.assertIn("if widget is not None:", helper_source)
        self.assertIn("lay.addWidget(widget)", helper_source)
        self.assertIn("self._add_optional_widget_to_layout(lay, 'actual_size_check')", toolbar_source)
        self.assertIn("self._add_optional_widget_to_layout(lay, 'actual_size_help_btn')", toolbar_source)
        self.assertIn("self._add_optional_widget_to_layout(lay, 'guides_check')", toolbar_source)
        self.assertIn("self._add_optional_widget_to_layout(lay, 'guides_help_btn')", toolbar_source)
        self.assertNotIn("getattr(self, 'actual_size_check', None)", toolbar_source)

    def test_preview_toolbar_help_texts_are_substantive(self):
        source = STUDIO_SOURCE

        self.assertIn("preview_toggle_plan = gui_layouts.build_preview_display_toggle_plan()", source)
        self.assertIn("self.actual_size_help_btn = self._help_icon_button(actual_size_help_text)", source)
        self.assertIn("ONにすると右ペインの倍率欄は「実寸補正」に切り替わります。", LAYOUTS_SOURCE)
        self.assertIn("表示が実物より大きい/小さい場合は、この実寸補正を調整してください。", LAYOUTS_SOURCE)

        self.assertIn("self.guides_help_btn = self._help_icon_button(guide_help_text)", source)
        self.assertIn("本文が端に寄りすぎていないか、余白設定が意図通りかを確認するときに使います。", LAYOUTS_SOURCE)
        self.assertIn("変換結果そのものを書き換える機能ではなく、確認用の表示補助です。", LAYOUTS_SOURCE)

    def test_view_toggle_button_chrome_is_owned_by_plan(self):
        source = _method_source(STUDIO_SOURCE, '_build_view_toggle_bar')

        self.assertIn("'top_row_contents_margins': (0, 0, 0, 0)", LAYOUTS_SOURCE)
        self.assertIn("'bottom_row_contents_margins': (0, 0, 0, 0)", LAYOUTS_SOURCE)
        self.assertIn("'view_button_object_name': 'viewToggleBtn'", LAYOUTS_SOURCE)
        self.assertIn("'view_button_focus_policy': 'no_focus'", LAYOUTS_SOURCE)
        self.assertIn("'view_button_checkable': True", LAYOUTS_SOURCE)
        self.assertIn("'font_view_checked_default': True", LAYOUTS_SOURCE)
        self.assertIn("'device_view_checked_default': False", LAYOUTS_SOURCE)
        self.assertIn("self._plan_int_tuple_value(toggle_plan, 'top_row_contents_margins', (0, 0, 0, 0), expected_length=4)", source)
        self.assertIn("self._plan_int_tuple_value(toggle_plan, 'bottom_row_contents_margins', (0, 0, 0, 0), expected_length=4)", source)
        self.assertIn("toggle_plan.get('view_button_object_name', 'viewToggleBtn')", source)
        self.assertIn("self._plan_bool_value(toggle_plan, 'view_button_checkable', True)", source)
        self.assertIn("self._plan_bool_value(toggle_plan, 'font_view_checked_default', True)", source)
        self.assertIn("self._plan_bool_value(toggle_plan, 'device_view_checked_default', False)", source)
        self.assertIn("toggle_plan.get('view_button_focus_policy', 'no_focus')", source)


    def test_preview_zoom_width_and_spacing_contracts_are_owned_by_plan(self):
        self.assertIn("'preview_zoom_spin_width': 78", LAYOUTS_SOURCE)
        self.assertIn("'display_toggle_spacing': 10", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_spacing': 8", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_down_text': '−'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_button_object_name': 'stepBtn'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_up_text': '+'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_spin_suffix': '%'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_spin_button_symbols': 'no_buttons'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_spin_accelerated': True", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_label_text': '表示倍率'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_actual_size_label_text': '実寸補正'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_normal_tooltip': 'フォントビュー（実寸近似OFF）と実機ビューの表示倍率です。'", LAYOUTS_SOURCE)
        self.assertIn("'preview_zoom_actual_size_tooltip': '実寸近似ON: 実機サイズに合わせる補正倍率です。'", LAYOUTS_SOURCE)

        build_source = _method_source(STUDIO_SOURCE, '_build_view_toggle_bar')
        zoom_source = _method_source(STUDIO_SOURCE, '_add_preview_zoom_controls_to_layout')
        self.assertIn("self._plan_int_value(toggle_plan, 'display_toggle_spacing', 10)", build_source)
        self.assertIn("self._plan_int_value(toggle_plan, 'preview_zoom_spacing', 8)", zoom_source)
        self.assertIn("toggle_plan.get('preview_zoom_down_text', '−')", zoom_source)
        self.assertIn("toggle_plan.get('preview_zoom_up_text', '+')", zoom_source)
        self.assertIn("preview_zoom_button_object_name = str(toggle_plan.get('preview_zoom_button_object_name', 'stepBtn'))", zoom_source)
        self.assertIn("self._plan_bool_value(toggle_plan, 'preview_zoom_spin_accelerated', True)", zoom_source)
        self.assertIn("self._plan_spin_button_symbols_value(toggle_plan, 'preview_zoom_spin_button_symbols', 'no_buttons')", zoom_source)
        self.assertNotIn('preview_zoom_spin_symbols = str(', zoom_source)
        self.assertIn("toggle_plan.get('preview_zoom_spin_suffix', '%')", zoom_source)
        self.assertIn("self._plan_int_value(toggle_plan, 'preview_zoom_spin_width', 78)", zoom_source)
        self.assertIn("self.preview_zoom_spin.setSuffix(str(toggle_plan.get('preview_zoom_spin_suffix', '%')))", zoom_source)
        self.assertNotIn("self.preview_zoom_spin.setSuffix('%')", zoom_source)

    def test_preview_zoom_dynamic_label_and_tooltips_are_owned_by_plan(self):
        source = _method_source(STUDIO_SOURCE, '_sync_preview_zoom_control_state')

        self.assertIn('toggle_plan = gui_layouts.build_view_toggle_bar_plan()', source)
        self.assertIn("'preview_zoom_actual_size_label_text' if actual_size else 'preview_zoom_label_text'", source)
        self.assertIn("'preview_zoom_actual_size_tooltip' if actual_size else 'preview_zoom_normal_tooltip'", source)


    def test_preview_view_help_text_is_owned_by_view_toggle_plan(self):
        source = _method_source(STUDIO_SOURCE, '_preview_view_help_text')
        self.assertIn('toggle_plan = gui_layouts.build_view_toggle_bar_plan()', source)
        self.assertIn("'help_text'", source)
        self.assertIn("'help_text': 'フォントビュー:", LAYOUTS_SOURCE)
        self.assertIn('実機ビュー: 変換後のXTCをページ送りしながら実機に近い形で確認します。', LAYOUTS_SOURCE)

    def test_navigation_widget_identity_is_owned_by_nav_bar_plan(self):
        source = _method_source(STUDIO_SOURCE, '_add_nav_controls_to_layout')
        self.assertIn("'current_xtc_label_object_name'", LAYOUTS_SOURCE)
        self.assertIn("'current_xtc_label_min_width': 0", LAYOUTS_SOURCE)
        self.assertIn("'nav_reverse_object_name'", LAYOUTS_SOURCE)
        self.assertIn("'nav_reverse_focus_policy'", LAYOUTS_SOURCE)
        self.assertIn("'page_input_minimum': 0", LAYOUTS_SOURCE)
        self.assertIn("'page_input_maximum': 0", LAYOUTS_SOURCE)
        self.assertIn("'page_input_empty_minimum': 0", LAYOUTS_SOURCE)
        self.assertIn("'page_input_empty_maximum': 0", LAYOUTS_SOURCE)
        self.assertIn("'page_input_active_minimum': 1", LAYOUTS_SOURCE)
        self.assertIn("'page_input_button_symbols': 'no_buttons'", LAYOUTS_SOURCE)
        self.assertIn("'page_input_keyboard_tracking': False", LAYOUTS_SOURCE)
        self.assertIn("'page_total_label_object_name'", LAYOUTS_SOURCE)
        self.assertIn("'nav_button_object_name'", LAYOUTS_SOURCE)
        self.assertIn("'nav_button_focus_policy'", LAYOUTS_SOURCE)
        self.assertIn("nav_bar_plan.get('current_xtc_label_object_name', 'hintLabel')", source)
        self.assertIn("self._plan_int_value(nav_bar_plan, 'current_xtc_label_min_width', 0)", source)
        self.assertIn("nav_bar_plan.get('nav_reverse_object_name', 'navToggle')", source)
        self.assertIn("self._plan_focus_policy_value(nav_bar_plan, 'nav_reverse_focus_policy', 'no_focus')", source)
        self.assertNotIn("str(nav_bar_plan.get('nav_reverse_focus_policy', 'no_focus')).strip().lower()", source)
        self.assertIn("self._plan_int_value(nav_bar_plan, 'page_input_minimum', 0)", source)
        self.assertIn("self._plan_int_value(nav_bar_plan, 'page_input_maximum', 0)", source)
        self.assertIn("self._plan_spin_button_symbols_value(nav_bar_plan, 'page_input_button_symbols', 'no_buttons')", source)
        self.assertNotIn('page_input_symbols = str(', source)
        self.assertIn("self._plan_bool_value(nav_bar_plan, 'page_input_keyboard_tracking', False)", source)
        self.assertIn("nav_bar_plan.get('page_total_label_object_name', 'hintLabel')", source)
        self.assertIn("nav_bar_plan.get('nav_button_object_name', 'navBtn')", source)
        self.assertIn("nav_bar_plan.get('nav_button_focus_policy', 'no_focus')", source)


    def test_spin_button_symbols_tokens_are_resolved_by_shared_helper(self):
        source = _method_source(STUDIO_SOURCE, '_plan_spin_button_symbols_value')

        self.assertIn("'up_down_arrows': QSpinBox.UpDownArrows", source)
        self.assertIn("'no_buttons': QSpinBox.NoButtons", source)
        self.assertIn("default == 'up_down_arrows'", source)

    def test_page_input_runtime_range_is_owned_by_nav_bar_plan(self):
        source = _method_source(STUDIO_SOURCE, '_reset_xtc_page_input')

        self.assertIn("'page_input_empty_minimum': 0", LAYOUTS_SOURCE)
        self.assertIn("'page_input_empty_maximum': 0", LAYOUTS_SOURCE)
        self.assertIn("'page_input_active_minimum': 1", LAYOUTS_SOURCE)
        self.assertIn('nav_bar_plan = gui_layouts.build_nav_bar_plan()', source)
        self.assertIn("self._plan_int_value(nav_bar_plan, 'page_input_empty_minimum', 0)", source)
        self.assertIn("self._plan_int_value(nav_bar_plan, 'page_input_empty_maximum', 0)", source)
        self.assertIn("self._plan_int_value(nav_bar_plan, 'page_input_active_minimum', 1)", source)
        self.assertIn('self.page_input.setRange(minimum, maximum)', source)


    def test_page_total_label_format_is_owned_by_nav_bar_plan(self):
        source = _method_source(STUDIO_SOURCE, '_apply_xtc_navigation_ui')

        self.assertIn("'page_total_label_format': '/ {total}'", LAYOUTS_SOURCE)
        self.assertIn('nav_bar_plan = gui_layouts.build_nav_bar_plan()', source)
        self.assertIn("nav_bar_plan.get('page_total_label_format', '/ {total}')", source)
        self.assertIn('total_label_format.format(total=total)', source)

    def test_right_preview_stack_chrome_contracts_are_owned_by_panel_plan(self):
        source = _method_source(STUDIO_SOURCE, '_build_right_preview')
        toggle_source = _method_source(STUDIO_SOURCE, '_build_view_toggle_bar')

        self.assertIn("'top_separator_object_name': 'topSep'", LAYOUTS_SOURCE)
        self.assertIn("'font_preview_alignment': 'center'", LAYOUTS_SOURCE)
        self.assertIn("'font_scroll_widget_resizable': False", LAYOUTS_SOURCE)
        self.assertIn("'font_scroll_alignment': 'center'", LAYOUTS_SOURCE)
        self.assertIn("'font_scroll_frame_shape': 'no_frame'", LAYOUTS_SOURCE)
        self.assertIn("'device_scroll_widget_resizable': False", LAYOUTS_SOURCE)
        self.assertIn("'device_scroll_alignment': 'center'", LAYOUTS_SOURCE)
        self.assertIn("'device_scroll_frame_shape': 'no_frame'", LAYOUTS_SOURCE)
        self.assertIn("'device_scroll_focus_policy': 'strong_focus'", LAYOUTS_SOURCE)

        self.assertNotIn("self._plan_frame_shape_value(preview_panel_plan, 'top_separator_frame_shape', 'hline')", source)
        self.assertIn("sep.setObjectName(str(toggle_plan.get('top_separator_object_name', 'topSep')))", toggle_source)
        self.assertIn("self._plan_alignment_value(preview_panel_plan, 'font_preview_alignment', 'center')", source)
        self.assertIn("self._plan_bool_value(preview_panel_plan, 'font_scroll_widget_resizable', False)", source)
        self.assertIn("self._plan_alignment_value(preview_panel_plan, 'font_scroll_alignment', 'center')", source)
        self.assertIn("self._plan_frame_shape_value(preview_panel_plan, 'font_scroll_frame_shape', 'no_frame')", source)
        self.assertIn("self._plan_bool_value(preview_panel_plan, 'device_scroll_widget_resizable', False)", source)
        self.assertIn("self._plan_alignment_value(preview_panel_plan, 'device_scroll_alignment', 'center')", source)
        self.assertIn("self._plan_frame_shape_value(preview_panel_plan, 'device_scroll_frame_shape', 'no_frame')", source)
        self.assertIn("self._plan_focus_policy_value(preview_panel_plan, 'device_scroll_focus_policy', 'strong_focus')", source)

    def test_navigation_button_texts_are_owned_by_nav_bar_plan(self):
        source = _method_source(STUDIO_SOURCE, '_update_nav_button_texts')

        self.assertIn("'prev_button_text': '前'", LAYOUTS_SOURCE)
        self.assertIn("'next_button_text': '次'", LAYOUTS_SOURCE)
        self.assertIn('nav_bar_plan = gui_layouts.build_nav_bar_plan()', source)
        self.assertIn("nav_bar_plan.get('prev_button_text', '前')", source)
        self.assertIn("nav_bar_plan.get('next_button_text', '次')", source)
        self.assertIn('self.prev_btn.setText(next_text)', source)
        self.assertIn('self.next_btn.setText(prev_text)', source)



if __name__ == '__main__':
    unittest.main()
