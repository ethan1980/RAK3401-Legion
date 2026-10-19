#pragma once
#include "configuration.h"
inline uint32_t sd_softdevice_is_enabled(uint8_t *result)
{
    *result = sdEnabled;
    return queryResult;
}
