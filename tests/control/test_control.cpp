// Compile the actual LegionControlModule.cpp, LegionControlPolicy.h and LegionIgnore.cpp.
// Commands must select the correct executor, originate one message only after channel revalidation,
// retain coherent paginated reports, and never claim durable ignore changes after a deferred save.
// These tests guard queue-vs-delivery confusion, command recursion, stale-hop SNR and legacy blocks.
// Trace requests must correlate by packet, target and channel, preserve both route directions,
// remain asynchronous, respect the 90s deadline across rollover, and stop exposing results after key changes.
// SDK, radio, NodeDB storage and scheduler boundaries are simulated; hardware RF delivery is not tested.
#include "MeshService.h"
#include "NodeDB.h"
#include "UptimeClock.h"
#include "mesh/Router.h"
#include "modules/AdminModule.h"
#include "modules/LegionControlModule.h"
#include "xmodem.h"
#include <cassert>
#include <iostream>
#include <set>
#include <string>

FakeChannels channels;
Owner owner;
Config config;
uint32_t ownNode = 0xabcdef01, rebootAtMsec = 0, radioGeneration = 0;
bool allocationFails = false, supplyReady = true, flashSafe = true, recoveryBlocked = false;
unsigned bootReports = 0;
bool legionBootFormat(char *output, size_t size, uint32_t node)
{
    ++bootReports;
    return std::snprintf(output, size, "!%08lx BOOT reset:watchdog(00000002) prev:unknown", (unsigned long)node) > 0;
}
NodeDB database;
NodeDB *nodeDB = &database;
MeshService meshService;
MeshService *service = &meshService;
Router testRouter;
Router *router = &testRouter;
XModem xModem;
AdminModule admin;
AdminModule *adminModule = &admin;
bool legionPowerTxReady()
{
    return supplyReady;
}
bool legionBatterySafeForFlash()
{
    return flashSafe;
}

class TestModule : public LegionControlModule
{
  public:
    using LegionControlModule::handleReceived;
    using LegionControlModule::runOnce;
    bool localLoopback() const { return loopbackOk; }
};

void channel(unsigned index, const char *name)
{
    auto &ch = channels.entries[index];
    ch.has_settings = true;
    ch.role = index ? meshtastic_Channel_Role_SECONDARY : meshtastic_Channel_Role_PRIMARY;
    std::strcpy(ch.settings.name, name);
    ch.settings.psk.size = 32;
    std::memset(ch.settings.psk.bytes, 0x42, 32);
}
void reset()
{
    channels = {};
    owner = {};
    config = {};
    database = {};
    meshService = {};
    testRouter = {};
    admin = {};
    xModem = {};
    Time::now = rebootAtMsec = radioGeneration = 0;
    allocationFails = recoveryBlocked = false;
    supplyReady = flashSafe = true;
    bootReports = 0;
    channel(2, "LegionRF");
    channel(0, "SFNarrow");
}
meshtastic_MeshPacket packet(const std::string &text, uint32_t id = 1, uint32_t from = 0x12345678)
{
    meshtastic_MeshPacket result;
    result.from = from;
    result.id = id;
    result.channel = 2;
    assert(text.size() <= sizeof(result.decoded.payload.bytes));
    result.decoded.payload.size = text.size();
    std::memcpy(result.decoded.payload.bytes, text.data(), text.size());
    return result;
}
std::string text(size_t index)
{
    const auto &p = meshService.sent.at(index).packet.decoded.payload;
    return {reinterpret_cast<const char *>(p.bytes), p.size};
}
std::string last()
{
    return text(meshService.sent.size() - 1);
}
void deliver(TestModule &module, const std::string &text, uint32_t id = 1, uint32_t from = 0x12345678)
{
    module.handleReceived(packet(text, id, from));
    Time::now += 10000;
    module.runOnce();
}
void next()
{
    Time::now += 5000;
}

