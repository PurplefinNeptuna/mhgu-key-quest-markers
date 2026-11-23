//! RGB configuration and persistence policy, independent of Forge and game pointers.
use crate::Badge;
use core::fmt::{self, Write};

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Palette {
    pub key: u32,
    pub urgent: u32,
    pub completed: u32,
    pub unlocks: u32,
    pub reward: u32,
}
impl Palette {
    // Exact game UI colours: counter_down Gathering object16, objective
    // instance14 and the Capture category's blue; provenance and offsets are in
    // research/theme-colours.json. The reward orange was chosen by the user.
    pub const DEFAULT: Self = Self {
        key: 0x006305,
        urgent: 0xa30000,
        completed: 0x808080,
        unlocks: 0x0032c2,
        reward: 0xff7f00,
    };
    pub fn color(self, badge: Badge) -> u32 {
        let rgb = match badge {
            Badge::Hidden => return 0,
            Badge::Key => self.key,
            Badge::Urgent => self.urgent,
            Badge::Completed => self.completed,
            Badge::Unlocks => self.unlocks,
            Badge::Reward => self.reward,
        };
        // Config uses RRGGBB; native ARM colour words store bytes R,G,B,A.
        0xff000000 | ((rgb & 255) << 16) | (rgb & 0xff00) | ((rgb >> 16) & 255)
    }
    pub fn valid(self) -> bool {
        [self.key, self.urgent, self.completed, self.unlocks, self.reward]
            .iter()
            .all(|v| *v <= 0xffffff)
    }
    pub fn parse(bytes: &[u8]) -> Result<Self, Error> {
        let text = core::str::from_utf8(bytes).map_err(|_| Error::Invalid)?;
        let mut section = false;
        let mut values = [None; 5];
        for line in text.lines().map(str::trim) {
            if line.is_empty() || line.starts_with(';') || line.starts_with('#') {
                continue;
            }
            if line.starts_with('[') {
                if !line.ends_with(']') {
                    return Err(Error::Invalid);
                }
                section = line == "[Colors]";
                continue;
            }
            let (key, value) = line.split_once('=').ok_or(Error::Invalid)?;
            if !section {
                continue;
            }
            let index = match key.trim() {
                "key" => 0,
                "urgent" => 1,
                "completed" => 2,
                "unlocks" => 3,
                "reward" => 4,
                _ => continue,
            };
            let value = value.trim();
            if values[index].is_some()
                || value.len() != 6
                || !value.bytes().all(|b| b.is_ascii_hexdigit())
            {
                return Err(Error::Invalid);
            }
            values[index] = Some(u32::from_str_radix(value, 16).map_err(|_| Error::Invalid)?);
        }
        Ok(Self {
            key: values[0].ok_or(Error::Invalid)?,
            urgent: values[1].ok_or(Error::Invalid)?,
            completed: values[2].ok_or(Error::Invalid)?,
            // Absent in configs saved before these colours existed; they keep their other colours.
            unlocks: values[3].unwrap_or(Self::DEFAULT.unlocks),
            reward: values[4].unwrap_or(Self::DEFAULT.reward),
        })
    }
    pub fn text(self) -> Result<Text, Error> {
        if !self.valid() {
            return Err(Error::Invalid);
        }
        let mut out = Text::new();
        write!(
            out,
            "[Colors]\nkey = {:06X}\nurgent = {:06X}\ncompleted = {:06X}\nunlocks = {:06X}\nreward = {:06X}\n",
            self.key, self.urgent, self.completed, self.unlocks, self.reward
        )
        .map_err(|_| Error::Invalid)?;
        Ok(out)
    }
}
/// Fixed bound prevents damaged save files from requesting arbitrary allocations.
pub struct Text {
    pub bytes: [u8; 1024],
    pub len: usize,
}
impl Text {
    pub const fn new() -> Self {
        Self {
            bytes: [0; 1024],
            len: 0,
        }
    }
}
impl Write for Text {
    fn write_str(&mut self, s: &str) -> fmt::Result {
        if self.len + s.len() > self.bytes.len() {
            return Err(fmt::Error);
        }
        self.bytes[self.len..self.len + s.len()].copy_from_slice(s.as_bytes());
        self.len += s.len();
        Ok(())
    }
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Error {
    Unavailable,
    Missing,
    Invalid,
    Read,
    Write,
    Verify,
    Commit,
}
impl Error {
    pub fn message(self) -> &'static str {
        match self {
            Self::Unavailable => "Save storage unavailable; load a player save and retry",
            Self::Missing => "No config found; using defaults",
            Self::Invalid => "Invalid config; using defaults",
            Self::Read => "Could not read config",
            Self::Write => "Could not write config",
            Self::Verify => "Config verification failed",
            Self::Commit => "Config commit failed",
        }
    }
}
/// Implementations own and close each handle; this policy owns the counted mount.
pub trait Files {
    fn mount(&mut self) -> bool;
    fn unmount(&mut self);
    fn read(&mut self, out: &mut Text) -> Result<(), Error>;
    fn write(&mut self, text: &Text) -> Result<(), Error>;
    fn commit(&mut self) -> bool;
}
struct Mount<'a, F: Files>(&'a mut F);
impl<F: Files> Drop for Mount<'_, F> {
    fn drop(&mut self) {
        self.0.unmount();
    }
}
pub fn load(files: &mut impl Files) -> Result<Palette, Error> {
    if !files.mount() {
        return Err(Error::Unavailable);
    }
    let mount = Mount(files);
    let mut text = Text::new();
    mount.0.read(&mut text)?;
    Palette::parse(&text.bytes[..text.len])
}
pub fn save(files: &mut impl Files, palette: Palette) -> Result<(), Error> {
    let text = palette.text()?; // Validate before mounting or touching existing contents.
    if !files.mount() {
        return Err(Error::Unavailable);
    }
    let mount = Mount(files);
    mount.0.write(&text)?;
    let mut check = Text::new();
    mount.0.read(&mut check).map_err(|_| Error::Verify)?;
    if check.bytes[..check.len] != text.bytes[..text.len] {
        return Err(Error::Verify);
    }
    if !mount.0.commit() {
        return Err(Error::Commit);
    }
    Ok(())
}
/// Draft and applied state are distinct: reset/edit never publish to native rows.
#[derive(Clone, Copy)]
pub struct Preferences {
    pub draft: Palette,
    pub applied: Palette,
    pub loaded: bool,
}
impl Preferences {
    pub const fn new() -> Self {
        Self {
            draft: Palette::DEFAULT,
            applied: Palette::DEFAULT,
            loaded: false,
        }
    }
    pub fn edit(&mut self, value: Palette) {
        self.draft = value;
        self.loaded = true;
    }
    pub fn load(&mut self, files: &mut impl Files) -> Result<(), Error> {
        if self.loaded {
            return Ok(());
        }
        match load(files) {
            Ok(value) => {
                self.applied = value;
                self.draft = value;
                self.loaded = true;
                Ok(())
            }
            Err(Error::Unavailable) => Err(Error::Unavailable),
            Err(reason) => {
                self.loaded = true;
                Err(reason)
            }
        }
    }
    pub fn save(&mut self, files: &mut impl Files) -> Result<(), Error> {
        self.loaded = true;
        save(files, self.draft)?;
        self.applied = self.draft;
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
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
}
