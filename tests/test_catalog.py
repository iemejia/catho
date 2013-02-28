#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import unittest
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from catho import catho

class TestCatalog(unittest.TestCase):
    def setUp(self):
        catho.file_touch_catho_dir()
        self.orig_path = '.'
        self.name = 'test'

    def test_file_get_filelist(self):
        filelist = catho.file_get_filelist(self.orig_path)
        self.assertTrue(filelist)
        self.assertTrue(len(filelist) > 0)

    def test_file_get_filelist_hash(self):
        filelist = catho.file_get_filelist(self.orig_path, compute_hash=True)
        self.assertTrue(filelist)
        self.assertTrue(len(filelist) > 0)
        
    def test_db_create(self):
        catho.db_create(self.name, catho.build_metadata(self.name, os.path.abspath(self.orig_path)), catho.file_get_filelist(self.orig_path))
        # self.assertEqual(md5(sub[2]), '4cd9278a35ba2305f47354ee13472260')

    def test_db_get_metadata(self):
        metadata = catho.db_get_metadata(self.name)
        self.assertTrue(metadata)
        self.assertTrue(len(metadata) == 5)
        # self.assertTrue(len(filelist) > 0)

    def test_db_get_catalog(self):
        catho.db_create(self.name, catho.build_metadata(self.name, os.path.abspath(self.orig_path)), catho.file_get_filelist(self.orig_path))
        catalog = catho.db_get_catalog(self.name)
        self.assertTrue(catalog)
        self.assertTrue(len(catalog) > 0)

    def test_file_get_catalogs(self):
        catho.db_create(self.name, catho.build_metadata(self.name, os.path.abspath(self.orig_path)), catho.file_get_filelist(self.orig_path))
        catalogs = catho.file_get_catalogs()
        self.assertTrue(catalogs)
        self.assertTrue(len(catalogs) > 0)

    def test_file_rm_catalog_file(self):
        catho.db_create(self.name, catho.build_metadata(self.name, os.path.abspath(self.orig_path)), catho.file_get_filelist(self.orig_path))
        catho.file_rm_catalog_file([self.name])
        return

    def test_metadata_str(self):
        catho.db_create(self.name, catho.build_metadata(self.name, os.path.abspath(self.orig_path)), catho.file_get_filelist(self.orig_path))
        str = catho.metadata_str(self.name)
        self.assertTrue(str)

    def test_catalog_str(self):
        catho.db_create(self.name, catho.build_metadata(self.name, os.path.abspath(self.orig_path)), catho.file_get_filelist(self.orig_path))
        str = catho.catalog_str(self.name)
        self.assertTrue(str)

    def test_catalogs_str(self):
        catho.db_create(self.name, catho.build_metadata(self.name, os.path.abspath(self.orig_path)), catho.file_get_filelist(self.orig_path))
        str = catho.catalogs_str()
        self.assertTrue(str)

if __name__ == '__main__':
    unittest.main()
