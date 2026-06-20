from __future__ import annotations

import importlib

from tests.studio_import_helper import load_studio_module


def test_layout_plans_expose_file_batch_and_share_png_actions():
    import tategakiXTC_gui_layouts as gui_layouts

    top_bar = gui_layouts.build_top_bar_plan(path_button_width=96)
    assert 'clipboard_button_text' not in top_bar
    assert 'aozora_button_text' not in top_bar
    assert 'コピーした本文をすぐ試す' not in top_bar['top_buttons_help_text']
    assert '青空文庫から探す' not in top_bar['top_buttons_help_text']

    view_bar = gui_layouts.build_view_toggle_bar_plan()
    assert view_bar['share_png_button_text'] == 'PNG保存'
    assert '枠付きPNG' in view_bar['share_png_button_tooltip']


def test_share_export_prefers_loaded_xtc_when_file_viewer_is_active(monkeypatch):
    load_studio_module(force_reload=True)
    helpers = importlib.import_module('tategakiXTC_gui_studio_sns_export_helpers')

    class _Image:
        def isNull(self):
            return False

    class _Window:
        current_page_index = 0
        current_preview_page_index = 0
        xtc_pages = [object()]

        def _is_file_viewer_mode_active(self):
            return True

        def _runtime_preview_pages(self):
            return ['not-base64-on-purpose']

        def _current_xtc_page_blob(self, *, force_loaded_xtc=False):
            assert force_loaded_xtc is True
            return b'xtc-page'

        def _xtc_page_count(self):
            return 1

    image = _Image()
    monkeypatch.setattr(helpers, 'xt_page_blob_to_qimage', lambda blob: image)

    result_image, page_number, total_pages = helpers.current_share_page_image(_Window())

    assert result_image is image
    assert page_number == 1
    assert total_pages == 1
