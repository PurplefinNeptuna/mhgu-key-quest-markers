#!/usr/bin/env python3
"""Execute the shipped ARM callbacks, native draw walker and native ownership cleanup.

Forge/kernel/MT factories and GPU commands are doubles; game archive bytes are
unchanged. This checks object insertion and real draw-list traversal, not pixels.
"""
import json,struct,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paths import BUILD_ROOT,CONFIG,input_path
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
INSTANCE_ARRAY=DATA+0x27000
REGS=[getattr(arm,'UC_ARM_REG_R'+str(i))for i in range(13)]
BADGE_ID=0x4b514d33
STYLE=[0xa4dc24,0xa4a9f4,0xa47a94,0xa4dca0,0xa47a04,0xa4aa24,0xa4aa5c,0xa4aa94,0xa4aac8,0xa4aafc,0xa4dc54,0xa4fa5c]
CASES=0

def test_case(label, *, offered=(303,),completed=(213,),available=True,prerequisites=True,invalid_object=False,
              invalid_info=False,invalid_owner=False,ordinary=False,bad_count=False,gui_identity=5,alternative_done=False,
              simultaneous=False,primary_count=63,fail_object=False,fail_cache=False,repeat=False,fail_at=0):
    global CASES
    u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);u.ctl_set_cpu_model(arm.UC_CPU_ARM_MAX)
    u.mem_map(MODULE,((len(data)+4095)//4096+64)*4096);u.mem_write(MODULE,data)
    u.mem_map(ENGINE,4096);u.mem_map(0x41000000,0x20000);u.mem_map(GAME,0x2000000)
    # Real game code rebuilds/traverses the draw cache and destroys the owned tree.
    for first,last in [(0xa494a0,0xa4964c),(0xa48668,0xa486fc),(0xa475e0,0xa47648),
                       (0xa38828,0xa38944),(0xa38bc0,0xa38e50),(0xa49b28,0xa49bac),(0xa4844c,0xa48470),(0x540c08,0x540c64),
                       (0xa4d0d8,0xa4d32c),(0xa4f60c,0xa4f840)]:
        u.mem_write(GAME+first,native_image[first:last])
    # Exercise the actual texture setters too, including their dirty propagation.
    u.mem_write(GAME+0xa47000,native_image[0xa47000:0xa57000])
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
    word(MODULE+base_symbol,GAME);word(MODULE+names['kqm_original'],ENGINE);word(MODULE+names['kqm_parent_original'],ENGINE+4)
    word(MODULE+names['kqm_tls_slot'],1);u.mem_write(MODULE+names['kqm_active'],b'\x01')
    word(CONTROLLER+0x54,UI);word(UI+0x24,HOLDER);word(HOLDER,VFT+0x100);word(VFT+0x1ac,GAME+0x1010)
    word(HOLDER+0x298,primary_count);word(HOLDER+0xf8,INSTANCE_ARRAY);word(HOLDER+0x294,INSTANCE_ARRAY+0x400)
    # The real DTI exposes three virtual slots. +0x0c is deliberately null:
    # earlier fixtures invented a placement-constructor slot that MHGU lacks.
    for offset in range(0,20,4):
        target=struct.unpack_from('<I',native_image,0x178ff90+offset)[0]
        word(VFT+0x200+offset,GAME+target if target else 0)
    assert read(VFT+0x20c)==0
    word(ROOT_DTI+4,1);word(DTI+4,2)
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
    word(VFT+0x208,GAME+0x1064);word(VFT+0x31c,GAME+0x1038)
    word(VFT+0x404+0x54,GAME+0x1060)
    word(GUI_RESOURCE+0x64,GUI_HEADER);word(GUI_HEADER+0xac,OBJECT_TABLE)
    for j,record_bytes in enumerate(row_objects):
        u.mem_write(OBJECT_TABLE+(30+j)*36,record_bytes)
        word(OBJECT_TABLE+(30+j)*36+0x14,DTI);word(OBJECT_TABLE+(30+j)*36+0x20,0)
    word(DTI,VFT+0x200);word(DTI+24,304//4);word(DTI+28,0x1b6313a3)
    word(ROOT_DTI+24,176//4)
    word(ALLOCATOR,VFT+0x300);word(VFT+0x320,GAME+0x1030);word(VFT+0x334,GAME+0x1034)
    word(VFT+0x514,GAME+0x1000);word(VFT+0x14,GAME+0x1000);word(VFT+0x404+0x14,GAME+0x1014)
    word(VFT+0x404+0x58,GAME+0x540c08);word(VFT+0x404+0x5c,GAME+0x540c38)
    word(VFT+4,GAME+0x1040);word(VFT+0x504,GAME+0xa475e0)
    for offset,target in [(0x38,0x1050),(0x3c,0x1054),(0x40,0x1058)]:word(VFT+offset,GAME+target)
    roots=[];parents=[];arrays=[];original_caches=[]
    for i in range(8):
        instance=DATA+0x28000+i*0x200;objects=DATA+0x2a000+i*0x100
        root=DATA+0x2c000+i*0x200;parent=DATA+0x2e000+i*0x200;desc=DATA+0x60000+i*0x40;cache=DATA+0x40000+i*0x400
        index=16+i;entry=INSTANCE_ARRAY+index*4 if index<primary_count else INSTANCE_ARRAY+0x400+(index-primary_count)*4
        word(entry,instance);word(instance+0x6c,GUI_OWNER);word(instance+0x70,GUI_RESOURCE)
        word(instance+0xd0,0xffffffff);word(instance+0xd4,0xffffffff)
        word(objects,root);word(objects+4,parent);word(root,VFT+0x404);word(root+0x50,1)
        word(parent,VFT+0x500);word(parent+0x50,14);word(parent+0x54,1)
        word(desc,20);half(desc+4,12);half(desc+6,15);word(desc+8,9);word(desc+12,30)
        word(root+0x9c,desc);word(root+0xa0,objects);word(root+0xa4,cache);word(root+0x80,cache)
        leaves=[DATA+0x70000+i*0x2000+j*0x140 for j in range(10)]
        for j,leaf in enumerate(leaves):
            word(objects+(j+2)*4,leaf);word(leaf,VFT)
            # Nine original drawable leaves and one non-drawing ticket container.
            word(leaf+0x54,1 if j==7 else 0x2000001)
            word(leaf+0x6c,0)
        roots.append(root);parents.append(parent);arrays.append(bytes(u.mem_read(objects,48)));original_caches.append(cache)
    word(ATLAS,22);word(ATLAS+12,0x02000200);word(ATLAS+0x28,DATA+0x64000)
    word(QUEST+0xb4,RESOURCE);word(RESOURCE+0x64,8);word(RESOURCE+0x6c,RECORDS)
    groups=[(207,2,int(alternative_done)),(105,1,0),(303,26,0),(206,26 if simultaneous else 25,0),
            (213,2,int(alternative_done)),(202,0,0),(402,27,0),(215,2,0)]
    for i,(id,category,alt)in enumerate(groups):u.mem_write(RECORDS+i*12,struct.pack('<IIBBBB',0,id,category,alt,0,0))
    word(GAME+0x18979f0,PROGRESS);u.mem_write(PROGRESS+0x3e0,struct.pack('<HH',2,1))
    ids=[202]*8 if ordinary else [207,105,303,206,213,202,0,402]
    for i,id in enumerate(ids):
        q=DATA+0x30000+i*0x200;word(ROWS+i*4,q if id else 0);word(q+8,id);half(q+0x10c,int(id in [303,206]))
    u.mem_write(INFO+0x1104,struct.pack('<16I',*offered,*([0]*(16-len(offered)))));word(INFO+0x1144,17 if bad_count else len(offered))
    u.mem_write(PROFILE+0x52c,b'\xff'*0x100) # New/acknowledgement bits do not complete quests.
    protected=[(PROFILE,0x72c),(QUEST,0x100),(RESOURCE,0x100),(RECORDS,96),(PROGRESS,0x3e4),(ROWS,32),(DATA+0x30000,0x1000),(INFO+0x1104,68)]
    immutable=[bytes(u.mem_read(p,n))for p,n in protected]
    u.reg_write(arm.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(arm.UC_ARM_REG_FPEXC,0x40000000)
    tls_value=0;states={};colors={};calls=[];parent_return=0;parent_sp=0;heap=DATA+0xa0000
    constructing=None;factory_index=0
    allocations={};freed=[];created=[];drawn=[];object_attempts=0
    def allocate(size):
        nonlocal heap
        p=heap;heap=(p+size+31)&~15;allocations[p]=size;u.mem_write(p+size,b'\xa5'*16);return p
    def release(p):
        assert p not in freed,('double free',hex(p));freed.append(p)
        if p in allocations:assert bytes(u.mem_read(p+allocations[p],16))==b'\xa5'*16,('allocation overflow',hex(p))
    def ret(cpu,value=0):cpu.reg_write(arm.UC_ARM_REG_R0,value);cpu.reg_write(arm.UC_ARM_REG_PC,cpu.reg_read(arm.UC_ARM_REG_LR))
    def text(cpu,p):
        out=b''
        while len(out)<100:
            c=bytes(cpu.mem_read(p+len(out),1))
            if c==b'\0':return out.decode()
            out+=c
        raise AssertionError('unterminated string')
    def trace(cpu,address,size,_):
        nonlocal tls_value,parent_return,parent_sp,object_attempts,factory_index
        r=[cpu.reg_read(x)for x in REGS[:4]]
        if address==RETURN:cpu.emu_stop();return
        if address==MODULE+names['mwc_svc_query']:
            cpu.mem_write(r[0],struct.pack('<QQ6I',GAME,0x2000000,0,0,7,0,0,0));word(r[1],0);ret(cpu);return
        if address==imports.get('nnosGetTlsValue'):assert r[0]==1;ret(cpu,tls_value);return
        if address==imports.get('nnosSetTlsValue'):assert r[0]==1;tls_value=r[1];ret(cpu);return
        if address==imports.get('forge_mem_getMainTextAddr'):ret(cpu,GAME);return
        if address==imports.get('forge_singleton_getInstanceByName'):ret(cpu,{'sQuest':QUEST,'sUserInfo':PROFILE}.get(text(cpu,r[0]),0));return
        if address==ENGINE+4:
            assert r[:2]==[CONTROLLER,0 if invalid_info else INFO] and tls_value!=0
            parent_return=cpu.reg_read(arm.UC_ARM_REG_LR);parent_sp=cpu.reg_read(arm.UC_ARM_REG_SP)
            cpu.reg_write(arm.UC_ARM_REG_SP,parent_sp-16);cpu.mem_write(parent_sp-16,struct.pack('<4I',0,0,ROWS,0))
            for reg,value in zip(REGS[:4],[UI,0,2,0]):cpu.reg_write(reg,value)
            cpu.reg_write(arm.UC_ARM_REG_LR,ENGINE+8);cpu.reg_write(arm.UC_ARM_REG_PC,MODULE+names['kqm_row']);calls.append('parent');return
        if address==ENGINE+8:cpu.reg_write(arm.UC_ARM_REG_SP,parent_sp);cpu.reg_write(arm.UC_ARM_REG_PC,parent_return);return
        if address==ENGINE:
            sp=cpu.reg_read(arm.UC_ARM_REG_SP);assert r+list(struct.unpack('<3I',cpu.mem_read(sp,12)))==[UI,0,2,0,0,0,ROWS]
            calls.append('row-original');ret(cpu);return
        if address==GAME+0x546f28:assert r[0]==HOLDER;ret(cpu,gui_identity);return
        if address==GAME+0x7aef68:ret(cpu,DTI if r[0]==0x1b6313a3 else ROOT_DTI);return
        if address==GAME+0x1000:ret(cpu,DTI);return
        if address==GAME+0x1014:ret(cpu,ROOT_DTI);return
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
        if address==GAME+0x7aa47c:ret(cpu,ALLOCATOR);return
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
        if address==GAME+0xa4fb58:assert tuple(struct.unpack('<4f',cpu.mem_read(r[1],16)))==(136.,344.,198.,406.)
        if address==GAME+0xa47950:
            row=next(i for i,p in enumerate(parents) if read(r[0]+0x70)==p) if read(r[0]+0x70) else None
            if row is not None:states[row]=r[1]
        if address==GAME+0xa4e0b8:
            row=next(i for i,p in enumerate(parents) if read(r[0]+0x70)==p);assert r[2]<4
            colors[row]=read(r[1])
        if address in [GAME+0x1050,GAME+0x1054,GAME+0x1058,GAME+0xa4e628,GAME+0xa4fc9c,GAME+0xa4eddc]:
            if address in [GAME+0x1054,GAME+0xa4fc9c] and read(r[0]+0x50)==BADGE_ID:drawn.append(r[0])
            ret(cpu);return
        if address==GAME+0x523da4:assert r[0]==PROFILE+0x42c;ret(cpu,int(r[1]in completed));return
        if address==GAME+0x3b1a18:assert r[:2]==[QUEST,2];ret(cpu,int(prerequisites));return
        if address==GAME+0x3b2174:assert r[0]==QUEST;ret(cpu,int(available));return
        if ENGINE+0x300<=address<ENGINE+4096:raise AssertionError(('unexpected import',hex(address)))
    u.hook_add(unicorn.UC_HOOK_CODE,trace)
    def call(address,a=0,b=0):
        u.reg_write(arm.UC_ARM_REG_SP,STACK);u.reg_write(arm.UC_ARM_REG_LR,RETURN);u.reg_write(arm.UC_ARM_REG_R0,a);u.reg_write(arm.UC_ARM_REG_R1,b)
        u.emu_start(address,RETURN+4,count=1000000);assert u.reg_read(arm.UC_ARM_REG_SP)==STACK,(hex(u.reg_read(arm.UC_ARM_REG_PC)),hex(u.reg_read(arm.UC_ARM_REG_SP)))
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
    constructing=None
    if invalid_owner:word(read(DATA+0x2a000+8)+0x74,DATA+0x28000)
    if invalid_object:word(read(DATA+0x2a000+7*0x100+8)+0x50,99)
    call(MODULE+names['kqm_parent'],CONTROLLER,0 if invalid_info else INFO)
    assert tls_value==0 and calls==['parent','row-original']
    if fail_at:
        assert len(created)==fail_at-1 and not states and not colors
        call(MODULE+names['kqm_parent'],CONTROLLER,INFO) # Recover while retaining valid hidden native children.
        assert tls_value==0 and calls==['parent','row-original']*2
    assert [bytes(u.mem_read(p,n))for p,n in protected]==immutable
    for i in range(8):assert bytes(u.mem_read(DATA+0x2a000+i*0x100,48))==arrays[i]
    if invalid_object or invalid_owner or gui_identity!=5 or fail_object or fail_cache:
        assert not states and not colors
        assert all(read(root+0xa4)==old for root,old in zip(roots,original_caches))
        assert all(p in freed for p in allocations) # Failed preparation releases all unpublished allocations.
    else:
        assert len(created)==8 and len(allocations)==16
        assert all(p in freed for p in original_caches)
        if repeat:
            call(MODULE+names['kqm_parent'],CONTROLLER,0 if invalid_info else INFO);assert len(created)==8 and len(allocations)==16
        if invalid_info or ordinary or bad_count:assert states==dict.fromkeys(range(8),0) and not colors
        else:
            assert states==dict(enumerate([1,1,1,1,1,0,0,0]))
            urgency=0xff39d2ff if 303 in offered and available and prerequisites else 0xff808080
            assert colors=={0:0xff808080 if 207 in completed or alternative_done else 0xff2547e7,1:0xff808080,
                           2:0xff808080 if 303 in completed else urgency,3:0xff39d2ff if simultaneous and 206 in offered else 0xff808080,4:0xff808080}
        for p in created:
            assert read(p+0x74)==GUI_OWNER
            i=next(i for i,parent in enumerate(parents) if read(p+0x70)==parent)
            assert read(p+0x54)&1==states[i]
            if i in colors:assert struct.unpack('<4I',u.mem_read(p+0xa4,16))==(colors[i],)*4
            assert read(p+0x104)==ATLAS
            assert struct.unpack('<4f',u.mem_read(p+0x10c,16))==(136.,344.,198.,406.)
            assert struct.unpack('<2f',u.mem_read(p+0x80,8))==(-28.,8.)
            assert struct.unpack('<2f',u.mem_read(p+0xb4,8))==(24.,24.)
        for root in roots:call(GAME+0xa494a0,root,0x12345678)
        assert len(drawn)==sum(states.values()),('native draw walker omitted badge',drawn,states)
        for p,size in allocations.items():assert bytes(u.mem_read(p+size,16))==b'\xa5'*16,('native draw-cache overflow',hex(p))
        # Run the actual root and base-container destructors; the mocked MT free
        # records ownership, while their real ARM loops destroy the new children.
        for root in roots:call(GAME+0xa48668,root)
        assert all(p in freed for p in allocations),('native cleanup leaked new allocations',allocations,freed)
    CASES+=1;return {'case':label,'visible':states,'colors':colors,'native_draws':len(drawn),'ownership_cleanup':True,'saved_records_unchanged':True}
results=[test_case('all badge states and native draw traversal'),test_case('urgent inactive',offered=()),
         test_case('urgent unavailable',available=False),test_case('urgent prerequisites incomplete',prerequisites=False),
         test_case('viewing still red'),test_case('key completion',completed=(207,213)),test_case('urgent completion',completed=(303,213)),
         test_case('resource object mismatch',invalid_object=True),test_case('animation address is not the GUI owner',invalid_owner=True),test_case('no offer context',invalid_info=True),
         test_case('ordinary rows',ordinary=True),test_case('invalid offer count',bad_count=True),test_case('different GUI',gui_identity=4),
         test_case('satisfied alternative',alternative_done=True),test_case('simultaneous urgents',simultaneous=True,offered=(303,206)),
         test_case('secondary table',primary_count=16),test_case('both tables',primary_count=20),test_case('primary table empty',primary_count=0),
         test_case('object allocation failure',fail_object=True),test_case('cache allocation failure',fail_cache=True),
         test_case('repeated row update reuses native children',repeat=True),
         test_case('partial allocation failure recovers without duplicate children',fail_at=4)]
record('native-adapter.json',{'status':'PASSED','compiled_nro':True,'cases':CASES,'results':results,
          'native_animation_constructor':True,'native_texture_constructor':True,'native_style_texture_color_visibility_setters':True,'null_dti_placement_slot':True,'native_cache_allocator_and_free':True,'distinct_gui_owner':True,'native_draw_walker':True,'native_root_destructors':True,'archive_replacements':0,
          'thread_context_restored':True,'runtime_test':'NOT RUN','nro_sha256':digest(BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro')})
print('PASS: compiled native insertion, actual draw walker/destructors, colors and allocation rollback:',CASES,'cases')
