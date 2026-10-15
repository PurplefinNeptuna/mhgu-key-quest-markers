//! Native row children. The game owns their MT allocations and draw caches;
//! no archive replacement, overlay, or game pointer retained by this plugin.
use crate::memory::{self, BASE};
use core::sync::atomic::{AtomicU32, Ordering};
use forge::mt::dti::MtDti;
use quest_badges_core::Badge;

const ID: u32 = 0x4b514d33; // KQM3, outside the counter's existing object IDs.
const TEXTURE_BYTES: usize = 304;
const MESSAGE_BYTES: usize = 352;
const MAP_BYTES: usize = 13 * 4; // Original twelve bindings plus our native child.
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
    instance: u32,
    objects: u32,
    owner: u32,
    parent: u32,
    tail: u32,
    resource: u32,
    cache: u32,
    badge: u32,
}
impl Row {
    // Lookup indices stay those of the original resource, even after appending
    // the badge. Check type and ownership before borrowing either native object.
    // The row title is cGUIObjMessage (resource CRC 0x2fb82eae), not its
    // cGUIObjText subclass. Both use the inherited Size/AutoScale setters.
    fn binding(self, index: u32, id: u32, dti: u32, size: usize) -> Option<u32> {
        let object = memory::word(self.objects + index * 4)?;
        (memory::writable(object, size)
            && memory::word(object + 0x50)? == id
            && memory::word(object + 0x70)? == self.parent
            && memory::word(object + 0x74)? == self.owner
            && memory::word(object + 0x78)? == self.resource
            && is_type(object, dti))
        .then_some(object)
    }

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
            // 15 sequences and 9 drawables. The resource descriptor and first twelve
            // bindings stay unchanged; the runtime map may append our child.
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
                    // Native resource cleanup counts the linked tree, not the
                    // resource descriptor. A retained child needs its 13th binding.
                    if badge != 0
                        && (!memory::readable(objects, MAP_BYTES)
                            || memory::word(objects + 48)? != badge)
                    {
                        return None;
                    }
                    return Some(Self {
                        root,
                        instance,
                        objects,
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
    fn mapping() -> Option<Self> {
        // Native map construction and destruction both use cGUIInstance's DTI
        // (verified GOT slot main+0x18422b4), independently of the Texture allocator.
        let dti = MtDti::find("cGUIInstance")?;
        let getter: unsafe extern "C" fn(u32) -> u32 =
            unsafe { core::mem::transmute((base() + 0x7aa47c) as usize) };
        let allocator = unsafe { getter(dti as *const _ as u32) };
        let allocate = method(allocator, 0x1c)?;
        let free = method(allocator, 0x34)?;
        let f: unsafe extern "C" fn(u32, u32, u32) -> u32 =
            unsafe { core::mem::transmute(allocate as usize) };
        let pointer = unsafe { f(allocator, MAP_BYTES as u32, 16) };
        let result = Self {
            allocator,
            free,
            pointer,
        };
        if !memory::writable(pointer, MAP_BYTES) || pointer & 15 != 0 {
            return None;
        }
        Some(result)
    }
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
        // Match the request slot's 32px size. Y=3 lifts the emblem's visible
        // centre into the white band; the quad stays within the 40px row.
        bits(object + 0x80, 365.0);
        bits(object + 0x84, 3.0);
        bits(object + 0xb4, 32.0);
        bits(object + 0xb8, 32.0);
        word(
            object + 0x54,
            memory::word(object + 0x54).ok_or(4u32)? | 0x20000,
        );
    }
    // Match Tex_icon's decoded static style. GUI kinds 17/18 store immediate
    // values: Mask=0 draws colour; Mask=1 enters the native mask-writing pass.
    // Each setter has a two-integer ABI; resource/sequence bytes stay untouched.
    for (offset, value) in [
        (0xa4dc24, 1),
        (0xa4a9f4, 0),
        (0xa47a94, 0),
        (0xa4dca0, 0),
        (0xa47a04, 2),
        (0xa4aa24, 1),
        (0xa4aa5c, 1),
        (0xa4aa94, 3),
        (0xa4aac8, 3),
        (0xa4aafc, 3),
        (0xa4dc54, 0),
        (0xa4fa5c, 0),
    ] {
        integer(offset, object, value);
    }
    integer(0xa4faf0, object, 22);
    if memory::word(object + 0x104).ok_or(5u32)? == 0 {
        return Err(5);
    }
    // r12-small selects the outlined top emblem; its 30px atlas region is
    // drawn in the same 32px quad as r12 for an isolated in-game comparison.
    let rect = [342f32, 0., 372., 30.];
    let f: unsafe extern "C" fn(u32, *const f32) =
        unsafe { core::mem::transmute((base() + 0xa4fb58) as usize) };
    unsafe { f(object, rect.as_ptr()) };
    set(object, Badge::Hidden);

    let mut mapping = Allocation::mapping().ok_or(9u32)?;
    // Preserve every resource/sequence binding at its original index. The native
    // cleanup walker asks for the tree count (13), so slot 12 must hold the child.
    unsafe {
        core::ptr::copy_nonoverlapping(row.objects as *const u8, mapping.pointer as *mut u8, 48);
        word(mapping.pointer + 48, object);
    }
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
    // frees the new cache; child destruction frees the badge. Publish both map
    // aliases before linking the child, so a 13-node tree always has 13 entries.
    unsafe {
        word(row.instance + 0xd8, mapping.pointer);
        word(row.root + 0xa0, mapping.pointer);
        word(row.root + 0xa4, cache);
        word(row.root + 0x80, cache);
        integer(0xa4844c, row.tail, object); // Native sibling link also supplies parent.
        word(
            row.parent + 0x54,
            memory::word(row.parent + 0x54).unwrap() | 0x80000,
        );
        word(row.root + 0x8c, memory::word(row.root + 0x8c).unwrap() | 3);
    }
    let old_map_free: unsafe extern "C" fn(u32, u32) =
        unsafe { core::mem::transmute(mapping.free as usize) };
    mapping.pointer = 0; // The animation destructor now owns the expanded map.
    unsafe { old_map_free(mapping.allocator, row.objects) };
    owned.pointer = 0; // Reachable from the row: native ownership takes over.
    unsafe { free(row.root, row.cache) };
    Ok(object)
}
/// Called only after the original normal counter row builder on its GUI thread.
/// Hide old badges and restore titles before any classification can return early.
/// Handles contain only callback-scoped pointers; no native object is retained.
pub fn objects(ui: u32) -> Result<[Option<Decoration>; 8], u32> {
    let (rows, texture, text) = (|| {
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
        let text = MtDti::find("cGUIObjMessage")?;
        if texture.size() != TEXTURE_BYTES || root.size() != 176 || text.size() != MESSAGE_BYTES {
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
        Some((rows, texture, text))
    })()
    .ok_or(1u32)?;
    for row in rows.iter().flatten() {
        if row.badge != 0 {
            set(row.badge, Badge::Hidden);
        }
        // Restore a valid title even when the request binding is missing. Only
        // rows with our child could have been fitted by a previous callback.
        if row.badge != 0 {
            if let Some(title) = row.binding(4, 6, text as *const _ as u32, MESSAGE_BYTES) {
                fit_title(title, 355.0, false);
            }
        }
    }
    if rows.iter().any(Option::is_none) {
        return Err(64);
    }
    let mut result = [None; 8];
    for (i, row) in rows.into_iter().flatten().enumerate() {
        let Some(title) = row.binding(4, 6, text as *const _ as u32, MESSAGE_BYTES) else {
            continue;
        };
        let Some(request) = row.binding(3, 20, texture as *const _ as u32, TEXTURE_BYTES) else {
            continue;
        };
        let object = if row.badge != 0 {
            row.badge
        } else {
            create(row, texture).map_err(|stage| {
                FAILURE.store(stage, Ordering::Relaxed);
                16u32
            })?
        };
        result[i] = Some(Decoration {
            object,
            title,
            root: row.root,
            request_visible: memory::word(request + 0x54).unwrap() & 1 != 0,
        });
    }
    Ok(result)
}

/// Size and AutoScale setters take integer/pointer arguments, unlike PosX's VFP
/// setter. Their native bodies do not invalidate text: match FontSize's +0xf0
/// bit16 (a5350c), consumed by a53aa8 to rebuild the cached glyph geometry.
fn fit_title(title: u32, width: f32, auto_scale: bool) {
    let flags = memory::word(title + 0xf0).unwrap();
    if memory::word(title + 0xc8) == Some(width.to_bits())
        && memory::word(title + 0xcc) == Some(38.0f32.to_bits())
        && flags & 1 == u32::from(auto_scale)
        && memory::word(title + 0xf8).unwrap() & 0xc0000 == 0
    {
        return;
    }
    let size = [width, 38.0];
    let set_size: unsafe extern "C" fn(u32, *const f32) =
        unsafe { core::mem::transmute((base() + 0xa53528) as usize) };
    unsafe { set_size(title, size.as_ptr()) };
    integer(0xa53348, title, u32::from(auto_scale));
    integer(0xa53324, title, 0); // Native AutoWrap enum: keep one line.
    unsafe { word(title + 0xf0, memory::word(title + 0xf0).unwrap() | 0x10000) };
}

#[derive(Clone, Copy)]
pub struct Decoration {
    pub object: u32,
    title: u32,
    root: u32,
    request_visible: bool,
}
impl Decoration {
    /// The original builder has already set request visibility for this row.
    /// Reserve four pixels before each badge; fit only badge-bearing titles.
    pub fn set(self, badge: Badge) {
        if badge != Badge::Hidden {
            let x: f32 = if self.request_visible { 329.0 } else { 365.0 };
            fit_title(self.title, x - 62.0 - 4.0, true);
            if memory::word(self.object + 0x80) != Some(x.to_bits()) {
                unsafe {
                    bits(self.object + 0x80, x);
                    word(
                        self.object + 0x54,
                        memory::word(self.object + 0x54).unwrap() | 0x20000,
                    );
                    word(
                        self.root + 0x8c,
                        memory::word(self.root + 0x8c).unwrap() | 2,
                    );
                }
            }
        }
        set(self.object, badge);
    }
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
