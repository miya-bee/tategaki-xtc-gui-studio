import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec


class _FakeCssItem:
    def __init__(self, file_name, css_text=None, media_type='text/css', raise_on_content=False):
        self.file_name = file_name
        self.media_type = media_type
        self._css_text = css_text or ''
        self._raise_on_content = raise_on_content

    def get_content(self):
        if self._raise_on_content:
            raise RuntimeError('boom')
        return self._css_text.encode('utf-8')


class _FakeBook:
    def __init__(self, items):
        self._items = list(items)

    def get_items(self):
        return list(self._items)


class EpubCssPagebreakSkipRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.BeautifulSoup = core._require_bs4_beautifulsoup()
        except Exception as exc:
            raise unittest.SkipTest(f'BeautifulSoup unavailable: {exc}')
        cls.font_path = resolve_test_font_path()

    def _soup(self, html):
        return self.BeautifulSoup(html, 'html.parser')

    def _load_fonts(self, args):
        font = core.load_truetype_font(self.font_path, args.font_size)
        ruby_font = core.load_truetype_font(self.font_path, args.ruby_size)
        return font, ruby_font

    def test_style_declares_bold_and_font_weight_helper_cover_edge_values(self):
        self.assertFalse(core.style_declares_bold(''))
        self.assertFalse(core.style_declares_bold('color: red;'))
        self.assertTrue(core.style_declares_bold('font-weight: bold;'))
        self.assertTrue(core.style_declares_bold('font-weight: 700;'))
        self.assertFalse(core.style_declares_bold('font-weight: 500;'))
        self.assertTrue(core._font_weight_value_is_bold('bolder'))
        self.assertFalse(core._font_weight_value_is_bold('normal'))

    def test_extract_bold_rules_skips_non_css_and_decode_errors(self):
        book = _FakeBook([
            _FakeCssItem('styles/main.css', '.strong { font-weight: 700; } #hero { font-weight: bold; } span { font-weight: 600; }'),
            _FakeCssItem('images/cover.png', '.ignored { font-weight: 700; }', media_type='image/png'),
            _FakeCssItem('styles/broken.css', raise_on_content=True),
        ])
        rules = core.extract_bold_rules(book)
        self.assertIn('strong', rules['classes'])
        self.assertIn('hero', rules['ids'])
        self.assertIn('span', rules['tags'])
        self.assertNotIn('ignored', rules['classes'])

    def test_node_is_bold_handles_inherited_tag_css_id_and_class_paths(self):
        soup = self._soup(
            '<body>'
            '<p id="hero">A</p>'
            '<span class="strong">B</span>'
            '<em style="font-weight: 700">C</em>'
            '<strong>D</strong>'
            '<section>E</section>'
            '</body>'
        )
        p, span, em, strong, section = soup.find_all(['p', 'span', 'em', 'strong', 'section'])
        rules = {'classes': {'strong'}, 'ids': {'hero'}, 'tags': {'section'}}

        self.assertTrue(core.node_is_bold(strong, False, {'classes': set(), 'ids': set(), 'tags': set()}))
        self.assertTrue(core.node_is_bold(section, False, rules))
        self.assertTrue(core.node_is_bold(em, False, {'classes': set(), 'ids': set(), 'tags': set()}))
        self.assertTrue(core.node_is_bold(p, False, rules))
        self.assertTrue(core.node_is_bold(span, False, rules))
        self.assertTrue(core.node_is_bold(section, True, {'classes': set(), 'ids': set(), 'tags': set()}))
        self.assertFalse(core.node_is_bold('plain text', False, {'classes': set(), 'ids': set(), 'tags': set()}))

    def test_paragraph_like_and_attr_token_helpers_cover_nested_and_split_values(self):
        soup = self._soup('<body><p>plain</p><div><p>nested</p></div><nav class="toc guide" role="doc-pagebreak/landmarks"></nav></body>')
        p = soup.find('p')
        div = soup.find('div')
        nav = soup.find('nav')

        self.assertTrue(core.is_paragraph_like(p))
        self.assertFalse(core.is_paragraph_like(div))
        self.assertEqual(core._epub_node_attr_tokens(nav), ['toc', 'guide', 'doc-pagebreak', 'landmarks'])

    def test_normalize_epub_text_fragment_cache_reuses_start_text_normalization(self):
        original = core._strip_leading_start_text
        calls = {'count': 0}

        def counting_strip(text):
            calls['count'] += 1
            return original(text)

        try:
            core._strip_leading_start_text = counting_strip
            first = core._normalize_epub_text_fragment('  start text : 本文\n', strip_start_text=True, strip_leading_for_indent=False)
            second = core._normalize_epub_text_fragment('  start text : 本文\n', strip_start_text=True, strip_leading_for_indent=False)
        finally:
            core._strip_leading_start_text = original
            core._normalize_epub_text_fragment.cache_clear()

        self.assertEqual(first, '本文')
        self.assertEqual(second, '本文')
        self.assertEqual(calls['count'], 1)

    def test_epub_node_analysis_exposes_paragraph_like_and_invalidates_on_structure_change(self):
        soup = self._soup('<body><p><span>x</span></p></body>')
        paragraph = soup.p

        first = core._epub_node_analysis(paragraph)
        self.assertTrue(first['paragraph_like'])

        paragraph.append(self._soup('<p>nested</p>').p)
        second = core._epub_node_analysis(paragraph)
        self.assertFalse(second['paragraph_like'])

    def test_css_selector_helpers_cover_normalize_split_match_and_merge(self):
        soup = self._soup('<body><p id="hero" class="lead strong" style="font-weight: 500; display: block;">x</p></body>')
        node = soup.p
        self.assertEqual(core._parse_css_style_declarations(' font-weight: 700 ; color: Red ; broken '), {'font-weight': '700', 'color': 'red'})
        self.assertEqual(core._split_css_selectors(' p.lead , span.note ,, #hero '), ['p.lead', 'span.note', '#hero'])
        self.assertEqual(core._normalize_epub_css_selector('body > p.lead::before[data-x]'), 'p.lead')
        self.assertEqual(core._normalize_epub_css_selector(''), '')
        self.assertTrue(core._epub_css_selector_matches_node(node, '*'))
        self.assertTrue(core._epub_css_selector_matches_node(node, 'p#hero.strong.lead'))
        self.assertFalse(core._epub_css_selector_matches_node(node, 'div#hero'))
        self.assertFalse(core._epub_css_selector_matches_node(node, 'p#other'))
        self.assertFalse(core._epub_css_selector_matches_node(node, 'p!!bad'))

        merged = core._merged_epub_css_for_node(
            node,
            css_rules=[
                {'selector': 'p.lead', 'declarations': {'font-weight': '700', 'display': 'none'}},
                {'selector': '.unused', 'declarations': {'visibility': 'hidden'}},
            ],
        )
        self.assertEqual(merged['font-weight'], '500')
        self.assertEqual(merged['display'], 'block')
        self.assertNotIn('visibility', merged)

    def test_extract_epub_css_rules_skips_empty_declarations_and_non_css_items(self):
        book = _FakeBook([
            _FakeCssItem('styles/main.css', 'p.note::before { color: red; } div[hidden] { display: none; } a, span.note { }'),
            _FakeCssItem('styles/extra.txt', 'p { margin-left: 1em; }', media_type='text/plain'),
            _FakeCssItem('styles/broken.css', raise_on_content=True),
        ])
        rules = core.extract_epub_css_rules(book)
        selectors = {rule['selector'] for rule in rules}
        self.assertIn('p.note', selectors)
        self.assertIn('div', selectors)
        self.assertNotIn('a', selectors)

    def test_skip_heading_length_pagebreak_note_and_indent_helpers_cover_css_branches(self):
        soup = self._soup(
            '<body>'
            '<script>x</script>'
            '<div hidden>y</div>'
            '<section aria-hidden="true">z</section>'
            '<p class="hidden-by-css">u</p>'
            '<nav epub:type="toc landmarks">toc</nav>'
            '<nav>keep</nav>'
            '<h2>見出し</h2>'
            '<span class="marker"></span>'
            '<div class="sectionbreak">pb</div>'
            '<p class="noteish">note</p>'
            '<p class="indented">indent</p>'
            '</body>'
        )
        script, hidden_div, aria_section, css_hidden, nav_toc, nav_keep, h2, marker, page_breaker, noteish, indented = soup.find_all(
            ['script', 'div', 'section', 'p', 'nav', 'nav', 'h2', 'span', 'div', 'p', 'p']
        )
        css_rules = [
            {'selector': '.hidden-by-css', 'declarations': {'display': 'none'}},
            {'selector': '.marker', 'declarations': {'page-break-before': 'always'}},
            {'selector': '.indented', 'declarations': {'margin-left': '2em', 'margin-top': '200%'}},
            {'selector': '.noteish', 'declarations': {'padding-left': '1em'}},
        ]

        self.assertTrue(core.epub_should_skip_node(script, css_rules=css_rules))
        self.assertTrue(core.epub_should_skip_node(hidden_div, css_rules=css_rules))
        self.assertTrue(core.epub_should_skip_node(aria_section, css_rules=css_rules))
        self.assertTrue(core.epub_should_skip_node(css_hidden, css_rules=css_rules))
        self.assertTrue(core.epub_should_skip_node(nav_toc, css_rules=css_rules))
        self.assertFalse(core.epub_should_skip_node(nav_keep, css_rules=css_rules))
        self.assertEqual(core.epub_heading_level(h2), 2)
        self.assertEqual(core.epub_heading_level(nav_keep), 0)
        self.assertEqual(core._css_length_to_chars('', 20), 0)
        self.assertEqual(core._css_length_to_chars('-1em', 20), 0)
        self.assertEqual(core._css_length_to_chars('40px', 20), 2)
        self.assertEqual(core._css_length_to_chars('2em', 20), 2)
        self.assertEqual(core._css_length_to_chars('150%', 20), 2)
        self.assertTrue(core.epub_node_requests_pagebreak(marker, css_rules=css_rules))
        self.assertTrue(core.epub_node_requests_pagebreak(page_breaker))
        self.assertTrue(core.epub_node_is_note_like(noteish, css_rules=css_rules, font_size=20))
        profile = core.epub_node_indent_profile(indented, css_rules=css_rules, font_size=20)
        self.assertEqual(profile['indent_chars'], 2)
        self.assertEqual(profile['wrap_indent_chars'], 2)
        self.assertEqual(profile['blank_before'], 2)

    def test_merged_css_cache_reuses_selector_scan_for_same_node(self):
        soup = self._soup('<body><p id="hero" class="lead" style="font-weight: 500">x</p></body>')
        node = soup.p
        css_rules = [
            {'selector': '.lead', 'declarations': {'display': 'block'}},
            {'selector': '#hero', 'declarations': {'page-break-before': 'always'}},
            {'selector': 'p.lead', 'declarations': {'margin-left': '2em'}},
        ]
        original = core._epub_css_selector_matches_node
        calls = {'count': 0}

        def counting_match(node_obj, selector):
            calls['count'] += 1
            return original(node_obj, selector)

        try:
            core._epub_css_selector_matches_node = counting_match
            merged_first = core._merged_epub_css_for_node(node, css_rules)
            first_call_count = calls['count']
            self.assertGreaterEqual(first_call_count, 3)
            self.assertEqual(merged_first['font-weight'], '500')
            self.assertEqual(merged_first['margin-left'], '2em')
            self.assertTrue(core.epub_node_requests_pagebreak(node, css_rules=css_rules))
            self.assertTrue(core.epub_node_is_note_like(node, css_rules=css_rules, font_size=20))
            profile = core.epub_node_indent_profile(node, css_rules=css_rules, font_size=20)
            self.assertEqual(profile['indent_chars'], 2)
            self.assertEqual(calls['count'], first_call_count)
        finally:
            core._epub_css_selector_matches_node = original

    def test_merged_css_cache_invalidates_when_inline_style_changes(self):
        soup = self._soup('<body><p class="lead" style="display:block">x</p></body>')
        node = soup.p
        css_rules = [{'selector': '.lead', 'declarations': {'visibility': 'hidden'}}]
        merged_first = core._merged_epub_css_for_node(node, css_rules)
        self.assertEqual(merged_first['display'], 'block')
        self.assertEqual(merged_first['visibility'], 'hidden')
        node['style'] = 'display:none'
        merged_second = core._merged_epub_css_for_node(node, css_rules)
        self.assertEqual(merged_second['display'], 'none')
        self.assertEqual(merged_second['visibility'], 'hidden')

    def test_paragraph_like_and_list_prefix_caches_invalidate_when_structure_changes(self):
        soup = self._soup('<body><p><span>x</span></p><ol start="3"><li>A</li><li>B</li></ol></body>')
        paragraph = soup.p
        li_a, li_b = soup.find('ol').find_all('li')

        self.assertTrue(core.is_paragraph_like(paragraph))
        paragraph.append(self._soup('<p>nested</p>').p)
        self.assertFalse(core.is_paragraph_like(paragraph))

        self.assertEqual(core._epub_list_item_prefix(li_a), '3．　')
        self.assertEqual(core._epub_list_item_prefix(li_b), '4．　')
        li_a['value'] = '9'
        self.assertEqual(core._epub_list_item_prefix(li_a), '9．　')
        self.assertEqual(core._epub_list_item_prefix(li_b), '4．　')

    def test_epub_node_analysis_cache_invalidates_when_class_and_role_change(self):
        soup = self._soup('<body><div class="lead" role="landmarks">x</div></body>')
        node = soup.div
        css_rules = [
            {'selector': '.lead', 'declarations': {'font-weight': '700', 'margin-left': '2em'}},
            {'selector': '.breakish', 'declarations': {'page-break-before': 'always'}},
        ]
        bold_rules = {'classes': {'lead'}, 'ids': set(), 'tags': set()}

        self.assertTrue(core.node_is_bold(node, False, bold_rules, css_rules=css_rules))
        self.assertEqual(core.epub_node_indent_profile(node, css_rules=css_rules, font_size=20)['indent_chars'], 2)
        self.assertFalse(core.epub_node_requests_pagebreak(node, css_rules=css_rules))
        self.assertFalse(core.epub_should_skip_node(node, css_rules=css_rules))

        node['class'] = ['breakish']
        node['role'] = 'toc'

        self.assertFalse(core.node_is_bold(node, False, bold_rules, css_rules=css_rules))
        self.assertEqual(core.epub_node_indent_profile(node, css_rules=css_rules, font_size=20)['indent_chars'], 0)
        self.assertTrue(core.epub_node_requests_pagebreak(node, css_rules=css_rules))
        self.assertFalse(core.epub_should_skip_node(node, css_rules=css_rules))

        node.name = 'nav'
        self.assertTrue(core.epub_should_skip_node(node, css_rules=css_rules))

    def test_pagebreak_marker_and_list_prefix_helpers_cover_text_image_and_orphan_cases(self):
        soup = self._soup(
            '<body>'
            '<hr/>'
            '<div class="pagebreak"></div>'
            '<div class="pagebreak">text</div>'
            '<div class="pagebreak"><img src="x.png"/></div>'
            '<ol start="3"><li value="9">A</li><li>B</li></ol>'
            '<ul><li>C</li></ul>'
            '<p>D</p>'
            '</body>'
        )
        hr, empty_div, text_div, image_div = soup.find_all(['hr', 'div', 'div', 'div'])
        ol_items = soup.find('ol').find_all('li')
        ul_item = soup.find('ul').find('li')
        p = soup.find('p')
        orphan = self._soup('<li>orphan</li>').li

        self.assertTrue(core.epub_pagebreak_node_is_marker(hr))
        self.assertTrue(core.epub_pagebreak_node_is_marker(empty_div))
        self.assertFalse(core.epub_pagebreak_node_is_marker(text_div))
        self.assertFalse(core.epub_pagebreak_node_is_marker(image_div))
        self.assertEqual(core._epub_list_item_prefix(ol_items[0]), '9．　')
        self.assertEqual(core._epub_list_item_prefix(ol_items[1]), '4．　')
        self.assertEqual(core._epub_list_item_prefix(ul_item), '・　')
        self.assertEqual(core._epub_list_item_prefix(p), '')
        self.assertEqual(core._epub_list_item_prefix(orphan), '')

        profile_heading = core.epub_node_indent_profile(self._soup('<h1>T</h1>').h1)
        self.assertEqual(profile_heading['heading_level'], 1)
        self.assertEqual(profile_heading['blank_before'], 2)
        profile_li = core.epub_node_indent_profile(ol_items[1])
        self.assertEqual(profile_li['prefix'], '4．　')
        self.assertTrue(profile_li['prefix_bold'])
        self.assertEqual(profile_li['wrap_indent_chars'], 1)
        profile_blockquote = core.epub_node_indent_profile(self._soup('<blockquote>x</blockquote>').blockquote)
        self.assertGreaterEqual(profile_blockquote['indent_chars'], 1)

    def test_render_epub_chapter_renderer_skips_toc_and_flushes_non_marker_pagebreak_nodes(self):
        args = core.ConversionArgs(
            width=180,
            height=180,
            font_size=24,
            ruby_size=12,
            line_spacing=32,
            output_format='xtc',
            margin_t=8,
            margin_b=8,
            margin_l=8,
            margin_r=8,
        )
        font, ruby_font = self._load_fonts(args)
        html = (
            '<html><body>'
            '<!-- comment should be ignored -->'
            '<nav epub:type="toc"><p>目次</p></nav>'
            '<p>前</p>'
            '<div class="pagebreak">後</div>'
            '</body></html>'
        )
        rendered_chars = []
        original_draw_char_tate = core.draw_char_tate

        def recording_draw(draw, char, pos_tuple, font_obj, f_size, **kwargs):
            rendered_chars.append(char)
            return None

        try:
            core.draw_char_tate = recording_draw
            pages = core._render_epub_chapter_pages_from_html(
                html,
                'text/chapter1.xhtml',
                args,
                font,
                ruby_font,
                {'classes': set(), 'ids': set(), 'tags': set()},
                {},
                {},
            )
        finally:
            core.draw_char_tate = original_draw_char_tate

        self.assertIn('前後', ''.join(rendered_chars))
        self.assertNotIn('目次', ''.join(rendered_chars))
        self.assertGreaterEqual(len(pages), 2)
        self.assertTrue(all(page['label'] == '本文ページ' for page in pages))


if __name__ == '__main__':
    unittest.main()
