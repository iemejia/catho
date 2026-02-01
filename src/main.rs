//! Catho - A command-line file catalog manager.

mod catalog;
mod cli;
mod db;
mod error;
mod file;
mod utils;

#[cfg(feature = "web")]
mod web;

use std::fs::File;
use std::io::Write;
use std::process::ExitCode;

use clap::CommandFactory;
use tracing_subscriber::EnvFilter;

use crate::catalog::{
    create_catalog, export_catalog, find_in_catalogs, find_regex_in_catalogs, format_catalog_info,
    format_catalog_list, format_search_results, list_catalogs, remove_catalogs, scan_catalogs,
    update_catalog,
};
use crate::cli::{Cli, Commands};
use crate::db::{db_get_catalog, db_get_metadata};
use crate::error::CathoError;
use crate::utils::HashType;

fn main() -> ExitCode {
    let cli = Cli::parse_args();

    // Set custom catalog directory from CATHO_DIR env var if set
    if let Ok(dir) = std::env::var("CATHO_DIR") {
        crate::file::set_catalog_dir(std::path::PathBuf::from(dir));
    }

    // Setup logging
    let log_level = if cli.silent {
        "off"
    } else if cli.verbose {
        "debug"
    } else {
        "info"
    };

    let subscriber = tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::new(log_level))
        .with_target(false)
        .with_writer(std::io::stderr);

    if let Some(ref log_file) = cli.log_file {
        // Log to file
        if let Ok(file) = File::create(log_file) {
            let subscriber = tracing_subscriber::fmt()
                .with_env_filter(EnvFilter::new(log_level))
                .with_target(false)
                .with_writer(file)
                .with_ansi(false);
            subscriber.init();
        } else {
            subscriber.init();
            tracing::warn!("Could not create log file: {}", log_file);
        }
    } else {
        subscriber.init();
    }

    match run_command(cli.command) {
        Ok(()) => ExitCode::SUCCESS,
        Err(e) => {
            tracing::error!("{}", e);
            ExitCode::FAILURE
        }
    }
}

fn run_command(command: Option<Commands>) -> Result<(), CathoError> {
    match command {
        None => {
            // No command, show help
            Cli::command().print_help().ok();
            println!();
            Ok(())
        }

        Some(Commands::Add {
            name,
            path,
            force,
            hash_type,
            update,
        }) => {
            let hash = HashType::from_str(&hash_type)
                .ok_or_else(|| CathoError::InvalidHashType(hash_type))?;

            if update {
                update_catalog(&name)?;
            } else {
                create_catalog(&name, &path, hash, force)?;
            }
            Ok(())
        }

        Some(Commands::List { names }) => {
            if names.is_empty() {
                // List all catalogs
                let catalogs = list_catalogs()?;
                println!("{}", format_catalog_list(&catalogs));
            } else {
                // Show detailed info for specified catalogs
                for name in &names {
                    let metadata = db_get_metadata(name)?;
                    let files = db_get_catalog(name)?;
                    let total_size: i64 = files.iter().map(|f| f.size).sum();
                    println!(
                        "{}",
                        format_catalog_info(name, &metadata, files.len(), total_size)
                    );
                }
            }
            Ok(())
        }

        Some(Commands::Remove { names }) => {
            remove_catalogs(&names)?;
            for name in &names {
                println!("Removed catalog: {}", name);
            }
            Ok(())
        }

        Some(Commands::Find {
            pattern,
            catalogs,
            regex,
        }) => {
            let catalog_refs: Option<&[String]> = if catalogs.is_empty() {
                None
            } else {
                Some(&catalogs)
            };

            let results = if regex {
                find_regex_in_catalogs(&pattern, catalog_refs)?
            } else {
                find_in_catalogs(&pattern, catalog_refs)?
            };

            println!("{}", format_search_results(&results));
            Ok(())
        }

        Some(Commands::Scan { path }) => {
            let results = scan_catalogs(&path)?;
            println!("{}", format_search_results(&results));
            Ok(())
        }

        Some(Commands::Export { name, output }) => {
            let exported = export_catalog(&name)?;
            let json = serde_json::to_string_pretty(&exported)?;

            match output {
                Some(path) => {
                    let mut file = File::create(&path)?;
                    file.write_all(json.as_bytes())?;
                    println!("Exported catalog '{}' to {}", name, path);
                }
                None => {
                    println!("{}", json);
                }
            }
            Ok(())
        }

        #[cfg(feature = "web")]
        Some(Commands::Web { port, host }) => {
            let rt = tokio::runtime::Runtime::new().map_err(CathoError::Io)?;

            rt.block_on(async {
                web::run_server(&host, port)
                    .await
                    .map_err(|e| CathoError::Io(std::io::Error::other(e.to_string())))
            })
        }
    }
}
