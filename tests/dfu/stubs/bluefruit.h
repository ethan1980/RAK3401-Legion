#pragma once
#include <cstddef>
#include <cstdint>

constexpr uint32_t NRF_SUCCESS = 0;
constexpr uint32_t NRF_ERROR_INVALID_PARAM = 7;
constexpr uint16_t BLE_GATT_STATUS_SUCCESS = 0;
constexpr uint16_t BLE_GATT_STATUS_ATTERR_INVALID_HANDLE = 0x101;
constexpr uint16_t BLE_GATT_STATUS_ATTERR_WRITE_NOT_PERMITTED = 0x103;
constexpr uint16_t BLE_GATT_STATUS_ATTERR_INVALID_OFFSET = 0x107;
constexpr uint16_t BLE_GATT_STATUS_ATTERR_INVALID_ATT_VAL_LENGTH = 0x10d;
constexpr uint16_t BLE_GATT_STATUS_ATTERR_UNLIKELY_ERROR = 0x10e;
constexpr uint16_t BLE_GATT_STATUS_ATTERR_INSUF_RESOURCES = 0x111;
constexpr uint16_t BLE_GATT_STATUS_ATTERR_CPS_CCCD_CONFIG_ERROR = 0x1fd;
constexpr uint8_t BLE_GATTS_OP_WRITE_REQ = 1;
constexpr uint8_t BLE_GATTS_AUTHORIZE_TYPE_WRITE = 2;
constexpr uint8_t BLE_GATTS_SYS_ATTR_FLAG_SYS_SRVCS = 1;
constexpr uint8_t BLE_GAP_ROLE_PERIPH = 1;
constexpr uint8_t BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION = 0x13;
struct ble_gap_addr_t {
    uint8_t type, addr[6];
};
struct ble_gap_irk_t {
    uint8_t bytes[16];
};
struct alignas(2) ble_gap_enc_key_t {
    uint8_t bytes[28];
};
struct ble_gatts_evt_write_t {
    uint16_t handle;
    uint8_t op;
    uint16_t offset, len;
    uint8_t data[20];
};
struct ble_gatts_rw_authorize_reply_params_t {
    uint8_t type;
    struct {
        struct {
            uint16_t gatt_status;
            uint8_t update;
            uint16_t offset, len;
            const uint8_t *p_data;
        } write;
    } params;
};
class BLECharacteristic
{
  public:
    using Callback = void (*)(uint16_t, BLECharacteristic *, ble_gatts_evt_write_t *);
    struct {
        uint16_t value_handle = 12;
    } attributes;
    Callback callback = nullptr;
    bool deferred = true;
    bool notifications = true;
    auto &handles() { return attributes; }
    bool notifyEnabled(uint16_t) { return notifications; }
    void setWriteAuthorizeCallback(Callback value, bool useAdaCallback = true)
    {
        callback = value;
        deferred = useAdaCallback;
    }
};
class BLEConnection
{
  public:
    ble_gap_addr_t address = {1, {1, 2, 3, 4, 5, 6}};
    bool encrypted = true;
    ble_gap_addr_t getPeerAddr() { return address; }
    bool secured() { return encrypted; }
};
class FakeBluefruit
{
  public:
    BLEConnection *Connection(uint16_t);
    struct Advertiser {
        void restartOnDisconnect(bool);
    } Advertising;
};
extern FakeBluefruit Bluefruit;
uint32_t sd_ble_gatts_rw_authorize_reply(uint16_t, const ble_gatts_rw_authorize_reply_params_t *);
uint32_t sd_ble_gatts_sys_attr_get(uint16_t, uint8_t *, uint16_t *, uint32_t);
uint32_t sd_ble_gap_disconnect(uint16_t, uint8_t);
void delay(uint32_t);
void vTaskSuspendAll();
[[noreturn]] void enterOTADfu();
