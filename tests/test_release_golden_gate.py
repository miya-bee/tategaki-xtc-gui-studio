from __future__ import annotations

from pathlib import Path

import pytest

import build_release_zip as builder


def test_golden_release_gate_runs_check_script_before_release_build(tmp_path: Path) -> None:
    script = tmp_path / 'tests' / 'generate_golden_images.py'
    script.parent.mkdir(parents=True)
    marker = tmp_path / 'golden_gate_was_run.txt'
    script.write_text(
        'from pathlib import Path\n'
        f'Path({str(marker)!r}).write_text("ok", encoding="utf-8")\n',
        encoding='utf-8',
    )

    builder._run_golden_release_gate(tmp_path)

    assert marker.read_text(encoding='utf-8') == 'ok'


def test_golden_release_gate_aborts_when_clean_check_fails(tmp_path: Path) -> None:
    script = tmp_path / 'tests' / 'generate_golden_images.py'
    script.parent.mkdir(parents=True)
    script.write_text(
        'import sys\n'
        'print("golden mismatch")\n'
        'raise SystemExit(3)\n',
        encoding='utf-8',
    )

    with pytest.raises(SystemExit) as exc_info:
        builder._run_golden_release_gate(tmp_path)

    message = str(exc_info.value)
    assert 'Golden release gate failed' in message
    assert 'golden mismatch' in message
