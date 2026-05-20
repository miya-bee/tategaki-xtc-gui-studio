from __future__ import annotations

"""Results-view orchestration helpers for the GUI layer.

This module prepares normalized results list state and selection decisions
without depending on Qt widgets so MainWindow can stay thinner while behavior
remains regression-tested.
"""

from pathlib import Path
import os
import ntpath
import re
from typing import Any, Iterable, Sequence

import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_worker_logic as worker_logic


def _iter_result_like_items(value: object) -> Iterable[object]:
    if value is None:
        return
    if isinstance(value, (str, bytes, bytearray, os.PathLike)):
        yield value
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _iter_result_like_items(nested)
        return
    try:
        iterator = iter(value)  # type: ignore[arg-type]
    except TypeError:
        yield value
        return
    for item in iterator:
        yield from _iter_result_like_items(item)



def coerce_result_path_list(value: object) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in _iter_result_like_items(value):
        raw = worker_logic._normalized_path_text(item).strip()
        if not raw:
            continue
        identity_key = normalize_results_path_key(raw) or raw
        if identity_key in seen:
            continue
        seen.add(identity_key)
        normalized.append(raw)
    return normalized



def _normalize_summary_line_item(item: object) -> list[str]:
    if item is None:
        return []
    if isinstance(item, dict):
        lines: list[str] = []
        for value in item.values():
            lines.extend(_normalize_summary_line_item(value))
        return lines
    if isinstance(item, (list, tuple, set, frozenset)):
        lines = []
        for nested in item:
            lines.extend(_normalize_summary_line_item(nested))
        return lines
    if isinstance(item, (bytes, bytearray)):
        text = bytes(item).decode('utf-8', errors='replace')
    elif isinstance(item, str):
        text = item
    else:
        return []
    stripped = text.strip()
    return [stripped] if stripped else []



def coerce_summary_line_list(value: object) -> list[str]:
    normalized: list[str] = []
    for item in _iter_result_like_items(value):
        normalized.extend(_normalize_summary_line_item(item))
    return normalized



def _result_label_candidates(raw: object) -> list[str]:
    path_text = worker_logic._normalized_path_text(raw).strip()
    if not path_text:
        return ['']
    base_label = studio_logic.build_result_display_name(path_text)
    windows_like = worker_logic._is_windows_like_path(path_text)
    normalized = ntpath.normpath(path_text) if windows_like else os.path.normpath(path_text)
    if normalized in {'', '.'}:
        return [base_label or path_text, path_text]
    drive, tail = ntpath.splitdrive(normalized) if windows_like else ('', normalized)
    parts = [part for part in re.split(r'[\\/]+', tail) if part and part not in {'.'}]
    candidates: list[str] = []
    if base_label:
        candidates.append(base_label)
    if parts:
        for depth in range(2, len(parts) + 1):
            candidate = '/'.join(parts[-depth:])
            if candidate and candidate not in candidates:
                candidates.append(candidate)
    raw_candidate = f'{drive}{tail}' if drive else normalized
    if raw_candidate and raw_candidate not in candidates:
        candidates.append(raw_candidate)
    if path_text not in candidates:
        candidates.append(path_text)
    return candidates or [path_text]



def build_results_entries(paths: object) -> list[tuple[str, str]]:
    raw_paths = coerce_result_path_list(paths)
    if not raw_paths:
        return []
    candidate_lists = [_result_label_candidates(raw) for raw in raw_paths]
    choice_indexes = [0 for _ in candidate_lists]
    resolved_labels = [candidates[0] if candidates else '' for candidates in candidate_lists]
    for index, label in enumerate(list(resolved_labels)):
        if not label:
            resolved_labels[index] = worker_logic._normalized_path_text(raw_paths[index]).strip()

    while True:
        duplicate_counts: dict[str, int] = {}
        for label in resolved_labels:
            duplicate_counts[label] = duplicate_counts.get(label, 0) + 1
        duplicate_indexes = [index for index, label in enumerate(resolved_labels) if duplicate_counts.get(label, 0) > 1]
        if not duplicate_indexes:
            break
        changed = False
        for index in duplicate_indexes:
            candidates = candidate_lists[index]
            next_index = min(choice_indexes[index] + 1, len(candidates) - 1)
            if next_index == choice_indexes[index]:
                continue
            choice_indexes[index] = next_index
            resolved_labels[index] = candidates[next_index]
            changed = True
        if not changed:
            break

    remaining_counts: dict[str, int] = {}
    for label in resolved_labels:
        remaining_counts[label] = remaining_counts.get(label, 0) + 1
    for index, label in enumerate(list(resolved_labels)):
        if remaining_counts.get(label, 0) > 1 or not label:
            resolved_labels[index] = worker_logic._normalized_path_text(raw_paths[index]).strip()
    return list(zip(resolved_labels, raw_paths))




