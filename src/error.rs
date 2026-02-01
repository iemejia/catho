//! Error types for catho.

use std::path::PathBuf;
use thiserror::Error;

/// Result type alias for catho operations.
pub type Result<T> = std::result::Result<T, CathoError>;

/// Errors that can occur in catho operations.
#[derive(Error, Debug)]
pub enum CathoError {
    /// Catalog already exists.
    #[error("catalog '{0}' already exists (use --force to overwrite)")]
    CatalogExists(String),

    /// Catalog not found.
    #[error("catalog '{0}' not found")]
    CatalogNotFound(String),

    /// Invalid catalog name.
    #[error("invalid catalog name: '{0}'")]
    #[allow(dead_code)]
    InvalidCatalogName(String),

    /// Path not found.
    #[error("path not found: {0}")]
    PathNotFound(PathBuf),

    /// Path is not a directory.
    #[error("path is not a directory: {0}")]
    NotADirectory(PathBuf),

    /// Invalid hash type.
    #[error("invalid hash type: '{0}' (valid types: sha256, none)")]
    InvalidHashType(String),

    /// Database error.
    #[error("database error: {0}")]
    Database(#[from] rusqlite::Error),

    /// IO error.
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    /// Walk directory error.
    #[error("directory walk error: {0}")]
    WalkDir(#[from] walkdir::Error),

    /// Regex error.
    #[error("regex error: {0}")]
    Regex(#[from] regex::Error),

    /// JSON error.
    #[error("JSON error: {0}")]
    Json(#[from] serde_json::Error),

    /// No catalogs available.
    #[error("no catalogs available")]
    NoCatalogs,
}
