from __future__ import annotations

import unittest

from tests.studio_import_helper import load_studio_module


class _UrlStub:
    def __init__(self, path: str) -> None:
        self._path = path

    def toLocalFile(self) -> str:
        return self._path


class _MimeStub:
    def __init__(self, paths: list[str] | None = None, text: str = '') -> None:
        self._paths = paths or []
        self._text = text

    def urls(self) -> list[_UrlStub]:
        return [_UrlStub(path) for path in self._paths]

    def text(self) -> str:
        return self._text


class _DropEventStub:
    def __init__(self, mime: _MimeStub) -> None:
        self._mime = mime
        self.accepted = False

    def mimeData(self) -> _MimeStub:
        return self._mime

    def acceptProposedAction(self) -> None:
        self.accepted = True


class SourceDropLineEditRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.studio = load_studio_module()

    def test_source_drop_line_edit_emits_first_local_path(self) -> None:
        line_edit = self.studio.SourceDropLineEdit()
        dropped: list[str] = []
        line_edit.sourcePathDropped.connect(dropped.append)

        event = _DropEventStub(_MimeStub([r'C:\books\sample.epub', r'C:\books\other.txt']))
        line_edit.dropEvent(event)

        self.assertTrue(event.accepted)
        self.assertEqual(dropped, [r'C:\books\sample.epub'])

    def test_source_drop_line_edit_accepts_text_fallback(self) -> None:
        line_edit = self.studio.SourceDropLineEdit()
        dropped: list[str] = []
        line_edit.sourcePathDropped.connect(dropped.append)

        event = _DropEventStub(_MimeStub([], text='"C:/books/sample.txt"'))
        line_edit.dropEvent(event)

        self.assertTrue(event.accepted)
        self.assertEqual(dropped, ['C:/books/sample.txt'])

    def test_target_path_drop_uses_existing_target_refresh_route(self) -> None:
        window = self.studio.MainWindow.__new__(self.studio.MainWindow)

        class _TargetEdit:
            def __init__(self) -> None:
                self.value = ''

            def blockSignals(self, _blocked: bool) -> bool:
                return False

            def setText(self, value: str) -> None:
                self.value = value

        target_edit = _TargetEdit()
        calls: list[object] = []
        window.target_edit = target_edit
        window._update_top_status = lambda: calls.append('status')
        window.save_ui_state = lambda: calls.append('save')
        window._show_ui_status_message_unless_render_failure_visible = lambda message, timeout: calls.append((message, timeout))
        window._schedule_target_preview_refresh = lambda *, reset_page: calls.append(('preview', reset_page))

        self.studio.MainWindow._apply_dropped_target_path(window, r'C:\books\sample.epub')

        self.assertEqual(target_edit.value, r'C:\books\sample.epub')
        self.assertIn('status', calls)
        self.assertIn('save', calls)
        self.assertIn(('preview', True), calls)


if __name__ == '__main__':
    unittest.main()
