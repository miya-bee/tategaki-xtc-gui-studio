"""
tategakiXTC_gui_core_deps.py — 任意依存 / 変換診断 helper

`tategakiXTC_gui_core.py` から分離した任意依存ライブラリ確認と、
変換失敗時のユーザー向け診断文生成の実装。互換性維持のため、
gui_core 側の re-export / 既存テストの monkey patch を各入口で同期する。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, cast
import importlib
import os


# Circular-import guard for direct split-module imports.
# ``tategakiXTC_gui_core`` re-exports many names from this module; when this
# module is imported first, core may ask for those names before the real
# definitions below have executed.  Placeholders let core finish importing;
# the real objects are published back to core at module end.
_SPLIT_IMPORT_PLACEHOLDER = object()
_CORE_REEXPORT_NAMES = (
    'OPTIONAL_DEPENDENCIES',
    '_compact_error_text',
    'build_conversion_error_report',
    '_require_patoolib',
    '_iter_with_optional_tqdm',
    '_is_module_available',
    'list_optional_dependency_status',
    'get_missing_dependencies_for_suffixes'
)
_CORE_REEXPORT_ALIASES = (
    ('OPTIONAL_DEPENDENCIES', 'OPTIONAL_DEPENDENCIES'),
    ('_compact_error_text', '_compact_error_text'),
    ('build_conversion_error_report', 'build_conversion_error_report'),
    ('_require_patoolib', '_require_patoolib'),
    ('_iter_with_optional_tqdm', '_deps_iter_with_optional_tqdm'),
    ('_is_module_available', '_deps_is_module_available'),
    ('list_optional_dependency_status', 'list_optional_dependency_status'),
    ('get_missing_dependencies_for_suffixes', 'get_missing_dependencies_for_suffixes')
)
for _name in _CORE_REEXPORT_NAMES:
    globals().setdefault(_name, _SPLIT_IMPORT_PLACEHOLDER)

import tategakiXTC_gui_core as _core
from tategakiXTC_gui_core_sync import core_sync_version, install_core_sync_tracker


_CORE_SYNC_EXCLUDED_NAMES = {'_core', '_refresh_core_globals'}
_CORE_SYNC_VERSION = -1

install_core_sync_tracker(_core)


def _refresh_core_globals(*, force: bool = False) -> None:
    """gui_core 側の互換 re-export / monkey patch を deps 実装へ反映する。"""
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
# --- 任意依存 / 変換診断 helper ---
# ==========================================

OPTIONAL_DEPENDENCIES = {
    'ebooklib': {
        'module': 'ebooklib',
        'package': 'ebooklib',
        'label': 'ebooklib',
        'purpose': 'EPUB変換',
        'impact': 'feature',
    },
    'beautifulsoup4': {
        'module': 'bs4',
        'package': 'beautifulsoup4',
        'label': 'beautifulsoup4',
        'purpose': 'EPUB変換',
        'impact': 'feature',
    },
    'patool': {
        'module': 'patoolib',
        'package': 'patool',
        'label': 'patool',
        'purpose': 'RAR / CBR 変換',
        'impact': 'feature',
    },
    'charset-normalizer': {
        'module': 'charset_normalizer',
        'package': 'charset-normalizer',
        'label': 'charset-normalizer',
        'purpose': 'TXT / Markdown の文字コード自動判定',
        'impact': 'feature',
    },
    'tqdm': {
        'module': 'tqdm',
        'package': 'tqdm',
        'label': 'tqdm',
        'purpose': 'コンソール進捗表示（未導入でも動作可）',
        'impact': 'convenience',
    },
    'numpy': {
        'module': 'numpy',
        'package': 'numpy',
        'label': 'numpy',
        'purpose': 'XTC / XTCH pack 高速化',
        'impact': 'performance',
    },
}


def _compact_error_text(value: object, max_len: int = 220) -> str:
    _refresh_core_globals()
    text = ' '.join(str(value or '').replace('　', ' ').split())
    if len(text) > max_len:
        return text[: max_len - 1] + '…'
    return text


def build_conversion_error_report(source_path: PathLike | None, exc: BaseException, stage: str = '') -> ConversionErrorReport:
    _refresh_core_globals()
    # 入力ごとの変換失敗をユーザー向けの説明文へ整形する。
    path = Path(source_path) if source_path else None
    suffix = (path.suffix.lower() if path else '')
    raw_detail = str(exc).strip() or exc.__class__.__name__
    stage = str(stage or '').strip()
    headline = '変換に失敗しました。'
    hint = 'ログもあわせて確認してください。'

    is_cancelled = False
    try:
        is_cancelled = isinstance(exc, ConversionCancelled)
    except Exception:
        is_cancelled = False
    if is_cancelled or '変換を停止しました' in raw_detail or '停止要求' in raw_detail:
        headline = '変換を停止しました。'
        hint = 'ユーザー操作により停止しました。EPUB / HTML / CSS のエラーではありません。'
        lines = []
        if path:
            lines.append(f'対象: {path.name}')
        lines.append(f'内容: {headline}')
        if stage:
            lines.append(f'段階: {stage}')
        lines.append(f'詳細: {_compact_error_text(raw_detail)}')
        lines.append(f'確認: {hint}')
        return {
            'headline': headline,
            'detail': _compact_error_text(raw_detail),
            'hint': hint,
            'display': '\n'.join(lines),
        }

    if 'pip install' in raw_detail or '必要です。' in raw_detail or '不足しています' in raw_detail:
        headline = '必要なライブラリが不足しているため変換できませんでした。'
        hint = 'requirements.txt を使って依存ライブラリを入れ直してください。'
    elif isinstance(exc, UnicodeDecodeError) or '文字コード' in raw_detail or "codec can't decode" in raw_detail:
        headline = 'テキストの文字コードを判定できませんでした。'
        hint = 'UTF-8 / UTF-8 BOM / CP932(Shift_JIS) などで保存し直すと改善する場合があります。'
    elif isinstance(exc, FileNotFoundError):
        headline = '入力ファイルを開けませんでした。'
        hint = 'ファイルが移動・削除されていないか確認してください。'
    elif suffix == '.epub':
        raw_lower = raw_detail.lower()
        if 'zipとして開けません' in raw_detail or 'badzipfile' in raw_lower or 'zip file' in raw_lower:
            headline = 'EPUB を ZIP として開けませんでした。'
            hint = 'ファイルが破損しているか、拡張子だけが .epub になっていないか確認してください。'
        elif 'container.xml' in raw_detail:
            headline = 'EPUB の構造ファイル container.xml に問題があります。'
            hint = 'EPUB の META-INF/container.xml が存在するか、OPF への参照が壊れていないか確認してください。'
        elif 'opf' in raw_lower or 'パッケージ文書' in raw_detail:
            headline = 'EPUB の OPF パッケージ文書に問題があります。'
            hint = 'content.opf などのパッケージ文書が存在し、XMLとして読めるか確認してください。'
        elif 'manifest' in raw_lower:
            headline = 'EPUB の manifest に問題があります。'
            hint = '本文ファイルや画像の一覧が空、または spine からの参照先が欠けていないか確認してください。'
        elif 'spine が' in raw_detail or 'spine は' in raw_detail or 'spine に' in raw_detail or '読み順情報 spine' in raw_detail:
            headline = 'EPUB の読み順情報 spine に問題があります。'
            hint = '本文章が spine に含まれている EPUB か、linear="no" の補助ページだけになっていないか確認してください。'
        elif 'drm' in raw_lower or 'encryption.xml' in raw_lower or '暗号化' in raw_detail:
            headline = 'EPUB が DRM付き、または暗号化要素を含む可能性があります。'
            hint = 'DRM付きEPUBには対応していません。購入サイトの制限や暗号化の有無を確認してください。'
        elif '画像' in raw_detail and ('見つかりません' in raw_detail or 'cannot identify image file' in raw_lower or 'broken data stream' in raw_lower):
            headline = 'EPUB 内の画像参照または画像データに問題があります。'
            hint = '画像リンク切れ、破損画像、未対応画像形式が混在していないか確認してください。'
        elif '本文章が見つかりません' in raw_detail or '本文が見つかりません' in raw_detail:
            headline = 'EPUB の本文が見つかりませんでした。'
            hint = '本文が spine に含まれている EPUB か確認してください。'
        elif 'pagebreak' in raw_lower or 'html' in raw_lower or 'xhtml' in raw_lower or '章' in stage:
            headline = 'EPUB の本文描画中に失敗しました。'
            hint = '該当章の HTML / XHTML / CSS が特殊、または壊れている可能性があります。問題の EPUB をログと一緒に確認してください。'
        else:
            headline = 'EPUB の読み込みまたは解析に失敗しました。'
            hint = 'EPUB が壊れていないか、DRM 付きでないか、必要ライブラリが入っているか確認してください。'
    elif suffix in {'.zip', '.cbz', '.rar', '.cbr'}:
        if '解凍' in raw_detail or 'extract' in raw_detail.lower():
            headline = 'アーカイブの展開に失敗しました。'
            hint = 'ZIP / CBZ / RAR / CBR が破損していないか、RAR 系では patool が導入済みか確認してください。'
        elif '画像ファイルが見つかりませんでした' in raw_detail or '変換対象の画像が見つかりませんでした' in raw_detail:
            headline = 'アーカイブ内に変換対象の画像が見つかりませんでした。'
            hint = f'対応画像は {", ".join(IMG_EXTS)} です。'
        else:
            headline = 'アーカイブ内画像の変換に失敗しました。'
            hint = f'対応画像は {", ".join(IMG_EXTS)} です。破損画像や未対応形式が混在していないか確認してください。'
    elif suffix in TEXTUAL_INPUT_SUFFIX_SET:
        if suffix in MARKDOWN_INPUT_SUFFIXES:
            headline = 'Markdown の読み込みまたは整形中に失敗しました。'
            hint = 'ログの「入力注意」に出ている非対応要素がないか確認してください。'
        else:
            headline = 'テキストファイルの読み込みまたは変換に失敗しました。'
            hint = '文字コードや改行コードが極端に特殊でないか確認してください。'

    lines = []
    if path:
        lines.append(f'対象: {path.name}')
    lines.append(f'内容: {headline}')
    if stage:
        lines.append(f'段階: {stage}')
    lines.append(f'詳細: {_compact_error_text(raw_detail)}')
    if hint:
        lines.append(f'確認: {hint}')
    return {
        'headline': headline,
        'detail': _compact_error_text(raw_detail),
        'hint': hint,
        'display': '\n'.join(lines),
    }


def _require_patoolib() -> Any:
    """patoolib を必要時に読み込む。"""
    _refresh_core_globals()
    try:
        import patoolib as patoolib_module
    except ImportError as e:
        raise RuntimeError(
            "アーカイブ変換には patool が必要です。`pip install patool` を実行してください。"
        ) from e
    return patoolib_module




def _iter_with_optional_tqdm(iterable: Iterable[Any], **kwargs: object) -> Iterable[Any]:
    _refresh_core_globals()
    """tqdm があれば利用し、無ければ元の iterable を返す。

    unittest / CI / localweb service などの非対話実行では、tqdm の stderr 制御や
    内部 monitor thread が環境によってプロセス終了を遅らせることがある。
    そのため stderr が TTY でない場合は既定で素の iterable を返し、CLI で
    明示的に表示したい場合だけ ``TATEGAKI_XTC_FORCE_TQDM=1`` で有効化する。
    """
    force_tqdm = os.environ.get('TATEGAKI_XTC_FORCE_TQDM', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    if not force_tqdm:
        try:
            import sys
            if not sys.stderr.isatty():
                return iterable
        except Exception:
            return iterable
    try:
        from tqdm import tqdm as tqdm_func
    except ImportError:
        return iterable
    try:
        return tqdm_func(iterable, **kwargs)
    except Exception:
        return iterable


def _is_module_available(module_name: str) -> bool:
    _refresh_core_globals()
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def list_optional_dependency_status() -> list[DependencyStatus]:
    _refresh_core_globals()
    statuses: list[DependencyStatus] = []
    for key, info in OPTIONAL_DEPENDENCIES.items():
        statuses.append({
            'key': key,
            'label': info['label'],
            'package': info['package'],
            'purpose': info['purpose'],
            'impact': cast(DependencyImpact, info['impact']),
            'available': _is_module_available(info['module']),
        })
    return statuses


def get_missing_dependencies_for_suffixes(suffixes: Iterable[str]) -> list[MissingDependency]:
    _refresh_core_globals()
    required_keys: list[str] = []
    normalized = {str(s or '').strip().lower() for s in suffixes if str(s or '').strip()}
    if '.epub' in normalized:
        required_keys.extend(['ebooklib', 'beautifulsoup4'])
    if '.rar' in normalized or '.cbr' in normalized:
        required_keys.append('patool')

    missing: list[MissingDependency] = []
    seen = set()
    for key in required_keys:
        if key in seen:
            continue
        seen.add(key)
        info = OPTIONAL_DEPENDENCIES[key]
        if not _is_module_available(info['module']):
            missing.append({
                'key': key,
                'label': info['label'],
                'package': info['package'],
                'purpose': info['purpose'],
            })
    return missing

def _publish_core_reexports() -> None:
    """Replace circular-import placeholders in gui_core with real split symbols."""
    for _source_name, _core_name in _CORE_REEXPORT_ALIASES:
        _value = globals().get(_source_name, _SPLIT_IMPORT_PLACEHOLDER)
        if _value is _SPLIT_IMPORT_PLACEHOLDER:
            continue
        try:
            setattr(_core, _core_name, _value)
        except Exception:
            pass


_publish_core_reexports()

