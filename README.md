# Catho

[![CI](https://github.com/iemejia/catho/actions/workflows/ci.yml/badge.svg)](https://github.com/iemejia/catho/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/catho.svg)](https://badge.fury.io/py/catho)
[![Python versions](https://img.shields.io/pypi/pyversions/catho.svg)](https://pypi.org/project/catho/)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

**Catho** is a command-line file catalog manager inspired by Robert Vasicek's
[Cathy](http://www.mtg.sk/rva/) project. It allows you to index and search files
across different media, volumes, and network locations without having physical
access to them.

## Features

- **Index files** from any directory, including external drives and network shares
- **Search catalogs** locally without needing access to the original media
- **SHA-1 hashing** for duplicate file detection
- **SQLite storage** for fast, portable catalog databases
- **Pattern matching** with wildcards and regex support

## Installation

### From PyPI (recommended)

```bash
pip install catho
```

### From source

```bash
git clone https://github.com/iemejia/catho.git
cd catho
pip install -e .
```

### Development installation

```bash
pip install -e ".[dev]"
pre-commit install
```

## Usage

### Create a catalog

```bash
# Index a directory with a catalog name
catho add my-usb-drive /media/usb-drive

# Index without calculating file hashes (faster)
catho add my-backup /backup/folder -H None
```

### List catalogs

```bash
# List all catalogs
catho ls

# Show details for a specific catalog
catho ls my-usb-drive
```

### Search for files

```bash
# Search for files matching a pattern (supports * wildcard)
catho find "*.mp3"

# Search in specific catalogs
catho find "report*.pdf" my-usb-drive my-backup

# Search all catalogs for files containing "photo"
catho find "*photo*"
```

### Update a catalog

```bash
# Update an existing catalog (adds new files, removes deleted ones)
catho add my-usb-drive /media/usb-drive --continue
```

### Remove a catalog

```bash
catho rm my-old-catalog
```

### Scan for duplicates

```bash
# Check if a file exists in any catalog
catho scan /path/to/file.txt
```

## Catalog Storage

Catalogs are stored as SQLite databases in `~/.catho/`. Each catalog contains:

- File names and paths (relative to the indexed root)
- File sizes and modification dates
- SHA-1 hashes (optional) for duplicate detection

For more details about the catalog structure, see
[docs/catalog.sql](catho/docs/catalog.sql).

## Development

### Running tests

```bash
pytest
```

### Running tests with coverage

```bash
pytest --cov=src/catho --cov-report=html
```

### Linting and formatting

```bash
ruff check src tests
ruff format src tests
mypy src/catho
```

### Building the package

```bash
pip install build
python -m build
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass and linting is clean
5. Submit a pull request

## License

This project is licensed under the GNU Lesser General Public License v3.0 - see
the [LICENSE](LICENSE) file for details.
