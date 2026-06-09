from __future__ import annotations

"""Small pure helpers for conversion completion-card text.

These helpers keep MainWindow focused on widget wiring while preserving the
existing completion-card wording and path display behavior.
"""

import ntpath
from pathlib import Path
from typing import Mapping

import tategakiXTC_gui_results_controller as results_controller
import tategakiXTC_gui_studio_logic as studio_logic
import tategakiXTC_worker_logic as worker_logic


def completion_card_parent_texts(paths: object) -> list[str]:
    parents: list[str] = []
    seen: set[str] = set()
    for value in results_controller.coerce_result_path_list(paths):
        path_text = worker_logic._normalized_path_text(value).strip()
        if not path_text:
            continue
        try:
            if worker_logic._is_windows_like_path(path_text):
                parent = ntpath.dirname(ntpath.normpath(path_text))
            else:
                parent = str(Path(path_text).parent)
        except Exception:
            parent = ''
        parent = worker_logic._normalized_path_text(parent).strip()
        if not parent:
            continue
        key = parent.replace('\\', '/').casefold()
        if key in seen:
            continue
        seen.add(key)
        parents.append(parent)
    return parents


def completion_card_result_item_texts(
    paths: object,
    *,
    base_path: object = '',
    max_items: int = 5,
) -> list[str]:
    """Return short output-file labels for the conversion completion card."""
    normalized_paths = results_controller.coerce_result_path_list(paths)
    base_text = worker_logic._normalized_path_text(base_path).strip()
    items: list[str] = []
    for value in normalized_paths[:max(0, int(max_items))]:
        path_text = worker_logic._normalized_path_text(value).strip()
        if not path_text:
            continue
        display_text = ''
        try:
            if base_text and worker_logic._is_windows_like_path(path_text):
                path_norm = ntpath.normpath(path_text)
                base_norm = ntpath.normpath(base_text)
                rel = ntpath.relpath(path_norm, base_norm)
                if rel and rel != '.' and not rel.startswith('..'):
                    display_text = rel
            elif base_text:
                path_obj = Path(path_text)
                base_obj = Path(base_text)
                try:
                    display_text = str(path_obj.relative_to(base_obj))
                except Exception:
                    display_text = ''
        except Exception:
            display_text = ''
        if not display_text:
            display_text = studio_logic.build_result_display_name(path_text) or path_text
        items.append(display_text)
    return items


def build_conversion_completion_card_message(
    converted_files: object,
    result: Mapping[str, object] | None = None,
    *,
    ui_language: str = 'ja',
) -> str:
    """Build the conversion completion-card message text.

    The wording is intentionally kept compatible with the previous MainWindow
    method.  ``ui_language='en'`` applies the existing UI translation table.
    """
    paths = results_controller.coerce_result_path_list(converted_files)
    count = len(paths)
    result_payload = result or {}
    is_folder_batch = bool(result_payload.get('folder_batch'))
    folder_batch_stopped = bool(result_payload.get('folder_batch_stopped'))
    target_text = worker_logic._normalized_path_text(result_payload.get('open_folder_target')).strip()
    english = ui_language == 'en'
    tr = (lambda message: studio_logic.translate_ui_text(message, 'en')) if english else (lambda message: str(message))
    if count <= 0:
        if is_folder_batch and folder_batch_stopped:
            lines = [tr('フォルダ一括変換を中止しました。'), tr('保存済みファイルはありません。')]
            processed = int(result_payload.get('folder_batch_processed_count') or 0)
            total = int(result_payload.get('folder_batch_total_count') or 0)
            pending = int(result_payload.get('folder_batch_pending_count') or 0)
            if total > 0:
                lines.append(tr(f'処理済み: {processed} / {total} 件'))
            if pending > 0:
                lines.append(tr(f'未処理: {pending} 件'))
            if target_text:
                lines.append(tr(f'出力先: {target_text}'))
            lines.append(tr('停止要求により、以降の未処理ファイルは変換していません。'))
            lines.append(tr('詳細は左下の「変換結果」タブにも記録しています。'))
            return '\n'.join(lines)
        if bool(result_payload.get('stopped')):
            lines = [tr('変換を中止しました。'), tr('保存済みファイルはありません。')]
            if target_text:
                lines.append(tr(f'出力先: {target_text}'))
            lines.append(tr('停止要求により、変換結果は保存されませんでした。'))
            lines.append(tr('詳細は左下の「ログ」タブにも記録しています。'))
            return '\n'.join(lines)
        return ''
    parents = completion_card_parent_texts(paths)
    destination = ''
    if len(parents) <= 1:
        destination = parents[0] if parents else target_text
    elif target_text:
        destination = target_text

    if count == 1:
        filename = studio_logic.build_result_display_name(paths[0]) or ('1 file' if english else '1件')
        if is_folder_batch and folder_batch_stopped:
            lines = [tr('フォルダ一括変換を中止しました。'), tr(f'保存済み: {filename}')]
        else:
            lines = [tr(f'保存しました: {filename}')]
        if destination:
            lines.append(tr(f'保存先: {destination}'))
        lines.append(tr('保存先を開く場合は、下の［保存先を開く］を押してください。'))
        lines.append(tr('詳細は左下の「変換結果」タブにも記録しています。'))
        return '\n'.join(lines)

    if is_folder_batch and folder_batch_stopped:
        lines = [tr('フォルダ一括変換を中止しました。'), tr(f'保存済み: {count}件')]
        processed = int(result_payload.get('folder_batch_processed_count') or 0)
        total = int(result_payload.get('folder_batch_total_count') or 0)
        pending = int(result_payload.get('folder_batch_pending_count') or 0)
        if total > 0:
            lines.append(tr(f'処理済み: {processed} / {total} 件'))
        if pending > 0:
            lines.append(tr(f'未処理: {pending} 件'))
    else:
        lines = [tr(f'保存しました: {count}件')]
    if len(parents) <= 1:
        if destination:
            lines.append(tr(f'保存先: {destination}'))
    else:
        lines.append(tr(f'保存先: 複数フォルダ（{len(parents)}か所）'))
        if target_text:
            lines.append(tr(f'基準フォルダ: {target_text}'))
        lines.append(tr('サブフォルダ構造を保持して保存しました。'))

    lines.append(tr('出力ファイル:'))
    item_base = target_text if len(parents) > 1 else destination
    item_texts = completion_card_result_item_texts(paths, base_path=item_base, max_items=5)
    for index, item_text in enumerate(item_texts, start=1):
        lines.append(f'{index}. {item_text}')
    remaining = count - len(item_texts)
    if remaining > 0:
        lines.append(tr(f'…ほか{remaining}件'))
    lines.append(tr('保存先を開く場合は、下の［保存先を開く］を押してください。'))
    lines.append(tr('詳細は左下の「変換結果」タブにも記録しています。'))
    return '\n'.join(lines)


__all__ = [
    'build_conversion_completion_card_message',
    'completion_card_parent_texts',
    'completion_card_result_item_texts',
]
