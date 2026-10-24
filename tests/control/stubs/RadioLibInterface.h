#pragma once
#include "configuration.h"
#include <cstdio>

class RadioInterface
{
  public:
    unsigned measurements = 0;
    uint32_t airtime = 300;
    uint32_t getPacketTime(const meshtastic_MeshPacket *)
    {
        ++measurements;
        return airtime;
    }
    void legionApcDescribe(char *output, size_t size) const
    {
        std::snprintf(output, size,
                      "gen:0 region:3 role:0 CUSTOM:0\nf_kHz:869618 bw_Hz:62500 sf:7 cr:5\ncfg_dBm:27 drive_dBm:18");
    }
};
class RadioLibInterface : public RadioInterface
{
  public:
    inline static RadioLibInterface *instance = nullptr;
};
