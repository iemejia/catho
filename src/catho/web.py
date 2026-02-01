"""Web UI for catho catalog viewer."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from jinja2 import BaseLoader, TemplateNotFound

from catho.db import db_get_catalog, db_get_metadata, get_catalog_by_pattern
from catho.file import file_get_catalogs
from catho.utils import sizeof_fmt


class DictLoader(BaseLoader):
    """Load templates from a dictionary."""

    def __init__(self, templates: dict[str, str]) -> None:
        self.templates = templates

    def get_source(
        self, _environment: Any, template: str
    ) -> tuple[str, str | None, Callable[[], bool]]:
        if template not in self.templates:
            raise TemplateNotFound(template)
        source = self.templates[template]
        return source, None, lambda: True


app = Flask(__name__)

# HTML Templates embedded for simplicity
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catho - File Catalog Viewer</title>
    <style>
        :root {
            --bg-color: #1a1a2e;
            --card-bg: #16213e;
            --accent: #0f3460;
            --highlight: #e94560;
            --text: #eaeaea;
            --text-muted: #a0a0a0;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-color);
            color: var(--text);
            min-height: 100vh;
        }

        .header {
            background: var(--card-bg);
            padding: 1rem 2rem;
            border-bottom: 1px solid var(--accent);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            font-size: 1.5rem;
            color: var(--highlight);
        }

        .header nav a {
            color: var(--text);
            text-decoration: none;
            margin-left: 1.5rem;
            transition: color 0.2s;
        }

        .header nav a:hover {
            color: var(--highlight);
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .search-box {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 8px;
            margin-bottom: 2rem;
        }

        .search-box input[type="text"] {
            width: 100%;
            padding: 0.75rem 1rem;
            border: 1px solid var(--accent);
            border-radius: 4px;
            background: var(--bg-color);
            color: var(--text);
            font-size: 1rem;
        }

        .search-box input[type="text"]:focus {
            outline: none;
            border-color: var(--highlight);
        }

        .catalog-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }

        .catalog-card {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1.5rem;
            border: 1px solid var(--accent);
            transition: transform 0.2s, border-color 0.2s;
        }

        .catalog-card:hover {
            transform: translateY(-2px);
            border-color: var(--highlight);
        }

        .catalog-card h3 {
            color: var(--highlight);
            margin-bottom: 0.75rem;
        }

        .catalog-card h3 a {
            color: inherit;
            text-decoration: none;
        }

        .catalog-card .meta {
            color: var(--text-muted);
            font-size: 0.875rem;
        }

        .catalog-card .meta span {
            display: block;
            margin-bottom: 0.25rem;
        }

        .file-table {
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
        }

        .file-table th,
        .file-table td {
            padding: 0.75rem 1rem;
            text-align: left;
            border-bottom: 1px solid var(--accent);
        }

        .file-table th {
            background: var(--accent);
            font-weight: 600;
            position: sticky;
            top: 0;
        }

        .file-table tr:hover {
            background: rgba(233, 69, 96, 0.1);
        }

        .file-table .size {
            text-align: right;
            font-family: monospace;
        }

        .file-table .hash {
            font-family: monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .file-table .path {
            color: var(--text-muted);
            font-size: 0.875rem;
        }

        .breadcrumb {
            margin-bottom: 1.5rem;
            color: var(--text-muted);
        }

        .breadcrumb a {
            color: var(--highlight);
            text-decoration: none;
        }

        .stats {
            display: flex;
            gap: 2rem;
            margin-bottom: 1.5rem;
            flex-wrap: wrap;
        }

        .stat {
            background: var(--card-bg);
            padding: 1rem 1.5rem;
            border-radius: 8px;
            border: 1px solid var(--accent);
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: var(--highlight);
        }

        .stat-label {
            color: var(--text-muted);
            font-size: 0.875rem;
        }

        .table-container {
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--accent);
        }

        .pagination {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-top: 1.5rem;
        }

        .pagination a, .pagination span {
            padding: 0.5rem 1rem;
            background: var(--card-bg);
            border: 1px solid var(--accent);
            border-radius: 4px;
            color: var(--text);
            text-decoration: none;
        }

        .pagination a:hover {
            border-color: var(--highlight);
        }

        .pagination .active {
            background: var(--highlight);
            border-color: var(--highlight);
        }

        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
        }

        .empty-state h2 {
            margin-bottom: 1rem;
        }

        .view-toggle {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }

        .view-toggle a {
            padding: 0.5rem 1rem;
            background: var(--card-bg);
            border: 1px solid var(--accent);
            border-radius: 4px;
            color: var(--text);
            text-decoration: none;
        }

        .view-toggle a:hover {
            border-color: var(--highlight);
        }

        .view-toggle a.active {
            background: var(--highlight);
            border-color: var(--highlight);
        }

        .tree {
            background: var(--card-bg);
            border: 1px solid var(--accent);
            border-radius: 8px;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.9rem;
            overflow-x: auto;
        }

        .tree ul {
            list-style: none;
            padding-left: 1.5rem;
        }

        .tree > ul {
            padding-left: 0;
        }

        .tree li {
            position: relative;
            padding: 0.15rem 0;
        }

        .tree .folder {
            cursor: pointer;
            color: var(--highlight);
        }

        .tree .folder::before {
            content: "📁 ";
        }

        .tree .folder.collapsed::before {
            content: "📂 ";
        }

        .tree .file::before {
            content: "📄 ";
        }

        .tree .file-info {
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-left: 0.5rem;
        }

        .tree .collapsed + ul {
            display: none;
        }
    </style>
</head>
<body>
    <header class="header">
        <h1>📁 Catho</h1>
        <nav>
            <a href="/">Home</a>
            <a href="/search">Search</a>
        </nav>
    </header>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

HOME_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="search-box">
    <form action="/search" method="get">
        <input type="text" name="q" placeholder="Search files across all catalogs..." value="{{ query or '' }}">
    </form>
</div>

{% if catalogs %}
<div class="catalog-grid">
    {% for catalog in catalogs %}
    <div class="catalog-card">
        <h3><a href="/catalog/{{ catalog.name }}">{{ catalog.name }}</a></h3>
        <div class="meta">
            <span>📦 Size: {{ catalog.size_fmt }}</span>
            <span>📅 Modified: {{ catalog.date_fmt }}</span>
        </div>
    </div>
    {% endfor %}
</div>
{% else %}
<div class="empty-state">
    <h2>No Catalogs Found</h2>
    <p>Create a catalog using: <code>catho add &lt;name&gt; &lt;path&gt;</code></p>
</div>
{% endif %}
{% endblock %}
"""

