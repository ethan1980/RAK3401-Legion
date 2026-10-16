#pragma once
#include "mesh/LegionCrc32.h"
#include <cstddef>
inline uint32_t crc32Buffer(const void *data, size_t size)
{
    uint32_t crc = UINT32_MAX;
    auto *bytes = static_cast<const uint8_t *>(data);
    for (size_t i = 0; i < size; ++i)
        crc = legionCrc32Update(crc, bytes[i]);
    return ~crc;
}
