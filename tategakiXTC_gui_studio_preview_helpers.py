from __future__ import annotations


def _coerce_preview_data_url(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value).decode('utf-8')
        except Exception:
            value = bytes(value).decode('ascii', errors='ignore')
    text = str(value).strip()
    return text or None


def _coerce_preview_base64_text(value: object) -> str:
    if isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value).decode('ascii')
        except Exception:
            value = bytes(value).decode('utf-8', errors='ignore')
    return str(value or '').strip()



def _safe_widget_int_value(widget: object, *, default: int = 0) -> int:
    """Return ``widget.value()`` as an int, falling back safely."""
    value_getter = getattr(widget, 'value', None)
    if callable(value_getter):
        try:
            return int(value_getter())
        except Exception:
            return int(default)
    return int(default)


def _preview_page_limit_value(
    limit_widget: object,
    *,
    default_limit: int,
    minimum: int = 1,
) -> int:
    """Return the normalized preview page limit visible in the UI."""
    floor = max(1, int(minimum))
    default_value = max(floor, int(default_limit))
    return max(floor, _safe_widget_int_value(limit_widget, default=default_value))


def _preview_widget_limit_value(limit_widget: object, *, default: int = 0) -> int:
    """Return the raw preview limit spin value used for status refresh logic."""
    return _safe_widget_int_value(limit_widget, default=default)


def _manual_preview_required_status_message(
    *,
    preview_limit: int,
    auto_refresh_max: int,
) -> str:
    """Return the manual-refresh-required preview status message.

    The strings intentionally match the legacy Japanese UI text.  Translation is
    still applied by the caller where the existing UI path did so before this
    refactor.
    """
    limit = max(1, int(preview_limit))
    max_auto = max(0, int(auto_refresh_max))
    if limit > max_auto:
        return f'プレビュー更新が必要です（更新対象 {limit} ページのため自動更新しません）'
    return 'プレビュー更新が必要です'
