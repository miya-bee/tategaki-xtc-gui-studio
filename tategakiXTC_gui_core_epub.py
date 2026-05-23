"""
tategakiXTC_gui_core_epub.py — EPUB 解析 / EPUB 章描画

`tategakiXTC_gui_core.py` から分離した EPUB 専用実装。renderer への一方向依存を保ち、
gui_core 側の互換 re-export / 既存テストの monkey patch も反映する。
"""
from __future__ import annotations

from typing import Any

import xml.etree.ElementTree as ET
import zipfile

import tategakiXTC_gui_core as _core
import tategakiXTC_gui_core_renderer as _renderer


def _refresh_split_globals() -> None:
    """renderer と gui_core の最新シンボルを EPUB 実装へ反映する。"""
    for _source in (_renderer, _core):
        for _name, _value in vars(_source).items():
            if _name.startswith('__') or _name in {'_core', '_renderer', '_refresh_split_globals'}:
                continue
            globals()[_name] = _value


_refresh_split_globals()


# --- moved from tategakiXTC_gui_core.py lines 258-267 ---
def _require_ebooklib_epub() -> Any:
    """ebooklib.epub を必要時に読み込む。"""
    try:
        from ebooklib import epub as epub_module
    except ImportError as e:
        raise RuntimeError(
            "EPUB変換には ebooklib が必要です。`pip install ebooklib` を実行してください。"
        ) from e
    return epub_module



# --- moved from tategakiXTC_gui_core.py lines 282-292 ---
def _require_bs4_beautifulsoup() -> Any:
    """bs4.BeautifulSoup を必要時に読み込む。"""
    try:
        from bs4 import BeautifulSoup as bs4_BeautifulSoup
    except ImportError as e:
        raise RuntimeError(
            "EPUB変換には beautifulsoup4 が必要です。`pip install beautifulsoup4` を実行してください。"
        ) from e
    return bs4_BeautifulSoup




# --- moved from tategakiXTC_gui_core.py lines 642-748 ---
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



# --- moved from tategakiXTC_gui_core.py lines 1156-1166 ---
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



# --- moved from tategakiXTC_gui_core.py lines 1222-1223 ---
EpubImageMap: TypeAlias = dict[str, bytes]
EpubImageBasenameMap: TypeAlias = dict[str, list[tuple[str, bytes] | str]]


# --- moved from tategakiXTC_gui_core.py lines 1282-1302 ---
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


# --- moved from tategakiXTC_gui_core.py lines 3744-4358 ---
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
    _refresh_split_globals()
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
EPUB_NAVIGATION_TOKENS = {
    'toc', 'doc-toc', 'landmarks', 'guide', 'page-list', 'pagelist',
    'page_list', 'loi', 'lot', 'loa', 'lov', 'index', 'navigation',
}
EPUB_NOTE_BODY_TOKENS = {
    'footnote', 'footnotes', 'doc-footnote', 'doc-footnotes',
    'endnote', 'endnotes', 'doc-endnote', 'doc-endnotes',
    'rearnote', 'rearnotes', 'doc-rearnote', 'doc-rearnotes',
    'annotation', 'annotations',
}
EPUB_NOTE_REFERENCE_TOKENS = {'noteref', 'doc-noteref'}
EPUB_BACK_REFERENCE_TOKENS = {
    'backref', 'backlink', 'back-link', 'doc-backlink', 'doc-backref',
}
EPUB_AUXILIARY_DOC_NAME_RE = re.compile(
    r'(?:^|[-_])(nav|toc|contents?|landmarks?|pagelist|page-list|footnotes?|endnotes?|notes?)(?:[-_]|$)',
    re.IGNORECASE,
)
EPUB_NOTE_REFERENCE_MARKER_RE = re.compile(
    r'^(?:[\[\]\(\)（）【】〔〕「」『』〈〉《》　\s]*'
    r'(?:\d+|[０-９]+|[一二三四五六七八九十百千]+|[ivxlcdm]+|[＊*†‡※]+)'
    r'[\[\]\(\)（）【】〔〕「」『』〈〉《》　\s]*|(?:注|脚注|note)\s*[\d０-９]+)$',
    re.IGNORECASE,
)
EPUB_BACK_REFERENCE_TEXT_RE = re.compile(r'^(?:戻る|本文へ戻る|本文に戻る|戻り|back|return|↩|↵|↑|△|▲)$', re.IGNORECASE)


