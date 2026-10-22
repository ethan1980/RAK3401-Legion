#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>

#define RAK3401_LEGION_TELEMETRY 1
#define RAK3401_LEGION_CONTROL 1
#define RAK3401_LEGION_BOOT 1
#define MESHTASTIC_EXCLUDE_ADMIN 0
#define RAK3401_LEGION_POWER 1
#define RAK3401_LEGION_RECOVERY 1
#define APP_VERSION 2.8.2.Legion0.4.0
#define str(s) #s
#define xstr(s) str(s)
#define optstr(s) xstr(s)
#define ARCH_NRF52 1
#define RAK3401 1
#define RAK13302 1
constexpr uint32_t NODENUM_BROADCAST = UINT32_MAX;
constexpr int meshtastic_MeshPacket_decoded_tag = 1;
constexpr int meshtastic_PortNum_TEXT_MESSAGE_APP = 1;
constexpr int meshtastic_PortNum_TRACEROUTE_APP = 70;
constexpr int meshtastic_PortNum_ROUTING_APP = 5;
constexpr int meshtastic_MeshPacket_Priority_BACKGROUND = 10;
constexpr int meshtastic_MeshPacket_Priority_DEFAULT = 0;
constexpr int meshtastic_MeshPacket_TransportMechanism_TRANSPORT_LORA = 1;
constexpr int meshtastic_Channel_Role_DISABLED = 0;
constexpr int meshtastic_Channel_Role_PRIMARY = 1;
constexpr int meshtastic_Channel_Role_SECONDARY = 2;
constexpr int RX_SRC_LOCAL = 2;
constexpr int RX_SRC_USER = 1;
enum meshtastic_Routing_Error {
    meshtastic_Routing_Error_NONE = 0,
    meshtastic_Routing_Error_NO_ROUTE = 1,
    meshtastic_Routing_Error_TIMEOUT = 3,
    meshtastic_Routing_Error_NO_INTERFACE = 4,
    meshtastic_Routing_Error_MAX_RETRANSMIT = 5,
    meshtastic_Routing_Error_NO_RESPONSE = 8,
    meshtastic_Routing_Error_DUTY_CYCLE_LIMIT = 9
};
struct meshtastic_RouteDiscovery {
    size_t route_count = 0;
    uint32_t route[8]{};
    size_t snr_towards_count = 0;
    int8_t snr_towards[8]{};
    size_t route_back_count = 0;
    uint32_t route_back[8]{};
    size_t snr_back_count = 0;
    int8_t snr_back[8]{};
};
struct Payload {
    size_t size = 0;
    uint8_t bytes[240]{};
};
struct Decoded {
    int portnum = meshtastic_PortNum_TEXT_MESSAGE_APP;
    bool want_response = false;
    uint32_t request_id = 0;
    Payload payload;
};
struct meshtastic_MeshPacket {
    uint32_t from = 0, to = NODENUM_BROADCAST, id = 0;
    uint8_t channel = 0;
    int which_payload_variant = meshtastic_MeshPacket_decoded_tag;
    int priority = 0;
    bool want_ack = false;
    int transport_mechanism = 0;
    bool has_rx_rssi = false, via_mqtt = false;
    float rx_snr = 0;
    Decoded decoded;
};
struct ChannelSettings {
    char name[12]{};
    struct {
        size_t size = 0;
        uint8_t bytes[32]{};
    } psk;
};
struct FakeChannel {
    bool has_settings = false;
    int role = meshtastic_Channel_Role_DISABLED;
    ChannelSettings settings;
};
class FakeChannels
{
  public:
    std::array<FakeChannel, 8> entries{};
    std::array<bool, 8> publicKeys{}, aead{};
    uint8_t getNumChannels() const { return entries.size(); }
    uint8_t getPrimaryIndex() const { return 0; }
    FakeChannel &getByIndex(size_t index) { return entries.at(index); }
    bool usesPublicKey(size_t index) const { return publicKeys.at(index); }
    bool isAEADEnabled(size_t index) const { return aead.at(index); }
    const char *getName(size_t index) const { return entries.at(index).settings.name; }
};
extern FakeChannels channels;
struct Owner {
    bool is_licensed = false;
    struct {
        size_t size = 32;
    } public_key;
};
extern Owner owner;
extern uint32_t ownNode;
extern bool allocationFails;
inline bool isBroadcast(uint32_t to)
{
    return to == NODENUM_BROADCAST;
}
inline uint32_t getFrom(const meshtastic_MeshPacket *p)
{
    return p->from ? p->from : ownNode;
}
inline long random(long low, long)
{
    return low;
}
