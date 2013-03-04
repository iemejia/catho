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
        self.path = '.'
        self.name = 'test'
        self.hash_type = 'sha1'
        self.metadata = []
        self.catalog = []

    def test_file_get_filelist(self):
        filelist = catho.file_get_filelist(self.path)
        self.assertTrue(filelist)
        
    def test_db_create(self):
        catho.db_create(self.name)

    def build_metadata(self):
        return catho.build_metadata(self.name, os.path.abspath(self.path))

    def test_build_metadata(self):
        self.metadata = self.build_metadata()
        self.assertTrue(self.metadata)
        self.assertEqual(len(self.metadata), 6)

    def full_db_create(self, name = ''):
        if (name == ''):
            catho.db_create(self.name)
        else:
            catho.db_create(name)
        catho.db_insert_metadata(self.name, self.build_metadata())
        # catalog = []
        filesubsets = catho.file_get_filelist(self.path)
        for files in filesubsets:
            # catalog.append(files)
            catho.db_insert_catalog(self.name, files)
        # self.assertEqual(md5(sub[2]), '4cd9278a35ba2305f47354ee13472260')

    # def full_db_create(self, name, metadata, catalog):
    #     self.name = name
    #     self.metadata = metadata
    #     self.catalog = catalog
    #     self.full_db_create(self)

    def test_db_get_metadata(self):
        self.full_db_create()
        metadata = catho.db_get_metadata(self.name)
        print metadata
        self.assertTrue(metadata)
        self.assertTrue(len(metadata) == 6)

    def test_db_get_catalog(self):
        self.full_db_create()
        catalog = catho.db_get_catalog(self.name)
        self.assertTrue(catalog)
        self.assertTrue(len(catalog) > 0)

    def test_file_get_catalogs(self):
        self.full_db_create()
        catalogs = catho.file_get_catalogs()
        self.assertTrue(catalogs)
        self.assertTrue(len(catalogs) > 0)

    def test_file_rm_catalog_file(self):
        self.full_db_create()
        catho.file_rm_catalog_file([self.name])
        return

    def test_metadata_str(self):
        self.full_db_create()
        str = catho.metadata_str(self.name)
        self.assertTrue(str)

    def test_catalog_str(self):
        self.full_db_create()
        str = catho.catalog_str(self.name)
        self.assertTrue(str)

    def test_catalogs_str(self):
        self.full_db_create()
        str = catho.catalogs_str()
        self.assertTrue(str)

    def test_find_in_catalogs_all_catalogs_two_or_more_matches(self):
        self.full_db_create()
        self.full_db_create(self.name + '_copy')
        items = catho.find_in_catalogs('test_catalog.py')
        self.assertTrue(len(items) > 1)

    def test_find_in_catalog_one_catalog_one_or_more_matches(self):
        self.full_db_create()
        items = catho.find_in_catalogs('test_catalog.py', ('test',))
        self.assertTrue(len(items) > 0)

    def test_find_in_catalogs_all_catalogs_not_matches(self):
        self.full_db_create()
        self.full_db_create(self.name + '_copy')
        items = catho.find_in_catalogs('not_existing_file.ext')
        self.assertTrue(len(items) == 0)

    def test_find_in_catalog_one_catalog_not_matches(self):
        self.full_db_create()
        items = catho.find_in_catalogs('not_existing_file.ext', ('test',))
        self.assertTrue(len(items) == 0)

if __name__ == '__main__':
    unittest.main()
