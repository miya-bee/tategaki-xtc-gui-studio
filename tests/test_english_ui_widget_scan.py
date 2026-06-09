from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Iterable

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

JAPANESE_RE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')
ALLOWED_JAPANESE_TOKENS = (
    # English help intentionally explains this glyph-position target as the
    # kanji numeral itself.  Keep the exception narrow so real Japanese UI text
    # still fails the scan.
    '一',
)
_CHILD_ARG = '--run-english-ui-widget-scan-child'
_SKIP_EXIT_CODE = 77
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _contains_disallowed_japanese(value: str) -> bool:
    stripped = value
    for token in ALLOWED_JAPANESE_TOKENS:
        stripped = stripped.replace(token, '')
    return bool(JAPANESE_RE.search(stripped))


def _safe_text_values(widget: object) -> Iterable[tuple[str, str]]:
    for attr in (
        'text',
        'toolTip',
        'statusTip',
        'whatsThis',
        'placeholderText',
        'accessibleName',
        'accessibleDescription',
        'windowTitle',
    ):
        getter = getattr(widget, attr, None)
        if not callable(getter):
            continue
        try:
            value = getter()
        except TypeError:
            continue
        except RuntimeError:
            continue
        if isinstance(value, str) and value.strip():
            yield attr, value

    item_text = getattr(widget, 'itemText', None)
    count_getter = getattr(widget, 'count', None)
    if callable(item_text) and callable(count_getter):
        try:
            count = int(count_getter())
        except Exception:
            count = 0
        for index in range(count):
            try:
                value = item_text(index)
            except Exception:
                continue
            if isinstance(value, str) and value.strip():
                yield f'itemText[{index}]', value

    tab_text = getattr(widget, 'tabText', None)
    if callable(tab_text) and callable(count_getter):
        try:
            count = int(count_getter())
        except Exception:
            count = 0
        for index in range(count):
            try:
                value = tab_text(index)
            except Exception:
                continue
            if isinstance(value, str) and value.strip():
                yield f'tabText[{index}]', value


def _iter_menu_text_objects(menu: object) -> Iterable[object]:
    """Yield a popup menu, its section/action labels, and nested submenus."""

    seen: set[int] = set()

    def walk(obj: object) -> Iterable[object]:
        ident = id(obj)
        if ident in seen:
            return
        seen.add(ident)
        yield obj
        actions_getter = getattr(obj, 'actions', None)
        if not callable(actions_getter):
            return
        try:
            actions = list(actions_getter())
        except Exception:
            return
        for action in actions:
            yield action
            menu_getter = getattr(action, 'menu', None)
            if not callable(menu_getter):
                continue
            try:
                submenu = menu_getter()
            except Exception:
                submenu = None
            if submenu is not None:
                yield from walk(submenu)

    yield from walk(menu)


def _dependency_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


def _run_scan_child() -> int:
    if not _dependency_available('PySide6') or not _dependency_available('PIL'):
        print('SKIP: real PySide6/Pillow offscreen UI scan requires installed GUI dependencies')
        return _SKIP_EXIT_CODE

    project_root = str(_PROJECT_ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from PySide6.QtWidgets import QApplication, QWidget
    import tategakiXTC_gui_studio as studio

    app = QApplication.instance() or QApplication([])
    original_settings_file = studio.SETTINGS_FILE
    with tempfile.TemporaryDirectory() as tmpdir:
        settings_file = Path(tmpdir) / 'tategakiXTC_gui_studio.ini'
        settings_file.write_text('[General]\nui_language=en\n', encoding='utf-8')
        studio.SETTINGS_FILE = settings_file
        window = None
        try:
            window = studio.MainWindow()
            if window.current_ui_language_value() != 'en':
                print(
                    json.dumps(
                        {
                            'error': 'English UI setup failed',
                            'current_ui_language': getattr(window, 'current_ui_language', None),
                            'current_ui_language_value': window.current_ui_language_value(),
                        },
                        ensure_ascii=False,
                    )
                )
                return 1
            expected_title = f'TategakiXTC GUI Studio {studio.APP_VERSION}'
            if window.windowTitle() != expected_title:
                print(
                    json.dumps(
                        {
                            'error': 'Unexpected English window title',
                            'actual': window.windowTitle(),
                            'expected': expected_title,
                        },
                        ensure_ascii=False,
                    )
                )
                return 1

            # Exercise runtime re-sync paths that can overwrite translated
            # construction-time values, including the right-pane help tooltip.
            window._apply_main_view_mode_ui('font')
            window._apply_main_view_mode_ui('device')
            window._update_language_restart_note_label('en')

            # The gear/display settings popup is built lazily when opened, so
            # it is not covered by the startup widget tree alone.  Capture the
            # menu before exec() blocks and include section/action text in the
            # same untranslated-Japanese scan.
            captured_menus: list[object] = []

            def _capture_menu_exec(menu: object, *_args: object, **_kwargs: object) -> None:
                captured_menus.append(menu)
                return None

            with mock.patch.object(studio.QMenu, 'exec', _capture_menu_exec):
                window.show_display_settings_popup()

            offenders: list[str] = []
            objects: list[object] = [window] + list(window.findChildren(QWidget))
            for menu in captured_menus:
                objects.extend(_iter_menu_text_objects(menu))
            for widget in objects:
                object_name_getter = getattr(widget, 'objectName', None)
                try:
                    object_name = object_name_getter() if callable(object_name_getter) else ''
                except Exception:
                    object_name = ''
                widget_name = widget.__class__.__name__
                widget_label = f'{widget_name}#{object_name}' if object_name else widget_name
                for source, value in _safe_text_values(widget):
                    if _contains_disallowed_japanese(value):
                        offenders.append(f'{widget_label}.{source}: {value!r}')
            if offenders:
                print(
                    json.dumps(
                        {
                            'error': 'Untranslated Japanese remained in English UI widgets',
                            'offenders': offenders[:50],
                            'offender_count': len(offenders),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
                return 1
            print('PASS: English UI real-widget scan completed with no untranslated Japanese')
            return 0
        finally:
            if window is not None:
                window.close()
            studio.SETTINGS_FILE = original_settings_file
            app.processEvents()


class EnglishUiWidgetScanTests(unittest.TestCase):
    def test_english_startup_visible_widget_text_has_no_untranslated_japanese(self) -> None:
        env = os.environ.copy()
        env.setdefault('QT_QPA_PLATFORM', 'offscreen')
        project_root = str(_PROJECT_ROOT)
        current_pythonpath = env.get('PYTHONPATH')
        env['PYTHONPATH'] = (
            project_root
            if not current_pythonpath
            else project_root + os.pathsep + current_pythonpath
        )
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), _CHILD_ARG],
            cwd=str(_PROJECT_ROOT),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if result.returncode == _SKIP_EXIT_CODE:
            self.skipTest((result.stdout or result.stderr).strip())
        self.assertEqual(
            result.returncode,
            0,
            'English UI real-widget scan subprocess failed.\n'
            f'--- stdout ---\n{result.stdout}\n'
            f'--- stderr ---\n{result.stderr}',
        )


if __name__ == '__main__':
    if _CHILD_ARG in sys.argv:
        raise SystemExit(_run_scan_child())
    unittest.main()