CATALOG_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="breadcrumb">
    <a href="/">Home</a> / {{ catalog_name }}
</div>

<div class="stats">
    <div class="stat">
        <div class="stat-value">{{ total_files }}</div>
        <div class="stat-label">Total Files</div>
    </div>
    <div class="stat">
        <div class="stat-value">{{ total_size }}</div>
        <div class="stat-label">Total Size</div>
    </div>
    <div class="stat">
        <div class="stat-value">{{ metadata.get('hash', 'N/A') }}</div>
        <div class="stat-label">Hash Type</div>
    </div>
    <div class="stat">
        <div class="stat-value">{{ metadata.get('path', 'N/A') }}</div>
        <div class="stat-label">Source Path</div>
    </div>
</div>

<div class="search-box">
    <form action="/catalog/{{ catalog_name }}" method="get">
        <input type="text" name="q" placeholder="Filter files in this catalog..." value="{{ query or '' }}">
        <input type="hidden" name="view" value="{{ view }}">
    </form>
</div>

<div class="view-toggle">
    <a href="?view=table{% if query %}&q={{ query }}{% endif %}" class="{% if view != 'tree' %}active{% endif %}">📋 Table</a>
    <a href="?view=tree{% if query %}&q={{ query }}{% endif %}" class="{% if view == 'tree' %}active{% endif %}">🌲 Tree</a>
</div>

{% if files %}
{% if view == 'tree' %}
<div class="tree">
    {{ tree_html|safe }}
</div>
{% else %}
<div class="table-container">
    <table class="file-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Path</th>
                <th>Size</th>
                <th>Date</th>
                <th>Hash</th>
            </tr>
        </thead>
        <tbody>
            {% for file in files %}
            <tr>
                <td>{{ file.name }}</td>
                <td class="path">{{ file.path }}</td>
                <td class="size">{{ file.size_fmt }}</td>
                <td>{{ file.date_fmt }}</td>
                <td class="hash" title="{{ file.hash }}">{{ file.hash[:16] }}...</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>