def _epub_auxiliary_doc_stem_kind(stem: object) -> str:
    """Classify XHTML file-name stems that are likely auxiliary reading-order pages.

    EPUBs in the wild sometimes put ``nav.xhtml`` / ``toc.xhtml`` /
    ``footnotes.xhtml`` in the spine without ``linear="no"`` and without rich
    EPUB3 attributes.  File-name based skipping is intentionally limited to
    well-known auxiliary stems so ordinary chapters are not removed by accident.
    """
    normalized = str(stem or '').strip().replace('_', '-').lower()
    if normalized in {'nav', 'toc', 'contents', 'content', 'landmark', 'landmarks', 'pagelist', 'page-list'}:
        return 'navigation'
    if normalized in {'footnote', 'footnotes', 'endnote', 'endnotes', 'rearnote', 'rearnotes'}:
        return 'notes'
    if normalized in {'note', 'notes'}:
        return 'maybe-notes'
    return ''


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



def _epub_token_matches(tokens: Sequence[str], candidates: set[str]) -> bool:
    normalized_candidates = {token.replace('_', '-').lower() for token in candidates}
    for token in tokens:
        norm = str(token or '').replace('_', '-').lower()
        if norm in normalized_candidates:
            return True
        if any(norm.endswith('-' + candidate) for candidate in normalized_candidates):
            return True
    return False


def _epub_node_href(node: Any) -> str:
    if not getattr(node, 'get', None):
        return ''
    for attr_name in ('href', 'xlink:href'):
        try:
            value = node.get(attr_name, '')
        except Exception:
            value = ''
        if value:
            return str(value or '').strip()
    return ''


def _epub_node_text(node: Any) -> str:
    try:
        return str(node.get_text('', strip=True))
    except Exception:
        return ''


def _epub_href_fragment(href: object) -> str:
    text = str(href or '').strip()
    if not text or '#' not in text:
        return ''
    return text.rsplit('#', 1)[-1].strip().lower()


def _epub_text_is_note_reference_marker(text: object) -> bool:
    stripped = re.sub(r'\s+', '', str(text or '').strip())
    if not stripped or len(stripped) > 12:
        return False
    return bool(EPUB_NOTE_REFERENCE_MARKER_RE.fullmatch(stripped))


def _epub_is_navigation_node(node_name: str, attr_tokens: Sequence[str]) -> bool:
    if node_name == 'nav':
        return _epub_token_matches(attr_tokens, EPUB_NAVIGATION_TOKENS)
    return _epub_token_matches(attr_tokens, {'doc-toc', 'doc-pagelist', 'doc-page-list', 'navigation'})


def _epub_is_note_body_node(node_name: str, attr_tokens: Sequence[str]) -> bool:
    if node_name in {'aside', 'section', 'div', 'li', 'p'} and _epub_token_matches(attr_tokens, EPUB_NOTE_BODY_TOKENS):
        return True
    return _epub_token_matches(attr_tokens, EPUB_NOTE_BODY_TOKENS)


def _epub_is_note_reference_link(node_name: str, attr_tokens: Sequence[str], href: str, text: str) -> bool:
    if node_name != 'a':
        return False
    if _epub_token_matches(attr_tokens, EPUB_NOTE_REFERENCE_TOKENS):
        # Explicit noteref/doc-noteref semantics are more reliable than link text.
        # Some publishers use labels such as "脚注へ" instead of [1].
        return True
    fragment = _epub_href_fragment(href)
    if not fragment:
        return False
    if not re.search(r'(?:^|[-_])(fn|footnote|endnote|note)[-_]?[0-9０-９一二三四五六七八九十]*$', fragment, re.IGNORECASE):
        return False
    return _epub_text_is_note_reference_marker(text)


def _epub_is_back_reference_link(node_name: str, attr_tokens: Sequence[str], href: str, text: str) -> bool:
    if node_name != 'a':
        return False
    if _epub_token_matches(attr_tokens, EPUB_BACK_REFERENCE_TOKENS):
        return True
    if EPUB_BACK_REFERENCE_TEXT_RE.fullmatch(str(text or '').strip()):
        fragment = _epub_href_fragment(href)
        return bool(fragment and re.search(r'(?:^|[-_])(ref|noteref|src|back)[-_]?', fragment, re.IGNORECASE))
    return False


def _epub_should_skip_auxiliary_node(node_name: str, attr_tokens: Sequence[str], href: str = '', text: str = '') -> bool:
    if _epub_is_navigation_node(node_name, attr_tokens):
        return True
    if _epub_is_note_body_node(node_name, attr_tokens):
        return True
    if _epub_is_note_reference_link(node_name, attr_tokens, href, text):
        return True
    if _epub_is_back_reference_link(node_name, attr_tokens, href, text):
        return True
    return False


