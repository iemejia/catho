from file import *
from db import *
from utils import *

import logging
import re
import sqlite3

logger = logging.getLogger('catho')
# ch = logging.StreamHandler()
# logger.addHandler(ch)
# logger.setLevel(logging.INFO)

sql_insert_metadata = 'INSERT INTO METADATA (key, value) VALUES (?,?)'
sql_insert_catalog = 'INSERT INTO CATALOG ' \
                     '(id, name, date, size, path, hash) ' \
                     'VALUES (?,?,?,?,?,?)'
sql_select_metadata = "SELECT * FROM METADATA;"
sql_select_catalog = "SELECT * FROM CATALOG;"
sql_delete_catalog = "DELETE FROM catalog where id IN (%s);"
sql_select_catalog_cond = 'SELECT * FROM catalog WHERE NAME = ? AND ' \
                          'PATH = ? AND size = ? AND date = ?;'
sql_select_catalog_by_pattern = "SELECT * FROM CATALOG " \
                                "WHERE name LIKE ? OR path LIKE ?;"
sql_select_catalog_by_regex = "SELECT * FROM CATALOG " \
                              "WHERE REGEX(?, path || name);"
sql_select_catalog_by_hash = "SELECT * FROM CATALOG WHERE hash IN (?);"
sql_select_catalog_by_absolute_name = "SELECT * FROM CATALOG " \
                                      "WHERE path || name = ?;"
sql_select_catalog_by_path = "SELECT * FROM CATALOG WHERE path LIKE ?;"


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
        c.execute('CREATE TABLE CATALOG (id INTEGER PRIMARY KEY AUTOINCREMENT,'
                  'name TEXT NOT NULL, date INTEGER NOT NULL, '
                  'size INTEGER NOT NULL, path TEXT NOT NULL, hash TEXT);')
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
        logger.debug('SQL: Executing %s %s' % (query, l))
        c.executemany(query, l)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s" % e)


def __db_get_all(name, query, params=()):
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


def __db_get_some(name, query, params=[]):
    """Generic query invocation in name db"""
    # TOFIX this method is too hacky, we have to fix this
    rows = []
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        conn.create_function("REGEX", 2, db_regex)
        c = conn.cursor()
        for param in params:
            logger.debug('SQL: Executing %s %s' % (query, param))
            c.execute(query, param)
            rs = c.fetchall()
            for r in rs:
                rows.append(r)
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s" % e)
    return rows


def db_get_deleted_ids(name):
    """Return a list of ids of the items that exist in the database but """
    """don't exist anymore in the filesystem"""
    m = db_get_metadata(name)
    deleted = []
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        logger.debug('SQL: Executing %s' % sql_select_catalog)
        for id, name, date, size, path, hash in c.execute(sql_select_catalog):
            filename = os.path.join(m['fullpath'], path, name)
            if not os.path.isfile(filename):
                deleted.append(id)
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s" % e)
    return deleted


def db_insert_metadata(name, metadata):
    return __db_executemany(name, sql_insert_metadata, metadata)


def db_insert_catalog(name, files):
    return __db_executemany(name, sql_insert_catalog, files)


def db_create(name):
    __db_create_schema(name)


def db_get_metadata(name):
    l = __db_get_all(name, sql_select_metadata)
    return list_of_tuples_to_dict(l)


def db_get_catalog(name):
    return __db_get_all(name, sql_select_catalog)


def get_catalog_by_pattern(name, pattern):
    return __db_get_all(name, sql_select_catalog_by_pattern,
                        (pattern, pattern))


def get_catalog_by_regex(name, regex):
    return __db_get_all(name, sql_select_catalog_by_regex, (regex,))


def get_catalog_by_absolute_name(name, fullpath):
    return __db_get_all(name, sql_select_catalog_by_absolute_name, (fullpath,))


def get_catalog_by_path(name, path):
    return __db_get_all(name, sql_select_catalog_by_path, (path + '%',))


def db_regex(pattern, string):
    regex = re.match(pattern, string)
    if regex:
        return True
    return False


def db_delete_catalog(name, l):
    """ deletes the rows the list of ids l from the catalog"""
    query = sql_delete_catalog % ",".join(map(str, l))
    """Creates the db schema"""
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        logger.debug('SQL: Executing %s' % query)
        c.execute(query)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s" % e)


def db_get_inserted_catalogs(name, l):
    """ arg is a 4-tuple of (name, path, size, date) """
    return __db_get_some(name, sql_select_catalog_cond, l)


def get_catalog_by_hash(name, l):
    """ arg is a list of items, we asume hash is the last element """
    # hashes = ', '.join("'%s'" % i[-1] for i in l)
    # print hashes
    hashes = tuple([i[-1] for i in l])
    return __db_get_all(name, sql_select_catalog_by_hash, hashes)
