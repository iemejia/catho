#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime
from utils import *
from file import *
from db import *
import argparse
import logging
import os
import time

VALID_HASH_TYPES = ['sha1']

# number of files read and inserted in the database per iteration
MAX_FILES_ITER = 1024

# for the pieces used for hash calculation 1MB (2**20),
# bittorrent sub-hashes are usually less or equal to 512k 256k = 262144
BLOCK_SIZE = 1048576

logger = logging.getLogger('catho')
ch = logging.StreamHandler()
logger.addHandler(ch)
logger.setLevel(logging.INFO)


# file functions
def build_metadata(name, path, fullpath, hash_type='sha1'):

    date = str(int(time.time()))
    metadata = [('version', '1'), ('name', name), ('path', path),
                ('fullpath', fullpath), ('createdate', date),
                ('lastmodifdate', date)]
    if hash_type:
        metadata.append(('hash', hash_type))
    return metadata


# to string functions
def metadata_str(name):
    meta = db_get_metadata(name)
    s = "METADATA\n"
    s += '\n'.join('%s: \t%s' % (key, value) for (key, value) in meta.items())
    return s


def catalog_str(name):
    catalog = db_get_catalog(name)
    # print catalog
    return catalog_to_str(catalog)


def catalog_to_str(catalog):
    s = ''
    s += '\n'.join('%s | %s | %s | %s | %s' %
         (name, datetime.fromtimestamp(date).isoformat(), size, path, hash)
         for (id, name, date, size, path, hash) in catalog)
    return s + '\n'


def catalogs_str(catalogs):
    s = ''
    for catalog in catalogs:
        date = str(datetime.fromtimestamp(catalog['date']))
        s += '\n{: >0} {: >15} {: >15}'.format(*(catalog['name'],
             catalog['size'], date))
    return s


def catalogs_info_str(names):
    s = ''
    for name in names:
        s += metadata_str(name)
        s += catalog_str(name)
    return s


# Catho operations
def find_in_catalogs(pattern, catalogs=None):
    catalogs = file_select_catalogs(catalogs)
    patterns = pattern.split('%')
    patterns = map(lambda s: s.replace('*', '%'), patterns)
    pattern = '%' + '[%]'.join(patterns) + '%'

    if len(catalogs) == 0:
        logger.error('Catalog does not exist')

    items = {}
    for catalog in catalogs:
        matches = get_catalog_by_pattern(catalog, pattern)
        if matches:
            items[catalog] = matches

    return items


def find_regex_in_catalogs(regex, catalogs=None):
    catalogs = file_select_catalogs(catalogs)

    if len(catalogs) == 0:
        logger.error('Catalog does not exist')

    items = {}
    for catalog in catalogs:
        matches = get_catalog_by_regex(catalog, regex)
        if matches:
            items[catalog] = matches

    return items


def find_hash_in_catalogs(files, catalogs=None):
    catalogs = file_select_catalogs(catalogs)

    if len(catalogs) == 0:
        logger.error('Catalog does not exist')

    items = {}
    for catalog in catalogs:
        matches = get_catalog_by_hash(catalog, files)
        if matches:
            items[catalog] = matches

    return items


def item_equals(file1, file2):
    """ compares two file items, for their name, path, size, date """
    for i in range(1, 5):
        if file1[i] != file2[i]:
            return False
    return True


def get_non_inserted_files(files, inserted_files):
    non_inserted_files = []
    for file in files:
        exists_in_db = False
        for inserted_file in inserted_files:
            if item_equals(file, inserted_file):
                exists_in_db = True
        if not exists_in_db:
            non_inserted_files.append(file)
    return non_inserted_files


def __build_select_catalog_cond_params(files):
    l = []
    for id, name, date, size, path, hash in files:
        l.append((name, path, size, date))
    return l


def update_catalog(name, path):
    if os.path.exists(file_get_catalog_abspath(name)):
        # we check that it's the same catalog
        fullpath = os.path.abspath(path)
        m = db_get_metadata(name)
        if name == m['name'] and fullpath == m['fullpath']:
            # we find the files who exist in the catalog but that have
            # been deleted in the path, and we remove them from the
            # database
            deleted_ids = db_get_deleted_ids(name)
            if deleted_ids:
                logger.info("Updating removed files in the filesystem")
                db_delete_catalog(name, deleted_ids)

            filesubsets = path_block_iterator(fullpath, MAX_FILES_ITER)
            for files in filesubsets:
                l = __build_select_catalog_cond_params(files)
                inserted_files = db_get_inserted_catalogs(name, l)
                # we find the new or updated files in the path
                non_inserted_files = get_non_inserted_files(files,
                                                            inserted_files)
                if non_inserted_files:
                    logger.info('Updating missing files in the catalog')
                    hashed_files = calc_hashes(fullpath, non_inserted_files,
                                               BLOCK_SIZE)
                    db_insert_catalog(name, hashed_files)
        else:
            logger.warning('impossible to continue invalid name or path '
                           ' %s:%s' % (name, fullpath))
    else:
        logger.warning('catalog %s not found.' % name)


