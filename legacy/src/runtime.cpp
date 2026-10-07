#include "runtime.h"
#include "memory_reader.h"
#include "native_platform.h"
#include "transaction.h"
#include "game_signatures.h"
#include <switch.h>
extern "C" {
#include <forge/mem.h>
}
#include <forge/singleton.h>
#include <forge/log.h>

extern "C" Result kqm_svc_query(MemoryInfo*, uint32_t*, uint64_t);
extern "C" Result kqm_svc_get_info(uint64_t*, uint32_t, uint32_t, uint64_t);
namespace kqm {
struct Query {
    bool region(uint64_t address, Region& out) const {
        MemoryInfo info{}; uint32_t page = 0;
        if (kqm_svc_query(&info, &page, address)) return false;
        out = {info.addr, info.size, info.perm}; return true;
    }
    char byte(uint32_t address) const {
        return *reinterpret_cast<volatile const char*>(address);
    }
};
static Query query;
static MemoryReader<Query> memory(query);
static NativePlatform platform;
static Transaction<NativePlatform> transaction(platform);
static TitleCache<1024, title_slot_bytes> cache;
static uint32_t main_base = 0, enabled = 0, attempted = 0;
static uint32_t outcomes[unsigned(Outcome::Count)]{};
static const char* status = "Waiting for initialization";
static const char* get_status() { return __atomic_load_n(&status, __ATOMIC_ACQUIRE); }
static void set_status(const char* value) { __atomic_store_n(&status, value, __ATOMIC_RELEASE); }
static uint32_t word(uint32_t address) { return *reinterpret_cast<volatile const uint32_t*>(address); }
static uint32_t group_instance() {
    const auto system = uintptr_t(forge_singleton_getInstanceByName("sQuest"));
    if ((system & 3) || !memory.readable(system, 0xb8)) return 0;
    const uint32_t group = word(uint32_t(system) + 0xb4);
    if ((group & 3) || !memory.readable(group, 0x70)) return 0;
    return group;
}
struct GroupView {
    uint32_t group, records, count;
    const GroupRecord* entry(unsigned index) const {
        using GetEntry = const GroupRecord*(*)(void*, uint32_t);
        const auto getter = reinterpret_cast<GetEntry>(main_base + group_getter_offset);
        const auto* entry = getter(reinterpret_cast<void*>(group), index);
        const uintptr_t expected = uint64_t(records) + index * sizeof(GroupRecord);
        return uintptr_t(entry) == expected ? entry : nullptr;
    }
    bool unchanged() const {
        return group_instance() == group && word(group + 0x64) == count &&
               word(group + 0x6c) == records;
    }
};
static Classification classification(uint32_t id) {
    const uint32_t group = group_instance();
    if (!group) return Classification::Unknown;
    GroupView view{group, word(group + 0x6c), word(group + 0x64)};
    if (!view.count || view.count > 4096 || (view.records & 3) ||
        !memory.readable(view.records, view.count * sizeof(GroupRecord)))
        return Classification::Unknown;
    return classify(view, id);
}
extern "C" char* kqm_get_name(void* object) {
    using Original = char*(*)(void*);
    const auto original_function = reinterpret_cast<Original>(transaction.original());
    if (!object || !original_function) return nullptr;
    char* original = original_function(object);
    if (!__atomic_load_n(&enabled, __ATOMIC_ACQUIRE)) return original;
    const auto address = uintptr_t(object);
    MarkResult result{original, Outcome::Unknown};
    if (!(address & 3) && memory.readable(address, 12)) {
        const uint32_t id = word(uint32_t(address) + 8);
        result = cache.mark(id, original, classification(id),
            [](const char* source, char* dest, unsigned capacity, unsigned& length) {
                return memory.title(source, dest, capacity, length);
            });
    }
    __atomic_fetch_add(&outcomes[unsigned(result.outcome)], 1u, __ATOMIC_RELAXED);
    return const_cast<char*>(result.title);
}
bool runtime_install() {
    if (__atomic_exchange_n(&attempted, 1u, __ATOMIC_ACQ_REL)) return runtime_active();
    main_base = forge_mem_getMainTextAddr();
    uint64_t program = 0;
    if (!main_base || main_base > 0xfe000000u ||
        kqm_svc_get_info(&program, 18, CUR_PROCESS_HANDLE, 0) ||
        program != 0x0100770008dd8000ull) {
        set_status("Inactive: unsupported program"); return false;
    }
    for (const auto& signature : signatures) {
        const uint64_t address = uint64_t(main_base) + signature.offset;
        if (!memory.readable(address, sizeof(signature.bytes))) {
            set_status("Inactive: unreadable build signature"); return false;
        }
        for (unsigned i = 0; i < sizeof(signature.bytes); ++i) {
            if (uint8_t(query.byte(uint32_t(address) + i)) != signature.bytes[i]) {
                set_status("Inactive: unsupported build or conflicting patch"); return false;
            }
        }
    }
    const HookSpec hook{main_base + name_getter_offset, uint32_t(&kqm_get_name),
                        {0xe92d4010u, 0xe1a04000u}};
    // Forge dispatches onInit before original sApp::run. Quest-list/details
    // consumers belong to the subsequent app loop. No hot installation/removal.
    const auto installed = transaction.install(hook, true);
    if (installed != InstallResult::Active) {
        set_status(installed == InstallResult::RestoreFailure ?
            "ERROR: restore failed; original trampoline retained; restart" :
            installed == InstallResult::CleanupFailure ?
            "Inactive: cleanup failed; arena retained; restart" :
            "Inactive: hook preparation failed");
        return false;
    }
    __atomic_store_n(&enabled, 1u, __ATOMIC_RELEASE);
    set_status("Active: progression key titles marked"); return true;
}
void runtime_update() {
    if (!runtime_active()) return;
    const uint32_t address = main_base + name_getter_offset;
    bool own = memory.readable(address, 32) && word(address) == 0xe51ff004u &&
               word(address + 4) == uint32_t(&kqm_get_name);
    for (unsigned i = 8; own && i < 32; ++i)
        own = uint8_t(query.byte(address + i)) == signatures[0].bytes[i];
    if (!own) {
        __atomic_store_n(&enabled, 0u, __ATOMIC_RELEASE);
        set_status("ERROR: quest-title hook changed; restart required");
        forge_log_warn("[key-quest-markers] External hook change; markers disabled; remove the conflicting patch and restart");
    }
}
bool runtime_active() { return __atomic_load_n(&enabled, __ATOMIC_ACQUIRE) != 0; }
const char* runtime_status() { return get_status(); }
Diagnostics runtime_diagnostics() {
    Diagnostics out{};
    for (unsigned i = 0; i < unsigned(Outcome::Count); ++i)
        out.outcomes[i] = __atomic_load_n(&outcomes[i], __ATOMIC_RELAXED);
    out.cache_used = cache.size(); out.install_result = unsigned(transaction.status());
    return out;
}
}
