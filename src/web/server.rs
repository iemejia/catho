//! Web server implementation using Axum.

use axum::{
    extract::{Path, Query},
    http::{header, StatusCode},
    response::{Html, IntoResponse, Json, Response},
    routing::get,
    Router,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tower_http::set_header::SetResponseHeaderLayer;

use crate::catalog::{export_catalog, find_in_catalogs, list_catalogs};
use crate::db::{db_get_catalog, db_get_metadata};
use crate::utils::{sizeof_fmt, truncate_hash};

/// Application state.
#[derive(Clone)]
pub struct AppState {
    // Currently stateless, but can hold shared state
}

/// Query parameters for catalog view.
#[derive(Debug, Deserialize)]
pub struct CatalogQuery {
    #[serde(default = "default_page")]
    page: usize,
    #[serde(default)]
    q: String,
    #[serde(default = "default_view")]
    view: String,
}

fn default_page() -> usize {
    1
}

fn default_view() -> String {
    "table".to_string()
}

/// Query parameters for search.
#[derive(Debug, Deserialize)]
pub struct SearchQuery {
    #[serde(default)]
    q: String,
}

/// API response for catalog list.
#[derive(Serialize)]
pub struct CatalogListResponse {
    catalogs: Vec<CatalogListItem>,
}

#[derive(Serialize)]
pub struct CatalogListItem {
    name: String,
    size: i64,
    size_fmt: String,
    date: i64,
}

/// API response for catalog detail.
#[derive(Serialize)]
pub struct CatalogDetailResponse {
    metadata: CatalogMetadataResponse,
    files: Vec<FileResponse>,
    total_files: usize,
    total_size: i64,
    total_size_fmt: String,
}

#[derive(Serialize)]
pub struct CatalogMetadataResponse {
    name: String,
    path: String,
    hash: String,
    createdate: i64,
    lastmodifdate: i64,
}

#[derive(Serialize)]
pub struct FileResponse {
    id: i64,
    name: String,
    path: String,
    size: i64,
    size_fmt: String,
    date: i64,
    hash: Option<String>,
}

/// Constants.
const DEFAULT_PAGE_SIZE: usize = 100;
const MAX_SEARCH_RESULTS_PER_CATALOG: usize = 100;
const MAX_TREE_VIEW_FILES: usize = 5000;

/// Catalog name validation regex.
fn is_valid_catalog_name(name: &str) -> bool {
    name.chars()
        .all(|c| c.is_alphanumeric() || c == '_' || c == '-')
}

/// Run the web server.
pub async fn run_server(host: &str, port: u16) -> Result<(), Box<dyn std::error::Error>> {
    let state = Arc::new(AppState {});

    let app = Router::new()
        // HTML routes
        .route("/", get(index_handler))
        .route("/catalog/{name}", get(catalog_handler))
        .route("/search", get(search_handler))
        // API routes
        .route("/api/catalogs", get(api_catalogs))
        .route("/api/catalog/{name}", get(api_catalog))
        // Security headers
        .layer(SetResponseHeaderLayer::if_not_present(
            header::X_CONTENT_TYPE_OPTIONS,
            header::HeaderValue::from_static("nosniff"),
        ))
        .layer(SetResponseHeaderLayer::if_not_present(
            header::X_FRAME_OPTIONS,
            header::HeaderValue::from_static("DENY"),
        ))
        .with_state(state);

    let addr = format!("{}:{}", host, port);
    tracing::info!("Starting web server at http://{}", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Index page handler.
async fn index_handler() -> Html<String> {
    let catalogs = list_catalogs().unwrap_or_default();

    let catalog_cards: String = if catalogs.is_empty() {
        "<p class=\"empty\">No catalogs available. Create one using: <code>catho add &lt;name&gt; &lt;path&gt;</code></p>".to_string()
    } else {
        catalogs
            .iter()
            .map(|c| {
                format!(
                    r#"<a href="/catalog/{}" class="catalog-card">
                        <h3>{}</h3>
                        <span class="size">{}</span>
                    </a>"#,
                    html_escape(&c.name),
                    html_escape(&c.name),
                    sizeof_fmt(c.size)
                )
            })
            .collect::<Vec<_>>()
            .join("\n")
    };

    Html(format!(
        r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Catho - File Catalog Manager</title>
    {CSS}
</head>
<body>
    <div class="container">
        <header>
            <h1>Catho</h1>
            <p>File Catalog Manager</p>
        </header>
        <nav>
            <a href="/" class="active">Catalogs</a>
            <a href="/search">Search</a>
        </nav>
        <main>
            <h2>Catalogs</h2>
            <div class="catalog-grid">
                {catalog_cards}
            </div>
        </main>
    </div>
</body>
</html>"#,
        CSS = CSS_STYLES,
        catalog_cards = catalog_cards
    ))
}

/// Catalog view handler.
async fn catalog_handler(Path(name): Path<String>, Query(params): Query<CatalogQuery>) -> Response {
    if !is_valid_catalog_name(&name) {
        return (StatusCode::BAD_REQUEST, "Invalid catalog name").into_response();
    }

    let metadata = match db_get_metadata(&name) {
        Ok(m) => m,
        Err(_) => return (StatusCode::NOT_FOUND, "Catalog not found").into_response(),
    };

    let all_files = match db_get_catalog(&name) {
        Ok(f) => f,
        Err(_) => {
            return (StatusCode::INTERNAL_SERVER_ERROR, "Failed to load catalog").into_response();
        }
    };

    // Filter files if search query provided
    let filtered_files: Vec<_> = if params.q.is_empty() {
        all_files.clone()
    } else {
        let pattern = params.q.to_lowercase();
        all_files
            .iter()
            .filter(|f| {
                f.name.to_lowercase().contains(&pattern) || f.path.to_lowercase().contains(&pattern)
            })
            .cloned()
            .collect()
    };

    let total_files = filtered_files.len();
    let total_size: i64 = filtered_files.iter().map(|f| f.size).sum();

    let view = if params.view == "tree" {
        "tree"
    } else {
        "table"
    };

    let content = if view == "tree" {
        build_tree_html(&all_files, &params.q)
    } else {
        build_table_html(&filtered_files, params.page, &name, &params.q)
    };

    let table_active = if view == "table" { "active" } else { "" };
    let tree_active = if view == "tree" { "active" } else { "" };

    Html(format!(
        r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{name} - Catho</title>
    {CSS}
</head>
<body>
    <div class="container">
        <header>
            <h1>Catho</h1>
            <p>File Catalog Manager</p>
        </header>
        <nav>
            <a href="/">Catalogs</a>
            <a href="/search">Search</a>
        </nav>
        <main>
            <h2>{name}</h2>
            <div class="catalog-info">
                <span>Path: {path}</span>
                <span>Files: {total_files}</span>
                <span>Size: {total_size}</span>
                <span>Hash: {hash}</span>
            </div>
            <div class="controls">
                <form method="get" class="search-form">
                    <input type="text" name="q" value="{query}" placeholder="Filter files...">
                    <input type="hidden" name="view" value="{view}">
                    <button type="submit">Filter</button>
                </form>
                <div class="view-toggle">
                    <a href="?view=table&q={query}" class="{table_active}">Table</a>
                    <a href="?view=tree&q={query}" class="{tree_active}">Tree</a>
                </div>
            </div>
            {content}
        </main>
    </div>
</body>
</html>"#,
        CSS = CSS_STYLES,
        name = html_escape(&name),
        path = html_escape(&metadata.fullpath),
        total_files = total_files,
        total_size = sizeof_fmt(total_size),
        hash = metadata.hash,
        query = html_escape(&params.q),
        view = view,
        table_active = table_active,
        tree_active = tree_active,
        content = content
    ))
    .into_response()
}

/// Build table HTML for file listing.
fn build_table_html(
    files: &[crate::file::FileItem],
    page: usize,
    _catalog: &str,
    query: &str,
) -> String {
    let total_pages = files.len().div_ceil(DEFAULT_PAGE_SIZE);
    let page = page.max(1).min(total_pages.max(1));
    let start = (page - 1) * DEFAULT_PAGE_SIZE;
    let end = (start + DEFAULT_PAGE_SIZE).min(files.len());
    let page_files = &files[start..end];

    let rows: String = page_files
        .iter()
        .map(|f| {
            let hash_preview = truncate_hash(f.hash.as_deref(), 16);
            format!(
                r#"<tr>
                    <td>{}</td>
                    <td>{}</td>
                    <td class="size">{}</td>
                    <td>{}</td>
                </tr>"#,
                html_escape(&f.name),
                html_escape(&f.path),
                sizeof_fmt(f.size),
                hash_preview
            )
        })
        .collect();

    let pagination = if total_pages > 1 {
        let mut links = Vec::new();
        if page > 1 {
            links.push(format!(
                r#"<a href="?page={}&q={}&view=table">&laquo; Prev</a>"#,
                page - 1,
                html_escape(query)
            ));
        }
        links.push(format!("Page {} of {}", page, total_pages));
        if page < total_pages {
            links.push(format!(
                r#"<a href="?page={}&q={}&view=table">Next &raquo;</a>"#,
                page + 1,
                html_escape(query)
            ));
        }
        format!(r#"<div class="pagination">{}</div>"#, links.join(" | "))
    } else {
        String::new()
    };

    format!(
        r#"<table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Path</th>
                    <th>Size</th>
                    <th>Hash</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        {pagination}"#,
        rows = rows,
        pagination = pagination
    )
}

/// A node in the file tree.
#[derive(Default)]
struct TreeNode<'a> {
    /// Files directly in this directory.
    files: Vec<&'a crate::file::FileItem>,
    /// Subdirectories.
    children: HashMap<String, TreeNode<'a>>,
}

impl<'a> TreeNode<'a> {
    /// Count total files in this node and all children.
    fn total_files(&self) -> usize {
        self.files.len()
            + self
                .children
                .values()
                .map(|c| c.total_files())
                .sum::<usize>()
    }

    /// Count matching files in this node and all children.
    fn count_matches(&self, filter: &str) -> usize {
        let file_matches = if filter.is_empty() {
            self.files.len()
        } else {
            self.files
                .iter()
                .filter(|f| Self::file_matches(f, filter))
                .count()
        };
        file_matches
            + self
                .children
                .values()
                .map(|c| c.count_matches(filter))
                .sum::<usize>()
    }

    /// Check if a file matches the filter.
    fn file_matches(file: &crate::file::FileItem, filter: &str) -> bool {
        if filter.is_empty() {
            return true;
        }
        let pattern = filter.to_lowercase();
        file.name.to_lowercase().contains(&pattern) || file.path.to_lowercase().contains(&pattern)
    }

    /// Render this node and its children as HTML.
    /// Returns (html, has_matches) where has_matches indicates if this node or its children have matching files.
    fn render(&self, name: &str, depth: usize, filter: &str) -> (String, bool) {
        let has_filter = !filter.is_empty();

        // First, check if we have any matches in this subtree
        let match_count = self.count_matches(filter);
        if has_filter && match_count == 0 {
            return (String::new(), false);
        }

        let mut html = String::new();
        let indent = "  ".repeat(depth);

        // Auto-open if: no filter and shallow depth, OR has filter and has matches
        let open_attr = if has_filter || depth < 2 { " open" } else { "" };

        // Show match count in header when filtering
        let count_display = if has_filter {
            format!("{} matches", match_count)
        } else {
            format!("{} items", self.total_files())
        };

        html.push_str(&format!(
            r#"{}<details{}><summary class="folder"><span class="folder-icon"></span>{} <span class="count">({})</span></summary>"#,
            indent,
            open_attr,
            html_escape(name),
            count_display
        ));

        html.push_str(&format!("{}<ul class=\"tree-list\">", indent));

        // Render subdirectories first (sorted)
        let mut child_names: Vec<_> = self.children.keys().collect();
        child_names.sort();
        for child_name in child_names {
            let child = self.children.get(child_name).unwrap();
            let (child_html, child_has_matches) = child.render(child_name, depth + 1, filter);
            if !has_filter || child_has_matches {
                html.push_str(&format!("{}<li class=\"tree-dir\">", indent));
                html.push_str(&child_html);
                html.push_str(&format!("{}</li>", indent));
            }
        }

        // Render files (sorted by name)
        let mut sorted_files = self.files.clone();
        sorted_files.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));
        for file in sorted_files {
            let is_match = Self::file_matches(file, filter);
            // Skip non-matching files when filtering
            if has_filter && !is_match {
                continue;
            }

            let hash_preview = truncate_hash(file.hash.as_deref(), 8);

            let match_class = if has_filter && is_match { " match" } else { "" };
            html.push_str(&format!(
                r#"{}<li class="tree-file{}"><span class="file-icon"></span><span class="file-name">{}</span><span class="file-size">{}</span><span class="file-hash">{}</span></li>"#,
                indent,
                match_class,
                html_escape(&file.name),
                sizeof_fmt(file.size),
                hash_preview
            ));
        }

        html.push_str(&format!("{}</ul>", indent));
        html.push_str(&format!("{}</details>", indent));

        (html, match_count > 0)
    }
}

/// Build tree HTML for file listing.
/// When filter is provided, the tree shows all parent directories leading to matching files.
fn build_tree_html(files: &[crate::file::FileItem], filter: &str) -> String {
    if files.len() > MAX_TREE_VIEW_FILES {
        return format!(
            r#"<p class="warning">Too many files ({}) for tree view. Maximum is {}. Use table view or filter results.</p>"#,
            files.len(),
            MAX_TREE_VIEW_FILES
        );
    }

    // Build hierarchical tree structure from ALL files
    let mut root = TreeNode::default();

    for file in files {
        let path = if file.path.is_empty() || file.path == "." {
            Vec::new()
        } else {
            file.path.split('/').map(String::from).collect::<Vec<_>>()
        };

        // Navigate/create path in tree
        let mut current = &mut root;
        for component in path {
            current = current.children.entry(component).or_default();
        }
        current.files.push(file);
    }

    // Render with filter - will only show nodes with matching descendants
    let (tree_html, has_matches) = root.render("(root)", 0, filter);

    if !filter.is_empty() && !has_matches {
        return r#"<p class="empty">No matching files found in tree view.</p>"#.to_string();
    }

    let mut html = String::from(r#"<div class="tree-view">"#);
    html.push_str(&tree_html);
    html.push_str("</div>");

    html
}

/// Search page handler.
async fn search_handler(Query(params): Query<SearchQuery>) -> Html<String> {
    let results = if params.q.is_empty() {
        String::new()
    } else {
        match find_in_catalogs(&params.q, None) {
            Ok(results) => {
                if results.is_empty() {
                    "<p class=\"empty\">No matches found.</p>".to_string()
                } else {
                    let mut html = String::new();
                    for result in results {
                        html.push_str(&format!(
                            r#"<div class="search-result">
                                <h3><a href="/catalog/{}">{}</a> ({} matches)</h3>
                                <ul>"#,
                            html_escape(&result.catalog),
                            html_escape(&result.catalog),
                            result.files.len().min(MAX_SEARCH_RESULTS_PER_CATALOG)
                        ));

                        for file in result.files.iter().take(MAX_SEARCH_RESULTS_PER_CATALOG) {
                            html.push_str(&format!(
                                r#"<li>{}/{} <span class="meta">({})</span></li>"#,
                                html_escape(&file.path),
                                html_escape(&file.name),
                                sizeof_fmt(file.size)
                            ));
                        }

                        if result.files.len() > MAX_SEARCH_RESULTS_PER_CATALOG {
                            html.push_str(&format!(
                                r#"<li class="more">...and {} more</li>"#,
                                result.files.len() - MAX_SEARCH_RESULTS_PER_CATALOG
                            ));
                        }

                        html.push_str("</ul></div>");
                    }
                    html
                }
            }
            Err(e) => format!(
                "<p class=\"error\">Error: {}</p>",
                html_escape(&e.to_string())
            ),
        }
    };

    Html(format!(
        r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search - Catho</title>
    {CSS}
</head>
<body>
    <div class="container">
        <header>
            <h1>Catho</h1>
            <p>File Catalog Manager</p>
        </header>
        <nav>
            <a href="/">Catalogs</a>
            <a href="/search" class="active">Search</a>
        </nav>
        <main>
            <h2>Search All Catalogs</h2>
            <form method="get" class="search-form large">
                <input type="text" name="q" value="{query}" placeholder="Search pattern (use * as wildcard)..." autofocus>
                <button type="submit">Search</button>
            </form>
            <div class="results">
                {results}
            </div>
        </main>
    </div>
</body>
</html>"#,
        CSS = CSS_STYLES,
        query = html_escape(&params.q),
        results = results
    ))
}

/// API: List catalogs.
async fn api_catalogs() -> Json<CatalogListResponse> {
    let catalogs = list_catalogs()
        .unwrap_or_default()
        .into_iter()
        .map(|c| CatalogListItem {
            name: c.name,
            size: c.size,
            size_fmt: sizeof_fmt(c.size),
            date: c.date,
        })
        .collect();

    Json(CatalogListResponse { catalogs })
}

/// API: Get catalog detail.
async fn api_catalog(Path(name): Path<String>) -> Response {
    if !is_valid_catalog_name(&name) {
        return (StatusCode::BAD_REQUEST, "Invalid catalog name").into_response();
    }

    match export_catalog(&name) {
        Ok(catalog) => {
            let total_size: i64 = catalog.files.iter().map(|f| f.size).sum();
            let response = CatalogDetailResponse {
                metadata: CatalogMetadataResponse {
                    name: catalog.metadata.name,
                    path: catalog.metadata.path,
                    hash: catalog.metadata.hash,
                    createdate: catalog.metadata.createdate.parse().unwrap_or(0),
                    lastmodifdate: catalog.metadata.lastmodifdate.parse().unwrap_or(0),
                },
                files: catalog
                    .files
                    .into_iter()
                    .map(|f| FileResponse {
                        id: f.id,
                        name: f.name,
                        path: f.path,
                        size: f.size,
                        size_fmt: sizeof_fmt(f.size),
                        date: f.date,
                        hash: f.hash,
                    })
                    .collect(),
                total_files: 0, // Will be set below
                total_size,
                total_size_fmt: sizeof_fmt(total_size),
            };
            let mut response = response;
            response.total_files = response.files.len();
            Json(response).into_response()
        }
        Err(_) => (StatusCode::NOT_FOUND, "Catalog not found").into_response(),
    }
}

/// HTML escape helper.
fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#x27;")
}

/// CSS styles.
const CSS_STYLES: &str = r#"<style>
:root {
    --bg-color: #1a1a2e;
    --surface-color: #16213e;
    --primary-color: #0f3460;
    --accent-color: #e94560;
    --text-color: #eee;
    --text-muted: #888;
    --border-color: #333;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    text-align: center;
    padding: 40px 0;
    border-bottom: 1px solid var(--border-color);
}

header h1 {
    color: var(--accent-color);
    font-size: 2.5em;
}

header p {
    color: var(--text-muted);
}

nav {
    display: flex;
    gap: 20px;
    justify-content: center;
    padding: 20px 0;
    border-bottom: 1px solid var(--border-color);
}

nav a {
    color: var(--text-color);
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 4px;
    transition: background 0.2s;
}

nav a:hover, nav a.active {
    background: var(--primary-color);
}

main {
    padding: 40px 0;
}

h2 {
    margin-bottom: 20px;
    color: var(--accent-color);
}

.catalog-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 20px;
}

