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

# import logging.config
# logging.config.fileConfig('logging.conf')

# create logger
logger = logging.getLogger('catho')
logger.setLevel(logging.DEBUG)

# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)

def touch_catho_dir():
    if not os.path.exists(catho_path):
        os.makedirs(catho_path)

def create_metadata(name, path):
    try:
        touch_catho_dir()
        conn = sqlite3.connect(catho_path + name + catho_extension)
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS METADATA;")
        c.execute("CREATE TABLE METADATA(key TEXT, value TEXT);")
        c.execute("INSERT INTO METADATA (key, value) VALUES('version', '1');")
        c.execute("INSERT INTO METADATA (key, value) VALUES('name', '" + name + "');")
        c.execute("INSERT INTO METADATA (key, value) VALUES('path', '" + path + "');")
        c.execute("INSERT INTO METADATA (key, value) VALUES('createdate', '" + str(int(time.time())) + "');")
        c.execute("INSERT INTO METADATA (key, value) VALUES('lastmodifdate', '" + str(int(time.time())) + "');")
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred:", e.args[0])

def create_catalog(name, files):
    try:
        touch_catho_dir()
        conn = sqlite3.connect(catho_path + name + catho_extension)
        conn.text_factory = str
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS CATALOG;")
        c.execute("CREATE TABLE CATALOG(id INT PRIMARY KEY ASC, name TEXT NOT NULL, date INT NOT NULL, size INT NOT NULL, path TEXT NOT NULL, hash TEXT);")
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
                date = datetime.fromtimestamp(timestamp)
                logger.info('{: >0} {: >15} {: >15}'.format(*(catalog, size, str(date))))
        else:
            logger.debug("TODO: Print catalog info")
            # pass
            
    elif (cmd == 'rm'):
        catalogs = sys.argv[2:]
        filelist = [ glob.glob(catho_path + f + catho_extension) for f in catalogs ]
        filelist = sum(filelist, [])
        for f in filelist:
            try:
                os.remove(f)
                logger.info("rm", f)
            except OSError:
                logger.error("rm: %s: No such file or directory" % f)

    elif (cmd == 'find'):
        logger.error("TODO find")
