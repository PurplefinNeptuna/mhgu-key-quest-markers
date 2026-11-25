"""Settings doubles for tests/native_adapter.py: Forge's save-data mount, the narrow nn::fs calls the
plugin's INI code makes, the game's save lock, and the ImGui widgets of its Plugin UI panel. One
`Settings` per case holds their state; the adapter's code hook offers each imported call to `handle`
first.

The save lock (forge-modding references/save-lock.md): every mount, write-mode open and commit must
hold sSavedata's mutex, unlocked only after the unmount. `game_saving` makes TryLock fail.

AAPCS i64 offsets occupy r2/r3; buffer and count use the stack.
"""
import struct
from unicorn import arm_const as arm
from adapter_fixture import DATA, ENGINE, MODULE, PURPLE_LIB, PURPLE_TABLE, names

PANEL = 'Key Quest Markers###key-quest-markers'
COLOURS = ['Key##kqm-key', 'Urgent##kqm-urgent', 'Completed##kqm-completed', 'Unlocks a quest##kqm-unlocks',
           'Gives a reward##kqm-reward']
FAILURES = ['mount', 'create', 'open', 'resize', 'write', 'flush', 'size', 'read', 'verify', 'commit']
CUSTOM = (0x123456, 0xA86432, 0x607080, 0x13579B, 0x2468AC)
COLOURS_SAVED = b'[Colors]\nkey = 123456\nurgent = A86432\ncompleted = 607080\nunlocks = 13579B\nreward = 2468AC\n'
# Grey badges values, as the Mod Options row and the panel's radio buttons order them.
COLOURED, GREY, HIDDEN_VALUE = 0, 1, 2
INI = [COLOURS_SAVED+b'[Badges]\nfinished_quests = '+name+b'\n' for name in (b'colored', b'gray', b'hidden')]
SAVED = INI[GREY]
HIDDEN = INI[HIDDEN_VALUE]
RADIOS = ['Colored##kqm-gray-colored', 'Gray##kqm-gray-gray', 'Hidden##kqm-gray-hidden']
LABELS = ['Colored', 'Gray', 'Hidden']
TRY_LOCK = '_ZN2nn2os12TryLockMutexEPNS0_9MutexTypeE'
UNLOCK = '_ZN2nn2os11UnlockMutexEPNS0_9MutexTypeE'
# ImGuiColorEditFlags DisplayHex | Uint8.
COLOUR_FLAGS = 4194304 | 8388608
OPEN = '_ZN2nn2fs8OpenFileEPNS0_10FileHandleEPKci'
READ = '_ZN2nn2fs8ReadFileENS0_10FileHandleExPvj'
WRITE = '_ZN2nn2fs9WriteFileENS0_10FileHandleExPKvjRKNS0_11WriteOptionE'


