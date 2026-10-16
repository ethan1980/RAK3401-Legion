// Compile LegionRecovery.cpp with the real generated Meshtastic messages and nanopb runtime.
// Simulated flash/files and an OpenSSL X25519 oracle exercise create/replace/delete, the exact
// boot preflight, restoration and notice code. This guards losing identity/position during
// serialization, treating healthy changed prefs as loss, and announcing an incomplete restore.
#include "CryptoEngine.h"
#include "ErriezCRC32.h"
#include "FSCommon.h"
#include "NodeDB.h"
#include "SPILock.h"
#include "modules/AdminModule.h"
#include <cassert>
#include <iostream>
#include <openssl/evp.h>
#include <sys/mman.h>

FakeFicr ficr;
FakeFilesystem fakeFs;
concurrency::Lock bus;
concurrency::Lock *spiLock = &bus;
meshtastic_LocalConfig config{};
meshtastic_LocalModuleConfig moduleConfig{};
meshtastic_ChannelFile channelFile{};
meshtastic_DeviceState devicestate{};
meshtastic_User &owner = devicestate.owner;
meshtastic_PositionLite fixedPosition{};
bool positionPresent = true, powerSafe = true;
NodeDB database;
NodeDB *nodeDB = &database;
AdminModule administrator;
AdminModule *adminModule = &administrator;
CryptoEngine cryptography;
CryptoEngine *crypto = &cryptography;
uint32_t rebootAtMsec = 0;
unsigned rawWrites = 0;

// Peer databases are deliberately absent from rescue snapshots; traversing one is a regression.
extern "C" bool meshtastic_NodeDatabase_callback(pb_istream_t *, pb_ostream_t *, const pb_field_t *)
{
    assert(false);
    return false;
}
extern "C" bool meshtastic_NodeDatabase_Legacy_callback(pb_istream_t *, pb_ostream_t *, const pb_field_t *)
{
    assert(false);
    return false;
}

void publicKey(uint8_t *out, const uint8_t *scalar)
{
    EVP_PKEY *key = EVP_PKEY_new_raw_private_key(EVP_PKEY_X25519, nullptr, scalar, 32);
    assert(key);
    size_t size = 32;
    assert(EVP_PKEY_get_raw_public_key(key, out, &size) && size == 32);
    EVP_PKEY_free(key);
}

bool CryptoEngine::matchesIdentityKey(const uint8_t *privateKey, const uint8_t *expected)
{
    uint8_t derived[32];
    publicKey(derived, privateKey);
    return std::memcmp(derived, expected, 32) == 0;
}

void flash_nrf5x_flush() {}
int flash_nrf5x_write(uint32_t address, const void *source, uint32_t size)
{
    assert(address >= 0xe8000 && address + size <= 0xea000);
    ++rawWrites;
    std::memcpy(reinterpret_cast<void *>(address), source, size);
    return size;
}

#include "mesh/LegionRecovery.cpp"

void writeCurrent()
{
    assert(persist(configFileName, meshtastic_LocalConfig_size, &meshtastic_LocalConfig_msg, &config));
    assert(persist(moduleConfigFileName, meshtastic_LocalModuleConfig_size, &meshtastic_LocalModuleConfig_msg, &moduleConfig));
    assert(persist(channelFileName, meshtastic_ChannelFile_size, &meshtastic_ChannelFile_msg, &channelFile));
    assert(persist(deviceStateFileName, meshtastic_DeviceState_size, &meshtastic_DeviceState_msg, &devicestate));
}

void readCurrent()
{
    config = {};
    moduleConfig = {};
    channelFile = {};
    devicestate = {};
    assert(probe(configFileName, meshtastic_LocalConfig_size, &meshtastic_LocalConfig_msg, &config) == PreferenceRead::Valid);
    assert(probe(moduleConfigFileName, meshtastic_LocalModuleConfig_size, &meshtastic_LocalModuleConfig_msg, &moduleConfig) ==
           PreferenceRead::Valid);
    assert(probe(channelFileName, meshtastic_ChannelFile_size, &meshtastic_ChannelFile_msg, &channelFile) ==
           PreferenceRead::Valid);
    assert(probe(deviceStateFileName, meshtastic_DeviceState_size, &meshtastic_DeviceState_msg, &devicestate) ==
           PreferenceRead::Valid);
}

