"""
tategakiXTC_gui_core_paths.py — 変換対象列挙 / 出力パス helper

`tategakiXTC_gui_core.py` から分離した、変換対象の列挙・出力ファイル名生成・
同名衝突解決の実装。互換性維持のため、gui_core 側の re-export / 既存テストの
monkey patch を各入口で同期する。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals'}
_CORE_SYNC_VERSION = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch を path 実装へ反映する。"""
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
# --- 変換対象 / 出力パス utility ---
# ==========================================

OUTPUT_FLAT_SEPARATOR = '~~'


def _natural_sort_key(path_like: Any) -> list[tuple[int, object]]:
    _refresh_core_globals()
    text = str(path_like).replace('\\', '/')
    parts = re.split(r'(\d+)', text)
    key: list[tuple[int, object]] = []
    for part in parts:
        if part == '':
            continue
        if part.isdigit():
            key.append((0, int(part)))
        else:
            key.append((1, part.casefold()))
    return key


def _encode_output_name_part(value: object) -> str:
    _refresh_core_globals()
    text = str(value or '')
    return text.replace('_', '_u').replace('~', '_t').strip()


def _build_flat_output_stem_from_relative(relative_path: str | Path) -> str:
    _refresh_core_globals()
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
    _refresh_core_globals()
    path = Path(path)
    encoded_stem = _encode_output_name_part(path.stem) or 'output'
    try:
        digest_source = str(path.resolve())
    except Exception:
        digest_source = str(path)
    digest = hashlib.sha1(digest_source.encode('utf-8', errors='ignore')).hexdigest()[:8]
    return f'_outside_{encoded_stem}_{digest}'


def iter_conversion_targets(target_path: PathLike, recursive: bool = True) -> list[Path]:
    _refresh_core_globals()
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
    _refresh_core_globals()
    path = Path(path)
    return path.suffix.lower() in {'.xtc', '.xtch'}


def _normalize_output_format(value: object) -> str:
    _refresh_core_globals()
    fmt = str(value or 'xtc').strip().lower()
    return 'xtch' if fmt == 'xtch' else 'xtc'


def get_output_path_for_target(path: PathLike, output_format: str = 'xtc', output_root: PathLike | None = None) -> Path | None:
    _refresh_core_globals()
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
    _refresh_core_globals()
    path = Path(path)
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    idx = 1
    while True:
        candidate = path.with_name(f'{stem}({idx}){suffix}')
        if not candidate.exists():
            return candidate
        idx += 1


def resolve_output_path_with_conflict(path: PathLike, strategy: str = 'rename') -> tuple[Path, ConflictPlan]:
    _refresh_core_globals()
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
    _refresh_core_globals()
    conflicts: list[tuple[PathLike, Path]] = []
    for path in targets:
        out_path = get_output_path_for_target(path, output_format)
        if out_path and out_path.exists():
            conflicts.append((path, out_path))
    return conflicts
