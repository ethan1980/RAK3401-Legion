#pragma once
#include <cstdint>
constexpr uint32_t NRF_SUCCESS = 0;
extern bool softDevice, failPowerApi;
inline uint32_t sd_softdevice_is_enabled(uint8_t *enabled)
{
    *enabled = softDevice;
    return failPowerApi ? 1 : NRF_SUCCESS;
}
