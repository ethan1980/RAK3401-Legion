// Compile the actual prepared LegionTelemetryModule.cpp and policy against simulated transports.
// Guard private-channel routing, local app delivery, bounded parsing, reply storms, duplicate
// requests, time rollover, changed keys, low-power cancellation and accurate compact reports.
// Hardware temperature accuracy, SPI signal integrity and actual RF delivery need bench tests.
#include "MeshService.h"
#include "NodeDB.h"
#include "PowerStatus.h"
#include "RadioLibInterface.h"
#include "UptimeClock.h"
#include "mesh/LegionRecovery.h"
#include "modules/LegionTelemetryModule.h"
#include <cassert>
#include <iostream>
#include <string>
#include <thread>

FakeChannels channels;
Owner owner;
uint32_t ownNode = 0xabcdef01;
bool allocationFails = false, supplyReady = true, temperatureReady = true;
uint16_t batteryMv = 4010;
int16_t temperatureQuarters = 117;
MeshService meshService;
MeshService *service = &meshService;
unsigned backupOperations = 0;
LegionBackupCommand lastBackup = LegionBackupCommand::None;
NodeDB database;
NodeDB *nodeDB = &database;
PowerStatus power;
PowerStatus *powerStatus = &power;
RadioLibInterface radio;

uint16_t legionPowerBatteryMv()
{
    return batteryMv;
}
bool legionPowerTxReady()
{
    return supplyReady;
}
bool legionReadCpuTemperature(int16_t &quarters)
{
    quarters = temperatureQuarters;
    return temperatureReady;
}

class TestModule : public LegionTelemetryModule
{
  public:
    using LegionTelemetryModule::handleReceived;
    using LegionTelemetryModule::runOnce;
    bool localLoopback() const { return loopbackOk; }
};

void reset()
{
    channels = {};
    auto &ch = channels.entries[2];
    ch.has_settings = true;
    ch.role = meshtastic_Channel_Role_SECONDARY;
    std::strcpy(ch.settings.name, "LegionRF");
    ch.settings.psk.size = 32;
    std::memset(ch.settings.psk.bytes, 0x42, 32);
    owner = {};
    Time::now = 0;
    supplyReady = temperatureReady = true;
    allocationFails = false;
    batteryMv = 4010;
    temperatureQuarters = 117;
    meshService.sent.clear();
    backupOperations = 0;
    lastBackup = LegionBackupCommand::None;
    power = {};
    radio = {};
    RadioLibInterface::instance = &radio;
}

meshtastic_MeshPacket request(std::string text = "/telemetry", uint32_t id = 1, uint32_t from = 0x12345678)
{
    meshtastic_MeshPacket p;
    p.from = from;
    p.id = id;
    p.channel = 2;
    p.decoded.payload.size = text.size();
    assert(text.size() <= sizeof(p.decoded.payload.bytes));
    std::memcpy(p.decoded.payload.bytes, text.data(), text.size());
    return p;
}

std::string text()
{
    assert(!meshService.sent.empty());
    const auto &p = meshService.sent.back().packet.decoded.payload;
    return {reinterpret_cast<const char *>(p.bytes), p.size};
}

void deliver(TestModule &module, const meshtastic_MeshPacket &p, uint32_t advance = 1000)
{
    assert(module.handleReceived(p) == ProcessMessage::CONTINUE);
    Time::now += advance;
    module.runOnce();
}

void test_standard_private_reply_and_local_copy()
{
    reset();
    TestModule module;
    assert(!module.localLoopback());
    deliver(module, request());
    assert(meshService.sent.size() == 1);
    const auto &sent = meshService.sent[0];
    assert(sent.packet.channel == 2 && sent.packet.to == NODENUM_BROADCAST);
    assert(sent.packet.decoded.portnum == meshtastic_PortNum_TEXT_MESSAGE_APP);
    assert(!sent.packet.want_ack && !sent.packet.decoded.want_response);
    assert(sent.packet.priority == meshtastic_MeshPacket_Priority_BACKGROUND);
    assert(sent.source == RX_SRC_LOCAL && sent.toPhone);
    assert(text().find("!abcdef01") != std::string::npos);
    assert(text().find("2.8.2.LGN0.6.0a1") != std::string::npos);
    assert(text().find("Legion0.5.1") == std::string::npos);
    assert(text().find("Legion0.3.0") == std::string::npos);
}

