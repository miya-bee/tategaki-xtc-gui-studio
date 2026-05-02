from __future__ import annotations

"""Small path/output helpers for tategakiXTC_gui_studio.

These helpers are kept independent from Qt so the MainWindow entry module can
continue to delegate without pulling more UI code into the split module.
"""

from pathlib import Path
from typing import Callable, Iterable


def _supported_targets_for_path(
    target_raw: object,
    resolver: Callable[[Path], Iterable[Path]],
) -> list[Path]:
    target_text = str(target_raw).strip()
    if not target_text:
        return []
    target_path = Path(target_text)
    if not target_path.exists():
        return []
    return list(resolver(target_path))


def _default_output_name_for_target(
    path: Path,
    output_format: str,
    *,
    get_output_path_for_target: Callable[[Path, str], object],
    sanitize_output_stem: Callable[[object], str],
) -> str:
    desired = get_output_path_for_target(path, output_format)
    candidate = Path(desired).stem if desired else path.stem
    sanitized = sanitize_output_stem(candidate)
    return sanitized or 'output'
