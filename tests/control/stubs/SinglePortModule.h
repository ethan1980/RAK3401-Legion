#pragma once
#include "configuration.h"
enum class ProcessMessage { CONTINUE, STOP };
class SinglePortModule
{
  public:
    SinglePortModule(const char *, int) {}
    virtual ~SinglePortModule() = default;

  protected:
    bool loopbackOk = false;
    virtual ProcessMessage handleReceived(const meshtastic_MeshPacket &) = 0;
    meshtastic_MeshPacket *allocDataPacket() { return allocationFails ? nullptr : new meshtastic_MeshPacket; }
};
