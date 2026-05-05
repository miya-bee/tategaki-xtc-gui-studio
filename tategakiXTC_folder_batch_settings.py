from __future__ import annotations

"""Settings helpers for the folder batch conversion feature.

The helpers are intentionally Qt-free.  They accept either a ``QSettings``-like
object (``value`` / ``setValue`` / optional ``sync``) or a plain mutable mapping
so that settings persistence can be regression-tested without PySide6.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from tategakiXTC_folder_batch_plan import normalize_existing_policy

FOLDER_BATCH_SETTINGS_PREFIX = 'folder_batch'
FOLDER_BATCH_INPUT_ROOT_KEY = f'{FOLDER_BATCH_SETTINGS_PREFIX}/input_root'
FOLDER_BATCH_OUTPUT_ROOT_KEY = f'{FOLDER_BATCH_SETTINGS_PREFIX}/output_root'
FOLDER_BATCH_INCLUDE_SUBFOLDERS_KEY = f'{FOLDER_BATCH_SETTINGS_PREFIX}/include_subfolders'
FOLDER_BATCH_PRESERVE_STRUCTURE_KEY = f'{FOLDER_BATCH_SETTINGS_PREFIX}/preserve_structure'
FOLDER_BATCH_EXISTING_POLICY_KEY = f'{FOLDER_BATCH_SETTINGS_PREFIX}/existing_policy'


@dataclass(frozen=True)
class FolderBatchDialogDefaults:
    input_root: str = ''
    output_root: str = ''
    include_subfolders: bool = True
    preserve_structure: bool = True
    existing_policy: str = 'skip'


def _settings_value(settings: object, key: str, default: Any) -> Any:
    if settings is None:
        return default
    if isinstance(settings, Mapping):
        return settings.get(key, default)
    value = getattr(settings, 'value', None)
    if callable(value):
        try:
            return value(key, default)
        except TypeError:
            raw = value(key)
            return default if raw is None else raw
    return default


def _settings_set_value(settings: object, key: str, value: Any) -> None:
    if settings is None:
        return
    if isinstance(settings, MutableMapping):
        settings[key] = value
        return
    setter = getattr(settings, 'setValue', None)
    if callable(setter):
        setter(key, value)


def _settings_sync(settings: object) -> None:
    sync = getattr(settings, 'sync', None)
    if callable(sync):
        sync()


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {'1', 'true', 'yes', 'on', 'checked', 'はい', '有効'}:
        return True
    if text in {'0', 'false', 'no', 'off', 'unchecked', 'いいえ', '無効'}:
        return False
    return default


def _coerce_path_text(value: object) -> str:
    if value is None:
        return ''
    raw = str(value).strip()
    if not raw:
        return ''
    try:
        return str(Path(raw)).strip()
    except Exception:
        return raw


def load_folder_batch_dialog_defaults(
    settings: object,
    *,
    default_input_root: str | Path = '',
    default_output_root: str | Path = '',
) -> FolderBatchDialogDefaults:
    """Load folder-batch defaults from a QSettings-like object.

    The feature defaults intentionally match the project decision:
    include subfolders = ON, preserve structure = ON, existing files = skip.
    """

    input_root = _coerce_path_text(
        _settings_value(settings, FOLDER_BATCH_INPUT_ROOT_KEY, str(default_input_root or ''))
    )
    output_root = _coerce_path_text(
        _settings_value(settings, FOLDER_BATCH_OUTPUT_ROOT_KEY, str(default_output_root or ''))
    )
    include_subfolders = _coerce_bool(
        _settings_value(settings, FOLDER_BATCH_INCLUDE_SUBFOLDERS_KEY, True),
        True,
    )
    preserve_structure = _coerce_bool(
        _settings_value(settings, FOLDER_BATCH_PRESERVE_STRUCTURE_KEY, True),
        True,
    )
    existing_policy = normalize_existing_policy(
        _settings_value(settings, FOLDER_BATCH_EXISTING_POLICY_KEY, 'skip'),
        'skip',
    )
    return FolderBatchDialogDefaults(
        input_root=input_root,
        output_root=output_root,
        include_subfolders=include_subfolders,
        preserve_structure=preserve_structure,
        existing_policy=existing_policy,
    )


def save_folder_batch_dialog_defaults(
    settings: object,
    *,
    input_root: str | Path,
    output_root: str | Path,
    include_subfolders: bool,
    preserve_structure: bool,
    existing_policy: str,
) -> None:
    """Persist the last used folder-batch dialog options."""

    _settings_set_value(settings, FOLDER_BATCH_INPUT_ROOT_KEY, str(input_root or ''))
    _settings_set_value(settings, FOLDER_BATCH_OUTPUT_ROOT_KEY, str(output_root or ''))
    _settings_set_value(settings, FOLDER_BATCH_INCLUDE_SUBFOLDERS_KEY, bool(include_subfolders))
    _settings_set_value(settings, FOLDER_BATCH_PRESERVE_STRUCTURE_KEY, bool(preserve_structure))
    _settings_set_value(settings, FOLDER_BATCH_EXISTING_POLICY_KEY, normalize_existing_policy(existing_policy))
    _settings_sync(settings)


def save_folder_batch_result_defaults(settings: object, result: object) -> None:
    """Persist defaults from a ``FolderBatchDialogResult``-like object."""

    save_folder_batch_dialog_defaults(
        settings,
        input_root=getattr(result, 'input_root', ''),
        output_root=getattr(result, 'output_root', ''),
        include_subfolders=bool(getattr(result, 'include_subfolders', True)),
        preserve_structure=bool(getattr(result, 'preserve_structure', True)),
        existing_policy=str(getattr(result, 'existing_policy', 'skip')),
    )
