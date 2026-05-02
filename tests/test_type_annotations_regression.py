import inspect
import unittest
from collections.abc import Collection
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

import tategakiXTC_gui_core as core
import tategakiXTC_gui_core_renderer as core_renderer
import tategakiXTC_gui_core_epub as core_epub
import tategakiXTC_worker_logic as worker_logic

from tests.studio_import_helper import load_studio_module


class TypeAnnotationRegressionTests(unittest.TestCase):
    def test_split_modules_expose_key_type_hints(self):
        for func in [
            core_renderer.generate_preview_base64,
            core_renderer._render_preview_page_from_target,
            core_renderer._render_text_blocks_to_page_entries,
            core_epub.load_epub_input_document,
            core_epub._render_epub_chapter_pages_from_html,
            core_epub.process_epub,
        ]:
            with self.subTest(func=func.__name__):
                hints = get_type_hints(func)
                self.assertIn('return', hints)

    def test_core_public_functions_have_return_type_hints(self):
        for func in [
            core.generate_preview_base64,
            core.process_archive,
            core.process_epub,
            core.process_text_file,
            core.process_markdown_file,
            core._classify_epub_embedded_image,
            core._make_inline_epub_image,
            core._resolve_epub_image_data,
            core._epub_runs,
            core._render_epub_chapter_pages_from_html,
            core._make_page_entry,
            core._append_page_entries_to_spool,
            core._write_page_entries_to_xtc,
            core.find_output_conflicts,
            core.apply_xtc_filter,
            core.apply_xtch_filter,
            core.png_to_xtg_bytes,
            core.png_to_xth_bytes,
            core.build_xtc,
            core.page_image_to_xt_bytes,
            core._build_default_preview_blocks,
            core._resolve_preview_source_path,
            core._select_preview_blocks,
            core._preview_fit_image,
            core._preview_source_requires_font,
            core._preview_target_requires_font,
            core._render_preview_page_from_target,
            core._render_text_blocks_to_images,
            core.build_conversion_error_report,
            core.list_optional_dependency_status,
            core.get_missing_dependencies_for_suffixes,
            core.extract_bold_rules,
            core.extract_epub_css_rules,
            core._merged_epub_css_for_node,
            core.epub_node_indent_profile,
            core._parse_aozora_indent_note,
            core._parse_aozora_emphasis_note,
            core._parse_aozora_side_line_note,
            core._scaled_kutoten_offset,
            core.create_image_draw,
            core._tokenize_vertical_text,
            core.draw_char_tate,
            core.get_font_entries,
            core.resolve_font_path,
            core.read_text_file_with_fallback,
            core._markdown_inline_to_runs,
            core._blocks_from_plain_text,
            core._extract_markdown_footnotes,
            core._blocks_from_markdown,
            core.load_text_input_document,
            core.load_archive_input_document,
            core.load_epub_input_document,
        ]:
            with self.subTest(func=func.__name__):
                hints = get_type_hints(func)
                self.assertIn('return', hints)

    def test_vertical_renderer_methods_have_key_type_hints(self):
        renderer_cls = core._VerticalPageRenderer
        for method_name in [
            'draw_runs',
            'draw_text_run',
            'advance_column',
            'insert_paragraph_indent',
            'add_full_page_image',
            'draw_side_lines',
            'draw_inline_image',
            '_iter_side_line_groups',
            '_draw_single_side_line',
        ]:
            with self.subTest(method_name=method_name):
                hints = get_type_hints(getattr(renderer_cls, method_name))
                self.assertIn('return', hints)


    def test_vertical_renderer_direct_run_helpers_use_vertical_layout_hints(self):
        renderer_cls = core._VerticalPageRenderer
        for method_name in [
            '_draw_text_run_plain',
            '_draw_text_run_ruby_only',
            '_draw_text_run_overlay_cells_only',
            '_draw_text_run_overlay_only',
        ]:
            with self.subTest(method_name=method_name):
                hints = get_type_hints(getattr(renderer_cls, method_name))
                self.assertIs(hints.get('layout_hints'), core.VerticalLayoutHints)
                self.assertIn('return', hints)


    def test_renderer_local_type_annotations_are_not_redeclared_in_same_scope(self):
        preview_source = inspect.getsource(core_renderer._render_preview_pages_from_target)
        draw_runs_source = inspect.getsource(core_renderer._VerticalPageRenderer.draw_runs)

        self.assertLessEqual(preview_source.count('render_state: dict[str, object] = {}'), 1)
        self.assertLessEqual(preview_source.count('page_images: list[Image.Image] = []'), 1)
        self.assertEqual(draw_runs_source.count('ruby_overlay_groups: list[RubyOverlayGroup] = []'), 0)
        self.assertEqual(draw_runs_source.count('overlay_cells: list[OverlayCell] = []'), 0)
        self.assertIn('ruby_overlay_groups: list[RubyOverlayGroup]', draw_runs_source)
        self.assertIn('overlay_cells: list[OverlayCell]', draw_runs_source)


    def test_studio_helpers_and_worker_methods_have_type_hints(self):
        studio = load_studio_module(force_reload=True)
        for func in [
            studio._collect_missing_startup_dependencies,
            studio._show_startup_dependency_alert,
            studio._format_missing_dependency_message,
            studio.plan_output_path_for_target,
            studio.build_conversion_summary,
            studio.parse_xtc_pages,
            studio.xtg_blob_to_qimage,
            studio.xth_blob_to_qimage,
            studio.xt_page_blob_to_qimage,
            studio.ConversionWorker._build_args,
            studio.ConversionWorker._resolve_supported_targets,
            studio.ConversionWorker._sanitize_output_stem,
            studio.ConversionWorker._collect_conversion_counts,
            studio.ConversionWorker._resolve_open_folder_target,
        ]:
            with self.subTest(func=func.__name__):
                hints = get_type_hints(func)
                self.assertIn('return', hints)

    def test_studio_mainwindow_and_viewer_methods_have_key_type_hints(self):
        studio = load_studio_module(force_reload=True)
        for func in [
            studio.XtcViewerWidget.set_profile,
            studio.XtcViewerWidget.set_page_image,
            studio.XtcViewerWidget._calculate_rects,
            studio.ConversionWorker._emit_progress,
            studio.ConversionWorker._make_progress_callback,
            studio.ConversionWorker._output_path_for_target,
            studio.ConversionWorker._process_target,
            studio.ConversionWorker._convert,
            studio.MainWindow.current_settings_dict,
            studio.MainWindow._supported_targets_for_path,
            studio.MainWindow._default_output_name_for_target,
            studio.MainWindow._prepare_conversion_settings,
            studio.MainWindow._available_font_entries,
            studio.MainWindow.current_font_value,
            studio.MainWindow.current_kinsoku_mode,
            studio.MainWindow.current_output_format,
            studio.MainWindow.current_output_conflict_mode,
            studio.MainWindow._load_preset_definitions,
            studio.MainWindow._preset_display_name,
            studio.MainWindow._preset_summary_text,
            studio.MainWindow.current_preset_payload,
            studio.MainWindow.refresh_preview,
            studio.MainWindow.load_xtc_from_path,
        ]:
            with self.subTest(func=func.__qualname__):
                hints = get_type_hints(func)
                self.assertIn('return', hints)
                self.assertIn('self', hints)

    def test_worker_logic_annotations_cover_primary_helpers(self):
        for func in [
            worker_logic.build_conversion_args,
            worker_logic.resolve_supported_conversion_targets,
            worker_logic.plan_output_path_for_target,
            worker_logic.extract_error_headline,
            worker_logic.summarize_error_headlines,
            worker_logic.collect_conversion_counts,
            worker_logic.resolve_open_folder_target,
            worker_logic.build_conversion_summary,
        ]:
            with self.subTest(func=func.__name__):
                hints = get_type_hints(func)
                self.assertIn('return', hints)



    def test_sweep469_type_hygiene_regressions(self):
        studio = load_studio_module(force_reload=True)

        batch_hints = get_type_hints(worker_logic.reserve_unique_output_path_for_batch)
        self.assertEqual(batch_hints['reserved_keys'], Collection[str] | None)

        paint_signature = inspect.signature(studio.VisibleArrowSpinBox.paintEvent)
        self.assertIs(paint_signature.parameters['self'].annotation, inspect.Signature.empty)

        wrapper_hints = get_type_hints(studio.plan_output_path_for_target)
        callback_hint = wrapper_hints['apply_conflict_strategy']
        callback_args = get_args(callback_hint)
        callback_types = [
            item for item in callback_args
            if get_origin(item) is not None and 'Callable' in str(get_origin(item))
        ]
        self.assertTrue(callback_types)
        callback_arg_types, callback_return_type = get_args(callback_types[0])
        self.assertEqual(callback_arg_types, [Path, str])
        self.assertEqual(callback_return_type, tuple[Path, core.ConflictPlan])

        apply_hints = get_type_hints(studio.ConversionWorker._apply_output_conflict_strategy)
        self.assertEqual(apply_hints['return'], tuple[Path, core.ConflictPlan])

        summary_signature = inspect.signature(worker_logic.build_conversion_summary)
        self.assertIn('summarize_error_headlines_func', summary_signature.parameters)
        self.assertNotIn('summarize_error_headlines', summary_signature.parameters)



    def test_worker_logic_typed_dicts_expose_expected_keys(self):
        self.assertEqual(
            worker_logic.WorkerConversionSettings.__optional_keys__,
            {
                'target', 'font_file', 'font_size', 'ruby_size', 'line_spacing',
                'margin_t', 'margin_b', 'margin_r', 'margin_l', 'dither',
                'threshold', 'night_mode', 'kinsoku_mode',
                'punctuation_position_mode', 'ichi_position_mode',
                'lower_closing_bracket_position_mode', 'output_format',
                'output_conflict', 'output_name', 'open_folder', 'width', 'height',
            },
        )
        self.assertEqual(
            worker_logic.ConversionCounts.__required_keys__,
            {'converted', 'renamed', 'overwritten', 'errors', 'skipped'},
        )
        self.assertEqual(
            worker_logic.ConflictPlan.__optional_keys__,
            {'desired_path', 'final_path', 'strategy', 'conflict', 'renamed', 'overwritten'},
        )
        self.assertEqual(
            worker_logic.ConversionErrorItem.__optional_keys__,
            {'source', 'error', 'headline', 'display'},
        )


    def test_core_typed_dicts_expose_expected_required_keys(self):
        self.assertEqual(
            core.TextRun.__required_keys__,
            {'text', 'ruby', 'bold', 'italic', 'emphasis', 'side_line', 'code'},
        )
        self.assertEqual(
            core.SegmentInfo.__required_keys__,
            frozenset(),
        )
        self.assertEqual(
            core.SegmentInfo.__optional_keys__,
            {'page_index', 'x', 'y', 'base_len', 'cell_text'},
        )
        self.assertEqual(
            core.PageEntry.__required_keys__,
            {'image', 'page_args', 'label'},
        )
        self.assertEqual(
            core.ConversionErrorReport.__required_keys__,
            {'headline', 'detail', 'hint', 'display'},
        )
        self.assertEqual(
            core.DependencyStatus.__required_keys__,
            {'key', 'label', 'package', 'purpose', 'impact', 'available'},
        )
        self.assertEqual(
            core.MissingDependency.__required_keys__,
            {'key', 'label', 'package', 'purpose'},
        )
        self.assertEqual(
            core.BoldRuleSets.__required_keys__,
            {'classes', 'ids', 'tags'},
        )
        self.assertEqual(
            core.CSSRule.__required_keys__,
            {'selector', 'declarations'},
        )
        self.assertEqual(
            core.EpubIndentProfile.__required_keys__,
            {'indent_chars', 'wrap_indent_chars', 'prefix', 'prefix_bold', 'blank_before', 'heading_level'},
        )
        self.assertEqual(
            core.AozoraNoteBlock.__optional_keys__,
            {'kind', 'indent_chars', 'wrap_indent_chars', 'target_text', 'emphasis', 'side_line'},
        )
        self.assertEqual(
            core.FontEntry.__required_keys__,
            {'label', 'value', 'path', 'index'},
        )
        self.assertEqual(
            core.FootnoteEntry.__required_keys__,
            {'id', 'text'},
        )

    def test_page_entry_and_epub_runs_follow_typed_dict_shape(self):
        args = core.ConversionArgs()
        page = core._make_page_entry(core.Image.new('L', (args.width, args.height), 255), page_args=args, label='本文ページ')
        self.assertEqual(set(page.keys()), {'image', 'page_args', 'label'})
        runs = core._epub_runs('sample', bold=True, italic=True, code=True, ruby='るび')
        self.assertEqual(len(runs), 1)
        self.assertEqual(set(runs[0].keys()), {'text', 'ruby', 'bold', 'italic', 'emphasis', 'side_line', 'code'})
        self.assertEqual(runs[0]['text'], 'sample')
        self.assertEqual(runs[0]['ruby'], 'るび')
        self.assertTrue(runs[0]['bold'])
        self.assertTrue(runs[0]['italic'])
        self.assertTrue(runs[0]['code'])

    def test_core_typed_alias_helpers_return_expected_shapes(self):
        report = core.build_conversion_error_report('sample.txt', FileNotFoundError('missing'))
        self.assertEqual(set(report.keys()), {'headline', 'detail', 'hint', 'display'})
        statuses = core.list_optional_dependency_status()
        self.assertTrue(all(set(item.keys()) == {'key', 'label', 'package', 'purpose', 'impact', 'available'} for item in statuses))
        rules = core.extract_epub_css_rules(type('Book', (), {'get_items': lambda self: []})())
        self.assertEqual(rules, [])


if __name__ == '__main__':
    unittest.main()
