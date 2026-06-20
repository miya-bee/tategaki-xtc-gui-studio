from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
import pytest

import tategakiXTC_gui_core as core
import tategakiXTC_gui_core_text as core_text


def _write_manifest(source_path: Path, image_dir: Path, *, caption: str = '図版キャプション') -> None:
    payload = {
        'version': 1,
        'image_dir': image_dir.name,
        'images': {
            '0001': {
                'file': '0001.png',
                'src': 'fig0001.png',
                'basename': 'fig0001.png',
                'caption': caption,
            }
        },
    }
    source_path.with_name(f'{source_path.stem}.images.json').write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True),
        encoding='utf-8',
    )

def test_select_preview_blocks_preserves_image_blocks_without_runs() -> None:
    blocks = [
        {'kind': 'image', 'image_id': '0001', 'image_src': 'fig0001.png', 'blank_before': 1},
        {'kind': 'paragraph', 'runs': [{'text': '本文'}]},
    ]

    selected = core._select_preview_blocks(blocks)

    assert selected[0]['kind'] == 'image'
    assert selected[0]['image_id'] == '0001'


def test_image_only_missing_sidecar_reports_image_acquisition_error(tmp_path: Path) -> None:
    source_path = tmp_path / 'sample.txt'
    source_path.write_text('［＃挿絵:0001］\n', encoding='utf-8')
    document = core.load_text_input_document(source_path, parser='plain')
    args = core.ConversionArgs(width=180, height=220, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')

    with pytest.raises(RuntimeError, match='挿絵を取得できませんでした'):
        core._render_text_blocks_to_page_entries(document.blocks, str(tmp_path / 'missing.ttf'), args)


def test_aozora_image_marker_resolves_manifest_caption_and_path(tmp_path: Path) -> None:
    source_path = tmp_path / 'sample.txt'
    source_path.write_text('本文\n［＃挿絵:0001］\n続き\n', encoding='utf-8')
    image_dir = tmp_path / 'sample_img'
    image_dir.mkdir()
    Image.new('L', (12, 12), 0).save(image_dir / '0001.png')
    _write_manifest(source_path, image_dir, caption='図版キャプション')

    document = core.load_text_input_document(source_path, parser='plain')
    image_blocks = [block for block in document.blocks if block.get('kind') == 'image']

    assert len(image_blocks) == 1
    assert image_blocks[0]['image_id'] == '0001'
    assert image_blocks[0]['caption'] == '図版キャプション'
    assert Path(str(image_blocks[0]['image_path'])).samefile(image_dir / '0001.png')


def test_aozora_image_sidecar_cache_key_tracks_image_file_changes(tmp_path: Path) -> None:
    source_path = tmp_path / 'sample.txt'
    source_path.write_text('本文\n［＃挿絵:0001］\n', encoding='utf-8')
    image_dir = tmp_path / 'sample_img'
    image_dir.mkdir()
    image_path = image_dir / '0001.png'
    image_path.write_bytes(b'old')
    _write_manifest(source_path, image_dir)

    before = core_text._aozora_image_sidecar_cache_key(source_path)
    image_path.write_bytes(b'new-content-with-different-size')
    after = core_text._aozora_image_sidecar_cache_key(source_path)

    assert before != after


def test_image_block_with_manifest_caption_renders_without_error(tmp_path: Path) -> None:
    source_path = tmp_path / 'sample.txt'
    source_path.write_text('本文\n［＃挿絵:0001］\n続き\n', encoding='utf-8')
    image_dir = tmp_path / 'sample_img'
    image_dir.mkdir()
    Image.new('L', (12, 12), 0).save(image_dir / '0001.png')
    _write_manifest(source_path, image_dir, caption='図版')
    document = core.load_text_input_document(source_path, parser='plain')

    from tests.image_golden_cases import FONT_PATH

    args = core.ConversionArgs(width=180, height=220, font_size=20, ruby_size=10, line_spacing=28, output_format='xtc')
    entries = core._render_text_blocks_to_page_entries(document.blocks, FONT_PATH, args)

    assert entries
    assert any(entry.get('label') == '本文ページ' for entry in entries)


def test_aozora_image_sidecar_cache_key_tracks_directory_images_without_manifest(tmp_path: Path) -> None:
    source_path = tmp_path / 'sample.txt'
    source_path.write_text('本文\n［＃挿絵（fig0001.png）入る］\n', encoding='utf-8')
    image_dir = tmp_path / 'sample_img'
    image_dir.mkdir()
    image_path = image_dir / 'fig0001.png'
    image_path.write_bytes(b'old')

    before = core_text._aozora_image_sidecar_cache_key(source_path)
    image_path.write_bytes(b'new-content-with-different-size')
    after = core_text._aozora_image_sidecar_cache_key(source_path)

    assert before != after


def test_preview_bundle_cache_key_tracks_aozora_sidecar_image_changes(tmp_path: Path) -> None:
    import tategakiXTC_gui_core_renderer as renderer

    source_path = tmp_path / 'sample.txt'
    source_path.write_text('本文\n［＃挿絵:0001］\n', encoding='utf-8')
    image_dir = tmp_path / 'sample_img'
    image_dir.mkdir()
    image_path = image_dir / '0001.png'
    image_path.write_bytes(b'old')
    _write_manifest(source_path, image_dir)
    payload = {
        'mode': 'text',
        'target_path': str(source_path),
        'font_file': '',
        'max_pages': 3,
    }

    before = renderer._preview_bundle_cache_key(payload, preview_sources=[source_path])
    image_path.write_bytes(b'new-content-with-different-size')
    after = renderer._preview_bundle_cache_key(payload, preview_sources=[source_path])

    assert before != after


def test_process_text_file_emits_text_full_page_image_and_caption_pages(tmp_path: Path) -> None:
    from tests.image_golden_cases import FONT_PATH

    source_path = tmp_path / 'sample.txt'
    source_path.write_text('本文\n［＃挿絵:0001］\n続き\n', encoding='utf-8')
    image_dir = tmp_path / 'sample_img'
    image_dir.mkdir()
    Image.new('L', (140, 180), 0).save(image_dir / '0001.png')
    _write_manifest(source_path, image_dir, caption='図版')

    args = core.ConversionArgs(
        width=180,
        height=220,
        font_size=20,
        ruby_size=10,
        line_spacing=28,
        output_format='xtc',
    )
    out_path = core.process_text_file(source_path, FONT_PATH, args, output_path=tmp_path / 'out.xtc')

    assert out_path.exists()
    assert core._verify_xt_container_file(out_path, 180, 220, 'xtc', expected_count=3) == 3
