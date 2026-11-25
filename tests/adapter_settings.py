"""Settings doubles for tests/native_adapter.py: Forge's save-data mount, the narrow nn::fs calls the
plugin's INI code makes, and the ImGui widgets of its Plugin UI panel. One `Settings` per case holds
their state; the adapter's code hook offers each imported call to `handle` first.

AAPCS i64 offsets occupy r2/r3; buffer and count use the stack.
"""
import struct
from unicorn import arm_const as arm

PANEL = 'Key Quest Markers###key-quest-markers'
COLOURS = ['Key##kqm-key', 'Urgent##kqm-urgent', 'Completed##kqm-completed', 'Unlocks a quest##kqm-unlocks',
           'Gives a reward##kqm-reward']
FAILURES = ['mount', 'create', 'open', 'resize', 'write', 'flush', 'size', 'read', 'verify', 'commit']
CUSTOM = (0x123456, 0xA86432, 0x607080, 0x13579B, 0x2468AC)
SAVED = b'[Colors]\nkey = 123456\nurgent = A86432\ncompleted = 607080\nunlocks = 13579B\nreward = 2468AC\n'
# ImGuiColorEditFlags DisplayHex | Uint8.
COLOUR_FLAGS = 4194304 | 8388608
OPEN = '_ZN2nn2fs8OpenFileEPNS0_10FileHandleEPKci'
READ = '_ZN2nn2fs8ReadFileENS0_10FileHandleExPvj'
WRITE = '_ZN2nn2fs9WriteFileENS0_10FileHandleExPKvjRKNS0_11WriteOptionE'


