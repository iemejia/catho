"""Tests for catho CLI."""

import tempfile
from pathlib import Path
from unittest.mock import patch

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

    def test_find_in_specific_catalog(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test finding in a specific catalog."""
        main(["add", "test", str(sample_files)])
        result = main(["find", "file1.txt", "test"])
        assert result == 0


class TestScanCommand:
    """Tests for the scan command."""

    def test_scan_file(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test scanning a file against catalogs."""
        main(["add", "test", str(sample_files)])
        file_path = str(sample_files / "file1.txt")
        result = main(["scan", file_path])
        assert result == 0

    def test_scan_nonexistent_file(
        self,
        temp_catho_dir: Path,
    ) -> None:
        """Test scanning a non-existent file."""
        result = main(["scan", "/nonexistent/path/file.txt"])
        assert result == 0  # Returns 0 even if file doesn't exist


class TestAddContinue:
    """Tests for the add --continue flag."""

    def test_add_continue(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test adding with --continue flag to update catalog."""
        main(["add", "test", str(sample_files)])
        # Add a new file
        (sample_files / "new_file.txt").write_text("new content")
        result = main(["add", "-c", "test", str(sample_files)])
        assert result == 0


class TestLsWithNames:
    """Tests for ls command with catalog names."""

    def test_ls_specific_catalog(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test listing a specific catalog."""
        main(["add", "test", str(sample_files)])
        result = main(["ls", "test"])
        assert result == 0


class TestVerboseFlag:
    """Tests for --verbose flag."""

    def test_verbose_mode(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test verbose mode increases logging."""
        result = main(["-v", "add", "test", str(sample_files)])
        assert result == 0


class TestSilentFlag:
    """Tests for --silent flag."""

    def test_silent_mode(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test silent mode suppresses logging."""
        result = main(["-s", "add", "test", str(sample_files)])
        assert result == 0


class TestCreateLogFlag:
    """Tests for --create-log flag."""

    def test_create_log(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test creating a log file."""
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            log_path = f.name

        try:
            result = main(["-l", log_path, "add", "test", str(sample_files)])
            assert result == 0
            # Log file should exist and have content
            assert Path(log_path).exists()
        finally:
            Path(log_path).unlink(missing_ok=True)


class TestHelpCommand:
    """Tests for help command."""

    def test_help_for_add(self) -> None:
        """Test help command for add subcommand."""
        result = main(["help", "add"])
        assert result == 0

    def test_help_for_ls(self) -> None:
        """Test help command for ls subcommand."""
        result = main(["help", "ls"])
        assert result == 0

    def test_help_for_find(self) -> None:
        """Test help command for find subcommand."""
        result = main(["help", "find"])
        assert result == 0


class TestWebCommand:
    """Tests for web command."""

    def test_web_command(self, temp_catho_dir: Path) -> None:
        """Test web command starts the server."""
        with patch("catho.web.run_server") as mock_run:
            result = main(["web"])
            assert result == 0
            mock_run.assert_called_once()

    def test_web_with_custom_port(self, temp_catho_dir: Path) -> None:
        """Test web command with custom port."""
        with patch("catho.web.run_server") as mock_run:
            result = main(["web", "-p", "5000"])
            assert result == 0
            mock_run.assert_called_once_with(host="127.0.0.1", port=5000, debug=False)

    def test_web_with_custom_host(self, temp_catho_dir: Path) -> None:
        """Test web command with custom host."""
        with patch("catho.web.run_server") as mock_run:
            result = main(["web", "--host", "0.0.0.0"])
            assert result == 0
            mock_run.assert_called_once_with(host="0.0.0.0", port=8080, debug=False)

    def test_web_with_debug(self, temp_catho_dir: Path) -> None:
        """Test web command with debug mode."""
        with patch("catho.web.run_server") as mock_run:
            result = main(["web", "--debug"])
            assert result == 0
            mock_run.assert_called_once_with(host="127.0.0.1", port=8080, debug=True)


class TestNoCommand:
    """Tests for running without a command."""

    def test_no_command_shows_help(
        self,
        temp_catho_dir: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that running without a command shows help."""
        result = main([])
        assert result == 1
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "catho" in captured.out.lower()


class TestAddWithNoneHash:
    """Tests for add command with None hash type."""

    def test_add_with_none_hash(
        self,
        temp_catho_dir: Path,
        sample_files: Path,
    ) -> None:
        """Test adding catalog with None hash type."""
        result = main(["add", "-H", "None", "test", str(sample_files)])
        assert result == 0
        assert (temp_catho_dir / "test.db").exists()
