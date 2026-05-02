import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class AozoraNoteParserRegressionTests(unittest.TestCase):
    def test_zenkaku_digits_to_int_handles_empty_invalid_and_fullwidth(self):
        self.assertIsNone(core._zenkaku_digits_to_int(None))
        self.assertIsNone(core._zenkaku_digits_to_int('   '))
        self.assertIsNone(core._zenkaku_digits_to_int('１２a'))
        self.assertEqual(core._zenkaku_digits_to_int(' １２ '), 12)

    def test_pagebreak_and_indent_notes_are_parsed(self):
        self.assertTrue(core._is_aozora_pagebreak_note(' 改ページ '))
        self.assertEqual(core._parse_aozora_indent_note('ここから２字下げ'), {
            'kind': 'indent_start',
            'indent_chars': 2,
            'wrap_indent_chars': 2,
        })
        self.assertEqual(core._parse_aozora_indent_note('３字下げ、折り返して１字下げ'), {
            'kind': 'indent_once',
            'indent_chars': 3,
            'wrap_indent_chars': 1,
        })
        self.assertEqual(core._parse_aozora_indent_note('字下げ終わり'), {'kind': 'indent_end'})
        self.assertIsNone(core._parse_aozora_indent_note(''))
        self.assertIsNone(core._parse_aozora_indent_note('これは注記ではない'))

    def test_indent_note_handles_failed_digit_conversion_paths(self):
        with patch.object(core, '_zenkaku_digits_to_int', side_effect=[None, 2]):
            self.assertIsNone(core._parse_aozora_indent_note('ここから2字下げ、折り返して2字下げ'))

        with patch.object(core, '_zenkaku_digits_to_int', side_effect=[2, None]):
            self.assertEqual(core._parse_aozora_indent_note('ここから2字下げ、折り返して2字下げ'), {
                'kind': 'indent_start',
                'indent_chars': 2,
                'wrap_indent_chars': 2,
            })

    def test_emphasis_kind_and_note_are_normalized(self):
        self.assertIsNone(core._normalize_aozora_emphasis_kind(''))
        self.assertEqual(core._normalize_aozora_emphasis_kind(' 白ごま傍点 '), '白ゴマ傍点')
        self.assertIsNone(core._parse_aozora_emphasis_note(''))
        self.assertIsNone(core._parse_aozora_emphasis_note('注記ではない'))
        self.assertIsNone(core._parse_aozora_emphasis_note('「語句」に未知傍点'))
        self.assertEqual(core._parse_aozora_emphasis_note('「語句」に丸傍点'), {
            'kind': 'emphasis',
            'target_text': '語句',
            'emphasis': '丸傍点',
        })

    def test_side_line_kind_and_note_are_normalized(self):
        self.assertIsNone(core._normalize_aozora_side_line_kind(''))
        self.assertEqual(core._normalize_aozora_side_line_kind(' 波線傍線 '), 'wavy')
        self.assertIsNone(core._parse_aozora_side_line_note(''))
        self.assertIsNone(core._parse_aozora_side_line_note('注記ではない'))
        self.assertIsNone(core._parse_aozora_side_line_note('「語句」に未知線'))
        self.assertEqual(core._parse_aozora_side_line_note('「語句」に二重傍線'), {
            'kind': 'side_line',
            'target_text': '語句',
            'side_line': 'double',
        })

    def test_merge_adjacent_runs_skips_empty_text_and_merges_matching_style(self):
        runs = [
            {'text': '', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
            {'text': '青', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
            {'text': '空', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
            {'text': '文庫', 'ruby': 'ぶんこ', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False},
        ]
        merged = core._merge_adjacent_runs(runs)
        self.assertEqual(merged[0]['text'], '青空')
        self.assertEqual(merged[1]['ruby'], 'ぶんこ')
        self.assertEqual(len(merged), 2)

    def test_apply_note_to_previous_block_routes_to_supported_note_kinds(self):
        blocks = [{'kind': 'paragraph', 'runs': [{'text': '本文', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False}]}]
        self.assertFalse(core._apply_note_to_previous_block([], {'kind': 'emphasis'}))
        self.assertFalse(core._apply_note_to_previous_block(blocks, None))
        self.assertFalse(core._apply_note_to_previous_block([{'kind': 'paragraph', 'runs': []}], {'kind': 'emphasis'}))
        self.assertTrue(core._apply_note_to_previous_block(blocks, {'kind': 'emphasis', 'target_text': '本文', 'emphasis': '丸傍点'}))
        self.assertEqual(blocks[0]['runs'][0]['emphasis'], '丸傍点')
        self.assertTrue(core._apply_note_to_previous_block(blocks, {'kind': 'side_line', 'target_text': '本文', 'side_line': 'wavy'}))
        self.assertEqual(blocks[0]['runs'][0]['side_line'], 'wavy')
        self.assertFalse(core._apply_note_to_previous_block(blocks, {'kind': 'pagebreak'}))

    def test_flush_and_append_text_run_merge_when_styles_match(self):
        runs = []
        core._flush_text_run_buffer(runs, '')
        self.assertEqual(runs, [])
        core._flush_text_run_buffer(runs, '青空', bold=False)
        core._flush_text_run_buffer(runs, '文庫', bold=False)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['text'], '青空文庫')
        core._append_text_run(runs, '')
        core._append_text_run(runs, '試験', bold=False)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['text'], '青空文庫試験')
        core._append_text_run(runs, '別', bold=True)
        self.assertEqual(len(runs), 2)
        self.assertTrue(runs[1]['bold'])

    def test_parse_aozora_note_only_line_prioritizes_specific_note_kinds(self):
        self.assertIsNone(core._parse_aozora_note_only_line('本文'))
        self.assertEqual(core._parse_aozora_note_only_line('［＃改ページ］'), {'kind': 'pagebreak'})
        self.assertEqual(core._parse_aozora_note_only_line('［＃ここから2字下げ］')['kind'], 'indent_start')
        self.assertEqual(core._parse_aozora_note_only_line('［＃「語句」に丸傍点］')['kind'], 'emphasis')
        self.assertEqual(core._parse_aozora_note_only_line('［＃「語句」に波線傍線］')['kind'], 'side_line')
        self.assertEqual(core._parse_aozora_note_only_line('［＃割り注］'), {'kind': 'note'})

    def test_aozora_inline_to_runs_supports_explicit_and_implicit_ruby(self):
        runs = core._aozora_inline_to_runs('前文｜青空《あおぞら》後文')
        self.assertEqual([run['text'] for run in runs], ['前文', '青空', '後文'])
        self.assertEqual(runs[1]['ruby'], 'あおぞら')

        implicit = core._aozora_inline_to_runs('東京《とうきょう》へ行く')
        self.assertEqual([run['text'] for run in implicit], ['東京', 'へ行く'])
        self.assertEqual(implicit[0]['ruby'], 'とうきょう')

    def test_aozora_inline_to_runs_keeps_literal_text_when_ruby_is_not_usable(self):
        runs = core._aozora_inline_to_runs('｜《るび》と《未対応》')
        self.assertEqual(''.join(run['text'] for run in runs), '｜《るび》と《未対応》')
        self.assertTrue(all(not run.get('ruby') for run in runs))

    def test_aozora_inline_to_runs_applies_inline_emphasis_and_side_line_notes(self):
        runs = core._aozora_inline_to_runs('前置き青空［＃「青空」に波線］文庫［＃「文庫」に丸傍点］')
        self.assertEqual([run['text'] for run in runs], ['前置き', '青空', '文庫'])
        self.assertEqual(runs[1]['side_line'], 'wavy')
        self.assertEqual(runs[2]['emphasis'], '丸傍点')

    def test_aozora_inline_to_runs_discards_unknown_inline_note_and_handles_empty(self):
        self.assertEqual(core._aozora_inline_to_runs(''), [])
        runs = core._aozora_inline_to_runs('本文［＃未知注記］末尾')
        self.assertEqual(''.join(run['text'] for run in runs), '本文末尾')

    def test_blocks_from_plain_text_apply_indent_pagebreak_and_aozora_notes(self):
        blocks = core._blocks_from_plain_text(
            '［＃ここから2字下げ、折り返して1字下げ］\n'
            '青空文庫\n'
            '［＃「文庫」に丸傍点］\n'
            '［＃ここで字下げ終わり］\n'
            '［＃改ページ］\n'
            '次段落'
        )
        self.assertEqual(blocks[0]['kind'], 'paragraph')
        self.assertEqual(blocks[0]['indent_chars'], 2)
        self.assertEqual(blocks[0]['wrap_indent_chars'], 1)
        self.assertEqual(blocks[0]['runs'][-1]['text'], '文庫')
        self.assertEqual(blocks[0]['runs'][-1]['emphasis'], '丸傍点')
        self.assertEqual(blocks[1]['kind'], 'pagebreak')
        self.assertEqual(blocks[2]['kind'], 'paragraph')
        self.assertEqual(blocks[2]['indent_chars'], 1)

    def test_blocks_from_markdown_apply_note_lines_but_leave_code_fence_literal(self):
        blocks = core._blocks_from_markdown(
            '［＃ここから3字下げ］\n'
            '青空文庫\n'
            '［＃「青空文庫」に波線傍線］\n'
            '```\n'
            '［＃改ページ］\n'
            '```\n'
            '［＃改ページ］\n'
            '後続'
        )
        self.assertEqual(blocks[0]['kind'], 'paragraph')
        self.assertEqual(blocks[0]['indent_chars'], 3)
        self.assertEqual(blocks[0]['runs'][0]['text'], '青空文庫')
        self.assertEqual(blocks[0]['runs'][0]['side_line'], 'wavy')
        code_blocks = [block for block in blocks if block.get('kind') == 'code']
        self.assertEqual(len(code_blocks), 1)
        self.assertIn('［＃改ページ］', ''.join(run['text'] for run in code_blocks[0]['runs']))
        pagebreaks = [block for block in blocks if block.get('kind') == 'pagebreak']
        self.assertEqual(len(pagebreaks), 1)
        self.assertEqual(blocks[-1]['kind'], 'paragraph')


if __name__ == '__main__':
    unittest.main()
