"""
P1-2 回帰テスト: 画像アーカイブ全件失敗時の代表原因表示
"""

import io
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tategakiXTC_gui_core as core


def _make_zip_with(tmpdir: Path, entries: dict) -> Path:
    """entries = {filename: bytes} で ZIP を作る"""
    archive_path = tmpdir / "test.zip"
    with zipfile.ZipFile(archive_path, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return archive_path


class ArchiveErrorMessageTests(unittest.TestCase):
    """全件変換失敗時のエラーメッセージに代表原因が含まれることを確認する。"""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmpdir.name)
        self.args = core.ConversionArgs(width=8, height=8, output_format="xtc")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_broken_png_reports_representative_error(self):
        """壊れた PNG のみの ZIP では、代表エラーを含むメッセージが出ること。

        process_image_data は変換失敗時に None を返す（例外は内部で握り潰す）。
        process_archive はその None を検知して fail_count に計上し、
        全件失敗時に代表エラーを含むメッセージを出す。
        """
        archive_path = _make_zip_with(self.tmpdir, {
            "001.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 20,  # 壊れた PNG
            "002.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 20,
        })
        with self.assertRaises(RuntimeError) as ctx:
            core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        # 全件失敗時のいずれかのメッセージが出ること
        self.assertTrue(
            "正常に変換できませんでした" in msg or "変換できる画像が見つかりませんでした" in msg,
            f"失敗を示すメッセージが含まれない: {msg!r}"
        )
        if "正常に変換できませんでした" in msg:
            self.assertIn("代表エラー", msg, "代表エラーの記述が含まれること")
            self.assertIn("変換失敗: 2 件", msg)

    def test_non_image_files_only_zip(self):
        """非画像ファイルのみの ZIP では、適切なエラーが出ること。"""
        archive_path = _make_zip_with(self.tmpdir, {
            "readme.txt": b"hello",
            "data.json": b"{}",
        })
        with self.assertRaises(RuntimeError) as ctx:
            core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        # 画像が0枚の場合は従来メッセージ、失敗ありなら代表エラー、どちらかが出ること
        self.assertTrue(
            "変換できる画像が見つかりませんでした" in msg or "変換に失敗しました" in msg,
            f"期待するメッセージが含まれない: {msg!r}"
        )

    def test_mixed_zip_partial_success(self):
        """正常な PNG が 1 枚でもあれば例外にならず、出力ファイルが生成されること。"""
        from PIL import Image
        buf = io.BytesIO()
        Image.new("L", (8, 8), 128).save(buf, format="PNG")
        valid_png = buf.getvalue()

        broken_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

        archive_path = _make_zip_with(self.tmpdir, {
            "001.png": broken_png,
            "002.png": valid_png,   # これだけ成功
        })
        out_path = core.process_archive(archive_path, self.args)
        self.assertTrue(out_path.exists(), "一部成功で出力ファイルが生成されること")
        self.assertEqual(out_path.read_bytes()[:4], b"XTC\x00", "XTC ヘッダが正しいこと")

    def test_traversal_skip_is_reported_with_dedicated_message(self):
        archive_path = self.tmpdir / "traversal.zip"
        archive_path.write_bytes(b'dummy')
        fake_doc = core.ArchiveInputDocument(
            source_path=archive_path,
            image_files=[Path('/tmp/outside.png')],
        )
        with unittest.mock.patch.object(core, 'load_archive_input_document', return_value=fake_doc):
            with self.assertRaises(RuntimeError) as ctx:
                core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: 安全のためアーカイブ内画像を処理しませんでした。', msg)
        self.assertIn('安全のためスキップしたパス: 1 件', msg)
        self.assertNotIn('変換失敗: 0 件', msg)


    def test_traversal_only_zip_members_are_reported_with_dedicated_message(self):
        from PIL import Image
        buf = io.BytesIO()
        Image.new('L', (8, 8), 255).save(buf, format='PNG')
        archive_path = _make_zip_with(self.tmpdir, {
            '../escape.png': buf.getvalue(),
            '/abs.png': buf.getvalue(),
        })
        with self.assertRaises(RuntimeError) as ctx:
            core.process_archive(archive_path, self.args)
        msg = str(ctx.exception)
        self.assertIn('内容: 安全のためアーカイブ内画像を処理しませんでした。', msg)
        self.assertIn('安全のためスキップしたパス: 2 件', msg)


if __name__ == "__main__":
    unittest.main()
