// Exercise the actual prepared firmware policy, streaming protobuf comparison and SafeFile code.
// Guard early transmission after weak recovery, battery/USB misclassification, reboot loops,
// skipped changed settings and replacing good settings with a truncated or corrupted write.
// Hardware I/O is simulated; thresholds and System OFF consumption still need a bench test.
#include "FSCommon.h"
#include "SPILock.h"
#include "SafeFile.h"
#include "mesh/LegionCrc32.h"
#include "mesh/LegionPersistence.h"
#include "power/LegionPowerPolicy.h"
#include <cassert>
#include <iostream>
#include <utility>

FakeFilesystem fakeFs;
concurrency::Lock lock;
concurrency::Lock *spiLock = &lock;

void test_divider_conversion()
{
    assert(legion::batteryMvFromAdc(2867, 1) == 3500);
    assert(legion::batteryMvFromAdc(2867 * 15, 15) == 3500);
    assert(legion::batteryMvFromAdc(0, 15) == 0);
    assert(legion::batteryMvFromAdc(4095, 1) == 4999);
    assert(legion::batteryMvFromAdc(0, 0) == 0);
}

void test_boot_reserve_and_usb()
{
    assert(!legion::bootPowerReady(3500, 3300, false));
    assert(legion::bootPowerReady(3600, 3300, false));
    assert(!legion::bootPowerReady(4000, 2999, false));
    assert(legion::bootPowerReady(0, 3300, true));
    assert(!legion::bootPowerReady(4000, 2800, true));
}

void test_tx_reserve()
{
    assert(!legion::transmitPowerReady(3499, 3300, false));
    assert(legion::transmitPowerReady(3500, 3300, false));
    assert(!legion::transmitPowerReady(4000, 2899, false));
    assert(!legion::transmitPowerReady(4000, 2999, false));
    assert(legion::transmitPowerReady(4000, 3000, false));
    assert(legion::transmitPowerReady(0, 3300, true));
    assert(!legion::transmitPowerReady(4000, 2800, true));
}

void test_consecutive_battery_readings()
{
    legion::PowerPolicy policy;
    assert(!policy.observeBattery(3400, false));
    assert(!policy.observeBattery(3400, false));
    assert(!policy.observeBattery(3500, false));
    assert(!policy.observeBattery(3400, false));
    assert(!policy.observeBattery(3400, false));
    assert(policy.observeBattery(3400, false));
    assert(policy.observeBattery(3400, false));
    assert(!policy.observeBattery(3600, false));
}

void test_exhausted_battery_is_not_absent()
{
    legion::PowerPolicy policy;
    assert(!policy.observeBattery(0, false));
    assert(!policy.observeBattery(0, false));
    assert(policy.observeBattery(0, false));
}

void test_usb_cancels_battery_shutdown()
{
    legion::PowerPolicy policy;
    assert(!policy.observeBattery(3400, false));
    assert(!policy.observeBattery(3400, false));
    assert(!policy.observeBattery(0, true));
    assert(!policy.observeBattery(3400, false));
    assert(!policy.observeBattery(3400, false));
}

void test_vdd_hysteresis_and_duration()
{
    legion::PowerPolicy policy;
    assert(!policy.observeVdd(2899, false));
    for (int i = 0; i < 4; ++i)
        assert(!policy.observeVdd(2950, false));
    assert(policy.observeVdd(2950, false));
    assert(!policy.observeVdd(3000, false));
    assert(!policy.observeVdd(2950, false));
}

void test_usb_cancels_vdd_shutdown()
{
    legion::PowerPolicy policy;
    for (int i = 0; i < 5; ++i)
        assert(!policy.observeVdd(2800, false));
    assert(!policy.observeVdd(2800, true));
    assert(!policy.observeVdd(2800, false));
}

void test_recovery_requires_stable_supply()
{
    legion::PowerPolicy policy;
    for (int i = 0; i < 3; ++i)
        assert(!policy.observeRecovery(3800, 3300, false));
    assert(!policy.observeRecovery(3799, 3300, false));
    assert(!policy.observeRecovery(3900, 2999, false));
    for (int i = 0; i < 3; ++i)
        assert(!policy.observeRecovery(3800, 3300, false));
    assert(policy.observeRecovery(3800, 3300, false));
}

void test_usb_recovery_still_requires_safe_vdd()
{
    legion::PowerPolicy policy;
    assert(!policy.observeRecovery(0, 2999, true));
    assert(policy.observeRecovery(0, 3300, true));
    for (int i = 0; i < 3; ++i)
        assert(!policy.observeRecovery(3900, 3300, false));
    assert(!policy.observeRecovery(0, 2900, true));
    assert(!policy.observeRecovery(3900, 3300, false));
}

