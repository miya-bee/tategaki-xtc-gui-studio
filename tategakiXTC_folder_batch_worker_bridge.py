from __future__ import annotations

"""Worker bridge for running real folder-batch conversions.

The folder-batch executor calls a tiny callback with
``(source_path, output_path, item)``.  The existing application already has a
single-file worker route in ``tategakiXTC_gui_studio_worker.ConversionWorker``:
it can build ``ConversionArgs`` from the current GUI settings and process one
source path into a caller-provided output path through its internal
``_process_target`` helper.

This module keeps that connection explicit and lazy:
- it does not import PySide6 or the existing worker at module import time;
- it first tries to obtain a current worker settings mapping from MainWindow;
- each item forces ``target`` to the source path and ``open_folder`` off;
- the exact output path is supplied directly to ``_process_target`` so the
  normal output naming/conflict logic is not reused for folder-batch items.
"""

from collections.abc import Mapping
import inspect
from pathlib import Path
from typing import Any, Callable, Iterable

from tategakiXTC_folder_batch_executor import FolderBatchConvertCallback
from tategakiXTC_folder_batch_plan import (
    FOLDER_BATCH_STATUS_CONVERT,
    FolderBatchPlanItem,
)

WorkerSettings = dict[str, Any]
SettingsGetter = Callable[[Path, Path, FolderBatchPlanItem], Mapping[str, Any]]
InnerProgressCallback = Callable[[int, int, str], None]
LogCallback = Callable[[str], None]


MAINWINDOW_WORKER_SETTINGS_GETTERS: tuple[str, ...] = (
    '_folder_batch_worker_settings',
    '_build_folder_batch_worker_settings',
    '_build_worker_settings_for_folder_batch',
    '_build_worker_settings',
    '_collect_worker_settings',
    '_build_conversion_settings',
    '_current_worker_settings',
    '_current_conversion_settings',
    'build_worker_settings',
    'collect_worker_settings',
)


def _call_with_supported_arity(callback: Callable[..., Any], *args: object) -> Any:
    """Call ``callback`` with the richest supported positional argument set.

    MainWindow helper names have not been finalized across historical builds.
    Some candidates accept ``(source_path, output_path, item)``, others accept
    fewer arguments or none.  Use ``inspect.signature(...).bind`` to decide the
    callable boundary before invoking it, so a ``TypeError`` raised inside the
    callback body is not mistaken for an arity mismatch and silently retried.
    """

    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        # Some extension/builtin callables do not expose a Python signature.
        # In that rare case, call once with the richest context and let any
        # TypeError surface unchanged rather than masking callback internals.
        return callback(*args)

    last_bind_error: TypeError | None = None
    for count in range(len(args), -1, -1):
        candidate_args = args[:count]
        try:
            signature.bind(*candidate_args)
        except TypeError as exc:
            last_bind_error = exc
            continue
        return callback(*candidate_args)

    assert last_bind_error is not None
    raise last_bind_error


def _dummy_folder_batch_item() -> FolderBatchPlanItem:
    return FolderBatchPlanItem(
        source_path=Path('dummy.txt'),
        desired_output_path=Path('dummy.xtc'),
        output_path=Path('dummy.xtc'),
        relative_source_path=Path('dummy.txt'),
        status=FOLDER_BATCH_STATUS_CONVERT,
    )


def _mapping_or_none(value: object) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    return None


def collect_worker_settings_from_mainwindow(
    main_window: object,
    source_path: Path,
    output_path: Path,
    item: FolderBatchPlanItem,
    *,
    getter_names: Iterable[str] = MAINWINDOW_WORKER_SETTINGS_GETTERS,
) -> WorkerSettings:
    """Return a current worker-settings mapping from ``main_window``.

    The final MainWindow integration can expose any one of the getter names in
    ``MAINWINDOW_WORKER_SETTINGS_GETTERS``.  A plain mapping may also be passed
    directly in tests.  The returned dict is a copy so the caller can safely
    override per-item fields.
    """

    if isinstance(main_window, Mapping):
        return dict(main_window)

    for name in getter_names:
        getter = getattr(main_window, name, None)
        if not callable(getter):
            continue
        value = _call_with_supported_arity(getter, source_path, output_path, item)
        mapping = _mapping_or_none(value)
        if mapping is not None:
            return dict(mapping)

    for attr_name in ('worker_settings', 'settings_dict', 'conversion_settings'):
        value = getattr(main_window, attr_name, None)
        mapping = _mapping_or_none(value)
        if mapping is not None:
            return dict(mapping)

    raise AttributeError(
        'MainWindow から現在の変換設定を取得できません。'
        ' _folder_batch_worker_settings() または _build_worker_settings() '
        'のような設定取得 hook を追加してください。'
    )


