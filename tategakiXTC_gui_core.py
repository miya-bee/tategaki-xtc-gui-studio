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

from tategakiXTC_numpy_helper import get_cached_numpy_module

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
    _ANNOTATION_ONLY_ATTRS = frozenset({'Image', 'ImageDraw', 'FreeTypeFont'})

    def __init__(self, module_name: str) -> None:
        self._module_name = module_name
        self._module: Any | None = None

    def _load(self) -> Any:
        if self._module is None:
            self._module = importlib.import_module(f'PIL.{self._module_name}')
        return self._module

    def __getattr__(self, name: str) -> Any:
        try:
            return getattr(self._load(), name)
        except ModuleNotFoundError:
            if name in self._ANNOTATION_ONLY_ATTRS:
                return Any
            raise


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
    np, _NUMPY_IMPORT_ATTEMPTED = get_cached_numpy_module(np, _NUMPY_IMPORT_ATTEMPTED)
    return np


LOGGER_NAME = 'tategaki_xtc'
LOGGER = logging.getLogger(LOGGER_NAME)
LOGGER.addHandler(logging.NullHandler())


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

# ==========================================
# --- 任意依存 / 変換診断 helper は分割モジュールで re-export ---
# 互換 hygiene: OPTIONAL_DEPENDENCIES の performance 系分類（例: 'impact': 'performance'）は
# tategakiXTC_gui_core_deps.py 側で維持する。
# ==========================================


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


# ==========================================
# --- 変換対象 / 出力パス helper は分割モジュールで re-export ---
# ==========================================


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
CLOSING_BRACKET_CHARS=set(")]}｝〕〉》≫」』﹂﹄】〙〗〟’”｠）］｣＞>")
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
    punctuation_position_mode: str = "standard"
    ichi_position_mode: str = "standard"
    lower_closing_bracket_position_mode: str = "standard"
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
        self.punctuation_position_mode = str(self.punctuation_position_mode or 'standard')
        self.ichi_position_mode = str(self.ichi_position_mode or 'standard')
        self.lower_closing_bracket_position_mode = str(getattr(self, 'lower_closing_bracket_position_mode', 'standard') or 'standard')
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

# ==========================================
# --- 任意依存 / 変換診断 helper ---
# ==========================================

from tategakiXTC_gui_core_deps import (
    OPTIONAL_DEPENDENCIES,
    _compact_error_text,
    build_conversion_error_report,
    _require_patoolib,
    _iter_with_optional_tqdm as _deps_iter_with_optional_tqdm,
    _is_module_available as _deps_is_module_available,
    list_optional_dependency_status,
    get_missing_dependencies_for_suffixes,
)


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
    return _deps_is_module_available(module_name)


class ConflictPlan(TypedDict, total=False):
    """出力ファイル衝突時の解決結果。"""
    desired_path: str
    final_path: str
    strategy: str
    conflict: bool
    renamed: bool
    overwritten: bool




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
# --- テキスト入力 helper ---
# ==========================================

