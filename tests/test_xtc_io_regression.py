from __future__ import annotations

import struct
import unittest

import sys
import types

try:
    import tategakiXTC_gui_studio_xtc_io as xtc_io
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local GUI deps
    if exc.name not in {'PySide6', 'PySide6.QtGui'}:
        raise
    pyside_module = types.ModuleType('PySide6')
    qtgui_module = types.ModuleType('PySide6.QtGui')
    qtgui_module.QImage = object
    sys.modules.setdefault('PySide6', pyside_module)
    sys.modules.setdefault('PySide6.QtGui', qtgui_module)
    import tategakiXTC_gui_studio_xtc_io as xtc_io


def _xtg_blob(width: int, height: int, payload: bytes) -> bytes:
    header = bytearray(22)
    header[0:4] = b'XTG\x00'
    struct.pack_into('<H', header, 4, width)
    struct.pack_into('<H', header, 6, height)
    struct.pack_into('<I', header, 10, len(payload))
    return bytes(header) + payload


class XtcIoRegressionTests(unittest.TestCase):
    def test_parse_xtc_pages_prefers_16_byte_entries_when_data_offset_has_padding(self) -> None:
        idx_off = 48
        count = 2
        padded_data_off = idx_off + count * 24
        blob1 = _xtg_blob(10, 20, b'a')
        blob2 = _xtg_blob(11, 21, b'b')
        page1_off = padded_data_off
        page2_off = page1_off + len(blob1)

        header = bytearray(48)
        header[0:4] = b'XTC\x00'
        struct.pack_into('<H', header, 6, count)
        struct.pack_into('<Q', header, 24, idx_off)
        struct.pack_into('<Q', header, 32, padded_data_off)

        table = bytearray()
        table += struct.pack('<Q I H H', page1_off, len(blob1), 10, 20)
        table += struct.pack('<Q I H H', page2_off, len(blob2), 11, 21)
        padding = b'\x00' * (padded_data_off - idx_off - len(table))
        data = bytes(header) + bytes(table) + padding + blob1 + blob2

        pages = xtc_io.parse_xtc_pages(data)

        self.assertEqual(len(pages), 2)
        self.assertEqual((pages[0].offset, pages[0].length, pages[0].width, pages[0].height), (page1_off, len(blob1), 10, 20))
        self.assertEqual((pages[1].offset, pages[1].length, pages[1].width, pages[1].height), (page2_off, len(blob2), 11, 21))


if __name__ == '__main__':
    unittest.main()
