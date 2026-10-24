#pragma once
#include "configuration.h"
#include <utility>

class Router
{
  public:
    uint32_t nextId = 0x98765432;
    std::vector<std::pair<uint32_t, uint32_t>> cancelled;
    meshtastic_MeshPacket *allocForSending()
    {
        if (allocationFails)
            return nullptr;
        auto packet = new meshtastic_MeshPacket;
        packet->from = ownNode;
        packet->id = nextId++;
        return packet;
    }
    bool cancelSending(uint32_t from, uint32_t id)
    {
        cancelled.push_back({from, id});
        return true;
    }
};
extern Router *router;
