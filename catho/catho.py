#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from utils import get_file_info
import argparse
import glob
import hashlib
import logging
import os
import sqlite3
import sys
import time

home = os.path.expanduser("~")
catho_path = home + "/.catho/"
catho_extension = '.db'

logger = logging.getLogger('catho')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

sql_insert_metadata = 'INSERT INTO METADATA (key, value) VALUES (?,?)'
sql_insert_catalog = 'INSERT INTO CATALOG (name, date, size, path, hash) VALUES (?,?,?,?,?)'
sql_select_metadata = "SELECT * FROM METADATA;"
sql_select_catalog = "SELECT * FROM CATALOG;"

# file functions
def file_touch_catho_dir():
    if not os.path.exists(catho_path):
        os.makedirs(catho_path)

def file_get_catalog_abspath(name):
    return catho_path + name + catho_extension

def file_get_sha1(filename):
    # todo should we use the git convention for this ?
    # sha1("blob " + filesize + "\0" + data)
    sha1 = hashlib.sha1()
    f = open(filename, 'rb')
    try:
        sha1.update(f.read())
    finally:
        f.close()
    return sha1.hexdigest()

def file_get_catalogs():
    catalogs = []
    files = os.listdir(catho_path)
    for filename in files:
        if filename.endswith(catho_extension):
            size, date = get_file_info(catho_path, filename)
            catalogs.append((filename[:-3], size, date))
    return catalogs

def file_get_filelist(orig_path, compute_hash = False):
    # todo verify if stat gives the same value in windows
    if compute_hash:
        logger.info("Computing hashes (this will take more time)...")
    files = []    
    for dirname, dirnames, filenames in os.walk(orig_path):
        for filename in filenames:
            try:
                path = os.path.join(dirname) # path of the file
                fullpath = os.path.join(dirname, filename)
                # logger.debug("Processing %s" % fullpath)
                size, date = get_file_info(dirname, filename)
                hash = ''
                if compute_hash and not os.path.isdir(filename):
                    hash = file_get_sha1(fullpath)
                    # logger.debug("SHA1 = %s" % hash)
                files.append((filename, date, size, path, hash))
            except OSError as oe:
                logger.error("An error occurred: %s" % oe)
            except UnicodeDecodeError as ue:
                logger.error("An error occurred: %s" % ue)
    return files

def file_rm_catalog_file(catalogs):
    """ deletes the list of cats """
    filelist = [ glob.glob(file_get_catalog_abspath(f)) for f in catalogs ]
    filelist = sum(filelist, [])
    for f in filelist:
        try:
            os.remove(f)
            logger.info("rm %s" % f)
        except OSError:
            logger.error("rm: %s: No such file or directory" % f)

# db functions
def __db_create_schema(name):
    """Creates the db schema"""
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS METADATA;")
        c.execute("CREATE TABLE METADATA (key TEXT, value TEXT);")
        c.execute("DROP TABLE IF EXISTS CATALOG;")
        c.execute("CREATE TABLE CATALOG (id INT PRIMARY KEY ASC, name TEXT NOT NULL, date INT NOT NULL, size INT NOT NULL, path TEXT NOT NULL, hash TEXT);")
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e)

def __db_insert(name, query, l):
    """Generic insert invocation in name db"""
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        c.executemany(query, l)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e)


def __db_get_all(name, query):
    """Generic query invocation in name db"""
    rows = []
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e)
    return rows

def build_metadata(name, path, compute_hash = False):
    date = str(int(time.time()))
    metadata = [('version', '1'), ('name', name), ('path', path), ('createdate', date), ('lastmodifdate', date)]
    if compute_hash:
        metadata.append(('hash', 'sha-1'))
    return metadata

def __db_insert_metadata(name, metadata):
    return __db_insert(name, sql_insert_metadata, metadata)

def __db_insert_catalog(name, files):
    return __db_insert(name, sql_insert_catalog, files)

def db_create(name, path, files):
    __db_create_schema(name)
    __db_insert_metadata(name, path)
    __db_insert_catalog(name, files)

def db_get_metadata(name):
    return __db_get_all(name, sql_select_metadata)

def db_get_catalog(name):
    return __db_get_all(name, sql_select_catalog)

# to string functions
def metadata_str(name):
    meta = db_get_metadata(name)
    s = "METADATA\n"
    s += '\n'.join('%s: \t%s' % (key, value) for (key, value) in meta)
    return s + '\n'

def catalog_str(name):
    catalog = db_get_catalog(name)
    s = "CATALOG\n"
    s += '\n'.join('%s\t%s\t%s\t%s\t%s' % (name, str(datetime.fromtimestamp(date)), size, path, hash) for (id, name, date, size, path, hash) in catalog)
    return s + '\n'

def catalogs_str():
    catalogs = file_get_catalogs()
    s = ''
    for catalog, size, timestamp in catalogs:
        date = str(datetime.fromtimestamp(timestamp))
        s += '\n{: >0} {: >15} {: >15}'.format(*(catalog, size, date))
    return s

def catalogs_info_str(names):
    s = ''
    for name in names:
        s += metadata_str(name)
        s += catalog_str(name)
    return s

if __name__ == '__main__':
    cmd = sys.argv[1]

    if (cmd == 'init'):
        file_touch_catho_dir()

    elif (cmd == 'add'):
        name = sys.argv[2]
        orig_path = sys.argv[3]
        extra_args = sys.argv[4:]
        # we check that the file exists or if it's forced and we create the cat
        if '-f' in extra_args or not os.path.exists(file_get_catalog_abspath(name)):
            logger.info("Creating catalog: %s" % name)
            compute_hash = '-H' in extra_args
            metadata = build_metadata(name, os.path.abspath(orig_path), compute_hash)
            files = file_get_filelist(orig_path, compute_hash)
            db_create(name, metadata, files)
        else:
            logger.error("Catalog: %s already exists" % name)

    elif (cmd == 'ls'):
        names = sys.argv[2:]
        if not names:
            logger.info(catalogs_str())
        else:
            logger.info(catalogs_info_str(names))

    elif (cmd == 'rm'):
        cats = sys.argv[2:]
        file_rm_catalog_file(cats)

    elif (cmd == 'find'):
        exprs = sys.argv[2:]
        if exprs:
            logger.error("TODO find")

    elif (cmd == 'scan'):
        logger.error("TODO scan")

    else:
        logger.error("Invalid command")