from tategakiXTC_gui_core_text import (
    _TEXT_INPUT_DOCUMENT_CACHE,
    _try_decode_bytes,
    _guess_utf16_without_bom,
    _detect_text_with_charset_normalizer,
    START_TEXT_RE,
    START_TEXT_ONLY_RE,
    _strip_leading_start_text,
    _is_start_text_only_line,
    _is_frontmatter_like_text_line,
    _can_strip_start_text_after_frontmatter,
    _strip_start_text_after_leading_frontmatter,
    AOZORA_NOTE_RE,
    AOZORA_NOTE_ONLY_RE,
    AOZORA_IMPLICIT_RUBY_BASE_RE,
    AOZORA_INDENT_RE,
    AOZORA_INDENT_END_RE,
    AOZORA_BOUTEN_NOTE_RE,
    AOZORA_BOUSEN_NOTE_RE,
    AOZORA_EMPHASIS_KIND_ALIASES,
    AOZORA_EMPHASIS_MARKERS,
    AOZORA_SIDE_LINE_KIND_ALIASES,
    AOZORA_EMPHASIS_SKIP_CHARS,
    AOZORA_SIDE_LINE_SKIP_CHARS,
    _zenkaku_digits_to_int,
    _is_aozora_pagebreak_note,
    _parse_aozora_indent_note,
    _normalize_aozora_emphasis_kind,
    _parse_aozora_emphasis_note,
    _normalize_aozora_side_line_kind,
    _parse_aozora_side_line_note,
    _merge_adjacent_runs,
    _apply_emphasis_to_recent_runs,
    _apply_side_line_to_recent_runs,
    _parse_aozora_note_only_line,
    _apply_note_to_previous_block,
    _flush_text_run_buffer,
    _append_text_run,
    _aozora_inline_to_runs,
    read_text_file_with_fallback,
    _markdown_inline_to_runs,
    _plain_inline_to_runs,
    _normalize_text_line,
    TEXT_INPUT_SUPPORT_SUMMARY,
    _dedupe_preserve_order,
    _find_markdown_support_warnings,
    _find_plain_text_support_warnings,
    _blocks_from_plain_text,
    MARKDOWN_FOOTNOTE_DEF_RE,
    MARKDOWN_DEF_LIST_RE,
    MARKDOWN_ORDERED_LIST_RE,
    MARKDOWN_FENCE_RE,
    _markdown_text_run,
    _set_runs_bold,
    _extract_markdown_footnotes,
    _split_markdown_table_row,
    _is_markdown_table_separator,
    _build_markdown_table_blocks,
    _append_markdown_footnote_blocks,
    _blocks_from_markdown,
    load_text_input_document,
    process_text_file as _text_process_text_file,
    process_markdown_file as _text_process_markdown_file,
)


# ==========================================
# --- CSS / ボールド解析 ---
# ==========================================


# ==========================================
# --- フォント・パス ユーティリティ ---
# ==========================================

from tategakiXTC_gui_core_fonts import (
    FONT_SPEC_INDEX_TOKEN,
    BUNDLED_FONT_DIR_NAMES,
    BUNDLED_FONT_FILE_SUFFIXES,
    _bundled_font_dir_candidates,
    _existing_bundled_font_dirs,
    _preferred_system_font_specs,
    _pick_system_font_spec,
    _legacy_font_fallback_spec,
    _candidate_font_paths,
    parse_font_spec,
    _cached_build_font_spec,
    build_font_spec,
    _font_path_key,
    _font_name_parts,
    _cached_load_truetype_font,
    load_truetype_font,
    describe_font_value,
    _font_entries_for_value,
    get_font_entries_for_value,
    _clear_named_cache,
    clear_font_entry_cache,
    _font_scan_targets,
    get_font_entries,
    get_font_list,
    _cached_resolve_font_path,
    resolve_font_path,
    _cached_require_font_path,
    require_font_path,
    get_code_font_value,
)


# ==========================================
# --- 変換対象 / 出力パス helper ---
# ==========================================

from tategakiXTC_gui_core_paths import (
    OUTPUT_FLAT_SEPARATOR,
    _natural_sort_key,
    _encode_output_name_part,
    _build_flat_output_stem_from_relative,
    _build_fallback_output_stem,
    iter_conversion_targets,
    should_skip_conversion_target,
    _normalize_output_format,
    get_output_path_for_target,
    make_unique_output_path,
    resolve_output_path_with_conflict,
    find_output_conflicts,
)


# ==========================================
# --- 画像フィルタ & XTG/XTC 変換 ---
# ==========================================

from tategakiXTC_gui_core_xtc import (
    XTCSpooledPages,
    _apply_xtc_filter_prepared,
    _apply_xtch_filter_prepared,
    _atomic_replace_xt_container,
    _clamp_u8,
    _compute_xtch_thresholds,
    _copy_fileobj_with_cancel,
    _dither_xtch_grayscale,
    _invert_grayscale_image,
    _invert_u8_lut,
    _looks_like_expected_xt_page_blob,
    _prepare_canvas_image,
    _prepared_canvas_to_xtg_bytes,
    _prepared_canvas_to_xth_bytes,
    _quantize_xtch_value,
    _verify_xt_container_file,
    _verify_xt_page_blob_header,
    _xtc_threshold_lut,
    _xtch_plane_value_lut,
    _xtch_quantization_lut,
    apply_xtc_filter,
    apply_xtch_filter,
    build_xtc,
    canvas_image_to_xt_bytes,
    ensure_valid_xt_page_blob,
    page_image_to_xt_bytes,
    png_to_xtg_bytes,
    png_to_xth_bytes,
)


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




