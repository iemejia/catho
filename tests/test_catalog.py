#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catho import catho

class TestCatalog(unittest.TestCase):
    def setUp(self):
        catho.touch_catho_dir()
        self.orig_path = '.'
        self.name = 'test'

    def test_get_filelist(self):
        filelist = catho.get_filelist(self.orig_path)
        self.assertTrue(filelist)
        self.assertTrue(len(filelist) > 0)

    def test_get_filelist_hash(self):
        filelist = catho.get_filelist(self.orig_path, compute_hash=True)
        self.assertTrue(filelist)
        self.assertTrue(len(filelist) > 0)
        
    def test_create_db(self):
        catho.create_db(self.name, os.path.abspath(self.orig_path), catho.get_filelist(self.orig_path))
        # self.assertEqual(md5(sub[2]), '4cd9278a35ba2305f47354ee13472260')

    def test_get_metadata(self):
        metadata = catho.get_metadata(self.name)
        self.assertTrue(metadata)
        self.assertTrue(len(metadata) == 5)
        # self.assertTrue(len(filelist) > 0)

    def test_get_catalog(self):
        catho.create_db(self.name, os.path.abspath(self.orig_path), catho.get_filelist(self.orig_path))
        catalog = catho.get_catalog(self.name)
        self.assertTrue(catalog)
        self.assertTrue(len(catalog) > 0)

    def test_get_catalogs(self):
        catho.create_db(self.name, os.path.abspath(self.orig_path), catho.get_filelist(self.orig_path))
        catalogs = catho.get_catalogs()
        self.assertTrue(catalogs)
        self.assertTrue(len(catalogs) > 0)

    def test_del_catalog_file(self):
        catho.create_db(self.name, os.path.abspath(self.orig_path), catho.get_filelist(self.orig_path))
        catho.del_catalog_file([self.name])
        return

    def test_metadata_str(self):
        # catho.create_db(self.name, os.path.abspath(self.orig_path), catho.get_filelist(self.orig_path))
        str = catho.metadata_str(self.name)
        self.assertTrue(str)

    def test_catalog_str(self):
        str = catho.catalog_str(self.name)
        self.assertTrue(str)

    def test_catalogs_str(self):
        str = catho.catalogs_str()
        self.assertTrue(str)

if __name__ == '__main__':
    unittest.main()
