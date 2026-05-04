"""ConversionWorker から切り出した GUI 非依存 helper 群。

Public helpers:
- build_conversion_args
- resolve_supported_conversion_targets
- sanitize_output_stem
- plan_output_path_for_target
- extract_error_headline
- summarize_error_headlines
- collect_conversion_counts
- resolve_open_folder_target
- build_conversion_summary
"""

from __future__ import annotations

import ntpath
import os
import math
from collections.abc import Collection
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Iterable, Literal, Mapping, Sequence, TypedDict

import tategakiXTC_gui_core as core
from tategakiXTC_gui_core import ConversionArgs


ConfigScalar = str | int | float | bool
OutputFormat = Literal['xtc', 'xtch']
ConflictStrategy = Literal['rename', 'overwrite', 'error']


class WorkerConversionSettings(TypedDict, total=False):
    target: str
    font_file: str
    font_size: ConfigScalar
    ruby_size: ConfigScalar
    line_spacing: ConfigScalar
    margin_t: ConfigScalar
    margin_b: ConfigScalar
    margin_r: ConfigScalar
    margin_l: ConfigScalar
    dither: ConfigScalar
    threshold: ConfigScalar
    night_mode: ConfigScalar
    kinsoku_mode: str
    punctuation_position_mode: str
    ichi_position_mode: str
    lower_closing_bracket_position_mode: str
    wave_dash_drawing_mode: str
    wave_dash_position_mode: str
    output_format: str
    output_conflict: str
    output_name: str
    open_folder: bool
    width: ConfigScalar
    height: ConfigScalar


ConflictPlan = core.ConflictPlan


class ConversionErrorItem(TypedDict, total=False):
    source: str
    error: str
    headline: str
    display: str


class ConversionCounts(TypedDict):
    converted: int
    renamed: int
    overwritten: int
    errors: int
    skipped: int


def _normalize_error_mapping_item(item: Mapping[object, object]) -> ConversionErrorItem:
    normalized_item: ConversionErrorItem = {}
    for key in ('source', 'error', 'headline', 'display'):
        if key not in item:
            continue
        value = item.get(key)
        if value is None:
            continue
        text = _coerce_error_text(value)
        if text and text.strip():
            normalized_item[key] = text
    return normalized_item


def _int_config_value(cfg: WorkerConversionSettings, key: str, default: int) -> int:
    value = cfg.get(key, default)
    try:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return int(value)
        if isinstance(value, float):
            return int(value) if math.isfinite(value) else int(default)
        if isinstance(value, (bytes, bytearray)):
            value = value.decode('utf-8')
        if isinstance(value, str):
            normalized = value.strip()
            if not normalized:
                return int(default)
            try:
                return int(normalized, 10)
            except (TypeError, ValueError, OverflowError):
                parsed = float(normalized)
                return int(parsed) if math.isfinite(parsed) else int(default)
    except (TypeError, ValueError, OverflowError):
        return int(default)
    return int(default)



def _bool_config_value(cfg: WorkerConversionSettings, key: str, default: bool) -> bool:
    value = cfg.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, float):
        return bool(value) if math.isfinite(value) else bool(default)
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        if not raw.strip():
            return bool(default)
        try:
            value = raw.decode('utf-8')
        except Exception:
            return bool(default)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return bool(default)
        if normalized in {'1', 'true', 'yes', 'on'}:
            return True
        if normalized in {'0', 'false', 'no', 'off'}:
            return False
        try:
            return bool(int(normalized, 10))
        except (TypeError, ValueError, OverflowError):
            pass
        try:
            parsed = float(normalized)
            return bool(parsed) if math.isfinite(parsed) else bool(default)
        except (TypeError, ValueError, OverflowError):
            pass
    return bool(default)





def coerce_postprocess_warning_messages(values: object) -> list[str]:
    if values is None:
        return []
    if isinstance(values, (list, tuple, set, frozenset)):
        candidates = list(values)
    else:
        candidates = [values]
    normalized: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        if item is None:
            continue
        text = _coerce_error_text(item).replace('\r\n', '\n').replace('\r', '\n')
        for line in text.split('\n'):
            message = line.strip()
            if not message or message in seen:
                continue
            seen.add(message)
            normalized.append(message)
    return normalized


