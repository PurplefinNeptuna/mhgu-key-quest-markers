#include "runtime.h"
#include <forge/hook.h>
#include <forge/log.h>
#include <stdarg.h>
#define CIMGUI_DEFINE_ENUMS_AND_STRUCTS
#include <cimgui.h>
#include <stddef.h>

struct ForgeVersion { uint16_t major, minor, patch; };
struct PluginInitParam { ForgeVersion required_ver; char name[64]; };
static_assert(sizeof(void*) == 4 && sizeof(Jit) == 28 && sizeof(Hook) == 76);
static_assert(offsetof(Hook, jit) == 16 && offsetof(Hook, ctx_jit) == 44 &&
              offsetof(Hook, has_ctx) == 72);
static_assert(sizeof(PluginInitParam) == 70 && offsetof(PluginInitParam, name) == 6);
extern "C" void init() {}
extern "C" void fini() {} // Buffers/trampoline remain alive for the process.
// Freestanding compiler-generated zero fills; not exported by target Forge.
extern "C" void* memset(void* destination, int value, size_t bytes) {
    auto* out = static_cast<volatile unsigned char*>(destination);
    for (size_t i = 0; i < bytes; ++i) out[i] = static_cast<unsigned char>(value);
    return destination;
}
extern "C" uint32_t kqm_active_v1() { return kqm::runtime_active(); }
extern "C" void forge_onLoad(PluginInitParam* out) {
    if (!out) return;
    auto* bytes = reinterpret_cast<volatile unsigned char*>(out);
    for (unsigned i = 0; i < sizeof(*out); ++i) bytes[i] = 0;
    out->required_ver = {1, 4, 1};
    const char* name = "Key Quest Markers";
    for (unsigned i = 0; name[i]; ++i) bytes[offsetof(PluginInitParam, name) + i] = name[i];
}
extern "C" void forge_onInit() {
    kqm::runtime_install();
    forge_log_info("[key-quest-markers] %s", kqm::runtime_status());
}
extern "C" void forge_onUpdate(float) { kqm::runtime_update(); }
extern "C" void forge_onImGuiInit(void* context, void* allocate, void* release) {
    igSetCurrentContext(static_cast<ImGuiContext*>(context));
    igSetAllocatorFunctions(reinterpret_cast<ImGuiMemAllocFunc>(allocate),
                           reinterpret_cast<ImGuiMemFreeFunc>(release), nullptr);
}
extern "C" void forge_onImGuiRender() {
    if (!igTreeNode_Str("Key Quest Markers###kqm_panel")) return;
    igTextUnformatted(kqm::runtime_status(), nullptr);
    igTextUnformatted("[KEY] marks progression quests, including completed keys.", nullptr);
    if (igTreeNode_Str("Diagnostics###kqm_diagnostics")) {
        const auto d = kqm::runtime_diagnostics();
        igText("Stored titles: %u / 1024; installation result: %u", d.cache_used, d.install_result);
        igText("Marked: %u; ordinary: %u; unknown: %u", d.outcomes[0], d.outcomes[1], d.outcomes[2]);
        igText("Title rejected: %u; cache busy: %u; cache full: %u",
               d.outcomes[3], d.outcomes[4], d.outcomes[5]);
        igTreePop();
    }
    igTreePop();
}
extern "C" void forge_onImGuiFreeRender() {}
