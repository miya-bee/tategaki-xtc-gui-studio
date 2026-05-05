from __future__ import annotations

"""Folder batch conversion planning helpers for TategakiXTC GUI Studio.

This module is intentionally Qt-free.  It builds a deterministic conversion plan
for the future GUI dialog without touching the renderer/converter internals.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

FOLDER_BATCH_EXISTING_POLICIES = ('skip', 'overwrite', 'rename')
FOLDER_BATCH_STATUS_CONVERT = 'convert'
FOLDER_BATCH_STATUS_SKIP_EXISTING = 'skip_existing'
FOLDER_BATCH_STATUS_SKIP_DUPLICATE = 'skip_duplicate'

# Keep this list close to the worker's currently supported direct inputs.
# Archives can be added later if the folder-batch UI decides to expose them.
DEFAULT_FOLDER_BATCH_SUFFIXES = (
    '.txt',
    '.md',
    '.markdown',
    '.epub',
    '.png',
    '.jpg',
    '.jpeg',
    '.webp',
)


FOLDER_BATCH_POLICY_LABELS = {
    'skip': 'スキップ',
    'overwrite': '上書き',
    'rename': '別名で保存',
}


def folder_batch_policy_label(policy: object) -> str:
    return FOLDER_BATCH_POLICY_LABELS.get(normalize_existing_policy(policy), 'スキップ')

@dataclass(frozen=True)
class FolderBatchPlanItem:
    source_path: Path
    desired_output_path: Path
    output_path: Path | None
    relative_source_path: Path
    status: str
    reason: str = ''
    existing_output: bool = False
    renamed: bool = False
    overwritten: bool = False
    duplicate_in_batch: bool = False

    @property
    def will_convert(self) -> bool:
        return self.status == FOLDER_BATCH_STATUS_CONVERT and self.output_path is not None


@dataclass(frozen=True)
class FolderBatchPlan:
    input_root: Path
    output_root: Path
    include_subfolders: bool
    preserve_structure: bool
    existing_policy: str
    output_format: str
    items: tuple[FolderBatchPlanItem, ...]

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def convert_count(self) -> int:
        return sum(1 for item in self.items if item.will_convert)

    @property
    def skipped_count(self) -> int:
        return sum(1 for item in self.items if not item.will_convert)

    @property
    def existing_skip_count(self) -> int:
        return sum(1 for item in self.items if item.status == FOLDER_BATCH_STATUS_SKIP_EXISTING)

    @property
    def duplicate_skip_count(self) -> int:
        return sum(1 for item in self.items if item.status == FOLDER_BATCH_STATUS_SKIP_DUPLICATE)

    @property
    def renamed_count(self) -> int:
        return sum(1 for item in self.items if item.renamed)

    @property
    def overwritten_count(self) -> int:
        return sum(1 for item in self.items if item.overwritten)


def normalize_existing_policy(value: object, default: str = 'skip') -> str:
    text = str(value or '').strip().lower().replace('-', '_')
    aliases = {
        'skip': 'skip',
        'スキップ': 'skip',
        'overwrite': 'overwrite',
        '上書き': 'overwrite',
        'rename': 'rename',
        'renamed': 'rename',
        '別名': 'rename',
        '別名保存': 'rename',
        '別名で保存': 'rename',
    }
    normalized = aliases.get(text, text)
    return normalized if normalized in FOLDER_BATCH_EXISTING_POLICIES else default


def normalize_output_format(value: object, default: str = 'xtc') -> str:
    text = str(value or '').strip().lower().lstrip('.')
    return text if text in {'xtc', 'xtch'} else default


def normalize_suffixes(suffixes: Iterable[str] | None = None) -> tuple[str, ...]:
    source = suffixes if suffixes is not None else DEFAULT_FOLDER_BATCH_SUFFIXES
    normalized: list[str] = []
    seen: set[str] = set()
    for suffix in source:
        text = str(suffix or '').strip().lower()
        if not text:
            continue
        if not text.startswith('.'):
            text = f'.{text}'
        if text not in seen:
            normalized.append(text)
            seen.add(text)
    return tuple(normalized)


def _required_path(value: Path | str, label: str) -> Path:
    text = str(value or '').strip()
    if not text:
        raise ValueError(f'{label}を指定してください。')
    return Path(text)


def discover_folder_batch_targets(
    input_root: Path | str,
    *,
    include_subfolders: bool = True,
    supported_suffixes: Iterable[str] | None = None,
) -> tuple[Path, ...]:
    root = _required_path(input_root, '入力元フォルダ')
    suffixes = set(normalize_suffixes(supported_suffixes))
    if not root.exists():
        raise FileNotFoundError(f'入力元フォルダが見つかりません: {root}')
    if not root.is_dir():
        raise NotADirectoryError(f'入力元はフォルダを指定してください: {root}')
    iterator = root.rglob('*') if include_subfolders else root.glob('*')
    return tuple(
        path
        for path in sorted(iterator, key=lambda p: str(p).lower())
        if path.is_file() and path.suffix.lower() in suffixes
    )


def _with_output_extension(path: Path, output_format: str) -> Path:
    return path.with_suffix(f'.{normalize_output_format(output_format)}')


def _candidate_with_index(path: Path, index: int) -> Path:
    return path.with_name(f'{path.stem}_{index}{path.suffix}')


def _normalize_match_key(path: Path) -> str:
    try:
        return str(path.resolve()).lower()
    except Exception:
        return str(path).lower()


def _unique_renamed_path(base_path: Path, reserved_keys: set[str]) -> Path:
    index = 2
    while True:
        candidate = _candidate_with_index(base_path, index)
        candidate_key = _normalize_match_key(candidate)
        if candidate_key not in reserved_keys and not candidate.exists():
            return candidate
        index += 1


def _desired_output_path(
    source_path: Path,
    relative_source_path: Path,
    output_root: Path,
    *,
    preserve_structure: bool,
    output_format: str,
) -> Path:
    if preserve_structure:
        relative_output = _with_output_extension(relative_source_path, output_format)
        return output_root / relative_output
    return output_root / _with_output_extension(Path(source_path.name), output_format)


def build_folder_batch_plan(
    input_root: Path | str,
    output_root: Path | str,
    *,
    include_subfolders: bool = True,
    preserve_structure: bool = True,
    existing_policy: str = 'skip',
    output_format: str = 'xtc',
    supported_suffixes: Iterable[str] | None = None,
    targets: Sequence[Path | str] | None = None,
) -> FolderBatchPlan:
    root = _required_path(input_root, '入力元フォルダ')
    out_root = _required_path(output_root, '出力先フォルダ')
    policy = normalize_existing_policy(existing_policy)
    fmt = normalize_output_format(output_format)
    if targets is None:
        source_paths = discover_folder_batch_targets(
            root,
            include_subfolders=include_subfolders,
            supported_suffixes=supported_suffixes,
        )
    else:
        source_paths = tuple(Path(path) for path in targets)
    reserved_output_keys: set[str] = set()
    items: list[FolderBatchPlanItem] = []
    for source_path in source_paths:
        try:
            relative_source_path = source_path.relative_to(root)
        except ValueError:
            relative_source_path = Path(source_path.name)
        desired = _desired_output_path(
            source_path,
            relative_source_path,
            out_root,
            preserve_structure=preserve_structure,
            output_format=fmt,
        )
        desired_key = _normalize_match_key(desired)
        exists = desired.exists()
        duplicate = desired_key in reserved_output_keys
        if duplicate and policy == 'skip':
            items.append(
                FolderBatchPlanItem(
                    source_path=source_path,
                    desired_output_path=desired,
                    output_path=None,
                    relative_source_path=relative_source_path,
                    status=FOLDER_BATCH_STATUS_SKIP_DUPLICATE,
                    reason='同じ出力先候補が一括変換内で重複したためスキップします。',
                    duplicate_in_batch=True,
                )
            )
            continue
        if exists and policy == 'skip':
            items.append(
                FolderBatchPlanItem(
                    source_path=source_path,
                    desired_output_path=desired,
                    output_path=None,
                    relative_source_path=relative_source_path,
                    status=FOLDER_BATCH_STATUS_SKIP_EXISTING,
                    reason='既存ファイルがあるためスキップします。',
                    existing_output=True,
                )
            )
            reserved_output_keys.add(desired_key)
            continue
        final_path = desired
        renamed = False
        overwritten = bool(exists and policy == 'overwrite')
        # Even when overwrite is selected, never let two inputs in the same run
        # write to the same output path.  Rename the later one to avoid data loss.
        if policy == 'rename' and (exists or duplicate):
            final_path = _unique_renamed_path(desired, reserved_output_keys)
            renamed = True
        elif duplicate:
            final_path = _unique_renamed_path(desired, reserved_output_keys)
            renamed = True
            overwritten = False
        reserved_output_keys.add(_normalize_match_key(final_path))
        items.append(
            FolderBatchPlanItem(
                source_path=source_path,
                desired_output_path=desired,
                output_path=final_path,
                relative_source_path=relative_source_path,
                status=FOLDER_BATCH_STATUS_CONVERT,
                reason='',
                existing_output=exists,
                renamed=renamed,
                overwritten=overwritten,
                duplicate_in_batch=duplicate,
            )
        )
    return FolderBatchPlan(
        input_root=root,
        output_root=out_root,
        include_subfolders=include_subfolders,
        preserve_structure=preserve_structure,
        existing_policy=policy,
        output_format=fmt,
        items=tuple(items),
    )


def describe_folder_batch_no_work(plan: FolderBatchPlan) -> str:
    """Return a concise explanation when a plan has no files to convert."""

    if plan.convert_count > 0:
        return ''
    if plan.total_count <= 0:
        return '\n'.join(
            [
                '変換対象ファイルが見つかりません。',
                '入力元フォルダ、サブフォルダ設定、対象ファイル形式を確認してください。',
            ]
        )

    if plan.existing_skip_count and plan.existing_skip_count == plan.skipped_count:
        return '\n'.join(
            [
                '対象ファイルはありますが、すべて既存ファイル扱いによりスキップされます。',
                '変換したい場合は「既存ファイルがある場合」を「上書き」または「別名で保存」に変更してください。',
            ]
        )
    if plan.duplicate_skip_count and plan.duplicate_skip_count == plan.skipped_count:
        return '\n'.join(
            [
                '対象ファイルはありますが、出力先の同名衝突によりすべてスキップされます。',
                '「フォルダ構造を保持して出力する」をオンにするか、「既存ファイルがある場合」を「別名で保存」に変更してください。',
            ]
        )

    reasons: list[str] = []
    if plan.existing_skip_count:
        reasons.append('既存ファイル')
    if plan.duplicate_skip_count:
        reasons.append('同名衝突')
    reason_text = 'または'.join(reasons) if reasons else '現在の条件'
    return '\n'.join(
        [
            f'対象ファイルはありますが、{reason_text}によりすべてスキップされます。',
            '変換条件を確認してください。',
        ]
    )


def describe_folder_batch_partial_skip_notice(plan: FolderBatchPlan) -> str:
    """Return a concise explanation when some files will be skipped."""

    if plan.convert_count <= 0 or plan.skipped_count <= 0:
        return ''
    if plan.existing_skip_count and plan.duplicate_skip_count:
        reason = '既存ファイルまたは同名衝突により'
    elif plan.existing_skip_count:
        reason = '既存ファイルがあるため'
    elif plan.duplicate_skip_count:
        reason = '出力先の同名衝突により'
    else:
        reason = '現在の条件により'
    return '\n'.join(
        [
            f'一部のファイルは{reason}スキップされます。',
            '変換予定のファイルのみ処理します。',
        ]
    )


def summarize_folder_batch_plan(plan: FolderBatchPlan) -> list[str]:
    lines = [
        f'変換対象: {plan.total_count} 件',
        f'変換予定: {plan.convert_count} 件',
        f'スキップ予定: {plan.skipped_count} 件',
        f'出力先: {plan.output_root}',
        f'既存ファイルの扱い: {folder_batch_policy_label(plan.existing_policy)}',
    ]
    if plan.existing_skip_count:
        lines.append(f'既存ファイルによるスキップ: {plan.existing_skip_count} 件')
    if plan.duplicate_skip_count:
        lines.append(f'同名衝突によるスキップ: {plan.duplicate_skip_count} 件')
    if plan.renamed_count:
        lines.append(f'別名保存予定: {plan.renamed_count} 件')
    if plan.overwritten_count:
        lines.append(f'上書き予定: {plan.overwritten_count} 件')
    return lines
