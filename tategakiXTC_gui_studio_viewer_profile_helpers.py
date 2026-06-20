from __future__ import annotations

"""Device viewer-profile resolution helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  The implementations
here receive the window object and call back through its methods
(``window._current_viewer_profile`` etc.), so instance-level overrides installed
by tests keep working.  This module intentionally does not import PySide6 or
``tategakiXTC_gui_studio``.
"""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

import tategakiXTC_worker_logic as worker_logic
import tategakiXTC_gui_studio_logic as studio_logic

from tategakiXTC_gui_studio_constants import DeviceProfile, DEVICE_PROFILES


def _current_viewer_profile(window: Any) -> DeviceProfile:
    profile_key, profile, width, height = window._resolved_profile_and_dimensions()
    if profile_key != 'custom':
        return profile

    px_per_mm = max(1e-6, float(profile.ppi) / 25.4)
    screen_w_mm = width / px_per_mm
    screen_h_mm = height / px_per_mm
    body_w_ratio = profile.body_w_mm / max(profile.screen_w_mm, 1e-6)
    body_h_ratio = profile.body_h_mm / max(profile.screen_h_mm, 1e-6)
    return replace(
        profile,
        width_px=width,
        height_px=height,
        screen_w_mm=screen_w_mm,
        screen_h_mm=screen_h_mm,
        body_w_mm=screen_w_mm * body_w_ratio,
        body_h_mm=screen_h_mm * body_h_ratio,
    )


def _preview_viewer_profile(window: Any, payload: object = None) -> DeviceProfile:
    preview_profile = window._viewer_profile_for_preview_payload(payload)
    named_key = str(getattr(preview_profile, 'key', '') or '').strip().lower()
    if named_key and named_key != 'custom' and named_key in DEVICE_PROFILES:
        named_profile = DEVICE_PROFILES.get(named_key)
        if named_profile is not None:
            return named_profile
    width = max(0, int(getattr(preview_profile, 'width_px', 0) or 0))
    height = max(0, int(getattr(preview_profile, 'height_px', 0) or 0))
    for key in ('x4', 'x3'):
        profile = DEVICE_PROFILES.get(key)
        if profile and int(profile.width_px) == width and int(profile.height_px) == height:
            return profile
    if width > 0 and height > 0:
        return window._custom_viewer_profile_for_dimensions(width, height)
    return preview_profile


def _loaded_xtc_document_viewer_profile(window: Any) -> DeviceProfile | None:
    page_profile = window._viewer_profile_for_xtc_pages(window._runtime_xtc_pages())
    if page_profile is not None:
        return page_profile
    loaded_profile = window.__dict__.get('loaded_xtc_viewer_profile')
    if loaded_profile is not None:
        return loaded_profile
    return None


def _refresh_loaded_xtc_viewer_profile_cache(window: Any) -> DeviceProfile | None:
    profile = window._viewer_profile_for_xtc_pages(window._runtime_xtc_pages())
    window.loaded_xtc_viewer_profile = profile
    return profile


def _sync_loaded_xtc_profile_ui_override(window: Any) -> bool:
    document_profile = window._loaded_xtc_document_viewer_profile()
    if document_profile is None:
        window.loaded_xtc_profile_ui_override = False
        return False
    current_profile = window._current_viewer_profile()
    current_key = str(getattr(window, 'current_profile_key', '') or '').strip().lower()
    document_key = str(getattr(document_profile, 'key', '') or '').strip().lower()
    if current_key and current_key != 'custom':
        override = document_key != current_key
    else:
        override = (
            int(getattr(document_profile, 'width_px', 0) or 0) != int(getattr(current_profile, 'width_px', 0) or 0)
            or int(getattr(document_profile, 'height_px', 0) or 0) != int(getattr(current_profile, 'height_px', 0) or 0)
        )
    window.loaded_xtc_profile_ui_override = bool(override)
    return bool(override)


