"""Exercise the bounded resource recipe and rejected corrupt/unsupported inputs."""
from pathlib import Path
import hashlib,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paths import input_path,BUILD_ROOT
from mhgu_assets import read_arc
from gui_badge import extend,verify,Gui
_,entries=read_arc(input_path('common_eng.arc'))
key=next(k for k in entries if k[0]=='eng\\GUI\\05_meeting_p\\count\\counter')
source=entries[key]['data'];patched=extend(source);verify(source,patched)
_,again=read_arc(BUILD_ROOT/'package/romfs/nativeNX/eng/arc/village/common_eng.arc')
assert again[key]['data']==patched
for k in entries:
    if k!=key:assert entries[k]['raw'][:76]==again[k]['raw'][:76] and entries[k]['packed']==again[k]['packed']
for invalid in [b'',source[:299],source[:-1],bytes([source[0]^1])+source[1:]]:
    try:extend(invalid)
    except ValueError:pass
    else:raise AssertionError('Unsupported source accepted')
bad=bytearray(patched);struct.pack_into('<I',bad,172,len(bad)-4)
try:Gui(bytes(bad))
except ValueError:pass
else:raise AssertionError('Out-of-bounds object table accepted')
bad=bytearray(patched);struct.pack_into('<I',bad,232,Gui(patched).word(232)+64)
try:verify(source,bytes(bad))
except ValueError:pass
else:raise AssertionError('Atlas binding modification accepted')
print('PASS: all 15 row states, existing bindings, 114 unrelated ARC resources and rejection fixtures')
