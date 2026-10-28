#pragma once
#include <cstdio>
#include <cstddef>
#include <cstdint>
inline unsigned componentsReports = 0;
inline bool legionComponentsFormat(char *output, size_t size, uint32_t node)
{
    ++componentsReports;
    return std::snprintf(output, size, "!%08lx COMPONENTS\nCC310 SHA:0 MAC:0 SW:0\nSPI:ON 8MHz BULK:ON\nDC/DC:ON REG1",
                         (unsigned long)node) > 0;
}