class Settings:
    def __init__(self, ret, text, word, read, mutex):
        self.ret = ret
        self.mutex = mutex
        self.save_locked = False
        self.game_saving = False
        self.lock_takes = 0
        # The radio button the panel clicks next (a Grey badges value), or None.
        self.grey_choice = None
        # Mod Options pages that Purple-lib's add_options double received.
        self.purple_pages = []
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

    def try_lock(self, cpu, r, imported):
        assert r[0] == self.mutex and not self.save_locked and self.mounted == 0
        self.save_locked = not self.game_saving
        self.lock_takes += int(self.save_locked)
        return int(self.save_locked)

    def unlock(self, cpu, r, imported):
        # After the unmount, so Forge's commit at unmount is covered.
        assert r[0] == self.mutex and self.save_locked and self.mounted == 0
        self.save_locked = False

    def mount(self, cpu, r, imported):
        assert self.save_locked, 'mount without the save lock'
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
        assert self.save_locked or not r[2] & 2, 'write open without the save lock'
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
        assert not self.handles and self.save_locked
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

    def radio(self, cpu, r, imported):
        value = RADIOS.index(self.text(cpu, r[0]))
        return int(self.grey_choice == value)

    def button(self, cpu, r, imported):
        label = self.text(cpu, r[0])
        return int(self.save_clicked if label.startswith('Save & apply') else self.reset_clicked)

    def panel_cases(self, init, render, palette, update):
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
        # Grey badges: a choice is pending until Save & apply, like a colour.
        self.grey_choice = HIDDEN_VALUE
        self.save_clicked = False
        render()
        assert self.disk == SAVED
        self.grey_choice = None
        self.save_clicked = True
        render()
        assert self.disk == HIDDEN
        self.grey_choice = COLOURED
        render()
        assert self.disk == INI[COLOURED]
        self.grey_choice = GREY
        render()
        assert self.disk == SAVED
        # The game is saving: Save & apply writes nothing, then saves on the next second.
        self.grey_choice = HIDDEN_VALUE
        self.game_saving = True
        render()
        assert self.disk == SAVED and not self.save_locked
        self.grey_choice = None
        self.save_clicked = False
        self.game_saving = False
        update()
        assert self.disk == HIDDEN and not self.save_locked
        self.grey_choice = GREY
        self.save_clicked = True
        render()
        assert self.disk == SAVED
        self.grey_choice = None
        self.save_clicked = False
        self.reset_clicked = True
        render()
        assert struct.unpack('<5I', palette()) == CUSTOM
        self.reset_clicked = False
        self.panel_open = False
        render()

    def mod_options_cases(self, call, result, text, read, memory, register, update):
        """Mod Options through the compiled export and callbacks, with an API version 3 table.
        `memory` is (read_bytes, write_bytes, scratch address)."""
        read_bytes, write_bytes, out = memory
        register()
        assert len(self.purple_pages) == 1, self.purple_pages
        page = struct.unpack('<10I', read_bytes(self.purple_pages[0], 40))
        size, _, title, row_count, row, get, set_value, closed, value_text, action = page
        assert size == 40 and row_count == 1 and value_text == action == 0
        call(title)
        assert text(result()) == 'Key Quest Markers'
        write_bytes(out, bytes(40))
        call(row, 0, 0, 0, out)
        assert result() & 255 == 1
        name, _, labels, label_count = struct.unpack('<4I', read_bytes(out, 16))
        assert text(name) == 'Finished quests' and label_count == 3
        assert [text(read(labels+4*i)) for i in range(3)] == LABELS
        call(row, 0, 0, 1, out)
        assert result() & 255 == 0
        register()
        assert len(self.purple_pages) == 1
        for value in (HIDDEN_VALUE, COLOURED, GREY):
            call(set_value, 0, 0, value)
            call(get)
            assert result() == value
            # Applied at once; the save waits for the window to close.
            before_close = self.disk
            update()
            assert self.disk == before_close
            call(closed)
            update()
            assert self.disk == INI[value], self.disk
        call(set_value, 0, 0, 3)
        call(get)
        assert result() == GREY
        # The game is saving: the Mod Options save waits for the lock and saves on the next second.
        self.game_saving = True
        call(set_value, 0, 0, HIDDEN_VALUE)
        call(closed)
        update()
        assert self.disk == SAVED and not self.save_locked
        self.game_saving = False
        update()
        assert self.disk == HIDDEN and not self.save_locked
        call(set_value, 0, 0, GREY)
        call(closed)
        update()
        assert self.disk == SAVED and self.lock_takes > 0

    def run_cases(self, call, u, text, read, word):
        """The settings cases of a custom-palette run: the panel, then Mod Options."""
        def init():
            call(MODULE+names['forge_onImGuiInit'], DATA+0x180000, ENGINE+0x100, ENGINE+0x104)

        def render():
            call(MODULE+names['forge_onImGuiRender'])

        def palette():
            return bytes(u.mem_read(MODULE+names['kqm_palette'], 20))

        def update():
            # One second (1.0f in r0 and s0, either float ABI), so the once-a-second retry runs.
            u.reg_write(arm.UC_ARM_REG_S0, 0x3f800000)
            call(MODULE+names['forge_onUpdate'], 0x3f800000)

        def register():
            call(MODULE+names['purplelib_on_register'], PURPLE_TABLE)

        def result():
            return u.reg_read(arm.UC_ARM_REG_R0)

        def read_bytes(p, n):
            return bytes(u.mem_read(p, n))

        self.panel_cases(init, render, palette, update)
        word(PURPLE_TABLE, 3)
        for entry in range(6):
            word(PURPLE_TABLE+4+entry*4, PURPLE_LIB+entry*4)
        memory = (read_bytes, u.mem_write, PURPLE_TABLE+0x100)
        self.mod_options_cases(call, result, text, read, memory, register, update)


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
    'igRadioButton_Bool': Settings.radio,
    'igSameLine': Settings.nothing,
    TRY_LOCK: Settings.try_lock,
    UNLOCK: Settings.unlock,
    'igTextUnformatted': Settings.nothing,
}
