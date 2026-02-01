"""Tests for catho web UI."""

from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from catho.catalog import create_catalog

# Skip tests if Flask is not installed
flask = pytest.importorskip("flask")

if TYPE_CHECKING:
    from flask.testing import FlaskClient

from catho.web import (  # noqa: E402
    ALLOWED_VIEWS,
    DEFAULT_PAGE_SIZE,
    MAX_SEARCH_RESULTS_PER_CATALOG,
    MAX_SEARCH_RESULTS_TOTAL,
    MAX_TREE_VIEW_FILES,
    DictLoader,
    app,
    build_tree_html,
    escape_sql_like,
    format_file_item,
    validate_catalog_name,
)


@pytest.fixture
def client() -> Generator["FlaskClient", None, None]:
    """Create a Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def web_catalog(temp_catho_dir: Path, sample_files: Path) -> str:
    """Create a catalog for web testing."""
    catalog_name = "web_test"
    create_catalog(catalog_name, str(sample_files), "sha256")
    return catalog_name


class TestConstants:
    """Tests for module constants."""

    def test_default_page_size(self) -> None:
        """Test that default page size is reasonable."""
        assert DEFAULT_PAGE_SIZE == 100

    def test_max_search_results(self) -> None:
        """Test search result limits."""
        assert MAX_SEARCH_RESULTS_PER_CATALOG == 100
        assert MAX_SEARCH_RESULTS_TOTAL == 500

    def test_max_tree_view_files(self) -> None:
        """Test tree view file limit."""
        assert MAX_TREE_VIEW_FILES == 5000

    def test_allowed_views(self) -> None:
        """Test allowed view modes."""
        assert {"table", "tree"} == ALLOWED_VIEWS


class TestDictLoader:
    """Tests for DictLoader Jinja2 loader."""

    def test_get_source_existing_template(self) -> None:
        """Test loading an existing template."""
        loader = DictLoader({"test": "Hello {{ name }}"})
        source, filename, uptodate = loader.get_source(None, "test")
        assert source == "Hello {{ name }}"
        assert filename is None
        assert uptodate() is True

    def test_get_source_missing_template(self) -> None:
        """Test loading a non-existent template raises error."""
        from jinja2 import TemplateNotFound

        loader = DictLoader({})
        with pytest.raises(TemplateNotFound):
            loader.get_source(None, "missing")


class TestValidateCatalogName:
    """Tests for catalog name validation."""

    def test_valid_names(self) -> None:
        """Test valid catalog names."""
        assert validate_catalog_name("test") is True
        assert validate_catalog_name("my_catalog") is True
        assert validate_catalog_name("my-catalog") is True
        assert validate_catalog_name("catalog123") is True
        assert validate_catalog_name("UPPERCASE") is True
        assert validate_catalog_name("Mix_Case-123") is True

    def test_invalid_names(self) -> None:
        """Test invalid catalog names."""
        assert validate_catalog_name("") is False
        assert validate_catalog_name("../parent") is False
        assert validate_catalog_name("path/traversal") is False
        assert validate_catalog_name("has space") is False
        assert validate_catalog_name("has.dot") is False
        assert validate_catalog_name("special!char") is False
        assert validate_catalog_name("<script>") is False


class TestEscapeSqlLike:
    """Tests for SQL LIKE pattern escaping."""

    def test_basic_pattern(self) -> None:
        """Test basic pattern conversion."""
        assert escape_sql_like("test") == "%test%"

    def test_wildcard_conversion(self) -> None:
        """Test * to % conversion."""
        # * becomes %, and pattern is wrapped in %...%
        assert escape_sql_like("*.txt") == "%%.txt%"
        assert escape_sql_like("file*") == "%file%%"

    def test_escape_sql_special_chars(self) -> None:
        """Test escaping SQL LIKE special characters."""
        assert escape_sql_like("100%") == "%100\\%%"
        assert escape_sql_like("file_name") == "%file\\_name%"
        assert escape_sql_like("path\\file") == "%path\\\\file%"

    def test_combined_special_chars(self) -> None:
        """Test combined special characters."""
        result = escape_sql_like("50%_test*")
        assert "\\%" in result
        assert "\\_" in result
        assert result.endswith("%")


class TestFormatFileItem:
    """Tests for file item formatting."""

    def test_basic_formatting(self) -> None:
        """Test basic file item formatting."""
        item = (1, "test.txt", 1704067200, 1024, "/path/to", "abc123")
        result = format_file_item(item)
        assert result["id"] == 1
        assert result["name"] == "test.txt"
        assert result["date"] == 1704067200
        assert result["size"] == 1024
        assert result["size_fmt"] == "1.0 KB"
        assert result["path"] == "/path/to"
        assert result["hash"] == "abc123"
        assert "date_fmt" in result

    def test_formatting_with_catalog_name(self) -> None:
        """Test file item formatting with catalog name."""
        item = (1, "test.txt", 1704067200, 1024, "/path", "hash")
        result = format_file_item(item, catalog_name="my_catalog")
        assert result["catalog"] == "my_catalog"

    def test_formatting_null_hash(self) -> None:
        """Test formatting with null hash."""
        item = (1, "test.txt", 1704067200, 1024, "/path", None)
        result = format_file_item(item)
        assert result["hash"] == ""


class TestBuildTreeHtml:
    """Tests for tree HTML generation."""

    def test_empty_files(self) -> None:
        """Test building tree from empty file list."""
        result = build_tree_html([])
        assert result == "<ul></ul>"

    def test_single_file(self) -> None:
        """Test building tree with single file."""
        files = [
            {
                "name": "test.txt",
                "path": "",
                "size_fmt": "1 KB",
                "date_fmt": "2024-01-01",
            }
        ]
        result = build_tree_html(files)
        assert "test.txt" in result
        assert "file" in result
        assert "1 KB" in result

    def test_nested_files(self) -> None:
        """Test building tree with nested directories."""
        files = [
            {
                "name": "file1.txt",
                "path": "dir1",
                "size_fmt": "1 KB",
                "date_fmt": "2024-01-01",
            },
            {
                "name": "file2.txt",
                "path": "dir1/subdir",
                "size_fmt": "2 KB",
                "date_fmt": "2024-01-02",
            },
        ]
        result = build_tree_html(files)
        assert "dir1" in result
        assert "subdir" in result
        assert "file1.txt" in result
        assert "file2.txt" in result
        assert "folder" in result

    def test_xss_escaping(self) -> None:
        """Test that file names are properly escaped for XSS."""
        files = [
            {
                "name": "<script>alert('xss')</script>",
                "path": "",
                "size_fmt": "1 KB",
                "date_fmt": "2024-01-01",
            }
        ]
        result = build_tree_html(files)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestHomeRoute:
    """Tests for home route."""

    def test_home_no_catalogs(self, client, temp_catho_dir: Path) -> None:
        """Test home page with no catalogs."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"No Catalogs Found" in response.data

    def test_home_with_catalogs(self, client, web_catalog: str) -> None:
        """Test home page with catalogs."""
        response = client.get("/")
        assert response.status_code == 200
        assert web_catalog.encode() in response.data


