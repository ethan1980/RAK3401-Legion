#pragma once
#include <cstdint>
struct DfuTestLock {
    bool lock(uint32_t);
    void unlock();
};
extern DfuTestLock *spiLock;
