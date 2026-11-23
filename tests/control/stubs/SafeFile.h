#pragma once

#include "concurrency/Lock.h"
#include <cstdint>
#include <cstring>
#include <vector>

inline concurrency::Lock spiMutex;
inline concurrency::Lock *spiLock = &spiMutex;
inline std::vector<uint8_t> nameRuleFile;
inline bool nameRuleSaveFails = false;
inline std::vector<uint8_t> autoArmFile;
inline bool autoArmSaveFails = false;
constexpr int FILE_O_READ = 0;

struct FakeNameFile {
    std::vector<uint8_t> *bytes = &nameRuleFile;
    size_t position = 0;
    explicit operator bool() const { return !bytes->empty(); }
    size_t read(uint8_t *data, size_t size)
    {
        if (size > bytes->size() - position)
            return 0;
        std::memcpy(data, bytes->data() + position, size);
        position += size;
        return size;
    }
    int read() { return position < bytes->size() ? (*bytes)[position++] : -1; }
    void close() {}
};

inline struct FakeFS {
    FakeNameFile open(const char *name, int)
    {
        return {std::strstr(name, "legionAutoArm") ? &autoArmFile : &nameRuleFile};
    }
} FSCom;

class SafeFile
{
  public:
    SafeFile(const char *name, bool) : autoArm(std::strstr(name, "legionAutoArm") != nullptr) {}
    size_t write(const uint8_t *data, size_t size)
    {
        pending.assign(data, data + size);
        return size;
    }
    bool close()
    {
        if (autoArm ? autoArmSaveFails : nameRuleSaveFails)
            return false;
        (autoArm ? autoArmFile : nameRuleFile) = pending;
        return true;
    }

    void abort() { pending.clear(); }

  private:
    bool autoArm;
    std::vector<uint8_t> pending;
};
