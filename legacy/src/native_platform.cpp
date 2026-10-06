#include "native_platform.h"
#if defined(KQM_HOST_PLATFORM_TEST)
#include "kernel_contract.h"
#else
#include <switch.h>
#endif
#include <stddef.h>

extern "C" {
Result kqm_svc_query(MemoryInfo*, uint32_t*, uint64_t);
Result kqm_svc_get_info(uint64_t*, uint32_t, uint32_t, uint64_t);
Result kqm_svc_create(uint32_t*, void*, uint64_t);
Result kqm_svc_control(uint32_t, uint32_t, uint64_t, uint64_t, uint32_t);
Result kqm_svc_close(uint32_t);
Result kqm_svc_flush(uint32_t, uint64_t, uint64_t);
}
namespace kqm {
static_assert(sizeof(MemoryInfo) == 40, "Pinned kernel query ABI");
static_assert(CodeMapOperation_MapOwner == 0 && CodeMapOperation_MapSlave == 1 &&
              CodeMapOperation_UnmapOwner == 2 && CodeMapOperation_UnmapSlave == 3);
static_assert(Perm_Rw == 3 && Perm_Rx == 5 && CUR_PROCESS_HANDLE == 0xffff8001u);
// A dedicated page: lending it to CodeMemory must not lend other plugin data.
alignas(4096) static uint32_t source_page[1024];
static NativePlatform* page_owner = nullptr;
static_assert(sizeof(source_page) == 4096);

// Boot-only search, bounded to ARM32 address space. The kernel is the authority
// for mapping availability. Concurrent allocation is not assumed safe; callers
// must establish the installation boundary before invoking Transaction.
struct Region { uint64_t start, end; };
static bool region(Region& out, uint32_t address_info, uint32_t size_info) {
    uint64_t address = 0, size = 0;
    if (kqm_svc_get_info(&address,address_info,CUR_PROCESS_HANDLE,0) ||
        kqm_svc_get_info(&size,size_info,CUR_PROCESS_HANDLE,0) ||
        address > 0x100000000ull || size > 0x100000000ull-address) return false;
    out = {address,address+size}; return true;
}
static uint32_t unused_page() {
    // Match pinned libnx virtmemFindCodeMemory: ASLR space, excluding alias
    // and heap reservations. Do not guess an address outside kernel bounds.
    Region aslr{}, alias{}, heap{};
    if (!region(aslr,12,13) || !region(alias,2,3) || !region(heap,4,5) ||
        aslr.end-aslr.start < 4096) return 0;
    uint64_t cursor = (aslr.start+4095) & ~uint64_t(4095);
    if (!cursor) cursor = 4096;
    while (cursor+4096 <= aslr.end) {
        bool skip = false;
        const Region excluded[] = {alias,heap};
        for (const Region& r : excluded) {
            if (cursor < r.end && r.start < cursor+4096) {
                cursor = (r.end+4095)&~uint64_t(4095); skip = true; break;
            }
        }
        if (skip) continue;
        MemoryInfo info{}; uint32_t page_info = 0;
        if (kqm_svc_query(&info,&page_info,cursor)) return 0;
        const uint64_t end = info.addr+info.size;
        if (info.addr > cursor || end <= cursor || end > 0x100000000ull) return 0;
        if (info.type == MemType_Unmapped && end-cursor >= 4096) return uint32_t(cursor);
        cursor = (end+4095)&~uint64_t(4095);
    }
    return 0;
}
uint32_t NativePlatform::read(uint32_t address) const {
    return *reinterpret_cast<volatile const uint32_t*>(address);
}
bool NativePlatform::create(unsigned bytes) {
    if (bytes != 4096 || handle || owner_mapped || slave_mapped || page_owner) return false;
    // Cleanup of failed preparation is performed here, before reporting failure.
    // On cleanup failure keep the handle/page owned; never retry or reuse it.
    if (kqm_svc_create(&handle, source_page, 4096)) {
        // The SVC wrapper stores its output register even on failure. Never
        // treat an unspecified failed-call output as an owned kernel handle.
        handle = 0;
        return false;
    }
    page_owner = this;
    rw = unused_page();
    if (!rw || kqm_svc_control(handle, CodeMapOperation_MapOwner, rw, 4096, Perm_Rw)) {
        close(); return false;
    }
    owner_mapped = true;
    rx = unused_page();
    if (!rx || kqm_svc_control(handle, CodeMapOperation_MapSlave, rx, 4096, Perm_Rx)) {
        close(); return false;
    }
    slave_mapped = true;
    return true;
}
bool NativePlatform::close() {
    // All mappings must be gone before closing/reclaiming the backing page.
    if (slave_mapped) {
        if (kqm_svc_control(handle, CodeMapOperation_UnmapSlave, rx, 4096, 0)) return false;
        slave_mapped = false;
    }
    if (owner_mapped) {
        if (kqm_svc_control(handle, CodeMapOperation_UnmapOwner, rw, 4096, 0)) return false;
        owner_mapped = false;
    }
    if (handle && kqm_svc_close(handle)) return false;
    handle = rw = rx = 0;
    if (page_owner == this) page_owner = nullptr;
    return true;
}
bool NativePlatform::prepare_slot(unsigned offset, const uint32_t* words) {
    if (!owner_mapped || offset > 4096 - 16 || (offset & 15)) return false;
    auto* out = reinterpret_cast<volatile uint32_t*>(rw + offset);
    for (unsigned i = 0; i < 4; ++i) out[i] = words[i];
    return true;
}
bool NativePlatform::sync_target(uint32_t address, unsigned bytes) {
    // Use the same kernel cache flush as the tested ARM32 legacy shim. The
    // pinned libnx ARM32 armICacheInvalidate is a no-op; Eden runtime cache
    // invalidation behavior still needs a fresh in-game test for this backend.
    const Result rc = kqm_svc_flush(CUR_PROCESS_HANDLE, address, bytes);
#if defined(__arm__)
    __asm__ volatile("dsb sy\n\tisb" ::: "memory");
#endif
    return rc == 0;
}
bool NativePlatform::make_executable() {
    return slave_mapped && owner_mapped && sync_target(rw, 4096);
}
bool NativePlatform::write_pair(uint32_t address, uint32_t first, uint32_t second) {
    MemoryInfo info{};
    uint32_t page_info = 0;
    if (!address || (address & 3u) || uint64_t(address)+8 > 0x100000000ull ||
        kqm_svc_query(&info, &page_info, address) ||
        info.type == MemType_Unmapped || (info.perm & Perm_Rx) != Perm_Rx || info.addr > address ||
        uint64_t(address)+8 > info.addr+info.size) return false;
    // Pinned Eden's guest write path permits writes to mapped RX guest code;
    // Forge's tested baseline uses the same direct-store publication. This is
    // not a permission-changing primitive or a native Switch support claim.
    auto* code = reinterpret_cast<volatile uint32_t*>(address);
    code[1] = second;
    code[0] = first;
    return read(address) == first && read(address + 4) == second;
}
}