def create_catalog(name, path, force=False):
    if force or not os.path.exists(file_get_catalog_abspath(name)):
        logger.info("Creating catalog: %s" % name)

        # we create the header of the datafile
        fullpath = os.path.abspath(path)
        metadata = build_metadata(name, path, fullpath, hash_type='sha1')
        db_create(name)
        db_insert_metadata(name, metadata)

        # and then we add in subsets the catalog (to avoid overusing memory)
        filesubsets = path_block_iterator(fullpath, MAX_FILES_ITER)
        for files in filesubsets:
            hashed_files = calc_hashes(fullpath, files, BLOCK_SIZE)
            db_insert_catalog(name, hashed_files)
        return True
    else:
        logger.warning("Catalog: %s already exists" % name)
        return False


def scan_catalogs(name):
    m = {}
    if os.path.exists(name):
        # fullpath = os.path.abspath(name)
        if os.path.isdir(name):
            logger.info("scanning dir: %s" % name)
            # and then we add in subsets the catalog (to avoid using memory)
            # filesubsets = path_block_iterator(fullpath, MAX_FILES_ITER)
            # for files in filesubsets:
            #     hashed_files = calc_hashes(fullpath, files, BLOCK_SIZE)
            #     m = find_hash_in_catalogs(hashed_files)

                # for h in hashed_files:
                #     m[h[1]] = find_hash_in_catalogs([h])
                # print m
                # return m
        else:  # is file
            logger.info("scanning file: %s" % name)
            hashed_files = [file_getfile_as_item(name, BLOCK_SIZE)]
            m[name] = find_hash_in_catalogs(hashed_files)
    else:
        logger.error("impossible to scan, invalid path: %s" % name)
    return m

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Catho', prog='catho',
                                     epilog='"catho <command> -h" for more '
                                            'information on a specific '
                                            'command.')
    subparsers = parser.add_subparsers(help='commands', dest='command')

    # init command
    init_parser = subparsers.add_parser('init', help='inits catalog '
                                                     'repository')
    # help command
    help_parser = subparsers.add_parser('help', help='help for command')
    help_parser.add_argument('cmd', action='store', help='command')

    # ls command
    list_parser = subparsers.add_parser('ls', help='list available catalogs')
    list_parser.add_argument('names', action='store', nargs='*',
                             help='catalog name')

    # add command
    add_parser = subparsers.add_parser('add', help='adds catalog')
    add_parser.add_argument('name', action='store', help='catalog name')
    add_parser.add_argument('path', action='store', help='path to index')
    add_parser.add_argument('-f', '--force', help='force', action='store_true')
    add_parser.add_argument('-c', '--continue', help='continue',
                            action='store_true', dest='cont')

    # rm command
    rm_parser = subparsers.add_parser('rm', help='removes catalog')
    rm_parser.add_argument('names', action='store', nargs='*',
                           help='catalog name')

    # find command
    find_parser = subparsers.add_parser('find',
                                        help='find a filename in catalog')
    find_parser.add_argument('pattern', action='store',
                             help='a pattern to match')
    find_parser.add_argument('catalogs', action='append', nargs='*',
                             help='catalog name')

    # scan command
    scan_parser = subparsers.add_parser('scan',
                                        help='scan if the corresponding arg'
                                             'exists in the catalog')
    scan_parser.add_argument('name', action='store', help='file or path name')

    # general options
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-s', '--silent', action='store_true')
    parser.add_argument('-l', '--create-log', help='creates log file',
                        action='store')

    args = parser.parse_args()
    # logger.debug(args)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.silent:
        logger.removeHandler(ch)
        logger.addHandler(logging.NullHandler())

    if args.create_log:
        logger.info('logging to file %s' % args.create_log)
        # to check RotatingFileHandler
        fh = logging.FileHandler(args.create_log)
        logger.addHandler(fh)

    # we evaluate each command
    if args.command == 'init':
        file_touch_dir(catho_path)

    elif args.command == 'add':
        if not args.cont:
            create_catalog(args.name, args.path, args.force)
        else:
            update_catalog(args.name, args.path)

    elif args.command == 'ls':
        if not args.names:
            catalogs = file_get_catalogs()
            logger.info(catalogs_str(catalogs))
        else:
            logger.info(catalogs_info_str(args.names))

    elif args.command == 'rm':
        file_rm_catalog_file(args.names)

    elif args.command == 'find':
        if args.catalogs[0]:
            catalogs = args.catalogs[0]
        else:
            catalogs = [catalog['name'] for catalog in file_get_catalogs()]

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
        matches = scan_catalogs(args.name)
        # logger.info(matches)
        for name, m in matches.iteritems():
            logger.info(name + ' found in catalogs: %s' % m.keys())
