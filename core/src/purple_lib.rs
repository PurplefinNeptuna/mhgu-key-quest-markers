//! Optional settings page in Purple-lib's Mod Options (its `API.md`). Purple-lib calls the
//! plugin's `purplelib_on_register` with its table of functions; without Purple-lib nothing here
//! runs. The records and the table mirror Purple-lib's API version 3 (Purple-lib r17 and later); a
//! later API version still reads them. The row text is here so the host tests can check it.
use core::ffi::{CStr, c_char, c_void};

pub const API_VERSION: u32 = 3;

#[repr(C)]
/// Purple-lib zeroes it before each call; the one row here is a labels row, which uses the first
/// four fields.
pub struct OptionRow {
    pub name: *const c_char,
    pub help: *const c_char,
    pub labels: *const *const c_char,
    pub label_count: u32,
    pub kind: u32,
    pub value_count: u32,
    pub first: i32,
    pub step: i32,
    pub suffix: *const c_char,
    pub flags: u32,
}

#[repr(C)]
pub struct Options {
    pub size: u32,
    pub context: *mut c_void,
    pub title: Option<extern "C" fn(*mut c_void, u32) -> *const c_char>,
    pub row_count: u32,
    pub row: Option<extern "C" fn(*mut c_void, u32, u32, *mut OptionRow) -> bool>,
    pub get: Option<extern "C" fn(*mut c_void, u32) -> u32>,
    pub set: Option<extern "C" fn(*mut c_void, u32, u32)>,
    pub closed: Option<extern "C" fn(*mut c_void)>,
    /// For text rows and action rows, which this page does not use.
    pub value_text: Option<extern "C" fn(*mut c_void, u32, u32, u32) -> *const c_char>,
    pub action: Option<extern "C" fn(*mut c_void, u32)>,
}

#[repr(C)]
pub struct Help {
    pub size: u32,
    pub context: *mut c_void,
    pub category: u32,
    pub page_count: u32,
    pub title: Option<extern "C" fn(*mut c_void, u32) -> *const c_char>,
    pub page: Option<extern "C" fn(*mut c_void, u32, u32) -> *const c_char>,
    pub open: Option<extern "C" fn(*mut c_void)>,
}

/// Purple-lib's functions, as it passes them to `purplelib_on_register`; valid for the whole run.
#[repr(C)]
pub struct Api {
    pub version: u32,
    pub add_options: extern "C" fn(*const Options) -> bool,
    pub add_help: extern "C" fn(*const Help) -> bool,
    pub hold_input: extern "C" fn(),
    pub options_shown: extern "C" fn(*const Options) -> bool,
    pub options_row: extern "C" fn(*const Options) -> i32,
    pub add_set_help: extern "C" fn(*const Options, *const Help) -> bool,
}

#[cfg(target_pointer_width = "32")]
const _: () = assert!(
    core::mem::size_of::<Options>() == 40
        && core::mem::size_of::<Help>() == 28
        && core::mem::size_of::<OptionRow>() == 40
        && core::mem::size_of::<Api>() == 28
);

/// Purple-lib keeps every pointer it is given, so all text is static. Every language shows the
/// English text: the mod ships no translations.
pub const TITLE: &CStr = c"Key Quest Markers";
pub const ROW_GREY_BADGES: u32 = 0;
pub const ROWS: u32 = 1;
pub const GREY_NAME: &CStr = c"Gray badges";
pub const GREY_HELP: &CStr = c"Colored keeps cleared quests' color.\r\nHidden removes gray badges.";
/// Indexed by the row's value, which is `GreyBadges as u32`: Colored, Gray, Hidden.
pub const GREY_LABELS: [&CStr; 3] = [c"Colored", c"Gray", c"Hidden"];
