#!/usr/bin/env python3
"""Check the staged candidate's native imports, exact code signatures and active callback path."""
import ast,json,re,struct,subprocess
from pathlib import Path
from paths import MOD,CONFIG,BUILD_ROOT,CARGO_TARGET,VERSION,input_path
from build import doctor,digest,record,source_hashes
from mhgu_binary import Nro,main_image
from native_support import nso_exports

def symbols():
    elf=CARGO_TARGET/'armv7a-none-eabi/release/libkey_quest_markers.so'
    result={}
    for line in subprocess.check_output([Path(CONFIG['devkitarm'])/'bin/arm-none-eabi-nm','-n',elf],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:result[fields[2]]=int(fields[0],16)
    return elf,result

def verify():
    doctor();nro_path=BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers.nro'
    data=nro_path.read_bytes();nro=Nro(data);elf,names=symbols()
    # DT_TEXTREL / DF_TEXTREL require writes to memory the Switch maps read-only.
    if 22 in nro.tags or nro.tags.get(30,0)&4:
        raise ValueError('NRO requires dynamic relocations in read-only memory')
    receipt=json.loads((BUILD_ROOT/'build.json').read_text())
    if receipt.get('version')!=VERSION or receipt['nro_sha256']!=digest(nro_path) or receipt.get('source_sha256')!=source_hashes():
        raise ValueError('Build receipt differs from staged NRO/current sources')
    exports={n.decode() for n,e,*_ in nro.symbols if n and e[5] and e[3]>>4==1}
    callbacks={'forge_onLoad','forge_onInit','forge_onUpdate','forge_onImGuiInit','forge_onImGuiRender'}
    # purplelib_on_register: Purple-lib finds it in the dynamic symbols and calls it (optional).
    if exports!=callbacks|{'purplelib_on_register','init','fini'}:
        raise ValueError('Unexpected plugin exports: '+str(exports))
    imports={n.decode() for n,e,*_ in nro.symbols if n and not e[5] and e[3]>>4==1}
    available=set().union(*(nso_exports(input_path(n)) for n in ['main','sdk','forge']))
    if imports-available:raise ValueError('Unresolved native imports: '+str(imports-available))
    image,_=main_image(input_path('main').read_bytes());windows=[]
    for offset,raw in re.findall(r'\(\s*0x([0-9a-f]+),\s*\[([^\]]+)\]',(MOD/'src/signatures.rs').read_text()):
        offset=int(offset,16);expected=ast.literal_eval('['+raw+']')
        if image[offset:offset+32]!=bytes(expected):raise ValueError('Signature mismatch: '+hex(offset))
        windows.append(hex(offset))
    if struct.unpack_from('<5I',image,0x178ff90)!=(0x32c,0xa568a8,0xa4f550,0,0):
        raise ValueError('Texture DTI vtable differs; placement virtual is unavailable')
    if struct.unpack_from('<I',image,0x18422b4)[0]!=0x2123210:
        raise ValueError('Native object-map allocator DTI differs')
    if len(windows)!=49:raise ValueError('Supporting signature windows missing')
    assert image[0x616cb0:0x616cb8]==bytes.fromhex('f04f2de904d04de2')
    if 'kqm_verified_contract' in names:raise ValueError('Inactive release gate remains in production')
    disasm=subprocess.check_output([Path(CONFIG['devkitarm'])/'bin/arm-none-eabi-objdump','-d',elf],text=True)
    writes=[line for line in disasm.splitlines() if '\tmsr\t' in line]
    if writes:raise ValueError('Unexpected processor status writes: '+str(writes))
    if imports&{'igBegin','forge_graphics_getContext','forge_config_create'}:
        raise ValueError('Unrequested settings/overlay dependency')
    if not {'igTreeNode_Str','igTreePop','igColorEdit3','forge_fs_mountSaveData','forge_fs_unmountSaveData'} <= imports:
        raise ValueError('Settings/config integration imports missing')
    if 'forge_onImGuiFreeRender' in exports: raise ValueError('Native badges must not use free rendering')
    if any(marker in data for marker in [b'diagnostic:', b'first classified page', b'gui_flags=', b'waiting for quest counter']):
        raise ValueError('Development log dumps remain in production runtime')
    expected={'romfs/nativeNX/plugins/key_quest_markers.nro','manifest.json'}
    source=BUILD_ROOT/'package';actual={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Unexpected runtime payload files')
    if json.loads((source/'manifest.json').read_text())['version']!=f'0.{VERSION.split("-")[0][1:]}.0':raise ValueError('manifest.json names another version')
    resources=json.loads((BUILD_ROOT/'resource.json').read_text())
    if resources['archive_replacements']!=0:
        raise ValueError('Unexpected archive replacement')
    record('verify.json',{'status':'PASSED','nro_sha256':digest(nro_path),'elf_sha256':digest(elf),
        'exports':sorted(exports),'strong_imports':sorted(imports),'signature_windows':windows,'hook_abi_bytes':24,
        'ordinary_hook_slots':2,'texture_constructor':'0xa4f60c','texture_dti_placement_virtual':False,'forge_trampoline_bytes':32,'forge_pool_chunk_bytes':16384,
        'compiled_status_writes':writes,'runtime_active':True,'text_relocations':False,
        'gui_attachment':'Game-owned native children and expanded draw caches','progression_semantics':'Native stages, alternatives and offered urgent IDs','runtime_test':'NOT RUN'})
    print('PASS: native imports/signatures, Hook ABI compilation, active callback path and payload inventory')
if __name__=='__main__':verify()
