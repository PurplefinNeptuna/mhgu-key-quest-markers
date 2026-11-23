//! Plain badge decisions. Native offsets, pointers and calls stay in the adapter.
#![no_std]
pub mod colors;

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
#[cfg(test)]
mod tests {
    use super::*;
    fn state() -> Evidence {
        Evidence {
            completed: false,
            needed_key: Some(true),
            active_urgent: Some(true),
            prerequisites_done: true,
            alternative_done: false,
            urgent_listed: true,
            unlocks: false,
            reward: false,
        }
    }
    #[test]
    fn unlocking_quests_are_blue_until_cleared_and_never_outrank_keys() {
        let mut s = state();
        s.unlocks = true;
        for category in [0, 18, 23, 55, 129, 255] {
            assert_eq!(decide(group(category), false, s), Badge::Unlocks);
            let mut done = s;
            done.completed = true;
            assert_eq!(decide(group(category), false, done), Badge::Completed);
            assert_eq!(decide(group(category), false, state()), Badge::Hidden);
            // Conflicting urgent flag on a non-urgent group stays hidden.
            assert_eq!(decide(group(category), true, s), Badge::Hidden);
        }
        assert_eq!(decide(group(1), false, s), Badge::Key);
        assert_eq!(decide(group(25), true, s), Badge::Urgent);
        let mut unknown = s;
        unknown.needed_key = None;
        unknown.active_urgent = None;
        assert_eq!(decide(group(1), false, unknown), Badge::Hidden);
        assert_eq!(decide(group(25), true, unknown), Badge::Hidden);
        assert_eq!(decide(Group { id: 0, ..group(0) }, false, s), Badge::Hidden);
    }
    #[test]
    fn reward_quests_are_orange_over_blue_and_under_keys() {
        let mut s = state();
        s.reward = true;
        for unlocks in [false, true] {
            s.unlocks = unlocks;
            assert_eq!(decide(group(0), false, s), Badge::Reward);
            let mut done = s;
            done.completed = true;
            assert_eq!(decide(group(0), false, done), Badge::Completed);
            assert_eq!(decide(group(0), true, s), Badge::Hidden);
            assert_eq!(decide(group(1), false, s), Badge::Key);
            assert_eq!(decide(group(25), true, s), Badge::Urgent);
        }
    }
    fn group(category: u8) -> Group {
        Group {
            id: 1,
            category,
            alternative: 0,
        }
    }
    #[test]
    fn a_window_accepts_only_a_foreign_forge_entry_hook() {
        let original = [7u8; 32];
        assert!(window_matches(&original, &original));
        let mut hooked = original;
        hooked[..4].copy_from_slice(&0xe51f_f004u32.to_le_bytes());
        hooked[4..8].copy_from_slice(&0x0320_1000u32.to_le_bytes());
        assert!(window_matches(&hooked, &original));
        let mut stray = original;
        stray[0] ^= 1;
        assert!(!window_matches(&stray, &original));
        let mut later = hooked;
        later[8] ^= 1;
        assert!(!window_matches(&later, &original));
    }
    #[test]
    fn current_completed_and_obsolete_keys() {
        for category in [1, 10, 11, 17, 19, 22] {
            let mut s = state();
            assert_eq!(decide(group(category), false, s), Badge::Key);
            s.completed = true;
            assert_eq!(decide(group(category), false, s), Badge::Completed);
            s.completed = false;
            s.needed_key = Some(false);
            assert_eq!(decide(group(category), false, s), Badge::Completed);
        }
    }
    #[test]
    fn urgent_current_old_unavailable_and_completed() {
        for category in [24, 25, 29, 33, 34, 35, 43, 46] {
            let g = group(category);
            let mut s = state();
            assert_eq!(decide(g, true, s), Badge::Urgent);
            s.urgent_listed = false;
            assert_eq!(decide(g, true, s), Badge::Completed);
            s.urgent_listed = true;
            s.prerequisites_done = false;
            assert_eq!(decide(g, true, s), Badge::Completed);
            s = state();
            s.completed = true;
            assert_eq!(decide(g, true, s), Badge::Completed);
            s.completed = false;
            s.active_urgent = Some(false);
            assert_eq!(decide(g, true, s), Badge::Completed);
        }
    }
    #[test]
    fn special_encounters_use_availability_and_shared_completion() {
        // Actual IDs/categories from the hashed Village quest/group resources.
        for (id, category) in [
            (308, 47),
            (309, 48),
            (319, 49),
            (320, 50),
            (324, 51),
            (325, 52),
            (329, 53),
            (330, 54),
        ] {
            let g = Group {
                id,
                category,
                alternative: (category - 47) / 2 + 1,
            };
            let mut s = state();
            s.urgent_listed = false;
            s.prerequisites_done = false; // Rank-up requirements do not gate these.
            assert_eq!(decide(g, false, s), Badge::Urgent);
            s.alternative_done = true;
            assert_eq!(decide(g, false, s), Badge::Completed);
            s.alternative_done = false;
            s.active_urgent = Some(false);
            assert_eq!(decide(g, false, s), Badge::Completed);
            s.active_urgent = None;
            assert_eq!(decide(g, false, s), Badge::Hidden);
            s.completed = true;
            assert_eq!(decide(g, false, s), Badge::Completed);
        }
    }
    #[test]
    fn alternatives_and_unresolved_records() {
        let mut s = state();
        s.alternative_done = true;
        assert_eq!(decide(group(1), false, s), Badge::Completed);
        s = state();
        s.needed_key = None;
        s.active_urgent = None;
        assert_eq!(decide(group(1), false, s), Badge::Hidden);
        assert_eq!(decide(group(25), true, s), Badge::Hidden);
        assert_eq!(decide(group(1), true, s), Badge::Hidden);
        assert_eq!(decide(group(25), false, s), Badge::Hidden);
        for category in [0, 18, 23, 55, 255] {
            assert_eq!(decide(group(category), false, state()), Badge::Hidden);
        }
        assert_eq!(
            decide(
                Group {
                    id: 0,
                    category: 1,
                    alternative: 0
                },
                false,
                state()
            ),
            Badge::Hidden
        );
    }
    #[test]
    fn simultaneous_urgents_are_independent() {
        // Synthetic verified availability facts: this does not assert which
        // specific native quest IDs form a simultaneous urgent group.
        let mut s = state();
        for id in [1, 2] {
            assert_eq!(
                decide(
                    Group {
                        id,
                        category: 43,
                        alternative: 0
                    },
                    true,
                    s
                ),
                Badge::Urgent
            );
        }
        s.completed = true;
        assert_eq!(
            decide(
                Group {
                    id: 1,
                    category: 43,
                    alternative: 0
                },
                true,
                s
            ),
            Badge::Completed
        );
        assert_eq!(
            decide(
                Group {
                    id: 2,
                    category: 43,
                    alternative: 0
                },
                true,
                state()
            ),
            Badge::Urgent
        );
    }
    #[test]
    fn viewing_is_not_completion_and_rows_reuse_no_state() {
        let g = group(1);
        let before = decide(g, false, state());
        for _ in 0..10 {
            assert_eq!(decide(g, false, state()), before);
        }
        assert_eq!(decide(group(0), false, state()), Badge::Hidden);
        let mut s = state();
        s.completed = true;
        assert_eq!(decide(g, false, s), Badge::Completed);
    }
    #[test]
    fn duplicate_missing_and_conflicting_metadata() {
        let g = group(1);
        assert_eq!(resolve_group([g, g].into_iter(), 1), Some(g));
        assert_eq!(resolve_group([g].into_iter(), 2), None);
        assert_eq!(
            resolve_group([g, Group { category: 2, ..g }].into_iter(), 1),
            None
        );
        assert_eq!(
            resolve_group(
                [
                    g,
                    Group {
                        alternative: 1,
                        ..g
                    }
                ]
                .into_iter(),
                1
            ),
            None
        );
    }
    #[test]
    fn native_progression_domains_and_g_entry() {
        assert_eq!(needed_key(group(2), 2, 1), Some(true));
        assert_eq!(needed_key(group(1), 2, 1), Some(false));
        assert_eq!(needed_key(group(19), 2, 9), Some(true));
        assert_eq!(needed_key(group(17), 2, 9), Some(false));
        assert_eq!(needed_key(group(10), 10, 13), Some(true));
        assert_eq!(needed_key(group(22), 10, 13), Some(false));
        assert_eq!(needed_key(group(18), 2, 8), None);
        assert_eq!(needed_key(group(1), 0, 1), None);
        assert_eq!(needed_key(group(11), 0, 1), Some(true));
    }
    #[test]
    fn unused_rows_and_menu_transition_do_not_retain_badges() {
        let page = [
            Some(group(1)),
            Some(group(25)),
            None,
            None,
            None,
            None,
            None,
            None,
        ];
        let draw = |page: [Option<Group>; 8]| {
            page.map(|g| g.map_or(Badge::Hidden, |g| decide(g, urgent(g.category), state())))
        };
        assert_eq!(
            draw(page),
            [
                Badge::Key,
                Badge::Urgent,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden
            ]
        );
        assert_eq!(draw([None; 8]), [Badge::Hidden; 8]);
        assert_eq!(draw(page)[0], Badge::Key);
    }
    #[test]
    fn exact_opaque_colors() {
        assert_eq!(
            colors::Palette::DEFAULT.color(Badge::Key).to_le_bytes(),
            [0, 99, 5, 255]
        );
        assert_eq!(
            colors::Palette::DEFAULT
                .color(Badge::Completed)
                .to_le_bytes(),
            [128, 128, 128, 255]
        );
        assert_eq!(
            colors::Palette::DEFAULT.color(Badge::Urgent).to_le_bytes(),
            [163, 0, 0, 255]
        );
        assert_eq!(
            colors::Palette::DEFAULT.color(Badge::Unlocks).to_le_bytes(),
            [0, 50, 194, 255]
        );
        assert_eq!(
            colors::Palette::DEFAULT.color(Badge::Reward).to_le_bytes(),
            [255, 127, 0, 255]
        );
    }
}
