//! Checked primary-file adapter. Forge owns the counted save-data mount.
//! Stock ScopedMount panics on mount failure; Reader asserts on short reads,
//! Writer ignores partial writes, and neither exposes checked flush/commit.
//! Only these missing error paths use the existing verified ARM32 SDK ABI.
use core::ffi::c_char;
use quest_badges_core::colors::{Error, Files, Text};
const PATH: &[u8] = b"savedata:/key_quest_markers.ini\0";
unsafe extern "C" {
    #[link_name = "_ZN2nn2fs23ScopedAutoAbortDisablerC1Ev"]
    fn disable_abort(previous: *mut u32);
    #[link_name = "_ZN2nn2fs25SetCurrentThreadFsContextEPKNS0_9FsContextE"]
    fn restore_context(previous: u32);
    #[link_name = "_ZN2nn2fs14CommitSaveDataEPKc"]
    fn commit(path: *const c_char) -> u32;
    #[link_name = "_ZN2nn2fs8OpenFileEPNS0_10FileHandleEPKci"]
    fn open(handle: *mut u32, path: *const c_char, mode: i32) -> u32;
    #[link_name = "_ZN2nn2fs9CloseFileENS0_10FileHandleE"]
    fn close(handle: u32);
    #[link_name = "_ZN2nn2fs11GetFileSizeEPxNS0_10FileHandleE"]
    fn size(out: *mut i64, handle: u32) -> u32;
    #[link_name = "_ZN2nn2fs8ReadFileENS0_10FileHandleExPvj"]
    fn read(handle: u32, offset: i64, out: *mut u8, len: u32) -> u32;
    #[link_name = "_ZN2nn2fs9WriteFileENS0_10FileHandleExPKvjRKNS0_11WriteOptionE"]
    fn write(handle: u32, offset: i64, bytes: *const u8, len: u32, option: *const u32) -> u32;
    #[link_name = "_ZN2nn2fs9FlushFileENS0_10FileHandleE"]
    fn flush(handle: u32) -> u32;
    #[link_name = "_ZN2nn2fs11SetFileSizeENS0_10FileHandleEx"]
    fn resize(handle: u32, len: i64) -> u32;
    #[link_name = "_ZN2nn2fs10CreateFileEPKcx"]
    fn create(path: *const c_char, len: i64) -> u32;
}
// FileHandle and FsContext pointers are one 32-bit ARM word, unlike generic
// ARM64 nnheaders. i64 offsets use AAPCS even-register/stack alignment.
struct Handle(u32);
impl Drop for Handle {
    fn drop(&mut self) {
        unsafe {
            close(self.0);
        }
    }
}
pub struct Storage {
    previous: u32,
}
impl Storage {
    pub fn new() -> Self {
        let mut previous = 0;
        // SAFETY: SDK writes the previous thread-local context into one word;
        // Drop restores it after all file handles and the counted mount close.
        unsafe {
            disable_abort(&mut previous);
        }
        Self { previous }
    }
}
impl Drop for Storage {
    fn drop(&mut self) {
        unsafe {
            restore_context(self.previous);
        }
    }
}
impl Files for Storage {
    fn mount(&mut self) -> bool {
        forge::fs::savedata::mount()
    }
    fn unmount(&mut self) {
        forge::fs::savedata::unmount();
    }
    fn read(&mut self, out: &mut Text) -> Result<(), Error> {
        // SAFETY: buffers are bounded, the path is NUL terminated, and every
        // successful SDK open is immediately owned by a closing Drop guard.
        unsafe {
            let mut handle = 0;
            if open(&mut handle, PATH.as_ptr().cast(), 1) != 0 {
                return Err(Error::Missing);
            }
            let handle = Handle(handle);
            let mut len = 0i64;
            if size(&mut len, handle.0) != 0 {
                return Err(Error::Read);
            }
            if len <= 0 || len > out.bytes.len() as i64 {
                return Err(Error::Invalid);
            }
            if read(handle.0, 0, out.bytes.as_mut_ptr(), len as u32) != 0 {
                return Err(Error::Read);
            }
            out.len = len as usize;
            Ok(())
        }
    }
    fn write(&mut self, text: &Text) -> Result<(), Error> {
        unsafe {
            let mut handle = 0;
            if open(&mut handle, PATH.as_ptr().cast(), 2) != 0
                && (create(PATH.as_ptr().cast(), text.len as i64) != 0
                    || open(&mut handle, PATH.as_ptr().cast(), 2) != 0)
            {
                return Err(Error::Write);
            }
            let handle = Handle(handle);
            let option = 1u32; // SDK WriteOption::Flush.
            if resize(handle.0, text.len as i64) != 0
                || write(handle.0, 0, text.bytes.as_ptr(), text.len as u32, &option) != 0
                || flush(handle.0) != 0
            {
                return Err(Error::Write);
            }
            Ok(())
        }
    }
    fn commit(&mut self) -> bool {
        unsafe { commit(c"savedata".as_ptr()) == 0 }
    }
}