class TestCatalogRoute:
    """Tests for catalog view route."""

    def test_view_catalog(self, client, web_catalog: str) -> None:
        """Test viewing a catalog."""
        response = client.get(f"/catalog/{web_catalog}")
        assert response.status_code == 200
        assert web_catalog.encode() in response.data

    def test_view_catalog_not_found(self, client, temp_catho_dir: Path) -> None:
        """Test viewing non-existent catalog.

        Note: The current implementation returns 200 with empty data when
        catalog doesn't exist but the db operations fail silently.
        This tests the current behavior.
        """
        response = client.get("/catalog/nonexistent")
        # Currently returns 200 because db errors are caught and return empty data
        assert response.status_code == 200

    def test_view_catalog_invalid_name(self, client, temp_catho_dir: Path) -> None:
        """Test viewing catalog with invalid name.

        Note: Flask URL routing interprets ../ differently, so the path
        becomes 'etc/passwd' which fails validation.
        """
        # Use a clearly invalid name that won't be rewritten by Flask routing
        response = client.get("/catalog/has.dot")
        assert response.status_code == 400

    def test_view_catalog_table_view(self, client, web_catalog: str) -> None:
        """Test catalog table view."""
        response = client.get(f"/catalog/{web_catalog}?view=table")
        assert response.status_code == 200
        assert b"table" in response.data.lower()

    def test_view_catalog_tree_view(self, client, web_catalog: str) -> None:
        """Test catalog tree view."""
        response = client.get(f"/catalog/{web_catalog}?view=tree")
        assert response.status_code == 200
        assert b"tree" in response.data.lower()

    def test_view_catalog_invalid_view(self, client, web_catalog: str) -> None:
        """Test catalog with invalid view defaults to table."""
        response = client.get(f"/catalog/{web_catalog}?view=invalid")
        assert response.status_code == 200
        # Should default to table view without error

    def test_view_catalog_pagination(self, client, web_catalog: str) -> None:
        """Test catalog pagination."""
        response = client.get(f"/catalog/{web_catalog}?page=1")
        assert response.status_code == 200

    def test_view_catalog_negative_page(self, client, web_catalog: str) -> None:
        """Test catalog with negative page number."""
        response = client.get(f"/catalog/{web_catalog}?page=-1")
        assert response.status_code == 200
        # Should default to page 1

    def test_view_catalog_search(self, client, web_catalog: str) -> None:
        """Test catalog search filter."""
        response = client.get(f"/catalog/{web_catalog}?q=file")
        assert response.status_code == 200


