#pragma once
#include <stdint.h>

namespace kqm {
struct HookSpec { uint32_t target, detour, expected[2]; };
enum class InstallResult {
    NotPrepared, Active, InvalidRecipe, NotQuiescent, SignatureMismatch,
    AllocationFailure, PreparationFailure, PublicationFailure,
    RestoreFailure, CleanupFailure
};
// One exact ARM entry hook, adapted from the owned controls transaction.
// Only the inspected push {r4,lr}; mov r4,r0 pair can be displaced.
template<class Platform> class Transaction {
    Platform& p;
    HookSpec journal{};
    bool arena_owned = false, touched = false, active = false;
    InstallResult result = InstallResult::NotPrepared;
    bool matches() const {
        return p.read(journal.target) == journal.expected[0] &&
               p.read(journal.target + 4) == journal.expected[1];
    }
    InstallResult cleanup(InstallResult cause) {
        if (arena_owned && !p.close()) return result = InstallResult::CleanupFailure;
        arena_owned = false; return result = cause;
    }
    InstallResult restore(InstallResult cause) {
        active = false;
        if (touched) {
            const uint32_t a = p.read(journal.target), b = p.read(journal.target + 4);
            // Accept our complete/partial write or unchanged original. Preserve
            // foreign changes and retain code if ownership cannot be proved.
            if (!((a == journal.expected[0] && b == journal.expected[1]) ||
                  ((a == journal.expected[0] || a == 0xe51ff004u) && b == journal.detour)))
                return result = InstallResult::RestoreFailure;
            if (!p.write_pair(journal.target, journal.expected[0], journal.expected[1]) ||
                !p.sync_target(journal.target, 8) || !matches())
                return result = InstallResult::RestoreFailure;
            touched = false;
        }
        return cleanup(cause);
    }
public:
    constexpr explicit Transaction(Platform& platform) : p(platform) {}
    bool is_active() const { return active; }
    InstallResult status() const { return result; }
    uint32_t original() const { return arena_owned && touched ? p.rx_base() : 0; }
    InstallResult install(const HookSpec& h, bool quiescent) {
        if (arena_owned || touched || active || !h.target || !h.detour ||
            ((h.target | h.detour) & 3) || uint64_t(h.target) + 8 >= 0x100000000ull ||
            (uint64_t(h.detour) < uint64_t(h.target) + 8 &&
             uint64_t(h.target) < uint64_t(h.detour) + 4) ||
            h.expected[0] != 0xe92d4010u || h.expected[1] != 0xe1a04000u)
            return result = InstallResult::InvalidRecipe;
        if (!quiescent) return result = InstallResult::NotQuiescent;
        journal = h;
        if (!matches()) return result = InstallResult::SignatureMismatch;
        if (!p.create(4096)) {
            arena_owned = p.owns_arena();
            return cleanup(InstallResult::AllocationFailure);
        }
        arena_owned = true;
        const uint32_t rw = p.rw_base(), rx = p.rx_base();
        if (!rw || !rx || ((rw | rx) & 4095) ||
            uint64_t(rw) + 4096 > 0x100000000ull || uint64_t(rx) + 4096 > 0x100000000ull ||
            (uint64_t(h.target) < uint64_t(rw) + 4096 && uint64_t(rw) < uint64_t(h.target) + 8) ||
            (uint64_t(h.target) < uint64_t(rx) + 4096 && uint64_t(rx) < uint64_t(h.target) + 8))
            return cleanup(InstallResult::PreparationFailure);
        const uint32_t words[4] = {h.expected[0], h.expected[1], 0xe51ff004u, h.target + 8};
        if (!p.prepare_slot(0, words) || !p.make_executable())
            return cleanup(InstallResult::PreparationFailure);
        if (!matches()) return cleanup(InstallResult::SignatureMismatch);
        // Make the original callable before publication, including failure.
        touched = true;
        if (!p.write_pair(h.target, 0xe51ff004u, h.detour) || !p.sync_target(h.target, 8) ||
            p.read(h.target) != 0xe51ff004u || p.read(h.target + 4) != h.detour)
            return restore(InstallResult::PublicationFailure);
        active = true; return result = InstallResult::Active;
    }
    InstallResult remove(bool quiescent) {
        if (!quiescent) return result = InstallResult::NotQuiescent;
        return restore(InstallResult::NotPrepared);
    }
};
}
