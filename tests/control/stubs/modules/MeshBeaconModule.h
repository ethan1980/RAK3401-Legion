#pragma once
#include <cstdint>
class MeshBeaconModule
{
  public:
    inline static bool channelEditAllowed = true;
    inline static unsigned changes = 0;
    static bool legionChannelEditAllowed(uint8_t) { return channelEditAllowed; }
    static void legionChannelsChanged() { ++changes; }
};
