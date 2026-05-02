"""
P0-1 回帰テスト: 「一」の通常本文での中央配置

「一」が ruby_mode=False でも 実インクbbox基準で、かつ本文の見た目中心へ
合わせる専用描画で呼ばれることを確認する。
過去版に合わせ、回転角は 0 度を維持する。
"""

import sys
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core

FONT_DIR = ROOT / "Font"
_FONT_CANDIDATES = list(FONT_DIR.glob("*.ttf")) if FONT_DIR.exists() else []


def _make_font(size=40):
    if _FONT_CANDIDATES:
        return ImageFont.truetype(str(_FONT_CANDIDATES[0]), size)
    return ImageFont.load_default()


def _make_draw(size=200):
    img = Image.new("L", (size, size), 255)
    draw = core.create_image_draw(img)
    return draw, img


class IchiCenteringTests(unittest.TestCase):
    """「一」が通常本文時も 実インクbbox基準かつ本文中心で描かれることを確認する。

    Note:
        draw_centered_glyph は内部で _render_text_glyph_image → draw_weighted_text を
        呼ぶため「draw_weighted_text が呼ばれないこと」は保証できない。
        ここでは draw_centered_glyph が呼ばれたことと、
        draw_char_tate の直接の呼び出しルートだけを確認する。
    """

    def test_ichi_calls_ink_centered_glyph_in_normal_mode(self):
        """ruby_mode=False で実インクbbox基準の本文中心描画が呼ばれること。"""
        draw, _ = _make_draw()
        font = _make_font(40)
        f_size = 40

        with mock.patch.object(core, "draw_ink_centered_glyph", wraps=core.draw_ink_centered_glyph) as mock_cg:
            core.draw_char_tate(draw, "一", (10, 10), font, f_size, ruby_mode=False)

        mock_cg.assert_called_once()
        _, kwargs = mock_cg.call_args
        self.assertEqual(kwargs.get("rotate_degrees", 0), 0)
        self.assertIs(kwargs.get("align_to_text_flow"), True)

    def test_ichi_calls_ink_centered_glyph_in_ruby_mode(self):
        """ruby_mode=True でも実インクbbox基準の本文中心描画が呼ばれること。"""
        draw, _ = _make_draw()
        font = _make_font(40)
        f_size = 40

        with mock.patch.object(core, "draw_ink_centered_glyph", wraps=core.draw_ink_centered_glyph) as mock_cg:
            core.draw_char_tate(draw, "一", (10, 10), font, f_size, ruby_mode=True)

        mock_cg.assert_called_once()
        self.assertIs(mock_cg.call_args.kwargs.get("align_to_text_flow"), True)

    def test_chouon_still_uses_centered_glyph(self):
        """「ー」は従来どおり draw_centered_glyph が呼ばれること（既存挙動を壊さない）。"""
        draw, _ = _make_draw()
        font = _make_font(40)
        f_size = 40

        with mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
            core.draw_char_tate(draw, "ー", (10, 10), font, f_size)

        mock_cg.assert_called_once()
        _, kwargs = mock_cg.call_args
        self.assertIs(kwargs.get("align_to_text_flow"), True)

    def test_ichi_and_chouon_use_different_centering_helpers(self):
        """「一」は実インクを本文中心へ、「ー」は従来どおり本文基準線へ合わせること。"""
        font = _make_font(40)
        f_size = 40

        draw, _ = _make_draw()
        with mock.patch.object(core, "draw_ink_centered_glyph",
                               wraps=core.draw_ink_centered_glyph) as mock_ichi, \
             mock.patch.object(core, "draw_centered_glyph",
                               wraps=core.draw_centered_glyph) as mock_centered:
            core.draw_char_tate(draw, "一", (10, 10), font, f_size)
        mock_ichi.assert_called_once()
        mock_centered.assert_not_called()

        draw, _ = _make_draw()
        with mock.patch.object(core, "draw_centered_glyph",
                               wraps=core.draw_centered_glyph) as mock_centered:
            core.draw_char_tate(draw, "ー", (10, 10), font, f_size)
        mock_centered.assert_called_once()
        self.assertIs(mock_centered.call_args.kwargs.get("align_to_text_flow"), True)

    def test_ink_centered_glyph_offsets_center_actual_ink_height(self):
        """幾何中央モードではフォント外枠ではなく実インク高さを中央へ置くこと。"""
        self.assertEqual(core._ink_centered_glyph_image_offsets(40, 20, 4, 0, 0), (10, 18))
        self.assertEqual(core._ink_centered_glyph_image_offsets(41, 21, 5, 0, 0), (10, 18))

    def test_ink_flow_centered_glyph_offsets_follow_reference_center(self):
        """本文中心モードでは実インク中心を通常漢字の見た目中心へ合わせること。"""
        target_center_y_q16 = int(round(26.0 * 16.0))
        self.assertEqual(
            core._ink_flow_centered_glyph_image_offsets(40, 20, 4, target_center_y_q16, 0, 0),
            (10, 24),
        )

    def test_ichi_visual_target_center_has_safe_lower_bound(self):
        """参照中心が浅すぎる場合でも「一」を上寄りに戻さないこと。"""
        font = _make_font(40)
        with mock.patch.object(core, "_get_reference_glyph_center", return_value=20.0):
            self.assertEqual(core._get_ichi_visual_target_center_y(font, f_size=40), 24.8)

    def test_draw_ink_centered_glyph_pastes_trimmed_ink_to_cell_center(self):
        """幾何中央指定時は切り詰め済みグリフ画像がセル中央へ貼られること。"""
        draw, _ = _make_draw()
        font = _make_font(40)
        glyph = Image.new("L", (20, 4), 0)
        mask = Image.new("L", (20, 4), 255)
        calls = []

        def fake_paste(_draw, _glyph, xy, _mask):
            calls.append((xy, _glyph.size, _mask.size))

        with mock.patch.object(core, "_render_text_glyph_and_mask_shared", return_value=(glyph, mask)), \
             mock.patch.object(core, "_paste_glyph_image", side_effect=fake_paste):
            core.draw_ink_centered_glyph(draw, "一", (10, 10), font, 40)

        self.assertEqual(calls, [((20, 28), (20, 4), (20, 4))])

    def test_draw_ink_centered_glyph_pastes_trimmed_ink_to_flow_center(self):
        """本文中心指定時は「一」の実インクが通常漢字の見た目中心へ下がること。"""
        draw, _ = _make_draw()
        font = _make_font(40)
        glyph = Image.new("L", (20, 4), 0)
        mask = Image.new("L", (20, 4), 255)
        calls = []

        def fake_paste(_draw, _glyph, xy, _mask):
            calls.append((xy, _glyph.size, _mask.size))

        with mock.patch.object(core, "_render_text_glyph_and_mask_shared", return_value=(glyph, mask)), \
             mock.patch.object(core, "_get_ichi_visual_target_center_y", return_value=26.0), \
             mock.patch.object(core, "_paste_glyph_image", side_effect=fake_paste):
            core.draw_ink_centered_glyph(draw, "一", (10, 10), font, 40, align_to_text_flow=True)

        self.assertEqual(calls, [((20, 34), (20, 4), (20, 4))])


    def test_horizontal_brackets_rotate_original_glyphs_to_horizontal_shape(self):
        """各種括弧が元字形フォールバック時は横長向きの回転指定で描画されること。"""
        font = _make_font(40)
        f_size = 40

        originals = (
            "「", "」", "『", "』", "【", "】", "〈", "〉", "［", "］",
            "≪", "≫", "《", "》", "〔", "〕", "（", "）", "(", ")", "｛", "｝",
        )
        for original_char in originals:
            with self.subTest(char=original_char):
                draw, _ = _make_draw()
                with mock.patch.object(core, "_resolve_vertical_glyph_char", return_value=original_char),                      mock.patch.object(core, "_should_rotate_horizontal_bracket", return_value=True),                      mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
                    core.draw_char_tate(draw, original_char, (10, 10), font, f_size)

                mock_cg.assert_called_once()
                args, kwargs = mock_cg.call_args
                self.assertEqual(args[1], original_char)
                self.assertEqual(kwargs.get("rotate_degrees"), 270)

    def test_horizontal_brackets_keep_vertical_forms_unrotated(self):
        """縦書き用の横長字形が使える場合は未回転で使うこと。"""
        font = _make_font(40)
        f_size = 40
        bracket_pairs = (
            ("「", "﹁"), ("」", "﹂"), ("『", "﹃"), ("』", "﹄"),
            ("【", "︻"), ("】", "︼"), ("〈", "︿"), ("〉", "﹀"),
            ("［", "﹇"), ("］", "﹈"), ("≪", "︽"), ("≫", "︾"),
            ("《", "︽"), ("》", "︾"), ("〔", "︹"), ("〕", "︺"),
            ("（", "︵"), ("）", "︶"), ("(", "︵"), (")", "︶"),
            ("｛", "︷"), ("｝", "︸"),
        )
        for original_char, resolved_char in bracket_pairs:
            with self.subTest(char=original_char):
                draw, _ = _make_draw()
                with mock.patch.object(core, "_resolve_vertical_glyph_char", return_value=resolved_char),                      mock.patch.object(core, "_should_rotate_horizontal_bracket", return_value=False),                      mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
                    core.draw_char_tate(draw, original_char, (10, 10), font, f_size)

                mock_cg.assert_called_once()
                args, kwargs = mock_cg.call_args
                self.assertEqual(args[1], resolved_char)
                self.assertEqual(kwargs.get("rotate_degrees"), 0)


    def test_opening_kagikakko_are_shifted_slightly_right(self):
        """開きかぎ括弧だけが右寄せ補正されること。"""
        font = _make_font(40)
        f_size = 40

        for char in ("「", "『"):
            with self.subTest(char=char):
                draw, _ = _make_draw()
                with mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
                    core.draw_char_tate(draw, char, (10, 10), font, f_size)
                mock_cg.assert_called_once()
                self.assertGreater(mock_cg.call_args.kwargs.get('extra_x', 0), 0)

    def test_non_target_brackets_do_not_get_right_shift(self):
        """閉じかぎ括弧や他の括弧類には右寄せ補正を入れないこと。"""
        font = _make_font(40)
        f_size = 40

        for char in ("」", "』", "【"):
            with self.subTest(char=char):
                draw, _ = _make_draw()
                with mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
                    core.draw_char_tate(draw, char, (10, 10), font, f_size)
                mock_cg.assert_called_once()
                self.assertEqual(mock_cg.call_args.kwargs.get('extra_x', 0), 0)

    def test_opening_kagikakko_are_shifted_slightly_down(self):
        """開きかぎ括弧は横長向きのまま、やや下寄せで描画されること。"""
        font = _make_font(40)
        f_size = 40

        draw, _ = _make_draw()
        with mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
            core.draw_char_tate(draw, "「", (10, 10), font, f_size)
        mock_cg.assert_called_once()
        self.assertGreater(mock_cg.call_args.kwargs.get('extra_y', 0), 0)

    def test_closing_kagikakko_are_shifted_slightly_up(self):
        """閉じかぎ括弧は横長向きのまま、やや上寄せで描画されること。"""
        font = _make_font(40)
        f_size = 40

        draw, _ = _make_draw()
        with mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
            core.draw_char_tate(draw, "」", (10, 10), font, f_size)
        mock_cg.assert_called_once()
        self.assertLess(mock_cg.call_args.kwargs.get('extra_y', 0), 0)


    def test_closing_kagikakko_correction_is_stronger_for_low_fonts(self):
        self.assertLessEqual(core._kagikakko_extra_y('」', 40), -7)
        self.assertLessEqual(core._kagikakko_extra_y('』', 40), -7)

    def test_opening_kagikakko_down_shift_is_softened(self):
        self.assertLessEqual(core._kagikakko_extra_y('「', 40), 8)
        self.assertLessEqual(core._kagikakko_extra_y('『', 40), 8)

    def test_strip_leading_start_text_handles_repeated_marker(self):
        self.assertEqual(core._strip_leading_start_text('  start text : start_text - 本文'), '本文')
        self.assertEqual(core._normalize_text_line('  START TEXT：本文', has_started_document=False), '本文')

    def test_other_kanji_bypasses_centered_glyph(self):
        """「二」「三」は draw_centered_glyph を経由しないこと（通常文字の挙動を壊さない）。"""
        for char in ("二", "三"):
            with self.subTest(char=char):
                draw, _ = _make_draw()
                font = _make_font(40)
                f_size = 40

                # draw_centered_glyph が呼ばれないことだけを確認
                # （draw_weighted_text は内部呼び出しを含めカウント困難なため対象外）
                with mock.patch.object(core, "draw_centered_glyph", wraps=core.draw_centered_glyph) as mock_cg:
                    core.draw_char_tate(draw, char, (10, 10), font, f_size)

                mock_cg.assert_not_called()

    def test_draw_char_tate_uses_cached_horizontal_bracket_helper_when_font_is_cacheable(self):
        draw, _ = _make_draw()
        font = _make_font(40)

        with mock.patch.object(core, '_resolve_cacheable_font_spec', return_value=('dummy.ttf', 0, 40)), \
             mock.patch.object(core, '_cached_horizontal_bracket_draw', return_value=('﹁', 270, 2, -1)) as mock_helper, \
             mock.patch.object(core, 'draw_centered_glyph') as mock_draw_centered:
            core.draw_char_tate(draw, '「', (10, 10), font, 40)

        mock_helper.assert_called_once_with('dummy.ttf', 0, 40, '「', 40, False, False)
        mock_draw_centered.assert_called_once()
        self.assertEqual(mock_draw_centered.call_args.args[1], '﹁')


if __name__ == "__main__":
    unittest.main()
