//! The game's GUI-holder API is not wrapped by Forge. Every pointer stays local
//! to the synchronous row callback; native calls are made only on the pinned build.
use crate::{
    gui,
    memory::{self, BASE},
    offers,
};
use core::{
    ffi::CStr,
    sync::atomic::{AtomicU32, Ordering},
};
use quest_badges_core::{Badge, Evidence, Group};

static ERRORS: AtomicU32 = AtomicU32::new(0);
// Two bounded development snapshots distinguish classification from rendering.
// Only scalars cross into onUpdate; native pointers never outlive the callback.
struct Snapshot {
    // 0=empty, 1=writer owns it, 2=published, 3=claimed by the lifecycle logger.
    state: AtomicU32,
    progress: AtomicU32,
    ids: [AtomicU32; 8],
    decisions: [AtomicU32; 8],
    flags: [AtomicU32; 8],
}
impl Snapshot {
    const fn new() -> Self {
        Self {
            state: AtomicU32::new(0),
            progress: AtomicU32::new(0),
            ids: [const { AtomicU32::new(0) }; 8],
            decisions: [const { AtomicU32::new(0) }; 8],
            flags: [const { AtomicU32::new(0) }; 8],
        }
    }
    fn publish(&self, progress: u32, ids: &[u32; 8], decisions: &[u32; 8], objects: &[u32; 8]) {
        if self
            .state
            .compare_exchange(0, 1, Ordering::Acquire, Ordering::Relaxed)
            .is_err()
        {
            return;
        }
        self.progress.store(progress, Ordering::Relaxed);
        for i in 0..8 {
            self.ids[i].store(ids[i], Ordering::Relaxed);
            self.decisions[i].store(decisions[i], Ordering::Relaxed);
            self.flags[i].store(
                memory::word(objects[i] + 0x54).unwrap_or(0),
                Ordering::Relaxed,
            );
        }
        self.state.store(2, Ordering::Release);
    }
    fn report(&self, label: &str) {
        // Claim this immutable snapshot once; acquire pairs with publication.
        if self
            .state
            .compare_exchange(2, 3, Ordering::Acquire, Ordering::Relaxed)
            .is_err()
        {
            return;
        }
        let p = self.progress.load(Ordering::Relaxed);
        log::error!(
            concat!(
                "Native quest badges ",
                env!("KQM_VERSION"),
                " diagnostic: {}, Village={}, Hub/G={}"
            ),
            label,
            p & 65535,
            p >> 16
        );
        for i in 0..8 {
            let d = self.decisions[i].load(Ordering::Relaxed);
            log::error!(
                concat!(
                    "Native quest badges ",
                    env!("KQM_VERSION"),
                    " diagnostic: row={} quest={} group={} quest_flags={:#x} badge={} gui_flags={:#x}"
                ),
                i,
                self.ids[i].load(Ordering::Relaxed),
                d & 255,
                (d >> 8) & 65535,
                d >> 24,
                self.flags[i].load(Ordering::Relaxed)
            );
        }
    }
}
static FIRST_PAGE: Snapshot = Snapshot::new();
static FIRST_VISIBLE: Snapshot = Snapshot::new();
pub fn report_diagnostics() {
    FIRST_PAGE.report("first classified page");
    FIRST_VISIBLE.report(
        "first visible badges; badge 0=hidden, 1=red, 2=grey, 3=purple; group 255=unresolved",
    );
}
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
fn available(quest: u32, id: u32, special: bool) -> bool {
    if special {
        // The normal counter predicate additionally checks its 51-entry enabled
        // bitfield (+0x35d4). These eight IDs are entries 0..7; scene flags alone
        // cannot distinguish the current first-run/repeat offer. Category 0xff
        // with null context bypasses only the unrelated DLC menu filter.
        let f: unsafe extern "C" fn(u32, u32, u32) -> u32 =
            unsafe { core::mem::transmute((base() + 0x54af8c) as usize) };
        return unsafe { f(id, 0xff, 0) == 1 };
    }
    // This is the same scene/quest-flag query used by the native counter's
    // availability predicate. It returns a bool and does not complete a quest.
    let f: unsafe extern "C" fn(u32, u32) -> u8 =
        unsafe { core::mem::transmute((base() + 0x3b2174) as usize) };
    unsafe { f(quest, id) != 0 }
}
fn alternative(groups: &Groups, profile: u32, g: Group) -> bool {
    if quest_badges_core::special_urgent(g.category) {
        // Native family table at main+0x162a8a0 pairs 47/48, 49/50, 51/52,
        // 53/54. Clearing either version satisfies that encounter's story event.
        return (0..groups.count).any(|i| {
            let other = groups.at(i);
            quest_badges_core::special_urgent(other.category)
                && (other.category - 47) / 2 == (g.category - 47) / 2
                && completed(profile, other.id)
        });
    }
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
fn set(object: Option<gui::Decoration>, badge: Badge) {
    if let Some(object) = object {
        object.set(badge);
    }
}
/// Apply the copied decision after the normal game row update. Hide first so
/// invalid metadata cannot leave yesterday's quest badge on a newly reused row.
pub fn update(ui: u32, quests: u32) {
    let objects = match gui::objects(ui) {
        Ok(objects) => objects,
        Err(flags) => {
            error(flags);
            return;
        }
    };
    if objects.iter().any(Option::is_none) {
        error(128);
    }
    for object in objects {
        set(object, Badge::Hidden);
    }
    let Some(quest) = singleton(c"sQuest") else {
        error(2);
        return;
    };
    let Some(profile) = singleton(c"sUserInfo") else {
        error(2);
        return;
    };
    let Some(offered) = offers::current(ui) else {
        error(8);
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
    let mut ids = [0; 8];
    let mut decisions = [255; 8];
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
        ids[i] = id;
        let Some(g) = groups.find(id) else {
            continue;
        };
        let Some(flags) = memory::half(data + 0x10c) else {
            continue;
        };
        let done = completed(profile, id);
        let is_urgent = quest_badges_core::urgent(g.category);
        let stage = if g.category <= 33 { village } else { hub };
        // Encounter pairs use the full normal counter availability predicate,
        // outside its rank-up pool and unrelated rank-key requirement.
        let special = quest_badges_core::special_urgent(g.category);
        let prereq = !is_urgent || special || prerequisites(quest, g, stage);
        let in_list = offered.contains(id);
        let active = is_urgent && (special || in_list) && available(quest, id, special);
        *badge = quest_badges_core::decide(
            g,
            flags & 1 != 0,
            Evidence {
                completed: done,
                needed_key: quest_badges_core::needed_key(g, village, hub),
                active_urgent: Some(active),
                prerequisites_done: prereq,
                alternative_done: alternative(&groups, profile, g),
                urgent_listed: in_list,
            },
        );
        // Pack category / u16 quest flags / badge into separate bytes. The
        // initial category 255 denotes an absent or conflicting group record.
        decisions[i] = u32::from(g.category) | (u32::from(flags) << 8) | ((*badge as u32) << 24);
    }
    if !groups.unchanged(quest) {
        error(4);
        return;
    }
    for (i, badge) in badges.into_iter().enumerate() {
        set(objects[i], badge);
    }
    let progress = u32::from(village) | (u32::from(hub) << 16);
    let objects = objects.map(|object| object.map_or(0, |object| object.object));
    FIRST_PAGE.publish(progress, &ids, &decisions, &objects);
    if badges.iter().any(|b| *b != Badge::Hidden) {
        FIRST_VISIBLE.publish(progress, &ids, &decisions, &objects);
    }
}
