//! The game's GUI-holder API is not wrapped by Forge. Every pointer stays local
//! to the synchronous row callback; native calls are made only on the pinned build.
use crate::memory::{self, BASE};
use core::{
    ffi::CStr,
    sync::atomic::{AtomicU32, Ordering},
};
use quest_badges_core::{Badge, Evidence, Group};

static ERRORS: AtomicU32 = AtomicU32::new(0);
pub fn take_errors() -> u32 {
    ERRORS.swap(0, Ordering::Relaxed)
}
fn error(code: u32) {
    ERRORS.fetch_or(code, Ordering::Relaxed);
}
fn base() -> u32 {
    BASE.load(Ordering::Relaxed)
}
fn singleton(name: &CStr) -> Option<u32> {
    // Raw Forge lookup avoids creating &'static mut aliases of game singletons.
    let p =
        unsafe { forge::sys::singleton::forge_singleton_getInstanceByName(name.as_ptr().cast()) }
            as u32;
    (p != 0).then_some(p)
}
fn completed(profile: u32, id: u32) -> bool {
    let f: unsafe extern "C" fn(u32, u32) -> u8 =
        unsafe { core::mem::transmute((base() + 0x523da4) as usize) };
    // Caller established the exact group record; this avoids the reader's index-zero fallback.
    unsafe { f(profile + 0x42c, id) != 0 }
}
struct Groups {
    resource: u32,
    records: u32,
    count: u32,
}
impl Groups {
    fn read(quest: u32) -> Option<Self> {
        let resource = memory::word(quest.checked_add(0xb4)?)?;
        let count = memory::word(resource.checked_add(0x64)?)?;
        let records = memory::word(resource.checked_add(0x6c)?)?;
        if count == 0
            || count > 4096
            || records & 3 != 0
            || !memory::readable(records, count as usize * 12)
        {
            return None;
        }
        Some(Self {
            resource,
            records,
            count,
        })
    }
    fn at(&self, i: u32) -> Group {
        // The entire contiguous native array was checked above. No Rust reference
        // or resource pointer escapes this callback's native ownership boundary.
        let p = (self.records + i * 12) as *const u8;
        unsafe {
            Group {
                id: core::ptr::read_volatile(p.add(4).cast()),
                category: core::ptr::read_volatile(p.add(8)),
                alternative: core::ptr::read_volatile(p.add(9)),
            }
        }
    }
    fn find(&self, id: u32) -> Option<Group> {
        quest_badges_core::resolve_group((0..self.count).map(|i| self.at(i)), id)
    }
    fn unchanged(&self, quest: u32) -> bool {
        memory::word(quest + 0xb4) == Some(self.resource)
            && memory::word(self.resource + 0x64) == Some(self.count)
            && memory::word(self.resource + 0x6c) == Some(self.records)
    }
}
fn prerequisites(quest: u32, group: Group, stage: u16) -> bool {
    if group.category <= 33 {
        // This native Village counter handles alternative requirement groups and
        // returns bit zero when all required groups have a completed member.
        let f: unsafe extern "C" fn(u32, u32) -> u32 =
            unsafe { core::mem::transmute((base() + 0x3b1a18) as usize) };
        unsafe { f(quest, stage as u32) & 1 != 0 }
    } else {
        // Hub/G tiers use the native total/completed counter (stage + 10 category).
        let mut total = 0u32;
        let mut done = 0u32;
        let f: unsafe extern "C" fn(u32, *mut u32, *mut u32, u32) =
            unsafe { core::mem::transmute((base() + 0x3b1d70) as usize) };
        unsafe { f(quest, &mut total, &mut done, stage as u32) };
        total <= 4096 && done == total
    }
}
fn listed(selector: u32, id: u32) -> Option<bool> {
    // These are incomplete-urgent pools, not proof of current progression. The
    // policy additionally requires proven current availability and prerequisites.
    if !memory::readable(selector, 0x1b4) {
        return None;
    }
    let mut found = false;
    for category in 0..5u32 {
        let n = memory::half(selector + 0x1a8 + category * 2)? as u32;
        if n > 16 {
            return None;
        }
        for i in 0..n {
            if memory::word(selector + 0x68 + category * 0x40 + i * 4)? == id {
                found = true;
            }
        }
    }
    Some(found)
}
fn alternative(groups: &Groups, profile: u32, g: Group) -> bool {
    if g.category > 10 || !(1..=11).contains(&g.alternative) {
        return false;
    }
    (0..groups.count).any(|i| {
        let other = groups.at(i);
        other.category == g.category
            && other.alternative == g.alternative
            && completed(profile, other.id)
    })
}
fn badge_objects(ui: u32) -> Option<[u32; 8]> {
    let holder = memory::word(ui.checked_add(0x24)?)?;
    let count = memory::word(holder.checked_add(0x298)?)?;
    let array = memory::word(holder.checked_add(0xf8)?)?;
    if !(24..=512).contains(&count) || !memory::readable(array, count as usize * 4) {
        return None;
    }
    let dti = forge::mt::dti::MtDti::find("cGUIObjTexture")? as *const _ as u32;
    let mut result = [0; 8];
    for (i, object) in result.iter_mut().enumerate() {
        let instance = memory::word(array + (16 + i as u32) * 4)?;
        let objects = memory::word(instance.checked_add(0xd8)?)?;
        if !memory::readable(objects, 13 * 4) {
            return None;
        }
        let p = memory::word(objects + 12 * 4)?;
        if !memory::readable(p, 304) || memory::word(p + 0x50) != Some(21) {
            return None;
        }
        let vft = memory::word(p)?;
        let getter = memory::word(vft.checked_add(0x14)?)?;
        if !memory::executable(getter, 4) {
            return None;
        }
        let get: unsafe extern "C" fn(u32) -> u32 =
            unsafe { core::mem::transmute(getter as usize) };
        if unsafe { get(p) } != dti {
            return None;
        }
        *object = p;
    }
    Some(result)
}
fn set(ui: u32, row: usize, badge: Badge) {
    let visible: unsafe extern "C" fn(u32, u32, u32, u32) =
        unsafe { core::mem::transmute((base() + 0x56e530) as usize) };
    let color: unsafe extern "C" fn(u32, u32, u32, u32) =
        unsafe { core::mem::transmute((base() + 0x56e6fc) as usize) };
    // Slot 12 is the added object in resource instances 16..23. These native
    // setters handle object visibility and all four vertex colors respectively.
    unsafe {
        if badge != Badge::Hidden {
            color(ui, 16 + row as u32, 12, badge.rgba());
        }
        visible(ui, 16 + row as u32, 12, u32::from(badge != Badge::Hidden));
    }
}
/// Apply the copied decision after the normal game row update. Hide first so
/// invalid metadata cannot leave yesterday's quest badge on a newly reused row.
pub fn update(ui: u32, quests: u32) {
    let Some(_objects) = badge_objects(ui) else {
        error(1);
        return;
    };
    for i in 0..8 {
        set(ui, i, Badge::Hidden);
    }
    let Some(quest) = singleton(c"sQuest") else {
        error(2);
        return;
    };
    let Some(profile) = singleton(c"sUserInfo") else {
        error(2);
        return;
    };
    let Some(selector) = singleton(c"sQuestSelector") else {
        error(2);
        return;
    };
    // The native urgent-completion processor's first argument comes from this
    // non-DTI global record; its stages are separate from sUserInfo completion.
    let Some(progress) = memory::word(base() + 0x18979f0) else {
        error(4);
        return;
    };
    if !memory::readable(progress, 0x3e4) {
        error(4);
        return;
    }
    let Some(village) = memory::half(progress + 0x3e0) else {
        error(4);
        return;
    };
    let Some(hub) = memory::half(progress + 0x3e2) else {
        error(4);
        return;
    };
    if village > 10 || hub > 13 {
        error(4);
        return;
    }
    if !memory::readable(profile, 0x72c) || !memory::readable(quests, 32) {
        error(4);
        return;
    }
    let Some(groups) = Groups::read(quest) else {
        error(4);
        return;
    };
    let mut badges = [Badge::Hidden; 8];
    for (i, badge) in badges.iter_mut().enumerate() {
        let Some(data) = memory::word(quests + i as u32 * 4) else {
            continue;
        };
        if data == 0 || !memory::readable(data, 0x110) {
            continue;
        }
        let Some(id) = memory::word(data + 8) else {
            continue;
        };
        let Some(g) = groups.find(id) else {
            continue;
        };
        let Some(flags) = memory::half(data + 0x10c) else {
            continue;
        };
        let done = completed(profile, id);
        let is_urgent = quest_badges_core::urgent(g.category);
        let stage = if g.category <= 33 { village } else { hub };
        let prereq = !is_urgent || prerequisites(quest, g, stage);
        let Some(in_list) = listed(selector, id) else {
            error(4);
            return;
        };
        *badge = quest_badges_core::decide(
            g,
            flags & 1 != 0,
            Evidence {
                completed: done,
                // Availability/current requirement semantics remain unproved. In r1
                // these facts stay unresolved; stage/rank alone must never color a quest.
                needed_key: None,
                active_urgent: None,
                prerequisites_done: prereq,
                alternative_done: alternative(&groups, profile, g),
                urgent_listed: in_list,
            },
        );
    }
    if !groups.unchanged(quest) {
        error(4);
        return;
    }
    for (i, badge) in badges.into_iter().enumerate() {
        set(ui, i, badge);
    }
}
