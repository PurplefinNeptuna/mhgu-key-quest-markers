//! The Mod Options row values and help text.
use quest_badges_core::purple_lib::*;
#[test]
fn values_round_trip_and_reject_unknown() {
    for on in [false, true] {
        assert_eq!(switch_from(switch_value(on)), Some(on));
    }
    assert_eq!(switch_from(2), None);
    assert_eq!(LABELS.len(), 2);
    assert_eq!(ROW_NAMES.len(), ROWS as usize);
    // The help bar shows about 40 columns a line.
    for help in ROW_HELP {
        for line in help.to_str().unwrap().split("\r\n") {
            assert!(line.len() <= 40, "{line}");
        }
    }
}