.catalog-card {
    background: var(--surface-color);
    padding: 20px;
    border-radius: 8px;
    text-decoration: none;
    color: var(--text-color);
    transition: transform 0.2s, box-shadow 0.2s;
}

.catalog-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 16px rgba(0,0,0,0.3);
}

.catalog-card h3 {
    margin-bottom: 10px;
}

.catalog-card .size {
    color: var(--text-muted);
}

.catalog-info {
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 20px;
    padding: 15px;
    background: var(--surface-color);
    border-radius: 8px;
}

.catalog-info span {
    color: var(--text-muted);
}

.controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
    gap: 10px;
}

.search-form {
    display: flex;
    gap: 10px;
}

.search-form input {
    padding: 10px 15px;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    background: var(--surface-color);
    color: var(--text-color);
    min-width: 250px;
}

.search-form.large input {
    min-width: 400px;
}

.search-form button {
    padding: 10px 20px;
    background: var(--accent-color);
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    transition: opacity 0.2s;
}

.search-form button:hover {
    opacity: 0.9;
}

.view-toggle {
    display: flex;
    gap: 5px;
}

.view-toggle a {
    padding: 8px 16px;
    background: var(--surface-color);
    color: var(--text-color);
    text-decoration: none;
    border-radius: 4px;
}

