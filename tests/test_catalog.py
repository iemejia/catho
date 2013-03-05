#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unittest

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
        
    def build_metadata(self):
        return catho.build_metadata(self.name, os.path.abspath(self.path))

    def test_build_metadata(self):
        self.metadata = self.build_metadata()
        self.assertTrue(self.metadata)
        self.assertEqual(len(self.metadata), 6)

    def test_db_get_metadata(self):
        catho.create_catalog(self.name, self.path)
        metadata = catho.db_get_metadata(self.name)
        self.assertTrue(metadata)
        self.assertTrue(len(metadata) == 6)

    def test_db_get_catalog(self):
        catho.create_catalog(self.name, self.path)
        catalog = catho.db_get_catalog(self.name)
        self.assertTrue(catalog)
        self.assertTrue(len(catalog) > 0)

    def test_file_get_catalogs(self):
        catalogs = catho.file_get_catalogs()
        self.assertTrue(catalogs)
        self.assertTrue(len(catalogs) > 0)

    def test_file_rm_catalog_file(self):
        catho.create_catalog(self.name, self.path, True)
        catho.file_rm_catalog_file([self.name])
        return

    def test_metadata_str(self):
        catho.create_catalog(self.name, self.path)
        str = catho.metadata_str(self.name)
        self.assertTrue(str)

    def test_catalog_str(self):
        catho.create_catalog(self.name, self.path)
        str = catho.catalog_str(self.name)
        self.assertTrue(str)

    def test_catalogs_str(self):
        str = catho.catalogs_str()
        self.assertTrue(str)

    def test_find_in_catalogs_all_catalogs_two_or_more_matches(self):
        catho.create_catalog(self.name, self.path)
        catho.create_catalog(self.name + '_copy', self.path)
        items = catho.find_in_catalogs('test_catalog.py')
        items = [f for catalog, files in items.iteritems() for f in files]
        self.assertTrue(len(items) > 1)

    def test_find_in_catalog_one_catalog_one_or_more_matches(self):
        catho.create_catalog(self.name, self.path)
        items = catho.find_in_catalogs('test_catalog.py', ('test',))
        items = [f for catalog, files in items.iteritems() for f in files]
        self.assertTrue(len(items) > 0)

    def test_find_in_catalogs_all_catalogs_not_matches(self):
        catho.create_catalog(self.name, self.path)
        catho.create_catalog(self.name + '_copy', self.path)
        items = catho.find_in_catalogs('not_existing_file.ext')
        items = [f for catalog, files in items.iteritems() for f in files]
        self.assertTrue(len(items) == 0)

    def test_find_in_catalog_one_catalog_not_matches(self):
        catho.create_catalog(self.name, self.path)
        items = catho.find_in_catalogs('not_existing_file.ext', ('test',))
        items = [f for catalog, files in items.iteritems() for f in files]
        self.assertTrue(len(items) == 0)

    def test_find_in_catalogs_selected_catalogs_not_matches(self):
        catho.create_catalog(self.name, self.path)
        catho.create_catalog(self.name + '_copy', self.path)
        items = catho.find_in_catalogs('not_existing_file.ext', (self.name, self.name + '_copy'))
        items = [f for catalog, files in items.iteritems() for f in files]
        self.assertTrue(len(items) == 0)

    def test_find_in_catalog_selected_catalog_not_matches(self):
        catho.create_catalog(self.name, self.path)
        catho.create_catalog(self.name + '_copy', self.path)
        items = catho.find_in_catalogs('not_existing_file.ext', (self.name, self.name + '_copy'))
        items = [f for catalog, files in items.iteritems() for f in files]
        self.assertTrue(len(items) == 0)      

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCatalog)
    unittest.TextTestRunner(verbosity=2).run(suite)
