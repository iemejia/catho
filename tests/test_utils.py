#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

import sys
import unittest
import os

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

if __name__ == '__main__':
    unittest.main()
