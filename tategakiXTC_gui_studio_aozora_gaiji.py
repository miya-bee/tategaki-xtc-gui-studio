from __future__ import annotations

"""Aozora Bunko external-character helpers.

Official Aozora HTML pages often encode JIS X 0213 level-3/level-4
characters as ``img.gaiji`` images such as ``2-12-93.png``.  The plain text
editions use the matching note form ``※［＃...、第4水準2-12-93］``.  These small
helpers convert the machine-readable Men-Ku-Ten / Unicode codes into real
Unicode text before the normal vertical text renderer sees the source.
"""

from functools import lru_cache
import re
from typing import Mapping


_MENKUTEN_RE = re.compile(r'(?<!\d)([12])-([0-9０-９]{1,2})-([0-9０-９]{1,2})(?!\d)')
_UNICODE_PLUS_RE = re.compile(r'(?i)(?:U\+|Unicode(?:・UCS)?[:：]?\s*|UCS[:：]?\s*)([0-9A-F]{4,6})')
_UNICODE_LOWER_U_RE = re.compile(r'(?<![0-9A-Za-z])u([0-9A-Fa-f]{4,6})(?![0-9A-Za-z])')
_AOZORA_GAIJI_NOTE_RE = re.compile(r'※［＃([^］]+)］')
_ZENKAKU_DIGIT_TRANS = str.maketrans('０１２３４５６７８９', '0123456789')


def _ascii_int(value: str) -> int | None:
    normalized = str(value or '').translate(_ZENKAKU_DIGIT_TRANS)
    if not normalized.isdigit():
        return None
    return int(normalized)


@lru_cache(maxsize=4096)
def jis_x0213_menkuten_to_unicode(plane: int, row: int, cell: int) -> str | None:
    """Convert JIS X 0213 Men-Ku-Ten numbers to Unicode text if possible."""
    if plane not in {1, 2} or not (1 <= row <= 94) or not (1 <= cell <= 94):
        return None
    data = bytes([row + 0xA0, cell + 0xA0]) if plane == 1 else bytes([0x8F, row + 0xA0, cell + 0xA0])
    for encoding in ('euc_jis_2004', 'euc_jisx0213'):
        try:
            return data.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return None


def _unicode_codepoint_to_text(value: str) -> str | None:
    try:
        codepoint = int(value, 16)
    except ValueError:
        return None
    if not (0 <= codepoint <= 0x10FFFF) or 0xD800 <= codepoint <= 0xDFFF:
        return None
    try:
        return chr(codepoint)
    except ValueError:
        return None


def aozora_gaiji_text_from_values(*values: object) -> str | None:
    """Return a Unicode replacement from Aozora gaiji alt/title/src strings."""
    for value in values:
        text = str(value or '')
        if not text:
            continue
        match = _MENKUTEN_RE.search(text)
        if match:
            plane = _ascii_int(match.group(1))
            row = _ascii_int(match.group(2))
            cell = _ascii_int(match.group(3))
            if plane is not None and row is not None and cell is not None:
                converted = jis_x0213_menkuten_to_unicode(plane, row, cell)
                if converted:
                    return converted
        match = _UNICODE_PLUS_RE.search(text) or _UNICODE_LOWER_U_RE.search(text)
        if match:
            converted = _unicode_codepoint_to_text(match.group(1))
            if converted:
                return converted
    return None


def aozora_gaiji_text_from_img_attrs(attrs: Mapping[str, object]) -> str | None:
    """Return the text represented by an Aozora ``img.gaiji`` element."""
    class_text = str(attrs.get('class', '') or '')
    src_text = str(attrs.get('src', '') or '')
    is_gaiji = 'gaiji' in {part.strip().lower() for part in class_text.replace('\u3000', ' ').split()}
    if not is_gaiji and '/gaiji/' not in src_text.replace('\\', '/'):
        return None
    return aozora_gaiji_text_from_values(attrs.get('alt', ''), attrs.get('title', ''), src_text)


def replace_aozora_gaiji_notes(value: str) -> str:
    """Replace Aozora ``※［＃...］`` external-character notes with Unicode."""
    if '※［＃' not in value:
        return value

    def _replace(match: re.Match[str]) -> str:
        note_text = match.group(1)
        converted = aozora_gaiji_text_from_values(note_text)
        return converted if converted else match.group(0)

    return _AOZORA_GAIJI_NOTE_RE.sub(_replace, value)


__all__ = [
    'aozora_gaiji_text_from_img_attrs',
    'aozora_gaiji_text_from_values',
    'jis_x0213_menkuten_to_unicode',
    'replace_aozora_gaiji_notes',
]