def _active_device_viewer_profile(window: Any, image: object = None) -> DeviceProfile:
    if window._effective_device_view_source() == 'preview':
        current_profile = window._current_viewer_profile()
        current_key = str(getattr(window, 'current_profile_key', '') or '').strip().lower()
        current_named_profile = None
        if current_key and current_key != 'custom':
            current_named_profile = DEVICE_PROFILES.get(current_key)

        preview_profile = window._preview_viewer_profile()

        candidate_image = image
        if candidate_image is None:
            viewer_widget = getattr(window, 'viewer_widget', None)
            candidate_image = getattr(viewer_widget, 'page_image', None) if viewer_widget is not None else None

        preview_width = max(0, int(getattr(preview_profile, 'width_px', 0) or 0))
        preview_height = max(0, int(getattr(preview_profile, 'height_px', 0) or 0))

        width, height = window._page_image_dimensions(candidate_image)
        if width > 0 and height > 0:
            if current_named_profile is not None:
                if int(current_named_profile.width_px) == width and int(current_named_profile.height_px) == height:
                    return current_named_profile

            current_width = max(0, int(getattr(current_profile, 'width_px', 0) or 0))
            current_height = max(0, int(getattr(current_profile, 'height_px', 0) or 0))
            if current_width == width and current_height == height:
                return current_profile

            if preview_width == width and preview_height == height:
                return preview_profile

            for key in ('x4', 'x3'):
                profile = DEVICE_PROFILES.get(key)
                if profile and int(profile.width_px) == width and int(profile.height_px) == height:
                    return profile

            if preview_width > 0 and preview_height > 0:
                return preview_profile
            return window._custom_viewer_profile_for_dimensions(width, height)

        if preview_width > 0 and preview_height > 0:
            return preview_profile

        if current_named_profile is not None:
            return current_named_profile

        current_width = max(0, int(getattr(current_profile, 'width_px', 0) or 0))
        current_height = max(0, int(getattr(current_profile, 'height_px', 0) or 0))
        if current_width > 0 and current_height > 0:
            return current_profile

        return current_profile

    if bool(getattr(window, 'loaded_xtc_profile_ui_override', False)):
        current_key = str(getattr(window, 'current_profile_key', '') or '').strip().lower()
        if current_key and current_key != 'custom':
            named_profile = DEVICE_PROFILES.get(current_key)
            if named_profile is not None:
                return named_profile
        return window._current_viewer_profile()

    document_profile = window._loaded_xtc_document_viewer_profile()
    if document_profile is not None:
        if image is not None:
            width, height = window._page_image_dimensions(image)
            image_profile = window._viewer_profile_for_dimensions(width, height)
            if (
                width > 0
                and height > 0
                and (
                    int(getattr(image_profile, 'width_px', 0) or 0) != int(getattr(document_profile, 'width_px', 0) or 0)
                    or int(getattr(image_profile, 'height_px', 0) or 0) != int(getattr(document_profile, 'height_px', 0) or 0)
                )
            ):
                return image_profile
        return document_profile
    if image is not None:
        return window._viewer_profile_for_page_image(image)
    return window._current_viewer_profile()


def _font_preview_viewer_profile(window: Any) -> DeviceProfile:
    preview_pages = window._runtime_preview_pages()
    if preview_pages:
        try:
            return window._preview_viewer_profile()
        except Exception:
            pass
    return window._current_viewer_profile()



def _apply_viewer_display_runtime_state(window: Any) -> None:
    if not hasattr(window, 'viewer_widget'):
        return

    actual_size = False
    if hasattr(window, 'actual_size_check') and hasattr(window.actual_size_check, 'isChecked'):
        actual_size = bool(window.actual_size_check.isChecked())

    calibration_pct = 100
    if hasattr(window, 'calib_spin') and hasattr(window.calib_spin, 'value'):
        try:
            calibration_pct = int(window.calib_spin.value())
        except Exception:
            calibration_pct = 100

    show_guides = False
    if hasattr(window, 'guides_check') and hasattr(window.guides_check, 'isChecked'):
        show_guides = bool(window.guides_check.isChecked())

    margin_t, margin_b, margin_r, margin_l = window._current_guide_margins()

    window.viewer_widget.set_actual_size(actual_size)
    window.viewer_widget.set_calibration(1.0 if actual_size else calibration_pct / 100.0)
    if hasattr(window.viewer_widget, 'set_preview_zoom_factor'):
        window.viewer_widget.set_preview_zoom_factor(window._preview_zoom_factor())
    window.viewer_widget.set_show_guides(show_guides)
    window.viewer_widget.set_guide_margins(margin_t, margin_b, margin_r, margin_l)
    try:
        window.viewer_widget.set_profile(window._active_device_viewer_profile())
    except Exception:
        pass


def _apply_profile_runtime_state(window: Any) -> None:
    profile_key, profile, _width, _height = window._resolved_profile_and_dimensions()
    window.current_profile_key = profile_key
    if hasattr(window, 'viewer_widget'):
        window.viewer_widget.set_profile(window._active_device_viewer_profile())
    try:
        window._sync_preview_size()
    except Exception:
        pass
    if hasattr(window, 'profile_hint'):
        window.profile_hint.setText(profile.tagline)
        window.profile_hint.setVisible(bool(profile.tagline))


def _page_image_dimensions(window: Any, image: object) -> tuple[int, int]:
    return studio_logic.read_image_dimensions(image)


