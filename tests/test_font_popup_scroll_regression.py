from __future__ import annotations

import unittest

from tests.studio_import_helper import load_studio_module


class _FakeScrollBar:
    def __init__(self, minimum: int = 0, value: int = 50) -> None:
        self._minimum = minimum
        self.value = value

    def minimum(self) -> int:
        return self._minimum

    def setValue(self, value: int) -> None:
        self.value = value


class _FakeView:
    def __init__(self) -> None:
        self.scrolled_to_top = False
        self.scroll_bar = _FakeScrollBar(minimum=3, value=40)

    def scrollToTop(self) -> None:
        self.scrolled_to_top = True

    def verticalScrollBar(self) -> _FakeScrollBar:
        return self.scroll_bar


class _FakeCombo:
    def __init__(self) -> None:
        self._view = _FakeView()

    def view(self) -> _FakeView:
        return self._view


class FontPopupScrollRegressionTests(unittest.TestCase):
    def test_scroll_helper_moves_popup_list_to_top(self) -> None:
        studio = load_studio_module(force_reload=True)
        combo = _FakeCombo()

        studio._scroll_combo_popup_to_top_now(combo)

        self.assertTrue(combo.view().scrolled_to_top)
        self.assertEqual(combo.view().scroll_bar.value, 3)


    def test_reset_popup_scroll_to_top_runs_sync_before_timers(self) -> None:
        studio = load_studio_module(force_reload=True)
        combo = _FakeCombo()
        calls = []

        original = studio._scroll_combo_popup_to_top_now
        had_single_shot = hasattr(studio.QTimer, 'singleShot')
        original_single_shot = getattr(studio.QTimer, 'singleShot', None)
        try:
            def fake_scroll(target) -> None:
                calls.append(target)
                original(target)

            def fake_single_shot(ms, callback) -> None:
                calls.append(f'timer:{ms}')

            studio._scroll_combo_popup_to_top_now = fake_scroll
            studio.QTimer.singleShot = fake_single_shot

            studio.FontPopupTopComboBox._reset_popup_scroll_to_top(combo)
        finally:
            studio._scroll_combo_popup_to_top_now = original
            if had_single_shot:
                studio.QTimer.singleShot = original_single_shot
            else:
                delattr(studio.QTimer, 'singleShot')

        self.assertIs(calls[0], combo)
        self.assertIn('timer:0', calls)
        self.assertIn('timer:25', calls)
        self.assertTrue(combo.view().scrolled_to_top)
        self.assertEqual(combo.view().scroll_bar.value, 3)

    def test_reset_popup_scroll_to_top_adds_longer_timer_for_first_popup(self) -> None:
        studio = load_studio_module(force_reload=True)
        combo = _FakeCombo()
        combo._first_popup_shown = True
        timers = []

        had_single_shot = hasattr(studio.QTimer, 'singleShot')
        original_single_shot = getattr(studio.QTimer, 'singleShot', None)
        try:
            def fake_single_shot(ms, callback) -> None:
                timers.append(ms)

            studio.QTimer.singleShot = fake_single_shot

            studio.FontPopupTopComboBox._reset_popup_scroll_to_top(combo)
        finally:
            if had_single_shot:
                studio.QTimer.singleShot = original_single_shot
            else:
                delattr(studio.QTimer, 'singleShot')

        self.assertEqual(timers, [0, 25, 80])

    def test_startup_font_combo_scroll_reset_scrolls_now_and_schedules_delayed_reset(self) -> None:
        studio = load_studio_module(force_reload=True)
        combo = _FakeCombo()
        delayed_calls = []

        class _Window:
            def __init__(self) -> None:
                self.font_combo = combo

        window = _Window()
        original = studio._scroll_combo_popup_to_top_now
        had_single_shot = hasattr(studio.QTimer, 'singleShot')
        original_single_shot = getattr(studio.QTimer, 'singleShot', None)
        try:
            def fake_scroll(target) -> None:
                delayed_calls.append(('scroll', target))
                original(target)

            def fake_single_shot(ms, callback) -> None:
                delayed_calls.append(('timer', ms, callback))

            combo._reset_popup_scroll_to_top = lambda: delayed_calls.append(('reset', combo))
            studio._scroll_combo_popup_to_top_now = fake_scroll
            studio.QTimer.singleShot = fake_single_shot

            studio.MainWindow._startup_font_combo_scroll_reset(window)
        finally:
            studio._scroll_combo_popup_to_top_now = original
            if had_single_shot:
                studio.QTimer.singleShot = original_single_shot
            else:
                delattr(studio.QTimer, 'singleShot')

        self.assertEqual(delayed_calls[0], ('scroll', combo))
        self.assertEqual(delayed_calls[1][0:2], ('timer', 50))
        self.assertIs(delayed_calls[1][2], combo._reset_popup_scroll_to_top)


if __name__ == '__main__':
    unittest.main()