void test_parser_targets_and_utf8()
{
    auto parse = [](const std::string &s) {
        return legion::parseControl(reinterpret_cast<const uint8_t *>(s.data()), s.size(), ownNode);
    };
    for (const auto &s : {"/msg", "/msg !bad hi text", "/msg !00000001 SFNarrow hi", "/reboot !12345678", "/zerohop"})
        assert(parse(s).command == legion::ControlCommand::None);
    for (const auto &s : {"/msg !abcdef01", "/msg !abcdef01 SFNarrow", "/reboot !abcdef01 extra", "/zerohop !abcdef01 0",
                          "/zerohop !abcdef01 -1", "/ignore !bad", "/ignorelist 0", "/ignorelist x"})
        assert(!parse(s).valid && parse(s).command != legion::ControlCommand::None);
    const auto quoted = parse(" /msg !ABCDEF01 \"My channel\" hola 🌍\n");
    assert(quoted.valid && !std::strcmp(quoted.channel, "My channel") && !std::strcmp(quoted.text, "hola 🌍\n"));
    assert(!parse(std::string("/msg !abcdef01 SFNarrow ") + std::string(200, 'x')).valid);
    assert(parse(std::string("/msg !abcdef01 S ") + std::string(199, 'x')).valid);
    assert(!parse(std::string("/msg !abcdef01 S a") + std::string(1, '\0') + "b").valid);
    assert(!parse("/msg !abcdef01 S \xc0\x80").valid);
    assert(!parse("/msg !abcdef01 S \xed\xa0\x80").valid);
    assert(parse("/ignore !12345678").group && parse("/ignorelist 2").page == 2);
}

void test_message_queue_channel_and_duplicates()
{
    reset();
    TestModule module;
    assert(!module.localLoopback());
    deliver(module, "/msg !abcdef01 sfnarrow Hola mundo");
    assert(meshService.sent.size() == 2 && text(0) == "Hola mundo");
    assert(meshService.sent[0].packet.channel == 0 && meshService.sent[1].packet.channel == 2);
    assert(last() == "!abcdef01: Message queued to SFNarrow");
    for (const auto &sent : meshService.sent) {
        assert(sent.source == RX_SRC_LOCAL && sent.toPhone && !sent.packet.want_ack && !sent.packet.decoded.want_response);
    }
    next();
    deliver(module, "/msg !abcdef01 sfnarrow Hola mundo");
    assert(meshService.sent.size() == 2);
    next();
    deliver(module, "/msg !abcdef01 missing text", 2);
    assert(last().find("not found") != std::string::npos && meshService.sent.size() == 3);
    channel(1, "SFNarrow");
    next();
    deliver(module, "/msg !abcdef01 SFNarrow ambiguous", 3);
    assert(last().find("Ambiguous") != std::string::npos);
    channels.entries[1].role = meshtastic_Channel_Role_DISABLED;
    meshService.result = 1;
    next();
    deliver(module, "/msg !abcdef01 SFNarrow rejected", 4);
    assert(last().find("queue rejected") != std::string::npos);
    for (size_t i = 2; i < meshService.sent.size(); ++i)
        assert(text(i).find("Message queued") == std::string::npos);
}

void test_changed_keys_and_pending_destination()
{
    for (int change = 0; change < 5; ++change) {
        reset();
        TestModule module;
        module.handleReceived(packet("/msg !abcdef01 SFNarrow once"));
        if (change == 0)
            channels.entries[2].settings.psk.bytes[0]++;
        if (change == 1)
            channels.entries[0].settings.psk.bytes[0]++;
        if (change == 2)
            channels.entries[0].role = meshtastic_Channel_Role_DISABLED;
        if (change == 3)
            owner.is_licensed = true;
        if (change == 4)
            channels.aead[2] = true;
        Time::now = 1000;
        module.runOnce();
        for (size_t i = 0; i < meshService.sent.size(); ++i)
            assert(text(i) != "once" && text(i).find("Message queued") == std::string::npos);
    }
}

void test_control_authorization_and_power()
{
    for (int invalid = 0; invalid < 10; ++invalid) {
        reset();
        TestModule module;
        auto p = packet("/reboot !abcdef01");
        if (invalid == 0)
            p.channel = 0;
        if (invalid == 1)
            channels.entries[2].settings.psk.size = 1;
        if (invalid == 2)
            channels.entries[2].settings.psk.bytes[0] = 0, std::memset(channels.entries[2].settings.psk.bytes, 0, 32);
        if (invalid == 3)
            channels.publicKeys[2] = true;
        if (invalid == 4)
            channel(3, "LegionRF");
        if (invalid == 5)
            p.to = ownNode;
        if (invalid == 6)
            owner.is_licensed = true;
        if (invalid == 7)
            supplyReady = false;
        if (invalid == 8)
            p.decoded.portnum = 99;
        if (invalid == 9)
            p.decoded.payload.size = 999;
        module.handleReceived(p);
        Time::now = 10000;
        module.runOnce();
        assert(!rebootAtMsec && meshService.sent.empty());
    }
    reset();
    TestModule module;
    admin.editing = true;
    deliver(module, "/reboot !abcdef01");
    assert(!rebootAtMsec && last().find("Busy") != std::string::npos);
    reset();
    TestModule noMemory;
    allocationFails = true;
    deliver(noMemory, "/msg !abcdef01 SFNarrow text");
    assert(meshService.sent.empty());
}