def _viewer_profile_for_dimensions(window: Any, width: object, height: object) -> DeviceProfile:
    current_profile = window._current_viewer_profile()
    resolution = studio_logic.build_viewer_profile_resolution_state(
        width,
        height,
        current_width=getattr(current_profile, 'width_px', 0),
        current_height=getattr(current_profile, 'height_px', 0),
        profile_dimensions={
            key: (getattr(profile, 'width_px', 0), getattr(profile, 'height_px', 0))
            for key, profile in DEVICE_PROFILES.items()
        },
        preferred_profile_keys=('x4', 'x3'),
    )
    resolution_kind = str(resolution.get('kind') or '').strip()
    if resolution_kind == 'current':
        return current_profile
    if resolution_kind == 'profile':
        profile = DEVICE_PROFILES.get(str(resolution.get('profile_key') or '').strip())
        if profile is not None:
            return profile
        return current_profile
    width_px = max(0, worker_logic._int_config_value({'value': resolution.get('width_px')}, 'value', 0))
    height_px = max(0, worker_logic._int_config_value({'value': resolution.get('height_px')}, 'value', 0))
    return window._custom_viewer_profile_for_dimensions(width_px, height_px)


def _custom_viewer_profile_for_dimensions(window: Any, width: int, height: int) -> DeviceProfile:
    base_profile = DEVICE_PROFILES.get('custom', DEVICE_PROFILES['x4'])
    metrics = studio_logic.build_custom_viewer_profile_metrics(
        width_px=width,
        height_px=height,
        ppi=getattr(base_profile, 'ppi', 300.0),
        screen_w_mm=getattr(base_profile, 'screen_w_mm', 1.0),
        screen_h_mm=getattr(base_profile, 'screen_h_mm', 1.0),
        body_w_mm=getattr(base_profile, 'body_w_mm', 1.0),
        body_h_mm=getattr(base_profile, 'body_h_mm', 1.0),
    )
    return replace(
        base_profile,
        width_px=int(metrics['width_px']),
        height_px=int(metrics['height_px']),
        screen_w_mm=float(metrics['screen_w_mm']),
        screen_h_mm=float(metrics['screen_h_mm']),
        body_w_mm=float(metrics['body_w_mm']),
        body_h_mm=float(metrics['body_h_mm']),
    )


def _viewer_profile_for_xtc_pages(window: Any, pages: object) -> DeviceProfile | None:
    page_list = window._normalized_xtc_pages_for_runtime(pages)
    if not page_list:
        return None
    total = len(page_list)
    current_index = window._normalized_xtc_page_index(getattr(window, 'current_page_index', 0), total=total)
    candidates: list[object] = []
    if 0 <= current_index < total:
        candidates.append(page_list[current_index])
    first_page = page_list[0]
    if not candidates or candidates[0] is not first_page:
        candidates.append(first_page)
    for candidate in candidates:
        width = max(0, worker_logic._int_config_value({'value': getattr(candidate, 'width', 0)}, 'value', 0))
        height = max(0, worker_logic._int_config_value({'value': getattr(candidate, 'height', 0)}, 'value', 0))
        if width > 0 and height > 0:
            return window._viewer_profile_for_dimensions(width, height)
    return None


def _viewer_profile_for_page_image(window: Any, image: object) -> DeviceProfile:
    current_key = getattr(window, 'current_profile_key', '')
    if current_key and current_key != 'custom':
        return window._current_viewer_profile()

    width, height = window._page_image_dimensions(image)
    return window._viewer_profile_for_dimensions(width, height)


def _viewer_profile_for_preview_payload(window: Any, payload: object = None) -> DeviceProfile:
    preview_payload_obj = payload if isinstance(payload, Mapping) else getattr(window, 'last_applied_preview_payload', None)
    preview_payload = dict(preview_payload_obj) if isinstance(preview_payload_obj, Mapping) else {}
    if not preview_payload:
        return window._current_viewer_profile()

    profile_key = window._normalize_choice_value(preview_payload.get('profile'), '', DEVICE_PROFILES)
    width = worker_logic._int_config_value({'width': preview_payload.get('width')}, 'width', 0)
    height = worker_logic._int_config_value({'height': preview_payload.get('height')}, 'height', 0)

    if profile_key and profile_key != 'custom':
        profile = DEVICE_PROFILES.get(profile_key)
        if profile is not None:
            return profile

    if width > 0 and height > 0:
        for key in ('x4', 'x3'):
            profile = DEVICE_PROFILES.get(key)
            if profile and int(profile.width_px) == width and int(profile.height_px) == height:
                return profile
        return window._custom_viewer_profile_for_dimensions(width, height)

    return window._current_viewer_profile()
