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
catalogs = []

logger = logging.getLogger('catho')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

def touch_catho_dir():
    if not os.path.exists(catho_path):
        os.makedirs(catho_path)

def __create_metadata(name, metadata):
    """Insert metadata from the metadata dictionnary"""
    try:
        touch_catho_dir()
        conn = sqlite3.connect(catho_path + name + catho_extension)
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
        touch_catho_dir()
        conn = sqlite3.connect(catho_path + name + catho_extension)
        conn.text_factory = str
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS CATALOG;")
        c.execute("CREATE TABLE CATALOG (id INT PRIMARY KEY ASC, name TEXT NOT NULL, date INT NOT NULL, size INT NOT NULL, path TEXT NOT NULL, hash TEXT);")
        c.executemany('INSERT INTO CATALOG (name, date, size, path) VALUES (?,?,?,?)', files)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e.args[0])

def update_catalogs_list():
    touch_catho_dir()
    files = os.listdir(catho_path)

    for filename in files:
        filename.endswith(catho_extension)
        size, date = get_file_info(catho_path, filename)
        catalogs.append((filename[:-3], size, date))

def load_catalogs():
    pass

def __get_all(name, query):
    """Generic query invocation in name db"""
    rows = []
    try:
        touch_catho_dir()
        conn = sqlite3.connect(catho_path + name + catho_extension)
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

def print_metadata(meta):
    logger.info("METADATA")
    logger.info('\n'.join('%s: \t%s' % (key, value) for (key, value) in meta))

def print_catalog(catalog):
    logger.info("CATALOG")
    logger.info('\n'.join('%s\t%s\t%s\t%s' % (name, str(datetime.fromtimestamp(date)), size, path) for (id, name, date, size, path, hash) in catalog))

def start():
    touch_catho_dir()
    update_catalogs_list()
    load_catalogs()

def create_db(name, path, files):
    create_metadata(name, path)
    create_catalog(name, files)

if __name__ == '__main__':
    start()
    # logger.debug(sys.argv)

    #if len(sys.argv) != 4:
    #    sys.exit(1)

    cmd = sys.argv[1]

    if (cmd == 'init'):
        touch_catho_dir()

    elif (cmd == 'add'):
        name = sys.argv[2]
        orig_path = sys.argv[3]

        # if not name:
        #     logger.debug(noname)
        # todo verify stat gives the same value in windows
        files = []    
        for dirname, dirnames, filenames in os.walk(orig_path):
            for filename in filenames:
                try:
                    fullpath = os.path.join(dirname, filename)
                    path = os.path.join(dirname) # path of the file
                    size, date = get_file_info(dirname, filename)
                    files.append((filename, date, size, path))
                except OSError as oe:
                    logger.error("An error occurred:", oe)
                except UnicodeDecodeError as ue:
                    logger.error("An error occurred:", ue)

        # logger.debug(files)
        create_db(name, os.path.abspath(orig_path), files)

    elif (cmd == 'ls'):
        cats = sys.argv[2:]
        if not cats:
            for catalog, size, timestamp in catalogs:
                date = str(datetime.fromtimestamp(timestamp))
                logger.info('{: >0} {: >15} {: >15}'.format(*(catalog, size, date)))
        else:
            for cat in cats:
                meta = get_metadata(cat)
                print_metadata(meta)
                catalog = get_catalog(cat)
                print_catalog(catalog)
        del cats
            
    elif (cmd == 'rm'):
        cats = sys.argv[2:]
        filelist = [ glob.glob(catho_path + f + catho_extension) for f in cats ]
        filelist = sum(filelist, [])
        for f in filelist:
            try:
                os.remove(f)
                logger.info("rm %s" % f)
            except OSError:
                logger.error("rm: %s: No such file or directory" % f)
        del cats

    elif (cmd == 'find'):
        logger.error("TODO find")

    elif (cmd == 'scan'):
        logger.error("TODO scan")