void reset()
{
    std::memset(reinterpret_cast<void *>(legion::RECOVERY_BASE), 0xff, 2 * legion::RECOVERY_PAGE_SIZE);
    restoredThisBoot = noticePending = persistenceBlocked = false;
    rawWrites = 0;
    fakeFs = {};
    powerSafe = positionPresent = true;
    administrator.editing = false;
    rebootAtMsec = 0;
    config = {};
    moduleConfig = {};
    channelFile = {};
    devicestate = {};
    ficr = {};
    config.version = devicestate.version = DEVICESTATE_CUR_VER;
    moduleConfig.version = channelFile.version = POSITION_TELEMETRY_OPTIN_VER;
    config.has_security = config.has_lora = config.has_position = true;
    config.lora.region = meshtastic_Config_LoRaConfig_RegionCode_EU_868;
    config.lora.tx_enabled = true;
    config.lora.spread_factor = 7;
    config.position.fixed_position = true;
    std::memset(config.security.private_key.bytes, 0x18, 32);
    config.security.private_key.bytes[31] = 0x58;
    config.security.private_key.size = config.security.public_key.size = 32;
    publicKey(config.security.public_key.bytes, config.security.private_key.bytes);
    devicestate.has_owner = devicestate.has_my_node = true;
    devicestate.my_node.my_node_num = crc32Buffer(config.security.public_key.bytes, 32);
    std::strcpy(owner.long_name, "Test Legion");
    std::strcpy(owner.short_name, "TL");
    owner.public_key.size = 32;
    std::memcpy(owner.public_key.bytes, config.security.public_key.bytes, 32);
    owner.has_is_unmessagable = owner.is_unmessagable = true;
    channelFile.channels_count = 3;
    auto &channel = channelFile.channels[2];
    channel.has_settings = true;
    channel.role = meshtastic_Channel_Role_SECONDARY;
    std::strcpy(channel.settings.name, "LegionRF");
    channel.settings.psk.size = 32;
    std::memset(channel.settings.psk.bytes, 0x42, 32);
    moduleConfig.has_mqtt = moduleConfig.mqtt.enabled = true;
    fixedPosition = {};
    fixedPosition.latitude_i = 403456789;
    fixedPosition.longitude_i = -37000000;
    fixedPosition.altitude = 655;
    writeCurrent();
}

std::string command(LegionBackupCommand operation)
{
    char reply[200]{};
    legionRecoveryCommand(operation, reply, sizeof(reply));
    return reply;
}

void arm()
{
    assert(command(LegionBackupCommand::Create).find("saved and verified") != std::string::npos);
}

void completeRestore()
{
    readCurrent();
    meshtastic_PositionLite position;
    bool present = false;
    assert(legionRecoveryPosition(position, present) && present);
    assert(position.latitude_i == 403456789 && position.longitude_i == -37000000 && position.altitude == 655);
    assert(legionRecoveryFinish());
}

void test_real_protobuf_snapshot_preserves_identity_settings_and_position()
{
    reset();
    arm();
    RecoveryPage page;
    assert(store.load(page) == RecoveryRead::Valid);
    meshtastic_BackupPreferences backup{};
    assert(snapshotValid(page, backup));
    assert(backup.config.security.private_key.size == 32 &&
           !std::memcmp(backup.config.security.private_key.bytes, config.security.private_key.bytes, 32));
    assert(backup.config.lora.spread_factor == 7 && backup.module_config.mqtt.enabled);
    assert(!std::strcmp(backup.owner.long_name, "Test Legion") && !backup.owner.is_unmessagable && !backup.owner.is_licensed);
    assert(page.hasPosition && page.latitude == fixedPosition.latitude_i);
    const auto generation = page.generation;
    std::strcpy(owner.long_name, "New current name");
    config.lora.spread_factor = 9;
    writeCurrent();
    assert(legionRecoveryBoot() == LegionBootRecovery::None);
    assert(store.load(page) == RecoveryRead::Valid && page.generation == generation);
    assert(!std::strcmp(owner.long_name, "New current name") && config.lora.spread_factor == 9);
    assert(command(LegionBackupCommand::Create).find("already exists") != std::string::npos);
}