void test_reboot_deadline_rollover_and_failure()
{
    reset();
    TestModule module;
    Time::now = UINT32_MAX - 10000;
    const auto accepted = Time::now;
    deliver(module, "/reboot !abcdef01");
    assert(rebootAtMsec == accepted + 20000 && last().find("20s") != std::string::npos);
    const auto deadline = rebootAtMsec;
    next();
    deliver(module, "/reboot !abcdef01", 2);
    assert(rebootAtMsec == deadline && last().find("already scheduled") != std::string::npos);
    reset();
    TestModule failedReply;
    allocationFails = true;
    deliver(failedReply, "/reboot !abcdef01");
    assert(rebootAtMsec == 20000 && meshService.sent.empty());
    reset();
    TestModule earlier;
    rebootAtMsec = 15000;
    deliver(earlier, "/reboot !abcdef01");
    assert(rebootAtMsec == 15000);
}

void addDirect(TestModule &module, uint32_t id, float snr, int8_t hops = 0, bool rf = true, bool rssi = true, bool mqtt = false)
{
    auto node = database.getOrCreateMeshNode(id);
    std::strcpy(node->short_name, "TEST");
    node->snr = snr;
    node->hops_away = hops < 0 ? 0 : hops;
    node->mqtt = mqtt;
    auto p = packet("");
    p.from = id;
    p.transport_mechanism = rf ? 1 : 0;
    p.has_rx_rssi = rssi;
    p.via_mqtt = mqtt;
    p.rx_snr = snr;
    module.observeLink(p, hops);
}

void test_zerohop_provenance_and_zero_snr()
{
    reset();
    TestModule module;
    addDirect(module, 0x11111111, 0);
    addDirect(module, 0x22222222, -3.25);
    addDirect(module, 0x33333333, 5, 1);
    addDirect(module, 0x44444444, 4, -1);
    addDirect(module, 0x55555555, 3, 0, false);
    addDirect(module, 0x66666666, 2, 0, true, false);
    addDirect(module, 0x77777777, 2, 0, true, true, true);
    addDirect(module, 0x88888888, 1);
    database.getMeshNode(0x88888888)->snrPresent = false;
    addDirect(module, 0x99999999, 1);
    database.getMeshNode(0x99999999)->slot = 2;
    addDirect(module, 0xaaaaaaaa, 1);
    addDirect(module, 0xaaaaaaaa, 2, 1);
    deliver(module, "/zerohop !abcdef01");
    assert(last().find("n:2 SNR") != std::string::npos && last().find("+0.00dB") != std::string::npos &&
           last().find("-3.25dB") != std::string::npos);
    assert(last().find("33333333") == std::string::npos && last().find("aaaaaaaa") == std::string::npos);
    next();
    ++radioGeneration;
    deliver(module, "/zerohop !abcdef01", 2);
    assert(last().find("No direct RF nodes this boot") != std::string::npos);
}

void test_snapshot_pages_owner_expiry_and_utf8()
{
    reset();
    TestModule module;
    for (unsigned i = 0; i < 20; ++i) {
        addDirect(module, 0x10000000 + i, i / 2.0f);
        std::strcpy(database.nodes.back().short_name, "🚀");
    }
    deliver(module, "/zerohop !abcdef01");
    const auto page1 = last();
    assert(page1.size() <= 199 && page1.find("Next:") != std::string::npos && page1.find("n:20") != std::string::npos);
    next();
    addDirect(module, 0x99999999, 50);
    deliver(module, "/zerohop !abcdef01", 2);
    assert(last() == page1);
    next();
    deliver(module, "/zerohop !abcdef01 2", 3, 0x87654321);
    assert(last().find("busy") != std::string::npos);
    next();
    deliver(module, "/zerohop !abcdef01 2", 4);
    const auto page2 = last();
    assert(page2 != page1 && page2.find("99999999") == std::string::npos);
    next();
    deliver(module, "/zerohop !abcdef01 2", 5);
    assert(last() == page2);
    Time::now += legion::CONTROL_SNAPSHOT_MS;
    deliver(module, "/zerohop !abcdef01 2", 6);
    assert(last().find("Snapshot expired") != std::string::npos);
    next();
    deliver(module, "/zerohop !abcdef01", 7);
    assert(last().find("n:21") != std::string::npos);
    next();
    channels.entries[2].settings.psk.bytes[0]++;
    deliver(module, "/zerohop !abcdef01 2", 8);
    assert(last().find("Snapshot expired") != std::string::npos);
}

