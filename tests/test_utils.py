"""Tests for catho utility functions."""

from pathlib import Path

from catho.utils import (
    file_hash,
    file_rm,
    file_touch_dir,
    file_touch_file,
    get_file_info,
    list_of_tuples_to_dict,
    sizeof_fmt,
)


class TestFileTouchDir:
    """Tests for file_touch_dir function."""

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Test creating a new directory."""
        new_dir = tmp_path / "new_directory"
        file_touch_dir(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_creates_nested_directories(self, tmp_path: Path) -> None:
        """Test creating nested directories."""
        nested = tmp_path / "a" / "b" / "c"
        file_touch_dir(nested)
        assert nested.exists()
        assert nested.is_dir()

    def test_existing_directory(self, tmp_path: Path) -> None:
        """Test that existing directories don't cause errors."""
        file_touch_dir(tmp_path)  # Should not raise


class TestFileTouchFile:
    """Tests for file_touch_file function."""

    def test_creates_file(self, tmp_path: Path) -> None:
        """Test creating a new file."""
        new_file = tmp_path / "new_file.txt"
        file_touch_file(new_file)
        assert new_file.exists()
        assert new_file.is_file()

    def test_updates_existing_file(self, tmp_path: Path) -> None:
        """Test touching an existing file updates mtime."""
        existing = tmp_path / "existing.txt"
        existing.write_text("content")
        file_touch_file(existing)
        # Content should be preserved
        assert existing.read_text() == "content"


class TestFileRm:
    """Tests for file_rm function."""

    def test_removes_file(self, tmp_path: Path) -> None:
        """Test removing a file."""
        test_file = tmp_path / "to_delete.txt"
        test_file.write_text("delete me")
        file_rm(test_file)
        assert not test_file.exists()

    def test_removes_empty_directory(self, tmp_path: Path) -> None:
        """Test removing an empty directory."""
        test_dir = tmp_path / "to_delete"
        test_dir.mkdir()
        file_rm(test_dir)
        assert not test_dir.exists()

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test removing a non-existent file doesn't raise."""
        nonexistent = tmp_path / "does_not_exist"
        file_rm(nonexistent)  # Should not raise


class TestGetFileInfo:
    """Tests for get_file_info function."""

    def test_returns_size_and_date(self, tmp_path: Path) -> None:
        """Test getting file info."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        size, date = get_file_info(test_file)
        assert size == 11  # "Hello World" is 11 bytes
        assert isinstance(date, int)
        assert date > 0


class TestSizeofFmt:
    """Tests for sizeof_fmt function."""

    def test_bytes(self) -> None:
        """Test formatting bytes."""
        assert sizeof_fmt(500) == "500.0 bytes"

    def test_kilobytes(self) -> None:
        """Test formatting kilobytes."""
        assert sizeof_fmt(1234) == "1.2 KB"

    def test_megabytes(self) -> None:
        """Test formatting megabytes."""
        assert sizeof_fmt(123456789) == "117.7 MB"

    def test_gigabytes(self) -> None:
        """Test formatting gigabytes."""
        assert sizeof_fmt(123456789012) == "115.0 GB"


class TestFileHash:
    """Tests for file_hash function."""

    def test_sha256_empty_file(self, tmp_path: Path) -> None:
        """Test SHA256 hash of empty file."""
        empty_file = tmp_path / "empty"
        empty_file.write_bytes(b"")
        result = file_hash(empty_file, 1048576, "sha256")
        # SHA256 of empty string
        assert (
            result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )

    def test_sha256_with_content(self, tmp_path: Path) -> None:
        """Test SHA256 hash of file with content."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World")
        result = file_hash(test_file, 1048576, "sha256")
        assert len(result) == 64  # SHA256 hex digest length

    def test_none_hash_type(self, tmp_path: Path) -> None:
        """Test that None hash type returns empty string."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        result = file_hash(test_file, 1048576, "None")
        assert result == ""


class TestListOfTuplesToDict:
    """Tests for list_of_tuples_to_dict function."""

    def test_basic_conversion(self) -> None:
        """Test basic tuple list to dict conversion."""
        tuples = [("a", "1"), ("b", "2"), ("c", "3")]
        result = list_of_tuples_to_dict(tuples)
        assert result == {"a": "1", "b": "2", "c": "3"}

    def test_empty_list(self) -> None:
        """Test empty list returns empty dict."""
        assert list_of_tuples_to_dict([]) == {}

    def test_duplicate_keys(self) -> None:
        """Test that first value wins for duplicate keys."""
        tuples = [("a", "1"), ("a", "2")]
        result = list_of_tuples_to_dict(tuples)
        assert result == {"a": "1"}
