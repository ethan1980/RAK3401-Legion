#pragma once
#include <cstdint>
class RadioLibInterface
{
  public:
    inline static RadioLibInterface *instance = nullptr;
    uint32_t rxGood = 0, rxBad = 0, txGood = 0, txRelay = 0;
    uint16_t txDrop = 0;
};