def _epub_spine_document_is_auxiliary(item: Any) -> bool:
    """Return True for navigation/footnote-only XHTML documents in the spine.

    Some EPUBs put nav.xhtml/toc.xhtml or standalone footnote documents in the
    spine without ``linear="no"``. Skipping these prevents TOC/backref text from
    becoming body pages while keeping normal chapter XHTML files untouched.
    """
    file_name = _normalize_epub_href(getattr(item, 'file_name', ''))
    basename = posixpath.basename(file_name).lower()
    stem = basename.rsplit('.', 1)[0]
    stem_kind = _epub_auxiliary_doc_stem_kind(stem)
    if not stem_kind and not EPUB_AUXILIARY_DOC_NAME_RE.search(stem):
        return False
    if stem_kind in {'navigation', 'notes'}:
        return True
    try:
        content = item.get_content()
    except Exception:
        return False
    if isinstance(content, bytes):
        text = content.decode('utf-8', errors='ignore').lower()
    else:
        text = str(content or '').lower()
    if any(marker in text for marker in (
        'epub:type="toc', "epub:type='toc", 'role="doc-toc', "role='doc-toc",
        'epub:type="landmarks', "epub:type='landmarks", 'page-list',
        'epub:type="footnote', "epub:type='footnote", 'epub:type="endnote', "epub:type='endnote",
        'doc-footnote', 'doc-endnote', 'noteref', 'backref', 'backlink',
    )):
        return True
    return False


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
    href_text = ''
    text_preview = ''
    if getattr(node, 'get', None):
        try:
            style_text = str(node.get('style', '') or '')
        except Exception:
            style_text = ''
        href_text = _epub_node_href(node)
    try:
        text_preview = _epub_node_text(node)[:32]
    except Exception:
        text_preview = ''
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
        href_text,
        text_preview,
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
    elif _epub_should_skip_auxiliary_node(node_name, attr_tokens, _epub_node_href(node), _epub_node_text(node)):
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


def _sanitize_epub_css_selector(selector: object) -> str:
    """Return a conservative selector string supported by the lightweight EPUB CSS matcher.

    Pseudo selectors and attribute selectors are intentionally stripped because this
    renderer only needs a safe subset of CSS.  Unlike the legacy normalizer, this
    helper preserves descendant/child relationships so rules such as ``.note p`` do
    not accidentally apply to every ``p`` in the document.
    """
    selector_text = str(selector or '').strip()
    if not selector_text:
        return ''
    selector_text = re.sub(r'/\*.*?\*/', '', selector_text)
    selector_text = re.sub(r'::?[A-Za-z0-9_-]+(?:\([^)]*\))?', '', selector_text)
    selector_text = re.sub(r'\[[^\]]+\]', '', selector_text)
    selector_text = re.sub(r'\s*([>+~])\s*', r' \1 ', selector_text)
    selector_text = re.sub(r'\s+', ' ', selector_text).strip()
    return selector_text


def _normalize_epub_css_selector(selector: object) -> str:
    selector_text = _sanitize_epub_css_selector(selector)
    if not selector_text:
        return ''
    parts = [part for part in re.split(r'\s*[>+~]\s*|\s+', selector_text) if part]
    return parts[-1].strip() if parts else ''


@lru_cache(maxsize=2048)
def _parse_epub_css_simple_selector_matcher(selector: str) -> tuple[str, tuple[str, ...], tuple[str, ...], bool]:
    normalized = str(selector or '').strip()
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
    if '[' in rest or ']' in rest or any(ch in rest for ch in ('>', '+', '~', ' ')):
        return tag, (), (), False
    ids = tuple(re.findall(r'#([A-Za-z0-9_-]+)', rest))
    classes = tuple(re.findall(r'\.([A-Za-z0-9_-]+)', rest))
    cleaned = re.sub(r'[#.][A-Za-z0-9_-]+', '', rest)
    return tag, ids, classes, not cleaned.strip()


@lru_cache(maxsize=2048)
def _parse_epub_css_selector_matcher(selector: str) -> tuple[str, tuple[str, ...], tuple[str, ...], bool]:
    return _parse_epub_css_simple_selector_matcher(_normalize_epub_css_selector(selector))


def _epub_css_simple_selector_matches_node(node: Any, selector: object) -> bool:
    tag, ids, classes, supported = _parse_epub_css_simple_selector_matcher(str(selector or ''))
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


def _epub_css_selector_matches_node(node: Any, selector: object) -> bool:
    selector_text = _sanitize_epub_css_selector(selector)
    if not selector_text or not getattr(node, 'name', None):
        return False
    if '+' in selector_text or '~' in selector_text:
        # Adjacent/general sibling combinators are not supported.  Returning False
        # is safer than applying the rightmost selector too broadly.
        return False

    tokens = [token for token in selector_text.replace('>', ' > ').split() if token]
    if not tokens:
        return False
    current = node
    idx = len(tokens) - 1
    if not _epub_css_simple_selector_matches_node(current, tokens[idx]):
        return False
    idx -= 1

    while idx >= 0:
        if tokens[idx] == '>':
            idx -= 1
            if idx < 0:
                return False
            parent = getattr(current, 'parent', None)
            if parent is None or not _epub_css_simple_selector_matches_node(parent, tokens[idx]):
                return False
            current = parent
            idx -= 1
            continue

        ancestor_selector = tokens[idx]
        ancestor = getattr(current, 'parent', None)
        found = None
        while ancestor is not None:
            if _epub_css_simple_selector_matches_node(ancestor, ancestor_selector):
                found = ancestor
                break
            ancestor = getattr(ancestor, 'parent', None)
        if found is None:
            return False
        current = found
        idx -= 1

    return True