from tategakiXTC_gui_core_cache import (
    INPUT_DOCUMENT_CACHE_MAX,
    _source_document_cache_key,
    _get_cached_input_document,
    _store_cached_input_document,
)


_EPUB_INPUT_DOCUMENT_CACHE: OrderedDict[tuple[str, int, int], EpubInputDocument] = OrderedDict()


def clear_input_document_cache() -> None:
    """Clear cached parsed text / EPUB input documents."""
    _TEXT_INPUT_DOCUMENT_CACHE.clear()
    _EPUB_INPUT_DOCUMENT_CACHE.clear()
    _cached_safe_zip_archive_image_listing.cache_clear()







# ==========================================
# --- アーカイブ入力 helper ---
# ==========================================

from tategakiXTC_gui_core_archive import (
    _cached_safe_zip_archive_image_listing,
    _safe_zip_archive_image_listing,
    _ARCHIVE_INVALID_COMPONENT_CHARS,
    _ARCHIVE_WINDOWS_RESERVED_NAMES,
    _sanitize_extracted_archive_member_component,
    _normalize_extracted_archive_member_key,
    _safe_zip_archive_image_infos,
    _unique_extracted_member_path,
    _extract_zip_archive_images_to_tempdir,
    _extract_archive_to_tempdir,
    _collect_archive_image_files,
    _list_zip_archive_image_members,
    _load_archive_input_document_compat,
    load_archive_input_document,
    process_archive as _archive_process_archive,
)


# ==========================================
# --- PageEntry / XTC 書き出し pipeline helper ---
# ==========================================

from tategakiXTC_gui_core_pages import (
    _make_page_entry,
    _resolve_page_entry,
    _append_page_entries_to_spool,
    _write_page_entries_to_xtc,
    _render_text_blocks_to_xtc,
)

