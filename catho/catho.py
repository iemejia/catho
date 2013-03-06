#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from utils import *
import argparse
import errno
import glob
import logging
import os
import sqlite3
import sys
import time
import re

VALID_HASH_TYPES = ['sha1']

MAX_FILES_ITER = 1024 # number of files read and inserted in the database per iteration
BLOCK_SIZE = 1048576 # for the pieces used for hash calculation 1MB (2**20), bittorrent sub-hashes are usually less or equal to 512k 256k = 262144

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
sql_delete_catalog = "DELETE FROM catalog where id IN "

# file functions
def file_touch_catho_dir():
    if not os.path.exists(catho_path):
        os.makedirs(catho_path)

def file_get_catalog_abspath(name):
    return catho_path + name + catho_extension

def file_get_catalogs():
    catalogs = []
    files = os.listdir(catho_path)
    ext_len = len(catho_extension)
    for filename in files:
        if filename.endswith(catho_extension):
            fullpath = os.path.join(catho_path, filename)
            size, date = get_file_info(fullpath)
            catalogs.append({ 'name' : filename[:-ext_len], 
                              'size' : size,
                              'date' : date })
    return catalogs

def file_select_catalogs(selection = []):
    catalogs = file_get_catalogs()
    if not selection:
        selected = [catalog['name'] for catalog in file_get_catalogs()]
    else:
        selected = [catalog['name'] for catalog in file_get_catalogs() if catalog['name'] in selection]

        if len(selection) != len(selected):
            discarded = [s for s in selection if s not in selected]
            logger.warning('Some catalogs ignored (%s)' % discarded)

    return selected

def path_block_iterator(fullpath, num_files):
    """ returns an iterator of a subcollection of files for the given size: """
    """ path in blocks of size num_files, it constructs a collection  """
    """ of fileitems """
    # links to directories are ignored to avoid recursion fo the instanct
    i = 0
    files = []
    for dirname, dirnames, filenames in os.walk(fullpath):
        # print(dirname, dirnames, filenames)
        for filename in filenames:
            i += 1
            # this is the complete file path for each directory
            path = os.path.join(dirname, filename)
            rel_path = path.replace(fullpath, '')
            rel_path = rel_path.replace(filename, '')
            try:
                size, date = get_file_info(path)
                hash = None
                files.append((filename, date, size, rel_path, hash))
                if i == num_files:
                    yield files
                    # we restart the accumulators
                    i = 0
                    files = []
            except OSError as oe:
                if oe.errno == errno.ENOENT:
                    realpath = os.path.realpath(path)
                    logger.error("Ignoring %s. No such target file or directory %s" % (path, realpath))
                else:
                    logger.error("An error occurred processing %s: %s" % (filename,oe))
            except UnicodeDecodeError as ue:
                logger.error("An error occurred processing %s: %s" % (filename, ue))
            except IOError as ioe:
                logger.error("An error occurred processing %s: %s" % (filename, ioe))

    yield files

def calc_hashes(fullpath, files, hash_type='sha1'):
    """ calc the hash value for each of the elements of the collection if """
    """ it has not been calculated """
    """ returns a list of tuples with the hash calculated """
    hashed_files = []
    for name, date, size, path, hash in files:
        if not hash:
            file_path = fullpath + path + name
            hash = file_hash(file_path, BLOCK_SIZE, hash_type)
            logger.debug("Calculating %s for %s | %s" % (hash_type, name, hash))
            hashed_files.append((name, date, size, path, hash))
    return hashed_files

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
        c.execute("CREATE TABLE CATALOG (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, date INTEGER NOT NULL, size INTEGER NOT NULL, path TEXT NOT NULL, hash TEXT);")
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s" % e)

def __db_executemany(name, query, l):
    """Generic insert invocation in name db"""
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        logger.debug('SQL: Executing %s %s' % (query ,l)) #
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
        conn.create_function("REGEX", 2, db_regex)
        c = conn.cursor()
        logger.debug('SQL: Executing %s %s' % (query, params))
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s" % e)
    return rows

