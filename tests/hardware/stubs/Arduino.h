#pragma once
#include "nrf_soc.h"
extern uint32_t cachedResetReason;
inline uint32_t readResetReason()
{
    return cachedResetReason;
}
