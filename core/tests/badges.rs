//! Badge decisions: keys, urgents, special encounters, unlock and reward badges.
use quest_badges_core::*;
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
fn urgent_chain_quests_are_keys_only_at_their_tier() {
    let mut s = state();
    s.unlocks = true;
    let chained = |g: Group, village: u16| {
        let g = urgent_chain(g, Some(5), village);
        let mut e = s;
        e.needed_key = needed_key(g, village, 0);
        decide(g, false, e)
    };
    assert_eq!(chained(group(0), 5), Badge::Key);
    assert_eq!(chained(group(0), 4), Badge::Unlocks);
    assert_eq!(chained(group(0), 6), Badge::Unlocks);
    let mut done = s;
    done.completed = true;
    let g = urgent_chain(group(0), Some(5), 5);
    assert_eq!(decide(g, false, done), Badge::Completed);
    // Real key and urgent groups keep their own category.
    assert_eq!(urgent_chain(group(3), Some(5), 5), group(3));
    assert_eq!(urgent_chain(group(29), Some(5), 5), group(29));
    assert_eq!(urgent_chain(group(0), None, 5), group(0));
    assert_eq!(urgent_chain(group(0), Some(0), 0), group(0));
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
#[test]
fn kept_colours_replace_grey_only_for_the_quests_own_clear() {
    let mut done = state();
    done.completed = true;
    // Urgent and key groups go back to red and green.
    assert_eq!(kept_colour(group(25), done, decide(group(25), true, done)), Badge::Urgent);
    assert_eq!(kept_colour(group(3), done, decide(group(3), false, done)), Badge::Key);
    // Other quests show orange before blue, as they did before the clear.
    let mut other = done;
    other.unlocks = true;
    assert_eq!(kept_colour(group(0), other, decide(group(0), false, other)), Badge::Unlocks);
    other.reward = true;
    assert_eq!(kept_colour(group(0), other, decide(group(0), false, other)), Badge::Reward);
    // Grey that is not the quest's own clear stays grey: an old key, a satisfied alternative.
    let mut old = state();
    old.needed_key = Some(false);
    assert_eq!(kept_colour(group(3), old, decide(group(3), false, old)), Badge::Completed);
    let mut alternative = state();
    alternative.alternative_done = true;
    assert_eq!(kept_colour(group(3), alternative, Badge::Completed), Badge::Completed);
    // Badges that are not grey pass through.
    assert_eq!(kept_colour(group(3), state(), Badge::Key), Badge::Key);
    assert_eq!(kept_colour(group(0), done, Badge::Hidden), Badge::Hidden);
}
