//! Copy the counter's offered urgents for the nested row builder, on the same
//! native thread. The TLS value points only to a borrowed parent callback frame.
use crate::memory;
use core::{
    ffi::c_void,
    marker::PhantomData,
    sync::atomic::{AtomicU32, Ordering},
};
use forge::sys::os::tls::{self, TlsSlot};
#[unsafe(no_mangle)]
pub static kqm_tls_slot: AtomicU32 = AtomicU32::new(u32::MAX);
core::arch::global_asm!(".hidden kqm_tls_slot");
const _: () = assert!(core::mem::size_of::<TlsSlot>() == 4);

#[derive(Clone, Copy)]
pub struct Offers {
    pub ui: u32,
    pub ids: [u32; 16],
    pub valid: bool,
}
impl Offers {
    /// Native cQuestList::buildPage counts these sixteen IDs for its urgent
    /// category. They are the counter's offered set, not selector unfinished pools.
    pub fn read(controller: u32, info: u32) -> Self {
        let mut result = Self {
            ui: 0,
            ids: [0; 16],
            valid: false,
        };
        if !memory::readable(controller, 0x58) || !memory::readable(info, 0x1148) {
            return result;
        }
        let Some(ui) = memory::word(controller + 0x54) else {
            return result;
        };
        result.ui = ui;
        for (i, id) in result.ids.iter_mut().enumerate() {
            let Some(value) = memory::word(info + 0x1104 + i as u32 * 4) else {
                return result;
            };
            *id = value;
        }
        let Some(count) = memory::word(info + 0x1144) else {
            return result;
        };
        // The native menu builder clears 16 IDs plus this count, adds only
        // available unfinished urgents, and clears IDs/count together on removal.
        result.valid = ui != 0
            && count <= 16
            && count == result.ids.iter().filter(|&&id| id != 0).count() as u32;
        result
    }
    pub fn contains(self, id: u32) -> bool {
        id != 0 && self.ids.contains(&id)
    }
}
fn slot() -> Option<TlsSlot> {
    let value = kqm_tls_slot.load(Ordering::Acquire);
    (value != u32::MAX).then(|| unsafe { core::mem::transmute::<u32, TlsSlot>(value) })
}
unsafe extern "C" fn destructor(_: *mut c_void) {
    // TLS owns no allocation. Every normal callback restores its previous value;
    // thread teardown must never free or dereference a native stack frame.
}
pub fn init() -> bool {
    let mut key = TlsSlot::new();
    // ThreadLocal::new panics on allocation failure. This checked Forge SDK
    // binding reports failure at initialization and allocates no per-thread heap.
    if unsafe { tls::nnosAllocateTlsSlot(&mut key, destructor) } != 0 || !key.valid() {
        return false;
    }
    kqm_tls_slot.store(
        unsafe { core::mem::transmute::<TlsSlot, u32>(key) },
        Ordering::Release,
    );
    true
}
pub struct Scope<'a> {
    key: TlsSlot,
    previous: *mut c_void,
    frame: PhantomData<&'a Offers>,
}
impl<'a> Scope<'a> {
    pub fn enter(frame: &'a Offers) -> Option<Self> {
        let key = slot()?;
        let previous = unsafe { tls::nnosGetTlsValue(key) };
        unsafe {
            tls::nnosSetTlsValue(key, (frame as *const Offers).cast_mut().cast());
        }
        Some(Self {
            key,
            previous,
            frame: PhantomData,
        })
    }
}
impl Drop for Scope<'_> {
    fn drop(&mut self) {
        unsafe {
            tls::nnosSetTlsValue(self.key, self.previous);
        }
    }
}
pub fn current(ui: u32) -> Option<Offers> {
    let ptr = unsafe { tls::nnosGetTlsValue(slot()?) } as *const Offers;
    if ptr.is_null() {
        return None;
    }
    // Scope's borrow keeps this plugin-owned stack value alive for the complete
    // parent call. Nested calls restore the previous frame before returning.
    let copy = unsafe { ptr.read() };
    (copy.valid && copy.ui == ui).then_some(copy)
}