.view-toggle a.active {
    background: var(--primary-color);
}

table {
    width: 100%;
    border-collapse: collapse;
    background: var(--surface-color);
    border-radius: 8px;
    overflow: hidden;
}

th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

th {
    background: var(--primary-color);
    font-weight: 600;
}

tr:hover {
    background: rgba(255,255,255,0.05);
}

.size {
    white-space: nowrap;
}

.pagination {
    display: flex;
    justify-content: center;
    gap: 15px;
    margin-top: 20px;
}

.pagination a {
    color: var(--accent-color);
    text-decoration: none;
}

.tree {
    background: var(--surface-color);
    padding: 20px;
    border-radius: 8px;
}

.tree details {
    margin-left: 20px;
}

.tree summary {
    cursor: pointer;
    padding: 5px;
    border-radius: 4px;
}

.tree summary:hover {
    background: rgba(255,255,255,0.05);
}

.tree .folder {
    font-weight: bold;
}

.tree .count {
    color: var(--text-muted);
    font-weight: normal;
}

.tree ul {
    list-style: none;
    margin-left: 20px;
}

.tree .file {
    padding: 3px 5px;
}

.tree .meta {
    color: var(--text-muted);
    font-size: 0.9em;
}

/* New hierarchical tree view styles */
.tree-view {
    background: var(--surface-color);
    padding: 20px;
    border-radius: 8px;
    font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
    font-size: 14px;
}