{% if total_pages > 1 %}
<div class="pagination">
    {% if page > 1 %}
    <a href="?page={{ page - 1 }}&view={{ view }}{% if query %}&q={{ query }}{% endif %}">&laquo; Prev</a>
    {% endif %}

    {% for p in range(1, total_pages + 1) %}
        {% if p == page %}
        <span class="active">{{ p }}</span>
        {% elif p <= 3 or p > total_pages - 2 or (p >= page - 1 and p <= page + 1) %}
        <a href="?page={{ p }}&view={{ view }}{% if query %}&q={{ query }}{% endif %}">{{ p }}</a>
        {% elif p == 4 or p == total_pages - 2 %}
        <span>...</span>
        {% endif %}
    {% endfor %}

    {% if page < total_pages %}
    <a href="?page={{ page + 1 }}&view={{ view }}{% if query %}&q={{ query }}{% endif %}">Next &raquo;</a>
    {% endif %}
</div>
{% endif %}
{% endif %}

{% else %}
<div class="empty-state">
    <h2>No Files Found</h2>
    <p>{% if query %}No files match your search.{% else %}This catalog is empty.{% endif %}</p>
</div>
{% endif %}
{% endblock %}
"""

SEARCH_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="breadcrumb">
    <a href="/">Home</a> / Search
</div>

<div class="search-box">
    <form action="/search" method="get">
        <input type="text" name="q" placeholder="Search files across all catalogs..." value="{{ query or '' }}" autofocus>
    </form>
</div>

{% if query %}
<div class="stats">
    <div class="stat">
        <div class="stat-value">{{ total_results }}</div>
        <div class="stat-label">Results Found</div>
    </div>
</div>
{% endif %}

{% if results %}
<div class="table-container">
    <table class="file-table">
        <thead>
            <tr>
                <th>Catalog</th>
                <th>Name</th>
                <th>Path</th>
                <th>Size</th>
                <th>Date</th>
            </tr>
        </thead>
        <tbody>
            {% for result in results %}
            <tr>
                <td><a href="/catalog/{{ result.catalog }}">{{ result.catalog }}</a></td>
                <td>{{ result.name }}</td>
                <td class="path">{{ result.path }}</td>
                <td class="size">{{ result.size_fmt }}</td>
                <td>{{ result.date_fmt }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% elif query %}
<div class="empty-state">
    <h2>No Results</h2>
    <p>No files match "{{ query }}"</p>
</div>
{% else %}
<div class="empty-state">
    <h2>Search All Catalogs</h2>
    <p>Enter a search term to find files across all your catalogs.</p>
    <p>Use * as a wildcard (e.g., *.txt)</p>
</div>
{% endif %}
{% endblock %}
"""

ERROR_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="empty-state">
    <h2>Catalog Not Found</h2>
    <p>The catalog you requested does not exist.</p>
