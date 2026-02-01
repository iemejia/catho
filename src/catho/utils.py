"""Utility functions for catho.

This module contains general utility functions that can be reused
across the project and potentially in other projects.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Literal


def file_touch_dir(path: str | Path) -> None:
    """Create directory if it doesn't exist.

    Args:
        path: Path to the directory to create.
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def file_touch_file(name: str | Path) -> None:
    """Touch a file (update mtime or create empty file).

    Args:
        name: Path to the file to touch.
    """
    path = Path(name)
    if path.exists():
        path.touch()
    else:
        path.touch()


def file_rm(name: str | Path) -> None:
    """Remove a file or directory.

    Args:
        name: Path to the file or directory to remove.
    """
    path = Path(name)
    if path.exists():
        if path.is_dir():
            path.rmdir()
        else:
            path.unlink()


def get_file_info(fullpath: str | Path) -> tuple[int, int]:
    """Return the size and modification date for a file.

    Args:
        fullpath: Path to the file.

    Returns:
        A tuple of (size in bytes, modification date in unix timestamp).
    """
    stat = os.stat(fullpath)
    date = int(stat.st_ctime)  # in unix time
    size = stat.st_size  # in bytes
    return size, date


def sizeof_fmt(num: float) -> str:
    """Format a file size as human-readable string.

    Args:
        num: Size in bytes.

    Returns:
        Human-readable size string (e.g., "1.5 MB").
    """
    for unit in ("bytes", "KB", "MB", "GB", "TB"):
        if num < 1024.0:
            return f"{num:3.1f} {unit}"
        num /= 1024.0
    return f"{num:3.1f} PB"


# Type alias for hash types
HashType = Literal["sha1", "None"]


def file_hash(
    filename: str | Path,
    block_size: int,
    hash_type: HashType = "sha1",
) -> str:
    """Calculate the hash for a file.

    The hash is calculated in blocks of block_size to support large files.

    Args:
        filename: Path to the file to hash.
        block_size: Size of blocks to read at a time.
        hash_type: Hash algorithm to use ('sha1' or 'None').

    Returns:
        Hexadecimal hash string, or empty string if hash_type is 'None'.
    """
    if hash_type == "sha1":
        h = hashlib.sha1()
        with open(filename, "rb") as f:
            while True:
                data = f.read(block_size)
                if not data:
                    break
                h.update(data)
        return h.hexdigest()
    return ""


def list_of_tuples_to_dict(items: list[tuple[str, str]]) -> dict[str, str]:
    """Convert a list of key-value tuples to a dictionary.

    Args:
        items: List of (key, value) tuples.

    Returns:
        Dictionary with the key-value pairs.
    """
    result: dict[str, str] = {}
    for k, v in items:
        result.setdefault(k, v)
    return result