.tree-view details {
    margin-left: 0;
}

.tree-view details details {
    margin-left: 20px;
    border-left: 1px solid var(--border-color);
    padding-left: 10px;
}

.tree-view summary {
    cursor: pointer;
    padding: 6px 10px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
    user-select: none;
}

.tree-view summary:hover {
    background: rgba(255,255,255,0.08);
}

.tree-view summary::-webkit-details-marker {
    display: none;
}

.tree-view details > summary::before {
    content: '▶';
    font-size: 10px;
    transition: transform 0.2s;
    color: var(--text-muted);
}

.tree-view details[open] > summary::before {
    transform: rotate(90deg);
}

.tree-view .folder-icon::before {
    content: '📁';
    margin-right: 4px;
}

.tree-view details[open] > summary .folder-icon::before {
    content: '📂';
}

.tree-view .count {
    color: var(--text-muted);
    font-weight: normal;
    font-size: 12px;
}

.tree-list {
    list-style: none;
    margin: 0;
    padding: 0;
}

.tree-dir {
    margin: 0;
}

.tree-file {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 10px 4px 28px;
    border-radius: 4px;
    margin: 1px 0;
}

.tree-file:hover {
    background: rgba(255,255,255,0.05);
}

.tree-file .file-icon::before {
    content: '📄';
}