void test_missing_and_corrupt_preferences_restore_before_a_notice()
{
    for (bool corrupt : {false, true}) {
        reset();
        arm();
        if (corrupt)
            fakeFs.put(moduleConfigFileName, {0xff, 0xff});
        else
            fakeFs.remove(configFileName);
        assert(legionRecoveryBoot() == LegionBootRecovery::Restored);
        char text[200];
        assert(!legionRecoveryNotice(text, sizeof(text), 2));
        completeRestore();
        assert(!owner.is_unmessagable && config.lora.spread_factor == 7);
        assert(legionRecoveryNotice(text, sizeof(text), 2));
        assert(std::string(text) == "Ashes to ashes, dust to dust, the node Test Legion has risen again");
        assert(!legionRecoveryNotice(text, sizeof(text), 0));
        assert(legionRecoveryNoticeAttempt());
        legionRecoveryNoticeQueued();
        restoredThisBoot = noticePending = false;
        assert(legionRecoveryBoot() == LegionBootRecovery::None && !legionRecoveryNotice(text, sizeof(text), 2));
    }
}

void test_temporary_reads_and_supported_v26_markers_do_not_restore()
{
    reset();
    arm();
    const auto writes = rawWrites;
    assert(legionRecoveryBoot() == LegionBootRecovery::None && rawWrites == writes);
    fakeFs.failOpenName = configFileName;
    assert(legionRecoveryBoot() == LegionBootRecovery::Blocked && rawWrites == writes);
    fakeFs.failOpenName.clear();
    config.version = 999;
    writeCurrent();
    assert(legionRecoveryBoot() == LegionBootRecovery::Blocked && rawWrites == writes);
}

void test_format_survival_factory_reset_delete_and_key_retirement()
{
    reset();
    arm();
    assert(legionRecoveryFactoryReset() == 1);
    assert(legionRecoveryBoot() == LegionBootRecovery::Restored);
    completeRestore();
    fakeFs.files.clear();
    assert(legionRecoveryBoot() == LegionBootRecovery::Restored);
    completeRestore();
    assert(command(LegionBackupCommand::Delete).find("deleted; recovery disabled") != std::string::npos);
    fakeFs.files.clear();
    assert(legionRecoveryBoot() == LegionBootRecovery::None && legionRecoveryFactoryReset() == 0);
    reset();
    arm();
    assert(legionRecoveryAcceptIdentity(nodeDB->getNodeNum() ^ 1));
    fakeFs.files.clear();
    assert(legionRecoveryBoot() == LegionBootRecovery::None);
}

void test_replace_unchanged_busy_and_low_power()
{
    reset();
    arm();
    auto writes = rawWrites;
    assert(command(LegionBackupCommand::Replace).find("already up to date") != std::string::npos && rawWrites == writes);
    std::strcpy(owner.long_name, "Explicit replacement");
    administrator.editing = true;
    assert(command(LegionBackupCommand::Replace).find("busy") != std::string::npos && rawWrites == writes);
    administrator.editing = false;
    powerSafe = false;
    assert(command(LegionBackupCommand::Replace).find("failed") != std::string::npos && rawWrites == writes);
    powerSafe = true;
    assert(command(LegionBackupCommand::Replace).find("saved and verified") != std::string::npos && rawWrites == writes + 1);
}

int main()
{
    void *memory = mmap(reinterpret_cast<void *>(legion::RECOVERY_BASE), 8192, PROT_READ | PROT_WRITE,
                        MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED_NOREPLACE, -1, 0);
    assert(memory == reinterpret_cast<void *>(legion::RECOVERY_BASE));
    test_real_protobuf_snapshot_preserves_identity_settings_and_position();
    test_missing_and_corrupt_preferences_restore_before_a_notice();
    test_temporary_reads_and_supported_v26_markers_do_not_restore();
    test_format_survival_factory_reset_delete_and_key_retirement();
    test_replace_unchanged_busy_and_low_power();
    assert(munmap(memory, 8192) == 0);
    std::cout << "Recovery engine: real protobuf identity/settings/position and transaction checks passed\n";
}
