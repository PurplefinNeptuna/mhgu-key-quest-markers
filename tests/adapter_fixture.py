"""Fixed inputs of tests/native_adapter.py: the compiled NRO and its symbols, the copied game image and
counter GUI resource, and the emulator's memory layout. Read once at import; every case shares them."""
import re
import struct
import subprocess
from pathlib import Path
from paths import BUILD_ROOT, CONFIG, SMALL_MARK, input_path
from verify import symbols
from mhgu_binary import Nro, main_image
from gui_layout import Gui
from mhgu_assets import read_arc
from unicorn import arm_const as arm

MODULE = 0x31000000
ENGINE = 0x32000000
RETURN = 0x32000100
STACK = 0x41010000
GAME = 0x33000000
DATA = 0x34000000
elf, names = symbols()
data = (BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers.nro').read_bytes()
nro = Nro(data)
native_image, _ = main_image(input_path('main').read_bytes())
_, arc = read_arc(input_path('common_eng.arc'))
gui = Gui(next(v['data'] for k, v in arc.items() if k[0].endswith('count\\counter')))
row_objects = gui.table(48, 172, 36)[30:42]
base_symbol = None
nm = [Path(CONFIG['devkitarm'])/'bin/arm-none-eabi-nm', '-C', '-n', elf]
for line in subprocess.check_output(nm, text=True).splitlines():
    fields = line.split(maxsplit=2)
    if len(fields) == 3 and fields[2] == 'key_quest_markers::memory::BASE':
        base_symbol = int(fields[0], 16)
assert base_symbol is not None
UI, HOLDER, CONTROLLER, INFO, PROFILE, QUEST, RESOURCE, RECORDS, PROGRESS, ROWS, DTI, VFT = (DATA+x for x in
    [0x1000, 0x2000, 0x3000, 0x4000, 0x10000, 0x20000, 0x21000, 0x22000, 0x23000, 0x24000, 0x25000, 0x26000])
ROOT_DTI, ALLOCATOR, ATLAS, GUI_RESOURCE = DATA+0x25100, DATA+0x25200, DATA+0x61000, DATA+0x62000
GUI_OWNER, GUI_HEADER, OBJECT_TABLE = DATA+0x65000, DATA+0x66000, DATA+0x67000
MESSAGE_DTI = DATA+0x25700
MAP_DTI, MAP_ALLOCATOR, ANIM_DTI, NULL_DTI = (DATA+x for x in [0x25300, 0x25400, 0x25500, 0x25600])
FOREIGN = DATA+0x82000
INSTANCE_ARRAY = DATA+0x27000
# The game's save lock (forge-modding references/save-lock.md): sSavedata's cell at main+0x2120320
# holds an object whose first word is its vtable main+0x17897f8; its save mutex is at +0xe80.
SAVEDATA = DATA+0x1e0000
SAVEDATA_CELL = GAME+0x2120320
SAVEDATA_VTABLE = GAME+0x17897f8
# Purple-lib's table functions are doubles at PURPLE_LIB + 4 * entry; add_options is the first.
PURPLE_LIB = ENGINE+0xf00
PURPLE_TABLE = DATA+0x1f0000
REGS = [getattr(arm, 'UC_ARM_REG_R'+str(i)) for i in range(13)]
BADGE_ID = 0x4b514d33
STYLE = [0xa4dc24, 0xa4a9f4, 0xa47a94, 0xa4dca0, 0xa47a04, 0xa4aa24, 0xa4aa5c, 0xa4aa94, 0xa4aac8, 0xa4aafc,
         0xa4dc54, 0xa4fa5c]
icon_props = gui.props(struct.unpack_from('<I', row_objects[2], 24)[0], row_objects[2][4])
STYLE_NAMES = ['BlendState', 'ControlPoint', 'FixFrame', 'Mask', 'Priority', 'ReferencePosition',
               'ReferenceRotation', 'ReferenceScaleX', 'ReferenceScaleY', 'ReferenceScaleZ', 'Reverse',
               'SamplerState']
SOURCE_STYLE = dict(zip(STYLE, (icon_props[k] for k in STYLE_NAMES)))
TITLE_CRC = struct.unpack_from('<I', row_objects[4], 20)[0]
# Derive the fixture's title class from the real resource.
assert TITLE_CRC == 0x2fb82eae
UNUSED_TEXT_DTI = DATA+0x25800
UV = (342., 0., 372., 30.) if SMALL_MARK == '1' else (136., 344., 198., 406.)
KEY_COLOR, URGENT_COLOR, COMPLETED_COLOR, UNLOCKS_COLOR, REWARD_COLOR = (
    0xff056300, 0xff0000a3, 0xff808080, 0xffc23200, 0xff007fff)


def hook_targets(source):
    """The game and plugin addresses the adapter's code hook acts on, read from its trace function."""
    body = source[source.index('    def trace(cpu,address,size,_):'):source.index('    def call(address,')]
    targets = {GAME+int(x, 16) for x in re.findall(r'GAME\+0x([0-9a-f]+)', body)}
    targets |= {GAME+x for x in STYLE}
    targets |= {MODULE+names[n] for n in re.findall(r"MODULE\+names\['(\w+)'\]", body)}
    targets |= {SAVEDATA_CELL}
    return sorted(targets)
