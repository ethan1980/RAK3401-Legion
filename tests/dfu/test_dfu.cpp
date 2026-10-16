/*
 * Run the actual LegionDfu.cpp callback and main-loop handoff against SDK/RTOS
 * stubs. ATT authorization must never depend on flash, an AdaCallback worker,
 * or a surviving BLEConnection pointer. Failed authorization must not arm a
 * reboot; missing bonds/busy SPI must leave a retryable running node. Only an
 * accepted START may copy bootloader peer data after flash is fenced and tasks
 * are suspended. These are software-contract tests, not physical BLE OTA tests.
 * The SoftDevice stub rejects a successful write without update/data/length;
 * 0.4.1 returned NRF_ERROR_INVALID_PARAM (0x7) on hardware for that omission.
 */
#include "platform/nrf52/LegionDfu.h"
#include <InternalFileSystem.h>
#include <SPILock.h>
#include <algorithm>
#include <cassert>
#include <concurrency/OSThread.h>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <utility/bonding.h>
#include <vector>

namespace
{
bool inCallback, spiHeld, fsHeld, suspended, spiAvailable = true, bondAvailable = true;
bool connectionPresent = true, injectConcurrentStart;
uint32_t nowMs, replyResult, attributeResult;
unsigned replies, lookups, flushes, resets, bonds, disconnects;
unsigned wakeups;
const ble_gatts_evt_write_t *activeRequest;
uint16_t lastStatus;
BLEConnection connection;
BLECharacteristic characteristic;
std::vector<std::string> steps;
struct ResetReached {
};

void send(const std::vector<uint8_t> &payload, uint8_t operation = 1, uint16_t offset = 0, uint16_t handle = 12)
{
    ble_gatts_evt_write_t request = {};
    request.handle = handle;
    request.op = operation;
    request.offset = offset;
    request.len = payload.size();
    std::copy(payload.begin(), payload.end(), request.data);
    const unsigned previous = replies;
    activeRequest = &request;
    inCallback = true;
    characteristic.callback(7, &characteristic, &request);
    inCallback = false;
    activeRequest = nullptr;
    assert(replies == previous + 1);
    std::memset(&request, 0xcc, sizeof(request));
}

void finish(uint32_t advance = 500)
{
    nowMs += advance;
    try {
        legionDfuProcess();
        assert(false && "Accepted START did not reach reset");
    } catch (const ResetReached &) {
    }
    assert(resets == 1 && flushes == 1 && disconnects == 1);
    assert(spiHeld && fsHeld && suspended);
    const auto *peer = reinterpret_cast<const uint8_t *>(0x20007f80UL);
    assert(peer[0] == (connection.encrypted ? 9 : 1));
    assert(peer[24] == (connection.encrypted ? 0x42 : 0));
    for (int i = 52; i < 60; ++i)
        assert(peer[i] == 0xa5);
    uint16_t crc = 0xffff;
    for (int i = 0; i < 60; ++i) {
        crc ^= uint16_t(peer[i]) << 8;
        for (int bit = 0; bit < 8; ++bit)
            crc = crc & 0x8000 ? uint16_t((crc << 1) ^ 0x1021) : uint16_t(crc << 1);
    }
    assert(peer[60] == uint8_t(crc) && peer[61] == uint8_t(crc >> 8));
}
} // namespace

