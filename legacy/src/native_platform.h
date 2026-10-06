#pragma once
#include <stdint.h>

namespace kqm {
// Private CodeMemory owner, not a slice of Forge's legacy arena. No fallback
// backend and no per-hook allocation. Not invoked without approved game hooks.
class NativePlatform {
    uint32_t handle = 0, rw = 0, rx = 0;
    bool owner_mapped = false, slave_mapped = false;
public:
    uint32_t read(uint32_t address) const;
    bool create(unsigned bytes);
    bool close();
    bool owns_arena() const { return handle != 0; }
    uint32_t rw_base() const { return rw; }
    uint32_t rx_base() const { return rx; }
    bool prepare_slot(unsigned offset, const uint32_t* words);
    bool make_executable();
    bool write_pair(uint32_t address, uint32_t first, uint32_t second);
    bool sync_target(uint32_t address, unsigned bytes);
};
}
