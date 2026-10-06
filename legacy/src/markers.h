#pragma once
#include <stddef.h>
#include <stdint.h>

namespace kqm {
constexpr unsigned prefix_bytes = 6;
constexpr char prefix[] = "[KEY] ";
struct GroupRecord {
    uint32_t vtable, id;
    uint8_t attribute1, attribute2, title_version, padding;
};
static_assert(sizeof(GroupRecord) == 12 && offsetof(GroupRecord, id) == 4 &&
              offsetof(GroupRecord, attribute1) == 8);
enum class Classification { Unknown, Ordinary, Key };
inline bool key_group(unsigned value) {
    return (value >= 1 && value <= 17) || (value >= 19 && value <= 22);
}
// View owns no data. The adapter validates the complete array, checks each
// native accessor result and rechecks resource identity after this scan.
template<class View> Classification classify(View& view, uint32_t id) {
    if (!id || !view.count || view.count > 4096) return Classification::Unknown;
    bool found = false;
    uint8_t a = 0, b = 0, version = 0;
    for (unsigned i = 0; i < view.count; ++i) {
        const auto* row = view.entry(i);
        if (!row) return Classification::Unknown;
        if (row->id != id) continue;
        if (found && (a != row->attribute1 || b != row->attribute2 ||
                      version != row->title_version)) return Classification::Unknown;
        found = true; a = row->attribute1; b = row->attribute2;
        version = row->title_version;
    }
    if (!found || !view.unchanged()) return Classification::Unknown;
    return key_group(a) ? Classification::Key : Classification::Ordinary;
}
enum class Outcome { Marked, Ordinary, Unknown, InvalidTitle, Busy, Full, Count };
struct MarkResult { const char* title; Outcome outcome; };

// Published strings never change or move. Every access to slot metadata is
// protected by a non-blocking lock; consumers may retain string pointers.
template<unsigned Capacity, unsigned Bytes> class TitleCache {
    static_assert(Bytes > prefix_bytes + 1 && Capacity > 0);
    static_assert(__atomic_always_lock_free(4, nullptr), "No libatomic dependency");
    struct Slot { uint32_t id; unsigned length; char title[Bytes]; };
    Slot slots[Capacity]{};
    unsigned used = 0;
    uint32_t lock_word = 0;
public:
    static constexpr unsigned source_bytes = Bytes - prefix_bytes;
    unsigned size() const { return __atomic_load_n(&used, __ATOMIC_RELAXED); }
#if defined(KQM_HOST_TEST)
    void hold_for_test(bool value) { __atomic_store_n(&lock_word, uint32_t(value), __ATOMIC_RELEASE); }
#endif
    template<class Reader> MarkResult mark(uint32_t id, const char* original,
                                           Classification classification, Reader&& reader) {
        if (classification != Classification::Key)
            return {original, classification == Classification::Ordinary ?
                              Outcome::Ordinary : Outcome::Unknown};
        char source[source_bytes]{};
        unsigned length = 0;
        if (!original || !reader(original, source, source_bytes, length) ||
            !length || length >= source_bytes || source[length] != 0)
            return {original, Outcome::InvalidTitle};
        uint32_t unlocked = 0;
        if (!__atomic_compare_exchange_n(&lock_word, &unlocked, 1u, true,
                                         __ATOMIC_ACQUIRE, __ATOMIC_RELAXED))
            return {original, Outcome::Busy};
        const unsigned count = __atomic_load_n(&used, __ATOMIC_RELAXED);
        const char* result = nullptr;
        for (unsigned i = 0; i < count; ++i) {
            const auto& slot = slots[i];
            if (slot.id != id || slot.length != length) continue;
            bool equal = true;
            for (unsigned j = 0; j < length; ++j)
                if (slot.title[prefix_bytes + j] != source[j]) { equal = false; break; }
            if (equal) { result = slot.title; break; }
        }
        if (!result && count < Capacity) {
            auto& slot = slots[count];
            slot.id = id; slot.length = length;
            for (unsigned i = 0; i < prefix_bytes; ++i) slot.title[i] = prefix[i];
            for (unsigned i = 0; i <= length; ++i) slot.title[prefix_bytes + i] = source[i];
            result = slot.title;
            __atomic_store_n(&used, count + 1, __ATOMIC_RELAXED);
        }
        __atomic_store_n(&lock_word, 0u, __ATOMIC_RELEASE);
        return {result ? result : original, result ? Outcome::Marked : Outcome::Full};
    }
};
}
