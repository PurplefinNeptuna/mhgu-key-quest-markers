from paths import MOD, SCRIPTS, FORGE, DEPS, PYTHON, CONTAINER_STORAGE, input_path
#!/usr/bin/env python3
"""Build/test the exact-build key-title candidate. Never installs or launches."""
import argparse
from collections import Counter
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import zipfile



import key_quest_research as research
import mhgu_binary as prior
from mhgu_binary import Nro
from mhgu_binary import nso_segments

from paths import ROOT, MOD, SCRIPTS, FORGE, DEPS, PYTHON, CONTAINER_STORAGE, input_path
RECIPE = MOD
WORK = ROOT / 'work/key-quest-markers'
OUT = ROOT / 'build/key-quest-markers'
MAIN = input_path('main')
LOADS = {'configured': None}
CALLBACKS = {'forge_onLoad', 'forge_onInit', 'forge_onUpdate', 'forge_onImGuiInit',
             'forge_onImGuiRender', 'forge_onImGuiFreeRender', 'kqm_active_v1', 'init', 'fini'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def run(args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def acceptance_for(payload, path=None):
    """Attach human runtime acceptance only to the identical tested payload."""
    path = path or RECIPE / 'RUNTIME_RESULTS.json'
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    if record.get('nro_sha256') != sha(payload) or record.get('status') != 'USER_ACCEPTED':
        return None
    if not all(record.get('emulators', {}).get(name, {}).get('status') == 'USER_PASSED'
               for name in ('Eden', 'Ryujinx')):
        return None
    return record


def nso_exports(data):
    """Read the actual ARM32 MOD0 dynamic table after segment hash validation."""
    segments = nso_segments(data)
    image = bytearray(max(s['address'] + s['size'] for s in segments))
    lib = ctypes.CDLL(ctypes.util.find_library('lz4'))
    lib.LZ4_decompress_safe.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
    flags = struct.unpack_from('<I', data, 12)[0]
    for i, segment in enumerate(segments):
        offset = struct.unpack_from('<I', data, 16 + 16 * i)[0]
        packed_size = struct.unpack_from('<I', data, 96 + 4 * i)[0]
        packed = data[offset:offset + packed_size]
        if flags & (1 << i):
            buf = ctypes.create_string_buffer(segment['size'])
            if lib.LZ4_decompress_safe(packed, buf, len(packed), segment['size']) != segment['size']:
                raise ValueError('NSO decompression changed')
            packed = buf.raw
        image[segment['address']:segment['address'] + segment['size']] = packed
    def span(offset, count):
        if offset < 0 or count < 0 or offset + count > len(image):
            raise ValueError('NSO dynamic metadata out of bounds')
        return image[offset:offset + count]
    def u32(offset):
        return struct.unpack('<I', span(offset, 4))[0]
    mod = u32(4)
    if span(mod, 4) != b'MOD0':
        raise ValueError('Unsupported Forge MOD0')
    dynamic = mod + struct.unpack('<i', span(mod + 4, 4))[0]
    tags = {}
    for i in range(128):
        tag, value = struct.unpack('<II', span(dynamic + i * 8, 8))
        if not tag:
            break
        if tag in tags:
            raise ValueError('Repeated dynamic tag')
        tags[tag] = value
    else:
        raise ValueError('Unterminated dynamic table')
    if not {4, 5, 6, 10, 11} <= tags.keys() or tags[11] != 16:
        raise ValueError('Unsupported Forge dynamic symbol format')
    buckets, count = struct.unpack('<II', span(tags[4], 8))
    span(tags[4], 8 + (buckets + count) * 4)
    symbols = span(tags[6], count * 16)
    names = bytes(span(tags[5], tags[10]))
    exports = set()
    for offset in range(0, len(symbols), 16):
        name, _, _, info, _, section = struct.unpack_from('<IIIBBH', symbols, offset)
        if name >= len(names) or names.find(b'\0', name) < 0:
            raise ValueError('Invalid Forge symbol name')
        if section and info >> 4 in (1, 2):
            exports.add(names[name:names.index(b'\0', name)].decode('ascii'))
    return exports


def snapshot():
    from paths import check_dependencies
    from native_support import snapshot
    check_dependencies()
    return snapshot()


def prepare():
    image, _ = prior.main_image(MAIN.read_bytes())
    quests, groups = research.local_inventory(WORK / 'inputs')
    comparison = research.compare(quests, WORK / 'research/kiranico-quest.html')
    if comparison['key_count'] != 118 or groups['count'] != 1509:
        raise ValueError('Verified quest inventory changed')
    maxima, counts = {}, Counter()
    for arc in ('vq', 'gq', 'gq2'):
        _, entries = research.read_arc(WORK / f'inputs/loc/arc/quest/{arc}.arc')
        for (name, kind), entry in entries.items():
            match = re.fullmatch(r'(eng|fre|ger|ita|spa|chS|chT)\\quest\\questData\\questData_\d{7}_\1', name)
            if not match:
                continue
            if kind != 0x242BB29A:
                raise ValueError('Unexpected quest title resource type')
            text = research.quest_title(entry['data']).encode('utf-8')
            language = match[1]
            counts[language] += 1
            maxima[language] = max(maxima.get(language, 0), len(text))
    if set(counts) != {'eng', 'fre', 'ger', 'ita', 'spa', 'chS', 'chT'}:
        raise ValueError('Incomplete localized title sizing')
    slot_bytes = max(256, max(maxima.values()) + 7)
    # Genuine ELF note header, GNU name and complete nonzero NSO descriptor.
    note = struct.pack('<III', 4, 16, 3) + b'GNU\0' + bytes.fromhex(prior.BUILD_ID)[:16]
    if image.count(note) != 1:
        raise ValueError('Missing/ambiguous GNU build-ID note')
    offsets = [0x3b57d0, 0x39bd1c, image.index(note)]
    if image[offsets[0]:offsets[0] + 8].hex() != '10402de90040a0e1':
        raise ValueError('Unexpected getter prologue')
    header = ['#pragma once', '#include <stdint.h>', 'namespace kqm {',
              f'constexpr unsigned title_slot_bytes = {slot_bytes};',
              'constexpr uint32_t name_getter_offset = 0x003b57d0;',
              'constexpr uint32_t group_getter_offset = 0x0039bd1c;',
              'struct Signature { uint32_t offset; uint8_t bytes[32]; };',
              'static constexpr Signature signatures[] = {']
    for offset in offsets:
        header.append('    {0x%x, {%s}},' % (offset, ','.join('0x%02x' % x for x in image[offset:offset + 32])))
    header += ['};', '}']
    expected = '\n'.join(header) + '\n'
    path = RECIPE / 'src/game_signatures.h'
    if path.exists() and path.read_text() != expected:
        raise ValueError('Pinned source signatures/title sizing differ; review before replacement')
    if not path.exists():
        path.write_text(expected)
    report = {'source_sha256': sha(MAIN.read_bytes()), 'build_id': prior.BUILD_ID,
              'signatures': [{'offset': hex(o), 'bytes': image[o:o + 32].hex()} for o in offsets],
              'title_slot_bytes': slot_bytes, 'localized_title_counts': dict(counts),
              'maximum_title_utf8_bytes': maxima, 'keys': 118, 'quest_group': groups,
              'key_ids': sorted({q['id'] for q in quests if q['key']}),
              'kiranico_html_sha256': comparison['html_sha256'],
              'runtime_classification': 'live quest group; no embedded quest ID list'}
    write_json(OUT / 'input-validation.json', report)
    # Host fixture contains serialized input facts only, and remains ignored.
    fixture = WORK / 'native-group-fixture.bin'
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture_data = (WORK / 'research/quest_group.qsg').read_bytes()
    if sha(fixture_data) != groups['resource_sha256']:
        raise ValueError('Host fixture differs from validated ARC resource')
    fixture.write_bytes(fixture_data)
    print(f'118 keys verified; {sum(counts.values())} localized titles; {slot_bytes}-byte slots')
    return report


def test():
    prepare()
    results = []
    tests = WORK / 'tests'
    tests.mkdir(parents=True, exist_ok=True)
    for name in ('markers', 'memory_reader', 'transaction', 'native_platform'):
        exe = tests / name
        inputs = [RECIPE / f'tests/{name}.cpp']
        flags = ['-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror', '-pthread',
                 '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
        if name == 'native_platform':
            inputs += [RECIPE / 'src/native_platform.cpp']
            flags += ['-DKQM_HOST_PLATFORM_TEST']
        run(['g++', *flags, '-I', RECIPE / 'src', '-I', RECIPE / 'tests', *inputs, '-o', exe])
        args = [exe]
        if name == 'markers':
            args += [WORK / 'native-group-fixture.bin']
        result = subprocess.run(list(map(str, args)), capture_output=True, text=True,
                                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=0'))
        (tests / f'{name}.log').write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name} failed: {tests / (name + ".log")}')
        results.append({'test': name, 'status': 'passed', 'output': result.stdout.strip()})
        print(result.stdout.strip())
    write_json(OUT / 'host-tests.json', results)
    return results


def build(refresh_support=False):
    before = snapshot()
    validation = prepare()
    native = WORK / 'native'
    native.mkdir(parents=True, exist_ok=True)
    command = r'''set -eu
export PATH=/opt/devkitpro/devkitARM/bin:$PATH
arm-none-eabi-g++ --version > /output/compiler.txt
flags='-DMHGU_DIAGNOSTICS={diagnostics} -Wall -Wextra -Werror -O2 -fPIC -marm -march=armv8-a+crc+crypto -mfloat-abi=softfp -mfpu=crypto-neon-fp-armv8 -fno-exceptions -fno-rtti -fno-unwind-tables -fno-asynchronous-unwind-tables -fno-threadsafe-statics -fno-builtin -fno-tree-loop-distribute-patterns'
for unit in plugin runtime native_platform; do
 arm-none-eabi-g++ -std=c++17 $flags -include /mod/vendor/forge/include/compat.h -I/mod/vendor/forge/include -isystem /mod/vendor/sdk/libs/libnx/nx/include -isystem /mod/vendor/sdk/libs/cimgui -c /mod/src/$unit.cpp -o /output/$unit.o
done
for unit in start svc; do
 arm-none-eabi-gcc -fPIC -marm -c /mod/src/$unit.S -o /output/$unit.o
done
arm-none-eabi-g++ -shared -nostdlib -Wl,--hash-style=sysv,-z,max-page-size=4096,-z,noexecstack,-init=init,-fini=fini -Wl,--version-script=/mod/src/exports.txt -Wl,-T,/mod/src/plugin.ld /output/start.o /output/plugin.o /output/runtime.o /output/native_platform.o /output/svc.o -o /output/plugin.elf
arm-none-eabi-readelf -aW /output/plugin.elf > /output/readelf.txt
arm-none-eabi-objdump -d /output/plugin.elf > /output/disassembly.txt
'''
    args = ['podman', '--root', CONTAINER_STORAGE, '--runroot',
            f'/tmp/mhgu-forge-container-{os.getuid()}', '--storage-driver', 'vfs', 'run', '--rm',
            '--network=none', '-v', f'{MOD}:/mod:ro', '-v', f'{ROOT}:/workspace:ro', '-v', f'{native}:/output:rw',
            prior.IMAGE, 'bash', '-lc', command.replace('{diagnostics}', os.environ.get('MHGU_DIAGNOSTICS', '0'))]
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True)
    (native / 'build.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f'ARM32 build failed: {native / "build.log"}')
    payload = prior.elf_to_nro((native / 'plugin.elf').read_bytes())
    acceptance = acceptance_for(payload)
    nro = Nro(payload)
    imports = {s[0].decode('ascii') for s in nro.symbols if s[0] and s[1][5] == 0}
    exports = {s[0].decode('ascii') for s in nro.symbols if s[0] and s[1][5] != 0}
    if not CALLBACKS <= exports:
        raise ValueError('Missing plugin callbacks/status export')
    if any(name.startswith(('__atomic', '__sync', 'jit', 'svc', 'forge_hook_', 'forge_patch_')) for name in imports):
        raise ValueError('Unexpected runtime or unsafe installer import')
    targets = [entry for entry in before if 'exports' in entry]
    if not targets or {entry['emulator'] for entry in targets} != {'configured'}:
        raise ValueError('Missing emulator Forge inventory')
    for entry in targets:
        missing = imports - set(entry['exports'])
        if missing:
            raise ValueError(f'Imports unavailable in {entry["path"]}: {missing}')
    if '.init_array' in (native / 'readelf.txt').read_text():
        raise ValueError('Dynamic static initialization is unsupported')
    bss = struct.unpack_from('<I', payload, 56)[0]
    if bss > 1024 * 1024:
        raise ValueError('Unexpected BSS growth')
    if snapshot() != before:
        raise ValueError('Installed packages/Forge checkout changed during build')
    write_json(OUT / 'binary-validation.json', {'imports': sorted(imports), 'exports': sorted(exports),
        'bss_bytes': bss, 'nro_bytes': len(payload), 'native_abi_assertions': 'passed',
        'CodeMemory': {'objects_added': 1, 'arena_bytes': 4096, 'trampoline_bytes': 16,
                       'runtime_headroom_verified': False}, 'installed_inventory': before,
        'runtime': {name: 'USER_PASSED' if acceptance else 'NOT RUN' for name in ('Eden', 'Ryujinx')}})
    package = OUT / 'package'
    target = package / 'romfs/nativeNX/plugins/key_quest_markers.nro'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    archive = OUT / 'candidates/key-quest-markers-r1-experimental.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        entry = zipfile.ZipInfo(str(target.relative_to(package)), (1980, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        z.writestr(entry, payload)
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [str(target.relative_to(package))] or z.read(z.namelist()[0]) != payload:
            raise ValueError('Packaged NRO readback failed')
    for name in ('README.md', 'COMPATIBILITY.md', 'MANUAL_TESTS.md', 'THIRD_PARTY.md'):
        shutil.copy2(RECIPE / name, OUT / name)
    if (RECIPE / 'RUNTIME_RESULTS.json').exists():
        shutil.copy2(RECIPE / 'RUNTIME_RESULTS.json', OUT / 'RUNTIME_RESULTS.json')
    sources = sorted(p for p in RECIPE.rglob('*') if p.is_file() and not any(x in p.relative_to(RECIPE).parts for x in ('build','work','tools','.venv','__pycache__')) and p.name!='build.local.json') + [Path(__file__).resolve(),
        SCRIPTS / 'key_quest_research.py', SCRIPTS / 'mhgu_binary.py',
        SCRIPTS / 'mhgu_assets.py']
    status = 'USER_ACCEPTED' if acceptance else 'EXPERIMENTAL_STATIC_VALIDATED_RUNTIME_NOT_RUN'
    manifest = {'revision': 'r1', 'status': status, 'published': False,
                'distribution_status_date': acceptance.get('distribution_status_date') if acceptance else None,
                'distribution_status_basis': acceptance.get('distribution_status_basis') if acceptance else None,
                'installed_by_recipe': False, 'title_slot_bytes': validation['title_slot_bytes'],
                'runtime_acceptance': {'path': 'RUNTIME_RESULTS.json', 'nro_sha256': sha(payload)} if acceptance else None,
                'forge_header_revision': prior.REVISION, 'compiler_container': prior.IMAGE,
                'libnx_svc_source_sha256': sha((prior.DEPS / 'libs/libnx/nx/source/kernel/svc32.s').read_bytes()),
                'nro': {'path': str(target.relative_to(OUT)), 'sha256': sha(payload)},
                'zip': {'path': str(archive.relative_to(OUT)), 'sha256': sha(archive.read_bytes())},
                'source_hashes': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sources}}
    write_json(OUT / 'manifest.json', manifest)
    (OUT / 'SHA256SUMS').write_text(f'{sha(payload)}  {target.relative_to(OUT)}\n'
                                  f'{sha(archive.read_bytes())}  {archive.relative_to(OUT)}\n')
    print(f'Staged {archive}: {len(payload)}-byte NRO, {bss}-byte BSS; all inventoried Forge imports resolved')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'test', 'build', 'all'))
    parser.add_argument('--refresh-support', action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare()
    if args.action in ('test', 'build', 'all'):
        test()
    if args.action in ('build', 'all'):
        build(args.refresh_support)


if __name__ == '__main__':
    main()
