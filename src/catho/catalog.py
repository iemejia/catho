"""Catalog operations for catho."""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

from catho.db import (
    db_create,
    db_delete_catalog,
    db_get_catalog,
    db_get_deleted_ids,
    db_get_inserted_catalogs,
    db_get_metadata,
    db_insert_catalog,
    db_insert_metadata,
    get_catalog_by_hash,
    get_catalog_by_pattern,
    get_catalog_by_regex,
)
from catho.file import (
    FileItem,
    HashType,
    calc_hashes,
    file_get_catalog_abspath,
    file_getfile_as_item,
    file_select_catalogs,
    path_block_iterator,
)

logger = logging.getLogger("catho")

# Valid hash types
VALID_HASH_TYPES = ["sha1", "None"]

# Number of files read and inserted in the database per iteration
MAX_FILES_ITER = 1024

# Block size for hash calculation (1MB = 2**20)
BLOCK_SIZE = 1048576


def build_metadata(
    name: str,
    path: str,
    fullpath: str,
    hash_type: HashType,
) -> list[tuple[str, str]]:
    """Build metadata for a catalog.

    Args:
        name: Catalog name.
        path: Original path.
        fullpath: Full absolute path.
        hash_type: Hash algorithm used.

    Returns:
        List of metadata key-value tuples.
    """
    date = str(int(time.time()))
    return [
        ("version", "1"),
        ("name", name),
        ("path", path),
        ("fullpath", fullpath),
        ("createdate", date),
        ("lastmodifdate", date),
        ("hash", hash_type),
    ]


def metadata_str(name: str) -> str:
    """Get metadata as a string.

    Args:
        name: Catalog name.

    Returns:
        Formatted metadata string.
    """
    meta = db_get_metadata(name)
    lines = ["METADATA"]
    lines.extend(f"{key}: \t{value}" for key, value in meta.items())
    return "\n".join(lines)


def catalog_str(name: str) -> str:
    """Get catalog contents as a string.

    Args:
        name: Catalog name.

    Returns:
        Formatted catalog string.
    """
    catalog = db_get_catalog(name)
    return catalog_to_str(catalog)


def catalog_to_str(catalog: list[tuple[Any, ...]]) -> str:
    """Format catalog items as a string.

    Args:
        catalog: List of catalog items.

    Returns:
        Formatted string.
    """
    lines = []
    for _item_id, name, date, size, path, hash_value in catalog:
        date_str = datetime.fromtimestamp(date).isoformat()
        lines.append(f"{name} | {date_str} | {size} | {path} | {hash_value}")
    return "\n".join(lines) + "\n"


def catalogs_str(catalogs: list[dict[str, Any]]) -> str:
    """Format list of catalogs as a string.

    Args:
        catalogs: List of catalog info dictionaries.

    Returns:
        Formatted string.
    """
    lines = []
    for catalog in catalogs:
        date = str(datetime.fromtimestamp(int(catalog["date"])))
        lines.append(f"\n{catalog['name']: >0} {catalog['size']: >15} {date: >15}")
    return "".join(lines)


def catalogs_info_str(names: list[str]) -> str:
    """Get detailed info for catalogs as a string.

    Args:
        names: List of catalog names.

    Returns:
        Formatted string with metadata and contents.
    """
    lines = []
    for name in names:
        lines.append(metadata_str(name))
        lines.append(catalog_str(name))
    return "".join(lines)


def find_in_catalogs(
    pattern: str,
    catalogs: list[str] | tuple[str, ...] | None = None,
) -> dict[str, list[tuple[Any, ...]]]:
    """Find files matching a pattern in catalogs.

    Args:
        pattern: Search pattern (supports * wildcards).
        catalogs: List of catalog names to search (None for all).

    Returns:
        Dictionary mapping catalog names to matching items.
    """
    selected = file_select_catalogs(list(catalogs) if catalogs else None)

    # Convert * to SQL LIKE pattern, preserving literal %
    patterns = pattern.split("%")
    patterns = [s.replace("*", "%") for s in patterns]
    pattern = "%" + "[%]".join(patterns) + "%"

    if not selected:
        logger.error("Catalog does not exist")

    items: dict[str, list[tuple[Any, ...]]] = {}
    for catalog in selected:
        matches = get_catalog_by_pattern(catalog, pattern)
        if matches:
            items[catalog] = matches

    return items


def find_regex_in_catalogs(
    regex: str,
    catalogs: list[str] | None = None,
) -> dict[str, list[tuple[Any, ...]]]:
    """Find files matching a regex in catalogs.

    Args:
        regex: Regular expression pattern.
        catalogs: List of catalog names to search (None for all).

    Returns:
        Dictionary mapping catalog names to matching items.
    """
    selected = file_select_catalogs(catalogs)

    if not selected:
        logger.error("Catalog does not exist")

    items: dict[str, list[tuple[Any, ...]]] = {}
    for catalog in selected:
        matches = get_catalog_by_regex(catalog, regex)
        if matches:
            items[catalog] = matches

    return items


