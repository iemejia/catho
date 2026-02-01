"""Tests for catho CLI."""

from pathlib import Path

import pytest

from catho.cli import create_parser, main


class TestCreateParser:
    """Tests for CLI parser creation."""

    def test_parser_creation(self) -> None:
        """Test that parser is created successfully."""
        parser = create_parser()
        assert parser is not None

    def test_version_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test --version flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])
        assert exc_info.value.code == 0

    def test_help_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test -h flag."""
        with pytest.raises(SystemExit) as exc_info:
            main(["-h"])
        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert "catho" in captured.out.lower()


class TestAddCommand:
    """Tests for the add command."""

    def test_add_catalog(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test adding a catalog via CLI."""
        result = main(["add", "test", str(sample_files)])
        assert result == 0
        assert (temp_catho_dir / "test.db").exists()

    def test_add_with_force(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test adding with --force flag."""
        main(["add", "test", str(sample_files)])
        result = main(["add", "-f", "test", str(sample_files)])
        assert result == 0

    def test_add_invalid_hash_type(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test adding with invalid hash type."""
        result = main(["add", "-H", "invalid", "test", str(sample_files)])
        assert result == 3


class TestLsCommand:
    """Tests for the ls command."""

    def test_ls_empty(self, temp_catho_dir: Path) -> None:
        """Test listing with no catalogs."""
        result = main(["ls"])
        assert result == 0

    def test_ls_with_catalogs(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test listing catalogs."""
        main(["add", "test1", str(sample_files)])
        main(["add", "test2", str(sample_files)])
        result = main(["ls"])
        assert result == 0


class TestRmCommand:
    """Tests for the rm command."""

    def test_rm_catalog(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test removing a catalog."""
        main(["add", "test", str(sample_files)])
        assert (temp_catho_dir / "test.db").exists()
        result = main(["rm", "test"])
        assert result == 0
        assert not (temp_catho_dir / "test.db").exists()


class TestFindCommand:
    """Tests for the find command."""

    def test_find_file(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test finding a file."""
        main(["add", "test", str(sample_files)])
        result = main(["find", "file1.txt"])
        assert result == 0

    def test_find_with_pattern(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test finding with wildcard pattern."""
        main(["add", "test", str(sample_files)])
        result = main(["find", "*.txt"])
        assert result == 0
