//! Native quest-row candidate. Forge supplies lifecycle, allocation and logging.
#![no_std]
extern crate alloc;
mod config;
mod gui;
mod hooks;
mod memory;
mod native;
mod offers;
mod purple_lib;
mod save_lock;
mod settings;
mod signatures;
mod quest_lists;
use core::sync::atomic::{AtomicU32, Ordering};
static REPORTED: AtomicU32 = AtomicU32::new(0);
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
    let label = concat!("Key Quest Markers ", env!("KQM_VERSION")).as_bytes();
    name[..label.len()].copy_from_slice(label);
    // The pinned Forge loader provides the complete writable 70-byte record.
    // This narrow ABI extension leaves vendored bindings and their pins intact.
    unsafe {
        params.cast::<PluginMetadata>().write(PluginMetadata {
            version: forge::ForgeVersion {
                major: 1,
                minor: 5,
                patch: 1,
            },
            name,
        });
    }
}
#[unsafe(no_mangle)]
pub extern "C" fn forge_onInit() {
    forge::log::init().expect("Failed to initialize Forge logger");
    settings::init();
    start();
}
fn start() {
    match hooks::install() {
        Ok(owner) => {
            core::mem::forget(owner);
            log::info!(concat!(
                "Key Quest Markers ",
                env!("KQM_VERSION"),
                " loaded"
            ));
        }
        Err(reason) => log::error!("Key Quest Markers: {reason}"),
    }
}
/// Optional: Purple-lib calls this once, from its first update, with its table of functions.
/// Without Purple-lib nothing calls it and the Plugin UI panel is the only settings page.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn purplelib_on_register(api: *const quest_badges_core::purple_lib::Api) {
    // SAFETY: Purple-lib passes its table, valid for the whole run, or null.
    let Some(api) = (unsafe { api.as_ref() }) else {
        return;
    };
    match purple_lib::register(api) {
        purple_lib::Registered::Done => log::info!("Key Quest Markers: setting added to Purple-lib Mod Options"),
        purple_lib::Registered::Repeated => {}
        purple_lib::Registered::OlderVersion(version) => log::warn!(
            "Key Quest Markers: Purple-lib API version {version} is older than {}; Mod Options not added",
            quest_badges_core::purple_lib::API_VERSION
        ),
        purple_lib::Registered::Refused => log::warn!("Key Quest Markers: Purple-lib refused the Mod Options page"),
    }
}
/// Native hooks publish failure bits only. Report each genuine failure once
/// here; successful row updates never generate log lines or retain snapshots.
#[unsafe(no_mangle)]
pub extern "C" fn forge_onUpdate(delta: f32) {
    settings::update(delta);
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
            if bit == 16 || bit == 64 {
                let stage = gui::take_failure();
                log::error!("Key Quest Markers hidden: {message}; stage={stage}");
            } else {
                log::error!("Key Quest Markers hidden: {message}");
            }
        }
    }
}

/// Forge supplies the live ImGui context and its matching allocator pair. They
/// remain loader-owned; no game GUI pointers enter the settings interface.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn forge_onImGuiInit(
    ctx: *mut core::ffi::c_void,
    alloc: *mut core::ffi::c_void,
    free: *mut core::ffi::c_void,
) {
    if ctx.is_null() || alloc.is_null() || free.is_null() {
        return;
    }
    unsafe {
        forge::imgui::set_current_context(&mut *ctx.cast());
        forge::imgui::set_allocator_functions(
            core::mem::transmute(alloc),
            core::mem::transmute(free),
        );
    }
}
#[forge::imgui_render]
fn panel() {
    settings::panel();
}
