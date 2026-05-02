"""
tategakiXTC_gui_core_fonts.py — フォント検出 / フォント指定 helper

`tategakiXTC_gui_core.py` から分離したフォント関連実装。互換性維持のため、
gui_core 側の re-export / 既存テストの monkey patch を各入口で同期する。
"""
from __future__ import annotations

from typing import Any

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals'}
_CORE_SYNC_VERSION = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch をフォント実装へ反映する。"""
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
    _refresh_core_globals()
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
    _refresh_core_globals()
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
    _refresh_core_globals()
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
    _refresh_core_globals()
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
    _refresh_core_globals()
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
    _refresh_core_globals()
    normalized_path = str(path_text or '').strip()
    if not normalized_path:
        return ''
    normalized_index = max(0, int(index or 0))
    if normalized_path.lower().endswith('.ttc') or normalized_index > 0:
        return f'{normalized_path}{FONT_SPEC_INDEX_TOKEN}{normalized_index}'
    return normalized_path


def build_font_spec(path_value: object, index: int = 0) -> str:
    """フォントパスと TTC face index を保存用文字列へ直列化する。"""
    _refresh_core_globals()
    return _cached_build_font_spec(str(path_value or ''), int(index or 0))


def _font_path_key(path_like: PathLike) -> str:
    _refresh_core_globals()
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
    _refresh_core_globals()
    try:
        family, style = font_obj.getname()
    except Exception:
        family, style = '', ''
    return str(family or '').strip(), str(style or '').strip()


@lru_cache(maxsize=256)
def _cached_load_truetype_font(font_path: str, font_index: int, size: int) -> Any:
    _refresh_core_globals()
    return ImageFont.truetype(font_path, size, index=font_index)


def load_truetype_font(font_value: object, size: int) -> Any:
    _refresh_core_globals()
    font_path = require_font_path(font_value)
    _font_value, font_index = parse_font_spec(font_value)
    return _cached_load_truetype_font(str(font_path), font_index, int(size))


def describe_font_value(font_value: object) -> str:
    _refresh_core_globals()
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
    _refresh_core_globals()
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
    _refresh_core_globals()
    return list(_font_entries_for_value(font_value))


def _clear_named_cache(name: str) -> None:
    obj = globals().get(name)
    cache_clear = getattr(obj, 'cache_clear', None)
    if callable(cache_clear):
        cache_clear()


def clear_font_entry_cache() -> None:
    _refresh_core_globals()
    _clear_named_cache('_font_entries_for_value')
    _clear_named_cache('_preferred_system_font_specs')
    _clear_named_cache('_font_scan_targets')
    _clear_named_cache('_cached_resolve_font_path')
    _clear_named_cache('_cached_require_font_path')
    _clear_named_cache('get_code_font_value')
    _clear_named_cache('_cached_load_truetype_font')
    _clear_named_cache('_cached_render_text_glyph_image')
    _clear_named_cache('_cached_render_text_glyph_bundle')
    _clear_named_cache('_cached_glyph_signature')
    _clear_named_cache('_missing_glyph_signatures')
    _clear_named_cache('_cached_font_has_distinct_glyph')
    _clear_named_cache('_cached_resolve_vertical_glyph_char')
    _clear_named_cache('_cached_tate_draw_spec')
    _clear_named_cache('_cached_horizontal_rotation_decision')
    _clear_named_cache('_cached_reference_glyph_center')
    _clear_named_cache('_get_reference_glyph_center')
    _clear_named_cache('_cached_build_font_spec')
    _clear_named_cache('_cached_resolve_cacheable_font_spec')
    _clear_named_cache('_candidate_font_paths')
    _clear_named_cache('_scaled_kutoten_offset')
    _clear_named_cache('_small_kana_offset')
    _clear_named_cache('_hanging_bottom_layout')
    _clear_named_cache('_hanging_bottom_draw_offsets')
    _clear_named_cache('_tate_hanging_punctuation_raise')
    _clear_named_cache('_effective_vertical_layout_bottom_margin')
    _clear_named_cache('_kagikakko_extra_y')
    _clear_named_cache('_should_draw_emphasis_for_cell_cached')
    _clear_named_cache('_should_draw_side_line_for_cell_cached')
    _clear_named_cache('_classify_tate_draw_char')
    _clear_named_cache('_is_render_spacing_char')
    _clear_named_cache('_is_tatechuyoko_token')
    _clear_named_cache('_tatechuyoko_layout_limits')
    _clear_named_cache('_cached_text_bbox_dims')
    _clear_named_cache('_glyph_canvas_layout')
    _clear_named_cache('_italic_extra_width')
    _clear_named_cache('_italic_transform_layout')
    _clear_named_cache('_tatechuyoko_paste_offsets')
    _clear_named_cache('_cached_tatechuyoko_candidate_dims')
    _clear_named_cache('_cached_tatechuyoko_fit_size')
    _clear_named_cache('_cached_tatechuyoko_bundle')
    _clear_named_cache('_split_ruby_text_segments_cached')
    _clear_named_cache('_tokenize_vertical_text_cached')
    _clear_named_cache('_build_single_token_vertical_layout_hints')
    _clear_named_cache('_build_two_token_vertical_layout_hints')
    _clear_named_cache('_build_three_token_vertical_layout_hints')
    _clear_named_cache('_build_four_token_vertical_layout_hints')
    _clear_named_cache('_build_vertical_layout_hints_cached')


@lru_cache(maxsize=1)
def _font_scan_targets() -> tuple[str, ...]:
    _refresh_core_globals()
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
    _refresh_core_globals()
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
    _refresh_core_globals()
    fonts = [entry['value'] for entry in get_font_entries()]
    return fonts if fonts else ['(フォントなし)']


@lru_cache(maxsize=512)
def _cached_resolve_font_path(font_spec: str) -> str:
    _refresh_core_globals()
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
    _refresh_core_globals()
    font_spec = build_font_spec(*parse_font_spec(font_value))
    if not font_spec:
        return None
    resolved = _cached_resolve_font_path(font_spec)
    return Path(resolved) if resolved else None


@lru_cache(maxsize=512)
def _cached_require_font_path(font_spec: str) -> str:
    _refresh_core_globals()
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
    _refresh_core_globals()
    font_spec = build_font_spec(*parse_font_spec(font_value))
    if not font_spec:
        raise RuntimeError("フォントが指定されていません。")
    return Path(_cached_require_font_path(font_spec))


@lru_cache(maxsize=64)
def get_code_font_value(primary_font_value: str = '') -> str:
    """コードブロック向けに使える等幅寄りフォントを探す。見つからない場合は元のフォントを返す。"""
    _refresh_core_globals()
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


