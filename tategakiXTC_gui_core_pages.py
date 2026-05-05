"""
tategakiXTC_gui_core_pages.py — PageEntry / XTC 書き出し pipeline

`tategakiXTC_gui_core.py` から分離した、描画済みページを XTC-family
コンテナへ流し込む共有 helper。互換性維持のため、gui_core 側の
re-export / 既存テストの monkey patch を各入口で同期する。
"""
from __future__ import annotations

import os
import struct
import tempfile
from pathlib import Path
from typing import Any, Callable, Sequence, cast

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals'}
_CORE_SYNC_VERSION = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch を page pipeline 実装へ反映する。"""
    global _CORE_SYNC_VERSION
    version = core_sync_version(_core)
    if not force and _CORE_SYNC_VERSION == version:
        return
    for _name, _value in vars(_core).items():
        if _name.startswith('__') or _name in _CORE_SYNC_EXCLUDED_NAMES:
            continue
        globals()[_name] = _value
    _CORE_SYNC_VERSION = version


_refresh_core_globals()


# ==========================================
# --- PageEntry / XTC 書き出し pipeline ---
# ==========================================

def _make_page_entry(image: Image.Image, page_args: ConversionArgs | None = None, label: str = '本文ページ') -> PageEntry:
    _refresh_core_globals()
    return {
        'image': image,
        'page_args': page_args,
        'label': label,
    }


def _resolve_page_entry(entry: PageEntryLike, default_args: ConversionArgs) -> tuple[Image.Image | None, ConversionArgs, str]:
    _refresh_core_globals()
    if isinstance(entry, dict):
        return cast(Image.Image | None, entry.get('image')), cast(ConversionArgs, entry.get('page_args') or default_args), str(entry.get('label') or 'ページ')
    return cast(Image.Image, entry), default_args, 'ページ'


def _append_page_entries_to_spool(page_entries: Sequence[PageEntryLike], spooled_pages: 'XTCSpooledPages', args: ConversionArgs, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None,
                                  message_builder: Callable[[int, int, PageEntryLike, str], str] | None = None, complete_message: str | Callable[[int, int, str | None], str] | None = None) -> None:
    _refresh_core_globals()
    total_pages = max(1, len(page_entries))
    last_message = None
    for page_index, entry in enumerate(page_entries, 1):
        _raise_if_cancelled(should_cancel)
        page_image, page_args, label = _resolve_page_entry(entry, args)
        if page_image is None:
            continue
        if callable(message_builder):
            message = message_builder(page_index, total_pages, entry, label)
        else:
            message = f'{label}を変換中… ({page_index}/{total_pages} ページ)'
        last_message = message
        _emit_progress(progress_cb, page_index - 1, total_pages, message)
        spooled_pages.add_blob(ensure_valid_xt_page_blob(page_image_to_xt_bytes(page_image, page_args.width, page_args.height, page_args), page_image, page_args.width, page_args.height, page_args))

    if complete_message is None:
        complete_message = f'ページ変換が完了しました。({spooled_pages.page_count} ページ)'
    elif callable(complete_message):
        complete_message = complete_message(spooled_pages.page_count, total_pages, last_message)
    _emit_progress(progress_cb, total_pages, total_pages, complete_message)


def _write_page_entries_to_xtc(page_entries: Sequence[PageEntryLike], source_path: PathLike, args: ConversionArgs, output_path: PathLike | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None,
                               message_builder: Callable[[int, int, PageEntryLike, str], str] | None = None, complete_message: str | Callable[[int, int, str | None], str] | None = None) -> Path:
    _refresh_core_globals()
    ext = '.xtch' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else '.xtc'
    out_path = Path(output_path) if output_path else Path(source_path).with_suffix(ext)
    renderable_pages = sum(1 for entry in page_entries if _resolve_page_entry(entry, args)[0] is not None)
    if renderable_pages == 0:
        raise ValueError('変換データがありません。')

    tmp_handle = tempfile.NamedTemporaryFile(prefix=f'{out_path.stem}_', suffix='.partial', dir=str(out_path.parent), delete=False)
    tmp_path = Path(tmp_handle.name)
    tmp_handle.close()

    try:
        idx_off = 48
        data_off = 48 + renderable_pages * 16
        total_pages = max(1, len(page_entries))
        page_specs: list[tuple[int, int, int]] = []
        last_message = None

        with open(tmp_path, 'w+b') as dst:
            dst.seek(data_off)
            for page_index, entry in enumerate(page_entries, 1):
                _raise_if_cancelled(should_cancel)
                page_image, page_args, label = _resolve_page_entry(entry, args)
                if page_image is None:
                    continue
                if callable(message_builder):
                    message = message_builder(page_index, total_pages, entry, label)
                else:
                    message = f'{label}を変換中… ({page_index}/{total_pages} ページ)'
                last_message = message
                _emit_progress(progress_cb, page_index - 1, total_pages, message)
                blob = page_image_to_xt_bytes(page_image, page_args.width, page_args.height, page_args)
                dst.write(blob)
                page_specs.append((len(blob), page_args.width, page_args.height))

            if complete_message is None:
                complete_text = f'ページ変換が完了しました。({len(page_specs)} ページ)'
            elif callable(complete_message):
                complete_text = complete_message(len(page_specs), total_pages, last_message)
            else:
                complete_text = complete_message
            _emit_progress(progress_cb, total_pages, total_pages, complete_text)

            _raise_if_cancelled(should_cancel)
            _emit_progress(progress_cb, 0, renderable_pages + 1, f'XTC索引を作成中… (0/{renderable_pages} ページ)')
            idx_table = bytearray()
            curr_off = data_off
            for idx, (size, page_w, page_h) in enumerate(page_specs, 1):
                _raise_if_cancelled(should_cancel)
                idx_table += struct.pack('<Q I H H', curr_off, size, page_w, page_h)
                curr_off += size
                _emit_progress(progress_cb, idx, renderable_pages + 1, f'XTC索引を作成中… ({idx}/{renderable_pages} ページ)')

            mark = b'XTCH' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else b'XTC\x00'
            header = struct.pack('<4sHHBBBBIQQQQ', mark, 1, len(page_specs), 1, 0, 0, 0, 0, 0, idx_off, data_off, 0)
            dst.seek(0)
            dst.write(header)
            dst.write(idx_table)
            dst.flush()

        os.replace(tmp_path, out_path)
        _emit_progress(progress_cb, renderable_pages + 1, renderable_pages + 1, f'XTCを書き出しました。({len(page_specs)} ページ)')
        return out_path
    except Exception:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def _render_text_blocks_to_xtc(blocks: Sequence[dict[str, Any]], source_path: PathLike, font_path: PathLike, args: ConversionArgs, output_path: PathLike | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    _refresh_core_globals()
    render_text_blocks_to_page_entries = globals().get('_render_text_blocks_to_page_entries')
    if not callable(render_text_blocks_to_page_entries):
        from tategakiXTC_gui_core_renderer import _render_text_blocks_to_page_entries as render_text_blocks_to_page_entries
        globals()['_render_text_blocks_to_page_entries'] = render_text_blocks_to_page_entries
    page_entries = render_text_blocks_to_page_entries(
        blocks,
        font_path,
        args,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
    )
    for entry in page_entries:
        entry['label'] = '描画済みページ'

    def _rendered_page_message(page_index: int, total_pages: int, entry: PageEntryLike, label: str) -> str:
        return f'{label}を変換中… ({page_index}/{total_pages} ページ)'

    def _rendered_page_complete_message(page_count: int, total_pages: int, last_message: str | None) -> str:
        return f'描画済みページを変換しました。({page_count} ページ)'

    return _write_page_entries_to_xtc(
        page_entries,
        source_path,
        args,
        output_path=output_path,
        should_cancel=should_cancel,
        progress_cb=progress_cb,
        message_builder=_rendered_page_message,
        complete_message=_rendered_page_complete_message,
    )