</div>
{% endblock %}
"""

# Register templates with the app
TEMPLATES = {
    "base": BASE_TEMPLATE,
    "home": HOME_TEMPLATE,
    "catalog": CATALOG_TEMPLATE,
    "search": SEARCH_TEMPLATE,
    "error": ERROR_TEMPLATE,
}
app.jinja_loader = DictLoader(TEMPLATES)


def format_file_item(
    item: tuple[Any, ...], catalog_name: str | None = None
) -> dict[str, Any]:
    """Format a file item for display.

    Args:
        item: Tuple of (id, name, date, size, path, hash).
        catalog_name: Optional catalog name to include.

    Returns:
        Dictionary with formatted values.
    """
    file_id, name, date, size, path, hash_value = item
    result = {
        "id": file_id,
        "name": name,
        "date": date,
        "date_fmt": datetime.fromtimestamp(date).strftime("%Y-%m-%d %H:%M"),
        "size": size,
        "size_fmt": sizeof_fmt(size),
        "path": path,
        "hash": hash_value or "",
    }
    if catalog_name:
        result["catalog"] = catalog_name
    return result


def build_tree_html(files: list[dict[str, Any]]) -> str:
    """Build an HTML tree structure from a flat list of files.

    Args:
        files: List of file dictionaries with 'path' and 'name' keys.

    Returns:
        HTML string representing the tree structure.
    """
    # Build tree structure
    tree: dict[str, Any] = {}
    for file in files:
        path = file["path"]
        parts = path.strip("/").split("/") if path else []
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
        # Store file info at the leaf
        current[file["name"]] = {"__file__": file}

    def render_node(node: dict[str, Any], level: int = 0) -> str:
        """Recursively render tree nodes as HTML."""
        html_parts = []
        # Sort: folders first, then files
        folders = sorted(
            [
                k
                for k in node
                if not isinstance(node[k].get("__file__"), dict)
                or "__file__" not in node[k]
            ]
        )
        files_here = sorted(
            [
                k
                for k in node
                if isinstance(node.get(k, {}), dict) and "__file__" in node.get(k, {})
            ]
        )

        # Actually separate folders and files properly
        folders = []
        files_here = []
        for key, value in node.items():
            if isinstance(value, dict):
                if "__file__" in value and len(value) == 1:
                    files_here.append((key, value["__file__"]))
                else:
                    folders.append((key, value))

        folders.sort(key=lambda x: x[0].lower())
        files_here.sort(key=lambda x: x[0].lower())

        for folder_name, folder_content in folders:
            # Filter out __file__ for subfolders that also have files
            sub_content = {k: v for k, v in folder_content.items() if k != "__file__"}
            if sub_content:
                html_parts.append(f'<li><span class="folder">{folder_name}</span>')
                html_parts.append("<ul>")
                html_parts.append(render_node(sub_content, level + 1))
                html_parts.append("</ul></li>")

        for file_name, file_info in files_here:
            size = file_info.get("size_fmt", "")
            date = file_info.get("date_fmt", "")
            html_parts.append(
                f'<li><span class="file">{file_name}</span>'
                f'<span class="file-info">({size}, {date})</span></li>'
            )

        return "\n".join(html_parts)

    return f"<ul>{render_node(tree)}</ul>"


@app.route("/")
def home() -> str:
    """Home page showing all catalogs."""
    catalogs = file_get_catalogs()
    formatted_catalogs = [
        {
            "name": catalog["name"],
            "size": catalog["size"],
            "size_fmt": sizeof_fmt(int(catalog["size"])),
            "date": catalog["date"],
            "date_fmt": datetime.fromtimestamp(int(catalog["date"])).strftime(
                "%Y-%m-%d %H:%M"
            ),
        }
        for catalog in catalogs
    ]

    return render_template(
        "home",
        catalogs=formatted_catalogs,
    )


@app.route("/catalog/<name>")
def view_catalog(name: str) -> str:
    """View a specific catalog."""
    page = request.args.get("page", 1, type=int)
    query = request.args.get("q", "")
    view = request.args.get("view", "table")
    per_page = 100

    try:
        metadata = db_get_metadata(name)
    except Exception:
        return render_template("error")

    if query:
        # Convert * to SQL LIKE pattern
        pattern = "%" + query.replace("*", "%") + "%"
        all_files = get_catalog_by_pattern(name, pattern)
    else:
        all_files = db_get_catalog(name)

    total_files = len(all_files)
    total_size = sum(f[3] for f in all_files)  # size is at index 3
    total_pages = (total_files + per_page - 1) // per_page

    # For tree view, show all files (no pagination)
    if view == "tree":
        files = [format_file_item(f) for f in all_files]
        tree_html = build_tree_html(files)
    else:
        # Paginate for table view
        start = (page - 1) * per_page
        end = start + per_page
        files = [format_file_item(f) for f in all_files[start:end]]
        tree_html = ""

    return render_template(
        "catalog",
        catalog_name=name,
        metadata=metadata,
        files=files,
        total_files=total_files,
        total_size=sizeof_fmt(total_size),
        page=page,
        total_pages=total_pages,
        query=query,
        view=view,
        tree_html=tree_html,
    )


@app.route("/search")
def search() -> str:
    """Search across all catalogs."""
    query = request.args.get("q", "")
    results: list[dict[str, Any]] = []

    if query:
        catalogs = file_get_catalogs()
        pattern = "%" + query.replace("*", "%") + "%"

        for catalog in catalogs:
            catalog_name = str(catalog["name"])
            matches = get_catalog_by_pattern(catalog_name, pattern)
            results.extend(
                format_file_item(match, catalog_name)
                for match in matches[:100]  # Limit per catalog
            )

    return render_template(
        "search",
        query=query,
        results=results[:500],  # Total limit
        total_results=len(results),
    )


@app.route("/api/catalogs")
def api_catalogs() -> Response:
    """API endpoint to list catalogs."""
    catalogs = file_get_catalogs()
    return jsonify(catalogs)


@app.route("/api/catalog/<name>")
def api_catalog(name: str) -> Response | tuple[Response, int]:
    """API endpoint to get catalog contents."""
    try:
        metadata = db_get_metadata(name)
        files = db_get_catalog(name)
        return jsonify(
            {
                "metadata": metadata,
                "files": [format_file_item(f) for f in files],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 404


def run_server(host: str = "127.0.0.1", port: int = 8080, debug: bool = False) -> None:
    """Run the web server.

    Args:
        host: Host to bind to.
        port: Port to listen on.
        debug: Enable debug mode.
    """
    print(f"Starting Catho Web UI at http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=True)
