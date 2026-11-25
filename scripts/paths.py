"""Resolve this mod's own inputs and candidate paths, in either workspace or exported form."""
from pathlib import Path
import json, os, sys
MOD=Path(__file__).resolve().parents[1]
SCRIPTS=MOD/'scripts'
WORKSPACE=MOD.parent.name=='mods' and (MOD.parent.parent/'scripts/mod_distribution.py').is_file()
ROOT=MOD.parent.parent if WORKSPACE else MOD
CONFIG=json.loads((MOD/'build.local.json').read_text()) if (MOD/'build.local.json').exists() else {}
# Interpret configured relative directories against this source checkout, so
# build.sh remains usable from any working directory after an independent export.
for key in ('rust_bin','cargo_home','cargo_forge','devkitarm','inputs','arm_python'):
    if key in CONFIG and not Path(CONFIG[key]).is_absolute(): CONFIG[key]=str(MOD/CONFIG[key])
# Two build-time comparison variants share one classifier and native adapter.
# Separate output trees prevent either package from overwriting the other.
SMALL_MARK=os.environ.get('KQM_SMALL_MARK','0')
if SMALL_MARK not in ('0','1'): raise ValueError('KQM_SMALL_MARK must be 0 or 1')
VERSION='r24-small' if SMALL_MARK=='1' else 'r24'
BUILD_ROOT=ROOT/('build/key-quest-markers/candidates/'+VERSION)
WORK_ROOT=ROOT/('work/key-quest-markers/candidates/'+VERSION)
CARGO_TARGET=WORK_ROOT/'cargo-target'
QUEST_LISTS=WORK_ROOT/'quest_lists.rs'
FORGE=MOD/'vendor/forge-rs'
DEPS=MOD/'vendor'
PYTHON=Path(CONFIG.get('python',sys.executable))
CONTAINER_STORAGE=Path(CONFIG.get('container_storage',ROOT/'tools/forge-container/storage'))
def input_path(name):return Path(CONFIG.get('inputs',ROOT/'work/key-quest-markers/inputs'))/name
