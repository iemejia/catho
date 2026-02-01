"""Catho - A command-line file catalog manager."""

from catho._version import __version__
from catho.catalog import (
    catalog_str,
    catalog_to_str,
    catalogs_info_str,
    catalogs_str,
    create_catalog,
    find_hash_in_catalogs,
    find_in_catalogs,
    find_regex_in_catalogs,
    metadata_str,
    scan_catalogs,
    update_catalog,
)
from catho.db import (
    db_create,
    db_get_catalog,
    db_get_metadata,
    db_insert_catalog,
    db_insert_metadata,
    get_catalog_by_hash,
    get_catalog_by_pattern,
    get_catalog_by_regex,
)
from catho.file import (
    calc_hashes,
    catho_path,
    file_get_catalog_abspath,
    file_get_catalogs,
    file_rm_catalog_file,
    file_select_catalogs,
    path_block_iterator,
)
from catho.utils import (
    file_hash,
    file_rm,
    file_touch_dir,
    file_touch_file,
    get_file_info,
    sizeof_fmt,
)

__all__ = [
    "__version__",
    # catalog
    "create_catalog",
    "update_catalog",
    "find_in_catalogs",
    "find_regex_in_catalogs",
    "find_hash_in_catalogs",
    "scan_catalogs",
    "metadata_str",
    "catalog_str",
    "catalog_to_str",
    "catalogs_str",
    "catalogs_info_str",
    # db
    "db_create",
    "db_get_metadata",
    "db_get_catalog",
    "db_insert_metadata",
    "db_insert_catalog",
    "get_catalog_by_pattern",
    "get_catalog_by_regex",
    "get_catalog_by_hash",
    # file
    "catho_path",
    "file_get_catalog_abspath",
    "file_get_catalogs",
    "file_select_catalogs",
    "path_block_iterator",
    "calc_hashes",
    "file_rm_catalog_file",
    # utils
    "file_touch_dir",
    "file_touch_file",
    "file_rm",
    "get_file_info",
    "sizeof_fmt",
    "file_hash",
]
