from __future__ import annotations

"""tategakiXTC_gui_studio_worker.py — GUI conversion worker layer.

Qt signal based worker and thin GUI-facing conversion helpers split from
``tategakiXTC_gui_studio.py``.  The entry module re-exports these names to keep
existing imports and monkey patches compatible.
"""

import logging
import math
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Callable, Mapping, cast

from PySide6.QtCore import QObject, Signal

import tategakiXTC_gui_core as core
import tategakiXTC_worker_logic as worker_logic
from tategakiXTC_gui_core import ConversionArgs
from tategakiXTC_gui_studio_constants import (
    FONT_REQUIRED_SUFFIXES,
    SUPPORTED_INPUT_SUFFIXES,
    TEXT_OR_MARKDOWN_LABEL,
)

APP_LOGGER_NAME = 'tategaki_xtc'
APP_LOGGER = logging.getLogger(APP_LOGGER_NAME)
WorkerConversionSettings = worker_logic.WorkerConversionSettings
ConversionErrorItem = worker_logic.ConversionErrorItem
OutputPlan = dict[str, object]
ConversionResult = dict[str, object]


def _coerce_ui_message_text(value: object, default: str = '') -> str:
    text = worker_logic._coerce_path_text(value)
    return text if text.strip() else default


def _entry_module_attr(name: str, fallback: object) -> object:
    entry_module = sys.modules.get('tategakiXTC_gui_studio')
    if entry_module is None:
        return fallback
    try:
        return getattr(entry_module, name)
    except Exception:
        return fallback


