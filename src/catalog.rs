//! Catalog operations for catho.

use serde::Serialize;
use std::fs;
use std::path::Path;
use walkdir::WalkDir;

use crate::db::{
    db_create, db_delete_catalog, db_get_catalog, db_get_deleted_ids, db_get_inserted_catalogs,
    db_get_metadata, db_insert_catalog, db_insert_metadata, db_update_lastmodifdate,
    get_catalog_by_hash, get_catalog_by_pattern, get_catalog_by_regex, CatalogMetadata,
};
use crate::error::{CathoError, Result};
use crate::file::{
    count_files, get_catalog_abspath, get_catalogs, remove_catalog_files, select_catalogs,
    CatalogInfo, FileItem, FileIterator,
};
use crate::utils::{file_hash, sizeof_fmt, HashType};

/// Search result from a catalog.
#[derive(Debug, Clone)]
pub struct SearchResult {
    /// Catalog name.
    pub catalog: String,
    /// Matching files.
    pub files: Vec<FileItem>,
}

/// Export format for catalogs.
#[derive(Debug, Clone, Serialize)]
pub struct ExportedCatalog {
    pub metadata: ExportedMetadata,
    pub files: Vec<ExportedFile>,
}

/// Exported metadata.
#[derive(Debug, Clone, Serialize)]
pub struct ExportedMetadata {
    pub name: String,
    pub path: String,
    pub hash: String,
    pub createdate: String,
    pub lastmodifdate: String,
}

/// Exported file item.
#[derive(Debug, Clone, Serialize)]
pub struct ExportedFile {
    pub id: i64,
    pub name: String,
    pub path: String,
    pub size: i64,
    pub date: i64,
    pub hash: Option<String>,
}

/// Create a new catalog by indexing a directory.
pub fn create_catalog(name: &str, path: &str, hash_type: HashType, force: bool) -> Result<()> {
    let catalog_path = get_catalog_abspath(name);

    // Check if catalog exists
    if catalog_path.exists() {
        if force {
            fs::remove_file(&catalog_path)?;
            tracing::info!("Removed existing catalog: {}", name);
        } else {
            return Err(CathoError::CatalogExists(name.to_string()));
        }
    }

    // Validate path
    let full_path = Path::new(path).canonicalize()?;
    if !full_path.exists() {
        return Err(CathoError::PathNotFound(full_path));
    }
    if !full_path.is_dir() {
        return Err(CathoError::NotADirectory(full_path));
    }

    // Create database
    db_create(name)?;

    // Insert metadata
    let metadata = CatalogMetadata::new(name, path, &full_path.to_string_lossy(), hash_type);
    db_insert_metadata(name, &metadata)?;

    // Count files for progress
    let total_files = count_files(&full_path);
    tracing::info!("Indexing {} files from {:?}", total_files, full_path);

    // Index files
    let mut file_iter = FileIterator::new(full_path, hash_type);
    let mut indexed = 0;

    while let Some(batch) = file_iter.next_batch()? {
        let count = batch.len();
        db_insert_catalog(name, &batch)?;
        indexed += count;
        tracing::debug!("Indexed {}/{} files", indexed, total_files);
    }

    tracing::info!("Created catalog '{}' with {} files", name, indexed);
    Ok(())
}

/// Update an existing catalog (add new files, remove deleted ones).
pub fn update_catalog(name: &str) -> Result<()> {
    let catalog_path = get_catalog_abspath(name);
    if !catalog_path.exists() {
        return Err(CathoError::CatalogNotFound(name.to_string()));
    }

    let metadata = db_get_metadata(name)?;
    let full_path = Path::new(&metadata.fullpath);

    if !full_path.exists() {
        return Err(CathoError::PathNotFound(full_path.to_path_buf()));
    }

    // Remove deleted files
    let deleted_ids = db_get_deleted_ids(name)?;
    if !deleted_ids.is_empty() {
        db_delete_catalog(name, &deleted_ids)?;
        tracing::info!("Removed {} deleted files from catalog", deleted_ids.len());
    }

    // Find new files
    let mut file_iter = FileIterator::new(full_path.to_path_buf(), metadata.hash);
    let mut added = 0;

    while let Some(batch) = file_iter.next_batch()? {
        // Filter out already existing files
        let existing = db_get_inserted_catalogs(name, &batch)?;
        let existing_keys: std::collections::HashSet<_> = existing
            .iter()
            .map(|f| (f.name.clone(), f.path.clone(), f.size, f.date))
            .collect();

        let new_files: Vec<_> = batch
            .into_iter()
            .filter(|f| !existing_keys.contains(&(f.name.clone(), f.path.clone(), f.size, f.date)))
            .collect();

        if !new_files.is_empty() {
            let count = new_files.len();
            db_insert_catalog(name, &new_files)?;
            added += count;
        }
    }

    if added > 0 {
        tracing::info!("Added {} new files to catalog", added);
    }

    db_update_lastmodifdate(name)?;
    tracing::info!("Updated catalog '{}'", name);
    Ok(())
}

