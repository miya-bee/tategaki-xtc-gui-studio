"""
tategakiXTC_gui_core.py — 変換コア

EPUB / ZIP / CBZ / CBR / TXT / Markdown を縦書き XTC 形式へ変換するロジック。
GUI (tategakiXTC_gui_studio.py) から呼び出して使用します。
"""
from __future__ import annotations


import base64
import codecs
import hashlib
import logging
import io
import importlib
import ntpath
import os
import re
import shutil
import struct
import tempfile
import zipfile
import posixpath
import subprocess
from collections import OrderedDict
from functools import lru_cache
from dataclasses import dataclass, replace as dc_replace
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from typing import Any, BinaryIO, Callable, Iterable, Literal, Mapping, Sequence, TYPE_CHECKING, TypedDict, cast

try:
    from typing import NotRequired, Required, TypeAlias
except ImportError:
    try:
        from typing_extensions import NotRequired, Required, TypeAlias  # type: ignore
    except ImportError:
        class _TypingCompatMarker:
            """Fallback marker for Python 3.10 without typing_extensions."""

            def __class_getitem__(cls, item: object) -> object:
                return item

        class NotRequired(_TypingCompatMarker):
            pass

        class Required(_TypingCompatMarker):
            pass

        TypeAlias = Any

# Pillow の Image / ImageDraw / ImageFont / ImageOps は描画・変換実行時まで遅延読み込みする。
# localweb service / 設定 payload 系では Pillow 本体は不要であり、環境によっては
# PIL.Image の eager import だけでもテストプロセスの終了を妨げることがある。
class _LazyPillowModule:
    def __init__(self, module_name: str) -> None:
        self._module_name = module_name
        self._module: Any | None = None

    def _load(self) -> Any:
        if self._module is None:
            self._module = importlib.import_module(f'PIL.{self._module_name}')
        return self._module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)


if TYPE_CHECKING:
    from PIL import Image as Image  # pragma: no cover
    from PIL import ImageDraw as ImageDraw  # pragma: no cover
    from PIL import ImageFont as ImageFont  # pragma: no cover
    from PIL import ImageOps as ImageOps  # pragma: no cover
else:
    Image = _LazyPillowModule('Image')
    ImageDraw = _LazyPillowModule('ImageDraw')
    ImageFont = _LazyPillowModule('ImageFont')
    ImageOps = _LazyPillowModule('ImageOps')

# numpy は XTC / XTCH pack の高速化にだけ使う optional 依存。
# モジュール import 時に読み込むと、環境によっては BLAS 初期化などの副作用で
# localweb service / テストの import 終了を妨げることがあるため、変換時まで遅延する。
np = None  # type: ignore[assignment]
_NUMPY_IMPORT_ATTEMPTED = False


def _get_numpy_module() -> Any:
    global np, _NUMPY_IMPORT_ATTEMPTED
    if _NUMPY_IMPORT_ATTEMPTED:
        return np
    if np is not None:
        _NUMPY_IMPORT_ATTEMPTED = True
        return np
    _NUMPY_IMPORT_ATTEMPTED = True
    try:
        import numpy as numpy_module  # type: ignore
    except Exception:  # pragma: no cover - optional dependency
        np = None  # type: ignore[assignment]
    else:
        np = numpy_module  # type: ignore[assignment]
    return np


LOGGER_NAME = 'tategaki_xtc'
LOGGER = logging.getLogger(LOGGER_NAME)
LOGGER.addHandler(logging.NullHandler())


INPUT_DOCUMENT_CACHE_MAX = 8


__all__ = [
    "ConversionArgs",
    "ConversionCancelled",
    "get_font_list",
    "resolve_font_path",
    "parse_font_spec",
    "build_font_spec",
    "describe_font_value",
    "get_font_entries",
    "get_font_entries_for_value",
    "clear_font_entry_cache",
    "iter_conversion_targets",
    "should_skip_conversion_target",
    "get_output_path_for_target",
    "make_unique_output_path",
    "resolve_output_path_with_conflict",
    "find_output_conflicts",
    "get_missing_dependencies_for_suffixes",
    "list_optional_dependency_status",
    "generate_preview_base64",
    "clear_preview_bundle_cache",
    "process_archive",
    "process_epub",
    "process_text_file",
    "process_markdown_file",
    "SUPPORTED_INPUT_SUFFIXES",
    "ARCHIVE_INPUT_SUFFIXES",
    "TEXT_INPUT_SUFFIXES",
    "MARKDOWN_INPUT_SUFFIXES",
]

OPTIONAL_DEPENDENCIES = {
    'ebooklib': {
        'module': 'ebooklib',
        'package': 'ebooklib',
        'label': 'ebooklib',
        'purpose': 'EPUB変換',
        'impact': 'feature',
    },
    'beautifulsoup4': {
        'module': 'bs4',
        'package': 'beautifulsoup4',
        'label': 'beautifulsoup4',
        'purpose': 'EPUB変換',
        'impact': 'feature',
    },
    'patool': {
        'module': 'patoolib',
        'package': 'patool',
        'label': 'patool',
        'purpose': 'RAR / CBR 変換',
        'impact': 'feature',
    },
    'charset-normalizer': {
        'module': 'charset_normalizer',
        'package': 'charset-normalizer',
        'label': 'charset-normalizer',
        'purpose': 'TXT / Markdown の文字コード自動判定',
        'impact': 'feature',
    },
    'tqdm': {
        'module': 'tqdm',
        'package': 'tqdm',
        'label': 'tqdm',
        'purpose': 'コンソール進捗表示（未導入でも動作可）',
        'impact': 'convenience',
    },
    'numpy': {
        'module': 'numpy',
        'package': 'numpy',
        'label': 'numpy',
        'purpose': 'XTC / XTCH pack 高速化',
        'impact': 'performance',
    },
}


def _compact_error_text(value: object, max_len: int = 220) -> str:
    text = ' '.join(str(value or '').replace('　', ' ').split())
    if len(text) > max_len:
        return text[: max_len - 1] + '…'
    return text


def build_conversion_error_report(source_path: PathLike | None, exc: BaseException, stage: str = '') -> ConversionErrorReport:
    # 入力ごとの変換失敗をユーザー向けの説明文へ整形する。
    path = Path(source_path) if source_path else None
    suffix = (path.suffix.lower() if path else '')
    raw_detail = str(exc).strip() or exc.__class__.__name__
    stage = str(stage or '').strip()
    headline = '変換に失敗しました。'
    hint = 'ログもあわせて確認してください。'

    if 'pip install' in raw_detail or '必要です。' in raw_detail or '不足しています' in raw_detail:
        headline = '必要なライブラリが不足しているため変換できませんでした。'
        hint = 'requirements.txt を使って依存ライブラリを入れ直してください。'
    elif isinstance(exc, UnicodeDecodeError) or '文字コード' in raw_detail or "codec can't decode" in raw_detail:
        headline = 'テキストの文字コードを判定できませんでした。'
        hint = 'UTF-8 / UTF-8 BOM / CP932(Shift_JIS) などで保存し直すと改善する場合があります。'
    elif isinstance(exc, FileNotFoundError):
        headline = '入力ファイルを開けませんでした。'
        hint = 'ファイルが移動・削除されていないか確認してください。'
    elif suffix == '.epub':
        if '本文章が見つかりません' in raw_detail:
            headline = 'EPUB の本文が見つかりませんでした。'
            hint = '本文が spine に含まれている EPUB か確認してください。'
        elif 'pagebreak' in raw_detail.lower() or 'html' in raw_detail.lower() or '章' in stage:
            headline = 'EPUB の本文描画中に失敗しました。'
            hint = '該当章の HTML / CSS が特殊な可能性があります。問題の EPUB をログと一緒に確認してください。'
        else:
            headline = 'EPUB の読み込みまたは解析に失敗しました。'
            hint = 'EPUB が壊れていないか、DRM 付きでないか、必要ライブラリが入っているか確認してください。'
    elif suffix in {'.zip', '.cbz', '.rar', '.cbr'}:
        if '解凍' in raw_detail or 'extract' in raw_detail.lower():
            headline = 'アーカイブの展開に失敗しました。'
            hint = 'ZIP / CBZ / RAR / CBR が破損していないか、RAR 系では patool が導入済みか確認してください。'
        elif '画像ファイルが見つかりませんでした' in raw_detail or '変換対象の画像が見つかりませんでした' in raw_detail:
            headline = 'アーカイブ内に変換対象の画像が見つかりませんでした。'
            hint = f'対応画像は {", ".join(IMG_EXTS)} です。'
        else:
            headline = 'アーカイブ内画像の変換に失敗しました。'
            hint = f'対応画像は {", ".join(IMG_EXTS)} です。破損画像や未対応形式が混在していないか確認してください。'
    elif suffix in TEXTUAL_INPUT_SUFFIX_SET:
        if suffix in MARKDOWN_INPUT_SUFFIXES:
            headline = 'Markdown の読み込みまたは整形中に失敗しました。'
            hint = 'ログの「入力注意」に出ている非対応要素がないか確認してください。'
        else:
            headline = 'テキストファイルの読み込みまたは変換に失敗しました。'
            hint = '文字コードや改行コードが極端に特殊でないか確認してください。'

    lines = []
    if path:
        lines.append(f'対象: {path.name}')
    lines.append(f'内容: {headline}')
    if stage:
        lines.append(f'段階: {stage}')
    lines.append(f'詳細: {_compact_error_text(raw_detail)}')
    if hint:
        lines.append(f'確認: {hint}')
    return {
        'headline': headline,
        'detail': _compact_error_text(raw_detail),
        'hint': hint,
        'display': '\n'.join(lines),
    }

def _require_ebooklib_epub() -> Any:
    """ebooklib.epub を必要時に読み込む。"""
    try:
        from ebooklib import epub as epub_module
    except ImportError as e:
        raise RuntimeError(
            "EPUB変換には ebooklib が必要です。`pip install ebooklib` を実行してください。"
        ) from e
    return epub_module


def _require_patoolib() -> Any:
    """patoolib を必要時に読み込む。"""
    try:
        import patoolib as patoolib_module
    except ImportError as e:
        raise RuntimeError(
            "アーカイブ変換には patool が必要です。`pip install patool` を実行してください。"
        ) from e
    return patoolib_module




def _require_bs4_beautifulsoup() -> Any:
    """bs4.BeautifulSoup を必要時に読み込む。"""
    try:
        from bs4 import BeautifulSoup as bs4_BeautifulSoup
    except ImportError as e:
        raise RuntimeError(
            "EPUB変換には beautifulsoup4 が必要です。`pip install beautifulsoup4` を実行してください。"
        ) from e
    return bs4_BeautifulSoup


def _iter_with_optional_tqdm(iterable: Iterable[Any], **kwargs: object) -> Iterable[Any]:
    """tqdm があれば利用し、無ければ元の iterable を返す。

    unittest / CI / localweb service などの非対話実行では、tqdm の stderr 制御や
    内部 monitor thread が環境によってプロセス終了を遅らせることがある。
    そのため stderr が TTY でない場合は既定で素の iterable を返し、CLI で
    明示的に表示したい場合だけ ``TATEGAKI_XTC_FORCE_TQDM=1`` で有効化する。
    """
    force_tqdm = os.environ.get('TATEGAKI_XTC_FORCE_TQDM', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    if not force_tqdm:
        try:
            import sys
            if not sys.stderr.isatty():
                return iterable
        except Exception:
            return iterable
    try:
        from tqdm import tqdm as tqdm_func
    except ImportError:
        return iterable
    try:
        return tqdm_func(iterable, **kwargs)
    except Exception:
        return iterable


def _is_module_available(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def list_optional_dependency_status() -> list[DependencyStatus]:
    statuses: list[DependencyStatus] = []
    for key, info in OPTIONAL_DEPENDENCIES.items():
        statuses.append({
            'key': key,
            'label': info['label'],
            'package': info['package'],
            'purpose': info['purpose'],
            'impact': cast(DependencyImpact, info['impact']),
            'available': _is_module_available(info['module']),
        })
    return statuses


def get_missing_dependencies_for_suffixes(suffixes: Iterable[str]) -> list[MissingDependency]:
    required_keys: list[str] = []
    normalized = {str(s or '').strip().lower() for s in suffixes if str(s or '').strip()}
    if '.epub' in normalized:
        required_keys.extend(['ebooklib', 'beautifulsoup4'])
    if '.rar' in normalized or '.cbr' in normalized:
        required_keys.append('patool')

    missing: list[MissingDependency] = []
    seen = set()
    for key in required_keys:
        if key in seen:
            continue
        seen.add(key)
        info = OPTIONAL_DEPENDENCIES[key]
        if not _is_module_available(info['module']):
            missing.append({
                'key': key,
                'label': info['label'],
                'package': info['package'],
                'purpose': info['purpose'],
            })
    return missing


class ConversionCancelled(RuntimeError):
    """変換キャンセル時に内部で送出する例外。"""


def _raise_if_cancelled(should_cancel: Callable[[], bool] | None = None) -> None:
    if callable(should_cancel) and should_cancel():
        raise ConversionCancelled('変換を停止しました。')


def _emit_progress(progress_cb: ProgressCallback | None = None, current: int | float | str = 0, total: int | float | str = 1, message: object = '') -> None:
    """進捗通知コールバックを安全に呼び出す。"""
    if not callable(progress_cb):
        return
    try:
        total_int = max(1, int(total))
    except Exception:
        total_int = 1
    try:
        current_int = int(current)
    except Exception:
        current_int = 0
    current_int = max(0, min(current_int, total_int))
    try:
        progress_cb(current_int, total_int, str(message or ''))
    except Exception:
        LOGGER.debug('進捗通知に失敗しました。', exc_info=True)


def _try_decode_bytes(raw: bytes, encoding: str) -> tuple[str, str] | None:
    """指定エンコーディングでデコードを試み、成功時のみ (text, encoding) を返す。"""
    try:
        return raw.decode(encoding), encoding
    except UnicodeDecodeError:
        return None


def _guess_utf16_without_bom(raw: bytes) -> str | None:
    """BOM なし UTF-16 の可能性を簡易推定する。"""
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
    return None


def _detect_text_with_charset_normalizer(raw: bytes) -> tuple[str, str] | None:
    """charset-normalizer による日本語寄りの自動判定を行う。"""
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
    return detected_text, detected_encoding

def _natural_sort_key(path_like: Any) -> list[tuple[int, object]]:
    """パスを自然順で比較するキーを返す。数値部分は整数として扱う。"""
    value = str(path_like).replace('\\', '/')
    key: list[tuple[int, object]] = []
    for chunk in re.split(r'(\d+)', value):
        if not chunk:
            continue
        if chunk.isdigit():
            key.append((0, int(chunk)))
        else:
            key.append((1, chunk.casefold()))
    return key


OUTPUT_FLAT_SEPARATOR = '~~'


def _encode_output_name_part(value: object) -> str:
    text = str(value or '')
    return text.replace('_', '_u').replace('~', '_t').strip()


def _build_flat_output_stem_from_relative(relative_path: str | Path) -> str:
    relative = Path(relative_path)
    rel_parts = list(relative.parts)
    if rel_parts:
        rel_parts[-1] = Path(rel_parts[-1]).stem
    encoded_parts = [
        _encode_output_name_part(part)
        for part in rel_parts
        if str(part).strip() and str(part) not in {'.', ''}
    ]
    flat_stem = OUTPUT_FLAT_SEPARATOR.join(part for part in encoded_parts if part)
    if flat_stem:
        return flat_stem
    fallback = _encode_output_name_part(Path(relative.name).stem)
    return fallback or 'output'


def _build_fallback_output_stem(path: str | Path) -> str:
    path = Path(path)
    encoded_stem = _encode_output_name_part(path.stem) or 'output'
    try:
        digest_source = str(path.resolve())
    except Exception:
        digest_source = str(path)
    digest = hashlib.sha1(digest_source.encode('utf-8', errors='ignore')).hexdigest()[:8]
    return f'_outside_{encoded_stem}_{digest}'


# ==========================================
# --- 基本設定 & 定数 ---
# ==========================================

DEF_WIDTH, DEF_HEIGHT = 480, 800
PREVIEW_PAGE_LIMIT = 10
PREVIEW_BUNDLE_CACHE_MAX = 8
IMG_EXTS = ('.jpg', '.jpeg', '.png', '.webp')
EPUB_INPUT_SUFFIXES = ('.epub',)
ARCHIVE_INPUT_SUFFIXES = ('.zip', '.rar', '.cbz', '.cbr')
TEXT_INPUT_SUFFIXES = ('.txt',)
MARKDOWN_INPUT_SUFFIXES = ('.md', '.markdown')
TEXTUAL_INPUT_SUFFIXES = TEXT_INPUT_SUFFIXES + MARKDOWN_INPUT_SUFFIXES
TEXTUAL_INPUT_SUFFIX_SET = frozenset(TEXTUAL_INPUT_SUFFIXES)
SUPPORTED_INPUT_SUFFIXES = frozenset(EPUB_INPUT_SUFFIXES + ARCHIVE_INPUT_SUFFIXES + TEXT_INPUT_SUFFIXES + MARKDOWN_INPUT_SUFFIXES)

TATE_REPLACE = {
    # --- 括弧・句読点 ---
    "…": "︙", "‥": "︰", "⋯": "︙", "︙": "︙", "︰": "︰", "─": "丨", "―": "丨", "—": "丨", "‐": "丨", "-": "丨",
    "～": "≀", "〜": "≀", "〰": "≀",
    "「": "﹁", "」": "﹂", "『": "﹃", "』": "﹄",
    "（": "︵", "）": "︶", "(": "︵", ")": "︶",
    "【": "︻", "】": "︼", "〔": "︹", "〕": "︺",
    "［": "﹇", "］": "﹈", "[": "﹇", "]": "﹈",
    "｛": "︷", "｝": "︸", "{": "︷", "}": "︸",
    "〈": "︿", "〉": "﹀", "＜": "︿", "＞": "﹀", "<": "︿", ">": "﹀",
    "《": "︽", "》": "︾", "≪": "︽", "≫": "︾",
    "、": "︑", "。": "︒",
    # --- 数学記号 ---
    "＝": "‖", "=": "‖",
    "＋": "＋",
    "±": "∓",
    "×": "×",
    "÷": "÷",
    "≠": "⧘",
    "≒": "≓",
    "≡": "⦀",
    "∞": "∞",
    "：": "‥",
    "；": "；",
}

# 三点リーダ類は、フォントによって U+FE19（︙）等の縦組み字形が
# 横向きや豆腐に近い形で描かれることがあるため、フォント任せにせず
# アプリ側で縦方向の点列として描画する。
VERTICAL_DOT_LEADER_THREE_CHARS = frozenset({'…', '⋯', '︙'})
VERTICAL_DOT_LEADER_TWO_CHARS = frozenset({'‥', '︰'})
VERTICAL_DOT_LEADER_CHARS = VERTICAL_DOT_LEADER_THREE_CHARS | VERTICAL_DOT_LEADER_TWO_CHARS

KUTOTEN_OFFSET_X, KUTOTEN_OFFSET_Y = 18, -8
SMALL_KANA_CHARS = set("ぁぃぅぇぉっゃゅょゎゕゖァィゥェォッャュョヮヵヶ")
OPENING_BRACKET_CHARS = set("([｛{〔〈《≪「『【〖〘〝‘“｟（［｢＜<")
CLOSING_BRACKET_CHARS=set(")]}｝〕〉》≫」』】〙〗〟’”｠）］｣＞>")
TAIL_PUNCTUATION_CHARS = set("、。，．､｡！？!?:;：；…‥⋯︙︰")
PROLONGED_SOUND_MARK_CHARS = set("ー－ｰ")
ITERATION_MARK_CHARS = set("々ゝゞヽヾ〻")
LINE_END_CONTIN_CHARS = set("―─〜～〰・")
LINE_HEAD_FORBIDDEN_CHARS = (
    TAIL_PUNCTUATION_CHARS
    | CLOSING_BRACKET_CHARS
    | PROLONGED_SOUND_MARK_CHARS
    | SMALL_KANA_CHARS
    | LINE_END_CONTIN_CHARS
    | ITERATION_MARK_CHARS
)
LINE_END_FORBIDDEN_CHARS = OPENING_BRACKET_CHARS
DOUBLE_PUNCT_TOKENS = {"!!", "!?", "?!", "？？", "！！", "！？", "？！"}
HANGING_PUNCTUATION_CHARS = {"、", "。", "，", "．", "､", "｡"}
LOWERABLE_HANGING_CLOSING_BRACKET_CHARS = set(CLOSING_BRACKET_CHARS)
CONTINUOUS_PUNCTUATION_PAIRS = {
    "……", "‥‥",
    "――", "──", "ーー",
    "～～", "〜〜", "〰〰",
    "・・",
}
REPEATABLE_CONTINUOUS_PUNCT_CHARS = set("…‥⋯︙︰―─ー〜～〰・")
CLOSE_BRACKET_CHARS = set(CLOSING_BRACKET_CHARS)


PARAGRAPH_LIKE_TAGS = {
    "p", "div", "section", "article", "header",
    "blockquote", "li", "dd", "dt",
    "h1", "h2", "h3", "h4", "h5", "h6",
}
STRUCTURAL_TAGS = PARAGRAPH_LIKE_TAGS | {"body", "html"}
START_TEXT_RE = re.compile(r'^\s*(?:start(?:\s+|_)*text\b\s*[:：-]?\s*)+', re.IGNORECASE)
START_TEXT_ONLY_RE = re.compile(r'^\s*start(?:\s+|_)*text\b\s*[:：-]?\s*$', re.IGNORECASE)


def _strip_leading_start_text(value: str) -> str:
    text = str(value or '')
    while True:
        stripped = START_TEXT_RE.sub('', text, count=1)
        if stripped == text:
            return stripped
        text = stripped


def _is_start_text_only_line(value: object) -> bool:
    return bool(START_TEXT_ONLY_RE.fullmatch(str(value or '')))


def _is_frontmatter_like_text_line(value: object) -> bool:
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
    if not leading_nonblank:
        return True
    return 2 <= len(leading_nonblank) <= 5 and all(_is_frontmatter_like_text_line(prev) for prev in leading_nonblank)


def _strip_start_text_after_leading_frontmatter(text: str) -> str:
    """先頭付近のタイトル・著者・章見出しの後ろに残る start text 行を取り除く。"""
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


def _epub_node_is_effectively_empty(node: Any) -> bool:
    for child in getattr(node, 'contents', ()):
        if isinstance(child, str):
            if str(child).replace('\ufeff', '').strip():
                return False
            continue
        if getattr(child, 'name', '') in {'img', 'image', 'br', 'hr'}:
            return False
        if not _epub_node_is_effectively_empty(child):
            return False
    return True


def _prune_empty_epub_ancestors(node: Any, body: Any) -> None:
    current = node
    while current is not None and current is not body:
        parent = getattr(current, 'parent', None)
        if current is body or getattr(current, 'name', '') in {'body', 'html'}:
            return
        if not _epub_node_is_effectively_empty(current):
            return
        current.extract()
        current = parent


def _strip_leading_start_text_from_epub_body(body: Any) -> None:
    leading_nonblank: list[str] = []
    body_started = False

    for descendant in list(getattr(body, 'descendants', ())):
        if body_started:
            break
        if not isinstance(descendant, str):
            continue

        parent = getattr(descendant, 'parent', None)
        parent_name = str(getattr(parent, 'name', '') or '').lower()
        if parent_name in {'script', 'style', 'rt', 'rp'}:
            continue

        raw_text = str(descendant).replace('\ufeff', '').replace('\xa0', ' ')
        if not raw_text.strip():
            continue

        stripped_text = raw_text.strip()
        if _can_strip_start_text_after_frontmatter(leading_nonblank):
            normalized = _strip_leading_start_text(stripped_text).strip()
            if normalized != stripped_text:
                if normalized:
                    descendant.replace_with(raw_text.replace(stripped_text, normalized, 1))
                else:
                    descendant.extract()
                    if parent is not None:
                        _prune_empty_epub_ancestors(parent, body)
                continue

        leading_nonblank.append(stripped_text)
        if not _is_frontmatter_like_text_line(stripped_text) or len(leading_nonblank) > 5:
            body_started = True
AOZORA_NOTE_RE = re.compile(r'［＃([^］]+)］')
AOZORA_NOTE_ONLY_RE = re.compile(r'^\s*［＃([^］]+)］\s*$')
# 暗黙ルビは『漢字＋かな送り』のみを対象とし、英数字混在は誤認識を避けるため除外する。
AOZORA_IMPLICIT_RUBY_BASE_RE = re.compile(r'[一-龯々〆ヶ]+[ぁ-ゖゝゞァ-ヺー゛゜ヽヾヿ]*$')
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
    normalized = re.sub(r'\s+', '', str(note_text or ''))
    return normalized in {'改ページ', '改丁', '改見開き'}


def _parse_aozora_indent_note(note_text: object) -> AozoraNoteBlock | None:
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
    normalized = re.sub(r'\s+', '', str(kind_text or ''))
    if not normalized:
        return None
    return AOZORA_EMPHASIS_KIND_ALIASES.get(normalized)


def _parse_aozora_emphasis_note(note_text: object) -> AozoraNoteBlock | None:
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
    normalized = re.sub(r'\s+', '', str(kind_text or ''))
    if not normalized:
        return None
    return AOZORA_SIDE_LINE_KIND_ALIASES.get(normalized)


def _parse_aozora_side_line_note(note_text: object) -> AozoraNoteBlock | None:
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


def _parse_aozora_note_only_line(value: str | None) -> AozoraNoteBlock | None:
    match = AOZORA_NOTE_ONLY_RE.match(value or '')
    if not match:
        return None
    note_text = match.group(1).strip()
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
    if not value:
        return []

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


# ==========================================
# --- 変換引数データクラス ---
# ==========================================

@dataclass
class ConversionArgs:
    """変換処理に渡すパラメータをまとめたデータクラス。"""
    width: int = DEF_WIDTH
    height: int = DEF_HEIGHT
    font_size: int = 26
    ruby_size: int = 12
    line_spacing: int = 44
    margin_t: int = 12
    margin_b: int = 14
    margin_r: int = 12
    margin_l: int = 12
    dither: bool = False
    night_mode: bool = False
    threshold: int = 128
    kinsoku_mode: str = "standard"
    output_format: str = "xtc"

    def __post_init__(self: ConversionArgs) -> None:
        int_fields = (
            'width', 'height', 'font_size', 'ruby_size', 'line_spacing',
            'margin_t', 'margin_b', 'margin_r', 'margin_l', 'threshold',
        )
        for field_name in int_fields:
            value = int(getattr(self, field_name))
            setattr(self, field_name, value)
        if self.width <= 0 or self.height <= 0:
            raise ValueError('width / height は 1 以上である必要があります。')
        if self.font_size < 6:
            raise ValueError('font_size は 6 以上である必要があります。')
        if self.ruby_size < 4:
            raise ValueError('ruby_size は 4 以上である必要があります。')
        if self.line_spacing <= 0:
            raise ValueError('line_spacing は 1 以上である必要があります。')
        for margin_name in ('margin_t', 'margin_b', 'margin_r', 'margin_l'):
            if getattr(self, margin_name) < 0:
                raise ValueError(f'{margin_name} は 0 以上である必要があります。')
        self.threshold = min(255, max(0, self.threshold))
        self.kinsoku_mode = str(self.kinsoku_mode or 'standard')
        self.output_format = _normalize_output_format(getattr(self, 'output_format', 'xtc'))


@dataclass
class TextInputDocument:
    """TXT / Markdown 入力を正規化した中間表現。"""
    source_path: Path
    text: str
    encoding: str
    blocks: TextBlocks
    format_label: str
    parser_key: str = 'plain'
    support_summary: str = ''
    warnings: WarningList | None = None


@dataclass
class ArchiveInputDocument:
    """画像アーカイブ入力を正規化した中間表現。"""
    source_path: Path
    image_files: list[Path]
    traversal_skipped: int = 0
    extracted_member_count: int = 0
    trusted_temp_files: bool = False


@dataclass
class EpubInputDocument:
    """EPUB 入力の解析結果をまとめた中間表現。"""
    source_path: Path
    book: object
    docs: list[Any]
    image_map: EpubImageMap
    image_basename_map: EpubImageBasenameMap
    bold_rules: BoldRuleSets
    css_rules: list[CSSRule] | None = None


# ==========================================
# --- 型エイリアス / TypedDict ---
# ==========================================

PathLike: TypeAlias = str | Path


class TextRun(TypedDict):
    """本文描画で共通利用する run 情報。"""
    text: str
    ruby: str
    bold: bool
    italic: bool
    emphasis: str
    side_line: str
    code: bool


class SegmentInfo(TypedDict, total=False):
    """描画後のルビ・傍点・傍線重ね描画に使う配置情報。"""
    page_index: Required[int]
    x: Required[int]
    y: Required[int]
    base_len: NotRequired[int]
    cell_text: NotRequired[str]


class RubyOverlayGroup(TypedDict):
    """ルビ重ね描画用に圧縮したセグメント列情報。"""
    page_index: int
    x: int
    start_y: int
    end_y: int
    base_len: int


OverlayCell: TypeAlias = tuple[int, int, int, str]


class PageEntry(TypedDict):
    """1ページ分の画像と、そのページ専用設定を束ねる。"""
    image: Image.Image
    page_args: ConversionArgs | None
    label: str


Runs: TypeAlias = list[TextRun]
PageEntries: TypeAlias = list[PageEntry]
if TYPE_CHECKING:
    PageEntryLike: TypeAlias = PageEntry | Image.Image
else:
    PageEntryLike: TypeAlias = Any
WarningList: TypeAlias = list[str]
CSSDeclarations: TypeAlias = dict[str, str]
EpubImageMap: TypeAlias = dict[str, bytes]
EpubImageBasenameMap: TypeAlias = dict[str, list[tuple[str, bytes] | str]]
CancelCallback: TypeAlias = Callable[[], bool]
ProgressCallback: TypeAlias = Callable[[int, int, str], None]
PageCreatedCallback: TypeAlias = Callable[[PageEntry], None]
PageEntryMessageBuilder: TypeAlias = Callable[[int, int, PageEntryLike, str], str]
CompleteMessageBuilder: TypeAlias = Callable[[int, int, str | None], str]
SideLineGroup: TypeAlias = dict[str, Any]
SideLineSpan: TypeAlias = tuple[int, int, int, int]
PageBlobList: TypeAlias = list[bytes]


class VerticalLayoutHints(TypedDict):
    line_head_forbidden: tuple[bool, ...]
    line_end_forbidden: tuple[bool, ...]
    hanging_punctuation: tuple[bool, ...]
    continuous_pair_with_next: tuple[bool, ...]
    protected_group_len: tuple[int, ...]
    would_start_forbidden_after_hang_pair: tuple[bool, ...]


class ConversionErrorReport(TypedDict):
    """ユーザー表示用の変換失敗サマリ。"""
    headline: str
    detail: str
    hint: str
    display: str


DependencyImpact: TypeAlias = Literal['feature', 'performance', 'convenience']


class DependencyStatus(TypedDict):
    """任意依存ライブラリの状態。"""
    key: str
    label: str
    package: str
    purpose: str
    impact: DependencyImpact
    available: bool


class MissingDependency(TypedDict):
    """不足している任意依存ライブラリの情報。"""
    key: str
    label: str
    package: str
    purpose: str


class ConflictPlan(TypedDict, total=False):
    """出力ファイル衝突時の解決結果。"""
    desired_path: str
    final_path: str
    strategy: str
    conflict: bool
    renamed: bool
    overwritten: bool


class BoldRuleSets(TypedDict):
    """EPUB CSS から抽出した太字セレクタ集合。"""
    classes: set[str]
    ids: set[str]
    tags: set[str]


class CSSRule(TypedDict):
    """正規化済みの EPUB CSS ルール。"""
    selector: str
    declarations: CSSDeclarations


class EpubIndentProfile(TypedDict):
    """EPUB ノードごとの字下げ・見出しプロファイル。"""
    indent_chars: int
    wrap_indent_chars: int
    prefix: str
    prefix_bold: bool
    blank_before: int
    heading_level: int


class AozoraNoteBlock(TypedDict, total=False):
    """青空文庫注記の簡易表現。"""
    kind: str
    indent_chars: int
    wrap_indent_chars: int
    target_text: str
    emphasis: str
    side_line: str


class FontEntry(TypedDict):
    """フォント一覧 UI へ渡すフォント候補。"""
    label: str
    value: str
    path: str
    index: int


class FootnoteEntry(TypedDict):
    """Markdown 脚注の中間表現。"""
    id: str
    text: str


TextBlock: TypeAlias = dict[str, Any]
TextBlocks: TypeAlias = list[TextBlock]
LinkDefinitions: TypeAlias = dict[str, str]
FontEntries: TypeAlias = list[FontEntry]


# ==========================================
# --- グリフ描画ヘルパー ---
# ==========================================

@lru_cache(maxsize=64)
def _scaled_kutoten_offset(f_size: int) -> tuple[int, int]:
    off_x = max(1, int(round(f_size * 0.06)))
    off_y = -max(1, int(round(f_size * 0.10)))
    return off_x, off_y


@lru_cache(maxsize=64)
def _small_kana_offset(f_size: int) -> tuple[int, int]:
    off_x = max(1, int(round(f_size * 0.08)))
    off_y = -max(2, int(round(f_size * 0.12)))
    return off_x, off_y


@lru_cache(maxsize=64)
def _kagikakko_extra_y(original_char: str, f_size: int) -> int:
    if original_char in {'「', '『'}:
        # sweep317: sweep316 ではフォントによって開き鉤括弧が下寄りに
        # 見えるケースがあったため、下げ量を少し弱める。
        return max(1, int(round(f_size * 0.18)))
    if original_char in {'」', '』'}:
        # sweep341: 閉じ鉤括弧は一部フォントで水平画が下に沈むため、
        # 通常描画側も少し強めに上げる。ぶら下げ時の bbox 補正とは
        # 独立させ、通常位置の見え方だけを微調整する。
        return -max(1, int(round(f_size * 0.18)))
    return 0


@lru_cache(maxsize=512)
def _should_draw_emphasis_for_cell_cached(cell_text: str) -> bool:
    if not cell_text:
        return False
    return any((ch not in AOZORA_EMPHASIS_SKIP_CHARS) and (not ch.isspace()) for ch in cell_text)


@lru_cache(maxsize=512)
def _should_draw_side_line_for_cell_cached(cell_text: str) -> bool:
    if not cell_text:
        return False
    return any((ch not in AOZORA_SIDE_LINE_SKIP_CHARS) and (not ch.isspace()) for ch in cell_text)


@lru_cache(maxsize=64)
def _get_side_line_pattern(font_size: int, line_kind: str) -> tuple[int, int, int]:
    normalized = str(line_kind or 'solid')
    if normalized == 'wavy':
        amplitude = max(1, int(round(font_size * 0.06)))
        wavelength = max(4, int(round(font_size * 0.22)))
        return amplitude, wavelength, 0
    if normalized == 'dashed':
        segment = max(3, int(round(font_size * 0.18)))
        gap = max(2, int(round(font_size * 0.12)))
        return segment, gap, 0
    if normalized == 'chain':
        segment = max(5, int(round(font_size * 0.28)))
        gap = max(2, int(round(font_size * 0.10)))
        return segment, gap, 0
    return 0, 0, 0


@lru_cache(maxsize=128)
def _get_side_line_style(font_size: int, ruby_size: int, side_line_kind: str, has_ruby_text: bool, prefer_left: bool, has_emphasis_kind: bool) -> tuple[int, int, int, int, int]:
    right_padding = max(0, ruby_size + 2) if has_ruby_text and not prefer_left else 0
    left_padding = max(2, int(round(font_size * 0.20))) if prefer_left and has_emphasis_kind else 0
    base_gap = max(1, int(round(font_size * 0.08)))
    width = 2 if side_line_kind == 'thick' else 1
    offset = 2 if side_line_kind == 'double' else 0
    return right_padding, left_padding, base_gap, width, offset


def _clamp_int(value: int, lower: int, upper: int) -> int:
    if upper < lower:
        return lower
    return min(max(int(value), int(lower)), int(upper))


def _side_line_horizontal_extent(font_size: int, line_kind: str, width: int) -> int:
    half_width = max(0, int(width) // 2)
    if str(line_kind or '') == 'wavy':
        amplitude, _wavelength, _unused = _get_side_line_pattern(font_size, 'wavy')
        return max(0, int(amplitude) + half_width)
    return half_width


@lru_cache(maxsize=512)
def _classify_tate_draw_char(char: str) -> str:
    if not char:
        return 'default'
    if len(char) == 2:
        return 'double_punct'
    if char == '一':
        return 'ichi'
    if char in {'ー', '－'}:
        return 'long_vowel'
    if char in HORIZONTAL_BRACKET_ORIGINAL_CHARS:
        return 'horizontal_bracket'
    if char in {'、', '。', '，', '．', '､', '｡'}:
        return 'punctuation'
    if char in SMALL_KANA_CHARS:
        return 'small_kana'
    if len(char) == 1 and char.isascii() and (not char.isspace()) and char.isalnum():
        return 'ascii_center'
    return 'default'


def create_image_draw(image: Image.Image) -> Any:
    draw = ImageDraw.Draw(image)
    setattr(draw, '_tategaki_image', image)
    setattr(draw, '_tategaki_target_image', image)
    return draw


def _get_draw_target_image(draw: Any) -> Image.Image:
    image = getattr(draw, '_tategaki_target_image', None)
    if image is not None:
        return image
    image = getattr(draw, '_tategaki_image', None)
    if image is not None:
        try:
            setattr(draw, '_tategaki_target_image', image)
        except Exception:
            pass
        return image
    image = getattr(draw, '_image', None)
    if image is not None:
        try:
            setattr(draw, '_tategaki_target_image', image)
        except Exception:
            pass
        return image
    raise AttributeError('描画先の Image オブジェクトを取得できませんでした。')


def _paste_glyph_image(draw: Any, glyph_img: Image.Image, xy: tuple[int, int], mask: Image.Image | None = None) -> None:
    target_image = _get_draw_target_image(draw)
    target_image.paste(glyph_img, (int(xy[0]), int(xy[1])), mask)


_FONT_OBJECT_CACHE_UNSET = object()


def _get_font_object_cache(font: Any, cache_attr: str) -> dict[Any, Any] | None:
    cache = getattr(font, cache_attr, None)
    return cache if isinstance(cache, dict) else None


def _get_or_create_font_object_cache(font: Any, cache_attr: str) -> dict[Any, Any] | None:
    cache = _get_font_object_cache(font, cache_attr)
    if cache is not None:
        return cache
    try:
        cache = {}
        setattr(font, cache_attr, cache)
        return cache
    except Exception:
        return None


@lru_cache(maxsize=512)
def _cached_resolve_cacheable_font_spec(font_path_text: str, font_index: int, font_size: int) -> tuple[str, int, int] | None:
    if not font_path_text or font_size <= 0:
        return None
    font_spec = _cached_build_font_spec(font_path_text, font_index)
    resolved_path = _cached_resolve_font_path(font_spec)
    if not resolved_path:
        return None
    return resolved_path, int(font_index), int(font_size)


def _resolve_cacheable_font_spec(font: Any) -> tuple[str, int, int] | None:
    cached_value = getattr(font, '_tategaki_cacheable_spec', _FONT_OBJECT_CACHE_UNSET)
    if cached_value is not _FONT_OBJECT_CACHE_UNSET:
        return None if cached_value is False else cached_value

    font_path = getattr(font, 'path', None)
    font_index = int(getattr(font, 'index', 0) or 0)
    font_size = int(getattr(font, 'size', 0) or 0)
    resolved_spec: tuple[str, int, int] | None = None
    if font_path and font_size > 0 and isinstance(font_path, (str, os.PathLike)):
        resolved_spec = _cached_resolve_cacheable_font_spec(str(font_path), font_index, font_size)
    try:
        setattr(font, '_tategaki_cacheable_spec', resolved_spec if resolved_spec is not None else False)
    except Exception:
        pass
    return resolved_spec


@lru_cache(maxsize=4096)
def _cached_render_text_glyph_bundle(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool, rotate_degrees: int, canvas_size: int | None, is_italic: bool) -> tuple[Image.Image, Image.Image]:
    glyph_img = _cached_render_text_glyph_image(font_path, font_index, font_size, text, is_bold, rotate_degrees, canvas_size, is_italic)
    return glyph_img, ImageOps.invert(glyph_img)


def _glyph_render_cache_key(text: str, is_bold: bool, rotate_degrees: int, canvas_size: int | None, is_italic: bool) -> tuple[str, bool, int, int | None, bool]:
    return str(text), bool(is_bold), int(rotate_degrees), (None if canvas_size is None else int(canvas_size)), bool(is_italic)


def _render_text_glyph_and_mask_shared(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> tuple[Image.Image, Image.Image]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_render_text_glyph_bundle(
            font_path,
            font_index,
            font_size,
            text,
            is_bold,
            int(rotate_degrees),
            canvas_size,
            is_italic,
        )
    cache_key = _glyph_render_cache_key(text, is_bold, int(rotate_degrees), canvas_size, is_italic)
    bundle_cache = _get_font_object_cache(font, '_tategaki_glyph_bundle_cache')
    if bundle_cache is not None and cache_key in bundle_cache:
        return bundle_cache[cache_key]
    glyph_cache = _get_font_object_cache(font, '_tategaki_glyph_image_cache')
    glyph_img = glyph_cache.get(cache_key) if glyph_cache is not None else None
    if glyph_img is None:
        glyph_img = _build_text_glyph_image(text, font, is_bold=is_bold, rotate_degrees=rotate_degrees, canvas_size=canvas_size, is_italic=is_italic)
        glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_glyph_image_cache')
        if glyph_cache is not None:
            glyph_cache[cache_key] = glyph_img
    bundle = (glyph_img, ImageOps.invert(glyph_img))
    bundle_cache = _get_or_create_font_object_cache(font, '_tategaki_glyph_bundle_cache')
    if bundle_cache is not None:
        bundle_cache[cache_key] = bundle
    return bundle


def _render_text_glyph_and_mask(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> tuple[Image.Image, Image.Image]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        glyph_img, mask = _cached_render_text_glyph_bundle(
            font_path,
            font_index,
            font_size,
            text,
            is_bold,
            int(rotate_degrees),
            canvas_size,
            is_italic,
        )
        return glyph_img.copy(), mask.copy()
    glyph_img = _build_text_glyph_image(
        text,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=canvas_size,
        is_italic=is_italic,
    )
    return glyph_img, ImageOps.invert(glyph_img)


def draw_weighted_text(draw: Any, pos_tuple: tuple[int, int], text: str, font: Any, is_bold: bool = False, is_italic: bool = False) -> None:
    draw_kwargs = {"font": font, "fill": 0}
    x, y = pos_tuple
    if is_italic:
        glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(text, font, is_bold=is_bold, is_italic=True)
        _paste_glyph_image(draw, glyph_img, (int(x), int(y)), glyph_mask)
        return
    draw.text((x, y), text, **draw_kwargs)
    if is_bold:
        # 疑似ボールド: 横方向 +1px、縦方向 +1px を重ねて太りを自然に増やす。
        draw.text((x + 1, y), text, **draw_kwargs)
        draw.text((x, y + 1), text, **draw_kwargs)


@lru_cache(maxsize=1024)
def _glyph_canvas_layout(glyph_w: int, glyph_h: int, bbox_left: int, bbox_top: int,
                         stroke_width: int, canvas_size: int | None) -> tuple[int, int, int]:
    pad = max(4, int(stroke_width) + 2)
    side = int(canvas_size) if canvas_size else max(int(glyph_w), int(glyph_h)) + pad * 4
    draw_x = (side - int(glyph_w)) // 2 - int(bbox_left)
    draw_y = (side - int(glyph_h)) // 2 - int(bbox_top)
    return int(side), int(draw_x), int(draw_y)


_GLYPH_ITALIC_SHEAR_PERMILLE = -220


def _trim_glyph_image_to_ink(glyph_img: Image.Image) -> Image.Image:
    ink_bbox = ImageOps.invert(glyph_img).getbbox()
    return glyph_img.crop(ink_bbox) if ink_bbox else glyph_img


@lru_cache(maxsize=256)
def _italic_extra_width(glyph_h: int, shear_permille: int = _GLYPH_ITALIC_SHEAR_PERMILLE) -> int:
    shear = abs(float(shear_permille) / 1000.0)
    return int(shear * int(glyph_h)) + 4


@lru_cache(maxsize=256)
def _italic_transform_layout(glyph_w: int, glyph_h: int,
                             shear_permille: int = _GLYPH_ITALIC_SHEAR_PERMILLE) -> tuple[tuple[int, int], tuple[float, float, float, float, float, float]]:
    shear = float(shear_permille) / 1000.0
    extra_w = _italic_extra_width(glyph_h, shear_permille)
    offset_x = extra_w if shear < 0 else 0
    return (
        (int(glyph_w) + int(extra_w), int(glyph_h)),
        (1.0, float(shear), float(offset_x), 0.0, 1.0, 0.0),
    )


def _build_text_glyph_image(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> Image.Image:
    stroke_width = 1 if is_bold else 0
    bbox = _get_text_bbox(font, text, is_bold=is_bold)
    glyph_w, glyph_h = _get_text_bbox_dims(font, text, is_bold=is_bold)
    side, draw_x, draw_y = _glyph_canvas_layout(
        glyph_w, glyph_h, int(bbox[0]), int(bbox[1]), stroke_width, canvas_size
    )
    glyph_img = Image.new("L", (side, side), 255)
    glyph_draw = create_image_draw(glyph_img)
    draw_weighted_text(glyph_draw, (draw_x, draw_y), text, font, is_bold=is_bold)
    glyph_img = _trim_glyph_image_to_ink(glyph_img)
    if rotate_degrees:
        glyph_img = glyph_img.rotate(rotate_degrees, expand=True, fillcolor=255)
        glyph_img = _trim_glyph_image_to_ink(glyph_img)
    if is_italic:
        transform_size, affine_coeffs = _italic_transform_layout(glyph_img.width, glyph_img.height)
        transformed = glyph_img.transform(
            transform_size,
            Image.AFFINE,  # type: ignore[attr-defined]
            affine_coeffs,
            resample=Image.Resampling.BICUBIC,
            fillcolor=255,
        )
        glyph_img = _trim_glyph_image_to_ink(transformed)
    return glyph_img


@lru_cache(maxsize=4096)
def _cached_render_text_glyph_image(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool, rotate_degrees: int, canvas_size: int | None, is_italic: bool) -> Image.Image:
    font = load_truetype_font(build_font_spec(font_path, font_index), font_size)
    return _build_text_glyph_image(
        text,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=canvas_size,
        is_italic=is_italic,
    )


def _render_text_glyph_image_shared(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> Image.Image:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_render_text_glyph_image(
            font_path,
            font_index,
            font_size,
            text,
            is_bold,
            int(rotate_degrees),
            canvas_size,
            is_italic,
        )
    cache_key = _glyph_render_cache_key(text, is_bold, int(rotate_degrees), canvas_size, is_italic)
    glyph_cache = _get_font_object_cache(font, '_tategaki_glyph_image_cache')
    if glyph_cache is not None and cache_key in glyph_cache:
        return glyph_cache[cache_key]
    glyph_img = _build_text_glyph_image(text, font, is_bold=is_bold, rotate_degrees=rotate_degrees, canvas_size=canvas_size, is_italic=is_italic)
    glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_glyph_image_cache')
    if glyph_cache is not None:
        glyph_cache[cache_key] = glyph_img
    return glyph_img


def _render_text_glyph_image(text: str, font: Any, is_bold: bool = False, rotate_degrees: int = 0, canvas_size: int | None = None, is_italic: bool = False) -> Image.Image:
    return _render_text_glyph_image_shared(
        text,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=canvas_size,
        is_italic=is_italic,
    ).copy()


_VERTICAL_GLYPH_FALLBACK_SENTINELS = ('͸', '΀', '﷐', '󰀀')


def _glyph_image_signature(image: Image.Image) -> tuple[int, int, bytes]:
    normalized = image if image.mode == 'L' else image.convert('L')
    return normalized.width, normalized.height, normalized.tobytes()


@lru_cache(maxsize=2048)
def _cached_glyph_signature(font_path: str, font_index: int, font_size: int, text: str,
                            is_bold: bool, is_italic: bool) -> tuple[int, int, bytes]:
    glyph_img = _cached_render_text_glyph_image(
        font_path,
        font_index,
        font_size,
        text,
        bool(is_bold),
        0,
        None,
        bool(is_italic),
    )
    return _glyph_image_signature(glyph_img)


@lru_cache(maxsize=128)
def _missing_glyph_signatures(font_path: str, font_index: int, size: int, is_bold: bool, is_italic: bool) -> tuple[tuple[int, int, bytes], ...]:
    signatures: list[tuple[int, int, bytes]] = []
    for sentinel in _VERTICAL_GLYPH_FALLBACK_SENTINELS:
        try:
            signatures.append(_cached_glyph_signature(font_path, font_index, size, sentinel, is_bold, is_italic))
        except Exception:
            continue
    return tuple(signatures)


def _missing_glyph_signatures_for_font(font: Any, *, is_bold: bool = False, is_italic: bool = False) -> tuple[tuple[int, int, bytes], ...]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _missing_glyph_signatures(font_path, font_index, font_size, bool(is_bold), bool(is_italic))
    cache_key = (bool(is_bold), bool(is_italic))
    missing_cache = _get_font_object_cache(font, '_tategaki_missing_glyph_signatures_cache')
    if missing_cache is not None and cache_key in missing_cache:
        return missing_cache[cache_key]
    signatures: list[tuple[int, int, bytes]] = []
    for sentinel in _VERTICAL_GLYPH_FALLBACK_SENTINELS:
        try:
            signatures.append(
                _glyph_image_signature(
                    _render_text_glyph_image_shared(sentinel, font, is_bold=is_bold, is_italic=is_italic)
                )
            )
        except Exception:
            continue
    resolved = tuple(signatures)
    missing_cache = _get_or_create_font_object_cache(font, '_tategaki_missing_glyph_signatures_cache')
    if missing_cache is not None:
        missing_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=1024)
def _cached_font_has_distinct_glyph(font_path: str, font_index: int, font_size: int, char: str, is_bold: bool, is_italic: bool) -> bool:
    if not char:
        return False
    try:
        glyph_signature = _cached_glyph_signature(font_path, font_index, font_size, char, is_bold, is_italic)
    except Exception:
        return False
    missing_signatures = _missing_glyph_signatures(font_path, font_index, font_size, is_bold, is_italic)
    if not missing_signatures:
        return False
    return glyph_signature not in missing_signatures


def _font_has_distinct_glyph(font: Any, char: str, *, is_bold: bool = False, is_italic: bool = False) -> bool:
    if not char:
        return False
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_font_has_distinct_glyph(font_path, font_index, font_size, char, is_bold, is_italic)
    cache_key = (str(char), bool(is_bold), bool(is_italic))
    glyph_cache = _get_font_object_cache(font, '_tategaki_distinct_glyph_cache')
    if glyph_cache is not None and cache_key in glyph_cache:
        return bool(glyph_cache[cache_key])
    try:
        glyph_signature = _glyph_image_signature(
            _render_text_glyph_image_shared(char, font, is_bold=is_bold, is_italic=is_italic)
        )
        missing_signatures = _missing_glyph_signatures_for_font(font, is_bold=is_bold, is_italic=is_italic)
        result = bool(missing_signatures) and glyph_signature not in missing_signatures
    except Exception:
        result = False
    glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_distinct_glyph_cache')
    if glyph_cache is not None:
        glyph_cache[cache_key] = result
    return result


def _should_rotate_to_horizontal_from_glyph_image(glyph_img: Image.Image) -> bool:
    width, height = glyph_img.size
    if width <= 0 or height <= 0:
        return False
    return height > max(width + 1, int(round(width * 1.08)))


@lru_cache(maxsize=128)
def _cached_horizontal_rotation_decision(font_path: str, font_index: int, font_size: int, char: str, is_bold: bool, is_italic: bool) -> bool:
    try:
        glyph_img = _cached_render_text_glyph_image(
            font_path,
            font_index,
            font_size,
            char,
            bool(is_bold),
            0,
            None,
            bool(is_italic),
        )
    except Exception:
        return False
    return _should_rotate_to_horizontal_from_glyph_image(glyph_img)


def _should_rotate_to_horizontal(font: Any, char: str, *, is_bold: bool = False, is_italic: bool = False) -> bool:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_horizontal_rotation_decision(font_path, font_index, font_size, char, is_bold, is_italic)
    cache_key = (str(char), bool(is_bold), bool(is_italic))
    rotation_cache = _get_font_object_cache(font, '_tategaki_horizontal_rotation_cache')
    if rotation_cache is not None and cache_key in rotation_cache:
        return bool(rotation_cache[cache_key])
    try:
        glyph_img = _render_text_glyph_image_shared(char, font, is_bold=is_bold, is_italic=is_italic)
        result = _should_rotate_to_horizontal_from_glyph_image(glyph_img)
    except Exception:
        result = False
    rotation_cache = _get_or_create_font_object_cache(font, '_tategaki_horizontal_rotation_cache')
    if rotation_cache is not None:
        rotation_cache[cache_key] = result
    return result


HORIZONTAL_BRACKET_ORIGINAL_CHARS = frozenset({
    '「', '」', '『', '』', '【', '】', '〈', '〉', '［', '］', '[', ']',
    '≪', '≫', '《', '》', '〔', '〕', '（', '）', '(', ')', '｛', '｝', '{', '}',
    '＜', '＞', '<', '>',
})
HORIZONTAL_BRACKET_VERTICAL_FORMS = frozenset({
    '﹁', '﹂', '﹃', '﹄', '︻', '︼', '︹', '︺', '︵', '︶', '﹇', '﹈',
    '︷', '︸', '︿', '﹀', '︽', '︾',
})
HORIZONTAL_BRACKET_CHARS = HORIZONTAL_BRACKET_ORIGINAL_CHARS | HORIZONTAL_BRACKET_VERTICAL_FORMS


def _should_rotate_horizontal_bracket(font: Any, char: str, *, is_bold: bool = False, is_italic: bool = False) -> bool:
    if char not in HORIZONTAL_BRACKET_CHARS:
        return False
    if char in HORIZONTAL_BRACKET_VERTICAL_FORMS:
        return False
    # 括弧類はどのフォントでも横長に見える向きへ統一する。
    # 縦書き用の横長字形が使える場合は未回転、元字形しかない場合は縦長判定で右回転する。
    return _should_rotate_to_horizontal(font, char, is_bold=is_bold, is_italic=is_italic)


_VERTICAL_PUNCTUATION_CHARS = {'、', '。', '，', '．', '､', '｡'}


@lru_cache(maxsize=2048)
def _is_render_spacing_char(char: str) -> bool:
    if not char:
        return False
    char_text = str(char)
    if len(char_text) == 1:
        return char_text.isspace()
    return all(ch.isspace() for ch in char_text)


@lru_cache(maxsize=1024)
def _cached_resolve_vertical_glyph_char(font_path: str, font_index: int, font_size: int, original_char: str, is_bold: bool, is_italic: bool) -> str:
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    if mapped_char == original_char:
        return original_char
    if _cached_font_has_distinct_glyph(font_path, font_index, font_size, mapped_char, is_bold, is_italic):
        return mapped_char
    if _cached_font_has_distinct_glyph(font_path, font_index, font_size, original_char, is_bold, is_italic):
        return original_char
    return mapped_char


def _resolve_vertical_glyph_char(original_char: str, font: Any, *, is_bold: bool = False, is_italic: bool = False) -> str:
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    if mapped_char == original_char:
        return original_char
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
    cache_key = (str(original_char), bool(is_bold), bool(is_italic))
    glyph_cache = _get_font_object_cache(font, '_tategaki_vertical_glyph_char_cache')
    if glyph_cache is not None and cache_key in glyph_cache:
        return str(glyph_cache[cache_key])
    mapped_supported = _font_has_distinct_glyph(font, mapped_char, is_bold=is_bold, is_italic=is_italic)
    if mapped_supported:
        resolved_char = mapped_char
    else:
        original_supported = _font_has_distinct_glyph(font, original_char, is_bold=is_bold, is_italic=is_italic)
        resolved_char = original_char if original_supported else mapped_char
    glyph_cache = _get_or_create_font_object_cache(font, '_tategaki_vertical_glyph_char_cache')
    if glyph_cache is not None:
        glyph_cache[cache_key] = resolved_char
    return resolved_char


@lru_cache(maxsize=1024)
def _cached_tate_punctuation_draw(font_path: str, font_index: int, font_size: int, original_char: str, is_bold: bool, is_italic: bool) -> tuple[str, bool]:
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
    fallback_layout = resolved_char == original_char and mapped_char != original_char
    return resolved_char, fallback_layout


def _resolve_tate_punctuation_draw(original_char: str, font: Any, *, is_bold: bool = False, is_italic: bool = False) -> tuple[str, bool]:
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    if mapped_char == original_char:
        return original_char, False
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_tate_punctuation_draw(font_path, font_index, font_size, original_char, is_bold, is_italic)
    cache_key = (str(original_char), bool(is_bold), bool(is_italic))
    draw_cache = _get_font_object_cache(font, '_tategaki_punctuation_draw_cache')
    if draw_cache is not None and cache_key in draw_cache:
        return draw_cache[cache_key]
    resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    fallback_layout = resolved_char == original_char and mapped_char != original_char
    resolved = (resolved_char, fallback_layout)
    draw_cache = _get_or_create_font_object_cache(font, '_tategaki_punctuation_draw_cache')
    if draw_cache is not None:
        draw_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=1024)
def _cached_horizontal_bracket_draw(font_path: str, font_index: int, font_size: int, original_char: str, f_size: int, is_bold: bool, is_italic: bool) -> tuple[str, int, int, int]:
    resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
    rotate_degrees = 0
    if resolved_char in HORIZONTAL_BRACKET_ORIGINAL_CHARS:
        rotate_degrees = 270 if _cached_horizontal_rotation_decision(
            font_path,
            font_index,
            font_size,
            resolved_char,
            is_bold,
            is_italic,
        ) else 0
    extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
    extra_y = _kagikakko_extra_y(original_char, f_size)
    return resolved_char, rotate_degrees, extra_x, extra_y


def _resolve_horizontal_bracket_draw(original_char: str, font: Any, f_size: int, *, is_bold: bool = False, is_italic: bool = False) -> tuple[str, int, int, int]:
    # 括弧は、縦書き互換字形が使えないフォールバック時に元字形を回転描画する。
    # 通常運用では cacheable font 用の lru_cache を使って高速化する。
    # ただし、回帰テストや診断コードが _resolve_vertical_glyph_char /
    # _should_rotate_horizontal_bracket を差し替えている場合は、その差し替え結果を
    # 確実に反映するため、font object 側の浅いキャッシュ経路へフォールバックする。
    cacheable_spec = _resolve_cacheable_font_spec(font)
    helper_overridden = (
        getattr(_resolve_vertical_glyph_char, 'mock_calls', None) is not None
        or getattr(_should_rotate_horizontal_bracket, 'mock_calls', None) is not None
    )
    if cacheable_spec and not helper_overridden:
        font_path, font_index, font_size = cacheable_spec
        return _cached_horizontal_bracket_draw(
            font_path,
            font_index,
            font_size,
            original_char,
            f_size,
            bool(is_bold),
            bool(is_italic),
        )

    cache_key = (str(original_char), int(f_size), bool(is_bold), bool(is_italic))
    draw_cache = _get_font_object_cache(font, '_tategaki_horizontal_bracket_draw_cache')
    if draw_cache is not None and cache_key in draw_cache:
        return draw_cache[cache_key]
    resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    rotate_degrees = 270 if _should_rotate_horizontal_bracket(font, resolved_char, is_bold=is_bold, is_italic=is_italic) else 0
    extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
    extra_y = _kagikakko_extra_y(original_char, f_size)
    resolved = (resolved_char, rotate_degrees, extra_x, extra_y)
    draw_cache = _get_or_create_font_object_cache(font, '_tategaki_horizontal_bracket_draw_cache')
    if draw_cache is not None:
        draw_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=1024)
def _cached_default_tate_draw(font_path: str, font_index: int, font_size: int, original_char: str, is_bold: bool, is_italic: bool) -> str:
    return _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)


def _resolve_default_tate_draw(original_char: str, font: Any, *, is_bold: bool = False, is_italic: bool = False) -> str:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_default_tate_draw(font_path, font_index, font_size, original_char, is_bold, is_italic)
    cache_key = (str(original_char), bool(is_bold), bool(is_italic))
    draw_cache = _get_font_object_cache(font, '_tategaki_default_tate_draw_cache')
    if draw_cache is not None and cache_key in draw_cache:
        return str(draw_cache[cache_key])
    resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    draw_cache = _get_or_create_font_object_cache(font, '_tategaki_default_tate_draw_cache')
    if draw_cache is not None:
        draw_cache[cache_key] = resolved_char
    return resolved_char


@lru_cache(maxsize=4096)
def _cached_tate_draw_spec(
    font_path: str,
    font_index: int,
    font_size: int,
    original_char: str,
    f_size: int,
    draw_kind: str,
    is_bold: bool,
    is_italic: bool,
) -> tuple[str, str, int, int, int, int, int, bool]:
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    resolved_char = original_char
    rotate_degrees = 0
    extra_x = 0
    extra_y = 0
    off_x = 0
    off_y = 0
    fallback_layout = False

    if draw_kind == 'horizontal_bracket':
        resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
        if resolved_char in HORIZONTAL_BRACKET_ORIGINAL_CHARS:
            rotate_degrees = 270 if _cached_horizontal_rotation_decision(
                font_path,
                font_index,
                font_size,
                resolved_char,
                is_bold,
                is_italic,
            ) else 0
        extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
        extra_y = _kagikakko_extra_y(original_char, f_size)
    elif draw_kind == 'punctuation':
        resolved_char = _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
        fallback_layout = resolved_char == original_char and mapped_char != original_char
        if not fallback_layout:
            off_x, off_y = _scaled_kutoten_offset(f_size)
    elif draw_kind == 'small_kana':
        resolved_char = (
            _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
            if mapped_char != original_char
            else original_char
        )
        off_x, off_y = _small_kana_offset(f_size)
    elif draw_kind == 'default':
        resolved_char = (
            _cached_resolve_vertical_glyph_char(font_path, font_index, font_size, original_char, is_bold, is_italic)
            if mapped_char != original_char
            else original_char
        )
    return draw_kind, resolved_char, rotate_degrees, extra_x, extra_y, off_x, off_y, fallback_layout



def _compute_uncached_tate_draw_spec(
    original_char: str,
    font: Any,
    f_size: int,
    *,
    draw_kind: str | None = None,
    is_bold: bool = False,
    is_italic: bool = False,
) -> tuple[str, str, int, int, int, int, int, bool]:
    draw_kind = draw_kind or _classify_tate_draw_char(original_char)
    mapped_char = TATE_REPLACE.get(original_char, original_char)
    resolved_char = original_char
    rotate_degrees = 0
    extra_x = 0
    extra_y = 0
    off_x = 0
    off_y = 0
    fallback_layout = False

    if draw_kind == 'horizontal_bracket':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
        rotate_degrees = 270 if _should_rotate_horizontal_bracket(font, resolved_char, is_bold=is_bold, is_italic=is_italic) else 0
        extra_x = max(1, int(round(f_size * 0.08))) if original_char in {'「', '『'} else 0
        extra_y = _kagikakko_extra_y(original_char, f_size)
    elif draw_kind == 'punctuation':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
        fallback_layout = resolved_char == original_char and mapped_char != original_char
        if not fallback_layout:
            off_x, off_y = _scaled_kutoten_offset(f_size)
    elif draw_kind == 'small_kana':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic) if mapped_char != original_char else original_char
        off_x, off_y = _small_kana_offset(f_size)
    elif draw_kind == 'default':
        resolved_char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic) if mapped_char != original_char else original_char
    return draw_kind, resolved_char, rotate_degrees, extra_x, extra_y, off_x, off_y, fallback_layout


def _compute_tate_draw_spec(
    original_char: str,
    font: Any,
    f_size: int,
    *,
    draw_kind: str | None = None,
    is_bold: bool = False,
    is_italic: bool = False,
) -> tuple[str, str, int, int, int, int, int, bool]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_tate_draw_spec(font_path, font_index, font_size, original_char, int(f_size), draw_kind or _classify_tate_draw_char(original_char), is_bold, is_italic)

    return _compute_uncached_tate_draw_spec(
        original_char,
        font,
        f_size,
        draw_kind=draw_kind,
        is_bold=is_bold,
        is_italic=is_italic,
    )


def _compute_reference_glyph_center(font: Any, *, is_bold: bool = False, f_size: int | None = None) -> float:
    refs = ("口", "田", "国", "漢", "あ", "ア", "亜")
    centers = []
    for ref in refs:
        bbox = _get_text_bbox(font, ref, is_bold=is_bold)
        if bbox and bbox[3] > bbox[1]:
            centers.append((bbox[1] + bbox[3]) / 2.0)
    if centers:
        return sum(centers) / len(centers)
    return (f_size / 2.0) if f_size else 0.0


@lru_cache(maxsize=128)
def _cached_reference_glyph_center(font_path: str, font_index: int, font_size: int, is_bold: bool) -> float:
    font = load_truetype_font(build_font_spec(font_path, font_index), font_size)
    return _compute_reference_glyph_center(font, is_bold=is_bold, f_size=font_size)


@lru_cache(maxsize=64)
def _get_reference_glyph_center(font: Any, is_bold: bool = False, f_size: int | None = None) -> float:
    """通常の全角文字が流し込み時に占める"見た目の中心"を推定する。"""
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_reference_glyph_center(font_path, font_index, font_size, bool(is_bold))
    cache_key = (bool(is_bold), int(f_size or 0))
    center_cache = _get_font_object_cache(font, '_tategaki_reference_center_cache')
    if center_cache is not None and cache_key in center_cache:
        return float(center_cache[cache_key])
    center = _compute_reference_glyph_center(font, is_bold=is_bold, f_size=f_size)
    center_cache = _get_or_create_font_object_cache(font, '_tategaki_reference_center_cache')
    if center_cache is not None:
        center_cache[cache_key] = float(center)
    return center


def _make_font_variant(font: Any, size: int) -> Any:
    size = int(size)
    variant_cache = getattr(font, '_tategaki_variant_cache', None)
    if isinstance(variant_cache, dict) and size in variant_cache:
        return variant_cache[size]

    variant_font: Any = font
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, _font_size = cacheable_spec
        variant_font = load_truetype_font(build_font_spec(font_path, font_index), size)
    else:
        used_font_variant = False
        if hasattr(font, "font_variant"):
            try:
                variant_font = font.font_variant(size=size)
                used_font_variant = True
            except TypeError:
                variant_font = font
        if not used_font_variant:
            font_path = getattr(font, 'path', None)
            font_index = getattr(font, 'index', 0)
            if font_path and isinstance(font_path, (str, os.PathLike)):
                variant_font = load_truetype_font(build_font_spec(font_path, int(font_index or 0)), size)

    try:
        if not isinstance(variant_cache, dict):
            variant_cache = {}
            setattr(font, '_tategaki_variant_cache', variant_cache)
        variant_cache[size] = variant_font
    except Exception:
        pass
    return variant_font


@lru_cache(maxsize=512)
def _centered_glyph_direct_offsets(f_size: int, glyph_w: int, glyph_h: int, bbox_left: int, bbox_top: int,
                                   align_to_text_flow: bool, target_center_y_q16: int, extra_x: int, extra_y: int) -> tuple[int, int]:
    offset_x = max(0, (f_size - glyph_w) // 2) - bbox_left + int(extra_x)
    if align_to_text_flow:
        target_center_y = target_center_y_q16 / 16.0
        glyph_center_y = bbox_top + (glyph_h / 2.0)
        offset_y = int(round(target_center_y - glyph_center_y))
    else:
        offset_y = max(0, (f_size - glyph_h) // 2) - bbox_top
    offset_y += int(extra_y)
    return int(offset_x), int(offset_y)


@lru_cache(maxsize=512)
def _centered_glyph_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                  align_to_text_flow: bool, target_center_y_q16: int,
                                  extra_x: int, extra_y: int) -> tuple[int, int]:
    offset_x = max(0, (f_size - glyph_w) // 2) + int(extra_x)
    if align_to_text_flow:
        target_center_y = target_center_y_q16 / 16.0
        offset_y = int(round(target_center_y - (glyph_h / 2.0)))
    else:
        offset_y = max(0, (f_size - glyph_h) // 2)
    offset_y += int(extra_y)
    return int(offset_x), int(offset_y)


def draw_centered_glyph(
    draw: Any,
    char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    is_bold: bool = False,
    rotate_degrees: int = 0,
    align_to_text_flow: bool = False,
    is_italic: bool = False,
    extra_x: int = 0,
    extra_y: int = 0,
) -> None:
    """
    Draw a single glyph centred within a square cell of size ``f_size``.

    This helper attempts to fast‑path the common case (no rotation/italic) by
    computing glyph bounding boxes and offsets directly rather than
    rendering an image for the glyph. When rotation or italics are
    requested, it falls back to rendering the glyph onto an image and
    pasting it.

    Parameters are intentionally kept simple and all optional flags are
    annotated to encourage the Python interpreter to avoid implicit
    conversions. Additional keyword arguments default to sensible values.
    """
    curr_x, curr_y = pos_tuple
    # Compute the target centre for aligning to the text flow only once.
    if align_to_text_flow:
        # Convert the floating centre into a fixed‑point integer scaled by 16.
        target_center_y_q16 = int(round(_get_reference_glyph_center(font, is_bold=is_bold, f_size=f_size) * 16.0))
    else:
        target_center_y_q16 = 0

    # Fast path: no rotation and no italic styling.
    if not rotate_degrees and not is_italic:
        # Resolve the glyph bounding box.  Using the cached helper avoids
        # allocating a new tuple on every call.
        bbox_left, bbox_top, bbox_right, bbox_bottom = _get_text_bbox(font, char, is_bold=is_bold)
        # Compute glyph width/height from the bbox.  Ensure they are at least 1px
        # tall/wide to avoid divide by zero in offset calculations.
        glyph_w = max(1, bbox_right - bbox_left)
        glyph_h = max(1, bbox_bottom - bbox_top)
        # Compute the centred offsets using the direct offset helper.  Pass
        # integers directly; the helper handles any further conversion.
        off_x, off_y = _centered_glyph_direct_offsets(
            f_size,
            glyph_w,
            glyph_h,
            bbox_left,
            bbox_top,
            align_to_text_flow,
            target_center_y_q16,
            extra_x,
            extra_y,
        )
        # Draw the glyph directly using the weighted text helper.  The italic
        # flag is always False in the fast path.
        draw_weighted_text(
            draw,
            (curr_x + off_x, curr_y + off_y),
            char,
            font,
            is_bold=is_bold,
            is_italic=False,
        )
        return

    # Slow path: either rotated or italic.  Render an image for the glyph.
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(
        char,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=f_size * 4,
        is_italic=is_italic,
    )
    gw, gh = glyph_img.size
    # Compute offsets for the rendered glyph.  Use the image‑based offset
    # helper since we cannot rely on the bounding box being relative to the
    # origin in the rotated/italic case.
    off_x, off_y = _centered_glyph_image_offsets(
        f_size,
        gw,
        gh,
        align_to_text_flow,
        target_center_y_q16,
        extra_x,
        extra_y,
    )
    # Paste the rendered glyph onto the draw target.
    _paste_glyph_image(
        draw,
        glyph_img,
        (curr_x + off_x, curr_y + off_y),
        glyph_mask,
    )


@lru_cache(maxsize=512)
def _ink_centered_glyph_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                      extra_x: int, extra_y: int) -> tuple[int, int]:
    """実インク画像をセルの幾何中央へ置くためのオフセット。"""
    offset_x = int(round((int(f_size) - int(glyph_w)) / 2.0)) + int(extra_x)
    offset_y = int(round((int(f_size) - int(glyph_h)) / 2.0)) + int(extra_y)
    return int(offset_x), int(offset_y)


@lru_cache(maxsize=512)
def _ink_flow_centered_glyph_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                           target_center_y_q16: int,
                                           extra_x: int, extra_y: int) -> tuple[int, int]:
    """実インク画像の中心を本文の見た目中心へ合わせるためのオフセット。"""
    offset_x = int(round((int(f_size) - int(glyph_w)) / 2.0)) + int(extra_x)
    target_center_y = float(target_center_y_q16) / 16.0
    offset_y = int(round(target_center_y - (int(glyph_h) / 2.0))) + int(extra_y)
    return int(offset_x), int(offset_y)


def _get_ichi_visual_target_center_y(font: Any, is_bold: bool = False, f_size: int | None = None) -> float:
    """漢数字「一」の実インクを合わせる縦方向の見た目中心を返す。

    通常漢字の bbox 中心を基準にする。ただし、フォントや Pillow 版によって
    参照中心がセル幾何中央付近へ倒れすぎる場合は、縦書き本文の見え方に
    合うようセル下寄りの安全下限を使う。
    """
    size = max(1, int(f_size or getattr(font, 'size', 0) or 1))
    try:
        target = float(_get_reference_glyph_center(font, is_bold=is_bold, f_size=size))
    except Exception:
        target = 0.0
    lower = size * 0.62
    upper = size * 0.82
    if target <= 0:
        target = lower
    return max(lower, min(target, upper))


def draw_ink_centered_glyph(
    draw: Any,
    char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    is_bold: bool = False,
    rotate_degrees: int = 0,
    align_to_text_flow: bool = False,
    is_italic: bool = False,
    extra_x: int = 0,
    extra_y: int = 0,
) -> None:
    """実インクbbox基準でグリフを描画する。

    align_to_text_flow=True の場合は、実インク中心を通常漢字の見た目中心へ
    合わせる。これにより、縦書き本文中の漢数字「一」がセル上側に
    残って見えるフォント差を抑える。
    """
    curr_x, curr_y = pos_tuple
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(
        char,
        font,
        is_bold=is_bold,
        rotate_degrees=rotate_degrees,
        canvas_size=f_size * 4,
        is_italic=is_italic,
    )
    gw, gh = glyph_img.size
    if align_to_text_flow:
        target_center_y_q16 = int(round(_get_ichi_visual_target_center_y(font, is_bold=is_bold, f_size=f_size) * 16.0))
        off_x, off_y = _ink_flow_centered_glyph_image_offsets(
            f_size, gw, gh, target_center_y_q16, extra_x, extra_y
        )
    else:
        off_x, off_y = _ink_centered_glyph_image_offsets(f_size, gw, gh, extra_x, extra_y)
    _paste_glyph_image(draw, glyph_img, (curr_x + off_x, curr_y + off_y), glyph_mask)


@lru_cache(maxsize=4096)
def _is_tatechuyoko_token(token: str) -> bool:
    if not token or len(token) < 2 or len(token) > 4:
        return False
    if not token.isascii() or not token.isalnum():
        return False
    if len(token) == 2:
        return True
    if len(token) == 3:
        return True
    return token.isdigit()


@lru_cache(maxsize=16)
def _tatechuyoko_layout_limits(f_size: int, text_len: int) -> tuple[int, int, int]:
    max_w = max(1, int(round(f_size * 0.92)))
    max_h = max(1, int(round(f_size * 0.58)))
    start_ratio = {2: 0.78, 3: 0.62, 4: 0.52}.get(int(text_len), 0.72)
    start_size = max(6, int(round(f_size * start_ratio)))
    return max_w, max_h, start_size


@lru_cache(maxsize=4096)
def _cached_text_bbox(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool) -> tuple[int, int, int, int]:
    font = load_truetype_font(build_font_spec(font_path, font_index), font_size)
    stroke_width = 1 if is_bold else 0
    return _normalize_text_bbox_result(_call_font_getbbox(font, text, stroke_width))


@lru_cache(maxsize=4096)
def _cached_text_bbox_dims(font_path: str, font_index: int, font_size: int, text: str, is_bold: bool) -> tuple[int, int]:
    bbox = _cached_text_bbox(font_path, font_index, font_size, text, bool(is_bold))
    return max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])


def _normalize_text_bbox_result(bbox: Any) -> tuple[int, int, int, int]:
    if not bbox:
        return 0, 0, 1, 1
    try:
        x0, y0, x1, y1 = bbox[:4]
    except Exception:
        return 0, 0, 1, 1
    try:
        x0_i, y0_i, x1_i, y1_i = int(x0), int(y0), int(x1), int(y1)
    except (TypeError, ValueError, OverflowError):
        return 0, 0, 1, 1
    if x1_i <= x0_i:
        x1_i = x0_i + 1
    if y1_i <= y0_i:
        y1_i = y0_i + 1
    return x0_i, y0_i, x1_i, y1_i


def _call_font_getbbox(font: Any, text: str, stroke_width: int) -> Any:
    getbbox = getattr(font, 'getbbox', None)
    if getbbox is None:
        return None
    try:
        return getbbox(text, stroke_width=stroke_width)
    except TypeError:
        try:
            return getbbox(text)
        except (AttributeError, OSError, TypeError, ValueError):
            return None
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def _get_text_bbox(font: Any, text: str, is_bold: bool = False) -> tuple[int, int, int, int]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_text_bbox(font_path, font_index, font_size, text, bool(is_bold))
    cache_key = (str(text), bool(is_bold))
    bbox_cache = _get_font_object_cache(font, '_tategaki_text_bbox_cache')
    if bbox_cache is not None and cache_key in bbox_cache:
        return bbox_cache[cache_key]
    stroke_width = 1 if is_bold else 0
    normalized_bbox = _normalize_text_bbox_result(_call_font_getbbox(font, text, stroke_width))
    bbox_cache = _get_or_create_font_object_cache(font, '_tategaki_text_bbox_cache')
    if bbox_cache is not None:
        bbox_cache[cache_key] = normalized_bbox
    return normalized_bbox


def _get_text_bbox_dims(font: Any, text: str, is_bold: bool = False) -> tuple[int, int]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_text_bbox_dims(font_path, font_index, font_size, text, bool(is_bold))
    cache_key = (str(text), bool(is_bold))
    dims_cache = _get_font_object_cache(font, '_tategaki_text_bbox_dims_cache')
    if dims_cache is not None and cache_key in dims_cache:
        cached = dims_cache[cache_key]
        return int(cached[0]), int(cached[1])
    bbox = _get_text_bbox(font, text, is_bold=is_bold)
    resolved = (max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1]))
    dims_cache = _get_or_create_font_object_cache(font, '_tategaki_text_bbox_dims_cache')
    if dims_cache is not None:
        dims_cache[cache_key] = resolved
    return resolved


@lru_cache(maxsize=2048)
def _cached_tatechuyoko_candidate_dims(font_path: str, font_index: int, font_size: int, text: str,
                                       is_bold: bool, is_italic: bool) -> tuple[int, int]:
    glyph_w, glyph_h = _cached_text_bbox_dims(font_path, font_index, font_size, text, bool(is_bold))
    if is_italic:
        glyph_w += _italic_extra_width(glyph_h)
    return glyph_w, glyph_h


def _estimate_tatechuyoko_candidate_dims(font: Any, text: str, is_bold: bool = False, is_italic: bool = False) -> tuple[int, int]:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, font_size = cacheable_spec
        return _cached_tatechuyoko_candidate_dims(font_path, font_index, font_size, text, bool(is_bold), bool(is_italic))
    cache_key = (str(text), bool(is_bold), bool(is_italic))
    dims_cache = _get_font_object_cache(font, '_tategaki_tatechuyoko_candidate_dims_cache')
    if dims_cache is not None and cache_key in dims_cache:
        cached = dims_cache[cache_key]
        return int(cached[0]), int(cached[1])
    glyph_w, glyph_h = _get_text_bbox_dims(font, text, is_bold=is_bold)
    if is_italic:
        glyph_w += _italic_extra_width(glyph_h)
    resolved = (glyph_w, glyph_h)
    dims_cache = _get_or_create_font_object_cache(font, '_tategaki_tatechuyoko_candidate_dims_cache')
    if dims_cache is not None:
        dims_cache[cache_key] = resolved
    return resolved


def _finalize_tatechuyoko_fit_size(resolved_size: int | None, start_size: int) -> int:
    # When no candidate size fits, keep the logical base size and let the bundle
    # builder clamp the rendered glyph image to the target cell bounds.
    return int(start_size if resolved_size is None else resolved_size)


@lru_cache(maxsize=1024)
def _cached_tatechuyoko_fit_size(font_path: str, font_index: int, f_size: int, text: str, is_bold: bool, is_italic: bool) -> int:
    max_w, max_h, start_size = _tatechuyoko_layout_limits(f_size, len(text))
    resolved_size: int | None = None
    for size in range(start_size, 5, -1):
        cand_w, cand_h = _cached_tatechuyoko_candidate_dims(font_path, font_index, size, text, is_bold, is_italic)
        if cand_w <= max_w and cand_h <= max_h:
            resolved_size = size
            break
    return _finalize_tatechuyoko_fit_size(resolved_size, start_size)


def _resolve_tatechuyoko_fit_size(font: Any, f_size: int, text: str, *, is_bold: bool = False, is_italic: bool = False) -> int:
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, _font_size = cacheable_spec
        return _cached_tatechuyoko_fit_size(font_path, font_index, int(f_size), str(text), bool(is_bold), bool(is_italic))
    cache_key = (int(f_size), str(text), bool(is_bold), bool(is_italic))
    fit_cache = _get_font_object_cache(font, '_tategaki_tatechuyoko_fit_size_cache')
    if fit_cache is not None and cache_key in fit_cache:
        return int(fit_cache[cache_key])
    max_w, max_h, start_size = _tatechuyoko_layout_limits(f_size, len(text))
    resolved_size: int | None = None
    for size in range(start_size, 5, -1):
        sub_font = _make_font_variant(font, size)
        cand_w, cand_h = _estimate_tatechuyoko_candidate_dims(sub_font, text, is_bold=is_bold, is_italic=is_italic)
        if cand_w <= max_w and cand_h <= max_h:
            resolved_size = size
            break
        if sub_font is font:
            break
    finalized_size = _finalize_tatechuyoko_fit_size(resolved_size, start_size)
    fit_cache = _get_or_create_font_object_cache(font, '_tategaki_tatechuyoko_fit_size_cache')
    if fit_cache is not None:
        fit_cache[cache_key] = int(finalized_size)
    return int(finalized_size)


@lru_cache(maxsize=1024)
def _cached_tatechuyoko_bundle(font_path: str, font_index: int, f_size: int, text: str, is_bold: bool, is_italic: bool) -> tuple[Image.Image, Image.Image]:
    max_w, max_h, _start_size = _tatechuyoko_layout_limits(f_size, len(text))
    fit_size = _cached_tatechuyoko_fit_size(font_path, font_index, f_size, text, bool(is_bold), bool(is_italic))
    render_font = load_truetype_font(build_font_spec(font_path, font_index), fit_size)
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(text, render_font, is_bold=is_bold, is_italic=is_italic)
    if glyph_img.width > max_w or glyph_img.height > max_h:
        scale = min(max_w / glyph_img.width, max_h / glyph_img.height)
        resized = (
            max(1, int(round(glyph_img.width * scale))),
            max(1, int(round(glyph_img.height * scale))),
        )
        glyph_img = glyph_img.resize(resized, Image.Resampling.LANCZOS)
        glyph_mask = glyph_mask.resize(resized, Image.Resampling.LANCZOS)
    return glyph_img, glyph_mask


def _build_tatechuyoko_bundle(font: Any, text: str, f_size: int, *, is_bold: bool = False, is_italic: bool = False) -> tuple[Image.Image, Image.Image]:
    cache_key = (str(text), int(f_size), bool(is_bold), bool(is_italic))
    bundle_cache = _get_font_object_cache(font, '_tategaki_tatechuyoko_bundle_cache')
    if bundle_cache is not None and cache_key in bundle_cache:
        return bundle_cache[cache_key]
    max_w, max_h, _start_size = _tatechuyoko_layout_limits(f_size, len(text))
    fit_size = _resolve_tatechuyoko_fit_size(font, f_size, text, is_bold=is_bold, is_italic=is_italic)
    chosen_font = _make_font_variant(font, fit_size)
    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(text, chosen_font, is_bold=is_bold, is_italic=is_italic)
    if glyph_img.width > max_w or glyph_img.height > max_h:
        scale = min(max_w / glyph_img.width, max_h / glyph_img.height)
        resized = (
            max(1, int(round(glyph_img.width * scale))),
            max(1, int(round(glyph_img.height * scale))),
        )
        glyph_img = glyph_img.resize(resized, Image.Resampling.LANCZOS)
        glyph_mask = glyph_mask.resize(resized, Image.Resampling.LANCZOS)
    bundle = (glyph_img, glyph_mask)
    bundle_cache = _get_or_create_font_object_cache(font, '_tategaki_tatechuyoko_bundle_cache')
    if bundle_cache is not None:
        bundle_cache[cache_key] = bundle
    return bundle


@lru_cache(maxsize=512)
def _tatechuyoko_paste_offsets(f_size: int, glyph_w: int, glyph_h: int) -> tuple[int, int]:
    return max(0, (int(f_size) - int(glyph_w)) // 2), max(0, (int(f_size) - int(glyph_h)) // 2)


def draw_tatechuyoko(draw: Any, text: str, pos_tuple: tuple[int, int], font: Any, f_size: int, is_bold: bool = False, is_italic: bool = False) -> None:
    curr_x, curr_y = pos_tuple
    cacheable_spec = _resolve_cacheable_font_spec(font)
    if cacheable_spec:
        font_path, font_index, _font_size = cacheable_spec
        glyph_img, glyph_mask = _cached_tatechuyoko_bundle(font_path, font_index, f_size, text, bool(is_bold), bool(is_italic))
    else:
        glyph_img, glyph_mask = _build_tatechuyoko_bundle(font, text, f_size, is_bold=is_bold, is_italic=is_italic)
    gw, gh = glyph_img.size
    off_x, off_y = _tatechuyoko_paste_offsets(f_size, gw, gh)
    _paste_glyph_image(draw, glyph_img, (curr_x + off_x, curr_y + off_y), glyph_mask)


def _should_center_ascii_glyph(char: str) -> bool:
    return _classify_tate_draw_char(char) == 'ascii_center'


def _tokenize_vertical_text_impl(text: str) -> list[str]:
    tokens: list[str] = []
    i = 0
    while i < len(text):
        if i + 1 < len(text) and text[i] in '！？!?' and text[i + 1] in '！？!?':
            token = text[i:i + 2]
            if token in DOUBLE_PUNCT_TOKENS:
                tokens.append(token)
                i += 2
                continue
        if text[i].isascii() and text[i].isalnum():
            j = i + 1
            while j < len(text) and text[j].isascii() and text[j].isalnum():
                j += 1
            run = text[i:j]
            if _is_tatechuyoko_token(run):
                tokens.append(run)
            else:
                tokens.extend(list(run))
            i = j
            continue
        tokens.append(text[i])
        i += 1
    return tokens


@lru_cache(maxsize=512)
def _tokenize_vertical_text_cached(text: str) -> tuple[str, ...]:
    return tuple(_tokenize_vertical_text_impl(text))


def _tokenize_vertical_text(text: str) -> list[str]:
    return list(_tokenize_vertical_text_cached(str(text or '')))


def _is_line_head_forbidden(token: str) -> bool:
    if not token:
        return False
    if token in DOUBLE_PUNCT_TOKENS:
        return True
    return all(ch in LINE_HEAD_FORBIDDEN_CHARS for ch in token)


def _is_line_end_forbidden(token: str) -> bool:
    if not token:
        return False
    return all(ch in LINE_END_FORBIDDEN_CHARS for ch in token)


def _is_hanging_punctuation(token: str) -> bool:
    return bool(token) and len(token) == 1 and token in HANGING_PUNCTUATION_CHARS


def _is_continuous_punctuation_pair(current_token: str, next_token: str) -> bool:
    if not current_token or not next_token:
        return False
    if len(current_token) != 1 or len(next_token) != 1:
        return False
    return (current_token + next_token) in CONTINUOUS_PUNCTUATION_PAIRS


def _continuous_punctuation_run_length(tokens: Sequence[str], start_idx: int) -> int:
    if start_idx >= len(tokens):
        return 0
    token = tokens[start_idx]
    if not token or len(token) != 1 or token not in REPEATABLE_CONTINUOUS_PUNCT_CHARS:
        return 0
    idx = start_idx + 1
    while idx < len(tokens) and tokens[idx] == token:
        idx += 1
    run_len = idx - start_idx
    return run_len if run_len >= 2 else 0


def _closing_punctuation_group_length(tokens: Sequence[str], start_idx: int) -> int:
    if start_idx >= len(tokens):
        return 0
    idx = start_idx
    while idx < len(tokens):
        token = tokens[idx]
        if not token or len(token) != 1 or token not in CLOSE_BRACKET_CHARS:
            break
        idx += 1
    if idx == start_idx:
        return 0
    tail_idx = idx
    while tail_idx < len(tokens):
        token = tokens[tail_idx]
        if token in DOUBLE_PUNCT_TOKENS:
            tail_idx += 1
            continue
        if len(token) == 1 and token in TAIL_PUNCTUATION_CHARS:
            tail_idx += 1
            continue
        break
    if tail_idx == idx:
        return idx - start_idx
    return tail_idx - start_idx


def _minimum_safe_group_length(tokens: Sequence[str], start_idx: int) -> int:
    """start_idx から、行末/行頭禁則を破らず同一行へ残すための最小まとまり長を返す。"""
    if start_idx >= len(tokens):
        return 0
    for end_idx in range(start_idx, len(tokens)):
        tail_token = tokens[end_idx]
        if _is_line_end_forbidden(tail_token):
            continue
        if end_idx + 1 < len(tokens):
            next_token = tokens[end_idx + 1]
            if _is_line_head_forbidden(next_token):
                continue
            if _is_continuous_punctuation_pair(tail_token, next_token):
                continue
        return end_idx - start_idx + 1
    return len(tokens) - start_idx


def _protected_token_group_length(tokens: Sequence[str], start_idx: int) -> int:
    return max(
        _continuous_punctuation_run_length(tokens, start_idx),
        _closing_punctuation_group_length(tokens, start_idx),
        _minimum_safe_group_length(tokens, start_idx),
    )


@lru_cache(maxsize=512)
def _build_single_token_vertical_layout_hints(token: str) -> VerticalLayoutHints:
    line_head_forbidden = _is_line_head_forbidden(token)
    line_end_forbidden = _is_line_end_forbidden(token)
    hanging_punctuation = _is_hanging_punctuation(token)
    return {
        'line_head_forbidden': (line_head_forbidden,),
        'line_end_forbidden': (line_end_forbidden,),
        'hanging_punctuation': (hanging_punctuation,),
        'continuous_pair_with_next': (False,),
        'protected_group_len': (1,),
        'would_start_forbidden_after_hang_pair': (False,),
    }


@lru_cache(maxsize=512)
def _build_two_token_vertical_layout_hints(first_token: str, second_token: str) -> VerticalLayoutHints:
    token_pair = (first_token, second_token)
    first_line_head_forbidden = _is_line_head_forbidden(first_token)
    second_line_head_forbidden = _is_line_head_forbidden(second_token)
    first_line_end_forbidden = _is_line_end_forbidden(first_token)
    second_line_end_forbidden = _is_line_end_forbidden(second_token)
    first_hanging_punctuation = _is_hanging_punctuation(first_token)
    second_hanging_punctuation = _is_hanging_punctuation(second_token)
    continuous_pair = _is_continuous_punctuation_pair(first_token, second_token)
    first_would_start_forbidden_after_hang_pair = first_hanging_punctuation and second_line_head_forbidden
    return {
        'line_head_forbidden': (first_line_head_forbidden, second_line_head_forbidden),
        'line_end_forbidden': (first_line_end_forbidden, second_line_end_forbidden),
        'hanging_punctuation': (first_hanging_punctuation, second_hanging_punctuation),
        'continuous_pair_with_next': (continuous_pair, False),
        'protected_group_len': (
            _protected_token_group_length(token_pair, 0),
            _protected_token_group_length(token_pair, 1),
        ),
        'would_start_forbidden_after_hang_pair': (
            first_would_start_forbidden_after_hang_pair,
            False,
        ),
    }


@lru_cache(maxsize=512)
def _build_three_token_vertical_layout_hints(first_token: str, second_token: str, third_token: str) -> VerticalLayoutHints:
    token_triplet = (first_token, second_token, third_token)
    first_line_head_forbidden = _is_line_head_forbidden(first_token)
    second_line_head_forbidden = _is_line_head_forbidden(second_token)
    third_line_head_forbidden = _is_line_head_forbidden(third_token)
    first_line_end_forbidden = _is_line_end_forbidden(first_token)
    second_line_end_forbidden = _is_line_end_forbidden(second_token)
    third_line_end_forbidden = _is_line_end_forbidden(third_token)
    first_hanging_punctuation = _is_hanging_punctuation(first_token)
    second_hanging_punctuation = _is_hanging_punctuation(second_token)
    third_hanging_punctuation = _is_hanging_punctuation(third_token)
    first_continuous_pair = _is_continuous_punctuation_pair(first_token, second_token)
    second_continuous_pair = _is_continuous_punctuation_pair(second_token, third_token)
    return {
        'line_head_forbidden': (first_line_head_forbidden, second_line_head_forbidden, third_line_head_forbidden),
        'line_end_forbidden': (first_line_end_forbidden, second_line_end_forbidden, third_line_end_forbidden),
        'hanging_punctuation': (first_hanging_punctuation, second_hanging_punctuation, third_hanging_punctuation),
        'continuous_pair_with_next': (first_continuous_pair, second_continuous_pair, False),
        'protected_group_len': (
            _protected_token_group_length(token_triplet, 0),
            _protected_token_group_length(token_triplet, 1),
            _protected_token_group_length(token_triplet, 2),
        ),
        'would_start_forbidden_after_hang_pair': (
            third_line_head_forbidden,
            False,
            False,
        ),
    }


@lru_cache(maxsize=512)
def _build_four_token_vertical_layout_hints(first_token: str, second_token: str, third_token: str, fourth_token: str) -> VerticalLayoutHints:
    token_quad = (first_token, second_token, third_token, fourth_token)
    first_line_head_forbidden = _is_line_head_forbidden(first_token)
    second_line_head_forbidden = _is_line_head_forbidden(second_token)
    third_line_head_forbidden = _is_line_head_forbidden(third_token)
    fourth_line_head_forbidden = _is_line_head_forbidden(fourth_token)
    first_line_end_forbidden = _is_line_end_forbidden(first_token)
    second_line_end_forbidden = _is_line_end_forbidden(second_token)
    third_line_end_forbidden = _is_line_end_forbidden(third_token)
    fourth_line_end_forbidden = _is_line_end_forbidden(fourth_token)
    first_hanging_punctuation = _is_hanging_punctuation(first_token)
    second_hanging_punctuation = _is_hanging_punctuation(second_token)
    third_hanging_punctuation = _is_hanging_punctuation(third_token)
    fourth_hanging_punctuation = _is_hanging_punctuation(fourth_token)
    first_continuous_pair = _is_continuous_punctuation_pair(first_token, second_token)
    second_continuous_pair = _is_continuous_punctuation_pair(second_token, third_token)
    third_continuous_pair = _is_continuous_punctuation_pair(third_token, fourth_token)
    return {
        'line_head_forbidden': (
            first_line_head_forbidden,
            second_line_head_forbidden,
            third_line_head_forbidden,
            fourth_line_head_forbidden,
        ),
        'line_end_forbidden': (
            first_line_end_forbidden,
            second_line_end_forbidden,
            third_line_end_forbidden,
            fourth_line_end_forbidden,
        ),
        'hanging_punctuation': (
            first_hanging_punctuation,
            second_hanging_punctuation,
            third_hanging_punctuation,
            fourth_hanging_punctuation,
        ),
        'continuous_pair_with_next': (
            first_continuous_pair,
            second_continuous_pair,
            third_continuous_pair,
            False,
        ),
        'protected_group_len': (
            _protected_token_group_length(token_quad, 0),
            _protected_token_group_length(token_quad, 1),
            _protected_token_group_length(token_quad, 2),
            _protected_token_group_length(token_quad, 3),
        ),
        'would_start_forbidden_after_hang_pair': (
            third_line_head_forbidden,
            fourth_line_head_forbidden,
            False,
            False,
        ),
    }


@lru_cache(maxsize=512)
def _build_vertical_layout_hints_cached(tokens: tuple[str, ...]) -> VerticalLayoutHints:
    token_count = len(tokens)
    if token_count <= 0:
        empty_bools: tuple[bool, ...] = ()
        empty_ints: tuple[int, ...] = ()
        return {
            'line_head_forbidden': empty_bools,
            'line_end_forbidden': empty_bools,
            'hanging_punctuation': empty_bools,
            'continuous_pair_with_next': empty_bools,
            'protected_group_len': empty_ints,
            'would_start_forbidden_after_hang_pair': empty_bools,
        }
    if token_count == 1:
        return _build_single_token_vertical_layout_hints(tokens[0])
    if token_count == 2:
        return _build_two_token_vertical_layout_hints(tokens[0], tokens[1])
    if token_count == 3:
        return _build_three_token_vertical_layout_hints(tokens[0], tokens[1], tokens[2])
    if token_count == 4:
        return _build_four_token_vertical_layout_hints(tokens[0], tokens[1], tokens[2], tokens[3])

    line_head_forbidden = [False] * token_count
    line_end_forbidden = [False] * token_count
    hanging_punctuation = [False] * token_count
    continuous_pair_with_next = [False] * token_count
    would_start_forbidden_after_hang_pair = [False] * token_count

    for idx, token in enumerate(tokens):
        line_head_forbidden[idx] = _is_line_head_forbidden(token)
        line_end_forbidden[idx] = _is_line_end_forbidden(token)
        hanging_punctuation[idx] = _is_hanging_punctuation(token)

    for idx in range(token_count - 1):
        continuous_pair_with_next[idx] = _is_continuous_punctuation_pair(tokens[idx], tokens[idx + 1])

    for idx in range(token_count - 2):
        would_start_forbidden_after_hang_pair[idx] = line_head_forbidden[idx + 2]

    same_run_len = [0] * token_count
    continuous_run_len = [0] * token_count
    close_run_len = [0] * token_count
    tail_run_len = [0] * token_count

    for idx in range(token_count - 1, -1, -1):
        token = tokens[idx]
        if idx + 1 < token_count and tokens[idx + 1] == token:
            same_run_len[idx] = same_run_len[idx + 1] + 1
        else:
            same_run_len[idx] = 1
        if token and len(token) == 1 and token in REPEATABLE_CONTINUOUS_PUNCT_CHARS and same_run_len[idx] >= 2:
            continuous_run_len[idx] = same_run_len[idx]
        if token and len(token) == 1 and token in CLOSE_BRACKET_CHARS:
            close_run_len[idx] = 1 + (close_run_len[idx + 1] if idx + 1 < token_count else 0)
        if token in DOUBLE_PUNCT_TOKENS or (len(token) == 1 and token in TAIL_PUNCTUATION_CHARS):
            tail_run_len[idx] = 1 + (tail_run_len[idx + 1] if idx + 1 < token_count else 0)

    closing_group_len = [0] * token_count
    for idx in range(token_count):
        close_len = close_run_len[idx]
        if close_len <= 0:
            continue
        tail_idx = idx + close_len
        closing_group_len[idx] = close_len + (tail_run_len[tail_idx] if tail_idx < token_count else 0)

    safe_tail = [False] * token_count
    for idx in range(token_count):
        if line_end_forbidden[idx]:
            continue
        if idx + 1 < token_count and (line_head_forbidden[idx + 1] or continuous_pair_with_next[idx]):
            continue
        safe_tail[idx] = True

    minimum_safe_group_len = [0] * token_count
    next_safe_tail_idx = token_count
    for idx in range(token_count - 1, -1, -1):
        if safe_tail[idx]:
            next_safe_tail_idx = idx
        minimum_safe_group_len[idx] = max(0, next_safe_tail_idx - idx + 1) if next_safe_tail_idx < token_count else (token_count - idx)

    protected_group_len = [0] * token_count
    for idx in range(token_count):
        protected_group_len[idx] = max(continuous_run_len[idx], closing_group_len[idx], minimum_safe_group_len[idx])

    return {
        'line_head_forbidden': tuple(line_head_forbidden),
        'line_end_forbidden': tuple(line_end_forbidden),
        'hanging_punctuation': tuple(hanging_punctuation),
        'continuous_pair_with_next': tuple(continuous_pair_with_next),
        'protected_group_len': tuple(protected_group_len),
        'would_start_forbidden_after_hang_pair': tuple(would_start_forbidden_after_hang_pair),
    }


def _build_vertical_layout_hints(tokens: Sequence[str]) -> VerticalLayoutHints:
    return _build_vertical_layout_hints_cached(tokens if isinstance(tokens, tuple) else tuple(tokens))


def _choose_vertical_layout_action_with_hints(hints: VerticalLayoutHints, idx: int, slots_left: int, current_not_top: bool, kinsoku_mode: str = 'standard', action_cache: dict[tuple[int, int, bool], str] | None = None) -> str:
    mode = kinsoku_mode if kinsoku_mode in {'standard', 'simple', 'off'} else _normalize_kinsoku_mode(kinsoku_mode)
    cache_key: tuple[int, int, bool] | None = None
    if action_cache is not None:
        cache_key = (idx, slots_left, bool(current_not_top))
        cached = action_cache.get(cache_key)
        if cached is not None:
            return cached

    token_count = len(hints['line_head_forbidden'])
    if idx >= token_count:
        result = 'done'
    elif slots_left <= 0:
        result = 'advance'
    elif mode == 'off':
        result = 'draw'
    else:
        line_end_forbidden = hints['line_end_forbidden'][idx]
        if slots_left == 1 and current_not_top and line_end_forbidden:
            result = 'advance'
        elif slots_left == 1 and current_not_top and idx + 1 < token_count:
            if mode == 'standard' and hints['continuous_pair_with_next'][idx]:
                result = 'advance'
            elif hints['hanging_punctuation'][idx + 1] and not line_end_forbidden:
                if mode == 'standard' and hints['would_start_forbidden_after_hang_pair'][idx]:
                    result = 'advance'
                else:
                    result = 'hang_pair'
            elif hints['line_head_forbidden'][idx + 1]:
                result = 'advance'
            else:
                result = 'draw'
        elif mode == 'simple':
            result = 'draw'
        elif hints['protected_group_len'][idx] >= 2 and slots_left < hints['protected_group_len'][idx] and current_not_top:
            result = 'advance'
        elif line_end_forbidden and current_not_top and idx + 1 < token_count and slots_left >= 2:
            next_action = _choose_vertical_layout_action_with_hints(
                hints, idx + 1, slots_left - 1, True,
                kinsoku_mode=mode, action_cache=action_cache,
            )
            result = 'advance' if next_action == 'advance' else 'draw'
        else:
            result = 'draw'

    if action_cache is not None and cache_key is not None:
        action_cache[cache_key] = result
    return result


def _normalize_kinsoku_mode(mode: object) -> str:
    mode = str(mode or 'standard').strip().lower()
    return mode if mode in {'off', 'simple', 'standard'} else 'standard'


@lru_cache(maxsize=128)
def _effective_vertical_layout_bottom_margin(margin_b: int, font_size: int) -> int:
    """Return the bottom guard used by the vertical line grid.

    The bottom margin is specified in pixels, but the vertical text renderer advances
    in whole ``font_size + 2`` cells.  With combinations such as top margin 0 and
    bottom margin 12, the old slot calculation could keep the same last text cell as
    bottom margin 0, making the preview look as if the bottom margin had been ignored.
    Add a small font-scaled descender guard only when a positive bottom margin is
    requested so the bottom margin is visibly reserved without changing true zero
    margin layouts.
    """
    margin_b = max(0, int(margin_b or 0))
    font_size = max(1, int(font_size or 1))
    if margin_b <= 0:
        return 0
    descender_guard = max(2, int(round(font_size * 0.25)))
    return margin_b + descender_guard


def _remaining_vertical_slots(curr_y: int, height: int, margin_b: int, font_size: int) -> int:
    effective_margin_b = _effective_vertical_layout_bottom_margin(margin_b, font_size)
    limit = height - effective_margin_b - font_size
    if curr_y > limit:
        return 0
    return 1 + (limit - curr_y) // (font_size + 2)


def _remaining_vertical_slots_for_current_column(
    curr_y: int,
    margin_t: int,
    height: int,
    margin_b: int,
    font_size: int,
    wrap_indent_step: int = 0,
) -> int:
    """Return remaining body slots while preserving progress on tiny pages.

    Normal pages should respect the effective bottom guard from
    ``_remaining_vertical_slots``.  Extremely short pages can report no usable
    slots even at the top of a fresh column; in that case allow one progress
    slot so layout code does not keep advancing columns forever without
    consuming a token.
    """
    slots_left = _remaining_vertical_slots(curr_y, height, margin_b, font_size)
    top_y = int(margin_t or 0) + max(0, int(wrap_indent_step or 0))
    if slots_left <= 0 and int(curr_y or 0) <= top_y:
        return 1
    return slots_left


def _would_start_forbidden_after_hang_pair(tokens: Sequence[str], idx: int) -> bool:
    """idx, idx+1 を同一行へ置いた直後、次行頭が禁則になるなら True。"""
    next_idx = idx + 2
    if next_idx >= len(tokens):
        return False
    next_token = tokens[next_idx]
    return _is_line_head_forbidden(next_token)


def _choose_vertical_layout_action(tokens: Sequence[str], idx: int, curr_y: int, margin_t: int, height: int, margin_b: int, font_size: int, kinsoku_mode: str = 'standard') -> str:
    if idx >= len(tokens):
        return 'done'
    token = tokens[idx]
    slots_left = _remaining_vertical_slots(curr_y, height, margin_b, font_size)
    if slots_left == 0:
        return 'advance'

    mode = _normalize_kinsoku_mode(kinsoku_mode)
    if mode == 'off':
        return 'draw'

    if (
        slots_left == 1
        and curr_y > margin_t
        and _is_line_end_forbidden(token)
    ):
        return 'advance'
    if slots_left == 1 and curr_y > margin_t and idx + 1 < len(tokens):
        next_token = tokens[idx + 1]
        if mode == 'standard' and _is_continuous_punctuation_pair(token, next_token):
            return 'advance'
        if _is_hanging_punctuation(next_token) and not _is_line_end_forbidden(token):
            if mode == 'standard' and _would_start_forbidden_after_hang_pair(tokens, idx):
                return 'advance'
            return 'hang_pair'
        if _is_line_head_forbidden(next_token):
            return 'advance'

    if mode == 'simple':
        return 'draw'

    protected_group_len = _protected_token_group_length(tokens, idx)
    if (
        protected_group_len >= 2
        and slots_left < protected_group_len
        and curr_y > margin_t
    ):
        return 'advance'
    if (
        _is_line_end_forbidden(token)
        and curr_y > margin_t
        and idx + 1 < len(tokens)
        and slots_left >= 2
    ):
        next_curr_y = curr_y + font_size + 2
        next_action = _choose_vertical_layout_action(
            tokens, idx + 1, next_curr_y, margin_t, height, margin_b, font_size,
            kinsoku_mode=mode,
        )
        if next_action == 'advance':
            return 'advance'
    return 'draw'


@lru_cache(maxsize=128)
def _double_punctuation_layout(f_size: int) -> tuple[int, int, int]:
    sub_f_size = int(f_size * 0.75)
    half_w = f_size // 2
    char_offset = (half_w - sub_f_size) // 2
    return sub_f_size, half_w, char_offset


@lru_cache(maxsize=128)
def _double_punctuation_draw_offsets(f_size: int) -> tuple[int, int, int]:
    sub_f_size, half_w, char_offset = _double_punctuation_layout(f_size)
    first_x = char_offset + 10
    second_x = half_w + char_offset + 10
    return sub_f_size, first_x, second_x


@lru_cache(maxsize=128)
def _hanging_bottom_layout(f_size: int, is_kutoten: bool, extra_raise_ratio: float) -> tuple[int, int]:
    if is_kutoten:
        lower_ratio = max(0.22, 0.28 - float(extra_raise_ratio))
    else:
        lower_ratio = max(0.12, 0.20 - float(extra_raise_ratio))
    local_lower = max(1, int(round(f_size * lower_ratio)))
    return 0, local_lower


@lru_cache(maxsize=512)
def _hanging_bottom_draw_offsets(f_size: int, glyph_h: int, canvas_height: int, is_kutoten: bool,
                                 extra_raise_ratio: float) -> tuple[int, int]:
    draw_x_delta = _scaled_kutoten_offset(f_size)[0] if is_kutoten else 0
    base_raise, local_lower = _hanging_bottom_layout(f_size, bool(is_kutoten), float(extra_raise_ratio))
    desired_y = base_raise + local_lower
    cell_limit_y = max(0, int(f_size) - int(glyph_h) - 1)
    page_limit_y = int(canvas_height) - int(glyph_h) - 1 if canvas_height else cell_limit_y
    draw_y_delta = max(0, min(desired_y, cell_limit_y, page_limit_y))
    return int(draw_x_delta), int(draw_y_delta)


def _limit_draw_y_delta_to_page(draw_y_delta: int, curr_y: int, glyph_h: int, canvas_height: int) -> int:
    """Clamp a glyph-local Y delta so the final paste/draw stays inside the page.

    The hanging helpers compute offsets relative to the current text cell.  Their
    cached ``canvas_height`` guard only knows the page height, not the current
    cell's absolute Y position.  Near the bottom of a page, that can leave enough
    local offset to draw or paste the glyph below the image.  Keep upward
    adjustments intact while capping only the lower edge.
    """
    draw_y_delta = int(draw_y_delta)
    if not canvas_height:
        return draw_y_delta
    page_bottom_delta = int(canvas_height) - int(curr_y) - int(glyph_h) - 1
    return int(min(draw_y_delta, page_bottom_delta))


def _draw_hanging_text_near_bottom(
    draw: Any,
    original_char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    canvas_height: int,
    *,
    is_bold: bool = False,
    is_italic: bool = False,
    extra_raise_ratio: float = 0.0,
    anchor_visible_ink: bool = False,
) -> None:
    """
    Render a character near the bottom of the cell for hanging punctuation and
    closing brackets.  Characters that map to vertical variants via
    ``TATE_REPLACE`` are resolved accordingly; otherwise the original
    character is used.  For punctuation marks, an additional horizontal
    offset is applied via ``_scaled_kutoten_offset``.

    The implementation avoids unnecessary boolean/float coercions and
    trusts the helpers to perform any required normalisation internally.
    """
    curr_x, curr_y = pos_tuple
    # Resolve the character to be drawn.  Only call the expensive glyph
    # resolver when the mapping differs.
    mapped_char = TATE_REPLACE.get(original_char)
    if mapped_char and mapped_char != original_char:
        char = _resolve_vertical_glyph_char(original_char, font, is_bold=is_bold, is_italic=is_italic)
    else:
        char = original_char
    # Obtain the glyph height from the bounding box.  The helper returns a
    # minimal 1×1 bbox for missing glyphs, so no fallback is needed here.
    bbox_left, bbox_top, bbox_right, bbox_bottom = _get_text_bbox(font, char, is_bold=is_bold)
    glyph_h = max(1, bbox_bottom - bbox_top)
    # Determine if the original character is a punctuation mark that needs
    # additional horizontal shifting.
    is_kutoten = original_char in {"、", "。", "，", "．", "､", "｡"}
    # Compute draw deltas for positioning near the bottom of the cell.  Do
    # not wrap values into bool/float here; the callee handles that.
    draw_x_delta, draw_y_delta = _hanging_bottom_draw_offsets(
        f_size,
        glyph_h,
        canvas_height,
        is_kutoten,
        extra_raise_ratio,
    )
    if anchor_visible_ink:
        # sweep341: Some fonts expose closing-bracket glyphs with a large
        # positive bbox top.  Drawing them at the raw baseline makes the
        # visible horizontal stroke sink even though the logical offset is the
        # same.  For hanging closing brackets, anchor by the visible ink top
        # instead of the font baseline so low-bbox fonts are pulled back up.
        draw_y_delta -= int(bbox_top)
    draw_y_delta = _limit_draw_y_delta_to_page(draw_y_delta, curr_y, glyph_h, canvas_height)
    # When hanging, we deliberately avoid applying the usual upward
    # correction used for normal punctuation.  Without this, the mark
    # would overlap with the preceding character.
    draw_weighted_text(
        draw,
        (curr_x + draw_x_delta, curr_y + draw_y_delta),
        char,
        font,
        is_bold=is_bold,
        is_italic=is_italic,
    )




def _is_lowerable_hanging_closing_bracket(token: str) -> bool:
    return bool(token) and len(token) == 1 and token in LOWERABLE_HANGING_CLOSING_BRACKET_CHARS


def draw_hanging_closing_bracket(draw: Any, char: str, pos_tuple: tuple[int, int], font: Any, f_size: int, canvas_height: int, is_bold: bool = False, ruby_mode: bool = False, is_italic: bool = False) -> None:
    _draw_hanging_text_near_bottom(
        draw, char, pos_tuple, font, f_size, canvas_height,
        is_bold=is_bold, is_italic=is_italic, extra_raise_ratio=0.18,
        anchor_visible_ink=True,
    )


@lru_cache(maxsize=128)
def _tate_punctuation_layout_insets(f_size: int, next_cell: bool, fallback_layout: bool) -> tuple[int, int, int]:
    if fallback_layout:
        right_inset = max(1, int(round(f_size * 0.08)))
        top_inset = max(1, int(round(f_size * 0.06)))
    else:
        right_inset = max(0, int(round(f_size * 0.03)))
        top_inset = max(4, int(round(f_size * (0.25 if next_cell else 0.10))))
    extra_raise = max(2, int(round(f_size * 0.18))) if next_cell else 0
    return right_inset, top_inset, extra_raise


@lru_cache(maxsize=128)
def _tate_hanging_punctuation_raise(f_size: int, fallback_layout: bool) -> int:
    # clean203〜sweep312 で維持していた「ぶら下げ句読点を少し上へ戻す」仕様を、
    # right/bottom アンカー方式の上に重ねる。
    # sweep317: sweep316 の一律強め補正は大きいフォント/インク幅の広い
    # フォントで本文と重なる副作用があったため、基礎持ち上げ量を少し戻し、
    # 実際の安全域判定を _tate_hanging_punctuation_min_top_offset 側で行う。
    base_ratio = 0.30 if not fallback_layout else 0.24
    return max(3, int(round(f_size * base_ratio)))


@lru_cache(maxsize=128)
def _tate_hanging_punctuation_visual_targets(f_size: int, fallback_layout: bool) -> tuple[int, int, int]:
    cell_top = f_size + 2
    if fallback_layout:
        center_target = cell_top + int(round(f_size * 0.47))
        max_top = cell_top + int(round(f_size * 0.37))
        center_weight = 4
    else:
        center_target = cell_top + int(round(f_size * 0.43))
        max_top = cell_top + int(round(f_size * 0.34))
        center_weight = 5
    return center_target, max_top, center_weight


@lru_cache(maxsize=128)
def _tate_hanging_punctuation_min_top_offset(f_size: int, ink_top: int, ink_bottom: int, glyph_h: int) -> int:
    # sweep325: ごく一部のフォントで、ぶら下がり句読点のインクが前セルの本文へ
    # 重なるケースが残ったため、安全側の下限を少し下げる。単純に全体を下げすぎると
    # 「低すぎる」見え方へ戻るため、インク実高さとグリフキャンバス高さが大きい場合を
    # より強く保護する。
    ink_height = max(1, int(ink_bottom) - int(ink_top))
    f_size = max(1, int(f_size))
    glyph_h = max(1, int(glyph_h))
    if ink_height <= max(3, int(round(f_size * 0.24))):
        ratio = 0.62
    elif ink_height <= max(4, int(round(f_size * 0.42))):
        ratio = 0.68
    else:
        ratio = 0.76
    if f_size >= 48:
        ratio = max(ratio, 0.72)
    if glyph_h >= int(round(f_size * 0.85)):
        ratio = max(ratio, 0.78)
    if glyph_h >= int(round(f_size * 1.05)):
        ratio = max(ratio, 0.82)
    safety_top = int(round(f_size * ratio))
    return int(safety_top - int(ink_top))


@lru_cache(maxsize=1024)
def _tate_hanging_punctuation_offset_y(
    f_size: int,
    ink_top: int,
    ink_bottom: int,
    top_inset: int,
    extra_raise: int,
    canvas_height: int,
    glyph_h: int,
    fallback_layout: bool = False,
) -> int:
    cell_top = f_size + 2
    cell_bottom = cell_top + f_size - 1
    bottom_inset = max(2, top_inset - extra_raise)
    target_bottom = cell_bottom - bottom_inset
    offset_from_bottom = target_bottom - ink_bottom

    center_target, max_top, center_weight = _tate_hanging_punctuation_visual_targets(
        f_size,
        fallback_layout,
    )
    ink_center = (ink_top + ink_bottom) / 2.0
    offset_from_center = int(round(center_target - ink_center))

    weight_base = 10
    offset_y = int(round(
        ((offset_from_bottom * (weight_base - center_weight)) + (offset_from_center * center_weight)) / weight_base
    ))
    offset_y -= _tate_hanging_punctuation_raise(f_size, fallback_layout)

    max_top_offset = max_top - ink_top
    min_top_offset = _tate_hanging_punctuation_min_top_offset(f_size, ink_top, ink_bottom, glyph_h)
    offset_y = min(offset_y, max_top_offset)
    offset_y = max(offset_y, min_top_offset)

    if canvas_height:
        offset_y = min(offset_y, max(0, canvas_height - glyph_h - 1))
    return int(offset_y)


@lru_cache(maxsize=512)
def _tate_punctuation_direct_offsets(f_size: int, glyph_w: int, glyph_h: int, bbox_left: int, bbox_top: int,
                                     right_inset: int, top_inset: int, extra_raise: int,
                                     next_cell: bool, canvas_height: int, fallback_layout: bool = False) -> tuple[int, int]:
    offset_x = max(0, f_size - glyph_w - right_inset) - bbox_left
    if next_cell:
        bbox_bottom = bbox_top + glyph_h
        offset_y = _tate_hanging_punctuation_offset_y(
            f_size,
            bbox_top,
            bbox_bottom,
            top_inset,
            extra_raise,
            canvas_height,
            glyph_h + bbox_top,
            fallback_layout,
        )
    else:
        offset_y = top_inset - bbox_top
    if canvas_height:
        offset_y = min(offset_y, max(0, canvas_height - glyph_h - 1 - bbox_top))
    return int(offset_x), int(offset_y)


@lru_cache(maxsize=512)
def _tate_punctuation_image_offsets(f_size: int, glyph_w: int, glyph_h: int,
                                    right_inset: int, top_inset: int, extra_raise: int,
                                    next_cell: bool, canvas_height: int, fallback_layout: bool = False) -> tuple[int, int]:
    offset_x = max(0, f_size - glyph_w - right_inset)
    if next_cell:
        offset_y = _tate_hanging_punctuation_offset_y(
            f_size,
            0,
            glyph_h,
            top_inset,
            extra_raise,
            canvas_height,
            glyph_h,
            fallback_layout,
        )
    else:
        offset_y = top_inset
    if canvas_height:
        offset_y = min(offset_y, max(0, canvas_height - glyph_h - 1))
    return int(offset_x), int(offset_y)


def _draw_tate_punctuation_glyph(
    draw: Any,
    glyph_char: str,
    pos_tuple: tuple[int, int],
    font: Any,
    f_size: int,
    *,
    is_bold: bool = False,
    is_italic: bool = False,
    next_cell: bool = False,
    canvas_height: int = 0,
    fallback_layout: bool = False,
) -> None:
    """句読点は画像ベースで描画し、ぶら下がり時は実際の描画下端に合わせる。"""
    curr_x, curr_y = pos_tuple

    right_inset, top_inset, extra_raise = _tate_punctuation_layout_insets(
        f_size,
        next_cell,
        fallback_layout,
    )

    glyph_img, glyph_mask = _render_text_glyph_and_mask_shared(
        glyph_char,
        font,
        is_bold=is_bold,
        is_italic=is_italic,
    )
    glyph_w, glyph_h = glyph_img.size

    off_x = max(0, f_size - glyph_w - right_inset)
    if next_cell:
        bbox = glyph_mask.getbbox() if glyph_mask else None
        if bbox:
            _ink_left, ink_top, _ink_right, ink_bottom = bbox
        else:
            ink_top, ink_bottom = 0, glyph_h
        off_y = _tate_hanging_punctuation_offset_y(
            f_size,
            ink_top,
            ink_bottom,
            top_inset,
            extra_raise,
            canvas_height,
            glyph_h,
            fallback_layout,
        )
    else:
        off_y = top_inset

    off_y = _limit_draw_y_delta_to_page(off_y, curr_y, glyph_h, canvas_height)

    _paste_glyph_image(
        draw,
        glyph_img,
        (curr_x + int(off_x), curr_y + int(off_y)),
        glyph_mask,
    )


def _vertical_dot_leader_count(char: str) -> int:
    if char in VERTICAL_DOT_LEADER_THREE_CHARS:
        return 3
    if char in VERTICAL_DOT_LEADER_TWO_CHARS:
        return 2
    return 0


def draw_vertical_dot_leader(draw: Any, char: str, pos_tuple: tuple[int, int], f_size: int, *, is_bold: bool = False) -> None:
    """三点リーダ/二点リーダをフォント非依存の縦点列として描画する。"""
    dot_count = _vertical_dot_leader_count(char)
    if dot_count <= 0:
        return
    curr_x, curr_y = pos_tuple
    f_size = max(1, int(f_size or 1))
    dot_diameter = max(2, int(round(f_size * (0.145 if is_bold else 0.125))))
    # sweep316: フォント任せをやめた dot leader はセル基準で描くため、
    # 以前の 0.25/0.50/0.75 では実際の文字重心より上側に見えるフォントがあった。
    # 点列全体を少し下げ、下端に触れない範囲で視覚中央へ寄せる。
    # sweep317: 点列が上寄りに見える環境が残ったため、セル中央より
    # やや下側へ再配置する。下端には触れないよう max_center_y で制限する。
    centers = (0.48, 0.76) if dot_count == 2 else (0.39, 0.63, 0.86)
    center_x = curr_x + (f_size / 2.0)
    max_center_y = curr_y + f_size - (dot_diameter / 2.0) - 1
    for ratio in centers:
        center_y = min(curr_y + (f_size * ratio), max_center_y)
        left = int(round(center_x - dot_diameter / 2.0))
        top = int(round(center_y - dot_diameter / 2.0))
        right = left + dot_diameter
        bottom = top + dot_diameter
        draw.ellipse((left, top, right, bottom), fill=0)


def draw_hanging_punctuation(draw: Any, char: str, pos_tuple: tuple[int, int], font: Any, f_size: int, canvas_height: int, is_bold: bool = False, ruby_mode: bool = False, is_italic: bool = False) -> None:
    if _is_render_spacing_char(char):
        return
    if char in {'，', '．', '､', '｡'}:
        _draw_tate_punctuation_glyph(
            draw,
            char,
            pos_tuple,
            font,
            f_size,
            is_bold=is_bold,
            is_italic=is_italic,
            next_cell=True,
            canvas_height=canvas_height,
            fallback_layout=False,
        )
        return
    glyph_char, fallback_layout = _resolve_tate_punctuation_draw(
        char,
        font,
        is_bold=is_bold,
        is_italic=is_italic,
    )
    _draw_tate_punctuation_glyph(
        draw,
        glyph_char,
        pos_tuple,
        font,
        f_size,
        is_bold=is_bold,
        is_italic=is_italic,
        next_cell=True,
        canvas_height=canvas_height,
        fallback_layout=fallback_layout,
    )


def draw_char_tate(draw: Any, char: str, pos_tuple: tuple[int, int], font: Any, f_size: int, is_bold: bool = False, ruby_mode: bool = False, is_italic: bool = False) -> None:
    curr_x, curr_y = pos_tuple
    draw_centered = draw_centered_glyph
    draw_weighted = draw_weighted_text
    compute_spec = _compute_tate_draw_spec
    tate_replace = TATE_REPLACE

    if _is_render_spacing_char(char):
        return

    if char in VERTICAL_DOT_LEADER_CHARS:
        draw_vertical_dot_leader(draw, char, (curr_x, curr_y), f_size, is_bold=is_bold)
        return

    if _is_tatechuyoko_token(char):
        draw_tatechuyoko(draw, char, (curr_x, curr_y), font, f_size, is_bold=is_bold, is_italic=is_italic)
        return

    original_char = char
    draw_kind = _classify_tate_draw_char(original_char)

    # 2文字（！？や！！）を横並びにする
    if draw_kind == 'double_punct':
        sub_f_size, first_x, second_x = _double_punctuation_draw_offsets(f_size)
        sub_font = _make_font_variant(font, sub_f_size)
        draw_weighted(draw, (curr_x + first_x, curr_y), original_char[0], sub_font, is_bold=is_bold, is_italic=is_italic)
        draw_weighted(draw, (curr_x + second_x, curr_y), original_char[1], sub_font, is_bold=is_bold, is_italic=is_italic)
        return

    if draw_kind == 'ichi':
        # sweep348: 「一」は実インクが薄く、単純なセル幾何中央だと通常漢字
        # より上寄りに見えやすい。通常漢字の見た目中心へ合わせ直し、
        # 縦書き本文中で中央に見える位置へ戻す。
        draw_ink_centered_glyph(
            draw, original_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, rotate_degrees=0, align_to_text_flow=True, is_italic=is_italic,
        )
        return

    if draw_kind == 'long_vowel':
        draw_centered(
            draw, original_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, rotate_degrees=90, align_to_text_flow=True, is_italic=is_italic,
        )
        return

    if draw_kind == 'ascii_center':
        draw_centered(
            draw, original_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, align_to_text_flow=False, is_italic=is_italic,
        )
        return

    if draw_kind == 'punctuation':
        if original_char not in tate_replace:
            off_x, off_y = _scaled_kutoten_offset(f_size)
            draw_weighted(draw, (curr_x + off_x, curr_y + off_y), original_char, font, is_bold=is_bold, is_italic=is_italic)
            return
        resolved_char, fallback_layout = _resolve_tate_punctuation_draw(
            original_char,
            font,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        if fallback_layout:
            _draw_tate_punctuation_glyph(
                draw,
                resolved_char,
                (curr_x, curr_y),
                font,
                f_size,
                is_bold=is_bold,
                is_italic=is_italic,
                next_cell=False,
                fallback_layout=True,
            )
        else:
            off_x, off_y = _scaled_kutoten_offset(f_size)
            draw_weighted(draw, (curr_x + off_x, curr_y + off_y), resolved_char, font, is_bold=is_bold, is_italic=is_italic)
        return

    if draw_kind == 'small_kana':
        off_x, off_y = _small_kana_offset(f_size)
        draw_weighted(draw, (curr_x + off_x, curr_y + off_y), original_char, font, is_bold=is_bold, is_italic=is_italic)
        return

    if draw_kind == 'horizontal_bracket':
        resolved_char, rotate_degrees, extra_x, extra_y = _resolve_horizontal_bracket_draw(
            original_char,
            font,
            f_size,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        draw_centered(
            draw, resolved_char, (curr_x, curr_y), font, f_size,
            is_bold=is_bold, rotate_degrees=rotate_degrees, align_to_text_flow=True, is_italic=is_italic,
            extra_x=extra_x, extra_y=extra_y,
        )
        return

    if draw_kind == 'default':
        if original_char not in tate_replace:
            draw_weighted(draw, (curr_x, curr_y), original_char, font, is_bold=is_bold, is_italic=is_italic)
            return
        resolved_char = _resolve_default_tate_draw(
            original_char,
            font,
            is_bold=is_bold,
            is_italic=is_italic,
        )
        draw_weighted(draw, (curr_x, curr_y), resolved_char, font, is_bold=is_bold, is_italic=is_italic)
        return

    _draw_kind, resolved_char, _rotate_degrees, _extra_x, _extra_y, _off_x, _off_y, _fallback_layout = compute_spec(
        original_char,
        font,
        f_size,
        draw_kind=draw_kind,
        is_bold=is_bold,
        is_italic=is_italic,
    )
    draw_weighted(draw, (curr_x, curr_y), resolved_char, font, is_bold=is_bold, is_italic=is_italic)


# ==========================================
# --- CSS / ボールド解析 ---
# ==========================================

def style_declares_bold(style_text: str | None) -> bool:
    style_text = str(style_text or '')
    if not style_text:
        return False
    match = re.search(r'font-weight\s*:\s*([^;]+)', style_text, re.IGNORECASE)
    if not match:
        return False
    value = match.group(1).strip().lower()
    if value in {"bold", "bolder"}:
        return True
    num_match = re.search(r'\d+', value)
    return bool(num_match and int(num_match.group()) >= 600)


def extract_bold_rules(book: Any) -> BoldRuleSets:
    rules: BoldRuleSets = {"classes": set(), "ids": set(), "tags": set()}
    for item in book.get_items():
        media_type = getattr(item, 'media_type', '') or ''
        file_name = getattr(item, 'file_name', '') or ''
        if 'css' not in media_type and not file_name.lower().endswith('.css'):
            continue
        try:
            css_text = item.get_content().decode('utf-8', errors='ignore')
        except Exception:
            continue
        for selector_block, declaration_block in re.findall(
            r'([^{}]+)\{([^{}]+)\}', css_text, re.DOTALL
        ):
            if not style_declares_bold(declaration_block):
                continue
            for selector in selector_block.split(','):
                selector = selector.strip()
                if not selector:
                    continue
                for class_name in re.findall(r'\.([A-Za-z0-9_-]+)', selector):
                    rules["classes"].add(class_name)
                for id_name in re.findall(r'#([A-Za-z0-9_-]+)', selector):
                    rules["ids"].add(id_name)
                tag_match = re.fullmatch(r'([A-Za-z][A-Za-z0-9_-]*)', selector)
                if tag_match:
                    rules["tags"].add(tag_match.group(1).lower())
    return rules


def node_is_bold(node: Any, inherited_bold: bool, bold_rules: BoldRuleSets, css_rules: Sequence[CSSRule] | None = None) -> bool:
    if inherited_bold:
        return True
    return bool(_epub_node_analysis(node, bold_rules=bold_rules, css_rules=css_rules).get('intrinsic_bold', False))


def is_paragraph_like(node: Any) -> bool:
    node_name = getattr(node, 'name', None)
    if node_name not in PARAGRAPH_LIKE_TAGS:
        return False
    for child in getattr(node, 'contents', []):
        if getattr(child, 'name', None) in PARAGRAPH_LIKE_TAGS:
            return False
    return True


EPUB_SKIP_TAGS = {"script", "style", "head", "meta", "link", "title"}
EPUB_NOTEISH_RE = re.compile(r'(?:^|[-_])(note|footnote|annotation|aside|caption|figcaption|colophon|credit|source)(?:[-_]|$)', re.IGNORECASE)
EPUB_PAGEBREAK_RE = re.compile(r'(?:^|[-_])(pagebreak|page-break|mbp_pagebreak|pbreak|sectionbreak|chapterbreak)(?:[-_]|$)', re.IGNORECASE)


def _epub_node_token_signature(node: Any) -> tuple[tuple[str, tuple[str, ...] | str], ...]:
    if not getattr(node, 'get', None):
        return ()
    signature: list[tuple[str, tuple[str, ...] | str]] = []
    for attr_name in ('class', 'id', 'epub:type', 'type', 'role'):
        raw = node.get(attr_name)
        if isinstance(raw, (list, tuple, set)):
            normalized = tuple(str(item) for item in raw if item)
            signature.append((attr_name, normalized))
        elif raw:
            signature.append((attr_name, str(raw)))
        else:
            signature.append((attr_name, ''))
    return tuple(signature)


def _epub_node_attr_tokens(node: Any) -> list[str]:
    if not getattr(node, 'get', None):
        return []
    cache_key = _epub_node_token_signature(node)
    cache_attr = '_tategaki_epub_attr_tokens_cache'
    cached = getattr(node, cache_attr, None)
    if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == cache_key and isinstance(cached[1], list):
        return cast(list[str], cached[1])
    values = []
    for _attr_name, raw in cache_key:
        if isinstance(raw, tuple):
            values.extend(raw)
        elif raw:
            values.append(raw)
    tokens: list[str] = []
    for value in values:
        tokens.extend(part.strip().lower() for part in re.split(r'[\s/]+', value) if part and part.strip())
    try:
        setattr(node, cache_attr, (cache_key, tokens))
    except Exception:
        pass
    return tokens


def _epub_node_analysis_signature(node: Any) -> tuple[Any, ...]:
    node_name = (getattr(node, 'name', '') or '').lower()
    hidden = False
    if getattr(node, 'has_attr', None):
        try:
            hidden = bool(node.has_attr('hidden'))
        except Exception:
            hidden = False
    aria_hidden = ''
    if getattr(node, 'get', None):
        try:
            aria_hidden = str(node.get('aria-hidden', '') or '').strip().lower()
        except Exception:
            aria_hidden = ''
    parent = getattr(node, 'parent', None)
    parent_name = (getattr(parent, 'name', '') or '').lower()
    parent_start = ''
    if getattr(parent, 'get', None):
        try:
            parent_start = str(parent.get('start', '') or '')
        except Exception:
            parent_start = ''
    value_attr = ''
    if getattr(node, 'get', None):
        try:
            value_attr = str(node.get('value', '') or '')
        except Exception:
            value_attr = ''
    style_text = ''
    if getattr(node, 'get', None):
        try:
            style_text = str(node.get('style', '') or '')
        except Exception:
            style_text = ''
    child_block_tags = tuple(
        (getattr(child, 'name', '') or '').lower()
        for child in getattr(node, 'contents', [])
        if (getattr(child, 'name', '') or '').lower() in PARAGRAPH_LIKE_TAGS
    )
    return (
        node_name,
        _epub_node_token_signature(node),
        hidden,
        aria_hidden,
        parent_name,
        parent_start,
        value_attr,
        style_text,
        child_block_tags,
    )


def _epub_node_analysis(node: Any, bold_rules: BoldRuleSets | None = None, css_rules: Sequence[CSSRule] | None = None, font_size: int = 16) -> dict[str, Any]:
    if not getattr(node, 'name', None):
        return {
            'node_name': '',
            'heading_level': 0,
            'style_map': {},
            'attr_tokens': [],
            'should_skip': False,
            'requests_pagebreak': False,
            'note_like': False,
            'indent_profile': {
                'indent_chars': 0,
                'wrap_indent_chars': 0,
                'prefix': '',
                'prefix_bold': False,
                'blank_before': 1,
                'heading_level': 0,
            },
            'intrinsic_bold': False,
            'paragraph_like': False,
        }
    cache_key = (
        id(css_rules) if css_rules is not None else 0,
        id(bold_rules) if bold_rules is not None else 0,
        int(font_size or 0),
        _epub_node_analysis_signature(node),
    )
    cache_attr = '_tategaki_epub_node_analysis_cache'
    cached = getattr(node, cache_attr, None)
    if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == cache_key and isinstance(cached[1], dict):
        return cast(dict[str, Any], cached[1])

    node_name = (getattr(node, 'name', '') or '').lower()
    heading_level = epub_heading_level(node)
    style_map = _merged_epub_css_for_node(node, css_rules)
    attr_tokens = _epub_node_attr_tokens(node)
    should_skip = False
    if node_name in EPUB_SKIP_TAGS:
        should_skip = True
    elif cache_key[3][2]:
        should_skip = True
    elif cache_key[3][3] == 'true':
        should_skip = True
    elif style_map.get('display', '') == 'none' or style_map.get('visibility', '') == 'hidden':
        should_skip = True
    elif node_name == 'nav' and any(token in {'toc', 'landmarks', 'guide'} for token in attr_tokens):
        should_skip = True

    requests_pagebreak = False
    if node_name == 'hr':
        requests_pagebreak = True
    elif 'doc-pagebreak' in attr_tokens or 'pagebreak' in attr_tokens:
        requests_pagebreak = True
    elif any(EPUB_PAGEBREAK_RE.search(token) for token in attr_tokens):
        requests_pagebreak = True
    else:
        pagebreak_style_values = {
            'page-break-before': {'always'},
            'page-break-after': {'always'},
            'break-before': {'page', 'right', 'left'},
            'break-after': {'page', 'right', 'left'},
        }
        requests_pagebreak = any(style_map.get(prop, '') in values for prop, values in pagebreak_style_values.items())

    note_like = False
    if node_name in {'aside', 'blockquote', 'figcaption', 'caption', 'footer'}:
        note_like = True
    elif any(EPUB_NOTEISH_RE.search(token) for token in attr_tokens):
        note_like = True
    else:
        note_like = (
            _css_length_to_chars(style_map.get('margin-left', ''), font_size) >= 1
            or _css_length_to_chars(style_map.get('padding-left', ''), font_size) >= 1
        )

    intrinsic_bold = False
    if node_name in {'b', 'strong'}:
        intrinsic_bold = True
    elif bold_rules:
        if node_name in bold_rules['tags']:
            intrinsic_bold = True
        elif _font_weight_value_is_bold(style_map.get('font-weight', '')):
            intrinsic_bold = True
        else:
            node_id = node.get('id') if getattr(node, 'get', None) else None
            if node_id and node_id in bold_rules['ids']:
                intrinsic_bold = True
            else:
                for class_name in node.get('class', []) or []:
                    if class_name in bold_rules['classes']:
                        intrinsic_bold = True
                        break
    else:
        intrinsic_bold = _font_weight_value_is_bold(style_map.get('font-weight', ''))

    profile: EpubIndentProfile = {
        'indent_chars': 0,
        'wrap_indent_chars': 0,
        'prefix': '',
        'prefix_bold': False,
        'blank_before': 1,
        'heading_level': heading_level,
    }
    if heading_level:
        profile['blank_before'] = 2 if heading_level <= 2 else 1
    else:
        if node_name == 'li':
            profile['prefix'] = _epub_list_item_prefix(node)
            profile['wrap_indent_chars'] = 1 if profile['prefix'] else 0
            profile['prefix_bold'] = True
        if node_name in {'dd', 'blockquote', 'aside', 'figcaption', 'caption'} or note_like:
            profile['indent_chars'] = max(int(profile['indent_chars'] or 0), 1)
            profile['wrap_indent_chars'] = max(profile['wrap_indent_chars'], 1)
        css_indent = max(
            _css_length_to_chars(style_map.get('margin-left', ''), font_size),
            _css_length_to_chars(style_map.get('padding-left', ''), font_size),
            _css_length_to_chars(style_map.get('text-indent', ''), font_size),
        )
        if css_indent > 0:
            profile['indent_chars'] = max(profile['indent_chars'], css_indent)
            profile['wrap_indent_chars'] = max(profile['wrap_indent_chars'], css_indent)
        margin_top_chars = max(
            _css_length_to_chars(style_map.get('margin-top', ''), font_size),
            _css_length_to_chars(style_map.get('padding-top', ''), font_size),
        )
        if margin_top_chars > 0:
            profile['blank_before'] = max(profile['blank_before'], margin_top_chars)

    analysis = {
        'node_name': node_name,
        'heading_level': heading_level,
        'style_map': style_map,
        'attr_tokens': attr_tokens,
        'should_skip': should_skip,
        'requests_pagebreak': requests_pagebreak,
        'note_like': note_like,
        'indent_profile': profile,
        'intrinsic_bold': intrinsic_bold,
        'paragraph_like': is_paragraph_like(node),
    }
    try:
        setattr(node, cache_attr, (cache_key, analysis))
    except Exception:
        pass
    return analysis


def epub_should_skip_node(node: Any, css_rules: Sequence[CSSRule] | None = None) -> bool:
    return bool(_epub_node_analysis(node, css_rules=css_rules).get('should_skip', False))


def epub_heading_level(node: Any) -> int:
    node_name = (getattr(node, 'name', '') or '').lower()
    if re.fullmatch(r'h([1-6])', node_name):
        return int(node_name[1])
    return 0


@lru_cache(maxsize=2048)
def _parse_css_style_declarations_cached(style_text: str) -> tuple[tuple[str, str], ...]:
    declarations: list[tuple[str, str]] = []
    for chunk in style_text.split(';'):
        if ':' not in chunk:
            continue
        prop, value = chunk.split(':', 1)
        prop = prop.strip().lower()
        value = value.strip().lower()
        if prop:
            declarations.append((prop, value))
    return tuple(declarations)


def _parse_css_style_declarations(style_value: object) -> CSSDeclarations:
    return dict(_parse_css_style_declarations_cached(str(style_value or '')))


def _split_css_selectors(selector_block: object) -> list[str]:
    return [selector.strip() for selector in str(selector_block or '').split(',') if selector and selector.strip()]


def _normalize_epub_css_selector(selector: object) -> str:
    selector = str(selector or '').strip()
    if not selector:
        return ''
    selector = re.sub(r'/\*.*?\*/', '', selector)
    selector = re.sub(r'::?[A-Za-z0-9_-]+(?:\([^)]*\))?', '', selector)
    selector = re.sub(r'\[[^\]]+\]', '', selector)
    parts = [part for part in re.split(r'\s*[>+~]\s*|\s+', selector) if part]
    return parts[-1].strip() if parts else ''


@lru_cache(maxsize=2048)
def _parse_epub_css_selector_matcher(selector: str) -> tuple[str, tuple[str, ...], tuple[str, ...], bool]:
    normalized = _normalize_epub_css_selector(selector)
    if not normalized:
        return '', (), (), False
    if normalized == '*':
        return '*', (), (), True
    tag_match = re.match(r'^[A-Za-z][A-Za-z0-9_-]*|^\*', normalized)
    tag = ''
    rest = normalized
    if tag_match:
        tag = tag_match.group(0).lower()
        rest = normalized[tag_match.end():]
    if '[' in rest or ']' in rest:
        return tag, (), (), False
    ids = tuple(re.findall(r'#([A-Za-z0-9_-]+)', rest))
    classes = tuple(re.findall(r'\.([A-Za-z0-9_-]+)', rest))
    cleaned = re.sub(r'[#.][A-Za-z0-9_-]+', '', rest)
    return tag, ids, classes, not cleaned.strip()


def _epub_css_selector_matches_node(node: Any, selector: object) -> bool:
    tag, ids, classes, supported = _parse_epub_css_selector_matcher(str(selector or ''))
    if not supported or not getattr(node, 'name', None):
        return False
    if tag == '*':
        return True
    node_name = (getattr(node, 'name', '') or '').lower()
    if tag and tag != '*' and tag != node_name:
        return False
    if ids and ids[-1] != str(node.get('id', '') or ''):
        return False
    node_classes = set(str(item) for item in (node.get('class', []) or []) if item)
    if any(class_name not in node_classes for class_name in classes):
        return False
    return True


def extract_epub_css_rules(book: Any) -> list[CSSRule]:
    rules: list[CSSRule] = []
    for item in book.get_items():
        media_type = getattr(item, 'media_type', '') or ''
        file_name = getattr(item, 'file_name', '') or ''
        if 'css' not in media_type and not file_name.lower().endswith('.css'):
            continue
        try:
            css_text = item.get_content().decode('utf-8', errors='ignore')
        except Exception:
            continue
        for selector_block, declaration_block in re.findall(r'([^{}]+)\{([^{}]+)\}', css_text, re.DOTALL):
            declarations = _parse_css_style_declarations(declaration_block)
            if not declarations:
                continue
            for selector in _split_css_selectors(selector_block):
                normalized = _normalize_epub_css_selector(selector)
                if not normalized:
                    continue
                rules.append({'selector': normalized, 'declarations': dict(declarations)})
    return rules


def _epub_css_node_cache_signature(node: Any) -> tuple[str, str, tuple[str, ...], str]:
    node_name = (getattr(node, 'name', '') or '').lower()
    node_id = ''
    node_classes: tuple[str, ...] = ()
    style_text = ''
    if getattr(node, 'get', None):
        try:
            node_id = str(node.get('id', '') or '')
        except Exception:
            node_id = ''
        try:
            node_classes = tuple(str(item) for item in (node.get('class', []) or []) if item)
        except Exception:
            node_classes = ()
        try:
            style_text = str(node.get('style', '') or '')
        except Exception:
            style_text = ''
    return node_name, node_id, node_classes, style_text


def _merged_epub_css_for_node(node: Any, css_rules: Sequence[CSSRule] | None = None) -> CSSDeclarations:
    if not getattr(node, 'name', None):
        return {}
    node_signature = _epub_css_node_cache_signature(node)
    style_text = node_signature[3]
    cache_key = (id(css_rules) if css_rules is not None else 0, node_signature)
    cache_attr = '_tategaki_epub_merged_css_cache'
    cached = getattr(node, cache_attr, None)
    if isinstance(cached, tuple) and len(cached) == 2 and cached[0] == cache_key and isinstance(cached[1], dict):
        return cast(CSSDeclarations, cached[1])

    merged: CSSDeclarations = {}
    for rule in css_rules or []:
        if _epub_css_selector_matches_node(node, rule.get('selector', '')):
            merged.update(rule.get('declarations', {}))
    if style_text:
        merged.update(_parse_css_style_declarations_cached(style_text))
    try:
        setattr(node, cache_attr, (cache_key, merged))
    except Exception:
        pass
    return merged


def _font_weight_value_is_bold(value: object) -> bool:
    value = str(value or '').strip().lower()
    if value in {'bold', 'bolder'}:
        return True
    num_match = re.search(r'\d+', value)
    return bool(num_match and int(num_match.group()) >= 600)


def _css_length_to_chars(value: object, font_size: int) -> int:
    text = str(value or '').strip().lower()
    if not text or text in {'0', '0px', '0em', '0rem'}:
        return 0
    match = re.search(r'(-?\d+(?:\.\d+)?)\s*(px|em|rem|%)?', text)
    if not match:
        return 0
    number = float(match.group(1))
    unit = match.group(2) or 'px'
    if number <= 0:
        return 0
    if unit == '%':
        pixels = font_size * (number / 100.0)
    elif unit in {'em', 'rem'}:
        pixels = font_size * number
    else:
        pixels = number
    return max(0, int(round(pixels / max(1, font_size))))


def epub_node_requests_pagebreak(node: Any, css_rules: Sequence[CSSRule] | None = None) -> bool:
    return bool(_epub_node_analysis(node, css_rules=css_rules).get('requests_pagebreak', False))


def epub_pagebreak_node_is_marker(node: Any) -> bool:
    if not epub_node_requests_pagebreak(node):
        return False
    node_name = (getattr(node, 'name', '') or '').lower()
    if node_name == 'hr':
        return True
    try:
        text = node.get_text('', strip=True)
    except Exception:
        text = ''
    if text:
        return False
    for child in getattr(node, 'descendants', []):
        child_name = (getattr(child, 'name', '') or '').lower()
        if child_name in {'img', 'image', 'svg'}:
            return False
    return True


def epub_node_is_note_like(node: Any, css_rules: Sequence[CSSRule] | None = None, font_size: int = 16) -> bool:
    return bool(_epub_node_analysis(node, css_rules=css_rules, font_size=font_size).get('note_like', False))


def _epub_list_parent_meta(parent: Any) -> tuple[str, str, int]:
    parent_name = (getattr(parent, 'name', '') or '').lower()
    start_value = ''
    if getattr(parent, 'get', None):
        try:
            start_value = str(parent.get('start', '') or '')
        except Exception:
            start_value = ''
    try:
        child_count = len(getattr(parent, 'contents', []))
    except Exception:
        child_count = 0
    return parent_name, start_value, child_count


def _epub_cached_list_prefix_map(parent: Any, force_rebuild: bool = False) -> dict[int, str]:
    cache_attr = '_tategaki_epub_list_prefix_cache'
    cache_meta = _epub_list_parent_meta(parent)
    cached = getattr(parent, cache_attr, None)
    if (
        not force_rebuild
        and isinstance(cached, tuple)
        and len(cached) == 2
        and cached[0] == cache_meta
        and isinstance(cached[1], dict)
    ):
        return cast(dict[int, str], cached[1])

    parent_name = cache_meta[0]
    prefix_map: dict[int, str] = {}
    if parent_name == 'ul':
        for child in getattr(parent, 'children', []):
            if (getattr(child, 'name', '') or '').lower() == 'li':
                prefix_map[id(child)] = '・　'
    elif parent_name == 'ol':
        try:
            start = int(cache_meta[1] or '1')
        except (TypeError, ValueError):
            start = 1
        li_index = 0
        for child in getattr(parent, 'children', []):
            if (getattr(child, 'name', '') or '').lower() != 'li':
                continue
            value_text = ''
            if getattr(child, 'get', None):
                try:
                    value_text = str(child.get('value', '') or '')
                except Exception:
                    value_text = ''
            try:
                number = int(value_text)
            except (TypeError, ValueError):
                number = start + li_index
            prefix_map[id(child)] = f'{number}．　'
            li_index += 1
    try:
        setattr(parent, cache_attr, (cache_meta, prefix_map))
    except Exception:
        pass
    return prefix_map


def _epub_list_item_prefix(node: Any) -> str:
    node_name = (getattr(node, 'name', '') or '').lower()
    if node_name != 'li':
        return ''
    parent = getattr(node, 'parent', None)
    parent_name = (getattr(parent, 'name', '') or '').lower()
    if parent_name not in {'ol', 'ul'}:
        return ''
    prefix_map = _epub_cached_list_prefix_map(parent)
    if parent_name == 'ol' and getattr(node, 'get', None):
        try:
            explicit_value = str(node.get('value', '') or '')
        except Exception:
            explicit_value = ''
        if explicit_value:
            try:
                expected_prefix = f'{int(explicit_value)}．　'
            except (TypeError, ValueError):
                expected_prefix = ''
            if expected_prefix and prefix_map.get(id(node), '') != expected_prefix:
                prefix_map = _epub_cached_list_prefix_map(parent, force_rebuild=True)
                if prefix_map.get(id(node), ''):
                    return prefix_map.get(id(node), '')
                return expected_prefix
        if prefix_map.get(id(node), ''):
            return prefix_map.get(id(node), '')
        try:
            start = int(getattr(parent, 'get', lambda *_args, **_kwargs: 1)('start', 1))
        except (TypeError, ValueError):
            start = 1
        return f'{start}．　'
    return prefix_map.get(id(node), '・　' if parent_name == 'ul' else '')


def epub_node_indent_profile(node: Any, css_rules: Sequence[CSSRule] | None = None, font_size: int = 16) -> EpubIndentProfile:
    return cast(EpubIndentProfile, dict(_epub_node_analysis(node, css_rules=css_rules, font_size=font_size).get('indent_profile', {
        'indent_chars': 0,
        'wrap_indent_chars': 0,
        'prefix': '',
        'prefix_bold': False,
        'blank_before': 1,
        'heading_level': 0,
    })))


# ==========================================
# --- フォント・パス ユーティリティ ---
# ==========================================

FONT_SPEC_INDEX_TOKEN = '|index='
BUNDLED_FONT_DIR_NAMES = ('Font', 'fonts')
BUNDLED_FONT_FILE_SUFFIXES = ('.ttf', '.ttc', '.otf', '.otc')


def _bundled_font_dir_candidates() -> tuple[Path, ...]:
    app_root = Path(__file__).parent.resolve()
    return tuple((app_root / name).resolve() for name in BUNDLED_FONT_DIR_NAMES)


@lru_cache(maxsize=1)
def _existing_bundled_font_dirs() -> tuple[Path, ...]:
    return tuple(path for path in _bundled_font_dir_candidates() if path.exists() and path.is_dir())


@lru_cache(maxsize=1)
def _preferred_system_font_specs() -> tuple[str, ...]:
    specs: list[str] = []
    seen: set[str] = set()

    def add_spec(value: object, index: int = 0) -> None:
        spec = build_font_spec(value, index)
        path_value, _font_index = parse_font_spec(spec)
        if not path_value or spec in seen:
            return
        path = Path(path_value)
        if not path.exists() or not path.is_file():
            return
        seen.add(spec)
        specs.append(spec)

    for candidate in (
        ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 0),
        ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 0),
        ('/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc', 0),
        ('/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc', 0),
        ('/usr/share/fonts/truetype/arphic/uming.ttc', 0),
        ('C:/Windows/Fonts/YuGothR.ttc', 0),
        ('C:/Windows/Fonts/YuGothB.ttc', 0),
        ('C:/Windows/Fonts/msgothic.ttc', 0),
        ('C:/Windows/Fonts/msmincho.ttc', 0),
        ('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc', 0),
        ('/System/Library/Fonts/ヒラギノ明朝 ProN.ttc', 0),
        ('/System/Library/Fonts/Hiragino Sans GB.ttc', 0),
        ('/System/Library/Fonts/Supplemental/Arial Unicode.ttf', 0),
    ):
        add_spec(*candidate)

    fc_match = shutil.which('fc-match')
    if fc_match:
        for family in ('Noto Sans CJK JP', 'Noto Serif CJK JP', 'sans', 'serif', 'monospace'):
            try:
                proc = subprocess.run(
                    [fc_match, '-f', '%{file}\n', family],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    timeout=3,
                )
            except Exception:
                continue
            matched = str(proc.stdout or '').strip()
            if matched:
                add_spec(matched, 0)
    return tuple(specs)


def _pick_system_font_spec(*, prefer_bold: bool = False, prefer_serif: bool = False) -> str:
    specs = list(_preferred_system_font_specs())
    if not specs:
        return ''

    def is_serif(path_value: str) -> bool:
        lower = path_value.lower()
        return any(token in lower for token in ('serif', 'mincho', 'ming'))

    def is_bold(path_value: str) -> bool:
        lower = path_value.lower()
        return any(token in lower for token in ('bold', 'black', 'heavy', 'semibold', 'semi-bold'))

    def choose(filtered: list[str]) -> str:
        return filtered[0] if filtered else ''

    preferred = [
        spec for spec in specs
        if (is_serif(parse_font_spec(spec)[0]) == prefer_serif)
        and (is_bold(parse_font_spec(spec)[0]) == prefer_bold)
    ]
    fallback_weight = [spec for spec in specs if is_bold(parse_font_spec(spec)[0]) == prefer_bold]
    fallback_style = [spec for spec in specs if is_serif(parse_font_spec(spec)[0]) == prefer_serif]
    return choose(preferred) or choose(fallback_weight) or choose(fallback_style) or specs[0]


def _legacy_font_fallback_spec(font_value: object) -> str:
    path_value, _font_index = parse_font_spec(font_value)
    base = Path(path_value).name.lower()
    if not base:
        return ''
    prefer_serif = 'serif' in base or 'mincho' in base
    prefer_bold = any(token in base for token in ('bold', 'black', 'heavy', 'semibold', 'semi-bold'))
    if any(token in base for token in ('notosansjp', 'notoserifjp', 'msgothic', 'msmincho', 'yugoth')):
        return _pick_system_font_spec(prefer_bold=prefer_bold, prefer_serif=prefer_serif)
    return ''


@lru_cache(maxsize=1024)
def _candidate_font_paths(path_value: str) -> tuple[Path, ...]:
    candidates: list[Path] = []
    seen: set[str] = set()

    def add(path_like: Path) -> None:
        key = str(path_like)
        if key in seen:
            return
        seen.add(key)
        candidates.append(path_like)

    path = Path(path_value)
    app_root = Path(__file__).parent
    if path.is_absolute():
        add(path)
        return tuple(candidates)

    add(app_root / path)
    bundled_dirs = _bundled_font_dir_candidates()
    first_part = str(path.parts[0]).casefold() if path.parts else ''
    if first_part in {name.casefold() for name in BUNDLED_FONT_DIR_NAMES}:
        tail = Path(*path.parts[1:]) if len(path.parts) > 1 else Path()
        for font_dir in bundled_dirs:
            add(font_dir / tail if tail.parts else font_dir)
    else:
        for font_dir in bundled_dirs:
            add(font_dir / path)
    return tuple(candidates)


@lru_cache(maxsize=512)
def parse_font_spec(font_value: object) -> tuple[str, int]:
    """保存用文字列からフォントパスと TTC face index を取り出す。"""
    value = str(font_value or '').strip()
    if not value:
        return '', 0
    if FONT_SPEC_INDEX_TOKEN in value:
        base, _, index_text = value.rpartition(FONT_SPEC_INDEX_TOKEN)
        try:
            return base, max(0, int(index_text))
        except ValueError:
            return value, 0
    return value, 0


@lru_cache(maxsize=1024)
def _cached_build_font_spec(path_text: str, index: int) -> str:
    normalized_path = str(path_text or '').strip()
    if not normalized_path:
        return ''
    normalized_index = max(0, int(index or 0))
    if normalized_path.lower().endswith('.ttc') or normalized_index > 0:
        return f'{normalized_path}{FONT_SPEC_INDEX_TOKEN}{normalized_index}'
    return normalized_path


def build_font_spec(path_value: object, index: int = 0) -> str:
    """フォントパスと TTC face index を保存用文字列へ直列化する。"""
    return _cached_build_font_spec(str(path_value or ''), int(index or 0))


def _font_path_key(path_like: PathLike) -> str:
    path = Path(path_like)
    bundled_dirs = set(_bundled_font_dir_candidates())
    try:
        resolved = path.resolve()
        if resolved.parent in bundled_dirs:
            return path.name
    except Exception:
        pass
    return str(path)


def _font_name_parts(font_obj: Any) -> tuple[str, str]:
    try:
        family, style = font_obj.getname()
    except Exception:
        family, style = '', ''
    return str(family or '').strip(), str(style or '').strip()


@lru_cache(maxsize=256)
def _cached_load_truetype_font(font_path: str, font_index: int, size: int) -> Any:
    return ImageFont.truetype(font_path, size, index=font_index)


def load_truetype_font(font_value: object, size: int) -> Any:
    font_path = require_font_path(font_value)
    _font_value, font_index = parse_font_spec(font_value)
    return _cached_load_truetype_font(str(font_path), font_index, int(size))


def describe_font_value(font_value: object) -> str:
    path_value, font_index = parse_font_spec(font_value)
    if not path_value:
        return ''
    base_name = Path(path_value).name
    if not base_name.lower().endswith('.ttc'):
        return base_name
    try:
        font_obj = load_truetype_font(font_value, 12)
        family, style = _font_name_parts(font_obj)
        details = ' / '.join(part for part in (family, style) if part)
        if details:
            return f'{base_name} [{details}]'
    except Exception:
        pass
    return f'{base_name} [index {font_index}]'


@lru_cache(maxsize=128)
def _font_entries_for_value(font_value: object) -> FontEntries:
    resolved_path = resolve_font_path(font_value)
    if not resolved_path or not resolved_path.exists():
        return []

    value_key = _font_path_key(resolved_path)
    suffix = resolved_path.suffix.lower()
    if suffix != '.ttc':
        return [{
            'label': Path(value_key).name,
            'value': build_font_spec(value_key, 0),
            'path': value_key,
            'index': 0,
        }]

    entries: FontEntries = []
    seen_labels = set()
    max_faces = 16
    for font_index in range(max_faces):
        spec = build_font_spec(value_key, font_index)
        try:
            font_obj = load_truetype_font(spec, 12)
        except Exception:
            if font_index == 0 and not entries:
                entries.append({
                    'label': f'{Path(value_key).name} [index 0]',
                    'value': spec,
                    'path': value_key,
                    'index': 0,
                })
            break
        family, style = _font_name_parts(font_obj)
        details = ' / '.join(part for part in (family, style) if part)
        label = f'{Path(value_key).name} [{details}]' if details else f'{Path(value_key).name} [index {font_index}]'
        if label in seen_labels:
            label = f'{label} #{font_index}'
        seen_labels.add(label)
        entries.append({
            'label': label,
            'value': spec,
            'path': value_key,
            'index': font_index,
        })
    return entries


def get_font_entries_for_value(font_value: object) -> FontEntries:
    return list(_font_entries_for_value(font_value))


def clear_font_entry_cache() -> None:
    _font_entries_for_value.cache_clear()
    _preferred_system_font_specs.cache_clear()
    _font_scan_targets.cache_clear()
    _cached_resolve_font_path.cache_clear()
    _cached_require_font_path.cache_clear()
    get_code_font_value.cache_clear()
    _cached_load_truetype_font.cache_clear()
    _cached_render_text_glyph_image.cache_clear()
    _cached_render_text_glyph_bundle.cache_clear()
    _cached_glyph_signature.cache_clear()
    _missing_glyph_signatures.cache_clear()
    _cached_font_has_distinct_glyph.cache_clear()
    _cached_resolve_vertical_glyph_char.cache_clear()
    _cached_tate_draw_spec.cache_clear()
    _cached_horizontal_rotation_decision.cache_clear()
    _cached_reference_glyph_center.cache_clear()
    _get_reference_glyph_center.cache_clear()
    _cached_build_font_spec.cache_clear()
    _cached_resolve_cacheable_font_spec.cache_clear()
    _candidate_font_paths.cache_clear()
    _scaled_kutoten_offset.cache_clear()
    _small_kana_offset.cache_clear()
    _hanging_bottom_layout.cache_clear()
    _hanging_bottom_draw_offsets.cache_clear()
    _tate_hanging_punctuation_raise.cache_clear()
    _effective_vertical_layout_bottom_margin.cache_clear()
    _kagikakko_extra_y.cache_clear()
    _should_draw_emphasis_for_cell_cached.cache_clear()
    _should_draw_side_line_for_cell_cached.cache_clear()
    _classify_tate_draw_char.cache_clear()
    _is_render_spacing_char.cache_clear()
    _is_tatechuyoko_token.cache_clear()
    _tatechuyoko_layout_limits.cache_clear()
    _cached_text_bbox_dims.cache_clear()
    _glyph_canvas_layout.cache_clear()
    _italic_extra_width.cache_clear()
    _italic_transform_layout.cache_clear()
    _tatechuyoko_paste_offsets.cache_clear()
    _cached_tatechuyoko_candidate_dims.cache_clear()
    _cached_tatechuyoko_fit_size.cache_clear()
    _cached_tatechuyoko_bundle.cache_clear()
    _split_ruby_text_segments_cached.cache_clear()
    _tokenize_vertical_text_cached.cache_clear()
    _build_single_token_vertical_layout_hints.cache_clear()
    _build_two_token_vertical_layout_hints.cache_clear()
    _build_three_token_vertical_layout_hints.cache_clear()
    _build_four_token_vertical_layout_hints.cache_clear()
    _build_vertical_layout_hints_cached.cache_clear()


@lru_cache(maxsize=1)
def _font_scan_targets() -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()

    def add(value: object) -> None:
        spec = build_font_spec(*parse_font_spec(value))
        if not spec or spec in seen:
            return
        seen.add(spec)
        values.append(spec)

    for font_dir in _existing_bundled_font_dirs():
        font_paths: list[Path] = []
        for suffix in BUNDLED_FONT_FILE_SUFFIXES:
            font_paths.extend(font_dir.glob(f'*{suffix}'))
        for font_path in sorted(font_paths, key=lambda path: path.name.lower()):
            add(str(font_path))
    for spec in _preferred_system_font_specs():
        add(spec)
    return tuple(values)


def get_font_entries() -> FontEntries:
    entries: FontEntries = []
    seen_values = set()
    for font_value in _font_scan_targets():
        for entry in _font_entries_for_value(font_value):
            value = entry['value']
            if value in seen_values:
                continue
            seen_values.add(value)
            entries.append(entry)
    return entries


def get_font_list() -> list[str]:
    fonts = [entry['value'] for entry in get_font_entries()]
    return fonts if fonts else ['(フォントなし)']


@lru_cache(maxsize=512)
def _cached_resolve_font_path(font_spec: str) -> str:
    path_value, _font_index = parse_font_spec(font_spec)
    if not path_value:
        return ''
    for candidate in _candidate_font_paths(path_value):
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    fallback_spec = _legacy_font_fallback_spec(font_spec)
    if fallback_spec:
        fallback_path, _fallback_index = parse_font_spec(fallback_spec)
        fallback = Path(fallback_path)
        if fallback.exists() and fallback.is_file():
            return str(fallback)
    fallback = Path(path_value)
    if not fallback.is_absolute():
        return str(_candidate_font_paths(path_value)[-1])
    return str(fallback)


def resolve_font_path(font_value: object) -> Path | None:
    font_spec = build_font_spec(*parse_font_spec(font_value))
    if not font_spec:
        return None
    resolved = _cached_resolve_font_path(font_spec)
    return Path(resolved) if resolved else None


@lru_cache(maxsize=512)
def _cached_require_font_path(font_spec: str) -> str:
    font_path = resolve_font_path(font_spec)
    if not font_path:
        raise RuntimeError("フォントが指定されていません。")
    if not font_path.exists():
        raise RuntimeError(f"フォントが見つかりません: {font_path}")
    if not font_path.is_file():
        raise RuntimeError(f"フォントパスが不正です: {font_path}")
    return str(font_path)


def require_font_path(font_value: object) -> Path:
    """有効なフォントパスを返し、未指定や欠落時は分かりやすい例外を送出する。"""
    font_spec = build_font_spec(*parse_font_spec(font_value))
    if not font_spec:
        raise RuntimeError("フォントが指定されていません。")
    return Path(_cached_require_font_path(font_spec))


@lru_cache(maxsize=64)
def get_code_font_value(primary_font_value: str = '') -> str:
    """コードブロック向けに使える等幅寄りフォントを探す。見つからない場合は元のフォントを返す。"""
    candidates: list[str] = []
    preferred_paths = [
        Path('C:/Windows/Fonts/msgothic.ttc'),
        Path('C:/Windows/Fonts/consola.ttf'),
        Path('C:/Windows/Fonts/cascadiamono.ttf'),
        Path('C:/Windows/Fonts/lucon.ttf'),
        Path('C:/Windows/Fonts/cour.ttf'),
    ]
    seen = set()

    def add_candidate(value: object) -> None:
        value = str(value or '').strip()
        if not value or value in seen:
            return
        seen.add(value)
        candidates.append(value)

    for pref in preferred_paths:
        if pref.exists():
            add_candidate(str(pref))

    for app_font_dir in _existing_bundled_font_dirs():
        for font_file in sorted(app_font_dir.glob('*')):
            if not font_file.is_file():
                continue
            lower_name = font_file.name.lower()
            if any(token in lower_name for token in ('mono', 'code', 'courier', 'consola', 'gothic')):
                add_candidate(str(font_file))

    add_candidate(primary_font_value)

    for candidate in candidates:
        try:
            load_truetype_font(candidate, 12)
            if candidate == str(primary_font_value or '').strip() and candidate:
                LOGGER.warning('コードブロック用の等幅寄りフォントが見つからず、本文フォントを使用します: %s', candidate)
            return candidate
        except Exception:
            continue
    if primary_font_value:
        LOGGER.warning('コードブロック用フォントが見つからず、指定フォントをそのまま使用します: %s', primary_font_value)
    else:
        LOGGER.warning('コードブロック用フォントが見つかりませんでした。')
    return primary_font_value


# ==========================================
# --- 変換対象ユーティリティ ---
# ==========================================

def iter_conversion_targets(target_path: PathLike, recursive: bool = True) -> list[Path]:
    target_path = Path(target_path)
    if target_path.is_file():
        return [target_path]
    if target_path.is_dir():
        walker = target_path.rglob('*') if recursive else target_path.iterdir()
        files = [
            p for p in walker
            if p.is_file() and not should_skip_conversion_target(p)
        ]
        return sorted(files, key=lambda p: _natural_sort_key(p.relative_to(target_path)))
    return []


def should_skip_conversion_target(path: PathLike) -> bool:
    path = Path(path)
    return path.suffix.lower() in {".xtc", ".xtch"}


def _normalize_output_format(value: object) -> str:
    fmt = str(value or 'xtc').strip().lower()
    return 'xtch' if fmt == 'xtch' else 'xtc'

def get_output_path_for_target(path: PathLike, output_format: str = 'xtc', output_root: PathLike | None = None) -> Path | None:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_INPUT_SUFFIXES:
        return None
    ext = '.xtch' if _normalize_output_format(output_format) == 'xtch' else '.xtc'
    if output_root:
        output_root = Path(output_root)
        try:
            relative = path.resolve().relative_to(output_root.resolve())
            flat_stem = _build_flat_output_stem_from_relative(relative)
            return output_root / f'{flat_stem}{ext}'
        except Exception as exc:
            fallback_stem = _build_fallback_output_stem(path)
            LOGGER.warning('output_root に対する相対パスを解決できなかったため、出力先を選択フォルダ直下へフォールバックします: path=%s output_root=%s reason=%s', path, output_root, exc)
            return output_root / f'{fallback_stem}{ext}'
    return path.with_suffix(ext)


def make_unique_output_path(path: PathLike) -> Path:
    path = Path(path)
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    idx = 1
    while True:
        candidate = path.with_name(f"{stem}({idx}){suffix}")
        if not candidate.exists():
            return candidate
        idx += 1


def resolve_output_path_with_conflict(path: PathLike, strategy: str = 'rename') -> tuple[Path, ConflictPlan]:
    path = Path(path)
    normalized = str(strategy or 'rename').strip().lower()
    if normalized not in {'rename', 'overwrite', 'error'}:
        normalized = 'rename'
    existed = path.exists()
    if normalized == 'overwrite':
        final_path = path
    elif normalized == 'error':
        if existed:
            raise RuntimeError(f'保存先に同名ファイルがあります: {path.name}')
        final_path = path
    else:
        final_path = make_unique_output_path(path)
    plan: ConflictPlan = {
        'desired_path': str(path),
        'final_path': str(final_path),
        'conflict': existed,
        'renamed': str(final_path) != str(path),
        'overwritten': existed and normalized == 'overwrite',
        'strategy': normalized,
    }
    return final_path, plan


def find_output_conflicts(targets: Sequence[PathLike], output_format: str = 'xtc') -> list[tuple[PathLike, Path]]:
    conflicts: list[tuple[PathLike, Path]] = []
    for path in targets:
        out_path = get_output_path_for_target(path, output_format)
        if out_path and out_path.exists():
            conflicts.append((path, out_path))
    return conflicts


# ==========================================
# --- 画像フィルタ & XTG/XTC 変換 ---
# ==========================================

def _prepare_canvas_image(img: Image.Image, w: int, h: int) -> Image.Image:
    if img.mode == 'L' and img.size == (w, h):
        return img
    work = img if img.mode == 'L' else img.convert('L')
    if work.size != (w, h):
        work = work.copy()
        work.thumbnail((w, h), Image.Resampling.LANCZOS)
    background = Image.new('L', (w, h), 255)
    offset = ((w - work.width) // 2, (h - work.height) // 2)
    background.paste(work, offset)
    return background


def _clamp_u8(value: int) -> int:
    if value < 0:
        return 0
    if value > 255:
        return 255
    return value


@lru_cache(maxsize=64)
def _compute_xtch_thresholds(threshold: int) -> tuple[int, int, int]:
    bias = max(-48, min(48, int(threshold) - 128))
    t1 = max(16, min(96, 64 + bias // 2))
    t2 = max(t1 + 16, min(176, 128 + bias))
    t3 = max(t2 + 16, min(240, 192 + bias // 2))
    return t1, t2, t3


@lru_cache(maxsize=256)
def _xtc_threshold_lut(threshold: int) -> tuple[int, ...]:
    thr = int(threshold)
    return tuple(255 if value > thr else 0 for value in range(256))


@lru_cache(maxsize=64)
def _xtch_quantization_lut(threshold: int) -> tuple[int, ...]:
    t1, t2, t3 = _compute_xtch_thresholds(int(threshold))
    return tuple(_quantize_xtch_value(value, t1, t2, t3) for value in range(256))


@lru_cache(maxsize=1)
def _xtch_plane_value_lut() -> tuple[int, ...]:
    return tuple(0 if value >= 213 else 2 if value >= 128 else 1 if value >= 43 else 3 for value in range(256))


@lru_cache(maxsize=1)
def _invert_u8_lut() -> tuple[int, ...]:
    return tuple(255 - value for value in range(256))


def _invert_grayscale_image(image: Image.Image) -> Image.Image:
    if image.mode == 'L':
        return image.point(_invert_u8_lut(), mode='L')
    return ImageOps.invert(image.convert('L'))


def _quantize_xtch_value(v: int, t1: int, t2: int, t3: int) -> int:
    if v <= t1:
        return 0
    if v <= t2:
        return 85
    if v <= t3:
        return 170
    return 255


def _dither_xtch_grayscale(background: Image.Image, w: int, h: int, t1: int, t2: int, t3: int) -> Image.Image:
    buf = bytearray(background.tobytes())
    row_base = 0
    for _y in range(h):
        next_row_base = row_base + w
        row_end = row_base + w
        for idx in range(row_base, row_end):
            old = buf[idx]
            newv = _quantize_xtch_value(old, t1, t2, t3)
            err = old - newv
            buf[idx] = newv
            x = idx - row_base
            if x + 1 < w:
                right = idx + 1
                buf[right] = _clamp_u8(int(buf[right] + err * 7 / 16))
            if next_row_base < len(buf):
                below = next_row_base + x
                if x > 0:
                    below_left = below - 1
                    buf[below_left] = _clamp_u8(int(buf[below_left] + err * 3 / 16))
                buf[below] = _clamp_u8(int(buf[below] + err * 5 / 16))
                if x + 1 < w:
                    below_right = below + 1
                    buf[below_right] = _clamp_u8(int(buf[below_right] + err * 1 / 16))
        row_base = next_row_base
    return Image.frombytes('L', (w, h), bytes(buf))


def _prepared_canvas_to_xtg_bytes(background: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    row_bytes = (w + 7) // 8
    threshold = int(args.threshold)
    night_mode = bool(getattr(args, 'night_mode', False))
    np_module = _get_numpy_module()
    if not args.dither and np_module is not None and (w * h) >= 256:
        arr = np_module.asarray(background, dtype=np_module.uint8)
        packed = np_module.packbits((arr > threshold).astype(np_module.uint8), axis=1, bitorder='big')
        if night_mode:
            np_module.bitwise_xor(packed, 0xFF, out=packed)
            rem = w & 7
            if rem:
                valid_mask = (0xFF << (8 - rem)) & 0xFF
                packed[:, -1] &= valid_mask
        data = bytearray(packed.tobytes())
    else:
        bw_img = background.convert('1', dither=Image.FLOYDSTEINBERG) if args.dither else background.point(_xtc_threshold_lut(threshold), mode='1')
        data = bytearray(bw_img.tobytes())
        if night_mode:
            for idx in range(len(data)):
                data[idx] ^= 0xFF
            rem = w & 7
            if rem:
                valid_mask = (0xFF << (8 - rem)) & 0xFF
                for row in range(h):
                    data[row * row_bytes + (row_bytes - 1)] &= valid_mask
    md5 = hashlib.md5(data).digest()[:8]
    return struct.pack('<4sHHBBI8s', b'XTG\x00', w, h, 0, 0, len(data), md5) + data


def _prepared_canvas_to_xth_bytes(background: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    threshold = int(args.threshold)
    t1, t2, t3 = _compute_xtch_thresholds(threshold)
    if args.dither:
        gray_img = _dither_xtch_grayscale(background, w, h, t1, t2, t3)
    else:
        gray_img = background.point(_xtch_quantization_lut(threshold), mode='L')
    if getattr(args, 'night_mode', False):
        gray_img = _invert_grayscale_image(gray_img)
    plane_size = ((w * h) + 7) // 8
    plane_value_lut = _xtch_plane_value_lut()

    np_module = _get_numpy_module()
    if np_module is not None and (w * h) >= 256:
        arr = np_module.asarray(gray_img, dtype=np_module.uint8)
        vals = np_module.asarray(plane_value_lut, dtype=np_module.uint8)[arr]
        seq = vals[:, ::-1].T.reshape(-1)
        plane1 = np_module.packbits((seq >> 1) & 1, bitorder='big')
        plane2 = np_module.packbits(seq & 1, bitorder='big')
        data = plane1.tobytes() + plane2.tobytes()
        if len(plane1) != plane_size or len(plane2) != plane_size:
            data = data[:plane_size] + data[plane_size:plane_size * 2]
    else:
        pixels = gray_img.load()
        assert pixels is not None
        plane1 = bytearray(plane_size)
        plane2 = bytearray(plane_size)
        bit_index = 0
        for x in range(w - 1, -1, -1):
            for y in range(h):
                val = plane_value_lut[int(pixels[x, y])]
                byte_index = bit_index >> 3
                shift = 7 - (bit_index & 7)
                if (val >> 1) & 1:
                    plane1[byte_index] |= 1 << shift
                if val & 1:
                    plane2[byte_index] |= 1 << shift
                bit_index += 1
        data = bytes(plane1 + plane2)
    md5 = hashlib.md5(data).digest()[:8]
    return struct.pack('<4sHHBBI8s', b'XTH\x00', w, h, 0, 0, len(data), md5) + data


def canvas_image_to_xt_bytes(background: Image.Image, w: int, h: int, args: ConversionArgs, *, prepared: bool = False) -> bytes:
    canvas = background if prepared else _prepare_canvas_image(background, w, h)
    return _prepared_canvas_to_xth_bytes(canvas, w, h, args) if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else _prepared_canvas_to_xtg_bytes(canvas, w, h, args)


def _apply_xtc_filter_prepared(background: Image.Image, dither: bool, threshold: int) -> Image.Image:
    if dither:
        return background.convert("1", dither=Image.FLOYDSTEINBERG)  # type: ignore[attr-defined]
    return background.point(_xtc_threshold_lut(int(threshold)), mode="1")


def _apply_xtch_filter_prepared(background: Image.Image, dither: bool, threshold: int, w: int, h: int) -> Image.Image:
    t1, t2, t3 = _compute_xtch_thresholds(int(threshold))
    if dither:
        return _dither_xtch_grayscale(background, w, h, t1, t2, t3)
    return background.point(_xtch_quantization_lut(int(threshold)), mode='L')


def apply_xtc_filter(img: Image.Image, dither: bool, threshold: int, w: int, h: int) -> Image.Image:
    return _apply_xtc_filter_prepared(_prepare_canvas_image(img, w, h), dither, threshold)


def apply_xtch_filter(img: Image.Image, dither: bool, threshold: int, w: int, h: int) -> Image.Image:
    return _apply_xtch_filter_prepared(_prepare_canvas_image(img, w, h), dither, threshold, w, h)


def png_to_xtg_bytes(img: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    return _prepared_canvas_to_xtg_bytes(_prepare_canvas_image(img, w, h), w, h, args)


def png_to_xth_bytes(img: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    return _prepared_canvas_to_xth_bytes(_prepare_canvas_image(img, w, h), w, h, args)


def _verify_xt_page_blob_header(blob_header: bytes, page_length: int, expected_w: int, expected_h: int, normalized_format: str, page_index: int) -> None:
    if len(blob_header) < 22:
        raise RuntimeError(f'自己検証に失敗しました: ページ {page_index} のページデータヘッダが不足しています。')
    expected_magic = b'XTH\x00' if normalized_format == 'xtch' else b'XTG\x00'
    magic = blob_header[:4]
    if magic != expected_magic:
        raise RuntimeError(
            f'自己検証に失敗しました: ページ {page_index} のデータ種別が不正です。 expected={expected_magic!r} actual={magic!r}'
        )
    blob_w = struct.unpack_from('<H', blob_header, 4)[0]
    blob_h = struct.unpack_from('<H', blob_header, 6)[0]
    payload_len = struct.unpack_from('<I', blob_header, 10)[0]
    if blob_w != expected_w or blob_h != expected_h:
        raise RuntimeError(
            f'自己検証に失敗しました: ページ {page_index} のサイズ情報が不正です。 expected={expected_w}x{expected_h} actual={blob_w}x{blob_h}'
        )
    if payload_len <= 0 or (22 + payload_len) != page_length:
        raise RuntimeError(
            f'自己検証に失敗しました: ページ {page_index} のペイロード長が不正です。 page_length={page_length} payload={payload_len}'
        )



def _verify_xt_container_file(path: Path, expected_w: int, expected_h: int, output_format: str, expected_count: int | None = None) -> int:
    normalized_format = _normalize_output_format(output_format)
    expected_mark = b'XTCH' if normalized_format == 'xtch' else b'XTC\x00'
    with open(path, 'rb') as fh:
        fh.seek(0, os.SEEK_END)
        file_size = fh.tell()
        fh.seek(0)
        header = fh.read(48)
        if len(header) < 48:
            raise RuntimeError('自己検証に失敗しました: XTC/XTCHヘッダが途中で切れています。')
        mark = header[:4]
        if mark != expected_mark:
            raise RuntimeError(
                f'自己検証に失敗しました: コンテナ種別が不正です。 expected={expected_mark!r} actual={mark!r}'
            )
        count = struct.unpack_from('<H', header, 6)[0]
        idx_off = struct.unpack_from('<Q', header, 24)[0] or 48
        data_off = struct.unpack_from('<Q', header, 32)[0] or (48 + count * 16)
        if expected_count is not None and count != int(expected_count):
            raise RuntimeError(
                f'自己検証に失敗しました: ページ数が一致しません。 expected={expected_count} actual={count}'
            )
        if count <= 0:
            raise RuntimeError('自己検証に失敗しました: ページ数が 0 です。')
        if idx_off < 48 or idx_off > file_size:
            raise RuntimeError(f'自己検証に失敗しました: ページテーブル開始位置が不正です。 idx_off={idx_off}')
        if data_off < idx_off + count * 16 or data_off > file_size:
            raise RuntimeError(f'自己検証に失敗しました: ページデータ開始位置が不正です。 data_off={data_off}')
        prev_end = data_off
        for page_index in range(1, count + 1):
            fh.seek(idx_off + (page_index - 1) * 16)
            entry = fh.read(16)
            if len(entry) != 16:
                raise RuntimeError(f'自己検証に失敗しました: ページ {page_index} の索引が途中で切れています。')
            offset, length, width, height = struct.unpack('<Q I H H', entry)
            end = offset + length
            if (
                length <= 0
                or width != expected_w
                or height != expected_h
                or offset < data_off
                or offset < prev_end
                or end > file_size
            ):
                raise RuntimeError(
                    f'自己検証に失敗しました: ページ {page_index} の索引が不正です。 '
                    f'offset={offset} length={length} width={width} height={height} file_size={file_size}'
                )
            fh.seek(offset)
            blob_header = fh.read(22)
            _verify_xt_page_blob_header(blob_header, length, expected_w, expected_h, normalized_format, page_index)
            prev_end = end
        if prev_end != file_size:
            raise RuntimeError(
                '自己検証に失敗しました: 最終ページ終端とファイルサイズが一致しません。 '
                f'page_end={prev_end} file_size={file_size}'
            )
    return count



def _atomic_replace_xt_container(out_path: Path, writer: Callable[[BinaryIO], None], verifier: Callable[[Path], None] | None = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_handle = tempfile.NamedTemporaryFile(prefix=f'{out_path.stem}_', suffix='.partial', dir=str(out_path.parent), delete=False)
    tmp_path = Path(tmp_handle.name)
    try:
        with tmp_handle:
            writer(tmp_handle)
            tmp_handle.flush()
            os.fsync(tmp_handle.fileno())
        if verifier is not None:
            verifier(tmp_path)
        os.replace(tmp_path, out_path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def build_xtc(page_blobs: Sequence[bytes], out_path: PathLike, w: int, h: int, output_format: str = 'xtc', should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None) -> None:
    _raise_if_cancelled(should_cancel)
    cnt = len(page_blobs)
    if cnt == 0:
        raise ValueError("変換データがありません。")
    _emit_progress(progress_cb, 0, cnt * 2 + 1, f'XTCを書き出す準備をしています… (0/{cnt} ページ)')
    idx_off = 48
    data_off = 48 + cnt * 16
    idx_table = bytearray()
    curr_off = data_off
    total_steps = cnt * 2 + 1
    for idx, b in enumerate(page_blobs, 1):
        _raise_if_cancelled(should_cancel)
        idx_table += struct.pack("<Q I H H", curr_off, len(b), w, h)
        curr_off += len(b)
        _emit_progress(progress_cb, idx, total_steps, f'XTC索引を作成中… ({idx}/{cnt} ページ)')
    mark = b"XTCH" if _normalize_output_format(output_format) == 'xtch' else b"XTC\x00"
    header = struct.pack("<4sHHBBBBIQQQQ", mark, 1, cnt, 1, 0, 0, 0, 0, 0, idx_off, data_off, 0)

    out_path = Path(out_path)

    def _writer(dst: BinaryIO) -> None:
        dst.write(header)
        dst.write(idx_table)
        for idx, blob in enumerate(page_blobs, 1):
            _raise_if_cancelled(should_cancel)
            dst.write(blob)
            _emit_progress(progress_cb, cnt + idx, total_steps, f'XTCページデータを書き込み中… ({idx}/{cnt} ページ)')

    normalized_output_format = _normalize_output_format(output_format)
    _atomic_replace_xt_container(
        out_path,
        _writer,
        verifier=lambda tmp_path: _verify_xt_container_file(tmp_path, w, h, normalized_output_format, expected_count=cnt),
    )
    _emit_progress(progress_cb, total_steps, total_steps, f'XTCを書き出しました。({cnt} ページ)')


def page_image_to_xt_bytes(img: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    return canvas_image_to_xt_bytes(img, w, h, args)


def _copy_fileobj_with_cancel(
    src: BinaryIO,
    dst: BinaryIO,
    *,
    should_cancel: CancelCallback | None = None,
    chunk_size: int = 1024 * 1024,
) -> int:
    """copyfileobj 相当の逐次コピーに中止判定を挟む。"""
    copied = 0
    while True:
        _raise_if_cancelled(should_cancel)
        chunk = src.read(max(1, int(chunk_size)))
        if not chunk:
            break
        dst.write(chunk)
        copied += len(chunk)
    _raise_if_cancelled(should_cancel)
    return copied


def _looks_like_expected_xt_page_blob(blob: object, expected_w: int, expected_h: int, args: ConversionArgs) -> bool:
    if not isinstance(blob, (bytes, bytearray, memoryview)):
        return False
    blob_bytes = bytes(blob)
    if len(blob_bytes) < 22:
        return False
    expected_magic = b'XTH\x00' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else b'XTG\x00'
    if blob_bytes[:4] != expected_magic:
        return False
    try:
        blob_w = struct.unpack_from('<H', blob_bytes, 4)[0]
        blob_h = struct.unpack_from('<H', blob_bytes, 6)[0]
        payload_len = struct.unpack_from('<I', blob_bytes, 10)[0]
    except struct.error:
        return False
    if blob_w != int(expected_w) or blob_h != int(expected_h):
        return False
    return payload_len > 0 and (22 + payload_len) == len(blob_bytes)


def ensure_valid_xt_page_blob(blob: object, page_image: Image.Image, w: int, h: int, args: ConversionArgs) -> bytes:
    if _looks_like_expected_xt_page_blob(blob, w, h, args):
        return bytes(blob)
    return canvas_image_to_xt_bytes(page_image, w, h, args)


class XTCSpooledPages:
    """ページデータを一時ファイルへ退避しながら XTC / XTCH を組み立てる。"""

    def __init__(self: XTCSpooledPages) -> None:
        self._tmp = tempfile.NamedTemporaryFile(prefix='tategaki_xtc_pages_', suffix='.bin', delete=False)
        self._tmp_path = Path(self._tmp.name)
        self.page_sizes: list[int] = []
        self.page_count = 0
        self.total_blob_bytes = 0
        self._closed = False

    def add_blob(self: XTCSpooledPages, blob: bytes | bytearray | memoryview | None) -> None:
        if not blob or self._closed:
            return
        self._tmp.write(blob)
        self.page_sizes.append(len(blob))
        self.page_count += 1
        self.total_blob_bytes += len(blob)

    def close(self: XTCSpooledPages) -> None:
        if not self._closed:
            self._tmp.flush()
            self._tmp.close()
            self._closed = True

    def __enter__(self: XTCSpooledPages) -> XTCSpooledPages:
        return self

    def __exit__(self: XTCSpooledPages, exc_type: type[BaseException] | None, exc: BaseException | None, tb: object) -> Literal[False]:
        self.cleanup()
        return False

    def __del__(self: XTCSpooledPages) -> None:
        try:
            self.cleanup()
        except Exception:
            pass

    def cleanup(self: XTCSpooledPages) -> None:
        try:
            self.close()
        finally:
            try:
                if self._tmp_path.exists():
                    self._tmp_path.unlink()
            except OSError:
                pass

    def finalize(self: XTCSpooledPages, out_path: PathLike, w: int, h: int, output_format: str = 'xtc', should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None) -> None:
        _raise_if_cancelled(should_cancel)
        self.close()
        cnt = self.page_count
        if cnt == 0:
            raise ValueError('変換データがありません。')

        _emit_progress(progress_cb, 0, cnt * 2 + 1, f'XTCを書き出す準備をしています… (0/{cnt} ページ)')
        idx_off = 48
        data_off = 48 + cnt * 16
        idx_table = bytearray()
        curr_off = data_off
        total_steps = cnt * 2 + 1
        for idx, size in enumerate(self.page_sizes, 1):
            _raise_if_cancelled(should_cancel)
            idx_table += struct.pack('<Q I H H', curr_off, size, w, h)
            curr_off += size
            _emit_progress(progress_cb, idx, total_steps, f'XTC索引を作成中… ({idx}/{cnt} ページ)')

        mark = b'XTCH' if _normalize_output_format(output_format) == 'xtch' else b'XTC\x00'
        header = struct.pack('<4sHHBBBBIQQQQ', mark, 1, cnt, 1, 0, 0, 0, 0, 0, idx_off, data_off, 0)
        out_path = Path(out_path)

        def _writer(dst: BinaryIO) -> None:
            dst.write(header)
            dst.write(idx_table)
            with open(self._tmp_path, 'rb') as src:
                if callable(progress_cb):
                    for idx, size in enumerate(self.page_sizes, 1):
                        _raise_if_cancelled(should_cancel)
                        blob = src.read(size)
                        if len(blob) != size:
                            raise RuntimeError('一時ページデータの読み込みに失敗しました。')
                        dst.write(blob)
                        _emit_progress(progress_cb, cnt + idx, total_steps, f'XTCページデータを書き込み中… ({idx}/{cnt} ページ)')
                else:
                    _copy_fileobj_with_cancel(src, dst, should_cancel=should_cancel, chunk_size=1024 * 1024)

        normalized_output_format = _normalize_output_format(output_format)
        try:
            _atomic_replace_xt_container(
                out_path,
                _writer,
                verifier=lambda tmp_path: _verify_xt_container_file(tmp_path, w, h, normalized_output_format, expected_count=cnt),
            )
        finally:
            self.cleanup()

        _emit_progress(progress_cb, total_steps, total_steps, f'XTCを書き出しました。({cnt} ページ)')


# ==========================================
# --- プレビュー生成 ---
# ==========================================

def _build_default_preview_blocks() -> TextBlocks:
    """プレビュー専用の代表サンプルを TextBlock 形式で返す。"""
    # 青空文庫『吾輩は猫である』公開 XHTML の冒頭段落構成に合わせて、
    # 文中の不必要な改行を入れず、段落単位でプレビュー用に構成する。
    return [
        {
            "indent": True,
            "blank_before": 0,
            "runs": [
                {"text": "吾輩", "ruby": "わがはい", "bold": False},
                {"text": "は猫である。名前はまだ無い。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "どこで生れたかとんと", "ruby": "", "bold": False},
                {"text": "見当", "ruby": "けんとう", "bold": False},
                {"text": "がつかぬ。何でも薄暗いじめじめした所でニャーニャー泣いていた事だけは", "ruby": "", "bold": False},
                {"text": "記憶", "ruby": "きおく", "bold": False},
                {"text": "している。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "吾輩はここで始めて人間というものを見た。しかもあとで聞くとそれは書生という人間中で一番", "ruby": "", "bold": False},
                {"text": "獰悪", "ruby": "どうあく", "bold": False},
                {"text": "な種族であったそうだ。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "この書生というのは時々我々を", "ruby": "", "bold": False},
                {"text": "捕", "ruby": "つかま", "bold": False},
                {"text": "えて", "ruby": "", "bold": False},
                {"text": "煮", "ruby": "に", "bold": False},
                {"text": "て食うという話である。しかしその当時は何という考もなかったから別段恐しいとも思わなかった。ただ彼の", "ruby": "", "bold": False},
                {"text": "掌", "ruby": "てのひら", "bold": False},
                {"text": "に載せられてスーと持ち上げられた時何だかフワフワした感じがあったばかりである。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "掌", "ruby": "てのひら", "bold": False},
                {"text": "の上で少し落ちついて書生の顔を見たのがいわゆる人間というものの", "ruby": "", "bold": False},
                {"text": "見始", "ruby": "みはじめ", "bold": False},
                {"text": "であろう。この時妙なものだと思った感じが今でも残っている。第一毛をもって装飾されべきはずの顔がつるつるしてまるで", "ruby": "", "bold": False},
                {"text": "薬缶", "ruby": "やかん", "bold": False},
                {"text": "だ。その後猫にもだいぶ逢ったがこんな", "ruby": "", "bold": False},
                {"text": "片輪", "ruby": "かたわ", "bold": False},
                {"text": "には一度も出会わした事がない。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "のみならず顔の真中があまりに突起している。そうしてその穴の中から時々ぷうぷうと", "ruby": "", "bold": False},
                {"text": "煙", "ruby": "けむり", "bold": False},
                {"text": "を吹く。どうも", "ruby": "", "bold": False},
                {"text": "咽", "ruby": "む", "bold": False},
                {"text": "せぽくて実に弱った。これが人間の飲む", "ruby": "", "bold": False},
                {"text": "煙草", "ruby": "たばこ", "bold": False},
                {"text": "というものである事はようやくこの頃知った。", "ruby": "", "bold": False},
            ],
        },
        {
            "indent": True,
            "blank_before": 1,
            "runs": [
                {"text": "この書生の掌の", "ruby": "", "bold": False},
                {"text": "裏", "ruby": "うち", "bold": False},
                {"text": "でしばらくはよい心持に坐っておったが、しばらくすると非常な速力で運転し始めた。", "ruby": "", "bold": False},
            ],
        },
    ]


def _resolve_preview_source_paths(target_path: PathLike | None) -> list[Path]:
    target_raw = str(target_path or '').strip()
    if not target_raw:
        return []
    path = Path(target_raw)
    if not path.exists():
        return []
    if path.is_file():
        suffix = path.suffix.lower()
        return [path] if suffix in SUPPORTED_INPUT_SUFFIXES or suffix in IMG_EXTS else []
    if not path.is_dir():
        return []

    conversion_sources = [
        p for p in iter_conversion_targets(path)
        if p.suffix.lower() in SUPPORTED_INPUT_SUFFIXES
    ]
    if conversion_sources:
        return conversion_sources

    image_sources = [
        p for p in path.rglob('*')
        if p.is_file() and p.suffix.lower() in IMG_EXTS and not should_skip_conversion_target(p)
    ]
    return sorted(image_sources, key=lambda p: _natural_sort_key(p.relative_to(path)))


def _resolve_preview_source_path(target_path: PathLike | None) -> Path | None:
    sources = _resolve_preview_source_paths(target_path)
    return sources[0] if sources else None


def _select_preview_blocks(blocks: Sequence[TextBlock] | None, *, max_blocks: int = 6) -> TextBlocks:
    selected: TextBlocks = []
    nonblank_count = 0
    for block in blocks or []:
        kind = str(block.get('kind', '') or '') if isinstance(block, dict) else ''
        if kind == 'blank':
            if selected:
                selected.append(block)
            continue
        runs = block.get('runs', []) if isinstance(block, dict) else []
        if not any(str(run.get('text', '') or '') for run in runs):
            continue
        selected.append(block)
        nonblank_count += 1
        if nonblank_count >= max_blocks:
            break
    return selected or _build_default_preview_blocks()


def _preview_fit_image(src_img: Image.Image, args: ConversionArgs) -> Image.Image:
    return _prepare_canvas_image(src_img, args.width, args.height)


def _preview_source_requires_font(preview_source: Path | None) -> bool:
    if preview_source is None:
        return True
    suffix = str(getattr(preview_source, 'suffix', '') or '').lower()
    if suffix in IMG_EXTS or suffix in {'.zip', '.cbz', '.cbr', '.rar'}:
        return False
    return True


def _preview_target_requires_font(target_path: PathLike | None, *, preview_sources: Sequence[Path] | None = None) -> bool:
    sources = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
    if not sources:
        return True
    return any(_preview_source_requires_font(source) for source in sources)


class _PreviewPageLimitReached(RuntimeError):
    """Raised internally to stop preview rendering once the requested page limit is reached."""


def _render_preview_pages_from_target(target_path: PathLike | None, font_value: str | Path, preview_args: ConversionArgs, *, max_pages: int = PREVIEW_PAGE_LIMIT, progress_cb: ProgressCallback | None = None, preview_sources: Sequence[Path] | None = None) -> tuple[list[Image.Image], bool]:
    resolved_preview_sources = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
    preview_source = resolved_preview_sources[0] if resolved_preview_sources else None
    blank_page = Image.new('L', (preview_args.width, preview_args.height), 255)
    max_pages = max(1, int(max_pages or PREVIEW_PAGE_LIMIT))
    truncated = False

    if len(resolved_preview_sources) > 1:
        page_images: list[Image.Image] = []
        total_sources = len(resolved_preview_sources)
        for source_index, source_path in enumerate(resolved_preview_sources, 1):
            if len(page_images) >= max_pages:
                truncated = True
                break
            remaining_pages = max_pages - len(page_images)
            _emit_progress(progress_cb, source_index - 1, total_sources, f'フォルダ内のプレビュー対象を処理中… ({source_index - 1}/{total_sources} 件)')
            source_pages, source_truncated = _render_preview_pages_from_target(
                source_path,
                font_value,
                preview_args,
                max_pages=remaining_pages,
                progress_cb=progress_cb,
            )
            for page_image in source_pages:
                if len(page_images) >= max_pages:
                    truncated = True
                    break
                page_images.append(page_image)
            if source_truncated:
                truncated = True
                break
        return (page_images if page_images else [blank_page.copy()]), truncated

    if preview_source is None:
        target_raw = str(target_path or '').strip()
        if target_raw:
            target_candidate = Path(target_raw)
            if not target_candidate.exists():
                raise RuntimeError('プレビュー対象が見つかりません。対応ファイルが含まれているか確認してください。')
        render_state: dict[str, object] = {}
        page_images = _render_text_blocks_to_images(
            _build_default_preview_blocks(),
            font_value,
            preview_args,
            progress_cb=progress_cb,
            max_output_pages=max_pages,
            render_state=render_state,
        )
        return (page_images[:max_pages] if page_images else [blank_page.copy()]), bool(render_state.get('page_limit_reached', False))

    suffix = preview_source.suffix.lower()
    if suffix in IMG_EXTS:
        with Image.open(preview_source) as src_img:
            return [_preview_fit_image(src_img, preview_args)], False

    if suffix in ('.txt',):
        document = load_text_input_document(preview_source, parser='plain')
        render_state: dict[str, object] = {}
        page_images = _render_text_blocks_to_images(
            document.blocks,
            font_value,
            preview_args,
            progress_cb=progress_cb,
            max_output_pages=max_pages,
            render_state=render_state,
        )
        return (page_images if page_images else [blank_page.copy()]), bool(render_state.get('page_limit_reached', False))

    if suffix in MARKDOWN_INPUT_SUFFIXES:
        document = load_text_input_document(preview_source, parser='markdown')
        render_state: dict[str, object] = {}
        page_images = _render_text_blocks_to_images(
            document.blocks,
            font_value,
            preview_args,
            progress_cb=progress_cb,
            max_output_pages=max_pages,
            render_state=render_state,
        )
        return (page_images if page_images else [blank_page.copy()]), bool(render_state.get('page_limit_reached', False))

    if suffix == '.epub':
        epub_doc = load_epub_input_document(preview_source)
        font = load_truetype_font(font_value, preview_args.font_size)
        ruby_font = load_truetype_font(font_value, preview_args.ruby_size)
        page_images: list[Image.Image] = []
        total_docs = max(1, len(epub_doc.docs))

        def _collect_page(entry: PageEntry) -> None:
            nonlocal truncated
            page_image = entry.get('image') if isinstance(entry, dict) else None
            if page_image is None:
                return
            if len(page_images) >= max_pages:
                truncated = True
                raise _PreviewPageLimitReached()
            page_images.append(page_image)
            _emit_progress(progress_cb, len(page_images), max_pages, f'プレビューページを作成中… ({len(page_images)}/{max_pages} ページ)')
            if len(page_images) >= max_pages:
                truncated = True
                raise _PreviewPageLimitReached()

        try:
            for doc_index, item in enumerate(epub_doc.docs, 1):
                if len(page_images) >= max_pages:
                    truncated = True
                    break
                remaining_pages = max_pages - len(page_images)
                _emit_progress(progress_cb, doc_index - 1, total_docs, f'EPUB章を組版中… ({max(0, doc_index - 1)}/{total_docs} 章)')
                chapter_pages = _render_epub_chapter_pages_from_html(
                    item.get_content(),
                    getattr(item, 'file_name', ''),
                    preview_args,
                    font,
                    ruby_font,
                    epub_doc.bold_rules,
                    epub_doc.image_map,
                    epub_doc.image_basename_map,
                    epub_doc.css_rules,
                    primary_font_value=str(font_value),
                    page_created_cb=_collect_page,
                    store_page_entries=False,
                    max_output_pages=remaining_pages,
                )
                for entry in chapter_pages:
                    _collect_page(entry)
                if len(page_images) >= max_pages:
                    truncated = True
                    break
            if len(page_images) < max_pages:
                truncated = False
        except _PreviewPageLimitReached:
            truncated = True
        return (page_images if page_images else [blank_page.copy()]), truncated

    if suffix in ('.zip', '.cbz'):
        try:
            image_infos, _traversal_skipped = _safe_zip_archive_image_infos(preview_source)
            page_images = []
            with zipfile.ZipFile(preview_source) as zf:
                for _pure, info in image_infos[:max_pages]:
                    with zf.open(info) as member_fp:
                        with Image.open(member_fp) as src_img:
                            page_images.append(_preview_fit_image(src_img, preview_args))
            truncated = len(image_infos) > max_pages
            return (page_images if page_images else [blank_page.copy()]), truncated
        except (zipfile.BadZipFile, OSError):
            pass

    if suffix in ('.zip', '.cbz', '.cbr', '.rar'):
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_document = _load_archive_input_document_compat(preview_source, tmpdir)
            page_images = []
            for image_path in archive_document.image_files[:max_pages]:
                with Image.open(image_path) as src_img:
                    page_images.append(_preview_fit_image(src_img, preview_args))
            truncated = len(archive_document.image_files) > max_pages
            return (page_images if page_images else [blank_page.copy()]), truncated

    page_images = _render_text_blocks_to_images(
        _build_default_preview_blocks(),
        font_value,
        preview_args,
        progress_cb=progress_cb,
        max_output_pages=max_pages,
    )
    return (page_images[:max_pages] if page_images else [blank_page.copy()]), len(page_images) > max_pages


def _render_preview_page_from_target(target_path: PathLike | None, font_value: str | Path, preview_args: ConversionArgs) -> Image.Image:
    page_images, _truncated = _render_preview_pages_from_target(target_path, font_value, preview_args, max_pages=1)
    return page_images[0] if page_images else Image.new('L', (preview_args.width, preview_args.height), 255)


def _apply_preview_postprocess(image: Image.Image, *, mode: object, output_format: str, dither: bool, threshold: int, width: int, height: int, night_mode: bool) -> Image.Image:
    if mode != 'image' and output_format == 'xtch':
        result = _apply_xtch_filter_prepared(image, dither, threshold, width, height)
    elif mode != 'image':
        result = _apply_xtc_filter_prepared(image, dither, threshold)
    else:
        result = image
    if night_mode:
        result = _invert_grayscale_image(result)
    return result


def _encode_preview_png_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    normalized = image if image.mode in {'1', 'L', 'LA', 'RGB', 'RGBA'} else image.convert('RGBA' if 'A' in image.mode else 'RGB')
    normalized.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def _mapping_get_int(mapping: Mapping[str, object], key: str, default: int) -> int:
    """Return an integer value from a loosely typed mapping."""
    value = mapping.get(key, default)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    return default


def _mapping_get_bool(mapping: Mapping[str, object], key: str, default: bool) -> bool:
    """Return a boolean value from a loosely typed mapping."""
    value = mapping.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {'1', 'true', 'yes', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'off', ''}:
            return False
    return bool(default)


_PREVIEW_BUNDLE_CACHE: OrderedDict[tuple[object, ...], dict[str, object]] = OrderedDict()


def _preview_path_signature(path: Path) -> tuple[str, int, int]:
    try:
        stat = path.stat()
        mtime_ns = getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1_000_000_000))
        return (str(path.resolve()), int(stat.st_size), int(mtime_ns))
    except OSError:
        return (str(path), -1, -1)


def _preview_bundle_cache_key(args: Mapping[str, object], *, preview_sources: Sequence[Path] | None = None) -> tuple[object, ...]:
    mode = str(args.get('mode', 'text') or 'text')
    width = _mapping_get_int(args, 'width', DEF_WIDTH)
    height = _mapping_get_int(args, 'height', DEF_HEIGHT)
    dither = _mapping_get_bool(args, 'dither', False)
    threshold = _mapping_get_int(args, 'threshold', 128)
    night_mode = _mapping_get_bool(args, 'night_mode', False)
    output_format = _normalize_output_format(args.get('output_format', 'xtc'))
    max_pages = max(1, _mapping_get_int(args, 'max_pages', PREVIEW_PAGE_LIMIT))

    common = (mode, width, height, dither, threshold, night_mode, output_format, max_pages)
    if mode == 'image':
        file_b64 = args.get('file_b64')
        digest = hashlib.sha1(file_b64.encode('utf-8')).hexdigest() if isinstance(file_b64, str) and file_b64 else '<default-gradient>'
        return common + (digest,)

    target_path = str(args.get('target_path', '') or '').strip()
    font_part = (
        str(args.get('font_file', '') or ''),
        _mapping_get_int(args, 'font_size', 26),
        _mapping_get_int(args, 'ruby_size', 12),
        _mapping_get_int(args, 'line_spacing', 44),
        _mapping_get_int(args, 'margin_t', 12),
        _mapping_get_int(args, 'margin_b', 14),
        _mapping_get_int(args, 'margin_r', 12),
        _mapping_get_int(args, 'margin_l', 12),
        _normalize_kinsoku_mode(args.get('kinsoku_mode', 'standard')),
    )
    source_paths = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
    source_signature = tuple(_preview_path_signature(path) for path in source_paths[:max_pages])
    return common + font_part + (target_path, len(source_paths), source_signature)


def clear_preview_bundle_cache() -> None:
    _PREVIEW_BUNDLE_CACHE.clear()


def _iter_preview_bundle_pages(value: object) -> Iterator[object]:
    if value is None:
        return
    if isinstance(value, str):
        yield value
        return
    if isinstance(value, (bytes, bytearray)):
        try:
            yield bytes(value).decode('ascii')
        except Exception:
            yield bytes(value).decode('utf-8', errors='ignore')
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_preview_bundle_pages(nested)
        return
    try:
        iterator = iter(value)  # type: ignore[arg-type]
    except Exception:
        return
    for item in iterator:
        yield from _iter_preview_bundle_pages(item)



def _normalize_preview_bundle_pages(value: object) -> list[str]:
    pages: list[str] = []
    for item in _iter_preview_bundle_pages(value):
        if isinstance(item, str):
            text = item.strip()
            if text:
                pages.append(text)
    return pages



def _get_cached_preview_bundle(cache_key: tuple[object, ...]) -> dict[str, object] | None:
    cached = _PREVIEW_BUNDLE_CACHE.get(cache_key)
    if cached is None:
        return None
    _PREVIEW_BUNDLE_CACHE.move_to_end(cache_key)
    pages = _normalize_preview_bundle_pages(cached.get('pages'))
    page_count = _mapping_get_int(cached, 'page_count', len(pages))
    if page_count <= 0:
        page_count = len(pages)
    source_count = _mapping_get_int(cached, 'source_count', 0)
    if source_count < 0:
        source_count = 0
    return {
        'pages': pages,
        'page_count': page_count,
        'truncated': _mapping_get_bool(cached, 'truncated', False),
        'source_count': source_count,
    }



def _store_cached_preview_bundle(cache_key: tuple[object, ...], bundle: Mapping[str, object]) -> None:
    pages = _normalize_preview_bundle_pages(bundle.get('pages'))
    page_count = _mapping_get_int(bundle, 'page_count', len(pages))
    if page_count <= 0:
        page_count = len(pages)
    source_count = _mapping_get_int(bundle, 'source_count', 0)
    if source_count < 0:
        source_count = 0
    _PREVIEW_BUNDLE_CACHE[cache_key] = {
        'pages': pages,
        'page_count': page_count,
        'truncated': _mapping_get_bool(bundle, 'truncated', False),
        'source_count': source_count,
    }
    _PREVIEW_BUNDLE_CACHE.move_to_end(cache_key)
    while len(_PREVIEW_BUNDLE_CACHE) > PREVIEW_BUNDLE_CACHE_MAX:
        _PREVIEW_BUNDLE_CACHE.popitem(last=False)


def generate_preview_bundle(args: Mapping[str, object], progress_cb: ProgressCallback | None = None) -> dict[str, object]:
    """Render preview pages and return base64-encoded PNGs plus pagination info."""
    try:
        _args: dict[str, object] = dict(args)
        mode = _args.get('mode', 'text')
        preview_sources = None if mode == 'image' else _resolve_preview_source_paths(_args.get('target_path', ''))
        cache_key = _preview_bundle_cache_key(_args, preview_sources=preview_sources)
        cached_bundle = _get_cached_preview_bundle(cache_key)
        if cached_bundle is not None:
            cached_pages = max(1, _mapping_get_int(cached_bundle, 'page_count', len(cached_bundle.get('pages', []))))
            _emit_progress(progress_cb, cached_pages, cached_pages, f'キャッシュ済みのプレビューを再利用しています… ({cached_pages}/{cached_pages} ページ)')
            return cached_bundle

        w = _mapping_get_int(_args, 'width', DEF_WIDTH)
        h = _mapping_get_int(_args, 'height', DEF_HEIGHT)
        dither = _mapping_get_bool(_args, 'dither', False)
        threshold = _mapping_get_int(_args, 'threshold', 128)
        mode = _args.get('mode', 'text')
        night_mode = _mapping_get_bool(_args, 'night_mode', False)
        kinsoku_mode = _normalize_kinsoku_mode(_args.get('kinsoku_mode', 'standard'))
        output_format = _normalize_output_format(_args.get('output_format', 'xtc'))
        max_pages = max(1, _mapping_get_int(_args, 'max_pages', PREVIEW_PAGE_LIMIT))

        if mode == 'image':
            _emit_progress(progress_cb, 0, 3, 'プレビュー画像を準備しています…')
            file_b64 = _args.get('file_b64')
            src_img: Image.Image
            if file_b64:
                if not isinstance(file_b64, str):
                    raise ValueError('画像プレビュー用データURIが不正です。')
                if "," not in file_b64:
                    raise ValueError('画像プレビュー用データURIが不正です。')
                _header, encoded = file_b64.split(",", 1)
                src_img = Image.open(io.BytesIO(base64.b64decode(encoded)))
            else:
                src_img = Image.new('L', (w, h), 255)
                draw = create_image_draw(src_img)
                for i in range(16):
                    draw.rectangle([0, i * (h // 16), w, (i + 1) * (h // 16)], fill=int(255 * (i / 15)))
            _emit_progress(progress_cb, 1, 3, 'プレビュー画像を変換しています…')
            page_images = [apply_xtch_filter(src_img, dither, threshold, w, h) if output_format == 'xtch' else apply_xtc_filter(src_img, dither, threshold, w, h)]
            truncated = False
            preview_source_count = 1
        else:
            font_value = _args.get('font_file', "")
            target_path = _args.get('target_path', '')
            preview_sources = list(preview_sources) if preview_sources is not None else _resolve_preview_source_paths(target_path)
            preview_source_count = len(preview_sources)
            preview_args = ConversionArgs(
                width=w,
                height=h,
                font_size=_mapping_get_int(_args, 'font_size', 26),
                ruby_size=_mapping_get_int(_args, 'ruby_size', 12),
                line_spacing=_mapping_get_int(_args, 'line_spacing', 44),
                margin_t=_mapping_get_int(_args, 'margin_t', 12),
                margin_b=_mapping_get_int(_args, 'margin_b', 14),
                margin_r=_mapping_get_int(_args, 'margin_r', 12),
                margin_l=_mapping_get_int(_args, 'margin_l', 12),
                dither=dither,
                night_mode=night_mode,
                threshold=threshold,
                kinsoku_mode=kinsoku_mode,
                output_format=output_format,
            )
            if _preview_target_requires_font(target_path, preview_sources=preview_sources):
                require_font_path(font_value)
            page_images, truncated = _render_preview_pages_from_target(target_path, font_value, preview_args, max_pages=max_pages, progress_cb=progress_cb, preview_sources=preview_sources)

        total_pages = max(1, len(page_images))
        encoded_pages = []
        for idx, image in enumerate(page_images, 1):
            _emit_progress(progress_cb, idx - 1, total_pages, f'プレビュー画像を整えています… ({idx - 1}/{total_pages} ページ)')
            processed = _apply_preview_postprocess(
                image,
                mode=mode,
                output_format=output_format,
                dither=dither,
                threshold=threshold,
                width=w,
                height=h,
                night_mode=night_mode,
            )
            _emit_progress(progress_cb, idx, total_pages, f'プレビューを出力しています… ({idx}/{total_pages} ページ)')
            encoded_pages.append(_encode_preview_png_base64(processed))
        bundle = {'pages': encoded_pages, 'page_count': len(encoded_pages), 'truncated': bool(truncated), 'source_count': int(preview_source_count) if mode != 'image' else 1}
        _store_cached_preview_bundle(cache_key, bundle)
        return bundle

    except Exception as e:
        LOGGER.exception('Preview Error: %s', e)
        raise RuntimeError(f"プレビュー生成に失敗しました: {e}") from e


def generate_preview_base64(args: Mapping[str, object]) -> str:
    """Render the first preview page and return it as a base64 PNG string.

    Args:
        args: Preview and rendering options supplied by the GUI layer.

    Returns:
        Base64-encoded PNG string for the first preview page.
    """
    bundle = generate_preview_bundle(args)
    pages = bundle.get('pages', []) if isinstance(bundle, dict) else []
    if not pages:
        blank = Image.new('L', (_mapping_get_int(dict(args), 'width', DEF_WIDTH), _mapping_get_int(dict(args), 'height', DEF_HEIGHT)), 255)
        return _encode_preview_png_base64(blank)
    first = pages[0]
    if not isinstance(first, str):
        raise RuntimeError('プレビュー生成に失敗しました: 先頭ページの形式が不正です。')
    return first

# ==========================================
# --- アーカイブ / EPUB 変換 ---
# ==========================================

def process_image_data(data: bytes | bytearray | memoryview | str | PathLike | BinaryIO, args: ConversionArgs, should_cancel: Callable[[], bool] | None = None) -> bytes | None:
    """画像データまたは画像パスを読み込み、出力形式に応じた XTC-family バイト列を返す。"""
    _raise_if_cancelled(should_cancel)
    try:
        image_source: io.BytesIO | str | PathLike
        close_source = False
        if isinstance(data, (bytes, bytearray, memoryview)):
            image_source = io.BytesIO(bytes(data))
            close_source = True
        else:
            image_source = data
        try:
            with Image.open(image_source) as s_img:
                bg = _prepare_canvas_image(s_img, args.width, args.height)
                _raise_if_cancelled(should_cancel)
                return canvas_image_to_xt_bytes(bg, args.width, args.height, args, prepared=True)
        finally:
            if close_source and hasattr(image_source, 'close'):
                image_source.close()
    except Exception as e:
        LOGGER.exception('画像処理エラー: %s', e)
        return None




_TEXT_INPUT_DOCUMENT_CACHE: OrderedDict[tuple[str, str, int, int], TextInputDocument] = OrderedDict()
_EPUB_INPUT_DOCUMENT_CACHE: OrderedDict[tuple[str, int, int], EpubInputDocument] = OrderedDict()


def _source_document_cache_key(path_like: PathLike) -> tuple[str, int, int]:
    path = Path(path_like)
    try:
        stat = path.stat()
        mtime_ns = getattr(stat, 'st_mtime_ns', int(stat.st_mtime * 1_000_000_000))
        return (str(path.resolve()), int(stat.st_size), int(mtime_ns))
    except OSError:
        return (str(path), -1, -1)


def _get_cached_input_document(cache: OrderedDict[tuple[object, ...], Any], cache_key: tuple[object, ...]) -> Any | None:
    cached = cache.get(cache_key)
    if cached is None:
        return None
    cache.move_to_end(cache_key)
    return cached


def _store_cached_input_document(cache: OrderedDict[tuple[object, ...], Any], cache_key: tuple[object, ...], document: Any) -> Any:
    cache[cache_key] = document
    cache.move_to_end(cache_key)
    while len(cache) > INPUT_DOCUMENT_CACHE_MAX:
        cache.popitem(last=False)
    return document


def clear_input_document_cache() -> None:
    """Clear cached parsed text / EPUB input documents."""
    _TEXT_INPUT_DOCUMENT_CACHE.clear()
    _EPUB_INPUT_DOCUMENT_CACHE.clear()
    _cached_safe_zip_archive_image_listing.cache_clear()



def read_text_file_with_fallback(text_path: PathLike) -> tuple[str, str]:
    """TXT / Markdown を BOM 判定・自動判定・既知候補の順で読み込む。"""
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
    if not value:
        return []
    if parse_aozora:
        runs = _aozora_inline_to_runs(value, bold=False, italic=False)
        if code:
            for run in runs:
                run['code'] = True
        return runs
    return [{'text': value, 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': bool(code)}]


def _normalize_text_line(value: str, has_started_document: bool = False, strip_leading_for_indent: bool = False) -> str:
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
    warnings: WarningList = []
    if re.search(r'^#{1,6}\s+\S', text, flags=re.MULTILINE):
        warnings.append('Markdown の見出し記法らしい行があります。見出しとして整形したい場合は .md / .markdown で保存してください。')
    if re.search(r'^(?:[-*+]\s+|\d+[\.)]\s+)\S', text, flags=re.MULTILINE):
        warnings.append('Markdown の箇条書き・番号付きリストらしい行があります。テキスト入力では通常段落として扱います。')
    return _dedupe_preserve_order(warnings)


def _blocks_from_plain_text(text: str) -> TextBlocks:
    blocks: TextBlocks = []
    active_indent = None
    pending_once_indent = None
    has_started_content = False
    for raw_line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        normalized = _normalize_text_line(raw_line, has_started_document=has_started_content, strip_leading_for_indent=False)
        if not normalized:
            blocks.append({'kind': 'blank'})
            continue
        note_block = _parse_aozora_note_only_line(normalized)
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
            continue
        runs = _plain_inline_to_runs(normalized)
        if not runs:
            blocks.append({'kind': 'blank'})
            continue
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
    return blocks


MARKDOWN_FOOTNOTE_DEF_RE = re.compile(r'^\[\^([^\]]+)\]:\s*(.*)$')
MARKDOWN_DEF_LIST_RE = re.compile(r'^\s*:\s+(.*)$')
MARKDOWN_ORDERED_LIST_RE = re.compile(r'^\s*(\d+)[\.)]\s+(.*)$')
MARKDOWN_FENCE_RE = re.compile(r'^\s*(```+|~~~+)')


def _markdown_text_run(text: str, *, bold: bool = False, code: bool = False) -> TextRun:
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
    for run in runs:
        run['bold'] = True
    return runs


def _extract_markdown_footnotes(lines: Sequence[str]) -> tuple[list[str], list[FootnoteEntry], LinkDefinitions]:
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
    cells = _split_markdown_table_row(line)
    if not cells:
        return False
    for cell in cells:
        compact = cell.replace(' ', '')
        if not compact or not re.fullmatch(r':?-{3,}:?', compact):
            return False
    return True


def _build_markdown_table_blocks(headers: Sequence[str], rows: Sequence[Sequence[str]], *, link_definitions: Mapping[str, str] | None = None) -> TextBlocks:
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


def _blocks_from_markdown(text: str) -> TextBlocks:
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
    source_path = Path(text_path)
    parser_key = str(parser or 'plain').strip().lower()
    if parser_key != 'markdown':
        parser_key = 'plain'
    cache_key = (parser_key, *_source_document_cache_key(source_path))
    cached = _get_cached_input_document(_TEXT_INPUT_DOCUMENT_CACHE, cache_key)
    if isinstance(cached, TextInputDocument):
        return cached

    text, encoding = read_text_file_with_fallback(source_path)
    normalized_text = _strip_start_text_after_leading_frontmatter(text)
    if parser_key == 'markdown':
        blocks = _blocks_from_markdown(normalized_text)
        format_label = 'Markdown'
        warnings = _find_markdown_support_warnings(normalized_text)
    else:
        blocks = _blocks_from_plain_text(normalized_text)
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



@lru_cache(maxsize=128)
def _cached_safe_zip_archive_image_listing(path_text: str, file_size: int, mtime_ns: int) -> tuple[tuple[str, ...], int]:
    """ZIP/CBZ 内の安全な画像メンバー名を自然順でキャッシュする。"""
    archive = Path(path_text)
    member_names: list[str] = []
    traversal_skipped = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = str(getattr(info, 'filename', '') or '')
            if not name or getattr(info, 'is_dir', lambda: False)():
                continue
            pure = PurePosixPath(name)
            if pure.is_absolute() or '..' in pure.parts:
                if pure.suffix.lower() in IMG_EXTS:
                    traversal_skipped += 1
                continue
            if pure.suffix.lower() not in IMG_EXTS:
                continue
            member_names.append(pure.as_posix())
    member_names.sort(key=_natural_sort_key)
    return tuple(member_names), traversal_skipped



def _safe_zip_archive_image_listing(archive_path: PathLike) -> tuple[list[str], int]:
    """ZIP/CBZ 内の安全な画像メンバー名を自然順で返す。"""
    path_text, file_size, mtime_ns = _source_document_cache_key(archive_path)
    member_names, traversal_skipped = _cached_safe_zip_archive_image_listing(path_text, file_size, mtime_ns)
    return list(member_names), traversal_skipped





_ARCHIVE_INVALID_COMPONENT_CHARS = frozenset(r'<>:"\|?*')
_ARCHIVE_WINDOWS_RESERVED_NAMES = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
})


def _sanitize_extracted_archive_member_component(part: str, fallback: str = 'item') -> str:
    raw = str(part or '').replace('\x00', '').strip()
    cleaned = ''.join(
        '_' if (ord(ch) < 32 or ch in _ARCHIVE_INVALID_COMPONENT_CHARS) else ch
        for ch in raw
    ).strip(' .')
    if not cleaned or cleaned in {'.', '..'}:
        cleaned = fallback
    stem = Path(cleaned).stem.strip(' .')
    if cleaned.upper() in _ARCHIVE_WINDOWS_RESERVED_NAMES or stem.upper() in _ARCHIVE_WINDOWS_RESERVED_NAMES:
        cleaned = f'_{cleaned}'
    return cleaned or fallback


def _normalize_extracted_archive_member_key(path: PathLike) -> str:
    raw = str(path or '').strip()
    if not raw:
        return ''
    path_obj = Path(raw)
    windows_like = bool(path_obj.drive) or ('\\' in raw)
    normalized = ntpath.normpath(raw) if windows_like else os.path.normpath(raw)
    return ntpath.normcase(normalized) if windows_like else normalized.casefold()


def _safe_zip_archive_image_infos(archive_path: PathLike, *, should_cancel: CancelCallback | None = None) -> tuple[list[tuple[PurePosixPath, zipfile.ZipInfo]], int]:
    """ZIP/CBZ 内の安全な画像メンバー情報を自然順で返す。"""
    archive = Path(archive_path)
    image_infos: list[tuple[PurePosixPath, zipfile.ZipInfo]] = []
    traversal_skipped = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            _raise_if_cancelled(should_cancel)
            name = str(getattr(info, 'filename', '') or '')
            if not name or getattr(info, 'is_dir', lambda: False)():
                continue
            pure = PurePosixPath(name)
            if pure.is_absolute() or '..' in pure.parts:
                if pure.suffix.lower() in IMG_EXTS:
                    traversal_skipped += 1
                continue
            if pure.suffix.lower() not in IMG_EXTS:
                continue
            image_infos.append((pure, info))
    image_infos.sort(key=lambda item: _natural_sort_key(item[0].as_posix()))
    return image_infos, traversal_skipped



def _unique_extracted_member_path(dest_path: Path) -> Path:
    if not dest_path.exists():
        return dest_path
    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent
    index = 1
    while True:
        candidate = parent / f'{stem}({index}){suffix}'
        if not candidate.exists():
            return candidate
        index += 1



def _extract_zip_archive_images_to_tempdir(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> tuple[list[Path], int]:
    """ZIP/CBZ から安全な画像メンバーだけを一時ディレクトリへ抽出する。"""
    out_dir = Path(tmpdir_path)
    image_infos, traversal_skipped = _safe_zip_archive_image_infos(archive_path, should_cancel=should_cancel)
    extracted_files: list[Path] = []
    reserved_dest_keys: set[str] = set()
    with zipfile.ZipFile(Path(archive_path)) as zf:
        for pure, info in image_infos:
            _raise_if_cancelled(should_cancel)
            sanitized_parts = [
                _sanitize_extracted_archive_member_component(part, 'item')
                for part in pure.parts
            ]
            desired_path = out_dir.joinpath(*sanitized_parts)
            dest_path = _unique_extracted_member_path(desired_path)
            dest_key = _normalize_extracted_archive_member_key(dest_path) or str(dest_path)
            if dest_key in reserved_dest_keys:
                stem = desired_path.stem
                suffix = desired_path.suffix
                parent = desired_path.parent
                index = 1
                while True:
                    candidate = parent / f'{stem}({index}){suffix}'
                    candidate_key = _normalize_extracted_archive_member_key(candidate) or str(candidate)
                    if candidate_key not in reserved_dest_keys and not candidate.exists():
                        dest_path = candidate
                        dest_key = candidate_key
                        break
                    index += 1
            reserved_dest_keys.add(dest_key)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with zf.open(info) as src_fp, open(dest_path, 'wb') as out_fp:
                    _copy_fileobj_with_cancel(src_fp, out_fp, should_cancel=should_cancel, chunk_size=1024 * 1024)
            except Exception:
                try:
                    dest_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise
            extracted_files.append(dest_path)
    return extracted_files, traversal_skipped

def _extract_archive_to_tempdir(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> tuple[int, list[Path] | None]:
    """アーカイブを一時ディレクトリへ展開する。"""
    suffix = Path(archive_path).suffix.lower()
    if suffix in ('.zip', '.cbz'):
        extracted_files, traversal_skipped = _extract_zip_archive_images_to_tempdir(archive_path, tmpdir_path, should_cancel=should_cancel)
        return traversal_skipped, extracted_files
    _raise_if_cancelled(should_cancel)
    patoolib = _require_patoolib()
    patoolib.extract_archive(str(archive_path), outdir=str(tmpdir_path), verbosity=-1)
    _raise_if_cancelled(should_cancel)
    return 0, None


def _collect_archive_image_files(tmpdir_path: PathLike) -> list[Path]:
    """展開済みディレクトリから画像ファイルを自然順で収集する。"""
    base_dir = Path(tmpdir_path)
    return sorted(
        [p for p in base_dir.rglob('*') if p.suffix.lower() in IMG_EXTS],
        key=lambda p: _natural_sort_key(p.relative_to(base_dir)),
    )


def _list_zip_archive_image_members(archive_path: PathLike) -> list[str]:
    """ZIP/CBZ 内の画像メンバー名を安全側に寄せて自然順で列挙する。"""
    member_names, _traversal_skipped = _safe_zip_archive_image_listing(archive_path)
    return member_names


def _load_archive_input_document_compat(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> ArchiveInputDocument:
    """load_archive_input_document の旧2引数モックとも互換を保って呼び出す。"""
    try:
        return load_archive_input_document(archive_path, tmpdir_path, should_cancel=should_cancel)
    except TypeError as exc:
        msg = str(exc)
        if 'unexpected keyword argument' not in msg or 'should_cancel' not in msg:
            raise
        return load_archive_input_document(archive_path, tmpdir_path)


def load_archive_input_document(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> ArchiveInputDocument:
    """画像アーカイブを展開し、描画対象画像一覧へ正規化する。"""
    source_path = Path(archive_path)
    temp_path = Path(tmpdir_path)
    _raise_if_cancelled(should_cancel)
    traversal_skipped, extracted_files = _extract_archive_to_tempdir(source_path, temp_path, should_cancel=should_cancel)
    _raise_if_cancelled(should_cancel)
    image_files = extracted_files if extracted_files is not None else _collect_archive_image_files(temp_path)
    _raise_if_cancelled(should_cancel)
    return ArchiveInputDocument(
        source_path=source_path,
        image_files=image_files,
        traversal_skipped=traversal_skipped,
        extracted_member_count=len(image_files),
        trusted_temp_files=extracted_files is not None,
    )



def _normalize_epub_href(href: object) -> str:
    """EPUB 内 href を比較しやすい相対 POSIX パスへ正規化する。"""
    value = str(href or '').strip().replace('\\', '/')
    if not value:
        return ''
    if value.startswith('data:') or '://' in value:
        return ''
    value = unquote(value).split('#', 1)[0].split('?', 1)[0]
    if not value:
        return ''
    norm = posixpath.normpath(value)
    if norm in {'', '.'}:
        return ''
    return norm.lstrip('/')



def _build_epub_image_maps(book: Any) -> tuple[EpubImageMap, EpubImageBasenameMap]:
    image_map = {
        _normalize_epub_href(getattr(item, 'file_name', '')): item.get_content()
        for item in book.get_items()
        if (
            getattr(item, 'media_type', '').startswith('image/')
            or Path(getattr(item, 'file_name', '')).suffix.lower() in IMG_EXTS
        )
        and _normalize_epub_href(getattr(item, 'file_name', ''))
    }
    image_basename_map: EpubImageBasenameMap = {}
    for normalized_name, image_bytes in image_map.items():
        image_basename_map.setdefault(posixpath.basename(normalized_name), []).append((normalized_name, image_bytes))
    return image_map, image_basename_map



def _collect_epub_spine_documents(book: Any) -> list[Any]:
    docs: list[Any] = []
    for item_id in book.spine:
        item_key = item_id[0] if isinstance(item_id, tuple) else item_id
        it = book.get_item_with_id(item_key)
        if not it:
            continue
        media_type = (getattr(it, 'media_type', '') or '').lower()
        file_name = (getattr(it, 'file_name', '') or '').lower()
        if (
            media_type in ('application/xhtml+xml', 'text/html')
            or file_name.endswith(('.xhtml', '.html', '.htm'))
        ):
            docs.append(it)
    return docs



def load_epub_input_document(epub_path: PathLike) -> EpubInputDocument:
    """EPUB を読み込み、本文文書群と画像対応表へ正規化する。"""
    source_path = Path(epub_path)
    cache_key = _source_document_cache_key(source_path)
    cached = _get_cached_input_document(_EPUB_INPUT_DOCUMENT_CACHE, cache_key)
    if isinstance(cached, EpubInputDocument):
        return cached

    epub = _require_ebooklib_epub()
    book = epub.read_epub(str(source_path))
    image_map, image_basename_map = _build_epub_image_maps(book)
    document = EpubInputDocument(
        source_path=source_path,
        book=book,
        docs=_collect_epub_spine_documents(book),
        image_map=image_map,
        image_basename_map=image_basename_map,
        bold_rules=extract_bold_rules(book),
        css_rules=extract_epub_css_rules(book),
    )
    return cast(EpubInputDocument, _store_cached_input_document(_EPUB_INPUT_DOCUMENT_CACHE, cache_key, document))


def _has_renderable_text_blocks(blocks: Sequence[Mapping[str, Any]], should_cancel: Callable[[], bool] | None = None) -> bool:
    for block in blocks:
        _raise_if_cancelled(should_cancel)
        if block.get('kind') == 'blank':
            continue
        runs = block.get('runs', [])
        if any(run.get('text', '') for run in runs):
            return True
    return False


@lru_cache(maxsize=2048)
def _split_ruby_text_segments_cached(
    rt_text: str,
    segment_lengths: tuple[int, ...],
    segment_capacities: tuple[int | None, ...] | None = None,
) -> tuple[str, ...]:
    """ルビ文字列を複数セグメントへ按分する。"""
    if not rt_text:
        return tuple('' for _ in segment_lengths)

    total_base = sum(segment_lengths) or 1
    total_ruby = len(rt_text)
    target_counts = []
    for seg_len in segment_lengths:
        target_counts.append(round(total_ruby * seg_len / total_base))

    if total_ruby >= len(segment_lengths):
        target_counts = [max(1, c) for c in target_counts]

    diff = total_ruby - sum(target_counts)
    if diff > 0:
        order = sorted(range(len(segment_lengths)), key=lambda i: (-segment_lengths[i], i))
        j = 0
        while diff > 0 and order:
            target_counts[order[j % len(order)]] += 1
            diff -= 1
            j += 1
    elif diff < 0:
        order = sorted(range(len(segment_lengths)), key=lambda i: (segment_lengths[i], -i))
        j = 0
        while diff < 0 and order:
            target_idx = order[j % len(order)]
            min_allowed = 1 if total_ruby >= len(segment_lengths) else 0
            if target_counts[target_idx] > min_allowed:
                target_counts[target_idx] -= 1
                diff += 1
            j += 1
            if j > len(order) * 4 and diff < 0:
                break

    if segment_capacities:
        target_counts = [max(0, int(c)) for c in target_counts]
        for j, cap in enumerate(segment_capacities):
            if cap is not None:
                target_counts[j] = min(target_counts[j], max(0, int(cap)))

        overflow = max(0, total_ruby - sum(target_counts))
        if overflow > 0:
            expandable = [
                j for j, cap in enumerate(segment_capacities)
                if cap is None or target_counts[j] < max(0, int(cap))
            ]
            order = sorted(expandable, key=lambda j: (-segment_lengths[j], j))
            j = 0
            while overflow > 0 and order:
                target_idx = order[j % len(order)]
                cap = segment_capacities[target_idx]
                if cap is None or target_counts[target_idx] < max(0, int(cap)):
                    target_counts[target_idx] += 1
                    overflow -= 1
                j += 1
                if j > len(order) * 4 and overflow > 0:
                    break

        if overflow > 0:
            order = sorted(range(len(segment_lengths)), key=lambda j: (-segment_lengths[j], j))
            j = 0
            while overflow > 0 and order:
                target_counts[order[j % len(order)]] += 1
                overflow -= 1
                j += 1
                if j > len(order) * 4 and overflow > 0:
                    break

    parts = []
    pos = 0
    for count in target_counts:
        parts.append(rt_text[pos:pos + count])
        pos += count
    if pos < total_ruby:
        if parts:
            parts[-1] += rt_text[pos:]
        else:
            parts = [rt_text[pos:]]
    while len(parts) < len(segment_lengths):
        parts.append('')
    return tuple(parts)


def _split_ruby_text_segments(rt_text: str, segment_lengths: Sequence[int], segment_capacities: Sequence[int | None] | None = None) -> list[str]:
    segment_lengths_tuple = tuple(int(v) for v in segment_lengths)
    segment_capacities_tuple = None if segment_capacities is None else tuple(None if cap is None else int(cap) for cap in segment_capacities)
    return list(_split_ruby_text_segments_cached(str(rt_text or ''), segment_lengths_tuple, segment_capacities_tuple))


def _append_ruby_overlay_group(groups: list[RubyOverlayGroup], page_index: int, x_pos: int, y_pos: int, base_len: int) -> None:
    base_len = max(1, int(base_len or 1))
    page_index = int(page_index)
    x_pos = int(x_pos)
    y_pos = int(y_pos)
    if groups:
        current = groups[-1]
        # Ruby groups may span page boundaries.  Normal continuation within the
        # same vertical column advances downward, while a page/column reset moves
        # Y back to the top margin.  Do not merge a backward Y jump into the
        # previous compact group; that would create an inverted start/end range
        # and split the ruby text against the wrong page-local capacity.
        if (
            current['page_index'] == page_index
            and current['x'] == x_pos
            and y_pos >= int(current['end_y'])
        ):
            current['end_y'] = y_pos
            current['base_len'] += base_len
            return
    groups.append({
        'page_index': page_index,
        'x': x_pos,
        'start_y': y_pos,
        'end_y': y_pos,
        'base_len': base_len,
    })


def _build_ruby_overlay_groups(segment_infos: Sequence[Mapping[str, Any]]) -> list[RubyOverlayGroup]:
    groups: list[RubyOverlayGroup] = []
    for info in segment_infos:
        _append_ruby_overlay_group(
            groups,
            int(info['page_index']),
            int(info['x']),
            int(info['y']),
            int(info.get('base_len', 1) or 1),
        )
    return groups


def _append_overlay_cell(cells: list[OverlayCell], page_index: int, x_pos: int, y_pos: int, cell_text: str) -> None:
    cells.append((int(page_index), int(x_pos), int(y_pos), str(cell_text or '')))


def _effective_ruby_overlay_bottom_margin(args: ConversionArgs) -> int:
    """Return the bottom guard shared by base text and ruby overlays.

    Ruby is drawn after the base glyph run has already reserved the vertical
    layout bottom guard.  If overlay placement uses only the raw bottom margin,
    long or bottom-adjacent ruby can drift below the last legal base-text slot
    and look clipped or too close to the page edge.
    """
    return _effective_vertical_layout_bottom_margin(args.margin_b, args.font_size)


def _ruby_group_capacity_for_args(group: Mapping[str, Any], segment_index: int, total_segments: int, args: ConversionArgs) -> int:
    """セグメントごとのルビ配置可能数を算出する。"""
    slot_h = max(1, args.ruby_size + 2)
    page_top = args.margin_t
    page_bottom = args.height - _effective_ruby_overlay_bottom_margin(args)
    chars = group.get('chars')
    if chars:
        start_y = int(chars[0]['y'])
        end_y = int(chars[-1]['y']) + args.font_size
    else:
        start_y = int(group.get('start_y', page_top))
        end_y = int(group.get('end_y', start_y)) + args.font_size

    if total_segments == 1:
        usable_top = page_top
        usable_bottom = page_bottom
    elif segment_index == 0:
        usable_top = page_top
        usable_bottom = min(page_bottom, end_y)
    elif segment_index == total_segments - 1:
        usable_top = max(page_top, start_y)
        usable_bottom = page_bottom
    else:
        usable_top = page_top
        usable_bottom = page_bottom

    usable_height = max(0, usable_bottom - usable_top)
    if usable_height <= 0:
        return 0
    return ((usable_height - 1) // slot_h) + 1


def _clamp_margin_value(value: object, limit: int) -> int:
    try:
        margin = int(value or 0)
    except (TypeError, ValueError):
        margin = 0
    return max(0, min(max(0, int(limit or 0)), margin))


def _apply_text_page_margin_clip(image: Image.Image, args: ConversionArgs | None) -> Image.Image:
    """本文ページの四辺余白に残った描画画素を白でクリップする。

    縦書き本文はフォントによって実インクがセル外へ出る場合があるため、
    レイアウト段階の余白計算に加え、ページ確定直前に外側余白を白で
    戻す。右辺は本文セルの外側にルビ用スペースを持つため、消すのは
    指定された右余白そのものだけに限定し、ルビ予約領域は残す。
    """
    if image is None or args is None:
        return image
    width, height = image.size
    if width <= 0 or height <= 0:
        return image
    margin_t = _clamp_margin_value(getattr(args, 'margin_t', 0), height)
    margin_b = _clamp_margin_value(getattr(args, 'margin_b', 0), height)
    margin_r = _clamp_margin_value(getattr(args, 'margin_r', 0), width)
    margin_l = _clamp_margin_value(getattr(args, 'margin_l', 0), width)
    if not (margin_t or margin_b or margin_r or margin_l):
        return image
    draw = ImageDraw.Draw(image)
    fill_value = 255
    if margin_t:
        draw.rectangle((0, 0, width - 1, margin_t - 1), fill=fill_value)
    if margin_b:
        y0 = max(0, height - margin_b)
        draw.rectangle((0, y0, width - 1, height - 1), fill=fill_value)
    if margin_l:
        draw.rectangle((0, 0, margin_l - 1, height - 1), fill=fill_value)
    if margin_r:
        x0 = max(0, width - margin_r)
        draw.rectangle((x0, 0, width - 1, height - 1), fill=fill_value)
    return image


def _page_label_allows_text_margin_clip(label: object) -> bool:
    label_text = str(label or '')
    if '挿絵' in label_text or '画像' in label_text:
        return False
    return True


def _apply_page_entry_margin_clip(entry: PageEntry) -> PageEntry:
    if not isinstance(entry, dict):
        return entry
    if not _page_label_allows_text_margin_clip(entry.get('label', '')):
        return entry
    image = entry.get('image')
    args = entry.get('page_args')
    if image is not None and args is not None:
        _apply_text_page_margin_clip(cast(Image.Image, image), cast(ConversionArgs, args))
    return entry

class _VerticalPageRenderer:
    def __init__(self: _VerticalPageRenderer, args: ConversionArgs, font: Any, ruby_font: Any, *, should_cancel: CancelCallback | None = None, page_created_cb: PageCreatedCallback | None = None,
                 store_page_entries: bool = True, max_buffered_pages: int | None = None,
                 default_page_args: ConversionArgs | None = None, default_page_label: str = '本文ページ', emphasis_font_value: str | None = None,
                 code_font: Any | None = None, code_font_loader: Callable[[], Any] | None = None) -> None:
        self.args = args
        self.font = font
        self.ruby_font = ruby_font
        self.code_font = code_font
        self._code_font_loader = code_font_loader
        self.should_cancel = should_cancel
        self.page_created_cb = page_created_cb
        self.store_page_entries = bool(store_page_entries)
        self.max_buffered_pages = max(1, int(max_buffered_pages)) if max_buffered_pages else None
        self.default_page_args = default_page_args or args
        self.default_page_label = default_page_label
        self.emphasis_font_value = emphasis_font_value
        self.page_entries: PageEntries = []
        self._page_draw_cache: dict[int, ImageDraw.ImageDraw] = {}
        self._emphasis_font_cache_key: tuple[object, ...] | None = None
        self._emphasis_font_cache: Any | None = None
        self._emphasis_metrics_cache: dict[tuple[str, bool], tuple[int, int, int, int]] = {}
        self.has_started_document = False
        self._pending_paragraph_indent = False
        self._new_blank_page()

    def _new_blank_page(self: _VerticalPageRenderer) -> None:
        self.img = Image.new('L', (self.args.width, self.args.height), 255)
        self.draw = create_image_draw(self.img)
        self._page_draw_cache.clear()
        self.curr_x = self.args.width - self.args.font_size - (self.args.ruby_size + 4) - self.args.margin_r
        self.curr_y = self.args.margin_t
        self.has_drawn_on_page = False

    def add_page(self: _VerticalPageRenderer, image: Image.Image, *, label: str | None = None, page_args: ConversionArgs | None = None, copy_image: bool = True) -> PageEntry:
        stored_image = image.copy() if copy_image else image
        entry = _make_page_entry(
            stored_image,
            page_args=page_args or self.default_page_args,
            label=label or self.default_page_label,
        )
        # Ruby overlays are drawn after the base run has been laid out. When a
        # ruby run crosses a page boundary, earlier page images must remain
        # mutable until ``draw_split_ruby_groups`` has placed each ruby segment
        # on the correct page. Therefore page entries are retained here and
        # drained via ``pop_page_entries()`` after an overlay-safe boundary.
        self.page_entries.append(entry)
        if self.max_buffered_pages is not None and len(self.page_entries) >= self.max_buffered_pages:
            raise _PreviewPageLimitReached()
        return entry

    def flush_current_page(self: _VerticalPageRenderer, *, label: str | None = None, page_args: ConversionArgs | None = None) -> None:
        if self.has_drawn_on_page:
            self.add_page(self.img, label=label, page_args=page_args, copy_image=False)
        self._new_blank_page()

    @property
    def has_pending_output(self: _VerticalPageRenderer) -> bool:
        return bool(self.has_drawn_on_page or self.page_entries)

    def add_full_page_image(self: _VerticalPageRenderer, image: Image.Image, *, label: str | None = None, page_args: ConversionArgs | None = None, copy_image: bool = True) -> PageEntry:
        """Append a full-page image entry and reset the current working page.

        This is used for EPUB illustration pages and other content that should occupy
        an entire output page instead of being drawn into the current text column.
        Any in-progress text page is flushed first so the full-page image is emitted as
        its own page entry. Afterward a fresh blank page is prepared for subsequent
        text rendering.

        Args:
            image: Source image to store as a page entry.
            label: Optional human-readable page label for diagnostics and previews.
            page_args: Optional per-page conversion arguments. When omitted, the
                renderer's default page args are used.
            copy_image: Whether to store a copy of ``image`` in the page entry.

        Returns:
            The page entry dictionary that was appended to the renderer output.
        """
        if self.has_drawn_on_page:
            self.flush_current_page()
        entry = self.add_page(image, label=label, page_args=page_args, copy_image=copy_image)
        self._new_blank_page()
        return entry

    def set_pending_paragraph_indent(self: _VerticalPageRenderer, enabled: bool = True) -> None:
        self._pending_paragraph_indent = bool(enabled)

    def clear_pending_paragraph_indent(self: _VerticalPageRenderer) -> None:
        self._pending_paragraph_indent = False

    @property
    def has_pending_paragraph_indent(self: _VerticalPageRenderer) -> bool:
        return bool(self._pending_paragraph_indent)

    def apply_pending_paragraph_indent(self: _VerticalPageRenderer, indent_chars: int = 0) -> bool:
        """Apply a deferred paragraph indent if one is pending.

        EPUB rendering can defer indent insertion until the first actual text run is
        encountered after a ``<br>`` or paragraph boundary. This method resolves that
        deferred state, inserts the requested indent into the current column, and then
        clears the pending flag.

        Args:
            indent_chars: Preferred indent width in character units. When a pending
                paragraph indent exists, at least one character of indent is enforced.

        Returns:
            ``True`` when an indent was inserted, otherwise ``False``.
        """
        if self._pending_paragraph_indent:
            indent_chars = max(int(indent_chars or 0), 1)
        indent_chars = max(0, int(indent_chars or 0))
        if indent_chars <= 0:
            self._pending_paragraph_indent = False
            return False
        self.insert_paragraph_indent(indent_chars, continuation_indent_chars=indent_chars)
        self._pending_paragraph_indent = False
        return True

    def pop_page_entries(self: _VerticalPageRenderer) -> PageEntries:
        entries = self.page_entries
        self.page_entries = []
        self._page_draw_cache.clear()
        for entry in entries:
            _apply_page_entry_margin_clip(entry)
        if self.page_created_cb is not None:
            for entry in entries:
                self.page_created_cb(entry)
        if not self.store_page_entries:
            return []
        return entries

    def set_page_buffer_limit(self: _VerticalPageRenderer, value: int | None) -> None:
        self.max_buffered_pages = max(1, int(value)) if value else None

    def _indent_step_height(self: _VerticalPageRenderer, indent_chars: int) -> int:
        return max(0, int(indent_chars or 0)) * (self.args.font_size + 2)

    def _advance_column_with_indent_step(self: _VerticalPageRenderer, indent_step_height: int = 0) -> None:
        """Move to the next column using a precomputed continuation indent.

        Args:
            indent_step_height: Continuation indent already converted from character
                units into pixels.
        """
        _raise_if_cancelled(self.should_cancel)
        self.curr_y = self.args.margin_t + max(0, int(indent_step_height or 0))
        self.curr_x -= self.args.line_spacing
        if self.curr_x < self.args.margin_l:
            self.flush_current_page()
            self.curr_y = self.args.margin_t + max(0, int(indent_step_height or 0))

    def advance_column(self: _VerticalPageRenderer, count: int = 1, indent_chars: int = 0) -> None:
        """Move rendering to the next vertical column one or more times.

        The current Y position is reset to the top margin plus any continuation indent.
        When the next column would move past the left margin, the current page is
        flushed and a fresh blank page is started automatically.

        Args:
            count: Number of columns to advance.
            indent_chars: Continuation indent, expressed in character units, to apply
                when the new column starts.
        """
        _raise_if_cancelled(self.should_cancel)
        indent_step_height = self._indent_step_height(indent_chars)
        for _ in range(max(0, count)):
            self._advance_column_with_indent_step(indent_step_height)

    def ensure_room(self: _VerticalPageRenderer, char_height: int | None = None, continuation_indent_chars: int = 0) -> None:
        """Ensure the current column has space for the next glyph or block.

        When the current Y position would exceed the bottom margin after placing a
        glyph of ``char_height``, the renderer advances to a new column using the
        provided continuation indent.

        Args:
            char_height: Height of the next element in pixels. Defaults to the body
                font size when omitted.
            continuation_indent_chars: Indent to apply if a column advance becomes
                necessary.
        """
        char_height = char_height or self.args.font_size
        effective_margin_b = _effective_vertical_layout_bottom_margin(self.args.margin_b, self.args.font_size)
        if self.curr_y > self.args.height - effective_margin_b - char_height:
            self._advance_column_with_indent_step(self._indent_step_height(continuation_indent_chars))

    def insert_paragraph_indent(self: _VerticalPageRenderer, indent_chars: int = 0, continuation_indent_chars: int | None = None) -> None:
        """Insert vertical space that represents a paragraph indent.

        The indent is implemented as a Y offset measured in whole character steps. If
        the resulting position would overflow the current column, the renderer advances
        to a new column and reapplies the continuation indent there.

        Args:
            indent_chars: Indent width in character units.
            continuation_indent_chars: Indent to apply after an automatic column break.
                When omitted, the same value as ``indent_chars`` is reused.
        """
        indent_chars = max(0, int(indent_chars or 0))
        if indent_chars <= 0:
            return
        if continuation_indent_chars is None:
            continuation_indent_chars = indent_chars
        continuation_indent_chars = max(0, int(continuation_indent_chars or 0))
        self.curr_y += self._indent_step_height(indent_chars)
        self.ensure_room(self.args.font_size, continuation_indent_chars=continuation_indent_chars)

    def get_page_image_draw(self: _VerticalPageRenderer, page_index: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        if page_index == len(self.page_entries):
            return self.img, self.draw
        target_img = self.page_entries[page_index]['image']
        target_draw = self._page_draw_cache.get(page_index)
        if target_draw is None:
            target_draw = create_image_draw(target_img)
            self._page_draw_cache[page_index] = target_draw
        return target_img, target_draw

    def _draw_text_run_plain(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *, wrap_indent_step: int = 0,
                             is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                draw_hang_pair(
                    draw_obj, tokens[idx + 1], (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_ruby_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *,
                                  ruby_overlay_groups: list[RubyOverlayGroup], wrap_indent_step: int = 0,
                                  is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_ruby_group = _append_ruby_overlay_group
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token) + len(next_token))
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_overlay_cells_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *,
                                          overlay_cells: list[OverlayCell], wrap_indent_step: int = 0,
                                          is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_overlay_cell = _append_overlay_cell
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token + next_token)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_overlay_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: VerticalLayoutHints, run_font: Any, *,
                                    ruby_overlay_groups: list[RubyOverlayGroup] | None = None,
                                    overlay_cells: list[OverlayCell] | None = None, wrap_indent_step: int = 0,
                                    is_bold: bool = False, is_italic: bool = False) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_ruby_group = _append_ruby_overlay_group if ruby_overlay_groups is not None else None
        append_overlay_cell = _append_overlay_cell if overlay_cells is not None else None
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                if append_ruby_group is not None:
                    append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token) + len(next_token))
                if append_overlay_cell is not None:
                    append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token + next_token)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            if append_ruby_group is not None:
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            if append_overlay_cell is not None:
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_segment_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                    segment_infos: list[SegmentInfo], wrap_indent_step: int = 0, is_bold: bool = False,
                                    is_italic: bool = False, needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                append_segment_info(current_page_index, curr_x, curr_y, len(token) + len(next_token), token + next_token)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_segment_and_ruby_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                             segment_infos: list[SegmentInfo], ruby_overlay_groups: list[RubyOverlayGroup],
                                             wrap_indent_step: int = 0, is_bold: bool = False, is_italic: bool = False,
                                             needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        append_ruby_group = _append_ruby_overlay_group
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                base_len = len(token) + len(next_token)
                cell_text = token + next_token
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, base_len)
                append_segment_info(current_page_index, curr_x, curr_y, base_len, cell_text)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def _draw_text_run_segment_and_overlay_cells_only(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                                      segment_infos: list[SegmentInfo], overlay_cells: list[OverlayCell],
                                                      wrap_indent_step: int = 0, is_bold: bool = False, is_italic: bool = False,
                                                      needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        append_overlay_cell = _append_overlay_cell
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                base_len = len(token) + len(next_token)
                cell_text = token + next_token
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, cell_text)
                append_segment_info(current_page_index, curr_x, curr_y, base_len, cell_text)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()


    def _draw_text_run_segment_and_overlay_mixed(self: _VerticalPageRenderer, tokens: Sequence[str], layout_hints: Sequence[str], run_font: Any, *,
                                                 segment_infos: list[SegmentInfo], ruby_overlay_groups: list[RubyOverlayGroup], overlay_cells: list[OverlayCell],
                                                 wrap_indent_step: int = 0, is_bold: bool = False, is_italic: bool = False,
                                                 needs_base_len: bool = True, needs_cell_text: bool = True) -> None:
        token_count = len(tokens)
        if token_count <= 0:
            return
        args = self.args
        font_size = args.font_size
        page_height = args.height
        margin_t = args.margin_t
        margin_b = args.margin_b
        line_step = font_size + 2
        kinsoku_mode = _normalize_kinsoku_mode(args.kinsoku_mode)
        action_cache: dict[tuple[int, int, bool], str] = {}
        choose_layout_action = _choose_vertical_layout_action_with_hints
        advance_for_wrap = self._advance_column_with_indent_step
        draw_char = draw_char_tate
        draw_hang_pair = draw_hanging_punctuation
        draw_hang_bracket = draw_hanging_closing_bracket
        is_lowerable_hang_bracket = _is_lowerable_hanging_closing_bracket
        append_segment = segment_infos.append
        append_ruby_group = _append_ruby_overlay_group
        append_overlay_cell = _append_overlay_cell
        raise_if_cancelled = _raise_if_cancelled
        remaining_slots = _remaining_vertical_slots_for_current_column
        should_cancel = self.should_cancel
        has_started_document = bool(self.has_started_document)
        has_drawn_on_page = bool(self.has_drawn_on_page)
        current_page_index = len(self.page_entries)
        curr_x = self.curr_x
        curr_y = self.curr_y
        draw_obj = self.draw
        slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        if needs_base_len and needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                    'cell_text': cell_text,
                })
        elif needs_base_len:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'base_len': base_len,
                })
        elif needs_cell_text:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                    'cell_text': cell_text,
                })
        else:
            def append_segment_info(page_index: int, x_pos: int, y_pos: int, base_len: int, cell_text: str) -> None:
                append_segment({
                    'page_index': page_index,
                    'x': x_pos,
                    'y': y_pos,
                })

        def sync_renderer_state() -> None:
            self.curr_x = curr_x
            self.curr_y = curr_y
            self.has_drawn_on_page = has_drawn_on_page
            self.has_started_document = has_started_document

        def refresh_after_wrap() -> None:
            nonlocal current_page_index, has_drawn_on_page, has_started_document, curr_x, curr_y, draw_obj, slots_left
            current_page_index = len(self.page_entries)
            has_drawn_on_page = bool(self.has_drawn_on_page)
            has_started_document = bool(self.has_started_document)
            curr_x = self.curr_x
            curr_y = self.curr_y
            draw_obj = self.draw
            slots_left = remaining_slots(curr_y, margin_t, page_height, margin_b, font_size, wrap_indent_step)

        idx = 0
        while idx < token_count:
            raise_if_cancelled(should_cancel)
            token = tokens[idx]
            action = choose_layout_action(
                layout_hints,
                idx,
                slots_left,
                curr_y > margin_t,
                kinsoku_mode=kinsoku_mode,
                action_cache=action_cache,
            )
            if action == 'advance':
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                continue
            if action == 'hang_pair':
                if is_lowerable_hang_bracket(token):
                    draw_hang_bracket(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size, page_height,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                else:
                    draw_char(
                        draw_obj, token, (curr_x, curr_y), run_font, font_size,
                        is_bold=is_bold, is_italic=is_italic,
                    )
                next_token = tokens[idx + 1]
                draw_hang_pair(
                    draw_obj, next_token, (curr_x, curr_y), run_font, font_size, page_height,
                    is_bold=is_bold, is_italic=is_italic,
                )
                base_len = len(token) + len(next_token)
                cell_text = token + next_token
                append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, base_len)
                append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, cell_text)
                append_segment_info(current_page_index, curr_x, curr_y, base_len, cell_text)
                if not has_drawn_on_page:
                    has_drawn_on_page = True
                if not has_started_document:
                    has_started_document = True
                sync_renderer_state()
                advance_for_wrap(wrap_indent_step)
                refresh_after_wrap()
                idx += 2
                continue

            draw_char(
                draw_obj, token, (curr_x, curr_y), run_font, font_size,
                is_bold=is_bold, is_italic=is_italic,
            )
            append_ruby_group(ruby_overlay_groups, current_page_index, curr_x, curr_y, len(token))
            append_overlay_cell(overlay_cells, current_page_index, curr_x, curr_y, token)
            append_segment_info(current_page_index, curr_x, curr_y, len(token), token)
            curr_y += line_step
            slots_left -= 1
            if not has_drawn_on_page:
                has_drawn_on_page = True
            if not has_started_document:
                has_started_document = True
            idx += 1

        sync_renderer_state()

    def draw_text_run(self: _VerticalPageRenderer, text: str, run_font: Any, *, wrap_indent_chars: int = 0, segment_infos: list[SegmentInfo] | None = None,
                      ruby_overlay_groups: list[RubyOverlayGroup] | None = None, overlay_cells: list[OverlayCell] | None = None,
                      is_bold: bool = False, is_italic: bool = False, segment_info_needs_base_len: bool = True,
                      segment_info_needs_cell_text: bool = True) -> None:
        """Draw a single text run into the current page or subsequent columns.

        This method performs glyph-level wrapping, records per-segment placement into
        ``segment_infos`` for later ruby or emphasis overlay, and honors bold/italic
        styling hints supplied by the caller.

        Args:
            text: Text content to draw.
            run_font: Font object selected for this run.
            wrap_indent_chars: Continuation indent applied after automatic column
                breaks while this run is being drawn.
            segment_infos: Optional list that receives placement metadata for each
                contiguous segment rendered from this run.
            ruby_overlay_groups: Optional compact ruby overlay groups updated while
                rendering this run. When supplied, ruby metadata can be captured
                without allocating per-cell ``base_len`` entries.
            overlay_cells: Optional compact overlay cell tuples updated while
                rendering this run. When supplied, emphasis and side-line metadata
                can be captured without allocating per-cell dictionaries.
            is_bold: Whether bold styling should be simulated for this run.
            is_italic: Whether italic styling should be simulated for this run.
            segment_info_needs_base_len: Whether captured segment metadata should
                include ``base_len`` for ruby overlay grouping.
            segment_info_needs_cell_text: Whether captured segment metadata should
                include ``cell_text`` for emphasis or side-line filtering.
        """
        if not text:
            return
        _raise_if_cancelled(self.should_cancel)
        wrap_indent_chars = max(0, int(wrap_indent_chars or 0))
        wrap_indent_step = self._indent_step_height(wrap_indent_chars)
        build_single_hints = _build_single_token_vertical_layout_hints
        tokenize_vertical_text = _tokenize_vertical_text_cached
        build_layout_hints = _build_vertical_layout_hints
        if len(text) == 1:
            tokens = (text,)
            layout_hints = build_single_hints(text)
        else:
            tokens = tokenize_vertical_text(text)
            layout_hints = build_layout_hints(tokens)
        capture_mask = (
            (4 if segment_infos is not None else 0)
            | (2 if ruby_overlay_groups is not None else 0)
            | (1 if overlay_cells is not None else 0)
        )
        if capture_mask == 0:
            self._draw_text_run_plain(
                tokens,
                layout_hints,
                run_font,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        if capture_mask == 2:
            self._draw_text_run_ruby_only(
                tokens,
                layout_hints,
                run_font,
                ruby_overlay_groups=ruby_overlay_groups,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        if capture_mask == 1:
            self._draw_text_run_overlay_cells_only(
                tokens,
                layout_hints,
                run_font,
                overlay_cells=overlay_cells,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        if capture_mask == 3:
            self._draw_text_run_overlay_only(
                tokens,
                layout_hints,
                run_font,
                ruby_overlay_groups=ruby_overlay_groups,
                overlay_cells=overlay_cells,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            return
        needs_base_len = bool(segment_info_needs_base_len)
        needs_cell_text = bool(segment_info_needs_cell_text) or bool(capture_mask & 1)
        if capture_mask == 4:
            self._draw_text_run_segment_only(
                tokens,
                layout_hints,
                run_font,
                segment_infos=segment_infos,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
                needs_base_len=needs_base_len,
                needs_cell_text=needs_cell_text,
            )
            return
        if capture_mask == 6:
            self._draw_text_run_segment_and_ruby_only(
                tokens,
                layout_hints,
                run_font,
                segment_infos=segment_infos,
                ruby_overlay_groups=ruby_overlay_groups,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
                needs_base_len=needs_base_len,
                needs_cell_text=needs_cell_text,
            )
            return
        if capture_mask == 5:
            self._draw_text_run_segment_and_overlay_cells_only(
                tokens,
                layout_hints,
                run_font,
                segment_infos=segment_infos,
                overlay_cells=overlay_cells,
                wrap_indent_step=wrap_indent_step,
                is_bold=is_bold,
                is_italic=is_italic,
                needs_base_len=needs_base_len,
                needs_cell_text=needs_cell_text,
            )
            return
        self._draw_text_run_segment_and_overlay_mixed(
            tokens,
            layout_hints,
            run_font,
            segment_infos=segment_infos,
            ruby_overlay_groups=ruby_overlay_groups,
            overlay_cells=overlay_cells,
            wrap_indent_step=wrap_indent_step,
            is_bold=is_bold,
            is_italic=is_italic,
            needs_base_len=needs_base_len,
            needs_cell_text=needs_cell_text,
        )
        return

    def _ruby_group_capacity(self: _VerticalPageRenderer, group: Mapping[str, Any], segment_index: int, total_segments: int) -> int:
        return _ruby_group_capacity_for_args(group, segment_index, total_segments, self.args)

    def _get_code_font(self: _VerticalPageRenderer, default_font: Any | None = None) -> Any:
        if self.code_font is not None:
            return self.code_font
        loader = self._code_font_loader
        if callable(loader):
            try:
                self.code_font = loader()
            except Exception:
                self.code_font = default_font or self.font
        else:
            self.code_font = default_font or self.font
        return self.code_font

    def _select_run_font(self: _VerticalPageRenderer, run: Mapping[str, Any] | None, default_font: Any | None = None) -> Any:
        base_font = default_font or self.font
        return self._get_code_font(base_font) if bool((run or {}).get('code', False)) else base_font

    def _collect_repeated_run_texts(self: _VerticalPageRenderer, runs: Sequence[Mapping[str, Any]] | None, *, min_len: int = 7, max_len: int = 256) -> set[str]:
        if not runs:
            return set()
        min_len = max(1, int(min_len or 1))
        max_len = max(min_len, int(max_len or min_len))
        repeated_counts: dict[str, int] = {}
        repeated_texts: set[str] = set()
        for run in runs:
            if not run:
                continue
            seg_text = str(run.get('text', '') or '')
            text_len = len(seg_text)
            if text_len < min_len or text_len > max_len:
                continue
            next_count = repeated_counts.get(seg_text, 0) + 1
            if next_count >= 2:
                repeated_texts.add(seg_text)
            repeated_counts[seg_text] = next_count
        return repeated_texts

    def draw_runs(self: _VerticalPageRenderer, runs: Sequence[Mapping[str, Any]] | None, *, default_font: Any | None = None, wrap_indent_chars: int = 0) -> None:
        """Draw a sequence of rich text runs and their overlays.

        Each run may contain formatting flags such as ``bold``, ``italic``, ``code``,
        ``ruby``, ``emphasis``, or ``side_line``. The method renders the base text run
        first and then applies ruby, emphasis marks, and side lines using the segment
        metadata captured during drawing.

        Args:
            runs: Sequence of run dictionaries, typically produced by text/Markdown or
                EPUB preprocessing.
            default_font: Base font to use for runs that do not request a code font.
            wrap_indent_chars: Continuation indent applied after automatic column
                breaks while any of the supplied runs are being drawn.
        """
        _raise_if_cancelled(self.should_cancel)
        base_font = default_font or self.font
        wrap_indent_chars = max(0, int(wrap_indent_chars or 0))
        wrap_indent_step = self._indent_step_height(wrap_indent_chars)
        get_code_font = self._get_code_font
        draw_text_run = self.draw_text_run
        draw_text_run_plain = self._draw_text_run_plain
        draw_text_run_ruby_only = self._draw_text_run_ruby_only
        draw_text_run_overlay_cells_only = self._draw_text_run_overlay_cells_only
        draw_text_run_overlay_only = self._draw_text_run_overlay_only
        build_single_hints = _build_single_token_vertical_layout_hints
        tokenize_vertical_text = _tokenize_vertical_text_cached
        build_layout_hints_cached = _build_vertical_layout_hints_cached
        draw_split_ruby_groups = self.draw_split_ruby_groups
        draw_emphasis_marks_cells = self.draw_emphasis_marks_cells
        draw_side_lines_cells = self.draw_side_lines_cells
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        code_font = None
        repeated_medium_texts = self._collect_repeated_run_texts(runs, min_len=7, max_len=256)
        local_run_layout_cache: dict[str, tuple[tuple[str, ...], VerticalLayoutHints]] = {}
        local_run_layout_cache_get = local_run_layout_cache.get
        local_run_layout_cache_set = local_run_layout_cache.__setitem__
        if repeated_medium_texts:
            for repeated_text in repeated_medium_texts:
                repeated_tokens = tokenize_vertical_text(repeated_text)
                local_run_layout_cache_set(repeated_text, (repeated_tokens, build_layout_hints_cached(repeated_tokens)))
        for run in runs or ():
            raise_if_cancelled(should_cancel)
            if not run:
                continue
            get_value = run.get
            seg_text = get_value('text', '')
            if not seg_text:
                continue
            ruby = get_value('ruby', '')
            emphasis = get_value('emphasis', '')
            side_line = get_value('side_line', '')
            is_bold = bool(get_value('bold'))
            is_italic = bool(get_value('italic'))
            if get_value('code', False):
                if code_font is None:
                    code_font = get_code_font(base_font)
                run_font = code_font
            else:
                run_font = base_font
            run_mode = (
                (4 if ruby else 0)
                | (2 if emphasis else 0)
                | (1 if side_line else 0)
            )
            overlay_mode = run_mode & 3
            text_len = len(seg_text)
            use_cached_direct_path = (text_len <= 8) or (seg_text in repeated_medium_texts)
            if use_cached_direct_path:
                cached_run_layout = local_run_layout_cache_get(seg_text)
                if cached_run_layout is None:
                    if text_len == 1:
                        tokens = (seg_text,)
                        layout_hints = build_single_hints(seg_text)
                    else:
                        tokens = tokenize_vertical_text(seg_text)
                        layout_hints = build_layout_hints_cached(tokens)
                    local_run_layout_cache_set(seg_text, (tokens, layout_hints))
                else:
                    tokens, layout_hints = cached_run_layout
                if run_mode == 0:
                    draw_text_run_plain(
                        tokens,
                        layout_hints,
                        run_font,
                        wrap_indent_step=wrap_indent_step,
                        is_bold=is_bold,
                        is_italic=is_italic,
                    )
                    continue
                if run_mode == 4:
                    ruby_overlay_groups: list[RubyOverlayGroup] = []
                    draw_text_run_ruby_only(
                        tokens,
                        layout_hints,
                        run_font,
                        ruby_overlay_groups=ruby_overlay_groups,
                        wrap_indent_step=wrap_indent_step,
                        is_bold=is_bold,
                        is_italic=is_italic,
                    )
                    if ruby_overlay_groups:
                        draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
                    continue
                if run_mode < 4:
                    overlay_cells: list[OverlayCell] = []
                    draw_text_run_overlay_cells_only(
                        tokens,
                        layout_hints,
                        run_font,
                        overlay_cells=overlay_cells,
                        wrap_indent_step=wrap_indent_step,
                        is_bold=is_bold,
                        is_italic=is_italic,
                    )
                    if overlay_cells:
                        if overlay_mode & 2:
                            draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=False)
                        if overlay_mode & 1:
                            draw_side_lines_cells(overlay_cells, side_line, ruby_text='', emphasis_kind=emphasis)
                    continue
                ruby_overlay_groups: list[RubyOverlayGroup] = []
                overlay_cells: list[OverlayCell] = []
                draw_text_run_overlay_only(
                    tokens,
                    layout_hints,
                    run_font,
                    ruby_overlay_groups=ruby_overlay_groups,
                    overlay_cells=overlay_cells,
                    wrap_indent_step=wrap_indent_step,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                if ruby_overlay_groups:
                    draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
                if overlay_cells:
                    if overlay_mode & 2:
                        draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=True)
                    if overlay_mode & 1:
                        draw_side_lines_cells(overlay_cells, side_line, ruby_text=ruby, emphasis_kind=emphasis)
                continue
            if run_mode == 0:
                draw_text_run(
                    seg_text,
                    run_font,
                    wrap_indent_chars=wrap_indent_chars,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                continue
            if run_mode == 4:
                ruby_overlay_groups: list[RubyOverlayGroup] = []
                draw_text_run(
                    seg_text,
                    run_font,
                    wrap_indent_chars=wrap_indent_chars,
                    ruby_overlay_groups=ruby_overlay_groups,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                if ruby_overlay_groups:
                    draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
                continue
            if run_mode < 4:
                overlay_cells: list[OverlayCell] = []
                draw_text_run(
                    seg_text,
                    run_font,
                    wrap_indent_chars=wrap_indent_chars,
                    overlay_cells=overlay_cells,
                    is_bold=is_bold,
                    is_italic=is_italic,
                )
                if overlay_cells:
                    if overlay_mode & 2:
                        draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=False)
                    if overlay_mode & 1:
                        draw_side_lines_cells(overlay_cells, side_line, ruby_text='', emphasis_kind=emphasis)
                continue
            ruby_overlay_groups: list[RubyOverlayGroup] = []
            overlay_cells: list[OverlayCell] = []
            draw_text_run(
                seg_text,
                run_font,
                wrap_indent_chars=wrap_indent_chars,
                ruby_overlay_groups=ruby_overlay_groups,
                overlay_cells=overlay_cells,
                is_bold=is_bold,
                is_italic=is_italic,
            )
            if ruby_overlay_groups:
                draw_split_ruby_groups(ruby_overlay_groups, ruby, is_bold=is_bold, is_italic=is_italic)
            if overlay_cells:
                if overlay_mode & 2:
                    draw_emphasis_marks_cells(overlay_cells, emphasis, prefer_left=True)
                if overlay_mode & 1:
                    draw_side_lines_cells(overlay_cells, side_line, ruby_text=ruby, emphasis_kind=emphasis)

    def draw_split_ruby(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]], rt_text: str, *, is_bold: bool = False, is_italic: bool = False) -> None:
        _raise_if_cancelled(self.should_cancel)
        if not rt_text or not segment_infos:
            return
        self.draw_split_ruby_groups(
            _build_ruby_overlay_groups(segment_infos),
            rt_text,
            is_bold=is_bold,
            is_italic=is_italic,
        )

    def draw_split_ruby_groups(self: _VerticalPageRenderer, grouped: Sequence[Mapping[str, Any]], rt_text: str, *, is_bold: bool = False, is_italic: bool = False) -> None:
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        raise_if_cancelled(should_cancel)
        if not rt_text or not grouped:
            return
        total_segments = len(grouped)
        if total_segments == 1:
            ruby_parts = [str(rt_text or '')]
        else:
            segment_lengths = [group['base_len'] for group in grouped]
            ruby_group_capacity = self._ruby_group_capacity
            segment_capacities = [
                ruby_group_capacity(group, idx, total_segments)
                for idx, group in enumerate(grouped)
            ]
            ruby_parts = _split_ruby_text_segments(rt_text, segment_lengths, segment_capacities=segment_capacities)

        args = self.args
        ruby_size = args.ruby_size
        font_size = args.font_size
        min_ry = args.margin_t
        effective_bottom_margin = _effective_ruby_overlay_bottom_margin(args)
        max_ry = args.height - effective_bottom_margin - ruby_size
        max_visible_ry = args.height - effective_bottom_margin
        step_y = ruby_size + 2
        get_page_image_draw = self.get_page_image_draw
        draw_char_tate_fn = draw_char_tate
        ruby_font = self.ruby_font
        cached_page_index = None
        target_draw = None
        last_segment_index = total_segments - 1
        center_single_segment = total_segments == 1
        ruby_bbox_cache: dict[str, tuple[int, int, int, int]] = {}
        for idx, (group, ruby_part) in enumerate(zip(grouped, ruby_parts)):
            raise_if_cancelled(should_cancel)
            if not ruby_part:
                continue
            group_page_index = group['page_index']
            if cached_page_index != group_page_index or target_draw is None:
                _target_img, target_draw = get_page_image_draw(group_page_index)
                cached_page_index = group_page_index
            start_y = group['start_y']
            end_y = group['end_y']
            rb_h = max(font_size, end_y - start_y + font_size)
            rt_h = len(ruby_part) * step_y
            if center_single_segment:
                ry = start_y + (rb_h - rt_h) // 2
            elif idx == 0:
                ry = end_y + font_size - rt_h
            elif idx == last_segment_index:
                ry = start_y
            else:
                ry = start_y + (rb_h - rt_h) // 2
            if ry < min_ry:
                ry = min_ry
            elif ry > max_ry:
                ry = max_ry
            ruby_x = group['x'] + font_size + 1
            for r_char in ruby_part:
                raise_if_cancelled(should_cancel)
                bbox = ruby_bbox_cache.get(r_char)
                if bbox is None:
                    bbox = _get_text_bbox(ruby_font, r_char, is_bold=is_bold)
                    ruby_bbox_cache[r_char] = bbox
                bbox_x0, bbox_y0, bbox_x1, bbox_y1 = bbox
                min_draw_x = -int(bbox_x0)
                max_draw_x = args.width - int(bbox_x1)
                if max_draw_x < min_draw_x:
                    ry += step_y
                    continue
                draw_x = max(min_draw_x, min(int(ruby_x), max_draw_x))
                min_draw_y = min_ry - int(bbox_y0)
                max_draw_y = max_visible_ry - int(bbox_y1)
                if max_draw_y < min_draw_y:
                    ry += step_y
                    continue
                draw_y = max(min_draw_y, min(int(ry), max_draw_y))
                if min_ry <= draw_y + int(bbox_y0) and draw_y + int(bbox_y1) <= max_visible_ry:
                    draw_char_tate_fn(
                        target_draw, r_char, (draw_x, draw_y), ruby_font, ruby_size,
                        is_bold=is_bold, ruby_mode=True, is_italic=is_italic,
                    )
                ry += step_y

    def _should_draw_emphasis_for_cell(self: _VerticalPageRenderer, cell_text: str) -> bool:
        return _should_draw_emphasis_for_cell_cached(str(cell_text or ''))

    def _get_emphasis_font(self: _VerticalPageRenderer) -> Any:
        emphasis_size = max(8, int(round(self.args.font_size * 0.48)))
        cache_key = (self.emphasis_font_value or '', emphasis_size, id(self.font))
        if self._emphasis_font_cache_key == cache_key and self._emphasis_font_cache is not None:
            return self._emphasis_font_cache
        emphasis_font = self.font
        if self.emphasis_font_value:
            try:
                emphasis_font = load_truetype_font(self.emphasis_font_value, emphasis_size)
            except Exception:
                emphasis_font = self.font
        self._emphasis_font_cache_key = cache_key
        self._emphasis_font_cache = emphasis_font
        self._emphasis_metrics_cache.clear()
        return emphasis_font

    def _get_emphasis_marker_metrics(self: _VerticalPageRenderer, marker: str) -> tuple[int, int, int, int]:
        cache_key = str(marker or '')
        cached = self._emphasis_metrics_cache.get(cache_key)
        if cached is not None:
            return cached
        emphasis_font = self._get_emphasis_font()
        bbox = _get_text_bbox(emphasis_font, cache_key, is_bold=False)
        mark_w = max(1, bbox[2] - bbox[0])
        mark_h = max(1, bbox[3] - bbox[1])
        metrics = (mark_w, mark_h, int(bbox[0]), int(bbox[1]))
        self._emphasis_metrics_cache[cache_key] = metrics
        return metrics

    def draw_emphasis_marks(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]], emphasis_kind: str, *, prefer_left: bool = False) -> None:
        _raise_if_cancelled(self.should_cancel)
        if not emphasis_kind or not segment_infos:
            return
        overlay_cells = [
            (int(info['page_index']), int(info['x']), int(info['y']), str(info.get('cell_text', '') or ''))
            for info in segment_infos
        ]
        self.draw_emphasis_marks_cells(overlay_cells, emphasis_kind, prefer_left=prefer_left)

    def draw_emphasis_marks_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell], emphasis_kind: str, *, prefer_left: bool = False) -> None:
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        raise_if_cancelled(should_cancel)
        marker = AOZORA_EMPHASIS_MARKERS.get(emphasis_kind)
        if not marker or not overlay_cells:
            return
        emphasis_font = self._get_emphasis_font()
        emphasis_size = max(8, int(round(self.args.font_size * 0.48)))
        mark_w, mark_h, bbox_x0, bbox_y0 = self._get_emphasis_marker_metrics(marker)
        x_offset = max(1, emphasis_size // 6) if prefer_left else max(1, emphasis_size // 8)
        get_page_image_draw = self.get_page_image_draw
        should_draw_for_cell = self._should_draw_emphasis_for_cell
        args = self.args
        font_size = args.font_size
        mark_y_offset = max(0, (font_size - mark_h) // 2) - bbox_y0
        mark_x_delta = (-mark_w - x_offset - bbox_x0) if prefer_left else (font_size + x_offset - bbox_x0)
        min_mark_y = int(args.margin_t) - bbox_y0
        max_mark_y = int(args.height - _effective_vertical_layout_bottom_margin(args.margin_b, font_size) - mark_h - bbox_y0)
        min_mark_x = -bbox_x0
        max_mark_x = int(args.width - mark_w - bbox_x0)
        cached_page_index = None
        draw_text = None
        for page_index, x_pos, y_pos, cell_text in overlay_cells:
            raise_if_cancelled(should_cancel)
            if not should_draw_for_cell(cell_text):
                continue
            if cached_page_index != page_index or draw_text is None:
                _target_img, target_draw = get_page_image_draw(page_index)
                cached_page_index = page_index
                draw_text = target_draw.text
            mark_y = int(y_pos + mark_y_offset)
            if max_mark_y >= min_mark_y:
                mark_y = min(max(mark_y, min_mark_y), max_mark_y)
            else:
                mark_y = min_mark_y
            mark_x = int(x_pos + mark_x_delta)
            if max_mark_x >= min_mark_x:
                mark_x = min(max(mark_x, min_mark_x), max_mark_x)
            else:
                mark_x = min_mark_x
            draw_text((mark_x, mark_y), marker, font=emphasis_font, fill=0)

    def _should_draw_side_line_for_cell(self: _VerticalPageRenderer, cell_text: str) -> bool:
        return _should_draw_side_line_for_cell_cached(str(cell_text or ''))

    def _iter_side_line_groups(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]]) -> list[SideLineGroup]:
        overlay_cells = [
            (int(info['page_index']), int(info['x']), int(info['y']), str(info.get('cell_text', '') or ''))
            for info in segment_infos
        ]
        return self._iter_side_line_groups_cells(overlay_cells)

    def _iter_side_line_spans_cells_iter(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell]) -> Iterator[SideLineSpan]:
        current_page_index = None
        current_x = None
        start_y = None
        end_y = None
        prev_y = None
        max_step = self.args.font_size + 3
        should_draw = self._should_draw_side_line_for_cell

        for page_index, x_pos, y_pos, cell_text in overlay_cells:
            if not should_draw(cell_text):
                if current_page_index is not None:
                    yield (current_page_index, current_x, start_y, end_y)
                current_page_index = None
                current_x = None
                start_y = None
                end_y = None
                prev_y = None
                continue
            if (
                current_page_index == page_index
                and current_x == x_pos
                and prev_y is not None
                and 0 <= (y_pos - prev_y) <= max_step
            ):
                end_y = y_pos
            else:
                if current_page_index is not None:
                    yield (current_page_index, current_x, start_y, end_y)
                current_page_index = page_index
                current_x = x_pos
                start_y = y_pos
                end_y = y_pos
            prev_y = y_pos

        if current_page_index is not None:
            yield (current_page_index, current_x, start_y, end_y)

    def _iter_side_line_spans_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell]) -> list[SideLineSpan]:
        return list(self._iter_side_line_spans_cells_iter(overlay_cells))

    def _iter_side_line_groups_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell]) -> list[SideLineGroup]:
        groups: list[SideLineGroup] = []
        for page_index, x_pos, start_y, end_y in self._iter_side_line_spans_cells(overlay_cells):
            if start_y == end_y:
                infos = [(page_index, x_pos, start_y, '')]
            else:
                infos = [(page_index, x_pos, start_y, ''), (page_index, x_pos, end_y, '')]
            groups.append({'page_index': page_index, 'x': x_pos, 'infos': infos})
        return groups

    def _draw_single_side_line(self: _VerticalPageRenderer, target_draw: ImageDraw.ImageDraw, x: int, y1: int, y2: int, line_kind: str, width: int = 1) -> None:
        draw_line = target_draw.line
        x = int(x)
        y1 = int(y1)
        y2 = max(y1, int(y2))
        if y1 == y2:
            # Keep degenerate guard-clamped spans as a valid two-endpoint line.
            # Some ImageDraw backends reject a one-point polyline, notably for
            # wavy side-lines after lower-bound and bottom-guard clamping.
            draw_line((x, y1, x, y2), fill=0, width=width)
            return
        if line_kind not in {'wavy', 'dashed', 'chain'}:
            draw_line((x, y1, x, y2), fill=0, width=width)
            return
        pattern_a, pattern_b, _unused = _get_side_line_pattern(self.args.font_size, line_kind)
        if line_kind == 'wavy':
            points = []
            append_point = points.append
            amplitude = pattern_a
            wavelength = pattern_b
            y = y1
            idx = 0
            while y <= y2:
                offset = -amplitude if idx % 2 == 0 else amplitude
                append_point((x + offset, y))
                y += wavelength
                idx += 1
            if not points or points[-1][1] != y2:
                offset = -amplitude if idx % 2 == 0 else amplitude
                append_point((x + offset, y2))
            draw_line(points, fill=0, width=width)
            return
        seg = pattern_a
        gap = pattern_b
        y = y1
        while y <= y2:
            seg_end = min(y2, y + seg)
            draw_line((x, y, x, seg_end), fill=0, width=width)
            y = seg_end + gap

    def draw_side_lines(self: _VerticalPageRenderer, segment_infos: Sequence[Mapping[str, Any]], side_line_kind: str, *, ruby_text: str = '', emphasis_kind: str = '') -> None:
        _raise_if_cancelled(self.should_cancel)
        if not side_line_kind or not segment_infos:
            return
        overlay_cells = [
            (int(info['page_index']), int(info['x']), int(info['y']), str(info.get('cell_text', '') or ''))
            for info in segment_infos
        ]
        self.draw_side_lines_cells(overlay_cells, side_line_kind, ruby_text=ruby_text, emphasis_kind=emphasis_kind)

    def draw_side_lines_cells(self: _VerticalPageRenderer, overlay_cells: Sequence[OverlayCell], side_line_kind: str, *, ruby_text: str = '', emphasis_kind: str = '') -> None:
        raise_if_cancelled = _raise_if_cancelled
        should_cancel = self.should_cancel
        raise_if_cancelled(should_cancel)
        if not side_line_kind or not overlay_cells:
            return
        args = self.args
        font_size = args.font_size
        prefer_left = bool(emphasis_kind)
        is_double = side_line_kind == 'double'
        right_padding, left_padding, base_gap, width, offset = _get_side_line_style(
            font_size,
            args.ruby_size,
            str(side_line_kind or ''),
            bool(ruby_text),
            prefer_left,
            prefer_left,
        )
        y_inset = max(1, int(round(font_size * 0.08)))
        get_page_image_draw = self.get_page_image_draw
        draw_side_line = self._draw_single_side_line
        iter_spans = self._iter_side_line_spans_cells_iter
        cached_page_index = None
        target_draw = None
        double_offset = max(2, offset)
        if prefer_left:
            base_x_delta = -base_gap - left_padding
            secondary_x_delta = -double_offset if is_double else None
        else:
            base_x_delta = font_size + base_gap + right_padding
            secondary_x_delta = double_offset if is_double else None
        primary_kind = 'solid' if is_double else side_line_kind
        primary_width = 1 if is_double else width
        bottom_guard = int(args.height - _effective_vertical_layout_bottom_margin(args.margin_b, font_size))
        min_y = int(args.margin_t)
        max_primary_x_extent = _side_line_horizontal_extent(font_size, str(primary_kind or ''), primary_width)
        min_primary_x = max_primary_x_extent
        max_primary_x = int(args.width - 1 - max_primary_x_extent)

        def clamp_span_y(start: int, end: int) -> tuple[int, int]:
            y1 = _clamp_int(start + y_inset, min_y, bottom_guard)
            y2 = _clamp_int(end + font_size - y_inset, min_y, bottom_guard)
            if y2 < y1:
                y2 = y1
            return y1, y2

        def clamp_line_x(x: int, kind: str, line_width: int) -> int:
            extent = _side_line_horizontal_extent(font_size, str(kind or ''), line_width)
            return _clamp_int(x, extent, int(args.width - 1 - extent))

        def clamp_line_pair_x(primary_x: int, secondary_x: int) -> tuple[int, int]:
            primary_extent = _side_line_horizontal_extent(font_size, str(primary_kind or ''), primary_width)
            secondary_extent = _side_line_horizontal_extent(font_size, 'solid', 1)
            primary_x = int(primary_x)
            secondary_x = int(secondary_x)
            canvas_right = int(args.width - 1)
            min_shift = max(primary_extent - primary_x, secondary_extent - secondary_x)
            max_shift = min(
                canvas_right - primary_extent - primary_x,
                canvas_right - secondary_extent - secondary_x,
            )
            if min_shift <= max_shift:
                shift = _clamp_int(0, min_shift, max_shift)
                return primary_x + shift, secondary_x + shift
            return (
                clamp_line_x(primary_x, primary_kind, primary_width),
                clamp_line_x(secondary_x, 'solid', 1),
            )

        if secondary_x_delta is None:
            for page_index, x_pos, start_y, end_y in iter_spans(overlay_cells):
                raise_if_cancelled(should_cancel)
                if cached_page_index != page_index or target_draw is None:
                    _target_img, target_draw = get_page_image_draw(page_index)
                    cached_page_index = page_index
                y1, y2 = clamp_span_y(start_y, end_y)
                line_x = _clamp_int(x_pos + base_x_delta, min_primary_x, max_primary_x)
                draw_side_line(target_draw, line_x, y1, y2, primary_kind, width=primary_width)
            return
        for page_index, x_pos, start_y, end_y in iter_spans(overlay_cells):
            raise_if_cancelled(should_cancel)
            if cached_page_index != page_index or target_draw is None:
                _target_img, target_draw = get_page_image_draw(page_index)
                cached_page_index = page_index
            y1, y2 = clamp_span_y(start_y, end_y)
            base_x, secondary_x = clamp_line_pair_x(
                x_pos + base_x_delta,
                x_pos + base_x_delta + secondary_x_delta,
            )
            draw_side_line(target_draw, base_x, y1, y2, primary_kind, width=primary_width)
            draw_side_line(target_draw, secondary_x, y1, y2, 'solid', width=1)

    def draw_inline_image(self: _VerticalPageRenderer, char_img: Image.Image | None, *, wrap_indent_chars: int = 0) -> None:
        if char_img is None:
            return
        self.ensure_room(self.args.font_size, continuation_indent_chars=wrap_indent_chars)
        paste_x = self.curr_x + (self.args.font_size - char_img.width) // 2
        paste_y = self.curr_y + max(0, (self.args.font_size - char_img.height) // 2)
        self.img.paste(char_img, (paste_x, paste_y))
        self.curr_y += self.args.font_size + 2
        self.has_drawn_on_page = True
        self.has_started_document = True


def _render_text_blocks_to_page_entries(blocks: Sequence[TextBlock], font_value: str | Path, args: ConversionArgs, should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None, max_output_pages: int | None = None, render_state: dict[str, object] | None = None) -> PageEntries:
    _raise_if_cancelled(should_cancel)
    if not _has_renderable_text_blocks(blocks, should_cancel=should_cancel):
        raise RuntimeError("入力ファイルに変換できる本文がありません。")

    font = load_truetype_font(font_value, args.font_size)
    ruby_font = load_truetype_font(font_value, args.ruby_size)

    def _load_code_font() -> Any:
        code_font_value = get_code_font_value(str(font_value))
        try:
            return load_truetype_font(code_font_value, args.font_size)
        except Exception:
            return font

    page_entries: PageEntries = []
    render_progress_state = {'active_block_index': 0}
    page_limit = max(1, int(max_output_pages)) if max_output_pages else None
    page_limit_reached = False
    if render_state is not None:
        render_state.clear()
        render_state['page_limit_reached'] = False
    renderer = _VerticalPageRenderer(
        args,
        font,
        ruby_font,
        should_cancel=should_cancel,
        max_buffered_pages=page_limit,
        default_page_args=args,
        default_page_label='本文ページ',
        emphasis_font_value=font_value,
        code_font_loader=_load_code_font,
    )

    def _estimate_text_render_total() -> int:
        completed_pages = max(0, len(page_entries))
        active_block_index = int(render_progress_state.get('active_block_index', 0) or 0)
        remaining_blocks = max(0, len(blocks) - active_block_index)
        return max(1, completed_pages + remaining_blocks + 1)

    def add_page_entry(image: Image.Image, *, copy_image: bool = True, label: str = '本文ページ') -> None:
        nonlocal page_limit_reached
        if page_limit is not None and len(page_entries) >= page_limit:
            page_limit_reached = True
            return
        entry = _make_page_entry(image.copy() if copy_image else image, page_args=args, label=label)
        _apply_page_entry_margin_clip(entry)
        page_entries.append(entry)
        _emit_progress(progress_cb, len(page_entries), _estimate_text_render_total(), f'本文ページを作成中… ({len(page_entries)} ページ)')

    def spool_completed_block_pages() -> None:
        for entry in renderer.pop_page_entries():
            _raise_if_cancelled(should_cancel)
            add_page_entry(entry['image'], copy_image=False, label=entry.get('label') or '本文ページ')
        if page_limit is not None:
            remaining = page_limit - len(page_entries)
            renderer.set_page_buffer_limit(remaining if remaining > 0 else 1)

    def draw_runs(runs: Sequence[TextRun], wrap_indent_chars: int = 0) -> None:
        _raise_if_cancelled(should_cancel)
        renderer.draw_runs(runs, default_font=font, wrap_indent_chars=wrap_indent_chars)

    has_renderable_after_index = [False] * (len(blocks) + 1)
    seen_renderable = False
    for reverse_index in range(len(blocks) - 1, -1, -1):
        has_renderable_after_index[reverse_index] = seen_renderable
        if blocks[reverse_index].get('kind') not in {'blank', 'pagebreak'}:
            seen_renderable = True

    total_blocks = max(1, len(blocks))
    first_content = True
    previous_was_blank = False
    try:
        for block_index, block in enumerate(blocks, 1):
            render_progress_state['active_block_index'] = block_index
            _emit_progress(progress_cb, block_index - 1, total_blocks, f'テキストを描画中… ({max(0, block_index - 1)}/{total_blocks} ブロック)')
            block_kind = block.get('kind')
            if block_kind == 'blank':
                previous_was_blank = True
                continue
            if block_kind == 'pagebreak':
                previous_was_blank = False
                if renderer.has_pending_output:
                    renderer.flush_current_page()
                    spool_completed_block_pages()
                if page_limit is not None and len(page_entries) >= page_limit and has_renderable_after_index[block_index]:
                    page_limit_reached = True
                    break
                continue
            gap = block.get('blank_before', 1)
            if first_content:
                first_content = False
            elif renderer.has_drawn_on_page:
                renderer.advance_column(max(gap, 2 if previous_was_blank else gap))
            previous_was_blank = False
            block_indent_chars = block.get('indent_chars', 1 if block.get('indent', False) else 0)
            block_wrap_indent_chars = block.get('wrap_indent_chars', 0)
            if block.get('indent', False):
                renderer.insert_paragraph_indent(block_indent_chars)
            draw_runs(block.get('runs', []), wrap_indent_chars=block_wrap_indent_chars)
            spool_completed_block_pages()
            if page_limit is not None and len(page_entries) >= page_limit and has_renderable_after_index[block_index]:
                page_limit_reached = True
                break
    except _PreviewPageLimitReached:
        page_limit_reached = True
        spool_completed_block_pages()

    if not page_limit_reached:
        spool_completed_block_pages()
        if renderer.has_drawn_on_page:
            if page_limit is not None and len(page_entries) >= page_limit:
                page_limit_reached = True
            else:
                add_page_entry(renderer.img, copy_image=False)

    if page_limit_reached:
        _emit_progress(progress_cb, len(page_entries), max(1, page_limit or len(page_entries)), f'プレビュー生成を上限 {len(page_entries)} ページで打ち切りました。')
    if render_state is not None:
        render_state['page_limit_reached'] = bool(page_limit_reached)
    _emit_progress(progress_cb, total_blocks, total_blocks, f'テキスト描画が完了しました。({len(page_entries)} ページ)')
    return page_entries


def _render_text_blocks_to_images(blocks: Sequence[TextBlock], font_value: str | Path, args: ConversionArgs, should_cancel: CancelCallback | None = None, progress_cb: ProgressCallback | None = None, max_output_pages: int | None = None, render_state: dict[str, object] | None = None) -> list[Image.Image]:
    return [entry['image'] for entry in _render_text_blocks_to_page_entries(
        blocks,
        font_value,
        args,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
        max_output_pages=max_output_pages,
        render_state=render_state,
    )]

def _make_page_entry(image: Image.Image, page_args: ConversionArgs | None = None, label: str = '本文ページ') -> PageEntry:
    return {
        'image': image,
        'page_args': page_args,
        'label': label,
    }


def _resolve_page_entry(entry: PageEntryLike, default_args: ConversionArgs) -> tuple[Image.Image | None, ConversionArgs, str]:
    if isinstance(entry, dict):
        return cast(Image.Image | None, entry.get('image')), cast(ConversionArgs, entry.get('page_args') or default_args), str(entry.get('label') or 'ページ')
    return cast(Image.Image, entry), default_args, 'ページ'


def _append_page_entries_to_spool(page_entries: Sequence[PageEntryLike], spooled_pages: 'XTCSpooledPages', args: ConversionArgs, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None,
                                  message_builder: Callable[[int, int, PageEntryLike, str], str] | None = None, complete_message: str | Callable[[int, int, str | None], str] | None = None) -> None:
    total_pages = max(1, len(page_entries))
    last_message = None
    for page_index, entry in enumerate(page_entries, 1):
        _raise_if_cancelled(should_cancel)
        page_image, page_args, label = _resolve_page_entry(entry, args)
        if page_image is None:
            continue
        if callable(message_builder):
            message = message_builder(page_index, total_pages, entry, label)
        else:
            message = f'{label}を変換中… ({page_index}/{total_pages} ページ)'
        last_message = message
        _emit_progress(progress_cb, page_index - 1, total_pages, message)
        spooled_pages.add_blob(ensure_valid_xt_page_blob(page_image_to_xt_bytes(page_image, page_args.width, page_args.height, page_args), page_image, page_args.width, page_args.height, page_args))

    if complete_message is None:
        complete_message = f'ページ変換が完了しました。({spooled_pages.page_count} ページ)'
    elif callable(complete_message):
        complete_message = complete_message(spooled_pages.page_count, total_pages, last_message)
    _emit_progress(progress_cb, total_pages, total_pages, complete_message)


def _write_page_entries_to_xtc(page_entries: Sequence[PageEntryLike], source_path: PathLike, args: ConversionArgs, output_path: PathLike | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None,
                               message_builder: Callable[[int, int, PageEntryLike, str], str] | None = None, complete_message: str | Callable[[int, int, str | None], str] | None = None) -> Path:
    ext = '.xtch' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else '.xtc'
    out_path = Path(output_path) if output_path else Path(source_path).with_suffix(ext)
    renderable_pages = sum(1 for entry in page_entries if _resolve_page_entry(entry, args)[0] is not None)
    if renderable_pages == 0:
        raise ValueError('変換データがありません。')

    tmp_handle = tempfile.NamedTemporaryFile(prefix=f'{out_path.stem}_', suffix='.partial', dir=str(out_path.parent), delete=False)
    tmp_path = Path(tmp_handle.name)
    tmp_handle.close()

    try:
        idx_off = 48
        data_off = 48 + renderable_pages * 16
        total_pages = max(1, len(page_entries))
        page_specs: list[tuple[int, int, int]] = []
        last_message = None

        with open(tmp_path, 'w+b') as dst:
            dst.seek(data_off)
            for page_index, entry in enumerate(page_entries, 1):
                _raise_if_cancelled(should_cancel)
                page_image, page_args, label = _resolve_page_entry(entry, args)
                if page_image is None:
                    continue
                if callable(message_builder):
                    message = message_builder(page_index, total_pages, entry, label)
                else:
                    message = f'{label}を変換中… ({page_index}/{total_pages} ページ)'
                last_message = message
                _emit_progress(progress_cb, page_index - 1, total_pages, message)
                blob = page_image_to_xt_bytes(page_image, page_args.width, page_args.height, page_args)
                dst.write(blob)
                page_specs.append((len(blob), page_args.width, page_args.height))

            if complete_message is None:
                complete_text = f'ページ変換が完了しました。({len(page_specs)} ページ)'
            elif callable(complete_message):
                complete_text = complete_message(len(page_specs), total_pages, last_message)
            else:
                complete_text = complete_message
            _emit_progress(progress_cb, total_pages, total_pages, complete_text)

            _raise_if_cancelled(should_cancel)
            _emit_progress(progress_cb, 0, renderable_pages + 1, f'XTC索引を作成中… (0/{renderable_pages} ページ)')
            idx_table = bytearray()
            curr_off = data_off
            for idx, (size, page_w, page_h) in enumerate(page_specs, 1):
                _raise_if_cancelled(should_cancel)
                idx_table += struct.pack('<Q I H H', curr_off, size, page_w, page_h)
                curr_off += size
                _emit_progress(progress_cb, idx, renderable_pages + 1, f'XTC索引を作成中… ({idx}/{renderable_pages} ページ)')

            mark = b'XTCH' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else b'XTC\x00'
            header = struct.pack('<4sHHBBBBIQQQQ', mark, 1, len(page_specs), 1, 0, 0, 0, 0, 0, idx_off, data_off, 0)
            dst.seek(0)
            dst.write(header)
            dst.write(idx_table)
            dst.flush()

        os.replace(tmp_path, out_path)
        _emit_progress(progress_cb, renderable_pages + 1, renderable_pages + 1, f'XTCを書き出しました。({len(page_specs)} ページ)')
        return out_path
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def _render_text_blocks_to_xtc(blocks: Sequence[dict[str, Any]], source_path: PathLike, font_path: PathLike, args: ConversionArgs, output_path: PathLike | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    page_entries = _render_text_blocks_to_page_entries(
        blocks,
        font_path,
        args,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )
    for entry in page_entries:
        entry['label'] = '描画済みページ'

    def _rendered_page_message(page_index: int, total_pages: int, entry: PageEntryLike, label: str) -> str:
        return f'{label}を変換中… ({page_index}/{total_pages} ページ)'

    def _rendered_page_complete_message(page_count: int, total_pages: int, last_message: str | None) -> str:
        return f'描画済みページを変換しました。({page_count} ページ)'

    return _write_page_entries_to_xtc(
        page_entries,
        source_path,
        args,
        output_path=output_path,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
        message_builder=_rendered_page_message,
        complete_message=_rendered_page_complete_message,
    )

def process_text_file(text_path: str | Path, font_path: str | Path, args: ConversionArgs, output_path: str | Path | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    """プレーンテキストを縦書き XTC へ変換する。

    青空文庫記法は一部対応として、ルビ（｜...《...》 / 漢字列《...》）、
    改ページ注記（［＃改ページ］など）、字下げ注記（［＃ここから２字下げ］など）、傍点注記・傍線注記（［＃「語」に傍点］［＃「語」に傍線］など）を解釈し、その他の注記は描画から除外する。
    """
    _raise_if_cancelled(should_cancel)
    document = load_text_input_document(text_path, parser='plain')
    if document.support_summary:
        LOGGER.info('%s 対応範囲: %s', document.format_label, document.support_summary)
    for warning in document.warnings or []:
        LOGGER.warning('%s 入力注意: %s', document.format_label, warning)
    _emit_progress(progress_cb, 0, 1, f'{document.format_label}ファイルを読み込みました。')
    return _render_text_blocks_to_xtc(document.blocks, document.source_path, font_path, args, output_path=output_path, should_cancel=should_cancel, progress_cb=progress_cb)



def process_markdown_file(text_path: str | Path, font_path: str | Path, args: ConversionArgs, output_path: str | Path | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    """Markdown を簡易整形して縦書き XTC へ変換する。

    見出し・箇条書き・番号付きリストに加え、pipe table / 定義リスト / 脚注を簡易展開して描画する。
    本文中では青空文庫のルビ記法・改ページ注記・字下げ注記・傍点注記・傍線注記を一部解釈する。
    コードブロックとインラインコードは、可能なら等幅寄りフォントへ切り替えて描画する。
    """
    _raise_if_cancelled(should_cancel)
    document = load_text_input_document(text_path, parser='markdown')
    if document.support_summary:
        LOGGER.info('%s 対応範囲: %s', document.format_label, document.support_summary)
    for warning in document.warnings or []:
        LOGGER.warning('%s 入力注意: %s', document.format_label, warning)
    _emit_progress(progress_cb, 0, 1, f'{document.format_label}ファイルを読み込みました。')
    return _render_text_blocks_to_xtc(document.blocks, document.source_path, font_path, args, output_path=output_path, should_cancel=should_cancel, progress_cb=progress_cb)


def process_archive(archive_path: str | Path, args: ConversionArgs, output_path: str | Path | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    """Convert an image archive such as ZIP/CBZ/CBR/RAR into XTC or XTCH.

    The archive is extracted into a temporary directory, supported image files are
    filtered and sorted, then each image is converted into a page entry and written to
    the requested XTC-family output. Safety checks such as path-traversal filtering are
    applied during extraction.

    Args:
        archive_path: Archive file to convert.
        args: Conversion arguments controlling target size and output format.
        output_path: Optional explicit output path. When omitted, the output path is
            derived from ``archive_path``.
        should_cancel: Optional cancellation callback queried during long operations.
        progress_cb: Optional callback receiving ``(current, total, message)`` updates.

    Returns:
        Path to the generated output file.
    """
    archive_path = Path(archive_path)
    _raise_if_cancelled(should_cancel)
    LOGGER.info('[アーカイブ変換開始] %s', archive_path.name)
    ext = '.xtch' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else '.xtc'
    out_path = Path(output_path) if output_path else archive_path.with_suffix(ext)

    image_items: list[Path | str] = []
    conversion_fail_count = 0
    traversal_skipped = 0
    first_exc: Exception | None = None
    last_exc: Exception | None = None
    total_images = 0

    with XTCSpooledPages() as spooled_pages:
        direct_zip_infos: list[tuple[PurePosixPath, zipfile.ZipInfo]] | None = None
        if archive_path.suffix.lower() in ('.zip', '.cbz'):
            try:
                direct_zip_infos, traversal_skipped = _safe_zip_archive_image_infos(archive_path, should_cancel=should_cancel)
            except Exception:
                direct_zip_infos = None
                traversal_skipped = 0

        if direct_zip_infos is not None:
            image_items = [pure.as_posix() for pure, _info in direct_zip_infos]
            LOGGER.info('アーカイブ内画像数: %s 枚', len(image_items))
            total_images = len(image_items)
            progress_total = max(1, total_images)
            _emit_progress(progress_cb, 0, progress_total, f'アーカイブ内画像を確認しました。({len(image_items)} 枚)')
            try:
                with zipfile.ZipFile(archive_path) as zf:
                    for img_index, (pure, info) in enumerate(_iter_with_optional_tqdm(direct_zip_infos, desc="通常変換中", unit="枚", leave=False), 1):
                        display_name = pure.name or pure.as_posix()
                        _emit_progress(progress_cb, img_index - 1, max(1, total_images), f'画像を変換中… ({max(0, img_index - 1)}/{total_images} 枚) {display_name}')
                        _raise_if_cancelled(should_cancel)
                        try:
                            with zf.open(info) as member_fp:
                                blob = process_image_data(member_fp, args, should_cancel=should_cancel)
                            if blob:
                                spooled_pages.add_blob(blob)
                                _emit_progress(progress_cb, img_index, max(1, total_images), f'画像を変換中… ({img_index}/{total_images} 枚) {display_name}')
                            else:
                                LOGGER.warning('画像変換結果なし (%s): 変換に失敗した可能性があります', display_name)
                                if first_exc is None:
                                    first_exc = ValueError(f'cannot identify image file: {display_name}')
                                conversion_fail_count += 1
                        except Exception as e:
                            LOGGER.warning('画像スキップ (%s): %s', display_name, e)
                            if first_exc is None:
                                first_exc = e
                            last_exc = e
                            conversion_fail_count += 1
                            continue
            except Exception as e:
                report = build_conversion_error_report(archive_path, e, stage='アーカイブ展開')
                raise RuntimeError(report['display']) from e
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                try:
                    archive_document = _load_archive_input_document_compat(archive_path, tmpdir_path, should_cancel=should_cancel)
                except Exception as e:
                    report = build_conversion_error_report(archive_path, e, stage='アーカイブ展開')
                    raise RuntimeError(report['display']) from e

                image_items = archive_document.image_files
                traversal_skipped = int(getattr(archive_document, 'traversal_skipped', 0) or 0)
                trusted_temp_files = bool(getattr(archive_document, 'trusted_temp_files', False))
                LOGGER.info('アーカイブ内画像数: %s 枚', len(image_items))
                total_images = len(image_items)
                progress_total = max(1, total_images)
                _emit_progress(progress_cb, 0, progress_total, f'アーカイブを展開しました。({len(image_items)} 枚)')

                tmpdir_resolved = tmpdir_path.resolve()
                for img_index, img_p in enumerate(_iter_with_optional_tqdm(image_items, desc="通常変換中", unit="枚", leave=False), 1):
                    assert isinstance(img_p, Path)
                    _emit_progress(progress_cb, img_index - 1, max(1, total_images), f'画像を変換中… ({max(0, img_index - 1)}/{total_images} 枚) {img_p.name}')
                    _raise_if_cancelled(should_cancel)
                    try:
                        resolved_img = img_p if trusted_temp_files else img_p.resolve(strict=False)
                        if not trusted_temp_files:
                            try:
                                resolved_img.relative_to(tmpdir_resolved)
                            except ValueError:
                                LOGGER.warning('パス・トラバーサル検出のためスキップ: %s', img_p)
                                traversal_skipped += 1
                                continue
                        blob = process_image_data(resolved_img, args, should_cancel=should_cancel)
                        if blob:
                            spooled_pages.add_blob(blob)
                            _emit_progress(progress_cb, img_index, max(1, total_images), f'画像を変換中… ({img_index}/{total_images} 枚) {img_p.name}')
                        else:
                            LOGGER.warning('画像変換結果なし (%s): 変換に失敗した可能性があります', img_p.name)
                            if first_exc is None:
                                first_exc = ValueError(f'cannot identify image file: {img_p.name}')
                            conversion_fail_count += 1
                    except Exception as e:
                        LOGGER.warning('画像スキップ (%s): %s', img_p.name, e)
                        if first_exc is None:
                            first_exc = e
                        last_exc = e
                        conversion_fail_count += 1
                        continue

        if spooled_pages.page_count > 0:
            _emit_progress(progress_cb, max(1, total_images), max(1, total_images), f'画像変換が完了しました。({spooled_pages.page_count} ページ)')
            spooled_pages.finalize(out_path, args.width, args.height, getattr(args, 'output_format', 'xtc'), should_cancel=should_cancel, progress_cb=progress_cb)
            LOGGER.info('通常変換完了: %s', out_path.name)
            return out_path

    if total_images == 0 and traversal_skipped > 0:
        raise RuntimeError(
            f'対象: {archive_path.name}\n'
            '内容: 安全のためアーカイブ内画像を処理しませんでした。\n'
            '画像は 0 枚見つかりましたが、安全のため処理を行いませんでした。\n'
            f'安全のためスキップしたパス: {traversal_skipped} 件\n'
            '確認: アーカイブ内のパス構造に問題がないか確認してください。'
        )

    if not image_items:
        raise RuntimeError(
            f'対象: {archive_path.name}\n'
            '内容: 変換できる画像が見つかりませんでした。\n'
            f'詳細: 対応画像は {", ".join(IMG_EXTS)} です。\n'
            '確認: 画像ファイルがサブフォルダ内にある場合も含め、アーカイブ内に画像が入っているか確認してください。'
        )

    if (conversion_fail_count + traversal_skipped) > 0 and total_images > 0:
        rep_exc = first_exc or last_exc
        rep_msg = _compact_error_text(rep_exc) if rep_exc else '詳細不明'
        if conversion_fail_count == 0 and traversal_skipped > 0:
            detail = [
                f'画像は {len(image_items)} 枚見つかりましたが、安全のため処理を行いませんでした。',
                f'安全のためスキップしたパス: {traversal_skipped} 件',
                '確認: アーカイブ内のパス構造に問題がないか確認してください。',
            ]
            raise RuntimeError(
                f'対象: {archive_path.name}\n'
                '内容: 安全のためアーカイブ内画像を処理しませんでした。\n'
                + '\n'.join(detail)
            )
        detail = [
            f'画像は {len(image_items)} 枚見つかりましたが、正常に変換できませんでした。',
            f'変換失敗: {conversion_fail_count} 件',
        ]
        if rep_exc is not None:
            detail.append(f'代表エラー: {rep_msg}')
        if traversal_skipped:
            detail.append(f'安全のためスキップしたパス: {traversal_skipped} 件')
        detail.append(f'確認: 対応画像は {", ".join(IMG_EXTS)} です。破損画像や未対応形式が混在していないか確認してください。')
        raise RuntimeError(
            f'対象: {archive_path.name}\n'
            '内容: アーカイブ内画像の変換に失敗しました。\n'
            + '\n'.join(detail)
        )
    raise RuntimeError(f'対象: {archive_path.name}\n内容: 変換できる画像が見つかりませんでした。')

def _classify_epub_embedded_image(s_img: Image.Image, args: ConversionArgs) -> bool:
    """EPUB 埋め込み画像を本文内画像として扱うか、フルページ挿絵として扱うか判定する。"""
    img_w, img_h = s_img.size
    if img_w <= 0 or img_h <= 0:
        return False

    content_w = max(1, args.width - args.margin_l - args.margin_r)
    content_h = max(1, args.height - args.margin_t - args.margin_b)
    area_ratio = (img_w * img_h) / float(content_w * content_h)
    w_ratio = img_w / float(content_w)
    h_ratio = img_h / float(content_h)

    if area_ratio >= 0.18:
        return True
    if h_ratio >= 0.38:
        return True
    if w_ratio >= 0.55 and h_ratio >= 0.12:
        return True
    if w_ratio >= 0.42 and h_ratio >= 0.24:
        return True
    if area_ratio >= 0.11 and (h_ratio >= 0.20 or w_ratio >= 0.45):
        return True

    if area_ratio <= 0.07 and h_ratio <= 0.22 and w_ratio <= 0.55:
        return False

    return img_h >= max(180, min(260, args.font_size * 6)) and area_ratio >= 0.09


def _make_inline_epub_image(s_img: Image.Image, args: ConversionArgs) -> Image.Image | None:
    """本文中に差し込む画像を 1 マス内へ収まるよう整形する。"""
    img_w, img_h = s_img.size
    if img_w <= 0 or img_h <= 0:
        return None

    cell_w = max(4, args.font_size - 4)
    cell_h = max(4, args.font_size - 2)
    scale = min(cell_w / float(img_w), cell_h / float(img_h))
    new_w = max(1, int(round(img_w * scale)))
    new_h = max(1, int(round(img_h * scale)))
    if s_img.mode != 'L':
        s_img = s_img.convert('L')
    return s_img.resize((new_w, new_h), Image.Resampling.LANCZOS)


@lru_cache(maxsize=256)
def _inspect_epub_embedded_image(img_data: bytes, width: int, height: int, margin_l: int, margin_r: int, margin_t: int, margin_b: int, font_size: int) -> tuple[bool, int, int]:
    """EPUB 埋め込み画像の分類に必要な寸法情報を cache する。"""
    with Image.open(io.BytesIO(img_data)) as s_img:
        img_w, img_h = s_img.size
    if img_w <= 0 or img_h <= 0:
        return False, img_w, img_h

    content_w = max(1, width - margin_l - margin_r)
    content_h = max(1, height - margin_t - margin_b)
    area_ratio = (img_w * img_h) / float(content_w * content_h)
    w_ratio = img_w / float(content_w)
    h_ratio = img_h / float(content_h)

    if area_ratio >= 0.18:
        return True, img_w, img_h
    if h_ratio >= 0.38:
        return True, img_w, img_h
    if w_ratio >= 0.55 and h_ratio >= 0.12:
        return True, img_w, img_h
    if w_ratio >= 0.42 and h_ratio >= 0.24:
        return True, img_w, img_h
    if area_ratio >= 0.11 and (h_ratio >= 0.20 or w_ratio >= 0.45):
        return True, img_w, img_h

    if area_ratio <= 0.07 and h_ratio <= 0.22 and w_ratio <= 0.55:
        return False, img_w, img_h

    return img_h >= max(180, min(260, font_size * 6)) and area_ratio >= 0.09, img_w, img_h


@lru_cache(maxsize=256)
def _prepare_inline_epub_image_bytes(img_data: bytes, font_size: int, night_mode: bool) -> tuple[int, int, bytes] | None:
    """inline EPUB 画像を cacheable な L バイト列へ整形する。"""
    with Image.open(io.BytesIO(img_data)) as s_img:
        temp_args = ConversionArgs(font_size=font_size)
        inline_img = _make_inline_epub_image(s_img, temp_args)
    if inline_img is None:
        return None
    if night_mode:
        inline_img = ImageOps.invert(inline_img)
    return inline_img.width, inline_img.height, inline_img.tobytes()


def _resolve_epub_image_data(doc_file_name: str, raw_src: str, image_map: Mapping[str, bytes], image_basename_map: Mapping[str, Sequence[tuple[str, bytes] | str]]) -> tuple[str | None, bytes | None]:
    """文書相対パスを考慮して EPUB 内画像を解決する。"""
    src_norm = _normalize_epub_href(raw_src)
    if not src_norm:
        return None, None

    candidates: list[str] = []
    doc_norm = _normalize_epub_href(doc_file_name)
    if doc_norm:
        base_dir = posixpath.dirname(doc_norm)
        joined = _normalize_epub_href(posixpath.join(base_dir, src_norm))
        if joined:
            candidates.append(joined)
    candidates.append(src_norm)

    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate in image_map:
            return candidate, image_map[candidate]

    basename = posixpath.basename(src_norm)
    basename_matches = image_basename_map.get(basename, [])
    if len(basename_matches) == 1:
        match = basename_matches[0]
        if isinstance(match, (tuple, list)) and len(match) >= 2:
            return match[0], match[1]
        normalized_match = _normalize_epub_href(match)
        if normalized_match and normalized_match in image_map:
            return normalized_match, image_map[normalized_match]

    return None, None


def _epub_runs(text: str, *, bold: bool = False, italic: bool = False, code: bool = False, ruby: str = '') -> Runs:
    """EPUBテキスト片を共通 run リストへ正規化する。"""
    runs: Runs = []
    _append_text_run(
        runs,
        text,
        ruby=ruby,
        bold=bool(bold),
        italic=bool(italic),
        code=bool(code),
    )
    return runs


_EPUB_TEXT_LEADING_WS_RE = re.compile(r'^[\s\u3000]+')


@lru_cache(maxsize=8192)
def _normalize_epub_text_fragment(text: str, strip_start_text: bool = False, strip_leading_for_indent: bool = False) -> str:
    """EPUB本文のテキスト断片を描画前に正規化する。"""
    normalized = text.replace('\r', '').replace('\n', '').replace('\xa0', ' ')
    if strip_start_text:
        normalized = _strip_leading_start_text(normalized)
    normalized = normalized.rstrip()
    if strip_leading_for_indent:
        normalized = _EPUB_TEXT_LEADING_WS_RE.sub('', normalized)
    return normalized



def _render_epub_chapter_pages_from_html(html_content: str | bytes, doc_file_name: str, args: ConversionArgs, font: Any, ruby_font: Any, bold_rules: Mapping[str, set[str]],
                                         image_map: Mapping[str, bytes], image_basename_map: Mapping[str, Sequence[tuple[str, bytes] | str]], css_rules: Sequence[dict[str, Any]] | None = None, primary_font_value: str = '',
                                         code_font_value: str | None = None, should_cancel: Callable[[], bool] | None = None, page_created_cb: Callable[[PageEntry], None] | None = None, store_page_entries: bool = True,
                                         max_output_pages: int | None = None) -> PageEntries:
    """EPUB 1章分の HTML を描画し、ページエントリ一覧を返す。"""
    BeautifulSoup = _require_bs4_beautifulsoup()
    soup = BeautifulSoup(html_content, 'html.parser')
    body = soup.find('body') or soup
    _strip_leading_start_text_from_epub_body(body)
    resolved_code_font_value = str(code_font_value or '').strip()

    def _load_code_font() -> Any:
        nonlocal resolved_code_font_value
        if not resolved_code_font_value and primary_font_value:
            resolved_code_font_value = get_code_font_value(primary_font_value)
        try:
            return load_truetype_font(resolved_code_font_value or primary_font_value or '', args.font_size)
        except Exception:
            return font

    page_limit = max(1, int(max_output_pages)) if max_output_pages else None
    # sweep353: EPUB chapter rendering must keep completed pages local until all
    # delayed ruby overlays have been applied.  The public page_created_cb is
    # intentionally not wired into the low-level renderer here; callers that want
    # streaming receive finalized chapter_pages from this function and can invoke
    # their callback after the overlay-safe boundary.
    renderer = _VerticalPageRenderer(
        args,
        font,
        ruby_font,
        should_cancel=should_cancel,
        page_created_cb=None,
        store_page_entries=True,
        max_buffered_pages=page_limit,
        default_page_args=args,
        default_page_label='本文ページ',
        code_font_loader=_load_code_font,
    )
    completed_page_entries: PageEntries = []

    def drain_completed_pages() -> None:
        entries = renderer.pop_page_entries()
        if entries:
            # Pages may still receive delayed ruby overlays when a ruby run crosses
            # a page boundary.  Defer the streaming callback from this helper and
            # return the finalized entries instead; process_epub will stream the
            # returned chapter pages after the overlay-safe boundary.
            completed_page_entries.extend(entries)
        if page_limit is not None:
            remaining = page_limit - len(completed_page_entries)
            renderer.set_page_buffer_limit(remaining if remaining > 0 else 1)

    resolved_image_cache: dict[str, tuple[str | None, bytes | None]] = {}

    def normalize_text(text: str, strip_leading_for_indent: bool = False) -> str:
        return _normalize_epub_text_fragment(
            text,
            strip_start_text=not renderer.has_started_document,
            strip_leading_for_indent=strip_leading_for_indent,
        )

    def draw_text_node(text: str, inherited_bold: bool, inherited_code: bool, wrap_indent_chars: int) -> None:
        text = normalize_text(text, strip_leading_for_indent=renderer.has_pending_paragraph_indent)
        if not text:
            return
        renderer.apply_pending_paragraph_indent()
        renderer.draw_runs(
            _epub_runs(text, bold=inherited_bold, code=inherited_code),
            default_font=font,
            wrap_indent_chars=wrap_indent_chars,
        )
        drain_completed_pages()

    def _handle_epub_image_node(node: Any, wrap_indent_chars: int) -> None:
        raw_src = str(node.get('src', node.get('xlink:href', '')) or '')
        cached_resolution = resolved_image_cache.get(raw_src)
        if cached_resolution is None:
            cached_resolution = _resolve_epub_image_data(doc_file_name, raw_src, image_map, image_basename_map)
            resolved_image_cache[raw_src] = cached_resolution
        resolved_src, img_data = cached_resolution
        if not img_data:
            return
        try:
            is_full_page, _img_w, _img_h = _inspect_epub_embedded_image(
                img_data,
                args.width,
                args.height,
                args.margin_l,
                args.margin_r,
                args.margin_t,
                args.margin_b,
                args.font_size,
            )
            if not is_full_page:
                prepared = _prepare_inline_epub_image_bytes(img_data, args.font_size, args.night_mode)
                if prepared is None:
                    return
                img_w, img_h, img_bytes = prepared
                renderer.draw_inline_image(
                    Image.frombytes('L', (img_w, img_h), img_bytes),
                    wrap_indent_chars=wrap_indent_chars,
                )
                drain_completed_pages()
                return
            with Image.open(io.BytesIO(img_data)) as s_img:
                full_page_img = s_img.convert('L')
            renderer.add_full_page_image(
                full_page_img,
                label='挿絵ページ',
                page_args=dc_replace(args, night_mode=False),
                copy_image=False,
            )
            drain_completed_pages()
        except Exception as e:
            LOGGER.warning('画像処理エラー (%s): %s', resolved_src or raw_src, e)

    def _extract_epub_ruby_parts(node: Any) -> tuple[str, str]:
        rb_parts: list[str] = []
        rt_parts: list[str] = []
        for child in getattr(node, 'contents', ()):
            child_name = getattr(child, 'name', '')
            if child_name == 'rt':
                try:
                    rt_parts.append(child.get_text())
                except Exception:
                    rt_parts.append(str(child))
                continue
            if child_name == 'rp':
                continue
            if hasattr(child, 'get_text'):
                rb_parts.append(child.get_text())
            else:
                rb_parts.append(str(child))
        return ''.join(rb_parts), ''.join(rt_parts)

    def _handle_ruby_node(node: Any, node_bold: bool, node_code: bool, wrap_indent_chars: int) -> None:
        rb, rt = _extract_epub_ruby_parts(node)
        rb = normalize_text(rb, strip_leading_for_indent=renderer.has_pending_paragraph_indent)
        if not rb:
            return
        renderer.apply_pending_paragraph_indent()
        renderer.draw_runs(
            _epub_runs(rb, bold=node_bold, code=node_code, ruby=rt),
            default_font=font,
            wrap_indent_chars=wrap_indent_chars,
        )
        drain_completed_pages()

    def handle_inline_node(node: Any, node_name: str, node_bold: bool, node_code: bool, wrap_indent_chars: int, requests_pagebreak: bool = False) -> bool:
        if requests_pagebreak:
            renderer.flush_current_page()
            drain_completed_pages()
            renderer.clear_pending_paragraph_indent()
            if epub_pagebreak_node_is_marker(node):
                return True

        if node_name == 'br':
            renderer.advance_column(1, indent_chars=wrap_indent_chars)
            renderer.set_pending_paragraph_indent(True)
            return True

        if node_name in {'img', 'image'} and (node.get('src') or node.get('xlink:href')):
            _handle_epub_image_node(node, wrap_indent_chars)
            return True

        if node_name == 'ruby':
            _handle_ruby_node(node, node_bold, node_code, wrap_indent_chars)
            return True

        return False

    def walk_xml(node: Any, inherited_bold: bool = False, wrap_indent_chars: int = 0, inherited_code: bool = False) -> None:
        _raise_if_cancelled(should_cancel)

        if isinstance(node, str):
            draw_text_node(node, inherited_bold, inherited_code, wrap_indent_chars)
            return

        if not getattr(node, 'name', None):
            return
        analysis = _epub_node_analysis(node, bold_rules=bold_rules, css_rules=css_rules, font_size=args.font_size)
        if analysis.get('should_skip', False):
            return

        node_name = str(analysis.get('node_name', '') or '')
        node_bold = bool(inherited_bold or analysis.get('intrinsic_bold', False))
        node_code = bool(inherited_code or node_name in {'code', 'pre', 'tt', 'kbd', 'samp'})

        if handle_inline_node(node, node_name, node_bold, node_code, wrap_indent_chars, requests_pagebreak=bool(analysis.get('requests_pagebreak', False))):
            return

        profile = cast(EpubIndentProfile, analysis.get('indent_profile', {
            'indent_chars': 0,
            'wrap_indent_chars': 0,
            'prefix': '',
            'prefix_bold': False,
            'blank_before': 1,
            'heading_level': 0,
        }))
        block_wrap_indent_chars = max(int(wrap_indent_chars or 0), int(profile.get('wrap_indent_chars', 0) or 0))
        block_indent_chars = int(profile.get('indent_chars', 0) or 0)
        block_prefix = profile.get('prefix', '')
        is_block_node = bool(analysis.get('paragraph_like', False))

        if is_block_node:
            if renderer.has_drawn_on_page:
                renderer.advance_column(max(1, int(profile.get('blank_before', 1) or 1)))
            renderer.set_pending_paragraph_indent(block_indent_chars > 0 and not block_prefix)
            if int(profile.get('heading_level', 0) or 0):
                renderer.clear_pending_paragraph_indent()
                node_bold = True

        if block_prefix:
            renderer.apply_pending_paragraph_indent(block_indent_chars)
            renderer.draw_runs(
                _epub_runs(block_prefix, bold=bool(profile.get('prefix_bold')) or node_bold),
                default_font=font,
                wrap_indent_chars=block_wrap_indent_chars,
            )
            drain_completed_pages()

        for child in node.contents:
            _raise_if_cancelled(should_cancel)
            if isinstance(child, str):
                draw_text_node(child, node_bold, node_code, block_wrap_indent_chars)
            else:
                walk_xml(child, node_bold, wrap_indent_chars=block_wrap_indent_chars, inherited_code=node_code)

    try:
        walk_xml(body)
        if renderer.has_drawn_on_page:
            renderer.add_page(renderer.img, copy_image=False)
        drain_completed_pages()
    except _PreviewPageLimitReached:
        drain_completed_pages()
    if page_limit is not None:
        return completed_page_entries[:page_limit]
    return completed_page_entries


def process_epub(epub_path: str | Path, font_path: str | Path, args: ConversionArgs, output_path: str | Path | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    """Convert an EPUB file into a vertical-layout XTC or XTCH document.

    The EPUB is parsed into chapter documents and embedded images, each chapter is
    rendered through the shared vertical page renderer, and the resulting page entries
    are written into the requested output format. Per-page overrides are preserved for
    cases such as full-page illustrations that should not use night mode.

    Args:
        epub_path: EPUB file to convert.
        font_path: Primary font file used for body text and ruby.
        args: Conversion arguments controlling page size and rendering behavior.
        output_path: Optional explicit output path. When omitted, the output path is
            derived from ``epub_path``.
        should_cancel: Optional cancellation callback queried during long operations.
        progress_cb: Optional callback receiving ``(current, total, message)`` updates.

    Returns:
        Path to the generated output file.
    """
    epub_path = Path(epub_path)
    _raise_if_cancelled(should_cancel)
    try:
        document = load_epub_input_document(epub_path)
    except Exception as exc:
        report = build_conversion_error_report(epub_path, exc, stage='EPUB読込')
        raise RuntimeError(report['display']) from exc

    try:
        font = load_truetype_font(font_path, args.font_size)
        ruby_font = load_truetype_font(font_path, args.ruby_size)
    except Exception as exc:
        report = build_conversion_error_report(epub_path, exc, stage='フォント読込')
        raise RuntimeError(report['display']) from exc

    docs = document.docs
    if not docs:
        report = build_conversion_error_report(epub_path, RuntimeError('本文章が見つかりませんでした'), stage='EPUB解析')
        raise RuntimeError(report['display'])

    total_rendered_pages = 0
    total_docs = max(1, len(docs))
    _emit_progress(progress_cb, 0, total_docs, f'EPUBを解析しました。({len(docs)} 章)')
    class _EpubChapterConvertError(RuntimeError):
        """章の本文描画は成功したが、ページ blob 変換で失敗したことを示す。"""
        pass

    with XTCSpooledPages() as spooled_pages:
        for doc_index, item in enumerate(_iter_with_optional_tqdm(docs, desc="描画中", unit="章", leave=False), 1):
            _raise_if_cancelled(should_cancel)
            chapter_name = Path(getattr(item, "file_name", "") or f"chapter_{doc_index}").name
            _emit_progress(progress_cb, doc_index - 1, total_docs, f'章を描画中… ({max(0, doc_index - 1)}/{total_docs} 章) {chapter_name}')

            chapter_page_count = 0

            def _page_created(entry: PageEntry, doc_index: int = doc_index, total_docs: int = total_docs) -> None:
                nonlocal total_rendered_pages, chapter_page_count
                page_image = entry.get('image') if isinstance(entry, dict) else None
                if page_image is None:
                    return
                page_args = cast(ConversionArgs, entry.get('page_args') or args)
                label = str(entry.get('label') or 'ページ')
                try:
                    spooled_pages.add_blob(ensure_valid_xt_page_blob(page_image_to_xt_bytes(page_image, page_args.width, page_args.height, page_args), page_image, page_args.width, page_args.height, page_args))
                except Exception as exc:
                    raise _EpubChapterConvertError(str(exc)) from exc
                chapter_page_count += 1
                total_rendered_pages += 1
                _emit_progress(
                    progress_cb,
                    min(doc_index, total_docs),
                    total_docs,
                    f'章の描画済みページを変換中… ({total_rendered_pages} ページ目 / {doc_index}/{total_docs} 章) {label}'
                )


            try:
                chapter_pages = _render_epub_chapter_pages_from_html(
                    item.get_content(),
                    getattr(item, 'file_name', ''),
                    args,
                    font,
                    ruby_font,
                    document.bold_rules,
                    document.image_map,
                    document.image_basename_map,
                    document.css_rules,
                    primary_font_value=str(font_path),
                    should_cancel=should_cancel,
                    page_created_cb=_page_created,
                    store_page_entries=False,
                )
            except Exception as exc:
                stage = f'章変換: {chapter_name}' if isinstance(exc, _EpubChapterConvertError) else f'章描画: {chapter_name}'
                report = build_conversion_error_report(epub_path, exc, stage=stage)
                raise RuntimeError(report['display']) from exc

            if chapter_pages and chapter_page_count == 0:
                prev_total = total_rendered_pages
                try:
                    def _chapter_progress_message(page_index: int, total_pages: int, entry: PageEntryLike, label: str,
                                                  _doc_index: int = doc_index, _total_docs: int = total_docs) -> str:
                        return f'章の描画済みページを変換中… ({page_index} ページ目 / {total_pages} ページ, {_doc_index}/{_total_docs} 章)'

                    def _chapter_complete_message(page_count: int, total_pages: int, _last: str | None,
                                                  _doc_index: int = doc_index, _total_docs: int = total_docs) -> str:
                        return f'章のページ変換が完了しました。({page_count} 累計ページ, {_doc_index}/{_total_docs} 章)'

                    _append_page_entries_to_spool(
                        chapter_pages,
                        spooled_pages,
                        args,
                        should_cancel=should_cancel,
                        progress_cb=progress_cb,
                        message_builder=_chapter_progress_message,
                        complete_message=_chapter_complete_message,
                    )
                    total_rendered_pages = spooled_pages.page_count
                    chapter_page_count = total_rendered_pages - prev_total
                except Exception as exc:
                    report = build_conversion_error_report(epub_path, exc, stage=f'章変換: {chapter_name}')
                    raise RuntimeError(report['display']) from exc



            if chapter_page_count:
                _emit_progress(progress_cb, min(doc_index, total_docs), total_docs, f'章のページ変換が完了しました。({total_rendered_pages} 累計ページ / {doc_index}/{total_docs} 章)')
            _emit_progress(progress_cb, doc_index, total_docs, f'章の変換を完了しました。({doc_index}/{total_docs} 章)')

        ext = '.xtch' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else '.xtc'
        out_path = Path(output_path) if output_path else epub_path.with_suffix(ext)
        try:
            spooled_pages.finalize(out_path, args.width, args.height, getattr(args, 'output_format', 'xtc'), should_cancel=should_cancel, progress_cb=progress_cb)
        except Exception as exc:
            report = build_conversion_error_report(epub_path, exc, stage='出力書込')
            raise RuntimeError(report['display']) from exc
        return out_path

def main() -> None:
    raise SystemExit("GUI版は tategakiXTC_gui_studio.py を起動してください。")


if __name__ == "__main__":
    main()
