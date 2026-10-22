#pragma once
#include "configuration.h"
#include <cstring>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#include <vector>
struct CryptoKey {
    uint8_t bytes[32]{};
    int length = 0;
};
class CryptoEngine
{
  public:
    virtual ~CryptoEngine() = default;
    virtual void hash(uint8_t *bytes, size_t size)
    {
        uint8_t output[32];
        unsigned length = 0;
        EVP_Digest(bytes, size, output, &length, EVP_sha256(), nullptr);
        std::memcpy(bytes, output, 32);
    }
    virtual void hmacSha256(const uint8_t *key, const uint8_t *header, size_t headerSize, const uint8_t *data, size_t size,
                            uint8_t *output)
    {
        std::vector<uint8_t> message;
        if (headerSize)
            message.insert(message.end(), header, header + headerSize);
        if (size)
            message.insert(message.end(), data, data + size);
        unsigned length = 0;
        HMAC(EVP_sha256(), key, 32, message.data(), message.size(), output, &length);
    }
    virtual void encryptAESCtr(CryptoKey, uint8_t *, size_t, uint8_t *) {}
};
extern CryptoEngine *crypto;
