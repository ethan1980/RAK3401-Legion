#pragma once
#include "configuration.h"
#include <functional>
struct SentPacket {
    meshtastic_MeshPacket packet;
    int source;
    bool toPhone;
};
class MeshService
{
  public:
    std::vector<SentPacket> sent;
    int result = 0;
    std::function<void(const meshtastic_MeshPacket &)> onSend;
    int sendToMesh(meshtastic_MeshPacket *p, int source, bool toPhone)
    {
        sent.push_back({*p, source, toPhone});
        if (onSend)
            onSend(*p);
        delete p;
        return result;
    }
};
extern MeshService *service;
