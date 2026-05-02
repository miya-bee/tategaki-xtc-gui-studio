from __future__ import annotations

import io
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

from tests.golden_case_registry import CASE_SPECS


UPDATE_GOLDEN_ENV = 'TATEGAKI_UPDATE_GOLDEN'
UPDATE_GOLDEN_ARG = '--update-golden'


def _image_tools():
    from PIL import Image, ImageChops, ImageStat

    return Image, ImageChops, ImageStat


def _case_specs() -> Dict[str, Dict]:
    return CASE_SPECS


def _golden_dir() -> Path:
    from tests.golden_case_registry import GOLDEN_DIR

    return GOLDEN_DIR


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _render_case(name: str):
    from tests.image_golden_cases import render_case

    return render_case(name)


def _resolve_case_thresholds(spec: Dict) -> Dict[str, float]:
    from tests.golden_case_registry import resolve_case_thresholds

    return resolve_case_thresholds(spec)


def reference_font_path() -> Path:
    return _project_root() / 'Font' / 'NotoSansJP-Regular.ttf'


def has_bundled_reference_font() -> bool:
    return reference_font_path().exists()


def _has_bundled_reference_font() -> bool:
    return has_bundled_reference_font()


def should_update_goldens(argv: List[str] | None = None, environ: Dict[str, str] | None = None) -> bool:
    argv = list(sys.argv if argv is None else argv)
    environ = os.environ if environ is None else environ
    if UPDATE_GOLDEN_ARG in argv:
        return True
    value = str(environ.get(UPDATE_GOLDEN_ENV, '')).strip().lower()
    return value in {'1', 'true', 'yes', 'on'}


def strip_update_flag(argv: List[str] | None = None) -> List[str]:
    values = list(sys.argv if argv is None else argv)
    return [value for value in values if value != UPDATE_GOLDEN_ARG]


def to_binary_mask(img):
    gray = img.convert('L')
    return gray.point(lambda p: 0 if p < 250 else 255, 'L')


def golden_path(name: str) -> Path:
    return _golden_dir() / f'{name}.png'


def load_golden(name: str):
    path = golden_path(name)
    if not path.exists():
        return None
    Image, _, _ = _image_tools()
    return Image.open(path).convert('L')


def save_golden(name: str, img) -> Path:
    path = golden_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    _render_case_png_bytes.cache_clear()
    return path


@lru_cache(maxsize=None)
def _render_case_png_bytes(name: str) -> bytes:
    img = _render_case(name)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def compare_case(name: str) -> Dict[str, object]:
    case_specs = _case_specs()
    spec = case_specs[name]
    thresholds = _resolve_case_thresholds(spec)
    if not _has_bundled_reference_font():
        return {
            'name': name,
            'spec': spec,
            'thresholds': thresholds,
            'actual': None,
            'expected': None,
            'missing': False,
            'size_matches': True,
            'diff_ratio': 0.0,
            'mean_abs': 0.0,
            'stale': False,
            'skipped': True,
            'reason': '同梱基準フォントが無いためゴールデン比較を省略しました。',
        }
    Image, ImageChops, ImageStat = _image_tools()
    actual = to_binary_mask(Image.open(io.BytesIO(_render_case_png_bytes(name))).convert('L'))
    expected = load_golden(name)
    if expected is None:
        return {
            'name': name,
            'spec': spec,
            'thresholds': thresholds,
            'actual': actual,
            'expected': None,
            'missing': True,
            'size_matches': False,
            'diff_ratio': 1.0,
            'mean_abs': 255.0,
            'stale': True,
            'skipped': False,
            'reason': '',
        }
    expected = to_binary_mask(expected)
    size_matches = actual.size == expected.size
    if size_matches:
        diff = ImageChops.difference(actual, expected)
        diff_bbox = diff.getbbox()
        nonzero_count = 0
        if diff_bbox is not None:
            nonzero_count = sum(diff.histogram()[1:])
        total_pixels = actual.size[0] * actual.size[1]
        diff_ratio = nonzero_count / float(total_pixels)
        mean_abs = ImageStat.Stat(diff).mean[0]
    else:
        diff_ratio = 1.0
        mean_abs = 255.0
    stale = (not size_matches) or diff_ratio > thresholds['threshold_ratio'] or mean_abs > thresholds['threshold_mean']
    return {
        'name': name,
        'spec': spec,
        'thresholds': thresholds,
        'actual': actual,
        'expected': expected,
        'missing': False,
        'size_matches': size_matches,
        'diff_ratio': diff_ratio,
        'mean_abs': mean_abs,
        'stale': stale,
        'skipped': False,
        'reason': '',
    }


def refresh_case(name: str) -> Path:
    result = compare_case(name)
    if result.get('skipped') or result.get('actual') is None:
        raise RuntimeError(str(result.get('reason') or 'ゴールデン画像を生成できませんでした。'))
    return save_golden(name, result['actual'])


def summarize_result(result: Dict[str, object]) -> str:
    name = str(result['name'])
    if result.get('skipped'):
        return f"{name}: {str(result.get('reason') or '').strip()}"
    if result['missing']:
        return f'{name}: ゴールデン画像がありません'
    if not result['size_matches']:
        actual = result['actual']
        expected = result['expected']
        return f'{name}: 画像サイズが異なります ({actual.size} != {expected.size})'
    profile_name = result['spec'].get('threshold_profile', 'custom')
    return (
        f"{name}: profile={profile_name}, "
        f"diff_ratio={float(result['diff_ratio']):.4f} / {float(result['thresholds']['threshold_ratio']):.4f}, "
        f"mean_abs={float(result['mean_abs']):.4f} / {float(result['thresholds']['threshold_mean']):.4f}"
    )


