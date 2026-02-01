"""Tests for catho file operations."""

from pathlib import Path

from catho.catalog import create_catalog
from catho.file import (
    CATHO_EXTENSION,
    CATHO_PATH,
    calc_hashes,
    file_get_catalog_abspath,
    file_get_catalogs,
    file_getfile_as_item,
    file_rm_catalog_file,
    file_select_catalogs,
    path_block_iterator,
)


class TestConstants:
    """Tests for file module constants."""

    def test_catho_path_is_home_based(self) -> None:
        """Test that CATHO_PATH is in home directory."""
        assert CATHO_PATH.is_absolute()
        assert ".catho" in str(CATHO_PATH)

    def test_catho_extension(self) -> None:
        """Test catalog file extension."""
        assert CATHO_EXTENSION == ".db"


class TestFileGetCatalogAbspath:
    """Tests for file_get_catalog_abspath function."""

    def test_returns_path_object(self) -> None:
        """Test that function returns a Path object."""
        result = file_get_catalog_abspath("test")
        assert isinstance(result, Path)

    def test_includes_extension(self) -> None:
        """Test that result includes .db extension."""
        result = file_get_catalog_abspath("test")
        assert result.suffix == ".db"

    def test_includes_catalog_name(self) -> None:
        """Test that result includes catalog name."""
        result = file_get_catalog_abspath("my_catalog")
        assert "my_catalog" in str(result)