def build_metadata(name, path, fullpath, hash_type = 'sha1'):
    date = str(int(time.time()))
    metadata = [('version', '1'), ('name', name), ('path', path), ('fullpath', fullpath), ('createdate', date), ('lastmodifdate', date)]
    if hash_type:
        metadata.append(('hash', hash_type))
    return metadata

def db_insert_metadata(name, metadata):
    return __db_executemany(name, sql_insert_metadata, metadata)

def db_insert_catalog(name, files):
    return __db_executemany(name, sql_insert_catalog, files)

def db_create(name):
    __db_create_schema(name)

def db_get_metadata(name):
    l = __db_get_all(name, sql_select_metadata)
    return list_of_tuples_to_dir(l)

def db_get_catalog(name):
    return __db_get_all(name, sql_select_catalog)

def db_regex(pattern, string):
    regex = re.match(pattern, string)
    if regex:
        return True
    return False

# to string functions
def metadata_str(name):
    meta = db_get_metadata(name)
    s = "METADATA\n"
    s += '\n'.join('%s: \t%s' % (key, value) for (key, value) in meta.items())
    return s

def catalog_str(name):
    catalog = db_get_catalog(name)
    # print catalog
    s = "CATALOG\n"
    return catalog_to_str(catalog)

def catalog_to_str(catalog):
    s = ''
    s += '\n'.join('%s | %s | %s | %s' % (name, datetime.fromtimestamp(date).isoformat(), size, path) for (id, name, date, size, path, hash) in catalog)
    return s + '\n'

def catalogs_str():
    catalogs = file_get_catalogs()
    s = ''
    for catalog in catalogs:
        date = str(datetime.fromtimestamp(catalog['date']))
        s += '\n{: >0} {: >15} {: >15}'.format(*(catalog['name'], catalog['size'], date))
    return s

def catalogs_info_str(names):
    s = ''
    for name in names:
        s += metadata_str(name)
        s += catalog_str(name)
    return s

# Catho operations

def find_in_catalogs(pattern, catalogs = None):
    catalogs = file_select_catalogs(catalogs)
    patterns = pattern.split('%')
    patterns = map(lambda s: s.replace('*', '%'), patterns)
    pattern = '%' + '[%]'.join(patterns) + '%'

    if len(catalogs) == 0:
        logger.error('Catalog does not exist')

    query = "SELECT * FROM CATALOG WHERE name LIKE ? or path LIKE ?;"

    items = {}
    for catalog in catalogs:
        matches = __db_get_all(catalog, query, (pattern, pattern))
        if matches:
            items[catalog] = matches

    return items


def find_plus_in_catalogs(regex, catalogs = None):
    catalogs = file_select_catalogs(catalogs) 

    if len(catalogs) == 0:
        logger.error('Catalog does not exist')

    query = "SELECT * FROM CATALOG WHERE REGEX(?, name);"

    items = [] 
    for catalog in catalogs:
        matches = __db_get_all(catalog, query, (regex,))
        items.extend(matches)

    return items

def db_build_select_string(files):
    s = []
    for name, date, size, path, hash in files:
        s.append("NAME = '%s' AND PATH = '%s' AND size = %s AND date = %s" % (name, path, size, date))
    return 'SELECT * FROM catalog WHERE ' + ' OR '.join(s)

def file_equals(file, db_file):
    """ an equals for the tuple """
    for i in range(4):
        # this is a tricky hack since the first element of db_tuples is the pk index
        # TOFIX
        if file[i] != db_file[i+1]:
            return False
    return True
    
def get_non_inserted_files(files, inserted_files):
    non_inserted_files = []
    for file in files:
        exists_in_db = False
        for inserted_file in inserted_files:
            if file_equals(file, inserted_file):
                exists_in_db = True
        if not exists_in_db:
            non_inserted_files.append(file)
    return non_inserted_files

