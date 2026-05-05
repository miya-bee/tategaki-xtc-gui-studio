from __future__ import annotations

"""Safety diagnostics for folder batch conversion roots.

These helpers are Qt-free and intentionally advisory.  They do not block the
feature by themselves; the dialog/controller can decide how strongly to surface
warnings.  The goal is to catch risky folder choices before MainWindow/worker
integration begins.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FolderBatchRootSafetyReport:
    input_root: Path
    output_root: Path
    warnings: tuple[str, ...]

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)


def _resolve_for_compare(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path.absolute()


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def analyze_folder_batch_roots(input_root: str | Path, output_root: str | Path) -> FolderBatchRootSafetyReport:
    """Return advisory warnings for risky input/output root combinations."""

    in_text = str(input_root or '').strip()
    out_text = str(output_root or '').strip()
    warnings: list[str] = []
    in_path = Path(in_text) if in_text else Path()
    out_path = Path(out_text) if out_text else Path()
    if not in_text:
        warnings.append('入力元フォルダが未指定です。')
    if not out_text:
        warnings.append('出力先フォルダが未指定です。')
    if not in_text or not out_text:
        return FolderBatchRootSafetyReport(input_root=in_path, output_root=out_path, warnings=tuple(warnings))

    resolved_input = _resolve_for_compare(in_path)
    resolved_output = _resolve_for_compare(out_path)
    if resolved_input == resolved_output:
        warnings.append('入力元フォルダと出力先フォルダが同じです。変換後ファイルが入力元側に混在します。')
    elif _is_relative_to(resolved_output, resolved_input):
        warnings.append('出力先フォルダが入力元フォルダの配下です。再実行時の混在に注意してください。')
    elif _is_relative_to(resolved_input, resolved_output):
        warnings.append('入力元フォルダが出力先フォルダの配下です。出力先の管理単位に注意してください。')
    return FolderBatchRootSafetyReport(input_root=in_path, output_root=out_path, warnings=tuple(warnings))

def format_folder_batch_safety_warnings(
    report: FolderBatchRootSafetyReport,
    *,
    prefix: str = '注意: ',
) -> list[str]:
    """Return user-facing warning lines for a safety report.

    Keeping this formatting Qt-free lets the dialog, controller tests, and future
    release docs use the same Japanese wording without duplicating it.
    """

    if not report.has_warnings:
        return []
    return [f'{prefix}{warning}' for warning in report.warnings]


def summarize_folder_batch_root_safety(input_root: str | Path, output_root: str | Path) -> list[str]:
    """Analyze roots and return warning lines for confirmation dialogs."""

    return format_folder_batch_safety_warnings(
        analyze_folder_batch_roots(input_root, output_root),
    )