def merge_postprocess_warnings_into_summary_lines(summary_lines: object, warning_values: object) -> list[object]:
    if isinstance(summary_lines, list):
        merged_lines: list[object] = list(summary_lines)
    elif isinstance(summary_lines, tuple):
        merged_lines = list(summary_lines)
    elif summary_lines is None:
        merged_lines = []
    else:
        merged_lines = [summary_lines]

    if isinstance(warning_values, (list, tuple)) and all(isinstance(item, str) for item in warning_values):
        warnings = [item.strip() for item in warning_values if isinstance(item, str) and item.strip()]
        if any(('\n' in item) or ('\r' in item) for item in warnings):
            warnings = coerce_postprocess_warning_messages(warning_values)
        else:
            warnings = list(dict.fromkeys(warnings))
    else:
        warnings = coerce_postprocess_warning_messages(warning_values)
    if not warnings:
        return merged_lines

    existing_lines: set[str] = set()
    for item in merged_lines:
        if item is None:
            continue
        text = _coerce_error_text(item).replace('\r\n', '\n').replace('\r', '\n')
        for line in text.split('\n'):
            normalized = line.strip()
            if normalized:
                existing_lines.add(normalized)

    for warning_message in warnings:
        summary_line = f'警告: {warning_message}'
        if summary_line in existing_lines:
            continue
        merged_lines.append(summary_line)
        existing_lines.add(summary_line)
    return merged_lines

def _str_config_value(cfg: WorkerConversionSettings, key: str, default: str) -> str:
    value = cfg.get(key, default)
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        try:
            return raw.decode('utf-8')
        except Exception:
            return default
    if value is None:
        return default
    return str(value)


__all__ = [
    'WorkerConversionSettings',
    'ConflictPlan',
    'ConversionErrorItem',
    'ConversionCounts',
    'build_conversion_args',
    'resolve_supported_conversion_targets',
    'sanitize_output_stem',
    'normalize_target_path_text',
    'plan_output_path_for_target',
    'reserve_unique_output_path_for_batch',
    'extract_error_headline',
    'summarize_error_headlines',
    'collect_conversion_counts',
    'resolve_open_folder_target',
    'build_conversion_summary',
    'coerce_postprocess_warning_messages',
    'merge_postprocess_warnings_into_summary_lines',
]


def build_conversion_args(cfg: WorkerConversionSettings) -> ConversionArgs:
    return ConversionArgs(
        width=_int_config_value(cfg, 'width', 480),
        height=_int_config_value(cfg, 'height', 800),
        font_size=_int_config_value(cfg, 'font_size', 26),
        ruby_size=_int_config_value(cfg, 'ruby_size', 12),
        line_spacing=_int_config_value(cfg, 'line_spacing', 44),
        margin_t=_int_config_value(cfg, 'margin_t', 12),
        margin_b=_int_config_value(cfg, 'margin_b', 14),
        margin_r=_int_config_value(cfg, 'margin_r', 12),
        margin_l=_int_config_value(cfg, 'margin_l', 12),
        dither=_bool_config_value(cfg, 'dither', False),
        night_mode=_bool_config_value(cfg, 'night_mode', False),
        threshold=_int_config_value(cfg, 'threshold', 128),
        kinsoku_mode=_str_config_value(cfg, 'kinsoku_mode', 'standard'),
        punctuation_position_mode=_str_config_value(cfg, 'punctuation_position_mode', 'standard'),
        ichi_position_mode=_str_config_value(cfg, 'ichi_position_mode', 'standard'),
        lower_closing_bracket_position_mode=_str_config_value(cfg, 'lower_closing_bracket_position_mode', 'standard'),
        wave_dash_drawing_mode=core._wave_dash_drawing_mode(_str_config_value(cfg, 'wave_dash_drawing_mode', 'rotate')),
        wave_dash_position_mode=core._wave_dash_position_mode(_str_config_value(cfg, 'wave_dash_position_mode', 'standard')),
        output_format=_str_config_value(cfg, 'output_format', 'xtc'),
    )



def resolve_supported_conversion_targets(tp: Path, supported_input_suffixes: Iterable[str]) -> list[Path]:
    allowed_suffixes = frozenset(
        list(str(item).lower() for item in supported_input_suffixes)
        + [str(item).lower() for item in core.IMG_EXTS]
    )
    all_targets = core.iter_conversion_targets(tp)
    targets = [p for p in all_targets if not core.should_skip_conversion_target(p)]
    return [p for p in targets if p.suffix.lower() in allowed_suffixes]



_INVALID_FILENAME_CHARS = frozenset(r'<>:"/\\|?*')
_WINDOWS_RESERVED_FILENAMES = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
})


