#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catho.utils import *

class TestUtils(unittest.TestCase):
    def setUp(self):
        return
    def test_catalog_creation(self):
        # self.assertEqual(md5(sub[2]), '4cd9278a35ba2305f47354ee13472260')
        return

if __name__ == '__main__':
    unittest.main()
