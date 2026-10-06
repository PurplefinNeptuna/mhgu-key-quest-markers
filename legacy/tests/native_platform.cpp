#include "native_platform.h"
#include "kernel_contract.h"
#include <cassert>
#include <cstdio>
#include <map>
#include <sys/mman.h>

static unsigned calls, fail_at, creates;
static bool created, fail_cleanup, fail_slave_search;
static std::map<uint64_t, unsigned> maps;
static uint32_t target_address;
static MemoryInfo target_info;
static bool ok() { return ++calls != fail_at; }
extern "C" Result kqm_svc_query(MemoryInfo* info, uint32_t*, uint64_t a) {
    if (!ok() || (fail_slave_search && maps.size()==1)) return 1;
    if (a == target_address && target_address) { *info = target_info; return 0; }
    *info = {};
    info->addr = a; info->size = 4096;
    info->type = maps.count(a) ? 0x14 : 0;
    return 0;
}
extern "C" Result kqm_svc_get_info(uint64_t* value, uint32_t id, uint32_t handle, uint64_t sub) {
    assert(handle==CUR_PROCESS_HANDLE && sub==0);
    if(!ok())return 1;
    // Excluded pages are unmapped in this fixture: the allocator must still
    // skip reservations, not merely trust an unmapped MemoryInfo record.
    switch(id) {
        case 12:*value=0x10000000;break;
        case 13:*value=0x10000;break;
        case 2:*value=0x10000000;break;
        case 3:*value=0x1000;break;
        case 4:*value=0x10001000;break;
        case 5:*value=0x1000;break;
        default:assert(false);
    }
    return 0;
}
extern "C" Result kqm_svc_create(uint32_t* out, void* source, uint64_t bytes) {
    assert(!created && bytes == 4096 && (uintptr_t(source) & 4095) == 0);
    if (!ok()) { *out = 0xdeadbeef; return 1; }
    ++creates; created = true; *out = 42; return 0;
}
extern "C" Result kqm_svc_control(uint32_t handle, uint32_t op, uint64_t a,
                                  uint64_t bytes, uint32_t perm) {
    assert(created && handle == 42 && bytes == 4096 && a % 4096 == 0);
    if (!ok() || (fail_cleanup && op >= 2)) return 1;
    if (op < 2) {
        assert(!maps.count(a) && perm == (op == 0 ? Perm_Rw : Perm_Rx)); maps[a] = op;
    } else {
        assert(maps.at(a) == op - 2 && perm == 0); maps.erase(a);
    }
    return 0;
}
extern "C" Result kqm_svc_close(uint32_t h) {
    assert(h == 42 && created && maps.empty());
    if (!ok() || fail_cleanup) return 1;
    created = false; return 0;
}
extern "C" Result kqm_svc_flush(uint32_t handle, uint64_t address, uint64_t bytes) {
    assert(handle == CUR_PROCESS_HANDLE && address != 0 && bytes != 0);
    return ok() ? 0 : 1;
}
static void reset(unsigned fail = 0) {
    assert(!created && maps.empty()); calls = creates = 0; fail_at = fail; fail_cleanup = false;fail_slave_search=false;
}
int main() {
    unsigned scenarios = 0, successful_calls;
    {
        reset(); kqm::NativePlatform p, q;
        assert(p.create(4096) && p.owns_arena() && creates == 1 && maps.size() == 2);
        assert(p.rw_base() == 0x10002000 && p.rx_base() == 0x10003000);
        assert(!q.create(4096)); // Cannot lend one source page to two owners.
        assert(p.make_executable()); successful_calls = calls;
        assert(p.close() && !p.owns_arena() && !created && maps.empty()); ++scenarios;
    }
    for (unsigned fail = 1; fail <= successful_calls; ++fail) {
        reset(fail); kqm::NativePlatform p;
        if (p.create(4096)) assert(!p.make_executable());
        assert(p.close() && !created && maps.empty()); ++scenarios;
    }
    {
        reset(); kqm::NativePlatform p, q;
        assert(p.create(4096)); fail_cleanup = true;
        assert(!p.close() && p.owns_arena() && created);
        assert(!q.create(4096)); fail_cleanup = false;
        assert(p.close() && !created && maps.empty()); ++scenarios;
    }
    {
        reset(); kqm::NativePlatform p;
        fail_slave_search=true;fail_cleanup = true;
        assert(!p.create(4096) && p.owns_arena() && created && maps.size() == 1);
        fail_cleanup = false;fail_slave_search=false;
        assert(p.close() && !created && maps.empty()); ++scenarios;
    }
    {
        reset(); kqm::NativePlatform p;
        assert(p.create(4096)); fail_at = calls + 3;
        assert(!p.close() && p.owns_arena() && maps.empty());
        assert(p.close() && !created); ++scenarios;
    }
    {
        reset(); kqm::NativePlatform p;
        void* allocation = mmap(nullptr,4096,PROT_READ|PROT_WRITE,
                                 MAP_PRIVATE|MAP_ANONYMOUS|MAP_32BIT,-1,0);
        assert(allocation!=MAP_FAILED && uintptr_t(allocation)<=0xfffff000u);
        target_address=uint32_t(uintptr_t(allocation));
        auto* words=static_cast<uint32_t*>(allocation); words[0]=11;words[1]=22;
        target_info={};target_info.addr=target_address;target_info.size=4096;target_info.type=0x14;
        for(uint32_t perm : {0u,1u,3u,4u}) {
            target_info.perm=perm;
            assert(!p.write_pair(target_address,33,44) && words[0]==11 && words[1]==22);
            ++scenarios;
        }
        target_info.perm=5;target_info.type=0;
        assert(!p.write_pair(target_address,33,44));++scenarios;
        target_info.type=0x14;target_info.size=4;
        assert(!p.write_pair(target_address,33,44));++scenarios;
        target_info.size=4096;fail_at=calls+1;
        assert(!p.write_pair(target_address,33,44));++scenarios;
        fail_at=0;assert(!p.write_pair(target_address+1,33,44));++scenarios;
        assert(p.write_pair(target_address,33,44) && words[0]==33 && words[1]==44);++scenarios;
        assert(munmap(allocation,4096)==0);target_address=0;
    }
    std::printf("Native-platform ownership tests passed: %u scenarios with fake syscalls; ARM32 SVC execution remains untested.\n", scenarios);
}
