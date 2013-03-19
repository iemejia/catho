#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from catho import utils


class TestUtils(unittest.TestCase):

    def setUp(self):
        return

    def test_catalog_creation(self):
        path = os.path.dirname(utils.__file__)
        fullpath = os.path.join(path, 'utils.py')
        (size, date) = utils.get_file_info(fullpath)
        self.assertTrue(size)
        self.assertTrue(date)
        return

    def test_sizeof_fmt(self):
        s1 = utils.sizeof_fmt(123456789)
        s2 = utils.sizeof_fmt(123456789012)
        s3 = utils.sizeof_fmt(1234)
        self.assertEqual(s1, '117.7 MB')
        self.assertEqual(s2, '115.0 GB')
        self.assertEqual(s3, '1.2 KB')

    def test_file_hash(self):
        filename = 'LICENSE'
        block_size = 1048576
        h1 = utils.file_hash(filename, block_size, hash_type='sha1')
        self.assertEqual(h1, '2a4bdae6ceb4166ca3f66f937b12208f7b3064f6')

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestUtils)
    unittest.TextTestRunner(verbosity=2).run(suite)
