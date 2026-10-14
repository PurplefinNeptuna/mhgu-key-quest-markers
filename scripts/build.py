#!/usr/bin/env python3
"""Offline standalone candidate build. No command installs or starts a game."""
import argparse, hashlib, json, os, shutil, subprocess, sys, zipfile, zlib
from html import escape
from pathlib import Path
from paths import MOD, ROOT, CONFIG, BUILD_ROOT, WORK_ROOT, CARGO_TARGET, PYTHON, input_path
from gui_badge import extend, verify as verify_gui
from mhgu_assets import read_arc, repack

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def source_hashes():
    """Tie receipts to the exact owned executable/resource recipe inputs."""
    files=['Cargo.toml','Cargo.lock','.cargo/config.toml','armv7a-none-eabi.json','build.rs','scripts/gui_badge.py']
    files += [str(p.relative_to(MOD)) for folder in ['src','core/src','link']
              for p in sorted((MOD/folder).rglob('*')) if p.is_file()]
    return {n:digest(MOD/n) for n in files}
def record(name, value):
    BUILD_ROOT.mkdir(parents=True, exist_ok=True)
    (BUILD_ROOT/name).write_text(json.dumps(value,indent=2)+'\n')
def run(args, **kw): subprocess.run(list(map(str,args)),check=True,**kw)
def environment():
    env=os.environ.copy();runtime=ROOT/'tools/mhgu-dti-dumper'
    rust=Path(CONFIG.get('rust_bin',runtime/'rustup/toolchains/nightly-x86_64-unknown-linux-gnu/bin'))
    compiler=CONFIG.get('devkitarm') or env.get('DEVKITARM')
    if not compiler: raise ValueError('Set devkitarm in build.local.json or DEVKITARM')
    env.update(CARGO_HOME=str(CONFIG.get('cargo_home',runtime/'cargo')), RUSTUP_HOME=str(runtime/'rustup'),
               RUSTUP_TOOLCHAIN='nightly',RUSTC=str(rust/'rustc'),CARGO_NET_OFFLINE='true',
               DEVKITARM=str(compiler),CARGO_TARGET_DIR=str(CARGO_TARGET))
    env['PATH']=os.pathsep.join([str(rust),str(Path(compiler)/'bin'),env.get('PATH','')])
    return env,rust

def converter(): return Path(CONFIG.get('cargo_forge',ROOT/'tools/mhgu-dti-dumper/cargo/bin/cargo-forge'))
def doctor():
    env,rust=environment();lock=json.loads((MOD/'dependencies.lock.json').read_text())
    version=subprocess.check_output([rust/'rustc','--version'],env=env,text=True).strip()
    if version!=lock['rust_version']: raise ValueError('Pinned Rust version differs')
    pinned_tools=[('rustc',rust/'rustc'),('cargo_forge',converter())]
    pinned_tools.extend((name,Path(CONFIG.get('devkitarm',env['DEVKITARM']))/'bin'/name)
                        for name in lock['tool_sha256'] if name.startswith('arm-none-eabi-'))
    for n,p in pinned_tools:
        if digest(p)!=lock['tool_sha256'][n]: raise ValueError('Pinned tool differs: '+n)
    for n,h in lock['files'].items():
        if digest(MOD/n)!=h: raise ValueError('Pinned source differs: '+n)
    for n,h in lock['inputs'].items():
        if digest(input_path(n))!=h: raise ValueError('Supplied native/resource input differs: '+n)
    if digest(rust.parent/'lib/rustlib/src/rust/library/Cargo.lock')!=digest(MOD/'research/sysroot-Cargo.lock'):
        raise ValueError('Pinned rust-src resolver differs')
    print('PASS: pinned Rust, Forge sources, registry sources and copied inputs')

def prepare():
    doctor()
    source=input_path('common_eng.arc');blob,entries=read_arc(source)
    keys=[k for k in entries if k[0]=='eng\\GUI\\05_meeting_p\\count\\counter']
    if len(keys)!=1: raise ValueError('Missing/ambiguous counter GUI')
    key=keys[0];patched=extend(entries[key]['data'])
    selected={k:('HD',e) for k,e in entries.items()}
    replacement=dict(entries[key]);replacement.update(data=patched,packed=zlib.compress(patched,9))
    selected[key]=('native-badge',replacement)
    result=repack(blob,entries,selected)
    target=BUILD_ROOT/'package/romfs/nativeNX/eng/arc/village/common_eng.arc'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
    _,again=read_arc(target)
    if again.keys()!=entries.keys(): raise ValueError('ARC resource inventory changed')
    verify_gui(entries[key]['data'],again[key]['data'])
    for k in entries:
        if k!=key and (entries[k]['data']!=again[k]['data'] or entries[k]['packed']!=again[k]['packed']):
            raise ValueError('Unrelated resource changed: '+str(k))
    record('resource.json',{'status':'PASSED','source_sha256':digest(source),'archive_sha256':digest(target),
           'gui_sha256':hashlib.sha256(patched).hexdigest(),'resource':list(key),'resources':len(entries),
           'changed_resources':1,'old_gui_bytes':len(entries[key]['data']),'new_gui_bytes':len(patched),
           'existing_row_sequences':15,'badge_slot':12,'badge_id':21,'texture_id':22,
           'new_atlas':False,'vertex_buffer_preserved':True,'attachment_runtime':'NOT VERIFIED'})

