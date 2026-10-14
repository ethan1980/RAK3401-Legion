#pragma once
#include "SPILock.h"
namespace concurrency
{
class LockGuard
{
  public:
    explicit LockGuard(Lock *value) : lock(value) { lock->lock(); }
    ~LockGuard() { lock->unlock(); }

  private:
    Lock *lock;
};
} // namespace concurrency
