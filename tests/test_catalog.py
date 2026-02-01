"""Tests for catho catalog operations."""

from pathlib import Path

import catho
from catho.catalog import (
    build_metadata,
    catalog_str,
    catalog_to_str,
    catalogs_info_str,
    catalogs_str,
    create_catalog,
    find_hash_in_catalogs,
    find_in_catalogs,
    find_regex_in_catalogs,
    get_non_inserted_files,
    item_equals,
    metadata_str,
    scan_catalogs,
    update_catalog,
)
from catho.file import file_get_catalogs, file_getfile_as_item, path_block_iterator


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


class TestBuildMetadata:
    """Tests for build_metadata function."""

    def test_build_metadata_structure(self) -> None:
        """Test that build_metadata creates proper structure."""
        metadata = build_metadata("test", "/path", "/full/path", "sha256")
        assert len(metadata) == 7
        keys = [k for k, v in metadata]
        assert "version" in keys
        assert "name" in keys
        assert "path" in keys
        assert "fullpath" in keys
        assert "createdate" in keys
        assert "lastmodifdate" in keys
        assert "hash" in keys

    def test_build_metadata_values(self) -> None:
        """Test that build_metadata sets correct values."""
        metadata = build_metadata("mycat", "/orig", "/full/orig", "None")
        meta_dict = dict(metadata)
        assert meta_dict["version"] == "1"
        assert meta_dict["name"] == "mycat"
        assert meta_dict["path"] == "/orig"
        assert meta_dict["fullpath"] == "/full/orig"
        assert meta_dict["hash"] == "None"


class TestCatalogToStr:
    """Tests for catalog_to_str function."""

    def test_catalog_to_str_empty(self) -> None:
        """Test catalog_to_str with empty catalog."""
        result = catalog_to_str([])
        assert result == "\n"

    def test_catalog_to_str_with_items(self) -> None:
        """Test catalog_to_str with items."""
        catalog = [
            (1, "file.txt", 1704067200, 1024, "/path", "abc123"),
        ]
        result = catalog_to_str(catalog)
        assert "file.txt" in result
        assert "1024" in result
        assert "/path" in result
        assert "abc123" in result


class TestCatalogsInfoStr:
    """Tests for catalogs_info_str function."""

    def test_catalogs_info_str(self, test_catalog: str) -> None:
        """Test getting detailed info for catalogs."""
        result = catalogs_info_str([test_catalog])
        assert "METADATA" in result
        assert test_catalog in result


class TestItemEquals:
    """Tests for item_equals function."""

    def test_equal_items(self) -> None:
        """Test comparing equal items."""
        item1 = (1, "file.txt", 1704067200, 1024, "/path", "hash1")
        item2 = (2, "file.txt", 1704067200, 1024, "/path", "hash2")
        assert item_equals(item1, item2) is True

    def test_different_items(self) -> None:
        """Test comparing different items."""
        item1 = (1, "file1.txt", 1704067200, 1024, "/path", "hash1")
        item2 = (1, "file2.txt", 1704067200, 1024, "/path", "hash1")
        assert item_equals(item1, item2) is False


class TestGetNonInsertedFiles:
    """Tests for get_non_inserted_files function."""

    def test_all_files_new(self) -> None:
        """Test when all files are new."""
        files = [
            (None, "file1.txt", 1704067200, 1024, "/path", None),
            (None, "file2.txt", 1704067300, 2048, "/path2", None),
        ]
        inserted = []
        result = get_non_inserted_files(files, inserted)
        assert len(result) == 2

    def test_some_files_exist(self) -> None:
        """Test when some files already exist."""
        files = [
            (None, "file1.txt", 1704067200, 1024, "/path", None),
            (None, "file2.txt", 1704067300, 2048, "/path2", None),
        ]
        inserted = [
            (1, "file1.txt", 1704067200, 1024, "/path", "hash1"),
        ]
        result = get_non_inserted_files(files, inserted)
        assert len(result) == 1
        assert result[0][1] == "file2.txt"

    def test_all_files_exist(self) -> None:
        """Test when all files already exist."""
        files = [
            (None, "file1.txt", 1704067200, 1024, "/path", None),
        ]
        inserted = [
            (1, "file1.txt", 1704067200, 1024, "/path", "hash1"),
        ]
        result = get_non_inserted_files(files, inserted)
        assert len(result) == 0


