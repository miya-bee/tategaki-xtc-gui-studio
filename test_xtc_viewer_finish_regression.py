from tests.studio_import_helper import load_studio_module

studio = load_studio_module(force_reload=True)
MainWindow = studio.MainWindow


class DummyWindow:
    def __init__(self):
        self.active_cleared = False
        self.terminal_calls = []
        self.logs = []
        self.populate_calls = []
        self.cleared_loaded = False
        self.cleared_summary = None
        self.bottom_tabs = type('Tabs', (), {'index': None, 'setCurrentIndex': lambda self, idx: setattr(self, 'index', idx)})()
        self.status_bar_calls = []

    def _clear_active_conversion_run_token(self):
        self.active_cleared = True

    def _apply_conversion_terminal_state(self, message, **kwargs):
        self.terminal_calls.append((message, kwargs))

    def _show_conversion_results(self, *_args, **_kwargs):
        raise RuntimeError('boom')

    def _render_failure_status_message(self, title, exc):
        return f'{title}: {exc}'

    def append_log(self, text, reflect_in_status=True):
        self.logs.append((text, reflect_in_status))

    def populate_results(self, converted_files, summary_lines):
        self.populate_calls.append((list(converted_files), summary_lines))

    def _clear_loaded_xtc_state(self):
        self.cleared_loaded = True

    def _clear_results_view(self, summary_text=None):
        self.cleared_summary = summary_text

    def statusBar(self):
        outer = self

        class _Status:
            def showMessage(self, text, timeout):
                outer.status_bar_calls.append((text, timeout))

        return _Status()


def test_on_conversion_finished_result_display_failure_does_not_crash_and_keeps_results_visible():
    dummy = DummyWindow()
    MainWindow.on_conversion_finished(dummy, {
        'message': 'done',
        'stopped': False,
        'converted_files': ['exports/book.xtc'],
        'summary_lines': ['保存 1 件'],
    })

    assert dummy.active_cleared is True
    assert dummy.terminal_calls
    assert dummy.logs == [('変換結果表示エラー: boom', False)]
    assert dummy.populate_calls == [(['exports/book.xtc'], ['保存 1 件', '警告: 変換結果表示エラー: boom'])]
    assert dummy.cleared_loaded is True
    assert dummy.bottom_tabs.index == studio.RESULT_TAB_INDEX


def test_on_conversion_finished_result_display_failure_emits_all_normalized_warnings():
    dummy = DummyWindow()
    emitted = []
    dummy._emit_postprocess_warning = lambda message, duration_ms=5000: emitted.append((message, duration_ms))
    MainWindow.on_conversion_finished(dummy, {
        'message': 'done',
        'stopped': False,
        'converted_files': ['exports/book.xtc'],
        'summary_lines': ['保存 1 件'],
    })

    assert emitted == [('変換結果表示エラー: boom', 5000)]
