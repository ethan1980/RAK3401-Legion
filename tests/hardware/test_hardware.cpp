// Exercise the production accelerator/session/boot code and nRF52 dispatch with
// Nordic's actual SDK declarations. OpenSSL emulates only the hardware boundary.
// Pin byte-for-byte SHA/HMAC results, 64-byte DMA framing, output atomicity on
// every failure stage, nested/concurrent users and retained shutdown ownership.
// These tests do not establish physical CC310 performance, power draw or resets.
#include "Adafruit_nRFCrypto.h"
#include "Arduino.h"
#include "CryptoEngine.h"
#include "mesh/HardwareRNG.h"
#include "platform/nrf52/LegionBoot.h"
#include "platform/nrf52/LegionComponents.h"
#include "platform/nrf52/LegionCrypto.h"
#include "platform/nrf52/NRF52CryptoSession.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstring>
#include <iostream>
#include <nrf_cc310/include/crys_hash.h>
#include <nrf_cc310/include/crys_hmac.h>
#include <openssl/rand.h>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

Adafruit_nRFCrypto nRFCrypto;
FakePower powerRegisters;
bool softDevice = false, failPowerApi = false;
uint32_t cachedResetReason = 0;
enum class Failure { None, Begin, Init, Update, Finish };
Failure failure = Failure::None;
unsigned updates = 0;
std::atomic<unsigned> active{0}, initializations{0};
std::thread::id sdkOwner;
struct Context {
    std::vector<uint8_t> data, key;
    bool partial = false;
};
std::unordered_map<void *, Context> contexts;

bool Adafruit_nRFCrypto::begin()
{
    assert(active.fetch_add(1) == 0);
    sdkOwner = std::this_thread::get_id();
    ++initializations;
    return failure != Failure::Begin;
}
void Adafruit_nRFCrypto::end()
{
    assert(sdkOwner == std::this_thread::get_id());
    assert(active.fetch_sub(1) == 1);
}
bool FakeRandom::generate(uint8_t *output, size_t size)
{
    assert(active == 1 && sdkOwner == std::this_thread::get_id());
    return RAND_bytes(output, size) == 1;
}
void referenceHash(const uint8_t *input, size_t size, uint8_t *output)
{
    unsigned length = 0;
    assert(EVP_Digest(input, size, output, &length, EVP_sha256(), nullptr) == 1 && length == 32);
}
void referenceMac(const uint8_t *key, const std::vector<uint8_t> &data, uint8_t *output)
{
    unsigned length = 0;
    assert(HMAC(EVP_sha256(), key, 32, data.data(), data.size(), output, &length) && length == 32);
}
CRYSError_t initialize(void *context, const uint8_t *key = nullptr, size_t keySize = 0)
{
    assert(active == 1 && sdkOwner == std::this_thread::get_id());
    if (failure == Failure::Init)
        return 1;
    Context state;
    if (keySize)
        state.key.assign(key, key + keySize);
    contexts[context] = state;
    return 0;
}
CRYSError_t update(void *context, uint8_t *data, size_t size)
{
    assert(active == 1 && sdkOwner == std::this_thread::get_id());
    assert(data && size && (reinterpret_cast<uintptr_t>(data) % 4 == 0));
    auto &state = contexts.at(context);
    assert(!state.partial); // The real SDK rejects an update after a partial block.
    ++updates;
    if (failure == Failure::Update && updates == 2)
        return 2;
    state.partial = size % 64;
    state.data.insert(state.data.end(), data, data + size);
    std::this_thread::yield();
    return 0;
}
CRYSError_t finish(void *context, CRYS_HASH_Result_t output)
{
    assert(active == 1 && sdkOwner == std::this_thread::get_id());
    assert(reinterpret_cast<uintptr_t>(output) % 4 == 0);
    if (failure == Failure::Finish)
        return 3;
    const auto &state = contexts.at(context);
    if (state.key.empty())
        referenceHash(state.data.data(), state.data.size(), reinterpret_cast<uint8_t *>(output));
    else
        referenceMac(state.key.data(), state.data, reinterpret_cast<uint8_t *>(output));
    contexts.erase(context);
    return 0;
}
CRYSError_t CRYS_HASH_Init(CRYS_HASHUserContext_t *context, CRYS_HASH_OperationMode_t mode)
{
    assert(mode == CRYS_HASH_SHA256_mode);
    return initialize(context);
}
CRYSError_t CRYS_HASH_Update(CRYS_HASHUserContext_t *context, uint8_t *data, size_t size)
{
    return update(context, data, size);
}
CRYSError_t CRYS_HASH_Finish(CRYS_HASHUserContext_t *context, CRYS_HASH_Result_t output)
{
    return finish(context, output);
}
CRYSError_t CRYS_HASH_Free(CRYS_HASHUserContext_t *context)
{
    contexts.erase(context);
    return 0;
}
CRYSError_t CRYS_HMAC_Init(CRYS_HMACUserContext_t *context, CRYS_HASH_OperationMode_t mode, uint8_t *key, uint16_t size)
{
    assert(mode == CRYS_HASH_SHA256_mode && size == 32 && reinterpret_cast<uintptr_t>(key) % 4 == 0);
    return initialize(context, key, size);
}
CRYSError_t CRYS_HMAC_Update(CRYS_HMACUserContext_t *context, uint8_t *data, size_t size)
{
    return update(context, data, size);
}
CRYSError_t CRYS_HMAC_Finish(CRYS_HMACUserContext_t *context, CRYS_HASH_Result_t output)
{
    return finish(context, output);
}
CRYSError_t CRYS_HMAC_Free(CRYS_HMACUserContext_t *context)
{
    contexts.erase(context);
    return 0;
}

