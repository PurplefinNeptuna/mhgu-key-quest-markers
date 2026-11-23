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
