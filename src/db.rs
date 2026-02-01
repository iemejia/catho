//! Database operations for catho.

use regex::Regex;
use rusqlite::{functions::FunctionFlags, params, Connection};
use std::collections::HashMap;
use std::path::Path;

use crate::error::{CathoError, Result};
use crate::file::{get_catalog_abspath, FileItem};
use crate::utils::{touch_dir, HashType};

/// SQL statements.
const SQL_CREATE_METADATA: &str = "CREATE TABLE METADATA (key TEXT, value TEXT)";
const SQL_CREATE_CATALOG: &str = "CREATE TABLE CATALOG (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date INTEGER NOT NULL,
    size INTEGER NOT NULL,
    path TEXT NOT NULL,
    hash TEXT
)";
const SQL_INSERT_METADATA: &str = "INSERT INTO METADATA (key, value) VALUES (?, ?)";
const SQL_INSERT_CATALOG: &str =
    "INSERT INTO CATALOG (id, name, date, size, path, hash) VALUES (?, ?, ?, ?, ?, ?)";
const SQL_SELECT_METADATA: &str = "SELECT * FROM METADATA";
const SQL_SELECT_CATALOG: &str = "SELECT * FROM CATALOG";
const SQL_DELETE_CATALOG: &str = "DELETE FROM CATALOG WHERE id IN ";
const SQL_SELECT_CATALOG_COND: &str =
    "SELECT * FROM CATALOG WHERE name = ? AND path = ? AND size = ? AND date = ?";
const SQL_SELECT_CATALOG_BY_PATTERN: &str =
    "SELECT * FROM CATALOG WHERE name LIKE ? ESCAPE '\\' OR path LIKE ? ESCAPE '\\'";
const SQL_SELECT_CATALOG_BY_REGEX: &str =
    "SELECT * FROM CATALOG WHERE REGEX(?, path || '/' || name)";
const SQL_SELECT_CATALOG_BY_HASH: &str = "SELECT * FROM CATALOG WHERE hash IN ";
#[allow(dead_code)]
const SQL_SELECT_CATALOG_BY_PATH: &str = "SELECT * FROM CATALOG WHERE path LIKE ? ESCAPE '\\'";

/// Metadata keys.
pub const META_VERSION: &str = "version";
pub const META_NAME: &str = "name";
pub const META_PATH: &str = "path";
pub const META_FULLPATH: &str = "fullpath";
pub const META_CREATEDATE: &str = "createdate";
pub const META_LASTMODIFDATE: &str = "lastmodifdate";
pub const META_HASH: &str = "hash";

/// Current schema version.
pub const SCHEMA_VERSION: &str = "1";

/// Catalog metadata.
#[derive(Debug, Clone)]
pub struct CatalogMetadata {
    pub version: String,
    pub name: String,
    pub path: String,
    pub fullpath: String,
    pub createdate: i64,
    pub lastmodifdate: i64,
    pub hash: HashType,
}

impl CatalogMetadata {
    /// Create metadata for a new catalog.
    pub fn new(name: &str, path: &str, fullpath: &str, hash_type: HashType) -> Self {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0);

        Self {
            version: SCHEMA_VERSION.to_string(),
            name: name.to_string(),
            path: path.to_string(),
            fullpath: fullpath.to_string(),
            createdate: now,
            lastmodifdate: now,
            hash: hash_type,
        }
    }

    /// Convert metadata to key-value pairs.
    pub fn to_pairs(&self) -> Vec<(&'static str, String)> {
        vec![
            (META_VERSION, self.version.clone()),
            (META_NAME, self.name.clone()),
            (META_PATH, self.path.clone()),
            (META_FULLPATH, self.fullpath.clone()),
            (META_CREATEDATE, self.createdate.to_string()),
            (META_LASTMODIFDATE, self.lastmodifdate.to_string()),
            (META_HASH, self.hash.to_string()),
        ]
    }
}

