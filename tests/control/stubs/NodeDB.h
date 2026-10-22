#pragma once
#include "configuration.h"
#include "mesh/LegionIgnore.h"
#include <algorithm>
#define SEGMENT_CONFIG 1
#define SEGMENT_NODEDATABASE 16
#define MAX_NUM_NODES 120
using NodeNum = uint32_t;
constexpr uint32_t NODEINFO_BITFIELD_IS_IGNORED_MASK = 16;
struct meshtastic_NodeInfoLite {
    uint32_t num = 0, bitfield = 0;
    char short_name[5]{};
    bool has_hops_away = true, snrPresent = true, mqtt = false;
    uint8_t hops_away = 0;
    uint8_t channel = 0;
    uint16_t slot = 1;
    float snr = 0;
};
inline bool nodeInfoLiteIsIgnored(const meshtastic_NodeInfoLite *node)
{
    return node && (node->bitfield & 16);
}
inline bool nodeInfoLiteIsProtected(const meshtastic_NodeInfoLite *node)
{
    return node && node->bitfield;
}
inline bool nodeInfoLiteHasSnr(const meshtastic_NodeInfoLite *node)
{
    return node->snrPresent;
}
inline bool nodeInfoLiteViaMqtt(const meshtastic_NodeInfoLite *node)
{
    return node->mqtt;
}
inline bool nodeInfoLiteHeardOnSlot(const meshtastic_NodeInfoLite *node, uint16_t slot)
{
    return node->slot == slot;
}
struct Config {
    struct {
        size_t ignore_incoming_count = 0;
        uint32_t ignore_incoming[3]{};
    } lora;
};
extern Config config;
class NodeDB
{
  public:
    uint32_t getNodeNum() const { return ownNode; }
    std::vector<meshtastic_NodeInfoLite> nodes;
    std::vector<meshtastic_NodeInfoLite> savedNodes;
    Config savedConfig;
    unsigned saveCalls = 0, notifications = 0, erased = 0;
    int lastSavedSegments = 0;
    bool saveSucceeds = true, admissionFails = false, protectFails = false, nodeDatabaseDirty = false, deferSave = false;
    size_t getNumMeshNodes() const { return nodes.size(); }
    meshtastic_NodeInfoLite *getMeshNodeByIndex(size_t i) { return &nodes.at(i); }
    meshtastic_NodeInfoLite *getMeshNode(uint32_t id)
    {
        for (auto &node : nodes)
            if (node.num == id)
                return &node;
        return nullptr;
    }
    meshtastic_NodeInfoLite *getOrCreateMeshNode(uint32_t id)
    {
        if (auto node = getMeshNode(id))
            return node;
        if (admissionFails)
            return nullptr;
        nodes.push_back({});
        nodes.back().num = id;
        return &nodes.back();
    }
    int numProtectedNodes() const
    {
        return std::count_if(nodes.begin(), nodes.end(), [](const auto &node) { return nodeInfoLiteIsProtected(&node); });
    }
    bool setProtectedFlag(meshtastic_NodeInfoLite *node, uint32_t mask, bool on)
    {
        if (!node || (on && protectFails))
            return false;
        if (on)
            node->bitfield |= mask;
        else
            node->bitfield &= ~mask;
        return true;
    }
    void eraseNodeSatellites(uint32_t) { ++erased; }
    void notifyObservers(bool) { ++notifications; }
    uint16_t committedLoraSlot() const { return 1; }
    bool saveToDisk(int segments)
    {
        ++saveCalls;
        lastSavedSegments = segments;
        if (saveSucceeds && !deferSave) {
            savedNodes = nodes;
            savedConfig = config;
            nodeDatabaseDirty = false;
        }
        return saveSucceeds;
    }
    LegionIgnoreResult legionSetIgnored(uint32_t node, bool ignored);
    bool legionIgnoreSavePending() const { return legionIgnorePendingSegments != 0; }
    bool legionFlushIgnoreChanges(bool force = false);
    int legionIgnorePendingSegments = 0;
    uint32_t legionIgnoreLastSave = 0;
    bool legionIgnoreSaveAttempted = false;
};
extern NodeDB *nodeDB;