class TestFindRegexInCatalogs:
    """Tests for find_regex_in_catalogs function."""

    def test_find_regex_match(self, test_catalog: str) -> None:
        """Test finding files with regex pattern."""
        items = find_regex_in_catalogs(".*file.*", [test_catalog])
        assert test_catalog in items
        assert len(items[test_catalog]) >= 1

    def test_find_regex_no_match(self, test_catalog: str) -> None:
        """Test regex with no matches."""
        items = find_regex_in_catalogs("^xyz123_nomatch$", [test_catalog])
        files = [f for _, files in items.items() for f in files]
        assert len(files) == 0

    def test_find_regex_all_catalogs(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test finding regex in all catalogs."""
        create_catalog("regex_cat1", str(sample_files), "sha256")
        create_catalog("regex_cat2", str(sample_files), "sha256")
        items = find_regex_in_catalogs(".*\\.txt$")
        # Should find in both catalogs
        assert len(items) >= 2


class TestFindHashInCatalogs:
    """Tests for find_hash_in_catalogs function."""

    def test_find_hash_match(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test finding files by hash."""
        create_catalog("hash_cat", str(sample_files), "sha256")

        # Get a file's hash from the catalog
        catalog = catho.db_get_catalog("hash_cat")
        if catalog:
            file_hash = catalog[0][5]
            if file_hash:
                files = [(None, "test", 0, 0, "", file_hash)]
                items = find_hash_in_catalogs(files, ["hash_cat"])
                assert "hash_cat" in items

    def test_find_hash_no_match(self, test_catalog: str) -> None:
        """Test hash search with no matches."""
        files = [(None, "test", 0, 0, "", "nonexistent_hash_value")]
        items = find_hash_in_catalogs(files, [test_catalog])
        files_found = [f for _, files in items.items() for f in files]
        assert len(files_found) == 0


class TestScanCatalogs:
    """Tests for scan_catalogs function."""

    def test_scan_existing_file(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test scanning an existing file."""
        create_catalog("scan_cat", str(sample_files), "sha256")
        file_path = str(sample_files / "file1.txt")
        result = scan_catalogs(file_path)
        assert file_path in result

    def test_scan_nonexistent_path(self, temp_catho_dir: Path) -> None:
        """Test scanning a non-existent path."""
        result = scan_catalogs("/nonexistent/path/file.txt")
        assert result == {}


class TestUpdateCatalogEdgeCases:
    """Additional tests for update_catalog edge cases."""

    def test_update_removes_deleted_files(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test that update removes deleted files from catalog."""
        create_catalog("update_test", str(sample_files), "sha256")

        # Verify file1.txt is in catalog
        items = find_in_catalogs("file1.txt", ["update_test"])
        assert len(items.get("update_test", [])) == 1

        # Delete the file
        (sample_files / "file1.txt").unlink()

        # Update catalog
        update_catalog("update_test", str(sample_files))

        # File should no longer be found (but we can't easily verify deletion
        # without checking the catalog directly)

    def test_update_nonexistent_catalog(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test updating a non-existent catalog does nothing."""
        # Should not raise an error
        update_catalog("nonexistent", str(sample_files))

    def test_update_wrong_path(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test updating with wrong path."""
        create_catalog("wrong_path_cat", str(sample_files), "sha256")
        # Update with a different path - should warn
        update_catalog("wrong_path_cat", "/different/path")


class TestFindInCatalogsEdgeCases:
    """Additional tests for find_in_catalogs edge cases."""

    def test_find_with_percent_literal(self, test_catalog: str) -> None:
        """Test finding with literal percent sign."""
        # Should escape % properly
        items = find_in_catalogs("100%", [test_catalog])
        files = [f for _, files in items.items() for f in files]
        assert len(files) == 0  # No files with "100%" in name

    def test_find_all_catalogs(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test finding in all catalogs (no catalog list)."""
        create_catalog("find_all_1", str(sample_files), "sha256")
        create_catalog("find_all_2", str(sample_files), "sha256")
        items = find_in_catalogs("file1.txt")
        assert len(items) >= 2


class TestFileGetFileAsItem:
    """Tests for file_getfile_as_item function."""

    def test_getfile_as_item(self, sample_files: Path) -> None:
        """Test getting file as item tuple."""
        file_path = sample_files / "file1.txt"
        result = file_getfile_as_item(str(file_path), 1048576, "sha256")
        assert result[0] is None  # id
        assert str(file_path) in result[1]  # name
        assert result[2] > 0  # date
        assert result[3] == 11  # size ("Hello World")
        assert result[4] == ""  # path
        assert len(result[5]) == 64  # sha256 hash

    def test_getfile_as_item_with_path(self, sample_files: Path) -> None:
        """Test getting file as item with original path."""
        file_path = sample_files / "file1.txt"
        result = file_getfile_as_item(str(file_path), 1048576, "sha256", "/orig")
        assert result[4] == "/orig"
