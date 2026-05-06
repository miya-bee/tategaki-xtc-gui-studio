from __future__ import annotations

"""Optional-dependency guidance helpers for folder batch conversion.

The normal single-file conversion route already checks optional libraries before
starting.  Folder batch conversion can contain mixed inputs, so this module keeps
preflight guidance non-blocking: the dialog and logs can tell the user which
planned files may fail because an optional dependency is missing, while TXT /
Markdown / image items can still run.
"""

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from tategakiXTC_folder_batch_plan import FolderBatchPlan

MissingDependencyGetter = Callable[[Iterable[str]], list[Mapping[str, Any]]]


def folder_batch_planned_source_suffixes(plan: FolderBatchPlan) -> tuple[str, ...]:
    """Return unique source suffixes for items that will actually convert."""

    suffixes: list[str] = []
    seen: set[str] = set()
    for item in plan.items:
        if not item.will_convert:
            continue
        suffix = Path(item.source_path).suffix.lower()
        if suffix and suffix not in seen:
            suffixes.append(suffix)
            seen.add(suffix)
    return tuple(suffixes)


def _default_missing_dependency_getter(suffixes: Iterable[str]) -> list[Mapping[str, Any]]:
    import tategakiXTC_gui_core as core

    return list(core.get_missing_dependencies_for_suffixes(suffixes))


def missing_dependencies_for_folder_batch_plan(
    plan: FolderBatchPlan,
    *,
    dependency_getter: MissingDependencyGetter | None = None,
) -> list[Mapping[str, Any]]:
    """Return optional dependencies missing for planned conversion items.

    This is best-effort by design.  If the dependency checker itself is not
    available in a split test environment, folder batch planning should still be
    usable and the real worker will raise a detailed error per file later.
    """

    suffixes = folder_batch_planned_source_suffixes(plan)
    if not suffixes:
        return []
    getter = dependency_getter or _default_missing_dependency_getter
    try:
        return list(getter(suffixes))
    except Exception:
        return []


def format_folder_batch_missing_dependency_lines(missing: Iterable[Mapping[str, Any]]) -> list[str]:
    """Format missing optional dependencies as user-facing Japanese lines."""

    items = list(missing)
    if not items:
        return []

    lines = [
        '注意: EPUB などの変換に必要な追加ライブラリが不足しています。',
    ]
    for item in items:
        label = str(item.get('label') or item.get('package') or '不明なライブラリ')
        purpose = str(item.get('purpose') or '').strip()
        package = str(item.get('package') or '').strip()
        if purpose and package and package != label:
            lines.append(f'- {label}（{purpose} / pip install {package}）')
        elif purpose:
            lines.append(f'- {label}（{purpose}）')
        elif package and package != label:
            lines.append(f'- {label}（pip install {package}）')
        else:
            lines.append(f'- {label}')
    lines.append('該当形式は失敗する可能性があります。install_requirements.bat または requirements.txt で依存ライブラリを入れ直してください。')
    return lines


def describe_folder_batch_missing_dependencies(
    plan: FolderBatchPlan,
    *,
    dependency_getter: MissingDependencyGetter | None = None,
) -> str:
    """Return a multi-line warning for missing dependencies, or an empty string."""

    missing = missing_dependencies_for_folder_batch_plan(plan, dependency_getter=dependency_getter)
    return '\n'.join(format_folder_batch_missing_dependency_lines(missing))
