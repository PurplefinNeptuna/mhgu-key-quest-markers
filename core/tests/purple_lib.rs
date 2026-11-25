//! The Mod Options row's labels and help text.
use quest_badges_core::colors::GreyBadges;
use quest_badges_core::purple_lib::*;
#[test]
fn labels_follow_the_setting_values() {
    assert_eq!(GREY_LABELS.len(), GreyBadges::ALL.len());
    for (value, mode) in GreyBadges::ALL.into_iter().enumerate() {
        assert_eq!(mode as usize, value);
        assert_eq!(GreyBadges::from_value(value as u32), Some(mode));
    }
    assert_eq!(GreyBadges::from_value(3), None);
    assert_eq!(GREY_LABELS[GreyBadges::Grey as usize].to_str().unwrap(), "Grey");
    // The help bar shows about 40 columns a line, and a value about 11.
    for line in GREY_HELP.to_str().unwrap().split("\r\n") {
        assert!(line.len() <= 40, "{line}");
    }
    for label in GREY_LABELS {
        assert!(label.to_bytes().len() <= 11);
    }
}
