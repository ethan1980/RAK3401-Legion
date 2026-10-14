#pragma once
#include <stddef.h>
#include <stdint.h>
using pb_byte_t = uint8_t;
struct pb_msgdesc_t {
    bool fail = false;
    int failAfter = -1;
};
struct pb_ostream_t {
    bool (*callback)(pb_ostream_t *, const pb_byte_t *, size_t);
    void *state;
    size_t max_size;
};
