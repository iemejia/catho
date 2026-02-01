"""Database operations for catho."""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from typing import Any

from catho.file import FileItem, file_get_catalog_abspath
from catho.utils import list_of_tuples_to_dict

logger = logging.getLogger("catho")

# SQL statements
SQL_INSERT_METADATA = "INSERT INTO METADATA (key, value) VALUES (?,?)"
SQL_INSERT_CATALOG = (
    "INSERT INTO CATALOG (id, name, date, size, path, hash) VALUES (?,?,?,?,?,?)"
)
SQL_SELECT_METADATA = "SELECT * FROM METADATA;"
SQL_SELECT_CATALOG = "SELECT * FROM CATALOG;"
SQL_DELETE_CATALOG = "DELETE FROM catalog where id IN (%s);"
SQL_SELECT_CATALOG_COND = (
    "SELECT * FROM catalog WHERE NAME = ? AND PATH = ? AND size = ? AND date = ?;"
)
SQL_SELECT_CATALOG_BY_PATTERN = (
    "SELECT * FROM CATALOG WHERE name LIKE ? OR path LIKE ?;"
)
SQL_SELECT_CATALOG_BY_REGEX = "SELECT * FROM CATALOG WHERE REGEX(?, path || name);"
SQL_SELECT_CATALOG_BY_HASH = "SELECT * FROM CATALOG WHERE hash IN (?);"
SQL_SELECT_CATALOG_BY_ABSOLUTE_NAME = "SELECT * FROM CATALOG WHERE path || name = ?;"
SQL_SELECT_CATALOG_BY_PATH = "SELECT * FROM CATALOG WHERE path LIKE ?;"


def _db_regex(pattern: str, string: str) -> bool:
    """SQLite regex function.

    Args:
        pattern: Regex pattern.
        string: String to match.

    Returns:
        True if pattern matches string.
    """
    return bool(re.match(pattern, string))


