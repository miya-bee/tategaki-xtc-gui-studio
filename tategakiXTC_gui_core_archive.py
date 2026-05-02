"""
tategakiXTC_gui_core_archive.py — アーカイブ入力 helper

`tategakiXTC_gui_core.py` から分離した ZIP / CBZ / RAR / CBR 入力の
安全な列挙・抽出・中間表現化の実装。互換性維持のため、gui_core 側の
re-export / 既存テストの monkey patch を各入口で同期する。
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path, PurePosixPath
import ntpath
import os
import tempfile
import zipfile

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals', 'process_archive'}
_CORE_SYNC_VERSION = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch を archive 実装へ反映する。"""
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
# --- アーカイブ入力 helper ---
# ==========================================

@lru_cache(maxsize=128)
def _cached_safe_zip_archive_image_listing(path_text: str, file_size: int, mtime_ns: int) -> tuple[tuple[str, ...], int]:
    """ZIP/CBZ 内の安全な画像メンバー名を自然順でキャッシュする。"""
    _refresh_core_globals()
    archive = Path(path_text)
    member_names: list[str] = []
    traversal_skipped = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = str(getattr(info, 'filename', '') or '')
            if not name or getattr(info, 'is_dir', lambda: False)():
                continue
            pure = PurePosixPath(name)
            if pure.is_absolute() or '..' in pure.parts:
                if pure.suffix.lower() in IMG_EXTS:
                    traversal_skipped += 1
                continue
            if pure.suffix.lower() not in IMG_EXTS:
                continue
            member_names.append(pure.as_posix())
    member_names.sort(key=_natural_sort_key)
    return tuple(member_names), traversal_skipped



def _safe_zip_archive_image_listing(archive_path: PathLike) -> tuple[list[str], int]:
    """ZIP/CBZ 内の安全な画像メンバー名を自然順で返す。"""
    _refresh_core_globals()
    path_text, file_size, mtime_ns = _source_document_cache_key(archive_path)
    member_names, traversal_skipped = _cached_safe_zip_archive_image_listing(path_text, file_size, mtime_ns)
    return list(member_names), traversal_skipped





_ARCHIVE_INVALID_COMPONENT_CHARS = frozenset(r'<>:"\|?*')
_ARCHIVE_WINDOWS_RESERVED_NAMES = frozenset({
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
})


def _sanitize_extracted_archive_member_component(part: str, fallback: str = 'item') -> str:
    _refresh_core_globals()
    raw = str(part or '').replace('\x00', '').strip()
    cleaned = ''.join(
        '_' if (ord(ch) < 32 or ch in _ARCHIVE_INVALID_COMPONENT_CHARS) else ch
        for ch in raw
    ).strip(' .')
    if not cleaned or cleaned in {'.', '..'}:
        cleaned = fallback
    stem = Path(cleaned).stem.strip(' .')
    if cleaned.upper() in _ARCHIVE_WINDOWS_RESERVED_NAMES or stem.upper() in _ARCHIVE_WINDOWS_RESERVED_NAMES:
        cleaned = f'_{cleaned}'
    return cleaned or fallback


def _normalize_extracted_archive_member_key(path: PathLike) -> str:
    _refresh_core_globals()
    raw = str(path or '').strip()
    if not raw:
        return ''
    path_obj = Path(raw)
    windows_like = bool(path_obj.drive) or ('\\' in raw)
    normalized = ntpath.normpath(raw) if windows_like else os.path.normpath(raw)
    return ntpath.normcase(normalized) if windows_like else normalized.casefold()


def _safe_zip_archive_image_infos(archive_path: PathLike, *, should_cancel: CancelCallback | None = None) -> tuple[list[tuple[PurePosixPath, zipfile.ZipInfo]], int]:
    """ZIP/CBZ 内の安全な画像メンバー情報を自然順で返す。"""
    _refresh_core_globals()
    archive = Path(archive_path)
    image_infos: list[tuple[PurePosixPath, zipfile.ZipInfo]] = []
    traversal_skipped = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            _raise_if_cancelled(should_cancel)
            name = str(getattr(info, 'filename', '') or '')
            if not name or getattr(info, 'is_dir', lambda: False)():
                continue
            pure = PurePosixPath(name)
            if pure.is_absolute() or '..' in pure.parts:
                if pure.suffix.lower() in IMG_EXTS:
                    traversal_skipped += 1
                continue
            if pure.suffix.lower() not in IMG_EXTS:
                continue
            image_infos.append((pure, info))
    image_infos.sort(key=lambda item: _natural_sort_key(item[0].as_posix()))
    return image_infos, traversal_skipped