/// Open a connection to a catalog database.
fn open_connection(name: &str) -> Result<Connection> {
    let path = get_catalog_abspath(name);
    if !path.exists() {
        return Err(CathoError::CatalogNotFound(name.to_string()));
    }
    let conn = Connection::open(&path)?;
    register_regex_function(&conn)?;
    Ok(conn)
}

/// Register the REGEX function for SQLite.
fn register_regex_function(conn: &Connection) -> Result<()> {
    conn.create_scalar_function("REGEX", 2, FunctionFlags::SQLITE_UTF8, |ctx| {
        let pattern: String = ctx.get(0)?;
        let text: String = ctx.get(1)?;

        match Regex::new(&pattern) {
            Ok(re) => Ok(re.is_match(&text)),
            Err(_) => Ok(false),
        }
    })?;
    Ok(())
}

/// Create a new catalog database.
pub fn db_create(name: &str) -> Result<()> {
    let catho_dir = crate::file::catho_path();
    touch_dir(&catho_dir)?;

    let path = get_catalog_abspath(name);
    let conn = Connection::open(&path)?;

    conn.execute(SQL_CREATE_METADATA, [])?;
    conn.execute(SQL_CREATE_CATALOG, [])?;

    tracing::debug!("Created database: {:?}", path);
    Ok(())
}

/// Insert metadata into a catalog.
pub fn db_insert_metadata(name: &str, metadata: &CatalogMetadata) -> Result<()> {
    let conn = open_connection(name)?;

    for (key, value) in metadata.to_pairs() {
        conn.execute(SQL_INSERT_METADATA, params![key, value])?;
    }

    Ok(())
}

/// Insert file items into a catalog.
pub fn db_insert_catalog(name: &str, items: &[FileItem]) -> Result<()> {
    let conn = open_connection(name)?;

    let tx = conn.unchecked_transaction()?;
    {
        let mut stmt = tx.prepare(SQL_INSERT_CATALOG)?;
        for item in items {
            stmt.execute(params![
                item.id, item.name, item.date, item.size, item.path, item.hash
            ])?;
        }
    }
    tx.commit()?;

    Ok(())
}

/// Get metadata from a catalog.
pub fn db_get_metadata(name: &str) -> Result<CatalogMetadata> {
    let conn = open_connection(name)?;

    let mut stmt = conn.prepare(SQL_SELECT_METADATA)?;
    let rows = stmt.query_map([], |row| {
        let key: String = row.get(0)?;
        let value: String = row.get(1)?;
        Ok((key, value))
    })?;

    let mut map: HashMap<String, String> = HashMap::new();
    for row in rows {
        let (key, value) = row?;
        map.insert(key, value);
    }

    Ok(CatalogMetadata {
        version: map.get(META_VERSION).cloned().unwrap_or_default(),
        name: map.get(META_NAME).cloned().unwrap_or_default(),
        path: map.get(META_PATH).cloned().unwrap_or_default(),
        fullpath: map.get(META_FULLPATH).cloned().unwrap_or_default(),
        createdate: map
            .get(META_CREATEDATE)
            .and_then(|s| s.parse().ok())
            .unwrap_or(0),
        lastmodifdate: map
            .get(META_LASTMODIFDATE)
            .and_then(|s| s.parse().ok())
            .unwrap_or(0),
        hash: map
            .get(META_HASH)
            .and_then(|s| HashType::from_str(s))
            .unwrap_or_default(),
    })
}

/// Get all items from a catalog.
pub fn db_get_catalog(name: &str) -> Result<Vec<FileItem>> {
    let conn = open_connection(name)?;

    let mut stmt = conn.prepare(SQL_SELECT_CATALOG)?;
    let rows = stmt.query_map([], |row| {
        Ok(FileItem {
            id: Some(row.get(0)?),
            name: row.get(1)?,
            date: row.get(2)?,
            size: row.get(3)?,
            path: row.get(4)?,
            hash: row.get(5)?,
        })
    })?;

    let mut items = Vec::new();
    for row in rows {
        items.push(row?);
    }

    Ok(items)
}

