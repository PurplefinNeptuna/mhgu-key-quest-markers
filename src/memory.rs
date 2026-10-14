//! Checked native memory and cache synchronization; Forge owns hooks and allocations.
//! Forge provides addresses/singletons. Its memory-query and program-ID helpers
//! are internal, not exported by the pinned loader; cache flushing has no wrapper.
//! These narrow SVC bindings cover those unavailable plugin operations.
use core::sync::atomic::AtomicU32;

pub static BASE: AtomicU32 = AtomicU32::new(0);
// Horizon's pseudo-handle denotes this running process; no handle ownership
// or closing is required for the mapping and cache operations below.
const CURRENT_PROCESS: u32 = 0xffff8001;
// Match the kernel's query-memory output layout exactly, including padding.
// repr(C) fixes field order and C alignment for the assembly SVC wrapper.
#[repr(C)]
#[derive(Default)]
struct MemoryInfo {
    address: u64,
    size: u64,
    kind: u32,
    attributes: u32,
    permissions: u32,
    ipc: u32,
    device: u32,
    padding: u32,
}
const _: () = assert!(core::mem::size_of::<MemoryInfo>() == 40);
unsafe extern "C" {
    fn mwc_svc_query(info: *mut MemoryInfo, page: *mut u32, address: u64) -> u32;
    fn mwc_svc_get_info(out: *mut u64, id: u32, handle: u32, sub_id: u64) -> u32;
    fn mwc_svc_flush(handle: u32, address: u64, bytes: u64) -> u32;
}
core::arch::global_asm!(include_str!("svc.S"), options(raw));
// GetInfo selector 18 supplies the program ID. Exact instruction signatures
// in hooks.rs then distinguish the expected executable code.
pub fn correct_program() -> bool {
    let mut title = 0; // SAFETY: writable output and current-process pseudo-handle match the pinned SVC ABI.
    unsafe {
        mwc_svc_get_info(&mut title, 18, CURRENT_PROCESS, 0) == 0 && title == 0x0100770008dd8000
    }
}
// Reject null/wrapped ARM32 spans, then require the whole copy to fit in one
// readable mapping. This checks address access; it does not take ownership of
// the game object or extend its lifetime beyond the synchronous native call.
fn mapped(address: u32, bytes: usize, permissions: u32) -> bool {
    if address == 0 || address as u64 + bytes as u64 > 0x1_0000_0000 {
        return false;
    }
    let mut info = MemoryInfo::default();
    let mut page = 0;
    // SAFETY: outputs are initialized, naturally aligned structs of the kernel's declared size.
    unsafe {
        mwc_svc_query(&mut info, &mut page, address as u64) == 0
            && (info.permissions & permissions) == permissions
            && info.address <= address as u64
            && address as u64 + bytes as u64 <= info.address + info.size
    }
}
pub fn writable(address: u32, bytes: usize) -> bool {
    mapped(address, bytes, 3)
}
pub fn readable(address: u32, bytes: usize) -> bool {
    mapped(address, bytes, 1)
}
// Horizon permission bits 1 (read) and 4 (execute) must both cover the complete
// trampoline. The RX alias belongs to Forge and remains live until process exit.
pub fn executable(address: u32, bytes: usize) -> bool {
    mapped(address, bytes, 5)
}
// After writing or restoring instructions, flush process caches and execute
// ARM barriers before those addresses can be used as code.
pub fn sync_code(address: u32, bytes: usize) -> bool {
    // SAFETY: caller supplies a validated executable span. This is the tested ARM32 process cache-flush contract.
    let result = unsafe { mwc_svc_flush(CURRENT_PROCESS, address as u64, bytes as u64) };
    // SAFETY: barriers change no memory contents and establish instruction visibility after kernel synchronization.
    unsafe { core::arch::asm!("dsb sy", "isb", options(nostack, preserves_flags)) };
    result == 0
}

/// Copy scalars without constructing references to game-owned objects.
pub fn word(address: u32) -> Option<u32> {
    if address & 3 != 0 || !readable(address, 4) {
        return None;
    }
    // SAFETY: alignment/mapping checked; callers hold native resource lifetime.
    Some(unsafe { core::ptr::read_volatile(address as *const u32) })
}
pub fn half(address: u32) -> Option<u16> {
    if address & 1 != 0 || !readable(address, 2) {
        return None;
    }
    Some(unsafe { core::ptr::read_volatile(address as *const u16) })
}
pub fn copy(address: u32, out: &mut [u8]) -> bool {
    if !readable(address, out.len()) {
        return false;
    }
    // SAFETY: source lifetime is held by synchronous native caller; destination owned.
    unsafe { core::ptr::copy_nonoverlapping(address as *const u8, out.as_mut_ptr(), out.len()) };
    true
}