def build():
    prepare();env,_=environment();lock=digest(MOD/'Cargo.lock')
    link=MOD/'target';output=MOD/'key_quest_markers_rs.nro'
    if link.exists() or link.is_symlink() or output.exists(): raise ValueError('Preserving existing target/ or loose NRO')
    CARGO_TARGET.mkdir(parents=True,exist_ok=True);link.symlink_to(CARGO_TARGET,target_is_directory=True)
    try: run([converter(),'forge','build','--release'],cwd=MOD,env=env)
    finally:
        link.unlink()
        if output.exists(): shutil.move(output,CARGO_TARGET/output.name)
    if digest(MOD/'Cargo.lock')!=lock: raise ValueError('Cargo.lock changed during build')
    dest=BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro'
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(CARGO_TARGET/output.name,dest)
    record('build.json',{'status':'BUILT','nro_sha256':digest(dest),'forge_rs_revision':
        'd1865b68e9b194eb3eacc8bd71bbf601a5fac63e','verified_contract':0,'source_sha256':source_hashes(),'runtime_test':'NOT RUN'})

def test():
    env,rust=environment()
    for manifest in ['core/Cargo.toml','tests/hooks-harness/Cargo.toml']:
        run([rust/'cargo','test','--locked','--config',MOD/'.cargo/vendor.toml','--manifest-path',MOD/manifest,
             '--target','x86_64-unknown-linux-gnu'],cwd=MOD.parent,env=env)
    run([PYTHON,MOD/'tests/resource.py'])
    run([CONFIG.get('arm_python',ROOT/'tools/mwc-analysis-venv/bin/python'),MOD/'tests/arm.py'])
    verify();record('tests.json',{'status':'PASSED','nro_sha256':digest(BUILD_ROOT/'package/romfs/nativeNX/plugins/key_quest_markers_rs.nro'),
                     'resource_sha256':digest(BUILD_ROOT/'package/romfs/nativeNX/eng/arc/village/common_eng.arc'),
                     'host':True,'resource':True,'arm':True,'runtime_test':'NOT RUN'})
def verify(): run([PYTHON,MOD/'scripts/verify.py'])
def package():
    verify();source=BUILD_ROOT/'package';nro=source/'romfs/nativeNX/plugins/key_quest_markers_rs.nro'
    test_record=json.loads((BUILD_ROOT/'tests.json').read_text())
    if test_record['status']!='PASSED' or test_record['nro_sha256']!=digest(nro) or test_record.get('resource_sha256')!=digest(source/'romfs/nativeNX/eng/arc/village/common_eng.arc'): raise ValueError('Test this exact build first')
    dest=BUILD_ROOT/'delivery';dest.mkdir(parents=True,exist_ok=True)
    payloads={str(p.relative_to(source)):digest(p) for p in source.rglob('*') if p.is_file()}
    named=dest/'key-quest-markers-rs'
    previous={str(p.relative_to(named)) for p in named.rglob('*') if p.is_file()}
    if previous-payloads.keys(): raise ValueError('Preserving unexpected previous candidate files')
    shutil.copytree(source,named,dirs_exist_ok=True)
    guide=(MOD/'DISTRIBUTION_README.md').read_bytes();(dest/'README.md').write_bytes(guide)
    archive=dest/'key-quest-markers-rs-r1-candidate.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('README.md',guide)
        for n in sorted(payloads): z.write(source/n,'key-quest-markers-rs/'+n)
    import mod_distribution as distribution
    spec=json.loads((MOD/'DISTRIBUTION.json').read_text())
    (dest/'README.html').write_bytes(distribution.readme_html(guide))
    (dest/'GAMEBANANA_README.html').write_bytes(distribution.gamebanana_readme_html(guide,spec['gamebanana']))
    notices='\n\n'.join((MOD/n).read_text() for n in ['DISTRIBUTION_NOTICES.md','LICENSE','vendor/forge-rs/LICENSE',
        'vendor/libnx/LICENSE-MIT','licenses/FORGE-MIT.txt','vendor/crates/log-0.4.34/LICENSE-MIT','licenses/RUST-MIT.txt','licenses/COMPILER_BUILTINS.txt'])
    (dest/'NOTICES.txt').write_text(notices);(dest/'NOTICES.html').write_text('<pre>'+escape(notices)+'</pre>\n')
    evidence={n:json.loads((BUILD_ROOT/(n+'.json')).read_text()) for n in ['resource','build','arm','verify','tests']}
    (dest/'VALIDATION.json').write_text(json.dumps(evidence,indent=2)+'\n')
    manifest={'mod':'key-quest-markers-rs','version':'r1','status':'DEVELOPMENT','runtime_test':'NOT RUN',
              'runtime_active':False,'package_name':'key-quest-markers-rs','payloads':payloads,'archive_sha256':digest(archive)}
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (dest/'SHA256SUMS').write_text(''.join(digest(p)+'  '+str(p.relative_to(dest))+'\n'
                 for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='SHA256SUMS'))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and z.read('README.md')==guide
        assert set(z.namelist())=={'README.md',*('key-quest-markers-rs/'+n for n in payloads)}
        for n,h in payloads.items(): assert hashlib.sha256(z.read('key-quest-markers-rs/'+n)).hexdigest()==h==digest(named/n)
    for line in (dest/'SHA256SUMS').read_text().splitlines():
        h,n=line.split('  ',1);assert digest(dest/n)==h
    print('Verified inactive DEVELOPMENT candidate:',archive)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['doctor','prepare','build','test','verify','package','export'])
    p.add_argument('--output',type=Path);a=p.parse_args()
    if a.command=='export':
        if a.output is None: p.error('export requires --output')
        run([PYTHON,MOD/'scripts/export_source.py','--output',a.output])
    else: globals()[a.command]()
if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as e:print(e,file=sys.stderr);sys.exit(1)