void test_directory_capacity_and_all_pages()
{
    for (bool snr : {false, true}) {
        legion::ControlDirectory directory;
        directory.clear(snr, 65535);
        for (unsigned i = 0; i < 140; ++i)
            directory.add(0x10000000 + i, "🌍", -128 + i);
        directory.finish();
        std::set<std::string> ids;
        for (uint16_t page = 1; page < 129; ++page) {
            char output[200];
            if (!directory.format(output, sizeof(output), ownNode, page))
                break;
            const std::string body(output);
            assert(body.size() <= 199 && body.find("partial") != std::string::npos);
            assert(legion::validUtf8(reinterpret_cast<const uint8_t *>(output), body.size()));
            for (unsigned i = 0; i < 128; ++i) {
                char id[10];
                std::snprintf(id, sizeof(id), "!%08x", 0x10000000 + i);
                if (body.find(id) != std::string::npos)
                    assert(ids.insert(id).second);
            }
        }
        assert(ids.size() == 128);
    }
}

void test_ignore_union_persistence_and_idempotency()
{
    reset();
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Saved);
    assert(nodeInfoLiteIsIgnored(database.getMeshNode(0x11111111)) && database.saveCalls == 1 && database.erased == 1);
    database.nodes = database.savedNodes;
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Unchanged && database.saveCalls == 1);
    config.lora.ignore_incoming_count = 3;
    config.lora.ignore_incoming[0] = 0x11111111;
    config.lora.ignore_incoming[1] = 0x22222222;
    config.lora.ignore_incoming[2] = 0x11111111;
    assert(database.legionSetIgnored(0x11111111, false) == LegionIgnoreResult::Saved);
    assert(database.lastSavedSegments == (SEGMENT_CONFIG | SEGMENT_NODEDATABASE));
    assert(!nodeInfoLiteIsIgnored(database.getMeshNode(0x11111111)) && config.lora.ignore_incoming_count == 1 &&
           config.lora.ignore_incoming[0] == 0x22222222);
    assert(database.savedConfig.lora.ignore_incoming_count == 1);
    const auto saves = database.saveCalls;
    assert(database.legionSetIgnored(0x11111111, false) == LegionIgnoreResult::Unchanged && database.saveCalls == saves);
    for (auto id : {0u, 1u, 2u, 3u, UINT32_MAX, ownNode})
        assert(database.legionSetIgnored(id, true) == LegionIgnoreResult::Invalid);
}

void test_ignore_deferred_failure_capacity_and_group_scope()
{
    reset();
    database.saveSucceeds = false;
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Pending && database.legionIgnoreSavePending());
    const auto saves = database.saveCalls;
    assert(!database.legionFlushIgnoreChanges() && database.saveCalls == saves);
    Time::now = 60000;
    database.saveSucceeds = true;
    assert(database.legionFlushIgnoreChanges() && !database.legionIgnoreSavePending());
    reset();
    xModem.busy = true;
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Pending && database.saveCalls == 0);
    xModem.busy = false;
    assert(database.legionFlushIgnoreChanges());
    reset();
    owner.public_key.size = 0;
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Pending && database.saveCalls == 0);
    reset();
    database.deferSave = true;
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Pending && database.legionIgnoreSavePending());
    reset();
    flashSafe = false;
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Unavailable && database.nodes.empty());
    reset();
    for (unsigned i = 0; i < 118; ++i) {
        auto node = database.getOrCreateMeshNode(i + 100);
        node->bitfield = 16;
    }
    assert(database.legionSetIgnored(0x11111111, true) == LegionIgnoreResult::Capacity && database.nodes.size() == 118);
    for (auto local : {0xabcdef01u, 0xabcdef02u, 0xabcdef03u}) {
        reset();
        ownNode = local;
        TestModule module;
        deliver(module, "/ignore !11111111");
        assert(last().find("Ignored !11111111") != std::string::npos);
        next();
        deliver(module, "/ignorelist", 2);
        assert(last().find("n:1") != std::string::npos && last().find("!11111111") != std::string::npos);
        next();
        deliver(module, "/unignore !11111111", 3);
        assert(last().find("Unignored") != std::string::npos);
        next();
        deliver(module, "/ignorelist", 4);
        assert(last().find("No ignored nodes") != std::string::npos);
    }
    ownNode = 0xabcdef01;
}

