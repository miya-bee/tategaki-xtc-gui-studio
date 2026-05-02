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
