#pragma once
#include <cstdint>
class PowerStatus
{
  public:
    bool battery = true;
    uint8_t percent = 82;
    bool getHasBattery() const { return battery; }
    uint8_t getBatteryChargePercent() const { return percent; }
};
extern PowerStatus *powerStatus;
