#pragma once
#define ARCH_NRF52 1
#define RAK3401_LEGION_DFU 1
void dfuTestLog(const char *, ...);
#define LOG_INFO(...) dfuTestLog(__VA_ARGS__)
#define LOG_ERROR(...) dfuTestLog(__VA_ARGS__)