/// Find files matching a pattern in catalogs.
/// Pattern supports * as wildcard.
pub fn find_in_catalogs(pattern: &str, catalogs: Option<&[String]>) -> Result<Vec<SearchResult>> {
    let catalog_names = select_catalogs(catalogs)?;

    // Convert * to SQL LIKE pattern
    // Also escape % and _ for literal matching
    let sql_pattern = pattern
        .replace('\\', "\\\\")
        .replace('%', "\\%")
        .replace('_', "\\_")
        .replace('*', "%");

    // Add % at start and end for substring matching
    let sql_pattern = format!("%{}%", sql_pattern);

    let mut results = Vec::new();
    for catalog in catalog_names {
        let files = get_catalog_by_pattern(&catalog, &sql_pattern)?;
        if !files.is_empty() {
            results.push(SearchResult {
                catalog: catalog.clone(),
                files,
            });
        }
    }

    Ok(results)
}

/// Find files matching a regex pattern in catalogs.
pub fn find_regex_in_catalogs(
    regex: &str,
    catalogs: Option<&[String]>,
) -> Result<Vec<SearchResult>> {
    let catalog_names = select_catalogs(catalogs)?;

    let mut results = Vec::new();
    for catalog in catalog_names {
        let files = get_catalog_by_regex(&catalog, regex)?;
        if !files.is_empty() {
            results.push(SearchResult {
                catalog: catalog.clone(),
                files,
            });
        }
    }

    Ok(results)
}

/// Find files matching given hashes in catalogs.
pub fn find_hash_in_catalogs(
    hashes: &[String],
    catalogs: Option<&[String]>,
) -> Result<Vec<SearchResult>> {
    let catalog_names = select_catalogs(catalogs)?;

    let mut results = Vec::new();
    for catalog in catalog_names {
        let files = get_catalog_by_hash(&catalog, hashes)?;
        if !files.is_empty() {
            results.push(SearchResult {
                catalog: catalog.clone(),
                files,
            });
        }
    }

    Ok(results)
}

/// Scan a file or directory and find matches in all catalogs by hash.
pub fn scan_catalogs(path: &str) -> Result<Vec<SearchResult>> {
    let target = Path::new(path);
    if !target.exists() {
        return Err(CathoError::PathNotFound(target.to_path_buf()));
    }

    // Collect hashes
    let mut hashes = Vec::new();

    if target.is_file() {
        if let Some(hash) = file_hash(target, HashType::Sha256)? {
            hashes.push(hash);
        }
    } else if target.is_dir() {
        for entry in WalkDir::new(target).into_iter().filter_map(|e| e.ok()) {
            if entry.path().is_file() {
                if let Ok(Some(hash)) = file_hash(entry.path(), HashType::Sha256) {
                    hashes.push(hash);
                }
            }
        }
    }

    if hashes.is_empty() {
        return Ok(Vec::new());
    }

    find_hash_in_catalogs(&hashes, None)
}

/// List all catalogs.
pub fn list_catalogs() -> Result<Vec<CatalogInfo>> {
    get_catalogs()
}

/// Remove catalogs.
pub fn remove_catalogs(names: &[String]) -> Result<()> {
    remove_catalog_files(names)
}

/// Export a catalog to JSON format.
pub fn export_catalog(name: &str) -> Result<ExportedCatalog> {
    let metadata = db_get_metadata(name)?;
    let files = db_get_catalog(name)?;

    Ok(ExportedCatalog {
        metadata: ExportedMetadata {
            name: metadata.name,
            path: metadata.fullpath,
            hash: metadata.hash.to_string(),
            createdate: metadata.createdate.to_string(),
            lastmodifdate: metadata.lastmodifdate.to_string(),
        },
        files: files
            .into_iter()
            .map(|f| ExportedFile {
                id: f.id.unwrap_or(0),
                name: f.name,
                path: f.path,
                size: f.size,
                date: f.date,
                hash: f.hash,
            })
            .collect(),
    })
}

