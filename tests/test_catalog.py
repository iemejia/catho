"""Tests for catho catalog operations."""

from pathlib import Path

import catho
from catho.catalog import (
    catalog_str,
    catalogs_str,
    create_catalog,
    find_in_catalogs,
    metadata_str,
    update_catalog,
)
from catho.file import file_get_catalogs, path_block_iterator


class TestPathBlockIterator:
    """Tests for path_block_iterator function."""

    def test_yields_batches(self, sample_files: Path) -> None:
        """Test that iterator yields batches of correct size."""
        batch_size = 2
        batches = list(path_block_iterator(str(sample_files), batch_size))
        # Should have files in batches
        for batch in batches[:-1]:  # All but last batch
            assert len(batch) <= batch_size

    def test_includes_all_files(self, sample_files: Path) -> None:
        """Test that all files are included."""
        all_files = []
        for batch in path_block_iterator(str(sample_files), 10):
            all_files.extend(batch)
        # We have 4 files: file1.txt, file2.txt, subdir/file3.txt, subdir/data.csv
        assert len(all_files) == 4


class TestCreateCatalog:
    """Tests for create_catalog function."""

    def test_creates_catalog(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test creating a new catalog."""
        result = create_catalog("test", str(sample_files), "sha256")
        assert result is True
        # Catalog file should exist
        assert (temp_catho_dir / "test.db").exists()

    def test_existing_catalog_without_force(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test that creating existing catalog without force returns False."""
        create_catalog("test", str(sample_files), "sha256")
        result = create_catalog("test", str(sample_files), "sha256")
        assert result is False

    def test_existing_catalog_with_force(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test that creating existing catalog with force succeeds."""
        create_catalog("test", str(sample_files), "sha256")
        result = create_catalog("test", str(sample_files), "sha256", force=True)
        assert result is True


class TestDbOperations:
    """Tests for database operations."""

    def test_get_metadata(self, test_catalog: str) -> None:
        """Test getting catalog metadata."""
        metadata = catho.db_get_metadata(test_catalog)
        assert metadata
        assert len(metadata) == 7
        assert metadata["name"] == test_catalog
        assert metadata["version"] == "1"
        assert metadata["hash"] == "sha256"

    def test_get_catalog(self, test_catalog: str) -> None:
        """Test getting catalog contents."""
        catalog = catho.db_get_catalog(test_catalog)
        assert catalog
        assert len(catalog) > 0


class TestFileGetCatalogs:
    """Tests for file_get_catalogs function."""

    def test_lists_catalogs(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test listing available catalogs."""
        create_catalog("cat1", str(sample_files), "sha256")
        create_catalog("cat2", str(sample_files), "sha256")
        catalogs = file_get_catalogs()
        names = [c["name"] for c in catalogs]
        assert "cat1" in names
        assert "cat2" in names


class TestCatalogStrFunctions:
    """Tests for catalog string formatting functions."""

    def test_metadata_str(self, test_catalog: str) -> None:
        """Test metadata string formatting."""
        result = metadata_str(test_catalog)
        assert "METADATA" in result
        assert test_catalog in result

    def test_catalog_str(self, test_catalog: str) -> None:
        """Test catalog string formatting."""
        result = catalog_str(test_catalog)
        assert result  # Should not be empty

    def test_catalogs_str(self, test_catalog: str) -> None:
        """Test catalogs list string formatting."""
        catalogs = file_get_catalogs()
        result = catalogs_str(catalogs)
        assert result  # Should not be empty


class TestFindInCatalogs:
    """Tests for find_in_catalogs function."""

    def test_find_existing_file(self, test_catalog: str) -> None:
        """Test finding an existing file."""
        items = find_in_catalogs("file1.txt", [test_catalog])
        assert test_catalog in items
        assert len(items[test_catalog]) > 0

    def test_find_with_wildcard(self, test_catalog: str) -> None:
        """Test finding files with wildcard pattern."""
        items = find_in_catalogs("*.txt", [test_catalog])
        files = [f for _, files in items.items() for f in files]
        assert len(files) >= 3  # file1.txt, file2.txt, file3.txt

    def test_find_nonexistent_file(self, test_catalog: str) -> None:
        """Test finding a non-existent file returns empty."""
        items = find_in_catalogs("nonexistent_file.xyz", [test_catalog])
        files = [f for _, files in items.items() for f in files]
        assert len(files) == 0

    def test_find_in_multiple_catalogs(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test finding in multiple catalogs."""
        create_catalog("cat1", str(sample_files), "sha256")
        create_catalog("cat2", str(sample_files), "sha256")
        items = find_in_catalogs("file1.txt", ["cat1", "cat2"])
        # Should find in both catalogs
        files = [f for _, files in items.items() for f in files]
        assert len(files) >= 2


class TestUpdateCatalog:
    """Tests for update_catalog function."""

    def test_update_adds_new_files(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test that update adds new files."""
        create_catalog("test", str(sample_files), "sha256")
        # Add a new file
        (sample_files / "new_file.txt").write_text("new content")
        update_catalog("test", str(sample_files))
        # New file should be in catalog
        items = find_in_catalogs("new_file.txt", ["test"])
        files = [f for _, files in items.items() for f in files]
        assert len(files) > 0


class TestFileCatalogOperations:
    """Tests for file catalog operations."""

    def test_rm_catalog_file(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test removing a catalog file."""
        create_catalog("to_delete", str(sample_files), "sha256")
        assert (temp_catho_dir / "to_delete.db").exists()
        catho.file_rm_catalog_file(["to_delete"])
        assert not (temp_catho_dir / "to_delete.db").exists()
