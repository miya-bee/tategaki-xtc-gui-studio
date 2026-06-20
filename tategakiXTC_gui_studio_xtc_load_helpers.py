from __future__ import annotations

"""XTC/XTCH load-context helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._xtc_display_name`` etc.), so instance-level overrides installed by
tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``; the Qt-heavy document/render application methods
are implemented here without importing PySide6; entry wrappers inject Qt callables where needed.
"""

from pathlib import Path
from typing import Any, Callable, Mapping
import base64
import logging

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_gui_results_controller as results_controller


def _xtc_source_payload(window: Any, path: object) -> dict[str, str]:
    path_text = worker_logic._normalized_path_text(path).strip()
    return studio_logic.build_xtc_source_payload(
        path_text,
        window._xtc_display_name(path_text),
    )


def _normalized_xtc_bytes(window: Any, data: object) -> bytes:
    return studio_logic.normalize_xtc_bytes(data)


def _xtc_document_payload(
    window: Any,
    data: object,
    *,
    parse_xtc_pages: Callable[[bytes], object],
) -> dict[str, object]:
    xtc_data = window._normalized_xtc_bytes(data)
    pages = parse_xtc_pages(xtc_data)
    return studio_logic.build_xtc_document_payload_from_pages(xtc_data, pages)


def _xtc_source_document_payload(window: Any, path: object) -> dict[str, object]:
    source_payload = window._xtc_source_payload(path)
    raw = Path(source_payload['path_text']).read_bytes()
    document_payload = window._xtc_document_payload(raw)
    return studio_logic.build_xtc_source_document_payload(source_payload, document_payload)


def _xtc_display_name(window: Any, path: object) -> str:
    path_text = worker_logic._normalized_path_text(path).strip()
    return studio_logic.build_xtc_display_name(path_text)


def _apply_loaded_xtc_path_success(window: Any, path_text: str, display_name: str) -> None:
    context = results_controller.build_loaded_xtc_path_success_context(
        path_text,
        display_name,
        window._result_item_paths(),
        language=window.current_ui_language_value(),
    )
    window._apply_loaded_xtc_ui_context(context)


def _apply_loaded_xtc_path_failure(window: Any) -> None:
    window._apply_loaded_xtc_ui_context(results_controller.build_loaded_xtc_failure_context())


def _restore_results_selection_after_xtc_load_failure(window: Any) -> None:
    try:
        preview_active = window._is_preview_display_active()
    except Exception:
        preview_active = False
    if preview_active:
        window._clear_results_selection_with_fallback(
            results_controller.build_results_clear_selection_context()
        )
        return
    restored_path = worker_logic._normalized_path_text(getattr(window, '_loaded_xtc_path_text', None)).strip()
    if restored_path:
        if window._sync_results_selection_for_loaded_path_with_fallback(restored_path):
            return
    window._clear_results_selection_with_fallback(
        results_controller.build_results_clear_selection_context()
    )


def _xtc_load_failure_preserved_display_name(window: Any) -> str:
    try:
        preview_active = window._is_preview_display_active()
    except Exception:
        preview_active = False
    remembered_display_name = worker_logic._normalized_path_text(
        getattr(window, '_loaded_xtc_display_name', None)
    ).strip()
    remembered_path = worker_logic._normalized_path_text(
        getattr(window, '_loaded_xtc_path_text', None)
    ).strip()
    remembered_path_display_name = ''
    if remembered_path:
        remembered_path_display_name = worker_logic._normalized_path_text(
            window._xtc_display_name(remembered_path)
        ).strip()
    label_text = ''
    if hasattr(window, 'current_xtc_label'):
        text_getter = getattr(window.current_xtc_label, 'text', None)
        try:
            label_text = text_getter() if callable(text_getter) else text_getter
        except Exception:
            label_text = ''
    return studio_logic.build_xtc_load_failure_preserved_display_name(
        preview_active=preview_active,
        remembered_display_name=remembered_display_name,
        remembered_path_display_name=remembered_path_display_name,
        current_label_text=label_text,
    )


def _xtc_load_failure_status_message(window: Any, path: object, exc: Exception) -> str:
    target = worker_logic._normalized_path_text(path).strip() or '指定ファイル'
    detail = worker_logic._normalized_path_text(exc).strip()
    preserved = window._xtc_load_failure_preserved_display_name()
    return studio_logic.build_xtc_load_failure_status_message(
        target,
        detail,
        preserved,
        language=window.current_ui_language_value(),
    )


def _apply_loaded_xtc_bytes_success(window: Any) -> None:
    window._apply_loaded_xtc_ui_context(
        results_controller.build_loaded_xtc_bytes_success_context(language=window.current_ui_language_value())
    )


