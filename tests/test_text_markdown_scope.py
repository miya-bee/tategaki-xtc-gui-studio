import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


class TextMarkdownScopeTests(unittest.TestCase):
    def test_markdown_front_matter_task_and_reference_link_are_handled(self):
        sample = """---
title: Sample
layout: post
---
# 見出し
- [ ] 未完了タスク
- [x] 完了タスク

[参考][ref]

[ref]: https://example.com/docs
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'sample.md'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='markdown')

        block_kinds = [block.get('kind') for block in document.blocks]
        self.assertEqual(document.parser_key, 'markdown')
        self.assertIn('task_list', block_kinds)
        self.assertEqual(document.blocks[0].get('kind'), 'heading')
        self.assertEqual(document.blocks[0].get('runs')[0].get('text'), '見出し')
        task_runs = [block.get('runs', []) for block in document.blocks if block.get('kind') == 'task_list']
        self.assertTrue(any(runs and runs[0].get('text') == '☐' for runs in task_runs))
        self.assertTrue(any(runs and runs[0].get('text') == '☑' for runs in task_runs))
        paragraph_runs = [block.get('runs', []) for block in document.blocks if block.get('kind') == 'paragraph']
        flattened = ''.join(run.get('text', '') for runs in paragraph_runs for run in runs)
        self.assertIn('参考', flattened)
        self.assertNotIn('title:', flattened)

    def test_markdown_warnings_collect_html_and_math(self):
        sample = """<div class='note'>
本文
</div>

$$
a^2+b^2=c^2
$$
"""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'warn.md'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='markdown')

        joined = '\n'.join(document.warnings or [])
        self.assertIn('生 HTML', joined)
        self.assertIn('数式ブロック', joined)

    def test_plain_text_strips_start_text_after_leading_blank_lines_until_real_content(self):
        sample = '\n\nstart text\n本文'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'plain.txt'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='plain')

        flattened = ''.join(
            run.get('text', '')
            for block in document.blocks
            for run in block.get('runs', [])
        )
        self.assertEqual(flattened, '本文')

    def test_markdown_strips_start_text_after_leading_blank_lines_until_real_content(self):
        sample = '\n\nstart text\n# 見出し\n\n本文'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'sample.md'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='markdown')

        flattened = ''.join(
            run.get('text', '')
            for block in document.blocks
            for run in block.get('runs', [])
        )
        self.assertNotIn('start text', flattened.lower())
        self.assertIn('見出し', flattened)
        self.assertIn('本文', flattened)

    def test_plain_text_strips_start_text_after_title_author_frontmatter(self):
        sample = '三四郎\n夏目漱石\n一\nstart text\nうとうととして目がさめると女は'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'plain.txt'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='plain')

        flattened = ''.join(
            run.get('text', '')
            for block in document.blocks
            for run in block.get('runs', [])
        )
        self.assertNotIn('start text', flattened.lower())
        self.assertIn('三四郎', flattened)
        self.assertIn('夏目漱石', flattened)
        self.assertIn('うとうととして目がさめると女は', flattened)

    def test_markdown_strips_start_text_after_heading_frontmatter(self):
        sample = '# 三四郎\n## 夏目漱石\nstart text\n\n本文'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'sample.md'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='markdown')

        flattened = ''.join(
            run.get('text', '')
            for block in document.blocks
            for run in block.get('runs', [])
        )
        self.assertNotIn('start text', flattened.lower())
        self.assertIn('三四郎', flattened)
        self.assertIn('夏目漱石', flattened)
        self.assertIn('本文', flattened)

    def test_plain_text_does_not_strip_start_text_after_document_has_started(self):
        sample = '本文\nstart text\n続き'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'plain.txt'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='plain')

        flattened = ''.join(
            run.get('text', '')
            for block in document.blocks
            for run in block.get('runs', [])
        )
        self.assertIn('start text', flattened)

    def test_plain_text_warns_when_markdown_like_lines_are_present(self):
        sample = '# 見出し\n- 箇条書き\n本文'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'plain.txt'
            path.write_text(sample, encoding='utf-8')
            document = core.load_text_input_document(path, parser='plain')

        joined = '\n'.join(document.warnings or [])
        self.assertIn('見出し記法', joined)
        self.assertIn('箇条書き', joined)


if __name__ == '__main__':
    unittest.main()