class Settings:
    def __init__(self, ret, text, word, read):
        self.ret = ret
        self.text = text
        self.word = word
        self.read = read
        self.disk = None
        self.handles = {}
        self.next_handle = 1
        self.mounted = 0
        self.contexts = 0
        self.fs_ready = False
        self.fs_fail = ''
        self.commits = 0
        self.picker_values = None
        self.save_clicked = False
        self.reset_clicked = False
        self.panel_open = True
        self.tree_balance = 0

    def balanced(self):
        """No open file, mount, SDK abort context or ImGui tree is left over."""
        return not self.handles and self.mounted == self.contexts == self.tree_balance == 0

    def handle(self, cpu, imported, r):
        """Run the double for an imported settings call and return True, or return False."""
        double = DOUBLES.get(imported)
        if double is None:
            return False
        result = double(self, cpu, r, imported)
        self.ret(cpu, result or 0)
        return True

    def mount(self, cpu, r, imported):
        ready = self.fs_ready and self.fs_fail != 'mount'
        if ready:
            self.mounted += 1
        return int(ready)

    def unmount(self, cpu, r, imported):
        assert self.mounted > 0
        self.mounted -= 1

    def disable_abort(self, cpu, r, imported):
        self.word(r[0], 0x123)
        self.contexts += 1

    def restore_context(self, cpu, r, imported):
        assert r[0] == 0x123
        self.contexts -= 1

    def open(self, cpu, r, imported):
        assert self.text(cpu, r[1]) == 'savedata:/key_quest_markers.ini' and self.mounted > 0
        if self.disk is None or self.fs_fail == 'open':
            return 0x202
        handle = self.next_handle
        self.next_handle += 1
        self.handles[handle] = r[2]
        self.word(r[0], handle)

    def close(self, cpu, r, imported):
        assert r[0] in self.handles
        del self.handles[r[0]]

    def size(self, cpu, r, imported):
        assert r[1] in self.handles
        if self.fs_fail == 'size':
            return 1
        cpu.mem_write(r[0], struct.pack('<q', len(self.disk)))

    def create(self, cpu, r, imported):
        if self.disk is not None or self.fs_fail == 'create':
            return 1
        self.disk = b''

    def resize(self, cpu, r, imported):
        assert r[0] in self.handles and r[3] == 0
        if self.fs_fail == 'resize':
            return 1
        self.disk = (self.disk+bytes(r[2]))[:r[2]]

    def transfer(self, cpu, r, imported):
        assert r[0] in self.handles and r[2:] == [0, 0]
        sp = cpu.reg_read(arm.UC_ARM_REG_SP)
        buffer, length = struct.unpack('<2I', cpu.mem_read(sp, 8))
        if imported == READ:
            if self.fs_fail == 'read':
                return 1
            content = self.disk[:length]
            if self.fs_fail == 'verify':
                content = b'!'+content[1:]
            cpu.mem_write(buffer, content)
            return 0
        assert self.read(self.read(sp+8)) == 1
        if self.fs_fail == 'write':
            return 1
        self.disk = bytes(cpu.mem_read(buffer, length))

    def flush(self, cpu, r, imported):
        return int(self.fs_fail == 'flush')

    def commit(self, cpu, r, imported):
        assert not self.handles
        self.commits += 1
        return int(self.fs_fail == 'commit')

    def nothing(self, cpu, r, imported):
        return 0

    def tree_node(self, cpu, r, imported):
        assert self.text(cpu, r[0]) == PANEL
        self.tree_balance += int(self.panel_open)
        return int(self.panel_open)

    def tree_pop(self, cpu, r, imported):
        assert self.tree_balance == 1
        self.tree_balance -= 1

    def colour(self, cpu, r, imported):
        index = COLOURS.index(self.text(cpu, r[0]))
        assert r[2] & COLOUR_FLAGS == COLOUR_FLAGS
        if self.picker_values is not None:
            rgb = self.picker_values[index]
            components = ((rgb >> shift & 255)/255 for shift in (16, 8, 0))
            cpu.mem_write(r[1], struct.pack('<3f', *components))
        return int(self.picker_values is not None)

    def button(self, cpu, r, imported):
        label = self.text(cpu, r[0])
        return int(self.save_clicked if label.startswith('Save & apply') else self.reset_clicked)

    def panel_cases(self, init, render, palette):
        """Pending edits, every storage failure, a saved INI, and a reset that stays pending."""
        self.fs_ready = True
        init()
        render()
        before = palette()
        self.picker_values = CUSTOM
        render()
        assert palette() == before and self.disk is None
        self.picker_values = None
        self.save_clicked = True
        for failure in FAILURES:
            self.fs_fail = failure
            self.disk = None
            render()
            assert palette() == before, failure
            assert self.balanced(), failure
        previous_commits = self.commits
        self.fs_fail = ''
        render()
        assert struct.unpack('<5I', palette()) == CUSTOM
        assert self.disk == SAVED
        assert self.balanced() and self.commits == previous_commits+1
        self.save_clicked = False
        self.reset_clicked = True
        render()
        assert struct.unpack('<5I', palette()) == CUSTOM
        self.reset_clicked = False
        self.panel_open = False
        render()


DOUBLES = {
    'forge_fs_mountSaveData': Settings.mount,
    'forge_fs_unmountSaveData': Settings.unmount,
    '_ZN2nn2fs23ScopedAutoAbortDisablerC1Ev': Settings.disable_abort,
    '_ZN2nn2fs25SetCurrentThreadFsContextEPKNS0_9FsContextE': Settings.restore_context,
    OPEN: Settings.open,
    '_ZN2nn2fs9CloseFileENS0_10FileHandleE': Settings.close,
    '_ZN2nn2fs11GetFileSizeEPxNS0_10FileHandleE': Settings.size,
    '_ZN2nn2fs10CreateFileEPKcx': Settings.create,
    '_ZN2nn2fs11SetFileSizeENS0_10FileHandleEx': Settings.resize,
    READ: Settings.transfer,
    WRITE: Settings.transfer,
    '_ZN2nn2fs9FlushFileENS0_10FileHandleE': Settings.flush,
    '_ZN2nn2fs14CommitSaveDataEPKc': Settings.commit,
    'igSetCurrentContext': Settings.nothing,
    'igSetAllocatorFunctions': Settings.nothing,
    'igTreeNode_Str': Settings.tree_node,
    'igTreePop': Settings.tree_pop,
    'igColorEdit3': Settings.colour,
    'igButton': Settings.button,
    'igTextUnformatted': Settings.nothing,
}
