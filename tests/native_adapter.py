#!/usr/bin/env python3
"""Run the real ARM parent/row/adapter code against a native-shaped memory fixture.

Kernel/Forge/native callees are doubles. This proves the candidate reaches all
badge setters with resolved evidence; it is not a gameplay/rendering acceptance.
"""
import json,struct,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paths import BUILD_ROOT,CONFIG
from verify import symbols
from mhgu_binary import Nro
from build import record,digest
import unicorn
from unicorn import arm_const as arm
MODULE,ENGINE,RETURN,STACK,GAME,DATA=0x31000000,0x32000000,0x32000100,0x41010000,0x33000000,0x34000000
elf,names=symbols();data=(BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro').read_bytes();nro=Nro(data)
# Rust-private BASE remains identifiable in the demangled ELF symbol table.
demangled={}
for line in subprocess.check_output([Path(CONFIG['devkitarm'])/'bin/arm-none-eabi-nm','-C','-n',elf],text=True).splitlines():
    fields=line.split(maxsplit=2)
    if len(fields)==3:demangled[fields[2]]=int(fields[0],16)
base_symbol=demangled['key_quest_markers_rs::memory::BASE']

UI,HOLDER,CONTROLLER,INFO,PROFILE,QUEST,RESOURCE,RECORDS,PROGRESS,ROWS,DTI,VFT=(DATA+x for x in
    [0x1000,0x2000,0x3000,0x4000,0x10000,0x20000,0x21000,0x22000,0x23000,0x24000,0x25000,0x26000])
INSTANCE_ARRAY=DATA+0x27000
REGS=[getattr(arm,'UC_ARM_REG_R'+str(i))for i in range(13)]
CASES=0

def test_case(label, *, offered=(303,),completed=(213,),available=True,prerequisites=True,invalid_object=False,invalid_info=False,ordinary=False,bad_count=False,gui_identity=5,alternative_done=False,simultaneous=False):
    global CASES
    u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);u.ctl_set_cpu_model(arm.UC_CPU_ARM_MAX)
    u.mem_map(MODULE,((len(data)+4095)//4096+64)*4096);u.mem_write(MODULE,data)
    u.mem_map(ENGINE,4096);u.mem_map(0x41000000,0x20000);u.mem_map(GAME,0x2000000)
    import_targets={};next_import=ENGINE+0x300
    for name,entry,*_ in nro.symbols:
        if name and not entry[5]:import_targets[name.decode()]=next_import;next_import+=4
    rel_ranges=[]
    if 17 in nro.tags:rel_ranges.append((nro.tags[17],nro.tags[18]))
    if 23 in nro.tags:rel_ranges.append((nro.tags[23],nro.tags[2]))
    for start,length in rel_ranges:
        for at in range(start,start+length,8):
            dest,info=struct.unpack_from('<II',data,at);kind=info&255;sym=info>>8
            value=struct.unpack('<I',u.mem_read(MODULE+dest,4))[0]
            if kind==23:value+=MODULE
            elif kind in [2,21,22]:
                name,e,*_=nro.symbols[sym]
                address=MODULE+e[1] if e[5] else import_targets.get(name.decode(),0)
                value=(value if kind==2 else 0)+address
            else:raise AssertionError(('relocation',kind))
            u.mem_write(MODULE+dest,struct.pack('<I',value&0xffffffff))
    def word(p,v):u.mem_write(p,struct.pack('<I',v))
    word(MODULE+base_symbol,GAME);word(MODULE+names['kqm_original'],ENGINE)
    word(MODULE+names['kqm_parent_original'],ENGINE+4)
    word(MODULE+names['kqm_tls_slot'],1);u.mem_write(MODULE+names['kqm_active'],b'\x01')
    word(CONTROLLER+0x54,UI);word(UI+0x24,HOLDER);word(HOLDER,VFT+0x100);word(VFT+0x1ac,GAME+0x1010);word(HOLDER+0x298,63);word(HOLDER+0xf8,INSTANCE_ARRAY)
    for i in range(8):
        instance=DATA+0x28000+i*0x200;objects=DATA+0x2a000+i*0x100;badge=DATA+0x2c000+i*0x200
        word(INSTANCE_ARRAY+(16+i)*4,instance);word(instance+0xd8,objects);word(objects+12*4,badge)
        word(badge,VFT);word(badge+0x50,99 if invalid_object and i==7 else 21)
    word(VFT+0x14,GAME+0x1000)
    word(QUEST+0xb4,RESOURCE);word(RESOURCE+0x64,8);word(RESOURCE+0x6c,RECORDS)
    groups=[(207,2,int(alternative_done)),(105,1,0),(303,26,0),(206,25,0),(213,2,int(alternative_done)),(202,0,0),(402,27,0),(215,2,0)]
    if simultaneous:groups[3]=(206,26,0)
    for i,(id,category,alt)in enumerate(groups):u.mem_write(RECORDS+i*12,struct.pack('<IIBBBB',0,id,category,alt,0,0))
    word(GAME+0x18979f0,PROGRESS);u.mem_write(PROGRESS+0x3e0,struct.pack('<HH',2,1))
    ids=[207,105,303,206,213,202,0,402]
    if ordinary:ids=[202]*8
    for i,id in enumerate(ids):
        quest_data=DATA+0x30000+i*0x200
        word(ROWS+i*4,quest_data if id else 0)
        word(quest_data+8,id);u.mem_write(quest_data+0x10c,struct.pack('<H',int(id in [303,206])))
    u.mem_write(INFO+0x1104,struct.pack('<16I',*offered,*([0]*(16-len(offered)))))
    word(INFO+0x1144,17 if bad_count else len(offered))
    # Acknowledgement bits are all one, but completion is supplied separately.
    # The compiled adapter must still keep quest 207 red when merely viewed.
    u.mem_write(PROFILE+0x52c,b'\xff'*0x100)
    initial_game=bytes(u.mem_read(DATA,0x32000))
    u.reg_write(arm.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(arm.UC_ARM_REG_FPEXC,0x40000000)
    u.reg_write(arm.UC_ARM_REG_SP,STACK);u.reg_write(arm.UC_ARM_REG_LR,RETURN)
    u.reg_write(arm.UC_ARM_REG_R0,CONTROLLER);u.reg_write(arm.UC_ARM_REG_R1,0 if invalid_info else INFO)
    tls_value=0;states={};colors={};calls=[];parent_return=0;parent_sp=0
    def ret(cpu,value=0):
        cpu.reg_write(arm.UC_ARM_REG_R0,value);cpu.reg_write(arm.UC_ARM_REG_PC,cpu.reg_read(arm.UC_ARM_REG_LR))
    def cstring(cpu,p):
        out=b''
        while len(out)<100:
            b=bytes(cpu.mem_read(p+len(out),1))
            if b==b'\0':return out.decode()
            out+=b
        raise AssertionError('unterminated fixture string')
    def trace(cpu,address,size,_):
        nonlocal tls_value,parent_return,parent_sp
        r=[cpu.reg_read(x)for x in REGS[:4]]
        if address==RETURN:cpu.emu_stop();return
        if address==MODULE+names['mwc_svc_query']:
            # Query the fixture's game mapping; output layout matches Horizon.
            cpu.mem_write(r[0],struct.pack('<QQ6I',GAME,0x2000000,0,0,7,0,0,0));word(r[1],0);ret(cpu);return
        if address==import_targets.get('nnosGetTlsValue'):assert r[0]==1;ret(cpu,tls_value);return
        if address==import_targets.get('nnosSetTlsValue'):assert r[0]==1;tls_value=r[1];ret(cpu);return
        if address==import_targets.get('forge_mem_getMainTextAddr'):ret(cpu,GAME);return
        if address==import_targets.get('forge_singleton_getInstanceByName'):
            ret(cpu,{'sQuest':QUEST,'sUserInfo':PROFILE}.get(cstring(cpu,r[0]),0));return
        if address==ENGINE+4:
            assert r[:2]==[CONTROLLER,0 if invalid_info else INFO];assert tls_value!=0
            parent_return=cpu.reg_read(arm.UC_ARM_REG_LR);parent_sp=cpu.reg_read(arm.UC_ARM_REG_SP)
            cpu.reg_write(arm.UC_ARM_REG_SP,parent_sp-16);cpu.mem_write(parent_sp-16,struct.pack('<4I',0,0,ROWS,0))
            for reg,value in zip(REGS[:4],[UI,0,2,0]):cpu.reg_write(reg,value)
            cpu.reg_write(arm.UC_ARM_REG_LR,ENGINE+8);cpu.reg_write(arm.UC_ARM_REG_PC,MODULE+names['kqm_row']);calls.append('parent');return
        if address==ENGINE+8:
            cpu.reg_write(arm.UC_ARM_REG_SP,parent_sp);cpu.reg_write(arm.UC_ARM_REG_PC,parent_return);return
        if address==ENGINE:
            sp=cpu.reg_read(arm.UC_ARM_REG_SP);args=r+list(struct.unpack('<3I',cpu.mem_read(sp,12)))
            assert args==[UI,0,2,0,0,0,ROWS];calls.append('row-original');ret(cpu);return
        if address==GAME+0x546f28:assert r[0]==HOLDER;ret(cpu,gui_identity);return
        if address in [GAME+0x7aef68,GAME+0x1000]:ret(cpu,DTI);return
        if address==GAME+0x523da4:assert r[0]==PROFILE+0x42c;ret(cpu,int(r[1]in completed));return
        if address==GAME+0x3b1a18:assert r[:2]==[QUEST,2];ret(cpu,int(prerequisites));return
        if address==GAME+0x3b2174:assert r[0]==QUEST;ret(cpu,int(available));return
        if address in [GAME+0x56e530,GAME+0x56e6fc]:
            assert r[0]==UI and 16<=r[1]<24 and r[2]==12 and 'row-original'in calls
            row=r[1]-16
            if address==GAME+0x56e530:states[row]=r[3]
            else:colors[row]=r[3]
            ret(cpu);return
        if ENGINE+0x300<=address<ENGINE+4096:raise AssertionError(('unexpected native import',hex(address),[n for n,a in import_targets.items()if a==address]))
    u.hook_add(unicorn.UC_HOOK_CODE,trace)
    u.emu_start(MODULE+names['kqm_parent'],RETURN+4,count=250000)
    assert tls_value==0 and u.reg_read(arm.UC_ARM_REG_SP)==STACK and calls==['parent','row-original']
    assert bytes(u.mem_read(DATA,0x32000))==initial_game # No saved progression/acknowledgement writes.
    if invalid_object or gui_identity!=5:assert not states and not colors
    elif invalid_info or ordinary or bad_count:assert states==dict.fromkeys(range(8),0) and not colors
    else:
        assert states==dict(enumerate([1,1,1,1,1,0,0,0]))
        expected_urgent=0xff39d2ff if 303 in offered and available and prerequisites else 0xff808080
        assert colors=={0:0xff808080 if 207 in completed or alternative_done else 0xff2547e7,1:0xff808080,
                        2:0xff808080 if 303 in completed else expected_urgent,3:0xff39d2ff if simultaneous and 206 in offered else 0xff808080,4:0xff808080}
    CASES+=1;return {'case':label,'visible':states,'colors':colors,'saves_unchanged':True}
results=[test_case('current key, obsolete key, active urgent, inactive urgent, completed, ordinary, unused, conflict'),
         test_case('urgent inactive',offered=()),test_case('urgent unavailable',available=False),
         test_case('urgent prerequisites incomplete',prerequisites=False),test_case('viewing still red'),
         test_case('key completion observed',completed=(207,213)),test_case('urgent completion observed',completed=(303,213)),
         test_case('resource object mismatch',invalid_object=True),test_case('counter transition has no context',invalid_info=True),
         test_case('ordinary rows replace old badges',ordinary=True),
         test_case('invalid offered count',bad_count=True),test_case('different GUI set',gui_identity=4),
         test_case('satisfied alternative becomes grey',alternative_done=True),
         test_case('simultaneous offered urgents',simultaneous=True,offered=(303,206))]
record('native-adapter.json',{'status':'PASSED','compiled_nro':True,'cases':CASES,'results':results,
          'callback_path':'parent -> native original -> row -> original row -> native adapter -> native setters',
          'thread_context_restored':True,'runtime_test':'NOT RUN','nro_sha256':digest(BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro')})
print('PASS: compiled active parent/row callbacks, resolved native badge states and scoped TLS:',CASES,'cases')
