//! Forge settings callbacks own drafts and file I/O; native hooks only copy RGB words.
use crate::config::Storage;
use core::{
    cell::UnsafeCell,
    sync::atomic::{AtomicBool, AtomicU32, Ordering},
};
use forge::os::{lock::ScopedLock, mutex::Mutex, once_lock::OnceLock};
use quest_badges_core::colors::{Error, Palette, Preferences};
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
/// Hide grey badges and keep cleared colours; read by the row hook and by Mod Options `get`,
/// written without locks.
static HIDE_GREY: AtomicBool = AtomicBool::new(Palette::DEFAULT.hide_completed);
static KEEP_CLEARED: AtomicBool = AtomicBool::new(Palette::DEFAULT.keep_cleared);
pub fn palette() -> Palette {
    Palette {
        key: kqm_palette[0].load(Ordering::Acquire),
        urgent: kqm_palette[1].load(Ordering::Acquire),
        completed: kqm_palette[2].load(Ordering::Acquire),
        unlocks: kqm_palette[3].load(Ordering::Acquire),
        reward: kqm_palette[4].load(Ordering::Acquire),
        hide_completed: hide_grey(),
        keep_cleared: keep_cleared(),
    }
}
pub fn hide_grey() -> bool {
    HIDE_GREY.load(Ordering::Acquire)
}
/// Mod Options `set`: applies at once; `update` then records it in the preferences.
pub fn set_hide_grey(hide: bool) {
    HIDE_GREY.store(hide, Ordering::Release);
}
pub fn keep_cleared() -> bool {
    KEEP_CLEARED.load(Ordering::Acquire)
}
/// Mod Options `set`: applies at once; `update` then records it in the preferences.
pub fn set_keep_cleared(keep: bool) {
    KEEP_CLEARED.store(keep, Ordering::Release);
}
fn publish(p: Palette) {
    for (slot, value) in kqm_palette.iter().zip([p.key, p.urgent, p.completed, p.unlocks, p.reward]) {
        slot.store(value, Ordering::Release);
    }
    HIDE_GREY.store(p.hide_completed, Ordering::Release);
    KEEP_CLEARED.store(p.keep_cleared, Ordering::Release);
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
            state.preferences.apply_badges(hide_grey(), keep_cleared());
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
                state.feedback = "Colours loaded";
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
        if ui::checkbox(c"Hide grey badges##kqm-hide-grey", &mut draft.hide_completed) {
            changed = true;
        }
        if ui::checkbox(c"Keep cleared colours##kqm-keep-cleared", &mut draft.keep_cleared) {
            changed = true;
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
