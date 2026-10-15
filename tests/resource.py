"""Read-only resource fixtures; runtime delivery must contain no ARC replacement."""
from pathlib import Path
import sys,struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paths import input_path,BUILD_ROOT
from gui_layout import inspect,Gui
from mhgu_assets import read_arc
info=inspect(input_path('common_eng.arc'))
_,entries=read_arc(input_path('common_eng.arc'))
source=next(v['data'] for k,v in entries.items() if k[0].endswith('count\\counter'))
for invalid in [b'',source[:299],source[:-1],bytes([source[0]^1])+source[1:]]:
    try:Gui(invalid)
    except ValueError:pass
    else:raise AssertionError('Corrupt resource accepted')
bad=bytearray(source);struct.pack_into('<I',bad,172,len(bad)-4)
try:Gui(bytes(bad))
except ValueError:pass
else:raise AssertionError('Out-of-bounds object table accepted')
assert info['existing_sequences']==15 and info['existing_objects']==12
# These constants live directly in INIT_PARAM.value, unlike Visible's byte-table
# reference. Reading them as byte offsets made almost every field appear as 1.
gui=Gui(source);icon=gui.table(48,172,36)[32]
props=gui.props(struct.unpack_from('<I',icon,24)[0],icon[4])
assert {k:props[k]for k in ['ControlPoint','FixFrame','Mask','ReferenceScaleX','ReferenceScaleY',
                          'ReferenceScaleZ','Reverse','SamplerState']}=={
    'ControlPoint':0,'FixFrame':0,'Mask':0,'ReferenceScaleX':3,'ReferenceScaleY':3,
    'ReferenceScaleZ':3,'Reverse':0,'SamplerState':0}
assert props['Visible']==1 and props['BlendState']==1 and props['Priority']==2
objects=gui.table(48,172,36)[30:42]
request=gui.props(struct.unpack_from('<I',objects[3],24)[0],objects[3][4])
title=gui.props(struct.unpack_from('<I',objects[4],24)[0],objects[4][4])
assert struct.unpack_from('<I',objects[4],20)[0]==0x2fb82eae # The source declares Message, not Text.
assert info['title_class']=='cGUIObjMessage' and info['title_bytes']==352
assert struct.unpack_from('<I',objects[3])[0]==20 and struct.unpack_from('<I',objects[4])[0]==6
assert (request['PosX'],request['PosY'],request['Size'][:2])==(365.,2.,(32.,32.))
assert (title['PosX'],title['Size'][:2],title['AutoScale'],title['AutoWrap'])==(62.,(355.,38.),0,0)
assert 365+32/2==request['PosX']+request['Size'][0]/2
assert 329+32+4==request['PosX']
assert 62+299+4==365 and 62+263+4==329
background=gui.props(struct.unpack_from('<I',objects[6],24)[0],objects[6][4])
assert 0 <= 3 and 3+32 <= background['Size'][1] # Native row envelope.
assert not list((BUILD_ROOT/'package').rglob('*.arc'))
print('PASS: native row/atlas fixture, resource bounds, all 15 original sequences and zero ARC payloads')