def _result_parent_display_text(raw: object) -> str:
    path_text = worker_logic._normalized_path_text(raw).strip()
    if not path_text:
        return ''
    try:
        if worker_logic._is_windows_like_path(path_text):
            parent = ntpath.dirname(ntpath.normpath(path_text))
            return parent or ''
        return str(Path(path_text).parent) if str(Path(path_text).parent) != '.' else ''
    except Exception:
        return ''


def _unique_result_parent_display_texts(paths: Sequence[object]) -> list[str]:
    parents: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        parent = _result_parent_display_text(raw).strip()
        if not parent:
            continue
        key = normalize_results_path_key(parent) or parent.casefold()
        if key in seen:
            continue
        seen.add(key)
        parents.append(parent)
    return parents


def build_conversion_completion_guidance_lines(
    paths: object,
    *,
    open_folder_target: object = '',
    stopped: object = False,
) -> list[str]:
    """Return user-facing completion guidance for converted result paths.

    The normal summary lines say how many files were saved.  These lines add the
    post-conversion orientation: where the files are, how to inspect them, and
    what to do next.  Keep this helper Qt-free so single-file, folder, and
    subfolder-preserving cases can be regression-tested cheaply.
    """

    raw_paths = coerce_result_path_list(paths)
    if not raw_paths:
        if bool(stopped):
            return ['確認: 途中停止のため保存ファイルはありません。ログ欄を確認してください。']
        return []

    parents = _unique_result_parent_display_texts(raw_paths)
    target_text = worker_logic._normalized_path_text(open_folder_target).strip()
    lines: list[str] = ['【変換完了】保存結果を確認できます。']
    count = len(raw_paths)
    if count == 1:
        lines.append('種類: 単独ファイル変換')
        display_name = studio_logic.build_result_display_name(raw_paths[0])
        if display_name:
            lines.append(f'出力ファイル: {display_name}')
        destination = parents[0] if parents else target_text
        if destination:
            lines.append(f'保存先: {destination}')
    else:
        lines.append(f'保存件数: {count}件')
        if len(parents) == 1:
            lines.append('種類: 複数ファイル変換')
            lines.append(f'保存先: {parents[0]}')
            lines.append('確認対象: 下の一覧からファイルを選べます。')
        else:
            lines.append('種類: サブフォルダ込み一括変換')
            lines.append(f'保存先: 複数フォルダ（{len(parents)}か所）')
            if target_text:
                lines.append(f'基準フォルダ: {target_text}')
            lines.append('確認対象: フォルダ構造を保った保存結果を、下の一覧から選べます。')
    lines.append('操作: ［保存先を開く］で出力フォルダを開けます。')
    lines.append('操作: 一覧のファイルを選び［実機ビューで確認］またはダブルクリックで確認できます。')
    return studio_logic.merge_unique_message_values([], lines)


def build_completion_summary_text(lines: object, entry_count: int = 0) -> str:
    normalized = coerce_summary_line_list(lines)
    if not normalized and entry_count > 0:
        normalized = ['【変換完了】保存結果を確認できます。', f'保存ファイル: {entry_count} 件']
    if not normalized:
        return ''
    return '\n'.join(normalized)

def build_results_view_state(paths: object, summary_lines: object = None) -> dict[str, Any]:
    entries = build_results_entries(paths)
    normalized_summary_lines = coerce_summary_line_list(summary_lines)
    return {
        'entries': entries,
        'summary_text': studio_logic.build_results_summary_message(normalized_summary_lines, len(entries)),
        'initial_index': 0 if entries else None,
    }





def build_results_apply_context(paths: object, summary_lines: object = None) -> dict[str, Any]:
    state = build_results_view_state(paths, summary_lines)
    entries = list(state.get('entries') or [])
    initial_index = studio_logic.payload_optional_int_value(state, 'initial_index')
    return {
        'entries': entries,
        'summary_text': state.get('summary_text', ''),
        'initial_index': initial_index,
        'has_entries': bool(entries),
    }


def build_results_selection_context(target_path: object, candidate_paths: Sequence[object]) -> dict[str, Any]:
    matched_index = find_matching_loaded_path_index(target_path, candidate_paths)
    return {
        'matched_index': matched_index,
        'clear_selection': matched_index is None,
    }


