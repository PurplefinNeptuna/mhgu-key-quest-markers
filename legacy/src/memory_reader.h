#pragma once
#include <stddef.h>
#include <stdint.h>

namespace kqm {
struct Region { uint64_t address, size; unsigned permission; };
// Kernel-backed adapter on ARM32; fake regions in host tests. No guessed
// readability and no dereference across a mapping boundary.
template<class Query> class MemoryReader {
    Query& query;
    bool region(uint64_t address, Region& out) const {
        if (!address || address >= 0x100000000ull || !query.region(address, out) ||
            !(out.permission & 1) || out.address > address ||
            out.size > 0x100000000ull - out.address ||
            out.address + out.size <= address) return false;
        return true;
    }
public:
    explicit constexpr MemoryReader(Query& q) : query(q) {}
    bool readable(uint64_t address, unsigned bytes) const {
        if (!bytes || !address || address >= 0x100000000ull ||
            bytes > 0x100000000ull - address) return false;
        const uint64_t end = address + bytes;
        while (address < end) {
            Region info{};
            if (!region(address, info)) return false;
            address = info.address + info.size;
        }
        return true;
    }
    bool title(const char* source, char* dest, unsigned capacity, unsigned& length) const {
        length = 0;
        uint64_t address = uintptr_t(source);
        while (length < capacity) {
            Region info{};
            if (!region(address, info)) return false;
            const uint64_t end = info.address + info.size;
            while (address < end && length < capacity) {
                const char value = query.byte(uint32_t(address++));
                dest[length] = value;
                if (!value) return true;
                ++length;
            }
        }
        return false;
    }
};
}
