# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2024-12-XX

### Added
- Modern Python packaging with `pyproject.toml`
- Full type hints throughout the codebase
- Comprehensive test suite using pytest
- GitHub Actions CI/CD pipeline
- Pre-commit hooks for code quality
- Support for Python 3.9-3.13
- `py.typed` marker for PEP 561 compliance
- `--version` flag for CLI

### Changed
- Migrated from `distutils` to `setuptools` with PEP 517/518 build system
- Reorganized source code to `src/` layout
- Moved tests to project root `tests/` directory
- Updated import system to use proper absolute imports
- Improved logging with lazy string formatting
- Enhanced error handling in file operations

### Removed
- Dropped Python 2.x and Python 3.3 support
- Removed deprecated `setup.py`, `.travis.yml`, `requirements.txt`
- Removed `argparse` from dependencies (part of stdlib in Python 3)

### Fixed
- Python 3 compatibility issues with imports
- IOError handling (now uses OSError as per Python 3)
- Unbound variable issues in error handling

## [0.1dev] - Previous

Initial development version with basic catalog functionality.
