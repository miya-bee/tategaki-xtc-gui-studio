import unittest

import tategakiXTC_gui_core as core


class ApiSafetyRegressionTests(unittest.TestCase):
    def test_xtc_spooled_pages_add_blob_after_close_is_ignored(self):
        spool = core.XTCSpooledPages()
        try:
            spool.add_blob(b"abc")
            spool.close()
            spool.add_blob(b"def")
            self.assertEqual(spool.page_count, 1)
            self.assertEqual(spool.total_blob_bytes, 3)
        finally:
            spool.cleanup()

    def test_conversion_args_rejects_negative_margin(self):
        with self.assertRaises(ValueError):
            core.ConversionArgs(margin_l=-1)

    def test_conversion_args_normalizes_output_format(self):
        args = core.ConversionArgs(output_format='xtch')
        self.assertEqual(args.output_format, 'xtch')

    def test_supported_input_suffixes_is_membership_container(self):
        self.assertIn('.epub', core.SUPPORTED_INPUT_SUFFIXES)
        self.assertIn('.txt', core.SUPPORTED_INPUT_SUFFIXES)


if __name__ == '__main__':
    unittest.main()
