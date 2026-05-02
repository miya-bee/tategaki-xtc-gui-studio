import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec

FONT_SPEC = resolve_test_font_spec()
FONT_PATH = resolve_test_font_path()


class _BBoxTypeErrorFont:
    def __init__(self, bbox=(0, 2, 10, 18)):
        self._bbox = bbox

    def getbbox(self, text, stroke_width=None):
        if stroke_width is not None:
            raise TypeError('stroke_width unsupported')
        return self._bbox


class _NoCenterFont:
    def getbbox(self, text, stroke_width=None):
        return (0, 0, 0, 0)


class _VariantTypeErrorFont:
    path = str(FONT_PATH)
    index = 0

    def font_variant(self, size=None):
        raise TypeError('unsupported')


class _VariantNoPathFont:
    def font_variant(self, size=None):
        raise TypeError('unsupported')


class _CountingBBoxFont:
    def __init__(self, bbox=(0, 2, 10, 18)):
        self._bbox = bbox
        self.calls = []

    def getbbox(self, text, stroke_width=None):
        self.calls.append((text, stroke_width))
        return self._bbox


class _RenderSignatureFont:
    pass


class FontAndDrawHelperRegressionTests(unittest.TestCase):
    def setUp(self):
        core.clear_font_entry_cache()
        core.parse_font_spec.cache_clear()
        self.font = core.load_truetype_font(FONT_SPEC, 24)

    def test_glyph_position_modes_limit_punctuation_to_hanging_marks_and_allow_five_ichi_steps(self):
        standard_kuto = core._scaled_kutoten_offset_for_mode(24, 'standard')
        for mode in ('down_strong', 'down_weak', 'up_weak', 'up_strong', 'plus', 'minus'):
            self.assertEqual(core._scaled_kutoten_offset_for_mode(24, mode), standard_kuto)

        standard_insets = core._tate_punctuation_layout_insets(24, False, False, 'standard')
        for mode in ('down_strong', 'down_weak', 'up_weak', 'up_strong', 'plus', 'minus'):
            self.assertEqual(core._tate_punctuation_layout_insets(24, False, False, mode), standard_insets)

        hanging_standard = core._punctuation_extra_y_for_mode(24, 'standard')
        hanging_down_strong = core._punctuation_extra_y_for_mode(24, 'down_strong')
        hanging_down_weak = core._punctuation_extra_y_for_mode(24, 'down_weak')
        hanging_up_weak = core._punctuation_extra_y_for_mode(24, 'up_weak')
        hanging_up_strong = core._punctuation_extra_y_for_mode(24, 'up_strong')
        self.assertGreater(hanging_down_strong, hanging_down_weak)
        self.assertGreater(hanging_down_weak, hanging_standard)
        self.assertLess(hanging_up_weak, hanging_standard)
        self.assertLess(hanging_up_strong, hanging_up_weak)
        self.assertEqual(core._punctuation_extra_y_for_mode(24, 'plus'), hanging_down_strong)
        self.assertEqual(core._punctuation_extra_y_for_mode(24, 'minus'), hanging_up_strong)

        ichi_standard = core._ichi_extra_y_for_mode(24, 'standard')
        ichi_down_strong = core._ichi_extra_y_for_mode(24, 'down_strong')
        ichi_down_weak = core._ichi_extra_y_for_mode(24, 'down_weak')
        ichi_up_weak = core._ichi_extra_y_for_mode(24, 'up_weak')
        ichi_up_strong = core._ichi_extra_y_for_mode(24, 'up_strong')
        self.assertEqual(ichi_standard, 0)
        self.assertGreater(ichi_down_strong, ichi_down_weak)
        self.assertGreater(ichi_down_weak, ichi_standard)
        self.assertLess(ichi_up_weak, ichi_standard)
        self.assertLess(ichi_up_strong, ichi_up_weak)
        self.assertEqual(core._ichi_extra_y_for_mode(24, 'plus'), ichi_down_strong)
        self.assertEqual(core._ichi_extra_y_for_mode(24, 'minus'), ichi_up_strong)

        lower_bracket_standard = core._lower_closing_bracket_extra_y_for_mode('」', 24, 'standard')
        lower_bracket_up_weak = core._lower_closing_bracket_extra_y_for_mode('」', 24, 'up_weak')
        lower_bracket_up_strong = core._lower_closing_bracket_extra_y_for_mode('」', 24, 'up_strong')
        self.assertEqual(lower_bracket_standard, 0)
        self.assertEqual(lower_bracket_up_weak, -4)
        self.assertEqual(lower_bracket_up_strong, -8)
        self.assertLess(lower_bracket_up_weak, lower_bracket_standard)
        self.assertLess(lower_bracket_up_strong, lower_bracket_up_weak)
        self.assertEqual(core._lower_closing_bracket_extra_y_for_mode('」', 24, 'down_strong'), 0)
        self.assertEqual(core._lower_closing_bracket_extra_y_for_mode('「', 24, 'up_strong'), 0)
        self.assertEqual(core._lower_closing_bracket_extra_y_for_mode('』', 24, 'up_weak'), lower_bracket_up_weak)
        self.assertEqual(core._lower_closing_bracket_extra_y_for_mode('﹂', 24, 'up_weak'), lower_bracket_up_weak)
        self.assertEqual(core._lower_closing_bracket_extra_y_for_mode('﹄', 24, 'up_strong'), lower_bracket_up_strong)
        self.assertTrue(core._is_lowerable_hanging_closing_bracket('﹂'))
        self.assertTrue(core._is_lowerable_hanging_closing_bracket('﹄'))

        self.assertEqual(core._glyph_position_mode('補正'), 'down_strong')
        self.assertEqual(core._glyph_position_mode('マイナス補正'), 'up_strong')
        self.assertEqual(core._glyph_position_mode('上補正'), 'up_strong')
        self.assertEqual(core._glyph_position_mode('上補正 弱'), 'up_weak')
        self.assertEqual(core._glyph_position_mode('下補正'), 'down_strong')
        self.assertEqual(core._glyph_position_mode('下補正 弱'), 'down_weak')
        self.assertEqual(core._glyph_position_mode('unknown'), 'standard')

    def test_parse_and_build_font_spec_cover_index_variants(self):
        self.assertEqual(core.parse_font_spec(''), ('', 0))
        self.assertEqual(
            core.parse_font_spec(f'C:/font.ttc{core.FONT_SPEC_INDEX_TOKEN}3'),
            ('C:/font.ttc', 3),
        )
        self.assertEqual(
            core.parse_font_spec(f'C:/font.ttc{core.FONT_SPEC_INDEX_TOKEN}abc'),
            (f'C:/font.ttc{core.FONT_SPEC_INDEX_TOKEN}abc', 0),
        )
        self.assertEqual(core.build_font_spec('sample.ttf', 0), 'sample.ttf')
        self.assertEqual(core.build_font_spec('sample.ttc', 0), f'sample.ttc{core.FONT_SPEC_INDEX_TOKEN}0')
        self.assertEqual(core.build_font_spec('sample.ttf', 2), f'sample.ttf{core.FONT_SPEC_INDEX_TOKEN}2')

    def test_font_path_key_and_name_parts_handle_edge_cases(self):
        expected_key = FONT_PATH.name if FONT_PATH.parent == ROOT / 'Font' else str(FONT_PATH)
        self.assertEqual(core._font_path_key(FONT_PATH), expected_key)
        self.assertEqual(core._font_name_parts(self.font), self.font.getname())
        self.assertEqual(core._font_name_parts(object()), ('', ''))

    def test_make_font_variant_falls_back_to_truetype_or_original_font(self):
        variant = core._make_font_variant(self.font, 18)
        self.assertTrue(hasattr(variant, 'getbbox'))
        self.assertIs(variant, core._make_font_variant(self.font, 18))

        variant_from_path = core._make_font_variant(_VariantTypeErrorFont(), 14)
        self.assertTrue(hasattr(variant_from_path, 'getbbox'))
        self.assertIs(variant_from_path, core._make_font_variant(_VariantTypeErrorFont(), 14))

        original = _VariantNoPathFont()
        self.assertIs(core._make_font_variant(original, 14), original)

    def test_make_font_variant_memoizes_per_font_object_and_size(self):
        core.clear_font_entry_cache()
        with mock.patch.object(core, 'load_truetype_font', wraps=core.load_truetype_font) as mocked_loader:
            first = core._make_font_variant(self.font, 18)
            second = core._make_font_variant(self.font, 18)

        self.assertIs(first, second)
        self.assertEqual(mocked_loader.call_count, 1)

    def test_get_reference_glyph_center_handles_typeerror_and_empty_centers(self):
        center = core._get_reference_glyph_center(_BBoxTypeErrorFont(), is_bold=True, f_size=20)
        self.assertGreater(center, 0)
        self.assertEqual(core._get_reference_glyph_center(_NoCenterFont(), is_bold=False, f_size=22), 11.0)

    def test_get_reference_glyph_center_reuses_cacheable_font_path_cache(self):
        core.clear_font_entry_cache()
        with mock.patch.object(core, '_compute_reference_glyph_center', wraps=core._compute_reference_glyph_center) as mocked_compute:
            first = core._get_reference_glyph_center(self.font, is_bold=False, f_size=24)
            second = core._get_reference_glyph_center(self.font, is_bold=False, f_size=24)
        self.assertEqual(first, second)
        self.assertEqual(mocked_compute.call_count, 1)

    def test_get_reference_glyph_center_memoizes_per_noncacheable_font_object(self):
        core._get_reference_glyph_center.cache_clear()
        font = _CountingBBoxFont()

        first = core._get_reference_glyph_center(font, is_bold=True, f_size=20)
        second = core._get_reference_glyph_center(font, is_bold=True, f_size=20)

        self.assertEqual(first, second)
        self.assertEqual(len(font.calls), 7)

    def test_get_text_bbox_memoizes_per_noncacheable_font_object_and_bold_flag(self):
        font = _CountingBBoxFont()

        first = core._get_text_bbox(font, '漢', is_bold=False)
        second = core._get_text_bbox(font, '漢', is_bold=False)
        bold_bbox = core._get_text_bbox(font, '漢', is_bold=True)

        self.assertEqual(first, second)
        self.assertEqual(bold_bbox, (0, 2, 10, 18))
        self.assertEqual(font.calls, [('漢', 0), ('漢', 1)])

    def test_missing_glyph_signatures_for_font_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()

        def fake_render(text, *_args, **_kwargs):
            glyph = Image.new('L', (4, 6), 255)
            glyph.putpixel((len(str(text)) % 3, 1), 0)
            return glyph

        with mock.patch.object(core, '_render_text_glyph_image_shared', side_effect=fake_render) as mocked_render:
            first = core._missing_glyph_signatures_for_font(font, is_bold=False, is_italic=False)
            second = core._missing_glyph_signatures_for_font(font, is_bold=False, is_italic=False)

        self.assertEqual(first, second)
        self.assertEqual(mocked_render.call_count, len(core._VERTICAL_GLYPH_FALLBACK_SENTINELS))

    def test_font_has_distinct_glyph_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()

        def fake_render(text, *_args, **_kwargs):
            glyph = Image.new('L', (4, 6), 255)
            if text == '縦':
                glyph.putpixel((1, 1), 0)
            else:
                glyph.putpixel((0, 0), 0)
            return glyph

        with mock.patch.object(core, '_render_text_glyph_image_shared', side_effect=fake_render) as mocked_render:
            first = core._font_has_distinct_glyph(font, '縦', is_bold=False, is_italic=False)
            second = core._font_has_distinct_glyph(font, '縦', is_bold=False, is_italic=False)

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(mocked_render.call_count, 1 + len(core._VERTICAL_GLYPH_FALLBACK_SENTINELS))

    def test_font_has_distinct_glyph_for_noncacheable_font_returns_false_for_missing_glyph_signature(self):
        font = _RenderSignatureFont()

        def fake_render(_text, *_args, **_kwargs):
            glyph = Image.new('L', (4, 6), 255)
            glyph.putpixel((0, 0), 0)
            return glyph

        with mock.patch.object(core, '_render_text_glyph_image_shared', side_effect=fake_render):
            result = core._font_has_distinct_glyph(font, '縦', is_bold=False, is_italic=False)

        self.assertFalse(result)

    def test_font_has_distinct_glyph_for_noncacheable_font_returns_false_when_missing_sentinels_unavailable(self):
        font = _RenderSignatureFont()

        def fake_render(text, *_args, **_kwargs):
            if text in core._VERTICAL_GLYPH_FALLBACK_SENTINELS:
                raise OSError('sentinel unavailable')
            glyph = Image.new('L', (4, 6), 255)
            glyph.putpixel((1, 1), 0)
            return glyph

        with mock.patch.object(core, '_render_text_glyph_image_shared', side_effect=fake_render):
            result = core._font_has_distinct_glyph(font, '縦', is_bold=False, is_italic=False)

        self.assertFalse(result)

    def test_cached_font_has_distinct_glyph_returns_false_when_missing_sentinels_unavailable(self):
        with mock.patch.object(core, '_cached_glyph_signature', return_value=(4, 6, b'x')) as glyph_sig,              mock.patch.object(core, '_missing_glyph_signatures', return_value=()) as missing_sigs:
            result = core._cached_font_has_distinct_glyph('dummy.ttf', 0, 24, '縦', False, False)

        glyph_sig.assert_called_once_with('dummy.ttf', 0, 24, '縦', False, False)
        missing_sigs.assert_called_once_with('dummy.ttf', 0, 24, False, False)
        self.assertFalse(result)

    def test_should_rotate_to_horizontal_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        glyph = Image.new('L', (6, 18), 255)
        glyph.putpixel((1, 1), 0)

        with mock.patch.object(core, '_render_text_glyph_image_shared', return_value=glyph) as mocked_render:
            first = core._should_rotate_to_horizontal(font, 'A', is_bold=False, is_italic=False)
            second = core._should_rotate_to_horizontal(font, 'A', is_bold=False, is_italic=False)

        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(mocked_render.call_count, 1)

    def test_resolve_vertical_glyph_char_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        with mock.patch.object(core, '_font_has_distinct_glyph', side_effect=[False, True]) as mocked_has_glyph:
            first = core._resolve_vertical_glyph_char('…', font, is_bold=False, is_italic=False)
            second = core._resolve_vertical_glyph_char('…', font, is_bold=False, is_italic=False)

        self.assertEqual(first, '…')
        self.assertEqual(second, '…')
        self.assertEqual(mocked_has_glyph.call_count, 2)

    def test_resolve_tate_punctuation_draw_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        with mock.patch.object(core, '_resolve_vertical_glyph_char', return_value='、') as mocked_resolve:
            first = core._resolve_tate_punctuation_draw('、', font, is_bold=False, is_italic=False)
            second = core._resolve_tate_punctuation_draw('、', font, is_bold=False, is_italic=False)

        self.assertEqual(first, second)
        self.assertEqual(mocked_resolve.call_count, 1)

    def test_resolve_horizontal_bracket_draw_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        with mock.patch.object(core, '_resolve_vertical_glyph_char', return_value='「') as mocked_resolve,              mock.patch.object(core, '_should_rotate_horizontal_bracket', return_value=True) as mocked_rotate:
            first = core._resolve_horizontal_bracket_draw('「', font, 24, is_bold=False, is_italic=False)
            second = core._resolve_horizontal_bracket_draw('「', font, 24, is_bold=False, is_italic=False)

        self.assertEqual(first, second)
        self.assertEqual(mocked_resolve.call_count, 1)
        self.assertEqual(mocked_rotate.call_count, 1)

    def test_resolve_default_tate_draw_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        with mock.patch.object(core, '_resolve_vertical_glyph_char', return_value='︙') as mocked_resolve:
            first = core._resolve_default_tate_draw('…', font, is_bold=False, is_italic=False)
            second = core._resolve_default_tate_draw('…', font, is_bold=False, is_italic=False)

        self.assertEqual(first, second)
        self.assertEqual(mocked_resolve.call_count, 1)

    def test_resolve_cacheable_font_spec_memoizes_on_font_object(self):
        core.clear_font_entry_cache()
        with mock.patch.object(core, '_cached_resolve_cacheable_font_spec', wraps=core._cached_resolve_cacheable_font_spec) as mocked_cached:
            first = core._resolve_cacheable_font_spec(self.font)
            second = core._resolve_cacheable_font_spec(self.font)

        self.assertEqual(first, second)
        self.assertEqual(mocked_cached.call_count, 1)

    def test_resolve_and_require_font_path_cover_missing_and_non_file(self):
        self.assertIsNone(core.resolve_font_path(''))
        resolved = core.resolve_font_path(FONT_SPEC)
        self.assertEqual(resolved, FONT_PATH)
        self.assertEqual(core.require_font_path(FONT_SPEC), FONT_PATH)

        with self.assertRaisesRegex(RuntimeError, 'フォントが指定されていません'):
            core.require_font_path('')
        with self.assertRaisesRegex(RuntimeError, 'フォントが見つかりません'):
            core.require_font_path('missing_font.ttf')
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(RuntimeError, 'フォントパスが不正です'):
                core.require_font_path(tmpdir)

    def test_resolve_font_path_reuses_cached_filesystem_probe_for_same_spec(self):
        core.clear_font_entry_cache()
        fake_path = Path('/tmp/fake_font.ttf')
        exists_calls = []
        is_file_calls = []

        def fake_exists(path_obj):
            exists_calls.append(str(path_obj))
            return path_obj == fake_path

        def fake_is_file(path_obj):
            is_file_calls.append(str(path_obj))
            return path_obj == fake_path

        with mock.patch.object(core, '_candidate_font_paths', return_value=[fake_path]), \
             mock.patch.object(Path, 'exists', fake_exists), \
             mock.patch.object(Path, 'is_file', fake_is_file):
            resolved1 = core.resolve_font_path('fake_font.ttf')
            resolved2 = core.resolve_font_path('fake_font.ttf')

        self.assertEqual(resolved1, fake_path)
        self.assertEqual(resolved2, fake_path)
        self.assertEqual(len(exists_calls), 1)
        self.assertEqual(len(is_file_calls), 1)

    def test_require_font_path_reuses_cached_validation_for_same_spec(self):
        core.clear_font_entry_cache()
        fake_path = Path('/tmp/fake_font.ttf')
        exists_calls = []
        is_file_calls = []

        def fake_exists(path_obj):
            exists_calls.append(str(path_obj))
            return path_obj == fake_path

        def fake_is_file(path_obj):
            is_file_calls.append(str(path_obj))
            return path_obj == fake_path

        with mock.patch.object(core, 'resolve_font_path', return_value=fake_path), \
             mock.patch.object(Path, 'exists', fake_exists), \
             mock.patch.object(Path, 'is_file', fake_is_file):
            resolved1 = core.require_font_path('fake_font.ttf')
            resolved2 = core.require_font_path('fake_font.ttf')

        self.assertEqual(resolved1, fake_path)
        self.assertEqual(resolved2, fake_path)
        self.assertEqual(len(exists_calls), 1)
        self.assertEqual(len(is_file_calls), 1)

    def test_describe_font_value_covers_ttf_and_ttc_fallbacks(self):
        described = core.describe_font_value(FONT_PATH)
        self.assertTrue(described.startswith(FONT_PATH.name))
        fake_ttc = f'fake.ttc{core.FONT_SPEC_INDEX_TOKEN}4'
        with mock.patch.object(core, 'load_truetype_font', side_effect=RuntimeError('boom')):
            self.assertEqual(core.describe_font_value(fake_ttc), 'fake.ttc [index 4]')

    def test_font_entries_for_value_handles_nonexistent_ttf_and_ttc_fallback(self):
        self.assertEqual(core.get_font_entries_for_value('missing.ttf'), [])

        entries = core.get_font_entries_for_value(str(FONT_PATH))
        self.assertGreaterEqual(len(entries), 1)
        self.assertEqual(entries[0]['index'], 0)

        fake_ttc_path = ROOT / 'Font' / 'fake.ttc'
        real_exists = Path.exists

        def fake_exists(path_obj):
            if path_obj == fake_ttc_path:
                return True
            return real_exists(path_obj)

        load_calls = []

        def fake_load(font_value, size):
            load_calls.append((font_value, size))
            if len(load_calls) == 1:
                raise OSError('bad face 0')
            raise AssertionError('second TTC face should not be probed after fallback')

        with mock.patch.object(core, 'resolve_font_path', return_value=fake_ttc_path), \
             mock.patch.object(Path, 'exists', fake_exists), \
             mock.patch.object(core, 'load_truetype_font', side_effect=fake_load):
            core.clear_font_entry_cache()
            entries = core.get_font_entries_for_value(str(fake_ttc_path))

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['label'], 'fake.ttc [index 0]')
        self.assertEqual(entries[0]['index'], 0)

    def test_get_font_entries_and_font_list_dedupe_and_fallback(self):
        dup_entry = {'label': 'A', 'value': 'same.ttf', 'path': 'same.ttf', 'index': 0}
        unique_entry = {'label': 'B', 'value': 'other.ttf', 'path': 'other.ttf', 'index': 0}
        with mock.patch.object(core, '_font_entries_for_value', side_effect=[[dup_entry], [unique_entry]]), \
             mock.patch.object(core, '_font_scan_targets', return_value=('b.ttf', 'a.ttc')):
            entries = core.get_font_entries()
        self.assertEqual([entry['value'] for entry in entries], ['same.ttf', 'other.ttf'])

        with mock.patch.object(core, 'get_font_entries', return_value=[]):
            self.assertEqual(core.get_font_list(), ['(フォントなし)'])

    def test_get_code_font_value_warns_and_falls_back_when_no_candidate_loads(self):
        core.get_code_font_value.cache_clear()
        with mock.patch.object(Path, 'exists', return_value=False), \
             mock.patch.object(Path, 'glob', return_value=[]), \
             mock.patch.object(core, 'load_truetype_font', side_effect=OSError('bad font')):
            with self.assertLogs(core.LOGGER, level='WARNING') as cm:
                result = core.get_code_font_value('primary.ttf')
        self.assertEqual(result, 'primary.ttf')
        self.assertTrue(any('指定フォントをそのまま使用します' in msg for msg in cm.output))

        core.get_code_font_value.cache_clear()
        with mock.patch.object(Path, 'exists', return_value=False), \
             mock.patch.object(Path, 'glob', return_value=[]), \
             mock.patch.object(core, 'load_truetype_font', side_effect=OSError('bad font')):
            with self.assertLogs(core.LOGGER, level='WARNING') as cm:
                result = core.get_code_font_value('')
        self.assertEqual(result, '')
        self.assertTrue(any('コードブロック用フォントが見つかりませんでした' in msg for msg in cm.output))

    def test_create_image_draw_and_get_draw_target_cover_attribute_paths(self):
        img = Image.new('L', (20, 20), 255)
        draw = core.create_image_draw(img)
        self.assertIs(core._get_draw_target_image(draw), img)
        self.assertIs(getattr(draw, '_tategaki_target_image', None), img)

        plain_img = Image.new('L', (10, 10), 255)
        plain_draw = ImageDraw.Draw(plain_img)
        self.assertIs(core._get_draw_target_image(plain_draw), plain_img)
        self.assertIs(getattr(plain_draw, '_tategaki_target_image', None), plain_img)
        self.assertIs(core._get_draw_target_image(plain_draw), plain_img)

        with self.assertRaisesRegex(AttributeError, '描画先の Image オブジェクトを取得できませんでした'):
            core._get_draw_target_image(types.SimpleNamespace())

    def test_draw_weighted_text_italic_uses_glyph_paste_path(self):
        img = Image.new('L', (40, 40), 255)
        draw = core.create_image_draw(img)
        glyph = Image.new('L', (6, 8), 0)
        mask = Image.new('L', (6, 8), 255)
        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph, mask)) as mocked_bundle, \
             mock.patch.object(core, '_paste_glyph_image', wraps=core._paste_glyph_image) as mocked_paste:
            core.draw_weighted_text(draw, (5, 6), 'A', self.font, is_bold=True, is_italic=True)
        mocked_bundle.assert_called_once()
        mocked_paste.assert_called_once()
        self.assertIsNotNone(ImageOps.invert(img).getbbox())

    def test_render_text_glyph_image_rotate_and_italic_paths_return_nonempty_image(self):
        rotated = core._render_text_glyph_image('A', self.font, rotate_degrees=90)
        italic = core._render_text_glyph_image('A', self.font, is_italic=True)
        self.assertGreater(rotated.width, 0)
        self.assertGreater(rotated.height, 0)
        self.assertGreater(italic.width, 0)
        self.assertGreater(italic.height, 0)

    def test_build_text_glyph_image_uses_bbox_helpers(self):
        bbox = (1, 2, 11, 16)

        def delegated_bbox(font, text, is_bold=False):
            self.assertIs(font, self.font)
            self.assertEqual(text, 'A')
            self.assertFalse(is_bold)
            return bbox

        def delegated_dims(font, text, is_bold=False):
            self.assertIs(font, self.font)
            self.assertEqual(text, 'A')
            self.assertFalse(is_bold)
            return (10, 14)

        with mock.patch.object(core, '_get_text_bbox', side_effect=delegated_bbox) as mocked_bbox,              mock.patch.object(core, '_get_text_bbox_dims', side_effect=delegated_dims) as mocked_dims:
            img = core._build_text_glyph_image('A', self.font)

        mocked_bbox.assert_called_once()
        mocked_dims.assert_called_once()
        self.assertGreater(img.width, 0)
        self.assertGreater(img.height, 0)

    def test_render_text_glyph_image_reuses_cached_glyph_raster_for_same_font_and_char(self):
        original_builder = core._build_text_glyph_image
        build_calls = []

        def counting_builder(*args, **kwargs):
            build_calls.append((args, kwargs))
            return original_builder(*args, **kwargs)

        core.clear_font_entry_cache()
        with mock.patch.object(core, '_build_text_glyph_image', side_effect=counting_builder):
            first = core._render_text_glyph_image('A', self.font)
            second = core._render_text_glyph_image('A', self.font)
            rotated = core._render_text_glyph_image('A', self.font, rotate_degrees=90)
            rotated_again = core._render_text_glyph_image('A', self.font, rotate_degrees=90)

        self.assertEqual(len(build_calls), 2)
        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertEqual(rotated.tobytes(), rotated_again.tobytes())
        self.assertIsNot(first, second)
        self.assertIsNot(rotated, rotated_again)

    def test_render_text_glyph_image_shared_reuses_cached_image_object_for_cacheable_font(self):
        core.clear_font_entry_cache()
        first = core._render_text_glyph_image_shared('A', self.font)
        second = core._render_text_glyph_image_shared('A', self.font)
        public_copy = core._render_text_glyph_image('A', self.font)

        self.assertEqual(first.tobytes(), second.tobytes())
        self.assertIs(first, second)
        self.assertEqual(first.tobytes(), public_copy.tobytes())
        self.assertIsNot(first, public_copy)

    def test_render_text_glyph_image_shared_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        glyph = Image.new('L', (5, 7), 0)

        with mock.patch.object(core, '_build_text_glyph_image', return_value=glyph) as mocked_build:
            first = core._render_text_glyph_image_shared('A', font, rotate_degrees=90)
            second = core._render_text_glyph_image_shared('A', font, rotate_degrees=90)

        self.assertIs(first, second)
        self.assertEqual(mocked_build.call_count, 1)

    def test_load_truetype_font_reuses_cached_font_object_for_same_spec_and_size(self):
        core.clear_font_entry_cache()
        with mock.patch.object(core.ImageFont, 'truetype', wraps=core.ImageFont.truetype) as mocked_truetype:
            font1 = core.load_truetype_font(FONT_SPEC, 24)
            font2 = core.load_truetype_font(FONT_SPEC, 24)
            font3 = core.load_truetype_font(FONT_SPEC, 26)

        self.assertIs(font1, font2)
        self.assertIsNot(font1, font3)
        self.assertEqual(mocked_truetype.call_count, 2)


    def test_render_text_glyph_and_mask_reuses_cached_bundle_for_same_font_and_char(self):
        original_builder = core._build_text_glyph_image
        build_calls = []

        def counting_builder(*args, **kwargs):
            build_calls.append((args, kwargs))
            return original_builder(*args, **kwargs)

        core.clear_font_entry_cache()
        with mock.patch.object(core, '_build_text_glyph_image', side_effect=counting_builder):
            first_img, first_mask = core._render_text_glyph_and_mask('A', self.font)
            second_img, second_mask = core._render_text_glyph_and_mask('A', self.font)
            rotated_img, rotated_mask = core._render_text_glyph_and_mask('A', self.font, rotate_degrees=90)
            rotated_img_again, rotated_mask_again = core._render_text_glyph_and_mask('A', self.font, rotate_degrees=90)

        self.assertEqual(len(build_calls), 2)
        self.assertEqual(first_img.tobytes(), second_img.tobytes())
        self.assertEqual(first_mask.tobytes(), second_mask.tobytes())
        self.assertEqual(rotated_img.tobytes(), rotated_img_again.tobytes())
        self.assertEqual(rotated_mask.tobytes(), rotated_mask_again.tobytes())
        self.assertIsNot(first_img, second_img)
        self.assertIsNot(first_mask, second_mask)
        self.assertIsNot(rotated_img, rotated_img_again)
        self.assertIsNot(rotated_mask, rotated_mask_again)

    def test_render_text_glyph_and_mask_shared_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        glyph = Image.new('L', (5, 7), 0)

        with mock.patch.object(core, '_build_text_glyph_image', return_value=glyph) as mocked_build,              mock.patch.object(core.ImageOps, 'invert', wraps=core.ImageOps.invert) as mocked_invert:
            first_img, first_mask = core._render_text_glyph_and_mask_shared('A', font, is_italic=True)
            second_img, second_mask = core._render_text_glyph_and_mask_shared('A', font, is_italic=True)

        self.assertIs(first_img, second_img)
        self.assertIs(first_mask, second_mask)
        self.assertEqual(mocked_build.call_count, 1)
        self.assertEqual(mocked_invert.call_count, 1)

    def test_font_has_distinct_glyph_reuses_cached_decision_for_same_font_and_char(self):
        core.clear_font_entry_cache()
        with mock.patch.object(core, '_cached_glyph_signature', wraps=core._cached_glyph_signature) as mocked_signature:
            first = core._font_has_distinct_glyph(self.font, '「')
            signature_calls_after_first = mocked_signature.call_count
            second = core._font_has_distinct_glyph(self.font, '「')

        self.assertEqual(first, second)
        self.assertGreater(signature_calls_after_first, 0)
        self.assertEqual(mocked_signature.call_count, signature_calls_after_first)


    def test_tatechuyoko_and_ascii_token_helpers_cover_false_paths(self):
        self.assertFalse(core._is_tatechuyoko_token(''))
        self.assertFalse(core._is_tatechuyoko_token('ABCDE'))
        self.assertFalse(core._is_tatechuyoko_token('ABCD'))
        self.assertFalse(core._is_tatechuyoko_token('あ1'))
        self.assertTrue(core._is_tatechuyoko_token('AI'))
        self.assertTrue(core._is_tatechuyoko_token('123'))
        self.assertTrue(core._is_tatechuyoko_token('2025'))
        self.assertFalse(core._should_center_ascii_glyph(''))
        self.assertFalse(core._should_center_ascii_glyph(' '))
        self.assertFalse(core._should_center_ascii_glyph('!'))
        self.assertTrue(core._should_center_ascii_glyph('A'))

    def test_tokenize_and_kinsoku_helpers_cover_edge_branches(self):
        self.assertEqual(core._tokenize_vertical_text('ABC!?..'), ['ABC', '!?', '.', '.'])
        self.assertFalse(core._is_line_head_forbidden(''))
        self.assertTrue(core._is_line_head_forbidden('!!'))
        self.assertFalse(core._is_line_end_forbidden(''))
        self.assertFalse(core._is_continuous_punctuation_pair('!!', '！'))
        self.assertEqual(core._continuous_punctuation_run_length(['A'], 1), 0)
        self.assertEqual(core._continuous_punctuation_run_length(['A'], 0), 0)
        self.assertEqual(core._closing_punctuation_group_length(['」', '!?', '。'], 0), 3)
        self.assertEqual(core._minimum_safe_group_length(['（', '」'], 5), 0)
        self.assertEqual(core._minimum_safe_group_length(['（', '」'], 0), 2)
        self.assertEqual(core._normalize_kinsoku_mode('weird'), 'standard')
        self.assertEqual(core._remaining_vertical_slots(50, 100, 10, 20), 1)
        self.assertEqual(core._effective_vertical_layout_bottom_margin(0, 20), 0)
        self.assertEqual(core._effective_vertical_layout_bottom_margin(12, 20), 17)
        self.assertLess(
            core._remaining_vertical_slots(0, 100, 12, 20),
            core._remaining_vertical_slots(0, 100, 0, 20),
        )
        self.assertEqual(
            core._remaining_vertical_slots_for_current_column(0, 0, 30, 20, 20),
            1,
        )
        self.assertEqual(
            core._remaining_vertical_slots_for_current_column(25, 0, 30, 20, 20),
            0,
        )
        self.assertEqual(
            core._remaining_vertical_slots_for_current_column(12, 10, 100, 10, 20, 2 * (20 + 2)),
            core._remaining_vertical_slots(12, 100, 10, 20),
        )
        self.assertTrue(core._would_start_forbidden_after_hang_pair(['あ', '、', '」'], 0))
        self.assertFalse(core._would_start_forbidden_after_hang_pair(['あ', '、'], 0))

    def test_choose_vertical_layout_action_covers_done_off_pair_and_recursive_advance(self):
        self.assertEqual(
            core._choose_vertical_layout_action([], 0, 0, 0, 100, 10, 20),
            'done',
        )
        self.assertEqual(
            core._choose_vertical_layout_action(['）'], 0, 10, 10, 100, 10, 20, kinsoku_mode='off'),
            'draw',
        )
        self.assertEqual(
            core._choose_vertical_layout_action(['!', '?'], 0, 70, 10, 100, 10, 20, kinsoku_mode='standard'),
            'advance',
        )
        self.assertEqual(
            core._choose_vertical_layout_action(['A', '、', '」'], 0, 70, 10, 100, 10, 20, kinsoku_mode='standard'),
            'advance',
        )
        self.assertEqual(
            core._choose_vertical_layout_action(['（', '」', '。'], 0, 40, 10, 100, 10, 20, kinsoku_mode='standard'),
            'advance',
        )

    def test_vertical_layout_hints_match_legacy_helpers(self):
        tokens = ['（', '」', '。', 'A', '、', '」', '!', '?']
        hints = core._build_vertical_layout_hints(tokens)

        self.assertEqual(hints['line_head_forbidden'][2], core._is_line_head_forbidden(tokens[2]))
        self.assertEqual(hints['line_end_forbidden'][0], core._is_line_end_forbidden(tokens[0]))
        self.assertEqual(hints['hanging_punctuation'][4], core._is_hanging_punctuation(tokens[4]))
        self.assertEqual(hints['continuous_pair_with_next'][6], core._is_continuous_punctuation_pair(tokens[6], tokens[7]))
        self.assertEqual(hints['would_start_forbidden_after_hang_pair'][3], core._would_start_forbidden_after_hang_pair(tokens, 3))
        self.assertEqual(
            list(hints['protected_group_len']),
            [core._protected_token_group_length(tokens, idx) for idx in range(len(tokens))],
        )

    def test_choose_vertical_layout_action_with_hints_matches_legacy_helper(self):
        cases = [
            (['）'], 10, 10, 100, 10, 20, 'off'),
            (['!', '?'], 70, 10, 100, 10, 20, 'standard'),
            (['A', '、', '」'], 70, 10, 100, 10, 20, 'standard'),
            (['（', '」', '。'], 40, 10, 100, 10, 20, 'standard'),
            (['（', '」', '。'], 10, 10, 100, 10, 20, 'simple'),
        ]
        for tokens, curr_y, margin_t, height, margin_b, font_size, mode in cases:
            with self.subTest(tokens=tokens, curr_y=curr_y, mode=mode):
                expected = core._choose_vertical_layout_action(
                    tokens, 0, curr_y, margin_t, height, margin_b, font_size, kinsoku_mode=mode,
                )
                hints = core._build_vertical_layout_hints(tokens)
                actual = core._choose_vertical_layout_action_with_hints(
                    hints,
                    0,
                    core._remaining_vertical_slots(curr_y, height, margin_b, font_size),
                    curr_y > margin_t,
                    kinsoku_mode=mode,
                    action_cache={},
                )
                self.assertEqual(actual, expected)

    def test_hanging_and_vertical_draw_helpers_render_pixels(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        core._draw_hanging_text_near_bottom(draw, '、', (10, 10), self.font, 24, 120)
        core._draw_hanging_text_near_bottom(draw, '）', (40, 10), self.font, 24, 120)
        core.draw_hanging_closing_bracket(draw, '）', (70, 10), self.font, 24, 120)
        core.draw_hanging_punctuation(draw, '。', (90, 10), self.font, 24, 120, is_italic=True)
        self.assertIsNotNone(ImageOps.invert(img).getbbox())
        self.assertTrue(core._is_lowerable_hanging_closing_bracket('）'))
        self.assertFalse(core._is_lowerable_hanging_closing_bracket('A'))

    def test_draw_hanging_punctuation_moves_line_head_punctuation_slightly_up(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        glyph_img = Image.new('L', (8, 8), 255)
        glyph_mask = Image.new('L', (8, 8), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 2, 6, 5), fill=255)
        pasted = []

        with mock.patch.object(core, '_resolve_tate_punctuation_draw', return_value=('︒', False)),              mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)) as render_bundle,              mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)):
            core.draw_hanging_punctuation(draw, '。', (10, 10), self.font, 24, 120)

        render_bundle.assert_called_once()
        self.assertEqual(len(pasted), 1)
        right_inset, top_inset, extra_raise = core._tate_punctuation_layout_insets(24, True, False)
        ink_top, ink_bottom = glyph_mask.getbbox()[1], glyph_mask.getbbox()[3]
        expected_x = 10 + max(0, 24 - glyph_img.width - right_inset)
        expected_y = 10 + core._tate_hanging_punctuation_offset_y(
            24,
            ink_top,
            ink_bottom,
            top_inset,
            extra_raise,
            120,
            glyph_img.height,
            False,
        )
        self.assertEqual(pasted[0], (expected_x, expected_y))

    def test_draw_hanging_punctuation_down_modes_move_down_and_up_modes_move_up(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        glyph_img = Image.new('L', (8, 8), 255)
        glyph_mask = Image.new('L', (8, 8), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 2, 6, 5), fill=255)

        def capture_y(position_mode: str) -> int:
            pasted = []
            setattr(draw, '_tategaki_punctuation_position_mode', position_mode)
            with mock.patch.object(core, '_resolve_tate_punctuation_draw', return_value=('︒', False)), \
                 mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)), \
                 mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)):
                core.draw_hanging_punctuation(draw, '。', (10, 10), self.font, 24, 120)
            self.assertEqual(len(pasted), 1)
            return pasted[0][1]

        standard_y = capture_y('standard')
        down_strong_y = capture_y('down_strong')
        down_weak_y = capture_y('down_weak')
        up_weak_y = capture_y('up_weak')
        up_strong_y = capture_y('up_strong')
        self.assertGreater(down_strong_y, down_weak_y)
        self.assertGreater(down_weak_y, standard_y)
        self.assertLess(up_weak_y, standard_y)
        self.assertLess(up_strong_y, up_weak_y)

    def test_draw_hanging_punctuation_unmapped_glyph_uses_image_path_without_vertical_resolution(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        glyph_img = Image.new('L', (8, 8), 255)
        glyph_mask = Image.new('L', (8, 8), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 1, 6, 6), fill=255)
        pasted = []

        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)) as render_bundle,              mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)),              mock.patch.object(core, '_resolve_tate_punctuation_draw', wraps=core._resolve_tate_punctuation_draw) as resolve_punct:
            core.draw_hanging_punctuation(draw, '，', (10, 10), self.font, 24, 120)

        self.assertEqual(resolve_punct.call_count, 0)
        render_bundle.assert_called_once_with('，', self.font, is_bold=False, is_italic=False)
        self.assertEqual(len(pasted), 1)
        right_inset, top_inset, extra_raise = core._tate_punctuation_layout_insets(24, True, False)
        ink_top, ink_bottom = glyph_mask.getbbox()[1], glyph_mask.getbbox()[3]
        expected_x = 10 + max(0, 24 - glyph_img.width - right_inset)
        expected_y = 10 + core._tate_hanging_punctuation_offset_y(
            24,
            ink_top,
            ink_bottom,
            top_inset,
            extra_raise,
            120,
            glyph_img.height,
            False,
        )
        self.assertEqual(pasted[0], (expected_x, expected_y))

    def test_draw_hanging_punctuation_near_page_bottom_stays_inside_canvas(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        glyph_img = Image.new('L', (10, 20), 255)
        glyph_mask = Image.new('L', (10, 20), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 0, 8, 19), fill=255)
        pasted = []

        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)), \
             mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)):
            core.draw_hanging_punctuation(draw, '，', (10, 95), self.font, 24, 120)

        self.assertEqual(len(pasted), 1)
        self.assertLessEqual(pasted[0][1] + glyph_img.height, 119)

    def test_draw_hanging_punctuation_allows_bottom_margin_overhang_but_not_canvas_escape(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        glyph_img = Image.new('L', (10, 20), 255)
        glyph_mask = Image.new('L', (10, 20), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 0, 8, 19), fill=255)
        pasted = []

        height = 120
        margin_b = 10
        font_size = 24
        effective_bottom_y = height - core._effective_vertical_layout_bottom_margin(margin_b, font_size)
        last_body_cell_y = effective_bottom_y - font_size

        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)), \
             mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)):
            core.draw_hanging_punctuation(draw, '，', (10, last_body_cell_y), self.font, font_size, height)

        self.assertEqual(len(pasted), 1)
        pasted_bottom = pasted[0][1] + glyph_img.height
        self.assertGreater(pasted_bottom, effective_bottom_y)
        self.assertLessEqual(pasted_bottom, height - 1)

    def test_draw_hanging_punctuation_allows_standard_kutoten_bottom_margin_overhang_only(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        glyph_img = Image.new('L', (10, 20), 255)
        glyph_mask = Image.new('L', (10, 20), 0)
        ImageDraw.Draw(glyph_mask).rectangle((1, 0, 8, 19), fill=255)
        pasted = []

        height = 120
        margin_b = 10
        font_size = 24
        effective_bottom_y = height - core._effective_vertical_layout_bottom_margin(margin_b, font_size)
        last_body_cell_y = effective_bottom_y - font_size

        with mock.patch.object(core, '_resolve_tate_punctuation_draw', return_value=('。', False)), \
             mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)), \
             mock.patch.object(core, '_paste_glyph_image', side_effect=lambda _draw, _img, xy, _mask=None: pasted.append(xy)):
            core.draw_hanging_punctuation(draw, '。', (10, last_body_cell_y), self.font, font_size, height)

        self.assertEqual(len(pasted), 1)
        pasted_bottom = pasted[0][1] + glyph_img.height
        self.assertGreater(pasted_bottom, effective_bottom_y)
        self.assertLessEqual(pasted_bottom, height - 1)

    def test_text_page_margin_clip_keeps_ordinary_bottom_margin_pixels_clipped(self):
        height = 120
        args = core.ConversionArgs(
            width=120,
            height=height,
            font_size=24,
            margin_t=0,
            margin_b=40,
            margin_l=0,
            margin_r=0,
            kinsoku_mode='standard',
            punctuation_position_mode='standard',
        )

        clip_start = core._bottom_margin_clip_start_for_text_page(height, args)
        self.assertEqual(clip_start, height - args.margin_b)

        img = Image.new('L', (120, height), 255)
        img.putpixel((10, clip_start - 1), 0)
        img.putpixel((10, clip_start), 0)

        core._apply_text_page_margin_clip(img, args)

        self.assertEqual(img.getpixel((10, clip_start - 1)), 0)
        self.assertEqual(img.getpixel((10, clip_start)), 255)

    def test_text_page_margin_clip_keeps_legacy_bottom_clip_when_hanging_is_off(self):
        height = 120
        args = core.ConversionArgs(
            width=120,
            height=height,
            font_size=24,
            margin_t=0,
            margin_b=40,
            margin_l=0,
            margin_r=0,
            kinsoku_mode='off',
        )

        self.assertEqual(core._hanging_punctuation_bottom_clip_allowance(args), 0)
        self.assertEqual(
            core._bottom_margin_clip_start_for_text_page(height, args),
            height - args.margin_b,
        )

    def test_hanging_punctuation_survives_text_page_bottom_margin_clip(self):
        height = 120
        margin_b = 40
        font_size = 24
        args = core.ConversionArgs(
            width=120,
            height=height,
            font_size=font_size,
            margin_t=0,
            margin_b=margin_b,
            margin_l=0,
            margin_r=0,
            kinsoku_mode='standard',
            punctuation_position_mode='standard',
        )
        effective_bottom_y = height - core._effective_vertical_layout_bottom_margin(margin_b, font_size)
        last_body_cell_y = effective_bottom_y - font_size
        glyph_img = Image.new('L', (10, 20), 0)
        glyph_mask = Image.new('L', (10, 20), 255)

        img = Image.new('L', (120, height), 255)
        draw = core.create_image_draw(img)
        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)):
            core.draw_hanging_punctuation(draw, '，', (10, last_body_cell_y), self.font, font_size, height)

        ordinary_margin_pixel = (80, height - margin_b + 5)
        img.putpixel(ordinary_margin_pixel, 0)
        before_clip_bbox = ImageOps.invert(img).getbbox()
        self.assertIsNotNone(before_clip_bbox)
        self.assertGreater(before_clip_bbox[3], height - margin_b)

        core._apply_text_page_margin_clip(img, args)

        self.assertEqual(img.getpixel(ordinary_margin_pixel), 255)
        restored_hanging_band = img.crop((0, height - margin_b, 50, height))
        self.assertIsNotNone(ImageOps.invert(restored_hanging_band).getbbox())

    def test_draw_hanging_closing_bracket_near_page_bottom_clamps_lower_edge(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        draw_positions = []

        def capture_draw(_draw, pos, text, _font, is_bold=False, is_italic=False):
            draw_positions.append((pos, text, is_bold, is_italic))

        with mock.patch.object(core, '_resolve_vertical_glyph_char', return_value='﹂'), \
             mock.patch.object(core, '_get_text_bbox', return_value=(0, 0, 12, 18)), \
             mock.patch.object(core, '_hanging_bottom_draw_offsets', return_value=(0, 16)), \
             mock.patch.object(core, 'draw_weighted_text', side_effect=capture_draw):
            core.draw_hanging_closing_bracket(draw, '」', (10, 105), self.font, 24, 120)

        self.assertEqual(draw_positions, [((10, 101), '﹂', False, False)])

    def test_tate_hanging_punctuation_raise_reuses_cache_and_uses_sweep317_safety_ratio(self):
        core._tate_hanging_punctuation_raise.cache_clear()
        first = core._tate_hanging_punctuation_raise(24, False)
        info_after_first = core._tate_hanging_punctuation_raise.cache_info()
        second = core._tate_hanging_punctuation_raise(24, False)
        info_after_second = core._tate_hanging_punctuation_raise.cache_info()

        self.assertEqual(first, max(3, int(round(24 * 0.30))))
        self.assertEqual(core._tate_hanging_punctuation_raise(24, True), max(3, int(round(24 * 0.24))))
        self.assertEqual(second, first)
        self.assertEqual(info_after_first.hits, 0)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_tate_hanging_punctuation_offset_y_pulls_low_font_glyph_upward(self):
        _, top_inset, extra_raise = core._tate_punctuation_layout_insets(24, True, False)
        baseline = core._tate_hanging_punctuation_offset_y(24, 2, 6, top_inset, extra_raise, 120, 8, False)
        low_font = core._tate_hanging_punctuation_offset_y(24, 4, 8, top_inset, extra_raise, 120, 8, False)
        self.assertLess(low_font, baseline)

    def test_tate_hanging_punctuation_offset_y_uses_sweep317_safe_visual_band(self):
        _, top_inset, extra_raise = core._tate_punctuation_layout_insets(24, True, False)
        offset_y = core._tate_hanging_punctuation_offset_y(24, 0, 12, top_inset, extra_raise, 120, 12, False)
        self.assertGreaterEqual(offset_y, int(round(24 * 0.62)))
        self.assertLessEqual(offset_y, int(round(24 * 0.34)) + 18)

    def test_tate_hanging_punctuation_offset_y_scales_with_font_size(self):
        _, top_inset_small, extra_raise_small = core._tate_punctuation_layout_insets(24, True, False)
        _, top_inset_large, extra_raise_large = core._tate_punctuation_layout_insets(48, True, False)
        small = core._tate_hanging_punctuation_offset_y(24, 2, 6, top_inset_small, extra_raise_small, 240, 8, False)
        large = core._tate_hanging_punctuation_offset_y(48, 4, 12, top_inset_large, extra_raise_large, 480, 16, False)
        self.assertGreater(large, small)


    def test_tate_hanging_punctuation_offset_y_keeps_large_font_from_overlapping_previous_cell(self):
        _, top_inset, extra_raise = core._tate_punctuation_layout_insets(64, True, False)
        offset_y = core._tate_hanging_punctuation_offset_y(64, 0, 10, top_inset, extra_raise, 640, 10, False)
        self.assertGreaterEqual(offset_y, int(round(64 * 0.72)))

    def test_tate_hanging_punctuation_offset_y_keeps_tall_glyph_from_overlapping_previous_cell(self):
        _, top_inset, extra_raise = core._tate_punctuation_layout_insets(24, True, False)
        offset_y = core._tate_hanging_punctuation_offset_y(24, 0, 24, top_inset, extra_raise, 120, 24, False)
        self.assertGreaterEqual(offset_y, int(round(24 * 0.78)))

    def test_tate_hanging_punctuation_offset_y_adds_guard_for_large_glyph_canvas(self):
        _, top_inset, extra_raise = core._tate_punctuation_layout_insets(24, True, False)
        offset_y = core._tate_hanging_punctuation_offset_y(24, 0, 16, top_inset, extra_raise, 120, 27, False)
        self.assertGreaterEqual(offset_y, int(round(24 * 0.82)))


    def test_vertical_dot_leader_centers_are_lowered_for_visual_balance(self):
        img = Image.new('L', (80, 80), 255)
        draw = core.create_image_draw(img)
        core.draw_vertical_dot_leader(draw, '…', (10, 10), 40)
        bbox = ImageOps.invert(img).getbbox()
        self.assertIsNotNone(bbox)
        self.assertGreaterEqual(bbox[1], 22)
        self.assertGreaterEqual(bbox[3], 43)


    def test_draw_hanging_text_near_bottom_reuses_bbox_helper(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        draw_positions = []

        def capture_draw(_draw, pos, text, _font, is_bold=False, is_italic=False):
            draw_positions.append((pos, text, is_bold, is_italic))

        with mock.patch.object(core, '_resolve_vertical_glyph_char', return_value='）'),              mock.patch.object(core, '_get_text_bbox', return_value=(0, 0, 8, 8)) as get_bbox,              mock.patch.object(core, 'draw_weighted_text', side_effect=capture_draw):
            core._draw_hanging_text_near_bottom(draw, '）', (10, 10), self.font, 24, 120, extra_raise_ratio=0.18)

        get_bbox.assert_called_once_with(self.font, '）', is_bold=False)
        self.assertEqual(draw_positions, [((10, 13), '）', False, False)])

    def test_draw_hanging_text_near_bottom_skips_vertical_resolution_for_unmapped_char(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        draw_positions = []

        def capture_draw(_draw, pos, text, _font, is_bold=False, is_italic=False):
            draw_positions.append((pos, text, is_bold, is_italic))

        with mock.patch.object(core, '_resolve_vertical_glyph_char', side_effect=AssertionError('should not resolve')),              mock.patch.object(core, '_get_text_bbox', return_value=(0, 0, 8, 8)) as get_bbox,              mock.patch.object(core, 'draw_weighted_text', side_effect=capture_draw):
            core._draw_hanging_text_near_bottom(draw, 'A', (10, 10), self.font, 24, 120)

        get_bbox.assert_called_once_with(self.font, 'A', is_bold=False)
        self.assertEqual(draw_positions, [((10, 15), 'A', False, False)])

    def test_hanging_bottom_layout_reuses_cache_for_same_parameters(self):
        core._hanging_bottom_layout.cache_clear()

        core._hanging_bottom_layout(24, False, 0.18)
        info_after_first = core._hanging_bottom_layout.cache_info()
        core._hanging_bottom_layout(24, False, 0.18)
        info_after_second = core._hanging_bottom_layout.cache_info()

        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)


    def test_hanging_bottom_draw_offsets_reuse_cache_for_same_parameters(self):
        core._hanging_bottom_draw_offsets.cache_clear()

        first = core._hanging_bottom_draw_offsets(24, 8, 120, True, 0.18)
        info_after_first = core._hanging_bottom_draw_offsets.cache_info()
        second = core._hanging_bottom_draw_offsets(24, 8, 120, True, 0.18)
        info_after_second = core._hanging_bottom_draw_offsets.cache_info()

        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_draw_hanging_text_near_bottom_uses_cached_offset_helper(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        draw_positions = []

        def capture_draw(_draw, pos, text, _font, is_bold=False, is_italic=False):
            draw_positions.append((pos, text, is_bold, is_italic))

        with mock.patch.object(core, '_resolve_vertical_glyph_char', return_value='、') as resolve_char,              mock.patch.object(core, '_get_text_bbox', return_value=(0, 0, 8, 8)) as get_bbox,              mock.patch.object(core, '_hanging_bottom_draw_offsets', return_value=(3, 5)) as draw_offsets,              mock.patch.object(core, 'draw_weighted_text', side_effect=capture_draw):
            core._draw_hanging_text_near_bottom(draw, '、', (10, 10), self.font, 24, 120)

        resolve_char.assert_called_once_with('、', self.font, is_bold=False, is_italic=False)
        get_bbox.assert_called_once_with(self.font, '、', is_bold=False)
        draw_offsets.assert_called_once_with(24, 8, 120, True, 0.0)
        self.assertEqual(draw_positions, [((13, 15), '、', False, False)])

    def test_hanging_closing_bracket_anchors_visible_ink_for_low_bbox_fonts(self):
        img = Image.new('L', (120, 120), 255)
        draw = core.create_image_draw(img)
        draw_positions = []

        def capture_draw(_draw, pos, text, _font, is_bold=False, is_italic=False):
            draw_positions.append((pos, text, is_bold, is_italic))

        with mock.patch.object(core, '_resolve_vertical_glyph_char', return_value='﹂') as resolve_char, \
             mock.patch.object(core, '_get_text_bbox', return_value=(0, 9, 12, 21)) as get_bbox, \
             mock.patch.object(core, '_hanging_bottom_draw_offsets', return_value=(0, 4)) as draw_offsets, \
             mock.patch.object(core, 'draw_weighted_text', side_effect=capture_draw):
            core.draw_hanging_closing_bracket(draw, '」', (10, 10), self.font, 24, 120)

        resolve_char.assert_called_once_with('」', self.font, is_bold=False, is_italic=False)
        get_bbox.assert_called_once_with(self.font, '﹂', is_bold=False)
        draw_offsets.assert_called_once_with(24, 12, 120, False, 0.18)
        self.assertEqual(draw_positions, [((10, 5), '﹂', False, False)])

    def test_double_punctuation_draw_offsets_reuse_cache_for_same_size(self):
        core._double_punctuation_draw_offsets.cache_clear()

        first = core._double_punctuation_draw_offsets(24)
        info_after_first = core._double_punctuation_draw_offsets.cache_info()
        second = core._double_punctuation_draw_offsets(24)
        info_after_second = core._double_punctuation_draw_offsets.cache_info()

        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_double_punctuation_layout_reuses_cache_for_same_size(self):
        core._double_punctuation_layout.cache_clear()

        core._double_punctuation_layout(24)
        info_after_first = core._double_punctuation_layout.cache_info()
        core._double_punctuation_layout(24)
        info_after_second = core._double_punctuation_layout.cache_info()

        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_draw_char_tate_double_punctuation_uses_cached_offsets(self):
        img = Image.new('L', (160, 120), 255)
        draw = core.create_image_draw(img)
        draw_positions = []

        def capture_draw(_draw, pos, text, _font, is_bold=False, is_italic=False):
            draw_positions.append((pos, text))

        with mock.patch.object(core, '_double_punctuation_draw_offsets', return_value=(18, 3, 15)) as offsets,              mock.patch.object(core, '_make_font_variant', return_value=self.font) as make_variant,              mock.patch.object(core, 'draw_weighted_text', side_effect=capture_draw):
            core.draw_char_tate(draw, '!?', (40, 10), self.font, 24)

        offsets.assert_called_once_with(24)
        make_variant.assert_called_once_with(self.font, 18)
        self.assertEqual(draw_positions, [((43, 10), '!'), ((55, 10), '?')])

    def test_draw_char_tate_keeps_inline_punctuation_standard_when_down_mode_selected(self):
        img = Image.new('L', (160, 120), 255)
        draw = core.create_image_draw(img)
        setattr(draw, '_tategaki_punctuation_position_mode', 'down_strong')
        draw_positions = []

        def capture_draw(_draw, pos, text, _font, is_bold=False, is_italic=False):
            draw_positions.append((pos, text))

        with mock.patch.object(core, 'draw_weighted_text', side_effect=capture_draw):
            core.draw_char_tate(draw, '，', (40, 10), self.font, 24)

        off_x, off_y = core._scaled_kutoten_offset(24)
        self.assertEqual(draw_positions, [((40 + off_x, 10 + off_y), '，')])

    def test_draw_char_tate_lower_closing_bracket_modes_move_only_target_up(self):
        img = Image.new('L', (160, 120), 255)
        draw = core.create_image_draw(img)

        def capture_extra_y(char: str, mode: str) -> int:
            captured = []
            setattr(draw, '_tategaki_lower_closing_bracket_position_mode', mode)

            def capture_centered(_draw, text, pos, _font, f_size, **kwargs):
                captured.append((text, kwargs.get('extra_y', 0)))

            with mock.patch.object(core, '_resolve_horizontal_bracket_draw', return_value=('﹂', 0, 0, -4)), \
                 mock.patch.object(core, 'draw_centered_glyph', side_effect=capture_centered):
                core.draw_char_tate(draw, char, (40, 10), self.font, 24)
            self.assertEqual(len(captured), 1)
            return int(captured[0][1])

        standard_y = capture_extra_y('」', 'standard')
        up_weak_y = capture_extra_y('」', 'up_weak')
        up_strong_y = capture_extra_y('」', 'up_strong')
        self.assertEqual(standard_y, -4)
        self.assertEqual(up_weak_y, -8)
        self.assertEqual(up_strong_y, -12)
        self.assertLess(up_weak_y, standard_y)
        self.assertLess(up_strong_y, up_weak_y)
        self.assertEqual(capture_extra_y('「', 'up_strong'), standard_y)

    def test_draw_tatechuyoko_and_char_tate_cover_major_dispatch_paths(self):
        img = Image.new('L', (160, 120), 255)
        draw = core.create_image_draw(img)
        core.draw_tatechuyoko(draw, 'ABCD', (10, 10), self.font, 24)
        core.draw_char_tate(draw, '!?', (40, 10), self.font, 24)
        core.draw_char_tate(draw, '、', (70, 10), self.font, 24)
        core.draw_char_tate(draw, 'ぁ', (90, 10), self.font, 24)
        core.draw_char_tate(draw, 'A', (110, 10), self.font, 24)
        core.draw_char_tate(draw, '漢', (130, 10), self.font, 24)
        self.assertIsNotNone(ImageOps.invert(img).getbbox())

    def test_draw_tatechuyoko_reuses_cached_fitted_bundle_for_cacheable_fonts(self):
        draw = core.create_image_draw(Image.new('L', (160, 120), 255))
        font = core.load_truetype_font(FONT_SPEC, 24)
        core._cached_tatechuyoko_bundle.cache_clear()
        core.draw_tatechuyoko(draw, '2025', (10, 10), font, 24)
        info_after_first = core._cached_tatechuyoko_bundle.cache_info()
        core.draw_tatechuyoko(draw, '2025', (10, 10), font, 24)
        info_after_second = core._cached_tatechuyoko_bundle.cache_info()
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_cached_tatechuyoko_fit_size_avoids_font_variant_loop_for_cacheable_font(self):
        font_path, font_index, _font_size = core._resolve_cacheable_font_spec(self.font)
        core._cached_tatechuyoko_fit_size.cache_clear()
        with mock.patch.object(core, '_cached_tatechuyoko_candidate_dims', wraps=core._cached_tatechuyoko_candidate_dims) as mocked_dims,              mock.patch.object(core, '_make_font_variant', side_effect=AssertionError('should not build font variants')):
            size = core._cached_tatechuyoko_fit_size(font_path, font_index, 24, '2025', False, False)

        self.assertGreaterEqual(size, 6)
        self.assertGreater(mocked_dims.call_count, 0)


    def test_line_head_forbidden_covers_iteration_marks(self):
        for ch in '々ゝゞヽヾ〻':
            self.assertIn(ch, core.ITERATION_MARK_CHARS)
            self.assertIn(ch, core.LINE_HEAD_FORBIDDEN_CHARS)

    def test_prolonged_sound_mark_covers_halfwidth_katakana_mark(self):
        self.assertIn('ｰ', core.PROLONGED_SOUND_MARK_CHARS)
        self.assertIn('ｰ', core.LINE_HEAD_FORBIDDEN_CHARS)

    def test_tate_replace_covers_em_dash_and_hyphen(self):
        self.assertEqual(core.TATE_REPLACE.get('—'), '丨')
        self.assertEqual(core.TATE_REPLACE.get('‐'), '丨')


    def test_draw_centered_glyph_nonrotated_nonitalic_uses_direct_text_path(self):
        img = Image.new('L', (80, 80), 255)
        draw = core.create_image_draw(img)
        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', wraps=core._render_text_glyph_and_mask_shared) as mocked_bundle:
            core.draw_centered_glyph(draw, 'A', (10, 10), self.font, 24, is_bold=False, rotate_degrees=0, align_to_text_flow=False, is_italic=False)
        self.assertEqual(mocked_bundle.call_count, 0)
        self.assertIsNotNone(ImageOps.invert(img).getbbox())

    def test_draw_centered_glyph_rotated_keeps_glyph_bundle_path(self):
        img = Image.new('L', (80, 80), 255)
        draw = core.create_image_draw(img)
        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', wraps=core._render_text_glyph_and_mask_shared) as mocked_bundle:
            core.draw_centered_glyph(draw, 'ー', (10, 10), self.font, 24, is_bold=False, rotate_degrees=90, align_to_text_flow=True, is_italic=False)
        self.assertEqual(mocked_bundle.call_count, 1)
        self.assertIsNotNone(ImageOps.invert(img).getbbox())

    def test_should_rotate_to_horizontal_from_glyph_image_uses_trimmed_size_directly(self):
        glyph_img = Image.new('L', (6, 14), 255)
        with self.assertRaises(AssertionError):
            with mock.patch.object(core.ImageOps, 'invert', side_effect=AssertionError('legacy trim path called')):
                core.ImageOps.invert(glyph_img)

        with mock.patch.object(core.ImageOps, 'invert', side_effect=AssertionError('legacy trim path called')):
            self.assertTrue(core._should_rotate_to_horizontal_from_glyph_image(glyph_img))

    def test_draw_tate_punctuation_glyph_nonitalic_uses_image_path(self):
        img = Image.new('L', (80, 120), 255)
        draw = core.create_image_draw(img)
        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', wraps=core._render_text_glyph_and_mask_shared) as mocked_bundle:
            core._draw_tate_punctuation_glyph(draw, '、', (10, 10), self.font, 24, is_bold=False, is_italic=False, next_cell=True, canvas_height=120, fallback_layout=False)
        self.assertEqual(mocked_bundle.call_count, 1)
        self.assertIsNotNone(ImageOps.invert(img).getbbox())

    def test_glyph_canvas_layout_reuses_cache_for_same_parameters(self):
        core._glyph_canvas_layout.cache_clear()
        first = core._glyph_canvas_layout(12, 16, 1, 2, 0, None)
        info_after_first = core._glyph_canvas_layout.cache_info()
        second = core._glyph_canvas_layout(12, 16, 1, 2, 0, None)
        info_after_second = core._glyph_canvas_layout.cache_info()
        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_centered_glyph_offset_helpers_reuse_cached_layout(self):
        core._centered_glyph_direct_offsets.cache_clear()
        first = core._centered_glyph_direct_offsets(24, 10, 12, 1, 2, True, 192, 0, 0)
        info_after_first = core._centered_glyph_direct_offsets.cache_info()
        second = core._centered_glyph_direct_offsets(24, 10, 12, 1, 2, True, 192, 0, 0)
        info_after_second = core._centered_glyph_direct_offsets.cache_info()
        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

        core._centered_glyph_image_offsets.cache_clear()
        first_img = core._centered_glyph_image_offsets(24, 14, 18, True, 192, 1, -1)
        info_after_first_img = core._centered_glyph_image_offsets.cache_info()
        second_img = core._centered_glyph_image_offsets(24, 14, 18, True, 192, 1, -1)
        info_after_second_img = core._centered_glyph_image_offsets.cache_info()
        self.assertEqual(first_img, second_img)
        self.assertEqual(info_after_second_img.hits, info_after_first_img.hits + 1)


    def test_tate_punctuation_offset_helpers_reuse_cached_layout(self):
        core._tate_punctuation_direct_offsets.cache_clear()
        first = core._tate_punctuation_direct_offsets(24, 8, 10, 1, 2, 1, 4, 3, True, 120, False)
        info_after_first = core._tate_punctuation_direct_offsets.cache_info()
        second = core._tate_punctuation_direct_offsets(24, 8, 10, 1, 2, 1, 4, 3, True, 120, False)
        info_after_second = core._tate_punctuation_direct_offsets.cache_info()
        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

        core._tate_punctuation_image_offsets.cache_clear()
        first_img = core._tate_punctuation_image_offsets(24, 10, 12, 1, 4, 3, False, 120, False)
        info_after_first_img = core._tate_punctuation_image_offsets.cache_info()
        second_img = core._tate_punctuation_image_offsets(24, 10, 12, 1, 4, 3, False, 120, False)
        info_after_second_img = core._tate_punctuation_image_offsets.cache_info()
        self.assertEqual(first_img, second_img)
        self.assertEqual(info_after_second_img.hits, info_after_first_img.hits + 1)


    def test_draw_tate_punctuation_glyph_italic_keeps_glyph_bundle_path(self):
        img = Image.new('L', (80, 120), 255)
        draw = core.create_image_draw(img)
        with mock.patch.object(core, '_render_text_glyph_and_mask_shared', wraps=core._render_text_glyph_and_mask_shared) as mocked_bundle:
            core._draw_tate_punctuation_glyph(draw, '、', (10, 10), self.font, 24, is_bold=False, is_italic=True, next_cell=False, canvas_height=120, fallback_layout=False)
        self.assertEqual(mocked_bundle.call_count, 1)
        self.assertIsNotNone(ImageOps.invert(img).getbbox())


    def test_italic_layout_helpers_reuse_cache_for_same_parameters(self):
        core._italic_extra_width.cache_clear()
        first_extra = core._italic_extra_width(18)
        info_after_first_extra = core._italic_extra_width.cache_info()
        second_extra = core._italic_extra_width(18)
        info_after_second_extra = core._italic_extra_width.cache_info()
        self.assertEqual(first_extra, second_extra)
        self.assertEqual(info_after_second_extra.hits, info_after_first_extra.hits + 1)

        core._italic_transform_layout.cache_clear()
        first_layout = core._italic_transform_layout(12, 18)
        info_after_first_layout = core._italic_transform_layout.cache_info()
        second_layout = core._italic_transform_layout(12, 18)
        info_after_second_layout = core._italic_transform_layout.cache_info()
        self.assertEqual(first_layout, second_layout)
        self.assertEqual(info_after_second_layout.hits, info_after_first_layout.hits + 1)

    def test_glyph_image_signature_uses_rendered_image_without_retrimming(self):
        glyph_img = core._render_text_glyph_image_shared('A', self.font)
        with mock.patch.object(core.ImageOps, 'invert', side_effect=AssertionError('legacy trim path called')):
            signature = core._glyph_image_signature(glyph_img)

        self.assertEqual(signature[0], glyph_img.width)
        self.assertEqual(signature[1], glyph_img.height)
        self.assertEqual(signature[2], glyph_img.tobytes())

    def test_estimate_tatechuyoko_candidate_dims_uses_cached_dims_for_cacheable_font(self):
        font_path, font_index, font_size = core._resolve_cacheable_font_spec(self.font)
        with mock.patch.object(core, '_cached_tatechuyoko_candidate_dims', return_value=(17, 14)) as mocked_dims:
            dims = core._estimate_tatechuyoko_candidate_dims(self.font, 'AB', is_bold=False, is_italic=True)

        mocked_dims.assert_called_once_with(font_path, font_index, font_size, 'AB', False, True)
        self.assertEqual(dims, (17, 14))

    def test_tatechuyoko_paste_offsets_reuse_cache_for_same_parameters(self):
        core._tatechuyoko_paste_offsets.cache_clear()
        first = core._tatechuyoko_paste_offsets(24, 10, 12)
        info_after_first = core._tatechuyoko_paste_offsets.cache_info()
        second = core._tatechuyoko_paste_offsets(24, 10, 12)
        info_after_second = core._tatechuyoko_paste_offsets.cache_info()
        self.assertEqual(first, second)
        self.assertEqual(info_after_second.hits, info_after_first.hits + 1)

    def test_draw_tatechuyoko_uses_cached_paste_offsets(self):
        draw = core.create_image_draw(Image.new('L', (160, 120), 255))
        glyph_img = Image.new('L', (10, 12), 0)
        glyph_mask = Image.new('L', (10, 12), 255)
        font_path, font_index, _font_size = core._resolve_cacheable_font_spec(self.font)

        with mock.patch.object(core, '_cached_tatechuyoko_bundle', return_value=(glyph_img, glyph_mask)) as cached_bundle,              mock.patch.object(core, '_tatechuyoko_paste_offsets', return_value=(7, 5)) as paste_offsets,              mock.patch.object(core, '_paste_glyph_image', wraps=core._paste_glyph_image) as paste_glyph:
            core.draw_tatechuyoko(draw, 'AB', (20, 30), self.font, 24)

        cached_bundle.assert_called_once_with(font_path, font_index, 24, 'AB', False, False)
        paste_offsets.assert_called_once_with(24, 10, 12)
        paste_glyph.assert_called_once()
        self.assertEqual(paste_glyph.call_args.args[2], (27, 35))

    def test_build_tatechuyoko_bundle_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()
        glyph_img = Image.new('L', (10, 12), 0)
        glyph_mask = Image.new('L', (10, 12), 255)

        with mock.patch.object(core, '_make_font_variant', return_value=font) as mocked_variant,              mock.patch.object(core, '_estimate_tatechuyoko_candidate_dims', return_value=(10, 12)) as mocked_dims,              mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)) as mocked_bundle:
            first = core._build_tatechuyoko_bundle(font, 'AB', 24)
            second = core._build_tatechuyoko_bundle(font, 'AB', 24)

        self.assertIs(first[0], second[0])
        self.assertIs(first[1], second[1])
        self.assertGreater(mocked_variant.call_count, 0)
        self.assertGreater(mocked_dims.call_count, 0)
        self.assertEqual(mocked_bundle.call_count, 1)

    def test_estimate_tatechuyoko_candidate_dims_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()

        with mock.patch.object(core, '_get_text_bbox_dims', return_value=(10, 12)) as mocked_dims,              mock.patch.object(core, '_italic_extra_width', return_value=3) as mocked_italic:
            first = core._estimate_tatechuyoko_candidate_dims(font, 'AB', is_bold=False, is_italic=True)
            second = core._estimate_tatechuyoko_candidate_dims(font, 'AB', is_bold=False, is_italic=True)

        self.assertEqual(first, (13, 12))
        self.assertEqual(second, (13, 12))
        mocked_dims.assert_called_once_with(font, 'AB', is_bold=False)
        mocked_italic.assert_called_once_with(12)

    def test_resolve_tatechuyoko_fit_size_memoizes_per_noncacheable_font_object(self):
        font = _RenderSignatureFont()

        with mock.patch.object(core, '_make_font_variant', return_value=font) as mocked_variant,              mock.patch.object(core, '_estimate_tatechuyoko_candidate_dims', return_value=(10, 12)) as mocked_dims:
            first = core._resolve_tatechuyoko_fit_size(font, 24, 'AB', is_bold=False, is_italic=False)
            second = core._resolve_tatechuyoko_fit_size(font, 24, 'AB', is_bold=False, is_italic=False)

        self.assertEqual(first, second)
        self.assertEqual(mocked_variant.call_count, 1)
        self.assertEqual(mocked_dims.call_count, 1)

    def test_resolve_tatechuyoko_fit_size_stops_early_when_font_cannot_variant(self):
        font = _VariantNoPathFont()

        with mock.patch.object(core, '_estimate_tatechuyoko_candidate_dims', return_value=(999, 999)) as mocked_dims:
            fit_size = core._resolve_tatechuyoko_fit_size(font, 24, 'AB', is_bold=False, is_italic=False)

        self.assertEqual(fit_size, core._tatechuyoko_layout_limits(24, 2)[2])
        self.assertEqual(mocked_dims.call_count, 1)

    def test_build_tatechuyoko_bundle_uses_fit_size_helper_for_noncacheable_font(self):
        font = _RenderSignatureFont()
        glyph_img = Image.new('L', (10, 12), 0)
        glyph_mask = Image.new('L', (10, 12), 255)

        with mock.patch.object(core, '_resolve_tatechuyoko_fit_size', return_value=18) as mocked_fit_size,              mock.patch.object(core, '_make_font_variant', return_value=font) as mocked_variant,              mock.patch.object(core, '_render_text_glyph_and_mask_shared', return_value=(glyph_img, glyph_mask)) as mocked_bundle:
            bundle = core._build_tatechuyoko_bundle(font, 'AB', 24)

        mocked_fit_size.assert_called_once_with(font, 24, 'AB', is_bold=False, is_italic=False)
        mocked_variant.assert_called_once_with(font, 18)
        mocked_bundle.assert_called_once_with('AB', font, is_bold=False, is_italic=False)
        self.assertIs(bundle[0], glyph_img)
        self.assertIs(bundle[1], glyph_mask)

if __name__ == '__main__':
    unittest.main()
