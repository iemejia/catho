"""File system operations for catho."""

import errno
import logging
import os
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, TypeAlias

from catho.utils import file_hash, get_file_info

# Type aliases for export (using TypeAlias for cross-module import compatibility)
HashType: TypeAlias = Literal["sha256", "None"]  # noqa: UP040
FileItem: TypeAlias = tuple[int | None, str, int, int, str, str | None]  # noqa: UP040

logger = logging.getLogger("catho")

# Default path for storing catalogs
CATHO_PATH: Path = Path.home() / ".catho"
CATHO_EXTENSION: str = ".db"

# Legacy aliases for backward compatibility
catho_path: str = str(CATHO_PATH)
catho_extension: str = CATHO_EXTENSION


def file_get_catalog_abspath(name: str) -> Path:
    """Get the absolute path for a catalog database.

    Args:
        name: Name of the catalog.

    Returns:
        Full path to the catalog database file.
    """
    return CATHO_PATH / f"{name}{CATHO_EXTENSION}"


def file_get_catalogs() -> list[dict[str, str | int]]:
    """List all available catalogs.

    Returns:
        List of dictionaries with catalog info (name, size, date).
    """
    if not CATHO_PATH.exists():
        return []

    catalogs: list[dict[str, str | int]] = []
    for filepath in CATHO_PATH.iterdir():
        if filepath.suffix == CATHO_EXTENSION:
            size, date = get_file_info(filepath)
            catalogs.append(
                {
                    "name": filepath.stem,
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
    fullpath: str | Path,
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
    root = Path(fullpath)
    files: list[FileItem] = []

    for filepath in root.rglob("*"):
        if not filepath.is_file():
            continue

        try:
            rel_path = str(filepath.parent.relative_to(root))
            size, date = get_file_info(filepath)
            # id and hash are None initially
            files.append((None, filepath.name, date, size, rel_path, None))

            if len(files) == num_files:
                yield files
                files = []

        except OSError as oe:
            if oe.errno == errno.ENOENT:
                logger.error(
                    "Ignoring %s. No such target file or directory %s",
                    filepath,
                    filepath.resolve(),
                )
            else:
                logger.error(
                    "An error occurred processing %s: %s",
                    filepath.name,
                    oe,
                )
        except UnicodeDecodeError as ue:
            logger.error(
                "An error occurred processing %s: %s",
                filepath.name,
                ue,
            )

    if files:
        yield files


def calc_hashes(
    fullpath: str | Path,
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
    root = Path(fullpath)
    hashed_files: list[FileItem] = []

    for file_id, name, date, size, path, file_hash_value in files:
        if not file_hash_value:
            file_path = root / path / name
            try:
                calculated_hash = file_hash(file_path, block_size, hash_type)
                logger.debug(
                    "Calculating %s for %s | %s", hash_type, name, calculated_hash
                )
                hashed_files.append((file_id, name, date, size, path, calculated_hash))
            except OSError as ioe:
                error_code = ioe.errno or 0
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
        path = file_get_catalog_abspath(name)
        try:
            if path.exists():
                path.unlink()
                logger.info("rm %s", path)
            else:
                logger.error("rm: %s: No such file or directory", path)
        except OSError:
            logger.error("rm: %s: No such file or directory", path)


def file_getfile_as_item(
    name: str | Path,
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
    filepath = Path(name)
    size, date = get_file_info(filepath)
    calculated_hash = file_hash(filepath, block_size, hash_type)
    return (None, str(filepath), date, size, path or "", calculated_hash)
