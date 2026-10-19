#pragma once
#include "configuration.h"
inline uint32_t sd_power_dcdc_mode_set(uint32_t value)
{
    ++setCalls;
    setArgument = value;
    if (!setResult && !readbackFails)
        power.DCDCEN = value;
    return setResult;
}
