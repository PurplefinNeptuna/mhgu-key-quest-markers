//! Quest ID lists derived at build time by scripts/quest_unlocks.py from the game's
//! unlock script and NPC talk tables. IDs another mod adds are simply absent:
//! a miss means no badge.
include!(concat!(env!("OUT_DIR"), "/quest_lists.rs"));

/// Clearing this quest unlocks a different quest.
pub fn unlocks_another(id: u32) -> bool {
    UNLOCKS.binary_search(&id).is_ok()
}

/// This quest grants Hunter Arts or Felyne ingredients, or its clear is required
/// on the way to a quest that does.
pub fn leads_to_reward(id: u32) -> bool {
    REWARDS.binary_search(&id).is_ok()
}

/// Village tier (1..10) at which a rank-up urgent quest needs this quest although its
/// group is neither key nor urgent. The list is sorted by quest ID.
pub fn urgent_key_tier(id: u32) -> Option<u8> {
    let found = URGENT_KEYS.binary_search_by_key(&id, |&(quest, _)| quest).ok()?;
    Some(URGENT_KEYS[found].1)
}
