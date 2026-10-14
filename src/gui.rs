//! Native row children. The game owns their MT allocations and draw caches;
//! no archive, object-index array, overlay, or pointer retained by this plugin.
use crate::memory::{self, BASE};
use core::sync::atomic::{AtomicU32, Ordering};
use forge::mt::dti::MtDti;
use quest_badges_core::Badge;

const ID: u32 = 0x4b514d33; // KQM3, outside the counter's existing object IDs.
const TEXTURE_BYTES: usize = 304;
const CACHE_BYTES: usize = 10 * 16 + 8; // Ten drawable begin/end pairs plus terminator.
static FAILURE: AtomicU32 = AtomicU32::new(0);
pub fn take_failure() -> u32 {
    FAILURE.swap(0, Ordering::Relaxed)
}
fn base() -> u32 {
    BASE.load(Ordering::Relaxed)
}
fn method(object: u32, offset: u32) -> Option<u32> {
    let vft = memory::word(object)?;
    let f = memory::word(vft.checked_add(offset)?)?;
    memory::executable(f, 4).then_some(f)
}
fn is_type(object: u32, dti: u32) -> bool {
    let Some(f) = method(object, 0x14) else {
        return false;
    };
    let get: unsafe extern "C" fn(u32) -> u32 = unsafe { core::mem::transmute(f as usize) };
    unsafe { get(object) == dti }
}
// Callers checked writable storage and native ownership before using these
// scalar writes. No references are formed to the game's mutable objects.
unsafe fn word(address: u32, value: u32) {
    unsafe { core::ptr::write_volatile(address as *mut u32, value) };
}
unsafe fn bits(address: u32, value: f32) {
    unsafe { word(address, value.to_bits()) };
}
fn integer(offset: u32, object: u32, value: u32) {
    let f: unsafe extern "C" fn(u32, u32) =
        unsafe { core::mem::transmute((base() + offset) as usize) };
    unsafe { f(object, value) };
}

#[derive(Clone, Copy)]
struct Row {
    root: u32,
    owner: u32,
    parent: u32,
    tail: u32,
    resource: u32,
    cache: u32,
    badge: u32,
}
impl Row {
    fn read(instance: u32, root_dti: u32, texture_dti: u32) -> Option<Self> {
        let mut stage = 1;
        let result = (|| {
            if !memory::writable(instance, 224) {
                return None;
            }
            stage = 2;
            let objects = memory::word(instance + 0xd8)?;
            let root = memory::word(instance + 0xdc)?;
            if !memory::readable(objects, 12 * 4)
                || !memory::writable(root, 176)
                || memory::word(objects)? != root
                || !is_type(root, root_dti)
            {
                return None;
            }
            stage = 3;
            let description = memory::word(root + 0x9c)?;
            // The unmodified counter row is animation 20 with 12 lookup objects,
            // 15 sequences and 9 drawables. These tables stay exactly as the game built them.
            if memory::word(description)? != 20
                || memory::half(description + 4)? != 12
                || memory::half(description + 6)? != 15
                || memory::word(description + 8)? != 9
                || memory::word(root + 0xa0)? != objects
                || memory::word(root + 0x50)? != 1
            {
                return None;
            }
            stage = 4;
            let cache = memory::word(root + 0xa4)?;
            if cache == 0
                || memory::word(root + 0x80)? != cache
                || !memory::readable(cache, 9 * 16 + 8)
            {
                return None;
            }
            stage = 5;
            let parent = memory::word(objects + 4)?;
            let source = memory::word(objects + 8)?;
            if !memory::writable(parent, 192)
                || memory::word(parent + 0x50)? != 14
                || !memory::readable(source, TEXTURE_BYTES)
                || memory::word(source + 0x50)? != 12
                || memory::word(source + 0x70)? != parent
                || !is_type(source, texture_dti)
            {
                return None;
            }
            stage = 6;
            // a38828 passes instance+0x6c to a38bc0, which assigns it to each
            // object's +0x74. This is the owning cGUI, not the animation instance.
            let owner = memory::word(instance + 0x6c)?;
            let resource = memory::word(source + 0x78)?;
            if !memory::readable(owner, 4) || resource == 0 || memory::word(source + 0x74)? != owner
            {
                return None;
            }
            stage = 7;
            let lookup: unsafe extern "C" fn(u32, u32) -> u32 =
                unsafe { core::mem::transmute((base() + 0xb80fd0) as usize) };
            let atlas = unsafe { lookup(resource, 22) };
            if !memory::readable(atlas, 64)
                || memory::word(atlas)? != 22
                || memory::word(atlas + 12)? != 0x02000200
                || memory::word(atlas + 0x28)? == 0
            {
                return None;
            }
            stage = 8;
            let mut tail = memory::word(parent + 0x68)?;
            let mut badge = 0;
            let mut seen = [0; 64];
            // Check a bounded sibling chain, including cycles and foreign ID collisions.
            // Only this direct parent is searched; the ticket subtree remains separate.
            for i in 0..seen.len() {
                if tail == 0
                    || seen[..i].contains(&tail)
                    || !memory::writable(tail, 0x94)
                    || memory::word(tail + 0x70)? != parent
                {
                    return None;
                }
                seen[i] = tail;
                if memory::word(tail + 0x50)? == ID {
                    if badge != 0
                        || !memory::writable(tail, TEXTURE_BYTES)
                        || !is_type(tail, texture_dti)
                        || memory::word(tail + 0x74)? != owner
                        || memory::word(tail + 0x78)? != resource
                    {
                        return None;
                    }
                    badge = tail;
                }
                let next = memory::word(tail + 0x6c)?;
                if next == 0 {
                    return Some(Self {
                        root,
                        owner,
                        parent,
                        tail,
                        resource,
                        cache,
                        badge,
                    });
                }
                tail = next;
            }
            None
        })();
        if result.is_none() {
            // Store only a small stage number; game pointers never escape the callback.
            let _ = FAILURE.compare_exchange(0, stage, Ordering::Relaxed, Ordering::Relaxed);
        }
        result
    }
}

