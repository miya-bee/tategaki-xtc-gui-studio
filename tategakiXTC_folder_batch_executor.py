from __future__ import annotations

"""Folder batch execution helpers for TategakiXTC GUI Studio.

This module is deliberately independent from Qt and from the renderer internals.
It consumes a :class:`FolderBatchPlan` and calls a converter callback for each
planned item.  The GUI worker can wire the callback to the existing single-file
conversion route later, while this module keeps batch bookkeeping testable.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from tategakiXTC_folder_batch_plan import (
    FOLDER_BATCH_STATUS_SKIP_DUPLICATE,
    FOLDER_BATCH_STATUS_SKIP_EXISTING,
    FolderBatchPlan,
    FolderBatchPlanItem,
)

FolderBatchConvertCallback = Callable[[Path, Path, FolderBatchPlanItem], object]
FolderBatchLogCallback = Callable[[str], None]
FolderBatchProgressCallback = Callable[[int, int, FolderBatchPlanItem], None]
FolderBatchCancelCallback = Callable[[], bool]


@dataclass(frozen=True)
class FolderBatchExecutionItem:
    source_path: Path
    desired_output_path: Path
    output_path: Path | None
    relative_source_path: Path
    status: str
    message: str = ''
    existing_output: bool = False
    renamed: bool = False
    overwritten: bool = False
    duplicate_in_batch: bool = False

    @property
    def success(self) -> bool:
        return self.status == 'success'

    @property
    def skipped(self) -> bool:
        return self.status.startswith('skip')

    @property
    def failed(self) -> bool:
        return self.status == 'error'


@dataclass(frozen=True)
class FolderBatchExecutionResult:
    plan: FolderBatchPlan
    items: tuple[FolderBatchExecutionItem, ...]
    stopped: bool = False

    @property
    def success_count(self) -> int:
        return sum(1 for item in self.items if item.success)

    @property
    def skipped_count(self) -> int:
        return sum(1 for item in self.items if item.skipped)

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.failed)

    @property
    def attempted_count(self) -> int:
        return self.success_count + self.failed_count

    @property
    def processed_count(self) -> int:
        return len(self.items)

    @property
    def pending_count(self) -> int:
        return max(0, self.plan.total_count - self.processed_count)

    @property
    def existing_skip_count(self) -> int:
        return sum(1 for item in self.items if item.status == FOLDER_BATCH_STATUS_SKIP_EXISTING)

    @property
    def duplicate_skip_count(self) -> int:
        return sum(1 for item in self.items if item.status == FOLDER_BATCH_STATUS_SKIP_DUPLICATE)

    @property
    def renamed_success_count(self) -> int:
        return sum(1 for item in self.items if item.success and item.renamed)

    @property
    def overwritten_success_count(self) -> int:
        return sum(1 for item in self.items if item.success and item.overwritten)

    def summary_lines(self) -> list[str]:
        lines = [
            'フォルダ一括変換が完了しました。' if not self.stopped else 'フォルダ一括変換を停止しました。',
            f'成功: {self.success_count} 件',
            f'スキップ: {self.skipped_count} 件',
            f'失敗: {self.failed_count} 件',
            f'処理済み: {self.processed_count} / {self.plan.total_count} 件',
            f'出力先: {self.plan.output_root}',
        ]
        if self.renamed_success_count:
            lines.append(f'別名で保存: {self.renamed_success_count} 件')
        if self.overwritten_success_count:
            lines.append(f'上書き保存: {self.overwritten_success_count} 件')
        skip_reasons: list[str] = []
        if self.existing_skip_count:
            skip_reasons.append(f'既存ファイル {self.existing_skip_count} 件')
        if self.duplicate_skip_count:
            skip_reasons.append(f'同名衝突 {self.duplicate_skip_count} 件')
        if skip_reasons:
            lines.append('スキップ内訳: ' + ' / '.join(skip_reasons))
        if self.stopped:
            lines.append(f'未処理: {self.pending_count} 件')
            lines.append('停止要求により、残りのファイルは処理していません。')
        if self.failed_count:
            lines.append('失敗したファイルはログ欄の [ERROR] 行を確認してください。')
        elif self.success_count:
            lines.append('出力先フォルダを確認してください。')
        return lines


def _emit_log(callback: FolderBatchLogCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)


def _emit_progress(
    callback: FolderBatchProgressCallback | None,
    log_cb: FolderBatchLogCallback | None,
    index: int,
    total: int,
    item: FolderBatchPlanItem,
) -> None:
    if callback is None:
        return
    try:
        callback(index, total, item)
    except Exception as exc:
        _emit_log(log_cb, f'[WARN] 進捗通知に失敗しました: {_safe_message(exc)}')


def _safe_message(exc: BaseException) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__


def execute_folder_batch_plan(
    plan: FolderBatchPlan,
    converter: FolderBatchConvertCallback,
    *,
    log_cb: FolderBatchLogCallback | None = None,
    progress_cb: FolderBatchProgressCallback | None = None,
    should_cancel: FolderBatchCancelCallback | None = None,
) -> FolderBatchExecutionResult:
    """Execute a folder batch plan using ``converter``.

    The converter receives ``source_path``, ``output_path`` and the plan item.
    One failed conversion does not abort the whole batch; the error is collected
    and processing continues.  A cancellation callback can stop before the next
    item starts.
    """

    result_items: list[FolderBatchExecutionItem] = []
    convert_items = tuple(item for item in plan.items if item.will_convert)
    total_convert = max(1, len(convert_items))
    convert_index = 0
    stopped = False

    for item in plan.items:
        if not item.will_convert:
            message = item.reason or 'スキップしました。'
            result_items.append(
                FolderBatchExecutionItem(
                    source_path=item.source_path,
                    desired_output_path=item.desired_output_path,
                    output_path=item.output_path,
                    relative_source_path=item.relative_source_path,
                    status=item.status,
                    message=message,
                    existing_output=item.existing_output,
                    renamed=item.renamed,
                    overwritten=item.overwritten,
                    duplicate_in_batch=item.duplicate_in_batch,
                )
            )
            _emit_log(log_cb, f'[SKIP] {item.relative_source_path} — {message}')
            continue

        if should_cancel is not None and should_cancel():
            stopped = True
            _emit_log(log_cb, '[STOP] 停止要求により、フォルダ一括変換を中断しました。')
            break

        assert item.output_path is not None
        convert_index += 1
        _emit_progress(progress_cb, log_cb, convert_index, total_convert, item)
        try:
            item.output_path.parent.mkdir(parents=True, exist_ok=True)
            converter(item.source_path, item.output_path, item)
        except Exception as exc:  # intentionally continue with the next file
            message = _safe_message(exc)
            result_items.append(
                FolderBatchExecutionItem(
                    source_path=item.source_path,
                    desired_output_path=item.desired_output_path,
                    output_path=item.output_path,
                    relative_source_path=item.relative_source_path,
                    status='error',
                    message=message,
                    existing_output=item.existing_output,
                    renamed=item.renamed,
                    overwritten=item.overwritten,
                    duplicate_in_batch=item.duplicate_in_batch,
                )
            )
            _emit_log(log_cb, f'[ERROR] {item.relative_source_path} — {message}')
            continue

        result_items.append(
            FolderBatchExecutionItem(
                source_path=item.source_path,
                desired_output_path=item.desired_output_path,
                output_path=item.output_path,
                relative_source_path=item.relative_source_path,
                status='success',
                message='変換しました。',
                existing_output=item.existing_output,
                renamed=item.renamed,
                overwritten=item.overwritten,
                duplicate_in_batch=item.duplicate_in_batch,
            )
        )
        _emit_log(log_cb, f'[OK] {item.relative_source_path} -> {item.output_path}')

    result = FolderBatchExecutionResult(plan=plan, items=tuple(result_items), stopped=stopped)
    status_label = 'STOP' if result.stopped else 'DONE'
    _emit_log(
        log_cb,
        f'[{status_label}] 成功 {result.success_count} 件 / スキップ {result.skipped_count} 件 / '
        f'失敗 {result.failed_count} 件 / 処理済み {result.processed_count} / {result.plan.total_count} 件',
    )
    return result
