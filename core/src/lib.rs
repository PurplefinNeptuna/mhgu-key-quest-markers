//! Plain badge decisions. Native offsets, pointers and calls stay in the adapter.
#![no_std]
pub mod colors;
pub mod purple_lib;

/// A required code window as it may legitimately be found: the original bytes, or the original bytes
/// with another plugin's Forge entry hook (`ldr pc, [pc, #-4]` plus its detour address) over the first
/// eight. Both of this mod's hooks only run code around the original, so they chain onto such a hook.
pub fn window_matches(actual: &[u8; 32], expected: &[u8; 32]) -> bool {
    actual == expected || (actual[..4] == 0xe51f_f004u32.to_le_bytes() && actual[8..] == expected[8..])
}

/// The native group record's category is key tier or urgent tier, not quest type.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Group {
    pub id: u32,
    pub category: u8,
    pub alternative: u8,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Badge {
    Hidden,
    Key,
    Completed,
    Urgent,
    Unlocks,
    Reward,
}
/// None means the adapter could not prove relevance/availability. These facts
/// must come from native progression, never from the page currently being viewed.
#[derive(Clone, Copy, Debug)]
pub struct Evidence {
    pub completed: bool,
    pub needed_key: Option<bool>,
    pub active_urgent: Option<bool>,
    pub prerequisites_done: bool,
    pub alternative_done: bool,
    pub urgent_listed: bool,
    /// Clearing this quest unlocks a different quest (build-time unlock list).
    pub unlocks: bool,
    /// Grants Hunter Arts or ingredients, or leads to a quest that does (build-time list).
    pub reward: bool,
}
pub const fn key(category: u8) -> bool {
    (category >= 1 && category <= 17) || (category >= 19 && category <= 22)
}
/// These four Village encounter pairs are urgent on Kiranico but do not set
/// cQuestData's rank-up urgent bit. Consecutive categories share one story event.
pub const fn special_urgent(category: u8) -> bool {
    category >= 47 && category <= 54
}
pub const fn urgent(category: u8) -> bool {
    category >= 24 && category <= 54
}
/// Reject missing/conflicting metadata; identical native duplicates retain their
/// original completion-array positions but agree on the badge's identity.
pub fn resolve_group(records: impl Iterator<Item = Group>, id: u32) -> Option<Group> {
    let mut found = None;
    for g in records.filter(|g| g.id == id) {
        if found.is_some_and(|previous| previous != g) {
            return None;
        }
        found = Some(g);
    }
    found
}
/// Native script progression exposes Village tiers 1..10 and Hub/G tiers 1..13.
/// Key group categories are Village tier and Hub/G tier + 10; category 18 is
/// the key-free G-entry transition. Only the quest's own domain must be known.
pub fn needed_key(group: Group, village: u16, hub: u16) -> Option<bool> {
    if !key(group.category) {
        return None;
    }
    let (tier, limit, category) = if group.category <= 10 {
        (village, 10, group.category as u16)
    } else {
        (hub, 13, group.category as u16 - 10)
    };
    if tier == 0 || tier > limit {
        return None;
    }
    Some(category == tier)
}
/// A quest outside the key and urgent categories that the rank-up urgent quest of
/// Village tier `chain` needs (build-time list). At that tier it reads as one of the
/// tier's key quests; at any other tier, or with no chain tier, it is unchanged.
pub fn urgent_chain(group: Group, chain: Option<u8>, village: u16) -> Group {
    match chain {
        Some(tier)
            if (1..=10).contains(&tier)
                && village == tier as u16
                && !key(group.category)
                && !urgent(group.category) =>
        {
            Group {
                category: tier,
                alternative: 0,
                ..group
            }
        }
        _ => group,
    }
}
/// Rank-up identity requires the native group and urgency flag; the separate
/// Village encounter groups use their native availability and pair completion.
/// Completion and satisfied alternatives cannot turn key/urgent. An unresolved
/// unfinished quest stays hidden instead of assuming that its rank is current.
/// Key and urgent quests keep their own badge. Any other reward or reward-chain
/// quest is orange, and any other quest that unlocks another is blue; both turn grey once cleared.
pub fn decide(group: Group, urgent_flag: bool, state: Evidence) -> Badge {
    let badge = rank_badge(group, urgent_flag, state);
    // An urgent flag on a non-urgent group is conflicting metadata and stays hidden.
    let ranked = urgent_flag || urgent(group.category) || key(group.category);
    if badge != Badge::Hidden || group.id == 0 || ranked || !(state.reward || state.unlocks) {
        return badge;
    }
    if state.completed {
        Badge::Completed
    } else if state.reward {
        Badge::Reward
    } else {
        Badge::Unlocks
    }
}
fn rank_badge(group: Group, urgent_flag: bool, state: Evidence) -> Badge {
    if group.id == 0 {
        return Badge::Hidden;
    }
    if urgent(group.category) {
        if !urgent_flag && !special_urgent(group.category) {
            return Badge::Hidden;
        }
        if state.completed || (special_urgent(group.category) && state.alternative_done) {
            return Badge::Completed;
        }
        return match state.active_urgent {
            None => Badge::Hidden,
            Some(true)
                if special_urgent(group.category)
                    || (state.prerequisites_done && state.urgent_listed) =>
            {
                Badge::Urgent
            }
            _ => Badge::Completed,
        };
    }
    if urgent_flag || !key(group.category) {
        return Badge::Hidden;
    }
    if state.completed || state.alternative_done {
        return Badge::Completed;
    }
    match state.needed_key {
        None => Badge::Hidden,
        Some(true) => Badge::Key,
        Some(false) => Badge::Completed,
    }
}