def _output_format_from_output_path(output_path: Path, fallback: object = 'xtc') -> str:
    suffix = Path(output_path).suffix.lower().lstrip('.')
    if suffix in {'xtc', 'xtch'}:
        return suffix
    text = str(fallback or '').strip().lower().lstrip('.')
    return text if text in {'xtc', 'xtch'} else 'xtc'


def build_worker_settings_for_folder_batch_item(
    base_settings: Mapping[str, Any],
    source_path: Path,
    output_path: Path,
) -> WorkerSettings:
    """Return per-item worker settings for direct ``_process_target`` use."""

    settings = dict(base_settings)
    settings['target'] = str(Path(source_path))
    settings['open_folder'] = False
    settings['output_name'] = Path(output_path).stem
    settings['output_format'] = _output_format_from_output_path(
        Path(output_path), settings.get('output_format', 'xtc')
    )
    # ``_process_target`` writes exactly to ``output_path``.  Still store a
    # safe conflict value so any downstream summary/log code sees an explicit
    # non-renaming policy for this already-planned destination.
    settings['output_conflict'] = 'overwrite'
    return settings


def _import_default_worker_class() -> type[Any]:
    from tategakiXTC_gui_studio_worker import ConversionWorker

    return ConversionWorker


def _build_args_with_worker(worker: object, settings: Mapping[str, Any]) -> object:
    build_args = getattr(worker, '_build_args', None)
    if callable(build_args):
        return build_args(settings)
    from tategakiXTC_gui_studio_worker import build_conversion_args

    return build_conversion_args(settings)  # type: ignore[arg-type]


def make_worker_bridge_converter(
    settings_getter: SettingsGetter,
    *,
    worker_cls: type[Any] | None = None,
    inner_progress_cb: InnerProgressCallback | None = None,
    log_cb: LogCallback | None = None,
) -> FolderBatchConvertCallback:
    """Build a folder-batch converter using ``ConversionWorker._process_target``.

    ``settings_getter`` should return the current GUI worker settings before
    per-item overrides.  ``worker_cls`` is injectable for unit tests.
    """

    def _convert(source_path: Path, output_path: Path, item: FolderBatchPlanItem) -> Path:
        source = Path(source_path)
        output = Path(output_path)
        base_settings = settings_getter(source, output, item)
        settings = build_worker_settings_for_folder_batch_item(base_settings, source, output)
        actual_worker_cls = worker_cls or _import_default_worker_class()
        worker = actual_worker_cls(settings)
        args = _build_args_with_worker(worker, settings)
        process_target = getattr(worker, '_process_target', None)
        if not callable(process_target):
            raise RuntimeError('ConversionWorker._process_target が見つかりません。')
        output.parent.mkdir(parents=True, exist_ok=True)
        font_value = str(settings.get('font_file', '') or '')
        if log_cb is not None:
            log_cb(f'[WORKER] {item.relative_source_path} -> {output}')
        saved = process_target(source, font_value, args, output, progress_cb=inner_progress_cb)
        return Path(saved or output)

    return _convert


def make_mainwindow_worker_bridge_converter(
    main_window: object,
    *,
    worker_cls: type[Any] | None = None,
    inner_progress_cb: InnerProgressCallback | None = None,
    log_cb: LogCallback | None = None,
) -> FolderBatchConvertCallback:
    """Build a real converter from MainWindow settings + existing worker route.

    The settings hook is validated eagerly so GUI launchers can warn before
    importing or opening the Qt dialog.  This keeps missing-integration failures
    cheap and clear.
    """

    dummy_item = _dummy_folder_batch_item()
    collect_worker_settings_from_mainwindow(
        main_window,
        dummy_item.source_path,
        dummy_item.output_path or Path('dummy.xtc'),
        dummy_item,
    )

    def _settings_getter(source: Path, output: Path, item: FolderBatchPlanItem) -> Mapping[str, Any]:
        return collect_worker_settings_from_mainwindow(main_window, source, output, item)

    return make_worker_bridge_converter(
        _settings_getter,
        worker_cls=worker_cls,
        inner_progress_cb=inner_progress_cb,
        log_cb=log_cb,
    )


def can_collect_worker_settings_from_mainwindow(main_window: object) -> bool:
    """Best-effort readiness check used by integration diagnostics/tests."""

    dummy_item = _dummy_folder_batch_item()
    try:
        collect_worker_settings_from_mainwindow(
            main_window,
            dummy_item.source_path,
            dummy_item.output_path or Path('dummy.xtc'),
            dummy_item,
        )
        return True
    except Exception:
        return False
