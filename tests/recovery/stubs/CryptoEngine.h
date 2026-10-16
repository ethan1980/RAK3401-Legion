#pragma once
#include <cstdint>
class CryptoEngine
{
  public:
    bool matchesIdentityKey(const uint8_t *privateKey, const uint8_t *publicKey);
};
extern CryptoEngine *crypto;
