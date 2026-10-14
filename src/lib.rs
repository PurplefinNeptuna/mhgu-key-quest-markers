//! Native quest-row candidate. Forge supplies lifecycle, allocation and logging.
#![no_std]
extern crate alloc;
mod hooks;
mod memory;
mod native;
mod offers;
mod signatures;
use core::sync::atomic::{AtomicU32, Ordering};
static REPORTED: AtomicU32 = AtomicU32::new(0);
#[forge::entry]
fn start() {
    match hooks::install() {
        Ok(owner) => {
            core::mem::forget(owner);
            log::info!("Native quest badges installed");
        }
        Err(reason) => log::warn!("Native quest badges: {reason}"),
    }
}
/// Hot hooks publish only bit flags. Deduplicated diagnostics run in Forge's
/// regular lifecycle callback without a settings panel or config file.
#[unsafe(no_mangle)]
pub extern "C" fn forge_onUpdate(_delta: f32) {
    let errors = native::take_errors();
    let old = REPORTED.fetch_or(errors, Ordering::Relaxed);
    for (bit, message) in [
        (1, "counter GUI attachment mismatch"),
        (2, "quest singleton missing"),
        (4, "quest/progression record unavailable or conflicting"),
        (8, "counter urgent offer context unavailable"),
    ] {
        if errors & !old & bit != 0 {
            log::warn!("Native quest badges hidden: {message}");
        }
    }
}
