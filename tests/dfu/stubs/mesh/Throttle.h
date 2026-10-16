#pragma once
#include "UptimeClock.h"
class Throttle
{
  public:
    static bool hasElapsed(uint32_t at, uint32_t interval) { return uint32_t(Time::getMillis() - at) >= interval; }
    static uint32_t remainingMs(uint32_t at, uint32_t interval)
    {
        const uint32_t elapsed = Time::getMillis() - at;
        return elapsed >= interval ? 0 : interval - elapsed;
    }
};