def _reset_xtc_page_input(
    window: Any,
    total_pages: object,
    current_page: object = 0,
    *,
    bulk_block_signals: Callable[..., object],
    build_nav_bar_plan: Callable[[], Mapping[str, object]],
) -> None:
    if not hasattr(window, 'page_input'):
        return
    nav_bar_plan = window._localized_plan(build_nav_bar_plan())
    page_input_state = studio_logic.build_page_input_apply_state(
        total_pages=total_pages,
        current_page=current_page,
        empty_minimum=window._plan_int_value(nav_bar_plan, 'page_input_empty_minimum', 0),
        empty_maximum=window._plan_int_value(nav_bar_plan, 'page_input_empty_maximum', 0),
        active_minimum=window._plan_int_value(nav_bar_plan, 'page_input_active_minimum', 1),
    )
    minimum = window._payload_int_value(page_input_state, 'minimum', 0)
    maximum = window._payload_int_value(page_input_state, 'maximum', 0)
    value = window._payload_int_value(page_input_state, 'value', 0)
    with bulk_block_signals(window.page_input):
        window.page_input.setRange(minimum, maximum)
        window.page_input.setValue(value)


def _apply_xtc_document_payload(window: Any, payload: Mapping[str, object]) -> None:
    xtc_data = window._normalized_xtc_bytes(payload.get('data', b''))
    pages = window._normalized_xtc_pages_for_runtime(payload.get('pages'))
    total = max(0, worker_logic._int_config_value(payload, 'total', len(pages)))
    total = len(pages) if pages else total
    current_index = window._normalized_xtc_page_index(payload.get('current_index', 0), total=total) if pages else 0
    current_page = current_index + 1 if total > 0 else 0
    window.xtc_bytes = xtc_data
    window.xtc_pages = pages
    window._clear_xtc_page_qimage_cache()
    window.loaded_xtc_profile_ui_override = False
    window.device_view_source = 'xtc'
    window.current_device_preview_page_index = 0
    window.current_page_index = current_index
    window._refresh_loaded_xtc_viewer_profile_cache()
    window._reset_xtc_page_input(total, current_page if window.xtc_pages else 0)
    window.render_current_page(refresh_navigation=True)


def _apply_loaded_xtc_document(window: Any, data: bytes, pages: list[Any]) -> None:
    window._apply_xtc_document_payload(
        {
            'data': data,
            'pages': pages,
            'total': len(pages),
            'current_index': 0,
            'current_page': 1 if pages else 0,
        }
    )


def _current_xtc_page_blob(window: Any, *, force_loaded_xtc: bool = False) -> bytes | None:
    if not getattr(window, 'xtc_bytes', b''):
        return None
    if force_loaded_xtc:
        pages = window._runtime_xtc_pages()
        total = len(pages)
        if total <= 0:
            return None
        current_index = window._normalized_xtc_page_index(total=total)
        payload = studio_logic.build_xtc_page_state_payload(pages, current_index)
    else:
        payload = window._xtc_page_state_payload()
        total = worker_logic._int_config_value(payload, 'total', 0)
        if total <= 0:
            return None
        current_index = worker_logic._int_config_value(payload, 'current_index', 0)
    if current_index != getattr(window, 'current_page_index', 0):
        window.current_page_index = current_index
        window._refresh_loaded_xtc_viewer_profile_cache()
    page = payload.get('page')
    if page is None:
        return None
    offset = max(0, worker_logic._int_config_value({'value': getattr(page, 'offset', 0)}, 'value', 0))
    length = max(0, worker_logic._int_config_value({'value': getattr(page, 'length', 0)}, 'value', 0))
    return window.xtc_bytes[offset: offset + length]


def _clear_xtc_viewer_page(window: Any, *, refresh_navigation: bool = True) -> None:
    if hasattr(window, 'viewer_widget'):
        try:
            window.viewer_widget.set_profile(window._active_device_viewer_profile())
        except Exception:
            pass
        window.viewer_widget.clear_page()
        window._resync_device_preview_layout_now_and_later()
    if refresh_navigation:
        window.update_navigation_ui()


def _apply_rendered_xtc_page(
    window: Any,
    image: object,
    *,
    refresh_navigation: bool = True,
    profile: object | None = None,
) -> None:
    if hasattr(window, 'viewer_widget'):
        resolved_profile = profile or window._viewer_profile_for_page_image(image)
        window.viewer_widget.set_profile(resolved_profile)
        window.viewer_widget.set_page_image(image)
        window._resync_device_preview_layout_now_and_later()
    try:
        window._refresh_successful_device_render_status()
    except Exception:
        pass
    if refresh_navigation:
        window.update_navigation_ui()