def _unique_extracted_member_path(dest_path: Path) -> Path:
    _refresh_core_globals()
    if not dest_path.exists():
        return dest_path
    stem = dest_path.stem
    suffix = dest_path.suffix
    parent = dest_path.parent
    index = 1
    while True:
        candidate = parent / f'{stem}({index}){suffix}'
        if not candidate.exists():
            return candidate
        index += 1



def _extract_zip_archive_images_to_tempdir(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> tuple[list[Path], int]:
    """ZIP/CBZ から安全な画像メンバーだけを一時ディレクトリへ抽出する。"""
    _refresh_core_globals()
    out_dir = Path(tmpdir_path)
    image_infos, traversal_skipped = _safe_zip_archive_image_infos(archive_path, should_cancel=should_cancel)
    extracted_files: list[Path] = []
    reserved_dest_keys: set[str] = set()
    with zipfile.ZipFile(Path(archive_path)) as zf:
        for pure, info in image_infos:
            _raise_if_cancelled(should_cancel)
            sanitized_parts = [
                _sanitize_extracted_archive_member_component(part, 'item')
                for part in pure.parts
            ]
            desired_path = out_dir.joinpath(*sanitized_parts)
            dest_path = _unique_extracted_member_path(desired_path)
            dest_key = _normalize_extracted_archive_member_key(dest_path) or str(dest_path)
            if dest_key in reserved_dest_keys:
                stem = desired_path.stem
                suffix = desired_path.suffix
                parent = desired_path.parent
                index = 1
                while True:
                    candidate = parent / f'{stem}({index}){suffix}'
                    candidate_key = _normalize_extracted_archive_member_key(candidate) or str(candidate)
                    if candidate_key not in reserved_dest_keys and not candidate.exists():
                        dest_path = candidate
                        dest_key = candidate_key
                        break
                    index += 1
            reserved_dest_keys.add(dest_key)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with zf.open(info) as src_fp, open(dest_path, 'wb') as out_fp:
                    _copy_fileobj_with_cancel(src_fp, out_fp, should_cancel=should_cancel, chunk_size=1024 * 1024)
            except Exception:
                try:
                    dest_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise
            extracted_files.append(dest_path)
    return extracted_files, traversal_skipped

def _extract_archive_to_tempdir(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> tuple[int, list[Path] | None]:
    """アーカイブを一時ディレクトリへ展開する。"""
    _refresh_core_globals()
    suffix = Path(archive_path).suffix.lower()
    if suffix in ('.zip', '.cbz'):
        extracted_files, traversal_skipped = _extract_zip_archive_images_to_tempdir(archive_path, tmpdir_path, should_cancel=should_cancel)
        return traversal_skipped, extracted_files
    _raise_if_cancelled(should_cancel)
    patoolib = _require_patoolib()
    patoolib.extract_archive(str(archive_path), outdir=str(tmpdir_path), verbosity=-1)
    _raise_if_cancelled(should_cancel)
    return 0, None


def _collect_archive_image_files(tmpdir_path: PathLike) -> list[Path]:
    """展開済みディレクトリから画像ファイルを自然順で収集する。"""
    _refresh_core_globals()
    base_dir = Path(tmpdir_path)
    return sorted(
        [p for p in base_dir.rglob('*') if p.suffix.lower() in IMG_EXTS],
        key=lambda p: _natural_sort_key(p.relative_to(base_dir)),
    )


def _list_zip_archive_image_members(archive_path: PathLike) -> list[str]:
    """ZIP/CBZ 内の画像メンバー名を安全側に寄せて自然順で列挙する。"""
    _refresh_core_globals()
    member_names, _traversal_skipped = _safe_zip_archive_image_listing(archive_path)
    return member_names


def _load_archive_input_document_compat(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> ArchiveInputDocument:
    """load_archive_input_document の旧2引数モックとも互換を保って呼び出す。"""
    _refresh_core_globals()
    try:
        return load_archive_input_document(archive_path, tmpdir_path, should_cancel=should_cancel)
    except TypeError as exc:
        msg = str(exc)
        if 'unexpected keyword argument' not in msg or 'should_cancel' not in msg:
            raise
        return load_archive_input_document(archive_path, tmpdir_path)


def load_archive_input_document(archive_path: PathLike, tmpdir_path: PathLike, *, should_cancel: CancelCallback | None = None) -> ArchiveInputDocument:
    """画像アーカイブを展開し、描画対象画像一覧へ正規化する。"""
    _refresh_core_globals()
    source_path = Path(archive_path)
    temp_path = Path(tmpdir_path)
    _raise_if_cancelled(should_cancel)
    traversal_skipped, extracted_files = _extract_archive_to_tempdir(source_path, temp_path, should_cancel=should_cancel)
    _raise_if_cancelled(should_cancel)
    image_files = extracted_files if extracted_files is not None else _collect_archive_image_files(temp_path)
    _raise_if_cancelled(should_cancel)
    return ArchiveInputDocument(
        source_path=source_path,
        image_files=image_files,
        traversal_skipped=traversal_skipped,
        extracted_member_count=len(image_files),
        trusted_temp_files=extracted_files is not None,
    )


# ==========================================
# --- アーカイブ変換入口 ---
# ==========================================

def process_archive(archive_path: str | Path, args: ConversionArgs, output_path: str | Path | None = None, should_cancel: Callable[[], bool] | None = None, progress_cb: Callable[[int, int, str], None] | None = None) -> Path:
    """Convert an image archive such as ZIP/CBZ/CBR/RAR into XTC or XTCH.

    The archive is extracted into a temporary directory, supported image files are
    filtered and sorted, then each image is converted into a page entry and written to
    the requested XTC-family output. Safety checks such as path-traversal filtering are
    applied during extraction.

    Args:
        archive_path: Archive file to convert.
        args: Conversion arguments controlling target size and output format.
        output_path: Optional explicit output path. When omitted, the output path is
            derived from ``archive_path``.
        should_cancel: Optional cancellation callback queried during long operations.
        progress_cb: Optional callback receiving ``(current, total, message)`` updates.

    Returns:
        Path to the generated output file.
    """
    _refresh_core_globals()
    archive_path = Path(archive_path)
    _raise_if_cancelled(should_cancel)
    LOGGER.info('[アーカイブ変換開始] %s', archive_path.name)
    ext = '.xtch' if _normalize_output_format(getattr(args, 'output_format', 'xtc')) == 'xtch' else '.xtc'
    out_path = Path(output_path) if output_path else archive_path.with_suffix(ext)

    image_items: list[Path | str] = []
    conversion_fail_count = 0
    traversal_skipped = 0
    first_exc: Exception | None = None
    last_exc: Exception | None = None
    total_images = 0

    with XTCSpooledPages() as spooled_pages:
        direct_zip_infos: list[tuple[PurePosixPath, zipfile.ZipInfo]] | None = None
        if archive_path.suffix.lower() in ('.zip', '.cbz'):
            try:
                direct_zip_infos, traversal_skipped = _safe_zip_archive_image_infos(archive_path, should_cancel=should_cancel)
            except Exception:
                direct_zip_infos = None
                traversal_skipped = 0

        if direct_zip_infos is not None:
            image_items = [pure.as_posix() for pure, _info in direct_zip_infos]
            LOGGER.info('アーカイブ内画像数: %s 枚', len(image_items))
            total_images = len(image_items)
            progress_total = max(1, total_images)
            _emit_progress(progress_cb, 0, progress_total, f'アーカイブ内画像を確認しました。({len(image_items)} 枚)')
            try:
                with zipfile.ZipFile(archive_path) as zf:
                    for img_index, (pure, info) in enumerate(_iter_with_optional_tqdm(direct_zip_infos, desc="通常変換中", unit="枚", leave=False), 1):
                        display_name = pure.name or pure.as_posix()
                        _emit_progress(progress_cb, img_index - 1, max(1, total_images), f'画像を変換中… ({max(0, img_index - 1)}/{total_images} 枚) {display_name}')
                        _raise_if_cancelled(should_cancel)
                        try:
                            with zf.open(info) as member_fp:
                                blob = process_image_data(member_fp, args, should_cancel=should_cancel)
                            if blob:
                                spooled_pages.add_blob(blob)
                                _emit_progress(progress_cb, img_index, max(1, total_images), f'画像を変換中… ({img_index}/{total_images} 枚) {display_name}')
                            else:
                                LOGGER.warning('画像変換結果なし (%s): 変換に失敗した可能性があります', display_name)
                                if first_exc is None:
                                    first_exc = ValueError(f'cannot identify image file: {display_name}')
                                conversion_fail_count += 1
                        except Exception as e:
                            LOGGER.warning('画像スキップ (%s): %s', display_name, e)
                            if first_exc is None:
                                first_exc = e
                            last_exc = e
                            conversion_fail_count += 1
                            continue
            except Exception as e:
                report = build_conversion_error_report(archive_path, e, stage='アーカイブ展開')
                raise RuntimeError(report['display']) from e
        else:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                try:
                    archive_document = _load_archive_input_document_compat(archive_path, tmpdir_path, should_cancel=should_cancel)
                except Exception as e:
                    report = build_conversion_error_report(archive_path, e, stage='アーカイブ展開')
                    raise RuntimeError(report['display']) from e

                image_items = archive_document.image_files
                traversal_skipped = int(getattr(archive_document, 'traversal_skipped', 0) or 0)
                trusted_temp_files = bool(getattr(archive_document, 'trusted_temp_files', False))
                LOGGER.info('アーカイブ内画像数: %s 枚', len(image_items))
                total_images = len(image_items)
                progress_total = max(1, total_images)
                _emit_progress(progress_cb, 0, progress_total, f'アーカイブを展開しました。({len(image_items)} 枚)')

                tmpdir_resolved = tmpdir_path.resolve()
                for img_index, img_p in enumerate(_iter_with_optional_tqdm(image_items, desc="通常変換中", unit="枚", leave=False), 1):
                    assert isinstance(img_p, Path)
                    _emit_progress(progress_cb, img_index - 1, max(1, total_images), f'画像を変換中… ({max(0, img_index - 1)}/{total_images} 枚) {img_p.name}')
                    _raise_if_cancelled(should_cancel)
                    try:
                        resolved_img = img_p if trusted_temp_files else img_p.resolve(strict=False)
                        if not trusted_temp_files:
                            try:
                                resolved_img.relative_to(tmpdir_resolved)
                            except ValueError:
                                LOGGER.warning('パス・トラバーサル検出のためスキップ: %s', img_p)
                                traversal_skipped += 1
                                continue
                        blob = process_image_data(resolved_img, args, should_cancel=should_cancel)
                        if blob:
                            spooled_pages.add_blob(blob)
                            _emit_progress(progress_cb, img_index, max(1, total_images), f'画像を変換中… ({img_index}/{total_images} 枚) {img_p.name}')
                        else:
                            LOGGER.warning('画像変換結果なし (%s): 変換に失敗した可能性があります', img_p.name)
                            if first_exc is None:
                                first_exc = ValueError(f'cannot identify image file: {img_p.name}')
                            conversion_fail_count += 1
                    except Exception as e:
                        LOGGER.warning('画像スキップ (%s): %s', img_p.name, e)
                        if first_exc is None:
                            first_exc = e
                        last_exc = e
                        conversion_fail_count += 1
                        continue

        if spooled_pages.page_count > 0:
            _emit_progress(progress_cb, max(1, total_images), max(1, total_images), f'画像変換が完了しました。({spooled_pages.page_count} ページ)')
            spooled_pages.finalize(out_path, args.width, args.height, getattr(args, 'output_format', 'xtc'), should_cancel=should_cancel, progress_cb=progress_cb)
            LOGGER.info('通常変換完了: %s', out_path.name)
            return out_path

    if total_images == 0 and traversal_skipped > 0:
        raise RuntimeError(
            f'対象: {archive_path.name}\n'
            '内容: 安全のためアーカイブ内画像を処理しませんでした。\n'
            '画像は 0 枚見つかりましたが、安全のため処理を行いませんでした。\n'
            f'安全のためスキップしたパス: {traversal_skipped} 件\n'
            '確認: アーカイブ内のパス構造に問題がないか確認してください。'
        )

    if not image_items:
        raise RuntimeError(
            f'対象: {archive_path.name}\n'
            '内容: 変換できる画像が見つかりませんでした。\n'
            f'詳細: 対応画像は {", ".join(IMG_EXTS)} です。\n'
            '確認: 画像ファイルがサブフォルダ内にある場合も含め、アーカイブ内に画像が入っているか確認してください。'
        )

    if (conversion_fail_count + traversal_skipped) > 0 and total_images > 0:
        rep_exc = first_exc or last_exc
        rep_msg = _compact_error_text(rep_exc) if rep_exc else '詳細不明'
        if conversion_fail_count == 0 and traversal_skipped > 0:
            detail = [
                f'画像は {len(image_items)} 枚見つかりましたが、安全のため処理を行いませんでした。',
                f'安全のためスキップしたパス: {traversal_skipped} 件',
                '確認: アーカイブ内のパス構造に問題がないか確認してください。',
            ]
            raise RuntimeError(
                f'対象: {archive_path.name}\n'
                '内容: 安全のためアーカイブ内画像を処理しませんでした。\n'
                + '\n'.join(detail)
            )
        detail = [
            f'画像は {len(image_items)} 枚見つかりましたが、正常に変換できませんでした。',
            f'変換失敗: {conversion_fail_count} 件',
        ]
        if rep_exc is not None:
            detail.append(f'代表エラー: {rep_msg}')
        if traversal_skipped:
            detail.append(f'安全のためスキップしたパス: {traversal_skipped} 件')
        detail.append(f'確認: 対応画像は {", ".join(IMG_EXTS)} です。破損画像や未対応形式が混在していないか確認してください。')
        raise RuntimeError(
            f'対象: {archive_path.name}\n'
            '内容: アーカイブ内画像の変換に失敗しました。\n'
            + '\n'.join(detail)
        )
    raise RuntimeError(f'対象: {archive_path.name}\n内容: 変換できる画像が見つかりませんでした。')

