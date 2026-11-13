#pragma once
#include <cstddef>
#include <cstdint>
enum class LegionShutdown : uint8_t { Unknown, BootProtect, LowBattery, LowVdd, SystemOff, CpuThermal, Scramble };
struct LegionBootSnapshot {
    LegionShutdown previous = LegionShutdown::Unknown;
};
LegionBootSnapshot legionBootSnapshot();
bool legionBootFormat(char *output, size_t size, uint32_t node);