void test_backup_commands_are_targeted_and_share_channel_and_duplicate_gates()
{
    reset();
    TestModule module;
    for (const auto &command : {"/backup", "/backup replace !11111111", "/backup !abcdef0", "/backup status"})
        deliver(module, request(command));
    assert(backupOperations == 0 && meshService.sent.empty());
    auto wrongChannel = request("/backup !abcdef01");
    wrongChannel.channel = 0;
    deliver(module, wrongChannel);
    assert(backupOperations == 0);
    const auto command = request("/backup !abcdef01");
    deliver(module, command, 250);
    assert(backupOperations == 1 && lastBackup == LegionBackupCommand::Create && meshService.sent.size() == 1);
    Time::now += 61000;
    deliver(module, command, 250);
    assert(backupOperations == 1);
    deliver(module, request("/backup replace !abcdef01", 2), 250);
    assert(backupOperations == 2 && lastBackup == LegionBackupCommand::Replace);
}

void test_backup_cancellation_on_key_change_and_unsafe_power()
{
    reset();
    TestModule module;
    module.handleReceived(request("/backup delete !abcdef01"));
    channels.entries[2].settings.psk.bytes[0] ^= 1;
    Time::now += 1000;
    module.runOnce();
    assert(backupOperations == 0 && meshService.sent.empty());
    Time::now += 61000;
    supplyReady = false;
    deliver(module, request("/backup !abcdef01", 2), 250);
    assert(backupOperations == 0);
}

void test_local_phone_request()
{
    reset();
    TestModule module;
    deliver(module, request("/telemetry", 1, 0));
    assert(meshService.sent.size() == 1);
}

void test_targeted_and_exact_commands()
{
    reset();
    TestModule module;
    for (const auto &command : {"/telemetry !12345678", "/telemetryx", "hi /telemetry", "/telemetry !abcdef0z",
                                "/telemetry !abcdef01 more", "/Telemetry", "/telemetry !abcdef0", "/telemetry !abcdef012"})
        deliver(module, request(command));
    deliver(module, request(std::string("/telemetry\0tail", 15)));
    assert(meshService.sent.empty());
    deliver(module, request(" \t/telemetry !ABCDEF01\r\n"), 250);
    assert(meshService.sent.size() == 1);
}

void test_rejects_wrong_channel_port_destination_and_oversize()
{
    reset();
    TestModule module;
    auto p = request();
    p.channel = 0;
    deliver(module, p);
    p = request();
    p.decoded.portnum = 67;
    deliver(module, p);
    p = request();
    p.to = ownNode;
    deliver(module, p);
    p = request();
    p.which_payload_variant = 99;
    deliver(module, p);
    p = request();
    p.decoded.payload.size = sizeof(p.decoded.payload.bytes) + 1;
    deliver(module, p);
    assert(meshService.sent.empty());
}

void test_missing_disabled_primary_and_duplicate_channels()
{
    for (int mode = 0; mode < 5; ++mode) {
        reset();
        auto &ch = channels.entries[2];
        if (mode == 0)
            ch.has_settings = false;
        if (mode == 1)
            ch.role = meshtastic_Channel_Role_DISABLED;
        if (mode == 2)
            ch.role = meshtastic_Channel_Role_PRIMARY;
        if (mode == 3)
            std::strcpy(ch.settings.name, "LegionTR");
        if (mode == 4)
            channels.entries[3] = ch;
        TestModule module;
        deliver(module, request());
        assert(meshService.sent.empty());
    }
}