def sanitize_output_stem(name: str) -> str:
    raw = str(name or '').strip()
    if not raw:
        return ''
    basename = ntpath.basename(raw)
    basename = os.path.basename(basename)
    stem = Path(basename).stem.strip().rstrip(' .')
    if not stem or stem in {'.', '..'}:
        return ''
    if stem.startswith('.'):
        return ''
    if any(ord(ch) < 32 or ch in _INVALID_FILENAME_CHARS for ch in stem):
        return ''
    if stem.upper() in _WINDOWS_RESERVED_FILENAMES:
        return ''
    return stem


def normalize_target_path_text(value: object) -> str:
    raw = _coerce_path_text(value).strip()
    if not raw:
        return ''
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        quoted = raw[1:-1].strip()
        if quoted:
            return quoted
    return raw



def plan_output_path_for_target(
    path: Path,
    args: ConversionArgs,
    requested_name: str,
    supported_count: int,
    conflict_strategy: str,
    *,
    output_root: Path | None = None,
    apply_conflict_strategy: Callable[[Path, str], tuple[Path, ConflictPlan]] | None = None,
    output_path_getter: Callable[[Path, str, Path | None], Path | None] | None = None,
) -> tuple[Path | None, ConflictPlan | None, str | None]:
    if apply_conflict_strategy is None:
        apply_conflict_strategy = core.resolve_output_path_with_conflict
    if output_path_getter is None:
        output_path_getter = lambda src, fmt, out_root=None: core.get_output_path_for_target(src, fmt, output_root=out_root)

    requested_name = str(requested_name or '').strip()
    use_custom = bool(requested_name) and supported_count == 1
    warning = None
    if requested_name and not use_custom:
        warning = '出力名の指定は単一ファイル変換時のみ使用します。今回は自動命名にします。'
    desired: Path | None
    if use_custom:
        stem = sanitize_output_stem(requested_name)
        if not stem:
            raise RuntimeError('出力ファイル名が不正です。')
        ext = '.xtch' if str(getattr(args, 'output_format', 'xtc')).strip().lower() == 'xtch' else '.xtc'
        desired_base = output_root if output_root else path.parent
        desired = desired_base / f'{stem}{ext}'
        out_path, plan = apply_conflict_strategy(desired, conflict_strategy)
        return out_path, plan, warning
    desired = output_path_getter(path, str(getattr(args, 'output_format', 'xtc')), output_root)
    if not desired:
        return None, None, warning
    out_path, plan = apply_conflict_strategy(desired, conflict_strategy)
    return out_path, plan, warning


def reserve_unique_output_path_for_batch(
    out_path: Path,
    plan: ConflictPlan | None,
    reserved_keys: Collection[str] | None,
) -> tuple[Path, ConflictPlan | None]:
    final_path = Path(out_path)
    key = _normalize_path_match_key(final_path) or str(final_path)
    reserved = set(str(item) for item in (reserved_keys or ()) if str(item))
    if key not in reserved:
        return final_path, plan

    desired_raw = str(plan.get('desired_path') or final_path) if isinstance(plan, dict) else str(final_path)
    desired_path = Path(desired_raw)
    stem = desired_path.stem
    suffix = desired_path.suffix
    idx = 1
    while True:
        candidate = desired_path.with_name(f'{stem}({idx}){suffix}')
        candidate_key = _normalize_path_match_key(candidate) or str(candidate)
        if candidate_key not in reserved and not candidate.exists():
            break
        idx += 1

    new_plan: ConflictPlan | None
    if isinstance(plan, dict):
        new_plan = dict(plan)
    else:
        new_plan = {
            'desired_path': str(desired_path),
            'final_path': str(candidate),
            'conflict': False,
            'renamed': False,
            'overwritten': False,
            'strategy': 'rename',
        }
    new_plan['desired_path'] = str(desired_path)
    new_plan['final_path'] = str(candidate)
    new_plan['conflict'] = True
    new_plan['renamed'] = str(candidate) != str(desired_path)
    new_plan['overwritten'] = False
    new_plan['batch_collision'] = True
    return candidate, new_plan


def extract_error_headline(message: str) -> str:
    for line in str(message or '').splitlines():
        line = line.strip()
        if not line.startswith('内容:'):
            continue
        detail = line.split(':', 1)[1].strip()
        if detail:
            return detail
    compact = ' '.join(str(message or '').split())
    return compact[:80] + ('…' if len(compact) > 80 else '')



