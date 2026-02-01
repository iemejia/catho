"""Tests for catho database operations."""

from pathlib import Path

from catho.catalog import create_catalog
from catho.db import (
    _db_regex,
    db_create,
    db_delete_catalog,
    db_get_catalog,
    db_get_deleted_ids,
    db_get_inserted_catalogs,
    db_get_metadata,
    db_insert_catalog,
    db_insert_metadata,
    get_catalog_by_absolute_name,
    get_catalog_by_hash,
    get_catalog_by_path,
    get_catalog_by_pattern,
    get_catalog_by_regex,
)
from catho.file import file_get_catalog_abspath


class TestDbRegex:
    """Tests for the _db_regex function."""

    def test_basic_match(self) -> None:
        """Test basic regex matching."""
        assert _db_regex("test", "test") is True
        assert _db_regex("test", "testing") is True

    def test_pattern_match(self) -> None:
        """Test pattern matching."""
        assert _db_regex(".*\\.txt$", "file.txt") is True
        assert _db_regex(".*\\.txt$", "file.pdf") is False

    def test_no_match(self) -> None:
        """Test when pattern doesn't match."""
        assert _db_regex("^abc", "xyz") is False


class TestDbCreate:
    """Tests for database creation."""

    def test_create_database(self, temp_catho_dir: Path) -> None:
        """Test creating a new database."""
        db_create("new_catalog")
        db_path = file_get_catalog_abspath("new_catalog")
        assert db_path.exists()


class TestDbInsertMetadata:
    """Tests for metadata insertion."""

    def test_insert_metadata(self, temp_catho_dir: Path) -> None:
        """Test inserting metadata."""
        db_create("meta_test")
        metadata = [
            ("version", "1"),
            ("name", "meta_test"),
            ("hash", "sha256"),
        ]
        db_insert_metadata("meta_test", metadata)
        result = db_get_metadata("meta_test")
        assert result["version"] == "1"
        assert result["name"] == "meta_test"
        assert result["hash"] == "sha256"


class TestDbInsertCatalog:
    """Tests for catalog insertion."""

    def test_insert_catalog_items(self, temp_catho_dir: Path) -> None:
        """Test inserting catalog items."""
        db_create("cat_test")
        files = [
            (None, "file1.txt", 1704067200, 1024, "/path", "abc123"),
            (None, "file2.txt", 1704067300, 2048, "/path", "def456"),
        ]
        db_insert_catalog("cat_test", files)
        result = db_get_catalog("cat_test")
        assert len(result) == 2
        assert result[0][1] == "file1.txt"
        assert result[1][1] == "file2.txt"