def clear_loaded_xtc_state(window: Any) -> None:
    window.xtc_bytes = b''
    window.xtc_pages = []
    window._clear_xtc_page_qimage_cache()
    window.current_page_index = 0
    window.device_preview_pages_b64 = []
    window._clear_font_preview_page_pixmap_cache()
    window._clear_device_preview_page_qimage_cache()
    window._preview_page_cache_tokens = []
    window._device_preview_page_cache_tokens = []
    window.device_preview_pages_truncated = False
    window.current_device_preview_page_index = 0
    window.device_view_source = 'xtc'
    window.loaded_xtc_viewer_profile = None
    window.loaded_xtc_profile_ui_override = False
    window._loaded_xtc_display_name = None
    window._loaded_xtc_path_text = None
    window._set_current_xtc_display_name(None)
    window._clear_xtc_viewer_page(refresh_navigation=False)
    window.update_navigation_ui()


def leave_file_viewer_mode_for_target_change(window: Any) -> None:
    """Exit loaded XTC/XTCH viewer state before normal source preview."""
    was_viewer_active = False
    try:
        was_viewer_active = bool(window._is_file_viewer_mode_active())
    except Exception:
        was_viewer_active = False
    if was_viewer_active:
        try:
            window._clear_loaded_xtc_state()
        except Exception:
            logging.getLogger('tategaki_xtc').exception('変換対象変更時のファイルビューワー状態解除に失敗しました')
    try:
        window._refresh_preview_update_button_for_current_state()
    except Exception:
        try:
            window._restore_preview_update_button_from_file_viewer_state()
        except Exception:
            pass

def _set_current_device_preview_page_index(window: Any, index: object, *, refresh_navigation: bool = False) -> bool:
    nav_state = studio_logic.build_navigation_target_state(
        total=len(window._runtime_device_preview_pages()),
        current_index=getattr(window, 'current_device_preview_page_index', 0),
        target_index=index,
    )
    if not window._payload_bool_value(nav_state, 'active', False):
        if refresh_navigation:
            window.update_navigation_ui()
        return False
    new_idx = window._payload_int_value(
        nav_state,
        'target_index',
        int(getattr(window, 'current_device_preview_page_index', 0)),
    )
    if new_idx == getattr(window, 'current_device_preview_page_index', 0):
        try:
            window._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        if refresh_navigation:
            window.update_navigation_ui()
        return False
    window.current_device_preview_page_index = new_idx
    window.render_current_page(refresh_navigation=refresh_navigation)
    return True


def _set_current_page_index(window: Any, index: object, *, refresh_navigation: bool = False) -> bool:
    nav_state = studio_logic.build_navigation_target_state(
        total=window._xtc_page_count(),
        current_index=getattr(window, 'current_page_index', 0),
        target_index=index,
    )
    if not window._payload_bool_value(nav_state, 'active', False):
        if refresh_navigation:
            window.update_navigation_ui()
        return False
    new_idx = window._payload_int_value(
        nav_state,
        'target_index',
        int(getattr(window, 'current_page_index', 0)),
    )
    if new_idx == getattr(window, 'current_page_index', 0):
        try:
            window._sync_active_display_context_for_visible_page()
        except Exception:
            pass
        if refresh_navigation:
            window.update_navigation_ui()
        return False
    window.current_page_index = new_idx
    window._refresh_loaded_xtc_viewer_profile_cache()
    window.render_current_page(refresh_navigation=refresh_navigation)
    return True



def _apply_loaded_xtc_view_mode(window: Any, mode: object, *, safe: bool = False) -> None:
    # v1.3.8.10: the visible device-view switch was removed.  Legacy
    # contexts/INI values may still request ``device``; pass the raw request
    # through set_main_view_mode() so production code normalizes it to the
    # remaining font/file-viewer surface, while tests and older adapters can
    # still observe the compatibility input.
    if mode is None:
        return
    requested_mode = str(mode or '').strip()
    if not requested_mode:
        return
    if safe:
        window.main_view_mode = window._normalized_main_view_mode(requested_mode)
        return
    if hasattr(window, 'preview_stack'):
        window.set_main_view_mode(requested_mode)
        return
    window.main_view_mode = window._normalized_main_view_mode(requested_mode)


def open_xtc_file(
    window: Any,
    *,
    home_path: object,
    result_tab_index: int,
    log_tab_index: int,
) -> None:
    path, _ = window._get_open_file_name_with_status_fallback(
        'XTCファイルを開く',
        str(home_path),
        'XTC / XTCH Files (*.xtc *.xtch)',
        warning_title='XTC読込エラー',
        fallback_status_message='XTC/XTCH選択ダイアログを開けませんでした。',
    )
    if path:
        load_succeeded = window._load_xtc_from_path_with_result(path)
        if hasattr(window, 'bottom_tabs'):
            try:
                window._set_bottom_tab_index_with_fallback(result_tab_index if load_succeeded else log_tab_index)
            except Exception:
                logging.getLogger('tategaki_xtc').exception('XTC手動読込時のタブ切替に失敗しました')

