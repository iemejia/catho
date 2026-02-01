//! Utility functions for catho.

use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::Path;

use crate::error::Result;

/// Block size for reading files during hashing (1 MB).
pub const BLOCK_SIZE: usize = 1_048_576;

/// Hash type for file hashing.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum HashType {
    /// SHA-256 hash.
    #[default]
    Sha256,
    /// No hashing.
    None,
}

impl HashType {
    /// Parse a hash type from a string.
    pub fn from_str(s: &str) -> Option<Self> {
        match s.to_lowercase().as_str() {
            "sha256" => Some(Self::Sha256),
            "none" => Some(Self::None),
            _ => None,
        }
    }

    /// Convert to string representation.
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Sha256 => "sha256",
            Self::None => "none",
        }
    }
}

impl std::fmt::Display for HashType {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.as_str())
    }
}

/// Calculate SHA-256 hash of a file.
pub fn file_hash(path: &Path, hash_type: HashType) -> Result<Option<String>> {
    match hash_type {
        HashType::None => Ok(None),
        HashType::Sha256 => {
            let file = File::open(path)?;
            let mut reader = BufReader::with_capacity(BLOCK_SIZE, file);
            let mut hasher = Sha256::new();
            let mut buffer = vec![0u8; BLOCK_SIZE];

            loop {
                let bytes_read = reader.read(&mut buffer)?;
                if bytes_read == 0 {
                    break;
                }
                hasher.update(&buffer[..bytes_read]);
            }

            let result = hasher.finalize();
            Ok(Some(format!("{:x}", result)))
        }
    }
}

/// Format a size in bytes as a human-readable string.
pub fn sizeof_fmt(num: i64) -> String {
    const UNITS: &[&str] = &["bytes", "KB", "MB", "GB", "TB", "PB"];
    let mut num = num as f64;

    for unit in UNITS {
        if num < 1024.0 {
            return format!("{:.1} {}", num, unit);
        }
        num /= 1024.0;
    }

    format!("{:.1} PB", num)
}

/// Format a Unix timestamp as a human-readable date string (YYYY-MM-DD).
pub fn format_date(timestamp: i64) -> String {
    use time::{OffsetDateTime, UtcOffset};

    OffsetDateTime::from_unix_timestamp(timestamp)
        .map(|dt| dt.to_offset(UtcOffset::UTC))
        .map(|dt| format!("{:04}-{:02}-{:02}", dt.year(), dt.month() as u8, dt.day()))
        .unwrap_or_else(|_| "unknown".to_string())
}

/// Truncate a hash string for display purposes.
/// Returns the first `max_len` characters, or "-" if the hash is None.
pub fn truncate_hash(hash: Option<&str>, max_len: usize) -> &str {
    hash.map_or("-", |h| if h.len() > max_len { &h[..max_len] } else { h })
}

/// Create directory and parents if they don't exist.
pub fn touch_dir(path: &Path) -> Result<()> {
    fs::create_dir_all(path)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sizeof_fmt() {
        assert_eq!(sizeof_fmt(0), "0.0 bytes");
        assert_eq!(sizeof_fmt(1023), "1023.0 bytes");
        assert_eq!(sizeof_fmt(1024), "1.0 KB");
        assert_eq!(sizeof_fmt(1_048_576), "1.0 MB");
        assert_eq!(sizeof_fmt(1_073_741_824), "1.0 GB");
    }

    #[test]
    fn test_hash_type_from_str() {
        assert_eq!(HashType::from_str("sha256"), Some(HashType::Sha256));
        assert_eq!(HashType::from_str("SHA256"), Some(HashType::Sha256));
        assert_eq!(HashType::from_str("none"), Some(HashType::None));
        assert_eq!(HashType::from_str("None"), Some(HashType::None));
        assert_eq!(HashType::from_str("invalid"), None);
    }

    #[test]
    fn test_hash_type_as_str() {
        assert_eq!(HashType::Sha256.as_str(), "sha256");
        assert_eq!(HashType::None.as_str(), "none");
    }

    #[test]
    fn test_format_date() {
        // Unix epoch
        assert_eq!(format_date(0), "1970-01-01");
        // Known dates
        assert_eq!(format_date(1704067200), "2024-01-01"); // Jan 1, 2024
        assert_eq!(format_date(1735689600), "2025-01-01"); // Jan 1, 2025
        assert_eq!(format_date(1609459200), "2021-01-01"); // Jan 1, 2021
    }

    #[test]
    fn test_truncate_hash() {
        assert_eq!(truncate_hash(None, 8), "-");
        assert_eq!(truncate_hash(Some("abcdef"), 8), "abcdef");
        assert_eq!(truncate_hash(Some("abcdefghij"), 8), "abcdefgh");
        assert_eq!(truncate_hash(Some(""), 8), "");
    }
}