void testCrypto()
{
    std::array<uint8_t, 32> key, expected, actual;
    for (size_t i = 0; i < key.size(); ++i)
        key[i] = i * 37;
    for (const size_t size : {0u, 1u, 15u, 31u, 32u, 55u, 56u, 63u, 64u, 65u, 127u, 128u, 129u, 233u, 4097u}) {
        std::vector<uint8_t> input(std::max(size, size_t(32)) + 2, 0xa5);
        for (size_t i = 0; i < size; ++i)
            input[i + 1] = i * 17;
        referenceHash(input.data() + 1, size, expected.data());
        crypto->hash(input.data() + 1, size); // Real platform override, in place and unaligned.
        assert(std::equal(expected.begin(), expected.end(), input.begin() + 1));
        assert(input[0] == 0xa5 && input.back() == 0xa5);
        for (const size_t split : {0u, 1u, 15u, 63u, 64u, 65u, 129u}) {
            std::vector<uint8_t> message(split + size);
            for (size_t i = 0; i < message.size(); ++i)
                message[i] = i * 13;
            referenceMac(key.data(), message, expected.data());
            const auto tail = size ? message.data() + split : nullptr;
            crypto->hmacSha256(key.data(), message.data(), split, tail, size, actual.data());
            assert(actual == expected);
        }
    }
    // Every failure must leave helper output untouched, then the real platform
    // override must compute the exact software fallback and permit a later retry.
    std::vector<uint8_t> input(200, 0x37), header(15, 0x81);
    for (const auto injected : {Failure::Begin, Failure::Init, Failure::Update, Failure::Finish}) {
        failure = injected;
        updates = 0;
        actual.fill(0x77);
        assert(!legionCc310Sha256(input.data(), input.size(), actual.data()));
        assert(std::all_of(actual.begin(), actual.end(), [](uint8_t b) { return b == 0x77; }));
        auto data = input;
        updates = 0;
        crypto->hash(data.data(), data.size());
        referenceHash(input.data(), input.size(), expected.data());
        assert(std::equal(expected.begin(), expected.end(), data.begin()));
        updates = 0;
        actual.fill(0x77);
        assert(!legionCc310Hmac(key.data(), header.data(), header.size(), input.data(), input.size(), actual.data()));
        assert(std::all_of(actual.begin(), actual.end(), [](uint8_t b) { return b == 0x77; }));
        updates = 0;
        crypto->hmacSha256(key.data(), header.data(), header.size(), input.data(), input.size(), actual.data());
        auto message = header;
        message.insert(message.end(), input.begin(), input.end());
        referenceMac(key.data(), message, expected.data());
        assert(actual == expected && active == 0 && contexts.empty());
        failure = Failure::None;
        assert(legionCc310Sha256(input.data(), input.size(), actual.data()));
    }
    // The ACK key may alias the output; committing the digest must not corrupt
    // a key or data fragment before the SDK has consumed it.
    actual = key;
    std::vector<uint8_t> empty;
    referenceMac(key.data(), empty, expected.data());
    assert(legionCc310Hmac(actual.data(), nullptr, 0, nullptr, 0, actual.data()) && actual == expected);
    assert(!legionCc310Sha256(nullptr, 1, actual.data()));
    assert(!legionCc310Hmac(nullptr, nullptr, 0, nullptr, 0, actual.data()));

    std::vector<std::thread> workers;
    for (unsigned i = 0; i < 6; ++i)
        workers.emplace_back([&] {
            for (unsigned trial = 0; trial < 80; ++trial) {
                assert(nrf52CryptoBegin()); // Outer caller, nested hash and RNG sessions.
                uint8_t bytes[64]{};
                crypto->hash(bytes, sizeof(bytes));
                assert(HardwareRNG::fill(bytes, sizeof(bytes), false));
                crypto->hmacSha256(key.data(), bytes, 15, bytes + 15, 49, bytes);
                nrf52CryptoEnd();
            }
        });
    for (auto &worker : workers)
        worker.join();
    assert(active == 0 && contexts.empty());
    const auto stats = legionCryptoStats();
    assert(stats.sha > 480 && stats.hmac > 480 && stats.fallback == 18);
    std::cout << "Crypto dispatch, vectors, SDK errors, DMA framing and concurrency passed\n";
}