struct Allocation {
    allocator: u32,
    free: u32,
    pointer: u32,
}
impl Allocation {
    fn texture(dti: &MtDti) -> Option<Self> {
        let address = dti as *const _ as u32;
        let getter: unsafe extern "C" fn(u32) -> u32 =
            unsafe { core::mem::transmute((base() + 0x7aa47c) as usize) };
        let allocator = unsafe { getter(address) };
        let allocate = method(allocator, 0x20)?;
        let free = method(allocator, 0x34)?;
        let f: unsafe extern "C" fn(u32, u32, u32, u32) -> u32 =
            unsafe { core::mem::transmute(allocate as usize) };
        // The owning native destructor frees through this DTI's MT allocator.
        // Forge's malloc cannot be substituted for game-owned object memory.
        let pointer = unsafe { f(allocator, TEXTURE_BYTES as u32, 16, dti.id()) };
        if pointer == 0 {
            return None;
        }
        let result = Self {
            allocator,
            free,
            pointer,
        };
        if !memory::writable(pointer, TEXTURE_BYTES) || pointer & 15 != 0 {
            return None;
        }
        unsafe { core::ptr::write_bytes(pointer as *mut u8, 0, TEXTURE_BYTES) };
        Some(result)
    }
}
impl Drop for Allocation {
    fn drop(&mut self) {
        if self.pointer != 0 {
            let f: unsafe extern "C" fn(u32, u32) =
                unsafe { core::mem::transmute(self.free as usize) };
            unsafe { f(self.allocator, self.pointer) };
        }
    }
}
struct Constructed {
    pointer: u32,
    destroy: u32,
}
impl Drop for Constructed {
    fn drop(&mut self) {
        if self.pointer != 0 {
            let f: unsafe extern "C" fn(u32) =
                unsafe { core::mem::transmute(self.destroy as usize) };
            unsafe { f(self.pointer) };
        }
    }
}
fn create(row: Row, dti: &MtDti) -> Result<u32, u32> {
    let address = dti as *const _ as u32;
    let mut storage = Allocation::texture(dti).ok_or(1u32)?;
    // This game's Texture DTI has only three virtual slots: no placement
    // constructor at +0x0c. The verified standalone constructor takes storage in r0.
    let f: unsafe extern "C" fn(u32) -> u32 =
        unsafe { core::mem::transmute((base() + 0xa4f60c) as usize) };
    let object = unsafe { f(storage.pointer) };
    if object != storage.pointer {
        return Err(2);
    }
    let destroy = method(object, 4).ok_or(3u32)?;
    let mut owned = Constructed {
        pointer: object,
        destroy,
    };
    storage.pointer = 0; // Constructor succeeded: the native destructor now owns the block.
    if !is_type(object, address) {
        return Err(4);
    }
    unsafe {
        word(object + 0x50, ID);
        word(object + 0x74, row.owner);
        word(object + 0x78, row.resource);
        // PosX/PosY setters use the game's VFP scalar ABI. Their verified scalar
        // fields plus dirty bit give the same result without a float-call shim.
        bits(object + 0x80, -28.0);
        bits(object + 0x84, 8.0);
        bits(object + 0xb4, 24.0);
        bits(object + 0xb8, 24.0);
        word(
            object + 0x54,
            memory::word(object + 0x54).ok_or(4u32)? | 0x20000,
        );
    }
    // Match the native Tex_icon's static style; each of these setters has a
    // two-integer ABI. No sequence records or shared resource bytes are changed.
    for (offset, value) in [
        (0xa4dc24, 1),
        (0xa4a9f4, 1),
        (0xa47a94, 1),
        (0xa4dca0, 1),
        (0xa47a04, 2),
        (0xa4aa24, 1),
        (0xa4aa5c, 1),
        (0xa4aa94, 1),
        (0xa4aac8, 1),
        (0xa4aafc, 1),
        (0xa4dc54, 1),
        (0xa4fa5c, 1),
    ] {
        integer(offset, object, value);
    }
    integer(0xa4faf0, object, 22);
    if memory::word(object + 0x104).ok_or(5u32)? == 0 {
        return Err(5);
    }
    let rect = [136f32, 344., 198., 406.];
    let f: unsafe extern "C" fn(u32, *const f32) =
        unsafe { core::mem::transmute((base() + 0xa4fb58) as usize) };
    unsafe { f(object, rect.as_ptr()) };
    set(object, Badge::Hidden);

    let allocate = method(row.root, 0x58).ok_or(6u32)?;
    let release = method(row.root, 0x5c).ok_or(6u32)?;
    let f: unsafe extern "C" fn(u32, u32) -> u32 =
        unsafe { core::mem::transmute(allocate as usize) };
    let cache = unsafe { f(row.root, CACHE_BYTES as u32) };
    if cache == 0 {
        return Err(7);
    }
    let free: unsafe extern "C" fn(u32, u32) = unsafe { core::mem::transmute(release as usize) };
    if !memory::writable(cache, CACHE_BYTES) || cache & 15 != 0 {
        unsafe { free(row.root, cache) };
        return Err(8);
    }
    unsafe { core::ptr::write_bytes(cache as *mut u8, 0, CACHE_BYTES) };
    // Publish only after both allocations and complete initialization succeed.
    // The game's draw walker emits begin/end pairs for the new child, so its
    // original nine-drawable cache must grow by sixteen bytes. Root destruction
    // frees the new cache; child destruction frees the badge. Index arrays stay 12.
    unsafe {
        word(row.root + 0xa4, cache);
        word(row.root + 0x80, cache);
        integer(0xa4844c, row.tail, object); // Native sibling link also supplies parent.
        word(
            row.parent + 0x54,
            memory::word(row.parent + 0x54).unwrap() | 0x80000,
        );
        word(row.root + 0x8c, memory::word(row.root + 0x8c).unwrap() | 3);
    }
    owned.pointer = 0; // Reachable from the row: native ownership takes over.
    unsafe { free(row.root, row.cache) };
    Ok(object)
}
/// Called only after the original normal counter row builder on its GUI thread.
/// Validate all eight rows first, hide old badges, then create missing native children.
pub fn objects(ui: u32) -> Result<[u32; 8], u32> {
    let (rows, texture) = (|| {
        let holder = memory::word(ui.checked_add(0x24)?)?;
        if !memory::readable(holder, 0x29c) || method(holder, 0xac).is_none() {
            return None;
        }
        let identity: unsafe extern "C" fn(u32) -> u32 =
            unsafe { core::mem::transmute((base() + 0x546f28) as usize) };
        if unsafe { identity(holder) } != 5 {
            return None;
        }
        let count = memory::word(holder + 0x298)?;
        if count > 512 {
            return None;
        }
        let texture = MtDti::find("cGUIObjTexture")?;
        let root = MtDti::find("cGUIObjRoot")?;
        if texture.size() != TEXTURE_BYTES || root.size() != 176 {
            return None;
        }
        let mut rows = [None; 8];
        for (i, row) in rows.iter_mut().enumerate() {
            let index = 16 + i as u32;
            // A malformed row must not prevent hiding known owned children in the
            // other valid rows when their quest entries are being reused.
            *row = (|| {
                let (table, local) = if index < count {
                    (memory::word(holder + 0xf8)?, index)
                } else {
                    (memory::word(holder + 0x294)?, index - count)
                };
                if !memory::readable(table, (local as usize + 1) * 4) {
                    return None;
                }
                let instance = memory::word(table.checked_add(local * 4)?)?;
                Row::read(
                    instance,
                    root as *const _ as u32,
                    texture as *const _ as u32,
                )
            })();
        }
        Some((rows, texture))
    })()
    .ok_or(1u32)?;
    for row in rows.iter().flatten() {
        if row.badge != 0 {
            set(row.badge, Badge::Hidden);
        }
    }
    if rows.iter().any(Option::is_none) {
        return Err(64);
    }
    let mut result = [0; 8];
    for (i, row) in rows.into_iter().flatten().enumerate() {
        result[i] = if row.badge != 0 {
            row.badge
        } else {
            create(row, texture).map_err(|stage| {
                FAILURE.store(stage, Ordering::Relaxed);
                16u32
            })?
        };
    }
    Ok(result)
}
pub fn set(object: u32, badge: Badge) {
    if badge != Badge::Hidden {
        let value = badge.rgba();
        let color: unsafe extern "C" fn(u32, *const u32, u32) =
            unsafe { core::mem::transmute((base() + 0xa4e0b8) as usize) };
        for vertex in 0..4 {
            unsafe { color(object, &value, vertex) };
        }
    }
    integer(0xa47950, object, u32::from(badge != Badge::Hidden));
}
