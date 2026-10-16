#pragma once
namespace concurrency
{
struct DfuTestDelay {
    void interrupt();
};
extern DfuTestDelay mainDelay;
} // namespace concurrency
