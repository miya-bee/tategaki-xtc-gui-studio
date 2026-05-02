from __future__ import annotations

import io
import unittest

import tategakiXTC_gui_core as core


class _CancelAfterFirstRead(io.BytesIO):
    def __init__(self, data: bytes, cancel_state: dict[str, bool]) -> None:
        super().__init__(data)
        self._cancel_state = cancel_state
        self._read_count = 0

    def read(self, size: int = -1) -> bytes:  # type: ignore[override]
        chunk = super().read(size)
        if chunk:
            self._read_count += 1
            if self._read_count == 1:
                self._cancel_state['value'] = True
        return chunk


class SpooledCopyCancelRegressionTests(unittest.TestCase):
    def test_copy_fileobj_with_cancel_stops_mid_copy_without_progress_callback(self) -> None:
        cancel_state = {'value': False}
        src = _CancelAfterFirstRead(b'A' * 12, cancel_state)
        dst = io.BytesIO()

        with self.assertRaises(core.ConversionCancelled):
            core._copy_fileobj_with_cancel(
                src,
                dst,
                should_cancel=lambda: cancel_state['value'],
                chunk_size=4,
            )

        self.assertEqual(dst.getvalue(), b'A' * 4)


if __name__ == '__main__':
    unittest.main()