def update_catalog(name, path):
    if os.path.exists(file_get_catalog_abspath(name)):
        # we check that it's the same catalog
        fullpath = os.path.abspath(path)
        metadata = db_get_metadata(name)
        m = list_of_tuples_to_dir(metadata)
        if name == m['name'] and fullpath == m['fullpath']:
            print 's'
            filesubsets = path_block_iterator(fullpath, MAX_FILES_ITER)
            for files in filesubsets:
                query = db_build_select_string(files)
                inserted_files =  __db_get_all(name, query)
                # we find the new or updated files in the path
                # we are probably missing another pass to remove the files who don't exist anymore from the db, probably in a different method
                non_inserted_files = get_non_inserted_files(files, inserted_files)
                logger.info('Updating missing files...')
                hashed_files = calc_hashes(fullpath, non_inserted_files)
                # db_insert_catalog(name, hashed_files)
        else:
            logger.warning('impossible to continue invalid name or path  %s:%s' % (name, fullpath))
    else:
        logger.warning('catalog %s not found.' % name)

def create_catalog(name, path, force = False):
    if force or not os.path.exists(file_get_catalog_abspath(name)):
        logger.info("Creating catalog: %s" % name)

        # we create the header of the datafile
        fullpath = os.path.abspath(path)
        metadata = build_metadata(name, path, fullpath, hash_type = 'sha1')
        db_create(name)
        db_insert_metadata(name, metadata)

        # and then we add in subsets the catalog (to avoid overusing memory)
        filesubsets = path_block_iterator(fullpath, MAX_FILES_ITER)
        for files in filesubsets:
            hashed_files = calc_hashes(fullpath, files)
            db_insert_catalog(name, hashed_files)
        return True
    else:
        logger.warning("Catalog: %s already exists" % name)
        return False


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
    add_parser.add_argument('-c', '--continue', help='continue', action='store_true', dest='cont')

    # rm command
    rm_parser = subparsers.add_parser('rm', help='removes catalog')
    rm_parser.add_argument('names', action='store', nargs='*', help='catalog name')

    # find command
    find_parser = subparsers.add_parser('find', help='find a filename in catalog')
    find_parser.add_argument('pattern', action='store', help='a pattern to match')
    find_parser.add_argument('catalogs', action='append', nargs='*', help='catalog name')

    # scan command
    scan_parser = subparsers.add_parser('scan', help='find a filename in catalog')
    scan_parser.add_argument('name', action='store', help='path name')

    # general options
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--silent', action='store_true')
    parser.add_argument('-l', '--create-log', help='creates log file', action='store')

    args = parser.parse_args()
    # logger.debug(args)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.silent:
        logger.removeHandler(ch)
        logger.addHandler(logging.NullHandler())

    if args.create_log:
        logger.info('logging to file %s' % args.create_log)
        fh = logging.FileHandler(args.create_log) # to check RotatingFileHandler
        logger.addHandler(fh)

    # we evaluate each command
    if args.command == 'init':
        file_touch_catho_dir()

    elif args.command == 'add':
        if not args.cont:
            create_catalog(args.name, args.path, args.force)
        else:
            update_catalog(args.name, args.path)

    elif args.command == 'ls':
        if not args.names:
            logger.info(catalogs_str())
        else:
            logger.info(catalogs_info_str(args.names))

    elif args.command == 'rm':
        file_rm_catalog_file(args.names)

    elif args.command == 'find':
        if args.catalogs[0]:
            catalogs = args.catalogs[0]
        else:
            catalogs =  [catalog['name'] for catalog in file_get_catalogs()]

        str_catalogs = ', '.join(catalogs)
        logger.info("Finding %s in (%s)" % (args.pattern, str_catalogs)) 

        matches = find_in_catalogs(args.pattern, catalogs)

        count = 0
        for catalog, items in matches.iteritems():
            count += len(items)
            logger.info(catalog + ':')
            logger.info(catalog_to_str(items))

        logger.info("%s items found" % count)

    elif args.command == 'scan':
        logger.error("TODO scan %s" % args.name)

