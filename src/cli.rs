//! Command-line interface for catho.

use clap::{Parser, Subcommand};

/// A command-line file catalog manager for indexing and searching files across media.
#[derive(Parser, Debug)]
#[command(name = "catho")]
#[command(version, about, long_about = None)]
pub struct Cli {
    /// Enable verbose output (debug logging).
    #[arg(short, long, global = true)]
    pub verbose: bool,

    /// Suppress all output.
    #[arg(short, long, global = true)]
    pub silent: bool,

    /// Log output to a file.
    #[arg(short = 'l', long = "create-log", global = true)]
    pub log_file: Option<String>,

    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Create a new catalog by indexing a directory.
    Add {
        /// Name of the catalog to create.
        name: String,

        /// Path to the directory to index.
        path: String,

        /// Force overwrite if catalog already exists.
        #[arg(short, long)]
        force: bool,

        /// Hash type to use: sha256 (default) or none.
        #[arg(short = 'H', long = "hash-type", default_value = "sha256")]
        hash_type: String,

        /// Update existing catalog instead of creating new.
        #[arg(short = 'c', long = "continue")]
        update: bool,
    },

    /// List available catalogs or show detailed info.
    #[command(name = "ls")]
    List {
        /// Catalog names to show detailed info for.
        #[arg(num_args = 0..)]
        names: Vec<String>,
    },

    /// Remove catalog(s).
    #[command(name = "rm")]
    Remove {
        /// Catalog names to remove.
        #[arg(required = true, num_args = 1..)]
        names: Vec<String>,
    },

    /// Find files matching a pattern.
    Find {
        /// Pattern to search for (supports * wildcard).
        pattern: String,

        /// Catalogs to search in (all if not specified).
        #[arg(num_args = 0..)]
        catalogs: Vec<String>,

        /// Use regex pattern instead of wildcard.
        #[arg(short, long)]
        regex: bool,
    },

    /// Scan a file/directory and find matches by hash.
    Scan {
        /// Path to file or directory to scan.
        path: String,
    },

    /// Export a catalog to JSON format.
    Export {
        /// Catalog name to export.
        name: String,

        /// Output file (stdout if not specified).
        #[arg(short, long)]
        output: Option<String>,
    },

    /// Start the web UI server.
    #[cfg(feature = "web")]
    Web {
        /// Port to listen on.
        #[arg(short, long, default_value = "8080")]
        port: u16,

        /// Host to bind to.
        #[arg(long, default_value = "127.0.0.1")]
        host: String,
    },
}

impl Cli {
    /// Parse command line arguments.
    pub fn parse_args() -> Self {
        Self::parse()
    }
}
