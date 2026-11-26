//! Forge settings callbacks own drafts and file I/O; native hooks only copy RGB words.
use crate::config::Storage;
use core::{
    cell::UnsafeCell,
    sync::atomic::{AtomicU8, AtomicU32, Ordering},
};
use forge::os::{lock::ScopedLock, mutex::Mutex, once_lock::OnceLock};
use quest_badges_core::colors::{Error, GreyBadges, Palette, Preferences};
// Independent settings use atomic words so game hooks never borrow the UI or
// wait for its mutex. Each row-builder invocation copies the five words once.
core::arch::global_asm!(".hidden kqm_palette");
#[unsafe(no_mangle)]
pub static kqm_palette: [AtomicU32; 5] = [
    AtomicU32::new(Palette::DEFAULT.key),
    AtomicU32::new(Palette::DEFAULT.urgent),
    AtomicU32::new(Palette::DEFAULT.completed),
    AtomicU32::new(Palette::DEFAULT.unlocks),
    AtomicU32::new(Palette::DEFAULT.reward),
];
/// How grey badges show (`GreyBadges as u8`); read by the row hook and by Mod Options `get`,
/// written without locks.
static GREY: AtomicU8 = AtomicU8::new(Palette::DEFAULT.grey as u8);
/// Shown badge kinds, bit i for `colors::KINDS[i]`; read and written like `GREY`.
static SHOWN: AtomicU8 = AtomicU8::new(0b1111);
pub fn palette() -> Palette {
    Palette {
        key: kqm_palette[0].load(Ordering::Acquire),
        urgent: kqm_palette[1].load(Ordering::Acquire),
        completed: kqm_palette[2].load(Ordering::Acquire),
        unlocks: kqm_palette[3].load(Ordering::Acquire),
        reward: kqm_palette[4].load(Ordering::Acquire),
        grey: grey_badges(),
        shown: shown_kinds(),
    }
}
pub fn shown_kinds() -> [bool; 4] {
    let bits = SHOWN.load(Ordering::Acquire);
    core::array::from_fn(|i| bits & (1 << i) != 0)
}
fn shown_bits(shown: [bool; 4]) -> u8 {
    shown.iter().enumerate().map(|(i, &on)| (on as u8) << i).sum()
}
/// Mod Options `set` for one badge kind: applies at once, like `set_grey_badges`.
pub fn set_shown(kind: usize, on: bool) {
    let mut shown = shown_kinds();
    if let Some(slot) = shown.get_mut(kind) {
        *slot = on;
        SHOWN.store(shown_bits(shown), Ordering::Release);
    }
}
pub fn grey_badges() -> GreyBadges {
    GreyBadges::from_value(GREY.load(Ordering::Acquire) as u32).unwrap_or(Palette::DEFAULT.grey)
}
/// Mod Options `set`: applies at once; `update` then records it in the preferences.
pub fn set_grey_badges(grey: GreyBadges) {
    GREY.store(grey as u8, Ordering::Release);
}
/// Panel radio buttons, in the Mod Options row's order: Colored, Gray, Hidden.
const GREY_LABELS: [&core::ffi::CStr; 3] = [
    c"Colored##kqm-gray-colored",
    c"Gray##kqm-gray-gray",
    c"Hidden##kqm-gray-hidden",
];
/// Panel check boxes, in `colors::KINDS` order.
const SHOWN_LABELS: [&core::ffi::CStr; 4] = [
    c"Key##kqm-show-key",
    c"Urgent##kqm-show-urgent",
    c"Gives a reward##kqm-show-reward",
    c"Unlocks a quest##kqm-show-unlocks",
];
fn publish(p: Palette) {
    for (slot, value) in kqm_palette.iter().zip([p.key, p.urgent, p.completed, p.unlocks, p.reward]) {
        slot.store(value, Ordering::Release);
    }
    GREY.store(p.grey as u8, Ordering::Release);
    SHOWN.store(shown_bits(p.shown), Ordering::Release);
}
struct State {
    preferences: Preferences,
    feedback: &'static str,
    retry: f32,
    reported: u32,
    /// Mod Options closed after a change and the INI is not saved yet.
    save_pending: bool,
    /// Save & apply met a busy save lock or no save yet: the draft is saved on a later update.
    panel_pending: bool,
}
struct Shared {
    lock: Mutex,
    value: UnsafeCell<State>,
}
// SAFETY: value is accessed exclusively through with_state under its Forge
// mutex. Native callbacks access only the separate atomic RGB words.
unsafe impl Sync for Shared {}
unsafe impl Send for Shared {}
static STATE: OnceLock<Shared> = OnceLock::new();
pub fn init() {
    STATE.get_or_init(|| Shared {
        lock: Mutex::new(),
        value: UnsafeCell::new(State {
            preferences: Preferences::new(),
            feedback: "",
            retry: 0.0,
            reported: 0,
            save_pending: false,
            panel_pending: false,
        }),
    });
}
fn with_state(f: impl FnOnce(&mut State)) {
    if let Some(shared) = STATE.get() {
        let _guard = ScopedLock::new(&shared.lock);
        f(unsafe { &mut *shared.value.get() });
    }
}
/// Retry unavailable storage at most once per second. An edit or reset marks
/// loading complete, preventing a later disk read from replacing the draft.
pub fn update(delta: f32) {
    with_state(|state| {
        if crate::purple_lib::EDITED.swap(false, Ordering::AcqRel) {
            state.preferences.apply_grey(grey_badges());
            state.preferences.apply_shown(shown_kinds());
        }
        if crate::purple_lib::SAVE.swap(false, Ordering::AcqRel) {
            state.save_pending = true;
            state.retry = 0.0;
        }
        if state.preferences.loaded && !state.save_pending && !state.panel_pending {
            return;
        }
        state.retry -= if delta.is_finite() && delta > 0.0 {
            delta.min(1.0)
        } else {
            1.0 / 60.0
        };
        if state.retry > 0.0 {
            return;
        }
        state.retry = 1.0;
        if state.panel_pending {
            save_draft(state);
            return;
        }
        if state.save_pending {
            save_applied(state);
            return;
        }
        match state.preferences.load(&mut Storage::new()) {
            Ok(()) => {
                publish(state.preferences.applied);
                state.feedback = "Colors loaded";
            }
            Err(Error::Unavailable) => {}
            Err(reason) => {
                state.feedback = reason.message();
            }
        }
    });
}
/// Save after a Mod Options change; storage that is not ready yet is retried once a second.
fn save_applied(state: &mut State) {
    match state.preferences.save_applied(&mut Storage::new()) {
        Ok(()) => {
            state.save_pending = false;
            publish(state.preferences.applied);
            state.feedback = "Saved key_quest_markers.ini";
        }
        Err(Error::Unavailable) => {}
        Err(reason) => {
            state.save_pending = false;
            publish(state.preferences.applied);
            state.feedback = reason.message();
            report(state, reason);
        }
    }
}
/// Save & apply. The game's save lock may be busy, or no save loaded yet: the draft then stays
/// pending and `update` tries again once a second.
fn save_draft(state: &mut State) {
    match state.preferences.save(&mut Storage::new()) {
        Ok(()) => {
            // The draft holds any Mod Options change too, so a pending Mod Options save is done.
            state.panel_pending = false;
            state.save_pending = false;
            publish(state.preferences.applied);
            state.feedback = "Saved and applied key_quest_markers.ini";
        }
        Err(Error::Unavailable) => {
            state.panel_pending = true;
            state.feedback = "Saving as soon as the game's save storage is free";
        }
        Err(reason) => {
            state.panel_pending = false;
            state.feedback = reason.message();
            report(state, reason);
        }
    }
}
fn report(state: &mut State, reason: Error) {
    let bit = 1u32 << (reason as u32);
    if state.reported & bit == 0 {
        state.reported |= bit;
        log::warn!("Key Quest Markers: {}", reason.message());
    }
}
fn rgb(value: u32) -> [f32; 3] {
    [
        (value >> 16) as f32 / 255.0,
        ((value >> 8) & 255) as f32 / 255.0,
        (value & 255) as f32 / 255.0,
    ]
}
fn packed(value: [f32; 3]) -> Option<u32> {
    if value.iter().any(|v| !v.is_finite()) {
        return None;
    }
    let c = value.map(|v| (v.clamp(0.0, 1.0) * 255.0 + 0.5) as u32);
    Some((c[0] << 16) | (c[1] << 8) | c[2])
}
/// Invoked inside Forge's Plugin UI. The paired guard preserves TreePop on
/// every opened path; closing this settings tree never disables native badges.
pub fn panel() {
    use forge::{
        imgui as ui,
        sys::imgui::{ImGuiColorEditFlags as Flags, ImVec2},
    };
    if !ui::tree_node(c"Key Quest Markers###key-quest-markers") {
        return;
    }
    struct Tree;
    impl Drop for Tree {
        fn drop(&mut self) {
            ui::tree_pop();
        }
    }
    let _tree = Tree;
    with_state(|state| {
        let mut draft = state.preferences.draft;
        let mut changed = false;
        for (label, value) in [
            (c"Key##kqm-key", &mut draft.key),
            (c"Urgent##kqm-urgent", &mut draft.urgent),
            (c"Completed##kqm-completed", &mut draft.completed),
            (c"Unlocks a quest##kqm-unlocks", &mut draft.unlocks),
            (c"Gives a reward##kqm-reward", &mut draft.reward),
        ] {
            let mut components = rgb(*value);
            if ui::color_edit3(label, &mut components, Flags::DisplayHex | Flags::Uint8) {
                if let Some(rgb) = packed(components) {
                    *value = rgb;
                    changed = true;
                }
            }
        }
        ui::text("Show badges");
        for (i, label) in SHOWN_LABELS.into_iter().enumerate() {
            if i > 0 {
                ui::same_line(0.0, -1.0);
            }
            if ui::checkbox(label, &mut draft.shown[i]) {
                changed = true;
            }
        }
        ui::text("Finished quests");
        for (i, (mode, label)) in GreyBadges::ALL.into_iter().zip(GREY_LABELS).enumerate() {
            if i > 0 {
                ui::same_line(0.0, -1.0);
            }
            if ui::radio_button(label, draft.grey == mode) && draft.grey != mode {
                draft.grey = mode;
                changed = true;
            }
        }
        if ui::button(c"Reset defaults##kqm-reset", ImVec2::new(0.0, 0.0)) {
            draft = Palette::DEFAULT;
            changed = true;
        }
        if changed {
            state.preferences.edit(draft);
            state.feedback = "Pending changes; Save & apply to use them";
        }
        if ui::button(c"Save & apply##kqm-save", ImVec2::new(0.0, 0.0)) {
            save_draft(state);
        }
        if !state.feedback.is_empty() {
            ui::text(state.feedback);
        }
    });
}
