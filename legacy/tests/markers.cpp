#define KQM_HOST_TEST
#include "markers.h"
#include "game_signatures.h"
#include <cassert>
#include <cstring>
#include <fstream>
#include <iostream>
#include <iterator>
#include <set>
#include <string>
#include <thread>
#include <vector>

struct View {
    std::vector<kqm::GroupRecord> rows;
    unsigned count = 0;
    int bad_entry = -1;
    bool same = true;
    const kqm::GroupRecord* entry(unsigned index) const {
        return int(index) == bad_entry || index >= rows.size() ? nullptr : &rows[index];
    }
    bool unchanged() const { return same; }
};
static uint32_t u32(const std::vector<unsigned char>& bytes, unsigned offset) {
    return uint32_t(bytes.at(offset)) | uint32_t(bytes.at(offset + 1)) << 8 |
           uint32_t(bytes.at(offset + 2)) << 16 | uint32_t(bytes.at(offset + 3)) << 24;
}
static bool read_title(const char* source, char* dest, unsigned capacity, unsigned& length) {
    if (!source) return false;
    for (length = 0; length < capacity; ++length) {
        dest[length] = source[length];
        if (!source[length]) return true;
    }
    return false;
}
int main(int argc, char** argv) {
    assert(argc == 2);
    std::ifstream input(argv[1], std::ios::binary);
    std::vector<unsigned char> bytes{std::istreambuf_iterator<char>(input), {}};
    assert(u32(bytes, 0) == 0x40800000u && u32(bytes, 4) == 1509 && bytes.size() == 10571);
    View view;
    for (unsigned i = 0; i < 1509; ++i) {
        unsigned off = 8 + 7 * i;
        view.rows.push_back({0, u32(bytes, off), bytes[off + 4], bytes[off + 5], bytes[off + 6], 0});
    }
    view.count = unsigned(view.rows.size());
    std::set<uint32_t> keys;
    for (const auto& record : view.rows) {
        const auto found = kqm::classify(view, record.id);
        if (!record.id) { assert(found == kqm::Classification::Unknown); continue; }
        assert(found == (kqm::key_group(record.attribute1) ? kqm::Classification::Key : kqm::Classification::Ordinary));
        if (found == kqm::Classification::Key) keys.insert(record.id);
    }
    assert(keys.size() == 118 && keys.count(101) && keys.count(106) && keys.count(11106));
    assert(kqm::classify(view, 0) == kqm::Classification::Unknown);
    assert(kqm::classify(view, 0xffffffffu) == kqm::Classification::Unknown);
    View duplicate{{{0, 101, 1, 2, 3, 0}, {0, 101, 1, 2, 3, 0}}, 2};
    assert(kqm::classify(duplicate, 101) == kqm::Classification::Key);
    duplicate.rows[1].attribute1 = 47;
    assert(kqm::classify(duplicate, 101) == kqm::Classification::Unknown);
    duplicate.rows[1].attribute1 = 1; duplicate.rows[1].title_version = 4;
    assert(kqm::classify(duplicate, 101) == kqm::Classification::Unknown);
    view.same = false;
    assert(kqm::classify(view, 101) == kqm::Classification::Unknown);
    view.same = true; view.bad_entry = 5;
    assert(kqm::classify(view, 101) == kqm::Classification::Unknown);
    view.bad_entry = -1; view.count = 4097;
    assert(kqm::classify(view, 101) == kqm::Classification::Unknown);

    using C = kqm::Classification; using O = kqm::Outcome;
    kqm::TitleCache<2, 32> cache;
    const char* english = "Find the Ferns";
    const auto first = cache.mark(101, english, C::Key, read_title);
    assert(first.outcome == O::Marked && std::strcmp(first.title, "[KEY] Find the Ferns") == 0);
    assert(cache.mark(101, english, C::Key, read_title).title == first.title && cache.size() == 1);
    const char* localized = "Trouver les fougères";
    const auto second = cache.mark(101, localized, C::Key, read_title);
    assert(second.outcome == O::Marked && std::strcmp(second.title, "[KEY] Trouver les fougères") == 0);
    assert(second.title != first.title && std::strcmp(first.title, "[KEY] Find the Ferns") == 0);
    assert(cache.mark(106, english, C::Key, read_title).outcome == O::Full);
    assert(cache.mark(101, english, C::Ordinary, read_title).title == english);
    assert(cache.mark(101, english, C::Unknown, read_title).outcome == O::Unknown);
    assert(cache.mark(101, nullptr, C::Key, read_title).outcome == O::InvalidTitle);
    assert(cache.mark(101, "", C::Key, read_title).outcome == O::InvalidTitle);
    const std::string large(26, 'x');
    assert(cache.mark(101, large.c_str(), C::Key, read_title).outcome == O::InvalidTitle);
    assert(cache.mark(101, english, C::Key, [](const char*, char*, unsigned, unsigned&) { return false; }).title == english);
    cache.hold_for_test(true);
    assert(cache.mark(101, english, C::Key, read_title).outcome == O::Busy);
    cache.hold_for_test(false);
    assert(cache.mark(101, english, C::Key, read_title).title == first.title);

    auto full = new kqm::TitleCache<1024, kqm::title_slot_bytes>();
    const char* retained = nullptr;
    for (uint32_t id : keys) for (unsigned language = 0; language < 7; ++language) {
        const std::string title = "Title " + std::to_string(id) + " language " + std::to_string(language);
        const auto marked = full->mark(id, title.c_str(), C::Key, read_title);
        assert(marked.outcome == O::Marked);
        if (!retained) retained = marked.title;
    }
    assert(full->size() == 826);
    const std::string old_title(retained);
    for (unsigned i = 826; i < 1024; ++i)
        assert(full->mark(i + 2000000, english, C::Key, read_title).outcome == O::Marked);
    assert(full->size() == 1024 && old_title == retained);
    assert(full->mark(3000000, english, C::Key, read_title).outcome == O::Full);
    assert(old_title == retained);
    delete full; // Production keeps this storage until process termination.

    kqm::TitleCache<32, 64> concurrent;
    std::vector<std::thread> threads;
    for (unsigned worker = 0; worker < 16; ++worker) threads.emplace_back([&, worker] {
        const std::string title = "Quest " + std::to_string(worker % 8);
        for (unsigned i = 0; i < 2000; ++i) {
            const auto result = concurrent.mark(worker % 8 + 1, title.c_str(), C::Key, read_title);
            assert(result.outcome == O::Marked || result.outcome == O::Busy);
            if (result.outcome == O::Marked) assert(std::string(result.title) == "[KEY] " + title);
        }
    });
    for (auto& thread : threads) thread.join();
    assert(concurrent.size() == 8);
    bool nested = false;
    const auto recursive = concurrent.mark(1, "Quest 0", C::Key,
        [&](const char* text, char* dest, unsigned size, unsigned& length) {
            nested = concurrent.mark(1, "Quest 0", C::Key, read_title).outcome == O::Marked;
            return read_title(text, dest, size, length);
        });
    assert(nested && recursive.outcome == O::Marked && concurrent.size() == 8);
    std::cout << "118 native keys; all categories/duplicates; stable 826 language variants; capacity, reentrancy and 32000 concurrent calls passed\n";
}
