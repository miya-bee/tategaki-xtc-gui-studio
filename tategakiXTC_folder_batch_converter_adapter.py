from __future__ import annotations

"""Adapter helpers for connecting folder-batch execution to existing converters.

The folder-batch executor is intentionally simple: it calls a converter callback
with ``(source_path, output_path, plan_item)``.  Existing GUI conversion code may
not have that exact signature, so this module provides a small compatibility
layer that can wrap common single-file conversion functions without importing Qt
or renderer internals.

The adapter is conservative by design:
- it uses ``inspect.signature`` where possible instead of blindly retrying after
  ``TypeError``;
- a real ``TypeError`` raised inside the converter is not swallowed;
- path arguments are passed as ``Path`` objects by default, with an opt-in string
  path mode for older helper functions.
"""

from dataclasses import dataclass
import inspect
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from tategakiXTC_folder_batch_executor import FolderBatchConvertCallback
from tategakiXTC_folder_batch_plan import FolderBatchPlanItem


@dataclass(frozen=True)
class FolderBatchConversionContext:
    source_path: Path
    output_path: Path
    item: FolderBatchPlanItem

    @property
    def relative_source_path(self) -> Path:
        return self.item.relative_source_path


ExtraKwargsGetter = Callable[[FolderBatchConversionContext], Mapping[str, Any] | None]
BeforeAfterCallback = Callable[[FolderBatchConversionContext], None]


_SOURCE_PARAM_NAMES = (
    'source_path',
    'input_path',
    'input_file',
    'src_path',
    'src',
)
_OUTPUT_PARAM_NAMES = (
    'output_path',
    'output_file',
    'destination_path',
    'dest_path',
    'dst_path',
    'dst',
)
_ITEM_PARAM_NAMES = (
    'item',
    'plan_item',
    'folder_batch_item',
)


def _coerce_path(path: Path, *, as_string: bool) -> Path | str:
    return str(path) if as_string else path


def _safe_signature(callback: Callable[..., Any]) -> inspect.Signature | None:
    try:
        return inspect.signature(callback)
    except (TypeError, ValueError):
        return None


def _has_varargs(signature: inspect.Signature) -> bool:
    return any(param.kind == inspect.Parameter.VAR_POSITIONAL for param in signature.parameters.values())


def _has_varkw(signature: inspect.Signature) -> bool:
    return any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())


def _positional_capacity(signature: inspect.Signature) -> int:
    if _has_varargs(signature):
        return 99
    return sum(
        1
        for param in signature.parameters.values()
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    )


def _find_param_name(signature: inspect.Signature, candidates: Iterable[str]) -> str | None:
    for candidate in candidates:
        if candidate in signature.parameters:
            return candidate
    return None


def _call_with_best_supported_signature(
    callback: Callable[..., Any],
    context: FolderBatchConversionContext,
    *,
    path_as_string: bool = False,
    extra_kwargs: Mapping[str, Any] | None = None,
) -> Any:
    """Call ``callback`` using the best supported folder-batch signature.

    Supported forms, in priority order:
    - ``callback(source_path, output_path, item)``
    - ``callback(source_path, output_path)``
    - keyword forms such as ``input_path=...`` and ``output_path=...``
    - ``callback(context=FolderBatchConversionContext(...))``

    If the function has no introspectable signature, the canonical 3-argument
    form is used.  This mirrors the executor contract.
    """

    source = _coerce_path(context.source_path, as_string=path_as_string)
    output = _coerce_path(context.output_path, as_string=path_as_string)
    signature = _safe_signature(callback)
    if signature is None:
        return callback(source, output, context.item)

    kwargs = dict(extra_kwargs or {})
    positional_capacity = _positional_capacity(signature)

    source_name = _find_param_name(signature, _SOURCE_PARAM_NAMES)
    output_name = _find_param_name(signature, _OUTPUT_PARAM_NAMES)
    item_name = _find_param_name(signature, _ITEM_PARAM_NAMES)

    # Prefer semantic keyword binding when the callback exposes recognizable
    # names.  This avoids accidental conflicts such as passing a third optional
    # positional argument that is also supplied by extra_kwargs.
    if source_name and output_name:
        kwargs[source_name] = source
        kwargs[output_name] = output
        if item_name:
            kwargs[item_name] = context.item
        return callback(**kwargs)

    if positional_capacity >= 3:
        return callback(source, output, context.item, **kwargs)
    if positional_capacity >= 2:
        return callback(source, output, **kwargs)

    if 'context' in signature.parameters or _has_varkw(signature):
        kwargs['context'] = context
        return callback(**kwargs)

    raise TypeError(
        'フォルダ一括変換の converter callback として使える引数形式ではありません。'
    )


def make_folder_batch_converter_from_callable(
    callback: Callable[..., Any],
    *,
    path_as_string: bool = False,
    extra_kwargs_getter: ExtraKwargsGetter | None = None,
    before_each: BeforeAfterCallback | None = None,
    after_each: BeforeAfterCallback | None = None,
) -> FolderBatchConvertCallback:
    """Wrap an existing single-file conversion callable for folder batch use."""

    def _convert(source_path: Path, output_path: Path, item: FolderBatchPlanItem) -> Any:
        context = FolderBatchConversionContext(
            source_path=source_path,
            output_path=output_path,
            item=item,
        )
        if before_each is not None:
            before_each(context)
        extra_kwargs = extra_kwargs_getter(context) if extra_kwargs_getter is not None else None
        result = _call_with_best_supported_signature(
            callback,
            context,
            path_as_string=path_as_string,
            extra_kwargs=extra_kwargs,
        )
        if after_each is not None:
            after_each(context)
        return result

    return _convert


def make_output_override_kwargs(
    output_path: Path | str,
    *,
    key: str = 'output_path',
    path_as_string: bool = False,
) -> dict[str, Any]:
    """Return a tiny kwargs dict for existing converters that accept output override.

    This helper keeps MainWindow integration readable when the existing converter
    route already accepts a named output destination argument.
    """

    path = Path(output_path)
    return {key: str(path) if path_as_string else path}


def build_mainwindow_converter_from_known_hook(
    main_window: object,
    *,
    hook_names: Iterable[str] = (
        '_convert_single_file_for_folder_batch',
        '_convert_one_file_for_folder_batch',
        '_convert_single_file_with_output_path',
        '_run_single_file_conversion_with_output_path',
    ),
    path_as_string: bool = False,
) -> FolderBatchConvertCallback:
    """Build a converter from an explicit MainWindow hook if present.

    v1.2.2.5 does not guess the large existing conversion pipeline.  Instead it
    looks for a small hook method that the final GUI integration can add to
    MainWindow.  This avoids accidentally bypassing app-specific settings.
    """

    for name in hook_names:
        hook = getattr(main_window, name, None)
        if callable(hook):
            return make_folder_batch_converter_from_callable(hook, path_as_string=path_as_string)
    raise AttributeError(
        'MainWindow にフォルダ一括変換用の実変換 hook が見つかりません。'
        ' まず _convert_single_file_for_folder_batch(source_path, output_path, item) '
        'のような薄い接続メソッドを追加してください。'
    )
