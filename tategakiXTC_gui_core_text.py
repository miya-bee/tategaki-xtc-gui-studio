"""
tategakiXTC_gui_core_text.py — TXT / Markdown 入力 helper

`tategakiXTC_gui_core.py` から分離したテキスト読み込み・青空文庫注記・
Markdown 簡易整形の実装。互換性維持のため、gui_core 側の re-export /
既存テストの monkey patch を各入口で同期する。
"""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence, cast
import codecs
import json
import re


# Circular-import guard for direct split-module imports.
# ``tategakiXTC_gui_core`` re-exports many names from this module; when this
# module is imported first, core may ask for those names before the real
# definitions below have executed.  Placeholders let core finish importing;
# the real objects are published back to core at module end.
_SPLIT_IMPORT_PLACEHOLDER = object()
_CORE_REEXPORT_NAMES = (
    '_TEXT_INPUT_DOCUMENT_CACHE',
    '_try_decode_bytes',
    '_guess_utf16_without_bom',
    '_detect_text_with_charset_normalizer',
    'START_TEXT_RE',
    'START_TEXT_ONLY_RE',
    '_strip_leading_start_text',
    '_is_start_text_only_line',
    '_is_frontmatter_like_text_line',
    '_can_strip_start_text_after_frontmatter',
    '_strip_start_text_after_leading_frontmatter',
    'AOZORA_NOTE_RE',
    'AOZORA_NOTE_ONLY_RE',
    'AOZORA_IMAGE_MARKER_RE',
    'AOZORA_INSERTED_IMAGE_NOTE_RE',
    'AOZORA_IMPLICIT_RUBY_BASE_RE',
    'AOZORA_INDENT_RE',
    'AOZORA_INDENT_END_RE',
    'AOZORA_BOUTEN_NOTE_RE',
    'AOZORA_BOUSEN_NOTE_RE',
    'AOZORA_EMPHASIS_KIND_ALIASES',
    'AOZORA_EMPHASIS_MARKERS',
    'AOZORA_SIDE_LINE_KIND_ALIASES',
    'AOZORA_EMPHASIS_SKIP_CHARS',
    'AOZORA_SIDE_LINE_SKIP_CHARS',
    '_zenkaku_digits_to_int',
    '_is_aozora_pagebreak_note',
    '_parse_aozora_indent_note',
    '_normalize_aozora_emphasis_kind',
    '_parse_aozora_emphasis_note',
    '_normalize_aozora_side_line_kind',
    '_parse_aozora_side_line_note',
    '_merge_adjacent_runs',
    '_apply_emphasis_to_recent_runs',
    '_apply_side_line_to_recent_runs',
    '_parse_aozora_note_only_line',
    '_apply_note_to_previous_block',
    '_flush_text_run_buffer',
    '_append_text_run',
    '_aozora_inline_to_runs',
    'read_text_file_with_fallback',
    '_markdown_inline_to_runs',
    '_plain_inline_to_runs',
    '_consume_plain_text_leading_fullwidth_indent',
    '_plain_text_line_starts_with_opening_bracket',
    '_normalize_text_line',
    'TEXT_INPUT_SUPPORT_SUMMARY',
    '_dedupe_preserve_order',
    '_find_markdown_support_warnings',
    '_find_plain_text_support_warnings',
    '_is_plain_dialogue_compact_candidate',
    '_blocks_from_plain_text',
    'MARKDOWN_FOOTNOTE_DEF_RE',
    'MARKDOWN_DEF_LIST_RE',
    'MARKDOWN_ORDERED_LIST_RE',
    'MARKDOWN_FENCE_RE',
    '_markdown_text_run',
    '_set_runs_bold',
    '_extract_markdown_footnotes',
    '_split_markdown_table_row',
    '_is_markdown_table_separator',
    '_build_markdown_table_blocks',
    '_append_markdown_footnote_blocks',
    '_blocks_from_markdown',
    'load_text_input_document',
    'process_text_file',
    'process_markdown_file'
)
_CORE_REEXPORT_ALIASES = (
    ('_TEXT_INPUT_DOCUMENT_CACHE', '_TEXT_INPUT_DOCUMENT_CACHE'),
    ('_try_decode_bytes', '_try_decode_bytes'),
    ('_guess_utf16_without_bom', '_guess_utf16_without_bom'),
    ('_detect_text_with_charset_normalizer', '_detect_text_with_charset_normalizer'),
    ('START_TEXT_RE', 'START_TEXT_RE'),
    ('START_TEXT_ONLY_RE', 'START_TEXT_ONLY_RE'),
    ('_strip_leading_start_text', '_strip_leading_start_text'),
    ('_is_start_text_only_line', '_is_start_text_only_line'),
    ('_is_frontmatter_like_text_line', '_is_frontmatter_like_text_line'),
    ('_can_strip_start_text_after_frontmatter', '_can_strip_start_text_after_frontmatter'),
    ('_strip_start_text_after_leading_frontmatter', '_strip_start_text_after_leading_frontmatter'),
    ('AOZORA_NOTE_RE', 'AOZORA_NOTE_RE'),
    ('AOZORA_NOTE_ONLY_RE', 'AOZORA_NOTE_ONLY_RE'),
    ('AOZORA_IMAGE_MARKER_RE', 'AOZORA_IMAGE_MARKER_RE'),
    ('AOZORA_INSERTED_IMAGE_NOTE_RE', 'AOZORA_INSERTED_IMAGE_NOTE_RE'),
    ('AOZORA_IMPLICIT_RUBY_BASE_RE', 'AOZORA_IMPLICIT_RUBY_BASE_RE'),
    ('AOZORA_INDENT_RE', 'AOZORA_INDENT_RE'),
    ('AOZORA_INDENT_END_RE', 'AOZORA_INDENT_END_RE'),
    ('AOZORA_BOUTEN_NOTE_RE', 'AOZORA_BOUTEN_NOTE_RE'),
    ('AOZORA_BOUSEN_NOTE_RE', 'AOZORA_BOUSEN_NOTE_RE'),
    ('AOZORA_EMPHASIS_KIND_ALIASES', 'AOZORA_EMPHASIS_KIND_ALIASES'),
    ('AOZORA_EMPHASIS_MARKERS', 'AOZORA_EMPHASIS_MARKERS'),
    ('AOZORA_SIDE_LINE_KIND_ALIASES', 'AOZORA_SIDE_LINE_KIND_ALIASES'),
    ('AOZORA_EMPHASIS_SKIP_CHARS', 'AOZORA_EMPHASIS_SKIP_CHARS'),
    ('AOZORA_SIDE_LINE_SKIP_CHARS', 'AOZORA_SIDE_LINE_SKIP_CHARS'),
    ('_zenkaku_digits_to_int', '_zenkaku_digits_to_int'),
    ('_is_aozora_pagebreak_note', '_is_aozora_pagebreak_note'),
    ('_parse_aozora_indent_note', '_parse_aozora_indent_note'),
    ('_normalize_aozora_emphasis_kind', '_normalize_aozora_emphasis_kind'),
    ('_parse_aozora_emphasis_note', '_parse_aozora_emphasis_note'),
    ('_normalize_aozora_side_line_kind', '_normalize_aozora_side_line_kind'),
    ('_parse_aozora_side_line_note', '_parse_aozora_side_line_note'),
    ('_merge_adjacent_runs', '_merge_adjacent_runs'),
    ('_apply_emphasis_to_recent_runs', '_apply_emphasis_to_recent_runs'),
    ('_apply_side_line_to_recent_runs', '_apply_side_line_to_recent_runs'),
    ('_parse_aozora_note_only_line', '_parse_aozora_note_only_line'),
    ('_apply_note_to_previous_block', '_apply_note_to_previous_block'),
    ('_flush_text_run_buffer', '_flush_text_run_buffer'),
    ('_append_text_run', '_append_text_run'),
    ('_aozora_inline_to_runs', '_aozora_inline_to_runs'),
    ('read_text_file_with_fallback', 'read_text_file_with_fallback'),
    ('_markdown_inline_to_runs', '_markdown_inline_to_runs'),
    ('_plain_inline_to_runs', '_plain_inline_to_runs'),
    ('_consume_plain_text_leading_fullwidth_indent', '_consume_plain_text_leading_fullwidth_indent'),
    ('_plain_text_line_starts_with_opening_bracket', '_plain_text_line_starts_with_opening_bracket'),
    ('_normalize_text_line', '_normalize_text_line'),
    ('TEXT_INPUT_SUPPORT_SUMMARY', 'TEXT_INPUT_SUPPORT_SUMMARY'),
    ('_dedupe_preserve_order', '_dedupe_preserve_order'),
    ('_find_markdown_support_warnings', '_find_markdown_support_warnings'),
    ('_find_plain_text_support_warnings', '_find_plain_text_support_warnings'),
    ('_is_plain_dialogue_compact_candidate', '_is_plain_dialogue_compact_candidate'),
    ('_blocks_from_plain_text', '_blocks_from_plain_text'),
    ('MARKDOWN_FOOTNOTE_DEF_RE', 'MARKDOWN_FOOTNOTE_DEF_RE'),
    ('MARKDOWN_DEF_LIST_RE', 'MARKDOWN_DEF_LIST_RE'),
    ('MARKDOWN_ORDERED_LIST_RE', 'MARKDOWN_ORDERED_LIST_RE'),
    ('MARKDOWN_FENCE_RE', 'MARKDOWN_FENCE_RE'),
    ('_markdown_text_run', '_markdown_text_run'),
    ('_set_runs_bold', '_set_runs_bold'),
    ('_extract_markdown_footnotes', '_extract_markdown_footnotes'),
    ('_split_markdown_table_row', '_split_markdown_table_row'),
    ('_is_markdown_table_separator', '_is_markdown_table_separator'),
    ('_build_markdown_table_blocks', '_build_markdown_table_blocks'),
    ('_append_markdown_footnote_blocks', '_append_markdown_footnote_blocks'),
    ('_blocks_from_markdown', '_blocks_from_markdown'),
    ('load_text_input_document', 'load_text_input_document'),
    ('process_text_file', '_text_process_text_file'),
    ('process_markdown_file', '_text_process_markdown_file')
)
for _name in _CORE_REEXPORT_NAMES:
    globals().setdefault(_name, _SPLIT_IMPORT_PLACEHOLDER)

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_studio_aozora_gaiji import replace_aozora_gaiji_notes
from tategakiXTC_gui_core_cache import (
    _get_cached_input_document,
    _source_document_cache_key,
    _store_cached_input_document,
)
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals', 'process_text_file', 'process_markdown_file'}
_CORE_SYNC_VERSION = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch を text 実装へ反映する。"""
    global _CORE_SYNC_VERSION
    version = core_sync_version(_core)
    if not force and _CORE_SYNC_VERSION == version:
        return
    for _name, _value in vars(_core).items():
        if _name.startswith('__') or _name in _CORE_SYNC_EXCLUDED_NAMES:
            continue
        globals()[_name] = _value
    _CORE_SYNC_VERSION = version


_refresh_core_globals()


# ==========================================
# --- テキスト入力 helper ---
# ==========================================

_TEXT_INPUT_DOCUMENT_CACHE: OrderedDict[tuple[str, str, int, int], TextInputDocument] = OrderedDict()


def _try_decode_bytes(raw: bytes, encoding: str) -> tuple[str, str] | None:
    """指定エンコーディングでデコードを試み、成功時のみ (text, encoding) を返す。"""
    _refresh_core_globals()
    try:
        return raw.decode(encoding), encoding
    except UnicodeDecodeError:
        return None


def _is_utf16_plain_text_char(char: str) -> bool:
    code = ord(char)
    return (
        char in '\t\n\r ・、。！？「」『』【】（）()[]［］《》〈〉ー〜～…‥―—'
        or 0x20 <= code <= 0x7E
        or 0x3040 <= code <= 0x30FF
        or 0x3400 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
        or 0xFF00 <= code <= 0xFFEF
    )


def _utf16_without_bom_japanese_score(text: str) -> tuple[float, int]:
    if not text:
        return 0.0, 0
    bad = 0
    plain = 0
    kana = 0
    for char in text:
        code = ord(char)
        if 0x3040 <= code <= 0x30FF:
            kana += 1
        if _is_utf16_plain_text_char(char):
            plain += 1
        elif code < 0x20 or 0xD800 <= code <= 0xDFFF or 0xE000 <= code <= 0xF8FF:
            bad += 1
    return (plain / max(1, len(text))) - (bad / max(1, len(text))) * 2.0, kana


def _guess_utf16_without_bom(raw: bytes) -> str | None:
    """BOM なし UTF-16 の可能性を簡易推定する。"""
    _refresh_core_globals()
    if len(raw) < 4 or len(raw) % 2 != 0:
        return None
    even_nul = sum(1 for b in raw[0::2] if b == 0)
    odd_nul = sum(1 for b in raw[1::2] if b == 0)
    pairs = max(1, len(raw) // 2)
    even_ratio = even_nul / pairs
    odd_ratio = odd_nul / pairs
    if odd_ratio >= 0.25 and odd_ratio >= even_ratio * 3:
        return 'utf-16-le'
    if even_ratio >= 0.25 and even_ratio >= odd_ratio * 3:
        return 'utf-16-be'

    # 日本語UTF-16は、漢字・かな中心の本文だと NUL 比率だけでは判定
    # できない。CP932 等の偶数長バイト列を誤判定しないよう、かなを
    # 含む自然な日本語本文に限定して LE/BE を比較する。
    scored: list[tuple[float, int, str]] = []
    for encoding in ('utf-16-le', 'utf-16-be'):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        score, kana_count = _utf16_without_bom_japanese_score(text)
        scored.append((score, kana_count, encoding))
    if not scored:
        return None
    scored.sort(reverse=True)
    best_score, best_kana_count, best_encoding = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    required_kana = max(1, min(4, len(raw) // 24))
    if best_kana_count >= required_kana and best_score >= 0.85 and best_score >= second_score + 0.15:
        return best_encoding
    return None


def _detect_text_with_charset_normalizer(raw: bytes) -> tuple[str, str] | None:
    """charset-normalizer による日本語寄りの自動判定を行う。"""
    _refresh_core_globals()
    try:
        from charset_normalizer import from_bytes
    except ImportError:
        return None

    candidates = [
        'utf_8', 'utf_8_sig', 'cp932', 'shift_jis', 'euc_jp', 'iso2022_jp',
        'utf_16', 'utf_16_le', 'utf_16_be'
    ]
    try:
        best = from_bytes(raw, cp_isolation=candidates, preemptive_behaviour=True).best()
    except Exception:
        return None
    if not best or not best.encoding:
        return None
    detected_text = str(best)
    detected_encoding = best.encoding.replace('_', '-').lower()
    if detected_encoding in {'utf-16', 'utf-16-le', 'utf-16-be'}:
        # BOM-bearing UTF-16 has already been handled before charset-normalizer.
        # For BOM-less files, trust UTF-16 only when our stricter Japanese text
        # heuristic agrees.  Otherwise short CP932 Aozora TXT files with CRLF
        # blank lines can be misdetected as UTF-16BE and lose their newlines.
        guessed_utf16 = _guess_utf16_without_bom(raw)
        if guessed_utf16 is None:
            return None
        if detected_encoding in {'utf-16-le', 'utf-16-be'} and detected_encoding != guessed_utf16:
            return None
        detected_encoding = guessed_utf16
        try:
            detected_text = raw.decode(detected_encoding)
        except UnicodeDecodeError:
            return None
    return detected_text, detected_encoding


def _strip_leading_start_text(value: str) -> str:
    _refresh_core_globals()
    text = str(value or '')
    while True:
        stripped = START_TEXT_RE.sub('', text, count=1)
        if stripped == text:
            return stripped
        text = stripped


def _is_start_text_only_line(value: object) -> bool:
    _refresh_core_globals()
    return bool(START_TEXT_ONLY_RE.fullmatch(str(value or '')))


def _is_frontmatter_like_text_line(value: object) -> bool:
    _refresh_core_globals()
    text = str(value or '').replace('\ufeff', '').replace('\r', '').strip()
    if not text or _is_start_text_only_line(text):
        return False
    compact = re.sub(r'[\s\u3000]+', '', text)
    if not compact or len(compact) > 24:
        return False
    if re.search(r'[。．！？?!、，；：:]', compact):
        return False
    return True


def _can_strip_start_text_after_frontmatter(leading_nonblank: Sequence[str]) -> bool:
    _refresh_core_globals()
    if not leading_nonblank:
        return True
    return 2 <= len(leading_nonblank) <= 5 and all(_is_frontmatter_like_text_line(prev) for prev in leading_nonblank)


def _strip_start_text_after_leading_frontmatter(text: str) -> str:
    """先頭付近のタイトル・著者・章見出しの後ろに残る start text 行を取り除く。"""
    _refresh_core_globals()
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if not lines:
        return text

    leading_nonblank: list[str] = []
    kept_lines: list[str] = []
    removed = False
    body_started = False

    for line in lines:
        if removed or body_started:
            kept_lines.append(line)
            continue

        stripped = line.replace('\ufeff', '').strip()
        if not stripped:
            kept_lines.append(line)
            continue

        if _is_start_text_only_line(stripped) and _can_strip_start_text_after_frontmatter(leading_nonblank):
            removed = True
            continue

        kept_lines.append(line)
        leading_nonblank.append(line)
        if not _is_frontmatter_like_text_line(line) or len(leading_nonblank) > 5:
            body_started = True

    return '\n'.join(kept_lines)



AOZORA_NOTE_RE = re.compile(r'［＃([^］]+)］')
AOZORA_NOTE_ONLY_RE = re.compile(r'^\s*［＃([^］]+)］\s*$')
AOZORA_IMAGE_MARKER_RE = re.compile(r'^挿絵:([0-9]{1,8})$')
AOZORA_INSERTED_IMAGE_NOTE_RE = re.compile(
    r'^(?P<prefix>.*?(?:挿絵|図).*?)（(?P<filename>[^（）]*(?:\.png|\.jpg|\.jpeg|\.gif|\.webp))[^）]*）入る$',
    re.IGNORECASE,
)
# 暗黙ルビは『漢字＋かな送り』のみを対象とし、英数字混在は誤認識を避けるため除外する。
AOZORA_IMPLICIT_RUBY_BASE_RE = re.compile('[\u3400-\u4DBF\u4E00-\u9FFF\U00020000-\U0002EBEF々〆ヶ]+[ぁ-ゖゝゞァ-ヺー゛゜ヽヾヿ]*※*$')
AOZORA_INDENT_RE = re.compile(r'^(?:(ここから))?([0-9０-９]+)字下げ(?:、?折り返して([0-9０-９]+)字下げ)?$')
AOZORA_INDENT_END_RE = re.compile(r'^(?:ここで)?字下げ終わり$')
AOZORA_BOUTEN_NOTE_RE = re.compile(r'^[「『]([^」』]+)[」』]に(.*傍点)$')
AOZORA_BOUSEN_NOTE_RE = re.compile(r'^[「『]([^」』]+)[」』]に(.+)$')
AOZORA_EMPHASIS_KIND_ALIASES = {
    '傍点': '白ゴマ傍点',
    '白ゴマ傍点': '白ゴマ傍点',
    '白ごま傍点': '白ゴマ傍点',
    'ゴマ傍点': '黒ゴマ傍点',
    '黒ゴマ傍点': '黒ゴマ傍点',
    '黒ごま傍点': '黒ゴマ傍点',
    '丸傍点': '丸傍点',
    '白丸傍点': '白丸傍点',
    '黒三角傍点': '黒三角傍点',
    '白三角傍点': '白三角傍点',
    '二重丸傍点': '二重丸傍点',
    '蛇の目傍点': '蛇の目傍点',
    'ばつ傍点': 'ばつ傍点',
}
AOZORA_EMPHASIS_MARKERS = {
    '白ゴマ傍点': '﹆',
    '黒ゴマ傍点': '﹅',
    '丸傍点': '●',
    '白丸傍点': '○',
    '黒三角傍点': '▲',
    '白三角傍点': '△',
    '二重丸傍点': '◎',
    '蛇の目傍点': '◉',
    'ばつ傍点': '×',
}
AOZORA_SIDE_LINE_KIND_ALIASES = {
    '傍線': 'solid',
    '太傍線': 'thick',
    '二重傍線': 'double',
    '破線': 'dashed',
    '破線傍線': 'dashed',
    '鎖線': 'chain',
    '鎖線傍線': 'chain',
    '波線': 'wavy',
    '波線傍線': 'wavy',
}
AOZORA_EMPHASIS_SKIP_CHARS = set('、。，．､｡・：；？！!?…‥　 ' + ''.join(OPENING_BRACKET_CHARS) + ''.join(CLOSING_BRACKET_CHARS))
AOZORA_SIDE_LINE_SKIP_CHARS = AOZORA_EMPHASIS_SKIP_CHARS



def _zenkaku_digits_to_int(value: object) -> int | None:
    _refresh_core_globals()
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    translated = value.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    if not translated.isdigit():
        return None
    return int(translated)


def _is_aozora_pagebreak_note(note_text: object) -> bool:
    _refresh_core_globals()
    normalized = re.sub(r'\s+', '', str(note_text or ''))
    return normalized in {'改ページ', '改丁', '改見開き'}


def _parse_aozora_indent_note(note_text: object) -> AozoraNoteBlock | None:
    _refresh_core_globals()
    normalized = re.sub(r'\s+', '', str(note_text or ''))
    if not normalized:
        return None
    if AOZORA_INDENT_END_RE.fullmatch(normalized):
        return {'kind': 'indent_end'}
    match = AOZORA_INDENT_RE.fullmatch(normalized)
    if not match:
        return None
    block_start = bool(match.group(1))
    first_indent = _zenkaku_digits_to_int(match.group(2))
    wrap_indent = _zenkaku_digits_to_int(match.group(3))
    if first_indent is None:
        return None
    if wrap_indent is None:
        wrap_indent = first_indent
    return {
        'kind': 'indent_start' if block_start else 'indent_once',
        'indent_chars': max(0, first_indent),
        'wrap_indent_chars': max(0, wrap_indent),
    }



def _normalize_aozora_emphasis_kind(kind_text: object) -> str | None:
    _refresh_core_globals()
    normalized = re.sub(r'\s+', '', str(kind_text or ''))
    if not normalized:
        return None
    return AOZORA_EMPHASIS_KIND_ALIASES.get(normalized)


def _parse_aozora_emphasis_note(note_text: object) -> AozoraNoteBlock | None:
    _refresh_core_globals()
    normalized = re.sub(r'\s+', '', str(note_text or ''))
    if not normalized:
        return None
    match = AOZORA_BOUTEN_NOTE_RE.fullmatch(normalized)
    if not match:
        return None
    target_text = match.group(1)
    emphasis_kind = _normalize_aozora_emphasis_kind(match.group(2))
    if not target_text or not emphasis_kind:
        return None
    return {
        'kind': 'emphasis',
        'target_text': target_text,
        'emphasis': emphasis_kind,
    }


def _normalize_aozora_side_line_kind(kind_text: object) -> str | None:
    _refresh_core_globals()
    normalized = re.sub(r'\s+', '', str(kind_text or ''))
    if not normalized:
        return None
    return AOZORA_SIDE_LINE_KIND_ALIASES.get(normalized)


def _parse_aozora_side_line_note(note_text: object) -> AozoraNoteBlock | None:
    _refresh_core_globals()
    normalized = re.sub(r'\s+', '', str(note_text or ''))
    if not normalized:
        return None
    match = AOZORA_BOUSEN_NOTE_RE.fullmatch(normalized)
    if not match:
        return None
    target_text = match.group(1)
    side_line_kind = _normalize_aozora_side_line_kind(match.group(2))
    if not target_text or not side_line_kind:
        return None
    return {
        'kind': 'side_line',
        'target_text': target_text,
        'side_line': side_line_kind,
    }


def _merge_adjacent_runs(runs: Iterable[TextRun]) -> Runs:
    _refresh_core_globals()
    merged: Runs = []
    for run in runs:
        text_value = str(run.get('text', '') or '')
        if not text_value:
            continue
        if (
            merged
            and merged[-1].get('bold') == run.get('bold')
            and merged[-1].get('italic') == run.get('italic')
            and merged[-1].get('ruby', '') == run.get('ruby', '')
            and merged[-1].get('emphasis', '') == run.get('emphasis', '')
            and merged[-1].get('side_line', '') == run.get('side_line', '')
            and bool(merged[-1].get('code', False)) == bool(run.get('code', False))
        ):
            merged[-1]['text'] += text_value
        else:
            merged.append({
                'text': text_value,
                'ruby': str(run.get('ruby', '') or ''),
                'bold': bool(run.get('bold')),
                'italic': bool(run.get('italic')),
                'emphasis': str(run.get('emphasis', '') or ''),
                'side_line': str(run.get('side_line', '') or ''),
                'code': bool(run.get('code', False)),
            })
    return merged


def _apply_emphasis_to_recent_runs(runs: Runs, target_text: object, emphasis_kind: object) -> bool:
    _refresh_core_globals()
    target_text = str(target_text or '')
    emphasis_kind = str(emphasis_kind or '')
    if not runs or not target_text or not emphasis_kind:
        return False
    plain_text = ''.join(run.get('text', '') for run in runs)
    if not plain_text.endswith(target_text):
        return False

    remaining = len(target_text)
    updated: Runs = []
    for run in reversed(runs):
        text_value = run.get('text', '')
        if not text_value:
            continue
        if remaining <= 0:
            updated.append(dict(run))
            continue
        if remaining >= len(text_value):
            updated.append({**run, 'emphasis': emphasis_kind})
            remaining -= len(text_value)
            continue
        if run.get('ruby'):
            return False
        split_at = len(text_value) - remaining
        prefix_text = text_value[:split_at]
        target_part = text_value[split_at:]
        if target_part:
            updated.append({**run, 'text': target_part, 'emphasis': emphasis_kind})
        if prefix_text:
            updated.append({**run, 'text': prefix_text})
        remaining = 0
    if remaining != 0:
        return False
    runs[:] = _merge_adjacent_runs(reversed(updated))
    return True


def _apply_side_line_to_recent_runs(runs: Runs, target_text: object, side_line_kind: object) -> bool:
    _refresh_core_globals()
    target_text = str(target_text or '')
    side_line_kind = str(side_line_kind or '')
    if not runs or not target_text or not side_line_kind:
        return False
    plain_text = ''.join(run.get('text', '') for run in runs)
    if not plain_text.endswith(target_text):
        return False

    remaining = len(target_text)
    updated: Runs = []
    for run in reversed(runs):
        text_value = run.get('text', '')
        if not text_value:
            continue
        if remaining <= 0:
            updated.append(dict(run))
            continue
        if remaining >= len(text_value):
            updated.append({**run, 'side_line': side_line_kind})
            remaining -= len(text_value)
            continue
        if run.get('ruby'):
            return False
        split_at = len(text_value) - remaining
        prefix_text = text_value[:split_at]
        target_part = text_value[split_at:]
        if target_part:
            updated.append({**run, 'text': target_part, 'side_line': side_line_kind})
        if prefix_text:
            updated.append({**run, 'text': prefix_text})
        remaining = 0
    if remaining != 0:
        return False
    runs[:] = _merge_adjacent_runs(reversed(updated))
    return True



def _normalize_aozora_image_ref(value: object) -> str:
    text = str(value if value is not None else '').strip().replace('\\', '/')
    while text.startswith('./'):
        text = text[2:]
    return text


def _aozora_image_sidecar_paths(text_path: Path) -> tuple[Path, Path]:
    return text_path.with_name(f'{text_path.stem}_img'), text_path.with_name(f'{text_path.stem}.images.json')


def _read_aozora_image_manifest(text_path: str | Path | None) -> tuple[Path | None, dict[str, Any]]:
    if not text_path:
        return None, {}
    source_path = Path(text_path)
    image_dir, manifest_path = _aozora_image_sidecar_paths(source_path)
    if not manifest_path.exists():
        return image_dir if image_dir.exists() else None, {}
    try:
        payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception:
        return image_dir if image_dir.exists() else None, {}
    if not isinstance(payload, dict):
        return image_dir if image_dir.exists() else None, {}
    payload_image_dir = payload.get('image_dir')
    if isinstance(payload_image_dir, str) and payload_image_dir.strip():
        candidate = Path(payload_image_dir)
        if not candidate.is_absolute():
            candidate = manifest_path.parent / candidate
        image_dir = candidate
    return image_dir if image_dir.exists() else None, payload


def _manifest_images(payload: Mapping[str, Any] | None) -> dict[str, Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return {}
    images = payload.get('images')
    if isinstance(images, Mapping):
        return {str(key): value for key, value in images.items() if isinstance(value, Mapping)}
    return {}


def _matching_aozora_image_manifest_entries(
    manifest: Mapping[str, Any] | None,
    *,
    image_id: object = None,
    image_src: object = None,
) -> list[Mapping[str, Any]]:
    images = _manifest_images(manifest)
    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(item: Mapping[str, Any]) -> None:
        marker = id(item)
        if marker not in seen:
            seen.add(marker)
            candidates.append(item)

    image_id_text = str(image_id or '').strip()
    if image_id_text and image_id_text in images:
        add(images[image_id_text])
    src_text = _normalize_aozora_image_ref(image_src)
    src_base = Path(src_text).name.lower() if src_text else ''
    if src_text:
        for item in images.values():
            for key in ('src', 'basename', 'file'):
                value = _normalize_aozora_image_ref(item.get(key, ''))
                if value and (value == src_text or Path(value).name.lower() == src_base):
                    add(item)
                    break
    return candidates


def _resolve_aozora_image_path_from_manifest(
    *,
    image_dir: Path | None,
    manifest: Mapping[str, Any] | None,
    image_id: object = None,
    image_src: object = None,
) -> Path | None:
    candidates = _matching_aozora_image_manifest_entries(manifest, image_id=image_id, image_src=image_src)
    for item in candidates:
        file_value = str(item.get('file', '') or '').strip()
        if not file_value:
            continue
        candidate = Path(file_value)
        if not candidate.is_absolute():
            if image_dir is None:
                continue
            candidate = image_dir / candidate
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _resolve_aozora_image_path_without_manifest(source_path: Path | None, image_src: object = None) -> Path | None:
    if source_path is None:
        return None
    src_text = _normalize_aozora_image_ref(image_src)
    if not src_text:
        return None
    src_path = Path(src_text)
    candidates: list[Path] = []
    if src_path.is_absolute():
        candidates.append(src_path)
    else:
        image_dir, _manifest_path = _aozora_image_sidecar_paths(source_path)
        candidates.extend([
            source_path.parent / src_path,
            image_dir / src_path.name,
            image_dir / src_path,
        ])
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _resolve_aozora_image_block(note_block: Mapping[str, object], source_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(source_path) if source_path else None
    image_dir, manifest = _read_aozora_image_manifest(path)
    image_id = note_block.get('image_id')
    image_src = note_block.get('image_src')
    manifest_entries = _matching_aozora_image_manifest_entries(manifest, image_id=image_id, image_src=image_src)
    image_path = _resolve_aozora_image_path_from_manifest(
        image_dir=image_dir,
        manifest=manifest,
        image_id=image_id,
        image_src=image_src,
    )
    if image_path is None:
        image_path = _resolve_aozora_image_path_without_manifest(path, image_src)
    caption = str(note_block.get('caption', '') or '').strip()
    if not caption:
        for item in manifest_entries:
            manifest_caption = str(item.get('caption', '') or '').strip()
            if manifest_caption:
                caption = manifest_caption
                break
    block: dict[str, Any] = {
        'kind': 'image',
        'image_id': str(image_id or ''),
        'image_src': str(image_src or ''),
        'caption': caption,
        'blank_before': int(note_block.get('blank_before', 1) or 1),
    }
    if image_path is not None:
        block['image_path'] = str(image_path)
    return block


def _path_signature_for_cache(path: Path) -> tuple[object, ...]:
    try:
        stat = path.stat()
        mtime_ns = getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1_000_000_000))
        return (str(path.resolve()), int(stat.st_size), int(mtime_ns))
    except OSError:
        return (str(path), -1, -1)


def _aozora_image_sidecar_cache_key(source_path: Path) -> tuple[object, ...]:
    image_dir, manifest_path = _aozora_image_sidecar_paths(source_path)
    parts: list[object] = []
    parts.extend(_path_signature_for_cache(manifest_path))
    parts.extend(_path_signature_for_cache(image_dir))

    image_files: list[Path] = []
    try:
        payload = json.loads(manifest_path.read_text(encoding='utf-8'))
    except Exception:
        payload = None
    manifest_image_dir = image_dir
    manifest_entries = _manifest_images(payload if isinstance(payload, Mapping) else None)
    if isinstance(payload, Mapping):
        payload_image_dir = payload.get('image_dir')
        if isinstance(payload_image_dir, str) and payload_image_dir.strip():
            candidate = Path(payload_image_dir)
            if not candidate.is_absolute():
                candidate = manifest_path.parent / candidate
            manifest_image_dir = candidate
    if manifest_entries:
        for item in manifest_entries.values():
            file_value = str(item.get('file', '') or '').strip()
            if not file_value:
                continue
            file_path = Path(file_value)
            if not file_path.is_absolute():
                file_path = manifest_image_dir / file_path
            image_files.append(file_path)
    elif image_dir.exists():
        try:
            image_files.extend(sorted(path for path in image_dir.iterdir() if path.is_file())[:128])
        except OSError:
            pass

    for image_file in sorted({path for path in image_files}, key=lambda path: str(path))[:128]:
        parts.extend(_path_signature_for_cache(image_file))
    return tuple(parts)


def _parse_aozora_note_only_line(value: str | None) -> AozoraNoteBlock | None:
    _refresh_core_globals()
    match = AOZORA_NOTE_ONLY_RE.match(value or '')
    if not match:
        return None
    note_text = match.group(1).strip()
    image_marker = AOZORA_IMAGE_MARKER_RE.match(note_text)
    if image_marker:
        image_id = image_marker.group(1).zfill(4)
        return {'kind': 'image', 'image_id': image_id, 'blank_before': 1}
    image_note = AOZORA_INSERTED_IMAGE_NOTE_RE.match(note_text)
    if image_note:
        caption_match = re.search(r'キャプション[「『]([^」』]+)[」』]', note_text)
        return {
            'kind': 'image',
            'image_src': image_note.group('filename').strip(),
            'caption': caption_match.group(1).strip() if caption_match else '',
            'blank_before': 1,
        }
    if _is_aozora_pagebreak_note(note_text):
        return {'kind': 'pagebreak'}
    indent_note = _parse_aozora_indent_note(note_text)
    if indent_note:
        return indent_note
    emphasis_note = _parse_aozora_emphasis_note(note_text)
    if emphasis_note:
        return emphasis_note
    side_line_note = _parse_aozora_side_line_note(note_text)
    if side_line_note:
        return side_line_note
    return {'kind': 'note'}


def _apply_note_to_previous_block(blocks: list[dict[str, Any]], note_block: Mapping[str, object] | None) -> bool:
    _refresh_core_globals()
    if not blocks or not note_block:
        return False
    kind = note_block.get('kind')
    for block in reversed(blocks):
        runs = block.get('runs', [])
        if not runs:
            continue
        if kind == 'emphasis':
            return _apply_emphasis_to_recent_runs(runs, note_block.get('target_text', ''), note_block.get('emphasis', ''))
        if kind == 'side_line':
            return _apply_side_line_to_recent_runs(runs, note_block.get('target_text', ''), note_block.get('side_line', ''))
        return False
    return False


def _flush_text_run_buffer(runs: Runs, buffer: str, *, ruby: str = '', bold: bool = False, italic: bool = False, emphasis: str = '', side_line: str = '', code: bool = False) -> None:
    _refresh_core_globals()
    if not buffer:
        return
    if (
        runs
        and runs[-1].get('bold') == bold
        and runs[-1].get('italic') == italic
        and runs[-1].get('ruby', '') == (ruby or '')
        and runs[-1].get('emphasis', '') == (emphasis or '')
        and runs[-1].get('side_line', '') == (side_line or '')
        and bool(runs[-1].get('code', False)) == bool(code)
    ):
        runs[-1]['text'] += buffer
    else:
        runs.append({'text': buffer, 'ruby': ruby or '', 'bold': bold, 'italic': italic, 'emphasis': emphasis or '', 'side_line': side_line or '', 'code': bool(code)})


def _append_text_run(runs: Runs, text: str, *, ruby: str = '', bold: bool = False, italic: bool = False, emphasis: str = '', side_line: str = '', code: bool = False) -> None:
    _refresh_core_globals()
    if not text:
        return
    ruby = ruby or ''
    emphasis = emphasis or ''
    side_line = side_line or ''
    code = bool(code)
    if (
        runs
        and runs[-1].get('bold') == bold
        and runs[-1].get('italic') == italic
        and runs[-1].get('ruby', '') == ruby
        and runs[-1].get('emphasis', '') == emphasis
        and runs[-1].get('side_line', '') == side_line
        and bool(runs[-1].get('code', False)) == code
    ):
        runs[-1]['text'] += text
    else:
        runs.append({'text': text, 'ruby': ruby, 'bold': bold, 'italic': italic, 'emphasis': emphasis, 'side_line': side_line, 'code': code})


def _aozora_inline_to_runs(value: str, *, bold: bool = False, italic: bool = False) -> Runs:
    _refresh_core_globals()
    if not value:
        return []
    value = replace_aozora_gaiji_notes(value)

    runs: Runs = []
    buffer = ''
    index = 0
    length = len(value)
    while index < length:
        char = value[index]

        if value.startswith('［＃', index):
            end = value.find('］', index + 2)
            if end != -1:
                note_text = value[index + 2:end].strip()
                emphasis_note = _parse_aozora_emphasis_note(note_text)
                if emphasis_note:
                    _flush_text_run_buffer(runs, buffer, bold=bold, italic=italic)
                    buffer = ''
                    _apply_emphasis_to_recent_runs(runs, emphasis_note['target_text'], emphasis_note['emphasis'])
                    index = end + 1
                    continue
                side_line_note = _parse_aozora_side_line_note(note_text)
                if side_line_note:
                    _flush_text_run_buffer(runs, buffer, bold=bold, italic=italic)
                    buffer = ''
                    _apply_side_line_to_recent_runs(runs, side_line_note['target_text'], side_line_note['side_line'])
                index = end + 1
                continue

        if char == '｜':
            ruby_start = value.find('《', index + 1)
            ruby_end = value.find('》', ruby_start + 1) if ruby_start != -1 else -1
            if ruby_start != -1 and ruby_end != -1:
                base_text = value[index + 1:ruby_start]
                ruby_text = value[ruby_start + 1:ruby_end]
                if base_text and ruby_text:
                    _flush_text_run_buffer(runs, buffer, bold=bold, italic=italic)
                    buffer = ''
                    _append_text_run(runs, base_text, ruby=ruby_text, bold=bold, italic=italic)
                    index = ruby_end + 1
                    continue

        if char == '《':
            ruby_end = value.find('》', index + 1)
            if ruby_end != -1:
                ruby_text = value[index + 1:ruby_end]
                match = AOZORA_IMPLICIT_RUBY_BASE_RE.search(buffer)
                if ruby_text and match:
                    prefix = buffer[:match.start()]
                    base_text = buffer[match.start():]
                    if prefix:
                        _flush_text_run_buffer(runs, prefix, bold=bold, italic=italic)
                    buffer = ''
                    _append_text_run(runs, base_text, ruby=ruby_text, bold=bold, italic=italic)
                    index = ruby_end + 1
                    continue
                buffer += value[index:ruby_end + 1]
                index = ruby_end + 1
                continue

        buffer += char
        index += 1

    _flush_text_run_buffer(runs, buffer, bold=bold, italic=italic)
    return [run for run in runs if run.get('text')]


def read_text_file_with_fallback(text_path: PathLike) -> tuple[str, str]:
    """TXT / Markdown を BOM 判定・自動判定・既知候補の順で読み込む。"""
    _refresh_core_globals()
    raw = Path(text_path).read_bytes()
    if not raw:
        return '', 'utf-8'

    bom_candidates = (
        (codecs.BOM_UTF8, 'utf-8-sig'),
        (codecs.BOM_UTF32_LE, 'utf-32'),
        (codecs.BOM_UTF32_BE, 'utf-32'),
        (codecs.BOM_UTF16_LE, 'utf-16'),
        (codecs.BOM_UTF16_BE, 'utf-16'),
    )
    for bom, encoding in bom_candidates:
        if raw.startswith(bom):
            decoded = _try_decode_bytes(raw, encoding)
            if decoded:
                return decoded

    guessed_utf16 = _guess_utf16_without_bom(raw)
    if guessed_utf16:
        decoded = _try_decode_bytes(raw, guessed_utf16)
        if decoded:
            return decoded

    decoded_utf8 = _try_decode_bytes(raw, 'utf-8')
    if decoded_utf8:
        return decoded_utf8

    normalized = _detect_text_with_charset_normalizer(raw)
    if normalized:
        return normalized

    last_error = None
    fallback_encodings = (
        'utf-8-sig', 'cp932', 'shift_jis', 'euc_jp', 'iso2022_jp', 'utf-16', 'utf-16-le', 'utf-16-be'
    )
    for encoding in fallback_encodings:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc

    raise UnicodeDecodeError(
        last_error.encoding if last_error else 'unknown',
        last_error.object if last_error else raw,
        last_error.start if last_error else 0,
        last_error.end if last_error else 1,
        'テキストを自動判定できませんでした。UTF-8 / CP932 / Shift_JIS / EUC-JP / ISO-2022-JP / UTF-16 を確認してください。',
    )



def _markdown_inline_to_runs(value: str, link_definitions: Mapping[str, str] | None = None) -> Runs:
    _refresh_core_globals()
    link_definitions = {str(k).strip().lower(): str(v or '').strip() for k, v in (link_definitions or {}).items() if str(k).strip()}

    def _resolve_reference(label: object, fallback: object = '') -> str:
        key = str(label or '').strip().lower()
        return link_definitions.get(key, str(fallback or '').strip())

    value = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', lambda m: (m.group(1) or '').strip(), value)
    value = re.sub(r'!\[([^\]]*)\]\[([^\]]*)\]', lambda m: (m.group(1) or _resolve_reference(m.group(2), m.group(2))).strip(), value)
    value = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', lambda m: (m.group(1) or m.group(2)).strip(), value)
    value = re.sub(r'\[([^\]]+)\]\[([^\]]*)\]', lambda m: (m.group(1) or _resolve_reference(m.group(2) or m.group(1), m.group(2) or m.group(1))).strip(), value)
    value = re.sub(r'\[\^([^\]]+)\]', lambda m: f'※{m.group(1)}', value)
    runs: Runs = []
    pattern = re.compile(
        r'(`[^`]+`|'
        r'\*\*\*.+?\*\*\*|'
        r'(?<!\w)___(?!_).+?(?<!_)___(?!\w)|'
        r'\*\*.+?\*\*|'
        r'(?<!\w)__(?!_).+?(?<!_)__(?!\w)|'
        r'\*(?!\*)(.+?)\*(?!\*)|'
        r'(?<!\w)_(?!_).+?(?<!_)_(?!\w))'
    )
    pos = 0
    for match in pattern.finditer(value):
        if match.start() > pos:
            runs.extend(_aozora_inline_to_runs(value[pos:match.start()], bold=False, italic=False))
        token = match.group(0)
        if token.startswith('`') and token.endswith('`'):
            inner = token[1:-1]
            if inner:
                runs.append({'text': inner, 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': True})
            pos = match.end()
            continue
        bold = italic = False
        inner = token
        if (token.startswith('***') and token.endswith('***')) or (token.startswith('___') and token.endswith('___')):
            inner = token[3:-3]
            bold = True
            italic = True
        elif (token.startswith('**') and token.endswith('**')) or (token.startswith('__') and token.endswith('__')):
            inner = token[2:-2]
            bold = True
        elif (token.startswith('*') and token.endswith('*')) or (token.startswith('_') and token.endswith('_')):
            inner = token[1:-1]
            italic = True
        if inner:
            runs.extend(_aozora_inline_to_runs(inner, bold=bold, italic=italic))
        pos = match.end()
    if pos < len(value):
        runs.extend(_aozora_inline_to_runs(value[pos:], bold=False, italic=False))
    return _merge_adjacent_runs(runs)


def _plain_inline_to_runs(value: str, parse_aozora: bool = True, code: bool = False) -> Runs:
    _refresh_core_globals()
    if not value:
        return []
    if parse_aozora:
        runs = _aozora_inline_to_runs(value, bold=False, italic=False)
        if code:
            for run in runs:
                run['code'] = True
        return runs
    return [{'text': value, 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': bool(code)}]


def _consume_plain_text_leading_fullwidth_indent(value: str) -> tuple[str, int]:
    """Return text without leading ideographic spaces and their indent width.

    Plain TXT paragraphs are given a default one-character paragraph indent at
    render time. Aozora-style text often also stores that same paragraph indent
    as a leading fullwidth space in the source line. Leaving the space in the
    text run would render it in addition to the default paragraph indent, so the
    leading fullwidth spaces are converted into an explicit paragraph-indent
    width instead.
    """
    _refresh_core_globals()
    text = str(value or '')
    leading = len(text) - len(text.lstrip('　'))
    if leading <= 0:
        return text, 0
    return text[leading:], leading


def _plain_text_line_starts_with_opening_bracket(value: str) -> bool:
    """Return True when a TXT body line starts with an opening bracket.

    Dialogue lines in Japanese plain text often begin directly with an opening
    quote such as ``「`` or ``『``.  Those lines should not receive the default
    one-character paragraph indent; otherwise an artificial blank appears before
    the quote.  Explicit Aozora indent notes and literal leading fullwidth spaces
    are handled separately by the caller.
    """
    _refresh_core_globals()
    text = str(value or '')
    return bool(text) and text[0] in OPENING_BRACKET_CHARS


def _normalize_text_line(value: str, has_started_document: bool = False, strip_leading_for_indent: bool = False) -> str:
    _refresh_core_globals()
    value = value.replace('\ufeff', '').replace('\r', '').replace('\t', '    ').replace('\xa0', ' ')
    if not has_started_document:
        value = _strip_leading_start_text(value)
    value = value.rstrip()
    if strip_leading_for_indent:
        value = re.sub(r'^[\s\u3000]+', '', value)
    return value


TEXT_INPUT_SUPPORT_SUMMARY = {
    'plain': 'プレーンテキストとして扱います。青空文庫のルビ・改ページ注記・字下げ注記・傍点注記・傍線注記のみ簡易対応です。',
    'markdown': 'Markdown を簡易整形します。ATX / Setext 見出し・箇条書き・番号付きリスト・task list・pipe table・定義リスト・脚注・コードブロック・参照リンクを簡易対応します。',
}


def _dedupe_preserve_order(values: Iterable[object]) -> WarningList:
    _refresh_core_globals()
    seen = set()
    ordered: list[str] = []
    for value in values:
        item = str(value or '').strip()
        if not item or item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _find_markdown_support_warnings(text: str) -> WarningList:
    _refresh_core_globals()
    warnings: WarningList = []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    raw_html_lines: list[int] = []
    nested_list_lines: list[int] = []
    for index, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r'^<(?:!DOCTYPE|/?[A-Za-z][^>]*)>$', stripped):
            raw_html_lines.append(index)
        if re.match(r'^(?: {2,}|\t+)(?:[-*+]\s+|\d+[\.)]\s+)', line):
            nested_list_lines.append(index)
    if raw_html_lines:
        preview = ', '.join(str(n) for n in raw_html_lines[:5])
        suffix = ' ほか' if len(raw_html_lines) > 5 else ''
        warnings.append(f'Markdown の生 HTML は専用解釈せず、文字列として残る場合があります。該当行: {preview}{suffix}')
    if nested_list_lines:
        preview = ', '.join(str(n) for n in nested_list_lines[:5])
        suffix = ' ほか' if len(nested_list_lines) > 5 else ''
        warnings.append(f'ネストした Markdown リストは字下げを簡略化して描画します。該当行: {preview}{suffix}')
    if re.search(r'^```+\s*(mermaid|plantuml|graphviz|dot)\b', text, flags=re.IGNORECASE | re.MULTILINE):
        warnings.append('Mermaid / PlantUML / Graphviz などの図表コードブロックは図として描画せず、コードとして出力します。')
    if (
        text.count('$$') >= 2
        or re.search(r'^\${2}.*?\${2}$', text, flags=re.MULTILINE)
        or re.search(r'\\\[(.|\n)*?\\\]', text)
    ):
        warnings.append('数式ブロックは専用組版せず、プレーンテキストとして扱います。')
    return _dedupe_preserve_order(warnings)


def _find_plain_text_support_warnings(text: str) -> WarningList:
    _refresh_core_globals()
    warnings: WarningList = []
    if re.search(r'^#{1,6}\s+\S', text, flags=re.MULTILINE):
        warnings.append('Markdown の見出し記法らしい行があります。見出しとして整形したい場合は .md / .markdown で保存してください。')
    if re.search(r'^(?:[-*+]\s+|\d+[\.)]\s+)\S', text, flags=re.MULTILINE):
        warnings.append('Markdown の箇条書き・番号付きリストらしい行があります。テキスト入力では通常段落として扱います。')
    return _dedupe_preserve_order(warnings)


def _is_plain_dialogue_compact_candidate(
    body_text: str,
    *,
    explicit_indent_active: bool,
    leading_fullwidth_indent: int,
) -> bool:
    """Return whether a plain-text line is a compactable dialogue row.

    Aozora TXT uses blank lines to signal the places where the renderer should
    visibly open the composition.  Consecutive dialogue lines that begin with
    Japanese quotation marks and have no blank line between them should keep
    their independent block identity, but they should not force a fresh vertical
    column for every short speaker turn.  Limit this marker to unindented
    ``「`` / ``『`` rows so headings such as ``【確認ページ】``, Aozora indent
    blocks, quoted poems, and explicitly indented material keep the historical
    paragraph spacing.
    """
    if explicit_indent_active or int(leading_fullwidth_indent or 0) > 0:
        return False
    return str(body_text or '').startswith(('「', '『'))


def _blocks_from_plain_text(text: str, *, source_path: str | Path | None = None) -> TextBlocks:
    _refresh_core_globals()
    blocks: TextBlocks = []
    active_indent = None
    pending_once_indent = None
    has_started_content = False
    previous_compactable_dialogue_index: int | None = None
    for raw_line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        normalized = _normalize_text_line(raw_line, has_started_document=has_started_content, strip_leading_for_indent=False)
        if not normalized:
            blocks.append({'kind': 'blank'})
            previous_compactable_dialogue_index = None
            continue
        note_block = _parse_aozora_note_only_line(normalized)
        if note_block:
            if note_block['kind'] == 'pagebreak':
                blocks.append(note_block)
                previous_compactable_dialogue_index = None
            elif note_block['kind'] == 'indent_start':
                active_indent = {
                    'indent_chars': note_block.get('indent_chars', 0),
                    'wrap_indent_chars': note_block.get('wrap_indent_chars', note_block.get('indent_chars', 0)),
                }
                previous_compactable_dialogue_index = None
            elif note_block['kind'] == 'indent_end':
                active_indent = None
                pending_once_indent = None
                previous_compactable_dialogue_index = None
            elif note_block['kind'] == 'indent_once':
                pending_once_indent = {
                    'indent_chars': note_block.get('indent_chars', 0),
                    'wrap_indent_chars': note_block.get('wrap_indent_chars', note_block.get('indent_chars', 0)),
                }
                previous_compactable_dialogue_index = None
            elif note_block['kind'] in {'emphasis', 'side_line'}:
                _apply_note_to_previous_block(blocks, note_block)
                previous_compactable_dialogue_index = None
            elif note_block['kind'] == 'image':
                blocks.append(_resolve_aozora_image_block(note_block, source_path))
                has_started_content = True
                previous_compactable_dialogue_index = None
            continue
        body_text, leading_fullwidth_indent = _consume_plain_text_leading_fullwidth_indent(normalized)
        runs = _plain_inline_to_runs(body_text)
        if not runs:
            blocks.append({'kind': 'blank'})
            previous_compactable_dialogue_index = None
            continue
        indent_spec = pending_once_indent or active_indent
        explicit_indent_active = indent_spec is not None
        starts_with_opening_bracket = _plain_text_line_starts_with_opening_bracket(body_text)
        if indent_spec:
            base_indent_chars = int(indent_spec.get('indent_chars', 1) or 0)
            base_wrap_indent_chars = indent_spec.get('wrap_indent_chars', indent_spec.get('indent_chars', 1))
        else:
            base_indent_chars = 0 if starts_with_opening_bracket else 1
            base_wrap_indent_chars = 0
        if leading_fullwidth_indent:
            base_indent_chars = max(int(base_indent_chars or 0), int(leading_fullwidth_indent or 0))
        block = {
            'kind': 'paragraph',
            'runs': runs,
            'indent': bool(explicit_indent_active or base_indent_chars > 0),
            'indent_chars': max(0, int(base_indent_chars or 0)),
            'wrap_indent_chars': base_wrap_indent_chars,
            'blank_before': 1,
        }
        is_compactable_dialogue = _is_plain_dialogue_compact_candidate(
            body_text,
            explicit_indent_active=explicit_indent_active,
            leading_fullwidth_indent=leading_fullwidth_indent,
        )
        if is_compactable_dialogue and previous_compactable_dialogue_index is not None:
            previous_block = blocks[previous_compactable_dialogue_index]
            previous_block['compact_after'] = True
            block['suppress_paragraph_gap_before'] = True
        blocks.append(block)
        has_started_content = True
        pending_once_indent = None
        previous_compactable_dialogue_index = len(blocks) - 1 if is_compactable_dialogue else None
    return blocks


MARKDOWN_FOOTNOTE_DEF_RE = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)$')
MARKDOWN_DEF_LIST_RE = re.compile(r'^\s*:\s+(.*)$')
MARKDOWN_ORDERED_LIST_RE = re.compile(r'^\s*(\d+)[\.)]\s+(.*)$')
MARKDOWN_FENCE_RE = re.compile(r'^\s*(```+|~~~+)')


def _markdown_text_run(text: str, *, bold: bool = False, code: bool = False) -> TextRun:
    _refresh_core_globals()
    return {
        'text': text,
        'ruby': '',
        'bold': bool(bold),
        'italic': False,
        'emphasis': '',
        'side_line': '',
        'code': bool(code),
    }


def _set_runs_bold(runs: Runs) -> Runs:
    _refresh_core_globals()
    for run in runs:
        run['bold'] = True
    return runs


def _extract_markdown_footnotes(lines: Sequence[str]) -> tuple[list[str], list[FootnoteEntry], LinkDefinitions]:
    _refresh_core_globals()
    body_lines = []
    footnotes: list[FootnoteEntry] = []
    link_definitions: LinkDefinitions = {}
    in_code = False
    active_fence = ''
    index = 0

    if lines:
        first = lines[0].strip().replace('﻿', '')
        if first in {'---', '+++'}:
            fence = first
            probe = 1
            found_front_matter_end = False
            while probe < len(lines):
                if lines[probe].strip() == fence:
                    index = probe + 1
                    found_front_matter_end = True
                    break
                probe += 1
            if not found_front_matter_end:
                index = 0

    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()
        fence_match = MARKDOWN_FENCE_RE.match(stripped)
        if fence_match:
            marker = fence_match.group(1)
            marker_char = marker[:1]
            if not in_code:
                in_code = True
                active_fence = marker_char
            elif not active_fence or marker_char == active_fence:
                in_code = False
                active_fence = ''
            body_lines.append(raw_line)
            index += 1
            continue
        if not in_code:
            footnote_match = MARKDOWN_FOOTNOTE_DEF_RE.match(stripped)
            if footnote_match:
                footnote_id = footnote_match.group(1).strip()
                parts = [footnote_match.group(2).strip()]
                index += 1
                while index < len(lines):
                    continuation = lines[index]
                    continuation_stripped = continuation.strip()
                    if continuation.startswith('    ') or continuation.startswith('	'):
                        parts.append(continuation.lstrip())
                        index += 1
                        continue
                    if not continuation_stripped:
                        parts.append('')
                        index += 1
                        continue
                    break
                footnotes.append({'id': footnote_id, 'text': '\n'.join(parts).strip()})
                continue
            link_def_match = re.match(r'^\[([^\]]+)\]:\s*(\S.*)$', stripped)
            if link_def_match:
                link_key = link_def_match.group(1).strip().lower()
                link_target = link_def_match.group(2).strip()
                if link_key and link_target:
                    link_definitions[link_key] = link_target
                index += 1
                continue
        body_lines.append(raw_line)
        index += 1
    return body_lines, footnotes, link_definitions


def _split_markdown_table_row(line: object) -> list[str]:
    _refresh_core_globals()
    value = str(line or '').strip()
    if value.startswith('|'):
        value = value[1:]
    if value.endswith('|'):
        value = value[:-1]
    cells = []
    buffer = []
    escaped = False
    for ch in value:
        if escaped:
            buffer.append(ch)
            escaped = False
            continue
        if ch == '\\':
            escaped = True
            continue
        if ch == '|':
            cells.append(''.join(buffer).strip())
            buffer = []
            continue
        buffer.append(ch)
    if escaped:
        buffer.append('\\')
    cells.append(''.join(buffer).strip())
    return cells


def _is_markdown_table_separator(line: object) -> bool:
    _refresh_core_globals()
    cells = _split_markdown_table_row(line)
    if not cells:
        return False
    for cell in cells:
        compact = cell.replace(' ', '')
        if not compact or not re.fullmatch(r':?-{3,}:?', compact):
            return False
    return True


def _build_markdown_table_blocks(headers: Sequence[str], rows: Sequence[Sequence[str]], *, link_definitions: Mapping[str, str] | None = None) -> TextBlocks:
    _refresh_core_globals()
    blocks: TextBlocks = []
    clean_headers = [str(cell or '').strip() for cell in headers]
    if not rows:
        runs: Runs = []
        for header in clean_headers:
            if not header:
                continue
            if runs:
                runs.append(_markdown_text_run('　'))
            header_runs = _set_runs_bold(_markdown_inline_to_runs(header, link_definitions=link_definitions))
            runs.extend(header_runs)
        if runs:
            blocks.append({'kind': 'table_row', 'runs': _merge_adjacent_runs(runs), 'indent': False, 'blank_before': 1})
        return blocks

    for row in rows:
        runs = []
        width = max(len(clean_headers), len(row))
        for idx in range(width):
            header = clean_headers[idx] if idx < len(clean_headers) else ''
            cell = row[idx] if idx < len(row) else ''
            header = str(header or '').strip()
            cell = str(cell or '').strip()
            if not header and not cell:
                continue
            if runs:
                runs.append(_markdown_text_run('　'))
            if header:
                runs.extend(_set_runs_bold(_markdown_inline_to_runs(header, link_definitions=link_definitions)))
            if header and cell:
                runs.append(_markdown_text_run('：'))
            if cell:
                runs.extend(_markdown_inline_to_runs(cell, link_definitions=link_definitions))
        if runs:
            blocks.append({'kind': 'table_row', 'runs': _merge_adjacent_runs(runs), 'indent': False, 'blank_before': 1})
    return blocks


def _append_markdown_footnote_blocks(blocks: TextBlocks, footnotes: Sequence[FootnoteEntry], *, link_definitions: Mapping[str, str] | None = None) -> None:
    _refresh_core_globals()
    if not footnotes:
        return
    if blocks and blocks[-1].get('kind') != 'blank':
        blocks.append({'kind': 'blank'})
    heading_runs = [_markdown_text_run('脚注', bold=True)]
    blocks.append({'kind': 'heading', 'runs': heading_runs, 'indent': False, 'blank_before': 2})
    for note in footnotes:
        footnote_id = str(note.get('id', '')).strip()
        note_text = re.sub(r'\s*\n\s*', '　', str(note.get('text', '') or '').strip())
        runs: Runs = []
        prefix = f'※{footnote_id}' if footnote_id else '※'
        runs.append(_markdown_text_run(prefix, bold=True))
        if note_text:
            runs.append(_markdown_text_run('　'))
            runs.extend(_markdown_inline_to_runs(note_text, link_definitions=link_definitions))
        blocks.append({'kind': 'paragraph', 'runs': _merge_adjacent_runs(runs), 'indent': False, 'blank_before': 1})


def _blocks_from_markdown(text: str, *, source_path: str | Path | None = None) -> TextBlocks:
    _refresh_core_globals()
    blocks: TextBlocks = []
    body_lines, footnotes, link_definitions = _extract_markdown_footnotes(text.replace('\r\n', '\n').replace('\r', '\n').split('\n'))
    in_code = False
    active_fence = ''
    active_indent = None
    pending_once_indent = None
    has_started_content = False
    index = 0
    while index < len(body_lines):
        source = body_lines[index].replace('\ufeff', '').replace('\t', '    ')
        stripped = source.strip()
        fence_match = MARKDOWN_FENCE_RE.match(stripped)
        if fence_match:
            marker = fence_match.group(1)
            marker_char = marker[:1]
            if not in_code:
                in_code = True
                active_fence = marker_char
            elif not active_fence or marker_char == active_fence:
                in_code = False
                active_fence = ''
            index += 1
            continue
        if in_code:
            normalized = _normalize_text_line(source, has_started_document=has_started_content, strip_leading_for_indent=False)
            if not normalized:
                blocks.append({'kind': 'blank'})
            else:
                blocks.append({'kind': 'code', 'runs': _plain_inline_to_runs(normalized, parse_aozora=False, code=True), 'indent': False, 'blank_before': 1})
                has_started_content = True
            index += 1
            continue
        if not stripped:
            blocks.append({'kind': 'blank'})
            index += 1
            continue
        note_block = _parse_aozora_note_only_line(stripped)
        if note_block:
            if note_block['kind'] == 'pagebreak':
                blocks.append(note_block)
            elif note_block['kind'] == 'indent_start':
                active_indent = {
                    'indent_chars': note_block.get('indent_chars', 0),
                    'wrap_indent_chars': note_block.get('wrap_indent_chars', note_block.get('indent_chars', 0)),
                }
            elif note_block['kind'] == 'indent_end':
                active_indent = None
                pending_once_indent = None
            elif note_block['kind'] == 'indent_once':
                pending_once_indent = {
                    'indent_chars': note_block.get('indent_chars', 0),
                    'wrap_indent_chars': note_block.get('wrap_indent_chars', note_block.get('indent_chars', 0)),
                }
            elif note_block['kind'] in {'emphasis', 'side_line'}:
                _apply_note_to_previous_block(blocks, note_block)
            elif note_block['kind'] == 'image':
                blocks.append(_resolve_aozora_image_block(note_block, source_path))
                has_started_content = True
            index += 1
            continue

        if '|' in source and index + 1 < len(body_lines) and _is_markdown_table_separator(body_lines[index + 1]):
            headers = _split_markdown_table_row(source)
            row_index = index + 2
            rows = []
            while row_index < len(body_lines):
                row_source = body_lines[row_index]
                row_stripped = row_source.strip()
                if not row_stripped or MARKDOWN_FENCE_RE.match(row_stripped):
                    break
                if '|' not in row_source:
                    break
                rows.append(_split_markdown_table_row(row_source))
                row_index += 1
            table_blocks = _build_markdown_table_blocks(headers, rows, link_definitions=link_definitions)
            blocks.extend(table_blocks)
            if table_blocks:
                has_started_content = True
            pending_once_indent = None
            index = row_index
            continue

        if index + 1 < len(body_lines) and MARKDOWN_DEF_LIST_RE.match(body_lines[index + 1]):
            term = _normalize_text_line(source, has_started_document=has_started_content, strip_leading_for_indent=True)
            if term:
                term_runs = _set_runs_bold(_markdown_inline_to_runs(term, link_definitions=link_definitions))
                blocks.append({'kind': 'definition_term', 'runs': term_runs, 'indent': False, 'blank_before': 1})
                has_started_content = True
            index += 1
            while index < len(body_lines):
                def_match = MARKDOWN_DEF_LIST_RE.match(body_lines[index])
                if not def_match:
                    break
                def_parts = [def_match.group(1).strip()]
                index += 1
                while index < len(body_lines):
                    continuation = body_lines[index]
                    continuation_stripped = continuation.strip()
                    if not continuation_stripped:
                        break
                    if continuation.startswith('  ') and not MARKDOWN_DEF_LIST_RE.match(continuation):
                        def_parts.append(continuation_stripped)
                        index += 1
                        continue
                    break
                definition_text = '　'.join(part for part in def_parts if part)
                if definition_text:
                    runs = _markdown_inline_to_runs(definition_text, link_definitions=link_definitions)
                    blocks.append({'kind': 'definition', 'runs': runs, 'indent': True, 'indent_chars': 1, 'wrap_indent_chars': 1, 'blank_before': 1})
                    has_started_content = True
            pending_once_indent = None
            continue

        heading = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if heading:
            level = len(heading.group(1))
            content = _normalize_text_line(heading.group(2), has_started_document=has_started_content, strip_leading_for_indent=True)
            runs = _markdown_inline_to_runs(content, link_definitions=link_definitions)
            if runs:
                for run in runs:
                    run['bold'] = True
                blocks.append({'kind': 'heading', 'runs': runs, 'indent': False, 'blank_before': 2 if level <= 2 else 1})
                has_started_content = True
            pending_once_indent = None
            index += 1
            continue

        if index + 1 < len(body_lines) and stripped and re.fullmatch(r'(?:=\s*){3,}|(?:-\s*){3,}', body_lines[index + 1].strip()):
            marker_line = body_lines[index + 1].strip()
            level = 1 if '=' in marker_line else 2
            runs = _markdown_inline_to_runs(stripped, link_definitions=link_definitions)
            if runs:
                for run in runs:
                    run['bold'] = True
                blocks.append({'kind': 'heading', 'runs': runs, 'indent': False, 'blank_before': 2 if level <= 2 else 1})
                has_started_content = True
            pending_once_indent = None
            index += 2
            continue

        if stripped and re.fullmatch(r'(?:-{3,}|\*{3,}|_{3,})', stripped.replace(' ', '')):
            if not blocks or blocks[-1].get('kind') != 'blank':
                blocks.append({'kind': 'blank'})
            pending_once_indent = None
            index += 1
            continue

        quote = re.match(r'^\s*(>+)\s?(.*)$', source)
        if quote:
            depth = max(1, len(quote.group(1)))
            content = _normalize_text_line(quote.group(2), has_started_document=has_started_content, strip_leading_for_indent=True)
            if content:
                prefix = '引用：' if depth == 1 else f'引用{depth}：'
                runs = [_markdown_text_run(prefix, bold=True)] + _markdown_inline_to_runs(content, link_definitions=link_definitions)
                blocks.append({'kind': 'blockquote', 'runs': _merge_adjacent_runs(runs), 'indent': False, 'blank_before': 1, 'wrap_indent_chars': 1})
                has_started_content = True
            else:
                blocks.append({'kind': 'blank'})
            pending_once_indent = None
            index += 1
            continue

        task = re.match(r'^\s*[-*+]\s+\[( |x|X)\]\s+(.*)$', source)
        if task:
            marker = '☑' if task.group(1).lower() == 'x' else '☐'
            content = _normalize_text_line(task.group(2), has_started_document=has_started_content, strip_leading_for_indent=True)
            runs = [_markdown_text_run(marker, bold=True)]
            if content:
                runs.append(_markdown_text_run(' '))
                runs.extend(_markdown_inline_to_runs(content, link_definitions=link_definitions))
            blocks.append({'kind': 'task_list', 'runs': _merge_adjacent_runs(runs), 'indent': False, 'blank_before': 1})
            has_started_content = True
            pending_once_indent = None
            index += 1
            continue

        bullet = re.match(r'^\s*[-*+]\s+(.*)$', source)
        if bullet:
            content = _normalize_text_line(bullet.group(1), has_started_document=has_started_content, strip_leading_for_indent=True)
            runs = [_markdown_text_run('・')] + _markdown_inline_to_runs(content, link_definitions=link_definitions)
            blocks.append({'kind': 'bullet', 'runs': runs, 'indent': False, 'blank_before': 1})
            has_started_content = True
            pending_once_indent = None
            index += 1
            continue

        ordered = MARKDOWN_ORDERED_LIST_RE.match(source)
        if ordered:
            content = _normalize_text_line(ordered.group(2), has_started_document=has_started_content, strip_leading_for_indent=True)
            prefix = f'{ordered.group(1)}.'
            runs = [_markdown_text_run(prefix, bold=True)]
            if content:
                runs.append(_markdown_text_run('　'))
                runs.extend(_markdown_inline_to_runs(content, link_definitions=link_definitions))
            blocks.append({'kind': 'ordered_list', 'runs': _merge_adjacent_runs(runs), 'indent': False, 'blank_before': 1})
            has_started_content = True
            pending_once_indent = None
            index += 1
            continue

        normalized = _normalize_text_line(source, has_started_document=has_started_content, strip_leading_for_indent=True)
        if normalized:
            runs = _markdown_inline_to_runs(normalized, link_definitions=link_definitions)
            if runs:
                indent_spec = pending_once_indent or active_indent
                blocks.append({
                    'kind': 'paragraph',
                    'runs': runs,
                    'indent': True,
                    'indent_chars': indent_spec.get('indent_chars', 1) if indent_spec else 1,
                    'wrap_indent_chars': indent_spec.get('wrap_indent_chars', indent_spec.get('indent_chars', 1)) if indent_spec else 0,
                    'blank_before': 1,
                })
                has_started_content = True
                pending_once_indent = None
        index += 1

    _append_markdown_footnote_blocks(blocks, footnotes, link_definitions=link_definitions)
    return blocks


def load_text_input_document(text_path: PathLike, *, parser: str = 'plain') -> TextInputDocument:
    """TXT / Markdown を読み込み、入力形式ごとのブロック列へ正規化する。"""
    _refresh_core_globals()
    source_path = Path(text_path)
    parser_key = str(parser or 'plain').strip().lower()
    if parser_key != 'markdown':
        parser_key = 'plain'
    cache_key = (parser_key, *_source_document_cache_key(source_path), *_aozora_image_sidecar_cache_key(source_path))
    cached = _get_cached_input_document(_TEXT_INPUT_DOCUMENT_CACHE, cache_key)
    if isinstance(cached, TextInputDocument):
        return cached

    text, encoding = read_text_file_with_fallback(source_path)
    normalized_text = _strip_start_text_after_leading_frontmatter(text)
    if parser_key == 'markdown':
        blocks = _blocks_from_markdown(normalized_text, source_path=source_path)
        format_label = 'Markdown'
        warnings = _find_markdown_support_warnings(normalized_text)
    else:
        blocks = _blocks_from_plain_text(normalized_text, source_path=source_path)
        format_label = 'テキスト'
        warnings = _find_plain_text_support_warnings(normalized_text)
    document = TextInputDocument(
        source_path=source_path,
        text=text,
        encoding=encoding,
        blocks=blocks,
        format_label=format_label,
        parser_key=parser_key,
        support_summary=TEXT_INPUT_SUPPORT_SUMMARY.get(parser_key, ''),
        warnings=warnings,
    )
    return cast(TextInputDocument, _store_cached_input_document(_TEXT_INPUT_DOCUMENT_CACHE, cache_key, document))


def _process_text_input_document(
    text_path: str | Path,
    font_path: str | Path,
    args: ConversionArgs,
    *,
    parser: str,
    output_path: str | Path | None = None,
    should_cancel: Callable[[], bool] | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Path:
    """TXT / Markdown 共通の読み込み・警告通知・描画入口処理。"""
    _refresh_core_globals()
    _raise_if_cancelled(should_cancel)
    document = load_text_input_document(text_path, parser=parser)
    if document.support_summary:
        LOGGER.info('%s 対応範囲: %s', document.format_label, document.support_summary)
    for warning in document.warnings or []:
        LOGGER.warning('%s 入力注意: %s', document.format_label, warning)
    _emit_progress(progress_cb, 0, 1, f'{document.format_label}ファイルを読み込みました。')
    render_text_blocks_to_xtc = globals().get('_render_text_blocks_to_xtc')
    if not callable(render_text_blocks_to_xtc):
        from tategakiXTC_gui_core_pages import _render_text_blocks_to_xtc as render_text_blocks_to_xtc
        globals()['_render_text_blocks_to_xtc'] = render_text_blocks_to_xtc
    return render_text_blocks_to_xtc(
        document.blocks,
        document.source_path,
        font_path,
        args,
        output_path=output_path,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )


def process_text_file(
    text_path: str | Path,
    font_path: str | Path,
    args: ConversionArgs,
    output_path: str | Path | None = None,
    should_cancel: Callable[[], bool] | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Path:
    """プレーンテキストを縦書き XTC へ変換する。

    青空文庫記法は一部対応として、ルビ（｜...《...》 / 漢字列《...》）、
    改ページ注記（［＃改ページ］など）、字下げ注記（［＃ここから２字下げ］など）、
    傍点注記・傍線注記（［＃「語」に傍点］［＃「語」に傍線］など）を解釈し、
    その他の注記は描画から除外する。
    """
    return _process_text_input_document(
        text_path,
        font_path,
        args,
        parser='plain',
        output_path=output_path,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )


def process_markdown_file(
    text_path: str | Path,
    font_path: str | Path,
    args: ConversionArgs,
    output_path: str | Path | None = None,
    should_cancel: Callable[[], bool] | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Path:
    """Markdown を簡易整形して縦書き XTC へ変換する。

    見出し・箇条書き・番号付きリストに加え、pipe table / 定義リスト / 脚注を簡易展開して描画する。
    本文中では青空文庫のルビ記法・改ページ注記・字下げ注記・傍点注記・傍線注記を一部解釈する。
    コードブロックとインラインコードは、可能なら等幅寄りフォントへ切り替えて描画する。
    """
    return _process_text_input_document(
        text_path,
        font_path,
        args,
        parser='markdown',
        output_path=output_path,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )

def _publish_core_reexports() -> None:
    """Replace circular-import placeholders in gui_core with real split symbols."""
    for _source_name, _core_name in _CORE_REEXPORT_ALIASES:
        _value = globals().get(_source_name, _SPLIT_IMPORT_PLACEHOLDER)
        if _value is _SPLIT_IMPORT_PLACEHOLDER:
            continue
        try:
            setattr(_core, _core_name, _value)
        except Exception:
            pass


_publish_core_reexports()