/// Format a catalog listing as a string.
pub fn format_catalog_list(catalogs: &[CatalogInfo]) -> String {
    if catalogs.is_empty() {
        return "No catalogs available.".to_string();
    }

    let mut output = String::new();
    output.push_str("Available catalogs:\n");

    for cat in catalogs {
        output.push_str(&format!(
            "  {} ({}, {})\n",
            cat.name,
            sizeof_fmt(cat.size),
            crate::utils::format_date(cat.date)
        ));
    }

    output
}

/// Format search results as a string.
pub fn format_search_results(results: &[SearchResult]) -> String {
    if results.is_empty() {
        return "No matches found.".to_string();
    }

    let mut output = String::new();
    let total: usize = results.iter().map(|r| r.files.len()).sum();

    output.push_str(&format!("Found {} matches:\n\n", total));

    for result in results {
        output.push_str(&format!(
            "Catalog: {} ({} matches)\n",
            result.catalog,
            result.files.len()
        ));
        output.push_str(&format!("{:-<60}\n", ""));

        for file in &result.files {
            let hash_preview = crate::utils::truncate_hash(file.hash.as_deref(), 8);

            output.push_str(&format!(
                "  {} ({}, {}) [{}...]\n",
                file.full_path(),
                sizeof_fmt(file.size),
                crate::utils::format_date(file.date),
                hash_preview
            ));
        }
        output.push('\n');
    }

    output
}

/// Format catalog info as a string.
pub fn format_catalog_info(
    name: &str,
    metadata: &CatalogMetadata,
    file_count: usize,
    total_size: i64,
) -> String {
    let mut output = String::new();

    output.push_str(&format!("Catalog: {}\n", name));
    output.push_str(&format!("{:=<40}\n", ""));
    output.push_str(&format!("  Path:         {}\n", metadata.fullpath));
    output.push_str(&format!("  Hash type:    {}\n", metadata.hash));
    output.push_str(&format!(
        "  Created:      {}\n",
        crate::utils::format_date(metadata.createdate)
    ));
    output.push_str(&format!(
        "  Modified:     {}\n",
        crate::utils::format_date(metadata.lastmodifdate)
    ));
    output.push_str(&format!("  Files:        {}\n", file_count));
    output.push_str(&format!("  Total size:   {}\n", sizeof_fmt(total_size)));

    output
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn setup_test_env() -> (TempDir, TempDir) {
        let home_dir = TempDir::new().unwrap();
        let data_dir = TempDir::new().unwrap();

        // SAFETY: Tests run in isolation and set HOME for this process only
        unsafe { std::env::set_var("HOME", home_dir.path()) };

        // Create some test files
        fs::write(data_dir.path().join("file1.txt"), "hello").unwrap();
        fs::write(data_dir.path().join("file2.txt"), "world").unwrap();
        fs::create_dir(data_dir.path().join("subdir")).unwrap();
        fs::write(data_dir.path().join("subdir/file3.txt"), "test").unwrap();

        (home_dir, data_dir)
    }

    #[test]
    fn test_create_catalog() {
        let (_home, data) = setup_test_env();

        create_catalog(
            "test",
            &data.path().to_string_lossy(),
            HashType::None,
            false,
        )
        .unwrap();

        let catalogs = list_catalogs().unwrap();
        assert_eq!(catalogs.len(), 1);
        assert_eq!(catalogs[0].name, "test");
    }

    #[test]
    fn test_create_catalog_force() {
        let (_home, data) = setup_test_env();

        create_catalog(
            "test",
            &data.path().to_string_lossy(),
            HashType::None,
            false,
        )
        .unwrap();
        create_catalog("test", &data.path().to_string_lossy(), HashType::None, true).unwrap();

        let catalogs = list_catalogs().unwrap();
        assert_eq!(catalogs.len(), 1);
    }

    #[test]
    fn test_find_in_catalogs() {
        let (_home, data) = setup_test_env();

        create_catalog(
            "test",
            &data.path().to_string_lossy(),
            HashType::None,
            false,
        )
        .unwrap();

        let results = find_in_catalogs("file1", None).unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].files.len(), 1);
        assert_eq!(results[0].files[0].name, "file1.txt");
    }

    #[test]
    fn test_export_catalog() {
        let (_home, data) = setup_test_env();

        create_catalog(
            "test",
            &data.path().to_string_lossy(),
            HashType::None,
            false,
        )
        .unwrap();

        let exported = export_catalog("test").unwrap();
        assert_eq!(exported.metadata.name, "test");
        assert_eq!(exported.files.len(), 3);
    }
}
