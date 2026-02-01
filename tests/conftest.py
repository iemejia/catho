"""Pytest configuration and fixtures for catho tests."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_catho_dir(monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Create a temporary directory for catho catalogs.

    This fixture patches catho.file.CATHO_PATH to use a temp directory.
    """
    temp_dir = Path(tempfile.mkdtemp())
    import catho.file as file_module

    monkeypatch.setattr(file_module, "CATHO_PATH", temp_dir)
    monkeypatch.setattr(file_module, "catho_path", str(temp_dir))

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_files(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a directory with sample files for testing.

    Returns:
        Path to the directory containing sample files.
    """
    # Create some test files
    (tmp_path / "file1.txt").write_text("Hello World")
    (tmp_path / "file2.txt").write_text("Test content")

    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("Nested file")
    (subdir / "data.csv").write_text("col1,col2\n1,2\n3,4")

    yield tmp_path


@pytest.fixture
def test_catalog(
    temp_catho_dir: Path,
    sample_files: Path,
) -> Generator[str, None, None]:
    """Create a test catalog.

    Returns:
        Name of the created catalog.
    """
    import catho

    catalog_name = "test_catalog"
    catho.create_catalog(catalog_name, str(sample_files), "sha256")

    yield catalog_name
