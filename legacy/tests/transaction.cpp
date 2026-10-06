#include "transaction.h"
#include <array>
#include <cassert>
#include <iostream>
#include <map>
struct Fake {
    std::map<uint32_t,uint32_t> memory{{0x1000,0xe92d4010u},{0x1004,0xe1a04000u}};
    std::array<uint32_t,4> words{};
    unsigned op = 0, fail_at = 0, writes = 0;
    bool owned = false, executable = false, restore_failure = false, cleanup_failure = false;
    bool race_before = false, foreign_after = false;
    bool ok() { return ++op != fail_at; }
    uint32_t read(uint32_t address) { return memory.at(address); }
    uint32_t rw_base() const { return 0x800000; }
    uint32_t rx_base() const { return 0x900000; }
    bool owns_arena() const { return owned; }
    bool create(unsigned bytes) { assert(bytes == 4096); if (!ok()) return false; owned = true; return true; }
    bool close() { if (!ok() || cleanup_failure) return false; owned = executable = false; return true; }
    bool prepare_slot(unsigned offset, const uint32_t* source) {
        assert(owned && !executable && offset == 0);
        if (!ok()) return false;
        for (unsigned i = 0; i < 4; ++i) words[i] = source[i];
        return true;
    }
    bool make_executable() {
        if (!ok()) return false;
        executable = true;
        if (race_before) memory[0x1000] = 0xe3a00000;
        return true;
    }
    bool write_pair(uint32_t address, uint32_t a, uint32_t b) {
        assert(owned && executable && address == 0x1000);
        ++writes;
        if (a == 0xe92d4010u && restore_failure) return false;
        memory[address + 4] = b;
        if (!ok()) return false; // Partial write must roll back safely.
        memory[address] = a; return true;
    }
    bool sync_target(uint32_t address, unsigned bytes) {
        assert(address == 0x1000 && bytes == 8);
        if (foreign_after && memory[address] == 0xe51ff004u) memory[address + 4] = 0xbad000u;
        return ok();
    }
};
constexpr kqm::HookSpec hook{0x1000,0x3000,{0xe92d4010u,0xe1a04000u}};
void vanilla(const Fake& p) {
    assert(p.memory.at(0x1000) == hook.expected[0] && p.memory.at(0x1004) == hook.expected[1]);
}
int main() {
    using R = kqm::InstallResult;
    unsigned count = 0, steps = 0;
    {
        Fake p; kqm::Transaction<Fake> t(p);
        assert(t.install(hook,true) == R::Active && t.original() == p.rx_base());
        steps = p.op;
        assert(p.words[0] == hook.expected[0] && p.words[1] == hook.expected[1] &&
               p.words[2] == 0xe51ff004u && p.words[3] == 0x1008);
        assert(t.remove(false) == R::NotQuiescent && t.is_active());
        assert(t.remove(true) == R::NotPrepared && !p.owned && !t.original()); vanilla(p); ++count;
    }
    for (unsigned fail = 1; fail <= steps; ++fail) {
        Fake p; p.fail_at = fail; kqm::Transaction<Fake> t(p);
        assert(t.install(hook,true) != R::Active && !p.owned && !t.original()); vanilla(p); ++count;
    }
    for (unsigned scenario = 0; scenario < 7; ++scenario) {
        Fake p; kqm::Transaction<Fake> t(p); auto recipe = hook;
        if (scenario == 0) recipe.target |= 1;
        if (scenario == 1) recipe.detour |= 1;
        if (scenario == 2) recipe.expected[1] = 0xe59f0000;
        if (scenario == 3) recipe.detour = recipe.target;
        if (scenario == 4) p.memory[0x1000] ^= 1;
        if (scenario == 6) recipe.target = 0xfffffff8u;
        assert(t.install(recipe,scenario != 5) != R::Active && !p.owned && !p.writes); ++count;
    }
    {
        Fake p; p.race_before = true; kqm::Transaction<Fake> t(p);
        assert(t.install(hook,true) == R::SignatureMismatch && !p.owned && !p.writes);
        assert(p.memory[0x1000] == 0xe3a00000); ++count;
    }
    {
        Fake p; p.foreign_after = true; kqm::Transaction<Fake> t(p);
        assert(t.install(hook,true) == R::RestoreFailure && p.owned && !t.is_active());
        assert(p.memory[0x1004] == 0xbad000u && t.original() == p.rx_base()); ++count;
    }
    {
        Fake p; p.fail_at = 5; p.restore_failure = true; kqm::Transaction<Fake> t(p);
        assert(t.install(hook,true) == R::RestoreFailure && p.owned && t.original()); ++count;
    }
    {
        Fake p; p.fail_at = 2; p.cleanup_failure = true; kqm::Transaction<Fake> t(p);
        assert(t.install(hook,true) == R::CleanupFailure && p.owned && !t.original());
        assert(t.install(hook,true) == R::InvalidRecipe); vanilla(p); ++count;
    }
    std::cout << count << " transactional failure/ownership scenarios passed; executable original precedes publication\n";
}