def build_results_clear_selection_context() -> dict[str, Any]:
    return {
        'matched_index': None,
        'clear_selection': True,
    }


def build_loaded_xtc_path_success_context(
    path: object,
    display_name: object,
    candidate_paths: Sequence[object],
) -> dict[str, Any]:
    path_text = worker_logic._normalized_path_text(path).strip()
    label_text = worker_logic._normalized_path_text(display_name).strip()
    if not label_text and path_text:
        label_text = studio_logic.build_result_display_name(path_text)
    log_message = f'XTC/XTCH読込: {path_text}' if path_text else ''
    return {
        'device_view_source': 'xtc',
        'path_text': path_text,
        'display_name': label_text,
        'log_message': log_message,
        'view_mode': 'device',
        'selection_context': build_results_selection_context(path_text, candidate_paths),
        'safe_view_mode': False,
    }


def build_loaded_xtc_bytes_success_context(display_name: object = 'メモリ上のデータ') -> dict[str, Any]:
    label_text = worker_logic._normalized_path_text(display_name).strip() or 'メモリ上のデータ'
    return {
        'device_view_source': 'xtc',
        'path_text': '',
        'display_name': label_text,
        'log_message': '',
        'view_mode': 'device',
        'selection_context': build_results_clear_selection_context(),
        'safe_view_mode': True,
    }


def build_loaded_xtc_failure_context() -> dict[str, Any]:
    return {
        'clear_loaded_state': True,
        'selection_context': build_results_clear_selection_context(),
    }


def build_results_load_context(
    *,
    selected_indexes: Sequence[object],
    current_index: object,
    item_paths: Sequence[object],
    loaded_path: object = None,
) -> dict[str, Any]:
    item_path_list = list(item_paths)
    preferred_index = resolve_preferred_results_index(
        selected_indexes=selected_indexes,
        current_index=current_index,
        item_count=len(item_path_list),
    )
    if preferred_index is None:
        preferred_index = find_matching_loaded_path_index(loaded_path, item_path_list)
    resolved_path = None
    if preferred_index is not None and 0 <= preferred_index < len(item_path_list):
        resolved_path = item_path_list[preferred_index]
    path_text = worker_logic._normalized_path_text(resolved_path).strip()
    return {
        'preferred_index': preferred_index,
        'resolved_path': resolved_path,
        'has_selection': preferred_index is not None,
        'has_path': bool(path_text),
        'should_warn_no_selection': preferred_index is None,
        'should_warn_missing_path': preferred_index is not None and not path_text,
    }


def build_fallback_loaded_result_load_context(
    loaded_path: object,
    item_paths: Sequence[object],
) -> dict[str, Any]:
    """Return a best-effort result-load context for the currently loaded XTC path."""
    loaded_path_text = worker_logic._normalized_path_text(loaded_path).strip()
    if not loaded_path_text:
        return {}
    item_path_list = list(item_paths)
    matched_index = find_matching_loaded_path_index(loaded_path_text, item_path_list)
    if matched_index is None:
        return {}
    resolved_path = None
    if 0 <= matched_index < len(item_path_list):
        resolved_path = item_path_list[matched_index]
    path_text = worker_logic._normalized_path_text(resolved_path).strip()
    return {
        'preferred_index': matched_index,
        'resolved_path': resolved_path,
        'has_path': bool(path_text),
    }


def normalize_results_path_key(path: object) -> str:
    raw = worker_logic._normalized_path_text(path).strip()
    if not raw:
        return ''
    windows_like = worker_logic._is_windows_like_path(raw)
    try:
        normalized = raw if windows_like else str(Path(raw).resolve())
    except Exception:
        normalized = raw
    if windows_like:
        normalized = ntpath.normcase(ntpath.normpath(normalized)).replace('/', '\\')
    else:
        normalized = os.path.normcase(os.path.normpath(normalized))
    return normalized



def find_matching_loaded_path_index(target_path: object, candidate_paths: Sequence[object]) -> int | None:
    target_key = normalize_results_path_key(target_path)
    candidate_keys = [normalize_results_path_key(path) for path in candidate_paths]
    return studio_logic.find_matching_result_index(target_key, candidate_keys)



def resolve_preferred_results_index(
    *,
    selected_indexes: Sequence[object],
    current_index: object,
    item_count: object,
) -> int | None:
    return studio_logic.resolve_preferred_result_index(
        selected_indexes=selected_indexes,
        current_index=current_index,
        item_count=item_count,
    )