.tree-file .file-name {
    flex: 1;
    color: var(--text-color);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.tree-file .file-size {
    color: var(--text-muted);
    font-size: 12px;
    min-width: 70px;
    text-align: right;
}

.tree-file .file-hash {
    color: var(--accent-color);
    font-size: 11px;
    font-family: monospace;
    opacity: 0.7;
    min-width: 70px;
}

.tree-file.match {
    background: rgba(233, 69, 96, 0.15);
    border-left: 3px solid var(--accent-color);
    padding-left: 25px;
}

.tree-file.match .file-name {
    color: var(--accent-color);
    font-weight: 600;
}

.search-result {
    background: var(--surface-color);
    padding: 20px;
    border-radius: 8px;
    margin-bottom: 20px;
}

.search-result h3 a {
    color: var(--accent-color);
    text-decoration: none;
}

.search-result ul {
    list-style: none;
    margin-top: 10px;
}

.search-result li {
    padding: 5px 0;
    border-bottom: 1px solid var(--border-color);
}

.search-result .more {
    color: var(--text-muted);
    font-style: italic;
}

.empty, .warning, .error {
    padding: 20px;
    text-align: center;
    color: var(--text-muted);
}

.error {
    color: var(--accent-color);
}

code {
    background: var(--primary-color);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: monospace;
}
</style>"#;