uint32_t crc(const std::vector<uint8_t> &bytes)
{
    uint32_t value = 0xffffffffu;
    for (uint8_t byte : bytes)
        value = legionCrc32Update(value, byte);
    return value ^ 0xffffffffu;
}

void test_crc32_standard_vector()
{
    assert(crc({'1', '2', '3', '4', '5', '6', '7', '8', '9'}) == 0xcbf43926u);
    assert(crc({}) == 0);
}

void test_crc32_detects_xor_collision()
{
    assert(crc({0x12, 0x34}) != crc({0x13, 0x35}));
    assert(crc({0x12, 0x34}) != crc({0x12, 0x34, 0, 0}));
}

std::vector<uint8_t> payload()
{
    std::vector<uint8_t> bytes;
    for (int i = 0; i < 137; ++i)
        bytes.push_back(static_cast<uint8_t>(i));
    return bytes;
}

void test_matching_proto_never_writes()
{
    const auto data = payload();
    fakeFs.put("/prefs/config", data);
    const auto mutations = fakeFs.mutations;
    const pb_msgdesc_t fields;
    assert(legionProtoMatchesFile("/prefs/config", 200, &fields, &data));
    assert(fakeFs.mutations == mutations);
}

void test_changed_proto_is_not_skipped()
{
    auto data = payload();
    fakeFs.put("/prefs/config", data);
    data[70] ^= 1;
    const pb_msgdesc_t fields;
    assert(!legionProtoMatchesFile("/prefs/config", 200, &fields, &data));
}

void test_proto_length_mismatch_is_not_skipped()
{
    const auto data = payload();
    auto shorter = data;
    shorter.pop_back();
    fakeFs.put("/prefs/config", shorter);
    const pb_msgdesc_t fields;
    assert(!legionProtoMatchesFile("/prefs/config", 200, &fields, &data));
    auto longer = data;
    longer.push_back(0);
    fakeFs.put("/prefs/config", longer);
    assert(!legionProtoMatchesFile("/prefs/config", 200, &fields, &data));
}

void test_missing_proto_is_not_skipped()
{
    const auto data = payload();
    const pb_msgdesc_t fields;
    assert(!legionProtoMatchesFile("/prefs/missing", 200, &fields, &data));
}

void test_encoding_failure_is_not_skipped()
{
    const auto data = payload();
    fakeFs.put("/prefs/config", data);
    const pb_msgdesc_t fields{true};
    assert(!legionProtoMatchesFile("/prefs/config", 200, &fields, &data));
}

void test_safe_file_replaces_after_verification()
{
    const auto data = payload();
    fakeFs.put("/prefs/config", {9, 9});
    SafeFile file("/prefs/config", true);
    assert(file.write(data.data(), data.size()) == data.size());
    assert(file.close());
    assert(fakeFs.get("/prefs/config") == data);
    assert(!fakeFs.exists("/prefs/config.tmp"));
}

void test_safe_file_single_and_bulk_writes()
{
    const auto data = payload();
    SafeFile file("/prefs/config", true);
    for (size_t i = 0; i < 20; ++i)
        assert(file.write(data[i]) == 1);
    assert(file.write(data.data() + 20, data.size() - 20) == data.size() - 20);
    assert(file.close());
    assert(fakeFs.get("/prefs/config") == data);
}

void test_corruption_preserves_good_file()
{
    const auto data = payload();
    const std::vector<uint8_t> old{9, 9};
    fakeFs.put("/prefs/config", old);
    SafeFile file("/prefs/config", true);
    assert(file.write(data.data(), data.size()) == data.size());
    fakeFs.corruptClose = true;
    assert(!file.close());
    assert(fakeFs.get("/prefs/config") == old);
}

void test_trailing_data_preserves_good_file()
{
    const auto data = payload();
    const std::vector<uint8_t> old{9, 9};
    fakeFs.put("/prefs/config", old);
    SafeFile file("/prefs/config", true);
    assert(file.write(data.data(), data.size()) == data.size());
    fakeFs.appendClose = true;
    assert(!file.close());
    assert(fakeFs.get("/prefs/config") == old);
}