def extract_epub_css_rules(book: Any) -> list[CSSRule]:
    _refresh_split_globals()
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
                normalized = _sanitize_epub_css_selector(selector)
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
    _refresh_split_globals()
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
    _refresh_split_globals()
    return bool(_epub_node_analysis(node, css_rules=css_rules).get('requests_pagebreak', False))


def epub_pagebreak_node_is_marker(node: Any) -> bool:
    _refresh_split_globals()
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
    _refresh_split_globals()
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
    _refresh_split_globals()
    return cast(EpubIndentProfile, dict(_epub_node_analysis(node, css_rules=css_rules, font_size=font_size).get('indent_profile', {
        'indent_chars': 0,
        'wrap_indent_chars': 0,
        'prefix': '',
        'prefix_bold': False,
        'blank_before': 1,
        'heading_level': 0,
    })))



# --- moved from tategakiXTC_gui_core.py lines 6993-7065 ---
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


_EPUB_DATA_IMAGE_RE = re.compile(r'^data:image/[^;,]+(?:;charset=[^;,]+)?;base64,(.+)$', re.IGNORECASE | re.DOTALL)
_EPUB_CSS_URL_RE = re.compile(r'url\(\s*[\"\']?([^\)\"\']+)[\"\']?\s*\)', re.IGNORECASE)


def _decode_epub_data_image_uri(value: object) -> bytes | None:
    """Decode a base64 data:image URI embedded directly in EPUB HTML.

    Small publisher tools sometimes inline icons or cover fragments as
    ``data:image/...;base64,...``.  Treat invalid data as an unresolved image
    rather than failing the whole EPUB conversion.
    """
    text = str(value or '').strip()
    match = _EPUB_DATA_IMAGE_RE.match(text)
    if not match:
        return None
    try:
        return base64.b64decode(match.group(1), validate=False)
    except Exception:
        return None


def _extract_epub_css_url(value: object) -> str:
    """Return the first URL from a CSS url(...) value."""
    match = _EPUB_CSS_URL_RE.search(str(value or ''))
    return match.group(1).strip() if match else ''


def _first_epub_srcset_candidate(value: object) -> str:
    """Return the first URL candidate from a srcset-like attribute."""
    text = str(value or '').strip()
    if not text:
        return ''
    first = text.split(',', 1)[0].strip()
    return first.split()[0].strip() if first else ''


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



def _epub_spine_entry_id(item_id: Any) -> Any:
    if isinstance(item_id, (tuple, list)) and item_id:
        return item_id[0]
    return item_id


def _epub_spine_entry_is_linear(item_id: Any) -> bool:
    """Return False for EPUB spine entries explicitly marked ``linear="no"``.

    ebooklib commonly exposes spine entries as ``(idref, linear)`` tuples, but
    some fixtures/tools use dictionaries for the second field.  Treat unknown or
    missing values as linear to preserve legacy behavior while skipping explicit
    non-reading-order documents such as auxiliary TOC/cover/ad pages.
    """
    if not isinstance(item_id, (tuple, list)) or len(item_id) < 2:
        return True
    linear_value = item_id[1]
    if isinstance(linear_value, Mapping):
        linear_value = linear_value.get('linear', linear_value.get('linear-value', ''))
    text = str(linear_value or '').strip().lower()
    return text not in {'no', 'false', '0'}


def _collect_epub_spine_documents(book: Any) -> list[Any]:
    docs: list[Any] = []
    for item_id in book.spine:
        if not _epub_spine_entry_is_linear(item_id):
            continue
        item_key = _epub_spine_entry_id(item_id)
        it = book.get_item_with_id(item_key)
        if not it:
            continue
        media_type = (getattr(it, 'media_type', '') or '').lower()
        file_name = (getattr(it, 'file_name', '') or '').lower()
        if (
            media_type in ('application/xhtml+xml', 'text/html')
            or file_name.endswith(('.xhtml', '.html', '.htm'))
        ):
            if _epub_spine_document_is_auxiliary(it):
                continue
            docs.append(it)
    return docs