class TestFileGetCatalogs:
    """Tests for file_get_catalogs function."""

    def test_returns_list(self, temp_catho_dir: Path) -> None:
        """Test that function returns a list."""
        result = file_get_catalogs()
        assert isinstance(result, list)

    def test_empty_when_no_catalogs(self, temp_catho_dir: Path) -> None:
        """Test empty list when no catalogs exist."""
        result = file_get_catalogs()
        assert result == []

    def test_returns_catalog_info(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test that catalog info includes expected fields."""
        create_catalog("test", str(sample_files), "sha256")
        result = file_get_catalogs()
        assert len(result) == 1
        assert "name" in result[0]
        assert "size" in result[0]
        assert "date" in result[0]
        assert result[0]["name"] == "test"


class TestFileSelectCatalogs:
    """Tests for file_select_catalogs function."""

    def test_select_all(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test selecting all catalogs when no selection provided."""
        create_catalog("cat1", str(sample_files), "sha256")
        create_catalog("cat2", str(sample_files), "sha256")
        result = file_select_catalogs()
        assert len(result) == 2
        assert "cat1" in result
        assert "cat2" in result

    def test_select_specific(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test selecting specific catalogs."""
        create_catalog("cat1", str(sample_files), "sha256")
        create_catalog("cat2", str(sample_files), "sha256")
        result = file_select_catalogs(["cat1"])
        assert result == ["cat1"]

    def test_select_nonexistent_catalogs(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test selecting non-existent catalogs returns empty."""
        create_catalog("cat1", str(sample_files), "sha256")
        result = file_select_catalogs(["nonexistent"])
        assert result == []

    def test_select_mixed(self, temp_catho_dir: Path, sample_files: Path) -> None:
        """Test selecting mix of existent and non-existent catalogs."""
        create_catalog("cat1", str(sample_files), "sha256")
        result = file_select_catalogs(["cat1", "nonexistent"])
        assert result == ["cat1"]


class TestPathBlockIterator:
    """Tests for path_block_iterator function."""

    def test_yields_file_items(self, sample_files: Path) -> None:
        """Test that iterator yields FileItem tuples."""
        batches = list(path_block_iterator(str(sample_files), 100))
        assert len(batches) >= 1
        for batch in batches:
            for item in batch:
                assert len(item) == 6  # FileItem has 6 elements
                assert item[0] is None  # id is None initially
                assert isinstance(item[1], str)  # name
                assert isinstance(item[2], int)  # date
                assert isinstance(item[3], int)  # size
                assert isinstance(item[4], str)  # path
                assert item[5] is None  # hash is None initially

    def test_batch_size(self, sample_files: Path) -> None:
        """Test that batch size is respected."""
        batches = list(path_block_iterator(str(sample_files), 2))
        for batch in batches[:-1]:  # All but last
            assert len(batch) <= 2

    def test_path_as_pathlib(self, sample_files: Path) -> None:
        """Test that function accepts Path objects."""
        batches = list(path_block_iterator(sample_files, 100))
        assert len(batches) >= 1

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Test with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        batches = list(path_block_iterator(str(empty_dir), 100))
        assert batches == []


class TestCalcHashes:
    """Tests for calc_hashes function."""

    def test_calculates_sha256(self, sample_files: Path) -> None:
        """Test that SHA256 hashes are calculated."""
        files = [
            (None, "file1.txt", 1704067200, 11, ".", None),  # "Hello World" = 11 bytes
        ]
        result = calc_hashes(str(sample_files), files, 1048576, "sha256")
        assert len(result) == 1
        assert result[0][5] is not None
        assert len(result[0][5]) == 64  # SHA256 hex length

    def test_calculates_none_hash(self, sample_files: Path) -> None:
        """Test that None hash type returns empty string."""
        files = [
            (None, "file1.txt", 1704067200, 11, ".", None),
        ]
        result = calc_hashes(str(sample_files), files, 1048576, "None")
        assert len(result) == 1
        assert result[0][5] == ""

    def test_skips_already_hashed(self, sample_files: Path) -> None:
        """Test that files with existing hash are skipped."""
        files = [
            (None, "file1.txt", 1704067200, 11, ".", "existing_hash"),
        ]
        result = calc_hashes(str(sample_files), files, 1048576, "sha256")
        # Files with existing hash are skipped
        assert len(result) == 0

    def test_handles_missing_file(self, sample_files: Path) -> None:
        """Test handling of missing files."""
        files = [
            (None, "nonexistent.txt", 1704067200, 100, ".", None),
        ]
        result = calc_hashes(str(sample_files), files, 1048576, "sha256")
        # Missing files are not included in result
        assert len(result) == 0


class TestFileRmCatalogFile:
    """Tests for file_rm_catalog_file function."""

    def test_rm_existing_catalog(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test removing an existing catalog."""
        create_catalog("to_delete", str(sample_files), "sha256")
        db_path = temp_catho_dir / "to_delete.db"
        assert db_path.exists()

        file_rm_catalog_file(["to_delete"])
        assert not db_path.exists()

    def test_rm_nonexistent_catalog(self, temp_catho_dir: Path) -> None:
        """Test removing a non-existent catalog doesn't raise."""
        # Should not raise an exception
        file_rm_catalog_file(["nonexistent"])

    def test_rm_multiple_catalogs(
        self, temp_catho_dir: Path, sample_files: Path
    ) -> None:
        """Test removing multiple catalogs at once."""
        create_catalog("cat1", str(sample_files), "sha256")
        create_catalog("cat2", str(sample_files), "sha256")

        file_rm_catalog_file(["cat1", "cat2"])

        assert not (temp_catho_dir / "cat1.db").exists()
        assert not (temp_catho_dir / "cat2.db").exists()


class TestFileGetfileAsItem:
    """Tests for file_getfile_as_item function."""

    def test_returns_file_item(self, sample_files: Path) -> None:
        """Test that function returns a FileItem tuple."""
        file_path = sample_files / "file1.txt"
        result = file_getfile_as_item(str(file_path), 1048576, "sha256")

        assert len(result) == 6
        assert result[0] is None  # id
        assert str(file_path) in result[1]  # name
        assert isinstance(result[2], int)  # date
        assert result[3] == 11  # size ("Hello World")
        assert result[4] == ""  # path (default)
        assert len(result[5]) == 64  # sha256 hash

    def test_with_custom_path(self, sample_files: Path) -> None:
        """Test with custom path parameter."""
        file_path = sample_files / "file1.txt"
        result = file_getfile_as_item(str(file_path), 1048576, "sha256", "/custom/path")
        assert result[4] == "/custom/path"

    def test_with_none_hash(self, sample_files: Path) -> None:
        """Test with None hash type."""
        file_path = sample_files / "file1.txt"
        result = file_getfile_as_item(str(file_path), 1048576, "None")
        assert result[5] == ""

    def test_accepts_path_object(self, sample_files: Path) -> None:
        """Test that function accepts Path objects."""
        file_path = sample_files / "file1.txt"
        result = file_getfile_as_item(file_path, 1048576, "sha256")
        assert result[5] is not None


class TestPathBlockIteratorEdgeCases:
    """Edge case tests for path_block_iterator."""

    def test_handles_special_characters(self, tmp_path: Path) -> None:
        """Test handling files with special characters in names."""
        special_file = tmp_path / "file with spaces.txt"
        special_file.write_text("content")

        batches = list(path_block_iterator(str(tmp_path), 100))
        assert len(batches) == 1
        assert batches[0][0][1] == "file with spaces.txt"

    def test_deep_nesting(self, tmp_path: Path) -> None:
        """Test deeply nested directory structure."""
        deep_path = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep_path.mkdir(parents=True)
        (deep_path / "deep_file.txt").write_text("deep content")

        batches = list(path_block_iterator(str(tmp_path), 100))
        all_files = [f for batch in batches for f in batch]
        assert len(all_files) == 1
        assert all_files[0][1] == "deep_file.txt"
        assert "a/b/c/d/e" in all_files[0][4]