void testBoot(const std::string &scenario)
{
    powerRegisters.GPREGRET2 = 0xb2; // Our marker plus a foreign low-nibble CRC flag.
    if (scenario == "por")
        cachedResetReason = 0;
    else if (scenario == "watchdog")
        cachedResetReason = 2;
    else if (scenario == "lockup")
        cachedResetReason = 8;
    else if (scenario == "software")
        cachedResetReason = 4;
    else if (scenario == "pin")
        cachedResetReason = 1;
    else
        cachedResetReason = 0x30000;
    if (scenario == "missing")
        powerRegisters.GPREGRET2 = 2;
    if (scenario == "foreign")
        powerRegisters.GPREGRET2 = 0x72;
    softDevice = scenario == "wake" || scenario == "api_failure";
    failPowerApi = scenario == "api_failure";
    legionBootCapture();
    const auto boot = legionBootSnapshot();
    const bool known = scenario == "software" || scenario == "wake" || scenario == "api_failure";
    assert((boot.previous == LegionShutdown::LowBattery) == known);
    assert(boot.reset == cachedResetReason);
    assert(powerRegisters.GPREGRET == 0xa8);
    const auto expectedRegister = scenario == "foreign" ? 0x72u : scenario == "api_failure" ? 0xb2u : 2u;
    assert(powerRegisters.GPREGRET2 == expectedRegister);
    cachedResetReason = 2;
    legionBootCapture();
    assert(legionBootSnapshot().reset == boot.reset); // Capture once; never reinterpret a later register.
    char output[200];
    assert(legionBootFormat(output, sizeof(output), 0xabcdef01));
    assert(std::string(output).find("VBAT:NA") != std::string::npos);
    legionBootObserveVoltage(3891, 3310, false);
    legionBootObserveVoltage(4090, 3333, true);
    assert(legionBootFormat(output, sizeof(output), 0xabcdef01));
    const std::string report = output;
    assert(report.find("!abcdef01 BOOT") == 0 && report.find("VBAT:3891 VDD:3310mV USB:0") != std::string::npos);
    assert(report.size() <= 199 && report.find("CC310") == std::string::npos);
    const auto before = legionCryptoStats();
    assert(legionComponentsFormat(output, sizeof(output), 0xabcdef01));
    assert(std::string(output).find("SPI:OFF NA BULK:ON") != std::string::npos);
    assert(std::string(output).find("DC/DC:OFF REG1") != std::string::npos);
    powerRegisters.DCDCEN = 1;
    legionComponentsSpiAvailable(true);
    assert(legionComponentsFormat(output, sizeof(output), 0xabcdef01));
    assert(std::string(output).find("CC310 SHA:0 MAC:0 SW:0") != std::string::npos);
    assert(std::string(output).find("SPI:ON 8MHz BULK:ON") != std::string::npos);
    assert(std::string(output).find("DC/DC:ON REG1") != std::string::npos);
    const auto after = legionCryptoStats();
    assert(before.sha == after.sha && before.hmac == after.hmac && before.fallback == after.fallback);
    assert(!legionComponentsFormat(output, 12, 0xabcdef01) && !legionComponentsFormat(nullptr, 0, 0xabcdef01));
    assert(!legionBootFormat(output, 12, 0xabcdef01) && !legionBootFormat(nullptr, 0, 0xabcdef01));
    assert(legionBootRecordShutdown(LegionShutdown::BootProtect) == (scenario != "foreign" && scenario != "api_failure"));
    if (scenario != "foreign" && scenario != "api_failure") {
        assert(powerRegisters.GPREGRET2 == 0xa2);
        assert(legionBootRecordShutdown(LegionShutdown::LowVdd) && powerRegisters.GPREGRET2 == 0xc2);
        assert(legionBootRecordShutdown(LegionShutdown::SystemOff) && powerRegisters.GPREGRET2 == 0xd2);
    }
    assert(powerRegisters.GPREGRET == 0xa8);
    std::cout << "Boot " << scenario << " passed: " << report << '\n';
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    if (std::string(argv[1]) == "crypto")
        testCrypto();
    else
        testBoot(argv[1]);
    delete crypto;
}
