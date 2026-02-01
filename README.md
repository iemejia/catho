# Catho

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

**Catho** is a command-line file catalog manager inspired by Robert Vasicek's
[Cathy](http://www.mtg.sk/rva/) project. It allows you to index and search files
across different media, volumes, and network locations without having physical
access to them.

## Features

- **Index files** from any directory, including external drives and network shares
- **Search catalogs** locally without needing access to the original media
- **SHA-256 hashing** for duplicate file detection
- **SQLite storage** for fast, portable catalog databases
- **Pattern matching** with wildcards and regex support
- **Web UI** for browsing catalogs (optional feature)
- **Export to JSON** for integration with other tools

## Installation

### From crates.io (recommended)

```bash
cargo install catho
```

### With web UI support

```bash
cargo install catho --features web
```

### From source

```bash
git clone https://github.com/iemejia/catho.git
cd catho
cargo build --release

# Or with web UI:
cargo build --release --features web
```

The binary will be at `target/release/catho`.

## Usage

### Create a catalog

```bash
# Index a directory with a catalog name
catho add my-usb-drive /media/usb-drive

# Index without calculating file hashes (faster)
catho add my-backup /backup/folder -H none
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

# Search using regex
catho find --regex "photo_[0-9]{4}\.jpg"
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
# Check if a file exists in any catalog (by hash)
catho scan /path/to/file.txt

# Scan an entire directory
catho scan /path/to/folder
```

### Export catalog

```bash
# Export to stdout (JSON)
catho export my-catalog

# Export to file
catho export my-catalog -o catalog.json
```

### Web UI (requires `--features web`)

```bash
# Start web server on default port 8080
catho web

# Use custom port and host
catho web -p 3000 --host 0.0.0.0
```

Then open http://localhost:8080 in your browser.

## Catalog Storage

Catalogs are stored as SQLite databases in `~/.catho/`. Each catalog contains:

- File names and paths (relative to the indexed root)
- File sizes and modification dates
- SHA-256 hashes (optional) for duplicate detection

## Development

### Running tests

```bash
cargo test -- --test-threads=1
```

### Building

```bash
# Debug build
cargo build

# Release build
cargo build --release

# With web feature
cargo build --release --features web
```

### Linting

```bash
cargo clippy
cargo fmt --check
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
