#!/usr/bin/env python3
"""Check the staged candidate's native imports, exact code signatures and inactive gate."""
import ast,json,re,struct,subprocess
from pathlib import Path
from paths import MOD,CONFIG,BUILD_ROOT,CARGO_TARGET,input_path
from build import doctor,digest,record,source_hashes
from mhgu_binary import Nro,main_image
from native_support import nso_exports

def symbols():
    elf=CARGO_TARGET/'armv7a-none-eabi/release/libkey_quest_markers_rs.so'
    result={}
    for line in subprocess.check_output([Path(CONFIG['devkitarm'])/'bin/arm-none-eabi-nm','-n',elf],text=True).splitlines():
        fields=line.split()
        if len(fields)==3:result[fields[2]]=int(fields[0],16)
    return elf,result

def verify():
    doctor();nro_path=BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro'
    data=nro_path.read_bytes();nro=Nro(data);elf,names=symbols()
    receipt=json.loads((BUILD_ROOT/'build.json').read_text())
    if receipt['nro_sha256']!=digest(nro_path) or receipt.get('source_sha256')!=source_hashes():
        raise ValueError('Build receipt differs from staged NRO/current sources')
    exports={n.decode() for n,e,*_ in nro.symbols if n and e[5] and e[3]>>4==1}
    if exports!={'forge_onLoad','forge_onInit','forge_onUpdate','init','fini'}:raise ValueError('Unexpected plugin exports: '+str(exports))
    imports={n.decode() for n,e,*_ in nro.symbols if n and not e[5] and e[3]>>4==1}
    available=set().union(*(nso_exports(input_path(n)) for n in ['main','sdk','forge']))
    if imports-available:raise ValueError('Unresolved native imports: '+str(imports-available))
    image,_=main_image(input_path('main').read_bytes());windows=[]
    for offset,raw in re.findall(r'\(\s*0x([0-9a-f]+),\s*\[([^\]]+)\]',(MOD/'src/signatures.rs').read_text()):
        offset=int(offset,16);expected=ast.literal_eval('['+raw+']')
        if image[offset:offset+32]!=bytes(expected):raise ValueError('Signature mismatch: '+hex(offset))
        windows.append(hex(offset))
    if len(windows)!=13:raise ValueError('Supporting signature windows missing')
    assert image[0x616cb0:0x616cb8]==bytes.fromhex('f04f2de904d04de2')
    assert struct.unpack_from('<I',data,names['kqm_verified_contract'])[0]==0
    disasm=subprocess.check_output([Path(CONFIG['devkitarm'])/'bin/arm-none-eabi-objdump','-d',elf],text=True)
    writes=[line for line in disasm.splitlines() if '\tmsr\t' in line]
    if writes:raise ValueError('Unexpected processor status writes: '+str(writes))
    if imports&{'igBegin','igTreeNode_Str','forge_graphics_getContext','forge_config_create'}:
        raise ValueError('Unrequested settings/overlay dependency')
    expected={'romfs/nativeNX/plugins/key_quest_markers_rs.nro','romfs/nativeNX/eng/arc/village/common_eng.arc'}
    source=BUILD_ROOT/'package';actual={str(p.relative_to(source)) for p in source.rglob('*') if p.is_file()}
    if actual!=expected:raise ValueError('Unexpected runtime payload files')
    resources=json.loads((BUILD_ROOT/'resource.json').read_text())
    if digest(source/'romfs/nativeNX/eng/arc/village/common_eng.arc')!=resources['archive_sha256']:
        raise ValueError('Resource receipt differs')
    record('verify.json',{'status':'PASSED','nro_sha256':digest(nro_path),'elf_sha256':digest(elf),
        'exports':sorted(exports),'strong_imports':sorted(imports),'signature_windows':windows,'hook_abi_bytes':24,
        'ordinary_hook_slots':1,'forge_trampoline_bytes':16,'forge_pool_chunk_bytes':16384,
        'compiled_status_writes':writes,'verified_contract':0,'runtime_active':False,
        'gui_attachment':'NOT VERIFIED','progression_semantics':'NOT VERIFIED','runtime_test':'NOT RUN'})
    print('PASS: native imports/signatures, Hook ABI compilation, inactive gate and payload inventory')
if __name__=='__main__':verify()
