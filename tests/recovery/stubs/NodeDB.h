#pragma once
#include "mesh/generated/meshtastic/deviceonly.pb.h"
#define DEVICESTATE_CUR_VER 25
#define DEVICESTATE_MIN_VER 24
#define POSITION_TELEMETRY_OPTIN_VER 26
constexpr const char *configFileName = "/prefs/config.proto";
constexpr const char *moduleConfigFileName = "/prefs/module.proto";
constexpr const char *channelFileName = "/prefs/channels.proto";
constexpr const char *deviceStateFileName = "/prefs/device.proto";
extern meshtastic_LocalConfig config;
extern meshtastic_LocalModuleConfig moduleConfig;
extern meshtastic_ChannelFile channelFile;
extern meshtastic_DeviceState devicestate;
extern meshtastic_User &owner;
extern meshtastic_PositionLite fixedPosition;
extern bool positionPresent;
class NodeDB
{
  public:
    uint32_t getNodeNum() const { return devicestate.my_node.my_node_num; }
    bool copyNodePosition(uint32_t, meshtastic_PositionLite &position)
    {
        position = fixedPosition;
        return positionPresent;
    }
};
extern NodeDB *nodeDB;
