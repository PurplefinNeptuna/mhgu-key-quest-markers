#include "memory_reader.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <map>
#include <vector>
struct Query {
    std::vector<kqm::Region> regions;
    std::map<uint32_t, char> values;
    bool failed = false;
    mutable unsigned reads = 0;
    bool region(uint64_t address, kqm::Region& out) const {
        if (failed) return false;
        for (const auto& region : regions)
            if (address >= region.address && address - region.address < region.size) { out = region; return true; }
        return false;
    }
    char byte(uint32_t address) const { ++reads; return values.at(address); }
};
int main() {
    Query query{{{0x1000, 4, 1}, {0x1004, 4, 1}}, {{0x1000,'a'},{0x1001,'b'},{0x1002,'c'},
                {0x1003,'d'},{0x1004,'e'},{0x1005,0}}};
    kqm::MemoryReader<Query> reader(query);
    assert(reader.readable(0x1000, 8) && !reader.readable(0x1000, 9));
    assert(!reader.readable(0, 4) && !reader.readable(0x1000, 0));
    assert(!reader.readable(0xfffffffeu, 4) && !reader.readable(0x100000000ull, 1));
    char buffer[8]{}; unsigned length = 0;
    assert(reader.title(reinterpret_cast<const char*>(0x1000), buffer, sizeof(buffer), length));
    assert(length == 5 && std::strcmp(buffer,"abcde") == 0);
    query.regions[1].permission = 0;
    query.reads = 0;
    assert(!reader.title(reinterpret_cast<const char*>(0x1000), buffer, sizeof(buffer), length));
    assert(query.reads == 4); // Never reads the inaccessible next region.
    query.regions[1].permission = 1;
    assert(!reader.title(reinterpret_cast<const char*>(0x1000), buffer, 5, length));
    assert(length == 5);
    query.failed = true; query.reads = 0;
    assert(!reader.title(reinterpret_cast<const char*>(0x1000), buffer, sizeof(buffer), length));
    assert(query.reads == 0);
    query.failed = false;
    query.regions = {{0x1000, 0xffffffffffffffffull, 1}};
    assert(!reader.readable(0x1000, 4));
    query.regions = {{0xfffffffeu, 2, 1}};
    query.values = {{0xfffffffeu,'x'},{0xffffffffu,0}};
    assert(reader.title(reinterpret_cast<const char*>(0xfffffffeu), buffer, sizeof(buffer), length));
    query.values[0xffffffffu] = 'x';
    assert(!reader.title(reinterpret_cast<const char*>(0xfffffffeu), buffer, sizeof(buffer), length));
    std::cout << "Mapping boundaries, unreadable titles, overflow and unterminated strings passed\n";
}
