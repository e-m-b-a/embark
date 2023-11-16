import unittest

from embark.logviewer import LineCache


class TestLineCache(unittest.TestCase):

    def test_default(self):
        line_cache = LineCache('./test/logviewer/line_cache_test1.log')

        for _ in range(0, 2):
            self.assertEqual(12, line_cache.num_lines(), 'Incorrect number of lines.')
            self.assertEqual(len(line_cache.line_endings), len(line_cache.line_beginnings), 'The number of line beginnings and line endings do not match.')
            self.assertEqual([0, 7, 11, 23, 31, 41, 50, 54, 58, 72, 86, 104], line_cache.line_beginnings, 'The line beginning cache is not valid.')
            line_cache.refresh()

        self.assertEqual(b'10: ggggggggg\n11: hhhhhhhhhhhhh\n', line_cache.read_lines(0, 2), 'The line cache did not return the correct value.')
        self.assertEqual(b'9: ffffffffff\n10: ggggggggg\n11: hhhhhhhhhhhhh', line_cache.read_lines(1, 3), 'The line cache did not return the correct value.')

    def test_cr_lf(self):
        line_cache = LineCache('./test/logviewer/line_cache_test_cr_lf.log')

        for _ in range(0, 2):
            self.assertEqual(12, line_cache.num_lines(), 'Incorrect number of lines.')
            self.assertEqual(len(line_cache.line_endings), len(line_cache.line_beginnings), 'The number of line beginnings and line endings do not match.')
            self.assertEqual([0, 7, 10, 22, 30, 40, 49, 52, 55, 69, 83, 102], line_cache.line_beginnings, 'The line beginning cache is not valid.')
            line_cache.refresh()

        self.assertEqual(b'10: ggggggggg\n11: hhhhhhhhhhhhh\r\n', line_cache.read_lines(0, 2), 'The line cache did not return the correct value.')
        self.assertEqual(b'9: ffffffffff\n10: ggggggggg\n11: hhhhhhhhhhhhh', line_cache.read_lines(1, 3), 'The line cache did not return the correct value.')

    def test_no_newline_end(self):
        line_cache = LineCache('./test/logviewer/line_cache_test_no_newline.log')

        for _ in range(0, 2):
            self.assertEqual(11, line_cache.num_lines(), 'Incorrect number of lines.')
            self.assertEqual(len(line_cache.line_endings), len(line_cache.line_beginnings), 'The number of line beginnings and line endings do not match.')
            self.assertEqual([0, 7, 11, 23, 31, 41, 50, 54, 58, 72, 86], line_cache.line_beginnings, 'The line beginning cache is not valid.')
            line_cache.refresh()

        self.assertEqual(b'9: ffffffffff\n10: ggggggggg\n11: hhhhhhhhhhhhh', line_cache.read_lines(0, 2), 'The line cache did not return the correct value.')
        self.assertEqual(b'8: \n9: ffffffffff\n10: ggggggggg', line_cache.read_lines(1, 3), 'The line cache did not return the correct value.')

    def test_empty(self):
        line_cache = LineCache('./test/logviewer/line_cache_test_empty.log')

        for _ in range(0, 2):
            self.assertEqual(1, line_cache.num_lines(), 'Incorrect number of lines.')
            self.assertEqual(len(line_cache.line_endings), len(line_cache.line_beginnings), 'The number of line beginnings and line endings do not match.')
            self.assertEqual([0], line_cache.line_beginnings, 'The line beginning cache is not valid.')
            line_cache.refresh()

        self.assertEqual(b'', line_cache.read_lines(0, 0), 'The line cache did not return the correct value.')


if __name__ == '__main__':
    unittest.main()
