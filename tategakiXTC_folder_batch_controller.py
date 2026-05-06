from __future__ import annotations

"""Controller helpers for wiring folder batch conversion into the GUI.

This module keeps the actual MainWindow integration small.  MainWindow should
only need to add a button, call ``open_folder_batch_dialog_and_execute(...)``,
and provide a single-file converter callback that uses the existing conversion
route.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Protocol

from tategakiXTC_folder_batch_executor import (
    FolderBatchCancelCallback,
    FolderBatchConvertCallback,
    FolderBatchExecutionResult,
    FolderBatchLogCallback,
    FolderBatchProgressCallback,
    execute_folder_batch_plan,
)
from tategakiXTC_folder_batch_plan import (
    FolderBatchPlan,
    FolderBatchPlanItem,
    describe_folder_batch_no_work as describe_folder_batch_no_work_from_plan,
    describe_folder_batch_partial_skip_notice as describe_folder_batch_partial_skip_notice_from_plan,
    summarize_folder_batch_plan,
)
from tategakiXTC_folder_batch_settings import (
    FolderBatchDialogDefaults,
    load_folder_batch_dialog_defaults,
    save_folder_batch_result_defaults,
)

FolderBatchInformationCallback = Callable[[str, str], None]
FolderBatchWarningCallback = Callable[[str, str], None]
FolderBatchBeforeExecuteCallback = Callable[[FolderBatchPlan], None]
FolderBatchAfterExecuteCallback = Callable[[FolderBatchExecutionResult | None], None]
OutputFormatGetter = Callable[[], str]
MissingDependencyGetter = Callable[[Iterable[str]], list[dict[str, object]]]


class FolderBatchDialogProtocol(Protocol):
    def exec(self) -> int: ...
    def result_options(self) -> object | None: ...


@dataclass(frozen=True)
class FolderBatchControllerRun:
    dialog_result: object
    execution_result: FolderBatchExecutionResult


def _safe_dependency_text(item: dict[str, object], key: str) -> str:
    return str(item.get(key, '') or '').strip()


def default_missing_dependencies_for_suffixes(suffixes: Iterable[str]) -> list[dict[str, object]]:
    """Return missing optional dependencies for the given suffixes.

    The import is kept lazy so the controller remains cheap to load in tests and
    so callers can inject a fake checker without importing the full converter.
    """

    import tategakiXTC_gui_core as core

    return list(core.get_missing_dependencies_for_suffixes(suffixes))


def folder_batch_convert_suffixes(plan: FolderBatchPlan) -> tuple[str, ...]:
    """Return deterministic suffixes for items that will actually convert."""

    suffixes = {
        item.source_path.suffix.lower()
        for item in getattr(plan, 'items', ())
        if getattr(item, 'will_convert', False) and str(item.source_path.suffix or '').strip()
    }
    return tuple(sorted(suffixes))


def missing_dependencies_for_folder_batch_plan(
    plan: FolderBatchPlan,
    getter: MissingDependencyGetter | None = None,
) -> list[dict[str, object]]:
    """Check optional dependencies needed by the files that will be converted."""

    suffixes = folder_batch_convert_suffixes(plan)
    if not suffixes:
        return []
    checker = getter or default_missing_dependencies_for_suffixes
    try:
        return list(checker(suffixes))
    except Exception as exc:
        # Dependency diagnostics should never crash the dialog path.  If the
        # checker itself fails, let the normal conversion route report the
        # concrete error per file instead of blocking the user with a vague one.
        return []


def format_folder_batch_missing_dependency_message(missing_items: Iterable[dict[str, object]]) -> str:
    """Create a user-facing preflight warning for missing optional packages."""

    items = list(missing_items)
    lines = [
        'EPUB などの変換に必要な追加ライブラリが不足しています。',
        '安全のため、フォルダ一括変換は開始していません。',
        'TXT / Markdown / 画像だけを変換する場合は、EPUB などを除外して再実行できます。',
        '',
        '不足しているライブラリ:',
    ]
    packages: list[str] = []
    seen_packages: set[str] = set()
    purposes: list[str] = []
    seen_purposes: set[str] = set()
    for item in items:
        label = _safe_dependency_text(item, 'label') or _safe_dependency_text(item, 'package') or '不明なライブラリ'
        purpose = _safe_dependency_text(item, 'purpose')
        package = _safe_dependency_text(item, 'package') or label
        if purpose:
            lines.append(f'- {label}（{purpose}）')
            if purpose not in seen_purposes:
                purposes.append(purpose)
                seen_purposes.add(purpose)
        else:
            lines.append(f'- {label}')
        if package and package not in seen_packages:
            packages.append(package)
            seen_packages.add(package)
    if purposes:
        lines.extend([
            '',
            '影響する変換:',
            '- ' + ' / '.join(purposes),
        ])
    if packages:
        lines.extend([
            '',
            '対応方法:',
            '1. アプリを終了する',
            '2. 展開先フォルダの install_requirements.bat を実行する',
            '3. うまくいかない場合は、コマンドプロンプトで以下を実行する',
            '',
            'py -3.10 -m pip install -r requirements.txt',
            '',
            '不足分だけ入れる場合:',
            f'py -3.10 -m pip install {" ".join(packages)}',
        ])
    lines.extend([
        '',
        '補足: ebooklib / beautifulsoup4 は EPUB の読み込みと本文解析に使います。',
        'このままでは対象ファイルを変換できないため、処理は開始していません。',
    ])
    return '\n'.join(lines)


def normalize_output_format_from_getter(getter: OutputFormatGetter | None, default: str = 'xtc') -> str:
    if getter is None:
        return default
    try:
        text = str(getter() or '').strip().lower().lstrip('.')
    except Exception:
        return default
    return text if text in {'xtc', 'xtch'} else default


def folder_batch_dialog_kwargs(
    defaults: FolderBatchDialogDefaults,
    *,
    output_format: str,
    supported_suffixes: Iterable[str] | None = None,
) -> dict[str, object]:
    kwargs: dict[str, object] = {
        'output_format': output_format,
        'input_root': defaults.input_root,
        'output_root': defaults.output_root,
        'include_subfolders': defaults.include_subfolders,
        'preserve_structure': defaults.preserve_structure,
        'existing_policy': defaults.existing_policy,
    }
    if supported_suffixes is not None:
        kwargs['supported_suffixes'] = tuple(supported_suffixes)
    return kwargs




def describe_folder_batch_no_work(plan: FolderBatchPlan) -> str:
    """Return a user-facing explanation when a plan has no files to convert."""

    return describe_folder_batch_no_work_from_plan(plan)




def describe_folder_batch_partial_skip_notice(plan: FolderBatchPlan) -> str:
    """Return a user-facing explanation when a plan has both convert and skip items."""

    return describe_folder_batch_partial_skip_notice_from_plan(plan)


def folder_batch_plan_can_execute(plan: FolderBatchPlan | object) -> bool:
    """Return True only when a dialog plan contains at least one convert item."""

    try:
        return int(getattr(plan, 'convert_count', 0)) > 0
    except Exception:
        return False


def _safe_log_callback_warning(
    log_cb: FolderBatchLogCallback | None,
    label: str,
    exc: BaseException,
) -> None:
    if log_cb is None:
        return
    try:
        text = str(exc).strip() or exc.__class__.__name__
        log_cb(f'[WARN] {label}に失敗しました: {text}')
    except Exception:
        pass


def run_folder_batch_plan_with_callbacks(
    plan: FolderBatchPlan,
    converter: FolderBatchConvertCallback,
    *,
    log_cb: FolderBatchLogCallback | None = None,
    progress_cb: FolderBatchProgressCallback | None = None,
    should_cancel: FolderBatchCancelCallback | None = None,
    information_cb: FolderBatchInformationCallback | None = None,
    before_execute_cb: FolderBatchBeforeExecuteCallback | None = None,
    after_execute_cb: FolderBatchAfterExecuteCallback | None = None,
) -> FolderBatchExecutionResult:
    if log_cb is not None:
        for line in summarize_folder_batch_plan(plan):
            log_cb(f'[PLAN] {line}')
    if before_execute_cb is not None:
        try:
            before_execute_cb(plan)
        except Exception as exc:
            _safe_log_callback_warning(log_cb, '実行前UI更新', exc)
    result: FolderBatchExecutionResult | None = None
    try:
        result = execute_folder_batch_plan(
            plan,
            converter,
            log_cb=log_cb,
            progress_cb=progress_cb,
            should_cancel=should_cancel,
        )
    finally:
        if after_execute_cb is not None:
            try:
                after_execute_cb(result)
            except Exception as exc:
                _safe_log_callback_warning(log_cb, '実行後UI更新', exc)
    if information_cb is not None:
        try:
            information_cb('フォルダ一括変換', '\n'.join(result.summary_lines()))
        except Exception as exc:
            _safe_log_callback_warning(log_cb, '完了通知', exc)
    return result


def open_folder_batch_dialog_and_execute(
    parent: object,
    *,
    settings: object,
    converter: FolderBatchConvertCallback,
    output_format_getter: OutputFormatGetter | None = None,
    supported_suffixes: Iterable[str] | None = None,
    log_cb: FolderBatchLogCallback | None = None,
    progress_cb: FolderBatchProgressCallback | None = None,
    should_cancel: FolderBatchCancelCallback | None = None,
    information_cb: FolderBatchInformationCallback | None = None,
    warning_cb: FolderBatchWarningCallback | None = None,
    missing_dependency_getter: MissingDependencyGetter | None = None,
    before_execute_cb: FolderBatchBeforeExecuteCallback | None = None,
    after_execute_cb: FolderBatchAfterExecuteCallback | None = None,
    dialog_cls: Callable[..., FolderBatchDialogProtocol] | None = None,
    accepted_value: int = 1,
) -> FolderBatchControllerRun | None:
    """Open the folder-batch dialog and execute the accepted plan.

    ``dialog_cls`` exists to keep tests Qt-free.  Production code can omit it;
    the real ``FolderBatchDialog`` is imported lazily only when needed.
    """

    defaults = load_folder_batch_dialog_defaults(settings)
    output_format = normalize_output_format_from_getter(output_format_getter)
    if dialog_cls is None:
        from tategakiXTC_folder_batch_dialog import FolderBatchDialog

        dialog_cls = FolderBatchDialog
    dialog = dialog_cls(
        parent,
        **folder_batch_dialog_kwargs(
            defaults,
            output_format=output_format,
            supported_suffixes=supported_suffixes,
        ),
    )
    try:
        reply = dialog.exec()
    except Exception as exc:
        if warning_cb is not None:
            warning_cb('フォルダ一括変換', f'ダイアログを開けませんでした: {exc}')
        return None
    if reply != accepted_value:
        return None
    dialog_result = dialog.result_options()
    if dialog_result is None:
        if warning_cb is not None:
            warning_cb('フォルダ一括変換', '変換条件を取得できませんでした。')
        return None
    plan = getattr(dialog_result, 'plan', None)
    if plan is None:
        if warning_cb is not None:
            warning_cb('フォルダ一括変換', '変換計画を取得できませんでした。')
        return None
    if not folder_batch_plan_can_execute(plan):
        if warning_cb is not None:
            warning_cb('フォルダ一括変換', describe_folder_batch_no_work(plan))
        return None
    missing_dependencies = missing_dependencies_for_folder_batch_plan(
        plan,
        missing_dependency_getter,
    )
    if missing_dependencies:
        if warning_cb is not None:
            warning_cb(
                'フォルダ一括変換',
                format_folder_batch_missing_dependency_message(missing_dependencies),
            )
        return None
    try:
        save_folder_batch_result_defaults(settings, dialog_result)
    except Exception as exc:
        if warning_cb is not None:
            warning_cb('フォルダ一括変換', f'前回設定の保存に失敗しました。変換は続行します: {exc}')
    try:
        execution_result = run_folder_batch_plan_with_callbacks(
            plan,
            converter,
            log_cb=log_cb,
            progress_cb=progress_cb,
            should_cancel=should_cancel,
            information_cb=information_cb,
            before_execute_cb=before_execute_cb,
            after_execute_cb=after_execute_cb,
        )
    except Exception as exc:
        if warning_cb is not None:
            warning_cb('フォルダ一括変換', f'フォルダ一括変換を実行できませんでした: {exc}')
        return None
    return FolderBatchControllerRun(
        dialog_result=dialog_result,
        execution_result=execution_result,
    )


def make_dry_run_converter(log_cb: FolderBatchLogCallback | None = None) -> FolderBatchConvertCallback:
    """Return a safe converter that only writes a small marker file.

    This is useful for GUI smoke tests before the real worker route is wired in.
    Do not use this converter for the final public build.
    """

    def _convert(source_path: Path, output_path: Path, item: FolderBatchPlanItem) -> None:
        output_path.write_text(f'DRY RUN: {source_path}\n', encoding='utf-8')
        if log_cb is not None:
            log_cb(f'[DRY-RUN] {item.relative_source_path} -> {output_path}')

    return _convert
