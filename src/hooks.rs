//! One Forge-owned ordinary trampoline; initialization runs before game execution.
use crate::{memory, native, signatures::SIGNATURES};
use core::{
    ffi::c_void,
    sync::atomic::{AtomicBool, AtomicU32, Ordering},
};
use forge::patch::Patch;
// Internal detour/gate symbols are inspectable in the ELF, not loader callbacks.
core::arch::global_asm!(
    ".hidden kqm_row\n.hidden kqm_original\n.hidden kqm_active\n.hidden kqm_verified_contract"
);

// The immutable release gate deliberately stays zero until the research audit
// establishes current-urgent availability and new GUI attachment. Volatile read
// retains the candidate implementation for binary/ABI checks without activating it.
#[used]
#[unsafe(no_mangle)]
pub static kqm_verified_contract: u32 = 0;
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
/// Keep the patch owner until process exit. There is no plugin unload operation.
pub fn install() -> Result<Patch, &'static str> {
    if unsafe { core::ptr::read_volatile(&kqm_verified_contract) } != 3 {
        return Err("inactive r1: progression/GUI contract verification pending");
    }
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
            return Err("MHGU 1.4.0 code mismatch; disable the old prefix plugin");
        }
    }
    let target = base + 0x616cb0;
    let detour = kqm_row as *const () as u32;
    // The exact displaced PUSH r4-r11,lr / SUB sp,sp,#4 use no PC-relative
    // operands and neither read nor write GE or NZCVQ. Forge copies these eight bytes.
    let mut branch = [0; 8];
    branch[..4].copy_from_slice(&0xe51ff004u32.to_le_bytes());
    branch[4..].copy_from_slice(&detour.to_le_bytes());
    let mut patch = Patch::new(target, &branch, false);
    let mut original = core::ptr::null();
    let hook = unsafe {
        forge::sys::hook::forge_hook_create(
            target as *const c_void,
            detour as *const c_void,
            &mut original,
        )
    };
    let continuation = original as u32;
    let mut code = [0; 16];
    let valid = continuation != 0
        && continuation & 3 == 0
        && memory::executable(continuation, 16)
        && memory::copy(continuation, &mut code)
        && code[..8] == SIGNATURES[0].1[..8]
        && code[8..12] == 0xe51ff004u32.to_le_bytes()
        && code[12..] == (target + 8).to_le_bytes();
    if valid {
        kqm_original.store(continuation, Ordering::Release);
    }
    let mut actual = [0; 8];
    if !valid
        || hook.original != original
        || hook.target as u32 != target
        || hook.detour as u32 != detour
        || !memory::copy(target, &mut actual)
        || actual != branch
        || !memory::sync_code(target, 8)
    {
        return Err(if rollback(&mut patch) {
            "Forge hook failed; restored original"
        } else {
            "hook rollback failed; restart required"
        });
    }
    kqm_active.store(true, Ordering::Release);
    Ok(patch)
}
