//! Two Forge-owned ordinary trampolines; initialization precedes game execution.
use crate::{memory, native, offers, signatures::SIGNATURES};
use alloc::vec::Vec;
use core::{
    ffi::c_void,
    sync::atomic::{AtomicBool, AtomicU32, Ordering},
};
use forge::patch::Patch;
static ENTERED: AtomicU32 = AtomicU32::new(0);
pub fn entered() -> u32 {
    ENTERED.load(Ordering::Acquire)
}
// Internal detour/state symbols are inspectable in the ELF, not loader callbacks.
core::arch::global_asm!(
    ".hidden kqm_row\n.hidden kqm_original\n.hidden kqm_active\n.hidden kqm_parent_original\n.hidden kqm_parent"
);

// Two ordinary Forge trampolines: the parent supplies the native offered IDs,
// and the existing row builder draws its eight rows before applying our badges.
#[unsafe(no_mangle)]
pub static kqm_parent_original: AtomicU32 = AtomicU32::new(0);
#[unsafe(no_mangle)]
pub static kqm_original: AtomicU32 = AtomicU32::new(0);
#[unsafe(no_mangle)]
pub static kqm_active: AtomicBool = AtomicBool::new(false);
#[cfg(target_pointer_width = "32")]
const _: () = assert!(core::mem::size_of::<forge::sys::hook::Hook>() == 24);
#[cfg(target_pointer_width = "32")]
const _: () = assert!(
    core::mem::offset_of!(forge::sys::hook::Hook, context) == 12
        && core::mem::offset_of!(forge::sys::hook::Hook, ctx_cell) == 16
        && core::mem::align_of::<forge::sys::hook::Hook>() == 4
);

type RowBuilder = unsafe extern "C" fn(u32, u32, u32, u32, u32, u32, u32);
/// AAPCS forwards r0..r3 and three incoming stack words to Forge's original.
/// This is a function entry, with no float arguments or interior register capture.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kqm_row(
    ui: u32,
    selected: u32,
    page: u32,
    new: u32,
    other: u32,
    cursor: u32,
    quests: u32,
) {
    ENTERED.fetch_or(2, Ordering::Release);
    let original = kqm_original.load(Ordering::Acquire);
    if original == 0 {
        return;
    } // Installation never publishes ACTIVE without an original.
    let f: RowBuilder = unsafe { core::mem::transmute(original as usize) };
    unsafe {
        f(ui, selected, page, new, other, cursor, quests);
    }
    if kqm_active.load(Ordering::Acquire) {
        native::update(ui, quests);
    }
}

/// Read only copied urgent IDs before the native controller runs. Scope restores
/// its previous TLS frame on return, including nested menu updates on this thread.
#[unsafe(no_mangle)]
pub unsafe extern "C" fn kqm_parent(controller: u32, info: u32) {
    ENTERED.fetch_or(1, Ordering::Release);
    let original = kqm_parent_original.load(Ordering::Acquire);
    if original == 0 {
        return;
    }
    let f: unsafe extern "C" fn(u32, u32) = unsafe { core::mem::transmute(original as usize) };
    if !kqm_active.load(Ordering::Acquire) {
        unsafe {
            f(controller, info);
        }
        return;
    }
    let copied = offers::Offers::read(controller, info);
    let _scope = offers::Scope::enter(&copied);
    unsafe {
        f(controller, info);
    }
}

/// Restore only our branch words (or a partially installed original/branch pair).
/// Foreign modifications retain their ownership; disabled snapshots never write
/// on Drop. Forge keeps allocated continuations reachable for process lifetime.
pub(crate) fn rollback(patch: &mut Patch) -> bool {
    kqm_active.store(false, Ordering::Release);
    let mut current = [0; 8];
    if !memory::copy(patch.addr(), &mut current) {
        return false;
    }
    let original: [u8; 8] = patch.original_bytes().try_into().unwrap();
    let branch: [u8; 8] = patch.patch_bytes().try_into().unwrap();
    if !(0..8)
        .step_by(4)
        .all(|i| current[i..i + 4] == original[i..i + 4] || current[i..i + 4] == branch[i..i + 4])
    {
        return false;
    }
    if current != original {
        patch.enable();
        patch.disable();
    }
    memory::sync_code(patch.addr(), 8)
        && memory::copy(patch.addr(), &mut current)
        && current == original
}
/// Install both hooks transactionally before the game starts executing. The
/// parent callback has two pointer/integer arguments; the row callback has seven.
pub fn install() -> Result<Vec<Patch>, &'static str> {
    let base = forge::mem::text_addr();
    memory::BASE.store(base, Ordering::Relaxed);
    if base == 0 || base > 0xfe000000 || base & 3 != 0 || !memory::correct_program() {
        return Err("unsupported title/address");
    }
    for &(offset, bytes) in SIGNATURES {
        let mut actual = [0; 32];
        if !memory::executable(base + offset, 32)
            || !memory::copy(base + offset, &mut actual)
            || actual != bytes
        {
            return Err("MHGU 1.4.0 code mismatch at a required function");
        }
    }
    if !offers::init() {
        return Err("counter context TLS allocation failed");
    }
    let targets = [base + 0x616cb0, base + 0x54d030];
    let detours = [kqm_row as *const () as u32, kqm_parent as *const () as u32];
    let originals = [&kqm_original, &kqm_parent_original];
    let mut patches = Vec::with_capacity(2);
    for i in 0..2 {
        // Exact PUSH/SUB stack prologues contain no PC-relative or status-register
        // operations. Forge relocates their first eight bytes into its own pool.
        let mut branch = [0; 8];
        branch[..4].copy_from_slice(&0xe51ff004u32.to_le_bytes());
        branch[4..].copy_from_slice(&detours[i].to_le_bytes());
        patches.push(Patch::new(targets[i], &branch, false));
    }
    for i in 0..2 {
        let mut original = core::ptr::null();
        let hook = unsafe {
            forge::sys::hook::forge_hook_create(
                targets[i] as *const c_void,
                detours[i] as *const c_void,
                &mut original,
            )
        };
        let continuation = original as u32;
        let mut code = [0; 16];
        let valid = continuation != 0
            && continuation & 3 == 0
            && memory::executable(continuation, 16)
            && memory::copy(continuation, &mut code)
            // Supporting signatures may be reordered or added. Compare against
            // this target's pre-hook snapshot, not an unrelated table position.
            && &code[..8] == patches[i].original_bytes()
            && code[8..12] == 0xe51ff004u32.to_le_bytes()
            && code[12..] == (targets[i] + 8).to_le_bytes();
        if valid {
            originals[i].store(continuation, Ordering::Release);
        }
        let mut actual = [0; 8];
        if !valid
            || hook.original != original
            || hook.target as u32 != targets[i]
            || hook.detour as u32 != detours[i]
            || !memory::copy(targets[i], &mut actual)
            || actual != patches[i].patch_bytes()
            || !memory::sync_code(targets[i], 8)
        {
            let mut restored = true;
            for patch in patches.iter_mut().rev() {
                restored &= rollback(patch);
            }
            return Err(if restored {
                "Forge hook failed; restored originals"
            } else {
                "hook rollback failed; restart required"
            });
        }
    }
    kqm_active.store(true, Ordering::Release);
    Ok(patches)
}
