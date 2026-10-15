#!/usr/bin/env python3
"""Execute the shipped ARM callbacks, native draw walker and native ownership cleanup.

Forge/kernel/MT factories and GPU commands are doubles; game archive bytes are
unchanged. Native prepaint dispatch, texture draw and quad generation execute;
world transforms, bounding-box calculation and actual pixels are not simulated.
"""
import json,struct,subprocess,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paths import MOD,BUILD_ROOT,CONFIG,SMALL_MARK,input_path
from verify import symbols
from mhgu_binary import Nro,main_image
from build import record,digest
from gui_layout import Gui
from mhgu_assets import read_arc
import unicorn
from unicorn import arm_const as arm
MODULE,ENGINE,RETURN,STACK,GAME,DATA=0x31000000,0x32000000,0x32000100,0x41010000,0x33000000,0x34000000
elf,names=symbols();data=(BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro').read_bytes();nro=Nro(data)
native_image,_=main_image(input_path('main').read_bytes())
_,arc=read_arc(input_path('common_eng.arc'))
gui=Gui(next(v['data'] for k,v in arc.items() if k[0].endswith('count\\counter')))
row_objects=gui.table(48,172,36)[30:42]
base_symbol=None
for line in subprocess.check_output([Path(CONFIG['devkitarm'])/'bin/arm-none-eabi-nm','-C','-n',elf],text=True).splitlines():
    fields=line.split(maxsplit=2)
    if len(fields)==3 and fields[2]=='key_quest_markers_rs::memory::BASE':base_symbol=int(fields[0],16)
assert base_symbol is not None
UI,HOLDER,CONTROLLER,INFO,PROFILE,QUEST,RESOURCE,RECORDS,PROGRESS,ROWS,DTI,VFT=(DATA+x for x in
    [0x1000,0x2000,0x3000,0x4000,0x10000,0x20000,0x21000,0x22000,0x23000,0x24000,0x25000,0x26000])
ROOT_DTI,ALLOCATOR,ATLAS,GUI_RESOURCE=DATA+0x25100,DATA+0x25200,DATA+0x61000,DATA+0x62000
GUI_OWNER,GUI_HEADER,OBJECT_TABLE=DATA+0x65000,DATA+0x66000,DATA+0x67000
MESSAGE_DTI=DATA+0x25700
MAP_DTI,MAP_ALLOCATOR,ANIM_DTI,NULL_DTI=(DATA+x for x in [0x25300,0x25400,0x25500,0x25600])
INSTANCE_ARRAY=DATA+0x27000
REGS=[getattr(arm,'UC_ARM_REG_R'+str(i))for i in range(13)]
BADGE_ID=0x4b514d33
STYLE=[0xa4dc24,0xa4a9f4,0xa47a94,0xa4dca0,0xa47a04,0xa4aa24,0xa4aa5c,0xa4aa94,0xa4aac8,0xa4aafc,0xa4dc54,0xa4fa5c]
icon_props=gui.props(struct.unpack_from('<I',row_objects[2],24)[0],row_objects[2][4])
SOURCE_STYLE=dict(zip(STYLE,(icon_props[k]for k in ['BlendState','ControlPoint','FixFrame','Mask','Priority',
    'ReferencePosition','ReferenceRotation','ReferenceScaleX','ReferenceScaleY','ReferenceScaleZ','Reverse','SamplerState'])))
TITLE_CRC=struct.unpack_from('<I',row_objects[4],20)[0]
assert TITLE_CRC==0x2fb82eae # Derive the fixture's title class from the real resource.
UNUSED_TEXT_DTI=DATA+0x25800
UV=(342.,0.,372.,30.) if SMALL_MARK=='1' else (136.,344.,198.,406.)
CASES=0

def test_case(label, *, offered=(303,),completed=(213,),available=True,prerequisites=True,invalid_object=False,
              invalid_info=False,invalid_owner=False,ordinary=False,bad_count=False,gui_identity=5,alternative_done=False,
              simultaneous=False,primary_count=63,fail_object=False,fail_cache=False,repeat=False,fail_at=0,fail_hook=0,fail_mapping=False,
              requests=(),invalid_request=False,invalid_title=False,recycle=False,late_invalid=False,selected=0,special=False,special_enabled=tuple(range(8))):
    global CASES
    u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);u.ctl_set_cpu_model(arm.UC_CPU_ARM_MAX)
    u.mem_map(MODULE,((len(data)+4095)//4096+64)*4096);u.mem_write(MODULE,data)
    u.mem_map(ENGINE,4096);u.mem_map(0x41000000,0x20000);u.mem_map(GAME,0x2000000)
    # Real game code rebuilds/traverses the draw cache and destroys the owned tree.
    for first,last in [(0xa494a0,0xa4964c),(0xa48668,0xa486fc),(0xa475e0,0xa47648),
                       (0xa38828,0xa38944),(0xa38bc0,0xa38e50),(0xa49b28,0xa49bac),(0xa4844c,0xa48470),(0x540c08,0x540c64),
                       (0xa4d0d8,0xa4d32c),(0xa4f60c,0xa4f840),
                       (0x54af8c,0x54b0d4),(0x3b9870,0x3b98a4),(0xa42374,0xa423cc),(0xa449c0,0xa44e0c),(0xa38b58,0xa38bc0),(0xa38ffc,0xa39020),(0x5456e4,0x545930)]:
        u.mem_write(GAME+first,native_image[first:last])
    # Exercise the actual texture setters too, including their dirty propagation.
    u.mem_write(GAME+0xa47000,native_image[0xa47000:0xa57000])
    # Copy every checked window, including non-hook constructor signatures first.
    for raw in re.findall(r'\(\s*0x([0-9a-f]+)',(MOD/'src/signatures.rs').read_text()):
        offset=int(raw,16);u.mem_write(GAME+offset,native_image[offset:offset+32])
    imports={};next_import=ENGINE+0x300
    for name,e,*_ in nro.symbols:
        if name and not e[5]:imports[name.decode()]=next_import;next_import+=4
    ranges=[]
    if 17 in nro.tags:ranges.append((nro.tags[17],nro.tags[18]))
    if 23 in nro.tags:ranges.append((nro.tags[23],nro.tags[2]))
    for start,length in ranges:
        for at in range(start,start+length,8):
            dest,info=struct.unpack_from('<II',data,at);kind=info&255;sym=info>>8
            value=struct.unpack('<I',u.mem_read(MODULE+dest,4))[0]
            if kind==23:value+=MODULE
            elif kind in [2,21,22]:
                name,e,*_=nro.symbols[sym];address=MODULE+e[1] if e[5] else imports.get(name.decode(),0)
                value=(value if kind==2 else 0)+address
            else:raise AssertionError(('relocation',kind))
            u.mem_write(MODULE+dest,struct.pack('<I',value&0xffffffff))
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    def read(p):return struct.unpack('<I',u.mem_read(p,4))[0]
    def half(p,v):u.mem_write(p,struct.pack('<H',v))
    word(CONTROLLER+0x54,UI);word(UI+0x24,HOLDER);word(HOLDER,VFT+0x100);word(VFT+0x1ac,GAME+0x1010)
    word(HOLDER+0x298,primary_count);word(HOLDER+0xf8,INSTANCE_ARRAY);word(HOLDER+0x294,INSTANCE_ARRAY+0x400)
    # The real DTI exposes three virtual slots. +0x0c is deliberately null:
    # earlier fixtures invented a placement-constructor slot that MHGU lacks.
    for offset in range(0,20,4):
        target=struct.unpack_from('<I',native_image,0x178ff90+offset)[0]
        word(VFT+0x200+offset,GAME+target if target else 0)
    assert read(VFT+0x20c)==0
    word(ROOT_DTI+4,1);word(DTI+4,2);word(MESSAGE_DTI+4,4);word(MESSAGE_DTI+24,352//4);word(MESSAGE_DTI+28,TITLE_CRC)
    word(MESSAGE_DTI,VFT+0xa00);word(VFT+0xa08,GAME+0x1064)
    # Keep both real class identities available. Selecting the Text subclass for
    # this Message resource must fail; it must never make the fixture pass.
    word(UNUSED_TEXT_DTI+24,384//4);word(UNUSED_TEXT_DTI+28,0x313f6cc4)
    word(GAME+0x183f0b0,MESSAGE_DTI) # Real Message getDTI's GOT input.
    word(VFT+0x914,GAME+0xa56ab8);word(VFT+0x904,GAME+0x1040);word(VFT+0x950,GAME+0x1060);word(VFT+0x970,GAME+0xa554d0)
    for offset,target in [(0x38,0x1050),(0x3c,0x1054),(0x40,0x1058)]:word(VFT+0x900+offset,GAME+target)
    # Relocate the real Object/Polygon/Texture vtables and constructor globals.
    # Matrix/color/sGUI contents are fixture inputs; constructor instructions run.
    for table in [0x178f948,0x178fc40,0x178fcc0]:
        for offset in range(0,128,4):
            target=struct.unpack_from('<I',native_image,table+offset)[0]
            word(GAME+table+offset,GAME+target if target else 0)
    for got,target in [(0x1843638,GAME+0x178f948),(0x1843748,GAME+0x178fc40),
                       (0x18437bc,GAME+0x178fcc0),(0x1843664,ROOT_DTI),
                       (0x1839bd0,DATA+0xf0000),(0x1839514,DATA+0xf0100),
                       (0x1838eb8,DATA+0xf0200)]:word(GAME+got,target)
    u.mem_write(DATA+0xf0000,struct.pack('<16f',*[float(i%5==0)for i in range(16)]))
    word(DATA+0xf0100,0xffffffff);word(DATA+0xf0200,DATA+0xf0300)
    # Cleanup recognizes animation instances and visits map entries up to the
    # live tree count. Match its class/constant GOT inputs without replacing code.
    word(ANIM_DTI+28,0x1daa79db);word(NULL_DTI+4,3);word(NULL_DTI+28,3)
    for got,target in [(0x183ef78,ANIM_DTI),(0x183ef50,ANIM_DTI),
                       (0x183f088,DATA+0xf0400),(0x183ef80,ROOT_DTI),
                       (0x183f08c,ROOT_DTI),(0x183ef9c,DTI),(0x183f090,ROOT_DTI),
                       (0x18422b4,MAP_DTI)]:word(GAME+got,target)
    word(DATA+0xf0400,1)
    word(MAP_ALLOCATOR,VFT+0x700);word(VFT+0x71c,GAME+0x1070);word(VFT+0x734,GAME+0x1074)
    word(VFT+0x814,GAME+0x1080);word(VFT+0x404+4,GAME+0xa48668)
    word(VFT+0x50,GAME+0xa4fc68)
    word(VFT+0x208,GAME+0x1064);word(VFT+0x31c,GAME+0x1038)
    word(VFT+0x404+0x54,GAME+0x1060)
    word(GUI_RESOURCE+0x64,GUI_HEADER);word(GUI_HEADER+0xac,OBJECT_TABLE)
    for j,record_bytes in enumerate(row_objects):
        u.mem_write(OBJECT_TABLE+(30+j)*36,record_bytes)
        word(OBJECT_TABLE+(30+j)*36+0x14,MESSAGE_DTI if j==4 else DTI);word(OBJECT_TABLE+(30+j)*36+0x20,0)
    word(DTI,VFT+0x200);word(DTI+24,304//4);word(DTI+28,0x1b6313a3)
    word(ROOT_DTI+24,176//4)
    word(ALLOCATOR,VFT+0x300);word(VFT+0x320,GAME+0x1030);word(VFT+0x334,GAME+0x1034)
    word(VFT+0x514,GAME+0x1084);word(VFT+0x14,GAME+0x1000);word(VFT+0x404+0x14,GAME+0x1014)
    word(VFT+0x404+0x58,GAME+0x540c08);word(VFT+0x404+0x5c,GAME+0x540c38)
    word(VFT+4,GAME+0x1040);word(VFT+0x504,GAME+0xa475e0)
    for offset,target in [(0x38,0x1050),(0x3c,0x1054),(0x40,0x1058)]:word(VFT+offset,GAME+target)
    roots=[];parents=[];arrays=[];original_caches=[]
    for i in range(8):
        instance=DATA+0x28000+i*0x200;objects=DATA+0x2a000+i*0x100
        root=DATA+0x2c000+i*0x200;parent=DATA+0x2e000+i*0x200;desc=DATA+0x60000+i*0x40;cache=DATA+0x40000+i*0x400
        index=16+i;entry=INSTANCE_ARRAY+index*4 if index<primary_count else INSTANCE_ARRAY+0x400+(index-primary_count)*4
        word(entry,instance);word(instance,VFT+0x800);word(instance+0x6c,GUI_OWNER);word(instance+0x70,GUI_RESOURCE)
        word(instance+0xd0,0xffffffff);word(instance+0xd4,0xffffffff)
        word(objects,root);word(objects+4,parent);word(root,VFT+0x404);word(root+0x50,1)
        word(parent,VFT+0x500);word(parent+0x50,14);word(parent+0x54,1)
        word(desc,20);half(desc+4,12);half(desc+6,15);word(desc+8,9);word(desc+12,30)
        word(root+0x9c,desc);word(root+0xa0,objects);word(root+0xa4,cache);word(root+0x80,cache)
        leaves=[DATA+0x70000+i*0x2000+j*0x200 for j in range(10)]
        for j,leaf in enumerate(leaves):
            word(objects+(j+2)*4,leaf);word(leaf,VFT)
            # Nine original drawable leaves and one non-drawing ticket container.
            word(leaf+0x54,1 if j==7 else 0x2000001)
            word(leaf+0x6c,0)
            if j==2:
                word(leaf,VFT+0x900)
                u.mem_write(leaf+0x80,struct.pack("<2f",62.,9.))
                u.mem_write(leaf+0xc8,struct.pack("<2f",355.,38.))
        roots.append(root);parents.append(parent);arrays.append(bytes(u.mem_read(objects,48)));original_caches.append(cache)
    word(ATLAS,22);word(ATLAS+12,0x02000200);word(ATLAS+0x28,DATA+0x64000)
    # Execute the actual full availability predicate, its immutable 51-entry
    # table and enabled-bit check; only the pre-existing scene query is doubled.
    assert struct.unpack_from('<16I',native_image,0x162cde4)[::2]==(308,309,319,320,324,325,329,330)
    u.mem_write(GAME+0x162cde4,native_image[0x162cde4:0x162cde4+51*8])
    word(GAME+0x1838d28,DATA+0xf0800);word(DATA+0xf0800,QUEST)
    word(GAME+0x1838d74,DATA+0xf0804);word(DATA+0xf0804,QUEST)
    word(GAME+0x1838d88,DATA+0xf0808);word(DATA+0xf0808,PROFILE)
    word(PROFILE+0x35d4,sum(1<<i for i in special_enabled))
    word(QUEST+0xb4,RESOURCE);word(RESOURCE+0x64,8);word(RESOURCE+0x6c,RECORDS)
    groups=[(207,2,int(alternative_done)),(105,1,0),(303,26,0),(206,26 if simultaneous else 25,0),
            (213,2,int(alternative_done)),(202,0,0),(402,27,0),(215,2,0)]
    if special:
        groups=[(id,47+i,i//2+1) for i,id in enumerate([308,309,319,320,324,325,329,330])]
    for i,(id,category,alt)in enumerate(groups):u.mem_write(RECORDS+i*12,struct.pack('<IIBBBB',0,id,category,alt,0,0))
    word(GAME+0x18979f0,PROGRESS);u.mem_write(PROGRESS+0x3e0,struct.pack('<HH',2,1))
    ids=[202]*8 if ordinary else [207,105,303,206,213,202,0,402]
    if special:ids=[g[0] for g in groups]
    for i,id in enumerate(ids):
        q=DATA+0x30000+i*0x200;word(ROWS+i*4,q if id else 0);word(q+8,id);half(q+0x10c,(0x300 if id==308 else 0x308) if special else int(id in [303,206]))
    u.mem_write(INFO+0x1104,struct.pack('<16I',*offered,*([0]*(16-len(offered)))));word(INFO+0x1144,17 if bad_count else len(offered))
    u.mem_write(PROFILE+0x52c,b'\xff'*0x100) # New/acknowledgement bits do not complete quests.
    protected=[(PROFILE,0x72c),(PROFILE+0x35d4,8),(QUEST,0x100),(RESOURCE,0x100),(RECORDS,96),(PROGRESS,0x3e4),(ROWS,32),(DATA+0x30000,0x1000),(INFO+0x1104,68)]
    immutable=[bytes(u.mem_read(p,n))for p,n in protected]
    u.reg_write(arm.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(arm.UC_ARM_REG_FPEXC,0x40000000)
    tls_value=0;states={};colors={};calls=[];parent_return=0;parent_sp=0;heap=DATA+0xa0000
    constructing=None;factory_index=0
    plugin_heap=DATA+0x120000;hook_count=0;startup_logs=[]
    allocations={};freed=[];created=[];drawn=[];object_attempts=0;mapping_allocations=[];styles={};quads=[];fitting=False;fit_factors=[]
    # Isolate native colour/mask dispatch and geometry from GPU command encoding.
    # Model an active vertex-buffer frame and an already-bound texture shader.
    pool=DATA+0xf0300;context=DATA+0x150000;commands=DATA+0x151000
    vertices=DATA+0x160000;buffer=DATA+0x152000;draw_object=0;vertex_offset=0
    word(pool+0x90,1);word(pool+0x94,0);word(pool+0x98,1);word(pool+0xa4,buffer);word(pool+0xb0,vertices)
    word(context+4,commands);word(context+8,0x1000);word(commands+0x124,buffer);u.mem_write(commands+0x134,b'\x18')
    def allocate(size):
        nonlocal heap
        p=heap;heap=(p+size+31)&~15;allocations[p]=size;u.mem_write(p+size,b'\xa5'*16);return p
    def plugin_allocate(size):
        nonlocal plugin_heap
        pointer=plugin_heap;plugin_heap=(pointer+size+15)&~15;return pointer
    def release(p):
        assert p not in freed,('double free',hex(p));freed.append(p)
        if p in allocations:assert bytes(u.mem_read(p+allocations[p],16))==b'\xa5'*16,('allocation overflow',hex(p))
    def ret(cpu,value=0):cpu.reg_write(arm.UC_ARM_REG_R0,value);cpu.reg_write(arm.UC_ARM_REG_PC,cpu.reg_read(arm.UC_ARM_REG_LR))
    def text(cpu,p):
        out=b''
        while len(out)<512:
            c=bytes(cpu.mem_read(p+len(out),1))
            if c==b'\0':return out.decode()
            out+=c
        raise AssertionError('unterminated string')
    def trace(cpu,address,size,_):
        nonlocal tls_value,parent_return,parent_sp,object_attempts,factory_index,hook_count,draw_object,vertex_offset
        r=[cpu.reg_read(x)for x in REGS[:4]]
        if address==RETURN or (fitting and address==GAME+0xa423cc):cpu.emu_stop();return
        if fitting and address==GAME+0xa45b58:
            # Glyph measurement and final glyph scaling are supplied; execute
            # the real AutoScale flag dispatch and native clamped scale decision.
            fit_factors.append(struct.unpack('<f',struct.pack('<I',cpu.reg_read(arm.UC_ARM_REG_S0)))[0])
            ret(cpu);return
        if address==MODULE+names['mwc_svc_get_info']:
            assert r[1]==18;cpu.mem_write(r[0],struct.pack('<Q',0x0100770008dd8000));ret(cpu);return
        if address==MODULE+names['mwc_svc_flush']:ret(cpu);return
        if address==imports.get('nnosAllocateTlsSlot'):word(r[0],1);ret(cpu);return
        if address==imports.get('forge_log_getLevel'):ret(cpu,3);return # User's unchanged ERROR-only filter.
        if address==imports.get('forge_log'):startup_logs.append(text(cpu,r[2]));ret(cpu);return
        if address==imports.get('malloc'):ret(cpu,plugin_allocate(r[0]));return
        if address==imports.get('free'):ret(cpu);return
        if address==imports.get('forge_patch_create'):
            # AAPCS returns this 20-byte struct through hidden r0; arguments shift.
            out,target,source,length=r;assert length==8
            patch,original=plugin_allocate(8),plugin_allocate(8)
            cpu.mem_write(patch,bytes(cpu.mem_read(source,8)));cpu.mem_write(original,bytes(cpu.mem_read(target,8)))
            cpu.mem_write(out,struct.pack('<5I',target,8,patch,original,0));ret(cpu,out);return
        if address in [imports.get('forge_patch_enable'),imports.get('forge_patch_disable'),imports.get('forge_patch_destroy')]:
            target,length,patch,original,enabled=struct.unpack('<5I',cpu.mem_read(r[0],20))
            if address==imports.get('forge_patch_enable'):
                cpu.mem_write(target,bytes(cpu.mem_read(patch,length)));word(r[0]+16,1)
            elif enabled:
                cpu.mem_write(target,bytes(cpu.mem_read(original,length)));word(r[0]+16,0)
            ret(cpu);return
        if address==imports.get('forge_hook_create'):
            # Matching 24-byte Hook uses hidden r0 too. Forge owns the continuation.
            out,target,detour,original_out=r;hook_count+=1
            continuation=ENGINE+0x800+(hook_count-1)*16
            code=bytes(cpu.mem_read(target,8))+struct.pack('<II',0xe51ff004,target+8)
            if hook_count==fail_hook:code=b'\0'*4+code[4:]
            cpu.mem_write(continuation,code);word(original_out,continuation)
            cpu.mem_write(target,struct.pack('<II',0xe51ff004,detour))
            cpu.mem_write(out,struct.pack('<6I',target,detour,continuation,0,0,0));ret(cpu,out);return
        if address==MODULE+names['mwc_svc_query']:
            region,size=(ENGINE,4096) if ENGINE<=r[2]<ENGINE+4096 else (GAME,0x2000000)
            cpu.mem_write(r[0],struct.pack('<QQ6I',region,size,0,0,7,0,0,0));word(r[1],0);ret(cpu);return
        if address==imports.get('nnosGetTlsValue'):assert r[0]==1;ret(cpu,tls_value);return
        if address==imports.get('nnosSetTlsValue'):assert r[0]==1;tls_value=r[1];ret(cpu);return
        if address==imports.get('forge_mem_getMainTextAddr'):ret(cpu,GAME);return
        if address==imports.get('forge_singleton_getInstanceByName'):ret(cpu,{'sQuest':QUEST,'sUserInfo':PROFILE}.get(text(cpu,r[0]),0));return
        if address in [ENGINE+4,ENGINE+0x810]:
            assert r[:2]==[CONTROLLER,0 if invalid_info else INFO] and tls_value!=0
            parent_return=cpu.reg_read(arm.UC_ARM_REG_LR);parent_sp=cpu.reg_read(arm.UC_ARM_REG_SP)
            cpu.reg_write(arm.UC_ARM_REG_SP,parent_sp-16);cpu.mem_write(parent_sp-16,struct.pack('<4I',0,0,ROWS,0))
            for reg,value in zip(REGS[:4],[UI,selected,2,0]):cpu.reg_write(reg,value)
            cpu.reg_write(arm.UC_ARM_REG_LR,ENGINE+8);cpu.reg_write(arm.UC_ARM_REG_PC,GAME+0x616cb0);calls.append('parent');return
        if address==ENGINE+8:cpu.reg_write(arm.UC_ARM_REG_SP,parent_sp);cpu.reg_write(arm.UC_ARM_REG_PC,parent_return);return
        if address in [ENGINE,ENGINE+0x800]:
            sp=cpu.reg_read(arm.UC_ARM_REG_SP);assert r+list(struct.unpack('<3I',cpu.mem_read(sp,12)))==[UI,selected,2,0,0,0,ROWS]
            # Model the original builder's immediate request visibility, independent
            # of quest data. This catches accidental classification-based layout.
            for i in range(8):
                table=read(DATA+0x28000+i*0x200+0xd8);request=read(table+12)
                word(request+0x54,(read(request+0x54)&~1)|int(i in requests))
            calls.append('row-original');ret(cpu);return
        if address==GAME+0x546f28:assert r[0]==HOLDER;ret(cpu,gui_identity);return
        if address==GAME+0x7aef68:ret(cpu,MAP_DTI if r[0]==0x57fd7fb5 else DTI if r[0]==0x1b6313a3 else MESSAGE_DTI if r[0]==TITLE_CRC else UNUSED_TEXT_DTI if r[0]==0x313f6cc4 else ROOT_DTI);return
        if address==GAME+0x1000:ret(cpu,DTI);return
        if address==GAME+0x1014:ret(cpu,ROOT_DTI);return
        if address==GAME+0x1080:ret(cpu,ANIM_DTI);return
        if address==GAME+0x1084:ret(cpu,NULL_DTI);return
        if address==GAME+0xb80f94:
            assert r[:2]==[GUI_RESOURCE,20];ret(cpu,DATA+0x60000+constructing*0x40);return
        if address==GAME+0x1038:
            assert r[0]==ALLOCATOR and r[2]==16
            if r[1]==48:ret(cpu,DATA+0x2a000+constructing*0x100)
            elif r[1]==152:ret(cpu,original_caches[constructing])
            else:
                assert r[1]==168;ret(cpu,0 if fail_cache else allocate(168))
            return
        if address==GAME+0x1064:
            objects=DATA+0x2a000+constructing*0x100
            pointer=read(objects+factory_index*4);factory_index+=1;ret(cpu,pointer);return
        if address in [GAME+0xa484c4,GAME+0xa49bac,GAME+0xa49bb8,GAME+0x1060]:ret(cpu);return
        if address==GAME+0xb80fd0:assert r[:2]==[GUI_RESOURCE,22];ret(cpu,ATLAS);return
        if address==GAME+0x7aa47c:ret(cpu,MAP_ALLOCATOR if r[0]==MAP_DTI else ALLOCATOR);return
        if address==GAME+0x1070:
            assert r[0]==MAP_ALLOCATOR and r[2]==16
            if r[1]==48:ret(cpu,DATA+0x2a000+constructing*0x100)
            else:
                assert r[1]==52
                pointer=0 if fail_mapping else allocate(52)
                if pointer:mapping_allocations.append(pointer)
                ret(cpu,pointer)
            return
        if address==GAME+0x1074:
            assert r[0]==MAP_ALLOCATOR;release(r[1]);ret(cpu);return
        if address==GAME+0x1030:
            assert r==[ALLOCATOR,304,16,0x1b6313a3];object_attempts+=1
            ret(cpu,0 if fail_object or object_attempts==fail_at else allocate(304));return
        if address==GAME+0x1034:release(r[1]);ret(cpu);return
        if address==GAME+0xa4f60c:
            assert r[0]in allocations;created.append(r[0]) # Execute the real constructor below.
        if address in [GAME+0xa56a7c,GAME+0xa56a8c]:ret(cpu,DTI);return
        if address in [GAME+0xba2544,GAME+0xba28c4]:ret(cpu);return
        if address==GAME+0x1040:release(r[0]);ret(cpu);return
        # Style calls execute the original game instructions.
        if address==GAME+0xa4faf0:assert r[1]==22
        if address==GAME+0xa4fb58:assert tuple(struct.unpack('<4f',cpu.mem_read(r[1],16)))==UV
        if address-GAME in STYLE:styles.setdefault(r[0],{})[address-GAME]=r[1]
        if address==GAME+0xba2280:
            assert r[:3]==[pool,draw_object+0xbc,96]
            word(r[1],vertex_offset);word(r[1]+4,0x01800060);vertex_offset+=96
            word(commands+0x138,read(r[1]));ret(cpu,1);return
        if address in [GAME+0xa4eb9c,GAME+0xa3e3b0,GAME+0x541624,GAME+0x541844,GAME+0x542aa0,
                       GAME+0x8826fc,GAME+0x882760]:ret(cpu);return
        if address==GAME+0x93eff4:
            quads.append((draw_object,bytes(cpu.mem_read(vertices+read(draw_object+0xbc),96))))
            ret(cpu);return
        if address in [GAME+0xb375c4,GAME+0xb37dcc,GAME+0xb38004,GAME+0xb3880c]:
            raise AssertionError(('badge entered native mask pass instead of colour rendering',hex(address)))
        if address==GAME+0xa47950:
            row=next(i for i,p in enumerate(parents) if read(r[0]+0x70)==p) if read(r[0]+0x70) else None
            if row is not None:states[row]=r[1]
        if address==GAME+0xa4e0b8:
            row=next(i for i,p in enumerate(parents) if read(r[0]+0x70)==p);assert r[2]<4
            colors[row]=read(r[1])
        if address in [GAME+0x1050,GAME+0x1054,GAME+0x1058,GAME+0xa4e628,GAME+0xa4fc9c,GAME+0xa4eddc]:
            if address in [GAME+0xa4e628,GAME+0xa4fc9c,GAME+0xa4eddc] and read(r[0]+0x50)==BADGE_ID:
                if address==GAME+0xa4e628:
                    # Bounding-box calculation precedes this dispatch in the game;
                    # suppress that separate stage, without changing material mode.
                    word(r[0]+0xd0,read(r[0]+0xd0)&~1)
                if address==GAME+0xa4fc9c:drawn.append(r[0]);draw_object=r[0]
            else:ret(cpu);return
        if address==GAME+0x523da4:assert r[0]==PROFILE+0x42c;ret(cpu,int(r[1]in completed));return
        if address==GAME+0x3b1a18:assert not special and r[:2]==[QUEST,2];ret(cpu,int(prerequisites));return
        if address==GAME+0x54af8c:assert special and r[:3]==[r[0],0xff,0] and r[0] in ids
        if address==GAME+0x3b2174:assert r[0]==QUEST;ret(cpu,int(available));return
        if ENGINE+0x300<=address<ENGINE+4096:raise AssertionError(('unexpected import',hex(address)))
    u.hook_add(unicorn.UC_HOOK_CODE,trace)
    def call(address,a=0,b=0):
        u.reg_write(arm.UC_ARM_REG_SP,STACK);u.reg_write(arm.UC_ARM_REG_LR,RETURN);u.reg_write(arm.UC_ARM_REG_R0,a);u.reg_write(arm.UC_ARM_REG_R1,b)
        try:u.emu_start(address,RETURN+4,count=1000000)
        except unicorn.UcError as error:
            raise AssertionError((str(error),hex(u.reg_read(arm.UC_ARM_REG_PC)),hex(u.reg_read(arm.UC_ARM_REG_LR)),[hex(u.reg_read(r))for r in REGS[:8]])) from error
        assert u.reg_read(arm.UC_ARM_REG_SP)==STACK,(hex(u.reg_read(arm.UC_ARM_REG_PC)),hex(u.reg_read(arm.UC_ARM_REG_SP)))
    # Exercise the actual lifecycle/installer before any row callback; no forced
    # ACTIVE flag can hide a startup regression. Forge/kernel calls remain doubles.
    assert read(MODULE+base_symbol)==0 and bytes(u.mem_read(MODULE+names['kqm_active'],1))==b'\0'
    assert read(MODULE+names['kqm_original'])==read(MODULE+names['kqm_parent_original'])==0
    call(MODULE+names['forge_onInit'])
    if fail_hook:
        assert hook_count==fail_hook
        assert not read(MODULE+names['kqm_active'])&255
        assert any('restored originals' in message for message in startup_logs)
        for offset in [0x616cb0,0x54d030]:assert bytes(u.mem_read(GAME+offset,8))==native_image[offset:offset+8]
        CASES+=1;return {'case':label,'startup_rollback':True,'failed_hook':fail_hook}
    assert bytes(u.mem_read(MODULE+names['kqm_active'],1))==b'\x01',startup_logs
    assert hook_count==2 and read(MODULE+names['kqm_original'])==ENGINE+0x800
    assert read(MODULE+names['kqm_parent_original'])==ENGINE+0x810
    assert any('installed' in message for message in startup_logs)
    # Run both real ARM constructor functions. a38828 supplies the GUI owner;
    # a38bc0 writes each object's owner/resource and links the original ARC tree.
    # Factories and property initialization are doubles, not the ownership path.
    for i in range(8):
        constructing=i;factory_index=0
        instance=DATA+0x28000+i*0x200
        call(GAME+0xa38828,instance,20)
        assert factory_index==12 and read(instance+0xdc)==roots[i]
        for j in range(12):
            pointer=read(DATA+0x2a000+i*0x100+j*4)
            assert read(pointer+0x74)==GUI_OWNER and read(pointer+0x78)==GUI_RESOURCE
            assert read(pointer+0x50)==struct.unpack_from('<I',row_objects[j])[0]
        assert GUI_OWNER!=instance
        word(roots[i]+0x8c,3) # A newly constructed native row needs its first draw-list build.
    constructing=None
    if invalid_request:word(read(DATA+0x2a000+12)+0x50,99)
    if invalid_title=='subclass':
        u.mem_write(VFT+0xb00,bytes(u.mem_read(VFT+0x900,128)))
        word(VFT+0xb14,GAME+0xa56b4c)
        text_getter_got=0xa56b50+8+struct.unpack_from('<I',native_image,0xa56b58)[0]
        word(GAME+text_getter_got,UNUSED_TEXT_DTI)
        word(read(DATA+0x2a000+16),VFT+0xb00)
    elif invalid_title:word(read(DATA+0x2a000+16)+0x50,99)
    if invalid_owner:word(read(DATA+0x2a000+8)+0x74,DATA+0x28000)
    if invalid_object:word(read(DATA+0x2a000+7*0x100+8)+0x50,99)
    call(GAME+0x54d030,CONTROLLER,0 if invalid_info else INFO)
    assert tls_value==0 and calls==['parent','row-original']
    call(MODULE+names['forge_onUpdate'])
    assert any('entered urgent parent hook' in s for s in startup_logs)
    assert any('entered quest row hook' in s for s in startup_logs)
    if not (invalid_object or invalid_owner or invalid_info or bad_count or gui_identity!=5 or fail_object or fail_cache or fail_mapping or fail_at):
        assert any('first classified page, Village=2, Hub/G=1' in s for s in startup_logs),startup_logs
        if not ordinary:
            assert any(('row=0 quest=308 group=47 quest_flags=0x300 badge=' if special else 'row=0 quest=207 group=2 quest_flags=0x0 badge=') in s for s in startup_logs),startup_logs
            assert any('first visible badges;' in s for s in startup_logs),startup_logs
        else:assert not any('first visible badges;' in s for s in startup_logs)
    log_count=len(startup_logs)
    call(MODULE+names['forge_onUpdate'])
    assert len(startup_logs)==log_count,('diagnostics repeat every frame',startup_logs)
    if fail_at:
        assert len(created)==fail_at-1 and not states and not colors
        call(GAME+0x54d030,CONTROLLER,INFO) # Recover while retaining valid hidden native children.
        assert tls_value==0 and calls==['parent','row-original']*2
    assert [bytes(u.mem_read(p,n))for p,n in protected]==immutable
    for i in range(8):assert bytes(u.mem_read(DATA+0x2a000+i*0x100,48))==arrays[i]
    if invalid_object or invalid_owner or gui_identity!=5 or fail_object or fail_cache or fail_mapping:
        assert not states and not colors
        assert all(read(root+0xa4)==old for root,old in zip(roots,original_caches))
        assert all(p in freed for p in allocations) # Failed preparation releases all unpublished allocations.
    else:
        # Run the exact cleanup function seen in the crash. Its real count getter
        # counts 13 linked nodes and therefore requires a 13-entry lookup array.
        for i in range(8):call(GAME+0x5456e4,0,DATA+0x28000+i*0x200)
        assert len(created)==8-int(bool(invalid_request or invalid_title)) and len(allocations)==3*len(created)
        assert all(p in freed for i,p in enumerate(original_caches) if not(i==0 and (invalid_request or invalid_title)))
        if repeat:
            call(GAME+0x54d030,CONTROLLER,0 if invalid_info else INFO);assert len(created)==8-int(bool(invalid_request or invalid_title)) and len(allocations)==3*len(created)
        if invalid_info or ordinary or bad_count:assert states==dict.fromkeys(range(8),0) and not colors
        elif special:
            assert states==dict.fromkeys(range(8),1)
            assert colors=={i:(0xff808080 if not available or i not in special_enabled or any(id in completed for id in ids[(i//2)*2:(i//2)*2+2]) else 0xff39d2ff) for i in range(8)}
        else:
            assert states=={i:v for i,v in enumerate([1,1,1,1,1,0,0,0]) if not(i==0 and (invalid_request or invalid_title))}
            urgency=0xff39d2ff if 303 in offered and available and prerequisites else 0xff808080
            expected_colors={0:0xff808080 if 207 in completed or alternative_done else 0xff2547e7,1:0xff808080,
                           2:0xff808080 if 303 in completed else urgency,3:0xff39d2ff if simultaneous and 206 in offered else 0xff808080,4:0xff808080}
            if invalid_request or invalid_title:expected_colors.pop(0)
            assert colors==expected_colors
        request_bytes=[]
        for i in range(8):
            table=read(DATA+0x28000+i*0x200+0xd8)
            title=read(table+16);request=read(table+12)
            request_bytes.append(bytes(u.mem_read(request,304)))
            fitted=bool(states.get(i))
            width=(263. if i in requests else 299.) if fitted else 355.
            assert struct.unpack('<2f',u.mem_read(title+0xc8,8))==(width,38.)
            assert bool(read(title+0xf0)&1)==fitted
            assert read(title+0xf8)&0xc0000==0
            if fitted:assert read(title+0xf0)&0x10000 # Native cached-layout invalidation.
            if fitted:
                for measured in [80.,500.]:
                    parser=DATA+0x180000;glyph=parser+0x100
                    u.mem_write(parser,b'\0'*0x200)
                    word(parser+0x10,title);word(parser+0x1c,1);word(parser+8,1)
                    word(parser+0x48,glyph);u.mem_write(parser+0x30,struct.pack('<3f',width,38.,20.))
                    u.mem_write(glyph+4,struct.pack('<2f',measured,20.));word(glyph+0x28,22)
                    u.reg_write(arm.UC_ARM_REG_R4,parser);fitting=True;fit_factors.clear()
                    call(GAME+0xa42374);fitting=False
                    expected=min(1.,width/measured)
                    assert abs(struct.unpack('<f',u.mem_read(parser+0x38,4))[0]-20.*expected)<0.0001
                    assert bool(fit_factors)==(measured>width)
                    if fit_factors:assert abs(fit_factors[0]-expected)<0.0001
                # The real cached-layout refresh consumes bit16 and invokes
                # the native Text refresh virtual. Text buffers are empty in
                # this fixture; measurement/scaling were checked above.
                call(GAME+0xa53aa8,title)
                assert not(read(title+0xf0)&0x10000)

        for p in created:
            assert styles[p]==SOURCE_STYLE,('runtime style differs from actual GUI constants',styles[p],SOURCE_STYLE)
            assert read(p+0x74)==GUI_OWNER
            i=next(i for i,parent in enumerate(parents) if read(p+0x70)==parent)
            assert read(p+0x54)&1==states[i]
            if i in colors:assert struct.unpack('<4I',u.mem_read(p+0xa4,16))==(colors[i],)*4
            assert read(p+0x104)==ATLAS
            assert struct.unpack('<4f',u.mem_read(p+0x10c,16))==UV
            assert struct.unpack('<2f',u.mem_read(p+0x80,8))==((329. if i in requests and states.get(i) else 365.),3.)
            assert struct.unpack('<2f',u.mem_read(p+0xb4,8))==(32.,32.)
        if late_invalid:
            table=read(DATA+0x28000+0xd8);request=read(table+12);title=read(table+16)
            word(request+0x50,99)
            call(GAME+0x54d030,CONTROLLER,INFO)
            assert states[0]==0 and states[1]==1
            assert struct.unpack('<2f',u.mem_read(title+0xc8,8))==(355.,38.)
            assert not(read(title+0xf0)&1)
            call(MODULE+names['forge_onUpdate'])
            assert any('request/title binding invalid' in log for log in startup_logs)
            log_count=len(startup_logs)
            call(MODULE+names['forge_onUpdate']);assert len(startup_logs)==log_count
            word(request+0x50,20)
            call(GAME+0x54d030,CONTROLLER,INFO)
            assert states[0]==1 and len(created)==8
        if recycle:
            old_created=list(created)
            # Same slot changes from free to occupied; request mark stays intact.
            requests=tuple(range(8))
            call(GAME+0x54d030,CONTROLLER,INFO)
            for p in created:
                if read(p+0x54)&1:assert struct.unpack('<f',u.mem_read(p+0x80,4))[0]==329.
            # A later unavailable offer context must restore every fitted title
            # before classification's early return, including all unused rows.
            invalid_info=True
            call(GAME+0x54d030,CONTROLLER,0)
            assert created==old_created
            assert states==dict.fromkeys(range(8),0)
            for i in range(8):
                table=read(DATA+0x28000+i*0x200+0xd8);title=read(table+16)
                assert struct.unpack('<2f',u.mem_read(title+0xc8,8))==(355.,38.)
                assert not(read(title+0xf0)&1)
            # Reuse the slots for ordinary quests as when scrolling to a page
            # without keys. Their title area must be restored too.
            invalid_info=False
            for i in range(8):word(DATA+0x30000+i*0x200+8,202)
            call(GAME+0x54d030,CONTROLLER,INFO)
            assert states==dict.fromkeys(range(8),0)
            for i in range(8):
                title=read(read(DATA+0x28000+i*0x200+0xd8)+16)
                assert struct.unpack('<2f',u.mem_read(title+0xc8,8))==(355.,38.)
                assert not(read(title+0xf0)&1)
            for i,id in enumerate(ids):word(DATA+0x30000+i*0x200+8,id)
            # Restore valid context and original request states, exactly as a
            # scroll back to the first page does; no objects may be duplicated.
            requests=();invalid_info=False
            call(GAME+0x54d030,CONTROLLER,INFO)
            assert created==old_created and states==dict(enumerate([1,1,1,1,1,0,0,0]))
        for i in range(8):
            table=read(DATA+0x28000+i*0x200+0xd8)
            assert bytes(u.mem_read(read(table+12),304))==request_bytes[i]
        for root in roots:call(GAME+0xa494a0,root,context)
        assert len(drawn)==sum(states.values()),('native draw walker omitted badge',drawn,states)
        assert len(quads)==len(drawn),('no native colour quad emitted',len(quads),len(drawn))
        for p,quad in quads:
            f=struct.unpack('<24f',quad);words=struct.unpack('<24I',quad)
            i=next(i for i,parent in enumerate(parents)if read(p+0x70)==parent)
            assert [words[j]for j in [3,9,15,21]]==[colors[i]]*4
            assert [f[j]for j in [0,6,12,18]]==[0.,32.,0.,32.]
            assert [f[j]for j in [1,7,13,19]]==[0.,0.,32.,32.]
            assert [f[j]for j in [4,10,16,22]]==[UV[0]+.5,UV[2]-.5,UV[0]+.5,UV[2]-.5]
            assert [f[j]for j in [5,11,17,23]]==[UV[1]+.5,UV[1]+.5,UV[3]-.5,UV[3]-.5]
        for p,size in allocations.items():assert bytes(u.mem_read(p+size,16))==b'\xa5'*16,('native draw-cache overflow',hex(p))
        # Run the actual root and base-container destructors; the mocked MT free
        # records ownership, while their real ARM loops destroy the new children.
        for i,root in enumerate(roots):
            instance=DATA+0x28000+i*0x200;table=read(instance+0xd8)
            assert table==read(root+0xa0) and bytes(u.mem_read(table,48))==arrays[i]
            if not(i==0 and (invalid_request or invalid_title)):assert read(read(table+48)+0x50)==BADGE_ID
            call(GAME+0xa38b58,instance)
            assert read(instance+0xd8)==read(instance+0xdc)==0
        assert all(p in freed for p in allocations),('native cleanup leaked new allocations',allocations,freed)
    CASES+=1;return {'case':label,'visible':states,'colors':colors,'native_draws':len(drawn),'ownership_cleanup':True,'saved_records_unchanged':True}
results=[test_case('all eight special urgents outside rank-up offer pool',special=True,offered=(),prerequisites=False,requests=(0,2,4,6),repeat=True),
         test_case('only enabled special records become yellow',special=True,offered=(),special_enabled=(0,2,4,6),prerequisites=False),
         test_case('disabled special records remain grey despite scene availability',special=True,offered=(),special_enabled=(),prerequisites=False),
         test_case('special pair completed by first-run quest',special=True,offered=(),completed=(308,),prerequisites=False),
         test_case('special pair completed by repeat quest',special=True,offered=(),completed=(309,),prerequisites=False),
         test_case('special pairs complete independently',special=True,offered=(),completed=(308,324),prerequisites=False),
         test_case('unavailable special urgents are grey',special=True,offered=(),available=False,prerequisites=False),
         test_case('special urgency does not bypass invalid offer context',special=True,invalid_info=True),
         test_case('Text subclass is rejected for the Message resource',invalid_title='subclass'),
         test_case('invalid request on a fitted row restores its title',late_invalid=True),
         test_case('request shares the key slot without overwriting bubble',requests=(0,2,3,5)),
         test_case('selected row uses the same request-relative layout',requests=(0,4),selected=4),
         test_case('missing request binding leaves other badges working',invalid_request=True),
         test_case('missing title binding leaves other badges working',invalid_title=True),
         test_case('scrolling and early-return restore title fitting',recycle=True),
         test_case('first malformed trampoline rolls back',fail_hook=1),
         test_case('second malformed trampoline rolls back both targets',fail_hook=2),
         test_case('all badge states and native draw traversal'),test_case('urgent inactive',offered=()),
         test_case('urgent unavailable',available=False),test_case('urgent prerequisites incomplete',prerequisites=False),
         test_case('viewing still red'),test_case('key completion',completed=(207,213)),test_case('urgent completion',completed=(303,213)),
         test_case('resource object mismatch',invalid_object=True),test_case('animation address is not the GUI owner',invalid_owner=True),test_case('no offer context',invalid_info=True),
         test_case('ordinary rows',ordinary=True),test_case('invalid offer count',bad_count=True),test_case('different GUI',gui_identity=4),
         test_case('satisfied alternative',alternative_done=True),test_case('simultaneous urgents',simultaneous=True,offered=(303,206)),
         test_case('secondary table',primary_count=16),test_case('both tables',primary_count=20),test_case('primary table empty',primary_count=0),
         test_case('object allocation failure',fail_object=True),test_case('cache allocation failure',fail_cache=True),test_case('map allocation failure',fail_mapping=True),
         test_case('repeated row update reuses native children',repeat=True),
         test_case('partial allocation failure recovers without duplicate children',fail_at=4)]
record('native-adapter.json',{'status':'PASSED','compiled_nro':True,'cases':CASES,'results':results,
          'error_only_filter_diagnostic_snapshots':True,'deduplicated_scalar_snapshots':True,
          'title_resource_class_crc':TITLE_CRC,'native_message_type_getter':True,
          'resource_inline_constants':SOURCE_STYLE,'native_prepaint_and_texture_draw':True,'native_quad_geometry':True,'native_autoscale_dispatch_and_clamp':True,'request_visibility_placement':True,'title_restoration':True,
          'actual_forge_lifecycle_and_installer':True,'installed_entry_branches':True,'native_resource_cleanup':True,'expanded_object_map_and_native_instance_clear':True,'support_signatures_precede_hook_signatures':True,'native_animation_constructor':True,'native_texture_constructor':True,'native_style_texture_color_visibility_setters':True,'null_dti_placement_slot':True,'native_cache_allocator_and_free':True,'distinct_gui_owner':True,'native_draw_walker':True,'native_root_destructors':True,'archive_replacements':0,
          'thread_context_restored':True,'runtime_test':'NOT RUN','nro_sha256':digest(BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro')})
print('PASS: compiled native insertion, actual draw walker/destructors, colors and allocation rollback:',CASES,'cases')
