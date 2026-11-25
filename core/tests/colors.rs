//! Colour and grey badge settings, INI text and the load and save policy.
use quest_badges_core::{Badge, colors::*};
struct Disk {
    bytes: Text,
    mounts: i32,
    available: bool,
    fail: u8,
    writes: u32,
    commits: u32,
}
impl Disk {
    fn new() -> Self {
        Self {
            bytes: Text::new(),
            mounts: 0,
            available: true,
            fail: 0,
            writes: 0,
            commits: 0,
        }
    }
}
impl Files for Disk {
    fn mount(&mut self) -> bool {
        if !self.available {
            return false;
        }
        self.mounts += 1;
        true
    }
    fn unmount(&mut self) {
        self.mounts -= 1;
    }
    fn read(&mut self, out: &mut Text) -> Result<(), Error> {
        if self.fail == 2 {
            return Err(Error::Read);
        }
        if self.bytes.len == 0 {
            return Err(Error::Missing);
        }
        out.len = self.bytes.len;
        out.bytes[..out.len].copy_from_slice(&self.bytes.bytes[..out.len]);
        if self.fail == 3 {
            out.bytes[0] = b'!';
        }
        Ok(())
    }
    fn write(&mut self, text: &Text) -> Result<(), Error> {
        self.writes += 1;
        if self.fail == 1 {
            return Err(Error::Write);
        }
        self.bytes.len = text.len;
        self.bytes.bytes[..text.len].copy_from_slice(&text.bytes[..text.len]);
        Ok(())
    }
    fn commit(&mut self) -> bool {
        self.commits += 1;
        self.fail != 4
    }
}
#[test]
fn defaults_and_packing() {
    let p = Palette::DEFAULT;
    assert_eq!(p.color(Badge::Key), 0xff056300);
    assert_eq!(p.color(Badge::Urgent), 0xff0000a3);
    assert_eq!(p.color(Badge::Completed), 0xff808080);
    assert_eq!(p.color(Badge::Unlocks), 0xffc23200);
    assert_eq!(p.color(Badge::Reward), 0xff007fff);
    assert_eq!(p.color(Badge::Hidden), 0);
    assert_eq!(
        Palette::parse(&p.text().unwrap().bytes[..p.text().unwrap().len]),
        Ok(p)
    );
}
#[test]
fn malformed_configuration() {
    for text in [
        "",
        "[Colors]\nkey=FF0000",
        "[Colors]\nkey=GG0000\nurgent=FFFFFF\ncompleted=808080",
        "[Colors]\nkey=000000\nkey=ffffff\nurgent=ffffff\ncompleted=808080",
        "key=123456",
        "[Colors\nkey=123456",
    ] {
        assert_eq!(Palette::parse(text.as_bytes()), Err(Error::Invalid));
    }
    assert_eq!(Palette::parse(b"\xff"), Err(Error::Invalid));
    assert_eq!(
        Palette::parse(b"; comment\n[Colors]\nkey=006305\nurgent=a30000\ncompleted=808080\n"),
        Ok(Palette::DEFAULT)
    );
    // A config saved before the unlocks colour keeps its colours and gains the default blue.
    assert_eq!(
        Palette::parse(b"[Colors]\nkey=123456\nurgent=a30000\ncompleted=808080\n"),
        Ok(Palette {
            key: 0x123456,
            ..Palette::DEFAULT
        })
    );
    assert_eq!(
        Palette::parse(b"[Colors]\nkey=006305\nurgent=a30000\ncompleted=808080\nunlocks=0000ff\n"),
        Ok(Palette {
            unlocks: 0x0000ff,
            ..Palette::DEFAULT
        })
    );
    assert_eq!(
        Palette::parse(b"[Colors]\nkey=006305\nurgent=a30000\ncompleted=808080\nreward=ffd700\n"),
        Ok(Palette {
            reward: 0xffd700,
            ..Palette::DEFAULT
        })
    );
    for text in [
        "[Colors]\nkey=006305\nurgent=a30000\ncompleted=808080\nunlocks=00ff\n",
        "[Colors]\nkey=006305\nurgent=a30000\ncompleted=808080\nunlocks=0000ff\nunlocks=0000ff\n",
    ] {
        assert_eq!(Palette::parse(text.as_bytes()), Err(Error::Invalid));
    }
}
#[test]
fn pending_reset_save_and_restart() {
    let mut disk = Disk::new();
    let mut p = Preferences::new();
    assert_eq!(p.load(&mut disk), Err(Error::Missing));
    assert_eq!(disk.writes, 0);
    let custom = Palette {
        key: 0x123456,
        urgent: 0x987654,
        completed: 0xabcdef,
        unlocks: 0x13579b,
        reward: 0x2468ac,
        grey: GreyBadges::Hidden,
    };
    p.edit(custom);
    assert_eq!(p.applied, Palette::DEFAULT);
    p.save(&mut disk).unwrap();
    assert_eq!(p.applied, custom);
    p.edit(Palette::DEFAULT);
    assert_eq!(p.applied, custom); // Reset is pending too.
    let mut restarted = Preferences::new();
    restarted.load(&mut disk).unwrap();
    assert_eq!(restarted.applied, custom);
    assert_eq!(disk.mounts, 0);
    assert_eq!(disk.commits, 1);
}
#[test]
fn unavailable_and_delayed_load() {
    let mut d = Disk::new();
    d.available = false;
    let mut p = Preferences::new();
    assert_eq!(p.load(&mut d), Err(Error::Unavailable));
    assert!(!p.loaded);
    assert_eq!(d.mounts, 0);
    let custom = Palette {
        key: 1,
        ..Palette::DEFAULT
    };
    p.edit(custom);
    d.available = true;
    p.load(&mut d).unwrap();
    assert_eq!(p.draft, custom);
    assert_eq!(d.writes, 0);
}
#[test]
fn failures_preserve_draft_applied_and_balance_mounts() {
    for (fail, error) in [
        (1, Error::Write),
        (2, Error::Verify),
        (3, Error::Verify),
        (4, Error::Commit),
    ] {
        let mut d = Disk::new();
        d.fail = fail;
        let mut p = Preferences::new();
        let custom = Palette {
            key: 1,
            ..Palette::DEFAULT
        };
        p.edit(custom);
        assert_eq!(p.save(&mut d), Err(error));
        assert_eq!(p.draft, custom);
        assert_eq!(p.applied, Palette::DEFAULT);
        assert_eq!(d.mounts, 0);
    }
    let mut d = Disk::new();
    assert_eq!(
        save(
            &mut d,
            Palette {
                key: 0x1000000,
                ..Palette::DEFAULT
            }
        ),
        Err(Error::Invalid)
    );
    assert_eq!(d.writes, 0);
}
#[test]
fn grey_badges_setting() {
    let colours = "[Colors]\nkey=006305\nurgent=a30000\ncompleted=808080\n";
    // A released r23 INI has no [Badges] section: grey badges stay grey.
    assert_eq!(Palette::parse(colours.as_bytes()), Ok(Palette::DEFAULT));
    for mode in GreyBadges::ALL {
        let text = [colours, "[Badges]\ngrey_badges = ", mode.name(), "\n"].concat();
        let palette = Palette {
            grey: mode,
            ..Palette::DEFAULT
        };
        assert_eq!(Palette::parse(text.as_bytes()), Ok(palette));
        let saved = palette.text().unwrap();
        let line = ["[Badges]\ngrey_badges = ", mode.name(), "\n"].concat();
        assert!(saved.bytes[..saved.len].ends_with(line.as_bytes()));
        assert_eq!(Palette::parse(&saved.bytes[..saved.len]), Ok(palette));
    }
    for bad in ["", "1", "colored", "Grey"] {
        let text = [colours, "[Badges]\ngrey_badges = ", bad, "\n"].concat();
        assert_eq!(Palette::parse(text.as_bytes()), Err(Error::Invalid), "{bad}");
    }
    let twice = [colours, "[Badges]\ngrey_badges=grey\ngrey_badges=grey\n"].concat();
    assert_eq!(Palette::parse(twice.as_bytes()), Err(Error::Invalid));
    let hidden = Palette {
        grey: GreyBadges::Hidden,
        ..Palette::DEFAULT
    };
    assert_eq!(hidden.visible(Badge::Completed), Badge::Hidden);
    assert_eq!(hidden.visible(Badge::Key), Badge::Key);
    for mode in [GreyBadges::Coloured, GreyBadges::Grey] {
        let palette = Palette {
            grey: mode,
            ..Palette::DEFAULT
        };
        assert_eq!(palette.visible(Badge::Completed), Badge::Completed);
    }
    // A Mod Options change before the INI loads survives the load.
    let mut disk = Disk::new();
    save(&mut disk, Palette::DEFAULT).unwrap();
    let mut p = Preferences::new();
    p.apply_grey(GreyBadges::Coloured);
    p.load(&mut disk).unwrap();
    assert_eq!((p.applied.grey, p.draft.grey), (GreyBadges::Coloured, GreyBadges::Coloured));
}
#[test]
fn mod_options_saves_only_what_is_applied() {
    let mut disk = Disk::new();
    let saved = Palette {
        urgent: 0x654321,
        ..Palette::DEFAULT
    };
    save(&mut disk, saved).unwrap();
    // A change before the INI loads: the load keeps it, and the save keeps the saved colours.
    let mut p = Preferences::new();
    disk.available = false;
    p.apply_grey(GreyBadges::Hidden);
    assert_eq!(p.save_applied(&mut disk), Err(Error::Unavailable));
    disk.available = true;
    p.save_applied(&mut disk).unwrap();
    let hidden = Palette {
        grey: GreyBadges::Hidden,
        ..saved
    };
    assert_eq!(p.applied, hidden);
    let mut restarted = Preferences::new();
    restarted.load(&mut disk).unwrap();
    assert_eq!(restarted.applied, hidden);
    // A colour edit stays pending until Save & apply.
    p.edit(Palette {
        key: 0x123456,
        ..p.draft
    });
    p.apply_grey(GreyBadges::Grey);
    p.save_applied(&mut disk).unwrap();
    let mut again = Preferences::new();
    again.load(&mut disk).unwrap();
    assert_eq!(again.applied, saved);
    assert_eq!(p.draft.key, 0x123456);
    assert_eq!(disk.mounts, 0);
}