def load_epub_input_document(epub_path: PathLike) -> EpubInputDocument:
    """EPUB を読み込み、本文文書群と画像対応表へ正規化する。"""
    _refresh_split_globals()
    source_path = Path(epub_path)
    cache_key = _source_document_cache_key(source_path)
    cached = _get_cached_input_document(_EPUB_INPUT_DOCUMENT_CACHE, cache_key)
    if isinstance(cached, EpubInputDocument):
        return cached

    _preflight_epub_package(source_path)

    epub = _require_ebooklib_epub()
    try:
        book = epub.read_epub(str(source_path))
    except Exception as exc:
        if _epub_package_has_encryption_descriptor(source_path):
            raise RuntimeError(
                'EPUB の読み込みに失敗しました。META-INF/encryption.xml が見つかったため、DRM付きEPUB、または暗号化/難読化されたフォント・画像を含むEPUBの可能性があります。'
            ) from exc
        raise
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




def _epub_xml_local_name(tag: object) -> str:
    """Return an XML tag name without its namespace for EPUB package checks."""
    text = str(tag or '')
    if '}' in text:
        return text.rsplit('}', 1)[-1]
    if ':' in text:
        return text.rsplit(':', 1)[-1]
    return text


def _epub_structure_error(message: str) -> RuntimeError:
    """Create a normalized EPUB structure error for user-facing diagnostics."""
    return RuntimeError(str(message).strip() or 'EPUB構造を解析できませんでした。')


def _epub_find_container_rootfile_path(container_bytes: bytes) -> str:
    try:
        root = ET.fromstring(container_bytes)
    except ET.ParseError as exc:
        raise _epub_structure_error(
            'EPUB の META-INF/container.xml を解析できません。EPUB構造が壊れている可能性があります。'
        ) from exc

    fallback_path = ''
    for elem in root.iter():
        if _epub_xml_local_name(elem.tag) != 'rootfile':
            continue
        full_path = _normalize_epub_href(elem.attrib.get('full-path', ''))
        if not full_path:
            continue
        if not fallback_path:
            fallback_path = full_path
        media_type = str(elem.attrib.get('media-type', '') or '').strip().lower()
        if media_type == 'application/oebps-package+xml':
            return full_path
    if fallback_path:
        return fallback_path
    raise _epub_structure_error(
        'EPUB の META-INF/container.xml に OPF パッケージ文書への参照が見つかりません。'
    )


def _epub_read_zip_member(zf: zipfile.ZipFile, name: str, *, label: str) -> bytes:
    normalized = _normalize_epub_href(name)
    if not normalized:
        raise _epub_structure_error(f'EPUB の {label} への参照が空です。')
    try:
        return zf.read(normalized)
    except KeyError as exc:
        raise _epub_structure_error(
            f'EPUB の {label}が見つかりません。参照先: {normalized}'
        ) from exc


def _epub_manifest_item_path(opf_path: str, href: object) -> str:
    href_text = _normalize_epub_href(href)
    if not href_text:
        return ''
    base_dir = posixpath.dirname(_normalize_epub_href(opf_path))
    return _normalize_epub_href(posixpath.join(base_dir, href_text) if base_dir else href_text)


def _epub_spine_linear_text(value: object) -> str:
    return str(value or '').strip().lower()


