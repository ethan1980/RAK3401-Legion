#pragma once
#include "configuration.h"
inline uint32_t getPositionPrecisionForChannel(uint8_t index)
{
    const auto &ch = channels.getByIndex(index);
    return ch.role != meshtastic_Channel_Role_DISABLED ? ch.settings.module_settings.position_precision : 0;
}
inline bool findPositionChannel(uint8_t &index)
{
    for (uint8_t i = 0; i < channels.getNumChannels(); ++i)
        if (getPositionPrecisionForChannel(i)) {
            index = i;
            return true;
        }
    return false;
}
