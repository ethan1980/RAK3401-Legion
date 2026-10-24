#pragma once
#include <cstddef>
#include <cstdint>
class FakeRandom
{
  public:
    bool generate(uint8_t *output, size_t size);
};
class Adafruit_nRFCrypto
{
  public:
    bool begin();
    void end();
    FakeRandom Random;
};
extern Adafruit_nRFCrypto nRFCrypto;
class nRFCrypto_AES
{
  public:
    enum { encryptFlag, ctrMode };
    size_t blockLen(size_t size) const { return (size + 15) / 16 * 16; }
    bool begin() { return true; }
    bool Process(char *input, size_t size, uint8_t *, uint8_t *, size_t, char *output, int, int)
    {
        for (size_t i = 0; i < size; ++i)
            output[i] = input[i];
        return true;
    }
    void end() {}
};
