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
ch = logging.StreamHandler()
logger.addHandler(ch)
logger.setLevel(logging.INFO)

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
        logger.error("An error occurred: %s" % e)

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
        logger.error("An error occurred: %s" % e)


def __db_get_all(name, query, params = ()):
    """Generic query invocation in name db"""
    rows = []
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s" % e)
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

# Catho operations

def find_in_catalogs(regex, catalogs = None):
    if catalogs:
        catalogs = [catalog[0] for catalog in file_get_catalogs() if catalog[0] in catalogs]
    else:
        catalogs = [catalog[0] for catalog in file_get_catalogs()]    

    if len(catalogs) == 0:
        logger.error('Catalog does not exists')

    query = "SELECT * FROM CATALOG WHERE name = ?;"

    items = [] 
    for catalog in catalogs:
        matches = __db_get_all(catalog, query, (regex,))
        items.extend(matches)

    return items

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Catho', prog='catho', epilog='"catho <command> -h" for more information on a specific command.')
    subparsers = parser.add_subparsers(help='commands', dest='command' )

    # init command
    init_parser = subparsers.add_parser('init', help='inits catalog repository')

    # help command
    help_parser = subparsers.add_parser('help', help='help for command')
    help_parser.add_argument('cmd', action='store', help='command')

    # ls command
    list_parser = subparsers.add_parser('ls', help='list available catalogs')
    list_parser.add_argument('names', action='store', nargs='*', help='catalog name')

    # add command
    add_parser = subparsers.add_parser('add', help='adds catalog')
    add_parser.add_argument('name', action='store', help='catalog name')
    add_parser.add_argument('path', action='store', help='path to index')
    add_parser.add_argument('-f', '--force', help='force', action='store_true')
    add_parser.add_argument('-H', '--hash', help='add hash info in catalog creation', action='store_true')

    # rm command
    rm_parser = subparsers.add_parser('rm', help='removes catalog')
    rm_parser.add_argument('names', action='store', nargs='*', help='catalog name')

    # find command
    find_parser = subparsers.add_parser('find', help='find a filename in catalog')
    find_parser.add_argument('name', action='store', help='file name')
    find_parser.add_argument('catalog', action='store', nargs='?', help='file name')

    # scan command
    scan_parser = subparsers.add_parser('scan', help='find a filename in catalog')
    scan_parser.add_argument('name', action='store', help='path name')

    # general options
    parser.add_argument('-v', '--verbose', action='store_true')

    args = parser.parse_args()
    if (args.verbose):
        logger.setLevel(logging.DEBUG)
        logger.debug(args)

    # we evaluate each command
    if (args.command == 'init'):
        file_touch_catho_dir()

    elif (args.command == 'add'):
        # we check that the file exists or if it's forced and we create the cat
        if args.force or not os.path.exists(file_get_catalog_abspath(args.name)):
            logger.info("Creating catalog: %s" % args.name)
            metadata = build_metadata(args.name, os.path.abspath(args.path), args.hash)
            files = file_get_filelist(args.path, args.hash)
            db_create(args.name, metadata, files)
        else:
            logger.error("Catalog: %s already exists" % args.name)

    elif (args.command == 'ls'):
        if not args.names:
            logger.info(catalogs_str())
        else:
            logger.info(catalogs_info_str(args.names))

    elif (args.command == 'rm'):
        file_rm_catalog_file(args.names)

    elif (args.command == 'find'):
        #catalogs = []
        if args.catalog:
            catalogs = (args.catalog,)
        else:
            catalogs =  [catalog[0] for catalog in file_get_catalogs()]

        str_catalogs = ', '.join(catalogs)
        logger.info("Finding %s in (%s)" % (args.name, str_catalogs)) 

        items = find_in_catalogs(args.name, catalogs)
        for item in items:
            logger.info('%s', item)

        logger.info("%s items found" % len(items))

    elif (args.command == 'scan'):
        logger.error("TODO scan %s" % args.name)

