//! The game's save lock. Every game save op (write, delete, rename and the rest, `0x8778cc`..`0x878950`)
//! runs under the recursive mutex at `sSavedata +0xe80`, on its save worker (`0x878a68`) or inline on the
//! requester. The SDK's commit (`nn::fs::detail::FileSystemAccessor::Commit`) fails with 2002-6457 while
//! any file on the mount is open for write, from any thread: a plugin write handle open during a game
//! commit makes the game drop that save and show "An unknown error has occurred." So Key Quest Markers
//! holds this mutex from its mount to its unmount, which also covers Forge's commit at unmount (Forge
//! `fs.cpp`). Port of WishFinder's lock (forge-modding `references/save-lock.md`).
//! Research: work/save-guard/notes.md.
use crate::memory;
use core::sync::atomic::{AtomicBool, Ordering};

/// The sSavedata singleton's cell, its object vtable (DTI `sSavedata`) and its save mutex.
const SAVEDATA_CELL: u32 = 0x2120320;
const SAVEDATA_VTABLE: u32 = 0x17897f8;
const SAVE_MUTEX: u32 = 0xe80;

unsafe extern "C" {
    #[link_name = "_ZN2nn2os12TryLockMutexEPNS0_9MutexTypeE"]
    fn try_lock_mutex(mutex: u32) -> bool;
    #[link_name = "_ZN2nn2os11UnlockMutexEPNS0_9MutexTypeE"]
    fn unlock_mutex(mutex: u32);
}

/// Held while Key Quest Markers has the save mounted for a write; dropping it releases the game's mutex.
pub struct SaveLock(u32);

static MISSING_LOGGED: AtomicBool = AtomicBool::new(false);
static WAIT_LOGGED: AtomicBool = AtomicBool::new(false);

impl SaveLock {
    /// None while the game is in a save op, or while there is no sSavedata (or the cell holds something
    /// else): nothing is locked then, and the caller tries again later. Never blocks: the game thread
    /// must not wait on its own save worker.
    pub fn take() -> Option<Self> {
        let base = memory::BASE.load(Ordering::Relaxed);
        let savedata = memory::word(base + SAVEDATA_CELL).filter(|&s| s != 0);
        let Some(savedata) = savedata.filter(|&s| memory::word(s) == Some(base + SAVEDATA_VTABLE)) else {
            if !MISSING_LOGGED.swap(true, Ordering::Relaxed) {
                log::error!("Key Quest Markers can't find the game's save lock, so it won't save its settings yet");
            }
            return None;
        };
        let mutex = savedata + SAVE_MUTEX;
        // SAFETY: sSavedata's constructor initialises this mutex (`0x8771f0`), and the object is the
        // singleton whose vtable was just checked; it lives for the whole process.
        if unsafe { try_lock_mutex(mutex) } {
            return Some(Self(mutex));
        }
        if !WAIT_LOGGED.swap(true, Ordering::Relaxed) {
            log::info!("Key Quest Markers waited for the game to finish saving before saving its settings");
        }
        None
    }
}

impl Drop for SaveLock {
    fn drop(&mut self) {
        // SAFETY: this thread took the mutex in `take`.
        unsafe { unlock_mutex(self.0) }
    }
}
