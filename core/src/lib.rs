//! Plain badge decisions. Native offsets, pointers and calls stay in the adapter.
#![no_std]

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
    Red,
    Grey,
    Yellow,
}
impl Badge {
    /// Native polygon setters consume four RGBA bytes packed into an ARM word.
    pub const fn rgba(self) -> u32 {
        match self {
            Self::Hidden => 0,
            Self::Red => 0xff2547e7,
            Self::Grey => 0xff808080,
            Self::Yellow => 0xff39d2ff,
        }
    }
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
}
pub const fn key(category: u8) -> bool {
    (category >= 1 && category <= 17) || (category >= 19 && category <= 22)
}
pub const fn urgent(category: u8) -> bool {
    category >= 24 && category <= 46
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
/// Identity requires agreement between the native group and urgency flag.
/// Completion and satisfied alternatives cannot turn red/yellow. An unresolved
/// unfinished quest stays hidden instead of assuming that its rank is current.
pub fn decide(group: Group, urgent_flag: bool, state: Evidence) -> Badge {
    if group.id == 0 {
        return Badge::Hidden;
    }
    if urgent(group.category) {
        if !urgent_flag {
            return Badge::Hidden;
        }
        if state.completed {
            return Badge::Grey;
        }
        return match state.active_urgent {
            None => Badge::Hidden,
            Some(true) if state.prerequisites_done && state.urgent_listed => Badge::Yellow,
            _ => Badge::Grey,
        };
    }
    if urgent_flag || !key(group.category) {
        return Badge::Hidden;
    }
    if state.completed || state.alternative_done {
        return Badge::Grey;
    }
    match state.needed_key {
        None => Badge::Hidden,
        Some(true) => Badge::Red,
        Some(false) => Badge::Grey,
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
    fn current_completed_and_obsolete_keys() {
        for category in [1, 10, 11, 17, 19, 22] {
            let mut s = state();
            assert_eq!(decide(group(category), false, s), Badge::Red);
            s.completed = true;
            assert_eq!(decide(group(category), false, s), Badge::Grey);
            s.completed = false;
            s.needed_key = Some(false);
            assert_eq!(decide(group(category), false, s), Badge::Grey);
        }
    }
    #[test]
    fn urgent_current_old_unavailable_and_completed() {
        for category in [24, 25, 29, 33, 34, 35, 43, 46] {
            let g = group(category);
            let mut s = state();
            assert_eq!(decide(g, true, s), Badge::Yellow);
            s.urgent_listed = false;
            assert_eq!(decide(g, true, s), Badge::Grey);
            s.urgent_listed = true;
            s.prerequisites_done = false;
            assert_eq!(decide(g, true, s), Badge::Grey);
            s = state();
            s.completed = true;
            assert_eq!(decide(g, true, s), Badge::Grey);
            s.completed = false;
            s.active_urgent = Some(false);
            assert_eq!(decide(g, true, s), Badge::Grey);
        }
    }
    #[test]
    fn alternatives_and_unresolved_records() {
        let mut s = state();
        s.alternative_done = true;
        assert_eq!(decide(group(1), false, s), Badge::Grey);
        s = state();
        s.needed_key = None;
        s.active_urgent = None;
        assert_eq!(decide(group(1), false, s), Badge::Hidden);
        assert_eq!(decide(group(25), true, s), Badge::Hidden);
        assert_eq!(decide(group(1), true, s), Badge::Hidden);
        assert_eq!(decide(group(25), false, s), Badge::Hidden);
        for category in [0, 18, 23, 47, 255] {
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
                Badge::Yellow
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
            Badge::Grey
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
            Badge::Yellow
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
        assert_eq!(decide(g, false, s), Badge::Grey);
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
                Badge::Red,
                Badge::Yellow,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden,
                Badge::Hidden
            ]
        );
        assert_eq!(draw([None; 8]), [Badge::Hidden; 8]);
        assert_eq!(draw(page)[0], Badge::Red);
    }
    #[test]
    fn exact_opaque_colors() {
        assert_eq!(Badge::Red.rgba().to_le_bytes(), [231, 71, 37, 255]);
        assert_eq!(Badge::Grey.rgba().to_le_bytes(), [128, 128, 128, 255]);
        assert_eq!(Badge::Yellow.rgba().to_le_bytes(), [255, 210, 57, 255]);
    }
}
