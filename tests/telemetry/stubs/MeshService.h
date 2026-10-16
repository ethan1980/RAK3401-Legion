#pragma once
#include "configuration.h"
struct SentPacket {
    meshtastic_MeshPacket packet;
    int source;
    bool toPhone;
};
class MeshService
{
  public:
    std::vector<SentPacket> sent;
    int sendToMesh(meshtastic_MeshPacket *p, int source, bool toPhone)
    {
        sent.push_back({*p, source, toPhone});
        delete p;
        return 0;
    }
};
extern MeshService *service;