/// Delete items from a catalog by ID.
pub fn db_delete_catalog(name: &str, ids: &[i64]) -> Result<()> {
    if ids.is_empty() {
        return Ok(());
    }

    let conn = open_connection(name)?;

    let placeholders: Vec<String> = ids.iter().map(|_| "?".to_string()).collect();
    let sql = format!("{} ({})", SQL_DELETE_CATALOG, placeholders.join(","));

    let params: Vec<&dyn rusqlite::ToSql> =
        ids.iter().map(|id| id as &dyn rusqlite::ToSql).collect();
    conn.execute(&sql, params.as_slice())?;

    tracing::debug!("Deleted {} items from catalog {}", ids.len(), name);
    Ok(())
}

/// Find items in catalog that no longer exist on disk.
pub fn db_get_deleted_ids(name: &str) -> Result<Vec<i64>> {
    let metadata = db_get_metadata(name)?;
    let items = db_get_catalog(name)?;
    let root = Path::new(&metadata.fullpath);

    let mut deleted_ids = Vec::new();
    for item in items {
        let full_path = if item.path.is_empty() || item.path == "." {
            root.join(&item.name)
        } else {
            root.join(&item.path).join(&item.name)
        };

        if !full_path.exists() {
            if let Some(id) = item.id {
                deleted_ids.push(id);
            }
        }
    }

    Ok(deleted_ids)
}

/// Find items in catalog that match existing files (for update check).
pub fn db_get_inserted_catalogs(name: &str, items: &[FileItem]) -> Result<Vec<FileItem>> {
    let conn = open_connection(name)?;
    let mut stmt = conn.prepare(SQL_SELECT_CATALOG_COND)?;

    let mut existing = Vec::new();
    for item in items {
        let rows = stmt.query_map(params![item.name, item.path, item.size, item.date], |row| {
            Ok(FileItem {
                id: Some(row.get(0)?),
                name: row.get(1)?,
                date: row.get(2)?,
                size: row.get(3)?,
                path: row.get(4)?,
                hash: row.get(5)?,
            })
        })?;

        for row in rows {
            existing.push(row?);
        }
    }

    Ok(existing)
}

/// Search catalog by SQL LIKE pattern.
pub fn get_catalog_by_pattern(name: &str, pattern: &str) -> Result<Vec<FileItem>> {
    let conn = open_connection(name)?;

    let mut stmt = conn.prepare(SQL_SELECT_CATALOG_BY_PATTERN)?;
    let rows = stmt.query_map(params![pattern, pattern], |row| {
        Ok(FileItem {
            id: Some(row.get(0)?),
            name: row.get(1)?,
            date: row.get(2)?,
            size: row.get(3)?,
            path: row.get(4)?,
            hash: row.get(5)?,
        })
    })?;

    let mut items = Vec::new();
    for row in rows {
        items.push(row?);
    }

    Ok(items)
}

/// Search catalog by regex pattern.
pub fn get_catalog_by_regex(name: &str, regex: &str) -> Result<Vec<FileItem>> {
    let conn = open_connection(name)?;

    let mut stmt = conn.prepare(SQL_SELECT_CATALOG_BY_REGEX)?;
    let rows = stmt.query_map(params![regex], |row| {
        Ok(FileItem {
            id: Some(row.get(0)?),
            name: row.get(1)?,
            date: row.get(2)?,
            size: row.get(3)?,
            path: row.get(4)?,
            hash: row.get(5)?,
        })
    })?;

    let mut items = Vec::new();
    for row in rows {
        items.push(row?);
    }

    Ok(items)
}