def _format_golden_command(mode: str, case_names: List[str] | None = None) -> str:
    parts = [r'.venv\Scripts\python.exe', '-B', r'tests\generate_golden_images.py', mode]
    if not case_names:
        return ' '.join(parts)
    for name in normalize_case_names(case_names):
        parts.extend(['--case', name])
    return ' '.join(parts)


def format_golden_check_command(case_names: List[str] | None = None) -> str:
    return _format_golden_command('--check', case_names)


def format_golden_update_command(case_names: List[str] | None = None) -> str:
    return _format_golden_command('--update', case_names)


def format_golden_list_stale_command(case_names: List[str] | None = None) -> str:
    return _format_golden_command('--list-stale', case_names)


def _format_golden_command_block(mode: str, case_names: List[str] | None = None) -> str:
    lines = [
        r'.venv\Scripts\python.exe -B ^',
        r'  tests\generate_golden_images.py ^',
    ]
    names = normalize_case_names(case_names) if case_names else []
    if names:
        lines.append(f'  {mode} ^')
        for index, name in enumerate(names):
            suffix = ' ^' if index < len(names) - 1 else ''
            lines.append(f'  --case {name}{suffix}')
    else:
        lines.append(f'  {mode}')
    return '\n'.join(lines)


def format_golden_check_command_block(case_names: List[str] | None = None) -> str:
    return _format_golden_command_block('--check', case_names)


def format_golden_update_command_block(case_names: List[str] | None = None) -> str:
    return _format_golden_command_block('--update', case_names)


def format_golden_list_stale_command_block(case_names: List[str] | None = None) -> str:
    return _format_golden_command_block('--list-stale', case_names)


def describe_reference_font_next_check(case_names: List[str] | None = None) -> str:
    title = '実差分確認コマンド:'
    if not has_bundled_reference_font():
        title = 'フォント配置後の実差分確認コマンド:'
    return '\n'.join([
        title,
        format_golden_list_stale_command_block(case_names),
    ])


def stale_case_results(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [result for result in results if result.get('stale') and not result.get('skipped')]


def stale_case_names(results: List[Dict[str, object]]) -> List[str]:
    return [str(result['name']) for result in stale_case_results(results)]


def skipped_case_results(results: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [result for result in results if result.get('skipped')]


def skipped_case_names(results: List[Dict[str, object]]) -> List[str]:
    return [str(result['name']) for result in skipped_case_results(results)]


def describe_skipped_case_summary(case_names: List[str] | None = None) -> str:
    names = list(case_names or [])
    return f'比較省略ケース数: {len(names)}件'


def describe_skipped_case_names(case_names: List[str] | None = None) -> str:
    names = list(case_names or [])
    if not names:
        return '比較省略ケース: なし'
    return f"比較省略ケース: {', '.join(names)}"


def describe_reference_font_skip_hint() -> str:
    return '実差分確認には Font/NotoSansJP-Regular.ttf を配置してから再実行してください。'


def describe_reference_font_ready_hint() -> str:
    return '基準フォントが配置済みです。実差分確認を実行できます。'


def reference_font_status_code() -> str:
    return 'ready' if has_bundled_reference_font() else 'missing'


def describe_reference_font_action_hint() -> str:
    if has_bundled_reference_font():
        return describe_reference_font_ready_hint()
    return describe_reference_font_skip_hint()


def describe_reference_font_status() -> str:
    rel = reference_font_path().relative_to(_project_root())
    has_font = has_bundled_reference_font()
    status = 'あり' if has_font else 'なし'
    availability = '可能' if has_font else '不可'
    return '\n'.join([
        f'基準フォント: {rel.as_posix()}',
        f'状態: {status}',
        f'状態コード: {reference_font_status_code()}',
        f'実差分確認: {availability}',
    ])


def describe_reference_font_status_line() -> str:
    return f'基準フォント状態コード: {reference_font_status_code()}'


def describe_stale_case_summary(case_names: List[str] | None = None) -> str:
    names = list(case_names or [])
    return f'差分ケース数: {len(names)}件'


def describe_stale_case_names(case_names: List[str] | None = None) -> str:
    names = list(case_names or [])
    if not names:
        return '差分ケース: なし'
    return f"差分ケース: {', '.join(names)}"


def describe_golden_case_scope(case_names: List[str] | None = None) -> str:
    selected = normalize_case_names(case_names)
    if not case_names:
        return f'対象ケース: 全ケース ({len(selected)}件)'
    return f"対象ケース: {', '.join(selected)}"


def normalize_case_names(case_names: List[str] | None = None) -> List[str]:
    case_specs = _case_specs()
    if not case_names:
        return list(case_specs)
    selected: List[str] = []
    seen: set[str] = set()
    missing: List[str] = []
    for raw_name in case_names:
        name = str(raw_name).strip()
        if not name:
            continue
        if name not in case_specs:
            missing.append(name)
            continue
        if name in seen:
            continue
        selected.append(name)
        seen.add(name)
    if missing:
        raise KeyError(f"Unknown golden case(s): {', '.join(missing)}")
    return selected


def check_cases(case_names: List[str] | None = None) -> List[Dict[str, object]]:
    return [compare_case(name) for name in normalize_case_names(case_names)]


def check_all_cases() -> List[Dict[str, object]]:
    return check_cases()


def update_stale_case_results(results: List[Dict[str, object]]) -> List[Path]:
    updated: List[Path] = []
    for result in stale_case_results(results):
        actual = result.get('actual')
        if actual is None:
            continue
        updated.append(save_golden(str(result['name']), actual))
    return updated


def update_stale_cases(case_names: List[str] | None = None) -> List[Path]:
    return update_stale_case_results(check_cases(case_names))


def update_all_stale_cases() -> List[Path]:
    return update_stale_cases()