void test_gate_rollover_and_bounded_fuzz()
{
    legion::ControlGate gate;
    const uint32_t now = UINT32_MAX - 200;
    assert(gate.reserve(1, 1, now, 250) && !gate.ready(now + 249) && gate.ready(now + 250));
    gate.finish(now + 250);
    assert(!gate.reserve(1, 1, now + 10000, 250));
    assert(gate.reserve(1, 2, now + 10000, 250));
    uint32_t random = 17;
    uint8_t bytes[234];
    for (size_t trial = 0; trial < 10000; ++trial) {
        const size_t size = trial % sizeof(bytes);
        for (size_t i = 0; i < size; ++i) {
            random = random * 1664525 + 1013904223;
            bytes[i] = random >> 24;
        }
        legion::parseControl(bytes, size, ownNode);
        legion::validUtf8(bytes, size);
    }
}

meshtastic_MeshPacket traceReply(size_t index = 0)
{
    const auto &request = meshService.sent.at(index).packet;
    meshtastic_MeshPacket reply;
    reply.from = request.to;
    reply.to = ownNode;
    reply.channel = request.channel;
    reply.decoded.portnum = meshtastic_PortNum_TRACEROUTE_APP;
    reply.decoded.request_id = request.id;
    return reply;
}

meshtastic_RouteDiscovery exampleRoute()
{
    meshtastic_RouteDiscovery route;
    route.route_count = 2;
    route.route[0] = 0x11111111;
    route.route[1] = 0x22222222;
    route.route_back_count = 2;
    route.route_back[0] = 0x33333333;
    route.route_back[1] = 0x44444444;
    return route;
}

void test_trace_parser_and_authorization()
{
    const auto parse = [](const std::string &s) {
        return legion::parseControl(reinterpret_cast<const uint8_t *>(s.data()), s.size(), ownNode);
    };
    for (const auto &s : {"/trace", "/trace !bad !12345678", "/trace !00000001 !12345678"})
        assert(parse(s).command == legion::ControlCommand::None);
    for (const auto &s : {"/trace !abcdef01", "/trace !abcdef01 !bad", "/trace !abcdef01 !abcdef01", "/trace !abcdef01 !00000000",
                          "/trace !abcdef01 !00000003", "/trace !abcdef01 !ffffffff", "/trace !abcdef01 !12345678 extra"})
        assert(parse(s).command == legion::ControlCommand::Trace && !parse(s).valid);
    const auto valid = parse(" /trace !ABCDEF01 !1234ABCD\n");
    assert(valid.valid && valid.node == ownNode && valid.target == 0x1234abcd && !valid.group);
    reset();
    TestModule module;
    auto wrongChannel = packet("/trace !abcdef01 !12345678");
    wrongChannel.channel = 0;
    module.handleReceived(wrongChannel);
    Time::now = 10000;
    module.runOnce();
    assert(meshService.sent.empty());
    deliver(module, "/trace !abcdef02 !12345678");
    assert(meshService.sent.empty());
    deliver(module, "/trace !abcdef01 !00000001");
    assert(meshService.sent.size() == 1 && last().find("Usage: /trace") != std::string::npos);
}