void test_rejects_unset_public_invalid_zero_keys_and_ham_mode()
{
    for (int mode = 0; mode < 7; ++mode) {
        reset();
        auto &psk = channels.entries[2].settings.psk;
        if (mode < 4)
            psk.size = mode == 0 ? 0 : mode == 1 ? 1 : mode == 2 ? 15 : 33;
        if (mode == 4)
            channels.publicKeys[2] = true;
        if (mode == 5)
            std::memset(psk.bytes, 0, 32);
        if (mode == 6)
            owner.is_licensed = true;
        TestModule module;
        deliver(module, request());
        assert(meshService.sent.empty());
    }
}

void test_accepts_each_users_own_key_and_channel_index()
{
    for (uint8_t index : {1, 5, 7}) {
        reset();
        channels.entries[index] = channels.entries[2];
        channels.entries[2] = {};
        channels.entries[index].settings.psk.size = 16;
        std::memset(channels.entries[index].settings.psk.bytes, index + 1, 16);
        TestModule module;
        auto p = request();
        p.channel = index;
        deliver(module, p);
        assert(meshService.sent.size() == 1 && meshService.sent[0].packet.channel == index);
    }
}

void test_cooldown_and_repeated_packet()
{
    reset();
    TestModule module;
    const auto original = request();
    deliver(module, original);
    deliver(module, request("/telemetry", 2));
    assert(meshService.sent.size() == 1);
    Time::now = 61000;
    deliver(module, original);
    assert(meshService.sent.size() == 1);
    deliver(module, request("/telemetry", 3));
    assert(meshService.sent.size() == 2);
}

void test_channel_zero_cannot_fall_back_to_primary()
{
    reset();
    channels.entries[0] = channels.entries[2];
    channels.entries[2] = {};
    TestModule module;
    auto p = request();
    p.channel = 0;
    deliver(module, p);
    assert(meshService.sent.empty());
}

void test_pending_reply_ignores_second_request()
{
    reset();
    TestModule module;
    module.handleReceived(request());
    module.handleReceived(request("/telemetry", 2));
    Time::now = 999;
    module.runOnce();
    assert(meshService.sent.empty());
    Time::now = 1000;
    module.runOnce();
    assert(meshService.sent.size() == 1);
}

void test_changed_channel_key_or_aead_cancels_pending()
{
    for (int mode = 0; mode < 4; ++mode) {
        reset();
        TestModule module;
        module.handleReceived(request());
        if (mode == 0)
            channels.entries[2].settings.psk.bytes[0] ^= 1;
        if (mode == 1)
            channels.aead[2] = true;
        if (mode == 2)
            channels.entries[2].role = meshtastic_Channel_Role_DISABLED;
        if (mode == 3)
            std::strcpy(channels.entries[2].settings.name, "Other");
        Time::now = 1000;
        module.runOnce();
        assert(meshService.sent.empty());
    }
}

void test_low_power_and_allocation_failure_do_not_send_or_retry()
{
    for (int mode = 0; mode < 2; ++mode) {
        reset();
        TestModule module;
        supplyReady = mode != 0;
        allocationFails = mode == 1;
        deliver(module, request());
        assert(meshService.sent.empty());
        supplyReady = true;
        allocationFails = false;
        Time::now = 10000;
        module.runOnce();
        assert(meshService.sent.empty());
    }
}

void test_no_automatic_transmission()
{
    reset();
    TestModule module;
    for (unsigned i = 0; i < 36; ++i) {
        Time::now += 3600000;
        module.runOnce();
    }
    assert(meshService.sent.empty());
}

void test_statistics_current_values_and_extrema()
{
    reset();
    TestModule module;
    module.runOnce();
    legionTelemetryObserveNoise(-120);
    legionTelemetryObserveNoise(-90);
    legionTelemetryObserveNoise(-128);
    legionTelemetryObserveNoise(0);
    legionTelemetryObserveBattery(3900);
    batteryMv = 4000;
    temperatureQuarters = -1;
    radio.rxGood = 450;
    radio.rxBad = 7;
    radio.txGood = 32;
    radio.txRelay = 24;
    radio.txDrop = 2;
    deliver(module, request());
    const auto output = text();
    assert(output.find("CPU:-0.25 / max 29.25C") != std::string::npos);
    assert(output.find("BAT:82% 4.00 / min 3.90V") != std::string::npos);
    assert(output.find("N:-105 peak:-90dBm n:2") != std::string::npos);
    assert(output.find("RX:450 BAD:7 TX:32 REL:24 DROP:2") != std::string::npos);
}