def process_text_file(
    text_path: str | Path,
    font_path: str | Path,
    args: ConversionArgs,
    output_path: str | Path | None = None,
    should_cancel: Callable[[], bool] | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Path:
    """Convert a plain text file into vertical-writing XTC / XTCH output.

    The implementation body lives in ``tategakiXTC_gui_core_text.py``.
    This wrapper keeps the historical core API and monkey-patch surface intact.

    Args:
        text_path: Plain text source file to convert.
        font_path: Font file or font specification used for text rendering.
        args: Conversion arguments controlling page size, text layout, and output format.
        output_path: Optional explicit output path. When omitted, the output path is
            derived from ``text_path``.
        should_cancel: Optional cancellation callback queried during long operations.
        progress_cb: Optional callback receiving ``(current, total, message)`` updates.

    Returns:
        Path to the generated output file.
    """
    return _text_process_text_file(
        text_path,
        font_path,
        args,
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
    """Convert a Markdown file into vertical-writing XTC / XTCH output.

    The implementation body lives in ``tategakiXTC_gui_core_text.py``.
    This wrapper keeps the historical core API and monkey-patch surface intact.

    Args:
        text_path: Markdown source file to convert.
        font_path: Font file or font specification used for text rendering.
        args: Conversion arguments controlling page size, text layout, and output format.
        output_path: Optional explicit output path. When omitted, the output path is
            derived from ``text_path``.
        should_cancel: Optional cancellation callback queried during long operations.
        progress_cb: Optional callback receiving ``(current, total, message)`` updates.

    Returns:
        Path to the generated output file.
    """
    return _text_process_markdown_file(
        text_path,
        font_path,
        args,
        output_path=output_path,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )


def process_archive(archive_path: str | Path, args: ConversionArgs, output_path: str | Path | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    """Convert an image archive such as ZIP/CBZ/CBR/RAR into XTC or XTCH.

    The implementation body lives in ``tategakiXTC_gui_core_archive.py``.
    This wrapper keeps the historical core API and monkey-patch surface intact.

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
    return _archive_process_archive(
        archive_path,
        args,
        output_path=output_path,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )


# ==========================================
# --- 分割モジュール互換 re-export ---
# ==========================================
from tategakiXTC_gui_core_renderer import (
    _scaled_kutoten_offset,
    _glyph_position_mode,
    _draw_glyph_position_mode,
    _apply_draw_glyph_position_modes,
    _scaled_kutoten_offset_for_mode,
    _punctuation_extra_y_for_mode,
    _ichi_extra_y_for_mode,
    _lower_closing_bracket_extra_y_for_mode,
    _small_kana_offset,
    _kagikakko_extra_y,
    _should_draw_emphasis_for_cell_cached,
    _should_draw_side_line_for_cell_cached,
    _get_side_line_pattern,
    _get_side_line_style,
    _clamp_int,
    _side_line_horizontal_extent,
    _classify_tate_draw_char,
    create_image_draw,
    _get_draw_target_image,
    _paste_glyph_image,
    _get_font_object_cache,
    _get_or_create_font_object_cache,
    _cached_resolve_cacheable_font_spec,
    _resolve_cacheable_font_spec,
    _cached_render_text_glyph_bundle,
    _glyph_render_cache_key,
    _render_text_glyph_and_mask_shared,
    _render_text_glyph_and_mask,
    draw_weighted_text,
    _glyph_canvas_layout,
    _trim_glyph_image_to_ink,
    _italic_extra_width,
    _italic_transform_layout,
    _build_text_glyph_image,
    _cached_render_text_glyph_image,
    _render_text_glyph_image_shared,
    _render_text_glyph_image,
    _VERTICAL_GLYPH_FALLBACK_SENTINELS,
    _glyph_image_signature,
    _cached_glyph_signature,
    _missing_glyph_signatures,
    _missing_glyph_signatures_for_font,
    _cached_font_has_distinct_glyph,
    _font_has_distinct_glyph,
    _should_rotate_to_horizontal_from_glyph_image,
    _cached_horizontal_rotation_decision,
    _should_rotate_to_horizontal,
    _should_rotate_horizontal_bracket,
    _is_render_spacing_char,
    _cached_resolve_vertical_glyph_char,
    _resolve_vertical_glyph_char,
    _cached_tate_punctuation_draw,
    _resolve_tate_punctuation_draw,
    _cached_horizontal_bracket_draw,
    _resolve_horizontal_bracket_draw,
    _cached_default_tate_draw,
    _resolve_default_tate_draw,
    _cached_tate_draw_spec,
    _compute_uncached_tate_draw_spec,
    _compute_tate_draw_spec,
    _compute_reference_glyph_center,
    _cached_reference_glyph_center,
    _get_reference_glyph_center,
    _make_font_variant,
    _centered_glyph_direct_offsets,
    _centered_glyph_image_offsets,
    draw_centered_glyph,
    _ink_centered_glyph_image_offsets,
    _ink_flow_centered_glyph_image_offsets,
    _get_ichi_visual_target_center_y,
    draw_ink_centered_glyph,
    _is_tatechuyoko_token,
    _tatechuyoko_layout_limits,
    _cached_text_bbox,
    _cached_text_bbox_dims,
    _normalize_text_bbox_result,
    _call_font_getbbox,
    _get_text_bbox,
    _get_text_bbox_dims,
    _cached_tatechuyoko_candidate_dims,
    _estimate_tatechuyoko_candidate_dims,
    _finalize_tatechuyoko_fit_size,
    _cached_tatechuyoko_fit_size,
    _resolve_tatechuyoko_fit_size,
    _cached_tatechuyoko_bundle,
    _build_tatechuyoko_bundle,
    _tatechuyoko_paste_offsets,
    draw_tatechuyoko,
    _should_center_ascii_glyph,
    _tokenize_vertical_text_impl,
    _tokenize_vertical_text_cached,
    _tokenize_vertical_text,
    _is_line_head_forbidden,
    _is_line_end_forbidden,
    _is_hanging_punctuation,
    _is_continuous_punctuation_pair,
    _continuous_punctuation_run_length,
    _closing_punctuation_group_length,
    _minimum_safe_group_length,
    _protected_token_group_length,
    _build_single_token_vertical_layout_hints,
    _build_two_token_vertical_layout_hints,
    _build_three_token_vertical_layout_hints,
    _build_four_token_vertical_layout_hints,
    _build_vertical_layout_hints_cached,
    _build_vertical_layout_hints,
    _choose_vertical_layout_action_with_hints,
    _normalize_kinsoku_mode,
    _effective_vertical_layout_bottom_margin,
    _remaining_vertical_slots,
    _remaining_vertical_slots_for_current_column,
    _would_start_forbidden_after_hang_pair,
    _choose_vertical_layout_action,
    _double_punctuation_layout,
    _double_punctuation_draw_offsets,
    _hanging_bottom_layout,
    _hanging_bottom_draw_offsets,
    _limit_draw_y_delta_to_page,
    _draw_hanging_text_near_bottom,
    _is_lowerable_hanging_closing_bracket,
    draw_hanging_closing_bracket,
    _tate_punctuation_layout_insets,
    _tate_hanging_punctuation_raise,
    _tate_hanging_punctuation_visual_targets,
    _tate_hanging_punctuation_min_top_offset,
    _tate_hanging_punctuation_offset_y,
    _tate_punctuation_direct_offsets,
    _tate_punctuation_image_offsets,
    _draw_tate_punctuation_glyph,
    _vertical_dot_leader_count,
    draw_vertical_dot_leader,
    draw_hanging_punctuation,
    draw_char_tate,
    _build_default_preview_blocks,
    _resolve_preview_source_paths,
    _resolve_preview_source_path,
    _select_preview_blocks,
    _preview_fit_image,
    _preview_source_requires_font,
    _preview_target_requires_font,
    _PreviewPageLimitReached,
    _render_preview_pages_from_target,
    _render_preview_page_from_target,
    _apply_preview_postprocess,
    _encode_preview_png_base64,
    _mapping_get_int,
    _mapping_get_bool,
    _preview_path_signature,
    _preview_bundle_cache_key,
    clear_preview_bundle_cache,
    _iter_preview_bundle_pages,
    _normalize_preview_bundle_pages,
    _get_cached_preview_bundle,
    _store_cached_preview_bundle,
    generate_preview_bundle,
    generate_preview_base64,
    _has_renderable_text_blocks,
    _split_ruby_text_segments_cached,
    _split_ruby_text_segments,
    _append_ruby_overlay_group,
    _build_ruby_overlay_groups,
    _append_overlay_cell,
    _effective_ruby_overlay_bottom_margin,
    _ruby_group_capacity_for_args,
    _clamp_margin_value,
    _hanging_punctuation_bottom_clip_allowance,
    _bottom_margin_clip_start_for_text_page,
    _apply_text_page_margin_clip,
    _page_label_allows_text_margin_clip,
    _apply_page_entry_margin_clip,
    _VerticalPageRenderer,
    _render_text_blocks_to_page_entries,
    _render_text_blocks_to_images,
    _PREVIEW_BUNDLE_CACHE,
)


# ==========================================
# --- 分割モジュール互換 re-export ---
# ==========================================
from tategakiXTC_gui_core_epub import (
    _require_ebooklib_epub,
    _require_bs4_beautifulsoup,
    _epub_node_is_effectively_empty,
    _prune_empty_epub_ancestors,
    _strip_leading_start_text_from_epub_body,
    EpubInputDocument,
    EpubImageMap,
    EpubImageBasenameMap,
    BoldRuleSets,
    CSSRule,
    EpubIndentProfile,
    style_declares_bold,
    extract_bold_rules,
    node_is_bold,
    is_paragraph_like,
    _epub_node_token_signature,
    _epub_node_attr_tokens,
    _epub_node_analysis_signature,
    _epub_node_analysis,
    epub_should_skip_node,
    epub_heading_level,
    _parse_css_style_declarations_cached,
    _parse_css_style_declarations,
    _split_css_selectors,
    _normalize_epub_css_selector,
    _parse_epub_css_selector_matcher,
    _epub_css_selector_matches_node,
    extract_epub_css_rules,
    _epub_css_node_cache_signature,
    _merged_epub_css_for_node,
    _font_weight_value_is_bold,
    _css_length_to_chars,
    epub_node_requests_pagebreak,
    epub_pagebreak_node_is_marker,
    epub_node_is_note_like,
    _epub_list_parent_meta,
    _epub_cached_list_prefix_map,
    _epub_list_item_prefix,
    epub_node_indent_profile,
    _normalize_epub_href,
    _build_epub_image_maps,
    _collect_epub_spine_documents,
    load_epub_input_document,
    _classify_epub_embedded_image,
    _make_inline_epub_image,
    _inspect_epub_embedded_image,
    _prepare_inline_epub_image_bytes,
    _resolve_epub_image_data,
    _epub_runs,
    _normalize_epub_text_fragment,
    _render_epub_chapter_pages_from_html,
    process_epub,
)

def main() -> None:
    raise SystemExit("GUI版は tategakiXTC_gui_studio.py を起動してください。")


if __name__ == "__main__":
    main()
