#pragma once

#include "configuration.h"

inline constexpr int meshtastic_User_msg = 0;

inline bool pb_decode_from_bytes(const uint8_t *data, size_t size, const int *, meshtastic_User *user)
{
    // The fixture encodes a User containing only the long_name field.
    if (size < 3 || size - 2 >= sizeof(user->long_name) || data[0] != 0x12 || data[1] != size - 2)
        return false;
    std::memcpy(user->long_name, data + 2, size - 2);
    return true;
}