void test_trace_standard_request_and_asymmetric_routes()
{
    reset();
    channel(1, "Remote");
    database.getOrCreateMeshNode(0x12345678)->channel = 1;
    TestModule module;
    deliver(module, "/trace !abcdef01 !12345678");
    assert(meshService.sent.size() == 2);
    const auto request = meshService.sent[0];
    assert(request.packet.to == 0x12345678 && request.packet.channel == 1 && request.packet.from == ownNode);
    assert(request.packet.decoded.portnum == meshtastic_PortNum_TRACEROUTE_APP && request.packet.decoded.want_response);
    assert(request.packet.want_ack && request.packet.decoded.payload.size == 0 && request.source == RX_SRC_USER &&
           request.toPhone);
    assert(last().find("waiting up to 90s") != std::string::npos && meshService.sent[1].packet.channel == 2);
    next();
    deliver(module, "/zerohop !abcdef01", 2);
    assert(last().find("No eligible") != std::string::npos || last().find("n:0") != std::string::npos);
    const auto reply = traceReply();
    auto route = exampleRoute();
    legionControlObserveTraceRoute(reply, route);
    module.runOnce();
    assert(last().find("1/2 out: !abcdef01 > !11111111 > !22222222 > !12345678") != std::string::npos);
    assert(last().find("TR#98765432") != std::string::npos);
    const auto sent = meshService.sent.size();
    legionControlObserveTraceRoute(reply, {});
    module.runOnce();
    assert(meshService.sent.size() == sent);
    Time::now += legion::TRACE_REPLY_GAP_MS - 1;
    module.runOnce();
    assert(meshService.sent.size() == sent);
    ++Time::now;
    module.runOnce();
    assert(last().find("2/2 back: !12345678 > !33333333 > !44444444 > !abcdef01") != std::string::npos);
    assert(database.saveCalls == 0);
    for (size_t i = 1; i < meshService.sent.size(); ++i)
        assert(meshService.sent[i].packet.channel == 2 && text(i).size() <= 199);
}

void test_trace_correlation_and_deadline()
{
    for (int mismatch = 0; mismatch < 7; ++mismatch) {
        reset();
        TestModule module;
        deliver(module, "/trace !abcdef01 !12345678");
        auto reply = traceReply();
        if (mismatch == 0)
            ++reply.decoded.request_id;
        if (mismatch == 1)
            ++reply.from;
        if (mismatch == 2)
            reply.to = NODENUM_BROADCAST;
        if (mismatch == 3)
            reply.channel = 2;
        if (mismatch == 4)
            reply.decoded.portnum = meshtastic_PortNum_TEXT_MESSAGE_APP;
        if (mismatch == 5)
            reply.which_payload_variant = 0;
        auto route = exampleRoute();
        if (mismatch == 6)
            route.route_count = 9;
        legionControlObserveTraceRoute(reply, route);
        Time::now += legion::TRACE_WAIT_MS - 1;
        module.runOnce();
        assert(meshService.sent.size() == 2);
        ++Time::now;
        module.runOnce();
        assert(meshService.sent.size() == 3 && last().find("reachability unknown") != std::string::npos);
        assert(last().find("Unreachable") == std::string::npos && testRouter.cancelled.size() == 1);
        legionControlObserveTraceRoute(traceReply(), exampleRoute());
        Time::now += 10000;
        module.runOnce();
        assert(meshService.sent.size() == 3);
    }
    for (int before = 0; before < 2; ++before) {
        reset();
        TestModule module;
        Time::now = UINT32_MAX - 30000;
        deliver(module, "/trace !abcdef01 !12345678");
        Time::now += legion::TRACE_WAIT_MS - (before ? 1 : 0);
        legionControlObserveTraceRoute(traceReply(), exampleRoute());
        module.runOnce();
        assert(last().find(before ? "1/2 out" : "No traceroute response") != std::string::npos);
    }
}

