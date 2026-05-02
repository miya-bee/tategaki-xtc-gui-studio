from __future__ import annotations

"""Dialog fallback helpers for ``tategakiXTC_gui_studio``.

The entry module keeps the public ``MainWindow`` wrapper methods so existing
monkey patches and unbound test calls remain compatible.  This helper module
contains only Qt-object-agnostic control flow and receives Qt callables from the
wrapper, which keeps it lightweight and import-safe.
"""

from typing import Callable

DialogMessageFunc = Callable[[object, str, str], object]
DialogQuestionFunc = Callable[[object, str, str, object, object], object]
StatusMessageFunc = Callable[..., object]
CoerceTextFunc = Callable[[object], str]
OpenFileDialogFunc = Callable[[object, str, str, str], tuple[str, str]]
OpenDirectoryDialogFunc = Callable[[object, str, str], str]
WarningFallbackFunc = Callable[[str, str], object]


def show_warning_dialog_with_status_fallback(
    parent: object,
    dialog_func: object,
    status_func: StatusMessageFunc,
    title: str,
    message: str,
    *,
    duration_ms: int = 5000,
) -> None:
    try:
        if callable(dialog_func):
            dialog_func(parent, title, message)
            return
    except Exception:
        pass
    try:
        status_func(message, duration_ms)
    except Exception:
        pass


def ask_question_dialog_with_status_fallback(
    parent: object,
    dialog_func: object,
    status_func: StatusMessageFunc,
    coerce_text: CoerceTextFunc,
    title: str,
    message: str,
    buttons: object,
    default_button: object,
    *,
    duration_ms: int = 5000,
    fallback_status_message: str = '',
    fallback_answer: object = None,
) -> object:
    try:
        if callable(dialog_func):
            return dialog_func(parent, title, message, buttons, default_button)
    except Exception:
        pass
    status_message = coerce_text(fallback_status_message) or coerce_text(message)
    try:
        status_func(
            status_message,
            duration_ms,
            reuse_existing_message=False,
        )
    except Exception:
        pass
    return fallback_answer


def show_information_dialog_with_status_fallback(
    parent: object,
    dialog_func: object,
    status_func: StatusMessageFunc,
    coerce_text: CoerceTextFunc,
    title: str,
    message: str,
    *,
    duration_ms: int = 5000,
    fallback_status_message: str = '',
) -> None:
    try:
        if callable(dialog_func):
            dialog_func(parent, title, message)
            return
    except Exception:
        pass
    status_message = coerce_text(fallback_status_message) or coerce_text(message)
    try:
        status_func(
            status_message,
            duration_ms,
            reuse_existing_message=False,
        )
    except Exception:
        pass


def show_critical_dialog_with_status_fallback(
    parent: object,
    dialog_func: object,
    status_func: StatusMessageFunc,
    coerce_text: CoerceTextFunc,
    title: str,
    message: str,
    *,
    duration_ms: int = 5000,
    fallback_status_message: str = '',
) -> None:
    try:
        if callable(dialog_func):
            dialog_func(parent, title, message)
            return
    except Exception:
        pass
    status_message = coerce_text(fallback_status_message) or coerce_text(message)
    try:
        status_func(
            status_message,
            duration_ms,
            reuse_existing_message=False,
        )
    except Exception:
        pass


def get_open_file_name_with_status_fallback(
    parent: object,
    dialog_func: object,
    warning_fallback: WarningFallbackFunc,
    coerce_text: CoerceTextFunc,
    title: str,
    start_dir: str,
    filter_text: str,
    *,
    warning_title: str = 'ファイル選択エラー',
    fallback_status_message: str = '',
) -> tuple[str, str]:
    try:
        if callable(dialog_func):
            return dialog_func(parent, title, start_dir, filter_text)
        raise AttributeError('file dialog method is unavailable')
    except Exception as exc:
        detail = coerce_text(exc).strip()
        message = coerce_text(fallback_status_message).strip() or f'{title}ダイアログを開けませんでした。'
        if detail:
            message = f'{message} / {detail}'
        warning_fallback(warning_title, message)
        return '', ''


def get_existing_directory_with_status_fallback(
    parent: object,
    dialog_func: object,
    warning_fallback: WarningFallbackFunc,
    coerce_text: CoerceTextFunc,
    title: str,
    start_dir: str,
    *,
    warning_title: str = 'フォルダ選択エラー',
    fallback_status_message: str = '',
) -> str:
    try:
        if callable(dialog_func):
            return dialog_func(parent, title, start_dir)
        raise AttributeError('directory dialog method is unavailable')
    except Exception as exc:
        detail = coerce_text(exc).strip()
        message = coerce_text(fallback_status_message).strip() or f'{title}ダイアログを開けませんでした。'
        if detail:
            message = f'{message} / {detail}'
        warning_fallback(warning_title, message)
        return ''


__all__ = [
    'ask_question_dialog_with_status_fallback',
    'get_existing_directory_with_status_fallback',
    'get_open_file_name_with_status_fallback',
    'show_critical_dialog_with_status_fallback',
    'show_information_dialog_with_status_fallback',
    'show_warning_dialog_with_status_fallback',
]
