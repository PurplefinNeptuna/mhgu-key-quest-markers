//! Native quest-row candidate. Forge supplies lifecycle, allocation and logging.
#![no_std]
extern crate alloc;
mod gui;
mod hooks;
mod memory;
mod native;
mod offers;
mod signatures;
use core::sync::atomic::{AtomicU32, Ordering};
static REPORTED: AtomicU32 = AtomicU32::new(0);
static REPORTED_ENTRIES: AtomicU32 = AtomicU32::new(0);
// forge-rs exposes only the six-byte version prefix. The matching native loader
// also owns name[64] at offset 6 and hides empty names in its Loaded Plugins list.
#[repr(C)]
struct PluginMetadata {
    version: forge::ForgeVersion,
    name: [u8; 64],
}
const _: () = assert!(
    core::mem::size_of::<PluginMetadata>() == 70
        && core::mem::offset_of!(PluginMetadata, name) == 6
);
#[unsafe(no_mangle)]
pub unsafe extern "C" fn forge_onLoad(params: *mut forge::PluginInitParams) {
    if params.is_null() {
        return;
    }
    let mut name = [0; 64];
    let label = b"Native Quest Badges r11";
    name[..label.len()].copy_from_slice(label);
    // The pinned Forge loader provides the complete writable 70-byte record.
    // This narrow ABI extension leaves vendored bindings and their pins intact.
    unsafe {
        params.cast::<PluginMetadata>().write(PluginMetadata {
            version: forge::REQUIRED_VERSION,
            name,
        });
    }
}
#[unsafe(no_mangle)]
pub extern "C" fn forge_onInit() {
    forge::log::init().expect("Failed to initialize Forge logger");
    start();
}
fn start() {
    match hooks::install() {
        Ok(owner) => {
            core::mem::forget(owner);
            // DEVELOPMENT diagnostics use ERROR so the user's existing error-only
            // Forge filter records this result without changing their settings.
            log::error!(
                "Native quest badges r11 diagnostic: hooks installed; waiting for quest counter"
            );
        }
        Err(reason) => log::error!("Native quest badges: {reason}"),
    }
}
/// Hot hooks publish only bit flags. Deduplicated diagnostics run in Forge's
/// regular lifecycle callback without a settings panel or config file.
#[unsafe(no_mangle)]
pub extern "C" fn forge_onUpdate(_delta: f32) {
    let entered = hooks::entered();
    let previous = REPORTED_ENTRIES.fetch_or(entered, Ordering::Relaxed);
    for (bit, label) in [(1, "urgent parent"), (2, "quest row")] {
        if entered & !previous & bit != 0 {
            log::error!("Native quest badges r11 diagnostic: entered {label} hook");
        }
    }
    native::report_diagnostics();
    let errors = native::take_errors();
    let old = REPORTED.fetch_or(errors, Ordering::Relaxed);
    for (bit, message) in [
        (1, "counter GUI holder unavailable"),
        (2, "quest singleton missing"),
        (4, "quest/progression record unavailable or conflicting"),
        (8, "counter urgent offer context unavailable"),
        (
            16,
            "native badge object/cache allocation or initialization failed",
        ),
        (64, "native row/HD atlas validation failed"),
        (128, "request/title binding invalid; affected badge hidden"),
    ] {
        if errors & !old & bit != 0 {
            log::error!("Native quest badges hidden: {message}");
            if bit == 16 {
                let stage = gui::take_failure();
                log::error!(
                    "Native quest badge creation stage {stage}: 1=MT allocation, 2=constructor result, 3=destructor, 4=object type/fields, 5=texture binding, 6=cache methods, 7=cache allocation, 8=cache memory, 9=object map allocation"
                );
            }
            if bit == 64 {
                let stage = gui::take_failure();
                log::error!(
                    "Native quest badge validation stage {stage}: 1=instance, 2=root/type, 3=animation, 4=cache, 5=parent/icon, 6=GUI owner, 7=HD atlas, 8=child chain"
                );
            }
        }
    }
}