def load_xtc_from_path(window: Any, path: object) -> bool:
    try:
        payload = window._xtc_source_document_payload(path)
        window._apply_xtc_document_payload(payload)
        window._apply_loaded_xtc_path_success(
            str(payload.get('path_text', '')),
            str(payload.get('display_name', '')),
        )
        return True
    except Exception as exc:
        window._restore_results_selection_after_xtc_load_failure()
        status_message = window._xtc_load_failure_status_message(path, exc)
        reflect_failure_in_status = not window._visible_render_failure_status_text()
        window._append_log_with_status_fallback(
            status_message,
            reflect_in_status=reflect_failure_in_status,
        )
        try:
            window._show_critical_dialog_with_status_fallback(
                'XTC読込エラー',
                str(exc),
                fallback_status_message=status_message,
            )
        except Exception:
            try:
                logging.getLogger('tategaki_xtc').exception('XTC読込エラーダイアログの表示に失敗しました')
            except Exception:
                pass
        return False


def load_xtc_from_bytes(window: Any, data: bytes) -> None:
    window._apply_xtc_document_payload(window._xtc_document_payload(data))
    window._apply_loaded_xtc_bytes_success()


def render_current_page(
    window: Any,
    *,
    refresh_navigation: bool = True,
    decode_preview_png: Callable[[bytes, str], object],
    decode_preview_base64: Callable[..., bytes],
    xt_page_blob_to_qimage: Callable[[bytes], object],
) -> None:
    device_view_visible = window._normalized_main_view_mode(
        getattr(window, 'main_view_mode', 'font')
    ) == 'device'
    if window._has_loaded_xtc_viewer_document():
        window.device_view_source = 'xtc'
    effective_source = window._effective_device_view_source()
    if effective_source == 'preview':
        try:
            window._sync_preview_display_context_for_device_view()
        except Exception:
            pass
        preview_profile = window._active_device_viewer_profile()
        if hasattr(window, 'viewer_widget'):
            try:
                window.viewer_widget.set_profile(preview_profile)
            except Exception:
                pass
        pages = window._runtime_device_preview_pages()
        current_index = window._normalized_device_preview_page_index(
            getattr(window, 'current_device_preview_page_index', 0),
            total=len(pages),
        )
        window.current_device_preview_page_index = current_index
        cache_key = window._device_preview_page_qimage_cache_key(current_index)
        cached_qimage = window._cached_device_preview_page_qimage(cache_key)
        if cached_qimage is not None:
            qimg = cached_qimage
        else:
            try:
                raw = decode_preview_base64(window._coerce_preview_base64_text(pages[current_index]), validate=True)
                qimg = decode_preview_png(raw, 'PNG')
                qimg_is_null = getattr(qimg, 'isNull', None)
                if callable(qimg_is_null) and qimg_is_null():
                    raise RuntimeError('プレビュー画像の読み込みに失敗しました。')
            except Exception as exc:
                window._handle_xtc_render_failure(exc, refresh_navigation=refresh_navigation)
                return
            window._store_device_preview_page_qimage(cache_key, qimg)
        preview_profile = window._active_device_viewer_profile(qimg)
        window._apply_rendered_xtc_page(
            qimg,
            refresh_navigation=refresh_navigation,
            profile=preview_profile,
        )
        return

    if window._normalized_device_view_source_value(getattr(window, 'device_view_source', 'xtc')) != 'xtc':
        window.device_view_source = 'xtc'
    should_sync_loaded_display_context = device_view_visible or not window._runtime_preview_pages()
    if should_sync_loaded_display_context:
        try:
            window._sync_loaded_xtc_display_context_for_device_view()
        except Exception:
            pass
    blob = window._current_xtc_page_blob()
    if blob is None:
        try:
            window._sync_blank_device_display_context()
        except Exception:
            pass
        window._clear_xtc_viewer_page(refresh_navigation=refresh_navigation)
        return
    cache_key = window._xtc_page_qimage_cache_key()
    cached_qimage = window._cached_xtc_page_qimage(cache_key)
    if cached_qimage is not None:
        qi = cached_qimage
    else:
        try:
            qi = xt_page_blob_to_qimage(blob)
        except Exception as exc:
            window._handle_xtc_render_failure(exc, refresh_navigation=refresh_navigation)
            return
        window._store_xtc_page_qimage(cache_key, qi)
    window._apply_rendered_xtc_page(
        qi,
        refresh_navigation=refresh_navigation,
        profile=window._active_device_viewer_profile(qi),
    )