FakeBluefruit Bluefruit;
DfuTestFS InternalFS;
DfuTestLock testLock;
DfuTestLock *spiLock = &testLock;
namespace Time
{
uint32_t getMillis()
{
    return nowMs;
}
} // namespace Time
namespace concurrency
{
DfuTestDelay mainDelay;
void DfuTestDelay::interrupt()
{
    assert(inCallback);
    ++wakeups;
}
} // namespace concurrency
void dfuTestLog(const char *format, ...)
{
    assert(!inCallback);
    char message[256];
    va_list arguments;
    va_start(arguments, format);
    std::vsnprintf(message, sizeof(message), format, arguments);
    va_end(arguments);
    steps.emplace_back(message);
}
BLEConnection *FakeBluefruit::Connection(uint16_t handle)
{
    assert(inCallback && handle == 7);
    ++lookups;
    return connectionPresent ? &connection : nullptr;
}
void FakeBluefruit::Advertiser::restartOnDisconnect(bool value)
{
    assert(!value && fsHeld && !inCallback);
}
uint32_t sd_ble_gatts_rw_authorize_reply(uint16_t handle, const ble_gatts_rw_authorize_reply_params_t *reply)
{
    assert(inCallback && handle == 7 && !spiHeld && !fsHeld);
    assert(reply->type == BLE_GATTS_AUTHORIZE_TYPE_WRITE);
    ++replies;
    lastStatus = reply->params.write.gatt_status;
    const auto &write = reply->params.write;
    if (write.gatt_status == BLE_GATT_STATUS_SUCCESS &&
        (!write.update || write.len != activeRequest->len || write.offset != activeRequest->offset || !write.p_data ||
         std::memcmp(write.p_data, activeRequest->data, write.len) != 0))
        return NRF_ERROR_INVALID_PARAM;
    return replyResult;
}
uint32_t sd_ble_gatts_sys_attr_get(uint16_t handle, uint8_t *data, uint16_t *length, uint32_t flags)
{
    assert(inCallback && handle == 7 && *length == 8 && flags == BLE_GATTS_SYS_ATTR_FLAG_SYS_SRVCS);
    std::memset(data, 0xa5, *length);
    return attributeResult;
}
bool DfuTestLock::lock(uint32_t timeout)
{
    assert(!inCallback && timeout == 5000 && !spiHeld);
    if (injectConcurrentStart) {
        send({1, 4});
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_INSUF_RESOURCES);
    }
    spiHeld = spiAvailable;
    return spiHeld;
}
void DfuTestLock::unlock()
{
    assert(spiHeld && !fsHeld);
    spiHeld = false;
}
void DfuTestFS::_lockFS()
{
    assert(!inCallback && spiHeld && !fsHeld);
    fsHeld = true;
}
bool bond_load_keys(uint8_t role, ble_gap_addr_t *address, bond_keys_t *keys)
{
    assert(!inCallback && spiHeld && !fsHeld && role == BLE_GAP_ROLE_PERIPH);
    assert(address->type == 1 && address->addr[0] == 1);
    ++bonds;
    keys->peer_id.id_addr_info.type = 9;
    std::memset(keys->own_enc.bytes, 0x42, sizeof(keys->own_enc.bytes));
    return bondAvailable;
}
void flash_nrf5x_flush()
{
    assert(!inCallback && spiHeld && fsHeld && !suspended);
    ++flushes;
}
uint32_t sd_ble_gap_disconnect(uint16_t handle, uint8_t reason)
{
    assert(!inCallback && handle == 7 && spiHeld && fsHeld && flushes == 1);
    assert(reason == BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
    ++disconnects;
    return connectionPresent ? 0 : 8;
}
void delay(uint32_t ms)
{
    assert(!inCallback);
    if (fsHeld)
        assert(ms == 100);
    else
        assert(!spiHeld && ms > 0 && ms <= 500);
    nowMs += ms;
}
void vTaskSuspendAll()
{
    assert(!inCallback && fsHeld && flushes == 1);
    suspended = true;
}
[[noreturn]] void enterOTADfu()
{
    assert(suspended && spiHeld && fsHeld);
    ++resets;
    throw ResetReached{};
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    void *mapped = mmap(reinterpret_cast<void *>(0x20007000UL), 4096, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    assert(mapped == reinterpret_cast<void *>(0x20007000UL));
    legionDfuInstall(&characteristic);
    assert(characteristic.callback == legionDfuControlWrite && !characteristic.deferred);
    const std::string test = argv[1];
    if (test == "write_contract") {
        ble_gatts_evt_write_t request = {};
        request.len = 2;
        request.data[0] = 1;
        request.data[1] = 4;
        activeRequest = &request;
        inCallback = true;
        ble_gatts_rw_authorize_reply_params_t reply = {};
        reply.type = BLE_GATTS_AUTHORIZE_TYPE_WRITE;
        assert(sd_ble_gatts_rw_authorize_reply(7, &reply) == NRF_ERROR_INVALID_PARAM);
        reply.params.write.update = 1;
        assert(sd_ble_gatts_rw_authorize_reply(7, &reply) == NRF_ERROR_INVALID_PARAM);
        reply.params.write.len = request.len;
        reply.params.write.p_data = request.data;
        assert(sd_ble_gatts_rw_authorize_reply(7, &reply) == NRF_SUCCESS);
        reply.params.write.len = 1;
        assert(sd_ble_gatts_rw_authorize_reply(7, &reply) == NRF_ERROR_INVALID_PARAM);
        reply.params.write.len = 2;
        reply.params.write.offset = 1;
        assert(sd_ble_gatts_rw_authorize_reply(7, &reply) == NRF_ERROR_INVALID_PARAM);
        inCallback = false;
        activeRequest = nullptr;
    } else if (test == "probes") {
        spiAvailable = bondAvailable = false;
        for (unsigned opcode = 2; opcode < 256; ++opcode) {
            send({uint8_t(opcode)});
            assert(lastStatus == 0);
        }
        send({});
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_INVALID_ATT_VAL_LENGTH);
        send({1}, 2);
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_WRITE_NOT_PERMITTED);
        send({1}, 1, 1);
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_INVALID_OFFSET);
        send({1}, 1, 0, 99);
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_INVALID_HANDLE);
        characteristic.notifications = false;
        send({2});
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_CPS_CCCD_CONFIG_ERROR);
        send({1, 4});
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_CPS_CCCD_CONFIG_ERROR);
        nowMs = 5000;
        legionDfuProcess();
        assert(!lookups && !flushes && !resets && !bonds);
    } else if (test == "rejected") {
        connectionPresent = false;
        send({1, 4});
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_UNLIKELY_ERROR);
        connectionPresent = true;
        attributeResult = 8;
        send({1, 4});
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_UNLIKELY_ERROR);
        attributeResult = 0;
        replyResult = 8;
        send({1, 4});
        nowMs = 5000;
        legionDfuProcess();
        assert(!resets && !flushes);
        replyResult = 0;
        send({1, 4});
        finish();
    } else if (test == "busy_spi" || test == "missing_bond") {
        spiAvailable = test != "busy_spi";
        bondAvailable = test != "missing_bond";
        send({1, 4});
        nowMs = 500;
        legionDfuProcess();
        assert(!spiHeld && !fsHeld && !resets);
        spiAvailable = bondAvailable = true;
        send({1, 4});
        finish();
    } else {
        assert(test == "accepted" || test == "rollover" || test == "unsecured" || test == "concurrent");
        if (test == "rollover")
            nowMs = 0xffffff00U;
        if (test == "unsecured")
            connection.encrypted = false;
        injectConcurrentStart = test == "concurrent";
        const uint32_t start = nowMs;
        send({1, 4});
        assert(lastStatus == 0);
        assert(!resets && !flushes && !bonds);
        send({1, 4});
        assert(lastStatus == BLE_GATT_STATUS_ATTERR_INSUF_RESOURCES);
        send({2});
        assert(lastStatus == 0);
        nowMs = start;
        connectionPresent = false;
        assert(wakeups == 1);
        finish(499);
        assert(lookups == 1 && bonds == unsigned(connection.encrypted));
    }
    assert(munmap(mapped, 4096) == 0);
    std::printf("DFU contract passed: %s (not a hardware OTA test)\n", argv[1]);
}
