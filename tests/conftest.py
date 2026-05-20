from __future__ import annotations

import pytest

from tests.studio_import_helper import restore_qt_test_state


def pytest_runtest_setup(item):  # type: ignore[no-untyped-def]
    """Restore Qt class-level test state before unittest setUpClass/setUp."""
    restore_qt_test_state()


def pytest_runtest_teardown(item, nextitem):  # type: ignore[no-untyped-def]
    """Restore Qt class-level test state after each test item."""
    restore_qt_test_state()


@pytest.fixture(autouse=True)
def restore_mutable_qt_test_state():
    """Keep class-level Qt monkey patches from leaking between tests."""
    restore_qt_test_state()
    yield
    restore_qt_test_state()
