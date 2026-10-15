#!/usr/bin/env python3
"""Execute the compiled NRO's typed detour and version handshake with native-call doubles.

This checks the ARM calling convention, not Forge or in-game UI execution.
"""
import json,struct,subprocess,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from paths import VERSION, MOD,BUILD_ROOT,WORK_ROOT,CONFIG,input_path
from verify import symbols
from mhgu_binary import Nro,main_image
from build import record
import unicorn
from unicorn import arm_const as arm
MODULE,ENGINE,RETURN,STACK=0x31000000,0x32000000,0x32000100,0x41010000
elf,names=symbols();data=(BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers.nro').read_bytes();nro=Nro(data)
regs=[getattr(arm,'UC_ARM_REG_R'+str(i)) for i in range(13)]
ds=[getattr(arm,'UC_ARM_REG_D'+str(i)) for i in range(32)]
def machine():
    u=unicorn.Uc(unicorn.UC_ARCH_ARM,unicorn.UC_MODE_ARM);u.ctl_set_cpu_model(arm.UC_CPU_ARM_MAX)
    u.mem_map(MODULE,((len(data)+4095)//4096+64)*4096);u.mem_write(MODULE,data)
    # Apply local ARM ELF REL relocations, as the loader would. External imports
    # are unused in this pass-through fixture and intentionally remain unresolved.
    if 17 in nro.tags:
        for at in range(nro.tags[17],nro.tags[17]+nro.tags[18],8):
            dest,info=struct.unpack_from('<II',data,at);kind=info&255;sym=info>>8
            value=struct.unpack('<I',u.mem_read(MODULE+dest,4))[0]
            if kind==23:value+=MODULE
            elif kind in [2,21,22]:
                e=nro.symbols[sym][1]
                if not e[5]:continue
                value=(value if kind==2 else 0)+MODULE+e[1]
            else:raise AssertionError('Unsupported relocation: '+str(kind))
            u.mem_write(MODULE+dest,struct.pack('<I',value&0xffffffff))
    u.mem_map(ENGINE,4096);u.mem_write(ENGINE,struct.pack('<I',0xe12fff1e));u.mem_map(0x41000000,0x20000)
    u.reg_write(arm.UC_ARM_REG_C1_C0_2,0xf00000);u.reg_write(arm.UC_ARM_REG_FPEXC,0x40000000)
    u.reg_write(arm.UC_ARM_REG_SP,STACK);u.reg_write(arm.UC_ARM_REG_LR,RETURN)
    return u
checks=0
for ge in range(16):
    u=machine();values=[0x11220000+i*257 for i in range(7)]
    for i,r in enumerate(regs):u.reg_write(r,0x22440000+i*257)
    for i,r in enumerate(ds):u.reg_write(r,0x40010000abcd0000+i)
    initial_regs=[u.reg_read(r) for r in regs];initial_d=[u.reg_read(r) for r in ds]
    for i in range(4):u.reg_write(regs[i],values[i])
    u.reg_write(arm.UC_ARM_REG_CPSR,0xa8000013|(ge<<16))
    stack=struct.pack('<3I',*values[4:])+bytes(range(52));u.mem_write(STACK,stack)
    u.mem_write(MODULE+names['kqm_original'],struct.pack('<I',ENGINE))
    u.mem_write(MODULE+names['kqm_active'],b'\0')
    calls=[]
    def trace(cpu,address,size,_):
        if address==RETURN:cpu.emu_stop();return
        if address!=ENGINE:return
        sp=cpu.reg_read(arm.UC_ARM_REG_SP);assert sp%8==0
        actual=[cpu.reg_read(r) for r in regs[:4]]+list(struct.unpack('<3I',cpu.mem_read(sp,12)))
        assert actual==values and cpu.reg_read(arm.UC_ARM_REG_CPSR)&0xf0000==ge<<16
        calls.append(actual)
        # A native AAPCS callee may clobber r0-r3,r12,d0-d7,d16-d31 and flags.
        # Keep its own callee-saved registers, so any detour corruption is visible.
        for r in regs[:4]+[regs[12]]:cpu.reg_write(r,0xdeadbeef)
        for r in ds[:8]+ds[16:]:cpu.reg_write(r,0x7ff10000ffff0000)
        cpsr=cpu.reg_read(arm.UC_ARM_REG_CPSR);cpu.reg_write(arm.UC_ARM_REG_CPSR,(cpsr&~0xf80f0000)|0x58000000|((15-ge)<<16))
    u.hook_add(unicorn.UC_HOOK_CODE,trace)
    u.emu_start(MODULE+names['kqm_row'],RETURN+4,count=1500)
    assert len(calls)==1 and u.reg_read(arm.UC_ARM_REG_SP)==STACK
    assert bytes(u.mem_read(STACK,64))==stack
    assert [u.reg_read(r) for r in regs[4:12]]==initial_regs[4:12]
    assert [u.reg_read(r) for r in ds[8:16]]==initial_d[8:16]
    checks+=1
# Verify the complete native registration record, name and canaries.
u=machine();params=ENGINE+0x200;u.reg_write(arm.UC_ARM_REG_R0,params);u.mem_write(params-8,b'\xa5'*86)
u.emu_start(MODULE+names['forge_onLoad'],RETURN,count=1000)
assert struct.unpack('<3H',u.mem_read(params,6))==(1,5,1)
assert bytes(u.mem_read(params+6,64)).rstrip(b'\0')==('Key Quest Markers '+VERSION).encode()
assert bytes(u.mem_read(params-8,8))==bytes(u.mem_read(params+70,8))==b'\xa5'*8
# Compile the native header's struct without SDK includes; compiler-derived
# offsets independently agree with the production Rust compile-time assertions.
folder=WORK_ROOT/'abi';folder.mkdir(parents=True,exist_ok=True)
header=(MOD/'research/native-hook.h').read_text();hook=re.search(r'typedef struct Hook \{.*?\} Hook;',header,re.S).group()
(folder/'native.cpp').write_text('#include <stdint.h>\n#include <stddef.h>\n'+hook+'\n'
    'static_assert(sizeof(Hook)==24 && alignof(Hook)==4 && offsetof(Hook,context)==12 && offsetof(Hook,ctx_cell)==16 && offsetof(Hook,has_ctx)==20);\n')
compiler=Path(CONFIG['devkitarm'])/'bin'
subprocess.run([compiler/'arm-none-eabi-g++','-std=c++17','-marm','-mfloat-abi=soft','-c',folder/'native.cpp','-o',folder/'native.o'],check=True)
# Direct caller continuations overwrite NZCVQ before conditional use; none uses
# GE-dependent SEL before its next call/return. Retain windows for review.
image,_=main_image(input_path('main').read_bytes());binary=WORK_ROOT/'main-image.bin';binary.write_bytes(image)
windows={}
for at,size in [(0x616c00,48),(0x618bc0,40),(0x618cbc,28),(0x782bb4,4),(0x782e04,32),(0x6e3f68,28)]:
    text=subprocess.check_output([compiler/'arm-none-eabi-objdump','-D','-b','binary','-m','arm',
        '--start-address='+str(at),'--stop-address='+str(at+size),binary],text=True)
    assert '\tsel\t' not in text;windows[hex(at)]=text.split('Disassembly of section .data:')[-1].strip()
record('arm.json',{'status':'PASSED','typed_detour_cases':checks,'forwarded_integer_arguments':7,
        'registered_name':'Key Quest Markers '+VERSION,'metadata_bytes':70,'hook_abi_bytes':24,'minimum_forge_version':'1.5.1','GE':'unchanged before original in all 16 patterns; no restoration required at audited direct continuations',
        'preserved':['r4-r11','d8-d15','sp','incoming stack words'],'direct_caller_windows':windows,
        'live_flags':'Row and parent direct callers replace NZCVQ before conditional use or make an unconditional next call; no incoming GE consumer',
        'runtime_test':'NOT RUN','resource_attachment':'NOT VERIFIED'})
print('PASS: compiled seven-argument forwarding, callee-saved state, version handshake and native Hook ABI')
