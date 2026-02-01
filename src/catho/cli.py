"""Command-line interface for catho."""

import argparse
import contextlib
import logging
import sys

from catho._version import __version__
from catho.catalog import (
    VALID_HASH_TYPES,
    catalog_to_str,
    catalogs_info_str,
    catalogs_str,
    create_catalog,
    find_in_catalogs,
    scan_catalogs,
    update_catalog,
)
from catho.file import HashType, catho_path, file_get_catalogs, file_rm_catalog_file
from catho.utils import file_touch_dir

# Configure logging
logger = logging.getLogger("catho")
_handler = logging.StreamHandler()
logger.addHandler(_handler)
logger.setLevel(logging.INFO)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Catho - A command-line file catalog manager",
        prog="catho",
        epilog='"catho <command> -h" for more information on a specific command.',
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(help="commands", dest="command")

    # help command
    help_parser = subparsers.add_parser("help", help="help for command")
    help_parser.add_argument("cmd", action="store", help="command")

    # ls command
    list_parser = subparsers.add_parser("ls", help="list available catalogs")
    list_parser.add_argument(
        "names",
        action="store",
        nargs="*",
        help="catalog name",
    )

    # add command
    add_parser = subparsers.add_parser("add", help="adds catalog")
    add_parser.add_argument("name", action="store", help="catalog name")
    add_parser.add_argument("path", action="store", help="path to index")
    add_parser.add_argument(
        "-f",
        "--force",
        help="force overwrite",
        action="store_true",
    )
    add_parser.add_argument(
        "-H",
        "--hash-type",
        help="hash function (sha256 (default), None)",
        action="store",
        default="sha256",
    )
    add_parser.add_argument(
        "-c",
        "--continue",
        help="continue/update existing catalog",
        action="store_true",
        dest="cont",
    )

    # rm command
    rm_parser = subparsers.add_parser("rm", help="removes catalog")
    rm_parser.add_argument(
        "names",
        action="store",
        nargs="*",
        help="catalog name",
    )

    # find command
    find_parser = subparsers.add_parser(
        "find",
        help="find a filename in catalog",
    )
    find_parser.add_argument(
        "pattern",
        action="store",
        help="a pattern to match",
    )
    find_parser.add_argument(
        "catalogs",
        action="append",
        nargs="*",
        help="catalog name",
    )

    # scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="scan if the corresponding file/dir exists in the catalog",
    )
    scan_parser.add_argument("name", action="store", help="file or path name")

    # general options
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-s", "--silent", action="store_true")
    parser.add_argument(
        "-l",
        "--create-log",
        help="creates log file",
        action="store",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Create the default path for the catalogs (~/.catho)
    file_touch_dir(catho_path)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    if args.silent:
        logger.removeHandler(_handler)
        logger.addHandler(logging.NullHandler())

    if args.create_log:
        logger.info("logging to file %s", args.create_log)
        fh = logging.FileHandler(args.create_log)
        logger.addHandler(fh)

    # Handle commands
    if args.command == "add":
        logger.info("hash_type: %s", args.hash_type)
        if args.hash_type not in VALID_HASH_TYPES:
            logger.error("error: invalid hash function: %s", args.hash_type)
            return 3

        hash_type: HashType = args.hash_type
        if not args.cont:
            create_catalog(args.name, args.path, hash_type, args.force)
        else:
            update_catalog(args.name, args.path)

    elif args.command == "ls":
        if not args.names:
            all_catalogs = file_get_catalogs()
            logger.info(catalogs_str(all_catalogs))
        else:
            logger.info(catalogs_info_str(args.names))

    elif args.command == "rm":
        file_rm_catalog_file(args.names)

    elif args.command == "find":
        search_catalogs: list[str]
        if args.catalogs[0]:
            search_catalogs = args.catalogs[0]
        else:
            search_catalogs = [str(c["name"]) for c in file_get_catalogs()]

        str_catalogs = ", ".join(search_catalogs)
        logger.info("Finding %s in (%s)", args.pattern, str_catalogs)

        matches = find_in_catalogs(args.pattern, search_catalogs)

        count = 0
        for catalog_name, items in matches.items():
            count += len(items)
            logger.info("%s:", catalog_name)
            logger.info(catalog_to_str(items))

        logger.info("%s items found", count)

    elif args.command == "scan":
        scan_matches = scan_catalogs(args.name)
        for name, catalog_matches in scan_matches.items():
            logger.info("%s found in catalogs: %s", name, list(catalog_matches.keys()))

    elif args.command == "help":
        # Show help for specific command by re-invoking with -h
        # This is a cleaner approach than accessing private parser internals
        with contextlib.suppress(SystemExit):
            create_parser().parse_args([args.cmd, "-h"])

    else:
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
