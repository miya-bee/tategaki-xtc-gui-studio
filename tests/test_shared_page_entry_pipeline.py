import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core
from tests.font_test_helper import resolve_test_font_path, resolve_test_font_spec


class _FakeEpubItem:
    def __init__(self, file_name, html):
        self.file_name = file_name
        self._html = html

    def get_content(self):
        return self._html.encode('utf-8')


class SharedPageEntryPipelineTests(unittest.TestCase):
    def test_write_page_entries_to_xtc_respects_per_entry_args(self):
        args = core.ConversionArgs(width=320, height=480, output_format='xtc', night_mode=True)
        img1 = Image.new('L', (args.width, args.height), 255)
        alt_args = core.dc_replace(args, width=300, height=460, night_mode=False)
        img2 = Image.new('L', (alt_args.width, alt_args.height), 255)
        page_entries = [
            core._make_page_entry(img1, page_args=args, label='本文ページ'),
            core._make_page_entry(img2, page_args=alt_args, label='挿絵ページ'),
        ]
        observed = []

        def fake_page_image_to_xt_bytes(image, width, height, page_args):
            observed.append((width, height, page_args.night_mode))
            return b'page'

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtc'
            with mock.patch.object(core, 'page_image_to_xt_bytes', side_effect=fake_page_image_to_xt_bytes), \
                 mock.patch.object(core.XTCSpooledPages, 'finalize', side_effect=AssertionError('spool finalize should not be used')):
                result = core._write_page_entries_to_xtc(page_entries, out_path, args, output_path=out_path)
            self.assertEqual(result, out_path)
            data = out_path.read_bytes()
            header = data[:48]
            mark, version, page_count, *_ = struct.unpack('<4sHHBBBBIQQQQ', header)
            self.assertEqual(mark, b'XTC\x00')
            self.assertEqual(version, 1)
            self.assertEqual(page_count, 2)
            first = struct.unpack_from('<Q I H H', data, 48)
            second = struct.unpack_from('<Q I H H', data, 64)
            self.assertEqual(first[2:], (320, 480))
            self.assertEqual(second[2:], (300, 460))
        self.assertEqual(observed, [(320, 480, True), (300, 460, False)])

    def test_render_text_blocks_to_xtc_uses_page_entry_renderer_directly(self):
        args = core.ConversionArgs(width=320, height=480, output_format='xtc')
        entry = core._make_page_entry(Image.new('L', (320, 480), 255), page_args=args, label='本文ページ')
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtc'
            with mock.patch.object(core, '_render_text_blocks_to_page_entries', return_value=[entry]) as render_entries_mock,                  mock.patch.object(core, '_render_text_blocks_to_images', side_effect=AssertionError('legacy image path should not be used')),                  mock.patch.object(core, '_write_page_entries_to_xtc', return_value=out_path) as write_mock:
                result = core._render_text_blocks_to_xtc(
                    [{'kind': 'paragraph', 'runs': [{'text': '本文'}]}],
                    out_path,
                    resolve_test_font_path(),
                    args,
                    output_path=out_path,
                )
        self.assertEqual(result, out_path)
        render_entries_mock.assert_called_once()
        write_args = write_mock.call_args.args[0]
        self.assertEqual(len(write_args), 1)
        self.assertEqual(write_args[0]['label'], '描画済みページ')



    def test_process_epub_uses_shared_page_entry_pipeline(self):
        fake_doc = core.EpubInputDocument(
            source_path=Path('dummy.epub'),
            book=None,
            docs=[_FakeEpubItem('text/chapter1.xhtml', '<html><body><p>共有導線の確認です。</p></body></html>')],
            image_map={},
            image_basename_map={},
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
        )
        font_path = resolve_test_font_path()
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc')
        calls = []
        original_add_blob = core.XTCSpooledPages.add_blob

        def spy_add_blob(self, blob):
            calls.append(len(blob))
            return original_add_blob(self, blob)

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtc'
            with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc),                  mock.patch.object(core.XTCSpooledPages, 'add_blob', new=spy_add_blob):
                result = core.process_epub('dummy.epub', font_path, args, output_path=out_path)
            self.assertEqual(result, out_path)
            self.assertTrue(calls)


    def test_process_epub_illustration_page_uses_non_night_args(self):


        image = Image.new('L', (280, 280), 64)
        buf = io.BytesIO()
        image.save(buf, format='PNG')
        image_bytes = buf.getvalue()
        normalized_name = 'text/images/illust.png'
        fake_doc = core.EpubInputDocument(
            source_path=Path('dummy.epub'),
            book=None,
            docs=[_FakeEpubItem('text/chapter1.xhtml', '<html><body><img src="images/illust.png"/></body></html>')],
            image_map={normalized_name: image_bytes},
            image_basename_map={'illust.png': [(normalized_name, image_bytes)]},
            bold_rules={'classes': set(), 'ids': set(), 'tags': set()},
        )
        font_path = resolve_test_font_path()
        args = core.ConversionArgs(width=320, height=480, font_size=24, ruby_size=12, line_spacing=40, output_format='xtc', night_mode=True)
        observed_night_modes = []

        def fake_page_image_to_xt_bytes(image, width, height, page_args):
            observed_night_modes.append(page_args.night_mode)
            return b'page'

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / 'sample.xtc'
            with mock.patch.object(core, 'load_epub_input_document', return_value=fake_doc), \
                 mock.patch.object(core, 'page_image_to_xt_bytes', side_effect=fake_page_image_to_xt_bytes):
                result = core.process_epub('dummy.epub', font_path, args, output_path=out_path)
            self.assertEqual(result, out_path)

        self.assertTrue(observed_night_modes)
        self.assertFalse(observed_night_modes[0])


if __name__ == '__main__':
    unittest.main()
