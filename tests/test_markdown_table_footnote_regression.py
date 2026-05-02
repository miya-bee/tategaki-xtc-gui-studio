import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class MarkdownTableFootnoteRegressionTests(unittest.TestCase):
    def test_extract_markdown_footnotes_skips_front_matter_and_collects_multiline_notes(self):
        lines = [
            '---',
            'title: Sample',
            'tags: [a, b]',
            '---',
            '本文 [^n1]',
            '',
            '[^n1]: 1行目',
            '    2行目',
            '',
            '\t3行目',
            '[ref]: https://example.com',
        ]
        body_lines, footnotes, link_definitions = core._extract_markdown_footnotes(lines)
        self.assertEqual(body_lines, ['本文 [^n1]', ''])
        self.assertEqual(link_definitions, {'ref': 'https://example.com'})
        self.assertEqual(footnotes, [{'id': 'n1', 'text': '1行目\n2行目\n\n3行目'}])

    def test_extract_markdown_footnotes_keeps_note_syntax_inside_code_fence_literal(self):
        lines = [
            '```python',
            '[^code]: not a footnote',
            '[ref]: https://example.com/in-code',
            '```',
            '[^real]: 実際の脚注',
        ]
        body_lines, footnotes, link_definitions = core._extract_markdown_footnotes(lines)
        self.assertEqual(body_lines[:4], lines[:4])
        self.assertEqual(footnotes, [{'id': 'real', 'text': '実際の脚注'}])
        self.assertEqual(link_definitions, {})

    def test_markdown_inline_to_runs_resolves_images_links_and_styles(self):
        runs = core._markdown_inline_to_runs(
            '![図版][img] [参照][ref] [直リンク](https://x.invalid) [^n] ***強調*** `code`',
            link_definitions={'img': 'https://img.invalid/p.png', 'ref': 'https://example.com/doc'},
        )
        texts = [run['text'] for run in runs]
        self.assertIn('図版 参照 直リンク ※n ', ''.join(texts))
        self.assertTrue(any(run['text'] == '強調' and run['bold'] and run['italic'] for run in runs))
        self.assertTrue(any(run['text'] == 'code' and run['code'] for run in runs))

    def test_split_markdown_table_row_handles_escaped_pipes_and_trailing_backslash(self):
        cells = core._split_markdown_table_row(r'| 左\|中 | 右\\ | 末尾\\')
        self.assertEqual(cells, ['左|中', '右\\', '末尾\\'])

    def test_is_markdown_table_separator_accepts_alignment_markers_and_rejects_invalid_cells(self):
        self.assertTrue(core._is_markdown_table_separator('| :--- | ---: | :---: |'))
        self.assertFalse(core._is_markdown_table_separator('| -- | text |'))
        self.assertFalse(core._is_markdown_table_separator(''))

    def test_build_markdown_table_blocks_without_rows_emits_header_only_row(self):
        blocks = core._build_markdown_table_blocks(['列A', '', '列B'], [])
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]['kind'], 'table_row')
        texts = ''.join(run['text'] for run in blocks[0]['runs'])
        self.assertIn('列A', texts)
        self.assertIn('列B', texts)
        self.assertNotIn('：', texts)
        self.assertTrue(all(run['bold'] for run in blocks[0]['runs'] if run['text'].strip()))

    def test_build_markdown_table_blocks_with_rows_formats_pairs_and_skips_empty_cells(self):
        blocks = core._build_markdown_table_blocks(
            ['項目', '値', '備考'],
            [['色', '青'], ['', '空ヘッダ相当', '補足']],
        )
        self.assertEqual(len(blocks), 2)
        first_text = ''.join(run['text'] for run in blocks[0]['runs'])
        second_text = ''.join(run['text'] for run in blocks[1]['runs'])
        self.assertIn('項目：色', first_text)
        self.assertIn('値：青', first_text)
        self.assertIn('値：空ヘッダ相当', second_text)
        self.assertIn('備考：補足', second_text)

    def test_append_markdown_footnote_blocks_inserts_heading_and_blank_separator(self):
        blocks = [{'kind': 'paragraph', 'runs': [{'text': '本文', 'ruby': '', 'bold': False, 'italic': False, 'emphasis': '', 'side_line': '', 'code': False}]}]
        core._append_markdown_footnote_blocks(
            blocks,
            [
                {'id': 'n1', 'text': '脚注本文'},
                {'id': '', 'text': ''},
            ],
        )
        self.assertEqual([block['kind'] for block in blocks], ['paragraph', 'blank', 'heading', 'paragraph', 'paragraph'])
        self.assertEqual(''.join(run['text'] for run in blocks[2]['runs']), '脚注')
        self.assertEqual(''.join(run['text'] for run in blocks[3]['runs']), '※n1　脚注本文')
        self.assertEqual(''.join(run['text'] for run in blocks[4]['runs']), '※')

    def test_blocks_from_markdown_handles_table_definition_list_setext_and_quotes(self):
        text = (
            '見出し候補\n'
            '---\n\n'
            '| 項目 | 値 |\n'
            '| --- | --- |\n'
            '| 色 | [青][ref] |\n\n'
            '用語\n'
            ': 定義1\n'
            '  続き\n\n'
            '>\n'
            '> 引用本文\n\n'
            '[^n1]: 脚注本文\n'
            '[ref]: https://example.com/colors\n'
        )
        blocks = core._blocks_from_markdown(text)
        kinds = [block['kind'] for block in blocks]
        self.assertIn('heading', kinds)
        self.assertIn('table_row', kinds)
        self.assertIn('definition_term', kinds)
        self.assertIn('definition', kinds)
        self.assertIn('blockquote', kinds)
        self.assertIn('blank', kinds)
        heading_block = next(block for block in blocks if block['kind'] == 'heading')
        self.assertEqual(''.join(run['text'] for run in heading_block['runs']), '見出し候補')
        table_block = next(block for block in blocks if block['kind'] == 'table_row')
        self.assertIn('項目：色', ''.join(run['text'] for run in table_block['runs']))
        definition_block = next(block for block in blocks if block['kind'] == 'definition')
        self.assertIn('定義1続き'.replace('\u000c', '　'), ''.join(run['text'] for run in definition_block['runs']))
        quote_blocks = [block for block in blocks if block['kind'] == 'blockquote']
        self.assertEqual(''.join(run['text'] for run in quote_blocks[-1]['runs']), '引用：引用本文')
        footnote_heading = [block for block in blocks if block['kind'] == 'heading'][-1]
        self.assertEqual(''.join(run['text'] for run in footnote_heading['runs']), '脚注')

    def test_blocks_from_markdown_table_stops_before_code_fence(self):
        text = '| A | B |\n| --- | --- |\n```\nnot a row\n```'
        blocks = core._blocks_from_markdown(text)
        self.assertEqual([block['kind'] for block in blocks], ['table_row', 'code'])
        self.assertIn('A', ''.join(run['text'] for run in blocks[0]['runs']))
        self.assertEqual(''.join(run['text'] for run in blocks[1]['runs']), 'not a row')


if __name__ == '__main__':
    unittest.main()
