from __future__ import annotations

"""Qt-free logging helpers for tategakiXTC GUI Studio."""

from datetime import datetime, timedelta
from pathlib import Path


DEFAULT_LOG_RETENTION_DAYS = 30
DEFAULT_LOG_RETENTION_MAX_FILES = 50
DEFAULT_SESSION_LOG_PATTERN = 'tategakiXTC_gui_studio_*.log'


def _same_path(left: Path, right: Path) -> bool:
    """Best-effort path identity check that tolerates missing files."""
    try:
        return left.resolve() == right.resolve()
    except Exception:
        return left == right


def cleanup_old_session_logs(
    log_dir: Path,
    *,
    active_log_path: Path | None = None,
    keep_latest: int = DEFAULT_LOG_RETENTION_MAX_FILES,
    max_age_days: int = DEFAULT_LOG_RETENTION_DAYS,
    pattern: str = DEFAULT_SESSION_LOG_PATTERN,
    now: datetime | None = None,
) -> None:
    """Remove stale GUI session logs while preserving the active session log."""
    try:
        keep_latest = max(0, int(keep_latest))
        max_age_days = max(0, int(max_age_days))
        current_time = now or datetime.now()
        cutoff_ts = (current_time - timedelta(days=max_age_days)).timestamp()
        candidates: list[tuple[float, Path]] = []
        for path in log_dir.glob(pattern):
            if not path.is_file():
                continue
            if active_log_path is not None and _same_path(path, active_log_path):
                continue
            try:
                candidates.append((path.stat().st_mtime, path))
            except Exception:
                continue
        candidates.sort(key=lambda item: item[0], reverse=True)
        for index, (mtime, path) in enumerate(candidates):
            if index < keep_latest and mtime >= cutoff_ts:
                continue
            try:
                path.unlink()
            except Exception:
                continue
    except Exception:
        return


__all__ = [
    'DEFAULT_LOG_RETENTION_DAYS',
    'DEFAULT_LOG_RETENTION_MAX_FILES',
    'DEFAULT_SESSION_LOG_PATTERN',
    'cleanup_old_session_logs',
]
