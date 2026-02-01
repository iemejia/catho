//! Utility functions for catho.

use sha2::{Digest, Sha256};
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::Path;
use std::time::SystemTime;

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

/// Get file metadata (size and modification time).
pub fn get_file_info(path: &Path) -> Result<(u64, i64)> {
    let metadata = fs::metadata(path)?;
    let size = metadata.len();
    let mtime = metadata
        .modified()?
        .duration_since(SystemTime::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    Ok((size, mtime))
}

/// Format a size in bytes as a human-readable string.
pub fn sizeof_fmt(num: u64) -> String {
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

/// Format a Unix timestamp as a human-readable date string.
pub fn format_date(timestamp: i64) -> String {
    use std::time::{Duration, UNIX_EPOCH};

    let datetime = UNIX_EPOCH + Duration::from_secs(timestamp as u64);

    // Simple formatting without external crate
    if let Ok(duration) = datetime.duration_since(UNIX_EPOCH) {
        let secs = duration.as_secs();
        // Calculate date components
        let days = secs / 86400;
        let years = 1970 + days / 365;
        let remaining_days = days % 365;
        let months = remaining_days / 30 + 1;
        let day = remaining_days % 30 + 1;

        return format!("{:04}-{:02}-{:02}", years, months, day);
    }

    "unknown".to_string()
}

/// Create directory and parents if they don't exist.
pub fn touch_dir(path: &Path) -> Result<()> {
    fs::create_dir_all(path)?;
    Ok(())
}

/// Remove a file or empty directory.
#[allow(dead_code)]
pub fn remove_path(path: &Path) -> Result<()> {
    if path.is_dir() {
        fs::remove_dir(path)?;
    } else {
        fs::remove_file(path)?;
    }
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
}