/// Search catalog by hash values.
pub fn get_catalog_by_hash(name: &str, hashes: &[String]) -> Result<Vec<FileItem>> {
    if hashes.is_empty() {
        return Ok(Vec::new());
    }

    let conn = open_connection(name)?;

    let placeholders: Vec<String> = hashes.iter().map(|_| "?".to_string()).collect();
    let sql = format!(
        "{} ({})",
        SQL_SELECT_CATALOG_BY_HASH,
        placeholders.join(",")
    );

    let mut stmt = conn.prepare(&sql)?;
    let params: Vec<&dyn rusqlite::ToSql> =
        hashes.iter().map(|h| h as &dyn rusqlite::ToSql).collect();
    let rows = stmt.query_map(params.as_slice(), |row| {
        Ok(FileItem {
            id: Some(row.get(0)?),
            name: row.get(1)?,
            date: row.get(2)?,
            size: row.get(3)?,
            path: row.get(4)?,
            hash: row.get(5)?,
        })
    })?;

    let mut items = Vec::new();
    for row in rows {
        items.push(row?);
    }

    Ok(items)
}

/// Search catalog by path prefix.
#[allow(dead_code)]
pub fn get_catalog_by_path(name: &str, path: &str) -> Result<Vec<FileItem>> {
    let conn = open_connection(name)?;

    let pattern = format!("{}%", path.replace('\\', "\\\\").replace('%', "\\%"));
    let mut stmt = conn.prepare(SQL_SELECT_CATALOG_BY_PATH)?;
    let rows = stmt.query_map(params![pattern], |row| {
        Ok(FileItem {
            id: Some(row.get(0)?),
            name: row.get(1)?,
            date: row.get(2)?,
            size: row.get(3)?,
            path: row.get(4)?,
            hash: row.get(5)?,
        })
    })?;

    let mut items = Vec::new();
    for row in rows {
        items.push(row?);
    }

    Ok(items)
}

/// Update the lastmodifdate in metadata.
pub fn db_update_lastmodifdate(name: &str) -> Result<()> {
    let conn = open_connection(name)?;

    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs().to_string())
        .unwrap_or_else(|_| "0".to_string());

    conn.execute(
        "UPDATE METADATA SET value = ? WHERE key = ?",
        params![now, META_LASTMODIFDATE],
    )?;

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup_test_catalog(name: &str) -> TempDir {
        let temp_dir = TempDir::new().unwrap();
        // SAFETY: Tests run in isolation and set HOME for this process only
        unsafe { std::env::set_var("HOME", temp_dir.path()) };

        db_create(name).unwrap();
        let metadata = CatalogMetadata::new(name, "/test", "/test", HashType::Sha256);
        db_insert_metadata(name, &metadata).unwrap();

        temp_dir
    }

    #[test]
    fn test_db_create_and_metadata() {
        let _temp = setup_test_catalog("test_meta");
        let metadata = db_get_metadata("test_meta").unwrap();

        assert_eq!(metadata.name, "test_meta");
        assert_eq!(metadata.version, "1");
        assert_eq!(metadata.hash, HashType::Sha256);
    }

    #[test]
    fn test_db_insert_and_get_catalog() {
        let _temp = setup_test_catalog("test_insert");

        let items = vec![
            FileItem::new(
                None,
                "file1.txt".into(),
                1000,
                100,
                ".".into(),
                Some("abc".into()),
            ),
            FileItem::new(
                None,
                "file2.txt".into(),
                2000,
                200,
                "subdir".into(),
                Some("def".into()),
            ),
        ];

        db_insert_catalog("test_insert", &items).unwrap();

        let retrieved = db_get_catalog("test_insert").unwrap();
        assert_eq!(retrieved.len(), 2);
        assert_eq!(retrieved[0].name, "file1.txt");
        assert_eq!(retrieved[1].name, "file2.txt");
    }

    #[test]
    fn test_get_catalog_by_pattern() {
        let _temp = setup_test_catalog("test_pattern");

        let items = vec![
            FileItem::new(None, "document.pdf".into(), 1000, 100, ".".into(), None),
            FileItem::new(None, "image.png".into(), 2000, 200, ".".into(), None),
            FileItem::new(None, "notes.txt".into(), 3000, 300, ".".into(), None),
        ];
        db_insert_catalog("test_pattern", &items).unwrap();

        let results = get_catalog_by_pattern("test_pattern", "%.pdf").unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "document.pdf");
    }
}
