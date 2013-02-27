#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import os
import sqlite3
import argparse # still not used
from datetime import datetime
import time

from utils import get_file_info

home = os.path.expanduser("~")
catho_path = home + "/.catho/"
catalogs = []

def touch_catho_dir():
    if not os.path.exists(catho_path):
        os.makedirs(catho_path)

def create_metadata(name):
    try:
        touch_catho_dir()
        conn = sqlite3.connect(catho_path + name + '.db')
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS METADATA;")
        c.execute("CREATE TABLE METADATA(key TEXT, value TEXT);")
        c.execute("INSERT INTO METADATA (key, value) VALUES('version', '1');")
        c.execute("INSERT INTO METADATA (key, value) VALUES('name', '" + name + "');")
        c.execute("INSERT INTO METADATA (key, value) VALUES('createdate', '" + str(int(time.time())) + "');")
        c.execute("INSERT INTO METADATA (key, value) VALUES('lastmodifdate', '" + str(int(time.time())) + "');")
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print("An error occurred:", e.args[0])

def create_catalog(name, files):
    try:
        touch_catho_dir()
        conn = sqlite3.connect(catho_path + name + '.db')
        conn.text_factory = str
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS CATALOG;")
        c.execute("CREATE TABLE CATALOG(id INT PRIMARY KEY ASC, name TEXT NOT NULL, date INT NOT NULL, size INT NOT NULL, path TEXT NOT NULL, hash TEXT);")
        c.executemany('INSERT INTO CATALOG (name, date, size, path) VALUES (?,?,?,?)', files)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print("An error occurred:", e.args[0])

def update_catalogs_list():
    touch_catho_dir()
    files = os.listdir(catho_path)

    for filename in files:
        filename.endswith('.db')
        size, date = get_file_info(catho_path, filename)
        catalogs.append((filename[:-3], size, date))

def load_catalogs():
    pass


def start():
    touch_catho_dir()
    update_catalogs_list()
    load_catalogs()

def create_db(name, files):
    create_metadata(name)
    create_catalog(name, files)

if __name__ == '__main__':
    start()
    # print(sys.argv)

    #if len(sys.argv) != 4:
    #    sys.exit(1)

    cmd = sys.argv[1]

    if (cmd == 'add'):
        name = sys.argv[2]
        path = sys.argv[3]
        # if not name:
        #     print(noname)
        # todo verify stat gives the same value in windows
        files = []    
        for dirname, dirnames, filenames in os.walk(path):
            for filename in filenames:
                try:
                    fullpath = os.path.join(dirname, filename)
                    path = os.path.join(dirname) # path of the file
                    size, date = get_file_info(dirname, filename)
                    files.append((filename, date, size, path))
                except OSError as oe:
                    print("An error occurred:", oe)
                except UnicodeDecodeError as ue:
                    print("An error occurred:", ue)

        # print(files)
        create_db(name, files)

    elif (cmd == 'ls'):
        for catalog, size, timestamp in catalogs:
            date = datetime.fromtimestamp(timestamp)
            print('{: >15} {: >15} {: >15}'.format(*(catalog, size, str(date))))