void test_unavailable_sensors_and_unknown_charge()
{
    reset();
    TestModule module;
    temperatureReady = false;
    power.battery = false;
    deliver(module, request());
    assert(text().find("CPU:NA / max NAC") != std::string::npos);
    assert(text().find("BAT:NA%") != std::string::npos);
    assert(text().find("N:NA") != std::string::npos);
}

void test_report_fits_single_text_packet_at_counter_limits()
{
    reset();
    TestModule module;
    temperatureQuarters = -160;
    batteryMv = UINT16_MAX;
    radio.rxGood = radio.rxBad = radio.txGood = radio.txRelay = UINT32_MAX;
    radio.txDrop = UINT16_MAX;
    module.observeNoise(-127);
    deliver(module, request());
    assert(text().size() < 200 && text().find("4294967295") != std::string::npos);
}

void test_failed_temperature_refresh_preserves_only_known_maximum()
{
    reset();
    TestModule module;
    module.runOnce();
    temperatureReady = false;
    deliver(module, request());
    assert(text().find("CPU:NA / max 29.25C") != std::string::npos);
}

void test_gate_wrap_and_duplicate_expiry()
{
    legion::TelemetryRequestGate gate;
    const uint32_t start = UINT32_MAX - 499;
    assert(gate.reserve(1, 2, start, 500));
    assert(!gate.ready(UINT32_MAX));
    assert(gate.ready(0));
    gate.finish(0);
    assert(!gate.reserve(1, 3, 59999, 0));
    assert(!gate.reserve(1, 2, 60000, 0));
    assert(gate.reserve(2, 2, 60000, 0));
    gate.finish(60000);
    assert(gate.reserve(1, 2, start + legion::TELEMETRY_DUPLICATE_MS, 0));
}

void test_samples_are_thread_safe()
{
    reset();
    TestModule module;
    std::thread noise([] {
        for (int i = 0; i < 10000; ++i)
            legionTelemetryObserveNoise(-100);
    });
    std::thread supply([] {
        for (int i = 0; i < 10000; ++i)
            legionTelemetryObserveBattery(4000);
    });
    noise.join();
    supply.join();
    deliver(module, request());
    assert(text().find("N:-100 peak:-100dBm n:10000") != std::string::npos);
}

int main()
{
#define RUN(name)                                                                                                                \
    name();                                                                                                                      \
    std::cout << #name << " PASS\n"
    RUN(test_standard_private_reply_and_local_copy);
    RUN(test_backup_commands_are_targeted_and_share_channel_and_duplicate_gates);
    RUN(test_backup_cancellation_on_key_change_and_unsafe_power);
    RUN(test_local_phone_request);
    RUN(test_targeted_and_exact_commands);
    RUN(test_rejects_wrong_channel_port_destination_and_oversize);
    RUN(test_missing_disabled_primary_and_duplicate_channels);
    RUN(test_rejects_unset_public_invalid_zero_keys_and_ham_mode);
    RUN(test_accepts_each_users_own_key_and_channel_index);
    RUN(test_channel_zero_cannot_fall_back_to_primary);
    RUN(test_cooldown_and_repeated_packet);
    RUN(test_pending_reply_ignores_second_request);
    RUN(test_changed_channel_key_or_aead_cancels_pending);
    RUN(test_low_power_and_allocation_failure_do_not_send_or_retry);
    RUN(test_no_automatic_transmission);
    RUN(test_statistics_current_values_and_extrema);
    RUN(test_unavailable_sensors_and_unknown_charge);
    RUN(test_report_fits_single_text_packet_at_counter_limits);
    RUN(test_failed_temperature_refresh_preserves_only_known_maximum);
    RUN(test_gate_wrap_and_duplicate_expiry);
    RUN(test_samples_are_thread_safe);
    legionTelemetryModule = nullptr;
}
