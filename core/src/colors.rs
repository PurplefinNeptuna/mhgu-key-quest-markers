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
    /// How gray badges show (INI `[Badges] gray_badges`).
    pub grey: GreyBadges,
}
/// How a grey badge shows. The value is the Mod Options row's: Coloured, Grey, Hidden.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum GreyBadges {
    /// A quest whose own clear made it grey keeps the badge it had before; other grey stays grey.
    Coloured = 0,
    Grey = 1,
    /// Every grey badge is hidden.
    Hidden = 2,
}
impl GreyBadges {
    pub const ALL: [Self; 3] = [Self::Coloured, Self::Grey, Self::Hidden];
    /// The INI value.
    pub fn name(self) -> &'static str {
        ["colored", "gray", "hidden"][self as usize]
    }
    pub fn from_value(value: u32) -> Option<Self> {
        Self::ALL.get(value as usize).copied()
    }
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
        grey: GreyBadges::Grey,
    };
    /// The badge a row shows: grey becomes hidden while grey badges are Hidden.
    pub fn visible(self, badge: Badge) -> Badge {
        if self.grey == GreyBadges::Hidden && badge == Badge::Completed {
            Badge::Hidden
        } else {
            badge
        }
    }
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
        let mut section = "";
        let mut values = [None; 5];
        let mut grey = None;
        for line in text.lines().map(str::trim) {
            if line.is_empty() || line.starts_with(';') || line.starts_with('#') {
                continue;
            }
            if line.starts_with('[') {
                if !line.ends_with(']') {
                    return Err(Error::Invalid);
                }
                section = line;
                continue;
            }
            let (key, value) = line.split_once('=').ok_or(Error::Invalid)?;
            if section == "[Badges]" && key.trim() == "gray_badges" {
                let mode = GreyBadges::ALL.into_iter().find(|m| m.name() == value.trim());
                if grey.replace(mode.ok_or(Error::Invalid)?).is_some() {
                    return Err(Error::Invalid);
                }
                continue;
            }
            if section != "[Colors]" {
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
            // Absent in configs saved before the setting existed: grey badges stay grey.
            grey: grey.unwrap_or(GreyBadges::Grey),
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
        write!(out, "[Badges]\ngray_badges = {}\n", self.grey.name())
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
    /// Grey badges set through Mod Options, possibly before the INI loaded; a later load keeps it.
    pub grey_override: Option<GreyBadges>,
}
impl Preferences {
    pub const fn new() -> Self {
        Self {
            draft: Palette::DEFAULT,
            applied: Palette::DEFAULT,
            loaded: false,
            grey_override: None,
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
                if let Some(grey) = self.grey_override {
                    self.apply_grey(grey);
                }
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
    /// A change made elsewhere (Mod Options) that already applies: it joins both the applied and
    /// the draft palette, and a disk load that has not happened yet keeps it.
    pub fn apply_grey(&mut self, grey: GreyBadges) {
        self.applied.grey = grey;
        self.draft.grey = grey;
        self.grey_override = Some(grey);
    }
    /// Save what is applied, leaving pending colour edits as drafts. The saved colours are loaded
    /// first, so a save never replaces them with defaults; storage that is not ready yet returns
    /// `Unavailable` for a later retry.
    pub fn save_applied(&mut self, files: &mut impl Files) -> Result<(), Error> {
        match self.load(files) {
            Ok(()) | Err(Error::Missing) | Err(Error::Invalid) => {}
            Err(reason) => return Err(reason),
        }
        save(files, self.applied)
    }
}