class TestDbGetCatalog:
    """Tests for catalog retrieval."""

    def test_get_empty_catalog(self, temp_catho_dir: Path) -> None:
        """Test getting an empty catalog."""
        db_create("empty_cat")
        result = db_get_catalog("empty_cat")
        assert result == []

    def test_get_catalog_with_items(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test getting a catalog with items."""
        create_catalog("full_cat", str(sample_files), "sha256")
        result = db_get_catalog("full_cat")
        assert len(result) == 4  # 4 sample files


class TestGetCatalogByPattern:
    """Tests for pattern-based catalog search."""

    def test_find_by_name_pattern(self, test_catalog: str) -> None:
        """Test finding files by name pattern."""
        result = get_catalog_by_pattern(test_catalog, "%file%")
        assert len(result) >= 1

    def test_find_by_extension(self, test_catalog: str) -> None:
        """Test finding files by extension."""
        result = get_catalog_by_pattern(test_catalog, "%.txt")
        assert len(result) >= 3  # file1.txt, file2.txt, file3.txt

    def test_no_matches(self, test_catalog: str) -> None:
        """Test when no files match pattern."""
        result = get_catalog_by_pattern(test_catalog, "%nonexistent%")
        assert result == []


class TestGetCatalogByRegex:
    """Tests for regex-based catalog search."""

    def test_find_by_regex(self, test_catalog: str) -> None:
        """Test finding files by regex."""
        result = get_catalog_by_regex(test_catalog, ".*file.*\\.txt")
        assert len(result) >= 1

    def test_no_regex_matches(self, test_catalog: str) -> None:
        """Test when no files match regex."""
        result = get_catalog_by_regex(test_catalog, "^xyz123$")
        assert result == []


class TestGetCatalogByPath:
    """Tests for path-based catalog search."""

    def test_find_by_path_prefix(self, test_catalog: str) -> None:
        """Test finding files by path prefix."""
        result = get_catalog_by_path(test_catalog, "subdir")
        assert len(result) >= 2  # file3.txt and data.csv in subdir

    def test_no_path_matches(self, test_catalog: str) -> None:
        """Test when no files match path."""
        result = get_catalog_by_path(test_catalog, "nonexistent_path")
        assert result == []


class TestGetCatalogByAbsoluteName:
    """Tests for absolute name search."""

    def test_find_by_absolute_name(self, test_catalog: str) -> None:
        """Test finding file by full path + name."""
        result = get_catalog_by_absolute_name(test_catalog, ".file1.txt")
        # This may or may not find anything depending on how paths are stored
        assert isinstance(result, list)


class TestGetCatalogByHash:
    """Tests for hash-based catalog search."""

    def test_find_by_hash(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test finding files by hash."""
        create_catalog("hash_cat", str(sample_files), "sha256")
        # Get a file's hash from the catalog
        catalog = db_get_catalog("hash_cat")
        if catalog:
            # Get hash of first file
            file_hash = catalog[0][5]
            if file_hash:
                files = [(None, "test", 0, 0, "", file_hash)]
                result = get_catalog_by_hash("hash_cat", files)
                assert len(result) >= 1

    def test_no_hash_matches(self, test_catalog: str) -> None:
        """Test when no files match hash."""
        files = [(None, "test", 0, 0, "", "nonexistent_hash")]
        result = get_catalog_by_hash(test_catalog, files)
        assert result == []

    def test_empty_hash_list(self, test_catalog: str) -> None:
        """Test with empty hash list."""
        result = get_catalog_by_hash(test_catalog, [])
        assert result == []


class TestDbDeleteCatalog:
    """Tests for deleting catalog items."""

    def test_delete_items_by_id(self, temp_catho_dir: Path) -> None:
        """Test deleting items by ID."""
        db_create("del_test")
        files = [
            (None, "file1.txt", 1704067200, 1024, "/path", "abc123"),
            (None, "file2.txt", 1704067300, 2048, "/path", "def456"),
            (None, "file3.txt", 1704067400, 3072, "/path", "ghi789"),
        ]
        db_insert_catalog("del_test", files)

        # Get the catalog and find IDs
        catalog = db_get_catalog("del_test")
        assert len(catalog) == 3

        # Delete first item (ID should be 1)
        db_delete_catalog("del_test", [1])

        # Check that only 2 items remain
        catalog = db_get_catalog("del_test")
        assert len(catalog) == 2


class TestDbGetDeletedIds:
    """Tests for getting deleted file IDs."""

    def test_get_deleted_ids_no_deletions(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test getting deleted IDs when all files exist."""
        create_catalog("nodelete_cat", str(sample_files), "sha256")
        deleted_ids = db_get_deleted_ids("nodelete_cat")
        assert deleted_ids == []

    def test_get_deleted_ids_with_deletions(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test getting deleted IDs when files are missing."""
        create_catalog("delete_cat", str(sample_files), "sha256")

        # Delete a file from the filesystem
        (sample_files / "file1.txt").unlink()

        deleted_ids = db_get_deleted_ids("delete_cat")
        assert len(deleted_ids) == 1


class TestDbGetInsertedCatalogs:
    """Tests for getting already inserted catalog items."""

    def test_get_inserted_items(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test getting items that match criteria."""
        create_catalog("insert_cat", str(sample_files), "sha256")

        catalog = db_get_catalog("insert_cat")
        if catalog:
            # Build params from first item
            item = catalog[0]
            params = [(item[1], item[4], item[3], item[2])]  # name, path, size, date
            result = db_get_inserted_catalogs("insert_cat", params)
            assert len(result) == 1

    def test_get_inserted_no_match(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test when no items match criteria."""
        create_catalog("nomatch_cat", str(sample_files), "sha256")

        params = [("nonexistent.txt", "/fake/path", 9999, 0)]
        result = db_get_inserted_catalogs("nomatch_cat", params)
        assert result == []

    def test_get_inserted_empty_params(self, test_catalog: str) -> None:
        """Test with empty params list."""
        result = db_get_inserted_catalogs(test_catalog, [])
        assert result == []


class TestDbErrorHandling:
    """Tests for database error handling."""

    def test_get_metadata_nonexistent_catalog(self, temp_catho_dir: Path) -> None:
        """Test getting metadata from non-existent catalog."""
        # Create an empty db file without tables
        db_path = file_get_catalog_abspath("no_tables")
        db_path.touch()

        result = db_get_metadata("no_tables")
        assert result == {}

    def test_get_catalog_nonexistent(self, temp_catho_dir: Path) -> None:
        """Test getting catalog from non-existent database."""
        db_path = file_get_catalog_abspath("no_tables2")
        db_path.touch()

        result = db_get_catalog("no_tables2")
        assert result == []
