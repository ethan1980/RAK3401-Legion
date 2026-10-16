#pragma once
#include <cstddef>
#include <cstdint>
#define ARCH_NRF52 1
#define RAK3401_LEGION_RECOVERY 1
#define RAK3401_LEGION_FLASH 1
#define LOG_DEBUG(...) ((void)0)
#define LOG_INFO(...) ((void)0)
#define LOG_WARN(...) ((void)0)
#define LOG_ERROR(...) ((void)0)
struct FakeFicr { uint32_t DEVICEID[2] = {1234, 5678}; };
extern FakeFicr ficr;
#define NRF_FICR (&ficr)
inline void delay(unsigned) {}
