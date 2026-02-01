//! Web UI for catho (optional feature).

#[cfg(feature = "web")]
pub mod server;

#[cfg(feature = "web")]
pub use server::run_server;