void test_trace_routing_errors_and_local_failure()
{
    for (const auto error :
         {meshtastic_Routing_Error_NONE, meshtastic_Routing_Error_NO_ROUTE, meshtastic_Routing_Error_MAX_RETRANSMIT,
          meshtastic_Routing_Error_NO_RESPONSE, meshtastic_Routing_Error_TIMEOUT, meshtastic_Routing_Error_DUTY_CYCLE_LIMIT}) {
        reset();
        TestModule module;
        deliver(module, "/trace !abcdef01 !12345678");
        auto ack = traceReply();
        ack.from = 0x77777777; // A relay may return a correlated NAK.
        ack.decoded.portnum = meshtastic_PortNum_ROUTING_APP;
        ++ack.decoded.request_id;
        legionControlObserveTraceError(ack, error);
        Time::now += 6000;
        module.runOnce();
        assert(meshService.sent.size() == 2);
        --ack.decoded.request_id;
        legionControlObserveTraceError(ack, error);
        module.runOnce();
        if (error == meshtastic_Routing_Error_NONE) {
            assert(meshService.sent.size() == 2); // An ACK is not a traceroute response.
            legionControlObserveTraceRoute(traceReply(), exampleRoute());
            module.runOnce();
            assert(last().find("1/2 out") != std::string::npos);
        } else {
            assert(meshService.sent.size() == 3);
            assert((last().find("Unreachable") != std::string::npos) == (error == meshtastic_Routing_Error_NO_ROUTE));
            legionControlObserveTraceRoute(traceReply(), exampleRoute());
            Time::now += 6000;
            module.runOnce();
            assert(meshService.sent.size() == 3);
        }
    }
    reset();
    TestModule module;
    meshService.onSend = [](const meshtastic_MeshPacket &request) {
        if (request.decoded.portnum == meshtastic_PortNum_TRACEROUTE_APP) {
            auto error = traceReply();
            error.from = ownNode;
            error.decoded.portnum = meshtastic_PortNum_ROUTING_APP;
            legionControlObserveTraceError(error, meshtastic_Routing_Error_NO_INTERFACE);
        }
    };
    deliver(module, "/trace !abcdef01 !12345678");
    Time::now += 6000;
    module.runOnce();
    assert(last().find("Routing failed") != std::string::npos);
    reset();
    TestModule rejected;
    meshService.result = 1;
    deliver(rejected, "/trace !abcdef01 !12345678");
    assert(last().find("queue rejected") != std::string::npos);
    Time::now += 100000;
    rejected.runOnce();
    assert(meshService.sent.size() == 2);
    reset();
    TestModule noAllocation;
    allocationFails = true;
    deliver(noAllocation, "/trace !abcdef01 !12345678");
    allocationFails = false;
    Time::now += 100000;
    noAllocation.runOnce();
    assert(meshService.sent.empty());
}

void test_trace_config_changes_and_busy()
{
    for (int change = 0; change < 7; ++change) {
        reset();
        channel(1, "Remote");
        database.getOrCreateMeshNode(0x12345678)->channel = 1;
        TestModule module;
        deliver(module, "/trace !abcdef01 !12345678");
        legionControlObserveTraceRoute(traceReply(), exampleRoute());
        if (change == 0)
            channels.entries[2].settings.psk.bytes[0]++;
        if (change == 1)
            channels.entries[1].settings.psk.bytes[0]++;
        if (change == 2)
            channels.entries[0].settings.psk.bytes[0]++;
        if (change == 3)
            ++radioGeneration;
        if (change == 4)
            supplyReady = false;
        if (change == 5)
            channels.entries[1].role = meshtastic_Channel_Role_DISABLED;
        if (change == 6)
            owner.is_licensed = true;
        Time::now += 6000;
        module.runOnce();
        assert(testRouter.cancelled.size() == 1);
        for (size_t i = 1; i < meshService.sent.size(); ++i)
            assert(text(i).find("1/2 out") == std::string::npos);
        assert(meshService.sent.size() == (change == 0 || change == 4 || change == 6 ? 2 : 3));
    }
    reset();
    TestModule module;
    deliver(module, "/trace !abcdef01 !12345678");
    next();
    deliver(module, "/trace !abcdef01 !22222222", 2);
    assert(last().find("Trace busy") != std::string::npos);
    legionControlObserveTraceRoute(traceReply(), exampleRoute());
    module.runOnce();
    Time::now += 6000;
    module.runOnce();
    next();
    deliver(module, "/trace !abcdef01 !22222222", 3);
    assert(last().find("Trace cooldown") != std::string::npos);
    Time::now += 60000;
    deliver(module, "/trace !abcdef01 !22222222", 4);
    assert(last().find("Trace !22222222 queued") != std::string::npos);
}

