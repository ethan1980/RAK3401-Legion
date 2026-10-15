#pragma once
#include <cstdint>
namespace Time
{
inline uint32_t now = 0;
inline uint32_t getMillis()
{
    return now;
}
inline uint64_t getUptimeSecs()
{
    return now / 1000;
}
} // namespace Time
