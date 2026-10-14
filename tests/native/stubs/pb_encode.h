#pragma once
#include "pb.h"
#include <vector>
inline bool pb_encode(pb_ostream_t *stream, const pb_msgdesc_t *fields, const void *source)
{
    if (fields->fail)
        return false;
    const auto &bytes = *static_cast<const std::vector<uint8_t> *>(source);
    if (bytes.size() > stream->max_size)
        return false;
    for (size_t offset = 0; offset < bytes.size();) {
        const size_t left = bytes.size() - offset;
        const size_t chunk = left < 47 ? left : 47;
        if (!stream->callback(stream, bytes.data() + offset, chunk))
            return false;
        offset += chunk;
    }
    return stream->callback(stream, nullptr, 0);
}