def _coerce_progress_number(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else int(default)
    if isinstance(value, (bytes, bytearray)):
        value = worker_logic._coerce_path_text(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return int(default)
        try:
            return int(normalized, 10)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = float(normalized)
            except (TypeError, ValueError, OverflowError):
                return int(default)
            return int(parsed) if math.isfinite(parsed) else int(default)
    return int(default)

def _write_output_bytes_atomic(output_path: Path, blob: bytes) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_handle = tempfile.NamedTemporaryFile(prefix=f'{output_path.stem}_', suffix='.partial', dir=str(output_path.parent), delete=False)
    tmp_path = Path(tmp_handle.name)
    try:
        with tmp_handle:
            tmp_handle.write(blob)
            tmp_handle.flush()
            os.fsync(tmp_handle.fileno())
        os.replace(tmp_path, output_path)
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise
    return output_path


def _process_single_image_file(
    path: Path,
    font_value: str,
    args: ConversionArgs,
    output_path: Path,
    should_cancel: Callable[[], bool] | None = None,
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> Path:
    if progress_cb is not None:
        progress_cb(0, 1, '画像を読み込み中…')
    page_blob = core.process_image_data(path, args, should_cancel=should_cancel)
    if page_blob is None:
        raise RuntimeError('変換データがありません。')
    # ``process_image_data`` returns one XTC-family page blob (XTG/XTH), not
    # a readable XTC/XTCH container.  Single-file image conversion therefore
    # has to wrap the page blob with the normal container writer before saving.
    core.build_xtc(
        [bytes(page_blob)],
        output_path,
        int(getattr(args, 'width')),
        int(getattr(args, 'height')),
        str(getattr(args, 'output_format', 'xtc')),
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )
    if progress_cb is not None:
        progress_cb(1, 1, '画像変換が完了しました。')
    return output_path


PROCESSOR_BY_SUFFIX = {
    '.epub': core.process_epub,
    '.txt': core.process_text_file,
    '.md': core.process_markdown_file,
    '.markdown': core.process_markdown_file,
    '.png': _process_single_image_file,
    '.jpg': _process_single_image_file,
    '.jpeg': _process_single_image_file,
    '.webp': _process_single_image_file,
}


def _format_missing_dependency_message(missing_items: list[dict[str, object]]) -> str:
    lines = ['この操作に必要なライブラリが不足しています。', '']
    for item in missing_items:
        purpose = str(item.get('purpose', '')).strip()
        label = str(item.get('label', '')).strip() or str(item.get('package', '')).strip()
        if purpose:
            lines.append(f'- {label}（{purpose}）')
        else:
            lines.append(f'- {label}')
    install_packages = ' '.join(
        str(item.get('package', '')).strip() or str(item.get('label', '')).strip()
        for item in missing_items
    ).strip()
    if install_packages:
        lines.extend(['', 'インストール例:', f'pip install {install_packages}', 'または', 'pip install -r requirements.txt'])
    return '\n'.join(lines)


def _summarize_error_headlines(errors: list[ConversionErrorItem]) -> list[str]:
    return worker_logic.summarize_error_headlines(errors)


# ─────────────────────────────────────────────────────────
# データクラス
# ─────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────
# 変換ワーカー
# ─────────────────────────────────────────────────────────

def build_conversion_args(cfg: WorkerConversionSettings) -> ConversionArgs:
    return worker_logic.build_conversion_args(cfg)


def resolve_supported_conversion_targets(tp: Path) -> list[Path]:
    return worker_logic.resolve_supported_conversion_targets(tp, SUPPORTED_INPUT_SUFFIXES)


def sanitize_output_stem(name: str) -> str:
    return worker_logic.sanitize_output_stem(name)


def plan_output_path_for_target(
    path: Path,
    args: ConversionArgs,
    requested_name: str,
    supported_count: int,
    conflict_strategy: str,
    output_root: Path | None = None,
    apply_conflict_strategy: Callable[[Path, str], tuple[Path, core.ConflictPlan]] | None = None,
) -> tuple[Path | None, core.ConflictPlan | None, str | None]:
    return worker_logic.plan_output_path_for_target(
        path,
        args,
        requested_name,
        supported_count,
        conflict_strategy,
        output_root=output_root,
        apply_conflict_strategy=apply_conflict_strategy,
    )


def build_conversion_summary(
    converted_count: int,
    renamed_count: int,
    overwritten_count: int,
    errors: list[ConversionErrorItem],
    stopped: bool,
    *,
    skipped_count: int = 0,
) -> tuple[str, list[str]]:
    return worker_logic.build_conversion_summary(
        converted_count,
        renamed_count,
        overwritten_count,
        errors,
        stopped,
        skipped_count=skipped_count,
        summarize_error_headlines_func=_summarize_error_headlines,
    )


class ConversionWorker(QObject):
    # GUI 依存は Signal / log emit / OS フォルダオープンのみに寄せる。
    # 変換判断・集計・出力先決定は worker_logic 側の helper を優先して使う。
    finished = Signal(dict)
    error = Signal(str)
    log = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self: ConversionWorker, settings_dict: WorkerConversionSettings) -> None:
        super().__init__()
        self.settings_dict = settings_dict
        self._stop_requested = threading.Event()

    def stop(self: ConversionWorker) -> None:
        self._stop_requested.set()

    def _is_stop_requested(self: ConversionWorker) -> bool:
        try:
            return bool(self._stop_requested.is_set())
        except Exception:
            return False

    def _emit_progress(self: ConversionWorker, current: int, total: int, message: str) -> None:
        total_value = max(1, _coerce_progress_number(total, 1))
        current_value = max(0, min(_coerce_progress_number(current, 0), total_value))
        message_text = _coerce_ui_message_text(message)
        self.progress.emit(current_value, total_value, message_text)

    def _make_progress_callback(self: ConversionWorker, file_index: int, total_files: int, path: Path) -> Callable[[int, int, str], None]:
        total_files = max(1, int(total_files or 1))

        def callback(current: int, total: int, message: str) -> None:
            total_value = max(1, _coerce_progress_number(total, 1))
            current_value = max(0, min(_coerce_progress_number(current, 0), total_value))
            message_text = _coerce_ui_message_text(message)
            scale = 1000
            base = (file_index - 1) / total_files
            fraction = current_value / total_value
            overall = int(round((base + fraction / total_files) * scale))
            overall = max(0, min(overall, scale))
            prefix = f'[{file_index}/{total_files}] {path.name}'
            combined = f'{prefix} — {message_text}' if message_text else prefix
            self._emit_progress(overall, scale, combined)

        return callback

    def run(self: ConversionWorker) -> None:
        try:
            self.finished.emit(self._convert())
        except Exception as exc:
            APP_LOGGER.exception('変換ワーカーでエラーが発生しました')
            self.error.emit(str(exc))

    @staticmethod
    def _build_args(cfg: WorkerConversionSettings) -> ConversionArgs:
        return build_conversion_args(cfg)

    @staticmethod
    def _resolve_supported_targets(tp: Path) -> list[Path]:
        return resolve_supported_conversion_targets(tp)

    def _sanitize_output_stem(self_or_name: object, name: object | None = None) -> str:
        # Compatibility wrapper: support both class-level calls
        # ``ConversionWorker._sanitize_output_stem(name)`` and legacy
        # instance-level calls ``worker._sanitize_output_stem(name)``.
        raw_name = self_or_name if name is None else name
        return sanitize_output_stem(str(raw_name))

    @staticmethod
    def _collect_conversion_counts(converted: list[str], renamed: list[dict[str, object]], overwritten: list[dict[str, object]], errors: list[ConversionErrorItem], skipped: int = 0) -> dict[str, int]:
        return worker_logic.collect_conversion_counts(converted, renamed, overwritten, errors, skipped=skipped)

    @staticmethod
    def _resolve_open_folder_target(input_path: Path, converted_files: list[str]) -> str | None:
        return worker_logic.resolve_open_folder_target(input_path, converted_files)

    def _apply_output_conflict_strategy(self: ConversionWorker, desired_path: Path, strategy: str) -> tuple[Path, core.ConflictPlan]:
        return core.resolve_output_path_with_conflict(desired_path, strategy)

    def _output_path_for_target(self: ConversionWorker, path: Path, args: ConversionArgs, requested_name: str, supported_count: int, conflict_strategy: str, output_root: Path | None = None) -> tuple[Path | None, OutputPlan | None]:
        # Keep existing tests/extensions that monkey-patch
        # ``tategakiXTC_gui_studio.plan_output_path_for_target`` effective even
        # after moving the implementation to this split module.
        planner = cast(Callable[..., tuple[Path | None, core.ConflictPlan | None, str | None]], _entry_module_attr('plan_output_path_for_target', plan_output_path_for_target))
        out_path, plan, warning = planner(
            path,
            args,
            requested_name,
            supported_count,
            conflict_strategy,
            output_root=output_root,
            apply_conflict_strategy=self._apply_output_conflict_strategy,
        )
        if warning:
            self.log.emit(warning)
        return out_path, plan

    def _process_target(self: ConversionWorker, path: Path, font_value: str, args: ConversionArgs, out_path: Path, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
        suffix = path.suffix.lower()
        missing = core.get_missing_dependencies_for_suffixes([suffix])
        if missing:
            raise RuntimeError(_format_missing_dependency_message(missing))
        processor_map = _entry_module_attr('PROCESSOR_BY_SUFFIX', PROCESSOR_BY_SUFFIX)
        if isinstance(processor_map, Mapping):
            processor = cast(Any, processor_map).get(suffix)
        else:
            processor = PROCESSOR_BY_SUFFIX.get(suffix)
        if processor is not None:
            return processor(path, str(font_value), args, output_path=out_path, should_cancel=self._is_stop_requested, progress_cb=progress_cb)
        return core.process_archive(path, args, output_path=out_path, should_cancel=self._is_stop_requested, progress_cb=progress_cb)

    def _convert(self: ConversionWorker) -> ConversionResult:
        cfg = self.settings_dict
        target_raw = str(cfg.get('target', '')).strip()
        if not target_raw:
            raise RuntimeError('変換対象ファイルまたはフォルダを指定してください。')
        tp = Path(target_raw)
        if not tp.exists():
            raise RuntimeError(f'指定したパスが見つかりません: {tp}')

        args = self._build_args(cfg)
        supported = self._resolve_supported_targets(tp)
        if not supported:
            raise RuntimeError(f'変換対象の EPUB / ZIP / RAR / CBZ / CBR / PNG / JPG / JPEG / WEBP / {TEXT_OR_MARKDOWN_LABEL} が見つかりませんでした。')

        font_value = str(cfg.get('font_file', '')).strip()
        needs_font = any(p.suffix.lower() in FONT_REQUIRED_SUFFIXES for p in supported)
        if needs_font:
            font_path = core.resolve_font_path(font_value)
            if not font_path or not Path(font_path).exists():
                raise RuntimeError(f'フォントが見つかりません: {cfg.get("font_file", "") or font_path}')

        requested_name = str(cfg.get('output_name', '')).strip()
        conflict_strategy = str(cfg.get('output_conflict', 'rename')).strip().lower()
        converted, stopped = [], False
        errors, renamed_items, overwritten_items = [], [], []
        skipped_count = 0
        planned_desired_sources = {}
        total = len(supported)
        APP_LOGGER.info('変換開始: target=%s files=%s format=%s font=%s conflict=%s', tp, total, getattr(args, 'output_format', 'xtc'), font_value, conflict_strategy)
        self._emit_progress(0, 1000, f'変換準備が完了しました。({total} 件)')
        output_root = tp if tp.is_dir() else None
        for idx, path in enumerate(supported, 1):
            if self._is_stop_requested():
                stopped = True
                self.log.emit('停止要求を受け付けました。')
                break
            self.log.emit(f'[{idx}/{total}] 変換中: {path.name}')
            progress_cb = self._make_progress_callback(idx, total, path)
            progress_cb(0, 1, '変換を開始します。')
            try:
                out_path, plan = self._output_path_for_target(path, args, requested_name, total, conflict_strategy, output_root=output_root)
                if not out_path:
                    skipped_count += 1
                    self.log.emit(f'スキップ: {path.name}')
                    continue
                if plan and plan.get('desired_path'):
                    desired_raw = str(plan['desired_path']).strip()
                    desired_key = worker_logic._normalize_path_match_key(desired_raw) or desired_raw
                    source_key = worker_logic._normalize_path_match_key(path)
                    previous_source = planned_desired_sources.get(desired_key)
                    previous_source_key = worker_logic._normalize_path_match_key(previous_source) if previous_source else ''
                    if previous_source and previous_source_key != source_key:
                        warning = f'同じ出力名候補が複数入力で重複しました: {Path(plan["desired_path"]).name} <- {Path(previous_source).name} / {path.name}'
                        self.log.emit(warning)
                        APP_LOGGER.warning(warning)
                    else:
                        planned_desired_sources[desired_key] = str(path)
                saved = self._process_target(path, font_value, args, out_path, progress_cb=progress_cb)
                if plan and plan.get('renamed'):
                    renamed_items.append(plan)
                    self.log.emit(f'同名あり → 自動連番で保存: {Path(plan["desired_path"]).name} -> {Path(plan["final_path"]).name}')
                elif plan and plan.get('overwritten'):
                    overwritten_items.append(plan)
                    self.log.emit(f'同名あり → 上書き保存: {Path(plan["final_path"]).name}')
            except core.ConversionCancelled:
                stopped = True
                self.log.emit('停止要求を受け付けました。')
                break
            except Exception as exc:
                APP_LOGGER.exception('個別変換エラー: %s', path)
                report = core.build_conversion_error_report(path, exc)
                errors.append({
                    'source': str(path),
                    'error': str(exc),
                    'headline': report.get('headline', ''),
                    'display': report.get('display', str(exc)),
                })
                self.log.emit(report.get('display', f'エラー: {path.name}: {exc}'))
                if total == 1:
                    raise RuntimeError(report.get('display', str(exc))) from exc
                continue
            progress_cb(1, 1, '保存が完了しました。')
            converted.append(str(saved))
            self.log.emit(f'保存: {Path(saved).name}')
            if self._is_stop_requested():
                stopped = True
                self.log.emit('停止しました。')
                break

        postprocess_warnings: list[str] = []
        open_folder_target = ''
        open_folder_requested = worker_logic._bool_config_value(cfg, 'open_folder', True) and bool(converted)
        if open_folder_requested:
            try:
                tgt = self._resolve_open_folder_target(tp, converted)
                if not tgt:
                    warning = f'完了後フォルダの対象を特定できませんでした: {tp}'
                    self.log.emit(warning)
                    APP_LOGGER.warning(warning)
                    postprocess_warnings.append(warning)
                else:
                    open_folder_target = str(tgt)
            except Exception as exc:
                APP_LOGGER.exception('完了後フォルダの対象を特定できませんでした (target=%s converted=%s): %s', tp, len(converted), exc)
                detail = _coerce_ui_message_text(exc).strip()
                message = f'完了後フォルダを開けませんでした。 / 対象: {tp}'
                if detail:
                    message = f'{message} / {detail}'
                self.log.emit(message)
                postprocess_warnings.append(message)

        counts = self._collect_conversion_counts(
            converted,
            renamed_items,
            overwritten_items,
            errors,
            skipped=skipped_count,
        )
        msg, summary_lines = build_conversion_summary(
            counts['converted'],
            counts['renamed'],
            counts['overwritten'],
            errors,
            stopped,
            skipped_count=counts['skipped'],
        )

        self._emit_progress(1000, 1000, msg)
        self.log.emit(msg)
        APP_LOGGER.info('変換終了: saved=%s renamed=%s overwritten=%s errors=%s skipped=%s stopped=%s', counts['converted'], counts['renamed'], counts['overwritten'], counts['errors'], counts['skipped'], stopped)
        normalized_postprocess_warnings = worker_logic.coerce_postprocess_warning_messages(
            postprocess_warnings
        )
        summary_lines = worker_logic.merge_postprocess_warnings_into_summary_lines(
            summary_lines,
            normalized_postprocess_warnings,
        )
        return {
            'message': msg,
            'converted_files': converted,
            'stopped': stopped,
            'errors': errors,
            'summary_lines': summary_lines,
            'skipped_count': counts['skipped'],
            'postprocess_warnings': normalized_postprocess_warnings,
            'open_folder_requested': bool(open_folder_requested),
            'open_folder_target': open_folder_target,
        }