def _preflight_epub_package(epub_path: PathLike) -> None:
    """Validate the minimum EPUB package structure before handing it to ebooklib.

    ebooklib can raise terse low-level exceptions for malformed EPUBs.  This
    lightweight preflight keeps normal EPUBs on the existing route while turning
    common structural failures into actionable Japanese messages.
    """
    source_path = Path(epub_path)
    try:
        with zipfile.ZipFile(source_path, 'r') as zf:
            entries = {_normalize_epub_href(info.filename) for info in zf.infolist()}
            if not entries:
                raise _epub_structure_error('EPUB ZIP の中身が空です。EPUBファイルが破損している可能性があります。')
            if 'META-INF/container.xml' not in entries:
                raise _epub_structure_error(
                    'EPUB の META-INF/container.xml が見つかりません。EPUB構造が壊れている可能性があります。'
                )
            container_bytes = _epub_read_zip_member(zf, 'META-INF/container.xml', label='container.xml')
            opf_path = _epub_find_container_rootfile_path(container_bytes)
            opf_bytes = _epub_read_zip_member(zf, opf_path, label='OPF パッケージ文書')
            try:
                opf_root = ET.fromstring(opf_bytes)
            except ET.ParseError as exc:
                raise _epub_structure_error(
                    f'EPUB の OPF パッケージ文書を解析できません。参照先: {opf_path}'
                ) from exc

            manifest: dict[str, tuple[str, str]] = {}
            spine_refs: list[tuple[str, str]] = []
            for elem in opf_root.iter():
                local_name = _epub_xml_local_name(elem.tag)
                if local_name == 'item':
                    item_id = str(elem.attrib.get('id', '') or '').strip()
                    href = elem.attrib.get('href', '')
                    media_type = str(elem.attrib.get('media-type', '') or '').strip().lower()
                    if item_id:
                        manifest[item_id] = (_epub_manifest_item_path(opf_path, href), media_type)
                elif local_name == 'itemref':
                    idref = str(elem.attrib.get('idref', '') or '').strip()
                    linear = _epub_spine_linear_text(elem.attrib.get('linear', ''))
                    if idref:
                        spine_refs.append((idref, linear))

            if not manifest:
                raise _epub_structure_error('EPUB の manifest が空です。本文ファイルや画像の一覧を確認できません。')
            if not spine_refs:
                raise _epub_structure_error('EPUB の読み順情報 spine が見つかりません。本文の順番を判断できません。')

            linear_refs = [(idref, linear) for idref, linear in spine_refs if linear not in {'no', 'false', '0'}]
            if not linear_refs:
                raise _epub_structure_error(
                    'EPUB の読み順情報 spine はありますが、本文対象がすべて linear="no" 扱いです。本文として変換できる章が見つかりません。'
                )

            html_doc_count = 0
            for idref, _linear in linear_refs:
                manifest_entry = manifest.get(idref)
                if manifest_entry is None:
                    raise _epub_structure_error(
                        f'EPUB の spine が manifest に存在しない項目を参照しています。idref: {idref}'
                    )
                href_path, media_type = manifest_entry
                if not href_path:
                    raise _epub_structure_error(
                        f'EPUB の manifest 項目に本文ファイルへの href がありません。idref: {idref}'
                    )
                is_html = media_type in {'application/xhtml+xml', 'text/html'} or href_path.lower().endswith(('.xhtml', '.html', '.htm'))
                if is_html:
                    html_doc_count += 1
                    if href_path not in entries:
                        raise _epub_structure_error(
                            f'EPUB の spine が参照する本文ファイルが見つかりません。参照先: {href_path}'
                        )
            if html_doc_count == 0:
                raise _epub_structure_error(
                    'EPUB の spine に HTML/XHTML 本文ファイルが見つかりません。対応外の構造、またはDRM付きEPUBの可能性があります。'
                )
    except zipfile.BadZipFile as exc:
        raise _epub_structure_error(
            'EPUBファイルをZIPとして開けませんでした。ファイルが破損しているか、拡張子だけが .epub の可能性があります。'
        ) from exc
    except FileNotFoundError:
        raise
    except RuntimeError:
        raise
    except Exception as exc:
        raise _epub_structure_error(f'EPUB構造の事前確認に失敗しました。詳細: {exc}') from exc


def _epub_package_has_encryption_descriptor(epub_path: PathLike) -> bool:
    """Return True when the EPUB advertises encrypted/obfuscated resources."""
    try:
        with zipfile.ZipFile(Path(epub_path), 'r') as zf:
            entries = {_normalize_epub_href(info.filename) for info in zf.infolist()}
        return 'META-INF/encryption.xml' in entries
    except Exception:
        return False


# --- moved from tategakiXTC_gui_core.py lines 9822-10353 ---
def _classify_epub_embedded_image(s_img: Image.Image, args: ConversionArgs) -> bool:
    """EPUB 埋め込み画像を本文内画像として扱うか、フルページ挿絵として扱うか判定する。"""
    _refresh_split_globals()
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
    _refresh_split_globals()
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
    _refresh_split_globals()
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
    _refresh_split_globals()
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
    _refresh_split_globals()
    data_image = _decode_epub_data_image_uri(raw_src)
    if data_image:
        return 'data:image', data_image

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
    _refresh_split_globals()
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
    _refresh_split_globals()
    """EPUB本文のテキスト断片を描画前に正規化する。"""
    normalized = text.replace('\r', '').replace('\n', '').replace('\xa0', ' ')
    if strip_start_text:
        normalized = _strip_leading_start_text(normalized)
    normalized = normalized.rstrip()
    if strip_leading_for_indent:
        normalized = _EPUB_TEXT_LEADING_WS_RE.sub('', normalized)
    return normalized



def _epub_text_excluding_ruby_annotations(node: Any) -> str:
    parts: list[str] = []
    for child in getattr(node, 'contents', ()):  # BeautifulSoup Tag children
        child_name = (getattr(child, 'name', '') or '').lower()
        if child_name in {'rt', 'rp', 'rtc'}:
            continue
        if getattr(child, 'contents', None) is not None:
            parts.append(_epub_text_excluding_ruby_annotations(child))
        else:
            parts.append(str(child))
    if not getattr(node, 'contents', None) and hasattr(node, 'get_text'):
        try:
            return str(node.get_text('', strip=False))
        except Exception:
            return str(node)
    return ''.join(parts)


def _epub_collect_ruby_text(node: Any) -> str:
    node_name = (getattr(node, 'name', '') or '').lower()
    if node_name == 'rtc':
        rt_parts: list[str] = []
        try:
            rt_nodes = list(node.find_all('rt'))
        except Exception:
            rt_nodes = []
        for rt_node in rt_nodes:
            rt_parts.append(_epub_collect_ruby_text(rt_node))
        if rt_parts:
            return ''.join(rt_parts)
    try:
        text = str(node.get_text('', strip=False))
        if text:
            return text
    except Exception:
        pass
    return ''.join(str(child) for child in getattr(node, 'contents', ())) or str(node)


