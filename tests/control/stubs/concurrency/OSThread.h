#pragma once
#include <cstdint>
namespace concurrency
{
struct InterruptableDelay {
    unsigned interruptions = 0;
    void interrupt() { ++interruptions; }
};
inline InterruptableDelay mainDelay;
class OSThread
{
  public:
    explicit OSThread(const char *) {}
    virtual ~OSThread() = default;

  protected:
    virtual int32_t runOnce() = 0;
};
} // namespace concurrency
