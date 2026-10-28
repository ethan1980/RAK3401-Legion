#pragma once
#include "nrf_sdm.h"
struct FakePower {
    uint32_t GPREGRET = 0xa8, GPREGRET2 = 0, DCDCEN = 0;
};
extern FakePower powerRegisters;
#define NRF_POWER (&powerRegisters)
constexpr uint32_t POWER_RESETREAS_RESETPIN_Msk = 1;
constexpr uint32_t POWER_RESETREAS_DOG_Msk = 2;
constexpr uint32_t POWER_RESETREAS_SREQ_Msk = 4;
constexpr uint32_t POWER_RESETREAS_LOCKUP_Msk = 8;
constexpr uint32_t POWER_RESETREAS_OFF_Msk = 0x10000;
constexpr uint32_t POWER_RESETREAS_LPCOMP_Msk = 0x20000;
inline uint32_t sd_power_gpregret_clr(uint32_t index, uint32_t mask)
{
    if (index != 1 || failPowerApi)
        return 1;
    powerRegisters.GPREGRET2 &= ~mask;
    return NRF_SUCCESS;
}
inline uint32_t sd_power_gpregret_set(uint32_t index, uint32_t value)
{
    if (index != 1 || failPowerApi)
        return 1;
    powerRegisters.GPREGRET2 |= value;
    return NRF_SUCCESS;
}
