#pragma once
#include <cstdint>
#define RAK3401_LEGION_DCDC 1
#define ARCH_NRF52 1
#define RAK3401 1
#define RAK13302 1
#define LOG_WARN(...) ((void)0)
#define LOG_INFO(...) ((void)0)
constexpr uint32_t NRF_SUCCESS = 0;
constexpr uint32_t NRF_POWER_DCDC_ENABLE = 1;
struct FakePower {
    uint32_t DCDCEN = 0, DCDCEN0 = 0;
};
extern FakePower power;
#define NRF_POWER (&power)
extern uint32_t queryResult, setResult, setCalls, setArgument;
extern uint8_t sdEnabled;
extern bool readbackFails;