void test_short_write_preserves_good_file()
{
    const auto data = payload();
    const std::vector<uint8_t> old{9, 9};
    fakeFs.put("/prefs/config", old);
    SafeFile file("/prefs/config", true);
    fakeFs.shortWrites = true;
    assert(file.write(data.data(), data.size()) < data.size());
    assert(!file.close());
    assert(fakeFs.get("/prefs/config") == old);
}

void test_failed_rename_preserves_good_file()
{
    const auto data = payload();
    const std::vector<uint8_t> old{9, 9};
    fakeFs.put("/prefs/config", old);
    SafeFile file("/prefs/config", true);
    assert(file.write(data.data(), data.size()) == data.size());
    fakeFs.failRename = true;
    assert(!file.close());
    assert(fakeFs.get("/prefs/config") == old);
    assert(fakeFs.get("/prefs/config.tmp") == data);
}

void test_stale_temp_is_not_appended()
{
    const auto data = payload();
    fakeFs.put("/prefs/config.tmp", {1, 2, 3});
    SafeFile file("/prefs/config", true);
    assert(file.write(data.data(), data.size()) == data.size());
    assert(file.close());
    assert(fakeFs.get("/prefs/config") == data);
}

void test_complete_proto_save()
{
    const auto data = payload();
    const pb_msgdesc_t fields;
    assert(legionSaveProto("/prefs/config", 200, &fields, &data, true));
    assert(fakeFs.get("/prefs/config") == data);
    const auto mutations = fakeFs.mutations;
    assert(legionSaveProto("/prefs/config", 200, &fields, &data, true));
    assert(fakeFs.mutations == mutations);
}

void test_partial_encoding_keeps_complete_file()
{
    const auto data = payload();
    const std::vector<uint8_t> old{9, 9};
    fakeFs.put("/prefs/config", old);
    const pb_msgdesc_t fields{false, 47};
    assert(!legionSaveProto("/prefs/config", 200, &fields, &data, true));
    assert(fakeFs.get("/prefs/config") == old);
    assert(fakeFs.get("/prefs/config.tmp").size() == 47);
}

void test_proto_short_write_keeps_complete_file()
{
    const auto data = payload();
    const std::vector<uint8_t> old{9, 9};
    fakeFs.put("/prefs/config", old);
    const pb_msgdesc_t fields;
    fakeFs.shortWrites = true;
    assert(!legionSaveProto("/prefs/config", 200, &fields, &data, true));
    assert(fakeFs.get("/prefs/config") == old);
}

int main()
{
    const std::pair<const char *, void (*)()> tests[] = {
        {"divider conversion", test_divider_conversion},
        {"boot reserve and USB", test_boot_reserve_and_usb},
        {"TX reserve", test_tx_reserve},
        {"consecutive battery readings", test_consecutive_battery_readings},
        {"exhausted battery", test_exhausted_battery_is_not_absent},
        {"USB cancels battery shutdown", test_usb_cancels_battery_shutdown},
        {"VDD hysteresis", test_vdd_hysteresis_and_duration},
        {"USB cancels VDD shutdown", test_usb_cancels_vdd_shutdown},
        {"stable recovery", test_recovery_requires_stable_supply},
        {"safe USB recovery", test_usb_recovery_still_requires_safe_vdd},
        {"CRC32 reference vector", test_crc32_standard_vector},
        {"CRC32 XOR collisions", test_crc32_detects_xor_collision},
        {"matching protobuf", test_matching_proto_never_writes},
        {"changed protobuf", test_changed_proto_is_not_skipped},
        {"protobuf length", test_proto_length_mismatch_is_not_skipped},
        {"missing protobuf", test_missing_proto_is_not_skipped},
        {"encoding failure", test_encoding_failure_is_not_skipped},
        {"verified file replacement", test_safe_file_replaces_after_verification},
        {"single and bulk writes", test_safe_file_single_and_bulk_writes},
        {"corrupted write", test_corruption_preserves_good_file},
        {"trailing data", test_trailing_data_preserves_good_file},
        {"short write", test_short_write_preserves_good_file},
        {"failed rename", test_failed_rename_preserves_good_file},
        {"stale temporary file", test_stale_temp_is_not_appended},
        {"complete protobuf save", test_complete_proto_save},
        {"partial encoding", test_partial_encoding_keeps_complete_file},
        {"protobuf short write", test_proto_short_write_keeps_complete_file},
    };
    for (const auto &test : tests) {
        fakeFs = {};
        test.second();
        std::cout << "PASS: " << test.first << '\n';
    }
    std::cout << "Passed " << sizeof(tests) / sizeof(tests[0]) << " Legion firmware checks\n";
}