def _db_create_schema(name: str) -> None:
    """Create the database schema.

    Args:
        name: Name of the catalog.
    """
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS METADATA;")
        c.execute("CREATE TABLE METADATA (key TEXT, value TEXT);")
        c.execute("DROP TABLE IF EXISTS CATALOG;")
        c.execute(
            "CREATE TABLE CATALOG (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "name TEXT NOT NULL, date INTEGER NOT NULL, "
            "size INTEGER NOT NULL, path TEXT NOT NULL, hash TEXT);"
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s", e)


def _db_executemany(name: str, query: str, items: list[Any]) -> None:
    """Execute a query with multiple parameters.

    Args:
        name: Name of the catalog.
        query: SQL query to execute.
        items: List of parameter tuples.
    """
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        logger.debug("SQL: Executing %s %s", query, items)
        c.executemany(query, items)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s", e)


def _db_get_all(
    name: str,
    query: str,
    params: tuple[Any, ...] = (),
) -> list[tuple[Any, ...]]:
    """Execute a query and return all results.

    Args:
        name: Name of the catalog.
        query: SQL query to execute.
        params: Query parameters.

    Returns:
        List of result rows.
    """
    rows: list[tuple[Any, ...]] = []
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        conn.create_function("REGEX", 2, _db_regex)
        c = conn.cursor()
        logger.debug("SQL: Executing %s %s", query, params)
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s", e)
    return rows


def _db_get_some(
    name: str,
    query: str,
    params_list: list[tuple[Any, ...]] | None = None,
) -> list[tuple[Any, ...]]:
    """Execute a query multiple times with different parameters.

    Args:
        name: Name of the catalog.
        query: SQL query to execute.
        params_list: List of parameter tuples.

    Returns:
        Combined list of all result rows.
    """
    if params_list is None:
        params_list = []

    rows: list[tuple[Any, ...]] = []
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        conn.create_function("REGEX", 2, _db_regex)
        c = conn.cursor()
        for param in params_list:
            logger.debug("SQL: Executing %s %s", query, param)
            c.execute(query, param)
            rows.extend(c.fetchall())
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s", e)
    return rows


def db_get_deleted_ids(name: str) -> list[int]:
    """Get IDs of items that no longer exist in the filesystem.

    Args:
        name: Name of the catalog.

    Returns:
        List of IDs for deleted files.
    """
    from catho.db import db_get_metadata

    m = db_get_metadata(name)
    deleted: list[int] = []
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        logger.debug("SQL: Executing %s", SQL_SELECT_CATALOG)
        for row_id, row_name, _date, _size, path, _hash in c.execute(
            SQL_SELECT_CATALOG
        ):
            filename = os.path.join(m["fullpath"], path, row_name)
            if not os.path.isfile(filename):
                deleted.append(row_id)
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s", e)
    return deleted


def db_insert_metadata(name: str, metadata: list[tuple[str, str]]) -> None:
    """Insert metadata into the catalog.

    Args:
        name: Name of the catalog.
        metadata: List of (key, value) tuples.
    """
    _db_executemany(name, SQL_INSERT_METADATA, metadata)


def db_insert_catalog(name: str, files: list[FileItem]) -> None:
    """Insert file items into the catalog.

    Args:
        name: Name of the catalog.
        files: List of file items to insert.
    """
    _db_executemany(name, SQL_INSERT_CATALOG, files)


def db_create(name: str) -> None:
    """Create a new catalog database.

    Args:
        name: Name of the catalog.
    """
    _db_create_schema(name)


def db_get_metadata(name: str) -> dict[str, str]:
    """Get catalog metadata.

    Args:
        name: Name of the catalog.

    Returns:
        Dictionary of metadata key-value pairs.
    """
    rows = _db_get_all(name, SQL_SELECT_METADATA)
    return list_of_tuples_to_dict([(str(k), str(v)) for k, v in rows])


def db_get_catalog(name: str) -> list[tuple[Any, ...]]:
    """Get all items in a catalog.

    Args:
        name: Name of the catalog.

    Returns:
        List of catalog items.
    """
    return _db_get_all(name, SQL_SELECT_CATALOG)


def get_catalog_by_pattern(name: str, pattern: str) -> list[tuple[Any, ...]]:
    """Search catalog by pattern.

    Args:
        name: Name of the catalog.
        pattern: SQL LIKE pattern to match.

    Returns:
        List of matching items.
    """
    return _db_get_all(name, SQL_SELECT_CATALOG_BY_PATTERN, (pattern, pattern))


def get_catalog_by_regex(name: str, regex: str) -> list[tuple[Any, ...]]:
    """Search catalog by regex.

    Args:
        name: Name of the catalog.
        regex: Regex pattern to match.

    Returns:
        List of matching items.
    """
    return _db_get_all(name, SQL_SELECT_CATALOG_BY_REGEX, (regex,))


def get_catalog_by_absolute_name(name: str, fullpath: str) -> list[tuple[Any, ...]]:
    """Search catalog by absolute file path.

    Args:
        name: Name of the catalog.
        fullpath: Full path to search for.

    Returns:
        List of matching items.
    """
    return _db_get_all(name, SQL_SELECT_CATALOG_BY_ABSOLUTE_NAME, (fullpath,))


def get_catalog_by_path(name: str, path: str) -> list[tuple[Any, ...]]:
    """Search catalog by path prefix.

    Args:
        name: Name of the catalog.
        path: Path prefix to search for.

    Returns:
        List of matching items.
    """
    return _db_get_all(name, SQL_SELECT_CATALOG_BY_PATH, (path + "%",))


def db_delete_catalog(name: str, ids: list[int]) -> None:
    """Delete items from the catalog by ID.

    Args:
        name: Name of the catalog.
        ids: List of IDs to delete.
    """
    query = SQL_DELETE_CATALOG % ",".join(map(str, ids))
    try:
        conn = sqlite3.connect(file_get_catalog_abspath(name))
        conn.text_factory = str
        c = conn.cursor()
        logger.debug("SQL: Executing %s", query)
        c.execute(query)
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("An error occurred: %s", e)


def db_get_inserted_catalogs(
    name: str,
    items: list[tuple[str, str, int, int]],
) -> list[tuple[Any, ...]]:
    """Get catalog items that match the given criteria.

    Args:
        name: Name of the catalog.
        items: List of (name, path, size, date) tuples to search for.

    Returns:
        List of matching catalog items.
    """
    return _db_get_some(name, SQL_SELECT_CATALOG_COND, items)


def get_catalog_by_hash(
    name: str,
    files: list[FileItem],
) -> list[tuple[Any, ...]]:
    """Search catalog by file hash.

    Args:
        name: Name of the catalog.
        files: List of file items (hash is taken from last element).

    Returns:
        List of matching items.
    """
    hashes = tuple(item[-1] for item in files if item[-1])
    if not hashes:
        return []
    return _db_get_all(name, SQL_SELECT_CATALOG_BY_HASH, hashes)
