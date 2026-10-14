#pragma once
namespace concurrency
{
class Lock
{
  public:
    void lock() {}
    void unlock() {}
};
} // namespace concurrency
extern concurrency::Lock *spiLock;
