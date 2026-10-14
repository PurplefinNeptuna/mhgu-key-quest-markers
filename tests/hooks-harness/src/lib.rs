//! Compile the production installer against a tiny byte-backed Forge fixture.
extern crate alloc;
extern crate self as forge;
use std::sync::Mutex;
static BYTES: Mutex<[u8; 8]> = Mutex::new([0; 8]);
pub mod memory {
    pub static BASE: core::sync::atomic::AtomicU32 = core::sync::atomic::AtomicU32::new(0);
    pub fn correct_program() -> bool {
        true
    }
    pub fn executable(_: u32, _: usize) -> bool {
        true
    }
    pub fn sync_code(_: u32, _: usize) -> bool {
        true
    }
    pub fn copy(address: u32, out: &mut [u8]) -> bool {
        if address != 0x1000 || out.len() != 8 {
            return false;
        }
        out.copy_from_slice(&*crate::BYTES.lock().unwrap());
        true
    }
}
pub mod native {
    pub fn update(_: u32, _: u32) {}
}
pub mod offers {
    pub struct Offers;
    impl Offers {
        pub fn read(_: u32, _: u32) -> Self {
            Self
        }
    }
    pub struct Scope;
    impl Scope {
        pub fn enter(_: &Offers) -> Option<Self> {
            Some(Self)
        }
    }
    pub fn init() -> bool {
        true
    }
}
pub mod signatures {
    pub const SIGNATURES: &[(u32, [u8; 32])] = &[(0x616cb0, [0; 32])];
}
pub mod mem {
    pub fn text_addr() -> u32 {
        0x1000
    }
}
pub mod patch {
    pub struct Patch {
        addr: u32,
        original: [u8; 8],
        patch: [u8; 8],
        enabled: bool,
    }
    impl Patch {
        pub fn new(addr: u32, patch: &[u8], enabled: bool) -> Self {
            let mut original = [0; 8];
            assert!(crate::memory::copy(addr, &mut original));
            let mut p = Self {
                addr,
                original,
                patch: patch.try_into().unwrap(),
                enabled: false,
            };
            if enabled {
                p.enable();
            }
            p
        }
        pub fn addr(&self) -> u32 {
            self.addr
        }
        pub fn original_bytes(&self) -> &[u8] {
            &self.original
        }
        pub fn patch_bytes(&self) -> &[u8] {
            &self.patch
        }
        pub fn enable(&mut self) {
            *crate::BYTES.lock().unwrap() = self.patch;
            self.enabled = true;
        }
        pub fn disable(&mut self) {
            *crate::BYTES.lock().unwrap() = self.original;
            self.enabled = false;
        }
    }
    impl Drop for Patch {
        fn drop(&mut self) {
            if self.enabled {
                self.disable();
            }
        }
    }
}
pub mod sys {
    pub mod hook {
        use core::ffi::c_void;
        pub struct Hook {
            pub target: *const c_void,
            pub detour: *const c_void,
            pub original: *const c_void,
        }
        pub unsafe fn forge_hook_create(
            target: *const c_void,
            detour: *const c_void,
            _: *mut *const c_void,
        ) -> Hook {
            panic!(
                "unsupported-code fixture must not call Forge hook_create: {target:p}/{detour:p}"
            );
        }
    }
}
#[path = "../../../src/hooks.rs"]
mod hooks;
#[test]
fn rejected_code_and_owned_rollback() {
    assert!(hooks::install().is_err()); // Unsupported code returns before creating hooks or writing.
    let original = [1, 2, 3, 4, 5, 6, 7, 8];
    let branch = [9, 10, 11, 12, 13, 14, 15, 16];
    for current in [
        original,
        branch,
        [1, 2, 3, 4, 13, 14, 15, 16],
        [9, 10, 11, 12, 5, 6, 7, 8],
    ] {
        *BYTES.lock().unwrap() = original;
        let mut p = patch::Patch::new(0x1000, &branch, false);
        *BYTES.lock().unwrap() = current;
        assert!(hooks::rollback(&mut p));
        assert_eq!(*BYTES.lock().unwrap(), original);
    }
    *BYTES.lock().unwrap() = original;
    let mut p = patch::Patch::new(0x1000, &branch, false);
    let foreign = [99; 8];
    *BYTES.lock().unwrap() = foreign;
    assert!(!hooks::rollback(&mut p));
    drop(p);
    assert_eq!(*BYTES.lock().unwrap(), foreign); // Disabled snapshot Drop retains foreign ownership.
}