def find_hash_in_catalogs(
    files: list[FileItem],
    catalogs: list[str] | None = None,
) -> dict[str, list[tuple[Any, ...]]]:
    """Find files by hash in catalogs.

    Args:
        files: List of file items with hashes.
        catalogs: List of catalog names to search (None for all).

    Returns:
        Dictionary mapping catalog names to matching items.
    """
    selected = file_select_catalogs(catalogs)

    if not selected:
        logger.error("Catalog does not exist")

    items: dict[str, list[tuple[Any, ...]]] = {}
    for catalog in selected:
        matches = get_catalog_by_hash(catalog, files)
        if matches:
            items[catalog] = matches

    return items


def item_equals(file1: tuple[Any, ...], file2: tuple[Any, ...]) -> bool:
    """Compare two file items for equality.

    Compares name, path, size, and date (indices 1-4).

    Args:
        file1: First file item.
        file2: Second file item.

    Returns:
        True if items are equal.
    """
    return all(file1[i] == file2[i] for i in range(1, 5))


def get_non_inserted_files(
    files: list[FileItem],
    inserted_files: list[tuple[Any, ...]],
) -> list[FileItem]:
    """Get files that haven't been inserted yet.

    Args:
        files: List of files to check.
        inserted_files: List of already inserted files.

    Returns:
        List of files not in inserted_files.
    """
    non_inserted = []
    for file in files:
        exists_in_db = any(item_equals(file, inserted) for inserted in inserted_files)
        if not exists_in_db:
            non_inserted.append(file)
    return non_inserted


def _build_select_catalog_cond_params(
    files: list[FileItem],
) -> list[tuple[str, str, int, int]]:
    """Build parameters for catalog condition query.

    Args:
        files: List of file items.

    Returns:
        List of (name, path, size, date) tuples.
    """
    return [(name, path, size, date) for _, name, date, size, path, _ in files]


def update_catalog(name: str, path: str) -> None:
    """Update an existing catalog.

    Removes files that no longer exist and adds new files.

    Args:
        name: Catalog name.
        path: Path to re-scan.
    """
    if not os.path.exists(file_get_catalog_abspath(name)):
        logger.warning("catalog %s not found.", name)
        return

    fullpath = os.path.abspath(path)
    m = db_get_metadata(name)

    if name != m["name"] or fullpath != m["fullpath"]:
        logger.warning(
            "impossible to continue invalid name or path %s:%s",
            name,
            fullpath,
        )
        return

    # Remove files that have been deleted from the filesystem
    deleted_ids = db_get_deleted_ids(name)
    if deleted_ids:
        logger.info("Updating removed files in the filesystem")
        db_delete_catalog(name, deleted_ids)

    # Add new or modified files
    hash_type: HashType = m.get("hash", "sha1")  # type: ignore[assignment]
    filesubsets = path_block_iterator(fullpath, MAX_FILES_ITER)
    for files in filesubsets:
        params = _build_select_catalog_cond_params(files)
        inserted_files = db_get_inserted_catalogs(name, params)
        non_inserted_files = get_non_inserted_files(files, inserted_files)
        if non_inserted_files:
            logger.info("Updating missing files in the catalog")
            hashed_files = calc_hashes(
                fullpath,
                non_inserted_files,
                BLOCK_SIZE,
                hash_type,
            )
            db_insert_catalog(name, hashed_files)


def create_catalog(
    name: str,
    path: str,
    hash_type: HashType,
    force: bool = False,
) -> bool:
    """Create a new catalog.

    Args:
        name: Catalog name.
        path: Path to index.
        hash_type: Hash algorithm to use.
        force: Overwrite existing catalog.

    Returns:
        True if catalog was created, False if it already exists.
    """
    if not force and os.path.exists(file_get_catalog_abspath(name)):
        logger.warning("Catalog: %s already exists", name)
        return False

    logger.info("Creating catalog: %s", name)

    fullpath = os.path.abspath(path)
    metadata = build_metadata(name, path, fullpath, hash_type)
    db_create(name)
    db_insert_metadata(name, metadata)

    # Add files in batches to avoid memory issues
    filesubsets = path_block_iterator(fullpath, MAX_FILES_ITER)
    for files in filesubsets:
        hashed_files = calc_hashes(fullpath, files, BLOCK_SIZE, hash_type)
        db_insert_catalog(name, hashed_files)

    return True


def scan_catalogs(name: str) -> dict[str, dict[str, list[tuple[Any, ...]]]]:
    """Scan a file or directory against all catalogs.

    Args:
        name: File or directory path to scan.

    Returns:
        Dictionary mapping file names to their catalog matches.
    """
    result: dict[str, dict[str, list[tuple[Any, ...]]]] = {}

    if not os.path.exists(name):
        logger.error("impossible to scan, invalid path: %s", name)
        return result

    if os.path.isdir(name):
        logger.info("scanning dir: %s", name)
        # TODO: Implement directory scanning
    else:
        logger.info("scanning file: %s", name)
        hashed_files = [file_getfile_as_item(name, BLOCK_SIZE, "sha1")]
        result[name] = find_hash_in_catalogs(hashed_files)

    return result
