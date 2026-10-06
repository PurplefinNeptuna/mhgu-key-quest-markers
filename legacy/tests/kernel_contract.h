#pragma once
#include <stdint.h>
// Fake kernel for host ownership tests. Native builds use actual libnx headers.
using Result = uint32_t;
struct MemoryInfo {
    uint64_t addr, size;
    uint32_t type, attr, perm, ipc_refcount, device_refcount, padding;
};
constexpr uint32_t MemType_Unmapped = 0;
constexpr uint32_t Perm_Rw = 3, Perm_Rx = 5, CUR_PROCESS_HANDLE = 0xffff8001u;
enum { CodeMapOperation_MapOwner = 0, CodeMapOperation_MapSlave = 1,
       CodeMapOperation_UnmapOwner = 2, CodeMapOperation_UnmapSlave = 3 };
