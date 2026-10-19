#pragma once
#include <cstdint>
namespace concurrency
{
class OSThread
{
  public:
    explicit OSThread(const char *) {}
    virtual ~OSThread() = default;

  protected:
    virtual int32_t runOnce() = 0;
};
} // namespace concurrency