void test_trace_pending_validation_and_bounded_output()
{
    for (int change = 0; change < 5; ++change) {
        reset();
        TestModule module;
        module.handleReceived(packet("/trace !abcdef01 !12345678"));
        if (change == 0)
            ++radioGeneration;
        if (change == 1)
            database.getOrCreateMeshNode(0x12345678)->channel = 1;
        if (change == 2)
            xModem.busy = true;
        if (change == 3)
            recoveryBlocked = true;
        if (change == 4)
            admin.editing = true;
        Time::now += 10000;
        module.runOnce();
        assert(meshService.sent.size() == 1 && meshService.sent[0].packet.decoded.portnum == meshtastic_PortNum_TEXT_MESSAGE_APP);
    }
    for (int variant = 0; variant < 3; ++variant) {
        reset();
        TestModule module;
        deliver(module, "/trace !abcdef01 !12345678");
        meshtastic_RouteDiscovery route;
        if (variant == 1) {
            route.snr_towards_count = route.snr_back_count = 1;
        } else if (variant == 2) {
            route.route_count = route.route_back_count = 8;
            for (size_t i = 0; i < 8; ++i)
                route.route[i] = route.route_back[i] = 0x11111111 + i;
            route.route[3] = NODENUM_BROADCAST;
        }
        legionControlObserveTraceRoute(traceReply(), route);
        Time::now += 6000;
        module.runOnce();
        assert(last().size() <= 199);
        assert(last().find(variant == 0   ? "route not reported"
                           : variant == 1 ? "0 reported relays"
                                          : "> ? >") != std::string::npos);
        Time::now += 6000;
        module.runOnce();
        assert(last().size() <= 199 && last().find("2/2 back") != std::string::npos);
    }
    reset();
    TestModule failedResult;
    deliver(failedResult, "/trace !abcdef01 !12345678");
    legionControlObserveTraceRoute(traceReply(), exampleRoute());
    meshService.result = 1;
    Time::now += 6000;
    failedResult.runOnce();
    Time::now += 6000;
    failedResult.runOnce();
    assert(meshService.sent.size() == 3); // Do not send part 2 when part 1 was rejected.
}

void test_boot_query_authorization_and_read_only_behavior()
{
    reset();
    TestModule module;
    deliver(module, "/boot !abcdef02");
    assert(bootReports == 0 && meshService.sent.empty());
    auto wrong = packet("/boot !abcdef01", 2);
    wrong.channel = 0;
    module.handleReceived(wrong);
    Time::now += 10000;
    module.runOnce();
    assert(bootReports == 0 && meshService.sent.empty());
    // Reading boot state must not require safe flash voltage or interrupt a transfer.
    flashSafe = false;
    xModem.busy = true;
    recoveryBlocked = true;
    deliver(module, "/boot !abcdef01", 3);
    assert(bootReports == 1 && meshService.sent.size() == 1 && last().find("BOOT reset:watchdog") != std::string::npos);
    assert(meshService.sent[0].packet.channel == 2 && database.saveCalls == 0);
    next();
    deliver(module, "/boot !abcdef01", 3);
    assert(bootReports == 1); // Duplicate packet ID is not executed again.
    next();
    deliver(module, "/boot !abcdef01 extra", 4);
    assert(last().find("Usage: /boot") != std::string::npos && bootReports == 1);
    next();
    module.handleReceived(packet("/boot !abcdef01", 5));
    ++channels.entries[2].settings.psk.bytes[0];
    Time::now += 10000;
    module.runOnce();
    assert(bootReports == 1);
}

int main()
{
#define RUN(test)                                                                                                                \
    test();                                                                                                                      \
    std::cout << #test << " passed\n"
    RUN(test_parser_targets_and_utf8);
    RUN(test_message_queue_channel_and_duplicates);
    RUN(test_changed_keys_and_pending_destination);
    RUN(test_control_authorization_and_power);
    RUN(test_reboot_deadline_rollover_and_failure);
    RUN(test_zerohop_provenance_and_zero_snr);
    RUN(test_snapshot_pages_owner_expiry_and_utf8);
    RUN(test_directory_capacity_and_all_pages);
    RUN(test_ignore_union_persistence_and_idempotency);
    RUN(test_ignore_deferred_failure_capacity_and_group_scope);
    RUN(test_gate_rollover_and_bounded_fuzz);
    RUN(test_trace_parser_and_authorization);
    RUN(test_trace_standard_request_and_asymmetric_routes);
    RUN(test_trace_correlation_and_deadline);
    RUN(test_trace_routing_errors_and_local_failure);
    RUN(test_trace_config_changes_and_busy);
    RUN(test_trace_pending_validation_and_bounded_output);
    RUN(test_boot_query_authorization_and_read_only_behavior);
}
