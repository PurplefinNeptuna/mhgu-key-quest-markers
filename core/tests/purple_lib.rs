//! The Mod Options row values and help text.
use quest_badges_core::purple_lib::*;
#[test]
fn values_round_trip_and_reject_unknown() {
    for hide in [false, true] {
        assert_eq!(hide_from(hide_value(hide)), Some(hide));
    }
    assert_eq!(hide_from(2), None);
    assert_eq!(HIDE_GREY_LABELS.len(), 2);
    // The help bar shows about 40 columns a line.
    for line in HIDE_GREY_HELP.to_str().unwrap().split("\r\n") {
        assert!(line.len() <= 40, "{line}");
    }
}
