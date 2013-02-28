#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import sqlite3
import argparse # still not used
from datetime import datetime
import time
import glob
import hashlib
import logging

from utils import get_file_info

home = os.path.expanduser("~")
catho_path = home + "/.catho/"
catho_extension = '.db'

logger = logging.getLogger('catho')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

def touch_catho_dir():
    if not os.path.exists(catho_path):
        os.makedirs(catho_path)

def get_catalog_abspath(name):
    return catho_path + name + catho_extension

def __create_metadata(name, metadata):
    """Insert metadata from the metadata dictionnary"""
    try:
        conn = sqlite3.connect(get_catalog_abspath(name))
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS METADATA;")
        c.execute("CREATE TABLE METADATA (key TEXT, value TEXT);")
        c.executemany('INSERT INTO METADATA (key, value) VALUES (?,?)', metadata)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e)

def create_metadata(name, path):
    date = str(int(time.time()))
    metadata = [('version', '1'), ('name', name), ('path', path), ('createdate', date), ('lastmodifdate', date)]
    return __create_metadata(name, metadata)

def create_catalog(name, files):
    try:
        conn = sqlite3.connect(get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS CATALOG;")
        c.execute("CREATE TABLE CATALOG (id INT PRIMARY KEY ASC, name TEXT NOT NULL, date INT NOT NULL, size INT NOT NULL, path TEXT NOT NULL, hash TEXT);")
        c.executemany('INSERT INTO CATALOG (name, date, size, path, hash) VALUES (?,?,?,?,?)', files)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e.args[0])

def get_catalogs():
    catalogs = []
    files = os.listdir(catho_path)
    for filename in files:
        if filename.endswith(catho_extension):
            size, date = get_file_info(catho_path, filename)
            catalogs.append((filename[:-3], size, date))
    return catalogs

def __get_all(name, query):
    """Generic query invocation in name db"""
    rows = []
    try:
        conn = sqlite3.connect(get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        c.execute(query)
        rows = c.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e)
    return rows

def get_metadata(name):
    """Returns a tuple (key, value) with the metadata"""
    query = "SELECT * FROM METADATA;"
    return __get_all(name, query)

def get_catalog(name):
    """Returns a tuple of the catalog, a row corresponds to a file"""
    query = "SELECT * FROM CATALOG;"
    return __get_all(name, query)

def metadata_str(name):
    meta = get_metadata(name)
    s = "METADATA\n"
    s += '\n'.join('%s: \t%s' % (key, value) for (key, value) in meta)
    return s + '\n'

def catalog_str(name):
    catalog = get_catalog(name)
    s = "CATALOG\n"
    s += '\n'.join('%s\t%s\t%s\t%s\t%s' % (name, str(datetime.fromtimestamp(date)), size, path, hash) for (id, name, date, size, path, hash) in catalog)
    return s + '\n'

def create_db(name, path, files):
    create_metadata(name, path)
    create_catalog(name, files)

def get_sha1(filename):
    sha1 = hashlib.sha1()
    f = open(filename, 'rb')
    try:
        sha1.update(f.read())
    finally:
        f.close()
    return sha1.hexdigest()

def get_filelist(orig_path, compute_hash = False):
    # todo verify if stat gives the same value in windows
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
                    # todo should we use the git convention for this ?
                    # sha1("blob " + filesize + "\0" + data)
                    hash = get_sha1(fullpath)
                    # logger.debug("SHA1 = %s" % hash)
                files.append((filename, date, size, path, hash))
            except OSError as oe:
                logger.error("An error occurred:", oe)
            except UnicodeDecodeError as ue:
                logger.error("An error occurred:", ue)
    return files

def catalogs_str():
    catalogs = get_catalogs()
    s = ''
    for catalog, size, timestamp in catalogs:
        date = str(datetime.fromtimestamp(timestamp))
        s += '{: >0} {: >15} {: >15}'.format(*(catalog, size, date))
    return s

def catalogs_info_str(names):
    s = ''
    for name in names:
        s += metadata_str(name)
        s += catalog_str(name)
    return s

def del_catalog_file(catalogs):
    """ deletes the list of cats """
    filelist = [ glob.glob(get_catalog_abspath(f)) for f in catalogs ]
    filelist = sum(filelist, [])
    for f in filelist:
        try:
            os.remove(f)
            logger.info("rm %s" % f)
        except OSError:
            logger.error("rm: %s: No such file or directory" % f)

if __name__ == '__main__':
    cmd = sys.argv[1]

    if (cmd == 'init'):
        touch_catho_dir()

    elif (cmd == 'add'):
        name = sys.argv[2]
        orig_path = sys.argv[3]
        extra_args = sys.argv[4:]
        # we check that the file exists or if it's forced and we create the cat
        if '-f' in extra_args or not os.path.exists(get_catalog_abspath(name)):
            logger.info("Creating catalog: %s" % name)
            compute_hash = '-H' in extra_args
            if compute_hash:
                logger.info("Computing hashes (this will take more time)...")
            create_db(name, os.path.abspath(orig_path), get_filelist(orig_path, compute_hash))
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
        del_catalog_file(cats)

    elif (cmd == 'find'):
        logger.error("TODO find")

    elif (cmd == 'scan'):
        logger.error("TODO scan")

    else:
        logger.error("Invalid command")
