from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.studio_import_helper import load_studio_module


class StartupLoggingRegressionTests(unittest.TestCase):
    def _reset_logger(self, studio: object) -> logging.Logger:
        logger = logging.getLogger(getattr(studio, 'APP_LOGGER_NAME'))
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
        if hasattr(logger, '_tategaki_configured'):
            delattr(logger, '_tategaki_configured')
        setattr(studio, 'ACTIVE_LOG_DIR', None)
        setattr(studio, 'SESSION_LOG_PATH', None)
        return logger

    def test_configure_logging_falls_back_when_app_logs_dir_cannot_create_files(self) -> None:
        studio = load_studio_module(force_reload=True)
        logger = self._reset_logger(studio)
        with tempfile.TemporaryDirectory() as tmpdir:
            app_log_dir = Path(tmpdir) / 'readonly_logs'
            fallback_log_dir = Path(tmpdir) / 'fallback_logs'

            def accepts_log_file(path: Path) -> bool:
                return Path(path) == fallback_log_dir

            try:
                with mock.patch.object(studio, 'LOG_DIR', app_log_dir), \
                     mock.patch.object(studio, 'FALLBACK_LOG_DIR', fallback_log_dir), \
                     mock.patch.object(studio, '_log_dir_accepts_log_file', side_effect=accepts_log_file):
                    configured = studio._configure_app_logging()

                self.assertIs(configured, logger)
                self.assertEqual(getattr(studio, 'ACTIVE_LOG_DIR'), fallback_log_dir)
                self.assertIsNotNone(getattr(studio, 'SESSION_LOG_PATH'))
                self.assertTrue(str(getattr(studio, 'SESSION_LOG_PATH')).startswith(str(fallback_log_dir)))
                self.assertTrue(any(isinstance(handler, logging.FileHandler) for handler in logger.handlers))
            finally:
                # Release the session FileHandler before the TemporaryDirectory is
                # removed; otherwise Windows cannot delete the still-open .log file
                # (PermissionError [WinError 32]).
                self._reset_logger(studio)

    def test_configure_logging_continues_with_stream_only_when_no_log_dir_is_writable(self) -> None:
        studio = load_studio_module(force_reload=True)
        logger = self._reset_logger(studio)
        with tempfile.TemporaryDirectory() as tmpdir:
            app_log_dir = Path(tmpdir) / 'readonly_logs'
            fallback_log_dir = Path(tmpdir) / 'fallback_logs'
            with mock.patch.object(studio, 'LOG_DIR', app_log_dir), \
                 mock.patch.object(studio, 'FALLBACK_LOG_DIR', fallback_log_dir), \
                 mock.patch.object(studio, '_log_dir_accepts_log_file', return_value=False):
                configured = studio._configure_app_logging()

            self.assertIs(configured, logger)
            self.assertIsNone(getattr(studio, 'ACTIVE_LOG_DIR'))
            self.assertIsNone(getattr(studio, 'SESSION_LOG_PATH'))
            self.assertTrue(any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers))
            self.assertFalse(any(isinstance(handler, logging.FileHandler) for handler in logger.handlers))

    def test_session_log_path_for_display_does_not_raise_when_no_log_dir_is_writable(self) -> None:
        # Building the log tab must not crash after a stderr-only fallback, even
        # though ``_resolve_session_log_path`` itself raises when neither log dir
        # is writable.
        studio = load_studio_module(force_reload=True)
        self._reset_logger(studio)
        with tempfile.TemporaryDirectory() as tmpdir:
            app_log_dir = Path(tmpdir) / 'readonly_logs'
            fallback_log_dir = Path(tmpdir) / 'fallback_logs'
            try:
                with mock.patch.object(studio, 'LOG_DIR', app_log_dir), \
                     mock.patch.object(studio, 'FALLBACK_LOG_DIR', fallback_log_dir), \
                     mock.patch.object(studio, '_log_dir_accepts_log_file', return_value=False):
                    studio._configure_app_logging()
                    with self.assertRaises(Exception):
                        studio._resolve_session_log_path()
                    display_path = studio._session_log_path_for_display()
                self.assertEqual(Path(display_path), app_log_dir)
            finally:
                self._reset_logger(studio)


if __name__ == '__main__':
    unittest.main()