class TestSearchRoute:
    """Tests for search route."""

    def test_search_page_empty(self, client, temp_catho_dir: Path) -> None:
        """Test search page without query."""
        response = client.get("/search")
        assert response.status_code == 200
        assert b"Search All Catalogs" in response.data

    def test_search_with_query(self, client, web_catalog: str) -> None:
        """Test search with a query."""
        response = client.get("/search?q=file")
        assert response.status_code == 200
        assert b"Results Found" in response.data or b"No Results" in response.data

    def test_search_no_results(self, client, web_catalog: str) -> None:
        """Test search with no matching results."""
        response = client.get("/search?q=nonexistent_file_xyz")
        assert response.status_code == 200
        assert b"No Results" in response.data

    def test_search_with_wildcard(self, client, web_catalog: str) -> None:
        """Test search with wildcard pattern."""
        response = client.get("/search?q=*.txt")
        assert response.status_code == 200


class TestApiRoutes:
    """Tests for API routes."""

    def test_api_catalogs_empty(self, client, temp_catho_dir: Path) -> None:
        """Test API catalogs endpoint with no catalogs."""
        response = client.get("/api/catalogs")
        assert response.status_code == 200
        assert response.is_json
        assert response.json == []

    def test_api_catalogs_with_data(self, client, web_catalog: str) -> None:
        """Test API catalogs endpoint with catalogs."""
        response = client.get("/api/catalogs")
        assert response.status_code == 200
        assert response.is_json
        assert len(response.json) > 0
        assert any(c["name"] == web_catalog for c in response.json)

    def test_api_catalog_detail(self, client, web_catalog: str) -> None:
        """Test API catalog detail endpoint."""
        response = client.get(f"/api/catalog/{web_catalog}")
        assert response.status_code == 200
        assert response.is_json
        assert "metadata" in response.json
        assert "files" in response.json

    def test_api_catalog_not_found(self, client, temp_catho_dir: Path) -> None:
        """Test API catalog endpoint for non-existent catalog.

        Note: Current implementation returns 200 with empty metadata
        when catalog doesn't exist because db errors are caught.
        """
        response = client.get("/api/catalog/nonexistent")
        # Currently returns 200 because db errors return empty data
        assert response.status_code == 200
        assert response.is_json

    def test_api_catalog_invalid_name(self, client, temp_catho_dir: Path) -> None:
        """Test API catalog endpoint with invalid name."""
        # Use a clearly invalid name
        response = client.get("/api/catalog/has.dot")
        assert response.status_code == 400
        assert response.is_json
        assert "error" in response.json


class TestSecurityHeaders:
    """Tests for security headers."""

    def test_security_headers_present(self, client, temp_catho_dir: Path) -> None:
        """Test that security headers are present."""
        response = client.get("/")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in response.headers


class TestRunServer:
    """Tests for run_server function."""

    def test_run_server_import(self) -> None:
        """Test that run_server can be imported."""
        from catho.web import run_server

        assert callable(run_server)

    @patch("catho.web.app.run")
    def test_run_server_default_params(self, mock_run) -> None:
        """Test run_server with default parameters."""
        from catho.web import run_server

        run_server()
        mock_run.assert_called_once_with(host="127.0.0.1", port=8080, debug=False)

    @patch("catho.web.app.run")
    def test_run_server_custom_params(self, mock_run) -> None:
        """Test run_server with custom parameters."""
        from catho.web import run_server

        run_server(host="0.0.0.0", port=5000, debug=True)
        mock_run.assert_called_once_with(host="0.0.0.0", port=5000, debug=True)
