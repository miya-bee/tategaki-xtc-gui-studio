from __future__ import annotations

"""Optional dependency status helpers for ``tategakiXTC_gui_studio``.

The entry module keeps ``MainWindow`` wrapper methods so existing tests and
monkey patches can still replace those methods on the window object.  This
module keeps the grouping / warning control flow import-safe and receives the
small core callables from the wrapper.
"""

from pathlib import Path
from typing import Any, Callable

MissingDependencyItem = dict[str, object]
ListOptionalDependencyStatusFunc = Callable[[], list[MissingDependencyItem]]
GetMissingDependenciesForSuffixesFunc = Callable[[set[str]], list[MissingDependencyItem]]
FormatMissingDependencyMessageFunc = Callable[[list[MissingDependencyItem]], str]


def log_optional_dependency_status(
    window: Any,
    list_optional_dependency_status_func: ListOptionalDependencyStatusFunc,
) -> None:
    statuses = list_optional_dependency_status_func()
    missing = [item for item in statuses if not item.get('available')]
    if not missing:
        return

    grouped: dict[str, list[MissingDependencyItem]] = {
        'feature': [],
        'performance': [],
        'convenience': [],
    }
    for item in missing:
        impact = str(item.get('impact') or 'feature')
        grouped.setdefault(impact, []).append(item)

    lines: list[str] = []
    if grouped.get('feature'):
        lines.append('一部の追加ライブラリが未導入です。使えない機能があります。')
        for item in grouped['feature']:
            lines.append(f"- {item['label']}（{item['purpose']}）")
    if grouped.get('performance'):
        lines.append('高速化用の追加ライブラリが未導入です。変換速度が低下することがあります。')
        for item in grouped['performance']:
            lines.append(f"- {item['label']}（{item['purpose']}）")
    if grouped.get('convenience'):
        lines.append('任意の補助ライブラリが未導入です。進捗表示などが簡略化される場合があります。')
        for item in grouped['convenience']:
            lines.append(f"- {item['label']}（{item['purpose']}）")
    window._append_log_without_status_best_effort(' / '.join(lines))


def missing_dependencies_for_targets(
    targets: list[Path],
    get_missing_dependencies_for_suffixes_func: GetMissingDependenciesForSuffixesFunc,
) -> list[MissingDependencyItem]:
    suffixes = {p.suffix.lower() for p in targets}
    return get_missing_dependencies_for_suffixes_func(suffixes)


def check_conversion_dependencies(
    window: Any,
    cfg: dict[str, object],
    format_missing_dependency_message_func: FormatMissingDependencyMessageFunc,
) -> bool:
    supported = window._supported_targets_for_path(cfg.get('target', ''))
    missing = window._missing_dependencies_for_targets(supported)
    if not missing:
        return True
    window._show_warning_dialog_with_status_fallback(
        'ライブラリ不足',
        format_missing_dependency_message_func(missing),
    )
    missing_log_message = '不足ライブラリ: ' + ', '.join(str(item['label']) for item in missing)
    window._append_log_without_status_best_effort(missing_log_message)
    return False


__all__ = [
    'check_conversion_dependencies',
    'log_optional_dependency_status',
    'missing_dependencies_for_targets',
]
