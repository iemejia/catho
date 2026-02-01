//! File system operations for catho.

use rayon::prelude::*;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::RwLock;
use std::time::SystemTime;
use walkdir::WalkDir;

use crate::error::{CathoError, Result};
use crate::utils::{file_hash, HashType};

static CATALOG_DIR: RwLock<Option<PathBuf>> = RwLock::new(None);

/// Set custom catalog directory.
pub fn set_catalog_dir(path: PathBuf) {
    *CATALOG_DIR.write().unwrap() = Some(path);
}

/// Reset catalog directory to default (for testing).
#[cfg(test)]
pub fn reset_catalog_dir() {
    *CATALOG_DIR.write().unwrap() = None;
}

/// Catho catalog directory.
///
/// Priority: custom dir (via set_catalog_dir) > platform default
/// Platform-specific defaults:
/// - Linux: `~/.config/catho/catalogs`
/// - macOS: `~/Library/Application Support/catho/catalogs`
/// - Windows: `C:\Users\<User>\AppData\Roaming\catho\catalogs`
pub fn catho_path() -> PathBuf {
    CATALOG_DIR.read().unwrap().clone().unwrap_or_else(|| {
        dirs::config_dir()
            .expect("Could not find config directory")
            .join("catho")
            .join("catalogs")
    })
}

/// Extension for catalog database files.
pub const CATALOG_EXTENSION: &str = ".db";

/// Maximum number of files to process in a single batch.
pub const MAX_FILES_ITER: usize = 1024;

/// A file item in a catalog.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileItem {
    /// Unique ID (None before insertion, Some after).
    pub id: Option<i64>,
    /// File name.
    pub name: String,
    /// Modification time as Unix timestamp.
    pub date: i64,
    /// File size in bytes (stored as i64 for SQLite compatibility).
    pub size: i64,
    /// Relative path from catalog root.
    pub path: String,
    /// SHA-256 hash (None if hashing disabled).
    pub hash: Option<String>,
}

impl FileItem {
    /// Create a new file item.
    pub fn new(
        id: Option<i64>,
        name: String,
        date: i64,
        size: i64,
        path: String,
        hash: Option<String>,
    ) -> Self {
        Self {
            id,
            name,
            date,
            size,
            path,
            hash,
        }
    }

    /// Get the full relative path (path + name).
    pub fn full_path(&self) -> String {
        if self.path.is_empty() || self.path == "." {
            self.name.clone()
        } else {
            format!("{}/{}", self.path, self.name)
        }
    }
}

/// Information about a catalog.
#[derive(Debug, Clone)]
pub struct CatalogInfo {
    /// Catalog name.
    pub name: String,
    /// Database file size in bytes.
    pub size: i64,
    /// Database file modification time.
    pub date: i64,
}

/// Get the absolute path to a catalog's database file.
pub fn get_catalog_abspath(name: &str) -> PathBuf {
    catho_path().join(format!("{}{}", name, CATALOG_EXTENSION))
}

/// List all available catalogs.
pub fn get_catalogs() -> Result<Vec<CatalogInfo>> {
    let catho_dir = catho_path();

    if !catho_dir.exists() {
        return Ok(Vec::new());
    }

    let mut catalogs = Vec::new();

    for entry in fs::read_dir(&catho_dir)? {
        let entry = entry?;
        let path = entry.path();

        if let Some(ext) = path.extension() {
            if ext == "db" {
                if let Some(stem) = path.file_stem() {
                    let name = stem.to_string_lossy().to_string();
                    let metadata = fs::metadata(&path)?;
                    let (size, date) = (
                        metadata.len() as i64,
                        metadata
                            .modified()?
                            .duration_since(std::time::UNIX_EPOCH)
                            .map(|d| d.as_secs() as i64)
                            .unwrap_or(0),
                    );
                    catalogs.push(CatalogInfo { name, size, date });
                }
            }
        }
    }

    // Sort by name
    catalogs.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(catalogs)
}

/// Select catalogs by name, or return all if selection is empty.
pub fn select_catalogs(selection: Option<&[String]>) -> Result<Vec<String>> {
    let all_catalogs = get_catalogs()?;

    if all_catalogs.is_empty() {
        return Err(CathoError::NoCatalogs);
    }

    let all_names: Vec<String> = all_catalogs.into_iter().map(|c| c.name).collect();

    match selection {
        None | Some([]) => Ok(all_names),
        Some(names) => {
            let mut result = Vec::new();
            for name in names {
                if all_names.contains(name) {
                    result.push(name.clone());
                } else {
                    return Err(CathoError::CatalogNotFound(name.clone()));
                }
            }
            Ok(result)
        }
    }
}

/// Intermediate file entry before hashing (used for parallel processing).
#[derive(Debug, Clone)]
struct PendingFile {
    path: PathBuf,
    name: String,
    date: i64,
    size: i64,
    rel_path: String,
}

/// Iterator over files in a directory, yielding batches of FileItems.
/// Uses parallel hashing for improved performance on multi-core systems.
pub struct FileIterator {
    walker: walkdir::IntoIter,
    root: PathBuf,
    hash_type: HashType,
    batch_size: usize,
}

