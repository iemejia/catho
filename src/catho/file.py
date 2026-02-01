"""File system operations for catho."""

from __future__ import annotations

import errno
import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

from catho.utils import file_hash, get_file_info

HashType = Literal["sha1", "None"]

logger = logging.getLogger("catho")

# Default path for storing catalogs
catho_path: str = os.path.join(os.path.expanduser("~"), ".catho")
catho_extension: str = ".db"

# Type alias for file items
# (id, name, date, size, path, hash)
FileItem = tuple[int | None, str, int, int, str, str | None]


def file_get_catalog_abspath(name: str) -> str:
    """Get the absolute path for a catalog database.

    Args:
        name: Name of the catalog.

    Returns:
        Full path to the catalog database file.
    """
    return os.path.join(catho_path, name + catho_extension)


def file_get_catalogs() -> list[dict[str, str | int]]:
    """List all available catalogs.

    Returns:
        List of dictionaries with catalog info (name, size, date).
    """
    catalogs: list[dict[str, str | int]] = []
    if not os.path.exists(catho_path):
        return catalogs

    files = os.listdir(catho_path)
    ext_len = len(catho_extension)
    for filename in files:
        if filename.endswith(catho_extension):
            fullpath = os.path.join(catho_path, filename)
            size, date = get_file_info(fullpath)
            catalogs.append(
                {
                    "name": filename[:-ext_len],
                    "size": size,
                    "date": date,
                }
            )
    return catalogs


def file_select_catalogs(selection: list[str] | None = None) -> list[str]:
    """Select catalogs from available catalogs.

    Args:
        selection: List of catalog names to select. If None, selects all.

    Returns:
        List of selected catalog names that exist.
    """
    if not selection:
        return [str(catalog["name"]) for catalog in file_get_catalogs()]

    available = {str(catalog["name"]) for catalog in file_get_catalogs()}
    selected = [name for name in selection if name in available]

    if len(selection) != len(selected):
        discarded = [s for s in selection if s not in available]
        logger.warning("Some catalogs ignored (%s)", discarded)

    return selected


def path_block_iterator(
    fullpath: str,
    num_files: int,
) -> Iterator[list[FileItem]]:
    """Iterate over files in a path, yielding batches.

    Yields batches of file items for the given path. Links to directories
    are ignored to avoid recursion.

    Args:
        fullpath: The root path to walk.
        num_files: Maximum number of files per batch.

    Yields:
        Lists of file items (id, name, date, size, rel_path, hash).
    """
    i = 0
    files: list[FileItem] = []

    for dirname, _dirnames, filenames in os.walk(fullpath):
        for filename in filenames:
            try:
                rel_path = os.path.relpath(dirname, fullpath)
                # Full file path
                path = os.path.join(dirname, filename)
                size, date = get_file_info(path)
                # id and hash are None initially
                files.append((None, filename, date, size, rel_path, None))
                i += 1

                if i == num_files:
                    yield files
                    i = 0
                    files = []

            except OSError as oe:
                file_path = os.path.join(dirname, filename)
                if oe.errno == errno.ENOENT:
                    realpath = os.path.realpath(file_path)
                    logger.error(
                        "Ignoring %s. No such target file or directory %s",
                        file_path,
                        realpath,
                    )
                else:
                    logger.error(
                        "An error occurred processing %s: %s",
                        filename,
                        oe,
                    )
            except UnicodeDecodeError as ue:
                logger.error(
                    "An error occurred processing %s: %s",
                    filename,
                    ue,
                )

    if files:
        yield files


def calc_hashes(
    fullpath: str,
    files: list[FileItem],
    block_size: int,
    hash_type: HashType,
) -> list[FileItem]:
    """Calculate hash values for files that don't have them.

    Args:
        fullpath: Base path for the files.
        files: List of file items.
        block_size: Block size for hash calculation.
        hash_type: Type of hash to calculate.

    Returns:
        List of file items with hashes calculated.
    """
    hashed_files: list[FileItem] = []
    for file_id, name, date, size, path, file_hash_value in files:
        if not file_hash_value:
            file_path = os.path.join(fullpath, path, name)
            try:
                calculated_hash = file_hash(file_path, block_size, hash_type)
                logger.debug(
                    "Calculating %s for %s | %s", hash_type, name, calculated_hash
                )
                hashed_files.append((file_id, name, date, size, path, calculated_hash))
            except OSError as ioe:
                error_code = ioe.errno if ioe.errno is not None else 0
                logger.error(
                    "Error calculating hash for %s [%s:%s]",
                    file_path,
                    error_code,
                    os.strerror(error_code),
                )
    return hashed_files


def file_rm_catalog_file(catalogs: list[str]) -> None:
    """Delete catalog files.

    Args:
        catalogs: List of catalog names to delete.
    """
    for name in catalogs:
        path = Path(file_get_catalog_abspath(name))
        try:
            if path.exists():
                path.unlink()
                logger.info("rm %s", path)
            else:
                logger.error("rm: %s: No such file or directory", path)
        except OSError:
            logger.error("rm: %s: No such file or directory", path)


def file_getfile_as_item(
    name: str,
    block_size: int,
    hash_type: HashType,
    path: str | None = None,
) -> FileItem:
    """Get file information as a file item tuple.

    Args:
        name: Path to the file.
        block_size: Block size for hash calculation.
        hash_type: Type of hash to calculate.
        path: Optional original indexing path.

    Returns:
        File item tuple (id, name, date, size, path, hash).
    """
    size, date = get_file_info(name)
    calculated_hash = file_hash(name, block_size, hash_type)
    return (None, name, date, size, path or "", calculated_hash)