def summarize_error_headlines(errors: Sequence[ConversionErrorItem] | None, *, max_items: int = 2) -> list[str]:
    counts: dict[str, int] = {}
    for item in errors or []:
        headline = str(item.get('headline', '')).strip() or extract_error_headline(str(item.get('error', '')))
        if not headline:
            continue
        counts[headline] = counts.get(headline, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if not ranked:
        return []
    joined = ' / '.join(f'{headline} {count}件' for headline, count in ranked[: max(1, int(max_items or 1))])
    return [f'主な原因 {joined}']



def _coerce_count_item(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, os.PathLike):
        return 1 if os.fspath(value).strip() else 0
    if isinstance(value, str):
        return 1 if value.strip() else 0
    if isinstance(value, (bytes, bytearray)):
        return 1 if bytes(value).strip() else 0
    if isinstance(value, Mapping):
        return 1 if value else 0
    return 1



def _coerce_count(value: int | os.PathLike[str] | Iterable[Any] | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return max(0, int(value))
    if isinstance(value, float):
        return max(0, int(value)) if math.isfinite(value) else 0
    if isinstance(value, os.PathLike):
        return 1 if os.fspath(value).strip() else 0
    if isinstance(value, str):
        return 1 if value.strip() else 0
    if isinstance(value, (bytes, bytearray)):
        return 1 if bytes(value).strip() else 0
    if isinstance(value, Mapping):
        return 1 if value else 0
    if isinstance(value, Sequence):
        return max(0, sum(_coerce_count_item(item) for item in value))
    try:
        return max(0, sum(_coerce_count_item(item) for item in value))
    except TypeError:
        return 1 if value else 0



def collect_conversion_counts(
    converted: int | Iterable[Any] | None,
    renamed: int | Iterable[Any] | None,
    overwritten: int | Iterable[Any] | None,
    errors: int | Iterable[Any] | None,
    *,
    skipped: int | Iterable[Any] | None = 0,
) -> ConversionCounts:
    return {
        'converted': _coerce_count(converted),
        'renamed': _coerce_count(renamed),
        'overwritten': _coerce_count(overwritten),
        'errors': _coerce_count(errors),
        'skipped': _coerce_count(skipped),
    }



def _coerce_path_text(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        if not raw:
            return ''
        return os.fsdecode(raw)
    return str(value)


def _normalized_path_text(raw: object) -> str:
    return normalize_target_path_text(_coerce_path_text(raw))


def _is_windows_like_path(raw: object) -> bool:
    value = _normalized_path_text(raw).strip()
    return bool(value) and (
        (len(value) >= 2 and value[1] == ':')
        or value.startswith('\\')
        or value.startswith('//')
        or ('\\' in value)
    )


def _is_absolute_path_text(raw: object) -> bool:
    value = _normalized_path_text(raw).strip()
    if not value:
        return False
    return Path(value).is_absolute() or (
        len(value) >= 3 and value[1] == ':' and value[2] in ('\\', '/')
    ) or value.startswith('\\') or value.startswith('//')


def _normalize_path_match_key(value: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> str:
    raw = _normalized_path_text(value).strip()
    if not raw:
        return ''
    windows_like = _is_windows_like_path(raw)
    normalized = ntpath.normpath(raw) if windows_like else os.path.normpath(raw)
    return ntpath.normcase(normalized) if windows_like else os.path.normcase(normalized)


def _parent_for_path_like(value: str | bytes | os.PathLike[str] | os.PathLike[bytes]) -> Path:
    raw = _normalized_path_text(value).strip()
    if _is_windows_like_path(raw):
        return Path(ntpath.normpath(str(PureWindowsPath(raw).parent)))
    return Path(raw).parent


def resolve_open_folder_target(
    input_path: Path,
    converted_files: Sequence[str | bytes | os.PathLike[str] | os.PathLike[bytes]] | str | bytes | os.PathLike[str] | os.PathLike[bytes] | None = None,
) -> Path | None:
    if isinstance(converted_files, (str, bytes, bytearray, os.PathLike)):
        converted_items: Sequence[str | bytes | os.PathLike[str] | os.PathLike[bytes]] = [converted_files]
    else:
        converted_items = converted_files or []
    base_dir: Path | None = None
    if input_path.is_file():
        base_dir = input_path.parent
    elif input_path.is_dir():
        base_dir = input_path
    parents_by_key: dict[str, Path] = {}
    for item in converted_items:
        raw = _normalized_path_text(item).strip()
        if not raw:
            continue
        parent = _parent_for_path_like(item)
        if base_dir is not None and not _is_absolute_path_text(raw):
            if _is_windows_like_path(raw):
                rel_parts = [part for part in PureWindowsPath(str(parent)).parts if part not in ('', '.')]
                parent = base_dir.joinpath(*rel_parts) if rel_parts else base_dir
            else:
                parent = base_dir / parent
        parent = Path(ntpath.normpath(str(parent))) if _is_windows_like_path(str(parent)) else Path(os.path.normpath(str(parent)))
        key = _normalize_path_match_key(parent)
        if not key:
            continue
        parents_by_key.setdefault(key, parent)
    if len(parents_by_key) == 1:
        return next(iter(parents_by_key.values()))
    if input_path.is_file():
        return input_path.parent
    if input_path.is_dir():
        return input_path
    return None



def _coerce_error_text(value: object) -> str:
    if isinstance(value, os.PathLike):
        return os.fspath(value)
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        if not raw:
            return ''
        try:
            return raw.decode('utf-8')
        except Exception:
            return raw.decode('utf-8', errors='replace')
    return str(value)



def _has_meaningful_error_text(text: str) -> bool:
    return bool(str(text or '').strip())



def _normalize_error_items(errors: object) -> list[ConversionErrorItem]:
    if errors is None:
        return []
    if isinstance(errors, Mapping):
        normalized_item = _normalize_error_mapping_item(errors)
        return [normalized_item] if normalized_item else []
    if isinstance(errors, (int, float)):
        return [{} for _ in range(_coerce_count(errors))]
    if isinstance(errors, (str, bytes, bytearray, os.PathLike)):
        text = _coerce_error_text(errors)
        if not _has_meaningful_error_text(text):
            return []
        headline = extract_error_headline(text)
        return [{'headline': headline, 'error': text}]
    try:
        raw_items = list(errors)
    except TypeError:
        text = _coerce_error_text(errors)
        if not _has_meaningful_error_text(text):
            return []
        headline = extract_error_headline(text)
        return [{'headline': headline, 'error': text}]

    normalized: list[ConversionErrorItem] = []
    for item in raw_items:
        if item is None:
            continue
        if isinstance(item, Mapping):
            normalized_item = _normalize_error_mapping_item(item)
            if normalized_item:
                normalized.append(normalized_item)
            continue
        text = _coerce_error_text(item)
        if not _has_meaningful_error_text(text):
            continue
        normalized.append({'headline': extract_error_headline(text), 'error': text})
    return normalized



def _coerce_summary_count(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, int(value))
    if isinstance(value, float):
        return max(0, int(value)) if math.isfinite(value) else 0
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if isinstance(value, (bytes, bytearray)):
        try:
            value = bytes(value).decode('utf-8')
        except Exception:
            return 0
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return 0
        try:
            return max(0, int(normalized, 10))
        except (TypeError, ValueError, OverflowError):
            pass
        try:
            parsed = float(normalized)
            return max(0, int(parsed)) if math.isfinite(parsed) else 0
        except (TypeError, ValueError, OverflowError):
            return 0
    return _coerce_count(value)



def build_conversion_summary(
    converted_count: int,
    renamed_count: int,
    overwritten_count: int,
    errors: Iterable[ConversionErrorItem] | None,
    stopped: bool,
    *,
    skipped_count: int = 0,
    summarize_error_headlines_func: Callable[[list[ConversionErrorItem]], list[str]] | None = None,
) -> tuple[str, list[str]]:
    error_headline_summarizer = summarize_error_headlines_func or summarize_error_headlines_default
    error_items = _normalize_error_items(errors)
    error_total = len(error_items)

    converted_total = _coerce_summary_count(converted_count)
    renamed_total = _coerce_summary_count(renamed_count)
    overwritten_total = _coerce_summary_count(overwritten_count)
    skipped_total = _coerce_summary_count(skipped_count)

    summary_lines = [
        f'保存 {converted_total} 件',
        f'自動連番 {renamed_total} 件',
        f'上書き {overwritten_total} 件',
    ]
    if skipped_total:
        summary_lines.append(f'スキップ {skipped_total} 件')
    if error_total:
        summary_lines.append(f'エラー {error_total} 件')
        summary_lines.extend(error_headline_summarizer(error_items))
    if stopped:
        summary_lines.append('途中停止')

    if stopped:
        msg = f'変換を停止しました。({converted_total} 件を保存 / {error_total} 件エラー)'
    elif error_total and converted_total:
        msg = f'変換完了しました。({converted_total} 件を保存 / {error_total} 件エラー)'
    elif error_total and not converted_total:
        msg = f'変換できませんでした。({error_total} 件エラー)'
    elif skipped_total and not converted_total:
        msg = f'変換対象はありませんでした。({skipped_total} 件スキップ)'
    else:
        msg = f'変換完了しました。({converted_total} 件)'
    return msg, summary_lines



def summarize_error_headlines_default(errors: list[ConversionErrorItem]) -> list[str]:
    return summarize_error_headlines(errors)