impl FileIterator {
    /// Create a new file iterator.
    pub fn new(root: PathBuf, hash_type: HashType) -> Self {
        Self {
            walker: WalkDir::new(&root).into_iter(),
            root,
            hash_type,
            batch_size: MAX_FILES_ITER,
        }
    }

    /// Get the next batch of file items with parallel hash calculation.
    pub fn next_batch(&mut self) -> Result<Option<Vec<FileItem>>> {
        // Phase 1: Collect file metadata (fast, sequential)
        let mut pending: Vec<PendingFile> = Vec::with_capacity(self.batch_size);

        while pending.len() < self.batch_size {
            match self.walker.next() {
                None => break,
                Some(Err(e)) => {
                    tracing::warn!("Error walking directory: {}", e);
                    continue;
                }
                Some(Ok(entry)) => {
                    // Use entry's file_type to avoid extra stat call
                    let file_type = entry.file_type();
                    if !file_type.is_file() {
                        continue;
                    }

                    // Get metadata from DirEntry (avoids extra stat call)
                    let metadata = match entry.metadata() {
                        Ok(m) => m,
                        Err(e) => {
                            tracing::warn!("Error getting metadata for {:?}: {}", entry.path(), e);
                            continue;
                        }
                    };

                    let size = metadata.len() as i64;
                    let date = metadata
                        .modified()
                        .ok()
                        .and_then(|t| t.duration_since(SystemTime::UNIX_EPOCH).ok())
                        .map(|d| d.as_secs() as i64)
                        .unwrap_or(0);

                    let path = entry.path().to_path_buf();
                    let name = path
                        .file_name()
                        .map(|n| n.to_string_lossy().to_string())
                        .unwrap_or_default();

                    let rel_path = path
                        .parent()
                        .and_then(|p| p.strip_prefix(&self.root).ok())
                        .map(|p| p.to_string_lossy().to_string())
                        .unwrap_or_else(|| ".".to_string());

                    pending.push(PendingFile {
                        path,
                        name,
                        date,
                        size,
                        rel_path,
                    });
                }
            }
        }

        if pending.is_empty() {
            return Ok(None);
        }

        // Phase 2: Calculate hashes in parallel (slow, CPU/IO bound)
        let hash_type = self.hash_type;
        let items: Vec<FileItem> = pending
            .into_par_iter()
            .map(|pf| {
                let hash = match file_hash(&pf.path, hash_type) {
                    Ok(h) => h,
                    Err(e) => {
                        tracing::warn!("Error hashing file {:?}: {}", pf.path, e);
                        None
                    }
                };
                FileItem::new(None, pf.name, pf.date, pf.size, pf.rel_path, hash)
            })
            .collect();

        Ok(Some(items))
    }
}

/// Count the total number of files in a directory.
/// Uses file_type() from DirEntry to avoid extra stat calls.
pub fn count_files(path: &Path) -> usize {
    WalkDir::new(path)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .count()
}

/// Remove catalog database files.
pub fn remove_catalog_files(names: &[String]) -> Result<()> {
    for name in names {
        let path = get_catalog_abspath(name);
        if path.exists() {
            fs::remove_file(&path)?;
            tracing::info!("Removed catalog: {}", name);
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    #[test]
    fn test_catho_path() {
        // Reset to default to test the fallback behavior
        reset_catalog_dir();
        let path = catho_path();
        assert!(path.to_string_lossy().contains("catho"));
        assert!(path.ends_with("catho/catalogs") || path.ends_with("catho\\catalogs"));
    }

    #[test]
    fn test_get_catalog_abspath() {
        let path = get_catalog_abspath("test");
        assert!(path.to_string_lossy().ends_with("test.db"));
    }

    #[test]
    fn test_file_item_full_path() {
        let item = FileItem::new(None, "file.txt".into(), 0, 100, "subdir".into(), None);
        assert_eq!(item.full_path(), "subdir/file.txt");

        let item = FileItem::new(None, "file.txt".into(), 0, 100, ".".into(), None);
        assert_eq!(item.full_path(), "file.txt");

        let item = FileItem::new(None, "file.txt".into(), 0, 100, "".into(), None);
        assert_eq!(item.full_path(), "file.txt");
    }

    #[test]
    fn test_file_iterator() {
        let temp_dir = TempDir::new().unwrap();
        fs::write(temp_dir.path().join("test.txt"), "hello").unwrap();

        let mut iter = FileIterator::new(temp_dir.path().to_path_buf(), HashType::None);
        let batch = iter.next_batch().unwrap();

        assert!(batch.is_some());
        let items = batch.unwrap();
        assert_eq!(items.len(), 1);
        assert_eq!(items[0].name, "test.txt");
    }

    #[test]
    fn test_count_files() {
        let temp_dir = TempDir::new().unwrap();
        fs::write(temp_dir.path().join("a.txt"), "a").unwrap();
        fs::write(temp_dir.path().join("b.txt"), "b").unwrap();
        fs::create_dir(temp_dir.path().join("subdir")).unwrap();
        fs::write(temp_dir.path().join("subdir/c.txt"), "c").unwrap();

        assert_eq!(count_files(temp_dir.path()), 3);
    }
}
