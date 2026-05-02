from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from tategakiXTC_gui_studio_logging import cleanup_old_session_logs


class GuiStudioLoggingRegressionTests(unittest.TestCase):
    def _touch_at(self, path: Path, when: datetime) -> None:
        path.write_text(path.name, encoding='utf-8')
        ts = when.timestamp()
        os.utime(path, (ts, ts))

    def test_cleanup_old_session_logs_preserves_active_and_unrelated_files(self) -> None:
        now = datetime(2026, 5, 2, 12, 0, 0)
        with tempfile.TemporaryDirectory() as td:
            log_dir = Path(td)
            active = log_dir / 'tategakiXTC_gui_studio_20260401_000000.log'
            recent_1 = log_dir / 'tategakiXTC_gui_studio_20260502_115900.log'
            recent_2 = log_dir / 'tategakiXTC_gui_studio_20260502_115800.log'
            old = log_dir / 'tategakiXTC_gui_studio_20260301_000000.log'
            unrelated = log_dir / 'debug.log'

            self._touch_at(active, now - timedelta(days=60))
            self._touch_at(recent_1, now - timedelta(minutes=1))
            self._touch_at(recent_2, now - timedelta(minutes=2))
            self._touch_at(old, now - timedelta(days=62))
            self._touch_at(unrelated, now - timedelta(days=90))

            cleanup_old_session_logs(
                log_dir,
                active_log_path=active,
                keep_latest=2,
                max_age_days=30,
                now=now,
            )

            self.assertTrue(active.exists())
            self.assertTrue(recent_1.exists())
            self.assertTrue(recent_2.exists())
            self.assertTrue(unrelated.exists())
            self.assertFalse(old.exists())

    def test_cleanup_old_session_logs_enforces_keep_latest_even_for_recent_logs(self) -> None:
        now = datetime(2026, 5, 2, 12, 0, 0)
        with tempfile.TemporaryDirectory() as td:
            log_dir = Path(td)
            paths = [
                log_dir / f'tategakiXTC_gui_studio_20260502_120{i}00.log'
                for i in range(4)
            ]
            for index, path in enumerate(paths):
                self._touch_at(path, now - timedelta(minutes=3 - index))

            cleanup_old_session_logs(
                log_dir,
                keep_latest=2,
                max_age_days=365,
                now=now,
            )

            self.assertFalse(paths[0].exists())
            self.assertFalse(paths[1].exists())
            self.assertTrue(paths[2].exists())
            self.assertTrue(paths[3].exists())


if __name__ == '__main__':
    unittest.main()