def _extract_epub_ruby_parts(node: Any) -> tuple[str, str]:
    """Extract base text and ruby text without leaking rtc/rt text into the body.

    EPUBs in the wild use several ruby shapes, including simple
    ``<ruby>基<rt>ruby</rt></ruby>``, explicit ``rb`` nodes, and grouped
    ``rtc`` annotations.  The renderer needs the base string and annotation
    string separately; treating ``rtc`` as normal child text would duplicate ruby
    readings in the body.
    """
    rb_parts: list[str] = []
    rt_parts: list[str] = []
    for child in getattr(node, 'contents', ()):  # BeautifulSoup Tag children
        child_name = (getattr(child, 'name', '') or '').lower()
        if child_name == 'rt':
            rt_parts.append(_epub_collect_ruby_text(child))
            continue
        if child_name == 'rtc':
            rt_parts.append(_epub_collect_ruby_text(child))
            continue
        if child_name == 'rp':
            continue
        if child_name in {'rb', 'rbc'}:
            rb_parts.append(_epub_text_excluding_ruby_annotations(child))
            continue
        if getattr(child, 'contents', None) is not None:
            rb_parts.append(_epub_text_excluding_ruby_annotations(child))
        else:
            rb_parts.append(str(child))
    return ''.join(rb_parts), ''.join(rt_parts)


def _epub_image_node_source(node: Any) -> str:
    """Return the first supported image href-like attribute for EPUB image nodes."""
    for attr_name in ('src', 'xlink:href', 'href', 'data-src', 'data-original'):
        try:
            value = node.get(attr_name, '')
        except Exception:
            value = ''
        if value:
            return str(value)
    for attr_name in ('srcset', 'data-srcset'):
        try:
            value = node.get(attr_name, '')
        except Exception:
            value = ''
        candidate = _first_epub_srcset_candidate(value)
        if candidate:
            return candidate
    return ''


def _epub_background_image_source(node: Any, css_rules: Sequence[CSSRule] | None = None) -> str:
    """Return a conservative background-image URL for otherwise image-like EPUB nodes."""
    style_map = _merged_epub_css_for_node(node, css_rules)
    return _extract_epub_css_url(style_map.get('background-image', ''))


def _epub_picture_node_source(node: Any) -> str:
    """Return the best fallback source from a <picture> element."""
    try:
        img = node.find('img')
    except Exception:
        img = None
    if img is not None:
        src = _epub_image_node_source(img)
        if src:
            return src
    try:
        sources = list(node.find_all('source'))
    except Exception:
        sources = []
    for source in sources:
        src = _epub_image_node_source(source)
        if src:
            return src
    return ''


