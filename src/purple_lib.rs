//! Optional: the "Grey badges" setting (Coloured, Grey, Hidden) in Purple-lib's Mod Options.
//! Purple-lib calls the plugin's `purplelib_on_register` with its table of functions at start-up; without Purple-lib
//! nothing calls it, this module does nothing and the Plugin UI panel stays the only way to
//! change the setting.
//!
//! Purple-lib calls `get` and `set` inside the game's update, so they only touch the atomic
//! setting the row hook reads; `settings::update` picks up `EDITED` and `SAVE` from
//! `forge_onUpdate` and does the locking and the INI work there.
use crate::settings;
use core::ffi::{c_char, c_void};
use core::sync::atomic::{AtomicBool, Ordering};
use quest_badges_core::colors::GreyBadges;
use quest_badges_core::purple_lib::{self as api, Api, OptionRow, Options};

/// A value changed through Mod Options: the preferences take it over.
pub static EDITED: AtomicBool = AtomicBool::new(false);
/// Mod Options closed after a change: save the INI.
pub static SAVE: AtomicBool = AtomicBool::new(false);

extern "C" fn title(_: *mut c_void, _: u32) -> *const c_char {
    api::TITLE.as_ptr()
}

/// Read-only records of static data; no context is ever dereferenced.
struct Shared<T>(T);
// SAFETY: see above.
unsafe impl<T> Sync for Shared<T> {}
static LABELS: Shared<[*const c_char; 3]> = Shared([
    api::GREY_LABELS[0].as_ptr(),
    api::GREY_LABELS[1].as_ptr(),
    api::GREY_LABELS[2].as_ptr(),
]);

extern "C" fn row(_: *mut c_void, _: u32, index: u32, out: *mut OptionRow) -> bool {
    if index != api::ROW_GREY_BADGES || out.is_null() {
        return false;
    }
    // SAFETY: Purple-lib passes a writable `OptionRow`, zeroed before the call.
    unsafe {
        (*out).name = api::GREY_NAME.as_ptr();
        (*out).help = api::GREY_HELP.as_ptr();
        (*out).labels = LABELS.0.as_ptr();
        (*out).label_count = LABELS.0.len() as u32;
    }
    true
}

extern "C" fn get(_: *mut c_void, _: u32) -> u32 {
    settings::grey_badges() as u32
}

/// Applied at once: the next row update reads the new value.
extern "C" fn set(_: *mut c_void, index: u32, value: u32) {
    if index != api::ROW_GREY_BADGES {
        return;
    }
    if let Some(grey) = GreyBadges::from_value(value) {
        settings::set_grey_badges(grey);
        EDITED.store(true, Ordering::Release);
    }
}

extern "C" fn closed(_: *mut c_void) {
    SAVE.store(true, Ordering::Release);
}

static OPTIONS: Shared<Options> = Shared(Options {
    size: core::mem::size_of::<Options>() as u32,
    context: core::ptr::null_mut(),
    title: Some(title),
    row_count: api::ROWS,
    row: Some(row),
    get: Some(get),
    set: Some(set),
    closed: Some(closed),
    value_text: None,
    action: None,
});

pub enum Registered {
    /// Purple-lib is older than `API_VERSION`; nothing was registered.
    OlderVersion(u32),
    Refused,
    Done,
    /// A second call: the first one's registration stands.
    Repeated,
}

/// Register through Purple-lib's table, from `purplelib_on_register`: the one time Purple-lib
/// accepts records, during its first update.
pub fn register(purple: &Api) -> Registered {
    static CALLED: AtomicBool = AtomicBool::new(false);
    // A later Purple-lib still reads this record, by its `size`; an older one lacks the API.
    if purple.version < api::API_VERSION {
        return Registered::OlderVersion(purple.version);
    }
    if CALLED.swap(true, Ordering::AcqRel) {
        return Registered::Repeated;
    }
    if (purple.add_options)(&OPTIONS.0) {
        Registered::Done
    } else {
        Registered::Refused
    }
}
