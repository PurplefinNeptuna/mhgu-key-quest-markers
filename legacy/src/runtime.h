#pragma once
#include "markers.h"
namespace kqm {
bool runtime_install();
void runtime_update();
bool runtime_active();
const char* runtime_status();
struct Diagnostics { uint32_t outcomes[unsigned(Outcome::Count)]; unsigned cache_used, install_result; };
Diagnostics runtime_diagnostics();
}