def _render_epub_chapter_pages_from_html(html_content: str | bytes, doc_file_name: str, args: ConversionArgs, font: Any, ruby_font: Any, bold_rules: Mapping[str, set[str]],
                                         image_map: Mapping[str, bytes], image_basename_map: Mapping[str, Sequence[tuple[str, bytes] | str]], css_rules: Sequence[dict[str, Any]] | None = None, primary_font_value: str = '',
                                         code_font_value: str | None = None, should_cancel: Callable[[], bool] | None = None, page_created_cb: Callable[[PageEntry], None] | None = None, store_page_entries: bool = True,
                                         max_output_pages: int | None = None) -> PageEntries:
    """EPUB 1章分の HTML を描画し、ページエントリ一覧を返す。"""
    _refresh_split_globals()
    _renderer._refresh_core_globals()
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
    # Ruby overlays may be applied after base text layout and can cross page
    # boundaries.  Keep ruby-containing chapters in memory until the final overlay
    # pass has completed.  Ruby-free chapters can stream finalized pages to the
    # caller immediately, which reduces memory use for large one-chapter EPUBs.
    try:
        chapter_has_ruby = body.find('ruby') is not None
    except Exception:
        chapter_has_ruby = False
    stream_completed_pages = bool(page_created_cb is not None and not store_page_entries and not chapter_has_ruby)
    renderer = _VerticalPageRenderer(
        args,
        font,
        ruby_font,
        should_cancel=should_cancel,
        page_created_cb=page_created_cb if stream_completed_pages else None,
        store_page_entries=True if chapter_has_ruby else (store_page_entries if not stream_completed_pages else False),
        max_buffered_pages=page_limit,
        default_page_args=args,
        default_page_label='本文ページ',
        code_font_loader=_load_code_font,
    )
    completed_page_entries: PageEntries = []

    def drain_completed_pages() -> None:
        entries = renderer.pop_page_entries()
        if entries:
            # pop_page_entries() is called at overlay-safe boundaries.  When a
            # page_created_cb is supplied with store_page_entries=False, the renderer
            # streams finalized entries to the callback and returns an empty list.
            # This avoids retaining huge one-chapter EPUBs in memory while preserving
            # ruby overlay correctness.
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
        raw_src = _epub_image_node_source(node)
        if not raw_src and (getattr(node, 'name', '') or '').lower() == 'picture':
            raw_src = _epub_picture_node_source(node)
        if not raw_src:
            raw_src = _epub_background_image_source(node, css_rules)
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

    def _handle_ruby_node(node: Any, node_bold: bool, node_code: bool, wrap_indent_chars: int) -> None:
        rb, rt = _extract_epub_ruby_parts(node)
        rb = normalize_text(rb, strip_leading_for_indent=renderer.has_pending_paragraph_indent)
        if not rb:
            return
        renderer.apply_pending_paragraph_indent()
        renderer.draw_runs(
            _epub_runs(rb, bold=node_bold, code=node_code, ruby='' if bool(getattr(args, 'ruby_hide', False)) else rt),
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

        if node_name in {'img', 'image', 'source'} and _epub_image_node_source(node):
            _handle_epub_image_node(node, wrap_indent_chars)
            return True

        if node_name == 'picture' and _epub_picture_node_source(node):
            _handle_epub_image_node(node, wrap_indent_chars)
            return True

        background_src = _epub_background_image_source(node, css_rules)
        if background_src and _epub_node_is_effectively_empty(node):
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
    _refresh_split_globals()
    epub_path = Path(epub_path)
    _raise_if_cancelled(should_cancel)
    try:
        document = load_epub_input_document(epub_path)
    except ConversionCancelled:
        raise
    except Exception as exc:
        report = build_conversion_error_report(epub_path, exc, stage='EPUB読込')
        raise RuntimeError(report['display']) from exc

    try:
        font = load_truetype_font(font_path, args.font_size)
        ruby_font = load_truetype_font(font_path, args.ruby_size)
    except ConversionCancelled:
        raise
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

    if bool(getattr(args, 'page_number_enabled', False)):
        page_entries: PageEntries = []
        page_number_memory_notice_emitted = False
        for doc_index, item in enumerate(_iter_with_optional_tqdm(docs, desc="描画中", unit="章", leave=False), 1):
            _raise_if_cancelled(should_cancel)
            chapter_name = Path(getattr(item, "file_name", "") or f"chapter_{doc_index}").name
            _emit_progress(progress_cb, doc_index - 1, total_docs, f'章を描画中… ({max(0, doc_index - 1)}/{total_docs} 章) {chapter_name}')
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
                    page_created_cb=None,
                    store_page_entries=True,
                )
            except ConversionCancelled:
                raise
            except Exception as exc:
                report = build_conversion_error_report(epub_path, exc, stage=f'章描画: {chapter_name}')
                raise RuntimeError(report['display']) from exc
            page_entries.extend(chapter_pages)
            total_rendered_pages = len(page_entries)
            if not page_number_memory_notice_emitted and total_rendered_pages >= 300:
                page_number_memory_notice_emitted = True
                _emit_progress(
                    progress_cb,
                    doc_index,
                    total_docs,
                    'ページ番号表示ONのため、総ページ数確定までEPUBページを一時保持しています。大きいEPUBでは処理に時間やメモリを使います。'
                )
            _emit_progress(progress_cb, doc_index, total_docs, f'章の変換を完了しました。({doc_index}/{total_docs} 章 / {total_rendered_pages} 累計ページ)')
        if not page_entries:
            report = build_conversion_error_report(epub_path, RuntimeError('変換できるページがありませんでした'), stage='EPUB描画')
            raise RuntimeError(report['display'])
        ext = '.xtch' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else '.xtc'
        out_path = Path(output_path) if output_path else epub_path.with_suffix(ext)
        try:
            return _write_page_entries_to_xtc(
                page_entries,
                epub_path,
                args,
                output_path=out_path,
                should_cancel=should_cancel,
                progress_cb=progress_cb,
                message_builder=lambda page_index, total_pages, entry, label: f'EPUBページを変換中… ({page_index}/{total_pages} ページ)',
                complete_message=lambda page_count, total_pages, last: f'EPUBページ変換が完了しました。({page_count} ページ)',
            )
        except ConversionCancelled:
            raise
        except Exception as exc:
            report = build_conversion_error_report(epub_path, exc, stage='出力書込')
            raise RuntimeError(report['display']) from exc

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
                except ConversionCancelled:
                    raise
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
            except ConversionCancelled:
                raise
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
                except ConversionCancelled:
                    raise
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
        except ConversionCancelled:
            raise
        except Exception as exc:
            report = build_conversion_error_report(epub_path, exc, stage='出力書込')
            raise RuntimeError(report['display']) from exc
        return out_path
