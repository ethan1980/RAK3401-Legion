#pragma once

#include "concurrency/Lock.h"
#include <cstdint>
#include <cstring>
#include <vector>

inline concurrency::Lock spiMutex;
inline concurrency::Lock *spiLock = &spiMutex;
inline std::vector<uint8_t> nameRuleFile;
inline bool nameRuleSaveFails = false;
constexpr int FILE_O_READ = 0;

struct FakeNameFile {
    size_t position = 0;
    explicit operator bool() const { return !nameRuleFile.empty(); }
    size_t read(uint8_t *data, size_t size)
    {
        if (size > nameRuleFile.size() - position)
            return 0;
        std::memcpy(data, nameRuleFile.data() + position, size);
        position += size;
        return size;
    }
    int read() { return position < nameRuleFile.size() ? nameRuleFile[position++] : -1; }
    void close() {}
};

inline struct FakeFS {
    FakeNameFile open(const char *, int) { return {}; }
} FSCom;

class SafeFile
{
  public:
    SafeFile(const char *, bool) {}
    size_t write(const uint8_t *data, size_t size)
    {
        pending.assign(data, data + size);
        return size;
    }
    bool close()
    {
        if (nameRuleSaveFails)
            return false;
        nameRuleFile = pending;
        return true;
    }

  private:
    std::vector<uint8_t> pending;
};
